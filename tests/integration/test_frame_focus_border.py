"""Focus-border coloring regression for child-bearing frames.

A frame whose body holds child elements draws its top/bottom borders via
``Frame.render_to`` (focus-aware) but skips the body, so the vertical side
borders are painted only by the renderer's frame-border pass. That pass used to
ignore focus, so a focused frame rendered with focus-colored top/bottom borders
but unfocused (gray) left/right borders - a "half-highlighted" glitch. The pass
is now focus-aware; all four sides share the focus color. See issues.md (06-29).
"""

from __future__ import annotations

from wijjit import Wijjit
from wijjit.testing import WijjitHarness

TEMPLATE = """
{% frame id="f" title="Box" border="single" width=20 height=8 scrollable=true %}
  {% vstack %}
    line a
    line b
    line c
    line d
    line e
    line f
    line g
    line h
  {% endvstack %}
{% endframe %}
"""


def _make_app() -> Wijjit:
    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        return {"template": TEMPLATE, "data": {}}

    return app


def _border_colors(app):
    """Return (top_left_corner_fg, left_side_fg) for the frame ``f``."""
    frame = app.get_element_by_id("f")
    b = frame.bounds
    buf = app.renderer._last_displayed_buffer
    corner = buf.get_cell(b.x, b.y)  # top-left corner '+'
    side = buf.get_cell(b.x, b.y + 2)  # a left '|' on a content row
    return corner.fg_color, side.fg_color


def test_focused_frame_side_borders_match_top_border():
    """When focused, the vertical side border shares the top border's color."""
    app = _make_app()
    with WijjitHarness(app, size=(30, 12)) as h:
        frame = app.get_element_by_id("f")
        frame.focused = True
        app.needs_render = True
        h.tick()

        corner_fg, side_fg = _border_colors(app)
        assert corner_fg is not None
        # The side border must carry the SAME focus color as the corner/top.
        assert side_fg == corner_fg


def test_unfocused_frame_border_differs_from_focused():
    """Sanity: the side border color actually changes with focus.

    Guards against the test trivially passing because every border shares one
    static color regardless of focus.
    """
    focused_side = None
    unfocused_side = None

    app = _make_app()
    with WijjitHarness(app, size=(30, 12)) as h:
        frame = app.get_element_by_id("f")
        frame.focused = True
        app.needs_render = True
        h.tick()
        _, focused_side = _border_colors(app)

    app2 = _make_app()
    with WijjitHarness(app2, size=(30, 12)) as h:
        frame2 = app2.get_element_by_id("f")
        frame2.focused = False
        app2.needs_render = True
        h.tick()
        _, unfocused_side = _border_colors(app2)

    assert focused_side != unfocused_side
