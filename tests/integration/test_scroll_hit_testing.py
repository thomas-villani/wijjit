"""Mouse hit-testing regression tests for scrolled frames.

When a scrollable frame is scrolled, the renderer paints its children at a
shifted on-screen position (``bounds.y - scroll_offset``) but leaves each
element's logical ``bounds`` untouched. Hit-testing must therefore match the
*painted* position, not the logical one - otherwise a click only registers
several rows below where the element visually appears (the cross-cutting
"must click below a scrolled button" bug). See ``issues.md`` (06-29 review).
"""

from __future__ import annotations

from wijjit import Wijjit
from wijjit.elements.input import Button
from wijjit.testing import WijjitHarness

# A short scrollable frame whose button content overflows the viewport, so the
# button only becomes visible after scrolling down.
TEMPLATE = """
{% frame id="scroller" border="single" width=40 height=7 scrollable=true %}
  {% vstack spacing=0 %}
    {% text %}row 0{% endtext %}
    {% text %}row 1{% endtext %}
    {% text %}row 2{% endtext %}
    {% text %}row 3{% endtext %}
    {% text %}row 4{% endtext %}
    {% text %}row 5{% endtext %}
    {% button id="target" action="hit" %}Click Me{% endbutton %}
    {% text %}row 7{% endtext %}
    {% text %}row 8{% endtext %}
  {% endvstack %}
{% endframe %}
"""


def _make_app() -> tuple[Wijjit, list[bool]]:
    app = Wijjit()
    clicked: list[bool] = []

    @app.view("main", default=True)
    def main_view():
        return {"template": TEMPLATE, "data": {}}

    @app.on_action("hit")
    def on_hit(event):  # noqa: ANN001 - test handler
        clicked.append(True)

    return app, clicked


def test_click_hits_button_at_its_scrolled_on_screen_position():
    """A click where a scrolled button visually appears triggers its action."""
    app, clicked = _make_app()
    with WijjitHarness(app, size=(60, 24)) as h:
        frame = app.get_element_by_id("scroller")
        btn = app.get_element_by_id("target")
        assert isinstance(btn, Button)
        assert btn.bounds is not None

        # Scroll the frame down until the button is painted inside the viewport.
        h.scroll(10, 4, "down", amount=4)

        offset = frame.get_scroll_offset()
        assert offset > 0, "frame should have scrolled"

        # The button is now painted offset rows above its logical position.
        assert btn._screen_bounds is not None, "button should be visible after scroll"
        visual_y = btn.bounds.y - offset
        assert btn._screen_bounds.y == visual_y

        # Click where the button VISUALLY is (logical row - scroll offset).
        # Before the fix this missed, because hit-testing used the logical row.
        h.click(btn._screen_bounds.x + 1, visual_y)
        assert clicked, "click at the on-screen position should hit the button"


def test_click_at_stale_logical_position_does_not_hit_scrolled_button():
    """Clicking the button's old (unscrolled) row must not trigger it."""
    app, clicked = _make_app()
    with WijjitHarness(app, size=(60, 24)) as h:
        frame = app.get_element_by_id("scroller")
        btn = app.get_element_by_id("target")
        assert btn.bounds is not None

        h.scroll(10, 4, "down", amount=4)
        assert frame.get_scroll_offset() > 0

        # The logical row is now below the viewport (scrolled past); a click
        # there is outside the button's painted rect and must not fire it.
        h.click(btn.bounds.x + 1, btn.bounds.y)
        assert not clicked, "click at the stale logical row should not hit the button"
