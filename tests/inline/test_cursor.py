"""Tests for cursor control utilities."""

from wijjit.inline.cursor import (
    carriage_return,
    clear_line,
    clear_to_end_of_line,
    hide_cursor,
    move_cursor_down,
    move_cursor_up,
    move_to_column,
    restore_cursor_position,
    save_cursor_position,
    show_cursor,
)


class TestCursorVisibility:
    """Tests for cursor visibility functions."""

    def test_hide_cursor(self):
        """Test hide cursor returns correct ANSI sequence."""
        assert hide_cursor() == "\x1b[?25l"

    def test_show_cursor(self):
        """Test show cursor returns correct ANSI sequence."""
        assert show_cursor() == "\x1b[?25h"


class TestCursorMovement:
    """Tests for cursor movement functions."""

    def test_move_cursor_up(self):
        """Test cursor up movement."""
        assert move_cursor_up(1) == "\x1b[1A"
        assert move_cursor_up(5) == "\x1b[5A"
        assert move_cursor_up(10) == "\x1b[10A"

    def test_move_cursor_up_zero(self):
        """Test cursor up with zero returns empty string."""
        assert move_cursor_up(0) == ""

    def test_move_cursor_up_negative(self):
        """Test cursor up with negative returns empty string."""
        assert move_cursor_up(-1) == ""

    def test_move_cursor_down(self):
        """Test cursor down movement."""
        assert move_cursor_down(1) == "\x1b[1B"
        assert move_cursor_down(5) == "\x1b[5B"
        assert move_cursor_down(10) == "\x1b[10B"

    def test_move_cursor_down_zero(self):
        """Test cursor down with zero returns empty string."""
        assert move_cursor_down(0) == ""

    def test_move_cursor_down_negative(self):
        """Test cursor down with negative returns empty string."""
        assert move_cursor_down(-1) == ""

    def test_move_to_column(self):
        """Test cursor move to column."""
        assert move_to_column(1) == "\x1b[1G"
        assert move_to_column(10) == "\x1b[10G"
        assert move_to_column(80) == "\x1b[80G"


class TestCursorPosition:
    """Tests for cursor position save/restore functions."""

    def test_save_cursor_position(self):
        """Test save cursor position returns correct ANSI sequence."""
        assert save_cursor_position() == "\x1b[s"

    def test_restore_cursor_position(self):
        """Test restore cursor position returns correct ANSI sequence."""
        assert restore_cursor_position() == "\x1b[u"


class TestClearFunctions:
    """Tests for clear functions."""

    def test_clear_line(self):
        """Test clear line returns correct ANSI sequence."""
        assert clear_line() == "\x1b[2K"

    def test_clear_to_end_of_line(self):
        """Test clear to end of line returns correct ANSI sequence."""
        assert clear_to_end_of_line() == "\x1b[K"


class TestCarriageReturn:
    """Tests for carriage return function."""

    def test_carriage_return(self):
        """Test carriage return returns correct character."""
        assert carriage_return() == "\r"
