"""Theme C: valueless template-tag attributes should warn, not vanish silently.

``parse_tag_attributes`` only understands ``key=value`` attributes. A bare
attribute (e.g. ``{% button disabled %}``) previously caused it to stop parsing
and silently drop that attribute *and every attribute after it*. It now emits a
warning naming the offending attribute so the mistake is discoverable.
"""

from wijjit import Wijjit
from wijjit.testing.harness import WijjitHarness


def _render(template: str) -> None:
    app = Wijjit()
    app.view("main", default=True)(lambda: {"template": template})
    with WijjitHarness(app, size=(60, 20)) as h:
        h.tick(frames=1)


class TestValuelessAttributeWarning:
    def test_valueless_attribute_warns(self, wijjit_caplog):
        _render('{% button id="b" disabled %}X{% endbutton %}')
        msgs = [r.getMessage() for r in wijjit_caplog.records]
        assert any("valueless attribute" in m and "disabled" in m for m in msgs), msgs

    def test_well_formed_attributes_do_not_warn(self, wijjit_caplog):
        _render('{% button id="b" label="ok" %}X{% endbutton %}')
        attr_warnings = [
            r for r in wijjit_caplog.records if "valueless attribute" in r.getMessage()
        ]
        assert not attr_warnings
