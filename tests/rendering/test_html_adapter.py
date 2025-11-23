"""Tests for HTML string to Cell conversion utilities."""

from wijjit.rendering.html_adapter import (
    html_string_to_cells,
    strip_html_tags,
    visible_length_html,
)
from wijjit.styling.resolver import StyleResolver
from wijjit.styling.theme import DefaultTheme


class TestHtmlStringToCells:
    """Tests for html_string_to_cells function."""

    def test_empty_string(self):
        """Test empty string returns empty list."""
        cells = html_string_to_cells("")
        assert cells == []

    def test_plain_text(self):
        """Test plain text without HTML."""
        cells = html_string_to_cells("Hello World")
        assert len(cells) == 11
        assert cells[0].char == "H"
        assert cells[-1].char == "d"
        assert not cells[0].bold
        assert not cells[0].italic

    def test_bold_tag(self):
        """Test <b> tag applies bold styling."""
        cells = html_string_to_cells("<b>Bold</b>")
        assert len(cells) == 4
        assert cells[0].char == "B"
        assert cells[0].bold is True

    def test_strong_tag(self):
        """Test <strong> tag applies bold styling."""
        cells = html_string_to_cells("<strong>Strong</strong>")
        assert len(cells) == 6
        assert cells[0].bold is True

    def test_italic_tag(self):
        """Test <i> tag applies italic styling."""
        cells = html_string_to_cells("<i>Italic</i>")
        assert len(cells) == 6
        assert cells[0].char == "I"
        assert cells[0].italic is True

    def test_em_tag(self):
        """Test <em> tag applies italic styling."""
        cells = html_string_to_cells("<em>Emphasis</em>")
        assert len(cells) == 8
        assert cells[0].italic is True

    def test_underline_tag(self):
        """Test <u> tag applies underline styling."""
        cells = html_string_to_cells("<u>Underline</u>")
        assert len(cells) == 9
        assert cells[0].underline is True

    def test_strikethrough_tag(self):
        """Test <s> tag applies dim styling (strikethrough fallback)."""
        cells = html_string_to_cells("<s>Strike</s>")
        # Note: Cell doesn't have strikethrough, dim is used as fallback
        assert len(cells) == 6
        assert cells[0].dim is True

    def test_nested_tags(self):
        """Test nested tags combine styles."""
        cells = html_string_to_cells("<b><i>BoldItalic</i></b>")
        assert len(cells) == 10
        assert cells[0].bold is True
        assert cells[0].italic is True

    def test_mixed_styled_and_plain(self):
        """Test mixing styled and plain text."""
        cells = html_string_to_cells("<b>Bold</b> plain")
        assert len(cells) == 10
        # Bold part
        assert cells[0].bold is True
        assert cells[3].bold is True
        # Space after bold
        assert cells[4].char == " "
        # Plain part
        assert cells[5].bold is False

    def test_inline_style_fg_color(self):
        """Test inline style with foreground color."""
        cells = html_string_to_cells('<style fg="red">Red</style>')
        assert len(cells) == 3
        assert cells[0].fg_color is not None
        # Red color should be parsed
        assert cells[0].fg_color[0] > 0  # Red component

    def test_inline_style_bg_color(self):
        """Test inline style with background color."""
        cells = html_string_to_cells('<style bg="blue">Blue</style>')
        assert len(cells) == 4
        assert cells[0].bg_color is not None

    def test_hex_color(self):
        """Test hex color specification."""
        cells = html_string_to_cells('<style fg="#FF0000">Red</style>')
        assert len(cells) == 3
        assert cells[0].fg_color == (255, 0, 0)

    def test_short_hex_color(self):
        """Test short hex color (#RGB) specification."""
        cells = html_string_to_cells('<style fg="#F00">Red</style>')
        assert len(cells) == 3
        # Short hex #F00 should expand to (255, 0, 0)
        assert cells[0].fg_color == (255, 0, 0)

    def test_custom_element_as_class(self):
        """Test custom element names are treated as classes."""
        cells = html_string_to_cells("<danger>Error</danger>")
        # Without style resolver, no special styling
        assert len(cells) == 5
        assert cells[0].char == "E"

    def test_with_style_resolver(self):
        """Test theme-based styling with style resolver."""
        resolver = StyleResolver(DefaultTheme())
        cells = html_string_to_cells(
            "<text-danger>Error</text-danger>",
            style_resolver=resolver,
        )
        assert len(cells) == 5
        # .text-danger style should be applied (red color)
        assert cells[0].fg_color is not None
        # Should be red-ish
        assert cells[0].fg_color[0] > cells[0].fg_color[1]

    def test_invalid_html_returns_plain_text(self):
        """Test malformed HTML falls back to plain text."""
        # This shouldn't crash
        cells = html_string_to_cells("<b>unclosed")
        assert len(cells) > 0

    def test_newlines_preserved(self):
        """Test newlines are preserved as characters."""
        cells = html_string_to_cells("Line1\nLine2")
        # Find newline character
        newline_cells = [c for c in cells if c.char == "\n"]
        assert len(newline_cells) == 1


class TestStripHtmlTags:
    """Tests for strip_html_tags function."""

    def test_empty_string(self):
        """Test empty string."""
        assert strip_html_tags("") == ""

    def test_plain_text(self):
        """Test plain text without HTML."""
        assert strip_html_tags("Hello World") == "Hello World"

    def test_basic_tags(self):
        """Test stripping basic HTML tags."""
        assert strip_html_tags("<b>Bold</b>") == "Bold"
        assert strip_html_tags("<i>Italic</i>") == "Italic"

    def test_nested_tags(self):
        """Test stripping nested tags."""
        assert strip_html_tags("<b><i>Text</i></b>") == "Text"

    def test_mixed_content(self):
        """Test stripping tags from mixed content."""
        result = strip_html_tags("<b>Bold</b> and <i>italic</i>")
        assert result == "Bold and italic"

    def test_custom_elements(self):
        """Test stripping custom element tags."""
        assert strip_html_tags("<danger>Error</danger>") == "Error"


class TestVisibleLengthHtml:
    """Tests for visible_length_html function."""

    def test_empty_string(self):
        """Test empty string."""
        assert visible_length_html("") == 0

    def test_plain_text(self):
        """Test plain text length."""
        assert visible_length_html("Hello") == 5

    def test_with_tags(self):
        """Test length excludes HTML tags."""
        assert visible_length_html("<b>Hello</b>") == 5

    def test_nested_tags(self):
        """Test length with nested tags."""
        assert visible_length_html("<b><i>Hello</i></b>") == 5

    def test_multiple_tags(self):
        """Test length with multiple tagged sections."""
        assert visible_length_html("<b>Hello</b> <i>World</i>") == 11
