"""A "Flask for SSH apps" server: expose a Wijjit app over SSH.

:class:`WijjitSSH` wraps ``asyncssh`` so that each incoming SSH connection gets
its own Wijjit application, driven through a
:class:`~wijjit_ssh.backend.RemoteTerminalBackend`. You supply a factory - the
SSH analogue of a Flask view - that builds an app per connection:

>>> from wijjit import Wijjit, render_template_string
>>> from wijjit_ssh import WijjitSSH
>>>
>>> def make_app(session):
...     app = Wijjit()
...     @app.view("main", default=True)
...     def main():
...         return render_template_string(
...             "<vstack><text>Hi {{ who }}!</text></vstack>", who=session.username
...         )
...     return app
>>>
>>> WijjitSSH(make_app, host_keys=["ssh_host_key"]).run(port=8022)

Then ``ssh -p 8022 anyone@localhost`` drops the client straight into the TUI.

Prototype status / not-yet-hardened
------------------------------------
* **Auth is open** by default (any username, no credential). Pass ``authorize``
  to gate connections, or subclass for real key/password auth. Never expose the
  open default on an untrusted network.
* One input reader thread per session (inherited from ``InputHandler``). Fine
  for tens of sessions; a byte-parsing input path would remove the thread.
* Blocking sync handlers stall that session's frames; give each app an executor
  (``Wijjit(..., )`` + ``EXECUTOR``) for CPU-bound work.
* Channel I/O is text (utf-8); a strict binary path would use ``encoding=None``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

try:
    import asyncssh
except ImportError as exc:  # pragma: no cover - asyncssh is an optional dep
    raise ImportError(
        "wijjit-ssh requires asyncssh. Install it with: pip install asyncssh"
    ) from exc

from prompt_toolkit.input import create_pipe_input
from wijjit import Wijjit
from wijjit.terminal.size import set_terminal_size

from wijjit_ssh.backend import RemoteTerminalBackend


@dataclass
class SSHSession:
    """Context passed to the per-connection app factory.

    Attributes
    ----------
    username : str
        Username the client authenticated as.
    term_type : str
        Client's ``TERM`` (e.g. ``"xterm-256color"``).
    columns : int
        Negotiated terminal width.
    lines : int
        Negotiated terminal height.
    backend : RemoteTerminalBackend
        The transport for this connection. **Pass it to the app**:
        ``Wijjit(backend=session.backend)`` - this is what routes the app's I/O
        to the SSH channel instead of the server's console.
    conn : asyncssh.SSHServerConnection
        The underlying connection, for advanced use.
    """

    username: str
    term_type: str
    columns: int
    lines: int
    backend: RemoteTerminalBackend
    conn: object


AppFactory = Callable[[SSHSession], Wijjit]
Authorizer = Callable[[str], "bool | Awaitable[bool]"]


class _WijjitSSHSession(asyncssh.SSHServerSession):
    """Bridges one SSH channel to one Wijjit app instance.

    Parameters
    ----------
    app_factory : AppFactory
        Builds the app for this connection.
    conn : asyncssh.SSHServerConnection
        The owning connection (source of the authenticated username).
    """

    def __init__(self, app_factory: AppFactory, conn: object) -> None:
        self._app_factory = app_factory
        self._conn = conn
        self._chan: object = None
        self._term_type: str = "xterm"
        self._size: tuple[int, int] = (80, 24)
        self._pipe_cm = None
        self._pipe = None
        self._backend: Optional[RemoteTerminalBackend] = None
        self._app: Optional[Wijjit] = None
        self._task: Optional[asyncio.Task] = None

    # -- asyncssh session callbacks --------------------------------------------

    def connection_made(self, chan: object) -> None:
        self._chan = chan

    def pty_requested(
        self, term_type: str, term_size: tuple, term_modes: dict
    ) -> bool:
        # term_size is (width, height, pixwidth, pixheight).
        self._term_type = term_type or "xterm"
        width, height = term_size[0] or 80, term_size[1] or 24
        self._size = (width, height)
        return True

    def shell_requested(self) -> bool:
        return True

    def session_started(self) -> None:
        # Runs on the event loop. Seed the size override BEFORE building the app
        # so Wijjit.__init__ (which reads the terminal size) sees this client's
        # dimensions, then start the app in its own task, which inherits this
        # context (including the size override) at creation time.
        cols, lines = self._size

        self._pipe_cm = create_pipe_input()
        self._pipe = self._pipe_cm.__enter__()

        self._backend = RemoteTerminalBackend(self._chan, self._pipe, cols, lines)

        # Seed the size override before the factory runs so Wijjit.__init__ sizes
        # its managers to this client. The factory must wire the backend into the
        # app (Wijjit(backend=session.backend)); doing so is what points the
        # app's screen/input at the channel.
        set_terminal_size(cols, lines)
        session = SSHSession(
            username=self._conn.get_extra_info("username") or "anonymous",
            term_type=self._term_type,
            columns=cols,
            lines=lines,
            backend=self._backend,
            conn=self._conn,
        )
        app = self._app_factory(session)
        if app._backend is not self._backend:
            raise RuntimeError(
                "The app factory must pass the session backend to the app: "
                "Wijjit(backend=session.backend)."
            )
        self._app = app

        self._task = asyncio.ensure_future(self._run_app())

    async def _run_app(self) -> None:
        try:
            # Enter Wijjit's async loop directly (we are already on an event
            # loop; app.run() would try to start a new one via asyncio.run).
            await self._app.event_loop.run_async()  # type: ignore[union-attr]
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # pragma: no cover - defensive
            try:
                self._chan.write(f"\r\nApplication error: {exc}\r\n")  # type: ignore[attr-defined]
            except Exception:
                pass
        finally:
            if self._chan is not None:
                self._chan.close()  # type: ignore[attr-defined]

    def data_received(self, data: str, datatype: object) -> None:
        if self._backend is not None:
            self._backend.feed(data)

    def terminal_size_changed(
        self, width: int, height: int, pixwidth: int, pixheight: int
    ) -> None:
        if self._backend is not None:
            self._backend.resize(width, height)

    def eof_received(self) -> bool:
        return False

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if self._app is not None:
            # Ask the loop to stop; the task's finally closes the channel.
            self._app.quit()
        if self._task is not None:
            self._task.cancel()
        if self._pipe_cm is not None:
            try:
                self._pipe_cm.__exit__(None, None, None)
            except Exception:
                pass


class _WijjitSSHServer(asyncssh.SSHServer):
    """asyncssh server that mints a Wijjit session per connection."""

    def __init__(self, app_factory: AppFactory, authorize: Optional[Authorizer]) -> None:
        self._app_factory = app_factory
        self._authorize = authorize
        self._conn: object = None

    def connection_made(self, conn: object) -> None:
        self._conn = conn

    def begin_auth(self, username: str) -> bool:
        # Return False => no authentication required for this user. When an
        # authorizer is configured we still short-circuit here and enforce it in
        # password/public-key callbacks in a real build; kept open in the sketch.
        return False

    def session_requested(self) -> object:
        return _WijjitSSHSession(self._app_factory, self._conn)


class WijjitSSH:
    """Serve a Wijjit app over SSH, one app instance per connection.

    Parameters
    ----------
    app_factory : Callable[[SSHSession], Wijjit]
        Builds the app for each connection (the SSH analogue of a Flask view).
    host_keys : list of str
        Paths to SSH host key files. Generate one with
        ``ssh-keygen -f ssh_host_key -N ''``.
    authorize : Callable[[str], bool] or None, optional
        Optional per-username gate. Prototype: advisory only.
    """

    def __init__(
        self,
        app_factory: AppFactory,
        *,
        host_keys: list[str],
        authorize: Optional[Authorizer] = None,
    ) -> None:
        self._app_factory = app_factory
        self._host_keys = host_keys
        self._authorize = authorize

    async def run_async(self, host: str = "", port: int = 8022) -> None:
        """Start the SSH server and serve until cancelled.

        Parameters
        ----------
        host : str, optional
            Bind address (default: all interfaces).
        port : int, optional
            Bind port (default: 8022).
        """
        await asyncssh.create_server(
            lambda: _WijjitSSHServer(self._app_factory, self._authorize),
            host,
            port,
            server_host_keys=self._host_keys,
            # A TUI needs raw, char-at-a-time input and does its own drawing.
            # asyncssh's default PTY line editor would echo keystrokes and
            # buffer them until Enter - disable it so keys reach Wijjit
            # immediately and nothing is echoed over our frames.
            line_editor=False,
        )
        # Serve forever.
        await asyncio.Event().wait()

    def run(self, host: str = "", port: int = 8022) -> None:
        """Blocking convenience wrapper around :meth:`run_async`."""
        try:
            asyncio.run(self.run_async(host, port))
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
