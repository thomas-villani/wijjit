"""Load example apps headlessly for inspection and snapshot testing.

The ``examples/`` demos use two patterns to expose their
:class:`~wijjit.core.app.Wijjit` instance:

1. A module-level ``app = Wijjit(...)`` with view/handler decorators applied at
   import time (the majority).
2. A function-local ``app`` built inside ``main()`` (or the
   ``if __name__ == "__main__"`` block) and never exposed.

:func:`load_example_app` handles both. It executes the example module with
``__name__`` set to ``"__main__"`` (so the demo's entry point runs) while
temporarily patching :meth:`Wijjit.run` to *capture* the running instance
instead of entering the blocking event loop. The captured app is returned fully
wired but un-run, ready to drive through :class:`~wijjit.testing.WijjitHarness`.

This makes every example scriptable without a TTY, which is what the
``tests/examples`` snapshot suite and the ``python -m wijjit.testing`` CLI use.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from wijjit.core.app import Wijjit

if TYPE_CHECKING:
    from collections.abc import Iterator


class ExampleLoadError(RuntimeError):
    """Raised when an example module cannot be loaded or exposes no app."""


def load_example_app(path: str | Path) -> Wijjit:
    """Execute an example module and return its :class:`Wijjit` app un-run.

    Parameters
    ----------
    path : str or Path
        Filesystem path to an example ``.py`` file.

    Returns
    -------
    Wijjit
        The application instance the example builds, with all views and
        handlers registered but the event loop never started.

    Raises
    ------
    ExampleLoadError
        If the file does not exist, fails to import, or builds no ``Wijjit``
        instance that this loader can find.

    Notes
    -----
    The module is executed with ``__name__ == "__main__"`` so the demo's entry
    point runs, but :meth:`Wijjit.run` is patched to record ``self`` and return
    immediately rather than block on the event loop. Module ``stdout`` (banner
    ``print`` calls common in the demos) is suppressed during execution.
    """
    path = Path(path)
    if not path.is_file():
        raise ExampleLoadError(f"Example not found: {path}")

    captured: list[Wijjit] = []
    original_run = Wijjit.run

    def _capture_run(self: Wijjit) -> None:
        captured.append(self)

    source = path.read_text(encoding="utf-8")
    code = compile(source, str(path), "exec")
    module_globals: dict[str, object] = {
        "__name__": "__main__",
        "__file__": str(path),
        "__builtins__": __builtins__,
    }

    # Mimic a plain ``python example.py`` invocation: the demo must see only
    # its own name in ``sys.argv`` (several branch on ``len(sys.argv)``), not
    # whatever invoked the loader (e.g. pytest's argv).
    original_argv = sys.argv
    Wijjit.run = _capture_run  # type: ignore[method-assign]
    sys.argv = [str(path)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(code, module_globals)  # noqa: S102 - trusted local example files
    except ExampleLoadError:
        raise
    except Exception as exc:  # surface the demo's own failure with context
        raise ExampleLoadError(
            f"Example {path.name} raised while loading: {exc!r}"
        ) from exc
    finally:
        Wijjit.run = original_run  # type: ignore[method-assign]
        sys.argv = original_argv

    # Prefer the instance the demo actually ran; fall back to a module-level
    # ``app`` (or any Wijjit instance) for demos that never call run().
    if captured:
        return captured[-1]

    app = module_globals.get("app")
    if isinstance(app, Wijjit):
        return app
    for value in module_globals.values():
        if isinstance(value, Wijjit):
            return value

    raise ExampleLoadError(
        f"No Wijjit app found in {path.name} (it neither calls app.run() nor "
        f"exposes a module-level Wijjit instance)."
    )


def discover_examples(examples_dir: str | Path) -> Iterator[Path]:
    """Yield every runnable example ``.py`` under ``examples_dir``.

    Parameters
    ----------
    examples_dir : str or Path
        Root of the examples tree (typically ``<repo>/examples``).

    Yields
    ------
    Path
        Each example file, sorted, excluding ``__init__`` / ``conftest`` and
        any ``_`` -prefixed helper modules.
    """
    root = Path(examples_dir)
    for file in sorted(root.rglob("*.py")):
        if file.name.startswith("_") or file.stem in {"conftest"}:
            continue
        yield file
