"""``{% tree %}`` and ``{% table %}`` take ``"fill"`` sizes, as their tags document.

Both tags passed a ``"fill"`` string through to an element constructor that did
integer arithmetic on it, so ``height="fill"`` crashed the render.
"""

import pytest

from wijjit.testing import WijjitHarness, app_from_template

ROWS = [{"n": i} for i in range(50)]
NODES = {
    "id": "r",
    "label": "Root",
    "children": [{"id": f"c{i}", "label": f"Child {i}"} for i in range(50)],
}

KINDS = {"tree": "Tree", "table": "Table"}

TEMPLATES = {
    "tree": '{% tree id="x" data=state.nodes width="fill" height="fill" %}{% endtree %}',
    "table": '{% table id="x" data=state.rows columns=["n"] width="fill" height="fill" %}{% endtable %}',
}


def _element(h, tag):
    return next(e for e in h.app.positioned_elements if type(e).__name__ == KINDS[tag])


@pytest.mark.parametrize("tag", sorted(TEMPLATES))
def test_fills_the_screen_and_scrolls_the_rest(tag):
    template = (
        f'{{% vstack width="fill" height="fill" %}}{TEMPLATES[tag]}{{% endvstack %}}'
    )
    app = app_from_template(template, state={"rows": ROWS, "nodes": NODES})
    with WijjitHarness(app, size=(50, 16)) as h:
        h.tick(frames=1)
        h.assert_no_errors()
        element = _element(h, tag)
        # Fills the screen (less the one-cell margin the root frame keeps),
        # rather than growing to fit fifty rows.
        assert element.bounds.height >= 12
        assert element.bounds.height <= 16
        assert element.bounds.width >= 40
        lines = h.screen().splitlines()
        assert any(line.strip().startswith(("└", "╰")) for line in lines)


@pytest.mark.parametrize("tag", sorted(TEMPLATES))
def test_follows_a_resize(tag):
    template = (
        f'{{% vstack width="fill" height="fill" %}}{TEMPLATES[tag]}{{% endvstack %}}'
    )
    app = app_from_template(template, state={"rows": ROWS, "nodes": NODES})
    with WijjitHarness(app, size=(50, 16)) as h:
        h.tick(frames=1)
        h.resize(70, 24)
        h.tick(frames=1)
        h.assert_no_errors()
        element = _element(h, tag)
        assert element.bounds.height >= 20
        assert element.bounds.width >= 60
