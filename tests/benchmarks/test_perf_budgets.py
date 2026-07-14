"""Deterministic performance budgets (review Part 4, item 7).

The benchmark suite (``test_performance.py``) measures wall-clock time via
pytest-benchmark but asserts nothing, so a large regression passes silently.
Wall-clock thresholds would flake on shared CI runners, so these budgets pin
the *deterministic* proxies that define Wijjit's honest perf story instead:
bytes emitted to the terminal and layout passes per frame. They extend the
pattern established by ``tests/core/test_diff_render_bytes.py`` to a
representative multi-element dashboard, the app-level keystroke path, and
the layout engine.

Budgets are measured values with generous headroom, noted per test. If a
budget trips, either a regression landed (fix it) or the cost genuinely
changed (re-measure and update the budget in the same change, with a note).
"""

import pytest

from wijjit.core.renderer import Renderer

DASHBOARD = """
{% vstack width=100 height=30 %}
  {% frame height=3 title="Dash" %}Tick {{ tick }}{% endframe %}
  {% hstack height=14 %}
    {% frame width=50 title="Table" %}
      {% table id="t" columns=["A","B"] data=rows height=10 %}{% endtable %}
    {% endframe %}
    {% frame width=50 title="Chart" %}
      {% columnchart id="c" data=chart width=44 height=10 show_axis=true %}{% endcolumnchart %}
    {% endframe %}
  {% endhstack %}
  {% frame id="log" height=10 title="Log" scrollable=true %}
    {% vstack spacing=0 %}{% for l in lines %}{% text %}{{ l }}{% endtext %}{% endfor %}{% endvstack %}
  {% endframe %}
{% endvstack %}
"""

DASH_CONTEXT = {
    "rows": [{"A": f"a{i}", "B": f"b{i}"} for i in range(8)],
    "chart": [("X", 5), ("Y", 9), ("Z", 3)],
    "lines": [f"line {i}" for i in range(20)],
}

WIDTH, HEIGHT = 100, 30


def _render_dash(renderer: Renderer, tick: int) -> str:
    out, _, _ = renderer.render_with_layout(
        DASHBOARD,
        context={"tick": tick, **DASH_CONTEXT},
        width=WIDTH,
        height=HEIGHT,
    )
    return out


class TestDashboardByteBudgets:
    """Emitted-byte budgets for a representative multi-element screen."""

    def test_idle_frame_emits_nothing(self):
        renderer = Renderer()
        _render_dash(renderer, 0)
        assert _render_dash(renderer, 0) == ""

    def test_full_repaint_scales_with_screen_area(self):
        renderer = Renderer()
        _render_dash(renderer, 0)
        renderer._last_displayed_buffer = None
        full = _render_dash(renderer, 0)
        assert len(full) >= WIDTH * HEIGHT

    def test_one_value_change_emits_a_tiny_diff(self):
        """One changed template value repaints only its cells.

        Measured 2026-07-13: 7 bytes (the tick digit). Budget 100 gives
        ample headroom for styling changes while staying ~50x under a full
        repaint (~4950 bytes).
        """
        renderer = Renderer()
        _render_dash(renderer, 0)
        changed = _render_dash(renderer, 1)
        assert 0 < len(changed) <= 100, f"one-value change emitted {len(changed)} bytes"


class TestAppLevelByteBudgets:
    """End-to-end budgets through real event dispatch (harness capture)."""

    SCROLL_TPL = """
{% vstack spacing=0 %}
{% text %}header{% endtext %}
{% frame id="scroller" border="single" width=60 height=12 scrollable=true %}
  {% vstack spacing=0 %}{% for i in range(40) %}{% text %}row {{ i }}{% endtext %}{% endfor %}{% endvstack %}
{% endframe %}
{% textinput id="inp" placeholder="type here" width=30 %}{% endtextinput %}
{% endvstack %}
"""

    def _harness(self):
        from wijjit.testing import WijjitHarness, app_from_template

        app = app_from_template(self.SCROLL_TPL)
        return app, WijjitHarness(app, size=(80, 24))

    def test_scroll_one_line_repaints_only_the_frame_interior(self):
        """Scrolling one line must not repaint outside the frame.

        Also guards the Part-A clip sweep: unclipped element writes would
        dirty rows outside the interior. Measured 2026-07-13: 78 bytes vs a
        ~3100-byte full paint.
        """
        app, harness = self._harness()
        with harness as h:
            full = len(h.emitted_frames[0])
            frame = app.get_element_by_id("scroller")
            assert frame.scroll_manager is not None
            frame.scroll_manager.scroll_to(1)
            h.tick()
            scroll_diff = len(h.last_frame)
            assert 0 < scroll_diff < full / 5, (
                f"one-line scroll emitted {scroll_diff} bytes "
                f"(full paint is {full})"
            )

    def test_steady_state_keystroke_emits_a_small_diff(self):
        """A keystroke into a focused input emits a small diff end-to-end.

        The *first* keystroke restyles the whole input row (placeholder ->
        value transition) and is deliberately not budgeted here; the
        steady-state keystroke is the hot path. Measured 2026-07-13: 84
        bytes. Budget 300 leaves headroom for theme/SGR changes. (The
        per-cell SGR redundancy that inflates diff runs is review item
        2.12; if that is fixed this number should drop, not grow.)
        """
        app, harness = self._harness()
        with harness as h:
            assert app.focus_element_by_id("inp")
            h.tick()  # flush the focus restyle frame
            h.type("x")  # transition frame (unbudgeted)
            h.type("y")  # steady-state frame
            frame = h.last_frame
            assert (
                0 < len(frame) <= 300
            ), f"steady-state keystroke emitted {len(frame)} bytes"


class TestLayoutPassBudget:
    """Pin the layout-pass count so review item 2.4 cannot get worse.

    ``FrameNode.assign_bounds`` re-runs the whole subtree layout a second
    time when a scrollable frame needs a scrollbar column, so nesting
    scrollable frames doubles per level: a depth-3 chain costs 7 passes
    (1 + 2 + 4) per render today. That O(2^depth) behavior is review item
    2.4; this test pins the current cost so a fix ratchets it DOWN and any
    regression that adds another multiplier fails loudly.
    """

    NESTED = """
{% frame id="f1" height=20 scrollable=true %}{% frame id="f2" height=24 scrollable=true %}{% frame id="f3" height=28 scrollable=true %}
{% vstack spacing=0 %}{% for i in range(30) %}{% text %}row {{ i }}{% endtext %}{% endfor %}{% endvstack %}
{% endframe %}{% endframe %}{% endframe %}
"""

    def test_nested_scrollable_frames_layout_pass_count(self, monkeypatch):
        from wijjit.layout.engine import FrameNode

        calls = {"n": 0}
        orig = FrameNode.assign_bounds

        def spy(self, *args, **kwargs):
            calls["n"] += 1
            return orig(self, *args, **kwargs)

        monkeypatch.setattr(FrameNode, "assign_bounds", spy)
        renderer = Renderer()
        renderer.render_with_layout(self.NESTED, width=80, height=24)

        # Measured 2026-07-13: 7 (the 2^depth - 1 doubling of review 2.4).
        assert 0 < calls["n"] <= 7, (
            f"depth-3 nested scrollable frames took {calls['n']} "
            "FrameNode.assign_bounds passes (was 7; see review item 2.4)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
