"""Tests for autocomplete resolver."""

from unittest.mock import MagicMock

from wijjit.autocomplete.completer import (
    CallbackCompleter,
    StateCompleter,
    WordCompleter,
)
from wijjit.autocomplete.resolver import resolve_autocomplete


class MockApp:
    """Mock Wijjit app for testing."""

    def __init__(self):
        self.completers = {}
        self.state = MagicMock()


class TestResolveAutocompleteDisabled:
    """Tests for disabled autocomplete."""

    def test_none_returns_none(self):
        """Test None value returns None."""
        app = MockApp()
        result = resolve_autocomplete(None, "test", app)
        assert result is None

    def test_false_returns_none(self):
        """Test False value returns None."""
        app = MockApp()
        result = resolve_autocomplete(False, "test", app)
        assert result is None


class TestResolveAutocompleteCompleterInstance:
    """Tests for Completer instance input."""

    def test_word_completer_passthrough(self):
        """Test WordCompleter is passed through unchanged."""
        app = MockApp()
        completer = WordCompleter(["a", "b", "c"])
        result = resolve_autocomplete(completer, "test", app)
        assert result is completer

    def test_callback_completer_passthrough(self):
        """Test CallbackCompleter is passed through unchanged."""
        app = MockApp()
        completer = CallbackCompleter(lambda p, c: [])
        result = resolve_autocomplete(completer, "test", app)
        assert result is completer

    def test_state_completer_binds_app(self):
        """Test StateCompleter gets app bound."""
        app = MockApp()
        completer = StateCompleter("key")
        result = resolve_autocomplete(completer, "test", app)
        assert result is completer
        assert completer._app is app


class TestResolveAutocompleteList:
    """Tests for list input."""

    def test_list_creates_word_completer(self):
        """Test list creates WordCompleter."""
        app = MockApp()
        result = resolve_autocomplete(["apple", "banana"], "test", app)
        assert isinstance(result, WordCompleter)
        assert result.words == ["apple", "banana"]

    def test_tuple_creates_word_completer(self):
        """Test tuple creates WordCompleter."""
        app = MockApp()
        result = resolve_autocomplete(("apple", "banana"), "test", app)
        assert isinstance(result, WordCompleter)
        assert result.words == ["apple", "banana"]

    def test_empty_list_returns_none(self):
        """Test empty list returns None."""
        app = MockApp()
        result = resolve_autocomplete([], "test", app)
        assert result is None

    def test_list_filters_non_strings(self):
        """Test non-string items are filtered out."""
        app = MockApp()
        result = resolve_autocomplete(["apple", 123, "banana", None], "test", app)
        assert isinstance(result, WordCompleter)
        assert result.words == ["apple", "banana"]

    def test_list_all_non_strings_returns_none(self):
        """Test list with no strings returns None."""
        app = MockApp()
        result = resolve_autocomplete([1, 2, 3], "test", app)
        assert result is None


class TestResolveAutocompleteStateReference:
    """Tests for state.key reference."""

    def test_state_reference_creates_state_completer(self):
        """Test state.key creates StateCompleter."""
        app = MockApp()
        result = resolve_autocomplete("state.my_key", "test", app)
        assert isinstance(result, StateCompleter)
        assert result.state_key == "my_key"
        assert result._app is app

    def test_state_reference_with_dots(self):
        """Test state.nested.key creates StateCompleter with full key."""
        app = MockApp()
        # Note: current implementation takes everything after "state."
        result = resolve_autocomplete("state.nested.key", "test", app)
        assert isinstance(result, StateCompleter)
        assert result.state_key == "nested.key"


class TestResolveAutocompleteNamedCompleter:
    """Tests for named completer lookup."""

    def test_named_completer_lookup(self):
        """Test string looks up in app.completers."""
        app = MockApp()
        completer = WordCompleter(["x", "y", "z"])
        app.completers["my_completer"] = completer
        result = resolve_autocomplete("my_completer", "test", app)
        assert result is completer

    def test_named_completer_not_found_returns_none(self):
        """Test unknown name returns None with warning."""
        app = MockApp()
        result = resolve_autocomplete("unknown", "test", app)
        assert result is None

    def test_named_state_completer_binds_app(self):
        """Test named StateCompleter gets app bound."""
        app = MockApp()
        completer = StateCompleter("key")
        app.completers["my_state"] = completer
        result = resolve_autocomplete("my_state", "test", app)
        assert result is completer
        assert completer._app is app


class TestResolveAutocompleteAutoWire:
    """Tests for auto-wire by element ID."""

    def test_true_with_hash_prefix(self):
        """Test True looks up #element_id."""
        app = MockApp()
        completer = WordCompleter(["a"])
        app.completers["#username"] = completer
        result = resolve_autocomplete(True, "username", app)
        assert result is completer

    def test_true_without_hash_prefix(self):
        """Test True falls back to element_id without hash."""
        app = MockApp()
        completer = WordCompleter(["a"])
        app.completers["username"] = completer
        result = resolve_autocomplete(True, "username", app)
        assert result is completer

    def test_true_prefers_hash_prefix(self):
        """Test True prefers #element_id over element_id."""
        app = MockApp()
        completer1 = WordCompleter(["hash"])
        completer2 = WordCompleter(["no_hash"])
        app.completers["#username"] = completer1
        app.completers["username"] = completer2
        result = resolve_autocomplete(True, "username", app)
        assert result is completer1  # Prefers #username

    def test_true_no_element_id_returns_none(self):
        """Test True with no element_id returns None."""
        app = MockApp()
        result = resolve_autocomplete(True, None, app)
        assert result is None

    def test_true_completer_not_found_returns_none(self):
        """Test True with unknown element returns None."""
        app = MockApp()
        result = resolve_autocomplete(True, "unknown", app)
        assert result is None


class TestResolveAutocompleteInvalidInput:
    """Tests for invalid input types."""

    def test_int_returns_none(self):
        """Test integer returns None."""
        app = MockApp()
        result = resolve_autocomplete(123, "test", app)
        assert result is None

    def test_dict_returns_none(self):
        """Test dict returns None."""
        app = MockApp()
        result = resolve_autocomplete({"key": "value"}, "test", app)
        assert result is None

    def test_object_returns_none(self):
        """Test arbitrary object returns None."""
        app = MockApp()
        result = resolve_autocomplete(object(), "test", app)
        assert result is None
