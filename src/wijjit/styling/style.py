"""CSS-like styling system for terminal UI elements.

This module provides the Style class for defining element appearance using
a CSS-like approach with colors, text attributes, and cascade/merge support.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Style:
    """CSS-like style specification for terminal UI elements.

    This class represents a complete style specification including colors
    and text attributes. Styles can be merged using CSS-like cascade rules.

    Parameters
    ----------
    fg_color : tuple of (int, int, int) or None, optional
        Foreground RGB color (0-255 each) or None for default terminal color
    bg_color : tuple of (int, int, int) or None, optional
        Background RGB color (0-255 each) or None for default terminal color
    bold : bool or None, optional
        Bold text attribute. None means unspecified (default: None)
    italic : bool or None, optional
        Italic text attribute. None means unspecified (default: None)
    underline : bool or None, optional
        Underline text attribute. None means unspecified (default: None)
    dim : bool or None, optional
        Dim/faint text attribute. None means unspecified (default: None)
    reverse : bool or None, optional
        Reverse video (swap fg/bg colors) attribute. None means unspecified (default: None)

    Attributes
    ----------
    fg_color : tuple of (int, int, int) or None
        Foreground color in RGB
    bg_color : tuple of (int, int, int) or None
        Background color in RGB
    bold : bool or None
        Bold attribute (None = unspecified)
    italic : bool or None
        Italic attribute (None = unspecified)
    underline : bool or None
        Underline attribute (None = unspecified)
    dim : bool or None
        Dim attribute (None = unspecified)
    reverse : bool or None
        Reverse video attribute (None = unspecified)

    Examples
    --------
    Create a basic style:

    >>> style = Style(fg_color=(255, 0, 0), bold=True)
    >>> style.fg_color
    (255, 0, 0)
    >>> style.bold
    True

    Merge two styles (CSS cascade):

    >>> base = Style(fg_color=(255, 0, 0), bold=True)
    >>> override = Style(fg_color=(0, 255, 0))  # New color, keeps bold
    >>> merged = base.merge(override)
    >>> merged.fg_color
    (0, 255, 0)
    >>> merged.bold
    True

    Disable attributes via merge:

    >>> base = Style(bold=True, italic=True)
    >>> override = Style(bold=False)  # Explicitly disable bold
    >>> merged = base.merge(override)
    >>> merged.bold
    False
    >>> merged.italic
    True

    Convert to Cell attributes:

    >>> style = Style(fg_color=(255, 0, 0), bold=True)
    >>> attrs = style.to_cell_attrs()
    >>> attrs['fg_color']
    (255, 0, 0)
    >>> attrs['bold']
    True
    """

    fg_color: tuple[int, int, int] | None = None
    bg_color: tuple[int, int, int] | None = None
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    dim: bool | None = None
    reverse: bool | None = None

    def merge(self, other: "Style") -> "Style":
        """Merge another style on top of this one (CSS cascade).

        Parameters
        ----------
        other : Style
            Style to overlay on top of this style

        Returns
        -------
        Style
            New style with other's non-None values overriding self's values

        Notes
        -----
        This implements CSS-like cascade behavior where properties from
        'other' override properties from 'self'. For color properties,
        None means "use default" while a color tuple overrides. For
        boolean attributes, True overrides False.

        The merge is non-destructive - both input styles remain unchanged.

        Examples
        --------
        Merge colors:

        >>> base = Style(fg_color=(255, 0, 0))
        >>> override = Style(fg_color=(0, 255, 0))
        >>> merged = base.merge(override)
        >>> merged.fg_color
        (0, 255, 0)

        Merge attributes:

        >>> base = Style(bold=True)
        >>> override = Style(italic=True)
        >>> merged = base.merge(override)
        >>> merged.bold
        True
        >>> merged.italic
        True

        Override with None preserves base:

        >>> base = Style(fg_color=(255, 0, 0))
        >>> override = Style(bg_color=(0, 0, 255))
        >>> merged = base.merge(override)
        >>> merged.fg_color
        (255, 0, 0)
        >>> merged.bg_color
        (0, 0, 255)
        """
        return Style(
            fg_color=other.fg_color if other.fg_color is not None else self.fg_color,
            bg_color=other.bg_color if other.bg_color is not None else self.bg_color,
            bold=other.bold if other.bold is not None else self.bold,
            italic=other.italic if other.italic is not None else self.italic,
            underline=(
                other.underline if other.underline is not None else self.underline
            ),
            dim=other.dim if other.dim is not None else self.dim,
            reverse=other.reverse if other.reverse is not None else self.reverse,
        )

    def to_cell_attrs(self) -> dict[str, Any]:
        """Convert style to Cell constructor attributes.

        Returns
        -------
        dict
            Dictionary of attributes suitable for Cell(**attrs)

        Notes
        -----
        This is the PRIMARY method for converting styles to cell attributes
        in the cell-based rendering system. Returns a dictionary that can
        be unpacked directly into Cell constructor.

        Examples
        --------
        Convert to cell attributes:

        >>> style = Style(fg_color=(255, 0, 0), bold=True)
        >>> attrs = style.to_cell_attrs()
        >>> attrs
        {'fg_color': (255, 0, 0), 'bg_color': None, 'bold': True, 'italic': False,
            'underline': False, 'reverse': False, 'dim': False}

        Use with Cell:

        >>> from wijjit.terminal.cell import Cell
        >>> style = Style(fg_color=(0, 255, 0))
        >>> cell = Cell('A', **style.to_cell_attrs())
        >>> cell.fg_color
        (0, 255, 0)
        """
        return {
            "fg_color": self.fg_color,
            "bg_color": self.bg_color,
            "bold": self.bold if self.bold is not None else False,
            "italic": self.italic if self.italic is not None else False,
            "underline": self.underline if self.underline is not None else False,
            "reverse": self.reverse if self.reverse is not None else False,
            "dim": self.dim if self.dim is not None else False,
        }

    def to_ansi(self) -> str:
        """Convert style to ANSI escape sequence prefix.

        Returns
        -------
        str
            ANSI escape sequence (without content or reset)

        Notes
        -----
        This method is DEPRECATED and provided only for compatibility during
        the migration from ANSI string-based rendering to cell-based rendering.

        New code should use `to_cell_attrs()` instead.

        The returned string must be followed by content and then a reset code.

        Examples
        --------
        Generate ANSI prefix:

        >>> style = Style(fg_color=(255, 0, 0), bold=True)
        >>> prefix = style.to_ansi()
        >>> '\\x1b[' in prefix
        True
        >>> text = prefix + 'Hello' + '\\x1b[0m'

        Empty style returns empty string:

        >>> style = Style()
        >>> style.to_ansi()
        ''
        """
        codes = []

        # Text attributes (treat None as False)
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
            return f"\x1b[{ansi_codes}m"

        return ""

    def __bool__(self) -> bool:
        """Check if style has any non-default properties.

        Returns
        -------
        bool
            True if any style property is set, False if default/empty

        Notes
        -----
        Useful for conditionally applying styles or checking if a style
        has any effect.

        Examples
        --------
        Empty style is falsy:

        >>> style = Style()
        >>> bool(style)
        False

        Styled is truthy:

        >>> style = Style(bold=True)
        >>> bool(style)
        True
        """
        return (
            self.fg_color is not None
            or self.bg_color is not None
            or (self.bold is not None and self.bold)
            or (self.italic is not None and self.italic)
            or (self.underline is not None and self.underline)
            or (self.dim is not None and self.dim)
            or (self.reverse is not None and self.reverse)
        )


# Predefined common styles for convenience
DEFAULT_STYLE = Style()
BOLD_STYLE = Style(bold=True)
ITALIC_STYLE = Style(italic=True)
UNDERLINE_STYLE = Style(underline=True)
DIM_STYLE = Style(dim=True)


def parse_color(color_str: str) -> tuple[int, int, int] | None:
    """Parse color string to RGB tuple.

    Parameters
    ----------
    color_str : str
        Color specification in various formats:
        - Hex: "#FF0000" or "#F00"
        - RGB: "rgb(255, 0, 0)"
        - Named: "red", "blue", etc. (basic colors only)

    Returns
    -------
    tuple of (int, int, int) or None
        RGB color tuple or None if parsing failed

    Notes
    -----
    Supports common color formats for ease of use. Named colors are limited
    to basic terminal colors for consistency.

    Examples
    --------
    Parse hex color:

    >>> parse_color("#FF0000")
    (255, 0, 0)
    >>> parse_color("#F00")
    (255, 0, 0)

    Parse RGB:

    >>> parse_color("rgb(255, 0, 0)")
    (255, 0, 0)

    Parse named color:

    >>> parse_color("red")
    (255, 0, 0)

    Invalid returns None:

    >>> parse_color("invalid")
    """
    color_str = color_str.strip().lower()

    # Hex format: #RGB or #RRGGBB
    if color_str.startswith("#"):
        hex_str = color_str[1:]
        try:
            if len(hex_str) == 3:
                # Short form: #RGB -> #RRGGBB
                r = int(hex_str[0] * 2, 16)
                g = int(hex_str[1] * 2, 16)
                b = int(hex_str[2] * 2, 16)
                return (r, g, b)
            elif len(hex_str) == 6:
                # Long form: #RRGGBB
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b)
        except ValueError:
            # Invalid hex digits
            return None

    # RGB format: rgb(R, G, B)
    if color_str.startswith("rgb(") and color_str.endswith(")"):
        rgb_str = color_str[4:-1]
        parts = [p.strip() for p in rgb_str.split(",")]
        if len(parts) == 3:
            try:
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                return (r, g, b)
            except ValueError:
                pass

    # Named colors (basic terminal colors)
    named_colors = {
        "black": (0, 0, 0),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "yellow": (255, 255, 0),
        "blue": (0, 0, 255),
        "magenta": (255, 0, 255),
        "cyan": (0, 255, 255),
        "white": (255, 255, 255),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
    }

    return named_colors.get(color_str)
