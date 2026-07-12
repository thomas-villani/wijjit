"""A minimal Wijjit-over-SSH app.

Run it::

    ssh-keygen -f ssh_host_key -N ''          # once, to make a host key
    uv run python examples/hello_ssh.py       # starts the server on :8022

Then from another terminal::

    ssh -p 8022 yourname@localhost

You land straight in a live Wijjit TUI - a text field and a counter - served
over SSH. Every connection gets its own independent app instance and state.
"""

from __future__ import annotations

from wijjit import Wijjit, render_template_string

from wijjit_ssh import SSHSession, WijjitSSH

TEMPLATE = """
<vstack gap="1" padding="1">
  <frame title="Wijjit over SSH">
    <vstack gap="1" padding="1">
      <text>Hello, {{ username }}! Your terminal is {{ cols }}x{{ rows }}.</text>
      <text>Type your name and press Enter:</text>
      <textinput id="name" placeholder="name..." />
      <text>Greeted {{ count }} time(s).</text>
      <button id="greet">Greet</button>
      <text dim="true">Ctrl+Q to disconnect.</text>
    </vstack>
  </frame>
</vstack>
"""


def make_app(session: SSHSession) -> Wijjit:
    """Build one app per SSH connection (the SSH analogue of a Flask view)."""
    # Pass the session's backend into the app - this is what routes I/O to the
    # SSH channel instead of the server's own console.
    app = Wijjit(backend=session.backend, initial_state={"count": 0})

    @app.view("main", default=True)
    def main():
        return render_template_string(
            TEMPLATE,
            username=session.username,
            cols=session.columns,
            rows=session.lines,
            count=app.state["count"],
        )

    @app.on_action("greet")
    def greet():
        app.state["count"] += 1

    return app


if __name__ == "__main__":
    # WARNING: open auth (any username, no password). Do not expose publicly.
    server = WijjitSSH(make_app, host_keys=["ssh_host_key"])
    print("Wijjit SSH server listening on port 8022 (ssh -p 8022 you@localhost)")
    server.run(port=8022)
