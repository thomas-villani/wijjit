"""Tests for AutocompleteMixin positioning logic.

Tests the _position_popup() method which handles off-screen positioning:
- Flipping above input when too close to bottom edge
- Shifting left when too close to right edge
- Clamping to screen boundaries
"""

from unittest.mock import patch

from wijjit.autocomplete import WordCompleter
from wijjit.elements.input.text import TextInput
from wijjit.layout.bounds import Bounds


def make_terminal_size(columns: int, lines: int):
    """Create a mock terminal size object."""
    from collections import namedtuple

    TerminalSize = namedtuple("terminal_size", ["columns", "lines"])
    return TerminalSize(columns, lines)


class TestPopupPositioningDefault:
    """Test default popup positioning (below input)."""

    def test_popup_below_input(self):
        """Popup should appear below input by default."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = make_terminal_size(80, 24)

            completer = WordCompleter(["apple", "apricot", "avocado"])
            elem = TextInput(id="test", value="a", completer=completer)
            elem.bounds = Bounds(x=5, y=5, width=30, height=1)
            elem.cursor_pos = 1

            # Trigger autocomplete to create popup
            elem._trigger_autocomplete()

            assert elem._autocomplete_popup is not None
            popup_bounds = elem._autocomplete_popup.bounds

            # Popup should be below the input
            assert popup_bounds.y == elem.bounds.y + elem.bounds.height

    def test_popup_aligned_with_word_start(self):
        """Popup x position should align with word start."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = make_terminal_size(80, 24)

            completer = WordCompleter(["apple", "apricot", "avocado"])
            elem = TextInput(id="test", value="hello a", completer=completer)
            elem.bounds = Bounds(x=5, y=5, width=30, height=1)
            elem.cursor_pos = 7  # After "hello a"

            elem._trigger_autocomplete()

            popup_bounds = elem._autocomplete_popup.bounds
            # x = bounds.x + word_start + 2 (offset for decoration)
            # word_start is 6 ("hello " = 6 chars before "a")
            expected_x = elem.bounds.x + min(6 + 2, elem.bounds.width - 1)
            assert popup_bounds.x == expected_x


class TestPopupPositioningBottomEdge:
    """Test popup positioning when input is near bottom edge."""

    def test_popup_flips_above_when_near_bottom(self):
        """Popup should flip above input when too close to bottom edge."""
        with patch("shutil.get_terminal_size") as mock_size:
            # Small terminal height
            mock_size.return_value = make_terminal_size(80, 10)

            completer = WordCompleter(["apple", "apricot", "avocado"])
            elem = TextInput(id="test", value="a", completer=completer)
            # Input at bottom of screen (y=8 with height=1, so ends at y=9)
            elem.bounds = Bounds(x=5, y=8, width=30, height=1)
            elem.cursor_pos = 1

            elem._trigger_autocomplete()

            popup_bounds = elem._autocomplete_popup.bounds
            popup_height = popup_bounds.height

            # Popup should be above the input
            # y = input.y - popup_height
            assert popup_bounds.y == elem.bounds.y - popup_height

    def test_popup_clamps_to_top_when_no_room(self):
        """Popup should clamp to y=0 when no room above or below."""
        with patch("shutil.get_terminal_size") as mock_size:
            # Very small terminal
            mock_size.return_value = make_terminal_size(80, 5)

            completer = WordCompleter(["apple", "apricot", "avocado"])
            elem = TextInput(id="test", value="a", completer=completer)
            # Input near top, popup won't fit above either
            elem.bounds = Bounds(x=5, y=1, width=30, height=1)
            elem.cursor_pos = 1

            elem._trigger_autocomplete()

            popup_bounds = elem._autocomplete_popup.bounds

            # If flipping above would result in negative y, clamp to 0
            assert popup_bounds.y >= 0


class TestPopupPositioningRightEdge:
    """Test popup positioning when input is near right edge."""

    def test_popup_shifts_left_when_near_right_edge(self):
        """Popup should shift left when too close to right edge."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = make_terminal_size(40, 24)

            # Use long suggestions to make popup wider
            completer = WordCompleter(
                ["verylongsuggestion", "anotherlongone", "thirdlongitem"]
            )
            elem = TextInput(id="test", value="v", completer=completer)
            # Input near right edge
            elem.bounds = Bounds(x=30, y=5, width=10, height=1)
            elem.cursor_pos = 1

            elem._trigger_autocomplete()

            popup_bounds = elem._autocomplete_popup.bounds

            # Popup should not extend past right edge
            assert popup_bounds.x + popup_bounds.width <= 40

    def test_popup_clamps_to_left_edge(self):
        """Popup x position should never go negative."""
        with patch("shutil.get_terminal_size") as mock_size:
            # Very narrow terminal
            mock_size.return_value = make_terminal_size(20, 24)

            completer = WordCompleter(
                ["verylongsuggestion", "anotherlongone", "thirdlongitem"]
            )
            elem = TextInput(id="test", value="v", completer=completer)
            elem.bounds = Bounds(x=0, y=5, width=10, height=1)
            elem.cursor_pos = 1

            elem._trigger_autocomplete()

            popup_bounds = elem._autocomplete_popup.bounds

            # x should never be negative
            assert popup_bounds.x >= 0


class TestPopupPositioningCornerCases:
    """Test popup positioning in corner cases."""

    def test_popup_near_bottom_right_corner(self):
        """Popup should handle being near both bottom and right edges."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = make_terminal_size(40, 10)

            completer = WordCompleter(
                ["verylongsuggestion", "anotherlongone", "thirdlongitem"]
            )
            elem = TextInput(id="test", value="v", completer=completer)
            # Input in bottom-right corner
            elem.bounds = Bounds(x=30, y=8, width=10, height=1)
            elem.cursor_pos = 1

            elem._trigger_autocomplete()

            popup_bounds = elem._autocomplete_popup.bounds

            # Popup should flip above and shift left
            assert popup_bounds.y < elem.bounds.y  # Above input
            assert popup_bounds.x + popup_bounds.width <= 40  # Within right edge

    def test_no_bounds_does_not_crash(self):
        """_position_popup should handle missing bounds gracefully."""
        completer = WordCompleter(["apple", "banana"])
        elem = TextInput(id="test", value="a", completer=completer)
        elem.bounds = None  # No bounds set
        elem.cursor_pos = 1

        # Should not raise an exception
        elem._trigger_autocomplete()

        # Popup may or may not be created, but no crash
        # (popup positioning is skipped when bounds is None)

    def test_popup_position_with_empty_suggestions(self):
        """Positioning should handle when popup has no suggestions."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = make_terminal_size(80, 24)

            # Completer with no matching words
            completer = WordCompleter(["apple", "banana"])
            elem = TextInput(id="test", value="xyz", completer=completer)
            elem.bounds = Bounds(x=5, y=5, width=30, height=1)
            elem.cursor_pos = 3

            elem._trigger_autocomplete()

            # With no suggestions, popup should not be created
            assert elem._autocomplete_popup is None
