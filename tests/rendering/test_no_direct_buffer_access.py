"""Ratchet: forbid direct ScreenBuffer access from element render code.

Elements must paint through PaintContext (``write_text``, ``write_cell``,
``write_cells``, ``fill_rect``, ``draw_border``, ...) so the clip region is
enforced and wide characters are written column-correct (review items 2.1 and
2.11). Direct ``ctx.buffer.set_cell(...)``-style calls bypass both.

This test scans element sources for direct buffer access and compares the
per-file count against a shrinking allowance. The allowance may only go DOWN:

- Migrating a file to PaintContext? Set its allowance to 0 (or delete the
  entry - a missing entry means 0).
- Adding a *new* direct buffer call anywhere fails this test. Use the
  PaintContext API instead; extend it if it cannot express what you need.
"""

import re
from pathlib import Path

import wijjit.elements

ELEMENTS_DIR = Path(wijjit.elements.__file__).parent

DIRECT_BUFFER_ACCESS = re.compile(
    r"\.buffer\.(set_cell|get_cell|set_cells_horizontal|set_cells_vertical"
    r"|fill_rect)\("
)

# Remaining direct-buffer-access allowance per file (relative to
# src/wijjit/elements/). Counts as of 2026-07-13; each migration workstream
# lowers its file to zero. Do not raise any number.
ALLOWED = {
    "base.py": 1,
    "display/barchart.py": 4,
    "display/columnchart.py": 10,
    "display/contentview.py": 13,
    "display/gauge.py": 5,
    "display/heatmap.py": 4,
    "display/linechart.py": 7,
    "display/list.py": 21,
    "display/logview.py": 27,
    "display/pager.py": 4,
    "display/sparkline.py": 3,
    "display/tabbed_panel.py": 52,
    "display/table.py": 3,
    "display/tree.py": 24,
    "input/code_editor.py": 11,
    "input/text.py": 19,
}


def _count_direct_access() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(ELEMENTS_DIR.rglob("*.py")):
        rel = path.relative_to(ELEMENTS_DIR).as_posix()
        n = len(DIRECT_BUFFER_ACCESS.findall(path.read_text(encoding="utf-8")))
        if n:
            counts[rel] = n
    return counts


def test_no_new_direct_buffer_access():
    """Every element file stays at or below its direct-access allowance."""
    counts = _count_direct_access()

    over = {
        rel: (n, ALLOWED.get(rel, 0))
        for rel, n in counts.items()
        if n > ALLOWED.get(rel, 0)
    }
    assert not over, (
        "Direct ScreenBuffer access from element code exceeds the ratchet "
        f"allowance (found, allowed): {over}. Paint through the PaintContext "
        "API (write_text/write_cell/write_cells/fill_rect/draw_border) so the "
        "clip region and wide-character handling apply."
    )


def test_ratchet_allowances_not_stale():
    """Allowance entries must shrink as files are migrated, not linger."""
    counts = _count_direct_access()

    stale = {
        rel: (counts.get(rel, 0), allowed)
        for rel, allowed in ALLOWED.items()
        if counts.get(rel, 0) < allowed
    }
    assert not stale, (
        "These files now have fewer direct buffer calls than their ratchet "
        f"allowance (found, allowed): {stale}. Lower the ALLOWED entries in "
        "tests/rendering/test_no_direct_buffer_access.py to match (or delete "
        "them at zero) so the ratchet cannot slide back up."
    )
