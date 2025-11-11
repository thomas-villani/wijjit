"""Tests for state management."""

from unittest.mock import Mock

import pytest

from wijjit.core.state import State


class TestState:
    """Tests for State class."""

    def test_init_empty(self):
        """Test creating empty state."""
        state = State()
        assert len(state) == 0
        assert dict(state) == {}

    def test_init_with_data(self):
        """Test creating state with initial data."""
        state = State({"name": "Alice", "age": 30})
        assert len(state) == 2
        assert state["name"] == "Alice"
        assert state["age"] == 30

    def test_setitem(self):
        """Test setting items."""
        state = State()
        state["name"] = "Bob"
        assert state["name"] == "Bob"

    def test_getitem(self):
        """Test getting items."""
        state = State({"name": "Charlie"})
        assert state["name"] == "Charlie"

    def test_getitem_keyerror(self):
        """Test getting non-existent key raises KeyError."""
        state = State()
        with pytest.raises(KeyError):
            _ = state["nonexistent"]

    def test_attribute_access_get(self):
        """Test getting values via attribute access."""
        state = State({"name": "Diana"})
        assert state.name == "Diana"

    def test_attribute_access_set(self):
        """Test setting values via attribute access."""
        state = State()
        state.name = "Eve"
        assert state["name"] == "Eve"
        assert state.name == "Eve"

    def test_attribute_access_error(self):
        """Test accessing non-existent attribute raises AttributeError."""
        state = State()
        with pytest.raises(AttributeError):
            _ = state.nonexistent

    def test_contains(self):
        """Test membership checking."""
        state = State({"key": "value"})
        assert "key" in state
        assert "other" not in state

    def test_len(self):
        """Test length."""
        state = State()
        assert len(state) == 0

        state["a"] = 1
        assert len(state) == 1

        state["b"] = 2
        assert len(state) == 2

    def test_keys(self):
        """Test getting keys."""
        state = State({"a": 1, "b": 2})
        assert set(state.keys()) == {"a", "b"}

    def test_values(self):
        """Test getting values."""
        state = State({"a": 1, "b": 2})
        assert set(state.values()) == {1, 2}

    def test_items(self):
        """Test getting items."""
        state = State({"a": 1, "b": 2})
        assert set(state.items()) == {("a", 1), ("b", 2)}

    def test_on_change_callback(self):
        """Test global change callback."""
        state = State({"count": 0})
        callback = Mock()
        state.on_change(callback)

        state["count"] = 1

        callback.assert_called_once_with("count", 0, 1)

    def test_on_change_multiple_callbacks(self):
        """Test multiple global callbacks."""
        state = State()
        callback1 = Mock()
        callback2 = Mock()

        state.on_change(callback1)
        state.on_change(callback2)

        state["value"] = 42

        callback1.assert_called_once_with("value", None, 42)
        callback2.assert_called_once_with("value", None, 42)

    def test_on_change_no_trigger_on_same_value(self):
        """Test callback not triggered when value doesn't change."""
        state = State({"count": 5})
        callback = Mock()
        state.on_change(callback)

        state["count"] = 5  # Same value

        callback.assert_not_called()

    def test_on_change_via_attribute(self):
        """Test callback triggered via attribute access."""
        state = State()
        callback = Mock()
        state.on_change(callback)

        state.name = "Test"

        callback.assert_called_once_with("name", None, "Test")

    def test_watch_specific_key(self):
        """Test watching a specific key."""
        state = State({"a": 1, "b": 2})
        callback = Mock()
        state.watch("a", callback)

        state["a"] = 10  # Should trigger
        state["b"] = 20  # Should not trigger

        callback.assert_called_once_with(1, 10)

    def test_watch_multiple_keys(self):
        """Test watching multiple keys."""
        state = State({"x": 1, "y": 2})
        callback_x = Mock()
        callback_y = Mock()

        state.watch("x", callback_x)
        state.watch("y", callback_y)

        state["x"] = 10
        state["y"] = 20

        callback_x.assert_called_once_with(1, 10)
        callback_y.assert_called_once_with(2, 20)

    def test_watch_new_key(self):
        """Test watching a key that doesn't exist yet."""
        state = State()
        callback = Mock()
        state.watch("newkey", callback)

        state["newkey"] = "value"

        callback.assert_called_once_with(None, "value")

    def test_unwatch_specific_callback(self):
        """Test unwatching a specific callback."""
        state = State({"count": 0})
        callback1 = Mock()
        callback2 = Mock()

        state.watch("count", callback1)
        state.watch("count", callback2)

        state.unwatch("count", callback1)

        state["count"] = 1

        callback1.assert_not_called()
        callback2.assert_called_once_with(0, 1)

    def test_unwatch_all_callbacks(self):
        """Test unwatching all callbacks for a key."""
        state = State({"count": 0})
        callback1 = Mock()
        callback2 = Mock()

        state.watch("count", callback1)
        state.watch("count", callback2)

        state.unwatch("count")  # Remove all

        state["count"] = 1

        callback1.assert_not_called()
        callback2.assert_not_called()

    def test_unwatch_nonexistent_key(self):
        """Test unwatching a key that isn't watched."""
        state = State()
        # Should not raise an error
        state.unwatch("nonexistent")

    def test_update(self):
        """Test updating multiple values."""
        state = State({"a": 1, "b": 2})
        callback = Mock()
        state.on_change(callback)

        state.update({"a": 10, "c": 3})

        assert state["a"] == 10
        assert state["b"] == 2
        assert state["c"] == 3
        assert callback.call_count == 2  # Called for 'a' and 'c'

    def test_reset_with_data(self):
        """Test resetting state with new data."""
        state = State({"a": 1, "b": 2})
        callback = Mock()
        state.on_change(callback)

        state.reset({"x": 10, "y": 20})

        assert dict(state) == {"x": 10, "y": 20}
        # Should trigger changes for removed keys (a, b) and added keys (x, y)
        assert callback.call_count == 4

    def test_reset_empty(self):
        """Test resetting state to empty."""
        state = State({"a": 1, "b": 2})
        callback = Mock()
        state.on_change(callback)

        state.reset()

        assert dict(state) == {}
        assert callback.call_count == 2  # Called for 'a' and 'b' removal

    def test_callback_exception_handling(self):
        """Test that exceptions in callbacks don't break state updates."""
        state = State()

        def bad_callback(key, old, new):
            raise ValueError("Callback error")

        good_callback = Mock()

        state.on_change(bad_callback)
        state.on_change(good_callback)

        # Should not raise, and good_callback should still be called
        state["value"] = 42

        good_callback.assert_called_once_with("value", None, 42)

    def test_watcher_exception_handling(self):
        """Test that exceptions in watchers don't break state updates."""
        state = State()

        def bad_watcher(old, new):
            raise ValueError("Watcher error")

        good_watcher = Mock()

        state.watch("key", bad_watcher)
        state.watch("key", good_watcher)

        # Should not raise, and good_watcher should still be called
        state["key"] = "value"

        good_watcher.assert_called_once_with(None, "value")

    def test_private_attributes(self):
        """Test that private attributes work correctly."""
        state = State()
        # Should access internal attributes without going through __getitem__
        assert isinstance(state._change_callbacks, list)
        assert isinstance(state._watchers, dict)

    def test_del_item(self):
        """Test deleting items."""
        state = State({"a": 1, "b": 2})
        del state["a"]
        assert "a" not in state
        assert "b" in state

    def test_change_detection_with_complex_types(self):
        """Test change detection with lists and dicts."""
        state = State({"my_list": [1, 2, 3]})
        callback = Mock()
        state.on_change(callback)

        # Modifying the list in place doesn't trigger change
        state["my_list"].append(4)
        callback.assert_not_called()

        # Reassigning triggers change
        state["my_list"] = [1, 2, 3, 4, 5]
        callback.assert_called_once()

    def test_reserved_name_in_init(self):
        """Test that using reserved dict method names in init raises error."""
        with pytest.raises(
            ValueError, match="State keys cannot use reserved dict method names"
        ):
            State({"items": []})

        with pytest.raises(
            ValueError, match="State keys cannot use reserved dict method names"
        ):
            State({"keys": {}})

        with pytest.raises(
            ValueError, match="State keys cannot use reserved dict method names"
        ):
            State({"values": 123})

    def test_reserved_name_in_setitem(self):
        """Test that setting reserved dict method names raises error."""
        state = State()

        with pytest.raises(ValueError, match="State key 'items' is reserved"):
            state["items"] = []

        with pytest.raises(ValueError, match="State key 'keys' is reserved"):
            state["keys"] = {}

        with pytest.raises(ValueError, match="State key 'values' is reserved"):
            state["values"] = 123

    def test_non_reserved_names_work(self):
        """Test that non-reserved names work fine."""
        # These should all work without error
        state = State(
            {
                "items_list": [],
                "my_keys": {},
                "data_values": 123,
                "count": 0,
                "message": "hello",
            }
        )

        assert state["items_list"] == []
        assert state["my_keys"] == {}
        assert state["data_values"] == 123

        # Setting new non-reserved keys should also work
        state["new_key"] = "test"
        assert state["new_key"] == "test"
