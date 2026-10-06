"""``{% tree enter_selects=True %}``: Enter selects a node that has children.

By default Enter on a branch only expands or collapses it, so a keyboard user
could not select a branch at all (a click on its label could). An outline that
jumps to sections needs every heading selectable.
"""

from wijjit.testing import WijjitHarness, app_from_template

DATA = {
    "id": "root",
    "label": "Root",
    "children": [
        {"id": "a", "label": "Alpha", "children": [{"id": "a1", "label": "Alpha one"}]},
        {"id": "b", "label": "Beta"},
    ],
}


def _app(extra: str):
    template = f'{{% tree data=state.data on_select="picked" height=10 {extra} %}}{{% endtree %}}'
    picked: list[str] = []
    app = app_from_template(
        template,
        state={"data": DATA},
        actions={"picked": lambda e: picked.append(e.data["id"])},
    )
    return app, picked


def test_default_enter_on_a_branch_toggles_it():
    app, picked = _app("")
    with WijjitHarness(app, size=(40, 12)) as h:
        h.press("tab")
        h.press("enter")  # Root: expand
        h.assert_text("Alpha")
        assert picked == []


def test_enter_selects_a_branch():
    app, picked = _app("enter_selects=True")
    with WijjitHarness(app, size=(40, 12)) as h:
        h.press("tab")
        h.press("enter")
        assert picked == ["root"]
        assert "Alpha" not in h.screen()


def test_space_and_arrows_still_expand_and_collapse():
    app, picked = _app("enter_selects=True")
    with WijjitHarness(app, size=(40, 12)) as h:
        h.press("tab")
        h.press("space")
        h.assert_text("Alpha")
        h.press("down")
        h.press("right")
        h.assert_text("Alpha one")
        h.press("enter")
        assert picked == ["a"]
        h.press("left")
        assert "Alpha one" not in h.screen()


def test_enter_still_selects_a_leaf():
    app, picked = _app("enter_selects=True")
    with WijjitHarness(app, size=(40, 12)) as h:
        h.press("tab")
        h.press("space")
        h.press("down")
        h.press("down")
        h.press("enter")
        assert picked == ["b"]
