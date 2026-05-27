"""Tests for the headless WijjitHarness."""

import pytest

from wijjit import Wijjit
from wijjit.elements.input.button import Button
from wijjit.testing import ScriptedInputHandler, WijjitHarness

TEMPLATE = """
{% frame title="Harness" border="single" width=40 height=12 %}
  {% vstack spacing=1 %}
    {{ state.status }}
    {% textinput id="name" placeholder="name" width=20 %}{% endtextinput %}
    {% button action="greet" %}Greet{% endbutton %}
  {% endvstack %}
{% endframe %}
"""


def make_app() -> Wijjit:
    """Build a small app: status line, text input bound to ``name``, button."""
    app = Wijjit(initial_state={"name": "", "status": "ready"})

    @app.view("main", default=True)
    def main_view():
        return {"template": TEMPLATE}

    @app.on_action("greet")
    def greet(event=None):
        app.state["status"] = "Hello " + (app.state.get("name") or "world")

    return app


def test_initial_render_shows_view():
    with WijjitHarness(make_app(), size=(50, 16)) as h:
        h.assert_text("Harness")  # frame title
        h.assert_text("ready")  # initial status


def test_type_into_focused_input():
    with WijjitHarness(make_app(), size=(50, 16)) as h:
        h.press("tab")  # focus first focusable (the text input)
        h.type("Bob")
        h.assert_text("Bob")


def test_button_action_via_keyboard():
    with WijjitHarness(make_app(), size=(50, 16)) as h:
        h.press("tab")  # input
        h.type("Bob")
        h.press("tab")  # button
        h.press("enter")  # activate "greet"
        h.assert_text("Hello")


def test_button_action_via_mouse_click():
    app = make_app()
    with WijjitHarness(app, size=(50, 16)) as h:
        button = next(e for e in app.positioned_elements if isinstance(e, Button))
        assert button.bounds is not None
        h.click(button.bounds.x + 1, button.bounds.y)
        h.assert_text("Hello")


def test_quit_key_stops_loop():
    with WijjitHarness(make_app(), size=(50, 16)) as h:
        assert h.running is True
        h.press("ctrl+q")
        assert h.running is False


def test_screen_ansi_includes_styling_codes():
    with WijjitHarness(make_app(), size=(50, 16)) as h:
        ansi = h.screen_ansi()
        assert "\x1b[" in ansi  # contains ANSI escape sequences
        assert "Harness" in h.screen()  # plain-text view still has no codes


def test_scripted_input_handler_queue():
    handler = ScriptedInputHandler()
    assert handler.empty() is True


@pytest.mark.asyncio
async def test_read_input_async_returns_none_when_empty():
    handler = ScriptedInputHandler()
    assert await handler.read_input_async(timeout=0.0) is None
