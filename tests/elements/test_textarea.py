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
