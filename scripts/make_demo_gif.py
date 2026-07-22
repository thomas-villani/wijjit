"""Record an animated GIF of a bundled example -- without a terminal.

This is the moving counterpart to ``make_screenshots.py``. Rather than screen-
recording a real TTY (the usual approach, via asciinema/VHS and an ffmpeg
toolchain), it drives the app through :class:`wijjit.testing.WijjitHarness`,
captures the styled ANSI screen after each scripted step, and rasterizes those
frames with Pillow. No terminal, no external binaries, and the result is
deterministic -- the same script always produces the same GIF.

Usage
-----
From the repo root::

    uv run python scripts/make_demo_gif.py                  # every clip
    uv run python scripts/make_demo_gif.py todo             # one clip
    uv run python scripts/make_demo_gif.py --font PATH.ttf  # pick the font

Writes ``docs/assets/screenshots/<slug>.gif`` for every entry in ``CLIPS``.
Animated GIFs render on GitHub and on the PyPI project page, so the output can
be embedded the same way the SVG stills are.

Requirements
------------
Pillow (the ``images`` extra: ``uv pip install "wijjit[images]"``) and a
monospace TTF that covers box-drawing and braille glyphs. Common system fonts
are auto-detected; override with ``--font``.

Notes
-----
Each cell is drawn as one column, so a clip containing double-width characters
(CJK, emoji) would drift out of alignment. The bundled clips are all
single-width; keep it that way, or teach ``render_frame`` about wcwidth.
"""

from __future__ import annotations

import contextlib
import sys
import tempfile
from pathlib import Path
from typing import Any

from _termshot import FontSet, find_font, parse_screen, render_frame
from PIL import Image

from wijjit.testing import WijjitHarness, load_example_app

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "screenshots"

# A step is (action, hold_ms). The action is the same mini-language ``wijjit
# render --keys`` uses, with one addition: "" means "change nothing, just hold",
# which is how a clip pauses so a viewer can read the screen.
#   "tab" / "enter" / "space"  -> a key press
#   "type:TEXT"                -> typed one character per frame (typewriter)
#   "tick:N"                   -> advance N animation frames
CLIPS: dict[str, dict[str, Any]] = {
    "todo": {
        "example": "examples/apps/todo_app.py",
        "size": (74, 26),
        "steps": [
            ("", 1400),  # opening screen
            ("tab", 400),  # focus the input
            ("type:Ship wijjit 0.1.0", 60),  # typewriter
            ("", 500),
            ("enter", 1000),  # the item is added to the list
            # Seven tabs walk focus Add -> filter -> each existing checkbox and
            # land on the item we just added (see the tab order in todo_app.py).
            ("tab", 160),
            ("tab", 160),
            ("tab", 160),
            ("tab", 160),
            ("tab", 160),
            ("tab", 160),
            ("tab", 500),
            ("space", 2000),  # check it off; the counter ticks over
        ],
    },
    "charts": {
        "example": "examples/widgets/charts_demo.py",
        "size": (100, 40),
        "steps": [
            ("tick:2", 1600),
            ("r", 1400),  # refresh re-rolls every chart
            ("r", 1400),
            ("r", 1800),
        ],
    },
}


def build_clip(
    spec: dict[str, Any], fonts: FontSet
) -> tuple[list[Image.Image], list[int]]:
    """Drive one example and return its (frames, per-frame durations)."""
    cols, rows = spec["size"]
    frames: list[Image.Image] = []
    durations: list[int] = []

    def capture(harness: WijjitHarness, hold: int) -> None:
        grid = parse_screen(harness.screen_ansi())
        frames.append(render_frame(grid, fonts, cols, rows))
        durations.append(hold)

    # Run in a scratch directory. Some demos persist to the working directory
    # (todo_app.py auto-saves its list to ./todo.md), which would otherwise both
    # pollute the repo and make the clip depend on whatever was left behind by
    # the last run -- the demo would open with items from a previous recording.
    with tempfile.TemporaryDirectory() as scratch, contextlib.chdir(scratch):
        app = load_example_app(str(ROOT / spec["example"]))
        with WijjitHarness(app, size=(cols, rows)) as harness:
            for action, hold in spec["steps"]:
                if not action:
                    capture(harness, hold)
                elif action.startswith("type:"):
                    # One frame per character, so it reads as typing.
                    for char in action[len("type:") :]:
                        harness.type(char)
                        capture(harness, hold)
                elif action.startswith("tick:"):
                    harness.tick(frames=int(action[len("tick:") :]))
                    capture(harness, hold)
                else:
                    harness.press(action)
                    capture(harness, hold)

    return frames, durations


def main() -> int:
    argv = sys.argv[1:]
    font_path = None
    if "--font" in argv:
        idx = argv.index("--font")
        font_path = argv[idx + 1]
        del argv[idx : idx + 2]

    wanted = argv or list(CLIPS)
    unknown = [name for name in wanted if name not in CLIPS]
    if unknown:
        print(f"unknown clip(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"available: {', '.join(CLIPS)}", file=sys.stderr)
        return 2

    fonts = find_font(font_path)
    OUT.mkdir(parents=True, exist_ok=True)

    for name in wanted:
        frames, durations = build_clip(CLIPS[name], fonts)
        dst = OUT / f"{name}.gif"
        # Quantize together so the palette is stable across frames (otherwise
        # colours shimmer as each frame picks its own 256).
        quantized = [
            f.quantize(colors=255, method=Image.Quantize.MEDIANCUT) for f in frames
        ]
        quantized[0].save(
            dst,
            save_all=True,
            append_images=quantized[1:],
            duration=durations,
            loop=0,
            optimize=True,
            disposal=2,
        )
        size_kb = dst.stat().st_size / 1024
        print(f"wrote {dst.relative_to(ROOT)} ({len(frames)} frames, {size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
