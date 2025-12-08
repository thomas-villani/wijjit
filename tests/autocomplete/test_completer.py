"""Tests for completer classes."""

from unittest.mock import Mock

import pytest

from wijjit.autocomplete.completer import (
    AsyncCompleter,
    CallbackCompleter,
    CompleterConfig,
    StateCompleter,
    WordCompleter,
)


class TestCompleterConfig:
    """Tests for CompleterConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CompleterConfig()
        assert config.trigger == "manual"
        assert config.min_chars == 1
        assert config.trigger_key == "ctrl+/"
        assert config.case_sensitive is False
        assert config.match_anywhere is False
        assert config.max_suggestions == 10
        assert config.select_on_tab is True
        assert config.close_on_blur is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CompleterConfig(
            trigger="auto",
            min_chars=3,
            trigger_key="ctrl+j",
            case_sensitive=True,
            match_anywhere=True,
            max_suggestions=5,
            select_on_tab=False,
            close_on_blur=False,
        )
        assert config.trigger == "auto"
        assert config.min_chars == 3
        assert config.trigger_key == "ctrl+j"
        assert config.case_sensitive is True
        assert config.match_anywhere is True
        assert config.max_suggestions == 5
        assert config.select_on_tab is False
        assert config.close_on_blur is False

    def test_invalid_trigger(self):
        """Test that invalid trigger raises ValueError."""
        with pytest.raises(ValueError, match="trigger must be 'auto' or 'manual'"):
            CompleterConfig(trigger="invalid")

    def test_invalid_min_chars(self):
        """Test that negative min_chars raises ValueError."""
        with pytest.raises(ValueError, match="min_chars must be >= 0"):
            CompleterConfig(min_chars=-1)

    def test_invalid_max_suggestions(self):
        """Test that max_suggestions < 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_suggestions must be >= 1"):
            CompleterConfig(max_suggestions=0)


class TestWordCompleter:
    """Tests for WordCompleter class."""

    def test_basic_prefix_matching(self):
        """Test basic prefix matching."""
        completer = WordCompleter(["apple", "apricot", "banana", "blueberry"])
        assert completer.get_suggestions("ap") == ["apple", "apricot"]
        assert completer.get_suggestions("b") == ["banana", "blueberry"]
        assert completer.get_suggestions("c") == []

    def test_empty_prefix_returns_empty(self):
        """Test empty prefix returns empty list."""
        completer = WordCompleter(["apple", "banana"])
        assert completer.get_suggestions("") == []

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching (default)."""
        completer = WordCompleter(["Apple", "Apricot", "BANANA"])
        assert completer.get_suggestions("ap") == ["Apple", "Apricot"]
        assert completer.get_suggestions("AP") == ["Apple", "Apricot"]
        assert completer.get_suggestions("ban") == ["BANANA"]

    def test_case_sensitive_matching(self):
        """Test case-sensitive matching."""
        completer = WordCompleter(["Apple", "apricot", "BANANA"], case_sensitive=True)
        assert completer.get_suggestions("ap") == ["apricot"]
        assert completer.get_suggestions("Ap") == ["Apple"]
        assert completer.get_suggestions("BAN") == ["BANANA"]

    def test_match_anywhere(self):
        """Test substring matching anywhere in word."""
        completer = WordCompleter(
            ["pineapple", "apple", "grapple"], match_anywhere=True
        )
        assert completer.get_suggestions("apple") == ["pineapple", "apple", "grapple"]
        assert completer.get_suggestions("grape") == []  # No substring match

    def test_max_suggestions(self):
        """Test max_suggestions limit."""
        words = [f"word{i}" for i in range(20)]
        completer = WordCompleter(words, max_suggestions=5)
        suggestions = completer.get_suggestions("word")
        assert len(suggestions) == 5

    def test_context_ignored(self):
        """Test that context parameter is accepted but ignored."""
        completer = WordCompleter(["test"])
        result = completer.get_suggestions("t", context={"foo": "bar"})
        assert result == ["test"]

    def test_config_passed_through(self):
        """Test that config options are passed to CompleterConfig."""
        completer = WordCompleter(["test"], trigger="auto", min_chars=3)
        assert completer.config.trigger == "auto"
        assert completer.config.min_chars == 3


class TestCallbackCompleter:
    """Tests for CallbackCompleter class."""

    def test_basic_callback(self):
        """Test basic callback function."""

        def my_callback(prefix, context):
            return [f"{prefix}1", f"{prefix}2"]

        completer = CallbackCompleter(my_callback)
        assert completer.get_suggestions("test") == ["test1", "test2"]

    def test_callback_receives_context(self):
        """Test that callback receives context."""
        received_context = {}

        def my_callback(prefix, context):
            received_context.update(context or {})
            return []

        completer = CallbackCompleter(my_callback)
        completer.get_suggestions("test", context={"key": "value"})
        assert received_context == {"key": "value"}

    def test_max_suggestions_limit(self):
        """Test max_suggestions limit on callback results."""

        def my_callback(prefix, context):
            return [f"{prefix}{i}" for i in range(20)]

        completer = CallbackCompleter(my_callback, max_suggestions=5)
        suggestions = completer.get_suggestions("x")
        assert len(suggestions) == 5

    def test_callback_returns_empty(self):
        """Test callback returning empty list."""

        def my_callback(prefix, context):
            return []

        completer = CallbackCompleter(my_callback)
        assert completer.get_suggestions("test") == []


class TestAsyncCompleter:
    """Tests for AsyncCompleter class."""

    def test_sync_get_suggestions_raises(self):
        """Test that sync get_suggestions raises RuntimeError."""

        async def my_callback(prefix, context):
            return [prefix]

        completer = AsyncCompleter(my_callback)
        with pytest.raises(RuntimeError, match="requires async context"):
            completer.get_suggestions("test")

    @pytest.mark.asyncio
    async def test_async_get_suggestions(self):
        """Test async get_suggestions_async works."""

        async def my_callback(prefix, context):
            return [f"{prefix}1", f"{prefix}2"]

        completer = AsyncCompleter(my_callback)
        result = await completer.get_suggestions_async("test")
        assert result == ["test1", "test2"]

    @pytest.mark.asyncio
    async def test_async_max_suggestions(self):
        """Test max_suggestions limit on async results."""

        async def my_callback(prefix, context):
            return [f"{prefix}{i}" for i in range(20)]

        completer = AsyncCompleter(my_callback, max_suggestions=5)
        result = await completer.get_suggestions_async("x")
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_async_receives_context(self):
        """Test that async callback receives context."""
        received_context = {}

        async def my_callback(prefix, context):
            received_context.update(context or {})
            return []

        completer = AsyncCompleter(my_callback)
        await completer.get_suggestions_async("test", context={"key": "value"})
        assert received_context == {"key": "value"}


class TestStateCompleter:
    """Tests for StateCompleter class."""

    def test_without_bound_app(self):
        """Test that unbound completer returns empty list."""
        completer = StateCompleter("tags")
        assert completer.get_suggestions("test") == []

    def test_with_bound_app(self):
        """Test completer with bound app."""
        # Create a mock app with state
        mock_app = Mock()
        mock_app.state.tags = ["python", "javascript", "rust", "ruby"]

        completer = StateCompleter("tags")
        completer.bind_app(mock_app)

        assert completer.get_suggestions("py") == ["python"]
        assert completer.get_suggestions("r") == ["rust", "ruby"]
        assert completer.get_suggestions("java") == ["javascript"]

    def test_missing_state_key(self):
        """Test completer with missing state key."""
        mock_app = Mock()
        mock_app.state.other = ["value"]

        completer = StateCompleter("nonexistent")
        completer.bind_app(mock_app)

        # getattr returns None for missing attribute
        mock_app.state.nonexistent = None

        assert completer.get_suggestions("test") == []

    def test_non_list_state_value(self):
        """Test completer with non-list state value."""
        mock_app = Mock()
        mock_app.state.tags = "not a list"

        completer = StateCompleter("tags")
        completer.bind_app(mock_app)

        assert completer.get_suggestions("test") == []

    def test_empty_prefix(self):
        """Test empty prefix returns empty list."""
        mock_app = Mock()
        mock_app.state.tags = ["python"]

        completer = StateCompleter("tags")
        completer.bind_app(mock_app)

        assert completer.get_suggestions("") == []

    def test_case_insensitive(self):
        """Test case-insensitive matching (default)."""
        mock_app = Mock()
        mock_app.state.tags = ["Python", "JAVASCRIPT"]

        completer = StateCompleter("tags")
        completer.bind_app(mock_app)

        assert completer.get_suggestions("py") == ["Python"]
        assert completer.get_suggestions("java") == ["JAVASCRIPT"]

    def test_case_sensitive(self):
        """Test case-sensitive matching."""
        mock_app = Mock()
        mock_app.state.tags = ["Python", "python"]

        completer = StateCompleter("tags", case_sensitive=True)
        completer.bind_app(mock_app)

        assert completer.get_suggestions("py") == ["python"]
        assert completer.get_suggestions("Py") == ["Python"]

    def test_match_anywhere(self):
        """Test substring matching anywhere."""
        mock_app = Mock()
        mock_app.state.tags = ["typescript", "javascript", "coffeescript"]

        completer = StateCompleter("tags", match_anywhere=True)
        completer.bind_app(mock_app)

        assert completer.get_suggestions("script") == [
            "typescript",
            "javascript",
            "coffeescript",
        ]

    def test_max_suggestions(self):
        """Test max_suggestions limit."""
        mock_app = Mock()
        mock_app.state.tags = [f"tag{i}" for i in range(20)]

        completer = StateCompleter("tags", max_suggestions=5)
        completer.bind_app(mock_app)

        result = completer.get_suggestions("tag")
        assert len(result) == 5

    def test_skips_non_string_items(self):
        """Test that non-string items in list are skipped."""
        mock_app = Mock()
        mock_app.state.tags = ["valid", 123, None, "also_valid"]

        completer = StateCompleter("tags")
        completer.bind_app(mock_app)

        # Should only match string items
        assert completer.get_suggestions("val") == ["valid"]
        assert completer.get_suggestions("also") == ["also_valid"]


class TestCompleterAsync:
    """Tests for Completer base class async support."""

    @pytest.mark.asyncio
    async def test_word_completer_async(self):
        """Test that WordCompleter async version works."""
        completer = WordCompleter(["apple", "banana"])
        result = await completer.get_suggestions_async("ap")
        assert result == ["apple"]

    @pytest.mark.asyncio
    async def test_callback_completer_async(self):
        """Test that CallbackCompleter async version works."""

        def my_callback(prefix, context):
            return [prefix]

        completer = CallbackCompleter(my_callback)
        result = await completer.get_suggestions_async("test")
        assert result == ["test"]
