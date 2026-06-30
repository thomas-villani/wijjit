"""Tests for AutocompletePopup element."""

import pytest

from wijjit.autocomplete.popup import AutocompletePopup
from wijjit.autocomplete.state import AutocompleteState
from wijjit.terminal.input import Keys


def make_popup(
    suggestions: list[str] | None = None, max_visible: int = 10
) -> tuple[AutocompleteState, AutocompletePopup]:
    """Helper to create a popup with state."""
    state = AutocompleteState()
    if suggestions:
        state.suggestions = suggestions
    popup = AutocompletePopup(state, max_visible=max_visible)
    return state, popup


class TestAutocompletePopupInit:
    """Tests for AutocompletePopup initialization."""

    def test_init_with_suggestions(self):
        """Test initialization with a list of suggestions."""
        state, popup = make_popup(["apple", "banana", "cherry"])
        assert popup.suggestions == ["apple", "banana", "cherry"]
        assert popup.highlighted_index == 0
        assert popup.max_visible == 10

    def test_init_empty(self):
        """Test initialization with no suggestions."""
        state, popup = make_popup()
        assert popup.suggestions == []
        assert popup.highlighted_index == 0

    def test_init_with_custom_max_visible(self):
        """Test initialization with custom max_visible."""
        state, popup = make_popup(["a", "b", "c"], max_visible=5)
        assert popup.max_visible == 5

    def test_init_with_highlighted_index(self):
        """Test initialization with custom highlighted index in state."""
        state = AutocompleteState()
        state.suggestions = ["a", "b", "c"]
        state.highlighted_index = 2
        popup = AutocompletePopup(state)
        assert popup.highlighted_index == 2

    def test_not_focusable(self):
        """Test that popup is not focusable (focus stays on input)."""
        state, popup = make_popup(["a", "b", "c"])
        assert popup.focusable is False

    def test_state_reference(self):
        """Test that popup references state, not copies it."""
        state, popup = make_popup(["a", "b", "c"])
        # Changing state should reflect in popup
        state.highlighted_index = 2
        assert popup.highlighted_index == 2
        # Changing via popup should reflect in state
        popup.highlighted_index = 1
        assert state.highlighted_index == 1


class TestAutocompletePopupIntrinsicSize:
    """Tests for intrinsic size calculation."""

    def test_size_empty_suggestions(self):
        """Test size with no suggestions."""
        state, popup = make_popup([])
        width, height = popup.get_intrinsic_size()
        assert width == 20  # Minimum width
        assert height == 3  # Minimum height with border

    def test_size_based_on_content(self):
        """Test size based on suggestion content."""
        state, popup = make_popup(["apple", "banana", "cherry"])
        width, height = popup.get_intrinsic_size()
        # Width: longest word (6 for "banana") + 4 padding/border
        assert width == 10
        # Height: 3 items + 2 border
        assert height == 5

    def test_size_capped_at_max_visible(self):
        """Test height is capped at max_visible."""
        suggestions = [f"item{i}" for i in range(20)]
        state, popup = make_popup(suggestions, max_visible=10)
        width, height = popup.get_intrinsic_size()
        # Height: max_visible (10) + 2 border
        assert height == 12

    def test_size_capped_at_max_width(self):
        """Test width is capped at 50."""
        state, popup = make_popup(["x" * 100])  # Very long suggestion
        width, height = popup.get_intrinsic_size()
        assert width == 50  # Capped

    def test_size_ignores_ansi_codes(self):
        """Test that ANSI codes are not counted in width calculation."""
        # ANSI codes for red text: \x1b[31m ... \x1b[0m
        # Visible text is "apple" (5 chars), but with ANSI it's much longer
        ansi_suggestion = "\x1b[31mapple\x1b[0m"
        plain_suggestion = "apple"

        # Both should calculate the same width
        state_ansi, popup_ansi = make_popup([ansi_suggestion])
        state_plain, popup_plain = make_popup([plain_suggestion])

        width_ansi, _ = popup_ansi.get_intrinsic_size()
        width_plain, _ = popup_plain.get_intrinsic_size()

        # Width should be based on visible length (5) + 4 = 9
        assert width_ansi == width_plain == 9

    def test_size_with_multiple_ansi_suggestions(self):
        """Test width calculation with multiple ANSI-styled suggestions."""
        # Various ANSI styled suggestions
        suggestions = [
            "\x1b[32mshort\x1b[0m",  # green "short" (5 chars visible)
            "\x1b[1;34mlongerword\x1b[0m",  # bold blue "longerword" (10 chars visible)
            "\x1b[4mmedium\x1b[0m",  # underlined "medium" (6 chars visible)
        ]
        state, popup = make_popup(suggestions)
        width, height = popup.get_intrinsic_size()

        # Width should be based on longest visible: "longerword" (10) + 4 = 14
        assert width == 14


class TestAutocompletePopupNavigation:
    """Tests for highlight navigation."""

    def test_move_highlight_down(self):
        """Test moving highlight down."""
        state, popup = make_popup(["a", "b", "c"])
        assert popup.highlighted_index == 0
        popup.move_highlight(1)
        assert popup.highlighted_index == 1
        popup.move_highlight(1)
        assert popup.highlighted_index == 2

    def test_move_highlight_up(self):
        """Test moving highlight up."""
        state, popup = make_popup(["a", "b", "c"])
        state.highlighted_index = 2
        popup.move_highlight(-1)
        assert popup.highlighted_index == 1
        popup.move_highlight(-1)
        assert popup.highlighted_index == 0

    def test_move_highlight_clamp_bottom(self):
        """Test highlight doesn't go past end."""
        state, popup = make_popup(["a", "b", "c"])
        popup.move_highlight(10)  # Try to move way past end
        assert popup.highlighted_index == 2  # Clamped to last

    def test_move_highlight_clamp_top(self):
        """Test highlight doesn't go past start."""
        state, popup = make_popup(["a", "b", "c"])
        popup.move_highlight(-10)  # Try to move way past start
        assert popup.highlighted_index == 0  # Clamped to first

    def test_move_highlight_empty(self):
        """Test move highlight with no suggestions."""
        state, popup = make_popup([])
        popup.move_highlight(1)  # Should not crash
        assert popup.highlighted_index == 0


class TestAutocompletePopupSelectedSuggestion:
    """Tests for selected_suggestion property."""

    def test_selected_suggestion_first(self):
        """Test getting first suggestion."""
        state, popup = make_popup(["apple", "banana", "cherry"])
        assert popup.selected_suggestion == "apple"

    def test_selected_suggestion_after_move(self):
        """Test getting suggestion after moving highlight."""
        state, popup = make_popup(["apple", "banana", "cherry"])
        popup.move_highlight(1)
        assert popup.selected_suggestion == "banana"

    def test_selected_suggestion_empty(self):
        """Test selected_suggestion with no suggestions."""
        state, popup = make_popup([])
        assert popup.selected_suggestion is None


class TestAutocompletePopupSyncFromState:
    """Tests for sync_from_state method (replaces update_suggestions)."""

    def test_sync_from_state(self):
        """Test syncing popup from updated state."""
        state, popup = make_popup(["a", "b", "c"])
        popup.move_highlight(2)
        assert popup.highlighted_index == 2

        # Update state directly
        state.suggestions = ["x", "y"]
        state.highlighted_index = 0
        popup.sync_from_state()

        assert popup.suggestions == ["x", "y"]
        assert popup.highlighted_index == 0

    def test_sync_from_state_empty(self):
        """Test syncing to empty suggestions."""
        state, popup = make_popup(["a", "b", "c"])
        state.suggestions = []
        state.highlighted_index = 0
        popup.sync_from_state()
        assert popup.suggestions == []
        assert popup.highlighted_index == 0


class TestAutocompletePopupKeyHandling:
    """Tests for keyboard navigation."""

    def test_handle_key_down(self):
        """Test Down key handling."""
        state, popup = make_popup(["a", "b", "c"])
        assert popup.handle_key(Keys.DOWN) is True
        assert popup.highlighted_index == 1

    def test_handle_key_up(self):
        """Test Up key handling."""
        state, popup = make_popup(["a", "b", "c"])
        state.highlighted_index = 2
        assert popup.handle_key(Keys.UP) is True
        assert popup.highlighted_index == 1

    def test_handle_key_page_down(self):
        """Test PageDown key handling."""
        suggestions = [f"item{i}" for i in range(20)]
        state, popup = make_popup(suggestions, max_visible=5)
        assert popup.handle_key(Keys.PAGE_DOWN) is True
        assert popup.highlighted_index == 5

    def test_handle_key_page_up(self):
        """Test PageUp key handling."""
        suggestions = [f"item{i}" for i in range(20)]
        state, popup = make_popup(suggestions, max_visible=5)
        state.highlighted_index = 10
        assert popup.handle_key(Keys.PAGE_UP) is True
        assert popup.highlighted_index == 5

    def test_handle_key_home(self):
        """Test Home key handling."""
        state, popup = make_popup(["a", "b", "c"])
        state.highlighted_index = 2
        assert popup.handle_key(Keys.HOME) is True
        assert popup.highlighted_index == 0

    def test_handle_key_end(self):
        """Test End key handling."""
        state, popup = make_popup(["a", "b", "c"])
        assert popup.handle_key(Keys.END) is True
        assert popup.highlighted_index == 2

    def test_handle_key_unhandled(self):
        """Test unhandled key returns False."""
        state, popup = make_popup(["a", "b", "c"])
        assert popup.handle_key(Keys.TAB) is False
        assert popup.handle_key(Keys.ENTER) is False
        assert popup.handle_key(Keys.ESCAPE) is False

    def test_handle_key_empty_suggestions(self):
        """Test key handling with empty suggestions."""
        state, popup = make_popup([])
        assert popup.handle_key(Keys.DOWN) is False
        assert popup.handle_key(Keys.UP) is False


class TestAutocompletePopupMouseHandling:
    """Tests for mouse event handling."""

    @pytest.mark.asyncio
    async def test_handle_mouse_click_on_item(self):
        """Test clicking on a suggestion."""
        from wijjit.layout.bounds import Bounds
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        state, popup = make_popup(["apple", "banana", "cherry"])
        popup.bounds = Bounds(x=10, y=5, width=20, height=5)

        # Click on second item (y=7 is row 1 inside popup after border)
        event = MouseEvent(
            x=15,
            y=7,  # Inside popup, on second item
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )
        result = await popup.handle_mouse(event)
        assert result is True
        assert popup.highlighted_index == 1

    @pytest.mark.asyncio
    async def test_handle_mouse_click_invokes_on_select(self):
        """Clicking a suggestion fires the on_select callback.

        Regression: previously the click only moved the highlight and returned
        True; nothing committed the suggestion to the owning input, so
        mouse-selection silently did nothing.
        """
        from wijjit.layout.bounds import Bounds
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        state, popup = make_popup(["apple", "banana", "cherry"])
        popup.bounds = Bounds(x=10, y=5, width=20, height=5)

        calls: list[int] = []
        popup.on_select = lambda: calls.append(popup.highlighted_index)

        event = MouseEvent(
            x=15,
            y=7,  # second item
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )
        result = await popup.handle_mouse(event)
        assert result is True
        # Callback fired exactly once, after the highlight moved to the clicked row.
        assert calls == [1]

    @pytest.mark.asyncio
    async def test_handle_mouse_click_outside(self):
        """Test clicking outside popup returns False."""
        from wijjit.layout.bounds import Bounds
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        state, popup = make_popup(["apple", "banana", "cherry"])
        popup.bounds = Bounds(x=10, y=5, width=20, height=5)

        event = MouseEvent(
            x=5,
            y=5,  # Outside popup
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )
        result = await popup.handle_mouse(event)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_mouse_scroll_down(self):
        """Test scroll down event."""
        from wijjit.layout.bounds import Bounds
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        state, popup = make_popup(["a", "b", "c"])
        popup.bounds = Bounds(x=10, y=5, width=20, height=5)

        event = MouseEvent(
            x=15,
            y=7,
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_DOWN,
        )
        result = await popup.handle_mouse(event)
        assert result is True
        assert popup.highlighted_index == 1

    @pytest.mark.asyncio
    async def test_handle_mouse_scroll_up(self):
        """Test scroll up event."""
        from wijjit.layout.bounds import Bounds
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        state, popup = make_popup(["a", "b", "c"])
        state.highlighted_index = 2
        popup.bounds = Bounds(x=10, y=5, width=20, height=5)

        event = MouseEvent(
            x=15,
            y=7,
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_UP,
        )
        result = await popup.handle_mouse(event)
        assert result is True
        assert popup.highlighted_index == 1


class TestAutocompletePopupProperties:
    """Tests for convenience properties."""

    def test_has_suggestions_true(self):
        """Test has_suggestions with suggestions."""
        state, popup = make_popup(["a", "b", "c"])
        assert popup.has_suggestions is True

    def test_has_suggestions_false(self):
        """Test has_suggestions with no suggestions."""
        state, popup = make_popup([])
        assert popup.has_suggestions is False

    def test_suggestion_count(self):
        """Test suggestion_count property."""
        state, popup = make_popup(["a", "b", "c"])
        assert popup.suggestion_count == 3

    def test_suggestion_count_empty(self):
        """Test suggestion_count with no suggestions."""
        state, popup = make_popup([])
        assert popup.suggestion_count == 0
