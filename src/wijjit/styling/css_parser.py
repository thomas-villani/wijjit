"""CSS Parser for Wijjit.

This module provides CSS parsing functionality to load styles from CSS files
and convert them to Wijjit Style objects using the tinycss2 library.

The module provides both function-based API (recommended) and a class-based API
(for backwards compatibility).

Module Functions
----------------
parse_css : Parse CSS content string to Style dictionary
parse_css_file : Parse CSS file to Style dictionary
load_css_theme : Convenience function for loading CSS themes

Classes
-------
CSSParser : Backwards-compatible class wrapper around module functions
"""

from __future__ import annotations

from typing import Any

import tinycss2

from wijjit.styling.style import Style, parse_color

# CSS property to Wijjit Style attribute mapping
CSS_PROPERTY_MAP: dict[str, str] = {
    "color": "fg_color",
    "foreground-color": "fg_color",
    "fg-color": "fg_color",
    "background-color": "bg_color",
    "bg-color": "bg_color",
    "font-weight": "bold",
    "font-style": "italic",
    "text-decoration": "underline",
    "opacity": "dim",
    "filter": "reverse",
}


def _serialize_tokens(tokens: list) -> str:
    """Serialize tinycss2 tokens to CSS string.

    Parameters
    ----------
    tokens : list
        List of tinycss2 tokens

    Returns
    -------
    str
        Serialized CSS string
    """
    return tinycss2.serialize(tokens)


def _parse_color_tokens(tokens: list) -> tuple[int, int, int] | None:
    """Parse tinycss2 color tokens to RGB tuple.

    Parameters
    ----------
    tokens : list
        List of tinycss2 tokens representing color value

    Returns
    -------
    tuple of (int, int, int) or None
        RGB color tuple, or None if parsing fails

    Notes
    -----
    Supports:
    - rgb(r, g, b) function
    - #RRGGBB hex format
    - Named colors (basic set)
    """
    value_str = _serialize_tokens(tokens).strip()
    return parse_color(value_str)


def _parse_declarations(declarations: list) -> dict[str, Any]:
    """Parse CSS declarations and convert to Style attributes.

    Parameters
    ----------
    declarations : list
        List of tinycss2 Declaration objects

    Returns
    -------
    dict
        Dictionary of Style attributes

    Notes
    -----
    Handles various CSS property formats and converts them to
    Wijjit Style attributes.
    """
    style_attrs: dict[str, Any] = {}

    for item in declarations:
        # Only process Declaration objects (skip comments, etc.)
        if not isinstance(item, tinycss2.ast.Declaration):
            continue

        prop = item.name.lower()
        value_tokens = item.value

        # Map CSS property to Style attribute
        if prop in CSS_PROPERTY_MAP:
            # Get value as string
            value_str = _serialize_tokens(value_tokens).strip()

            # Special handling for different property types
            if prop in (
                "color",
                "foreground-color",
                "fg-color",
                "background-color",
                "bg-color",
            ):
                # Color value
                color = _parse_color_tokens(value_tokens)
                if color:
                    attr_name = CSS_PROPERTY_MAP[prop]
                    style_attrs[attr_name] = color

            elif prop == "font-weight":
                # Bold if "bold" or weight >= 600
                if value_str.lower() == "bold" or (
                    value_str.isdigit() and int(value_str) >= 600
                ):
                    style_attrs["bold"] = True

            elif prop == "font-style":
                # Italic
                if value_str.lower() == "italic":
                    style_attrs["italic"] = True

            elif prop == "text-decoration":
                # Underline
                if "underline" in value_str.lower():
                    style_attrs["underline"] = True

            elif prop == "opacity":
                # Dim if opacity < 1
                try:
                    opacity = float(value_str)
                    if opacity < 1.0:
                        style_attrs["dim"] = True
                except ValueError:
                    pass

            elif prop == "filter":
                # Reverse if "invert"
                if "invert" in value_str.lower():
                    style_attrs["reverse"] = True

    return style_attrs


def parse_css(css_content: str) -> dict[str, Style]:
    """Parse CSS content and return styles dictionary.

    This is the primary function for parsing CSS content into Wijjit Style objects.

    Parameters
    ----------
    css_content : str
        CSS content as string

    Returns
    -------
    dict of str to Style
        Dictionary mapping selectors to Style objects

    Notes
    -----
    Uses tinycss2 to parse CSS. The parser handles:
    - Single and multi-line comments (/* ... */)
    - Multiple selectors per rule (comma-separated)
    - RGB color values: rgb(r, g, b)
    - Hex color values: #RRGGBB
    - Named colors: white, black, red, etc.

    Examples
    --------
    >>> css = ".btn { color: white; background-color: blue; }"
    >>> styles = parse_css(css)
    >>> styles[".btn"].fg_color
    (255, 255, 255)
    """
    styles: dict[str, Style] = {}

    # Parse CSS using tinycss2
    rules = tinycss2.parse_stylesheet(css_content)

    # Process each rule
    for rule in rules:
        # Only process qualified rules (style rules with selectors)
        if not isinstance(rule, tinycss2.ast.QualifiedRule):
            continue

        # Get selector text from prelude tokens
        selector = _serialize_tokens(rule.prelude).strip()

        # Parse declarations from rule content
        declarations = tinycss2.parse_declaration_list(rule.content)
        style_attrs = _parse_declarations(declarations)

        # Create Style object
        if style_attrs:
            style = Style(**style_attrs)
            styles[selector] = style

    return styles


def parse_css_file(filepath: str) -> dict[str, Style]:
    """Parse a CSS file and return styles dictionary.

    Parameters
    ----------
    filepath : str
        Path to CSS file

    Returns
    -------
    dict of str to Style
        Dictionary mapping selectors to Style objects

    Examples
    --------
    >>> styles = parse_css_file("my_theme.css")
    >>> styles[".btn-primary"].bold
    True
    """
    with open(filepath, encoding="utf-8") as f:
        css_content = f.read()
    return parse_css(css_content)


def load_css_theme(filepath: str, name: str = "custom") -> dict[str, Style]:
    """Load styles from a CSS file.

    This is a convenience function for loading CSS themes.

    Parameters
    ----------
    filepath : str
        Path to CSS file
    name : str, optional
        Theme name (default: "custom"). Currently unused but kept for
        API compatibility.

    Returns
    -------
    dict of str to Style
        Dictionary mapping selectors to Style objects

    Examples
    --------
    >>> styles = load_css_theme("my_theme.css")
    >>> # Use with Theme
    >>> from wijjit.styling.theme import Theme
    >>> theme = Theme("my_theme", styles)
    """
    return parse_css_file(filepath)


class CSSParser:
    """Parse CSS files and convert to Wijjit Style objects using tinycss2.

    This class provides a backwards-compatible object-oriented interface
    to the module-level parsing functions. For new code, consider using
    the module functions directly: `parse_css()` and `parse_css_file()`.

    This parser supports a subset of CSS syntax relevant to terminal styling:
    - Class selectors (.btn-primary)
    - Pseudo-class selectors (.btn-primary:hover)
    - Element type selectors (button, input)
    - Combined selectors (button:focus)

    Supported CSS properties:
    - color / foreground-color -> fg_color
    - background-color -> bg_color
    - font-weight: bold -> bold
    - font-style: italic -> italic
    - text-decoration: underline -> underline
    - opacity (for dim effect) -> dim
    - filter: invert -> reverse

    Examples
    --------
    Parse a CSS file:

    >>> parser = CSSParser()
    >>> styles = parser.parse_file("theme.css")
    >>> # styles = {'.btn-primary': Style(...), ...}

    Parse CSS string:

    >>> css = '''
    ... .btn-primary {
    ...     color: rgb(255, 255, 255);
    ...     background-color: rgb(0, 120, 212);
    ...     font-weight: bold;
    ... }
    ... '''
    >>> styles = parser.parse(css)

    Or use module functions directly (recommended):

    >>> from wijjit.styling.css_parser import parse_css, parse_css_file
    >>> styles = parse_css(".btn { color: white; }")
    >>> styles = parse_css_file("theme.css")
    """

    # Class-level constant for backwards compatibility
    PROPERTY_MAP = CSS_PROPERTY_MAP

    def __init__(self):
        """Initialize CSS parser.

        The CSSParser class is stateless and delegates to module-level
        functions. This constructor exists for API compatibility.
        """
        pass

    def parse_file(self, filepath: str) -> dict[str, Style]:
        """Parse a CSS file and return styles dictionary.

        Parameters
        ----------
        filepath : str
            Path to CSS file

        Returns
        -------
        dict of str to Style
            Dictionary mapping selectors to Style objects

        Examples
        --------
        >>> parser = CSSParser()
        >>> styles = parser.parse_file("my_theme.css")
        """
        return parse_css_file(filepath)

    def parse(self, css_content: str) -> dict[str, Style]:
        """Parse CSS content and return styles dictionary.

        Parameters
        ----------
        css_content : str
            CSS content as string

        Returns
        -------
        dict of str to Style
            Dictionary mapping selectors to Style objects

        Notes
        -----
        Uses tinycss2 to parse CSS. The parser handles:
        - Single and multi-line comments (/* ... */)
        - Multiple selectors per rule (comma-separated)
        - RGB color values: rgb(r, g, b)
        - Hex color values: #RRGGBB
        - Named colors: white, black, red, etc.

        Examples
        --------
        >>> parser = CSSParser()
        >>> css = ".btn { color: white; background-color: blue; }"
        >>> styles = parser.parse(css)
        """
        return parse_css(css_content)

    def _serialize_tokens(self, tokens: list) -> str:
        """Serialize tinycss2 tokens to CSS string.

        Parameters
        ----------
        tokens : list
            List of tinycss2 tokens

        Returns
        -------
        str
            Serialized CSS string
        """
        return _serialize_tokens(tokens)

    def _parse_declarations(self, declarations: list) -> dict[str, Any]:
        """Parse CSS declarations and convert to Style attributes.

        Parameters
        ----------
        declarations : list
            List of tinycss2 Declaration objects

        Returns
        -------
        dict
            Dictionary of Style attributes

        Notes
        -----
        Handles various CSS property formats and converts them to
        Wijjit Style attributes.
        """
        return _parse_declarations(declarations)

    def _parse_color_tokens(self, tokens: list) -> tuple[int, int, int] | None:
        """Parse tinycss2 color tokens to RGB tuple.

        Parameters
        ----------
        tokens : list
            List of tinycss2 tokens representing color value

        Returns
        -------
        tuple of (int, int, int) or None
            RGB color tuple, or None if parsing fails

        Notes
        -----
        Supports:
        - rgb(r, g, b) function
        - #RRGGBB hex format
        - Named colors (basic set)
        """
        return _parse_color_tokens(tokens)

    def _parse_color(self, value: str) -> tuple[int, int, int] | None:
        """Parse CSS color value to RGB tuple.

        Parameters
        ----------
        value : str
            CSS color value (rgb(...), #hex, or named color)

        Returns
        -------
        tuple of (int, int, int) or None
            RGB color tuple, or None if parsing fails

        Notes
        -----
        Delegates to the canonical parse_color() function in style.py.
        Supports:
        - rgb(r, g, b) format
        - #RRGGBB hex format
        - Named colors (basic set)

        Examples
        --------
        >>> parser = CSSParser()
        >>> parser._parse_color("rgb(255, 0, 0)")
        (255, 0, 0)
        >>> parser._parse_color("#FF0000")
        (255, 0, 0)
        >>> parser._parse_color("red")
        (255, 0, 0)
        """
        return parse_color(value)
