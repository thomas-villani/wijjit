"""Undo/redo driven through a real app and event loop (review 2.10).

The unit tests in ``tests/elements/test_textarea.py`` call ``handle_key``
directly. These drive the harness, so the keys go through real event dispatch
and - crucially - a real render happens between keystrokes. That render is what
re-applies ``value`` from props onto the element, which is the one thing that
could silently empty the undo stack.
"""

from wijjit import Wijjit, render_template_string
from wijjit.testing import WijjitHarness

BOUND_TEMPLATE = """{% vstack %}
{% textarea id="notes" width=30 height=4 %}{% endtextarea %}
{% text %}state={{ state.notes }}{% endtext %}
{% endvstack %}"""


def _bound_app():
    app = Wijjit()
    app.state["notes"] = ""

    @app.view("main", default=True)
    def main():
        return render_template_string(BOUND_TEMPLATE)

    return app


class TestUndoThroughTheEventLoop:
    """Undo survives the render that happens between keystrokes."""

    def test_undo_survives_the_bound_prop_round_trip(self):
        """Undo survives a bound TextArea's own value round-trip.

        A bound TextArea round-trips: type -> the wiring writes
        ``state["notes"]`` -> the next render re-applies ``value`` from props
        (it is not an ephemeral prop). If that re-application reached
        ``set_value``, it would clear undo history and the stack would be empty
        by the time the user pressed Ctrl+Z.

        It does not, because the ``value`` *setter* already skips ``set_value``
        on an unchanged text - a guard that predates undo and exists to protect
        cursor/scroll from this same round-trip. This test pins that the two
        interact correctly, so that removing or weakening either one is caught
        here rather than by a user losing their undo stack on every keystroke.
        """
        app = _bound_app()

        with WijjitHarness(app, size=(46, 10)) as h:
            h.press("tab")
            h.type("hello")
            h.tick(frames=2)  # renders, and re-applies value from props
            assert app.state["notes"] == "hello"

            h.press("ctrl+z")
            h.tick(frames=2)

            assert app.state["notes"] == "", "undo history was wiped by prop sync"
            h.assert_no_errors()

    def test_redo_through_the_loop(self):
        app = _bound_app()

        with WijjitHarness(app, size=(46, 10)) as h:
            h.press("tab")
            h.type("hello")
            h.tick(frames=2)

            h.press("ctrl+z")
            h.tick(frames=2)
            assert app.state["notes"] == ""

            h.press("ctrl+y")
            h.tick(frames=2)

            assert app.state["notes"] == "hello"
            h.assert_no_errors()

    def test_undo_repaints_the_screen(self):
        """Undo must reach the screen, not just the element's value."""
        app = _bound_app()

        with WijjitHarness(app, size=(46, 10)) as h:
            h.press("tab")
            h.type("hello")
            h.tick(frames=2)
            h.assert_text("hello")

            h.press("ctrl+z")
            h.tick(frames=2)

            assert "hello" not in h.screen()
            h.assert_no_errors()

    def test_select_all_then_type_is_recoverable_in_a_live_app(self):
        """The review's headline case, through real dispatch."""
        app = _bound_app()
        app.state["notes"] = "important notes"

        with WijjitHarness(app, size=(46, 10)) as h:
            h.press("tab")
            h.press("ctrl+a")
            h.type("x")
            h.tick(frames=2)
            assert app.state["notes"] == "x"

            h.press("ctrl+z")
            h.tick(frames=2)

            assert app.state["notes"] == "important notes"
            h.assert_no_errors()
