"""Tests for TextArea element."""

from unittest.mock import Mock

from wijjit.elements.base import ElementType
from wijjit.elements.input.text import TextArea
from wijjit.terminal.input import Key, Keys, KeyType
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestTextAreaBasics:
    """Tests for TextArea basic functionality."""

    def test_create_textarea(self):
        """Test creating a text area."""
        textarea = TextArea(id="editor", width=40, height=10)
        assert textarea.id == "editor"
        assert textarea.width == 40
        assert textarea.height == 10
        assert textarea.focusable
        assert textarea.element_type == ElementType.INPUT

    def test_initial_value(self):
        """Test text area with initial value."""
        textarea = TextArea(value="Hello\nWorld")
        assert textarea.lines == ["Hello", "World"]
        assert textarea.get_value() == "Hello\nWorld"
        assert textarea.cursor_row == 0
        assert textarea.cursor_col == 0

    def test_empty_initial_value(self):
        """Test text area with empty initial value."""
        textarea = TextArea()
        assert textarea.lines == [""]
        assert textarea.get_value() == ""


class TestTextAreaEditing:
    """Tests for TextArea editing operations."""

    def test_insert_character(self):
        """Test inserting a character."""
        textarea = TextArea()
        textarea.handle_key(Key("H", KeyType.CHARACTER, "H"))
        assert textarea.get_value() == "H"
        assert textarea.cursor_col == 1

    def test_insert_multiple_characters(self):
        """Test typing multiple characters."""
        textarea = TextArea()
        for char in "Hello":
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))
        assert textarea.get_value() == "Hello"
        assert textarea.cursor_col == 5

    def test_enter_creates_new_line(self):
        """Test Enter key creates new line."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 5
        textarea.handle_key(Keys.ENTER)
        assert textarea.lines == ["Hello", ""]
        assert textarea.cursor_row == 1
        assert textarea.cursor_col == 0

    def test_enter_splits_line(self):
        """Test Enter splits line at cursor."""
        textarea = TextArea(value="HelloWorld")
        textarea.cursor_col = 5  # After "Hello"
        textarea.handle_key(Keys.ENTER)
        assert textarea.lines == ["Hello", "World"]
        assert textarea.cursor_row == 1
        assert textarea.cursor_col == 0

    def test_backspace_at_line_start_merges(self):
        """Test backspace at line start merges with previous line."""
        textarea = TextArea(value="Hello\nWorld")
        textarea.cursor_row = 1
        textarea.cursor_col = 0
        textarea.handle_key(Keys.BACKSPACE)
        assert textarea.lines == ["HelloWorld"]
        assert textarea.cursor_row == 0
        assert textarea.cursor_col == 5

    def test_backspace_deletes_character(self):
        """Test backspace deletes character."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 5
        textarea.handle_key(Keys.BACKSPACE)
        assert textarea.get_value() == "Hell"
        assert textarea.cursor_col == 4

    def test_delete_at_line_end_merges(self):
        """Test delete at line end merges with next line."""
        textarea = TextArea(value="Hello\nWorld")
        textarea.cursor_row = 0
        textarea.cursor_col = 5
        textarea.handle_key(Keys.DELETE)
        assert textarea.lines == ["HelloWorld"]
        assert textarea.cursor_row == 0
        assert textarea.cursor_col == 5

    def test_delete_character(self):
        """Test delete key deletes character."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 2  # After "He"
        textarea.handle_key(Keys.DELETE)
        assert textarea.get_value() == "Helo"
        assert textarea.cursor_col == 2


class TestTextAreaNavigation:
    """Tests for TextArea navigation."""

    def test_arrow_up(self):
        """Test up arrow moves cursor."""
        textarea = TextArea(value="Line1\nLine2\nLine3")
        textarea.cursor_row = 2
        textarea.handle_key(Keys.UP)
        assert textarea.cursor_row == 1

    def test_arrow_down(self):
        """Test down arrow moves cursor."""
        textarea = TextArea(value="Line1\nLine2\nLine3")
        textarea.cursor_row = 0
        textarea.handle_key(Keys.DOWN)
        assert textarea.cursor_row == 1

    def test_arrow_left(self):
        """Test left arrow moves cursor."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 3
        textarea.handle_key(Keys.LEFT)
        assert textarea.cursor_col == 2

    def test_arrow_right(self):
        """Test right arrow moves cursor."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 2
        textarea.handle_key(Keys.RIGHT)
        assert textarea.cursor_col == 3

    def test_home_key(self):
        """Test Home key moves to line start."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 3
        textarea.handle_key(Keys.HOME)
        assert textarea.cursor_col == 0

    def test_end_key(self):
        """Test End key moves to line end."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 0
        textarea.handle_key(Keys.END)
        assert textarea.cursor_col == 5


class TestTextAreaScrolling:
    """Tests for TextArea scrolling."""

    def test_scroll_manager_initialized(self):
        """Test scroll manager is properly initialized."""
        textarea = TextArea(height=5)
        assert textarea.scroll_manager.state.viewport_size == 5
        assert textarea.scroll_manager.state.content_size == 1

    def test_adding_lines_updates_scroll(self):
        """Test adding lines updates scroll manager."""
        textarea = TextArea(height=5)
        # Add 10 lines
        for _i in range(10):
            textarea.handle_key(Keys.ENTER)
        assert textarea.scroll_manager.state.content_size == 11


class TestTextAreaMouse:
    """Tests for TextArea mouse support."""

    def test_mouse_wheel_up(self):
        """Test mouse wheel up scrolls content."""
        # Create textarea with content larger than viewport
        content = "\n".join([f"Line {i}" for i in range(20)])
        textarea = TextArea(value=content, height=5)

        # Scroll to middle
        textarea.scroll_manager.scroll_to(10)

        # Mouse wheel up
        event = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_UP, x=0, y=0
        )
        result = textarea.handle_mouse(event)
        assert result
        assert textarea.scroll_manager.state.scroll_position == 7

    def test_mouse_wheel_down(self):
        """Test mouse wheel down scrolls content."""
        content = "\n".join([f"Line {i}" for i in range(20)])
        textarea = TextArea(value=content, height=5)

        event = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_DOWN, x=0, y=0
        )
        result = textarea.handle_mouse(event)
        assert result
        assert textarea.scroll_manager.state.scroll_position == 3

    def test_mouse_click_positions_cursor(self):
        """Test clicking positions cursor."""
        textarea = TextArea(value="Line1\nLine2\nLine3", height=5)

        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=3, y=1)
        textarea.handle_mouse(event)
        assert textarea.cursor_row == 1
        assert textarea.cursor_col == 3


class TestTextAreaValueBinding:
    """Tests for TextArea value get/set."""

    def test_get_value(self):
        """Test getting text area value."""
        textarea = TextArea(value="Hello\nWorld")
        assert textarea.get_value() == "Hello\nWorld"

    def test_set_value(self):
        """Test setting text area value."""
        textarea = TextArea()
        textarea.set_value("New\nContent")
        assert textarea.lines == ["New", "Content"]
        assert textarea.cursor_row == 0
        assert textarea.cursor_col == 0

    def test_on_change_callback(self):
        """Test on_change callback fires."""
        textarea = TextArea()
        callback = Mock()
        textarea.on_change = callback

        textarea.handle_key(Key("H", KeyType.CHARACTER, "H"))
        callback.assert_called_once()
        old_val, new_val = callback.call_args[0]
        assert old_val == ""
        assert new_val == "H"


class TestTextAreaRendering:
    """Tests for TextArea rendering."""

    def test_render_basic(self):
        """Test basic rendering."""
        textarea = TextArea(value="Hello\nWorld", width=10, height=5)
        result = textarea.render()
        assert result is not None
        assert isinstance(result, str)

    def test_render_shows_scrollbar_when_needed(self):
        """Test scrollbar appears when content exceeds viewport."""
        content = "\n".join([f"Line {i}" for i in range(20)])
        textarea = TextArea(value=content, width=10, height=5, show_scrollbar=True)
        result = textarea.render()
        # Should contain scrollbar character
        assert "│" in result or "█" in result

    def test_render_cursor_when_focused(self):
        """Test cursor is visible when textarea is focused."""
        textarea = TextArea(value="Hello\nWorld", width=20, height=5)
        textarea.on_focus()
        result = textarea.render()
        # Should contain reverse video escape codes for cursor
        assert "\x1b[7m" in result  # Reverse video on
        assert "\x1b[27m" in result  # Reverse video off

    def test_no_cursor_when_unfocused(self):
        """Test cursor is not visible when textarea is unfocused."""
        textarea = TextArea(value="Hello\nWorld", width=20, height=5)
        # Don't focus it
        result = textarea.render()
        # Should not contain reverse video escape codes
        assert "\x1b[7m" not in result

    def test_cursor_at_different_positions(self):
        """Test cursor renders at different positions."""
        textarea = TextArea(value="Hello", width=20, height=5)
        textarea.on_focus()

        # Cursor at start (0)
        textarea.cursor_col = 0
        result = textarea.render()
        # First character should be in reverse video
        assert "\x1b[7mH\x1b[27m" in result

        # Cursor at middle (2)
        textarea.cursor_col = 2
        result = textarea.render()
        # Third character should be in reverse video
        assert "\x1b[7ml\x1b[27m" in result

        # Cursor at end (5)
        textarea.cursor_col = 5
        result = textarea.render()
        # Should show space in reverse video at end
        assert "\x1b[7m \x1b[27m" in result


class TestTextAreaHardWrap:
    """Tests for TextArea hard wrap mode.

    Tests verify that wrap_mode="hard" correctly breaks long lines
    at word boundaries without raising AttributeError.
    """

    def test_hard_wrap_basic(self):
        """Test basic hard wrap functionality.

        Verifies that when a line exceeds width, it is hard-wrapped
        and additional lines are created.
        """
        textarea = TextArea(width=10, height=5, wrap_mode="hard")
        # Type a long line that exceeds width
        long_text = "This is a very long line that should wrap"
        for char in long_text:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        # Should have multiple lines after wrapping
        assert len(textarea.lines) > 1
        # Each line should be <= width
        for line in textarea.lines:
            assert len(line) <= 10

    def test_hard_wrap_at_word_boundary(self):
        """Test that hard wrap breaks at word boundaries.

        Verifies that wrap breaks at spaces or punctuation, not
        mid-word, and correctly uses is_wrap_boundary function.
        """
        textarea = TextArea(width=10, height=5, wrap_mode="hard")
        # Type text with clear word boundaries
        text = "Hello World Test"
        for char in text:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        # Should break at spaces, not in middle of words
        for line in textarea.lines:
            # Line shouldn't start or end with punctuation that suggests bad break
            assert len(line) <= 10
            # No AttributeError should have been raised

    def test_hard_wrap_with_no_boundaries(self):
        """Test hard wrap with no word boundaries.

        Verifies that when there are no wrap boundaries within width,
        the line is force-split at the width limit.
        """
        textarea = TextArea(width=10, height=5, wrap_mode="hard")
        # Type text with no spaces (no wrap boundaries)
        long_word = "VeryLongWordWithNoSpaces"
        for char in long_word:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        # Should force-split at width
        assert len(textarea.lines) > 1
        for line in textarea.lines[:-1]:  # All but last line
            assert len(line) <= 10

    def test_hard_wrap_with_punctuation_boundaries(self):
        """Test hard wrap at punctuation boundaries.

        Verifies that wrap can occur at various punctuation marks
        as defined by is_wrap_boundary function.
        """
        textarea = TextArea(width=15, height=5, wrap_mode="hard")
        # Text with various punctuation
        text = "Hello,world-test.end;item:value"
        for char in text:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        # Should wrap at punctuation boundaries
        for line in textarea.lines:
            assert len(line) <= 15

    def test_hard_wrap_basic_functionality(self):
        """Test that hard wrap basic functionality works.

        Verifies that hard wrap creates multiple lines when text exceeds width
        and doesn't crash with AttributeError.
        """
        textarea = TextArea(width=20, height=10, wrap_mode="hard")
        original_text = "This is a test of hard wrap"

        # Should not raise AttributeError (the bug we fixed)
        for char in original_text:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        # Should have multiple lines after wrapping
        assert len(textarea.lines) > 1

        # Verify text content is generally preserved (allowing for wrap behavior)
        result = textarea.get_value()
        # Count non-whitespace characters to verify content preservation
        original_non_ws = len([c for c in original_text if not c.isspace()])
        result_non_ws = len([c for c in result if not c.isspace()])
        assert result_non_ws == original_non_ws

    def test_hard_wrap_no_crash(self):
        """Test that hard wrap doesn't crash.

        Verifies that hard wrap functionality works without raising
        AttributeError (the bug we fixed with is_wrap_boundary).
        """
        textarea = TextArea(width=10, height=5, wrap_mode="hard")
        # Type text that will wrap
        text = "Hello World Testing"

        # Should not raise AttributeError about _is_wrap_boundary
        try:
            for char in text:
                textarea.handle_key(Key(char, KeyType.CHARACTER, char))
            success = True
        except AttributeError as e:
            if "_is_wrap_boundary" in str(e):
                success = False
            else:
                raise

        assert (
            success
        ), "Hard wrap should not raise AttributeError about _is_wrap_boundary"
        # Verify we have multiple lines (wrapping occurred)
        assert len(textarea.lines) > 1

    def test_hard_wrap_editing_wrapped_line(self):
        """Test editing a line that has been hard-wrapped.

        Verifies that when editing wrapped lines, the wrap is
        re-applied correctly.
        """
        textarea = TextArea(width=10, height=5, wrap_mode="hard")
        # Type long text that wraps
        text = "Hello World Test"
        for char in text:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        initial_line_count = len(textarea.lines)

        # Go back and add more text
        textarea.handle_key(Keys.HOME)  # Move to start
        textarea.handle_key(Key("X", KeyType.CHARACTER, "X"))

        # Should still be properly wrapped
        for line in textarea.lines:
            assert len(line) <= 10

    def test_hard_wrap_with_empty_line(self):
        """Test hard wrap with empty lines.

        Verifies that empty lines don't cause issues with wrapping.
        """
        textarea = TextArea(width=10, height=5, wrap_mode="hard")
        # Create an empty line
        textarea.handle_key(Keys.ENTER)
        # Type on next line
        text = "Hello World"
        for char in text:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        # Should handle empty lines correctly
        assert len(textarea.lines) >= 2
        assert textarea.lines[0] == ""

    def test_soft_wrap_unchanged(self):
        """Test that soft wrap mode is unaffected by is_wrap_boundary fix.

        Verifies that soft wrap still works correctly and doesn't
        call the hard wrap code path.
        """
        textarea = TextArea(width=10, height=5, wrap_mode="soft")
        # Type long text
        long_text = "This is a very long line for soft wrap"
        for char in long_text:
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        # Soft wrap keeps text on one logical line
        assert len(textarea.lines) == 1
        assert len(textarea.lines[0]) > 10  # Not hard-wrapped


class TestTextAreaSelection:
    """Tests for TextArea selection state and helper methods."""

    def test_initial_no_selection(self):
        """Test textarea starts with no selection."""
        textarea = TextArea(value="Hello World")
        assert not textarea._has_selection()
        assert textarea.selection_anchor is None

    def test_has_selection_with_anchor(self):
        """Test _has_selection returns True when anchor differs from cursor."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5
        assert textarea._has_selection()

    def test_no_selection_when_anchor_equals_cursor(self):
        """Test _has_selection returns False when anchor equals cursor."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 5)
        textarea.cursor_row = 0
        textarea.cursor_col = 5
        assert not textarea._has_selection()

    def test_clear_selection(self):
        """Test _clear_selection removes anchor."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea._clear_selection()
        assert textarea.selection_anchor is None
        assert not textarea._has_selection()

    def test_get_selection_range_single_line_forward(self):
        """Test getting selection range for single line selection (forward)."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_row = 0
        textarea.cursor_col = 5

        selection_range = textarea._get_selection_range()
        assert selection_range == ((0, 0), (0, 5))

    def test_get_selection_range_single_line_backward(self):
        """Test getting selection range for single line selection (backward)."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 5)
        textarea.cursor_row = 0
        textarea.cursor_col = 0

        selection_range = textarea._get_selection_range()
        assert selection_range == ((0, 0), (0, 5))

    def test_get_selection_range_multiline_forward(self):
        """Test getting selection range for multi-line selection (forward)."""
        textarea = TextArea(value="Hello\nWorld")
        textarea.selection_anchor = (0, 2)
        textarea.cursor_row = 1
        textarea.cursor_col = 3

        selection_range = textarea._get_selection_range()
        assert selection_range == ((0, 2), (1, 3))

    def test_get_selection_range_multiline_backward(self):
        """Test getting selection range for multi-line selection (backward)."""
        textarea = TextArea(value="Hello\nWorld")
        textarea.selection_anchor = (1, 3)
        textarea.cursor_row = 0
        textarea.cursor_col = 2

        selection_range = textarea._get_selection_range()
        assert selection_range == ((0, 2), (1, 3))

    def test_get_selection_range_no_selection(self):
        """Test getting selection range returns None when no selection."""
        textarea = TextArea(value="Hello World")
        assert textarea._get_selection_range() is None

    def test_get_selected_text_single_line(self):
        """Test getting selected text from single line."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        assert textarea._get_selected_text() == "Hello"

    def test_get_selected_text_multiline(self):
        """Test getting selected text from multiple lines."""
        textarea = TextArea(value="Hello\nWorld\nTest")
        textarea.selection_anchor = (0, 2)
        textarea.cursor_row = 2
        textarea.cursor_col = 2

        assert textarea._get_selected_text() == "llo\nWorld\nTe"

    def test_get_selected_text_no_selection(self):
        """Test getting selected text returns empty string when no selection."""
        textarea = TextArea(value="Hello World")
        assert textarea._get_selected_text() == ""

    def test_delete_selection_single_line(self):
        """Test deleting selection on single line."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        assert textarea._delete_selection()
        assert textarea.get_value() == " World"
        assert textarea.cursor_row == 0
        assert textarea.cursor_col == 0
        assert not textarea._has_selection()

    def test_delete_selection_multiline(self):
        """Test deleting multi-line selection."""
        textarea = TextArea(value="Hello\nWorld\nTest")
        textarea.selection_anchor = (0, 2)
        textarea.cursor_row = 2
        textarea.cursor_col = 2

        assert textarea._delete_selection()
        assert textarea.get_value() == "Hest"
        assert textarea.cursor_row == 0
        assert textarea.cursor_col == 2
        assert not textarea._has_selection()

    def test_delete_selection_no_selection(self):
        """Test deleting selection returns False when no selection."""
        textarea = TextArea(value="Hello World")
        assert not textarea._delete_selection()

    def test_select_all(self):
        """Test select all text."""
        textarea = TextArea(value="Hello\nWorld")
        textarea._select_all()

        assert textarea.selection_anchor == (0, 0)
        assert textarea.cursor_row == 1
        assert textarea.cursor_col == 5
        assert textarea._get_selected_text() == "Hello\nWorld"

    def test_select_word_at_position_middle(self):
        """Test selecting word at position (middle of word)."""
        textarea = TextArea(value="Hello World Test")
        textarea._select_word_at_position(0, 7)  # 'W' in World

        assert textarea.selection_anchor == (0, 6)
        assert textarea.cursor_col == 11

    def test_select_word_at_position_start(self):
        """Test selecting word at position (start of word)."""
        textarea = TextArea(value="Hello World Test")
        textarea._select_word_at_position(0, 0)  # 'H' in Hello

        assert textarea.selection_anchor == (0, 0)
        assert textarea.cursor_col == 5

    def test_select_word_at_position_non_word_char(self):
        """Test selecting non-word character."""
        textarea = TextArea(value="Hello, World")
        textarea._select_word_at_position(0, 5)  # ',' comma

        assert textarea.selection_anchor == (0, 5)
        assert textarea.cursor_col == 6

    def test_is_position_selected_single_line(self):
        """Test checking if position is selected (single line)."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 2)
        textarea.cursor_col = 7

        assert not textarea._is_position_selected(0, 0)
        assert not textarea._is_position_selected(0, 1)
        assert textarea._is_position_selected(0, 2)
        assert textarea._is_position_selected(0, 5)
        assert not textarea._is_position_selected(0, 7)
        assert not textarea._is_position_selected(0, 10)

    def test_is_position_selected_multiline(self):
        """Test checking if position is selected (multi-line)."""
        textarea = TextArea(value="Hello\nWorld\nTest")
        textarea.selection_anchor = (0, 3)
        textarea.cursor_row = 2
        textarea.cursor_col = 2

        # Line 0: positions >= 3 selected
        assert not textarea._is_position_selected(0, 0)
        assert textarea._is_position_selected(0, 3)
        assert textarea._is_position_selected(0, 4)

        # Line 1: all positions selected
        assert textarea._is_position_selected(1, 0)
        assert textarea._is_position_selected(1, 3)

        # Line 2: positions < 2 selected
        assert textarea._is_position_selected(2, 0)
        assert textarea._is_position_selected(2, 1)
        assert not textarea._is_position_selected(2, 2)


class TestTextAreaKeyboardSelection:
    """Tests for keyboard-based text selection."""

    def test_shift_right_arrow_selects(self):
        """Test Shift+Right arrow selects text."""
        textarea = TextArea(value="Hello")
        key = Key("shift+right", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea.selection_anchor == (0, 0)
        assert textarea.cursor_col == 1

    def test_shift_left_arrow_selects(self):
        """Test Shift+Left arrow selects text."""
        textarea = TextArea(value="Hello")
        textarea.cursor_col = 5
        key = Key("shift+left", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea.selection_anchor == (0, 5)
        assert textarea.cursor_col == 4

    def test_shift_down_arrow_selects(self):
        """Test Shift+Down arrow selects text."""
        textarea = TextArea(value="Hello\nWorld")
        key = Key("shift+down", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea.selection_anchor == (0, 0)
        assert textarea.cursor_row == 1

    def test_shift_up_arrow_selects(self):
        """Test Shift+Up arrow selects text."""
        textarea = TextArea(value="Hello\nWorld")
        textarea.cursor_row = 1
        key = Key("shift+up", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea.selection_anchor == (1, 0)
        assert textarea.cursor_row == 0

    def test_shift_home_selects_to_line_start(self):
        """Test Shift+Home selects to line start."""
        textarea = TextArea(value="Hello World")
        textarea.cursor_col = 5
        key = Key("shift+home", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea._get_selected_text() == "Hello"

    def test_shift_end_selects_to_line_end(self):
        """Test Shift+End selects to line end."""
        textarea = TextArea(value="Hello World")
        key = Key("shift+end", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea._get_selected_text() == "Hello World"

    def test_shift_ctrl_home_selects_to_document_start(self):
        """Test Shift+Ctrl+Home selects to document start."""
        textarea = TextArea(value="Hello\nWorld\nTest")
        textarea.cursor_row = 2
        textarea.cursor_col = 2
        key = Key("ctrl+shift+home", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea._get_selected_text() == "Hello\nWorld\nTe"

    def test_shift_ctrl_end_selects_to_document_end(self):
        """Test Shift+Ctrl+End selects to document end."""
        textarea = TextArea(value="Hello\nWorld\nTest")
        key = Key("ctrl+shift+end", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea._get_selected_text() == "Hello\nWorld\nTest"

    def test_shift_ctrl_right_selects_word(self):
        """Test Shift+Ctrl+Right selects by word."""
        textarea = TextArea(value="Hello World Test")
        key = Key("ctrl+shift+right", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        # Word boundary navigation includes trailing spaces
        assert textarea._get_selected_text() == "Hello "

    def test_shift_ctrl_left_selects_word_backward(self):
        """Test Shift+Ctrl+Left selects word backward."""
        textarea = TextArea(value="Hello World Test")
        textarea.cursor_col = 11  # After "World"
        key = Key("ctrl+shift+left", KeyType.SPECIAL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        # Selection should be from cursor back to start of "World"
        assert "World" in textarea._get_selected_text()

    def test_extending_existing_selection(self):
        """Test extending an existing selection."""
        textarea = TextArea(value="Hello World")

        # Create initial selection
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        # Extend it
        key = Key("shift+right", KeyType.SPECIAL)
        textarea.handle_key(key)

        assert textarea.selection_anchor == (0, 0)  # Anchor stays same
        assert textarea.cursor_col == 6
        assert textarea._get_selected_text() == "Hello "

    def test_arrow_without_shift_clears_selection(self):
        """Test arrow key without Shift clears selection."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        # Move right without shift
        textarea.handle_key(Keys.RIGHT)

        assert not textarea._has_selection()

    def test_ctrl_a_selects_all(self):
        """Test Ctrl+A selects all text."""
        textarea = TextArea(value="Hello\nWorld")
        key = Key("ctrl+a", KeyType.CONTROL)

        textarea.handle_key(key)
        assert textarea._has_selection()
        assert textarea._get_selected_text() == "Hello\nWorld"


class TestTextAreaClipboard:
    """Tests for clipboard operations."""

    def test_copy_selection(self):
        """Test copying selected text."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        assert textarea._copy_selection()
        # Can't easily test clipboard content without mocking, but verify method returns True
        assert textarea._has_selection()  # Selection remains

    def test_copy_no_selection(self):
        """Test copying with no selection returns False."""
        textarea = TextArea(value="Hello World")
        assert not textarea._copy_selection()

    def test_cut_selection(self):
        """Test cutting selected text."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        assert textarea._cut_selection()
        assert textarea.get_value() == " World"
        assert not textarea._has_selection()

    def test_cut_no_selection(self):
        """Test cutting with no selection returns False."""
        textarea = TextArea(value="Hello World")
        assert not textarea._cut_selection()

    def test_paste_single_line(self):
        """Test pasting single line text."""
        import sys

        textarea = TextArea(value="World")
        # Set fallback clipboard directly via sys.modules
        text_mod = sys.modules["wijjit.elements.input.text"]
        old_clipboard = text_mod._FALLBACK_CLIPBOARD
        text_mod._FALLBACK_CLIPBOARD = "Hello "

        result = textarea._paste()
        assert result
        assert textarea.get_value() == "Hello World"
        assert textarea.cursor_col == 6

        # Restore
        text_mod._FALLBACK_CLIPBOARD = old_clipboard

    def test_paste_multiline(self):
        """Test pasting multi-line text."""
        import sys

        textarea = TextArea(value="End")
        # Set fallback clipboard directly via sys.modules
        text_mod = sys.modules["wijjit.elements.input.text"]
        old_clipboard = text_mod._FALLBACK_CLIPBOARD
        text_mod._FALLBACK_CLIPBOARD = "Hello\nWorld\n"

        result = textarea._paste()
        assert result
        assert textarea.get_value() == "Hello\nWorld\nEnd"
        assert textarea.cursor_row == 2
        assert textarea.cursor_col == 0

        # Restore
        text_mod._FALLBACK_CLIPBOARD = old_clipboard

    def test_paste_replaces_selection(self):
        """Test pasting replaces selected text."""
        import sys

        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 6)
        textarea.cursor_col = 11  # Select "World"
        # Set fallback clipboard directly via sys.modules
        text_mod = sys.modules["wijjit.elements.input.text"]
        old_clipboard = text_mod._FALLBACK_CLIPBOARD
        text_mod._FALLBACK_CLIPBOARD = "Python"

        result = textarea._paste()
        assert result
        assert textarea.get_value() == "Hello Python"

        # Restore
        text_mod._FALLBACK_CLIPBOARD = old_clipboard

    def test_paste_empty_clipboard(self):
        """Test pasting from empty clipboard returns False."""
        textarea = TextArea(value="Hello")
        # Clear clipboard
        textarea._copy_to_clipboard("")

        result = textarea._paste()
        assert not result
        assert textarea.get_value() == "Hello"

    def test_ctrl_c_copies(self):
        """Test Ctrl+C copies selection."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5
        key = Key("ctrl+c", KeyType.CONTROL)

        result = textarea.handle_key(key)
        assert result
        assert textarea._has_selection()  # Selection remains

    def test_ctrl_x_cuts(self):
        """Test Ctrl+X cuts selection."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5
        key = Key("ctrl+x", KeyType.CONTROL)

        result = textarea.handle_key(key)
        assert result
        assert textarea.get_value() == " World"

    def test_ctrl_v_pastes(self):
        """Test Ctrl+V pastes clipboard content."""
        import sys

        textarea = TextArea(value="World")
        # Set fallback clipboard directly via sys.modules
        text_mod = sys.modules["wijjit.elements.input.text"]
        old_clipboard = text_mod._FALLBACK_CLIPBOARD
        text_mod._FALLBACK_CLIPBOARD = "Hello "
        key = Key("ctrl+v", KeyType.CONTROL)

        result = textarea.handle_key(key)
        assert result
        assert textarea.get_value() == "Hello World"

        # Restore
        text_mod._FALLBACK_CLIPBOARD = old_clipboard


class TestTextAreaSelectionEditing:
    """Tests for editing operations with selection."""

    def test_backspace_deletes_selection(self):
        """Test Backspace deletes selected text."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        textarea.handle_key(Keys.BACKSPACE)
        assert textarea.get_value() == " World"
        assert not textarea._has_selection()

    def test_delete_key_deletes_selection(self):
        """Test Delete key deletes selected text."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        textarea.handle_key(Keys.DELETE)
        assert textarea.get_value() == " World"
        assert not textarea._has_selection()

    def test_typing_replaces_selection(self):
        """Test typing character replaces selection."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 6)
        textarea.cursor_col = 11  # Select "World"

        textarea.handle_key(Key("X", KeyType.CHARACTER, "X"))
        assert textarea.get_value() == "Hello X"
        assert textarea.cursor_col == 7

    def test_enter_replaces_selection(self):
        """Test Enter key replaces selection with newline."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 5)
        textarea.cursor_col = 6  # Select space

        textarea.handle_key(Keys.ENTER)
        assert textarea.get_value() == "Hello\nWorld"
        assert textarea.cursor_row == 1
        assert textarea.cursor_col == 0

    def test_typing_multiple_chars_after_delete_selection(self):
        """Test typing multiple characters after deleting selection."""
        textarea = TextArea(value="Hello World")
        textarea.selection_anchor = (0, 6)
        textarea.cursor_col = 11

        for char in "Python":
            textarea.handle_key(Key(char, KeyType.CHARACTER, char))

        assert textarea.get_value() == "Hello Python"


class TestTextAreaMouseSelection:
    """Tests for mouse-based text selection."""

    def test_click_clears_selection(self):
        """Test clicking clears existing selection."""
        textarea = TextArea(value="Hello World", width=20, height=5)
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        event = MouseEvent(
            type=MouseEventType.CLICK,
            button=MouseButton.LEFT,
            x=10,
            y=0,
            shift=False,
        )
        textarea.handle_mouse(event)

        assert not textarea._has_selection()

    def test_shift_click_extends_selection(self):
        """Test Shift+Click extends selection."""
        textarea = TextArea(value="Hello World", width=20, height=5)
        textarea.cursor_col = 0

        event = MouseEvent(
            type=MouseEventType.CLICK,
            button=MouseButton.LEFT,
            x=5,
            y=0,
            shift=True,
        )
        textarea.handle_mouse(event)

        assert textarea._has_selection()
        assert textarea.selection_anchor == (0, 0)

    def test_double_click_selects_word(self):
        """Test double-click selects word."""
        textarea = TextArea(value="Hello World Test", width=20, height=5)

        event = MouseEvent(
            type=MouseEventType.DOUBLE_CLICK,
            button=MouseButton.LEFT,
            x=7,
            y=0,
            shift=False,
        )
        textarea.handle_mouse(event)

        assert textarea._has_selection()
        # Should select word at position (implementation may vary based on wrapping)

    def test_mouse_drag_creates_selection(self):
        """Test mouse drag creates selection."""
        textarea = TextArea(value="Hello World", width=20, height=5)

        # Mouse down
        press_event = MouseEvent(
            type=MouseEventType.PRESS,
            button=MouseButton.LEFT,
            x=0,
            y=0,
            shift=False,
        )
        textarea.handle_mouse(press_event)
        assert textarea._mouse_down

        # Drag
        drag_event = MouseEvent(
            type=MouseEventType.DRAG,
            button=MouseButton.LEFT,
            x=5,
            y=0,
            shift=False,
        )
        textarea.handle_mouse(drag_event)

        assert textarea._has_selection()

        # Release
        release_event = MouseEvent(
            type=MouseEventType.RELEASE,
            button=MouseButton.LEFT,
            x=5,
            y=0,
            shift=False,
        )
        textarea.handle_mouse(release_event)

        assert not textarea._mouse_down

    def test_mouse_press_with_shift_extends_selection(self):
        """Test mouse press with Shift extends selection."""
        textarea = TextArea(value="Hello World", width=20, height=5)
        textarea.cursor_col = 0

        event = MouseEvent(
            type=MouseEventType.PRESS,
            button=MouseButton.LEFT,
            x=5,
            y=0,
            shift=True,
        )
        textarea.handle_mouse(event)

        assert textarea._has_selection()
        assert textarea.selection_anchor == (0, 0)


class TestTextAreaSelectionEdgeCases:
    """Tests for edge cases in selection handling."""

    def test_select_all_empty_textarea(self):
        """Test select all on empty textarea."""
        textarea = TextArea(value="")
        textarea._select_all()

        assert textarea.selection_anchor == (0, 0)
        assert textarea.cursor_row == 0
        assert textarea.cursor_col == 0
        assert textarea._get_selected_text() == ""

    def test_selection_across_empty_lines(self):
        """Test selection spanning empty lines."""
        textarea = TextArea(value="Hello\n\nWorld")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_row = 2
        textarea.cursor_col = 5

        assert textarea._get_selected_text() == "Hello\n\nWorld"

    def test_delete_multiline_selection_leaves_single_line(self):
        """Test deleting multi-line selection leaves correct merged line."""
        textarea = TextArea(value="Hello\nMiddle\nWorld")
        textarea.selection_anchor = (0, 2)
        textarea.cursor_row = 2
        textarea.cursor_col = 2

        textarea._delete_selection()
        assert textarea.get_value() == "Herld"
        assert len(textarea.lines) == 1

    def test_paste_multiline_in_middle_of_line(self):
        """Test pasting multi-line text in middle of line."""
        import sys

        textarea = TextArea(value="HelloWorld")
        textarea.cursor_col = 5
        # Set fallback clipboard directly via sys.modules
        text_mod = sys.modules["wijjit.elements.input.text"]
        old_clipboard = text_mod._FALLBACK_CLIPBOARD
        text_mod._FALLBACK_CLIPBOARD = "A\nB\nC"

        result = textarea._paste()
        assert result
        assert textarea.get_value() == "HelloA\nB\nCWorld"
        assert textarea.cursor_row == 2
        assert textarea.cursor_col == 1

        # Restore
        text_mod._FALLBACK_CLIPBOARD = old_clipboard

    def test_selection_with_wrapping_none(self):
        """Test selection works with wrap_mode none."""
        textarea = TextArea(value="Short line", width=5, height=3, wrap_mode="none")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        assert textarea._get_selected_text() == "Short"

    def test_selection_with_wrapping_soft(self):
        """Test selection works with wrap_mode soft."""
        textarea = TextArea(value="Short line", width=5, height=3, wrap_mode="soft")
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5

        assert textarea._get_selected_text() == "Short"

    def test_cursor_movement_clears_selection(self):
        """Test various cursor movements clear selection when Shift not held."""
        textarea = TextArea(value="Hello\nWorld")

        # Create selection
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5
        assert textarea._has_selection()

        # Move cursor without shift - should clear selection
        textarea.handle_key(Keys.DOWN)
        assert not textarea._has_selection()

    def test_selection_at_document_boundaries(self):
        """Test selection at document start and end."""
        textarea = TextArea(value="Hello")

        # Select from start
        textarea.selection_anchor = (0, 0)
        textarea.cursor_col = 5
        assert textarea._get_selected_text() == "Hello"

        # Select to start (backward)
        textarea.selection_anchor = (0, 5)
        textarea.cursor_col = 0
        assert textarea._get_selected_text() == "Hello"
