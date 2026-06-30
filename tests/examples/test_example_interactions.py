"""Interaction regression tests for previously-broken example demos.

Each test drives a real demo through :class:`~wijjit.testing.WijjitHarness`,
reproducing the interaction that used to crash, hang, or corrupt the screen,
and asserts the fixed behaviour. See ``etc/issues.md`` for the original reports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wijjit.elements.input import Button, TextInput
from wijjit.testing import WijjitHarness, load_example_app

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _load(rel_path: str):
    return load_example_app(EXAMPLES_DIR / rel_path)


def _button(app, label_substr: str) -> Button:
    return next(
        b
        for b in app.positioned_elements
        if isinstance(b, Button) and label_substr in (b.label or "")
    )


def _click_button(harness: WijjitHarness, label_substr: str) -> None:
    btn = _button(harness.app, label_substr)
    assert btn.bounds is not None, f"button {label_substr!r} has no bounds"
    harness.click(btn.bounds.x + 1, btn.bounds.y)


def test_executor_demo_runs_sync_handler_in_executor():
    """executor_demo loaded (no app.configure crash) and runs a task."""
    app = _load("advanced/executor_demo.py")
    assert app.event_loop.executor is not None  # configured via constructor
    with WijjitHarness(app, size=(100, 36)) as h:
        _click_button(h, "Quick Task")
        assert app.state["operation_count"] == 1
        h.assert_text("complete")


def test_state_management_increment_does_not_hang():
    """state_management_demo increments without re-entrant on_change recursion."""
    app = _load("advanced/state_management_demo.py")
    with WijjitHarness(app, size=(100, 40)) as h:
        for _ in range(3):
            _click_button(h, "Increment")
        assert app.state["counter"] == 3
        assert app.state["counter_squared"] == 9
        h.assert_text("Counter: 3")


def test_form_demo_register_shows_errors_not_placeholders():
    """form_demo register surfaces validation errors, not [Missing element]."""
    app = _load("advanced/form_demo.py")
    with WijjitHarness(app, size=(90, 38)) as h:
        _click_button(h, "Register")
        screen = h.screen()
        assert "[Missing element" not in screen
        assert "Name is required" in screen
        assert "Email is required" in screen


def test_error_handling_demo_json_error_shows_message_not_placeholders():
    """error_handling_demo JSON error renders cleanly after the reconciler fix."""
    app = _load("advanced/error_handling_demo.py")
    with WijjitHarness(app, size=(100, 40)) as h:
        json_field = next(
            e
            for e in app.positioned_elements
            if isinstance(e, TextInput) and e.id == "json_input"
        )
        h.click(json_field.bounds.x + 1, json_field.bounds.y)
        h.type("garbage{{{")
        _click_button(h, "Parse JSON")
        screen = h.screen()
        assert "[Missing element" not in screen
        assert "Result: Error" in screen


def test_radio_demo_submit_does_not_crash_on_directional_padding():
    """radio_demo submit renders the order summary without a layout crash.

    Submitting reveals an `{% if state.submitted %}` block containing a
    `{% vstack padding_left=2 %}`. Directional padding reaches the layout node
    as a 4-tuple, which used to crash the VStack geometry (int + tuple). See
    issues.md (06-29 review).
    """
    app = _load("widgets/radio_demo.py")
    with WijjitHarness(app, size=(90, 36)) as h:
        _click_button(h, "Submit Order")
        assert app.state["submitted"] is True
        h.assert_text("Order submitted")


@pytest.mark.parametrize(
    "rel_path,label,old_key,new_text",
    [
        # The reconciler key-collision fix: text nodes whose positional keys
        # shift when conditional content appears must not be dropped.
        ("advanced/form_demo.py", "Register", "text_2", "Error"),
    ],
)
def test_reconciler_keeps_shifted_text_nodes(rel_path, label, old_key, new_text):
    """A text node whose positional key shifts is not evicted from the cache."""
    app = _load(rel_path)
    with WijjitHarness(app, size=(90, 38)) as h:
        _click_button(h, label)
        cache = app.renderer._reconciler._element_cache
        # Every text_* key referenced after the change is present (no gap).
        text_keys = [k for k in cache if str(k).startswith("text_")]
        assert old_key in text_keys
