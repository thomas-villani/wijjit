"""Allow ``python -m wijjit <command>`` to invoke the CLI."""

from __future__ import annotations

from wijjit.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
