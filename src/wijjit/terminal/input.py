"""Keyboard and mouse input handling for terminal applications.

This module provides utilities for reading and parsing keyboard and mouse input
in raw mode, including support for special keys, escape sequences, modifiers,
and ANSI mouse events. Supports both synchronous and asynchronous input reading.
"""

import asyncio
import queue
import sys
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Union

from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys as PTKeys

from wijjit.logging_config import get_logger
from wijjit.terminal.mouse import MouseEvent, MouseEventParser, MouseTrackingMode

# Get logger for this module
logger = get_logger(__name__)

# Maximum paste size to prevent infinite loop from malicious/stuck input
MAX_PASTE_SIZE = 1_000_000


class _ReaderError:
    """Sentinel object to signal fatal error from reader thread.

    This distinguishes between timeout (queue.Empty) and fatal error
    (reader thread crashed). Used internally by InputHandler.
    """

    def __init__(self, exception: BaseException | None = None):
        self.exception = exception

    def __repr__(self) -> str:
        return f"_ReaderError({self.exception!r})"


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
    def modifiers(self) -> list[str]:
        """Get list of modifiers for this key.

        Returns
        -------
        list
            List of modifier names (e.g., ['ctrl'], ['alt'], etc.)
        """
        mods: list[str] = []
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
    CTRL_SPACE = Key("ctrl+space", KeyType.CONTROL, "\x00")


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
    "\x00": Keys.CTRL_SPACE,  # Ctrl+Space (NUL character)
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
    PTKeys.ControlM: Keys.ENTER,  # Ctrl+M is Enter (carriage return)
    PTKeys.Tab: Keys.TAB,
    PTKeys.ControlI: Keys.TAB,  # Ctrl+I is Tab
    PTKeys.BackTab: Keys.BACKTAB,
    PTKeys.Escape: Keys.ESCAPE,
    PTKeys.Backspace: Keys.BACKSPACE,
    PTKeys.ControlC: Keys.CTRL_C,
    PTKeys.ControlD: Keys.CTRL_D,
    PTKeys.ControlZ: Keys.CTRL_Z,
    PTKeys.ControlAt: Keys.CTRL_SPACE,  # Ctrl+Space (Ctrl+@ = NUL)
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
        mouse_tracking_mode: "MouseTrackingMode | None" = None,
    ) -> None:
        self._input = create_input()
        self._raw_mode: Any | None = None

        # Mouse support
        # Note: mouse_enabled tracks whether mouse tracking is ACTIVE on the terminal
        # (i.e., escape sequences have been sent). _wants_mouse tracks whether
        # mouse support is requested via config.
        self._wants_mouse = enable_mouse
        self.mouse_enabled = False  # Will be True after enable_mouse_tracking()
        self._mouse_tracking_mode = (
            mouse_tracking_mode
            if mouse_tracking_mode is not None
            else MouseTrackingMode.BUTTON_EVENT
        )
        self.mouse_parser = MouseEventParser()

        # Queue for handling lookahead keys (used for Alt detection and mouse parsing)
        self._key_queue: list[Any] = []

        # Queue-based input reading to avoid thread leaks
        # This queue receives raw key lists from prompt_toolkit
        self._input_queue: queue.Queue[Any] = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._shutdown: threading.Event = threading.Event()
        self._reader_lock: threading.Lock = threading.Lock()

    def _ensure_reader_thread(self) -> None:
        """Ensure the persistent reader thread is running.

        This method starts a single background thread that continuously
        reads from prompt_toolkit and pushes results to a queue. This
        avoids spawning new threads for every timeout-based read.
        """
        with self._reader_lock:
            if self._reader_thread is None or not self._reader_thread.is_alive():
                self._shutdown.clear()

                def reader_loop() -> None:
                    while not self._shutdown.is_set():
                        try:
                            keys = self._input.read_keys()
                            if keys:
                                self._input_queue.put(keys)
                        except KeyboardInterrupt as e:
                            # KeyboardInterrupt is expected/normal termination
                            logger.debug(
                                "Reader thread interrupted by KeyboardInterrupt"
                            )
                            self._input_queue.put(_ReaderError(e))
                            break
                        except Exception as e:
                            # Unexpected exceptions are actual errors
                            logger.error(f"Error in reader thread: {e}", exc_info=True)
                            # On error, put sentinel to signal error condition
                            self._input_queue.put(_ReaderError(e))
                            break

                self._reader_thread = threading.Thread(
                    target=reader_loop, daemon=True, name="InputReaderThread"
                )
                self._reader_thread.start()
                logger.debug("Started persistent input reader thread")

    def _get_keys_from_queue(self, timeout: float | None = None) -> list[Any] | None:
        """Get keys from the input queue in a thread-safe manner.

        This method should be used instead of directly calling _input.read_keys()
        to ensure all input reading goes through the reader thread.

        Parameters
        ----------
        timeout : float or None
            Maximum time to wait in seconds. None blocks indefinitely.

        Returns
        -------
        list or None
            List of key presses, or None on timeout/error.
        """
        self._ensure_reader_thread()
        try:
            keys = self._input_queue.get(timeout=timeout)
            if isinstance(keys, _ReaderError):
                logger.debug(f"Reader thread error: {keys.exception}")
                return None
            return list(keys)
        except queue.Empty:
            return None

    async def _get_keys_from_queue_async(
        self, timeout: float | None = None
    ) -> list[Any] | None:
        """Get keys from the input queue asynchronously in a thread-safe manner.

        This method should be used instead of directly calling _input.read_keys()
        to ensure all input reading goes through the reader thread.

        Parameters
        ----------
        timeout : float or None
            Maximum time to wait in seconds. None blocks indefinitely.

        Returns
        -------
        list or None
            List of key presses, or None on timeout/error.
        """
        self._ensure_reader_thread()
        loop = asyncio.get_event_loop()
        try:
            keys = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._input_queue.get, True, timeout or None
                ),
                timeout=timeout,
            )
            if isinstance(keys, _ReaderError):
                logger.debug(f"Reader thread error: {keys.exception}")
                return None
            return list(keys)
        except (TimeoutError, queue.Empty):
            return None

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

        This implementation uses a persistent reader thread with a queue to
        avoid spawning new threads for every timeout-based read, preventing
        thread leaks.
        """
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
                # Ensure persistent reader thread is running
                self._ensure_reader_thread()

                # Read from queue with timeout
                try:
                    keys = self._input_queue.get(timeout=timeout)
                    if isinstance(keys, _ReaderError):
                        # Fatal error signaled by reader thread
                        logger.debug(f"Reader thread error: {keys.exception}")
                        return None
                except queue.Empty:
                    # Timeout expired
                    logger.debug(f"read_input timeout after {timeout}s")
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
                        # Use time-based aggregation to handle large pastes split across batches
                        paste_chars = [k.key for k in keys]
                        logger.debug(f"Detected paste start: {len(paste_chars)} chars")

                        # Continue aggregating with short timeout (20ms window)
                        # Apply MAX_PASTE_SIZE limit to prevent infinite loop
                        while len(paste_chars) < MAX_PASTE_SIZE:
                            more_keys = self._get_keys_from_queue(timeout=0.02)
                            if not more_keys:
                                break  # Timeout - no more paste data
                            # Check if all keys in this batch are also printable
                            batch_all_chars = all(
                                len(k.key) == 1 and k.key.isprintable()
                                for k in more_keys
                            )
                            if batch_all_chars:
                                paste_chars.extend(k.key for k in more_keys)
                                logger.debug(
                                    f"Paste continuation: +{len(more_keys)} chars"
                                )
                            else:
                                # Non-printable arrived, queue for later and stop
                                for k in more_keys:
                                    self._key_queue.append(k)
                                break

                        if len(paste_chars) >= MAX_PASTE_SIZE:
                            logger.warning(f"Paste truncated at {MAX_PASTE_SIZE} chars")

                        pasted_text = "".join(paste_chars)
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
                    # Use queue-based read for thread safety
                    next_keys = self._get_keys_from_queue(timeout=0.05)
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
                    else:
                        # Timeout expired - it's a standalone Escape key
                        logger.debug("Timeout expired, returning standalone Escape")
                        # Fall through to return Escape normally

            # Check if this might be a mouse sequence
            # Mouse sequences start with ESC [ < (SGR format)
            # or ESC [ M (normal format)
            if self.mouse_enabled and self.mouse_parser and key_press.data:
                # Windows console mouse: prompt_toolkit's Win32 input delivers
                # the whole event as a ";"-delimited string in a single KeyPress
                # (e.g. "LEFT;MOUSE_DOWN;13;6") rather than a vt100 escape
                # sequence, so no byte buffering or lookahead is needed.
                if key_press.key == PTKeys.WindowsMouseEvent:
                    mouse_event = self.mouse_parser.parse_windows(key_press.data)
                    if mouse_event:
                        return mouse_event
                    # Unrecognized payload: swallow it instead of letting it fall
                    # through and be injected as a junk character key.
                    return None

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
                        # Use queue-based read for thread safety (100ms timeout)
                        more_keys = self._get_keys_from_queue(timeout=0.1)
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
                        # Use queue-based read for thread safety (100ms timeout)
                        more_keys = self._get_keys_from_queue(timeout=0.1)
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
            if key_press.key.startswith("c-"):
                # Handle Ctrl+Space (c-@ or c-space)
                if key_press.key in ("c-@", "c-space"):
                    return Keys.CTRL_SPACE
                # Handle standard control keys
                ctrl_part = key_press.key[2:]
                if len(ctrl_part) == 1:
                    # Single character control key
                    ctrl_letter = ctrl_part
                    # Only calculate control char for letters a-z
                    if ctrl_letter.isalpha():
                        char = chr(ord(ctrl_letter.lower()) - ord("a") + 1)
                    else:
                        # For non-letters (/, @, etc.), use the character itself
                        char = ctrl_letter
                    return Key(f"ctrl+{ctrl_letter}", KeyType.CONTROL, char)
                else:
                    # Multi-character control key (e.g., c-space, c-left)
                    return Key(
                        f"ctrl+{ctrl_part}", KeyType.CONTROL, key_press.data or ""
                    )

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

        This implementation uses a persistent reader thread with a queue to
        avoid spawning new executor tasks for every timeout-based read,
        preventing task leaks.
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
                # Ensure persistent reader thread is running
                self._ensure_reader_thread()

                # Read from queue asynchronously with timeout
                try:
                    keys = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, self._input_queue.get, True, timeout or None
                        ),
                        timeout=timeout,
                    )
                    if isinstance(keys, _ReaderError):
                        # Fatal error signaled by reader thread
                        logger.debug(f"Reader thread error: {keys.exception}")
                        return None
                except (TimeoutError, queue.Empty):
                    logger.debug(f"read_input_async timeout after {timeout}s")
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
                        # Use time-based aggregation to handle large pastes split across batches
                        paste_chars = [k.key for k in keys]
                        logger.debug(f"Detected paste start: {len(paste_chars)} chars")

                        # Continue aggregating with short timeout (20ms window)
                        while True:
                            more_keys = await self._get_keys_from_queue_async(
                                timeout=0.02
                            )
                            if not more_keys:
                                break  # Timeout - no more paste data
                            # Check if all keys in this batch are also printable
                            batch_all_chars = all(
                                len(k.key) == 1 and k.key.isprintable()
                                for k in more_keys
                            )
                            if batch_all_chars:
                                paste_chars.extend(k.key for k in more_keys)
                                logger.debug(
                                    f"Paste continuation: +{len(more_keys)} chars"
                                )
                            else:
                                # Non-printable arrived, queue for later and stop
                                for k in more_keys:
                                    self._key_queue.append(k)
                                break

                        pasted_text = "".join(paste_chars)
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
                    # Use queue-based read for thread safety
                    next_keys = await self._get_keys_from_queue_async(timeout=0.05)
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
                    else:
                        # Timeout expired - it's a standalone Escape key
                        logger.debug("Timeout expired, returning standalone Escape")
                        # Fall through to return Escape normally

            # Check if this might be a mouse sequence
            # Mouse sequences start with ESC [ < (SGR format)
            # or ESC [ M (normal format)
            if self.mouse_enabled and self.mouse_parser and key_press.data:
                # Windows console mouse: prompt_toolkit's Win32 input delivers
                # the whole event as a ";"-delimited string in a single KeyPress
                # (e.g. "LEFT;MOUSE_DOWN;13;6") rather than a vt100 escape
                # sequence, so no byte buffering or lookahead is needed.
                if key_press.key == PTKeys.WindowsMouseEvent:
                    mouse_event = self.mouse_parser.parse_windows(key_press.data)
                    if mouse_event:
                        return mouse_event
                    # Unrecognized payload: swallow it instead of letting it fall
                    # through and be injected as a junk character key.
                    return None

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
                        # Use queue-based read for thread safety (100ms timeout)
                        more_keys = await self._get_keys_from_queue_async(timeout=0.1)
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
                        # Use queue-based read for thread safety (100ms timeout)
                        more_keys = await self._get_keys_from_queue_async(timeout=0.1)
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
            if key_press.key.startswith("c-"):
                # Handle Ctrl+Space (c-@ or c-space)
                if key_press.key in ("c-@", "c-space"):
                    return Keys.CTRL_SPACE
                # Handle standard control keys
                ctrl_part = key_press.key[2:]
                if len(ctrl_part) == 1:
                    # Single character control key
                    ctrl_letter = ctrl_part
                    # Only calculate control char for letters a-z
                    if ctrl_letter.isalpha():
                        char = chr(ord(ctrl_letter.lower()) - ord("a") + 1)
                    else:
                        # For non-letters (/, @, etc.), use the character itself
                        char = ctrl_letter
                    return Key(f"ctrl+{ctrl_letter}", KeyType.CONTROL, char)
                else:
                    # Multi-character control key (e.g., c-space, c-left)
                    return Key(
                        f"ctrl+{ctrl_part}", KeyType.CONTROL, key_press.data or ""
                    )

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

    def close(self) -> None:
        """Close the input handler and clean up all resources.

        This method should be called when the InputHandler is no longer
        needed to ensure proper cleanup of background threads, mouse
        tracking, raw mode, and input resources.
        """
        logger.debug("Shutting down input handler")

        # Shutdown persistent reader thread
        self._shutdown.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
            if self._reader_thread.is_alive():
                logger.warning("Reader thread did not terminate within timeout")

        # Disable mouse tracking if enabled
        if self.mouse_enabled:
            try:
                self.disable_mouse_tracking()
            except Exception as e:
                logger.debug(f"Error disabling mouse tracking: {e}")

        # Exit raw mode if active
        if self._raw_mode is not None:
            try:
                self._raw_mode.__exit__(None, None, None)
            except Exception as e:
                logger.debug(f"Error exiting raw mode during cleanup: {e}")
            self._raw_mode = None

        # Close the input
        if self._input:
            try:
                self._input.close()
            except Exception as e:
                logger.debug(f"Error closing input: {e}")

    def __del__(self) -> None:
        """Cleanup when InputHandler is garbage collected."""
        try:
            self.close()
        except Exception:
            # Avoid errors during garbage collection
            pass

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

    def enable_mouse_tracking(self, mode: "MouseTrackingMode | None" = None) -> None:
        """Enable mouse event tracking.

        Sends ANSI escape sequences to enable mouse tracking in the terminal.

        Parameters
        ----------
        mode : MouseTrackingMode, optional
            Tracking mode to use (default: uses mode from constructor)
        """
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

    def cleanup(self) -> None:
        """Clean up input handler state.

        This ensures resources are properly released.
        """
        self.close()
