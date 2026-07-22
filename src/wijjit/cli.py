"""Top-level ``wijjit`` command-line interface.

Developer- and LLM-friendly tooling for inspecting, validating, and driving
Wijjit apps::

    wijjit validate app.wij.j2 --render          # lint a template, show a snapshot
    wijjit validate examples/login.py            # lint a full example app
    wijjit tree app.wij.j2 --json                # dump the VNode "DOM" tree
    wijjit render examples/spinner.py --tick 5   # headless render
    wijjit run examples/login.py                 # launch an app in this terminal
    wijjit test -k login tests/                  # pass through to pytest
    wijjit llm-help > WIJJIT.md                  # paste-able LLM briefing

``validate`` and ``tree`` auto-detect their input: a ``.py`` file is loaded as a
full app, anything else is treated as a raw template. Template files are
conventionally named ``*.wij.j2`` so editors highlight them as Jinja, but the
extension is not enforced. The ``render`` subcommand ports ``python -m
wijjit.testing`` (which still works as before). ``run`` launches a ``.py`` app
interactively; ``test`` forwards to pytest.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from wijjit import __version__
from wijjit.testing.cli import _parse_size, run_render


def _load_context(path: Path | None) -> dict[str, Any] | None:
    """Load a JSON context file, or return None when no path is given."""
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Context file {path} must contain a JSON object.")
    return data


def _cmd_llm_help(args: argparse.Namespace) -> int:
    """Print the paste-able LLM briefing for this installation."""
    from wijjit.devtools import build_tag_reference, render_llm_help

    print(build_tag_reference() if args.tags_only else render_llm_help())
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    from wijjit.devtools import validate_file

    report = validate_file(
        args.file,
        context=_load_context(args.context),
        width=args.size[0],
        height=args.size[1],
        render=args.render,
    )
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        print(report.format_text())
        if args.render and report.rendered is not None:
            print("\n--- rendered ---")
            print(report.rendered)
    return 0 if report.ok else 1


def _cmd_tree(args: argparse.Namespace) -> int:
    from wijjit.devtools import build_vnode_tree, render_tree_text, vnode_to_dict

    try:
        root, rendered = build_vnode_tree(
            args.file,
            context=_load_context(args.context),
            width=args.size[0],
            height=args.size[1],
        )
    except Exception as exc:  # noqa: BLE001 - report cleanly, no traceback
        print(f"Failed to build tree: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(vnode_to_dict(root), indent=2, default=str))
    elif root is None:
        print("<no layout tree; template renders as plain text>")
        print(rendered)
    else:
        print(render_tree_text(root))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    return run_render(args.file, args.size, args.keys, args.tick, args.ansi)


def _cmd_run(args: argparse.Namespace) -> int:
    """Load a ``.py`` app and launch it interactively in this terminal."""
    from wijjit.testing.examples import ExampleLoadError, load_example_app

    try:
        app = load_example_app(args.file)
    except ExampleLoadError as exc:
        print(f"Failed to load {args.file}: {exc}", file=sys.stderr)
        return 1
    app.run()
    return 0


def _run_pytest(pytest_args: list[str]) -> int:
    """Forward ``pytest_args`` to pytest, or explain if pytest is missing."""
    try:
        import pytest
    except ImportError:
        print(
            "pytest is not installed. Install the dev extra: "
            "uv pip install 'wijjit[dev]'",
            file=sys.stderr,
        )
        return 1
    return int(pytest.main(pytest_args))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wijjit",
        description="Wijjit developer tooling: validate, inspect, and drive apps.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"wijjit {__version__}",
        help="Show the installed Wijjit version and exit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pv = sub.add_parser(
        "validate", help="Parse a template or app for errors; optionally render."
    )
    pv.add_argument("file", type=Path, help="Template file or example .py app.")
    pv.add_argument(
        "--render", action="store_true", help="Also print the rendered screen."
    )
    pv.add_argument(
        "--context", type=Path, help="JSON file of template context variables."
    )
    pv.add_argument(
        "--size",
        type=_parse_size,
        default=(80, 24),
        help="Render size as WIDTHxHEIGHT (default: 80x24).",
    )
    pv.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    pv.set_defaults(func=_cmd_validate)

    pt = sub.add_parser("tree", help="Dump the VNode (DOM) tree of a template or app.")
    pt.add_argument("file", type=Path, help="Template file or example .py app.")
    pt.add_argument("--json", action="store_true", help="Emit the tree as JSON.")
    pt.add_argument(
        "--context", type=Path, help="JSON file of template context variables."
    )
    pt.add_argument(
        "--size",
        type=_parse_size,
        default=(80, 24),
        help="Render size as WIDTHxHEIGHT (default: 80x24).",
    )
    pt.set_defaults(func=_cmd_tree)

    pr = sub.add_parser(
        "render", help="Render an example app headlessly and print the screen."
    )
    pr.add_argument("file", type=Path, help="Path to an example .py file.")
    pr.add_argument(
        "--size",
        type=_parse_size,
        default=(80, 24),
        help="Terminal size as WIDTHxHEIGHT (default: 80x24).",
    )
    pr.add_argument(
        "--keys",
        default="",
        help=(
            "Comma-separated input script (keys, type:TEXT, click:X,Y, "
            "tick:N, settle:N)."
        ),
    )
    pr.add_argument(
        "--tick",
        type=int,
        default=0,
        metavar="N",
        help="Advance N animation frames before printing (after --keys).",
    )
    pr.add_argument(
        "--ansi",
        action="store_true",
        help="Print the styled ANSI screen instead of plain text.",
    )
    pr.set_defaults(func=_cmd_render)

    prun = sub.add_parser(
        "run", help="Launch a .py Wijjit app interactively in this terminal."
    )
    prun.add_argument("file", type=Path, help="Path to a Wijjit .py app.")
    prun.set_defaults(func=_cmd_run)

    pllm = sub.add_parser(
        "llm-help",
        help="Print a paste-able Wijjit briefing for an LLM (Markdown).",
        description=(
            "Print a single self-contained Markdown briefing that teaches an "
            "LLM to write correct Wijjit apps. The tag reference is "
            "introspected from this installation, so it cannot go stale. "
            "Pipe it into an agent's context: wijjit llm-help > WIJJIT.md"
        ),
    )
    pllm.add_argument(
        "--tags-only",
        action="store_true",
        help="Print just the generated tag/attribute reference.",
    )
    pllm.set_defaults(func=_cmd_llm_help)

    # ``test`` forwards everything after it to pytest. The subparser exists so
    # ``--help`` lists it, but the real interception happens in ``main`` before
    # argparse sees the (pytest-owned) trailing arguments.
    ptest = sub.add_parser("test", help="Pass through to pytest (needs the dev extra).")
    ptest.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to pytest (e.g. -k login tests/).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``wijjit`` console script.

    Parameters
    ----------
    argv : list of str, optional
        Argument vector (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Process exit code.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    # ``test`` forwards everything after it to pytest. Intercept before argparse
    # so leading options (e.g. ``-k``, ``--co``) aren't mis-parsed by argparse's
    # REMAINDER handling.
    if argv and argv[0] == "test":
        return _run_pytest(argv[1:])

    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
