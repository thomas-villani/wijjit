"""Tests for ANSI escape sequence utilities."""

from wijjit.terminal.ansi import (
    ANSIColor,
    ANSICursor,
    ANSIScreen,
    ANSIStyle,
    clip_to_width,
    colorize,
    strip_ansi,
    visible_length,
)


class TestANSIColor:
    """Tests for ANSIColor class."""

    def test_foreground_colors(self):
        """Test that foreground color codes are correct."""
        assert ANSIColor.RED == "\x1b[31m"
        assert ANSIColor.GREEN == "\x1b[32m"
        assert ANSIColor.BLUE == "\x1b[34m"

    def test_bright_colors(self):
        """Test that bright color codes are correct."""
        assert ANSIColor.BRIGHT_RED == "\x1b[91m"
        assert ANSIColor.BRIGHT_GREEN == "\x1b[92m"

    def test_background_colors(self):
        """Test that background color codes are correct."""
        assert ANSIColor.BG_RED == "\x1b[41m"
        assert ANSIColor.BG_GREEN == "\x1b[42m"

    def test_reset(self):
        """Test reset code."""
        assert ANSIColor.RESET == "\x1b[0m"


class TestANSIStyle:
    """Tests for ANSIStyle class."""

    def test_text_styles(self):
        """Test that text style codes are correct."""
        assert ANSIStyle.BOLD == "\x1b[1m"
        assert ANSIStyle.UNDERLINE == "\x1b[4m"
        assert ANSIStyle.ITALIC == "\x1b[3m"

    def test_reset(self):
        """Test reset code."""
        assert ANSIStyle.RESET == "\x1b[0m"


class TestANSICursor:
    """Tests for ANSICursor class."""

    def test_up(self):
        """Test cursor up movement."""
        assert ANSICursor.up() == "\x1b[1A"
        assert ANSICursor.up(5) == "\x1b[5A"

    def test_down(self):
        """Test cursor down movement."""
        assert ANSICursor.down() == "\x1b[1B"
        assert ANSICursor.down(3) == "\x1b[3B"

    def test_forward(self):
        """Test cursor forward movement."""
        assert ANSICursor.forward() == "\x1b[1C"
        assert ANSICursor.forward(10) == "\x1b[10C"

    def test_back(self):
        """Test cursor backward movement."""
        assert ANSICursor.back() == "\x1b[1D"
        assert ANSICursor.back(7) == "\x1b[7D"

    def test_position(self):
        """Test cursor positioning."""
        assert ANSICursor.position(1, 1) == "\x1b[1;1H"
        assert ANSICursor.position(10, 20) == "\x1b[10;20H"

    def test_hide_show(self):
        """Test cursor visibility."""
        assert ANSICursor.hide() == "\x1b[?25l"
        assert ANSICursor.show() == "\x1b[?25h"

    def test_save_restore(self):
        """Test cursor position save and restore."""
        assert ANSICursor.save_position() == "\x1b[s"
        assert ANSICursor.restore_position() == "\x1b[u"


class TestANSIScreen:
    """Tests for ANSIScreen class."""

    def test_clear(self):
        """Test screen clearing."""
        assert ANSIScreen.clear() == "\x1b[2J"

    def test_clear_line(self):
        """Test line clearing."""
        assert ANSIScreen.clear_line() == "\x1b[2K"

    def test_clear_to_end(self):
        """Test clear to end of screen."""
        assert ANSIScreen.clear_to_end() == "\x1b[0J"

    def test_clear_to_start(self):
        """Test clear to start of screen."""
        assert ANSIScreen.clear_to_start() == "\x1b[1J"

    def test_alternate_buffer(self):
        """Test alternate buffer switching."""
        assert ANSIScreen.alternate_buffer_on() == "\x1b[?1049h"
        assert ANSIScreen.alternate_buffer_off() == "\x1b[?1049l"


class TestStripAnsi:
    """Tests for strip_ansi function."""

    def test_strip_simple_color(self):
        """Test stripping simple color codes."""
        text = f"{ANSIColor.RED}Hello{ANSIColor.RESET}"
        assert strip_ansi(text) == "Hello"

    def test_strip_multiple_codes(self):
        """Test stripping multiple codes."""
        text = f"{ANSIStyle.BOLD}{ANSIColor.GREEN}Test{ANSIStyle.RESET}"
        assert strip_ansi(text) == "Test"

    def test_strip_no_ansi(self):
        """Test text without ANSI codes."""
        text = "Plain text"
        assert strip_ansi(text) == "Plain text"

    def test_strip_empty(self):
        """Test empty string."""
        assert strip_ansi("") == ""

    def test_strip_cursor_codes(self):
        """Test stripping cursor movement codes."""
        text = f"{ANSICursor.position(5, 10)}Text"
        assert strip_ansi(text) == "Text"


class TestVisibleLength:
    """Tests for visible_length function."""

    def test_plain_text(self):
        """Test length of plain text."""
        assert visible_length("Hello") == 5

    def test_text_with_colors(self):
        """Test length excludes ANSI color codes."""
        text = f"{ANSIColor.RED}Hello{ANSIColor.RESET}"
        assert visible_length(text) == 5

    def test_text_with_styles(self):
        """Test length excludes ANSI style codes."""
        text = f"{ANSIStyle.BOLD}Test{ANSIStyle.RESET}"
        assert visible_length(text) == 4

    def test_empty(self):
        """Test empty string."""
        assert visible_length("") == 0

    def test_only_ansi_codes(self):
        """Test string with only ANSI codes."""
        text = f"{ANSIColor.RED}{ANSIStyle.BOLD}{ANSIColor.RESET}"
        assert visible_length(text) == 0


class TestClipToWidth:
    """Tests for clip_to_width function."""

    def test_clip_plain_text(self):
        """Test clipping plain text."""
        assert clip_to_width("Hello World", 5) == "He..."

    def test_no_clip_when_fits(self):
        """Test no clipping when text fits."""
        assert clip_to_width("Hello", 10) == "Hello"

    def test_clip_with_ansi(self):
        """Test clipping preserves ANSI codes."""
        text = f"{ANSIColor.RED}Hello World{ANSIColor.RESET}"
        result = clip_to_width(text, 5)
        # Should have color codes preserved but only "He" visible
        assert ANSIColor.RED in result
        assert visible_length(result) <= 5

    def test_clip_zero_width(self):
        """Test clipping to zero width."""
        assert clip_to_width("Hello", 0) == ""

    def test_clip_custom_ellipsis(self):
        """Test custom ellipsis."""
        result = clip_to_width("Hello World", 5, ellipsis=">")
        assert result == "Hell>"

    def test_clip_no_ellipsis(self):
        """Test clipping without ellipsis."""
        result = clip_to_width("Hello World", 5, ellipsis="")
        assert result == "Hello"


class TestColorize:
    """Tests for colorize function."""

    def test_colorize_with_color(self):
        """Test adding color to text."""
        result = colorize("Hello", color=ANSIColor.RED)
        assert result == f"{ANSIColor.RED}Hello{ANSIStyle.RESET}"

    def test_colorize_with_background(self):
        """Test adding background color."""
        result = colorize("Hello", bg_color=ANSIColor.BG_BLUE)
        assert result == f"{ANSIColor.BG_BLUE}Hello{ANSIStyle.RESET}"

    def test_colorize_with_bold(self):
        """Test adding bold style."""
        result = colorize("Hello", bold=True)
        assert result == f"{ANSIStyle.BOLD}Hello{ANSIStyle.RESET}"

    def test_colorize_with_underline(self):
        """Test adding underline style."""
        result = colorize("Hello", underline=True)
        assert result == f"{ANSIStyle.UNDERLINE}Hello{ANSIStyle.RESET}"

    def test_colorize_combined(self):
        """Test combining multiple styles."""
        result = colorize("Hello", color=ANSIColor.RED, bold=True, underline=True)
        assert ANSIStyle.BOLD in result
        assert ANSIStyle.UNDERLINE in result
        assert ANSIColor.RED in result
        assert result.endswith(f"Hello{ANSIStyle.RESET}")

    def test_colorize_no_styling(self):
        """Test colorize with no styling returns original text."""
        result = colorize("Hello")
        assert result == "Hello"
