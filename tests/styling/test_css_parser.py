"""Tests for CSS parser functionality.

This module tests the CSSParser class that converts CSS files to Wijjit Style objects
using the tinycss library.
"""

import os
import tempfile

from wijjit.styling.css_parser import CSSParser, load_css_theme


class TestCSSParser:
    """Tests for CSSParser class."""

    def setup_method(self):
        """Set up test fixtures.

        Creates a CSSParser instance for testing.
        """
        self.parser = CSSParser()

    def test_parse_empty_css(self):
        """Test parsing empty CSS content.

        Verifies that parsing empty CSS returns an empty dictionary.
        """
        css = ""
        styles = self.parser.parse(css)
        assert styles == {}

    def test_parse_single_class_selector(self):
        """Test parsing a single class selector.

        Verifies that class selectors are parsed correctly with a leading dot.
        """
        css = """
        .btn-primary {
            color: rgb(255, 255, 255);
            background-color: rgb(0, 120, 212);
        }
        """
        styles = self.parser.parse(css)

        assert ".btn-primary" in styles
        style = styles[".btn-primary"]
        assert style.fg_color == (255, 255, 255)
        assert style.bg_color == (0, 120, 212)

    def test_parse_element_selector(self):
        """Test parsing element type selector.

        Verifies that element selectors (without dots) are parsed correctly.
        """
        css = """
        button {
            color: white;
            background-color: blue;
        }
        """
        styles = self.parser.parse(css)

        assert "button" in styles
        style = styles["button"]
        assert style.fg_color == (255, 255, 255)  # white
        assert style.bg_color == (0, 0, 255)  # blue

    def test_parse_pseudo_class_selector(self):
        """Test parsing pseudo-class selectors.

        Verifies that pseudo-class selectors like :hover are parsed correctly.
        """
        css = """
        .btn-primary:hover {
            background-color: rgb(0, 140, 232);
        }
        """
        styles = self.parser.parse(css)

        assert ".btn-primary:hover" in styles
        style = styles[".btn-primary:hover"]
        assert style.bg_color == (0, 140, 232)

    def test_parse_multiple_selectors(self):
        """Test parsing multiple CSS rules.

        Verifies that multiple selectors in a single CSS string are all parsed.
        """
        css = """
        .text-bold {
            font-weight: bold;
        }

        .text-italic {
            font-style: italic;
        }

        .text-underline {
            text-decoration: underline;
        }
        """
        styles = self.parser.parse(css)

        assert len(styles) == 3
        assert styles[".text-bold"].bold is True
        assert styles[".text-italic"].italic is True
        assert styles[".text-underline"].underline is True


class TestColorParsing:
    """Tests for CSS color parsing."""

    def setup_method(self):
        """Set up test fixtures.

        Creates a CSSParser instance for testing.
        """
        self.parser = CSSParser()

    def test_parse_rgb_color(self):
        """Test parsing RGB color values.

        Verifies that rgb(r, g, b) format is parsed correctly.
        """
        css = """
        .test {
            color: rgb(255, 128, 64);
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (255, 128, 64)

    def test_parse_hex_color_6_digit(self):
        """Test parsing 6-digit hex colors.

        Verifies that #RRGGBB format is parsed correctly.
        """
        css = """
        .test {
            color: #FF8040;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (255, 128, 64)

    def test_parse_hex_color_3_digit(self):
        """Test parsing 3-digit hex colors.

        Verifies that #RGB format is expanded to #RRGGBB correctly.
        """
        css = """
        .test {
            color: #F84;
        }
        """
        styles = self.parser.parse(css)
        # #F84 -> #FF8844
        assert styles[".test"].fg_color == (255, 136, 68)

    def test_parse_named_color_white(self):
        """Test parsing named color 'white'.

        Verifies that CSS named color 'white' is parsed correctly.
        """
        css = """
        .test {
            color: white;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (255, 255, 255)

    def test_parse_named_color_black(self):
        """Test parsing named color 'black'.

        Verifies that CSS named color 'black' is parsed correctly.
        """
        css = """
        .test {
            color: black;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (0, 0, 0)

    def test_parse_named_color_red(self):
        """Test parsing named color 'red'.

        Verifies that CSS named color 'red' is parsed correctly.
        """
        css = """
        .test {
            color: red;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (255, 0, 0)

    def test_parse_named_color_gray(self):
        """Test parsing named color 'gray'.

        Verifies that CSS named color 'gray' is parsed correctly.
        """
        css = """
        .test {
            color: gray;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (128, 128, 128)

    def test_parse_background_color(self):
        """Test parsing background-color property.

        Verifies that background-color maps to bg_color attribute.
        """
        css = """
        .test {
            background-color: rgb(50, 100, 150);
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].bg_color == (50, 100, 150)


class TestPropertyMapping:
    """Tests for CSS property to Style attribute mapping."""

    def setup_method(self):
        """Set up test fixtures.

        Creates a CSSParser instance for testing.
        """
        self.parser = CSSParser()

    def test_font_weight_bold(self):
        """Test mapping font-weight: bold to bold attribute.

        Verifies that font-weight: bold sets bold=True.
        """
        css = """
        .test {
            font-weight: bold;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].bold is True

    def test_font_weight_600(self):
        """Test mapping font-weight: 600 to bold attribute.

        Verifies that numeric font-weight >= 600 sets bold=True.
        """
        css = """
        .test {
            font-weight: 600;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].bold is True

    def test_font_weight_700(self):
        """Test mapping font-weight: 700 to bold attribute.

        Verifies that numeric font-weight 700 sets bold=True.
        """
        css = """
        .test {
            font-weight: 700;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].bold is True

    def test_font_weight_normal(self):
        """Test that font-weight: normal does not set bold.

        Verifies that font-weight: normal doesn't create a style entry
        since it doesn't set any attributes.
        """
        css = """
        .test {
            font-weight: normal;
        }
        """
        styles = self.parser.parse(css)
        # Empty rules don't create style entries
        assert ".test" not in styles

    def test_font_style_italic(self):
        """Test mapping font-style: italic to italic attribute.

        Verifies that font-style: italic sets italic=True.
        """
        css = """
        .test {
            font-style: italic;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].italic is True

    def test_text_decoration_underline(self):
        """Test mapping text-decoration: underline to underline attribute.

        Verifies that text-decoration: underline sets underline=True.
        """
        css = """
        .test {
            text-decoration: underline;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].underline is True

    def test_opacity_dim(self):
        """Test mapping opacity < 1 to dim attribute.

        Verifies that opacity values less than 1.0 set dim=True.
        """
        css = """
        .test {
            opacity: 0.5;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].dim is True

    def test_opacity_full(self):
        """Test that opacity: 1 does not set dim.

        Verifies that opacity of 1.0 doesn't create a style entry
        since it doesn't set any attributes.
        """
        css = """
        .test {
            opacity: 1.0;
        }
        """
        styles = self.parser.parse(css)
        # Empty rules don't create style entries
        assert ".test" not in styles

    def test_filter_invert(self):
        """Test mapping filter: invert to reverse attribute.

        Verifies that filter: invert sets reverse=True.
        """
        css = """
        .test {
            filter: invert;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].reverse is True

    def test_multiple_properties(self):
        """Test parsing multiple properties in one rule.

        Verifies that multiple properties are all parsed correctly.
        """
        css = """
        .test {
            color: white;
            background-color: blue;
            font-weight: bold;
            font-style: italic;
            text-decoration: underline;
        }
        """
        styles = self.parser.parse(css)
        style = styles[".test"]
        assert style.fg_color == (255, 255, 255)
        assert style.bg_color == (0, 0, 255)
        assert style.bold is True
        assert style.italic is True
        assert style.underline is True


class TestAlternativePropertyNames:
    """Tests for alternative CSS property names."""

    def setup_method(self):
        """Set up test fixtures.

        Creates a CSSParser instance for testing.
        """
        self.parser = CSSParser()

    def test_foreground_color(self):
        """Test foreground-color as alias for color.

        Verifies that foreground-color maps to fg_color.
        """
        css = """
        .test {
            foreground-color: red;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (255, 0, 0)

    def test_fg_color(self):
        """Test fg-color as alias for color.

        Verifies that fg-color maps to fg_color.
        """
        css = """
        .test {
            fg-color: red;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].fg_color == (255, 0, 0)

    def test_bg_color(self):
        """Test bg-color as alias for background-color.

        Verifies that bg-color maps to bg_color.
        """
        css = """
        .test {
            bg-color: blue;
        }
        """
        styles = self.parser.parse(css)
        assert styles[".test"].bg_color == (0, 0, 255)


class TestFileLoading:
    """Tests for loading CSS from files."""

    def test_parse_file(self):
        """Test parsing CSS from a file.

        Verifies that parse_file() correctly reads and parses a CSS file.
        """
        parser = CSSParser()

        # Create a temporary CSS file
        css_content = """
        .btn-primary {
            color: white;
            background-color: rgb(0, 120, 212);
            font-weight: bold;
        }

        .text-bold {
            font-weight: bold;
        }
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False, encoding="utf-8"
        ) as f:
            f.write(css_content)
            temp_path = f.name

        try:
            styles = parser.parse_file(temp_path)

            assert len(styles) == 2
            assert ".btn-primary" in styles
            assert ".text-bold" in styles

            btn_style = styles[".btn-primary"]
            assert btn_style.fg_color == (255, 255, 255)
            assert btn_style.bg_color == (0, 120, 212)
            assert btn_style.bold is True

            text_style = styles[".text-bold"]
            assert text_style.bold is True
        finally:
            # Clean up temp file
            os.unlink(temp_path)

    def test_load_css_theme(self):
        """Test load_css_theme convenience function.

        Verifies that load_css_theme() correctly loads styles from a CSS file.
        """
        css_content = """
        .btn-primary {
            color: white;
            background-color: blue;
        }
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False, encoding="utf-8"
        ) as f:
            f.write(css_content)
            temp_path = f.name

        try:
            styles = load_css_theme(temp_path)

            assert ".btn-primary" in styles
            assert styles[".btn-primary"].fg_color == (255, 255, 255)
            assert styles[".btn-primary"].bg_color == (0, 0, 255)
        finally:
            # Clean up temp file
            os.unlink(temp_path)


class TestComplexCSS:
    """Tests for complex CSS scenarios."""

    def setup_method(self):
        """Set up test fixtures.

        Creates a CSSParser instance for testing.
        """
        self.parser = CSSParser()

    def test_css_comments(self):
        """Test that CSS comments are ignored.

        Verifies that /* ... */ comments don't affect parsing.
        """
        css = """
        /* This is a comment */
        .test {
            color: red; /* inline comment */
            background-color: blue;
        }
        /* Another comment */
        """
        styles = self.parser.parse(css)

        assert ".test" in styles
        assert styles[".test"].fg_color == (255, 0, 0)
        assert styles[".test"].bg_color == (0, 0, 255)

    def test_multiple_pseudo_classes(self):
        """Test parsing multiple pseudo-class variants.

        Verifies that different pseudo-classes for the same base selector
        create separate style entries.
        """
        css = """
        .btn {
            color: white;
        }

        .btn:hover {
            background-color: rgb(100, 100, 100);
        }

        .btn:focus {
            background-color: rgb(150, 150, 150);
        }
        """
        styles = self.parser.parse(css)

        assert ".btn" in styles
        assert ".btn:hover" in styles
        assert ".btn:focus" in styles

        assert styles[".btn"].fg_color == (255, 255, 255)
        assert styles[".btn:hover"].bg_color == (100, 100, 100)
        assert styles[".btn:focus"].bg_color == (150, 150, 150)

    def test_combined_element_and_class_selectors(self):
        """Test parsing both element and class selectors.

        Verifies that element selectors and class selectors can coexist
        in the same CSS.
        """
        css = """
        button {
            color: white;
        }

        .btn-primary {
            background-color: blue;
        }

        button:focus {
            font-weight: bold;
        }
        """
        styles = self.parser.parse(css)

        assert "button" in styles
        assert ".btn-primary" in styles
        assert "button:focus" in styles

        assert styles["button"].fg_color == (255, 255, 255)
        assert styles[".btn-primary"].bg_color == (0, 0, 255)
        assert styles["button:focus"].bold is True

    def test_whitespace_handling(self):
        """Test that whitespace in CSS is handled correctly.

        Verifies that extra whitespace doesn't affect parsing.
        """
        css = """
        .test    {
            color   :   rgb(  255  ,  128  ,  64  )  ;
            background-color:rgb(0,0,0);
        }
        """
        styles = self.parser.parse(css)

        assert ".test" in styles
        assert styles[".test"].fg_color == (255, 128, 64)
        assert styles[".test"].bg_color == (0, 0, 0)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures.

        Creates a CSSParser instance for testing.
        """
        self.parser = CSSParser()

    def test_invalid_color_ignored(self):
        """Test that invalid color values are ignored.

        Verifies that unparseable color values don't create style attributes.
        """
        css = """
        .test {
            color: notacolor;
        }
        """
        styles = self.parser.parse(css)

        # The rule should exist but with no fg_color
        if ".test" in styles:
            assert styles[".test"].fg_color is None

    def test_empty_rule(self):
        """Test that empty rules don't create entries.

        Verifies that rules with no declarations aren't added to styles dict.
        """
        css = """
        .test {
        }
        """
        styles = self.parser.parse(css)

        # Empty rule should not create an entry
        assert ".test" not in styles

    def test_unknown_property_ignored(self):
        """Test that unknown CSS properties are ignored.

        Verifies that properties not in PROPERTY_MAP are safely ignored.
        """
        css = """
        .test {
            color: red;
            unknown-property: value;
            background-color: blue;
        }
        """
        styles = self.parser.parse(css)

        assert ".test" in styles
        # Known properties should be parsed
        assert styles[".test"].fg_color == (255, 0, 0)
        assert styles[".test"].bg_color == (0, 0, 255)
