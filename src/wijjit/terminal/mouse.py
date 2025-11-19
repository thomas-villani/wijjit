"""Mouse event handling for terminal applications.

This module provides mouse event parsing and handling for ANSI terminal
mouse escape sequences. It supports both modern SGR format and legacy
normal format mouse events.

The module handles:
- Mouse button press/release/click events
- Mouse wheel scrolling
- Mouse movement and drag events
- Modifier keys (Shift, Alt, Ctrl)
- Click and double-click synthesis
"""

import re
import time
from dataclasses import dataclass
from enum import Enum, IntEnum


class MouseTrackingMode(IntEnum):
    """Mouse tracking modes for ANSI terminals.

    These correspond to the different mouse tracking modes that can be
    enabled via escape sequences.
    """

    DISABLED = 0
    X10 = 9  # Only button press, limited coordinates
    NORMAL = 1000  # Press and release
    BUTTON_EVENT = 1002  # Press, release, and drag
    ANY_EVENT = 1003  # All mouse motion (including hover)


class MouseButton(IntEnum):
    """Mouse button identifiers.

    These map to the button codes in ANSI mouse event sequences.
    """

    LEFT = 0
    MIDDLE = 1
    RIGHT = 2
    SCROLL_UP = 64
    SCROLL_DOWN = 65
    NONE = 255  # Motion without button pressed


class MouseEventType(Enum):
    """Types of mouse events.

    These represent high-level mouse event types that can be generated
    from ANSI mouse sequences.
    """

    PRESS = "press"  # Button pressed
    RELEASE = "release"  # Button released
    DRAG = "drag"  # Movement with button pressed
    MOVE = "move"  # Movement without button
    SCROLL = "scroll"  # Mouse wheel scrolling
    CLICK = "click"  # Synthesized from press+release
    DOUBLE_CLICK = "double_click"  # Synthesized from two clicks


@dataclass
class MouseEvent:
    """Represents a mouse event.

    Parameters
    ----------
    type : MouseEventType
        Type of mouse event
    button : MouseButton
        Button that triggered the event
    x : int
        Column position (0-based)
    y : int
        Row position (0-based)
    shift : bool, optional
        Whether Shift key was pressed (default: False)
    alt : bool, optional
        Whether Alt key was pressed (default: False)
    ctrl : bool, optional
        Whether Ctrl key was pressed (default: False)
    click_count : int, optional
        Number of clicks for click events (1=single, 2=double) (default: 0)

    Attributes
    ----------
    type : MouseEventType
        Type of mouse event
    button : MouseButton
        Button that triggered the event
    x : int
        Column position (0-based)
    y : int
        Row position (0-based)
    shift : bool
        Whether Shift key was pressed
    alt : bool
        Whether Alt key was pressed
    ctrl : bool
        Whether Ctrl key was pressed
    click_count : int
        Number of clicks for click events
    """

    type: MouseEventType
    button: MouseButton
    x: int
    y: int
    shift: bool = False
    alt: bool = False
    ctrl: bool = False
    click_count: int = 0

    def __str__(self) -> str:
        """String representation of mouse event.

        Returns
        -------
        str
            Human-readable event description
        """
        mods = []
        if self.shift:
            mods.append("Shift")
        if self.alt:
            mods.append("Alt")
        if self.ctrl:
            mods.append("Ctrl")

        mod_str = "+".join(mods) + "+" if mods else ""
        return f"{mod_str}{self.button.name} {self.type.value} at ({self.x}, {self.y})"


class MouseEventParser:
    """Parser for ANSI mouse event sequences.

    This class parses both SGR (modern) and normal (legacy) ANSI mouse
    event sequences and synthesizes high-level events like clicks and
    double-clicks.

    Parameters
    ----------
    double_click_threshold : float, optional
        Maximum time between clicks for double-click (default: 0.5 seconds)
    double_click_distance : int, optional
        Maximum distance between clicks for double-click (default: 2 pixels)

    Attributes
    ----------
    double_click_threshold : float
        Maximum time between clicks for double-click in seconds
    double_click_distance : int
        Maximum Manhattan distance between clicks for double-click
    """

    # SGR mouse format: ESC [ < button ; x ; y M/m
    # M = press, m = release
    SGR_PATTERN = re.compile(rb"\x1b\[<(\d+);(\d+);(\d+)([Mm])")

    # Normal mouse format: ESC [ M bxy
    # b, x, y are encoded as bytes (value + 32)
    NORMAL_PREFIX = b"\x1b[M"

    def __init__(
        self, double_click_threshold: float = 0.5, double_click_distance: int = 2
    ) -> None:
        self.double_click_threshold = double_click_threshold
        self.double_click_distance = double_click_distance

        # State for click synthesis
        self._last_press: tuple[MouseButton, int, int, float] | None = None
        self._last_click_time: float | None = None
        self._last_click_pos: tuple[int, int] | None = None
        self._last_click_button: MouseButton | None = None

    def parse_sgr(self, data: bytes) -> MouseEvent | None:
        """Parse SGR format mouse event sequence.

        SGR format is the modern, preferred format that supports extended
        coordinates and clear press/release distinction.

        Format: ESC [ < button ; x ; y M/m
        Where M = press, m = release

        Parameters
        ----------
        data : bytes
            Raw byte sequence to parse

        Returns
        -------
        MouseEvent or None
            Parsed mouse event, or None if not a valid SGR sequence
        """
        match = self.SGR_PATTERN.match(data)
        if not match:
            return None

        button_code = int(match.group(1))
        x = int(match.group(2)) - 1  # Convert to 0-based
        y = int(match.group(3)) - 1  # Convert to 0-based
        is_release = match.group(4) == b"m"

        return self._decode_event(button_code, x, y, is_release)

    def parse_normal(self, data: bytes) -> MouseEvent | None:
        """Parse normal (legacy) format mouse event sequence.

        Normal format uses printable ASCII encoding and has coordinate
        limitations (max 223 columns/rows).

        Format: ESC [ M bxy
        Where b, x, y are encoded as (value + 32)

        Parameters
        ----------
        data : bytes
            Raw byte sequence to parse

        Returns
        -------
        MouseEvent or None
            Parsed mouse event, or None if not a valid normal sequence
        """
        if len(data) < 6 or not data.startswith(self.NORMAL_PREFIX):
            return None

        button_code = data[3] - 32  # Decode from printable ASCII
        x = data[4] - 33  # Convert to 0-based (offset is 33 not 32)
        y = data[5] - 33  # Convert to 0-based

        # In normal mode, button 3 indicates release
        is_release = (button_code & 3) == 3

        return self._decode_event(button_code, x, y, is_release)

    def _decode_event(
        self, button_code: int, x: int, y: int, is_release: bool
    ) -> MouseEvent:
        """Decode button code into mouse event.

        The button code encodes:
        - Bits 0-1: Base button (0=left, 1=middle, 2=right, 3=release)
        - Bit 2: Shift modifier
        - Bit 3: Alt modifier
        - Bit 4: Ctrl modifier
        - Bit 5: Motion flag (drag/move)
        - Bits 6-7: Scroll flag (for wheel events)

        Parameters
        ----------
        button_code : int
            Encoded button code from ANSI sequence
        x : int
            Column position (0-based)
        y : int
            Row position (0-based)
        is_release : bool
            Whether this is a button release event

        Returns
        -------
        MouseEvent
            Decoded mouse event with synthesized click events
        """
        # Extract modifiers from bits 2-4
        shift = bool(button_code & 4)
        alt = bool(button_code & 8)
        ctrl = bool(button_code & 16)

        # Extract motion flag from bit 5
        motion = bool(button_code & 32)

        # Extract base button from bits 0-1
        base_button = button_code & 3

        # Check for scroll events (bit 6 set)
        if button_code & 64:
            # Scroll events use base_button to indicate direction
            button = (
                MouseButton.SCROLL_UP if base_button == 0 else MouseButton.SCROLL_DOWN
            )
            event_type = MouseEventType.SCROLL
        else:
            # Regular button events
            if base_button < 3:
                button = MouseButton(base_button)
            else:
                button = MouseButton.NONE

            # Determine event type
            if motion:
                event_type = (
                    MouseEventType.DRAG
                    if button != MouseButton.NONE
                    else MouseEventType.MOVE
                )
            elif is_release:
                event_type = MouseEventType.RELEASE
            else:
                event_type = MouseEventType.PRESS

        # Create base event
        event = MouseEvent(
            type=event_type, button=button, x=x, y=y, shift=shift, alt=alt, ctrl=ctrl
        )

        # Synthesize click events from press/release pairs
        event = self._synthesize_clicks(event)

        return event

    def _synthesize_clicks(self, event: MouseEvent) -> MouseEvent:
        """Synthesize click and double-click events.

        Tracks press/release pairs to generate CLICK events, and tracks
        click timing to generate DOUBLE_CLICK events.

        Parameters
        ----------
        event : MouseEvent
            Input event (PRESS or RELEASE)

        Returns
        -------
        MouseEvent
            Potentially modified event (CLICK or DOUBLE_CLICK instead of RELEASE)
        """
        current_time = time.time()

        if event.type == MouseEventType.PRESS:
            # Record press for later click synthesis
            self._last_press = (event.button, event.x, event.y, current_time)

        elif event.type == MouseEventType.RELEASE and self._last_press:
            press_button, press_x, press_y, press_time = self._last_press

            # Check if release matches the press (same button, close position)
            distance = abs(event.x - press_x) + abs(event.y - press_y)

            if distance <= self.double_click_distance and event.button == press_button:
                # This is a click!
                event = MouseEvent(
                    type=MouseEventType.CLICK,
                    button=event.button,
                    x=event.x,
                    y=event.y,
                    shift=event.shift,
                    alt=event.alt,
                    ctrl=event.ctrl,
                    click_count=1,
                )

                # Check for double-click
                if (
                    self._last_click_time is not None
                    and self._last_click_pos is not None
                    and self._last_click_button == event.button
                ):

                    time_diff = current_time - self._last_click_time
                    last_x, last_y = self._last_click_pos
                    last_distance = abs(event.x - last_x) + abs(event.y - last_y)

                    if (
                        time_diff < self.double_click_threshold
                        and last_distance <= self.double_click_distance
                    ):
                        # This is a double-click!
                        event = MouseEvent(
                            type=MouseEventType.DOUBLE_CLICK,
                            button=event.button,
                            x=event.x,
                            y=event.y,
                            shift=event.shift,
                            alt=event.alt,
                            ctrl=event.ctrl,
                            click_count=2,
                        )
                        # Reset double-click tracking
                        self._last_click_time = None
                        self._last_click_pos = None
                        self._last_click_button = None
                    else:
                        # Record this click for potential double-click
                        self._last_click_time = current_time
                        self._last_click_pos = (event.x, event.y)
                        self._last_click_button = event.button
                else:
                    # First click, record for potential double-click
                    self._last_click_time = current_time
                    self._last_click_pos = (event.x, event.y)
                    self._last_click_button = event.button

            # Clear press state
            self._last_press = None

        return event

    def get_sgr_match_length(self, data: bytes) -> int | None:
        """Get the length of an SGR mouse sequence if present.

        This is useful for knowing how many bytes to consume from an
        input buffer after parsing.

        Parameters
        ----------
        data : bytes
            Data buffer that might contain SGR sequence

        Returns
        -------
        int or None
            Length of SGR sequence in bytes, or None if not found
        """
        match = self.SGR_PATTERN.match(data)
        if match:
            return len(match.group(0))
        return None
