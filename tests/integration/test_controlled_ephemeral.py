"""Declarative ("controlled") ephemeral props (review 2.6).

Ephemeral UI state - cursor position, scroll offset, selection, highlight - is
preserved across re-renders rather than force-synced from the template. Before
this change it was *strictly* one-way: a template setting ``cursor_pos={{ ... }}``
was silently ignored, so there was no declarative way to say "put the cursor
here" or "scroll this list to row N" from ``state``.

The reconciler now applies a controllable ephemeral prop when - and only when -
its bound value *changes* between renders ("state wins, else preserve"). That
changed-only rule is what keeps it safe: a live edit that moves the cursor/scroll
without changing the bound value is preserved, so the caret does not snap back on
every keystroke (the React controlled-input footgun).

These tests pin both halves:

1. **Apply on change** - changing the bound value repositions the element.
2. **Preserve when unchanged** - a live cursor/scroll move survives a re-render
   whose bound value did not change.

Plus unit coverage of :meth:`Reconciler._diff_controlled_ephemeral`, including
that ``focused``/``hovered`` are deliberately *not* controllable (focus is the
FocusManager's job; hover is mouse-driven).
"""

from __future__ import annotations

from wijjit import Wijjit, render_template_string
from wijjit.core.element_registry import ElementRegistry
from wijjit.core.reconciler import Reconciler
from wijjit.core.vdom import CONTROLLABLE_EPHEMERAL_PROPS, EPHEMERAL_PROPS
from wijjit.testing import WijjitHarness

# --------------------------------------------------------------------------
# Unit: the diff helper - changed-only, controllable subset only.
# --------------------------------------------------------------------------


def _props(**kwargs: object) -> tuple[tuple[str, object], ...]:
    return tuple(sorted(kwargs.items()))


def _reconciler() -> Reconciler:
    return Reconciler(ElementRegistry())


def test_controllable_subset_excludes_focus_and_hover():
    """Focus and hover are ephemeral but not declaratively controllable."""
    assert "focused" not in CONTROLLABLE_EPHEMERAL_PROPS
    assert "hovered" not in CONTROLLABLE_EPHEMERAL_PROPS
    # Everything else ephemeral is controllable.
    assert CONTROLLABLE_EPHEMERAL_PROPS == EPHEMERAL_PROPS - {"focused", "hovered"}


def test_diff_reports_changed_controllable_prop():
    """A changed cursor_pos becomes a controlled-ephemeral change."""
    r = _reconciler()
    controlled = r._diff_controlled_ephemeral(
        _props(cursor_pos=0), _props(cursor_pos=5)
    )
    assert controlled == {"cursor_pos": (0, 5)}


def test_diff_ignores_unchanged_controllable_prop():
    """An unchanged bound value is not applied (preserve the live value)."""
    r = _reconciler()
    controlled = r._diff_controlled_ephemeral(
        _props(cursor_pos=5), _props(cursor_pos=5)
    )
    assert controlled == {}


def test_diff_ignores_focused_even_when_changed():
    """focused is ephemeral but excluded from declarative control."""
    r = _reconciler()
    controlled = r._diff_controlled_ephemeral(
        _props(focused=False), _props(focused=True)
    )
    assert controlled == {}


def test_diff_does_not_report_removed_ephemeral_prop():
    """Dropping a binding means 'stop controlling', not 'reset to None'."""
    r = _reconciler()
    controlled = r._diff_controlled_ephemeral(_props(cursor_pos=5), _props())
    assert controlled == {}


def test_regular_prop_diff_still_skips_ephemeral():
    """Ephemeral props never leak into the ordinary prop-change path."""
    r = _reconciler()
    changes = r._diff_props(_props(cursor_pos=0), _props(cursor_pos=5))
    assert changes == {}


# --------------------------------------------------------------------------
# Integration: drive real apps through the harness.
# --------------------------------------------------------------------------


def _cursor_app() -> Wijjit:
    app = Wijjit()
    app.state["name"] = "hello world"
    app.state["cur"] = 0

    tmpl = '{% vstack %}{% textinput id="name" cursor_pos=cur %}{% endtextinput %}{% endvstack %}'

    @app.view("main", default=True)
    def main():
        return render_template_string(tmpl, cur=app.state["cur"])

    return app


def test_controlled_cursor_applies_on_change():
    """Changing the bound cursor_pos repositions the caret."""
    app = _cursor_app()
    with WijjitHarness(app, size=(50, 6)) as h:
        el = app.get_element_by_id("name")
        app.state["cur"] = 5
        h.tick()
        assert el.cursor_pos == 5


def test_controlled_cursor_preserved_when_binding_unchanged():
    """A live cursor move survives a re-render with an unchanged binding."""
    app = _cursor_app()
    with WijjitHarness(app, size=(50, 6)) as h:
        el = app.get_element_by_id("name")
        app.state["cur"] = 5
        h.tick()
        # Live edit moves the caret; the bound value does not change.
        el.cursor_pos = 8
        h.tick()
        assert el.cursor_pos == 8, "an unchanged binding must not yank the caret back"
        # A genuine change to the binding wins again.
        app.state["cur"] = 2
        h.tick()
        assert el.cursor_pos == 2


def _scroll_app() -> Wijjit:
    app = Wijjit()
    app.state["sp"] = 0

    tmpl = (
        '{% vstack %}{% listview id="lst" items=items height=5 '
        "scroll_position=sp %}{% endlistview %}{% endvstack %}"
    )

    @app.view("main", default=True)
    def main():
        return render_template_string(
            tmpl, items=[f"row {i}" for i in range(30)], sp=app.state["sp"]
        )

    return app


def _scroll_pos(el: object) -> int:
    return el.scroll_manager.state.scroll_position  # type: ignore[attr-defined]


def test_controlled_scroll_applies_on_change():
    """Changing the bound scroll_position scrolls the list."""
    app = _scroll_app()
    with WijjitHarness(app, size=(40, 10)) as h:
        lst = app.get_element_by_id("lst")
        app.state["sp"] = 12
        h.tick()
        assert _scroll_pos(lst) == 12


def test_controlled_scroll_preserved_when_binding_unchanged():
    """A user scroll survives a re-render whose bound scroll did not change."""
    app = _scroll_app()
    with WijjitHarness(app, size=(40, 10)) as h:
        lst = app.get_element_by_id("lst")
        app.state["sp"] = 12
        h.tick()
        lst.scroll_manager.scroll_to(4)
        h.tick()
        assert _scroll_pos(lst) == 4, "an unchanged binding must not reset user scroll"


def _highlight_app() -> Wijjit:
    app = Wijjit()
    app.state["hi"] = 0

    tmpl = (
        '{% vstack %}{% select id="sel" options=opts '
        "highlighted_index=hi %}{% endselect %}{% endvstack %}"
    )

    @app.view("main", default=True)
    def main():
        return render_template_string(
            tmpl,
            opts=[{"value": str(i), "label": f"opt {i}"} for i in range(10)],
            hi=app.state["hi"],
        )

    return app


def test_controlled_highlight_applies_on_change():
    """Changing the bound highlighted_index moves the highlight."""
    app = _highlight_app()
    with WijjitHarness(app, size=(40, 12)) as h:
        sel = app.get_element_by_id("sel")
        app.state["hi"] = 4
        h.tick()
        assert sel.highlighted_index == 4


def test_controlled_highlight_preserved_when_binding_unchanged():
    """A live highlight move survives a re-render with an unchanged binding."""
    app = _highlight_app()
    with WijjitHarness(app, size=(40, 12)) as h:
        sel = app.get_element_by_id("sel")
        app.state["hi"] = 4
        h.tick()
        sel.highlighted_index = 7
        h.tick()
        assert sel.highlighted_index == 7
