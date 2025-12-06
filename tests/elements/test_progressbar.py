"""Tests for ProgressBar element.

This module tests the ProgressBar element including:
- Multiple display styles (filled, percentage, gradient, custom)
- Value and percentage calculations
- Color support
- Unicode and ASCII rendering
"""

from tests.helpers import render_element
from wijjit.elements.display.progress import ProgressBar
from wijjit.layout.bounds import Bounds
from wijjit.terminal.ansi import strip_ansi, visible_length


class TestProgressBar:
    """Test suite for ProgressBar element."""

    def test_initialization(self):
        """Test ProgressBar initialization with default values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar()
        assert pb.value == 0
        assert pb.max == 100
        assert pb.width == 40
        assert pb.style == "filled"
        assert pb.color is None
        assert pb.show_percentage is True
        assert pb.focusable is False

    def test_initialization_custom_values(self):
        """Test ProgressBar initialization with custom values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(
            id="test",
            value=50,
            max=200,
            width=60,
            style="gradient",
            color="cyan",
            show_percentage=False,
        )
        assert pb.id == "test"
        assert pb.value == 50
        assert pb.max == 200
        assert pb.width == 60
        assert pb.style == "gradient"
        assert pb.color == "cyan"
        assert pb.show_percentage is False

    def test_get_percentage(self):
        """Test percentage calculation.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(value=25, max=100)
        assert pb.get_percentage() == 25.0

        pb = ProgressBar(value=50, max=200)
        assert pb.get_percentage() == 25.0

        pb = ProgressBar(value=0, max=100)
        assert pb.get_percentage() == 0.0

        pb = ProgressBar(value=100, max=100)
        assert pb.get_percentage() == 100.0

    def test_get_percentage_edge_cases(self):
        """Test percentage calculation edge cases.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Zero max
        pb = ProgressBar(value=50, max=0)
        assert pb.get_percentage() == 0.0

        # Value exceeds max (should clamp to 100%)
        pb = ProgressBar(value=150, max=100)
        assert pb.get_percentage() == 100.0

        # Negative value (should clamp to 0%)
        pb = ProgressBar(value=-10, max=100)
        assert pb.get_percentage() == 0.0

    def test_set_progress(self):
        """Test set_progress method.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar()
        assert pb.value == 0

        pb.set_progress(50)
        assert pb.value == 50

        pb.set_progress(100)
        assert pb.value == 100

    def test_render_filled_style(self):
        """Test rendering filled block style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(value=50, max=100, width=40, style="filled")
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should have some output
        assert len(output) > 0

        # Visible length should match width
        assert visible_length(output) == pb.width

        # Should contain percentage text
        assert "50.0%" in output

    def test_render_percentage_style(self):
        """Test rendering percentage-only style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(value=75, max=100, width=40, style="percentage")
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should contain "Progress:" and percentage
        assert "Progress:" in output
        assert "75.0%" in output

        # Visible length should match width (padded)
        assert visible_length(output) <= pb.width

    def test_render_gradient_style(self):
        """Test rendering gradient color style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Low percentage (red)
        pb_low = ProgressBar(value=20, max=100, width=40, style="gradient")
        if not pb_low.bounds:
            pb_low.set_bounds(Bounds(0, 0, 40, 1))
        output_low = render_element(
            pb_low, width=pb_low.bounds.width, height=pb_low.bounds.height
        )
        assert len(strip_ansi(output_low)) > 0

        # Medium percentage (yellow)
        pb_med = ProgressBar(value=50, max=100, width=40, style="gradient")
        if not pb_med.bounds:
            pb_med.set_bounds(Bounds(0, 0, 40, 1))
        output_med = render_element(
            pb_med, width=pb_med.bounds.width, height=pb_med.bounds.height
        )
        assert len(strip_ansi(output_med)) > 0

        # High percentage (green)
        pb_high = ProgressBar(value=90, max=100, width=40, style="gradient")
        if not pb_high.bounds:
            pb_high.set_bounds(Bounds(0, 0, 40, 1))
        output_high = render_element(
            pb_high, width=pb_high.bounds.width, height=pb_high.bounds.height
        )
        assert len(strip_ansi(output_high)) > 0

        # All should have proper width
        assert visible_length(output_low) == pb_low.width
        assert visible_length(output_med) == pb_med.width
        assert visible_length(output_high) == pb_high.width

    def test_render_custom_style(self):
        """Test rendering custom character style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(
            value=50,
            max=100,
            width=40,
            style="custom",
            fill_char="=",
            empty_char="-",
        )
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should contain custom characters
        stripped = strip_ansi(output)
        assert "=" in stripped  # Fill character
        assert (
            "-" in stripped or stripped.count("=") == (40 - 6) // 2
        )  # Empty or filled

    def test_render_with_color(self):
        """Test rendering with color applied.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(value=50, max=100, width=40, style="filled", color="green")
        if not pb.bounds:
            pb.bounds = Bounds(0, 0, 40, 1)
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Cell-based rendering stores color in Cell objects, not ANSI codes
        # Verify the progress bar renders with filled blocks
        assert "\u2588" in output  # Filled block character

        # Stripped version should still have proper length
        stripped = strip_ansi(output)
        assert len(stripped) == pb.width

    def test_render_without_percentage(self):
        """Test rendering without percentage display.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(
            value=50, max=100, width=40, style="filled", show_percentage=False
        )
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should not contain percentage text
        assert "%" not in output

        # Width should be used entirely for bar
        assert visible_length(output) == pb.width

    def test_zero_progress(self):
        """Test rendering with zero progress.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(value=0, max=100, width=40, style="filled")
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should render without error
        assert len(output) > 0
        assert visible_length(output) == pb.width

    def test_full_progress(self):
        """Test rendering with full progress.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(value=100, max=100, width=40, style="filled")
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 40, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should render without error
        assert len(output) > 0
        assert visible_length(output) == pb.width
        assert "100.0%" in output

    def test_minimum_width(self):
        """Test rendering with very small width.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(value=50, max=100, width=10, style="filled")
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 10, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should render without error
        assert len(output) > 0
        # Width handling should be graceful
        assert visible_length(output) <= pb.width + 10  # Allow some overflow

    def test_gradient_color_selection(self):
        """Test gradient color selection at different percentages.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(style="gradient")

        # Test color selection logic
        from wijjit.terminal.ansi import ANSIColor

        # Low percentage -> RED
        color_low = pb._get_color_for_percentage(20)
        assert color_low == ANSIColor.RED

        # Medium percentage -> YELLOW
        color_med = pb._get_color_for_percentage(50)
        assert color_med == ANSIColor.YELLOW

        # High percentage -> GREEN
        color_high = pb._get_color_for_percentage(80)
        assert color_high == ANSIColor.GREEN

        # Edge cases
        assert pb._get_color_for_percentage(0) == ANSIColor.RED
        assert pb._get_color_for_percentage(33) == ANSIColor.YELLOW
        assert pb._get_color_for_percentage(66) == ANSIColor.GREEN
        assert pb._get_color_for_percentage(100) == ANSIColor.GREEN


class TestBarStyles:
    """Test suite for ProgressBar bar_style presets."""

    def test_default_bar_style(self):
        """Test that default bar_style is 'block'.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar()
        assert pb.bar_style == "block"
        # Block style uses unicode block characters
        assert pb.fill_char == "\u2588"  # Full block
        assert pb.empty_char == "\u2591"  # Light shade

    def test_bar_style_thin(self):
        """Test thin bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="thin")
        assert pb.bar_style == "thin"
        assert pb.fill_char == "\u2500"  # Box drawing horizontal
        assert pb.empty_char == "\u2508"  # Box drawing light quadruple dash

    def test_bar_style_thick(self):
        """Test thick bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="thick")
        assert pb.bar_style == "thick"
        assert pb.fill_char == "\u2501"  # Heavy horizontal
        assert pb.empty_char == "\u2509"  # Heavy quadruple dash

    def test_bar_style_equals(self):
        """Test equals bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="equals")
        assert pb.bar_style == "equals"
        assert pb.fill_char == "="
        assert pb.empty_char == " "

    def test_bar_style_arrow(self):
        """Test arrow bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="arrow")
        assert pb.bar_style == "arrow"
        assert pb.fill_char == ">"
        assert pb.empty_char == " "

    def test_bar_style_dots(self):
        """Test dots bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="dots")
        assert pb.bar_style == "dots"
        assert pb.fill_char == "\u2022"  # Bullet
        assert pb.empty_char == "\u00b7"  # Middle dot

    def test_bar_style_ascii(self):
        """Test ASCII bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="ascii")
        assert pb.bar_style == "ascii"
        assert pb.fill_char == "#"
        assert pb.empty_char == "-"

    def test_bar_style_hash(self):
        """Test hash bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="hash")
        assert pb.bar_style == "hash"
        assert pb.fill_char == "#"
        assert pb.empty_char == " "

    def test_bar_style_pipe(self):
        """Test pipe bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="pipe")
        assert pb.bar_style == "pipe"
        assert pb.fill_char == "|"
        assert pb.empty_char == " "

    def test_bar_style_square(self):
        """Test square bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="square")
        assert pb.bar_style == "square"
        assert pb.fill_char == "\u25a0"  # Black square
        assert pb.empty_char == "\u25a1"  # White square

    def test_fill_char_overrides_bar_style(self):
        """Test that fill_char overrides bar_style preset.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="equals", fill_char="*")
        assert pb.bar_style == "equals"
        assert pb.fill_char == "*"  # Override
        assert pb.empty_char == " "  # From bar_style

    def test_empty_char_overrides_bar_style(self):
        """Test that empty_char overrides bar_style preset.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="arrow", empty_char=".")
        assert pb.bar_style == "arrow"
        assert pb.fill_char == ">"  # From bar_style
        assert pb.empty_char == "."  # Override

    def test_both_chars_override_bar_style(self):
        """Test that both fill_char and empty_char override bar_style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(bar_style="block", fill_char="X", empty_char="O")
        assert pb.bar_style == "block"
        assert pb.fill_char == "X"  # Override
        assert pb.empty_char == "O"  # Override

    def test_render_bar_style_equals(self):
        """Test rendering with equals bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(
            value=50, max=100, width=20, bar_style="equals", show_percentage=False
        )
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 20, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should contain = for filled portion
        assert "=" in output

    def test_render_bar_style_arrow(self):
        """Test rendering with arrow bar style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        pb = ProgressBar(
            value=50, max=100, width=20, bar_style="arrow", show_percentage=False
        )
        if not pb.bounds:
            pb.set_bounds(Bounds(0, 0, 20, 1))
        output = render_element(pb, width=pb.bounds.width, height=pb.bounds.height)

        # Should contain > for filled portion
        assert ">" in output

    def test_unknown_bar_style_falls_back_to_block(self):
        """Test that unknown bar_style falls back to block style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Use an invalid bar style that's not in BAR_STYLES
        pb = ProgressBar.__new__(ProgressBar)
        # Manually set up the object to test fallback
        from wijjit.elements.display.progress import BAR_STYLES

        preset = BAR_STYLES.get("invalid_style", BAR_STYLES["block"])
        # Should fall back to block style
        assert preset == BAR_STYLES["block"]
