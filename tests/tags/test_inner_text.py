"""Inner-text discipline: tags accept both a label/value attribute and a body.

Buttons, menu items, checkboxes and radios use the body as the label when no
``label`` attribute is given (attribute wins). Text inputs use the body as the
initial value when no ``value`` attribute is given.
"""

from wijjit import Wijjit
from wijjit.testing.harness import WijjitHarness


def _first(app, class_name):
    return next(
        el for el in app.positioned_elements if el.__class__.__name__ == class_name
    )


def _run(template):
    app = Wijjit()
    app.view("main", default=True)(lambda: {"template": template})
    with WijjitHarness(app, size=(60, 16)) as h:
        h.tick(frames=1)
        return app


class TestButtonInnerText:
    def test_body_is_label(self):
        app = _run('{% button id="b" %}Cancel{% endbutton %}')
        assert _first(app, "Button").label == "Cancel"

    def test_label_attr_used(self):
        app = _run('{% button id="b" label="Save" %}{% endbutton %}')
        assert _first(app, "Button").label == "Save"

    def test_label_attr_overrides_body(self):
        app = _run('{% button id="b" label="Attr" %}Body{% endbutton %}')
        assert _first(app, "Button").label == "Attr"


class TestTextInputInnerText:
    def test_body_is_initial_value(self):
        app = _run('{% textinput id="t" %}hello{% endtextinput %}')
        assert _first(app, "TextInput").value == "hello"

    def test_value_attr_overrides_body(self):
        app = _run('{% textinput id="t" value="attr" %}body{% endtextinput %}')
        assert _first(app, "TextInput").value == "attr"

    def test_empty_body_is_empty_value(self):
        app = _run('{% textinput id="t" %}{% endtextinput %}')
        assert _first(app, "TextInput").value == ""


class TestMenuItemInnerText:
    TEMPLATE = """
    {% frame width="60" height="16" %}
        {% dropdown trigger="File" visible="show" %}
            {% menuitem action="a" %}From Body{% endmenuitem %}
            {% menuitem action="b" label="From Attr" %}{% endmenuitem %}
            {% menuitem action="c" label="Attr Wins" %}Ignored{% endmenuitem %}
        {% enddropdown %}
    {% endframe %}
    """

    def test_menuitem_labels(self):
        app = Wijjit()
        app.state.show = True
        app.view("main", default=True)(lambda: {"template": self.TEMPLATE})
        with WijjitHarness(app, size=(60, 16)) as h:
            h.tick(frames=1)
            menu = app.overlay_manager.overlays[0].element
            labels = [item.label for item in menu.items]
        assert labels == ["From Body", "From Attr", "Attr Wins"]
