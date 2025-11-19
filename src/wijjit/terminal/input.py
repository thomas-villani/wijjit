"""Keyboard and mouse input handling for terminal applications.

This module provides utilities for reading and parsing keyboard and mouse input
in raw mode, including support for special keys, escape sequences, modifiers,
and ANSI mouse events. Supports both synchronous and asynchronous input reading.
"""

import asyncio
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union

from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys as PTKeys

from wijjit.logging_config import get_logger
from wijjit.terminal.mouse import MouseEvent, MouseEventParser, MouseTrackingMode

# Get logger for this module
logger = get_logger(__name__)


class KeyType(Enum):
    """Type of key press."""

    CHARACTER = auto()
    SPECIAL = auto()
    CONTROL = auto()


@dataclass(frozen=True)
class Key:
    """Represents a keyboard key press.

    Parameters
    ----------
    name : str
        Name of the key (e.g., 'a', 'enter', 'up', 'ctrl+c')
    key_type : KeyType
        Type of key press
    char : str, optional
        Character representation if applicable
    """

    name: str
    key_type: KeyType
    char: str | None = None

    def __str__(self) -> str:
        """String representation of the key.

        Returns
        -------
        str
            Key name
        """
        return self.name

    @property
    def is_char(self) -> bool:
        """Check if this is a character key.

        Returns
        -------
        bool
            True if character key
        """
        return self.key_type == KeyType.CHARACTER

    @property
    def is_special(self) -> bool:
        """Check if this is a special key.

        Returns
        -------
        bool
            True if special key
        """
        return self.key_type == KeyType.SPECIAL

    @property
    def is_control(self) -> bool:
        """Check if this is a control key.

        Returns
        -------
        bool
            True if control key
        """
        return self.key_type == KeyType.CONTROL

    @property
    def is_ctrl_c(self) -> bool:
        """Check if this is Ctrl+C.

        Returns
        -------
        bool
            True if Ctrl+C
        """
        return self.name == "ctrl+c" or (self.char == "\x03")

    @property
    def modifiers(self) -> list:
        """Get list of modifiers for this key.

        Returns
        -------
        list
            List of modifier names (e.g., ['ctrl'], ['alt'], etc.)
        """
        mods = []
        if self.key_type == KeyType.CONTROL or "ctrl+" in self.name:
            mods.append("ctrl")
        if "alt+" in self.name:
            mods.append("alt")
        if "shift+" in self.name:
            mods.append("shift")
        return mods


# Common key definitions
class Keys:
    """Common keyboard key definitions."""

    # Special keys
    ENTER = Key("enter", KeyType.SPECIAL, "\r")
    TAB = Key("tab", KeyType.SPECIAL, "\t")
    BACKTAB = Key("shift+tab", KeyType.SPECIAL)
    ESCAPE = Key("escape", KeyType.SPECIAL, "\x1b")
    BACKSPACE = Key("backspace", KeyType.SPECIAL, "\x7f")
    DELETE = Key("delete", KeyType.SPECIAL)
    SPACE = Key("space", KeyType.CHARACTER, " ")

    # Arrow keys
    UP = Key("up", KeyType.SPECIAL)
    DOWN = Key("down", KeyType.SPECIAL)
    LEFT = Key("left", KeyType.SPECIAL)
    RIGHT = Key("right", KeyType.SPECIAL)

    # Control keys
    CTRL_C = Key("ctrl+c", KeyType.CONTROL, "\x03")

    # Navigation keys
    HOME = Key("home", KeyType.SPECIAL)
    END = Key("end", KeyType.SPECIAL)
    PAGE_UP = Key("pageup", KeyType.SPECIAL)
    PAGE_DOWN = Key("pagedown", KeyType.SPECIAL)

    # Function keys
    F1 = Key("f1", KeyType.SPECIAL)
    F2 = Key("f2", KeyType.SPECIAL)
    F3 = Key("f3", KeyType.SPECIAL)
    F4 = Key("f4", KeyType.SPECIAL)
    F5 = Key("f5", KeyType.SPECIAL)
    F6 = Key("f6", KeyType.SPECIAL)
    F7 = Key("f7", KeyType.SPECIAL)
    F8 = Key("f8", KeyType.SPECIAL)
    F9 = Key("f9", KeyType.SPECIAL)
    F10 = Key("f10", KeyType.SPECIAL)
    F11 = Key("f11", KeyType.SPECIAL)
    F12 = Key("f12", KeyType.SPECIAL)

    # Additional control keys
    CTRL_D = Key("ctrl+d", KeyType.CONTROL, "\x04")
    CTRL_Z = Key("ctrl+z", KeyType.CONTROL, "\x1a")


# Multi-byte escape sequence mappings for special keys
# Maps ANSI escape sequences (2+ bytes starting with ESC) to Key objects
# Used for arrow keys, function keys, and other terminal-specific sequences
ESCAPE_SEQUENCES = {
    "\x1b[A": Keys.UP,
    "\x1b[B": Keys.DOWN,
    "\x1b[C": Keys.RIGHT,
    "\x1b[D": Keys.LEFT,
    "\x1b[H": Keys.HOME,
    "\x1b[F": Keys.END,
    "\x1b[5~": Keys.PAGE_UP,
    "\x1b[6~": Keys.PAGE_DOWN,
    "\x1b[3~": Keys.DELETE,
    "\x1bOH": Keys.HOME,  # Alternative home
    "\x1bOF": Keys.END,  # Alternative end
}

# Single-byte character mappings
# Maps single characters (including control characters) to Key objects
# Used for simple keys like Enter, Tab, and ASCII control sequences
SINGLE_CHAR_KEYS = {
    "\r": Keys.ENTER,
    "\n": Keys.ENTER,
    "\t": Keys.TAB,
    "\x1b": Keys.ESCAPE,
    "\x7f": Keys.BACKSPACE,
    "\x08": Keys.BACKSPACE,  # Alternative backspace
    " ": Keys.SPACE,
    "\x03": Keys.CTRL_C,
    "\x04": Keys.CTRL_D,
    "\x1a": Keys.CTRL_Z,
}


# Map prompt_toolkit keys to our Key objects
PROMPT_TOOLKIT_KEY_MAP = {
    PTKeys.Up: Keys.UP,
    PTKeys.Down: Keys.DOWN,
    PTKeys.Left: Keys.LEFT,
    PTKeys.Right: Keys.RIGHT,
    PTKeys.Home: Keys.HOME,
    PTKeys.End: Keys.END,
    PTKeys.PageUp: Keys.PAGE_UP,
    PTKeys.PageDown: Keys.PAGE_DOWN,
    PTKeys.Delete: Keys.DELETE,
    PTKeys.Enter: Keys.ENTER,
    PTKeys.Tab: Keys.TAB,
    PTKeys.BackTab: Keys.BACKTAB,
    PTKeys.Escape: Keys.ESCAPE,
    PTKeys.Backspace: Keys.BACKSPACE,
    PTKeys.ControlC: Keys.CTRL_C,
    PTKeys.ControlD: Keys.CTRL_D,
    PTKeys.ControlZ: Keys.CTRL_Z,
    # Control+navigation keys
    PTKeys.ControlHome: Key("ctrl+home", KeyType.SPECIAL),
    PTKeys.ControlEnd: Key("ctrl+end", KeyType.SPECIAL),
    PTKeys.ControlLeft: Key("ctrl+left", KeyType.SPECIAL),
    PTKeys.ControlRight: Key("ctrl+right", KeyType.SPECIAL),
    # Shift+navigation keys
    PTKeys.ShiftUp: Key("shift+up", KeyType.SPECIAL),
    PTKeys.ShiftDown: Key("shift+down", KeyType.SPECIAL),
    PTKeys.ShiftLeft: Key("shift+left", KeyType.SPECIAL),
    PTKeys.ShiftRight: Key("shift+right", KeyType.SPECIAL),
    PTKeys.ShiftHome: Key("shift+home", KeyType.SPECIAL),
    PTKeys.ShiftEnd: Key("shift+end", KeyType.SPECIAL),
    PTKeys.ShiftPageUp: Key("shift+pageup", KeyType.SPECIAL),
    PTKeys.ShiftPageDown: Key("shift+pagedown", KeyType.SPECIAL),
    # Control+Shift+navigation keys
    PTKeys.ControlShiftUp: Key("ctrl+shift+up", KeyType.SPECIAL),
    PTKeys.ControlShiftDown: Key("ctrl+shift+down", KeyType.SPECIAL),
    PTKeys.ControlShiftLeft: Key("ctrl+shift+left", KeyType.SPECIAL),
    PTKeys.ControlShiftRight: Key("ctrl+shift+right", KeyType.SPECIAL),
    PTKeys.ControlShiftHome: Key("ctrl+shift+home", KeyType.SPECIAL),
    PTKeys.ControlShiftEnd: Key("ctrl+shift+end", KeyType.SPECIAL),
    PTKeys.ControlShiftPageUp: Key("ctrl+shift+pageup", KeyType.SPECIAL),
    PTKeys.ControlShiftPageDown: Key("ctrl+shift+pagedown", KeyType.SPECIAL),
    # Function keys
    PTKeys.F1: Keys.F1,
    PTKeys.F2: Keys.F2,
    PTKeys.F3: Keys.F3,
    PTKeys.F4: Keys.F4,
    PTKeys.F5: Keys.F5,
    PTKeys.F6: Keys.F6,
    PTKeys.F7: Keys.F7,
    PTKeys.F8: Keys.F8,
    PTKeys.F9: Keys.F9,
    PTKeys.F10: Keys.F10,
    PTKeys.F11: Keys.F11,
    PTKeys.F12: Keys.F12,
}


class InputHandler:
    """Handles reading and parsing keyboard and mouse input using prompt_toolkit.

    This provides cross-platform keyboard input handling with support
    for special keys, escape sequences, modifiers, and ANSI mouse events.

    Parameters
    ----------
    enable_mouse : bool, optional
        Whether to enable mouse event tracking (default: False)
    mouse_tracking_mode : MouseTrackingMode, optional
        Mouse tracking mode to use if enabled (default: BUTTON_EVENT)

    Attributes
    ----------
    _input : prompt_toolkit.input.Input
        The prompt_toolkit input object
    mouse_enabled : bool
        Whether mouse tracking is currently enabled
    mouse_parser : MouseEventParser or None
        Parser for ANSI mouse event sequences
    """

    def __init__(
        self,
        enable_mouse: bool = False,
        mouse_tracking_mode: Optional["MouseTrackingMode"] = None,
    ) -> None:
        self._input = create_input()
        self._raw_mode = None

        # Mouse support
        self.mouse_enabled = enable_mouse
        self._mouse_tracking_mode = (
            mouse_tracking_mode
            if mouse_tracking_mode is not None
            else (MouseTrackingMode.BUTTON_EVENT if MouseTrackingMode else None)
        )
        self.mouse_parser = MouseEventParser() if MouseEventParser else None

        # Queue for handling lookahead keys (used for Alt detection and mouse parsing)
        self._key_queue = []

    def read_input(
        self, timeout: float | None = None
    ) -> Union[Key, "MouseEvent", None]:
        """Read a single input event (keyboard or mouse).

        This method blocks until an input event occurs (or timeout expires)
        and returns either a Key object (for keyboard input) or a MouseEvent
        object (for mouse input).

        Parameters
        ----------
        timeout : float or None, optional
            Maximum time to wait for input in seconds. If None, blocks indefinitely.
            If timeout expires with no input, returns None. Default is None.

        Returns
        -------
        Key, MouseEvent, or None
            Input event, or None on timeout/error

        Notes
        -----
        Timeout support is critical for enabling animations (spinners) and
        time-based UI updates (notification expiry) without requiring user input.

        Cross-platform implementation uses threading for timeout on Windows
        and select.select() on Unix systems.
        """
        import threading

        try:
            # Enter raw mode if not already in it
            if self._raw_mode is None:
                self._raw_mode = self._input.raw_mode()
                self._raw_mode.__enter__()

            # Check if we have a queued key from previous lookahead
            if self._key_queue:
                key_press = self._key_queue.pop(0)
                logger.debug(f"Processing queued key: {key_press.key!r}")
            else:
                # If timeout specified, use platform-appropriate timeout mechanism
                if timeout is not None:
                    # On Windows, select.select() only works with sockets, not file descriptors
                    # Use threading-based timeout for cross-platform compatibility
                    keys_result = [None]
                    read_complete = threading.Event()

                    def read_thread():
                        try:
                            keys_result[0] = self._input.read_keys()
                        except Exception as e:
                            logger.error(f"Error reading input in thread: {e}")
                            keys_result[0] = []
                        finally:
                            read_complete.set()

                    thread = threading.Thread(target=read_thread, daemon=True)
                    thread.start()

                    # Wait for read to complete or timeout
                    if read_complete.wait(timeout):
                        # Read completed within timeout
                        keys = keys_result[0]
                        if not keys:
                            return None
                    else:
                        # Timeout expired
                        logger.debug(f"read_input timeout after {timeout}s")
                        return None
                else:
                    # No timeout - blocking read
                    keys = self._input.read_keys()
                    if not keys:
                        return None

                logger.debug(
                    f"read_keys() returned {len(keys)} key(s): {[k.key for k in keys]}"
                )

                # Check for paste: multiple printable characters at once
                if len(keys) > 1:
                    # Check if all keys are regular characters (paste detection)
                    all_chars = all(
                        len(k.key) == 1 and k.key.isprintable() for k in keys
                    )
                    if all_chars:
                        # This looks like a paste operation - combine all characters
                        pasted_text = "".join(k.key for k in keys)
                        logger.debug(f"Detected paste: {pasted_text!r}")
                        # Return a synthetic paste key that includes all the text
                        return Key(pasted_text, KeyType.CHARACTER, pasted_text)

                # Check for Alt+key (escape followed immediately by a character in same read)
                if (
                    len(keys) >= 2
                    and keys[0].key == "escape"
                    and len(keys[1].key) == 1
                    and keys[1].key.isalpha()
                ):
                    alt_char = keys[1].key.lower()
                    logger.debug(f"Detected Alt+{alt_char} from multi-key sequence")
                    return Key(f"alt+{alt_char}", KeyType.CONTROL)

                key_press = keys[0]

                # Escape key: Just return it (Alt detection handled via multi-key check above)
                # Note: Some terminals send Alt+letter as separate keys with delay.
                # The multi-key check above handles the common case where they arrive together.
                # For better Alt support across all terminals, use async version which has timeout-based detection.

            # Check if this might be a mouse sequence
            # Mouse sequences start with ESC [ < (SGR format)
            # or ESC [ M (normal format)
            if self.mouse_enabled and self.mouse_parser and key_press.data:
                data_bytes = (
                    key_press.data.encode("utf-8")
                    if isinstance(key_press.data, str)
                    else key_press.data
                )

                # Try to parse as SGR mouse event
                if data_bytes.startswith(b"\x1b[<"):
                    # We have the start of an SGR sequence, but need more data
                    # Read until we get M or m (press or release)
                    buffer = bytearray(data_bytes)
                    while buffer and buffer[-1] not in (ord("M"), ord("m")):
                        more_keys = self._input.read_keys()
                        if more_keys and more_keys[0].data:
                            more_data = more_keys[0].data
                            if isinstance(more_data, str):
                                buffer.extend(more_data.encode("utf-8"))
                            else:
                                buffer.extend(more_data)
                        else:
                            break

                    mouse_event = self.mouse_parser.parse_sgr(bytes(buffer))
                    if mouse_event:
                        return mouse_event

                # Try to parse as normal format mouse event
                elif data_bytes.startswith(b"\x1b[M"):
                    # Need 6 bytes total for normal format
                    buffer = bytearray(data_bytes)
                    while len(buffer) < 6:
                        more_keys = self._input.read_keys()
                        if more_keys and more_keys[0].data:
                            more_data = more_keys[0].data
                            if isinstance(more_data, str):
                                buffer.extend(more_data.encode("utf-8"))
                            else:
                                buffer.extend(more_data)
                        else:
                            break

                    if len(buffer) >= 6:
                        mouse_event = self.mouse_parser.parse_normal(bytes(buffer))
                        if mouse_event:
                            return mouse_event

            # Not a mouse event, process as keyboard input
            logger.debug(f"Processing key: {key_press.key!r}, data: {key_press.data!r}")

            # Check if it's a mapped special key first
            if key_press.key in PROMPT_TOOLKIT_KEY_MAP:
                mapped_key = PROMPT_TOOLKIT_KEY_MAP[key_press.key]

                # Return Escape key (Alt detection handled earlier via lookahead)
                if mapped_key == Keys.ESCAPE:
                    return mapped_key

                return mapped_key

            # Check for control characters
            if key_press.key.startswith("c-") and len(key_press.key) == 3:
                ctrl_letter = key_press.key[2]
                char = chr(ord(ctrl_letter) - ord("a") + 1)
                return Key(f"ctrl+{ctrl_letter}", KeyType.CONTROL, char)

            # Regular character
            if key_press.data:
                char = key_press.data
                if char == " ":
                    return Keys.SPACE
                return Key(char, KeyType.CHARACTER, char)

            return None

        except (EOFError, KeyboardInterrupt, IndexError) as e:
            logger.debug(f"Input read terminated: {type(e).__name__}")
            return None

    async def read_input_async(
        self, timeout: float | None = None
    ) -> Union[Key, "MouseEvent", None]:
        """Read a single input event asynchronously (keyboard or mouse).

        This method uses asyncio to handle input reading without blocking
        the event loop, making it suitable for async applications.

        Parameters
        ----------
        timeout : float or None, optional
            Maximum time to wait for input in seconds. If None, blocks indefinitely.
            If timeout expires with no input, returns None. Default is None.

        Returns
        -------
        Key, MouseEvent, or None
            Input event, or None on timeout/error

        Notes
        -----
        This async version properly integrates with asyncio event loops,
        allowing other async tasks to run while waiting for input.
        """
        loop = asyncio.get_event_loop()

        try:
            # Enter raw mode if not already in it
            if self._raw_mode is None:
                self._raw_mode = self._input.raw_mode()
                self._raw_mode.__enter__()

            # Check if we have a queued key from previous lookahead
            if self._key_queue:
                key_press = self._key_queue.pop(0)
                logger.debug(f"Processing queued key: {key_press.key!r}")
            else:
                # Read input asynchronously
                if timeout is not None:
                    # Use asyncio.wait_for for timeout
                    try:
                        keys = await asyncio.wait_for(
                            loop.run_in_executor(None, self._input.read_keys),
                            timeout=timeout,
                        )
                        if not keys:
                            return None
                    except TimeoutError:
                        logger.debug(f"read_input_async timeout after {timeout}s")
                        return None
                else:
                    # No timeout - wait indefinitely
                    keys = await loop.run_in_executor(None, self._input.read_keys)
                    if not keys:
                        return None

                logger.debug(
                    f"read_keys() returned {len(keys)} key(s): {[k.key for k in keys]}"
                )

                # Check for paste: multiple printable characters at once
                if len(keys) > 1:
                    # Check if all keys are regular characters (paste detection)
                    all_chars = all(
                        len(k.key) == 1 and k.key.isprintable() for k in keys
                    )
                    if all_chars:
                        # This looks like a paste operation - combine all characters
                        pasted_text = "".join(k.key for k in keys)
                        logger.debug(f"Detected paste: {pasted_text!r}")
                        # Return a synthetic paste key that includes all the text
                        return Key(pasted_text, KeyType.CHARACTER, pasted_text)

                # Check for Alt+key (escape followed immediately by a character in same read)
                if (
                    len(keys) >= 2
                    and keys[0].key == "escape"
                    and len(keys[1].key) == 1
                    and keys[1].key.isalpha()
                ):
                    alt_char = keys[1].key.lower()
                    logger.debug(f"Detected Alt+{alt_char} from multi-key sequence")
                    return Key(f"alt+{alt_char}", KeyType.CONTROL)

                key_press = keys[0]

                # If this is Escape, use timeout to check for Alt+key sequence
                if key_press.key == "escape":
                    logger.debug("Saw Escape, checking for Alt+key with timeout...")
                    # Use small timeout (50ms) to distinguish Escape from Alt+key
                    # Alt+key typically arrives within a few milliseconds
                    try:
                        next_keys = await asyncio.wait_for(
                            loop.run_in_executor(None, self._input.read_keys),
                            timeout=0.05,  # 50ms timeout
                        )
                        if next_keys:
                            next_key = next_keys[0]
                            logger.debug(f"Next key after Escape: {next_key.key!r}")
                            # If next key is a letter, return Alt+letter
                            if len(next_key.key) == 1 and next_key.key.isalpha():
                                alt_char = next_key.key.lower()
                                logger.debug(
                                    f"Detected Alt+{alt_char} via timeout lookahead"
                                )
                                return Key(f"alt+{alt_char}", KeyType.CONTROL)
                            else:
                                # Not Alt+key, queue the next key for later and return Escape
                                logger.debug(
                                    f"Not Alt+key, queueing {next_key.key!r} for next read"
                                )
                                self._key_queue.append(next_key)
                                # Fall through to return Escape normally
                    except TimeoutError:
                        # Timeout expired - it's a standalone Escape key
                        logger.debug("Timeout expired, returning standalone Escape")
                        # Fall through to return Escape normally

            # Check if this might be a mouse sequence
            # Mouse sequences start with ESC [ < (SGR format)
            # or ESC [ M (normal format)
            if self.mouse_enabled and self.mouse_parser and key_press.data:
                data_bytes = (
                    key_press.data.encode("utf-8")
                    if isinstance(key_press.data, str)
                    else key_press.data
                )

                # Try to parse as SGR mouse event
                if data_bytes.startswith(b"\x1b[<"):
                    # We have the start of an SGR sequence, but need more data
                    # Read until we get M or m (press or release)
                    buffer = bytearray(data_bytes)
                    while buffer and buffer[-1] not in (ord("M"), ord("m")):
                        more_keys = await loop.run_in_executor(
                            None, self._input.read_keys
                        )
                        if more_keys and more_keys[0].data:
                            more_data = more_keys[0].data
                            if isinstance(more_data, str):
                                buffer.extend(more_data.encode("utf-8"))
                            else:
                                buffer.extend(more_data)
                        else:
                            break

                    mouse_event = self.mouse_parser.parse_sgr(bytes(buffer))
                    if mouse_event:
                        return mouse_event

                # Try to parse as normal format mouse event
                elif data_bytes.startswith(b"\x1b[M"):
                    # Need 6 bytes total for normal format
                    buffer = bytearray(data_bytes)
                    while len(buffer) < 6:
                        more_keys = await loop.run_in_executor(
                            None, self._input.read_keys
                        )
                        if more_keys and more_keys[0].data:
                            more_data = more_keys[0].data
                            if isinstance(more_data, str):
                                buffer.extend(more_data.encode("utf-8"))
                            else:
                                buffer.extend(more_data)
                        else:
                            break

                    if len(buffer) >= 6:
                        mouse_event = self.mouse_parser.parse_normal(bytes(buffer))
                        if mouse_event:
                            return mouse_event

            # Not a mouse event, process as keyboard input
            logger.debug(f"Processing key: {key_press.key!r}, data: {key_press.data!r}")

            # Check if it's a mapped special key first
            if key_press.key in PROMPT_TOOLKIT_KEY_MAP:
                mapped_key = PROMPT_TOOLKIT_KEY_MAP[key_press.key]

                # Return Escape key (Alt detection handled earlier via lookahead)
                if mapped_key == Keys.ESCAPE:
                    return mapped_key

                return mapped_key

            # Check for control characters
            if key_press.key.startswith("c-") and len(key_press.key) == 3:
                ctrl_letter = key_press.key[2]
                char = chr(ord(ctrl_letter) - ord("a") + 1)
                return Key(f"ctrl+{ctrl_letter}", KeyType.CONTROL, char)

            # Regular character
            if key_press.data:
                char = key_press.data
                if char == " ":
                    return Keys.SPACE
                return Key(char, KeyType.CHARACTER, char)

            return None

        except (EOFError, KeyboardInterrupt, IndexError) as e:
            logger.debug(f"Input read terminated: {type(e).__name__}")
            return None

    def read_key(self) -> Key | None:
        """Read a single key press.

        This method blocks until a key is pressed and returns a Key object
        representing the pressed key. Mouse events are ignored.

        Returns
        -------
        Key or None
            Key object representing the key press, or None on error
        """
        # Use read_input() and filter for keyboard only
        while True:
            event = self.read_input()
            if event is None:
                return None
            if isinstance(event, Key):
                return event
            # Skip mouse events and keep reading

    def enable_mouse_tracking(self, mode: Optional["MouseTrackingMode"] = None) -> None:
        """Enable mouse event tracking.

        Sends ANSI escape sequences to enable mouse tracking in the terminal.

        Parameters
        ----------
        mode : MouseTrackingMode, optional
            Tracking mode to use (default: uses mode from constructor)
        """
        if not MouseTrackingMode:
            return  # Mouse module not available

        if mode is not None:
            self._mouse_tracking_mode = mode

        if self._mouse_tracking_mode is None:
            return

        # Enable mouse tracking mode
        sys.stdout.write(f"\033[?{self._mouse_tracking_mode}h")
        # Enable SGR extended mouse mode (better coordinate handling)
        sys.stdout.write("\033[?1006h")
        sys.stdout.flush()

        self.mouse_enabled = True

    def disable_mouse_tracking(self) -> None:
        """Disable mouse event tracking.

        Sends ANSI escape sequences to disable mouse tracking in the terminal.
        """
        if not self.mouse_enabled or self._mouse_tracking_mode is None:
            return

        # Disable mouse tracking mode
        sys.stdout.write(f"\033[?{self._mouse_tracking_mode}l")
        # Disable SGR extended mouse mode
        sys.stdout.write("\033[?1006l")
        sys.stdout.flush()

        self.mouse_enabled = False

    def close(self) -> None:
        """Close the input handler and clean up resources."""
        # Disable mouse tracking if enabled
        self.disable_mouse_tracking()

        # Exit raw mode if we entered it
        if self._raw_mode is not None:
            try:
                self._raw_mode.__exit__(None, None, None)
            except Exception as e:
                logger.debug(f"Error exiting raw mode during cleanup: {e}")
            self._raw_mode = None

        if self._input:
            self._input.close()

    def cleanup(self) -> None:
        """Clean up input handler state.

        This ensures resources are properly released.
        """
        self.close()
