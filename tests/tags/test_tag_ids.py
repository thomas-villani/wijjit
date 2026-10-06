"""Every display tag hands its ``id`` to the element it builds.

Six tags keyed the VNode by ``id`` but never set it as a prop, so the element
was built with ``id=None``: ``get_element_by_id`` and ``focus_element_by_id``
could not find it, and the element's ``{id}:{property}`` state keys were off.
"""

import pytest

from wijjit.testing import WijjitHarness, app_from_template

TAGS = {
    "table": '{% table id="X" data=[{"a": 1}] %}{% endtable %}',
    "tree": '{% tree id="X" data={"label": "r", "value": "r"} %}{% endtree %}',
    "progressbar": '{% progressbar id="X" value=3 max=10 %}{% endprogressbar %}',
    "spinner": '{% spinner id="X" active=True %}{% endspinner %}',
    "link": '{% link id="X" action="go" %}Go{% endlink %}',
}


@pytest.mark.parametrize("tag", sorted(TAGS))
def test_element_keeps_its_id(tag):
    with WijjitHarness(app_from_template(TAGS[tag]), size=(60, 20)) as h:
        h.tick(frames=1)
        h.assert_no_errors()
        element = h.app.get_element_by_id("X")
        assert element is not None
        assert element.id == "X"


def test_tree_can_be_focused_by_id():
    template = '{% tree id="X" data={"label": "r", "value": "r"} %}{% endtree %}'
    with WijjitHarness(app_from_template(template), size=(60, 20)) as h:
        h.tick(frames=1)
        assert h.app.focus_element_by_id("X") is True


def test_modal_element_keeps_its_id():
    template = '{% modal id="X" visible=True title="T" %}Hi{% endmodal %}'
    with WijjitHarness(app_from_template(template), size=(60, 20)) as h:
        h.tick(frames=1)
        h.assert_no_errors()
        modals = [
            e for e in h.app.positioned_elements if type(e).__name__ == "ModalElement"
        ]
        assert [m.id for m in modals] == ["X"]
