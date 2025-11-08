"""Tests for mouse event handling.

This module tests the mouse event parser for ANSI mouse escape sequences,
including SGR format, normal format, and click synthesis.
"""

import time

from wijjit.terminal.mouse import (
    MouseButton,
    MouseEvent,
    MouseEventParser,
    MouseEventType,
    MouseTrackingMode,
)


class TestMouseEventParser:
    """Tests for MouseEventParser class."""

    def test_parse_sgr_left_press(self):
        """Test parsing SGR format left button press."""
        parser = MouseEventParser()
        data = b"\x1b[<0;10;5M"  # Left button press at column 10, row 5

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.PRESS
        assert event.button == MouseButton.LEFT
        assert event.x == 9  # 0-based (10 - 1)
        assert event.y == 4  # 0-based (5 - 1)
        assert not event.shift
        assert not event.alt
        assert not event.ctrl

    def test_parse_sgr_left_release(self):
        """Test parsing SGR format left button release."""
        parser = MouseEventParser()
        data = b"\x1b[<0;10;5m"  # Left button release (lowercase 'm')

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.RELEASE
        assert event.button == MouseButton.LEFT
        assert event.x == 9
        assert event.y == 4

    def test_parse_sgr_middle_button(self):
        """Test parsing SGR format middle button."""
        parser = MouseEventParser()
        data = b"\x1b[<1;20;10M"  # Middle button

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.PRESS
        assert event.button == MouseButton.MIDDLE
        assert event.x == 19
        assert event.y == 9

    def test_parse_sgr_right_button(self):
        """Test parsing SGR format right button."""
        parser = MouseEventParser()
        data = b"\x1b[<2;15;8M"  # Right button

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.PRESS
        assert event.button == MouseButton.RIGHT
        assert event.x == 14
        assert event.y == 7

    def test_parse_sgr_with_shift_modifier(self):
        """Test parsing SGR format with Shift modifier."""
        parser = MouseEventParser()
        data = b"\x1b[<4;10;5M"  # Button code 4 = Shift modifier

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.shift
        assert not event.alt
        assert not event.ctrl

    def test_parse_sgr_with_alt_modifier(self):
        """Test parsing SGR format with Alt modifier."""
        parser = MouseEventParser()
        data = b"\x1b[<8;10;5M"  # Button code 8 = Alt modifier

        event = parser.parse_sgr(data)

        assert event is not None
        assert not event.shift
        assert event.alt
        assert not event.ctrl

    def test_parse_sgr_with_ctrl_modifier(self):
        """Test parsing SGR format with Ctrl modifier."""
        parser = MouseEventParser()
        data = b"\x1b[<16;10;5M"  # Button code 16 = Ctrl modifier

        event = parser.parse_sgr(data)

        assert event is not None
        assert not event.shift
        assert not event.alt
        assert event.ctrl

    def test_parse_sgr_with_multiple_modifiers(self):
        """Test parsing SGR format with multiple modifiers."""
        parser = MouseEventParser()
        # Button code: 0 (left) + 4 (shift) + 8 (alt) + 16 (ctrl) = 28
        data = b"\x1b[<28;10;5M"

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.button == MouseButton.LEFT
        assert event.shift
        assert event.alt
        assert event.ctrl

    def test_parse_sgr_scroll_up(self):
        """Test parsing SGR format scroll up event."""
        parser = MouseEventParser()
        data = b"\x1b[<64;10;5M"  # Scroll up

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.SCROLL
        assert event.button == MouseButton.SCROLL_UP
        assert event.x == 9
        assert event.y == 4

    def test_parse_sgr_scroll_down(self):
        """Test parsing SGR format scroll down event."""
        parser = MouseEventParser()
        data = b"\x1b[<65;10;5M"  # Scroll down

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.SCROLL
        assert event.button == MouseButton.SCROLL_DOWN

    def test_parse_sgr_drag_event(self):
        """Test parsing SGR format drag event."""
        parser = MouseEventParser()
        # Button code: 0 (left) + 32 (motion) = 32
        data = b"\x1b[<32;15;10M"

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.DRAG
        assert event.button == MouseButton.LEFT

    def test_parse_sgr_move_event(self):
        """Test parsing SGR format move event (no button)."""
        parser = MouseEventParser()
        # Button code: 3 (no button) + 32 (motion) = 35
        data = b"\x1b[<35;15;10M"

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.type == MouseEventType.MOVE
        assert event.button == MouseButton.NONE

    def test_parse_sgr_invalid_sequence(self):
        """Test that invalid SGR sequences return None."""
        parser = MouseEventParser()
        data = b"\x1b[invalid"

        event = parser.parse_sgr(data)

        assert event is None

    def test_parse_sgr_extended_coordinates(self):
        """Test SGR format with extended coordinates (>255)."""
        parser = MouseEventParser()
        data = b"\x1b[<0;300;200M"  # Coordinates beyond legacy limit

        event = parser.parse_sgr(data)

        assert event is not None
        assert event.x == 299
        assert event.y == 199

    def test_parse_normal_left_press(self):
        """Test parsing normal format left button press."""
        parser = MouseEventParser()
        # Format: ESC [ M bxy where b=32+button, x=33+col, y=33+row
        # Left press at (9, 4): b=32+0=32(' '), x=33+9=42('*'), y=33+4=37('%')
        data = b"\x1b[M *%"

        event = parser.parse_normal(data)

        assert event is not None
        assert event.type == MouseEventType.PRESS
        assert event.button == MouseButton.LEFT
        assert event.x == 9
        assert event.y == 4

    def test_parse_normal_release(self):
        """Test parsing normal format button release."""
        parser = MouseEventParser()
        # Release: button code 3, x=42, y=37
        data = b"\x1b[M#*%"  # 35 = 32+3

        event = parser.parse_normal(data)

        assert event is not None
        assert event.type == MouseEventType.RELEASE

    def test_parse_normal_too_short(self):
        """Test that too-short sequences return None."""
        parser = MouseEventParser()
        data = b"\x1b[M"  # Incomplete

        event = parser.parse_normal(data)

        assert event is None

    def test_parse_normal_wrong_prefix(self):
        """Test that wrong prefix returns None."""
        parser = MouseEventParser()
        data = b"\x1b[X abc"  # Wrong prefix

        event = parser.parse_normal(data)

        assert event is None

    def test_click_synthesis(self):
        """Test that press+release synthesizes CLICK event."""
        parser = MouseEventParser()

        # Press at (10, 5)
        press_data = b"\x1b[<0;11;6M"
        press_event = parser.parse_sgr(press_data)
        assert press_event.type == MouseEventType.PRESS

        # Release at same position
        release_data = b"\x1b[<0;11;6m"
        release_event = parser.parse_sgr(release_data)

        # Should synthesize CLICK
        assert release_event.type == MouseEventType.CLICK
        assert release_event.button == MouseButton.LEFT
        assert release_event.x == 10
        assert release_event.y == 5
        assert release_event.click_count == 1

    def test_click_synthesis_different_position(self):
        """Test that press and release at different positions doesn't synthesize click."""
        parser = MouseEventParser()

        # Press at (10, 5)
        press_data = b"\x1b[<0;11;6M"
        parser.parse_sgr(press_data)

        # Release at (20, 15) - far away
        release_data = b"\x1b[<0;21;16m"
        release_event = parser.parse_sgr(release_data)

        # Should NOT synthesize CLICK (too far)
        assert release_event.type == MouseEventType.RELEASE

    def test_click_synthesis_close_position(self):
        """Test that press and release within threshold synthesizes click."""
        parser = MouseEventParser(double_click_distance=2)

        # Press at (10, 5)
        press_data = b"\x1b[<0;11;6M"
        parser.parse_sgr(press_data)

        # Release at (11, 6) - within threshold
        release_data = b"\x1b[<0;12;7m"
        release_event = parser.parse_sgr(release_data)

        # Should synthesize CLICK
        assert release_event.type == MouseEventType.CLICK

    def test_double_click_synthesis(self):
        """Test that two clicks synthesize DOUBLE_CLICK event."""
        parser = MouseEventParser(double_click_threshold=1.0)

        # First click
        parser.parse_sgr(b"\x1b[<0;11;6M")  # Press
        click1 = parser.parse_sgr(b"\x1b[<0;11;6m")  # Release
        assert click1.type == MouseEventType.CLICK
        assert click1.click_count == 1

        # Second click (within time threshold)
        parser.parse_sgr(b"\x1b[<0;11;6M")  # Press
        click2 = parser.parse_sgr(b"\x1b[<0;11;6m")  # Release

        # Should synthesize DOUBLE_CLICK
        assert click2.type == MouseEventType.DOUBLE_CLICK
        assert click2.click_count == 2

    def test_double_click_different_position(self):
        """Test that clicks at different positions don't synthesize double-click."""
        parser = MouseEventParser(double_click_threshold=1.0, double_click_distance=2)

        # First click at (10, 5)
        parser.parse_sgr(b"\x1b[<0;11;6M")
        click1 = parser.parse_sgr(b"\x1b[<0;11;6m")
        assert click1.type == MouseEventType.CLICK

        # Second click at (20, 15) - far away
        parser.parse_sgr(b"\x1b[<0;21;16M")
        click2 = parser.parse_sgr(b"\x1b[<0;21;16m")

        # Should NOT synthesize DOUBLE_CLICK
        assert click2.type == MouseEventType.CLICK
        assert click2.click_count == 1

    def test_double_click_timeout(self):
        """Test that double-click times out after threshold."""
        parser = MouseEventParser(double_click_threshold=0.1)

        # First click
        parser.parse_sgr(b"\x1b[<0;11;6M")
        click1 = parser.parse_sgr(b"\x1b[<0;11;6m")
        assert click1.type == MouseEventType.CLICK

        # Wait longer than threshold
        time.sleep(0.15)

        # Second click
        parser.parse_sgr(b"\x1b[<0;11;6M")
        click2 = parser.parse_sgr(b"\x1b[<0;11;6m")

        # Should NOT synthesize DOUBLE_CLICK (timed out)
        assert click2.type == MouseEventType.CLICK
        assert click2.click_count == 1

    def test_double_click_different_button(self):
        """Test that clicks with different buttons don't synthesize double-click."""
        parser = MouseEventParser(double_click_threshold=1.0)

        # First click with left button
        parser.parse_sgr(b"\x1b[<0;11;6M")
        click1 = parser.parse_sgr(b"\x1b[<0;11;6m")
        assert click1.type == MouseEventType.CLICK

        # Second click with right button
        parser.parse_sgr(b"\x1b[<2;11;6M")
        click2 = parser.parse_sgr(b"\x1b[<2;11;6m")

        # Should NOT synthesize DOUBLE_CLICK (different button)
        assert click2.type == MouseEventType.CLICK
        assert click2.click_count == 1

    def test_get_sgr_match_length(self):
        """Test getting SGR sequence length."""
        parser = MouseEventParser()
        data = b"\x1b[<0;10;5M"

        length = parser.get_sgr_match_length(data)

        assert length == len(data)

    def test_get_sgr_match_length_no_match(self):
        """Test getting SGR sequence length with no match."""
        parser = MouseEventParser()
        data = b"invalid"

        length = parser.get_sgr_match_length(data)

        assert length is None

    def test_get_sgr_match_length_partial(self):
        """Test getting SGR sequence length with extra data."""
        parser = MouseEventParser()
        data = b"\x1b[<0;10;5Mextra"

        length = parser.get_sgr_match_length(data)

        # Should only match the SGR sequence, not the extra data
        assert length == 10  # Length of '\x1b[<0;10;5M'


class TestMouseEvent:
    """Tests for MouseEvent class."""

    def test_mouse_event_creation(self):
        """Test creating a mouse event."""
        event = MouseEvent(
            type=MouseEventType.CLICK,
            button=MouseButton.LEFT,
            x=10,
            y=5,
            shift=True,
            alt=False,
            ctrl=False,
            click_count=1,
        )

        assert event.type == MouseEventType.CLICK
        assert event.button == MouseButton.LEFT
        assert event.x == 10
        assert event.y == 5
        assert event.shift
        assert not event.alt
        assert not event.ctrl
        assert event.click_count == 1

    def test_mouse_event_str(self):
        """Test string representation of mouse event."""
        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.LEFT, x=10, y=5
        )

        s = str(event)

        assert "LEFT" in s
        assert "click" in s
        assert "(10, 5)" in s

    def test_mouse_event_str_with_modifiers(self):
        """Test string representation with modifiers."""
        event = MouseEvent(
            type=MouseEventType.CLICK,
            button=MouseButton.LEFT,
            x=10,
            y=5,
            shift=True,
            ctrl=True,
        )

        s = str(event)

        assert "Shift" in s
        assert "Ctrl" in s
        assert "LEFT" in s


class TestMouseTrackingMode:
    """Tests for MouseTrackingMode enum."""

    def test_tracking_mode_values(self):
        """Test that tracking mode enum values are correct."""
        assert MouseTrackingMode.DISABLED == 0
        assert MouseTrackingMode.X10 == 9
        assert MouseTrackingMode.NORMAL == 1000
        assert MouseTrackingMode.BUTTON_EVENT == 1002
        assert MouseTrackingMode.ANY_EVENT == 1003


class TestMouseButton:
    """Tests for MouseButton enum."""

    def test_button_values(self):
        """Test that button enum values are correct."""
        assert MouseButton.LEFT == 0
        assert MouseButton.MIDDLE == 1
        assert MouseButton.RIGHT == 2
        assert MouseButton.SCROLL_UP == 64
        assert MouseButton.SCROLL_DOWN == 65
        assert MouseButton.NONE == 255
