"""Cell-based terminal buffer for efficient rendering.

This module provides the core data structures for cell-based terminal rendering,
which enables efficient diff rendering, styling, and dirty region tracking.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import quote

from wijjit.terminal.ansi import get_hyperlink_schemes, is_no_color

# OSC 8 sequence that ends the active hyperlink (empty params, empty URI).
HYPERLINK_CLOSE = "\x1b]8;;\x1b\\"

# Longest hyperlink target emitted. Terminals cap OSC 8 URIs (VTE at 2083
# bytes); a longer target is dropped rather than emitted truncated.
MAX_HYPERLINK_LENGTH = 2048

# Longest OSC 8 ``id`` parameter kept. Terminals cap it too (VTE at 250).
MAX_HYPERLINK_ID_LENGTH = 250

# Characters left as-is when percent-encoding a hyperlink target: printable
# ASCII other than space. ``%`` is included so existing escapes survive.
_URI_SAFE = "".join(chr(c) for c in range(0x21, 0x7F))


def _is_control(char: str) -> bool:
    """Return whether ``char`` is a C0 or C1 control character, or DEL."""
    code = ord(char)
    return code < 0x20 or 0x7F <= code <= 0x9F


@dataclass(frozen=True, slots=True)
class Hyperlink:
    """An OSC 8 hyperlink target carried by the cells it covers.

    Opening a link is the terminal's job: Wijjit only emits the OSC 8 sequence
    around the cells that carry it, and never launches anything itself.

    Parameters
    ----------
    url : str
        The link target. Printable ASCII only (bytes 32-126, as the OSC 8
        convention requires), at most :data:`MAX_HYPERLINK_LENGTH` characters.
    id : str or None, optional
        The OSC 8 ``id`` parameter. Runs of cells that share a URL and an id are
        one link to the terminal, so a link wrapped across lines, or cut by a
        partial repaint, still highlights as one. Printable ASCII without
        ``:`` or ``;``, at most :data:`MAX_HYPERLINK_ID_LENGTH` characters.

    Raises
    ------
    ValueError
        If ``url`` or ``id`` could carry anything but a link: control
        characters (which would let a target inject escape sequences), other
        characters outside printable ASCII, or an over-long value. Use
        :func:`make_hyperlink` to build one from untrusted input.
    """

    url: str
    id: str | None = None

    def __post_init__(self) -> None:
        """Validate the target and id."""
        if not self.url or len(self.url) > MAX_HYPERLINK_LENGTH:
            raise ValueError("hyperlink url must be 1 to 2048 characters")
        if any(not 0x20 <= ord(c) <= 0x7E for c in self.url):
            raise ValueError("hyperlink url must be printable ASCII")
        if self.id is not None and (
            not self.id
            or len(self.id) > MAX_HYPERLINK_ID_LENGTH
            or any(not 0x21 <= ord(c) <= 0x7E or c in ":;" for c in self.id)
        ):
            raise ValueError("hyperlink id must be printable ASCII without ':' or ';'")

    def open_sequence(self) -> str:
        """Return the OSC 8 sequence that starts this link.

        Returns
        -------
        str
            ``ESC ] 8 ; params ; url ESC \\``. End the link with
            :data:`HYPERLINK_CLOSE`.
        """
        params = f"id={self.id}" if self.id else ""
        return f"\x1b]8;{params};{self.url}\x1b\\"


def hyperlink_sequence(link: Hyperlink | None) -> str:
    """Return the OSC 8 sequence that makes ``link`` the active link.

    Parameters
    ----------
    link : Hyperlink or None
        The link the next printed cells belong to, or None for no link.

    Returns
    -------
    str
        The link's open sequence, or :data:`HYPERLINK_CLOSE` for None. Opening
        a link also ends the previous one, so switching links directly needs
        no close in between.
    """
    return HYPERLINK_CLOSE if link is None else link.open_sequence()


def make_hyperlink(url: str, id: str | None = None) -> Hyperlink | None:
    """Build a :class:`Hyperlink` from untrusted input, or None if it is unsafe.

    Parameters
    ----------
    url : str
        The target as found in content (an OSC 8 URI).
    id : str or None, optional
        The OSC 8 ``id`` parameter, if any.

    Returns
    -------
    Hyperlink or None
        The link, or None when the target must not be emitted: it is empty,
        holds a control character (C0, DEL or C1, which could smuggle escape
        sequences into the output), is longer than
        :data:`MAX_HYPERLINK_LENGTH` once encoded, or its scheme is not in the
        allowlist set by :func:`wijjit.terminal.ansi.set_hyperlink_schemes`.

    Notes
    -----
    Other non-ASCII characters and spaces are percent-encoded rather than
    refused, so an internationalized URL still works. An invalid ``id`` is
    dropped and the link kept without one.
    """
    if not url or any(_is_control(c) for c in url):
        return None
    if any(not 0x21 <= ord(c) <= 0x7E for c in url):
        url = quote(url, safe=_URI_SAFE)
    if len(url) > MAX_HYPERLINK_LENGTH:
        return None

    schemes = get_hyperlink_schemes()
    if schemes is not None:
        scheme, sep, _ = url.partition(":")
        if not sep or scheme.lower() not in schemes:
            return None

    try:
        return Hyperlink(url, id)
    except ValueError:
        # Only the id can be at fault here: the url was checked above.
        return Hyperlink(url)


# Sentinel character marking a "continuation cell": the trailing column of a
# width-2 (wide) glyph. The head cell holds the full glyph and the following
# cell is a continuation carrying the head's style attributes with this empty
# char. Emitters skip continuation cells because the terminal advances two
# columns when the head glyph is printed. See ``is_continuation``.
CONTINUATION_CHAR = ""


def is_continuation(cell: "Cell") -> bool:
    """Return whether ``cell`` is the trailing column of a wide glyph.

    Parameters
    ----------
    cell : Cell
        Cell to test.

    Returns
    -------
    bool
        True if ``cell`` is a continuation cell (``char == CONTINUATION_CHAR``),
        i.e. the second column occupied by a preceding width-2 glyph.

    Notes
    -----
    Tested as ``not cell.char``: ``CONTINUATION_CHAR`` is the empty string and
    the empty string is the only falsy ``char`` in the pipeline (blank cells
    carry ``" "``), so this is exactly equivalent to ``== CONTINUATION_CHAR``
    while skipping the string compare on this hot path.
    """
    return not cell.char


@dataclass(slots=True)
class Cell:
    """A single terminal cell with character and styling attributes.

    This represents one character position in the terminal with associated
    colors and text attributes. Forms the foundation of the cell-based
    rendering system.

    Wide characters
    ---------------
    A width-2 glyph (most CJK, many emoji) is stored as two cells: a *head*
    cell holding the full glyph and a following *continuation* cell whose
    ``char`` is :data:`CONTINUATION_CHAR` (the empty string) carrying the same
    style attributes as the head. Use :func:`is_continuation` to detect the
    trailing cell. Emitters skip continuation cells because printing the head
    glyph already advances the terminal by two columns. Zero-width combining
    marks (e.g. an NFD-decomposed accent) are folded onto the base glyph as a
    single multi-code-point ``char`` on one cell.

    Parameters
    ----------
    char : str
        Single character or empty string
    fg_color : tuple of (int, int, int) or None, optional
        Foreground RGB color (0-255 each) or None for default terminal color
    bg_color : tuple of (int, int, int) or None, optional
        Background RGB color (0-255 each) or None for default terminal color
    bold : bool, optional
        Bold text attribute (default: False)
    italic : bool, optional
        Italic text attribute (default: False)
    underline : bool, optional
        Underline text attribute (default: False)
    reverse : bool, optional
        Reverse video (swap fg/bg colors) attribute (default: False)
    dim : bool, optional
        Dim/faint text attribute (default: False)
    link : Hyperlink or None, optional
        OSC 8 hyperlink the cell belongs to (default: None). Emitters open the
        link before the first cell of a run that carries it and close it after
        the last.

    Attributes
    ----------
    char : str
        The character to display
    fg_color : tuple of (int, int, int) or None
        Foreground color in RGB
    bg_color : tuple of (int, int, int) or None
        Background color in RGB
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
    link : Hyperlink or None
        OSC 8 hyperlink, or None
    _style_mask : int
        Pre-computed bitmask of style attributes for fast equality comparison.
        Computed in __post_init__. Bit layout: bold=1, italic=2, underline=4,
        reverse=8, dim=16.

    Notes
    -----
    RGB color values should be in the range 0-255. The terminal emulator
    will handle conversion to its native color format.

    The _style_mask field is an optimization for equality comparison. Instead
    of comparing 5 boolean fields individually, we compare a single integer.
    This reduces comparison overhead in hot rendering paths.

    Examples
    --------
    Create a simple cell with a character:

    >>> cell = Cell('A')
    >>> cell.char
    'A'

    Create a styled cell with color and bold:

    >>> cell = Cell('X', fg_color=(255, 0, 0), bold=True)
    >>> cell.fg_color
    (255, 0, 0)
    >>> cell.bold
    True
    """

    char: str
    fg_color: tuple[int, int, int] | None = None
    bg_color: tuple[int, int, int] | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False
    dim: bool = False
    link: Hyperlink | None = None
    # Pre-computed style mask for fast equality comparison (computed in __post_init__)
    _style_mask: int = 0

    def __post_init__(self) -> None:
        """Compute style mask after initialization."""
        # Pack boolean style attributes into a single integer bitmask
        # This enables O(1) comparison of all style flags
        object.__setattr__(
            self,
            "_style_mask",
            (self.bold)
            | (self.italic << 1)
            | (self.underline << 2)
            | (self.reverse << 3)
            | (self.dim << 4),
        )

    def __eq__(self, other: object) -> bool:
        """Check equality between two cells.

        Parameters
        ----------
        other : object
            Object to compare against

        Returns
        -------
        bool
            True if cells have identical content and styling

        Notes
        -----
        This optimized comparison uses pre-computed style masks to reduce
        the number of comparisons from 8 to 4 (char, style_mask, fg, bg).
        This is critical for diff rendering performance as it's called
        for every cell during buffer comparison.

        Comparison order is optimized for early exit:
        1. char - most likely to differ between cells
        2. _style_mask - single int comparison for 5 boolean fields
        3. fg_color - often differs for styled content
        4. bg_color - least likely to differ
        5. link - None on almost every cell
        """
        # Identity short-circuit. Empty buffer positions all reference one
        # shared blank cell (see screen_buffer._BLANK_CELL), so in the diff
        # hot path a blank column in both the old and new buffer is the *same*
        # object - this returns True without touching any field. Cheap and
        # universal (any reused cell instance benefits).
        if self is other:
            return True

        if not isinstance(other, Cell):
            return False

        # Optimized comparison order with pre-computed style mask
        return (
            self.char == other.char
            and self._style_mask == other._style_mask
            and self.fg_color == other.fg_color
            and self.bg_color == other.bg_color
            and self.link == other.link
        )

    def to_ansi(self) -> str:
        """Convert cell to ANSI escape sequence string.

        Returns
        -------
        str
            Character with ANSI styling codes

        Notes
        -----
        This generates the ANSI sequence needed to render this cell in a
        terminal. Used by the diff renderer to output styled text.

        When ``NO_COLOR`` is in effect, foreground and background colors are
        omitted while text attributes (bold, underline, reverse, ...) are kept.
        Reverse video in particular is how focus stays visible without color.

        Examples
        --------
        >>> cell = Cell('A', fg_color=(255, 0, 0), bold=True)
        >>> ansi = cell.to_ansi()
        >>> '\\x1b[' in ansi  # Contains ANSI codes
        True
        """
        codes = self._style_codes()

        # Build ANSI sequence
        if codes:
            ansi_codes = ";".join(codes)
            text = f"\x1b[{ansi_codes}m{self.char}\x1b[0m"
        else:
            text = self.char

        if self.link is not None:
            return f"{self.link.open_sequence()}{text}{HYPERLINK_CLOSE}"
        return text

    def _style_codes(self) -> list[str]:
        """Build the SGR parameter list for this cell, honoring ``NO_COLOR``.

        Returns
        -------
        list of str
            SGR parameters, e.g. ``["1", "38;2;255;0;0"]``. Color parameters are
            omitted entirely when :func:`~wijjit.terminal.ansi.is_no_color` is
            true.
        """
        codes = []

        # Text attributes are kept even under NO_COLOR: the standard suppresses
        # color, not styling, and reverse video is the color-free focus cue.
        if self.bold:
            codes.append("1")
        if self.dim:
            codes.append("2")
        if self.italic:
            codes.append("3")
        if self.underline:
            codes.append("4")
        if self.reverse:
            codes.append("7")

        if is_no_color():
            return codes

        # Foreground color (true color RGB)
        if self.fg_color is not None:
            r, g, b = self.fg_color
            codes.append(f"38;2;{r};{g};{b}")

        # Background color (true color RGB)
        if self.bg_color is not None:
            r, g, b = self.bg_color
            codes.append(f"48;2;{r};{g};{b}")

        return codes

    def get_style_codes(self) -> str:
        """Get ANSI style codes for this cell without character or reset.

        Returns
        -------
        str
            ANSI escape sequence for styling (without character or reset)

        Notes
        -----
        This is used by the diff renderer to emit style changes without
        resetting after each cell. The reset is handled at end of styled
        regions or end of lines.

        Colors are omitted when ``NO_COLOR`` is in effect; see
        :meth:`to_ansi`.

        Examples
        --------
        >>> cell = Cell('A', fg_color=(255, 0, 0), bold=True)
        >>> codes = cell.get_style_codes()
        >>> codes
        '\\x1b[1;38;2;255;0;0m'
        """
        codes = self._style_codes()

        # Build ANSI sequence (no char, no reset)
        if codes:
            ansi_codes = ";".join(codes)
            return f"\x1b[{ansi_codes}m"

        # No styling - emit reset to clear any previous style
        return "\x1b[0m"

    def clone(self) -> "Cell":
        """Create a deep copy of this cell.

        Returns
        -------
        Cell
            New cell with identical attributes
        """
        return Cell(
            char=self.char,
            fg_color=self.fg_color,
            bg_color=self.bg_color,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            reverse=self.reverse,
            dim=self.dim,
            link=self.link,
        )


@lru_cache(maxsize=1 << 15)
def intern_cell(
    char: str,
    fg_color: tuple[int, int, int] | None = None,
    bg_color: tuple[int, int, int] | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    reverse: bool = False,
    dim: bool = False,
    link: Hyperlink | None = None,
) -> Cell:
    """Return a shared, immutable ``Cell`` for a ``(char, style)`` combination.

    The cell-painting hot path (``PaintContext.write_text`` / ``write_cell``)
    used to allocate a fresh ``Cell`` for every glyph on every frame, which
    profiling showed dominated per-render cost once the buffer-allocation and
    diff costs were removed (~407k ``Cell.__post_init__`` calls over 400 renders
    on a 40-row view). Interning collapses repeated ``(char, style)`` pairs onto
    one object, so re-painting the same text costs a cache lookup instead of an
    allocation.

    It also speeds the diff: because an unchanged glyph resolves to the *same*
    object frame-over-frame, ``Cell.__eq__``'s identity short-circuit
    (``self is other``) settles it without comparing any field - the biggest win
    on the full-repaint path, where the old and new buffers are painted
    independently rather than copied.

    Sharing is safe for exactly the reason the shared blank cell is (see
    ``screen_buffer._BLANK_CELL``): cells are treated as immutable - painting
    replaces a buffer slot, never mutates a cell in place - and the one site
    that does mutate (overlay dimming in ``Renderer.composite_overlays``) copies
    first. The cache is bounded (LRU) so an app that paints an unbounded variety
    of styled glyphs (e.g. a truecolor image as text) cannot grow it without
    limit; eviction only turns a later hit back into an allocation.

    Parameters
    ----------
    char : str
        The glyph (or continuation/empty string) for the cell.
    fg_color, bg_color : tuple of (int, int, int) or None, optional
        Foreground / background RGB, or None for the terminal default.
    bold, italic, underline, reverse, dim : bool, optional
        Text attributes.
    link : Hyperlink or None, optional
        OSC 8 hyperlink the cell belongs to.

    Returns
    -------
    Cell
        A shared cell; callers must not mutate it (copy first if needed).
    """
    return Cell(
        char,
        fg_color=fg_color,
        bg_color=bg_color,
        bold=bold,
        italic=italic,
        underline=underline,
        reverse=reverse,
        dim=dim,
        link=link,
    )


class CellPool:
    """Pool of pre-allocated common Cell objects for performance.

    This class provides a cache of commonly-used cells to reduce allocations
    during rendering. Cells like spaces, border characters, etc. are created
    once and reused across frames.

    Notes
    -----
    This is a performance optimization that reduces GC pressure and allocation
    overhead in hot rendering paths. The pool is lazily initialized and uses
    a dictionary for O(1) lookups.

    Examples
    --------
    Get a space cell:

    >>> pool = CellPool()
    >>> space = pool.get_space()
    >>> space.char
    ' '

    Get a styled border cell:

    >>> border = pool.get_border_char('─', fg_color=(100, 100, 100))
    >>> border.char
    '─'
    """

    def __init__(self) -> None:
        """Initialize the cell pool with common cells."""
        # Cache for common cells
        self._cache: dict[tuple[Any, ...], Cell] = {}

        # Pre-create most common cells
        self._space = Cell(" ")
        self._cache[(" ", None, None, False, False, False, False, False)] = self._space

    def get_space(
        self,
        fg_color: tuple[int, int, int] | None = None,
        bg_color: tuple[int, int, int] | None = None,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        reverse: bool = False,
        dim: bool = False,
    ) -> Cell:
        """Get a space cell with optional styling.

        Parameters
        ----------
        fg_color : tuple of (int, int, int) or None, optional
            Foreground color
        bg_color : tuple of (int, int, int) or None, optional
            Background color
        bold : bool, optional
            Bold attribute
        italic : bool, optional
            Italic attribute
        underline : bool, optional
            Underline attribute
        reverse : bool, optional
            Reverse attribute
        dim : bool, optional
            Dim attribute

        Returns
        -------
        Cell
            Cached or new space cell
        """
        # Fast path for unstyled space (most common)
        if not any([fg_color, bg_color, bold, italic, underline, reverse, dim]):
            return self._space

        # Check cache
        key = (" ", fg_color, bg_color, bold, italic, underline, reverse, dim)
        if key in self._cache:
            return self._cache[key]

        # Create and cache
        cell = Cell(
            " ",
            fg_color=fg_color,
            bg_color=bg_color,
            bold=bold,
            italic=italic,
            underline=underline,
            reverse=reverse,
            dim=dim,
        )
        self._cache[key] = cell
        return cell

    def get_char(
        self,
        char: str,
        fg_color: tuple[int, int, int] | None = None,
        bg_color: tuple[int, int, int] | None = None,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        reverse: bool = False,
        dim: bool = False,
    ) -> Cell:
        """Get a cell with a specific character and optional styling.

        This method pools frequently-used characters like border chars.

        Parameters
        ----------
        char : str
            Character to display
        fg_color : tuple of (int, int, int) or None, optional
            Foreground color
        bg_color : tuple of (int, int, int) or None, optional
            Background color
        bold : bool, optional
            Bold attribute
        italic : bool, optional
            Italic attribute
        underline : bool, optional
            Underline attribute
        reverse : bool, optional
            Reverse attribute
        dim : bool, optional
            Dim attribute

        Returns
        -------
        Cell
            Cached or new cell

        Notes
        -----
        This is most effective for border characters and other frequently
        repeated glyphs. For unique characters, creating cells directly
        may be more efficient.
        """
        # Check cache
        key = (char, fg_color, bg_color, bold, italic, underline, reverse, dim)
        if key in self._cache:
            return self._cache[key]

        # Create and cache
        cell = Cell(
            char,
            fg_color=fg_color,
            bg_color=bg_color,
            bold=bold,
            italic=italic,
            underline=underline,
            reverse=reverse,
            dim=dim,
        )
        self._cache[key] = cell
        return cell

    def clear(self) -> None:
        """Clear the cache (for testing or memory management).

        Notes
        -----
        Preserves the common space cell. Useful for tests or if the cache
        grows too large in long-running applications.
        """
        self._cache.clear()
        self._cache[(" ", None, None, False, False, False, False, False)] = self._space


# Global cell pool instance for convenience
_global_pool = CellPool()


def get_pooled_cell(
    char: str,
    fg_color: tuple[int, int, int] | None = None,
    bg_color: tuple[int, int, int] | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    reverse: bool = False,
    dim: bool = False,
) -> Cell:
    """Get a cell from the global pool.

    Convenience function for accessing the global cell pool.

    Parameters
    ----------
    char : str
        Character to display
    fg_color : tuple of (int, int, int) or None, optional
        Foreground color
    bg_color : tuple of (int, int, int) or None, optional
        Background color
    bold : bool, optional
        Bold attribute
    italic : bool, optional
        Italic attribute
    underline : bool, optional
        Underline attribute
    reverse : bool, optional
        Reverse attribute
    dim : bool, optional
        Dim attribute

    Returns
    -------
    Cell
        Cached or new cell

    Examples
    --------
    >>> space = get_pooled_cell(' ')
    >>> border = get_pooled_cell('─', fg_color=(100, 100, 100))
    """
    return _global_pool.get_char(
        char, fg_color, bg_color, bold, italic, underline, reverse, dim
    )
