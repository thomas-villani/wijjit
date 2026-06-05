"""Suspend/background support for Wijjit applications.

This module provides the SuspendManager class which handles Ctrl+Z suspend
functionality on Unix-like systems (Linux, macOS, BSD). When enabled, pressing
Ctrl+Z will properly suspend the TUI application to the background, and the
'fg' command will resume it with the display fully restored.

On Windows, this functionality is not available and the module will be a no-op.

Notes
-----
Job control (Ctrl+Z suspend) requires:
- Unix-like operating system (Linux, macOS, BSD)
- Terminal running in a shell with job control enabled
- ENABLE_SUSPEND config option set to True (default)

Examples
--------
The suspend feature is automatically enabled on Unix systems. Users can
suspend the app with Ctrl+Z and resume with 'fg':

    $ python my_app.py
    [Press Ctrl+Z]
    [1]+  Stopped                 python my_app.py
    $ fg
    [App resumes with display restored]
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from types import FrameType
from typing import TYPE_CHECKING, Any

from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit

logger = get_logger(__name__)

# Check if we're on a Unix-like system that supports job control
_SUSPEND_AVAILABLE = sys.platform != "win32"

if _SUSPEND_AVAILABLE:
    import signal


class SuspendManager:
    """Manages suspend/resume (Ctrl+Z) functionality for TUI applications.

    This class handles the SIGTSTP (suspend) and SIGCONT (resume) signals
    on Unix-like systems, ensuring proper terminal state save/restore when
    the application is suspended and resumed.

    Parameters
    ----------
    app : Wijjit
        Reference to the main Wijjit application

    Attributes
    ----------
    app : Wijjit
        Application reference
    enabled : bool
        Whether suspend handling is currently active
    suspended : bool
        Whether the app is currently suspended

    Notes
    -----
    This class is a no-op on Windows where job control signals are not available.

    The suspend flow is:
    1. User presses Ctrl+Z, kernel sends SIGTSTP
    2. Our handler saves terminal state (exit alt screen, show cursor, etc.)
    3. We reset SIGTSTP to default and re-send it to actually suspend
    4. User runs 'fg' in shell, kernel sends SIGCONT
    5. Our handler restores terminal state and triggers re-render
    """

    def __init__(self, app: Wijjit) -> None:
        """Initialize the suspend manager.

        Parameters
        ----------
        app : Wijjit
            Reference to the main Wijjit application
        """
        self.app = app
        self.enabled = False
        self.suspended = False

        # Store original signal handlers to restore on cleanup
        self._original_sigtstp: Callable[..., Any] | int | None = None
        self._original_sigcont: Callable[..., Any] | int | None = None

        # Track terminal state at suspend time for restoration
        self._was_in_alt_buffer = False
        self._was_cursor_hidden = False
        self._was_mouse_enabled = False

    @property
    def available(self) -> bool:
        """Check if suspend functionality is available on this platform.

        Returns
        -------
        bool
            True if on Unix-like system, False on Windows
        """
        return _SUSPEND_AVAILABLE

    def register(self) -> bool:
        """Register signal handlers for suspend/resume.

        This method should be called after the terminal is set up
        (alternate screen entered, cursor hidden, etc.).

        Returns
        -------
        bool
            True if handlers were registered, False if not available
            or already registered

        Notes
        -----
        On Windows, this is a no-op and returns False.
        """
        if not _SUSPEND_AVAILABLE:
            logger.debug("Suspend not available on this platform (Windows)")
            return False

        if self.enabled:
            logger.debug("Suspend handlers already registered")
            return False

        if not self.app.config.get("ENABLE_SUSPEND", True):
            logger.debug("Suspend disabled via config")
            return False

        try:
            # Save original handlers
            self._original_sigtstp = signal.signal(signal.SIGTSTP, self._handle_sigtstp)  # type: ignore[attr-defined]
            self._original_sigcont = signal.signal(signal.SIGCONT, self._handle_sigcont)  # type: ignore[attr-defined]

            self.enabled = True
            logger.info("Suspend handlers registered (Ctrl+Z enabled)")
            return True

        except (OSError, ValueError) as e:
            # OSError: not running in main thread or signal not supported
            # ValueError: invalid signal number
            logger.warning(f"Failed to register suspend handlers: {e}")
            return False

    def unregister(self) -> None:
        """Unregister signal handlers and restore originals.

        This method should be called during application cleanup.
        """
        if not _SUSPEND_AVAILABLE or not self.enabled:
            return

        try:
            # Restore original handlers
            if self._original_sigtstp is not None:
                signal.signal(signal.SIGTSTP, self._original_sigtstp)  # type: ignore[attr-defined]
            if self._original_sigcont is not None:
                signal.signal(signal.SIGCONT, self._original_sigcont)  # type: ignore[attr-defined]

            self.enabled = False
            logger.debug("Suspend handlers unregistered")

        except (OSError, ValueError) as e:
            logger.warning(f"Error unregistering suspend handlers: {e}")

    def _handle_sigtstp(self, signum: int, frame: FrameType | None) -> None:
        """Handle SIGTSTP (Ctrl+Z suspend signal).

        This handler is called when the user presses Ctrl+Z. It:
        1. Saves current terminal state
        2. Restores terminal to normal mode (exit alt screen, show cursor)
        3. Restores default SIGTSTP handler
        4. Re-raises SIGTSTP to actually suspend the process

        Parameters
        ----------
        signum : int
            Signal number (SIGTSTP = 20 on most systems)
        frame : frame object
            Current stack frame (unused)
        """
        logger.info("Received SIGTSTP (Ctrl+Z), suspending application")

        # Save current terminal state for restoration on resume
        self._was_in_alt_buffer = self.app.screen_manager.in_alternate_buffer
        self._was_cursor_hidden = self.app.screen_manager._cursor_hidden
        self._was_mouse_enabled = self.app.input_handler.mouse_enabled

        # Clean up terminal state so user can interact with shell
        # Order matters: disable mouse first, then show cursor, then exit alt buffer
        if self._was_mouse_enabled:
            self.app.input_handler.disable_mouse_tracking()
            logger.debug("Disabled mouse tracking for suspend")

        if self._was_cursor_hidden:
            self.app.screen_manager.show_cursor()
            logger.debug("Shown cursor for suspend")

        if self._was_in_alt_buffer:
            self.app.screen_manager.exit_alternate_buffer()
            logger.debug("Exited alternate buffer for suspend")

        # Flush output to ensure all escape sequences are sent
        self.app.screen_manager.output.flush()

        self.suspended = True

        # Temporarily restore default SIGTSTP handler so we actually suspend
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)  # type: ignore[attr-defined]

        # Send SIGTSTP to ourselves to actually suspend
        # The process will stop here until resumed with SIGCONT
        os.kill(os.getpid(), signal.SIGTSTP)  # type: ignore[attr-defined]

        # Execution continues here after resume (before SIGCONT handler runs)
        # Re-register our handler for next Ctrl+Z
        signal.signal(signal.SIGTSTP, self._handle_sigtstp)  # type: ignore[attr-defined]

    def _handle_sigcont(self, signum: int, frame: FrameType | None) -> None:
        """Handle SIGCONT (resume signal).

        This handler is called when the process resumes after suspension
        (typically when user runs 'fg' in the shell). It:
        1. Restores terminal state (enter alt screen, hide cursor, etc.)
        2. Triggers a full re-render of the application

        Parameters
        ----------
        signum : int
            Signal number (SIGCONT = 18 on most systems)
        frame : frame object
            Current stack frame (unused)
        """
        if not self.suspended:
            # SIGCONT received but we weren't suspended by us
            # This can happen if another process sends SIGCONT
            logger.debug("Received SIGCONT but not in suspended state")
            return

        logger.info("Received SIGCONT, resuming application")

        # Restore terminal state in reverse order of cleanup
        # Order matters: enter alt buffer first, then hide cursor, then enable mouse
        if self._was_in_alt_buffer:
            self.app.screen_manager.enter_alternate_buffer()
            logger.debug("Restored alternate buffer after resume")

        if self._was_cursor_hidden:
            self.app.screen_manager.hide_cursor()
            logger.debug("Hidden cursor after resume")

        if self._was_mouse_enabled:
            self.app.input_handler.enable_mouse_tracking()
            logger.debug("Enabled mouse tracking after resume")

        self.suspended = False

        # Mark app as needing re-render to restore display
        self.app.needs_render = True
        logger.debug("Marked app for re-render after resume")

        # Force immediate render if possible
        # Note: This runs in signal handler context, so we just set the flag
        # The event loop will pick it up on next iteration
