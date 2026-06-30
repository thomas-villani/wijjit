"""Grid gap naming: column_gap canonical, col_gap deprecated alias (D4 / CC-4).

HStack spelled the full word ``column_gap`` while Grid abbreviated ``col_gap``
for the same axis. Grid now uses ``column_gap`` as canonical with ``col_gap``
kept as a back-compat alias.
"""

from wijjit import Wijjit
from wijjit.testing.harness import WijjitHarness


def _grid_props(template: str) -> dict:
    app = Wijjit()
    app.view("main", default=True)(lambda: {"template": template})
    with WijjitHarness(app, size=(40, 12)) as h:
        h.tick(frames=1)
        tree = h.app.renderer._last_vnode_tree

        def find(node):
            if node is None:
                return None
            if node.type == "Grid":
                return node.props_dict()
            for child in getattr(node, "children", []) or []:
                found = find(child)
                if found:
                    return found
            return None

        return find(tree) or {}


def test_column_gap_canonical():
    props = _grid_props("{% grid rows=2 cols=2 column_gap=3 row_gap=1 %}{% endgrid %}")
    assert props["column_gap"] == 3
    assert props["row_gap"] == 1
    assert "col_gap" not in props  # the abbreviated prop name is gone


def test_col_gap_alias():
    props = _grid_props("{% grid rows=2 cols=2 col_gap=4 %}{% endgrid %}")
    assert props["column_gap"] == 4


def test_column_gap_default_zero():
    props = _grid_props("{% grid rows=2 cols=2 %}{% endgrid %}")
    assert props["column_gap"] == 0
