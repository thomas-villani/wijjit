"""Tests proving the wijjit pytest plugin auto-loads (entry point wired)."""

import pytest

TEMPLATE = '{% frame title="Plugin" width=30 height=4 %}hello plugin{% endframe %}'


def test_harness_fixture_is_available(harness):
    h = harness(TEMPLATE, size=(40, 6))
    h.assert_text("hello plugin")
    h.assert_no_errors()


def test_make_app_fixture_builds_app(make_app):
    app = make_app(TEMPLATE, state={"x": 1})
    assert app.state["x"] == 1


@pytest.mark.wijjit_app
def test_wijjit_app_marker_is_registered(harness):
    # If the marker were unregistered, --strict-markers (pytest.ini) would error.
    h = harness(TEMPLATE)
    h.assert_text("hello plugin")
