"""Tests for the Style class and color parsing."""


from wijjit.styling.style import (
    BOLD_STYLE,
    DEFAULT_STYLE,
    DIM_STYLE,
    ITALIC_STYLE,
    UNDERLINE_STYLE,
    Style,
    parse_color,
)


class TestStyleCreation:
    """Test Style object creation and initialization."""

    def test_empty_style(self):
        """Test creating an empty style with defaults.

        Returns
        -------
        None
        """
        style = Style()
        assert style.fg_color is None
        assert style.bg_color is None
        assert style.bold is False
        assert style.italic is False
        assert style.underline is False
        assert style.dim is False
        assert style.reverse is False

    def test_style_with_colors(self):
        """Test creating style with RGB colors.

        Returns
        -------
        None
        """
        style = Style(fg_color=(255, 0, 0), bg_color=(0, 0, 255))
        assert style.fg_color == (255, 0, 0)
        assert style.bg_color == (0, 0, 255)

    def test_style_with_attributes(self):
        """Test creating style with text attributes.

        Returns
        -------
        None
        """
        style = Style(bold=True, italic=True, underline=True)
        assert style.bold is True
        assert style.italic is True
        assert style.underline is True
        assert style.dim is False
        assert style.reverse is False

    def test_style_with_all_attributes(self):
        """Test creating style with all attributes set.

        Returns
        -------
        None
        """
        style = Style(
            fg_color=(128, 128, 128),
            bg_color=(64, 64, 64),
            bold=True,
            italic=True,
            underline=True,
            dim=True,
            reverse=True,
        )
        assert style.fg_color == (128, 128, 128)
        assert style.bg_color == (64, 64, 64)
        assert style.bold is True
        assert style.italic is True
        assert style.underline is True
        assert style.dim is True
        assert style.reverse is True


class TestStyleMerge:
    """Test Style.merge() CSS-like cascade behavior."""

    def test_merge_empty_styles(self):
        """Test merging two empty styles.

        Returns
        -------
        None
        """
        base = Style()
        override = Style()
        merged = base.merge(override)

        assert merged.fg_color is None
        assert merged.bg_color is None
        assert merged.bold is False

    def test_merge_colors_override(self):
        """Test that colors from override replace base colors.

        Returns
        -------
        None
        """
        base = Style(fg_color=(255, 0, 0))
        override = Style(fg_color=(0, 255, 0))
        merged = base.merge(override)

        assert merged.fg_color == (0, 255, 0)

    def test_merge_colors_preserve_base(self):
        """Test that base colors are preserved when override has None.

        Returns
        -------
        None
        """
        base = Style(fg_color=(255, 0, 0), bg_color=(0, 0, 255))
        override = Style(fg_color=(0, 255, 0))  # Only fg, no bg
        merged = base.merge(override)

        assert merged.fg_color == (0, 255, 0)  # Override
        assert merged.bg_color == (0, 0, 255)  # Preserved from base

    def test_merge_attributes_combine(self):
        """Test that boolean attributes combine via OR.

        Returns
        -------
        None
        """
        base = Style(bold=True)
        override = Style(italic=True)
        merged = base.merge(override)

        assert merged.bold is True  # From base
        assert merged.italic is True  # From override
        assert merged.underline is False  # Neither set

    def test_merge_attributes_or_behavior(self):
        """Test that attributes use OR logic (True wins).

        Returns
        -------
        None
        """
        base = Style(bold=True, italic=False)
        override = Style(bold=False, italic=True)
        merged = base.merge(override)

        assert merged.bold is True  # True OR False = True
        assert merged.italic is True  # False OR True = True

    def test_merge_complex(self):
        """Test merging complex styles with colors and attributes.

        Returns
        -------
        None
        """
        base = Style(fg_color=(255, 0, 0), bold=True, italic=True)
        override = Style(fg_color=(0, 255, 0), bg_color=(0, 0, 255), underline=True)
        merged = base.merge(override)

        assert merged.fg_color == (0, 255, 0)  # Override
        assert merged.bg_color == (0, 0, 255)  # From override
        assert merged.bold is True  # From base
        assert merged.italic is True  # From base
        assert merged.underline is True  # From override

    def test_merge_chain(self):
        """Test chaining multiple merges.

        Returns
        -------
        None
        """
        style1 = Style(fg_color=(255, 0, 0))
        style2 = Style(bg_color=(0, 255, 0))
        style3 = Style(bold=True)

        result = style1.merge(style2).merge(style3)

        assert result.fg_color == (255, 0, 0)
        assert result.bg_color == (0, 255, 0)
        assert result.bold is True

    def test_merge_non_destructive(self):
        """Test that merge doesn't modify input styles.

        Returns
        -------
        None
        """
        base = Style(fg_color=(255, 0, 0))
        override = Style(fg_color=(0, 255, 0))

        merged = base.merge(override)

        # Original styles unchanged
        assert base.fg_color == (255, 0, 0)
        assert override.fg_color == (0, 255, 0)
        # Merged has new value
        assert merged.fg_color == (0, 255, 0)


class TestStyleToCellAttrs:
    """Test Style.to_cell_attrs() conversion."""

    def test_empty_style_to_cell_attrs(self):
        """Test converting empty style to cell attributes.

        Returns
        -------
        None
        """
        style = Style()
        attrs = style.to_cell_attrs()

        assert attrs == {
            "fg_color": None,
            "bg_color": None,
            "bold": False,
            "italic": False,
            "underline": False,
            "reverse": False,
            "dim": False,
        }

    def test_colored_style_to_cell_attrs(self):
        """Test converting colored style to cell attributes.

        Returns
        -------
        None
        """
        style = Style(fg_color=(255, 0, 0), bg_color=(0, 0, 255))
        attrs = style.to_cell_attrs()

        assert attrs["fg_color"] == (255, 0, 0)
        assert attrs["bg_color"] == (0, 0, 255)

    def test_attributed_style_to_cell_attrs(self):
        """Test converting style with text attributes.

        Returns
        -------
        None
        """
        style = Style(bold=True, italic=True, underline=True)
        attrs = style.to_cell_attrs()

        assert attrs["bold"] is True
        assert attrs["italic"] is True
        assert attrs["underline"] is True
        assert attrs["reverse"] is False
        assert attrs["dim"] is False

    def test_full_style_to_cell_attrs(self):
        """Test converting style with all properties set.

        Returns
        -------
        None
        """
        style = Style(
            fg_color=(128, 128, 128),
            bg_color=(64, 64, 64),
            bold=True,
            italic=True,
            underline=True,
            dim=True,
            reverse=True,
        )
        attrs = style.to_cell_attrs()

        assert attrs["fg_color"] == (128, 128, 128)
        assert attrs["bg_color"] == (64, 64, 64)
        assert attrs["bold"] is True
        assert attrs["italic"] is True
        assert attrs["underline"] is True
        assert attrs["dim"] is True
        assert attrs["reverse"] is True


class TestStyleToAnsi:
    """Test Style.to_ansi() ANSI sequence generation."""

    def test_empty_style_to_ansi(self):
        """Test that empty style produces empty ANSI string.

        Returns
        -------
        None
        """
        style = Style()
        ansi = style.to_ansi()
        assert ansi == ""

    def test_bold_to_ansi(self):
        """Test bold attribute generates correct ANSI code.

        Returns
        -------
        None
        """
        style = Style(bold=True)
        ansi = style.to_ansi()
        assert "\x1b[1m" in ansi or ansi == "\x1b[1m"

    def test_italic_to_ansi(self):
        """Test italic attribute generates correct ANSI code.

        Returns
        -------
        None
        """
        style = Style(italic=True)
        ansi = style.to_ansi()
        assert "3m" in ansi

    def test_underline_to_ansi(self):
        """Test underline attribute generates correct ANSI code.

        Returns
        -------
        None
        """
        style = Style(underline=True)
        ansi = style.to_ansi()
        assert "4m" in ansi

    def test_dim_to_ansi(self):
        """Test dim attribute generates correct ANSI code.

        Returns
        -------
        None
        """
        style = Style(dim=True)
        ansi = style.to_ansi()
        assert "2m" in ansi

    def test_reverse_to_ansi(self):
        """Test reverse attribute generates correct ANSI code.

        Returns
        -------
        None
        """
        style = Style(reverse=True)
        ansi = style.to_ansi()
        assert "7m" in ansi

    def test_fg_color_to_ansi(self):
        """Test foreground color generates correct ANSI code.

        Returns
        -------
        None
        """
        style = Style(fg_color=(255, 128, 64))
        ansi = style.to_ansi()
        # Should contain 24-bit color code: 38;2;R;G;B
        assert "38;2;255;128;64" in ansi

    def test_bg_color_to_ansi(self):
        """Test background color generates correct ANSI code.

        Returns
        -------
        None
        """
        style = Style(bg_color=(64, 128, 255))
        ansi = style.to_ansi()
        # Should contain 24-bit color code: 48;2;R;G;B
        assert "48;2;64;128;255" in ansi

    def test_combined_to_ansi(self):
        """Test combined attributes and colors.

        Returns
        -------
        None
        """
        style = Style(fg_color=(255, 0, 0), bg_color=(0, 0, 255), bold=True)
        ansi = style.to_ansi()

        # Should start with ESC[
        assert ansi.startswith("\x1b[")
        # Should end with m
        assert ansi.endswith("m")
        # Should contain bold code
        assert "1" in ansi
        # Should contain both colors
        assert "38;2;255;0;0" in ansi
        assert "48;2;0;0;255" in ansi


class TestStyleBool:
    """Test Style.__bool__() behavior."""

    def test_empty_style_is_falsy(self):
        """Test that empty style evaluates to False.

        Returns
        -------
        None
        """
        style = Style()
        assert not style
        assert bool(style) is False

    def test_style_with_fg_color_is_truthy(self):
        """Test that style with fg_color is truthy.

        Returns
        -------
        None
        """
        style = Style(fg_color=(255, 0, 0))
        assert style
        assert bool(style) is True

    def test_style_with_bg_color_is_truthy(self):
        """Test that style with bg_color is truthy.

        Returns
        -------
        None
        """
        style = Style(bg_color=(0, 0, 255))
        assert style
        assert bool(style) is True

    def test_style_with_bold_is_truthy(self):
        """Test that style with bold is truthy.

        Returns
        -------
        None
        """
        style = Style(bold=True)
        assert style
        assert bool(style) is True

    def test_style_with_any_attribute_is_truthy(self):
        """Test that style with any attribute is truthy.

        Returns
        -------
        None
        """
        styles = [
            Style(italic=True),
            Style(underline=True),
            Style(dim=True),
            Style(reverse=True),
        ]
        for style in styles:
            assert style
            assert bool(style) is True


class TestPredefinedStyles:
    """Test predefined style constants."""

    def test_default_style(self):
        """Test DEFAULT_STYLE is empty.

        Returns
        -------
        None
        """
        assert DEFAULT_STYLE.fg_color is None
        assert DEFAULT_STYLE.bg_color is None
        assert not DEFAULT_STYLE.bold
        assert not bool(DEFAULT_STYLE)

    def test_bold_style(self):
        """Test BOLD_STYLE has bold set.

        Returns
        -------
        None
        """
        assert BOLD_STYLE.bold is True
        assert bool(BOLD_STYLE) is True

    def test_italic_style(self):
        """Test ITALIC_STYLE has italic set.

        Returns
        -------
        None
        """
        assert ITALIC_STYLE.italic is True
        assert bool(ITALIC_STYLE) is True

    def test_underline_style(self):
        """Test UNDERLINE_STYLE has underline set.

        Returns
        -------
        None
        """
        assert UNDERLINE_STYLE.underline is True
        assert bool(UNDERLINE_STYLE) is True

    def test_dim_style(self):
        """Test DIM_STYLE has dim set.

        Returns
        -------
        None
        """
        assert DIM_STYLE.dim is True
        assert bool(DIM_STYLE) is True


class TestParseColor:
    """Test parse_color() function."""

    def test_parse_hex_long_form(self):
        """Test parsing long-form hex colors.

        Returns
        -------
        None
        """
        assert parse_color("#FF0000") == (255, 0, 0)
        assert parse_color("#00FF00") == (0, 255, 0)
        assert parse_color("#0000FF") == (0, 0, 255)
        assert parse_color("#FFFFFF") == (255, 255, 255)
        assert parse_color("#000000") == (0, 0, 0)

    def test_parse_hex_short_form(self):
        """Test parsing short-form hex colors.

        Returns
        -------
        None
        """
        assert parse_color("#F00") == (255, 0, 0)
        assert parse_color("#0F0") == (0, 255, 0)
        assert parse_color("#00F") == (0, 0, 255)
        assert parse_color("#FFF") == (255, 255, 255)
        assert parse_color("#000") == (0, 0, 0)

    def test_parse_hex_case_insensitive(self):
        """Test that hex parsing is case-insensitive.

        Returns
        -------
        None
        """
        assert parse_color("#ff0000") == (255, 0, 0)
        assert parse_color("#FF0000") == (255, 0, 0)
        assert parse_color("#Ff0000") == (255, 0, 0)

    def test_parse_rgb_format(self):
        """Test parsing rgb(R, G, B) format.

        Returns
        -------
        None
        """
        assert parse_color("rgb(255, 0, 0)") == (255, 0, 0)
        assert parse_color("rgb(0, 255, 0)") == (0, 255, 0)
        assert parse_color("rgb(0, 0, 255)") == (0, 0, 255)
        assert parse_color("rgb(128, 128, 128)") == (128, 128, 128)

    def test_parse_rgb_with_spaces(self):
        """Test that rgb() parsing handles spacing variations.

        Returns
        -------
        None
        """
        assert parse_color("rgb(255,0,0)") == (255, 0, 0)
        assert parse_color("rgb( 255 , 0 , 0 )") == (255, 0, 0)

    def test_parse_named_colors(self):
        """Test parsing named colors.

        Returns
        -------
        None
        """
        assert parse_color("red") == (255, 0, 0)
        assert parse_color("green") == (0, 255, 0)
        assert parse_color("blue") == (0, 0, 255)
        assert parse_color("white") == (255, 255, 255)
        assert parse_color("black") == (0, 0, 0)
        assert parse_color("cyan") == (0, 255, 255)
        assert parse_color("magenta") == (255, 0, 255)
        assert parse_color("yellow") == (255, 255, 0)
        assert parse_color("gray") == (128, 128, 128)
        assert parse_color("grey") == (128, 128, 128)  # Alternative spelling

    def test_parse_named_colors_case_insensitive(self):
        """Test that named color parsing is case-insensitive.

        Returns
        -------
        None
        """
        assert parse_color("RED") == (255, 0, 0)
        assert parse_color("Red") == (255, 0, 0)
        assert parse_color("red") == (255, 0, 0)

    def test_parse_color_with_whitespace(self):
        """Test that color parsing handles leading/trailing whitespace.

        Returns
        -------
        None
        """
        assert parse_color("  red  ") == (255, 0, 0)
        assert parse_color("  #FF0000  ") == (255, 0, 0)

    def test_parse_invalid_color_returns_none(self):
        """Test that invalid color strings return None.

        Returns
        -------
        None
        """
        assert parse_color("invalid") is None
        assert parse_color("notacolor") is None
        assert parse_color("#GGG") is None  # Invalid hex
        assert parse_color("rgb(300, 0, 0)") == (300, 0, 0)  # Out of range but parses
        assert parse_color("rgb(a, b, c)") is None  # Invalid values
        assert parse_color("") is None


class TestStyleEquality:
    """Test Style equality comparison."""

    def test_equal_empty_styles(self):
        """Test that two empty styles are equal.

        Returns
        -------
        None
        """
        style1 = Style()
        style2 = Style()
        assert style1 == style2

    def test_equal_colored_styles(self):
        """Test that styles with same colors are equal.

        Returns
        -------
        None
        """
        style1 = Style(fg_color=(255, 0, 0), bg_color=(0, 0, 255))
        style2 = Style(fg_color=(255, 0, 0), bg_color=(0, 0, 255))
        assert style1 == style2

    def test_equal_attributed_styles(self):
        """Test that styles with same attributes are equal.

        Returns
        -------
        None
        """
        style1 = Style(bold=True, italic=True)
        style2 = Style(bold=True, italic=True)
        assert style1 == style2

    def test_unequal_different_colors(self):
        """Test that styles with different colors are not equal.

        Returns
        -------
        None
        """
        style1 = Style(fg_color=(255, 0, 0))
        style2 = Style(fg_color=(0, 255, 0))
        assert style1 != style2

    def test_unequal_different_attributes(self):
        """Test that styles with different attributes are not equal.

        Returns
        -------
        None
        """
        style1 = Style(bold=True)
        style2 = Style(italic=True)
        assert style1 != style2
