"""Alternate screen buffer management for terminal applications.

This module provides utilities for managing the terminal's alternate screen buffer,
which allows TUI applications to run without disturbing the user's terminal history.
"""

import sys
from contextlib import contextmanager
from typing import TextIO

from .ansi import ANSIScreen, ANSICursor


class ScreenManager:
    """Manages terminal screen state and alternate buffer.

    This class handles entering/exiting alternate screen mode, cursor visibility,
    and screen clearing operations.

    Parameters
    ----------
    output : TextIO, optional
        Output stream to write to (default: sys.stdout)

    Attributes
    ----------
    output : TextIO
        The output stream being managed
    in_alternate_buffer : bool
        Whether currently in alternate screen mode
    """

    def __init__(self, output: TextIO = None):
        self.output = output or sys.stdout
        self.in_alternate_buffer = False
        self._cursor_hidden = False

    def enter_alternate_buffer(self) -> None:
        """Switch to alternate screen buffer.

        This allows the application to use the full terminal screen without
        affecting the user's terminal history. Changes made in alternate buffer
        are not preserved after exit.
        """
        if not self.in_alternate_buffer:
            self.output.write(ANSIScreen.alternate_buffer_on())
            self.output.flush()
            self.in_alternate_buffer = True

    def exit_alternate_buffer(self) -> None:
        """Return to main screen buffer.

        This restores the user's terminal to its previous state before
        entering alternate buffer mode.
        """
        if self.in_alternate_buffer:
            self.output.write(ANSIScreen.alternate_buffer_off())
            self.output.flush()
            self.in_alternate_buffer = False

    def clear(self) -> None:
        """Clear the entire screen.

        This clears all content from the current screen buffer.
        """
        self.output.write(ANSIScreen.clear())
        self.output.flush()

    def clear_line(self) -> None:
        """Clear the current line.

        This clears all content from the line where the cursor is currently positioned.
        """
        self.output.write(ANSIScreen.clear_line())
        self.output.flush()

    def move_cursor(self, row: int, col: int) -> None:
        """Move cursor to specific position.

        Parameters
        ----------
        row : int
            Row position (1-indexed)
        col : int
            Column position (1-indexed)
        """
        self.output.write(ANSICursor.position(row, col))
        self.output.flush()

    def hide_cursor(self) -> None:
        """Hide the terminal cursor.

        This is useful for TUI applications where a visible cursor might
        be distracting or confusing.
        """
        if not self._cursor_hidden:
            self.output.write(ANSICursor.hide())
            self.output.flush()
            self._cursor_hidden = True

    def show_cursor(self) -> None:
        """Show the terminal cursor.

        This should be called when exiting the application to restore
        normal terminal behavior.
        """
        if self._cursor_hidden:
            self.output.write(ANSICursor.show())
            self.output.flush()
            self._cursor_hidden = False

    def write(self, text: str) -> None:
        """Write text to the output stream.

        Parameters
        ----------
        text : str
            Text to write
        """
        self.output.write(text)
        self.output.flush()

    def cleanup(self) -> None:
        """Clean up screen state.

        This ensures the terminal is returned to a usable state by:
        - Exiting alternate buffer if active
        - Showing cursor if hidden
        - Clearing any remaining output
        """
        if self._cursor_hidden:
            self.show_cursor()
        if self.in_alternate_buffer:
            self.exit_alternate_buffer()


@contextmanager
def alternate_screen(output: TextIO = None, hide_cursor: bool = True):
    """Context manager for alternate screen buffer.

    This context manager handles entering and exiting alternate screen mode,
    with automatic cleanup on exit (including in case of exceptions).

    Parameters
    ----------
    output : TextIO, optional
        Output stream to use (default: sys.stdout)
    hide_cursor : bool, optional
        Whether to hide the cursor while in alternate buffer (default: True)

    Yields
    ------
    ScreenManager
        Screen manager instance for controlling the screen

    Examples
    --------
    >>> with alternate_screen() as screen:
    ...     screen.clear()
    ...     screen.write("Hello from alternate buffer!")
    """
    screen = ScreenManager(output)

    try:
        screen.enter_alternate_buffer()
        if hide_cursor:
            screen.hide_cursor()
        yield screen
    finally:
        screen.cleanup()
