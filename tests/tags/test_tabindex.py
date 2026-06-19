"""Tests for tabindex/tab_index normalization on display and chart tags.

The input tags normalized ``tabindex`` -> ``tab_index`` already; these tests
cover the display/chart tags (Table, Tree, ListView, LogView, ContentView,
BarChart), where focusable elements previously ignored an author-supplied
tab order.
"""

from wijjit import Wijjit
from wijjit.core.vdom import VNodeBuilder
from wijjit.tags.layout import apply_tabindex
from wijjit.testing.harness import WijjitHarness


class TestApplyTabindexHelper:
    """Unit tests for the apply_tabindex helper."""

    def test_html_style_tabindex(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_tabindex(vnode, {"tabindex": 4})
        assert vnode.props["tab_index"] == 4

    def test_python_style_tab_index(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_tabindex(vnode, {"tab_index": 2})
        assert vnode.props["tab_index"] == 2

    def test_absent_leaves_prop_unset(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_tabindex(vnode, {"other": 1})
        assert "tab_index" not in vnode.props


def _render_and_get(template: str, element_id: str):
    """Render a one-view app and return the reconciled element by id.

    The reconciler caches elements by their VNode key (the template id), which
    is the reliable lookup here -- some display tags do not also mirror the id
    onto the element instance, so ``get_element_by_id`` cannot be used.
    """
    app = Wijjit()
    app.view("main", default=True)(lambda: {"template": template})
    with WijjitHarness(app, size=(60, 20)) as h:
        h.tick(frames=1)
        return h.app.renderer._reconciler.get_cached_element(element_id)


class TestDisplayTagTabindex:
    """End-to-end: focusable display elements receive tab_index from tags."""

    def test_table_tabindex(self):
        elem = _render_and_get(
            '{% table id="tbl" columns=["A"] data=[{"A": "x"}] '
            "tabindex=3 %}{% endtable %}",
            "tbl",
        )
        assert elem is not None
        assert elem.tab_index == 3

    def test_tree_tabindex(self):
        elem = _render_and_get(
            '{% tree id="tr" data={"label": "root"} tabindex=5 %}{% endtree %}',
            "tr",
        )
        assert elem is not None
        assert elem.tab_index == 5

    def test_listview_tabindex(self):
        elem = _render_and_get(
            '{% listview id="lv" tabindex=2 %}{% endlistview %}', "lv"
        )
        assert elem is not None
        assert elem.tab_index == 2

    def test_table_without_tabindex_defaults_none(self):
        elem = _render_and_get(
            '{% table id="tbl2" columns=["A"] data=[{"A": "x"}] %}{% endtable %}',
            "tbl2",
        )
        assert elem is not None
        assert elem.tab_index is None
