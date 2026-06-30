"""Tests for tabindex/tab_index normalization on display and chart tags.

The input tags normalized ``tabindex`` -> ``tab_index`` already; these tests
cover the display/chart tags (Table, Tree, ListView, LogView, ContentView,
BarChart), where focusable elements previously ignored an author-supplied
tab order.
"""

from wijjit import Wijjit
from wijjit.core.vdom import VNodeBuilder
from wijjit.tags.layout import apply_common_attributes
from wijjit.testing.harness import WijjitHarness


class TestApplyCommonAttributesHelper:
    """Unit tests for the apply_common_attributes helper.

    This single helper subsumes the former ``apply_tabindex`` and the
    per-family ``class`` -> ``classes`` copies, handling both the HTML-style
    and Python-style spellings of each shared attribute.
    """

    def test_html_style_tabindex(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_common_attributes(vnode, {"tabindex": 4})
        assert vnode.props["tab_index"] == 4

    def test_python_style_tab_index(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_common_attributes(vnode, {"tab_index": 2})
        assert vnode.props["tab_index"] == 2

    def test_tabindex_absent_leaves_prop_unset(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_common_attributes(vnode, {"other": 1})
        assert "tab_index" not in vnode.props

    def test_html_style_class(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_common_attributes(vnode, {"class": "card"})
        assert vnode.props["classes"] == "card"

    def test_python_style_classes(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_common_attributes(vnode, {"classes": "card"})
        assert vnode.props["classes"] == "card"

    def test_class_absent_leaves_prop_unset(self):
        vnode = VNodeBuilder("Table", key="t")
        apply_common_attributes(vnode, {"other": 1})
        assert "classes" not in vnode.props


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


class TestLayoutContainerClasses:
    """The ``class`` attribute now reaches the layout containers.

    Previously frame/vstack/hstack/grid/splitpanel dropped ``class`` entirely
    (``{% frame class="card" %}`` produced no ``classes`` prop). The shared
    normalization path now forwards it like every other tag.

    ``Frame`` is a styled ``Element``, so its ``classes`` are applied to the
    element and participate in class-based theming. ``vstack``/``hstack``/
    ``grid`` are realized as pure layout nodes with no styling surface, so the
    contract there is only that the tag emits the normalized ``classes`` prop
    (verified at the VNode level rather than on a styled element).
    """

    def test_frame_class_applied_to_element(self):
        elem = _render_and_get(
            '{% frame id="fr" class="card" %}hello{% endframe %}', "fr"
        )
        assert elem is not None
        assert elem.classes == {"card"}

    def test_frame_multiple_classes(self):
        elem = _render_and_get(
            '{% frame id="fr2" class="card highlight" %}hi{% endframe %}', "fr2"
        )
        assert elem is not None
        assert elem.classes == {"card", "highlight"}

    def _vnode_classes(self, template: str):
        """Render a template and return the classes prop on its single VNode."""
        app = Wijjit()
        app.view("main", default=True)(lambda: {"template": template})
        with WijjitHarness(app, size=(60, 20)) as h:
            h.tick(frames=1)
            tree = h.app.renderer._last_vnode_tree
            found = []

            def walk(node):
                if node is None:
                    return
                props = node.props_dict()
                if "classes" in props:
                    found.append(props["classes"])
                for child in getattr(node, "children", []) or []:
                    walk(child)

            walk(tree)
            return found

    def test_vstack_emits_classes_prop(self):
        assert "col" in self._vnode_classes(
            '{% vstack id="vs" class="col" %}hello{% endvstack %}'
        )

    def test_hstack_emits_classes_prop(self):
        assert "row" in self._vnode_classes(
            '{% hstack id="hs" class="row" %}hello{% endhstack %}'
        )
