"""Integration tests: wide (CJK) and NFD text stay column-aligned in a frame.

These drive a real app through the headless harness and assert that a bordered
frame containing wide-character content keeps its right border on a single
column across every row -- both on the initial full render and after the text
changes (exercising the diff render path).
"""

from __future__ import annotations

import unicodedata

from wijjit.terminal.ansi import visible_length
from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = """
{% frame title="幅" width=24 height=5 border="single" %}
{% text %}{{ state.msg }}{% endtext %}
{% endframe %}
"""


def _frame_rows(screen: str) -> list[str]:
    """Non-empty screen rows, trimmed of trailing fill columns."""
    return [line.rstrip() for line in screen.split("\n") if line.strip()]


def _assert_aligned(screen: str) -> None:
    """Every non-empty row shares one visible width (right border aligned)."""
    rows = _frame_rows(screen)
    assert len(rows) >= 3, f"expected a bordered frame, got:\n{screen}"
    widths = {visible_length(row) for row in rows}
    assert len(widths) == 1, (
        f"rows have differing visible widths {sorted(widths)} -> border "
        f"misalignment:\n" + "\n".join(f"{visible_length(r):3d} {r!r}" for r in rows)
    )


def test_cjk_frame_border_aligns_initial_and_after_change():
    """A CJK-filled bordered frame stays aligned across a state-driven redraw."""
    app = app_from_template(TEMPLATE, state={"msg": "日本語テスト"})
    with WijjitHarness(app, size=(40, 10)) as h:
        screen = h.screen()
        # The wide text is actually present (continuation cells are empty
        # strings, so the glyphs read contiguously in the plain-text screen).
        assert "日本語テスト" in screen
        _assert_aligned(screen)

        # Change the CJK text and re-render -> exercises the diff path.
        h.state["msg"] = "テスト"
        h.tick()
        changed = h.screen()
        assert "テスト" in changed
        _assert_aligned(changed)


def test_nfd_filename_frame_border_aligns():
    """An NFD-decomposed filename (combining marks) keeps the frame aligned."""
    nfd = unicodedata.normalize("NFD", "résumé.txt")
    app = app_from_template(TEMPLATE, state={"msg": nfd})
    with WijjitHarness(app, size=(40, 10)) as h:
        _assert_aligned(h.screen())

        # Swap to a different NFD string and redraw (diff path).
        h.state["msg"] = unicodedata.normalize("NFD", "naïve café")
        h.tick()
        _assert_aligned(h.screen())
