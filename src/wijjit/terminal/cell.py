"""Cell-based terminal buffer for efficient rendering.

This module provides the core data structures for cell-based terminal rendering,
which enables efficient diff rendering, styling, and dirty region tracking.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Cell:
    """A single terminal cell with character and styling attributes.

    This represents one character position in the terminal with associated
    colors and text attributes. Forms the foundation of the cell-based
    rendering system.

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

    Notes
    -----
    RGB color values should be in the range 0-255. The terminal emulator
    will handle conversion to its native color format.

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
        This efficient comparison is critical for diff rendering performance,
        as it's called for every cell during buffer comparison.
        """
        if not isinstance(other, Cell):
            return False

        return (
            self.char == other.char
            and self.fg_color == other.fg_color
            and self.bg_color == other.bg_color
            and self.bold == other.bold
            and self.italic == other.italic
            and self.underline == other.underline
            and self.reverse == other.reverse
            and self.dim == other.dim
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

        Examples
        --------
        >>> cell = Cell('A', fg_color=(255, 0, 0), bold=True)
        >>> ansi = cell.to_ansi()
        >>> '\\x1b[' in ansi  # Contains ANSI codes
        True
        """
        codes = []

        # Text attributes
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

        # Foreground color (true color RGB)
        if self.fg_color is not None:
            r, g, b = self.fg_color
            codes.append(f"38;2;{r};{g};{b}")

        # Background color (true color RGB)
        if self.bg_color is not None:
            r, g, b = self.bg_color
            codes.append(f"48;2;{r};{g};{b}")

        # Build ANSI sequence
        if codes:
            ansi_codes = ";".join(codes)
            return f"\x1b[{ansi_codes}m{self.char}\x1b[0m"

        return self.char

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

        Examples
        --------
        >>> cell = Cell('A', fg_color=(255, 0, 0), bold=True)
        >>> codes = cell.get_style_codes()
        >>> codes
        '\\x1b[1;38;2;255;0;0m'
        """
        codes = []

        # Text attributes
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

        # Foreground color (true color RGB)
        if self.fg_color is not None:
            r, g, b = self.fg_color
            codes.append(f"38;2;{r};{g};{b}")

        # Background color (true color RGB)
        if self.bg_color is not None:
            r, g, b = self.bg_color
            codes.append(f"48;2;{r};{g};{b}")

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
        self._cache: dict[tuple, Cell] = {}

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
