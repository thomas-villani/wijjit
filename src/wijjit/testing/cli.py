"""Command-line entry point for driving an example headlessly.

Render any example to the terminal without a TTY, optionally scripting keys,
clicks, and animation ticks, then print the resulting screen as plain text or
ANSI. Intended for quick agent-driven iteration on visual/interaction bugs::

    python -m wijjit.testing examples/widgets/spinner_demo.py
    python -m wijjit.testing examples/advanced/login_form.py \\
        --size 100x30 --keys "tab,type:admin,tab,type:secret,enter" --ansi
    python -m wijjit.testing examples/widgets/spinner_demo.py --tick 5

The ``--keys`` script is a comma-separated list of steps, each one of:

* a named key (``tab``, ``enter``, ``up``, ``ctrl+q``, ...) or single char,
* ``type:TEXT`` to type a literal string,
* ``click:X,Y`` to left-click a cell,
* ``tick`` / ``tick:N`` to advance animation frames.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wijjit.testing.examples import ExampleLoadError, load_example_app
from wijjit.testing.harness import WijjitHarness


def _parse_size(text: str) -> tuple[int, int]:
    """Parse a ``WIDTHxHEIGHT`` string into a ``(cols, rows)`` tuple."""
    try:
        width, height = text.lower().split("x", 1)
        return int(width), int(height)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid size {text!r}; expected e.g. 80x24"
        ) from exc


def _apply_step(harness: WijjitHarness, step: str) -> None:
    """Apply a single ``--keys`` script step to the harness."""
    step = step.strip()
    if not step:
        return
    if step.startswith("type:"):
        harness.type(step[len("type:") :])
    elif step.startswith("click:"):
        x_str, y_str = step[len("click:") :].split(",", 1)
        harness.click(int(x_str), int(y_str))
    elif step == "tick":
        harness.tick()
    elif step.startswith("tick:"):
        harness.tick(int(step[len("tick:") :]))
    else:
        harness.press(step)


def run_render(
    example: Path,
    size: tuple[int, int] = (80, 24),
    keys: str = "",
    tick: int = 0,
    ansi: bool = False,
) -> int:
    """Load an example, apply a scripted input run, and print its screen.

    Shared by this module's ``main`` and the top-level ``wijjit render``
    subcommand so the rendering behavior stays identical.

    Parameters
    ----------
    example : Path
        Path to an example ``.py`` file.
    size : tuple of (int, int), optional
        Terminal ``(cols, rows)`` to render at.
    keys : str, optional
        Comma-separated input script (keys, ``type:TEXT``, ``click:X,Y``,
        ``tick:N``).
    tick : int, optional
        Animation frames to advance after the key script.
    ansi : bool, optional
        Print the styled ANSI screen instead of plain text.

    Returns
    -------
    int
        Process exit code (0 on success, 1 on load failure).
    """
    try:
        app = load_example_app(example)
    except ExampleLoadError as exc:
        print(f"Failed to load example: {exc}", file=sys.stderr)
        return 1

    with WijjitHarness(app, size=size) as harness:
        if keys:
            for step in keys.split(","):
                _apply_step(harness, step)
        if tick:
            harness.tick(tick)
        sys.stdout.write(harness.screen_ansi() if ansi else harness.screen())
        sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the headless example CLI.

    Parameters
    ----------
    argv : list of str, optional
        Argument vector (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Process exit code (0 on success, non-zero on load failure).
    """
    parser = argparse.ArgumentParser(
        prog="python -m wijjit.testing",
        description="Render a Wijjit example headlessly and print the screen.",
    )
    parser.add_argument("example", type=Path, help="Path to an example .py file.")
    parser.add_argument(
        "--size",
        type=_parse_size,
        default=(80, 24),
        help="Terminal size as WIDTHxHEIGHT (default: 80x24).",
    )
    parser.add_argument(
        "--keys",
        default="",
        help="Comma-separated input script (keys, type:TEXT, click:X,Y, tick:N).",
    )
    parser.add_argument(
        "--tick",
        type=int,
        default=0,
        metavar="N",
        help="Advance N animation frames before printing (after --keys).",
    )
    parser.add_argument(
        "--ansi",
        action="store_true",
        help="Print the styled ANSI screen instead of plain text.",
    )
    args = parser.parse_args(argv)

    return run_render(args.example, args.size, args.keys, args.tick, args.ansi)


if __name__ == "__main__":
    raise SystemExit(main())
