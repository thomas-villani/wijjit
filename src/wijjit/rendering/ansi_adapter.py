"""ANSI string to Cell conversion utilities.

This module converts between ANSI escape sequence strings and the cell-based
representation the screen buffer works in. It was written as a migration bridge
while elements moved to cell rendering, but it outlived that job: it is the
supported path for content that arrives *already* rendered as ANSI, which the
framework cannot produce cell-by-cell itself. :func:`ansi_string_to_cells` backs
the ``content_type="ansi"`` attribute (Rich-rendered tables, syntax-highlighted
output, captured process output) and is used by ContentView, Table, and the
content renderers.

OSC 8 hyperlinks in the content are kept: each cell a link covers carries it
(:class:`~wijjit.terminal.cell.Hyperlink`), and the emitters re-open the link
around those cells, so the terminal can still offer the click. A target that
could inject escape sequences, or whose scheme is not allowed, is dropped and
its text kept (:func:`~wijjit.terminal.cell.make_hyperlink`). Every other OSC
sequence (window titles and so on) is stripped.

Wide characters are column-correct: :func:`ansi_string_to_cells` emits a
continuation cell after each width-2 glyph, as the wcwidth-aware
:class:`~wijjit.rendering.paint_context.PaintContext` write APIs do, so cell
index and display column agree.
"""

import re
from dataclasses import replace

from wijjit.terminal.ansi import display_width
from wijjit.terminal.cell import (
    CONTINUATION_CHAR,
    Cell,
    Color,
    Hyperlink,
    is_continuation,
    make_hyperlink,
)

# Precompiled regex patterns for ANSI parsing
# SGR (Select Graphic Rendition) - styling codes we want to parse
_SGR_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")

# Other ANSI escape sequences to strip (cursor movement, erase, positioning...).
# This is the full ECMA-48 CSI grammar - ESC [ + parameter bytes (0x30-0x3F) +
# intermediate bytes (0x20-0x2F) + a final byte (0x40-0x7E) - deliberately the
# same shape as ``ANSI_ESCAPE_PATTERN`` in :mod:`wijjit.terminal.ansi`. The
# earlier ``\x1b\[[0-9;?]*[A-Za-z]`` was narrower on both ends: it omitted the
# intermediate bytes and restricted the final byte to letters, so a
# ``~``-terminated sequence like ``\x1b[3~`` did not match, fell through to the
# literal branch below, and planted a visible ESC character in the buffer.
_OTHER_ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

# OSC 8 hyperlink: ESC ] 8 ; params ; URI, terminated by BEL or ST (ESC \).
# params is a ':'-separated list of key=value pairs (only ``id`` is defined);
# an empty URI closes the active link. The URI group stops at the first
# terminator, so an ESC inside it that is not ST ends up in the target, where
# make_hyperlink refuses it.
_OSC8_PATTERN = re.compile(r"\x1b\]8;([^;\x07\x1b]*);(.*?)(?:\x07|\x1b\\)")

# Other OSC (Operating System Command) sequences to strip
# Format: ESC ] ... BEL or ESC ] ... ESC \
# Used for terminal titles, etc.
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
    - OSC 8 hyperlinks, attached to the cells they cover as ``Cell.link``.
      An unsafe target is dropped and its text kept unlinked; see
      :func:`~wijjit.terminal.cell.make_hyperlink`. A link left open at the end
      of the string covers the rest of it.

    This is a temporary utility for the migration period and will be removed
    once all elements use cell-based rendering.

    The result has one cell per terminal column, laid out as
    :meth:`wijjit.rendering.paint_context.PaintContext.write_text` lays out
    text: a width-2 glyph (CJK, most emoji) is a head cell plus a continuation
    cell, and a zero-width combining mark is folded onto the glyph before it.
    Index ``n`` of a row is therefore display column ``n``. Cut a row with
    :func:`clip_cells` so a wide glyph is never split at the edge.

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

    cells: list[Cell] = []
    current_style = _StyleState()
    current_link: Hyperlink | None = None
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

        # OSC 8 hyperlink: open (or close, with an empty URI) the active link.
        match = _OSC8_PATTERN.match(ansi_str, i)
        if match:
            current_link = _parse_hyperlink(match.group(1), match.group(2))
            i = match.end()
            continue

        # Check for other OSC (Operating System Command) sequences
        # These are used for window titles, etc.
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
            link=current_link,
        )
        i += 1

        width = display_width(char)
        if width == 0 and cells:
            # Zero-width (a combining mark): fold it onto the glyph it
            # modifies, stepping back over that glyph's continuation cell.
            head = len(cells) - 1
            if is_continuation(cells[head]) and head > 0:
                head -= 1
            cells[head] = replace(cells[head], char=cells[head].char + char)
            continue

        cells.append(cell)
        if width == 2:
            # Width-2 glyph: head cell plus a continuation cell in the next
            # column, as PaintContext.write_text lays them out.
            cells.append(replace(cell, char=CONTINUATION_CHAR))

    return cells


def clip_cells(cells: list[Cell], width: int) -> list[Cell]:
    """Cut a row of cells to ``width`` columns without halving a wide glyph.

    Parameters
    ----------
    cells : list of Cell
        A row as :func:`ansi_string_to_cells` returns it (one cell per column).
    width : int
        Columns to keep.

    Returns
    -------
    list of Cell
        At most ``width`` cells. When the cut falls between a wide glyph's head
        and its continuation, the head is replaced by a space in the same
        style: printed, it would spill one column past ``width`` (onto a
        border or scrollbar).
    """
    clipped = cells[:width]
    if (
        clipped
        and len(cells) > width
        and is_continuation(cells[width])
        and not is_continuation(clipped[-1])
    ):
        clipped[-1] = replace(clipped[-1], char=" ")
    return clipped


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
        # Skip continuation cells: the head glyph already advances the terminal
        # two columns, so emitting the continuation would push output right.
        if is_continuation(cell):
            continue
        parts.append(cell.to_ansi())

    return "".join(parts)


def _parse_hyperlink(params: str, uri: str) -> Hyperlink | None:
    """Turn the parts of an OSC 8 sequence into the link it opens.

    Parameters
    ----------
    params : str
        The ``:``-separated ``key=value`` parameters (only ``id`` is used).
    uri : str
        The target. Empty closes the active link.

    Returns
    -------
    Hyperlink or None
        The link to attach to the following cells, or None when the sequence
        closes the link or its target is unsafe.
    """
    if not uri:
        return None
    link_id = None
    for param in params.split(":"):
        key, sep, value = param.partition("=")
        if sep and key == "id":
            link_id = value
    return make_hyperlink(uri, link_id or None)


class _StyleState:
    """Internal class to track current ANSI style state during parsing.

    Attributes
    ----------
    fg_color : Color or None
        Current foreground: an RGB triple, a palette index, or None
    bg_color : Color or None
        Current background, in the same forms
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
        self.fg_color: Color | None = None
        self.bg_color: Color | None = None
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
    Handles the SGR (Select Graphic Rendition) codes that map onto a cell:

    - 0: Reset
    - 1 / 2 / 3 / 4 / 7: Bold / dim / italic / underline / reverse on
    - 22: Bold and dim off; 23 / 24 / 27: italic / underline / reverse off
    - 30-37, 90-97: Foreground palette colors 0-7 and 8-15
    - 40-47, 100-107: Background palette colors 0-7 and 8-15
    - 38;5;N / 48;5;N: Foreground / background palette color N
    - 38;2;R;G;B / 48;2;R;G;B: Foreground / background true color
    - 39 / 49: Default foreground / background

    Palette colors are kept as palette indices rather than converted to RGB,
    so they are emitted as palette codes and the terminal's theme decides how
    they look. Converting them pinned, say, blue (34) to a fixed navy that is
    hard to read on a dark background.
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

        # Text attributes on
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

        # Text attributes off
        elif code_num == 22:
            style.bold = False
            style.dim = False
        elif code_num == 23:
            style.italic = False
        elif code_num == 24:
            style.underline = False
        elif code_num == 27:
            style.reverse = False

        # Palette colors 0-7 (30-37 fg, 40-47 bg) and 8-15 (90-97, 100-107)
        elif 30 <= code_num <= 37:
            style.fg_color = code_num - 30
        elif 40 <= code_num <= 47:
            style.bg_color = code_num - 40
        elif 90 <= code_num <= 97:
            style.fg_color = code_num - 90 + 8
        elif 100 <= code_num <= 107:
            style.bg_color = code_num - 100 + 8

        # Default colors
        elif code_num == 39:
            style.fg_color = None
        elif code_num == 49:
            style.bg_color = None

        # Extended colors (38;... fg, 48;... bg)
        elif code_num == 38:
            i, color = _parse_extended_color(codes, i)
            if color is not None:
                style.fg_color = color
        elif code_num == 48:
            i, color = _parse_extended_color(codes, i)
            if color is not None:
                style.bg_color = color

        i += 1


def _parse_extended_color(codes: list[str], i: int) -> tuple[int, Color | None]:
    """Parse extended color codes (38;... or 48;...).

    Parameters
    ----------
    codes : list of str
        ANSI code parameters
    i : int
        Current index in codes list (pointing to 38 or 48)

    Returns
    -------
    tuple of (int, Color or None)
        New index and the parsed color, or None if parsing failed

    Notes
    -----
    Handles:
    - 38;2;R;G;B or 48;2;R;G;B: True color, as an RGB triple
    - 38;5;N or 48;5;N: 256-color palette, as the palette index N
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
            color_idx = int(codes[i + 2])
            if not 0 <= color_idx <= 255:
                return i + 2, None
            return i + 2, color_idx

    except (ValueError, IndexError):
        pass

    return i, None
