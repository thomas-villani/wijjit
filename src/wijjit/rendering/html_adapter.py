"""HTML string to Cell conversion utilities.

This module provides utilities to convert HTML-formatted strings to cell-based
representations, enabling HTML content in Wijjit elements.

Uses prompt_toolkit's HTML parser for robust HTML handling, then adapts the
output to Wijjit's Cell system with theme-based styling support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import HTML

from wijjit.terminal.cell import Cell

if TYPE_CHECKING:
    from wijjit.styling.resolver import StyleResolver


# Mapping of prompt_toolkit class names to style attributes
# Note: Cell doesn't have strikethrough, so <s>/<strike>/<del> use dim as fallback
_TAG_STYLE_MAP = {
    "b": {"bold": True},
    "strong": {"bold": True},
    "i": {"italic": True},
    "em": {"italic": True},
    "u": {"underline": True},
    "s": {"dim": True},  # Strikethrough fallback (Cell lacks strikethrough)
    "strike": {"dim": True},  # Strikethrough fallback
    "del": {"dim": True},  # Strikethrough fallback
    "dim": {"dim": True},
    "reverse": {"reverse": True},
}

# Color name to RGB mapping for prompt_toolkit color names
_COLOR_NAME_MAP = {
    # ANSI color names
    "black": (0, 0, 0),
    "red": (128, 0, 0),
    "green": (0, 128, 0),
    "yellow": (128, 128, 0),
    "blue": (0, 0, 128),
    "magenta": (128, 0, 128),
    "cyan": (0, 128, 128),
    "white": (192, 192, 192),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    # Bright ANSI colors
    "ansired": (255, 0, 0),
    "ansigreen": (0, 255, 0),
    "ansiyellow": (255, 255, 0),
    "ansiblue": (0, 0, 255),
    "ansimagenta": (255, 0, 255),
    "ansicyan": (0, 255, 255),
    "ansiwhite": (255, 255, 255),
    "ansibrightblack": (128, 128, 128),
    "ansibrightred": (255, 0, 0),
    "ansibrightgreen": (0, 255, 0),
    "ansibrightyellow": (255, 255, 0),
    "ansibrightblue": (0, 0, 255),
    "ansibrightmagenta": (255, 0, 255),
    "ansibrightcyan": (0, 255, 255),
    "ansibrightwhite": (255, 255, 255),
}


def html_string_to_cells(
    html_str: str,
    style_resolver: StyleResolver | None = None,
) -> list[Cell]:
    """Parse HTML string and convert to Cell objects.

    Parameters
    ----------
    html_str : str
        HTML-formatted string to parse. Supports:
        - Text formatting: <b>, <i>, <u>, <s>, <strong>, <em>
        - Inline styles: <style fg="color" bg="color">
        - Custom elements: <classname>text</classname> (resolves via theme)
        - CSS classes via custom elements
    style_resolver : StyleResolver, optional
        Style resolver for theme-based class styling. If provided,
        custom element names and class attributes are resolved through
        the theme's style definitions.

    Returns
    -------
    list of Cell
        List of Cell objects with appropriate styling applied.

    Notes
    -----
    Uses prompt_toolkit's HTML parser internally, which provides robust
    HTML handling including proper escaping and nested element support.

    Custom HTML elements (e.g., <danger>text</danger>) are resolved
    through the style_resolver if provided. The element name is looked
    up as a style class (e.g., '.danger' or 'danger').

    Examples
    --------
    Basic formatting:

    >>> cells = html_string_to_cells('<b>Bold</b> <i>italic</i>')
    >>> cells[0].bold
    True

    With theme styling:

    >>> from wijjit.styling.resolver import StyleResolver
    >>> from wijjit.styling.theme import DefaultTheme
    >>> resolver = StyleResolver(DefaultTheme())
    >>> cells = html_string_to_cells(
    ...     '<span class="text-danger">Error</span>',
    ...     style_resolver=resolver
    ... )

    Inline colors:

    >>> cells = html_string_to_cells(
    ...     '<style fg="red" bg="blue">Styled</style>'
    ... )
    """
    if not html_str:
        return []

    try:
        # Parse HTML using prompt_toolkit
        html_obj = HTML(html_str)
        formatted_text = html_obj.__pt_formatted_text__()
    except Exception:
        # If HTML parsing fails, treat as plain text
        return [Cell(char=c) for c in html_str]

    cells = []

    for style_str, text in formatted_text:
        # Parse the style string into attributes
        cell_attrs = _parse_style_string(style_str, style_resolver)

        # Create cells for each character with the parsed style
        for char in text:
            cells.append(Cell(char=char, **cell_attrs))

    return cells


def _parse_style_string(
    style_str: str,
    style_resolver: StyleResolver | None,
) -> dict:
    """Parse prompt_toolkit style string into Cell attributes.

    Parameters
    ----------
    style_str : str
        Style string from prompt_toolkit (e.g., 'class:b,i fg:red')
    style_resolver : StyleResolver, optional
        For resolving theme classes

    Returns
    -------
    dict
        Dictionary of Cell attributes (fg_color, bg_color, bold, etc.)
    """
    attrs: dict = {
        "fg_color": None,
        "bg_color": None,
        "bold": False,
        "italic": False,
        "underline": False,
        "reverse": False,
        "dim": False,
    }

    if not style_str:
        return attrs

    # Split style string into parts
    parts = style_str.split()

    for part in parts:
        if part.startswith("class:"):
            # Handle class-based styles (e.g., 'class:b,i' or 'class:danger')
            class_names = part[6:].split(",")  # Remove 'class:' prefix
            for class_name in class_names:
                _apply_class_style(attrs, class_name, style_resolver)

        elif part.startswith("fg:"):
            # Foreground color
            color = _parse_color(part[3:])
            if color:
                attrs["fg_color"] = color

        elif part.startswith("bg:"):
            # Background color
            color = _parse_color(part[3:])
            if color:
                attrs["bg_color"] = color

        elif part == "bold":
            attrs["bold"] = True
        elif part == "italic":
            attrs["italic"] = True
        elif part == "underline":
            attrs["underline"] = True
        elif part == "reverse":
            attrs["reverse"] = True

    return attrs


def _apply_class_style(
    attrs: dict,
    class_name: str,
    style_resolver: StyleResolver | None,
) -> None:
    """Apply styling from a class name.

    Parameters
    ----------
    attrs : dict
        Cell attributes dictionary to modify
    class_name : str
        Class name (e.g., 'b', 'i', 'danger', 'text-primary')
    style_resolver : StyleResolver, optional
        For resolving theme classes
    """
    # Check built-in tag mappings first
    if class_name in _TAG_STYLE_MAP:
        for key, value in _TAG_STYLE_MAP[class_name].items():
            attrs[key] = value
        return

    # Try to resolve through theme if resolver provided
    if style_resolver is not None:
        # Try with dot prefix for CSS classes
        style = style_resolver.resolve_style_by_class(f".{class_name}")
        if style:
            _merge_style_to_attrs(attrs, style)
            return

        # Try without dot prefix (for element styles)
        style = style_resolver.resolve_style_by_class(class_name)
        if style:
            _merge_style_to_attrs(attrs, style)


def _merge_style_to_attrs(attrs: dict, style) -> None:
    """Merge Style object properties into attrs dict.

    Parameters
    ----------
    attrs : dict
        Cell attributes dictionary to modify
    style : Style
        Style object to merge from
    """
    if style.fg_color is not None:
        attrs["fg_color"] = style.fg_color
    if style.bg_color is not None:
        attrs["bg_color"] = style.bg_color
    if style.bold:
        attrs["bold"] = True
    if style.italic:
        attrs["italic"] = True
    if style.underline:
        attrs["underline"] = True
    if style.reverse:
        attrs["reverse"] = True
    if style.dim:
        attrs["dim"] = True


def _parse_color(color_str: str) -> tuple[int, int, int] | None:
    """Parse a color string to RGB tuple.

    Parameters
    ----------
    color_str : str
        Color specification: named color, #RRGGBB, or #RGB

    Returns
    -------
    tuple of (int, int, int) or None
        RGB color tuple, or None if parsing failed
    """
    color_str = color_str.lower().strip()

    # Check named colors
    if color_str in _COLOR_NAME_MAP:
        return _COLOR_NAME_MAP[color_str]

    # Handle hex colors
    if color_str.startswith("#"):
        hex_color = color_str[1:]

        if len(hex_color) == 6:
            # #RRGGBB
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return (r, g, b)
            except ValueError:
                return None

        elif len(hex_color) == 3:
            # #RGB -> #RRGGBB
            try:
                r = int(hex_color[0] * 2, 16)
                g = int(hex_color[1] * 2, 16)
                b = int(hex_color[2] * 2, 16)
                return (r, g, b)
            except ValueError:
                return None

    return None


def strip_html_tags(html_str: str) -> str:
    """Strip HTML tags from string, returning plain text.

    Parameters
    ----------
    html_str : str
        HTML-formatted string

    Returns
    -------
    str
        Plain text with HTML tags removed

    Notes
    -----
    Uses prompt_toolkit's HTML parser to properly handle nested tags,
    entity escaping, etc.

    Examples
    --------
    >>> strip_html_tags('<b>Bold</b> and <i>italic</i>')
    'Bold and italic'
    """
    if not html_str:
        return ""

    try:
        html_obj = HTML(html_str)
        formatted_text = html_obj.__pt_formatted_text__()
        return "".join(text for _, text in formatted_text)
    except Exception:
        # If parsing fails, return original (simple fallback)
        import re

        return re.sub(r"<[^>]+>", "", html_str)


def visible_length_html(html_str: str) -> int:
    """Get visible length of HTML string (excluding tags).

    Parameters
    ----------
    html_str : str
        HTML-formatted string

    Returns
    -------
    int
        Length of visible text content

    Examples
    --------
    >>> visible_length_html('<b>Hello</b>')
    5
    """
    return len(strip_html_tags(html_str))
