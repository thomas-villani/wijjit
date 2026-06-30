"""Tests for app_from_template and the new harness assertions."""

from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = """
{% frame title="Form" width=40 height=8 %}
  {% vstack spacing=1 %}
    {% textinput id="name" placeholder="name" width=20 %}{% endtextinput %}
    {% button id="ok" action="go" %}Go{% endbutton %}
  {% endvstack %}
{% endframe %}
"""


def test_app_from_template_drives_through_harness():
    def go(event=None):
        app.state["clicked"] = True

    app = app_from_template(TEMPLATE, state={"clicked": False}, actions={"go": go})
    with WijjitHarness(app, size=(50, 12)) as h:
        h.press("tab")  # focus input
        h.type("Bob")
        h.press("tab")  # focus button
        h.press("enter")  # fire action
        h.assert_no_errors()
        assert h.state["name"] == "Bob"
        assert h.state["clicked"] is True


def test_assert_tree_contains_matches_type_and_key():
    app = app_from_template(TEMPLATE, state={})
    with WijjitHarness(app, size=(50, 12)) as h:
        h.assert_tree_contains(type="Button", key="ok")
        h.assert_tree_contains(type="TextInput")


def test_assert_tree_contains_raises_when_missing():
    app = app_from_template(TEMPLATE, state={})
    with WijjitHarness(app, size=(50, 12)) as h:
        try:
            h.assert_tree_contains(type="Table")
        except AssertionError as exc:
            assert "Table" in str(exc)
        else:
            raise AssertionError("expected AssertionError for missing Table")


def test_assert_no_errors_detects_handler_failure():
    def boom(event=None):
        raise RuntimeError("kaboom")

    app = app_from_template(TEMPLATE, state={}, actions={"go": boom})
    with WijjitHarness(app, size=(50, 12)) as h:
        h.press("tab")
        h.press("tab")
        h.press("enter")  # triggers boom
        try:
            h.assert_no_errors()
        except AssertionError as exc:
            assert "kaboom" in str(exc)
        else:
            raise AssertionError("expected assert_no_errors to fail")


def test_extra_named_views_register():
    app = app_from_template(
        "{% frame width=20 height=3 %}main{% endframe %}",
        views={"other": "{% frame width=20 height=3 %}other{% endframe %}"},
    )
    assert "main" in app.views
    assert "other" in app.views
