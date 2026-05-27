"""Enable ``python -m wijjit.testing`` to drive an example headlessly."""

from __future__ import annotations

from wijjit.testing.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
