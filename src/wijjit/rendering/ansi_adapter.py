"""ANSI string to Cell conversion utilities (temporary migration bridge).

This module provides utilities to convert between ANSI escape sequence strings
and cell-based representations. This is a temporary bridge during the migration
from ANSI string-based rendering to cell-based rendering.

NOTE: This module will be DEPRECATED and removed once all elements are migrated
to cell-based rendering.
"""

import re

from wijjit.terminal.cell import Cell

# Precompiled regex patterns for ANSI parsing
# SGR (Select Graphic Rendition) - styling codes we want to parse
_SGR_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")

# Other ANSI escape sequences to strip (cursor movement, erase, positioning, etc.)
# This matches CSI sequences: ESC [ (params) (letter) where letter is NOT 'm' (which is SGR)
_OTHER_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# OSC (Operating System Command) sequences to strip
# Format: ESC ] ... BEL or ESC ] ... ESC \
# Used by Rich for hyperlinks, terminal titles, etc.
_OSC_PATTERN = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)")


def ansi_string_to_cells(ansi_str: str) -> list[Cell]:
    """Parse ANSI escape sequence string and convert to Cell objects.

    Parameters
    ----------
    ansi_str : str
        String potentially containing ANSI escape codes

    Returns
    -------
    list of Cell
        List of Cell objects with parsed styling

    Notes
    -----
    This function parses ANSI escape sequences and converts them to Cell
    objects with appropriate styling attributes. Supports:
    - Basic colors (30-37, 90-97 for foreground; 40-47, 100-107 for background)
    - True color RGB (38;2;R;G;B and 48;2;R;G;B)
    - Text attributes (bold, dim, italic, underline, reverse)
    - Reset codes

    This is a temporary utility for the migration period and will be removed
    once all elements use cell-based rendering.

    Examples
    --------
    Parse a simple ANSI string:

    >>> cells = ansi_string_to_cells('\\x1b[31mRed\\x1b[0m')
    >>> len(cells)
    3
    >>> cells[0].char
    'R'

    Parse text with multiple styles:

    >>> cells = ansi_string_to_cells('\\x1b[1;31mBold Red\\x1b[0m')
    >>> cells[0].bold
    True
    """
    if not ansi_str:
        return []

    cells = []
    current_style = _StyleState()
    i = 0

    while i < len(ansi_str):
        # Check for SGR (styling) codes first
        match = _SGR_PATTERN.match(ansi_str, i)
        if match:
            # Parse ANSI code and update current style
            codes_str = match.group(1)
            if codes_str:
                codes = codes_str.split(";")
                _apply_ansi_codes(current_style, codes)
            else:
                # Empty code is reset
                current_style.reset()

            i = match.end()
            continue

        # Check for other ANSI escape sequences (cursor movement, erase, etc.)
        # These should be stripped/ignored as they don't make sense in cell rendering
        match = _OTHER_ANSI_PATTERN.match(ansi_str, i)
        if match:
            # Skip this escape sequence entirely
            i = match.end()
            continue

        # Check for OSC (Operating System Command) sequences
        # These are used by Rich for hyperlinks, window titles, etc.
        match = _OSC_PATTERN.match(ansi_str, i)
        if match:
            # Skip entire OSC sequence
            i = match.end()
            continue

        # Check for other escape sequences that might not match the patterns above
        if ansi_str[i] == "\x1b":
            # Look ahead to see if this is some other escape sequence
            # If we see ESC followed by something other than '[' or ']', skip it
            if i + 1 < len(ansi_str) and ansi_str[i + 1] not in "[":
                # Skip ESC and next char (simple heuristic)
                i += 2
                continue

        # Regular character - create cell with current style
        char = ansi_str[i]
        cell = Cell(
            char=char,
            fg_color=current_style.fg_color,
            bg_color=current_style.bg_color,
            bold=current_style.bold,
            italic=current_style.italic,
            underline=current_style.underline,
            reverse=current_style.reverse,
            dim=current_style.dim,
        )
        cells.append(cell)
        i += 1

    return cells


def cells_to_ansi(cells: list[Cell]) -> str:
    """Convert Cell objects to ANSI escape sequence string.

    Parameters
    ----------
    cells : list of Cell
        List of Cell objects to convert

    Returns
    -------
    str
        String with ANSI escape sequences

    Notes
    -----
    This function is primarily used for testing and debugging. It converts
    Cell objects back to ANSI strings. Style changes are optimized to group
    consecutive cells with identical styling.

    Examples
    --------
    Convert cells to ANSI string:

    >>> cell = Cell('A', fg_color=(255, 0, 0), bold=True)
    >>> ansi = cells_to_ansi([cell])
    >>> '\\x1b[' in ansi
    True
    """
    if not cells:
        return ""

    parts = []
    for cell in cells:
        parts.append(cell.to_ansi())

    return "".join(parts)


class _StyleState:
    """Internal class to track current ANSI style state during parsing.

    Attributes
    ----------
    fg_color : tuple of (int, int, int) or None
        Current foreground RGB color
    bg_color : tuple of (int, int, int) or None
        Current background RGB color
    bold : bool
        Bold attribute
    italic : bool
        Italic attribute
    underline : bool
        Underline attribute
    reverse : bool
        Reverse video attribute
    dim : bool
        Dim attribute
    """

    def __init__(self) -> None:
        self.fg_color: tuple[int, int, int] | None = None
        self.bg_color: tuple[int, int, int] | None = None
        self.bold: bool = False
        self.italic: bool = False
        self.underline: bool = False
        self.reverse: bool = False
        self.dim: bool = False

    def reset(self) -> None:
        """Reset all style attributes to default."""
        self.fg_color = None
        self.bg_color = None
        self.bold = False
        self.italic = False
        self.underline = False
        self.reverse = False
        self.dim = False


# ANSI color code mappings to RGB
_ANSI_BASIC_COLORS = {
    # Standard colors (30-37 for fg, 40-47 for bg)
    0: (0, 0, 0),  # Black
    1: (128, 0, 0),  # Red
    2: (0, 128, 0),  # Green
    3: (128, 128, 0),  # Yellow
    4: (0, 0, 128),  # Blue
    5: (128, 0, 128),  # Magenta
    6: (0, 128, 128),  # Cyan
    7: (192, 192, 192),  # White
}

_ANSI_BRIGHT_COLORS = {
    # Bright colors (90-97 for fg, 100-107 for bg)
    0: (128, 128, 128),  # Bright Black (Gray)
    1: (255, 0, 0),  # Bright Red
    2: (0, 255, 0),  # Bright Green
    3: (255, 255, 0),  # Bright Yellow
    4: (0, 0, 255),  # Bright Blue
    5: (255, 0, 255),  # Bright Magenta
    6: (0, 255, 255),  # Bright Cyan
    7: (255, 255, 255),  # Bright White
}


def _apply_ansi_codes(style: _StyleState, codes: list[str]) -> None:
    """Apply ANSI codes to style state.

    Parameters
    ----------
    style : _StyleState
        Style state to modify
    codes : list of str
        ANSI code parameters to apply

    Notes
    -----
    Handles various ANSI SGR (Select Graphic Rendition) codes including:
    - 0: Reset
    - 1: Bold
    - 2: Dim
    - 3: Italic
    - 4: Underline
    - 7: Reverse
    - 30-37: Foreground basic colors
    - 38;2;R;G;B: Foreground true color
    - 38;5;N: Foreground 256-color (approximate to RGB)
    - 40-47: Background basic colors
    - 48;2;R;G;B: Background true color
    - 48;5;N: Background 256-color (approximate to RGB)
    - 90-97: Foreground bright colors
    - 100-107: Background bright colors
    """
    i = 0
    while i < len(codes):
        code = codes[i]

        try:
            code_num = int(code)
        except ValueError:
            i += 1
            continue

        # Reset
        if code_num == 0:
            style.reset()

        # Text attributes
        elif code_num == 1:
            style.bold = True
        elif code_num == 2:
            style.dim = True
        elif code_num == 3:
            style.italic = True
        elif code_num == 4:
            style.underline = True
        elif code_num == 7:
            style.reverse = True

        # Foreground basic colors (30-37)
        elif 30 <= code_num <= 37:
            color_idx = code_num - 30
            style.fg_color = _ANSI_BASIC_COLORS[color_idx]

        # Background basic colors (40-47)
        elif 40 <= code_num <= 47:
            color_idx = code_num - 40
            style.bg_color = _ANSI_BASIC_COLORS[color_idx]

        # Foreground extended colors (38;...)
        elif code_num == 38:
            i, color = _parse_extended_color(codes, i)
            if color:
                style.fg_color = color

        # Background extended colors (48;...)
        elif code_num == 48:
            i, color = _parse_extended_color(codes, i)
            if color:
                style.bg_color = color

        # Foreground bright colors (90-97)
        elif 90 <= code_num <= 97:
            color_idx = code_num - 90
            style.fg_color = _ANSI_BRIGHT_COLORS[color_idx]

        # Background bright colors (100-107)
        elif 100 <= code_num <= 107:
            color_idx = code_num - 100
            style.bg_color = _ANSI_BRIGHT_COLORS[color_idx]

        i += 1


def _parse_extended_color(
    codes: list[str], i: int
) -> tuple[int, tuple[int, int, int] | None]:
    """Parse extended color codes (38;... or 48;...).

    Parameters
    ----------
    codes : list of str
        ANSI code parameters
    i : int
        Current index in codes list (pointing to 38 or 48)

    Returns
    -------
    tuple of (int, tuple or None)
        New index and parsed RGB color tuple, or None if parsing failed

    Notes
    -----
    Handles:
    - 38;2;R;G;B or 48;2;R;G;B: True color RGB
    - 38;5;N or 48;5;N: 256-color palette (approximate conversion)
    """
    if i + 2 >= len(codes):
        return i, None

    try:
        mode = int(codes[i + 1])

        # True color RGB mode (38;2;R;G;B or 48;2;R;G;B)
        if mode == 2:
            if i + 4 >= len(codes):
                return i, None
            r = int(codes[i + 2])
            g = int(codes[i + 3])
            b = int(codes[i + 4])
            return i + 4, (r, g, b)

        # 256-color mode (38;5;N or 48;5;N)
        elif mode == 5:
            if i + 2 >= len(codes):
                return i, None
            color_idx = int(codes[i + 2])
            # Approximate conversion from 256-color to RGB
            rgb = _256color_to_rgb(color_idx)
            return i + 2, rgb

    except (ValueError, IndexError):
        pass

    return i, None


def _256color_to_rgb(color_idx: int) -> tuple[int, int, int]:
    """Convert 256-color palette index to approximate RGB.

    Parameters
    ----------
    color_idx : int
        Color index (0-255)

    Returns
    -------
    tuple of (int, int, int)
        Approximate RGB color

    Notes
    -----
    The 256-color palette consists of:
    - 0-15: Basic and bright colors
    - 16-231: 6x6x6 RGB cube
    - 232-255: Grayscale ramp
    """
    # Basic colors (0-15)
    if color_idx < 8:
        return _ANSI_BASIC_COLORS[color_idx]
    elif color_idx < 16:
        return _ANSI_BRIGHT_COLORS[color_idx - 8]

    # 216-color RGB cube (16-231)
    elif 16 <= color_idx <= 231:
        idx = color_idx - 16
        r = (idx // 36) * 51
        g = ((idx % 36) // 6) * 51
        b = (idx % 6) * 51
        return (r, g, b)

    # Grayscale ramp (232-255)
    else:
        gray = 8 + (color_idx - 232) * 10
        return (gray, gray, gray)
