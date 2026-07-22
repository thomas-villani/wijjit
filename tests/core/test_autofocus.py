"""Declarative initial focus via ``autofocus=True``.

Before this existed, a freshly launched Wijjit app had nothing focused: you
typed and nothing happened until you pressed Tab. That is defensible as a
default -- focusing element 0 unconditionally makes the first Tab appear to
skip an element -- but it left no way to say "put the cursor here," which is
exactly what a form wants.

The rule under test: an element with ``autofocus`` takes focus whenever focus
would otherwise be unset. It never steals focus from an element that already
has it.
"""

from __future__ import annotations

from wijjit.testing import WijjitHarness, app_from_template

FORM = """
{% frame width=40 height=9 %}
  {% vstack padding=1 %}
    {% textinput id="first" width=20 %}{% endtextinput %}
    {% textinput id="second" width=20 autofocus=True %}{% endtextinput %}
    {% button id="go" action="go" %}Go{% endbutton %}
  {% endvstack %}
{% endframe %}
"""

NO_AUTOFOCUS = """
{% frame width=40 height=9 %}
  {% vstack padding=1 %}
    {% textinput id="first" width=20 %}{% endtextinput %}
    {% button id="go" action="go" %}Go{% endbutton %}
  {% endvstack %}
{% endframe %}
"""


def focused_id(app):
    """Return the id of the focused element, or None."""
    element = app.focus_manager.get_focused_element()
    return getattr(element, "id", None)


def test_autofocus_element_holds_focus_on_first_render():
    app = app_from_template(FORM, state={"first": "", "second": ""})
    with WijjitHarness(app, size=(44, 12)):
        assert focused_id(app) == "second"


def test_typing_works_with_no_tab_first():
    """The point of the feature: keystrokes land without a Tab."""
    app = app_from_template(FORM, state={"first": "", "second": ""})
    with WijjitHarness(app, size=(44, 12)) as harness:
        harness.type("hello")
        assert app.state["second"] == "hello"
        assert app.state["first"] == ""


def test_without_autofocus_nothing_is_focused():
    """The default is unchanged -- this is opt-in, not a new global behaviour."""
    app = app_from_template(NO_AUTOFOCUS, state={"first": ""})
    with WijjitHarness(app, size=(44, 12)) as harness:
        assert focused_id(app) is None
        harness.press("tab")
        assert focused_id(app) == "first"


def test_autofocus_does_not_steal_focus_from_the_user():
    """Once the user has moved focus, re-renders must not yank it back."""
    app = app_from_template(FORM, state={"first": "", "second": ""})
    with WijjitHarness(app, size=(44, 12)) as harness:
        harness.press("tab")
        moved_to = focused_id(app)
        assert moved_to != "second"

        # Force several more renders; focus must stay where the user put it.
        app.needs_render = True
        harness.tick(frames=3)
        assert focused_id(app) == moved_to


def test_tab_order_is_unaffected_by_autofocus():
    """autofocus picks a starting point; it does not reorder anything."""
    app = app_from_template(FORM, state={"first": "", "second": ""})
    with WijjitHarness(app, size=(44, 12)) as harness:
        assert focused_id(app) == "second"
        harness.press("tab")
        assert focused_id(app) == "go"
        harness.press("tab")
        assert focused_id(app) == "first"


def test_tabindex_minus_one_excludes_an_element_from_autofocus():
    """A non-tab-navigable element cannot claim autofocus."""
    template = """
{% frame width=40 height=9 %}
  {% vstack padding=1 %}
    {% textinput id="skipped" width=20 autofocus=True tabindex=-1 %}
    {% endtextinput %}
    {% button id="go" action="go" %}Go{% endbutton %}
  {% endvstack %}
{% endframe %}
"""
    app = app_from_template(template, state={"skipped": ""})
    with WijjitHarness(app, size=(44, 12)):
        assert focused_id(app) is None


def test_multiple_autofocus_picks_the_first_and_warns(wijjit_caplog):
    template = """
{% frame width=40 height=9 %}
  {% vstack padding=1 %}
    {% textinput id="one" width=20 autofocus=True %}{% endtextinput %}
    {% textinput id="two" width=20 autofocus=True %}{% endtextinput %}
  {% endvstack %}
{% endframe %}
"""
    app = app_from_template(template, state={"one": "", "two": ""})
    with WijjitHarness(app, size=(44, 12)):
        assert focused_id(app) == "one"

    messages = [r.getMessage() for r in wijjit_caplog.records]
    assert any("Multiple elements request autofocus" in m for m in messages)


def test_autofocus_is_not_reported_as_an_unknown_attribute():
    """The validator must know the attribute, or the linter contradicts the docs."""
    from wijjit.devtools import validate_template

    report = validate_template(FORM, context={"state": {"first": "", "second": ""}})
    assert not [f for f in report.findings if f.code == "unknown-attribute"]


def test_autofocus_survives_a_reconciler_update():
    """The prop is applied on create; an update must not silently drop it."""
    app = app_from_template(FORM, state={"first": "", "second": ""})
    with WijjitHarness(app, size=(44, 12)) as harness:
        element = app.get_element_by_id("second")
        assert element.autofocus is True

        app.needs_render = True
        harness.tick(frames=2)
        assert app.get_element_by_id("second").autofocus is True
