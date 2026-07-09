"""Regression tests for the diff renderer's terminal output volume.

The diff renderer's payoff is *bytes written to the terminal*, not CPU: an idle
frame must emit nothing, and a frame in which one widget changed must emit a
small update rather than a full repaint. Those properties are what keep a Wijjit
app flicker-free and responsive over a slow link, and they are easy to regress
silently (a stray full-buffer invalidation still renders correctly, it just
writes 500x more bytes).

The numbers here are deterministic. ``scripts/bench_perf.py`` reports the same
measurements in a human-readable table.
"""

import pytest

from wijjit.core.renderer import Renderer

TEMPLATE = """
{% frame title="Counter" border="single" %}
  {% vstack spacing=1 %}
    Hello, world.
    Frame {{ tick }}
    {% button action="go" %}Go{% endbutton %}
  {% endvstack %}
{% endframe %}
"""

SIZES = [(80, 24), (120, 40), (200, 60)]


def _render(renderer, tick, width, height):
    out, _, _ = renderer.render_with_layout(
        TEMPLATE, context={"tick": tick}, width=width, height=height
    )
    return out


@pytest.mark.parametrize(("width", "height"), SIZES)
def test_idle_frame_emits_nothing(width, height):
    """Re-rendering identical content must produce zero output."""
    renderer = Renderer()
    _render(renderer, 0, width, height)  # first paint

    assert _render(renderer, 0, width, height) == ""
    # Still nothing on a third identical frame.
    assert _render(renderer, 0, width, height) == ""


@pytest.mark.parametrize(("width", "height"), SIZES)
def test_full_repaint_covers_the_screen(width, height):
    """A forced full repaint should scale with the screen area."""
    renderer = Renderer()
    _render(renderer, 0, width, height)
    renderer._last_displayed_buffer = None  # force a full render

    full = _render(renderer, 0, width, height)

    # At minimum one byte per cell; ANSI positioning pushes it higher.
    assert len(full) >= width * height


@pytest.mark.parametrize(("width", "height"), SIZES)
def test_single_change_emits_a_small_diff(width, height):
    """Changing one line must not repaint the whole screen."""
    renderer = Renderer()
    _render(renderer, 0, width, height)
    renderer._last_displayed_buffer = None
    full = _render(renderer, 0, width, height)

    # "Frame 0" -> "Frame 1": a single character on a single row.
    changed = _render(renderer, 1, width, height)

    assert 0 < len(changed) <= 200, f"one-character change emitted {len(changed)} bytes"
    # The whole point: dramatically cheaper than a repaint.
    assert len(changed) * 10 < len(full)
