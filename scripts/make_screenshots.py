"""Regenerate the README / docs screenshots.

Drives a curated set of bundled example apps headlessly through the ``wijjit
render`` machinery, captures the styled ANSI screen, and renders each to an SVG
via Rich. The output is deterministic (no real TTY needed), so it can run in CI.

Usage
-----
From the repo root::

    uv run python scripts/make_screenshots.py

Writes ``docs/assets/screenshots/<slug>.svg`` for every entry in ``SHOTS``.

Notes
-----
SVGs are text-crisp at any zoom and render inline on GitHub. If the PyPI project
page does not render an SVG ``<img>``, rasterize these to PNG (e.g. with
``cairosvg``) and point the README at the PNGs instead.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "screenshots"

# (slug, example path, (width, height), keys script, tick frames, SVG title)
SHOTS: list[tuple[str, str, tuple[int, int], str, int, str]] = [
    (
        "charts",
        "examples/widgets/charts_demo.py",
        (100, 36),
        "",
        2,
        "wijjit - charts_demo.py",
    ),
    (
        "todo",
        "examples/apps/todo_app.py",
        (74, 28),
        "",
        0,
        "wijjit - todo_app.py",
    ),
    (
        "login",
        "examples/advanced/login_form.py",
        (60, 18),
        "tab,type:admin,tab,type:hunter2",
        0,
        "wijjit - login_form.py",
    ),
    (
        "code_editor",
        "examples/widgets/code_editor_demo.py",
        (92, 30),
        "",
        0,
        "wijjit - code_editor_demo.py",
    ),
]


def capture_ansi(path: str, size: tuple[int, int], keys: str, tick: int) -> str:
    """Render an example headlessly and return its styled ANSI screen."""
    width, height = size
    cmd = [
        sys.executable,
        "-m",
        "wijjit",
        "render",
        path,
        "--size",
        f"{width}x{height}",
        "--ansi",
    ]
    if keys:
        cmd += ["--keys", keys]
    if tick:
        cmd += ["--tick", str(tick)]
    result = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout


def to_svg(ansi: str, dst: Path, title: str) -> None:
    """Convert a captured ANSI screen to an SVG file via Rich."""
    lines = ansi.splitlines()
    width = max((Text.from_ansi(line).cell_len for line in lines), default=80)
    # Record into an in-memory sink so nothing hits the OS stdout encoding
    # (braille/box-drawing glyphs would break a cp1252 file on Windows).
    console = Console(record=True, width=width, height=len(lines), file=io.StringIO())
    for line in lines:
        console.print(Text.from_ansi(line), no_wrap=True, overflow="ignore")
    console.save_svg(str(dst), title=title)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, path, size, keys, tick, title in SHOTS:
        ansi = capture_ansi(path, size, keys, tick)
        dst = OUT / f"{slug}.svg"
        to_svg(ansi, dst, title)
        print(f"wrote {dst.relative_to(ROOT)} ({size[0]}x{size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
