"""Integration tests for autocomplete feature.

Tests the integration of autocomplete with TextInput element, template tags,
wiring manager, and the Wijjit application.
"""

import pytest

from wijjit import Wijjit
from wijjit.autocomplete import (
    CallbackCompleter,
    StateCompleter,
    WordCompleter,
)
from wijjit.elements.input.text import TextInput


class TestTextInputAutocomplete:
    """Test TextInput element with autocomplete."""

    def test_textinput_with_completer(self):
        """TextInput should accept completer parameter."""
        completer = WordCompleter(["apple", "banana", "cherry"])
        elem = TextInput(id="test", completer=completer)

        assert elem.completer is completer
        assert elem._autocomplete_state is not None
        assert not elem._autocomplete_state.is_open

    def test_textinput_with_autocomplete_spec(self):
        """TextInput should store autocomplete spec for deferred resolution."""
        elem = TextInput(id="test", autocomplete=["apple", "banana"])

        assert elem._autocomplete_spec == ["apple", "banana"]
        assert elem.completer is None  # Not resolved yet

    def test_textinput_autocomplete_state_initialized(self):
        """TextInput should initialize autocomplete state."""
        elem = TextInput(id="test")

        assert hasattr(elem, "_autocomplete_state")
        assert elem._autocomplete_state.is_open is False
        assert elem._autocomplete_state.suggestions == []


class TestWijjitCompletersRegistry:
    """Test Wijjit.completers registry."""

    def test_completers_dict_exists(self):
        """Wijjit should have completers dict."""
        app = Wijjit()
        assert hasattr(app, "completers")
        assert isinstance(app.completers, dict)
        assert len(app.completers) == 0

    def test_register_completer(self):
        """register_completer should add to completers dict."""
        app = Wijjit()
        completer = WordCompleter(["apple", "banana"])

        app.register_completer("fruits", completer)

        assert "fruits" in app.completers
        assert app.completers["fruits"] is completer

    def test_register_completer_with_hash_prefix(self):
        """register_completer should work with # prefix for ID matching."""
        app = Wijjit()
        completer = WordCompleter(["red", "green", "blue"])

        app.register_completer("#color", completer)

        assert "#color" in app.completers
        assert app.completers["#color"] is completer


class TestAutocompleteWiring:
    """Test autocomplete wiring in ElementWiringManager."""

    def test_wiring_resolves_list_autocomplete(self):
        """Wiring should resolve list autocomplete to WordCompleter."""
        from wijjit.core.state import State
        from wijjit.core.wiring import ElementWiringManager

        app = Wijjit()
        wiring = ElementWiringManager(app)
        state = State({})

        elem = TextInput(id="test", autocomplete=["apple", "banana"])
        wiring._wire_textinput(elem, state)

        assert elem.completer is not None
        assert isinstance(elem.completer, WordCompleter)
        assert elem._autocomplete_spec is None  # Cleared after resolution

    def test_wiring_resolves_named_completer(self):
        """Wiring should resolve named completer from app.completers."""
        from wijjit.core.state import State
        from wijjit.core.wiring import ElementWiringManager

        app = Wijjit()
        completer = WordCompleter(["red", "green", "blue"])
        app.register_completer("colors", completer)

        wiring = ElementWiringManager(app)
        state = State({})

        elem = TextInput(id="test", autocomplete="colors")
        wiring._wire_textinput(elem, state)

        assert elem.completer is completer

    def test_wiring_resolves_autowire_by_id(self):
        """Wiring should resolve autocomplete=True by looking up #element_id."""
        from wijjit.core.state import State
        from wijjit.core.wiring import ElementWiringManager

        app = Wijjit()
        completer = WordCompleter(["python", "javascript"])
        app.register_completer("#lang", completer)

        wiring = ElementWiringManager(app)
        state = State({})

        elem = TextInput(id="lang", autocomplete=True)
        wiring._wire_textinput(elem, state)

        assert elem.completer is completer

    def test_wiring_resolves_state_completer(self):
        """Wiring should resolve state.key to StateCompleter."""
        from wijjit.core.wiring import ElementWiringManager

        app = Wijjit()
        app.state.tags = ["tag1", "tag2", "tag3"]

        wiring = ElementWiringManager(app)
        state = app.state

        elem = TextInput(id="test", autocomplete="state.tags")
        wiring._wire_textinput(elem, state)

        assert elem.completer is not None
        assert isinstance(elem.completer, StateCompleter)

        # Test that it can get suggestions
        suggestions = elem.completer.get_suggestions("tag")
        assert "tag1" in suggestions
        assert "tag2" in suggestions

    def test_wiring_injects_overlay_manager(self):
        """Wiring should inject overlay manager when completer is set."""
        from wijjit.core.state import State
        from wijjit.core.wiring import ElementWiringManager

        app = Wijjit()
        wiring = ElementWiringManager(app)
        state = State({})

        elem = TextInput(id="test", autocomplete=["apple", "banana"])
        wiring._wire_textinput(elem, state)

        assert elem._overlay_manager is app.overlay_manager

    def test_wiring_skips_if_completer_already_set(self):
        """Wiring should not override existing completer."""
        from wijjit.core.state import State
        from wijjit.core.wiring import ElementWiringManager

        app = Wijjit()
        wiring = ElementWiringManager(app)
        state = State({})

        existing_completer = WordCompleter(["existing"])
        elem = TextInput(
            id="test",
            completer=existing_completer,
            autocomplete=["should", "not", "be", "used"],
        )
        wiring._wire_textinput(elem, state)

        assert elem.completer is existing_completer


class TestAutocompleteKeyHandling:
    """Test keyboard handling for autocomplete."""

    def test_ctrl_slash_triggers_autocomplete(self):
        """Ctrl+/ should trigger autocomplete popup."""
        from wijjit.terminal.input import Key, KeyType

        completer = WordCompleter(["apple", "banana", "cherry"])
        elem = TextInput(id="test", value="a", completer=completer)
        elem.cursor_pos = 1

        # Create Ctrl+/ key (name includes "ctrl+" so modifiers will include "ctrl")
        key = Key(name="ctrl+/", key_type=KeyType.CONTROL, char="/")

        # Handle the key
        result = elem.handle_key(key)

        assert result is True
        assert elem._autocomplete_state.is_open is True
        assert len(elem._autocomplete_state.suggestions) > 0

    def test_escape_closes_autocomplete(self):
        """Escape should close autocomplete popup."""
        from wijjit.terminal.input import Keys

        completer = WordCompleter(["apple", "banana"])
        elem = TextInput(id="test", value="a", completer=completer)
        elem.cursor_pos = 1

        # Manually open autocomplete
        elem._trigger_autocomplete()
        assert elem._autocomplete_state.is_open is True

        # Press Escape
        result = elem.handle_key(Keys.ESCAPE)

        assert result is True
        assert elem._autocomplete_state.is_open is False

    def test_enter_applies_suggestion(self):
        """Enter should apply selected suggestion."""
        from wijjit.terminal.input import Keys

        completer = WordCompleter(["apple", "apricot"])
        elem = TextInput(id="test", value="ap", completer=completer)
        elem.cursor_pos = 2

        # Manually trigger autocomplete (simpler than key press)
        elem._trigger_autocomplete()

        assert elem._autocomplete_state.is_open is True
        assert "apple" in elem._autocomplete_state.suggestions

        # Press Enter to select
        elem.handle_key(Keys.ENTER)

        assert elem._autocomplete_state.is_open is False
        assert elem.value == "apple"

    def test_down_arrow_navigates_suggestions(self):
        """Down arrow should move highlight in suggestions."""
        from wijjit.terminal.input import Keys

        completer = WordCompleter(["apple", "apricot", "avocado"])
        elem = TextInput(id="test", value="a", completer=completer)
        elem.cursor_pos = 1

        # Manually trigger autocomplete
        elem._trigger_autocomplete()

        initial_index = elem._autocomplete_state.highlighted_index
        assert initial_index == 0

        # Press Down
        elem.handle_key(Keys.DOWN)

        assert elem._autocomplete_state.highlighted_index == 1

    def test_typing_updates_suggestions(self):
        """Typing should update autocomplete suggestions."""
        from wijjit.terminal.input import Key, KeyType

        completer = WordCompleter(
            ["apple", "apricot", "banana"], trigger="auto", min_chars=1
        )
        elem = TextInput(id="test", value="", completer=completer)
        elem.cursor_pos = 0

        # Type 'a' - should trigger auto-complete
        key = Key(name="a", key_type=KeyType.CHARACTER, char="a")
        elem.handle_key(key)

        # Check suggestions are updated (after edit triggers auto-complete)
        assert elem._autocomplete_state.is_open is True
        assert "apple" in elem._autocomplete_state.suggestions
        assert "apricot" in elem._autocomplete_state.suggestions
        assert "banana" not in elem._autocomplete_state.suggestions


class TestAsyncCompleterErrorHandling:
    """Test error handling in async completers."""

    @pytest.mark.asyncio
    async def test_async_completer_error_closes_popup(self):
        """Async completer errors should close popup gracefully."""
        from wijjit.autocomplete.completer import AsyncCompleter

        async def failing_callback(
            prefix: str, context: dict | None = None
        ) -> list[str]:
            raise RuntimeError("Simulated network error")

        completer = AsyncCompleter(failing_callback)
        elem = TextInput(id="test", value="a", completer=completer)
        elem.cursor_pos = 1

        # Set up state as if autocomplete was triggered
        elem._autocomplete_state.prefix = "a"
        elem._autocomplete_state.is_open = True

        # Call the async fetch method directly (normally called via create_task)
        await elem._fetch_suggestions_async("a")

        # Should gracefully close autocomplete, not crash
        assert elem._autocomplete_state.is_open is False

    @pytest.mark.asyncio
    async def test_async_completer_error_ignored_if_prefix_changed(self):
        """Errors should be ignored if user has typed more."""
        from wijjit.autocomplete.completer import AsyncCompleter

        async def failing_callback(
            prefix: str, context: dict | None = None
        ) -> list[str]:
            raise RuntimeError("Simulated network error")

        completer = AsyncCompleter(failing_callback)
        elem = TextInput(id="test", value="abc", completer=completer)
        elem.cursor_pos = 3

        # Simulate: user typed "a", async fetch started, but user typed more
        elem._autocomplete_state.prefix = "abc"  # User has typed more
        elem._autocomplete_state.is_open = True

        # Call with old prefix "a" (simulating delayed response)
        await elem._fetch_suggestions_async("a")

        # Popup should still be open (error ignored because prefix changed)
        assert elem._autocomplete_state.is_open is True


class TestCallbackCompleterIntegration:
    """Test CallbackCompleter integration."""

    def test_callback_completer_in_wiring(self):
        """CallbackCompleter should work through wiring."""
        from wijjit.core.state import State
        from wijjit.core.wiring import ElementWiringManager

        def get_suggestions(prefix: str, context: dict | None) -> list[str]:
            items = ["item1", "item2", "item3"]
            return [i for i in items if i.startswith(prefix)]

        app = Wijjit()
        completer = CallbackCompleter(get_suggestions)
        app.register_completer("items", completer)

        wiring = ElementWiringManager(app)
        state = State({})

        elem = TextInput(id="test", autocomplete="items")
        wiring._wire_textinput(elem, state)

        assert elem.completer is completer

        # Test getting suggestions
        suggestions = elem.completer.get_suggestions("item")
        assert len(suggestions) == 3
