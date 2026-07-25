"""A focused text input must swallow plain characters, not fire hotkeys.

Single-character hotkeys are the norm in these apps (``q`` to quit, ``s`` to
save), and they used to fire while the user was typing into a text field - so
typing a name containing "q" quit the app. View-scoped handlers were already
suppressed for this reason; global ones were deliberately not, which is the gap
this covers.

Modified and special keys stay unambiguous and must keep working while typing,
otherwise Ctrl+S-style shortcuts would die inside every form.
"""

from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = """
{% frame title="Form" width=40 height=8 %}
  {% textinput id="name" width=20 %}{% endtextinput %}
{% endframe %}
"""


def _app_with_hotkeys():
    """Build an app whose global hotkeys record every firing."""
    fired: list[str] = []
    app = app_from_template(TEMPLATE)

    @app.on_key("q")
    def _quit(event):
        fired.append("q")

    @app.on_key("s")
    def _save(event):
        fired.append("s")

    @app.on_key("ctrl+s")
    def _ctrl_save(event):
        fired.append("ctrl+s")

    @app.on_key("escape")
    def _cancel(event):
        fired.append("escape")

    return app, fired


def test_plain_characters_do_not_fire_global_hotkeys_while_typing():
    app, fired = _app_with_hotkeys()
    with WijjitHarness(app, size=(60, 12)) as h:
        h.tick()
        assert app.focus_element_by_id("name")
        h.type("quincy sq")
        h.tick()

        assert fired == []
        assert app.get_element_by_id("name").value == "quincy sq"


def test_modified_keys_still_fire_while_typing():
    app, fired = _app_with_hotkeys()
    with WijjitHarness(app, size=(60, 12)) as h:
        h.tick()
        assert app.focus_element_by_id("name")
        h.press("ctrl+s")
        h.tick()

        assert "ctrl+s" in fired


def test_special_keys_still_fire_while_typing():
    app, fired = _app_with_hotkeys()
    with WijjitHarness(app, size=(60, 12)) as h:
        h.tick()
        assert app.focus_element_by_id("name")
        h.press("escape")
        h.tick()

        assert "escape" in fired


def test_hotkeys_fire_when_no_input_is_focused():
    app, fired = _app_with_hotkeys()
    with WijjitHarness(app, size=(60, 12)) as h:
        h.tick()
        app.focus_manager.clear()
        h.press("q")
        h.tick()

        assert "q" in fired
