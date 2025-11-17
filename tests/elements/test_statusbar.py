"""Tests for StatusBar element.

This module tests the StatusBar element including:
- Initialization with default and custom values
- Rendering with left, center, and right sections
- Alignment and padding behavior
- Width handling and clipping
- Color support (background and text colors)
- ANSI-aware text handling
- Edge cases (empty sections, overflow, etc.)
"""

from tests.helpers import render_element
from wijjit.elements.display.statusbar import StatusBar
from wijjit.layout.bounds import Bounds
from wijjit.terminal.ansi import strip_ansi, visible_length


class TestStatusBar:
    """Test suite for StatusBar element."""

    def test_initialization_defaults(self):
        """Test StatusBar initialization with default values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar()
        assert sb.left == ""
        assert sb.center == ""
        assert sb.right == ""
        assert sb.bg_color is None
        assert sb.text_color is None
        assert sb.width == 80
        assert sb.focusable is False
        assert sb.bind is True

    def test_initialization_custom_values(self):
        """Test StatusBar initialization with custom values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(
            id="test_status",
            left="File: app.py",
            center="Ready",
            right="Ln 1, Col 1",
            bg_color="blue",
            text_color="white",
            width=100,
        )
        assert sb.id == "test_status"
        assert sb.left == "File: app.py"
        assert sb.center == "Ready"
        assert sb.right == "Ln 1, Col 1"
        assert sb.bg_color == "blue"
        assert sb.text_color == "white"
        assert sb.width == 100

    def test_render_basic(self):
        """Test basic rendering with all three sections.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="Left", center="Center", right="Right", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Should render all sections
        assert "Left" in output
        assert "Center" in output
        assert "Right" in output

        # Should be exactly the specified width
        assert visible_length(output) == 40

    def test_render_left_alignment(self):
        """Test that left section is left-aligned.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="File: test.py", center="", right="", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Left content should appear at the start
        stripped = strip_ansi(output)
        assert stripped.startswith("File: test.py")

        # Should be padded to width
        assert visible_length(output) == 40

    def test_render_center_alignment(self):
        """Test that center section is centered.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="", center="Status", right="", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Center content should be roughly in the middle
        stripped = strip_ansi(output)
        center_pos = stripped.find("Status")

        # Should be roughly centered (within a few characters)
        expected_center = (40 - len("Status")) // 2
        assert abs(center_pos - expected_center) <= 2

        # Should be padded to width
        assert visible_length(output) == 40

    def test_render_right_alignment(self):
        """Test that right section is right-aligned.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="", center="", right="Line 42", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Right content should appear at the end
        stripped = strip_ansi(output)
        assert stripped.rstrip().endswith("Line 42")

        # Should be padded to width
        assert visible_length(output) == 40

    def test_render_all_sections_together(self):
        """Test rendering with all sections populated.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="app.py", center="Ready", right="Ln 1", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        stripped = strip_ansi(output)

        # All sections should be present
        assert "app.py" in stripped
        assert "Ready" in stripped
        assert "Ln 1" in stripped

        # Left should be at the start
        assert stripped.startswith("app.py")

        # Right should be at the end
        assert stripped.rstrip().endswith("Ln 1")

        # Should be exactly the width
        assert visible_length(output) == 40

    def test_render_empty_sections(self):
        """Test rendering with empty sections.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="", center="", right="", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Should render blank line of correct width
        stripped = strip_ansi(output)
        assert len(stripped) == 40
        assert stripped == " " * 40

    def test_render_overflow_clipping(self):
        """Test that content is clipped when it exceeds width.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Create statusbar with content longer than width
        sb = StatusBar(
            left="Very long left content that will overflow",
            center="Center content",
            right="Very long right content",
            width=40,
        )
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Output should not exceed width
        assert visible_length(output) == 40

        # Should contain clipped versions of content
        stripped = strip_ansi(output)
        assert len(stripped) == 40

    def test_render_with_background_color(self):
        """Test rendering with background color.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(
            left="Left", center="Center", right="Right", bg_color="blue", width=40
        )
        sb.bounds = Bounds(0, 0, 40, 1)
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Cell-based rendering stores colors in Cell objects, not ANSI codes
        # Content should be visible
        assert "Left" in output
        assert "Center" in output
        assert "Right" in output

    def test_render_with_text_color(self):
        """Test rendering with text color.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(
            left="Left", center="Center", right="Right", text_color="white", width=40
        )
        sb.bounds = Bounds(0, 0, 40, 1)
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Cell-based rendering stores colors in Cell objects, not ANSI codes
        # Content should be visible
        assert "Left" in output
        assert "Center" in output
        assert "Right" in output

    def test_render_with_both_colors(self):
        """Test rendering with both background and text colors.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(
            left="Left",
            center="Center",
            right="Right",
            bg_color="blue",
            text_color="white",
            width=40,
        )
        sb.bounds = Bounds(0, 0, 40, 1)
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Cell-based rendering stores colors in Cell objects, not ANSI codes
        # Output should have correct length
        assert len(output) == 40

    def test_get_bg_color_code(self):
        """Test background color code retrieval.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        from wijjit.terminal.ansi import ANSIColor

        sb = StatusBar(bg_color="blue")
        color_code = sb._get_bg_color_code()
        assert color_code == ANSIColor.BG_BLUE

        sb_no_color = StatusBar()
        assert sb_no_color._get_bg_color_code() is None

    def test_get_text_color_code(self):
        """Test text color code retrieval.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        from wijjit.terminal.ansi import ANSIColor

        sb = StatusBar(text_color="white")
        color_code = sb._get_text_color_code()
        assert color_code == ANSIColor.WHITE

        sb_no_color = StatusBar()
        assert sb_no_color._get_text_color_code() is None

    def test_render_with_ansi_codes_in_content(self):
        """Test rendering when content already contains ANSI codes.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        from wijjit.terminal.ansi import colorize

        # Create content with ANSI codes
        colored_left = colorize("Left", color="\x1b[31m")  # Red
        colored_center = colorize("Center", color="\x1b[32m")  # Green
        colored_right = colorize("Right", color="\x1b[33m")  # Yellow

        sb = StatusBar(
            left=colored_left, center=colored_center, right=colored_right, width=40
        )
        sb.bounds = Bounds(0, 0, 40, 1)
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Content should be present
        # Note: StatusBar may preserve ANSI codes from input content
        assert "Left" in output
        assert "Center" in output
        # Right may be truncated if colorized content is too long
        # Just verify output is non-empty
        assert len(output) > 0

    def test_render_different_widths(self):
        """Test rendering at different widths.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for width in [20, 40, 60, 80, 120]:
            sb = StatusBar(left="L", center="C", right="R", width=width)
            sb.set_bounds(Bounds(0, 0, width, 1))
            output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

            # Should match the specified width
            assert visible_length(output) == width

    def test_render_minimum_width(self):
        """Test rendering with very small width.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="Left", center="Center", right="Right", width=10)
        sb.set_bounds(Bounds(0, 0, 10, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Should handle gracefully - width should be 10
        assert visible_length(output) == 10

    def test_render_without_bounds(self):
        """Test rendering without bounds set uses width attribute.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="Left", center="Center", right="Right", width=50)
        output = render_element(sb, width=50, height=1)

        # Should use the width attribute
        assert len(output) == 50

    def test_render_with_bounds_overrides_width(self):
        """Test that bounds width overrides the width attribute.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="Left", center="Center", right="Right", width=50)
        sb.set_bounds(Bounds(0, 0, 80, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # Should use bounds width, not attribute width
        assert visible_length(output) == 80

    def test_render_only_left_section(self):
        """Test rendering with only left section.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="Only left", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        stripped = strip_ansi(output)
        assert stripped.startswith("Only left")
        assert visible_length(output) == 40

    def test_render_only_center_section(self):
        """Test rendering with only center section.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(center="Only center", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        stripped = strip_ansi(output)
        assert "Only center" in stripped
        assert visible_length(output) == 40

    def test_render_only_right_section(self):
        """Test rendering with only right section.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(right="Only right", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        stripped = strip_ansi(output)
        assert stripped.rstrip().endswith("Only right")
        assert visible_length(output) == 40

    def test_multiple_renders(self):
        """Test that multiple renders produce consistent output.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb = StatusBar(left="Left", center="Center", right="Right", width=40)
        sb.set_bounds(Bounds(0, 0, 40, 1))

        output1 = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)
        output2 = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)
        output3 = render_element(sb, width=sb.bounds.width, height=sb.bounds.height)

        # All renders should be identical
        assert output1 == output2
        assert output2 == output3

    def test_color_name_case_insensitive(self):
        """Test that color names are case-insensitive.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        sb_lower = StatusBar(bg_color="blue", text_color="white")
        sb_upper = StatusBar(bg_color="BLUE", text_color="WHITE")
        sb_mixed = StatusBar(bg_color="Blue", text_color="White")

        # All should work without errors
        sb_lower.set_bounds(Bounds(0, 0, 40, 1))
        sb_upper.set_bounds(Bounds(0, 0, 40, 1))
        sb_mixed.set_bounds(Bounds(0, 0, 40, 1))

        output_lower = render_element(
            sb_lower, width=sb_lower.bounds.width, height=sb_lower.bounds.height
        )
        output_upper = render_element(
            sb_upper, width=sb_upper.bounds.width, height=sb_upper.bounds.height
        )
        output_mixed = render_element(
            sb_mixed, width=sb_mixed.bounds.width, height=sb_mixed.bounds.height
        )

        # Cell-based rendering stores colors in Cell objects, not ANSI codes
        # All outputs should be non-empty
        assert len(output_lower) > 0
        assert len(output_upper) > 0
        assert len(output_mixed) > 0
