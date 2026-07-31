"""Giving a focused element first refusal on the Tab key.

Tab is claimed by the framework's built-in focus navigation, which runs as a
GLOBAL handler at priority 100 and cancels the event -- and a cancelled event
never reaches ``_route_key_to_focused_element``. The consequence was not just
that a ``TextArea`` could not indent: **no element could ever see Tab at all**,
which quietly made ``DataGrid``'s Tab cell navigation and the autocomplete
completer's ``select_on_tab`` unreachable code.

The rule under test: an element whose ``captures_tab`` property is True is
offered plain Tab before focus moves, and focus moves anyway if its
``handle_key`` declines. Shift+Tab is never offered, so backward focus movement
is always available as the way out (and it wraps, so every element stays
reachable even past an element that eats forward Tab).
"""

from __future__ import annotations

from wijjit.autocomplete import WordCompleter
from wijjit.testing import WijjitHarness, app_from_template

FORM = """
{% frame width=44 height=18 %}
  {% vstack padding=1 %}
    {% textarea id="plain" width=30 height=3 %}{% endtextarea %}
    {% textarea id="indent" width=30 height=3 capture_tab=True %}{% endtextarea %}
    {% textinput id="last" width=20 %}{% endtextinput %}
  {% endvstack %}
{% endframe %}
"""

EDITOR = """
{% frame width=44 height=14 %}
  {% vstack padding=1 %}
    {% codeeditor id="code" width=30 height=5 %}{% endcodeeditor %}
    {% textinput id="after" width=20 %}{% endtextinput %}
  {% endvstack %}
{% endframe %}
"""


def focused_id(app):
    """Return the id of the focused element, or None."""
    element = app.focus_manager.get_focused_element()
    return getattr(element, "id", None) if element else None


class TestTabMovesFocusByDefault:
    """The default is unchanged: Tab moves to the next element."""

    def test_plain_textarea_does_not_capture_tab(self):
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)) as h:
            h.press("tab")
            assert focused_id(app) == "plain"
            h.press("tab")
            assert focused_id(app) == "indent"

    def test_plain_textarea_inserts_nothing_on_tab(self):
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)) as h:
            h.press("tab")
            plain = app.get_element_by_id("plain")
            h.press("tab")
            assert plain.value == ""

    def test_captures_tab_property_defaults_false(self):
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)):
            assert app.get_element_by_id("plain").captures_tab is False
            assert app.get_element_by_id("indent").captures_tab is True


class TestCaptureTabInserts:
    """``capture_tab=True`` turns Tab into an indent."""

    def test_tab_inserts_the_indent_and_keeps_focus(self):
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)) as h:
            app.focus_element_by_id("indent")
            h.tick()
            h.type("x")
            h.press("tab")
            assert app.get_element_by_id("indent").value == "x    "
            assert focused_id(app) == "indent"

    def test_tab_width_is_honored(self):
        app = app_from_template(
            '{% textarea id="ta" width=30 height=3 capture_tab=True tab_width=2 %}'
            "{% endtextarea %}"
        )
        with WijjitHarness(app, size=(50, 12)) as h:
            app.focus_element_by_id("ta")
            h.tick()
            h.press("tab")
            h.type("x")
            assert app.get_element_by_id("ta").value == "  x"

    def test_tab_replaces_a_selection(self):
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)) as h:
            app.focus_element_by_id("indent")
            h.tick()
            h.type("abc")
            # The harness has no shift+arrow keys, so anchor the selection
            # directly: "abc" selected, cursor at the end.
            field = app.get_element_by_id("indent")
            field.selection_anchor = (0, 0)
            assert field._has_selection()
            h.press("tab")
            assert field.value == "    "

    def test_tab_insert_is_one_undo_unit(self):
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)) as h:
            app.focus_element_by_id("indent")
            h.tick()
            h.type("x")
            h.press("tab")
            assert app.get_element_by_id("indent").value == "x    "
            h.press("ctrl+z")
            assert app.get_element_by_id("indent").value == "x"


class TestShiftTabAlwaysEscapes:
    """Shift+Tab is never captured, so there is always a way out."""

    def test_shift_tab_leaves_a_capturing_element(self):
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)) as h:
            app.focus_element_by_id("indent")
            h.tick()
            h.press("shift+tab")
            assert focused_id(app) == "plain"

    def test_backward_cycle_wraps_so_nothing_is_stranded(self):
        # Tab cannot move forward past a capturing element, so the guarantee
        # that every element stays reachable rests on the backward wrap.
        app = app_from_template(FORM)
        with WijjitHarness(app, size=(60, 24)) as h:
            h.press("tab")
            assert focused_id(app) == "plain"
            h.press("shift+tab")
            assert focused_id(app) == "last"


class TestCodeEditorDefaultsToCapturing:
    """Unlike TextArea, a code editor indents on Tab out of the box."""

    def test_editor_indents_without_being_asked(self):
        app = app_from_template(EDITOR)
        with WijjitHarness(app, size=(60, 20)) as h:
            app.focus_element_by_id("code")
            h.tick()
            h.type("def f():")
            h.press("enter")
            h.press("tab")
            h.type("return 1")
            assert app.get_element_by_id("code").value == "def f():\n    return 1"
            assert focused_id(app) == "code"

    def test_editor_can_opt_out(self):
        app = app_from_template(
            "{% vstack %}"
            '{% codeeditor id="c" width=30 height=4 capture_tab=False %}'
            "{% endcodeeditor %}"
            '{% textinput id="after" width=10 %}{% endtextinput %}'
            "{% endvstack %}"
        )
        with WijjitHarness(app, size=(50, 14)) as h:
            app.focus_element_by_id("c")
            h.tick()
            h.press("tab")
            assert app.get_element_by_id("c").value == ""
            assert focused_id(app) == "after"


class TestAutocompleteSelectOnTab:
    """The completer's ``select_on_tab`` was unreachable; now it fires.

    ``captures_tab`` is a property rather than a flag precisely for this: a
    text input in a form must keep Tab-to-next-field, so it claims Tab only
    while its suggestion popup is open.
    """

    @staticmethod
    def _app():
        app = app_from_template(
            "{% vstack %}"
            '{% textinput id="lang" width=30 autocomplete=True %}{% endtextinput %}'
            '{% textinput id="other" width=30 %}{% endtextinput %}'
            "{% endvstack %}"
        )
        app.completers["lang"] = WordCompleter(
            ["python", "pytorch", "pandas"], trigger="auto", min_chars=2
        )
        return app

    def test_tab_accepts_the_highlighted_suggestion(self):
        app = self._app()
        with WijjitHarness(app, size=(60, 14)) as h:
            h.press("tab")
            field = app.get_element_by_id("lang")
            h.type("py")
            assert field._autocomplete_state.is_open
            assert field.captures_tab is True

            h.press("tab")
            assert field.value == "python"
            assert field._autocomplete_state.is_open is False
            assert focused_id(app) == "lang"

    def test_tab_moves_focus_once_the_popup_closes(self):
        app = self._app()
        with WijjitHarness(app, size=(60, 14)) as h:
            h.press("tab")
            field = app.get_element_by_id("lang")
            h.type("py")
            h.press("tab")  # accept
            assert field.captures_tab is False
            h.press("tab")  # now an ordinary focus move
            assert focused_id(app) == "other"

    def test_a_plain_input_never_claims_tab(self):
        app = self._app()
        with WijjitHarness(app, size=(60, 14)) as h:
            h.press("tab")
            h.press("tab")
            assert focused_id(app) == "other"
            assert app.get_element_by_id("other").captures_tab is False


class TestCaptureIsOptIn:
    """Returning True from handle_key is not enough on its own.

    ``DataGrid`` handles Tab and returns True unconditionally, including at
    the last cell. Routing on "did handle_key return True" alone would have
    made every grid a focus trap, so the seam requires an explicit opt-in.
    """

    def test_datagrid_still_tabs_out(self):
        app = app_from_template(
            "{% vstack %}"
            '{% datagrid id="grid" columns=["A", "B"] data=[[1, 2], [3, 4]] '
            "width=30 height=6 %}{% enddatagrid %}"
            '{% textinput id="after" width=10 %}{% endtextinput %}'
            "{% endvstack %}"
        )
        with WijjitHarness(app, size=(50, 16)) as h:
            app.focus_element_by_id("grid")
            h.tick()
            assert app.get_element_by_id("grid").captures_tab is False
            h.press("tab")
            assert focused_id(app) == "after"
