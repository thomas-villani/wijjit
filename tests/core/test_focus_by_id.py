"""Tests for app-level focus-by-id and bind-keys-to-focus helpers."""

from wijjit import Wijjit
from wijjit.testing.harness import WijjitHarness

TEMPLATE = """
{% vstack %}
  {% textinput id="first" %}{% endtextinput %}
  {% textinput id="second" %}{% endtextinput %}
  {% textinput id="third" %}{% endtextinput %}
{% endvstack %}
"""


def _app():
    app = Wijjit()
    app.view("main", default=True)(lambda: {"template": TEMPLATE})
    return app


class TestGetElementById:
    def test_returns_element(self):
        with WijjitHarness(_app(), size=(40, 12)) as h:
            h.tick(frames=1)
            elem = h.app.get_element_by_id("second")
            assert elem is not None
            assert elem.id == "second"

    def test_unknown_id_returns_none(self):
        with WijjitHarness(_app(), size=(40, 12)) as h:
            h.tick(frames=1)
            assert h.app.get_element_by_id("nope") is None


class TestFocusElementById:
    def test_focuses_named_element(self):
        with WijjitHarness(_app(), size=(40, 12)) as h:
            h.tick(frames=1)
            assert h.app.focus_element_by_id("third") is True
            focused = h.app.focus_manager.get_focused_element()
            assert focused is not None and focused.id == "third"

    def test_unknown_id_returns_false(self):
        with WijjitHarness(_app(), size=(40, 12)) as h:
            h.tick(frames=1)
            assert h.app.focus_element_by_id("missing") is False


class TestBindFocusKey:
    def test_key_moves_focus(self):
        app = _app()
        app.bind_focus_key("ctrl+l", "second")
        with WijjitHarness(app, size=(40, 12)) as h:
            h.tick(frames=1)
            h.press("ctrl+l")
            h.tick(frames=1)
            focused = app.focus_manager.get_focused_element()
            assert focused is not None and focused.id == "second"

    def test_ctrl_q_still_reserved(self):
        app = _app()
        try:
            app.bind_focus_key("ctrl+q", "second")
        except ValueError:
            return  # expected: Ctrl+Q is reserved
        raise AssertionError("binding ctrl+q should raise ValueError")
