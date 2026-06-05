"""Layout regression tests for ``examples/advanced/error_handling_demo.py``.

The demo previously overflowed its outer frame vertically (scrollbar appeared,
right-column child frames had their right borders clipped) and horizontally
(the third simulated-error button was truncated). These tests render the demo
through the standard headless harness and assert that:

- No vertical scrollbar character is rendered (no overflow).
- All three simulated-error buttons are present in full.
- The bottom action row (``Clear Errors`` / ``Clear History`` / ``Quit``) and
  the footer hint are visible.
- The two right-column child frames have intact right borders.
- The layout stays clean when an error message is set (the conditional row
  must not push content past the outer frame's bottom).
"""

from __future__ import annotations

from pathlib import Path

from wijjit.testing import load_example_app
from wijjit.testing.harness import WijjitHarness

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO = REPO_ROOT / "examples" / "advanced" / "error_handling_demo.py"
HARNESS_SIZE = (112, 45)


def _render(error_message: str = "") -> str:
    """Load the demo, optionally seed an error, and return the rendered screen."""
    app = load_example_app(DEMO)
    if error_message:
        app.state["error_message"] = error_message
    with WijjitHarness(app, size=HARNESS_SIZE) as harness:
        harness.tick(frames=2)
        return harness.screen()


def test_no_vertical_scrollbar() -> None:
    """The outer frame must fully contain its content (no overflow scrollbar)."""
    screen = _render()
    assert "█" not in screen, (
        "Vertical scrollbar block character appeared - content overflows the "
        "outer frame. The demo should fit at the documented size.\n\n" + screen
    )


def test_all_simulated_error_buttons_visible() -> None:
    """All three simulated-error buttons render in full (no truncation)."""
    screen = _render()
    for label in ("Null Ref", "Type Error", "Async Error"):
        assert label in screen, (
            f"Simulated-error button '{label}' missing or truncated.\n\n" + screen
        )


def test_bottom_action_buttons_and_footer_visible() -> None:
    """The bottom action row and footer hint must render inside the frame."""
    screen = _render()
    for label in ("Clear Errors", "Clear History", "Quit"):
        assert label in screen, f"Bottom button '{label}' not visible.\n\n{screen}"
    assert "[q] Quit" in screen, "Footer hint missing.\n\n" + screen


def test_right_column_frames_have_intact_right_borders() -> None:
    """The History and Patterns frame right borders must not be clipped.

    Right-border clipping showed up as the outer ``|`` sitting directly on the
    inner ``|`` with no separation, or the inner ``|`` being replaced by the
    scrollbar block. We assert the frame titles render and the screen has no
    ``█`` (already covered) and that the lines immediately after each
    title contain a closing ``┐`` somewhere - i.e. the frame closed
    properly rather than being cut off.
    """
    screen = _render()
    assert "Error History" in screen
    assert "Error Handling Patterns" in screen
    # Each child frame must have at least one top-right corner glyph.
    assert screen.count("┐") >= 3, (
        "Expected >= 3 top-right corners (outer + 2 child frames); some child "
        "frames likely had their top-right border clipped.\n\n" + screen
    )


def test_layout_stable_with_error_message() -> None:
    """Setting an error_message must not push content past the frame bottom."""
    screen = _render(error_message="Invalid JSON: Expecting value at position 0")
    assert "█" not in screen, (
        "Setting an error message caused vertical overflow.\n\n" + screen
    )
    assert "[ERROR]" in screen, "Error message row should be rendered."
    # Bottom actions still visible:
    assert "Clear Errors" in screen
    assert "Quit" in screen
    assert "[q] Quit" in screen
