"""A :class:`~wijjit.terminal.backend.TerminalBackend` bridged to an SSH channel.

This is the whole reason the backend seam exists: :class:`RemoteTerminalBackend`
runs an ordinary Wijjit app against an ``asyncssh`` session instead of the local
console. It:

* writes rendered frames and screen-control sequences to the SSH channel,
* feeds inbound channel bytes into Wijjit's normal key/mouse parser via a
  prompt_toolkit pipe input (so every element behaves exactly as it does
  locally), and
* reports the client's negotiated PTY size (refreshed on ``SIGWINCH``-style
  resize events) as a task-local override, so many differently-sized sessions
  coexist in one server process.

It sets ``owns_terminal = False`` so the event loop installs none of the
process-global terminal machinery (SIGTERM/SIGHUP/atexit restore, SIGTSTP
suspend) - there is no local tty to restore, and those handlers are
process-global and would collide across concurrent sessions.

.. note::

   Prototype. Rough edges intentionally left for hardening: it decodes channel
   data as text (fine for typed input and CSI/SGR escape sequences, but a true
   binary path would open the channel with ``encoding=None``); and each session
   carries its own input reader thread via
   :class:`~wijjit.terminal.input.InputHandler`.
"""

from __future__ import annotations

from typing import TextIO

from wijjit.terminal.backend import TerminalBackend
from wijjit.terminal.input import InputHandler
from wijjit.terminal.mouse import MouseTrackingMode


class _ChannelWriter:
    """Minimal text stream that writes to an ``asyncssh`` channel.

    Presents the ``write``/``flush`` surface that
    :class:`~wijjit.terminal.screen.ScreenManager` and
    :class:`~wijjit.terminal.input.InputHandler` expect. ``flush`` is a no-op:
    ``asyncssh`` channels buffer and drain on the event loop themselves.

    Parameters
    ----------
    chan : asyncssh.SSHServerChannel
        The channel to write to. Must be written from the event-loop thread.
    """

    def __init__(self, chan: object) -> None:
        self._chan = chan

    def write(self, data: str) -> None:
        # asyncssh encodes str per the channel's encoding (utf-8 by default),
        # which preserves ANSI escape bytes. Silently drop writes once the peer
        # has gone so a final frame racing connection loss can't crash the loop.
        try:
            self._chan.write(data)  # type: ignore[attr-defined]
        except (BrokenPipeError, ConnectionError, OSError):
            pass

    def flush(self) -> None:
        return None


class RemoteTerminalBackend(TerminalBackend):
    """Terminal backend that drives a Wijjit app over an SSH channel.

    Parameters
    ----------
    chan : asyncssh.SSHServerChannel
        The client's session channel; frames are written here.
    pipe_input : prompt_toolkit.input.PipeInput
        Pipe input that inbound channel bytes are fed into (see :meth:`feed`).
        Wijjit's :class:`~wijjit.terminal.input.InputHandler` reads from it just
        as it would from real stdin.
    columns : int
        Initial terminal width negotiated by the PTY request.
    lines : int
        Initial terminal height negotiated by the PTY request.
    """

    # Never touch process-global terminal state - there is no local tty here and
    # the process is shared by every concurrent session.
    owns_terminal = False
    # get_size() is authoritative and should be published to the task-local
    # size override so render/layout track this client's dimensions.
    provides_size = True

    def __init__(
        self,
        chan: object,
        pipe_input: object,
        columns: int,
        lines: int,
    ) -> None:
        self._writer = _ChannelWriter(chan)
        self._pipe_input = pipe_input
        self._columns = columns
        self._lines = lines

    @property
    def screen_output(self) -> TextIO | None:
        # ScreenManager writes alt-buffer/cursor/title sequences to the channel.
        return self._writer  # type: ignore[return-value]

    def write_frame(self, data: str) -> None:
        self._writer.write(data)

    def get_size(self) -> tuple[int, int]:
        return (self._columns, self._lines)

    def create_input_handler(
        self,
        *,
        enable_mouse: bool,
        mouse_tracking_mode: MouseTrackingMode | None,
    ) -> InputHandler:
        # Reuse Wijjit's real InputHandler, but sourced from the SSH pipe and
        # sinking mouse-enable sequences back to the channel.
        return InputHandler(
            enable_mouse=enable_mouse,
            mouse_tracking_mode=mouse_tracking_mode,
            input=self._pipe_input,
            output=self._writer,
        )

    # -- transport-side hooks (called by the SSH session, not by Wijjit) --------

    def feed(self, data: str) -> None:
        """Push inbound channel data into the input pipe.

        Parameters
        ----------
        data : str
            Bytes received on the channel, decoded as text by asyncssh.
        """
        self._pipe_input.send_text(data)  # type: ignore[attr-defined]

    def resize(self, columns: int, lines: int) -> None:
        """Record a new client terminal size.

        The running event loop reads this via :meth:`get_size` on its next frame
        and republishes it to the task-local size override, so overlays,
        notifications, and layout reflow to the new dimensions.

        Parameters
        ----------
        columns : int
            New terminal width.
        lines : int
            New terminal height.
        """
        self._columns = columns
        self._lines = lines
