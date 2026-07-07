"""Tests proving the wijjit pytest plugin auto-loads (entry point wired)."""

import pytest

TEMPLATE = '{% frame title="Plugin" width=30 height=4 %}hello plugin{% endframe %}'


# These use the shipped, ``wijjit_``-prefixed fixture names directly (not the
# in-repo conftest aliases), so they prove the plugin's entry point is wired.
def test_wijjit_harness_fixture_is_available(wijjit_harness):
    h = wijjit_harness(TEMPLATE, size=(40, 6))
    h.assert_text("hello plugin")
    h.assert_no_errors()


def test_wijjit_make_app_fixture_builds_app(wijjit_make_app):
    app = wijjit_make_app(TEMPLATE, state={"x": 1})
    assert app.state["x"] == 1


@pytest.mark.wijjit_app
def test_wijjit_app_marker_is_registered(wijjit_harness):
    # If the marker were unregistered, --strict-markers (pytest.ini) would error.
    h = wijjit_harness(TEMPLATE)
    h.assert_text("hello plugin")
