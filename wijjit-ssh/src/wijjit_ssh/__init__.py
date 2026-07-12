"""wijjit-ssh: serve Wijjit TUI apps over SSH ("Flask for SSH apps").

Public API
----------
WijjitSSH
    The server. Give it a per-connection app factory and host keys, call
    ``run()``.
SSHSession
    Context handed to the factory (username, term type, size, backend).
RemoteTerminalBackend
    The :class:`~wijjit.terminal.backend.TerminalBackend` implementation that
    bridges a Wijjit app to an SSH channel. Usually you never touch it directly;
    the factory just forwards ``session.backend`` into ``Wijjit(backend=...)``.
"""

from wijjit_ssh.backend import RemoteTerminalBackend
from wijjit_ssh.server import SSHSession, WijjitSSH

__all__ = ["WijjitSSH", "SSHSession", "RemoteTerminalBackend"]

__version__ = "0.0.1"
