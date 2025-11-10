"""Tests for Spinner element.

This module tests the Spinner element including:
- Multiple animation styles (dots, line, bouncing, clock)
- Frame advancement and cycling
- Unicode detection and ASCII fallback
- Active/inactive states
- Color support
"""

from wijjit.elements.display.spinner import SPINNER_FRAMES, Spinner
from wijjit.terminal.ansi import strip_ansi


class TestSpinner:
    """Test suite for Spinner element."""

    def test_initialization(self):
        """Test Spinner initialization with default values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner()
        assert spinner.active is True
        assert spinner.style == "dots"
        assert spinner.label == ""
        assert spinner.color is None
        assert spinner.frame_index == 0
        assert spinner.focusable is False

    def test_initialization_custom_values(self):
        """Test Spinner initialization with custom values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(
            id="test",
            active=False,
            style="line",
            label="Loading...",
            color="cyan",
            frame_index=5,
        )
        assert spinner.id == "test"
        assert spinner.active is False
        assert spinner.style == "line"
        assert spinner.label == "Loading..."
        assert spinner.color == "cyan"
        assert spinner.frame_index == 5

    def test_next_frame(self):
        """Test frame advancement.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(style="line")  # Line has 4 frames
        assert spinner.frame_index == 0

        spinner.next_frame()
        assert spinner.frame_index == 1

        spinner.next_frame()
        assert spinner.frame_index == 2

        spinner.next_frame()
        assert spinner.frame_index == 3

        # Should wrap around
        spinner.next_frame()
        assert spinner.frame_index == 0

    def test_frame_wrapping(self):
        """Test frame index wrapping for different styles.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Test dots style (10 frames)
        spinner_dots = Spinner(style="dots")
        for _ in range(10):
            spinner_dots.next_frame()
        assert spinner_dots.frame_index == 0  # Should wrap

        # Test line style (4 frames)
        spinner_line = Spinner(style="line")
        for _ in range(4):
            spinner_line.next_frame()
        assert spinner_line.frame_index == 0  # Should wrap

    def test_get_style_frames(self):
        """Test getting frames for different styles.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner()

        # Test dots style
        frames_dots = spinner._get_style_frames("dots")
        assert len(frames_dots) > 0
        assert isinstance(frames_dots, list)

        # Test line style
        frames_line = spinner._get_style_frames("line")
        assert len(frames_line) > 0
        assert frames_line == ["|", "/", "-", "\\"]

        # Test bouncing style
        frames_bouncing = spinner._get_style_frames("bouncing")
        assert len(frames_bouncing) > 0

        # Test clock style
        frames_clock = spinner._get_style_frames("clock")
        assert len(frames_clock) > 0

    def test_get_style_frames_invalid_style(self):
        """Test getting frames for invalid style (should default).

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner()
        frames = spinner._get_style_frames("invalid_style")
        # Should default to dots
        assert frames == spinner._get_style_frames("dots")

    def test_get_current_frame(self):
        """Test getting current animation frame.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(style="line")
        frame0 = spinner._get_current_frame()
        assert frame0 == "|"

        spinner.next_frame()
        frame1 = spinner._get_current_frame()
        assert frame1 == "/"

        spinner.next_frame()
        frame2 = spinner._get_current_frame()
        assert frame2 == "-"

        spinner.next_frame()
        frame3 = spinner._get_current_frame()
        assert frame3 == "\\"

    def test_render_active(self):
        """Test rendering when active.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(active=True, style="line", label="Loading...")
        output = spinner.render()

        # Should contain spinner character and label
        assert len(output) > 0
        assert "Loading..." in output

    def test_render_inactive_with_label(self):
        """Test rendering when inactive with label.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(active=False, label="Loading...")
        output = spinner.render()

        # Should only show label (no spinner character)
        assert output == "Loading..."

    def test_render_inactive_without_label(self):
        """Test rendering when inactive without label.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(active=False, label="")
        output = spinner.render()

        # Should return empty string
        assert output == ""

    def test_render_without_label(self):
        """Test rendering without label.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(active=True, style="line", label="")
        output = spinner.render()

        # Should contain only spinner character
        assert len(output) > 0
        assert len(strip_ansi(output)) <= 2  # Just the spinner char

    def test_render_with_color(self):
        """Test rendering with color applied.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(active=True, style="line", color="cyan")
        output = spinner.render()

        # Output should contain ANSI codes
        assert "\x1b[" in output  # ANSI escape sequence

    def test_all_styles_render(self):
        """Test that all styles render without errors.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        styles = ["dots", "line", "bouncing", "clock"]

        for style in styles:
            spinner = Spinner(active=True, style=style, label="Test")
            output = spinner.render()
            # Should render without error
            assert len(output) > 0
            assert "Test" in output

    def test_frame_index_bounds(self):
        """Test that frame index stays within bounds.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(style="line")  # 4 frames

        # Set index beyond bounds
        spinner.frame_index = 100

        # Should still get valid frame (wraps with modulo)
        frame = spinner._get_current_frame()
        assert frame in ["|", "/", "-", "\\"]

    def test_animation_sequence(self):
        """Test complete animation sequence for line style.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(style="line", label="Loading")
        expected_sequence = ["|", "/", "-", "\\"]

        for _expected_char in expected_sequence:
            output = spinner.render()
            # Check that the spinner character is in the output
            assert any(char in output for char in expected_sequence)
            spinner.next_frame()

        # After one complete cycle, should be back at start
        assert spinner.frame_index == 0

    def test_unicode_vs_ascii_frames(self):
        """Test that ASCII fallback frames exist for Unicode styles.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Check that ASCII versions exist for unicode-heavy styles
        assert "dots_ascii" in SPINNER_FRAMES
        assert "bouncing_ascii" in SPINNER_FRAMES
        assert "clock_ascii" in SPINNER_FRAMES

        # Line style is ASCII-compatible, so no separate ASCII version needed
        assert "line" in SPINNER_FRAMES

    def test_label_formatting(self):
        """Test label formatting with spinner.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(active=True, style="line", label="Processing data")
        output = spinner.render()

        # Should have format: "[spinner] Processing data"
        # where [spinner] is one character
        assert "Processing data" in output

        # Check space between spinner and label
        stripped = strip_ansi(output)
        assert " " in stripped  # Space separator

    def test_multiple_frame_advances(self):
        """Test advancing frames multiple times.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        spinner = Spinner(style="dots")  # 10 frames
        frames_seen = []

        # Advance through several cycles
        for _ in range(30):
            frames_seen.append(spinner.frame_index)
            spinner.next_frame()

        # Should have seen multiple complete cycles
        assert frames_seen.count(0) >= 3  # At least 3 times back to frame 0

    def test_color_options(self):
        """Test different color options.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        colors = ["red", "green", "yellow", "blue", "cyan", "magenta"]

        for color in colors:
            spinner = Spinner(active=True, style="line", color=color)
            output = spinner.render()
            # Should render without error and contain ANSI codes
            assert len(output) > 0
            if color:  # If color specified, should have ANSI codes
                assert "\x1b[" in output
