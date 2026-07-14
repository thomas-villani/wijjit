"""Tests for state management."""

import asyncio
import logging
import threading
from unittest.mock import Mock

import pytest

from wijjit.core.state import State
from wijjit.exceptions import StateKeyError


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

    def test_copy_returns_independent_state(self):
        """copy() returns a detached State, and does not raise.

        UserDict.copy() reassigns self.data, which State.__setattr__ rejects,
        so the inherited copy() raised StateKeyError. State overrides it.
        """
        state = State({"a": 1})
        callback = Mock()
        state.on_change(callback)

        clone = state.copy()

        assert isinstance(clone, State)
        assert dict(clone) == {"a": 1}

        # Independent data: writing to the clone leaves the original alone...
        clone["a"] = 2
        assert state["a"] == 1
        # ...and the original's callbacks are not carried over.
        callback.assert_not_called()

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

    def test_off_change_stops_callback(self):
        """off_change unregisters a global callback (counterpart to on_change)."""
        state = State({"count": 0})
        callback = Mock()
        state.on_change(callback)

        state["count"] = 1
        callback.assert_called_once_with("count", 0, 1)

        state.off_change(callback)
        state["count"] = 2
        # No further calls after removal.
        callback.assert_called_once_with("count", 0, 1)

    def test_off_change_unregistered_callback_is_noop(self):
        """off_change on a never-registered callback does nothing."""
        state = State({"count": 0})
        callback = Mock()
        state.off_change(callback)  # should not raise
        state["count"] = 1
        callback.assert_not_called()

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

        callback.assert_called_once_with("a", 1, 10)

    def test_watch_multiple_keys(self):
        """Test watching multiple keys."""
        state = State({"x": 1, "y": 2})
        callback_x = Mock()
        callback_y = Mock()

        state.watch("x", callback_x)
        state.watch("y", callback_y)

        state["x"] = 10
        state["y"] = 20

        callback_x.assert_called_once_with("x", 1, 10)
        callback_y.assert_called_once_with("y", 2, 20)

    def test_watch_new_key(self):
        """Test watching a key that doesn't exist yet."""
        state = State()
        callback = Mock()
        state.watch("newkey", callback)

        state["newkey"] = "value"

        callback.assert_called_once_with("newkey", None, "value")

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
        callback2.assert_called_once_with("count", 0, 1)

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

    def test_update_with_kwargs(self):
        """Test updating with keyword arguments."""
        state = State()
        callback = Mock()
        state.on_change(callback)

        state.update({}, count=5, ready=True)

        assert state["count"] == 5
        assert state["ready"] is True
        assert callback.call_count == 2  # Called for 'count' and 'ready'

    def test_update_combined(self):
        """Test updating with both dict and kwargs."""
        state = State()
        callback = Mock()
        state.on_change(callback)

        state.update({"a": 1}, b=2, c=3)

        assert state["a"] == 1
        assert state["b"] == 2
        assert state["c"] == 3
        assert callback.call_count == 3  # Called for 'a', 'b', and 'c'

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

        def bad_watcher(key, old, new):
            raise ValueError("Watcher error")

        good_watcher = Mock()

        state.watch("key", bad_watcher)
        state.watch("key", good_watcher)

        # Should not raise, and good_watcher should still be called
        state["key"] = "value"

        good_watcher.assert_called_once_with("key", None, "value")

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

    def test_method_named_keys_allowed_in_init(self):
        """Keys that shadow a State/dict method are legal at construction."""
        state = State({"items": [1, 2], "keys": {"a": 1}, "values": 123})

        assert state["items"] == [1, 2]
        assert state["keys"] == {"a": 1}
        assert state["values"] == 123

    def test_method_named_keys_allowed_in_setitem(self):
        """Subscript assignment accepts method-shadowing names."""
        state = State()

        state["items"] = ["a"]
        state["get"] = "gettable"
        state["update"] = 7

        assert state["items"] == ["a"]
        assert state["get"] == "gettable"
        assert state["update"] == 7

    def test_data_key_coexists_with_backing_store(self):
        """state['data'] is a normal key; self.data stays the backing store."""
        state = State({"data": "my value"})

        assert state["data"] == "my value"
        # The backing store still holds every key, including 'data' itself.
        assert state.data == {"data": "my value"}

    def test_mapping_protocol_survives_shadowed_keys(self):
        """dict(state) calls keys(); it must not resolve to a user key.

        This is why the shadowing is not inverted on the Python side: the
        Mapping protocol reaches the methods through attribute access.
        """
        state = State({"items": [1], "keys": "k", "values": "v", "get": "g"})

        assert dict(state) == {"items": [1], "keys": "k", "values": "v", "get": "g"}
        assert len(state) == 4
        assert set(state.keys()) == {"items", "keys", "values", "get"}
        assert state.get("items") == [1]

    def test_attribute_write_of_shadowed_name_raises(self):
        """state.items = x is refused: the same syntax cannot read it back."""
        state = State()

        with pytest.raises(StateKeyError, match=r"'items' shadows State.items"):
            state.items = ["a"]

        # The error points at the working form, which does not raise.
        state["items"] = ["a"]
        assert state["items"] == ["a"]

    def test_attribute_write_of_data_still_raises(self):
        """state.data = {...} would replace the store without callbacks."""
        state = State({"count": 1})

        with pytest.raises(StateKeyError, match="backing store"):
            state.data = {"other": 2}

        assert state["count"] == 1

    def test_method_named_keys_in_update_and_reset(self):
        """update() and reset() accept method-shadowing names too."""
        state = State({"old_key": "old"})

        state.update({"items": [1]}, values=2)
        assert state["items"] == [1]
        assert state["values"] == 2

        state.reset({"keys": "k", "copy": "c"})
        assert "old_key" not in state
        assert state["keys"] == "k"
        assert state["copy"] == "c"


class TestReentrancyGuard:
    """Tests for the re-entrant change-notification depth guard."""

    def test_cyclic_callback_does_not_recurse_forever(self):
        """A callback that writes back to state must not crash the interpreter."""
        from wijjit.core.state import _MAX_NOTIFY_DEPTH

        state = State({"x": 0, "log": []})
        invocations = []

        def cyclic(key, old, new):
            invocations.append(key)
            # Writing state re-triggers notification (the footgun).
            state["log"] = (state.get("log") or []) + [key]

        state.on_change(cyclic)
        state["x"] = 1  # Would previously recurse until a RecursionError.

        # Bounded by the depth guard rather than unbounded.
        assert len(invocations) <= _MAX_NOTIFY_DEPTH + 1
        assert state["x"] == 1

    def test_shallow_derived_state_still_propagates(self):
        """Legitimate derived-state chains (a -> b) keep working."""
        state = State({"a": 0, "b": 0})
        state.watch("a", lambda k, o, n: state.__setitem__("b", n * 2))
        state["a"] = 5
        assert state["b"] == 10

    def test_depth_resets_after_dispatch(self):
        """The depth counter returns to zero after a normal change."""
        state = State({"a": 0})
        state.on_change(lambda k, o, n: None)
        state["a"] = 1
        assert state._notify_depth == 0


class TestAsyncCallbackTracking:
    """Tests for tracking/error-surfacing of async on_change/watch callbacks
    (review item 2.7): exceptions must always be retrieved (no "Task exception
    was never retrieved" warnings) and worker-thread-scheduled tasks must be
    visible to flush_pending_async / the event loop's shutdown sweep.
    """

    @pytest.mark.asyncio
    async def test_async_on_change_exception_calls_error_hook(self):
        """An exception raised by an async on_change callback reaches the hook."""
        state = State({"k": 0})
        calls = []
        state._error_hook = lambda msg, exc: calls.append((msg, exc))

        async def bad_callback(key, old, new):
            raise ValueError("boom")

        state.on_change(bad_callback)
        state["k"] = 1
        await state.flush_pending_async()

        assert len(calls) == 1
        message, exc = calls[0]
        assert "bad_callback" in message
        assert "callback" in message
        assert isinstance(exc, ValueError)
        assert state._pending_tasks == set()

    @pytest.mark.asyncio
    async def test_async_watch_exception_calls_error_hook(self):
        """An exception raised by an async watch callback reaches the hook."""
        state = State({"k": 0})
        calls = []
        state._error_hook = lambda msg, exc: calls.append((msg, exc))

        async def bad_watcher(key, old, new):
            raise ValueError("boom")

        state.watch("k", bad_watcher)
        state["k"] = 1
        await state.flush_pending_async()

        assert len(calls) == 1
        message, exc = calls[0]
        assert "bad_watcher" in message
        assert "watcher" in message
        assert isinstance(exc, ValueError)
        assert state._pending_tasks == set()

    @pytest.mark.asyncio
    async def test_async_callback_exception_logged_without_hook(self, wijjit_caplog):
        """With no error hook set, the exception is still retrieved and logged
        (proving it isn't silently dropped / left for asyncio to warn about)."""
        state = State({"k": 0})
        assert state._error_hook is None

        async def bad_callback(key, old, new):
            raise ValueError("boom")

        state.on_change(bad_callback)
        state["k"] = 1
        await state.flush_pending_async()

        error_records = [r for r in wijjit_caplog.records if r.levelno >= logging.ERROR]
        assert any("bad_callback" in r.getMessage() for r in error_records)

    @pytest.mark.asyncio
    async def test_worker_thread_set_schedules_and_completes(self):
        """A state mutation from a worker thread still gets its async
        callback tracked in _pending_tasks and completed by flush."""
        state = State({"a": 0})
        invocations = []

        async def record(key, old, new):
            invocations.append((key, old, new))

        state.on_change(record)

        # First set on the loop thread, to capture state._loop.
        state["a"] = 1
        await state.flush_pending_async()
        assert len(invocations) == 1

        # Now set from a worker thread.
        t = threading.Thread(target=lambda: state.__setitem__("a", 2))
        t.start()
        t.join(timeout=5)
        assert not t.is_alive()

        await state.flush_pending_async()

        assert len(invocations) == 2
        assert invocations[1] == ("a", 1, 2)
        assert state._pending_tasks == set()

    @pytest.mark.asyncio
    async def test_worker_thread_callback_exception_reported(self):
        """An async callback raised from a worker-thread-scheduled task still
        reaches the error hook."""
        state = State({"a": 0})
        calls = []
        state._error_hook = lambda msg, exc: calls.append((msg, exc))

        async def bad_callback(key, old, new):
            raise ValueError("boom")

        state.on_change(bad_callback)

        # Capture state._loop via a loop-thread set first.
        state["a"] = 1
        await state.flush_pending_async()
        calls.clear()

        t = threading.Thread(target=lambda: state.__setitem__("a", 2))
        t.start()
        t.join(timeout=5)
        assert not t.is_alive()

        await state.flush_pending_async()

        assert len(calls) == 1
        message, exc = calls[0]
        assert "bad_callback" in message
        assert isinstance(exc, ValueError)

    @pytest.mark.asyncio
    async def test_flush_pending_async_waits_for_thread_scheduled_work(self):
        """flush_pending_async waits even for worker-thread-scheduled async
        callbacks that don't complete on the first event-loop tick."""
        state = State({"a": 0})
        completed = []

        async def slow_callback(key, old, new):
            await asyncio.sleep(0.05)
            completed.append(new)

        state.on_change(slow_callback)

        # Capture state._loop via a loop-thread set first.
        state["a"] = 1
        await state.flush_pending_async()
        completed.clear()

        t = threading.Thread(target=lambda: state.__setitem__("a", 2))
        t.start()
        t.join(timeout=5)
        assert not t.is_alive()

        await state.flush_pending_async()

        assert completed == [2]
