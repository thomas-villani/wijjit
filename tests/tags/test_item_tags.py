"""Nested item tags: {% selectitem %} and {% treeitem %}.

Select and Tree items can be declared via nested child tags, mirroring the
existing {% menuitem %} pattern, in addition to the options=/data= attributes.
"""

from wijjit import Wijjit
from wijjit.testing.harness import WijjitHarness


def _first(app, class_name):
    return next(
        el for el in app.positioned_elements if el.__class__.__name__ == class_name
    )


def _run(template, size=(60, 20), **state):
    app = Wijjit()
    for k, v in state.items():
        app.state[k] = v
    app.view("main", default=True)(lambda: {"template": template})
    with WijjitHarness(app, size=size) as h:
        h.tick(frames=1)
    return app


class TestSelectItem:
    def test_items_become_options(self):
        app = _run(
            '{% select id="s" %}'
            '{% selectitem value="a" %}Apple{% endselectitem %}'
            '{% selectitem value="b" label="Banana" %}{% endselectitem %}'
            "{% endselect %}"
        )
        select = _first(app, "Select")
        labels = [o["label"] for o in select.options]
        values = [o["value"] for o in select.options]
        assert labels == ["Apple", "Banana"]
        assert values == ["a", "b"]

    def test_value_defaults_to_label(self):
        app = _run(
            '{% select id="s" %}'
            "{% selectitem %}Solo{% endselectitem %}"
            "{% endselect %}"
        )
        select = _first(app, "Select")
        assert select.options[0]["value"] == "Solo"

    def test_disabled_item(self):
        app = _run(
            '{% select id="s" %}'
            '{% selectitem value="x" disabled=True %}Nope{% endselectitem %}'
            "{% endselect %}"
        )
        select = _first(app, "Select")
        # The disabled flag flows through to the element's disabled_values set.
        assert "x" in select.disabled_values

    def test_options_attr_takes_precedence(self):
        app = _run(
            '{% select id="s" options=["Z"] %}'
            "{% selectitem %}Ignored{% endselectitem %}"
            "{% endselect %}"
        )
        select = _first(app, "Select")
        labels = [o["label"] for o in select.options]
        assert labels == ["Z"]


class TestTreeItem:
    def test_flat_items(self):
        app = _run(
            '{% tree id="t" show_root=False %}'
            "{% treeitem %}One{% endtreeitem %}"
            "{% treeitem %}Two{% endtreeitem %}"
            "{% endtree %}"
        )
        tree = _first(app, "Tree")
        roots = tree.data["children"]
        assert [n["label"] for n in roots] == ["One", "Two"]

    def test_nested_items(self):
        app = _run(
            '{% tree id="t" %}'
            '{% treeitem label="src" %}'
            "{% treeitem %}app.py{% endtreeitem %}"
            "{% treeitem %}cli.py{% endtreeitem %}"
            "{% endtreeitem %}"
            "{% endtree %}"
        )
        tree = _first(app, "Tree")
        # Single top-level item becomes the root node.
        assert tree.data["label"] == "src"
        children = [c["label"] for c in tree.data["children"]]
        assert children == ["app.py", "cli.py"]

    def test_data_attr_takes_precedence(self):
        app = _run(
            '{% tree id="t" data={"label": "FromData", "children": []} %}'
            "{% treeitem %}Ignored{% endtreeitem %}"
            "{% endtree %}",
        )
        tree = _first(app, "Tree")
        assert tree.data["label"] == "FromData"
