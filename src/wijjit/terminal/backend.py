"""Pluggable terminal transport for Wijjit applications.

A :class:`TerminalBackend` bundles the four things a Wijjit event loop needs
from "the terminal", each of which was previously hard-wired to the process's
real controlling terminal:

1. **Output** - where rendered frames and screen-control sequences are written.
2. **Input** - a keyboard/mouse source (an :class:`~wijjit.terminal.input.InputHandler`).
3. **Size** - the current terminal dimensions.
4. **Ownership** - whether this app *owns* the process terminal, and may
   therefore install process-global machinery (signal/atexit terminal-restore,
   ``SIGTSTP`` suspend) and drive the real tty into raw mode.

The default :class:`LocalTerminalBackend` reproduces Wijjit's historical
behavior exactly: it writes to ``sys.stdout``, reads real stdin via
prompt_toolkit, sizes from :func:`shutil.get_terminal_size`, and owns the
terminal. Alternative backends (for example one that bridges to an SSH channel)
implement the same surface to run a Wijjit app somewhere other than the local
console - without any process-global side effects, and with a per-session size
so many connections can share one process.

See :mod:`wijjit.terminal.size` for how a non-local backend publishes its size
to render/layout code via a task-local context variable.
"""

from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING, Protocol, TextIO, runtime_checkable

from wijjit.terminal.input import InputHandler

if TYPE_CHECKING:
    from wijjit.terminal.input import Key
    from wijjit.terminal.mouse import MouseEvent, MouseTrackingMode


@runtime_checkable
class InputSource(Protocol):
    """The input surface the event loop drives.

    Wijjit's event loop never depends on *how* input is obtained, only on this
    surface. The local backend satisfies it with
    :class:`~wijjit.terminal.input.InputHandler` (prompt_toolkit on a reader
    thread); a remote backend can satisfy it by decoding bytes off a socket on
    the event loop. Declaring it as a protocol - rather than typing the seam
    against the concrete local handler - is what makes those alternatives
    expressible.

    Attributes
    ----------
    mouse_enabled : bool
        Whether mouse tracking is currently active on the terminal.
    """

    mouse_enabled: bool

    async def read_input_async(
        self, timeout: float | None = None
    ) -> Key | MouseEvent | None:
        """Wait for the next input event, or return None once ``timeout`` lapses."""
        ...

    def enable_mouse_tracking(self, mode: MouseTrackingMode | None = None) -> None:
        """Turn on mouse reporting."""
        ...

    def disable_mouse_tracking(self) -> None:
        """Turn off mouse reporting."""
        ...

    def close(self) -> None:
        """Release the input source at teardown."""
        ...

    def restore_terminal(self) -> None:
        """Undo terminal-affecting state (mouse tracking, raw mode)."""
        ...


class TerminalBackend:
    """Abstract transport connecting a Wijjit app to a terminal.

    Subclasses override the members below to run an app against a transport
    other than the local console. The base class is intentionally concrete for
    the "local" defaults so simple backends only override what differs.

    Attributes
    ----------
    owns_terminal : bool
        Whether the app may manage process-global terminal state: the
        SIGTERM/SIGHUP/atexit restore net, ``SIGTSTP`` suspend handling, and
        putting the real tty into raw mode. True for a local console app; a
        remote/multiplexed backend sets this False so N concurrent sessions in
        one process never fight over process-global handlers.
    provides_size : bool
        Whether :meth:`get_size` is authoritative and should be published to
        the task-local size override (see :mod:`wijjit.terminal.size`). False
        for the local backend, which reads the real terminal directly so the
        test harness's ``shutil`` monkeypatch keeps working.
    """

    owns_terminal: bool = True
    provides_size: bool = False

    @property
    def screen_output(self) -> TextIO | None:
        """Stream the :class:`~wijjit.terminal.screen.ScreenManager` writes to.

        Returns
        -------
        TextIO or None
            The output stream for screen-control sequences (alternate buffer,
            cursor visibility, title). ``None`` means "use ``sys.stdout``",
            matching :class:`~wijjit.terminal.screen.ScreenManager`'s default.
        """
        return None

    def write_frame(self, data: str) -> None:
        """Write a fully rendered frame to the terminal.

        Parameters
        ----------
        data : str
            The frame's ANSI byte string (already diffed by the renderer).
        """
        raise NotImplementedError

    def get_size(self) -> tuple[int, int]:
        """Return the current terminal size.

        Returns
        -------
        tuple of int
            ``(columns, lines)``.
        """
        raise NotImplementedError

    def create_input_handler(
        self,
        *,
        enable_mouse: bool,
        mouse_tracking_mode: MouseTrackingMode | None,
    ) -> InputSource:
        """Build the input source for this app.

        Parameters
        ----------
        enable_mouse : bool
            Whether mouse tracking is requested.
        mouse_tracking_mode : MouseTrackingMode or None
            Requested tracking granularity.

        Returns
        -------
        InputSource
            An input source wired to this backend's transport. The local backend
            returns an :class:`~wijjit.terminal.input.InputHandler`; other
            backends may return anything satisfying :class:`InputSource`.
        """
        raise NotImplementedError


class LocalTerminalBackend(TerminalBackend):
    """Default backend: the local console (``sys.stdout`` / real stdin).

    This is what :class:`~wijjit.core.app.Wijjit` uses when no backend is
    supplied. Behavior is byte-for-byte identical to Wijjit before the backend
    seam existed.

    Parameters
    ----------
    owns_terminal : bool, optional
        Whether to manage process-global terminal state (default True). Pass
        False to run on the local console without installing signal/atexit
        handlers or the suspend hook - useful for embedding, and the mechanism
        behind the ``REMOTE`` config flag.
    """

    provides_size = False

    def __init__(self, owns_terminal: bool = True) -> None:
        self.owns_terminal = owns_terminal

    @property
    def screen_output(self) -> TextIO | None:
        # None -> ScreenManager defaults to sys.stdout, resolved at write time.
        return None

    def write_frame(self, data: str) -> None:
        # ``sys.stdout`` is read dynamically (not cached) so pytest's capsys and
        # any other stdout redirection continue to capture frames. Mirrors the
        # historical ``print(data, end="", flush=True)`` including the Windows
        # console encoding fallback.
        try:
            sys.stdout.write(data)
            sys.stdout.flush()
        except UnicodeEncodeError:
            sys.stdout.buffer.write(data.encode("utf-8", errors="replace"))
            sys.stdout.flush()

    def get_size(self) -> tuple[int, int]:
        size = shutil.get_terminal_size()
        return (size.columns, size.lines)

    def create_input_handler(
        self,
        *,
        enable_mouse: bool,
        mouse_tracking_mode: MouseTrackingMode | None,
    ) -> InputHandler:
        return InputHandler(
            enable_mouse=enable_mouse,
            mouse_tracking_mode=mouse_tracking_mode,
        )
