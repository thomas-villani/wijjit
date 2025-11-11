"""ANSI escape sequence utilities for terminal control.

This module provides utilities for working with ANSI escape codes including
colors, cursor control, and text styling.
"""

import re

from wijjit.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# ANSI escape sequence pattern for stripping
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


class ANSIColor:
    """ANSI color codes for text and background."""

    # Foreground colors
    BLACK = "\x1b[30m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    WHITE = "\x1b[37m"

    # Bright foreground colors
    BRIGHT_BLACK = "\x1b[90m"
    BRIGHT_RED = "\x1b[91m"
    BRIGHT_GREEN = "\x1b[92m"
    BRIGHT_YELLOW = "\x1b[93m"
    BRIGHT_BLUE = "\x1b[94m"
    BRIGHT_MAGENTA = "\x1b[95m"
    BRIGHT_CYAN = "\x1b[96m"
    BRIGHT_WHITE = "\x1b[97m"

    # Background colors
    BG_BLACK = "\x1b[40m"
    BG_RED = "\x1b[41m"
    BG_GREEN = "\x1b[42m"
    BG_YELLOW = "\x1b[43m"
    BG_BLUE = "\x1b[44m"
    BG_MAGENTA = "\x1b[45m"
    BG_CYAN = "\x1b[46m"
    BG_WHITE = "\x1b[47m"

    # Reset
    RESET = "\x1b[0m"


class ANSIStyle:
    """ANSI text styling codes."""

    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    ITALIC = "\x1b[3m"
    UNDERLINE = "\x1b[4m"
    BLINK = "\x1b[5m"
    REVERSE = "\x1b[7m"
    HIDDEN = "\x1b[8m"
    STRIKETHROUGH = "\x1b[9m"

    RESET = "\x1b[0m"


class ANSICursor:
    """ANSI cursor control codes."""

    @staticmethod
    def up(n: int = 1) -> str:
        """Move cursor up n lines.

        Parameters
        ----------
        n : int
            Number of lines to move up

        Returns
        -------
        str
            ANSI escape sequence
        """
        return f"\x1b[{n}A"

    @staticmethod
    def down(n: int = 1) -> str:
        """Move cursor down n lines.

        Parameters
        ----------
        n : int
            Number of lines to move down

        Returns
        -------
        str
            ANSI escape sequence
        """
        return f"\x1b[{n}B"

    @staticmethod
    def forward(n: int = 1) -> str:
        """Move cursor forward n columns.

        Parameters
        ----------
        n : int
            Number of columns to move forward

        Returns
        -------
        str
            ANSI escape sequence
        """
        return f"\x1b[{n}C"

    @staticmethod
    def back(n: int = 1) -> str:
        """Move cursor back n columns.

        Parameters
        ----------
        n : int
            Number of columns to move back

        Returns
        -------
        str
            ANSI escape sequence
        """
        return f"\x1b[{n}D"

    @staticmethod
    def position(row: int, col: int) -> str:
        """Move cursor to specific position.

        Parameters
        ----------
        row : int
            Row position (1-indexed)
        col : int
            Column position (1-indexed)

        Returns
        -------
        str
            ANSI escape sequence
        """
        return f"\x1b[{row};{col}H"

    @staticmethod
    def hide() -> str:
        """Hide the cursor.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[?25l"

    @staticmethod
    def show() -> str:
        """Show the cursor.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[?25h"

    @staticmethod
    def save_position() -> str:
        """Save current cursor position.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[s"

    @staticmethod
    def restore_position() -> str:
        """Restore saved cursor position.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[u"

    @staticmethod
    def bell() -> str:
        """Emit terminal bell sound.

        Returns
        -------
        str
            Bell control character
        """
        return "\x07"


class ANSIScreen:
    """ANSI screen control codes."""

    @staticmethod
    def clear() -> str:
        """Clear entire screen.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[2J"

    @staticmethod
    def clear_line() -> str:
        """Clear current line.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[2K"

    @staticmethod
    def clear_to_end() -> str:
        """Clear from cursor to end of screen.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[0J"

    @staticmethod
    def clear_to_start() -> str:
        """Clear from cursor to start of screen.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[1J"

    @staticmethod
    def alternate_buffer_on() -> str:
        """Switch to alternate screen buffer.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[?1049h"

    @staticmethod
    def alternate_buffer_off() -> str:
        """Switch back to main screen buffer.

        Returns
        -------
        str
            ANSI escape sequence
        """
        return "\x1b[?1049l"


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text.

    Parameters
    ----------
    text : str
        Text potentially containing ANSI codes

    Returns
    -------
    str
        Text with ANSI codes removed
    """
    return ANSI_ESCAPE_PATTERN.sub("", text)


def visible_length(text: str) -> int:
    """Get the visible length of text (excluding ANSI codes).

    Parameters
    ----------
    text : str
        Text potentially containing ANSI codes

    Returns
    -------
    int
        Visible length of the text
    """
    return len(strip_ansi(text))


def clip_to_width(text: str, width: int, ellipsis: str = "...") -> str:
    """Clip text to specified width, preserving ANSI codes.

    This clips the visible text to the specified width while preserving
    any ANSI escape sequences in the output.

    Parameters
    ----------
    text : str
        Text to clip
    width : int
        Maximum visible width
    ellipsis : str
        Ellipsis to append if text is clipped

    Returns
    -------
    str
        Clipped text with ANSI codes preserved
    """
    if width <= 0:
        return ""

    current_length = visible_length(text)
    if current_length <= width:
        return text

    # Need to clip - iterate through preserving ANSI codes
    visible_count = 0
    result = []
    i = 0
    ellipsis_len = len(ellipsis)
    target_width = width - ellipsis_len if ellipsis_len <= width else width

    while i < len(text) and visible_count < target_width:
        if text[i : i + 2] == "\x1b[":
            # Found ANSI escape sequence - find the end
            end = i + 2
            while (
                end < len(text)
                and text[end]
                not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            ):
                end += 1
            if end < len(text):
                end += 1
            result.append(text[i:end])
            i = end
        else:
            # Regular character
            result.append(text[i])
            visible_count += 1
            i += 1

    output = "".join(result)
    if current_length > width and ellipsis:
        output += ellipsis

    # IMPORTANT: Preserve trailing ANSI codes (especially RESET) from the clipped portion
    # This prevents style bleeding when text is clipped
    trailing_ansi = []
    while i < len(text):
        if text[i : i + 2] == "\x1b[":
            # Found trailing ANSI escape sequence
            end = i + 2
            while (
                end < len(text)
                and text[end]
                not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            ):
                end += 1
            if end < len(text):
                end += 1
            trailing_ansi.append(text[i:end])
            i = end
        else:
            # Skip non-ANSI characters in clipped portion
            i += 1

    # Append trailing ANSI codes (like RESET) to prevent style bleeding
    if trailing_ansi:
        output += "".join(trailing_ansi)

    return output


def colorize(
    text: str,
    color: str | None = None,
    bg_color: str | None = None,
    bold: bool = False,
    underline: bool = False,
) -> str:
    """Apply ANSI colors and styles to text.

    Parameters
    ----------
    text : str
        Text to colorize
    color : str, optional
        Foreground color code
    bg_color : str, optional
        Background color code
    bold : bool
        Apply bold style
    underline : bool
        Apply underline style

    Returns
    -------
    str
        Text with ANSI styling applied
    """
    codes = []

    if bold:
        codes.append(ANSIStyle.BOLD)
    if underline:
        codes.append(ANSIStyle.UNDERLINE)
    if color:
        codes.append(color)
    if bg_color:
        codes.append(bg_color)

    if not codes:
        return text

    prefix = "".join(codes)
    return f"{prefix}{text}{ANSIStyle.RESET}"


_unicode_support_cache: bool | None = None


def supports_unicode() -> bool:
    """Check if the terminal supports unicode characters.

    This function checks the system encoding and environment variables
    to determine if unicode characters can be safely displayed.
    The result is cached for performance.

    Returns
    -------
    bool
        True if unicode is supported, False otherwise

    Notes
    -----
    Detection is based on:
    - System default encoding (UTF-8, utf8, etc.)
    - LANG environment variable
    - Terminal type environment variable
    """
    global _unicode_support_cache

    if _unicode_support_cache is not None:
        return _unicode_support_cache

    import locale
    import os
    import sys

    try:
        # Check system encoding
        encoding = sys.getdefaultencoding().lower()
        if "utf" in encoding or "utf8" in encoding:
            _unicode_support_cache = True
            return True

        # Check locale encoding
        locale_encoding = locale.getpreferredencoding().lower()
        if "utf" in locale_encoding or "utf8" in locale_encoding:
            _unicode_support_cache = True
            return True

        # Check LANG environment variable
        lang = os.environ.get("LANG", "").lower()
        if "utf" in lang or "utf8" in lang:
            _unicode_support_cache = True
            return True

        # Check if running on Windows with modern terminal
        if sys.platform == "win32":
            # Windows Terminal and Windows 10+ console support unicode
            wt_session = os.environ.get("WT_SESSION")
            if wt_session:
                _unicode_support_cache = True
                return True

        # Default to False for safety
        _unicode_support_cache = False
        return False

    except Exception as e:
        # If detection fails, default to False for safety
        logger.debug(f"Unicode support detection failed, defaulting to False: {e}")
        _unicode_support_cache = False
        return False


def is_wrap_boundary(char: str) -> bool:
    """Check if a character is a valid wrap boundary for line wrapping.

    Parameters
    ----------
    char : str
        Character to check

    Returns
    -------
    bool
        True if character is a wrap boundary (space, hyphen, or punctuation)

    Notes
    -----
    Smart word boundary detection for text wrapping.
    Allows breaking at spaces, hyphens, and common punctuation marks.

    Examples
    --------
    >>> is_wrap_boundary(' ')
    True
    >>> is_wrap_boundary('-')
    True
    >>> is_wrap_boundary('a')
    False
    >>> is_wrap_boundary('.')
    True
    """
    if not char:
        return False

    # Spaces are always wrap boundaries
    if char.isspace():
        return True

    # Hyphens allow wrapping after them
    if char == "-":
        return True

    # Common punctuation marks
    punctuation = ".,;:!?)]}\"'"
    if char in punctuation:
        return True

    return False


def wrap_text(text: str, width: int) -> list[str]:
    """Wrap a single line of text into multiple segments based on width.

    This function wraps text to the specified width while preserving ANSI
    escape codes. It uses smart word boundary detection to break at spaces,
    hyphens, and punctuation when possible, falling back to hard breaks at
    width boundaries when no suitable break point is found.

    Parameters
    ----------
    text : str
        Text to wrap (may contain ANSI escape codes)
    width : int
        Maximum width for each segment

    Returns
    -------
    list of str
        List of wrapped text segments, preserving ANSI codes

    Notes
    -----
    - Empty text returns a single empty string segment
    - Text shorter than width returns as-is in a single-element list
    - ANSI escape codes are preserved and don't count toward visible length
    - Smart word boundary detection prefers breaking at:
      1. Spaces
      2. Hyphens
      3. Punctuation marks
    - Falls back to hard break at width if no boundary found

    Examples
    --------
    Basic wrapping without ANSI codes:

    >>> wrap_text("Hello world this is a test", 10)
    ['Hello ', 'world this', ' is a test']

    Wrapping with ANSI codes (codes are preserved):

    >>> from wijjit.terminal.ansi import ANSIColor
    >>> text = f"{ANSIColor.RED}Hello{ANSIColor.RESET} world"
    >>> segments = wrap_text(text, 8)
    >>> # ANSI codes preserved, visible length respected

    Empty or short text:

    >>> wrap_text("", 10)
    ['']
    >>> wrap_text("Short", 10)
    ['Short']
    """
    if width <= 0:
        return [""]

    # Empty text returns single empty segment
    if not text:
        return [""]

    # Calculate visible length
    vis_len = visible_length(text)

    # If text fits within width, return as-is
    if vis_len <= width:
        return [text]

    # Text needs wrapping
    segments = []
    remaining = text

    while remaining:
        vis_len = visible_length(remaining)

        if vis_len <= width:
            # Remaining text fits
            segments.append(remaining)
            break

        # Find best wrap point within width
        # Scan through the visible characters to find last boundary before width
        last_boundary_vis = None
        last_boundary_actual = None

        # Strip ANSI to find visible character positions
        stripped = strip_ansi(remaining)

        # Build mapping of visible positions to actual positions
        # This accounts for ANSI codes in the original string
        for i, char in enumerate(stripped):
            if i >= width:
                break

            # Check if this is a wrap boundary
            if is_wrap_boundary(char):
                last_boundary_vis = i + 1  # Break after the boundary char
                last_boundary_actual = i + 1

        # Decide where to break
        if last_boundary_actual is not None and last_boundary_actual < len(stripped):
            # Found a wrap boundary within width
            # Use clip_to_width to get the segment with ANSI codes preserved
            segment = clip_to_width(remaining, last_boundary_vis, ellipsis="")
            segments.append(segment)

            # Calculate actual position in original string for the split
            # clip_to_width returns the string up to the visible width
            actual_cut_pos = len(segment)

            # Skip past the segment and remove leading spaces
            remaining = remaining[actual_cut_pos:].lstrip()

        else:
            # No wrap boundary found, force break at width
            segment = clip_to_width(remaining, width, ellipsis="")
            segments.append(segment)

            # Calculate actual position to cut
            actual_cut_pos = len(segment)
            remaining = remaining[actual_cut_pos:]

    return segments if segments else [""]


def dim_text(text: str, dim_factor: float = 0.6) -> str:
    """Dim text by reducing color brightness via ANSI codes.

    This function applies dimming to text with ANSI color codes by either
    using the ANSI DIM attribute or by reducing color intensity. Useful for
    creating backdrop dimming effects behind modals.

    Parameters
    ----------
    text : str
        Text potentially containing ANSI color codes
    dim_factor : float
        Dimming intensity (0.0 = black, 1.0 = original). Default is 0.6.

    Returns
    -------
    str
        Dimmed text with modified ANSI codes

    Notes
    -----
    For colored text, the function reduces RGB values in true-color codes
    and applies the DIM attribute for basic colors. For non-colored text,
    it applies the ANSI DIM style attribute.

    Examples
    --------
    >>> dim_text("Hello World")  # Applies DIM style
    >>> dim_text(f"{ANSIColor.RED}Error{ANSIColor.RESET}")  # Dims red color
    """
    if not text:
        return text

    # Pattern to match ANSI color codes
    # Matches: \x1b[XXm, \x1b[XX;XXm, \x1b[XX;XX;XXm, etc.
    ansi_pattern = re.compile(r"(\x1b\[[0-9;]*m)")

    parts = ansi_pattern.split(text)
    result = []
    has_ansi = False

    for part in parts:
        if ansi_pattern.match(part):
            # This is an ANSI code - try to dim it
            dimmed_code = _dim_ansi_code(part, dim_factor)
            result.append(dimmed_code)
            has_ansi = True
        else:
            # Regular text
            if part:
                result.append(part)

    # If no ANSI codes were found, wrap entire text with DIM
    if not has_ansi and text:
        return f"{ANSIStyle.DIM}{text}{ANSIStyle.RESET}"

    return "".join(result)


def _dim_ansi_code(code: str, dim_factor: float) -> str:
    """Dim a single ANSI escape code.

    Parameters
    ----------
    code : str
        ANSI escape code (e.g., '\x1b[31m')
    dim_factor : float
        Dimming intensity (0.0 = black, 1.0 = original)

    Returns
    -------
    str
        Dimmed ANSI code
    """
    # Extract the numeric part
    match = re.match(r"\x1b\[([0-9;]*)m", code)
    if not match:
        return code

    params = match.group(1)
    if not params:
        return code

    parts = params.split(";")

    # Handle different color code types
    if len(parts) == 1:
        # Basic 8/16 color codes
        color_code = int(parts[0])

        # Foreground colors (30-37, 90-97)
        if 30 <= color_code <= 37:
            # Bright version becomes normal, normal becomes dim
            return f"\x1b[2;{color_code}m"  # Add DIM attribute
        elif 90 <= color_code <= 97:
            # Bright colors -> normal colors
            normal_code = color_code - 60
            return f"\x1b[{normal_code}m"

        # Background colors (40-47, 100-107)
        elif 40 <= color_code <= 47:
            return f"\x1b[2;{color_code}m"  # Add DIM attribute
        elif 100 <= color_code <= 107:
            # Bright background -> normal background
            normal_code = color_code - 60
            return f"\x1b[{normal_code}m"

    elif len(parts) == 3 and parts[0] in ("38", "48") and parts[1] == "5":
        # 256-color mode: \x1b[38;5;Nm or \x1b[48;5;Nm
        fg_bg = parts[0]
        color_num = int(parts[2])

        # Dim by reducing color number (simple approach)
        dimmed_num = int(color_num * dim_factor)
        return f"\x1b[{fg_bg};5;{dimmed_num}m"

    elif len(parts) == 5 and parts[0] in ("38", "48") and parts[1] == "2":
        # RGB mode: \x1b[38;2;R;G;Bm or \x1b[48;2;R;G;Bm
        fg_bg = parts[0]
        r = int(parts[2])
        g = int(parts[3])
        b = int(parts[4])

        # Dim by reducing RGB values
        r_dimmed = int(r * dim_factor)
        g_dimmed = int(g * dim_factor)
        b_dimmed = int(b * dim_factor)

        return f"\x1b[{fg_bg};2;{r_dimmed};{g_dimmed};{b_dimmed}m"

    # Return original if we don't recognize the format
    return code


def apply_backdrop_dim(lines: list[str], dim_factor: float = 0.6) -> list[str]:
    """Apply dimming to a buffer of lines for backdrop effect.

    This function applies dimming to each line in a screen buffer, useful
    for creating backdrop dimming effects behind modals and overlays.

    Parameters
    ----------
    lines : list of str
        List of screen buffer lines (may contain ANSI codes)
    dim_factor : float
        Dimming intensity (0.0 = black, 1.0 = original). Default is 0.6.

    Returns
    -------
    list of str
        Dimmed lines with modified ANSI codes

    Notes
    -----
    This function processes each line independently, applying the dimming
    effect to all ANSI color codes found. Non-colored text receives the
    DIM style attribute.

    Examples
    --------
    >>> buffer = ["Line 1", f"{ANSIColor.BLUE}Line 2{ANSIColor.RESET}"]
    >>> dimmed = apply_backdrop_dim(buffer, dim_factor=0.5)
    """
    return [dim_text(line, dim_factor) for line in lines]
