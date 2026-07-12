# wijjit-ssh

**Flask for SSH apps.** Serve [Wijjit](../) TUI applications over SSH: Wijjit
draws the UI, `asyncssh` handles the transport and PTY, and every connection
gets its own live app instance.

> Status: **prototype / sketch.** The core transport seam it builds on
> (`wijjit.terminal.backend.TerminalBackend`) is in Wijjit proper; this package
> is the reference backend + server glue. See "Not yet hardened" below.

```python
from wijjit import Wijjit, render_template_string
from wijjit_ssh import WijjitSSH, SSHSession

def make_app(session: SSHSession) -> Wijjit:
    app = Wijjit(backend=session.backend)          # <- routes I/O to the channel
    @app.view("main", default=True)
    def main():
        return render_template_string(
            "<vstack padding='1'><text>Hi {{ who }}!</text></vstack>",
            who=session.username,
        )
    return app

WijjitSSH(make_app, host_keys=["ssh_host_key"]).run(port=8022)
```

```bash
ssh-keygen -f ssh_host_key -N ''      # make a host key (once)
uv run python examples/hello_ssh.py   # serve on :8022
ssh -p 8022 you@localhost             # connect from anywhere
```

## How it works

Wijjit's event loop talks to "the terminal" through a `TerminalBackend` - a
small seam covering four things: frame output, key/mouse input, terminal size,
and whether the app owns the process terminal. Locally that's
`LocalTerminalBackend` (stdout / stdin / `shutil` / signals on).

`wijjit_ssh.RemoteTerminalBackend` implements the same seam against an SSH
channel:

| Concern | Local backend | Remote (SSH) backend |
|---|---|---|
| Frame output | `sys.stdout` | `chan.write(...)` |
| Input | real stdin via prompt_toolkit | channel bytes fed into a prompt_toolkit **pipe input** (same key/mouse parser) |
| Size | `shutil.get_terminal_size()` | negotiated PTY size, refreshed on resize, published per-task |
| Terminal ownership | `owns_terminal=True` (signals/atexit/suspend/raw mode) | `owns_terminal=False` (none of that) |

Because Wijjit's render context and the terminal-size override are
**contextvar-based**, N concurrent sessions of different sizes coexist in one
process without stepping on each other - each runs as its own asyncio task.

## Not yet hardened

- **Auth is open by default** (any username, no credential). Wire real
  key/password auth before exposing this anywhere untrusted.
- One input reader thread per session; a byte-parsing input path would drop it.
- Blocking sync handlers stall that session's frames - give CPU-bound apps an
  executor.
- Channel I/O is utf-8 text; a strict binary path would use `encoding=None`.
```
