"""Regenerate the README / docs screenshots and the example gallery.

Drives a curated set of bundled example apps headlessly through the ``wijjit
render`` machinery, captures the styled ANSI screen, and renders each to an SVG
via Rich. The output is deterministic (no real TTY needed), so it can run in CI.

Usage
-----
From the repo root::

    uv run python scripts/make_screenshots.py            # both sets
    uv run python scripts/make_screenshots.py --readme   # hero shots only
    uv run python scripts/make_screenshots.py --gallery  # gallery only
    uv run python scripts/make_screenshots.py --only todo,login   # named shots

Writes ``docs/assets/screenshots/<slug>.svg`` for every entry in ``SHOTS`` (the
hero shots the README and docs embed) and
``docs/assets/screenshots/gallery/<slug>.svg`` for every entry in ``GALLERY``
(the wider tour linked from ``examples/GALLERY.md``).

Notes
-----
SVGs are text-crisp at any zoom and render inline on GitHub, which serves them
as ``image/svg+xml``. PyPI's description sanitizer also permits ``<img>`` with
no host restriction, so the same URLs work on the project page.

Determinism: demos that generate sample data from ``random`` seed it at import,
and every render runs in a throwaway working directory, so re-running this
script only rewrites an SVG when the example or the framework actually changed.
Keep it that way -- an unseeded demo turns every regeneration into a large
meaningless diff.

Two shots are inherently live and *will* produce a diff on every run:
``dashboard`` and ``system_monitor`` both display a wall-clock timestamp (and
the latter, real machine metrics). That is what those demos are for; just don't
regenerate them casually, and don't mistake their churn for a real change. Use
``--only`` when fixing an unrelated screenshot so their noise stays out of the
diff.
"""

from __future__ import annotations

import html
import io
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "screenshots"
GALLERY_OUT = OUT / "gallery"

# (slug, example path, (width, height), keys script, tick frames, SVG title)
SHOTS: list[tuple[str, str, tuple[int, int], str, int, str]] = [
    (
        "charts",
        "examples/widgets/charts_demo.py",
        (84, 40),
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
        "type:admin,tab,type:hunter2",
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

# The wider tour rendered into ``gallery/`` and indexed by examples/GALLERY.md.
# Same tuple shape as SHOTS. Sizes are chosen per demo so nothing clips; a demo
# that needs interaction to look like anything gets a short key script.
GALLERY: list[tuple[str, str, tuple[int, int], str, int, str]] = [
    # -- Applications --------------------------------------------------------
    (
        "system_monitor",
        "examples/apps/system_monitor.py",
        (94, 34),
        "",
        2,
        "wijjit - system_monitor.py",
    ),
    (
        "spreadsheet",
        "examples/apps/spreadsheet.py",
        (106, 28),
        "",
        0,
        "wijjit - spreadsheet.py",
    ),
    # The input is autofocus, so no leading tab. The bot streams its reply from
    # a background task, so "settle" pumps event-loop frames until that
    # finishes -- without it the capture catches the bot mid-sentence.
    (
        "chatbot",
        "examples/apps/chatbot.py",
        (84, 30),
        "type:help,enter,settle:400",
        0,
        "wijjit - chatbot.py",
    ),
    # -- Layout --------------------------------------------------------------
    (
        "dashboard",
        "examples/advanced/dashboard_demo.py",
        (122, 40),
        "",
        2,
        "wijjit - dashboard_demo.py",
    ),
    (
        "splitpanel_nested",
        "examples/advanced/splitpanel_nested_demo.py",
        (120, 28),
        "",
        0,
        "wijjit - splitpanel_nested_demo.py",
    ),
    (
        "hstack_flexbox",
        "examples/basic/hstack_flexbox_demo.py",
        (84, 32),
        "",
        0,
        "wijjit - hstack_flexbox_demo.py",
    ),
    (
        "grid",
        "examples/basic/grid_demo.py",
        (76, 38),
        "",
        0,
        "wijjit - grid_demo.py",
    ),
    # -- Data display --------------------------------------------------------
    (
        "table",
        "examples/widgets/table_demo.py",
        (104, 31),
        "",
        0,
        "wijjit - table_demo.py",
    ),
    # Expanded by clicking indicators: the `expanded=` state binding is dropped
    # at element creation (roadmap Group E, deferred to 0.1.1), so the initial
    # screen would show a single collapsed root. Clicks: expand "project",
    # expand "src", select "main.py" (populates the File Details pane).
    (
        "tree",
        "examples/widgets/tree_demo.py",
        (74, 28),
        "click:5,5,click:8,6,click:14,9",
        0,
        "wijjit - tree_demo.py",
    ),
    (
        "datagrid",
        "examples/widgets/datagrid_demo.py",
        (78, 30),
        "",
        0,
        "wijjit - datagrid_demo.py",
    ),
    (
        "logview",
        "examples/widgets/logview_demo.py",
        (102, 18),
        "",
        0,
        "wijjit - logview_demo.py",
    ),
    # (filesystem_browser.py is deliberately absent: it browses the working
    # directory, so under the scratch-CWD isolation above it would only ever
    # show an empty temp folder with a random name.)
    (
        "imageview",
        "examples/widgets/imageview_demo.py",
        (86, 32),
        "",
        0,
        "wijjit - imageview_demo.py",
    ),
    # -- Input and overlays --------------------------------------------------
    (
        "form",
        "examples/advanced/form_demo.py",
        (94, 40),
        "",
        0,
        "wijjit - form_demo.py",
    ),
    # Driven open with "d": an overlay dialog is the point of the demo, and the
    # initial screen is just a file list. (dialog_showcase.py would cover more
    # dialog types but its side-by-side child frames hit the horizontal
    # child-frame scroll bug deferred to 0.1.1, so it screenshots badly.)
    (
        "dialogs",
        "examples/widgets/confirm_dialog_demo.py",
        (62, 17),
        "d",
        0,
        "wijjit - confirm_dialog_demo.py",
    ),
    (
        "tabbedpanel",
        "examples/widgets/tabbedpanel_demo.py",
        (84, 36),
        "",
        0,
        "wijjit - tabbedpanel_demo.py",
    ),
    (
        "autocomplete",
        "examples/basic/autocomplete_demo.py",
        (92, 32),
        "type:py",
        0,
        "wijjit - autocomplete_demo.py",
    ),
    # -- Theming -------------------------------------------------------------
    (
        "css_theme",
        "examples/styling/css_theme_demo.py",
        (84, 36),
        "",
        0,
        "wijjit - css_theme_demo.py",
    ),
]


def capture_ansi(path: str, size: tuple[int, int], keys: str, tick: int) -> str:
    """Render an example headlessly and return its styled ANSI screen.

    Notes
    -----
    Output is reproducible on two counts. The demos that generate sample data
    from ``random`` seed it at import, so re-running this script rewrites the
    SVGs only when the example or the framework actually changed. And each
    render runs in a throwaway working directory, because some demos persist
    state next to the CWD (``todo_app.py`` auto-saves its list to ``./todo.md``)
    -- run from the repo root, that would both litter the tree and make the
    capture depend on whatever a previous run left behind.
    """
    width, height = size
    cmd = [
        sys.executable,
        "-m",
        "wijjit",
        "render",
        str(ROOT / path),
        "--size",
        f"{width}x{height}",
        "--ansi",
    ]
    if keys:
        cmd += ["--keys", keys]
    if tick:
        cmd += ["--tick", str(tick)]
    with tempfile.TemporaryDirectory() as scratch:
        result = subprocess.run(
            cmd,
            cwd=scratch,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    return result.stdout


# A terminal line's glyphs live in <text> runs clipped to a per-line rect
# (``...-line-N``); the window chrome (title, border) uses other clips, so this
# marker is what tells the two apart when we regrid.
_LINE_TEXT_RE = re.compile(r"<text ([^>]*?)>(.*?)</text>", re.DOTALL)
_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_TEXTLEN_RE = re.compile(r'textLength="([0-9.]+)"')


def _regrid_svg(svg: str) -> str:
    """Pin every glyph to its terminal cell so charts stay aligned.

    Rich emits each colour-contiguous span of a line as one ``<text>`` run with
    ``textLength`` and the default ``lengthAdjust="spacing"``, which only
    redistributes inter-glyph gaps. A glyph whose natural advance differs from
    the base cell -- block elements, braille dots, some box-drawing -- therefore
    drifts the rest of its run off the grid, so a chart column no longer sits
    over its axis. That drift is what makes the column and line charts look
    mis-rendered in a viewer that lacks the embedded font.

    This rewrites each terminal-line run into one ``<text>`` per cell, placed at
    its exact column and forced to a single cell width via
    ``lengthAdjust="spacingAndGlyphs"``. Every glyph is then squeezed or stretched
    into precisely its cell regardless of the rendering font's advances, so the
    grid holds. Backgrounds are separate ``<rect>`` elements Rich already places
    by pixel, so they are untouched.
    """
    lengths = [float(m) for m in _TEXTLEN_RE.findall(svg)]
    if not lengths:
        return svg
    cell_w = min(lengths)  # the width of a single narrow cell (a border, say)

    def rewrite(match: re.Match[str]) -> str:
        attrs = dict(_ATTR_RE.findall(match.group(1)))
        clip = attrs.get("clip-path", "")
        if "-line-" not in clip:
            return match.group(0)  # window chrome, not a terminal line
        content = html.unescape(match.group(2))
        x0 = float(attrs["x"])
        y = attrs["y"]
        cls = attrs.get("class", "")
        cls_attr = f'class="{cls}" ' if cls else ""
        cells: list[str] = []
        col = 0
        for char in content:
            width = cell_len(char)
            if char.strip():  # spaces render nothing; backgrounds are rects
                gx = x0 + col * cell_w
                cells.append(
                    f'<text {cls_attr}x="{gx:g}" y="{y}" '
                    f'textLength="{width * cell_w:g}" '
                    f'lengthAdjust="spacingAndGlyphs" '
                    f'clip-path="{clip}">{html.escape(char)}</text>'
                )
            col += width
        return "".join(cells)

    return _LINE_TEXT_RE.sub(rewrite, svg)


def to_svg(ansi: str, dst: Path, title: str) -> None:
    """Convert a captured ANSI screen to an SVG file via Rich.

    The SVG is post-processed by :func:`_regrid_svg` so block-element and braille
    glyphs (charts) stay pinned to the monospace grid in any viewer.
    """
    lines = ansi.splitlines()
    width = max((Text.from_ansi(line).cell_len for line in lines), default=80)
    # Record into an in-memory sink so nothing hits the OS stdout encoding
    # (braille/box-drawing glyphs would break a cp1252 file on Windows).
    console = Console(record=True, width=width, height=len(lines), file=io.StringIO())
    for line in lines:
        console.print(Text.from_ansi(line), no_wrap=True, overflow="ignore")
    dst.write_text(_regrid_svg(console.export_svg(title=title)), encoding="utf-8")


def render_set(
    shots: list[tuple[str, str, tuple[int, int], str, int, str]],
    out_dir: Path,
    only: set[str] | None = None,
) -> None:
    """Render every shot in ``shots`` into ``out_dir``.

    Parameters
    ----------
    shots : list of tuple
        Shot definitions, as in :data:`SHOTS` / :data:`GALLERY`.
    out_dir : Path
        Directory to write the SVGs into.
    only : set of str, optional
        When given, render just these slugs and skip the rest.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for slug, path, size, keys, tick, title in shots:
        if only is not None and slug not in only:
            continue
        ansi = capture_ansi(path, size, keys, tick)
        dst = out_dir / f"{slug}.svg"
        to_svg(ansi, dst, title)
        print(f"wrote {dst.relative_to(ROOT)} ({size[0]}x{size[1]})")


def main() -> int:
    argv = sys.argv[1:]

    # --only SLUG[,SLUG...] renders a subset. This exists because two shots
    # (dashboard, system_monitor) are inherently live and rewrite themselves on
    # every run; without a filter, fixing one unrelated screenshot drags their
    # churn into the diff and hides the change you actually made.
    only: set[str] | None = None
    if "--only" in argv:
        idx = argv.index("--only")
        if idx + 1 >= len(argv):
            print("--only needs a comma-separated list of slugs", file=sys.stderr)
            return 2
        only = {s.strip() for s in argv[idx + 1].split(",") if s.strip()}
        del argv[idx : idx + 2]

    flags = set(argv)
    unknown = flags - {"--readme", "--gallery"}
    if unknown:
        print(f"unknown option(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2

    # No flag means both sets.
    want_readme = "--readme" in flags or not flags
    want_gallery = "--gallery" in flags or not flags

    if only is not None:
        known = {s[0] for s in SHOTS} | {s[0] for s in GALLERY}
        unknown_slugs = only - known
        if unknown_slugs:
            print(
                f"unknown slug(s): {', '.join(sorted(unknown_slugs))}", file=sys.stderr
            )
            return 2

    if want_readme:
        render_set(SHOTS, OUT, only)
    if want_gallery:
        render_set(GALLERY, GALLERY_OUT, only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
