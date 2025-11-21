"""CSS Parser for Wijjit.

This module provides CSS parsing functionality to load styles from CSS files
and convert them to Wijjit Style objects using the tinycss2 library.
"""

from __future__ import annotations

import re
from typing import Any

import tinycss2

from wijjit.styling.style import Style


class CSSParser:
    """Parse CSS files and convert to Wijjit Style objects using tinycss2.

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
    """

    # CSS property to Wijjit Style attribute mapping
    PROPERTY_MAP = {
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

    def __init__(self):
        """Initialize CSS parser with tinycss2."""
        pass  # tinycss2 uses module-level functions, no parser instance needed

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
        with open(filepath, encoding="utf-8") as f:
            css_content = f.read()
        return self.parse(css_content)

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
        styles: dict[str, Style] = {}

        # Parse CSS using tinycss2
        rules = tinycss2.parse_stylesheet(css_content)

        # Process each rule
        for rule in rules:
            # Only process qualified rules (style rules with selectors)
            if not isinstance(rule, tinycss2.ast.QualifiedRule):
                continue

            # Get selector text from prelude tokens
            selector = self._serialize_tokens(rule.prelude).strip()

            # Parse declarations from rule content
            declarations = tinycss2.parse_declaration_list(rule.content)
            style_attrs = self._parse_declarations(declarations)

            # Create Style object
            if style_attrs:
                style = Style(**style_attrs)
                styles[selector] = style

        return styles

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
        return tinycss2.serialize(tokens)

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
        style_attrs: dict[str, Any] = {}

        for item in declarations:
            # Only process Declaration objects (skip comments, etc.)
            if not isinstance(item, tinycss2.ast.Declaration):
                continue

            prop = item.name.lower()
            value_tokens = item.value

            # Map CSS property to Style attribute
            if prop in self.PROPERTY_MAP:
                attr_name = self.PROPERTY_MAP[prop]

                # Get value as string
                value_str = self._serialize_tokens(value_tokens).strip()

                # Special handling for different property types
                if prop in (
                    "color",
                    "foreground-color",
                    "fg-color",
                    "background-color",
                    "bg-color",
                ):
                    # Color value
                    color = self._parse_color_tokens(value_tokens)
                    if color:
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
        # Convert tokens to string for parsing
        value_str = self._serialize_tokens(tokens).strip()
        return self._parse_color(value_str)

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
        value = value.strip().lower()

        # RGB format: rgb(r, g, b)
        rgb_match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", value)
        if rgb_match:
            r, g, b = rgb_match.groups()
            return (int(r), int(g), int(b))

        # Hex format: #RRGGBB or #RGB
        if value.startswith("#"):
            hex_value = value[1:]
            if len(hex_value) == 6:
                # #RRGGBB
                r = int(hex_value[0:2], 16)
                g = int(hex_value[2:4], 16)
                b = int(hex_value[4:6], 16)
                return (r, g, b)
            elif len(hex_value) == 3:
                # #RGB -> #RRGGBB
                r = int(hex_value[0] * 2, 16)
                g = int(hex_value[1] * 2, 16)
                b = int(hex_value[2] * 2, 16)
                return (r, g, b)

        # Named colors (basic set)
        named_colors = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
            "gray": (128, 128, 128),
            "grey": (128, 128, 128),
            "orange": (255, 165, 0),
            "purple": (128, 0, 128),
            "pink": (255, 192, 203),
            "brown": (165, 42, 42),
            "lime": (0, 255, 0),
            "navy": (0, 0, 128),
            "teal": (0, 128, 128),
            "silver": (192, 192, 192),
        }

        return named_colors.get(value)


def load_css_theme(filepath: str, name: str = "custom") -> dict[str, Style]:
    """Load styles from a CSS file.

    This is a convenience function that creates a CSSParser and parses the file.

    Parameters
    ----------
    filepath : str
        Path to CSS file
    name : str, optional
        Theme name (default: "custom")

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
    parser = CSSParser()
    return parser.parse_file(filepath)
