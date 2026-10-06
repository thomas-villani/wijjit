"""``{% tree expanded=... %}`` sets which nodes start open, or binds them to state.

The tag documented both forms, but after the move to the virtual DOM the prop
reached no element parameter, so the registry dropped it and every tree started
collapsed.
"""

from wijjit.testing import WijjitHarness, app_from_template

DATA = {
    "id": "root",
    "label": "Root",
    "children": [
        {"id": "a", "label": "Alpha", "children": [{"id": "a1", "label": "Alpha one"}]},
        {"id": "b", "label": "Beta", "children": [{"id": "b1", "label": "Beta one"}]},
    ],
}


def _tree(h):
    return next(e for e in h.app.positioned_elements if type(e).__name__ == "Tree")


def test_a_list_opens_those_nodes_at_start():
    template = (
        '{% tree data=state.data expanded=["root", "a"] height=10 %}{% endtree %}'
    )
    app = app_from_template(template, state={"data": DATA})
    with WijjitHarness(app, size=(40, 12)) as h:
        h.tick(frames=1)
        h.assert_no_errors()
        h.assert_text("Alpha one")
        assert "Beta one" not in h.screen()


def test_a_list_only_seeds_the_tree():
    template = (
        '{% tree id="t" data=state.data expanded=["root"] height=10 %}{% endtree %}'
    )
    app = app_from_template(template, state={"data": DATA})
    with WijjitHarness(app, size=(40, 12)) as h:
        h.tick(frames=1)
        _tree(h).expand_node("b")
        h.app.state["touch"] = 1
        h.tick(frames=1)
        h.assert_text("Beta one")


def test_a_string_binds_expansion_to_state():
    template = '{% tree data=state.data expanded="open" height=10 %}{% endtree %}'
    app = app_from_template(template, state={"data": DATA, "open": ["root", "b"]})
    with WijjitHarness(app, size=(40, 12)) as h:
        h.tick(frames=1)
        h.assert_text("Beta one")
        assert "Alpha one" not in h.screen()

        h.app.state["open"] = ["root", "a"]
        h.tick(frames=1)
        h.assert_text("Alpha one")
        assert "Beta one" not in h.screen()

        _tree(h).collapse_node("a")
        assert sorted(h.app.state["open"]) == ["root"]
