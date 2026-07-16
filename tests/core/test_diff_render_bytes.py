"""Regression tests for the diff renderer's terminal output volume.

The diff renderer's payoff is *bytes written to the terminal*, not CPU: an idle
frame must emit nothing, and a frame in which one widget changed must emit a
small update rather than a full repaint. Those properties are what keep a Wijjit
app flicker-free and responsive over a slow link, and they are easy to regress
silently (a stray full-buffer invalidation still renders correctly, it just
writes 500x more bytes).

The numbers here are deterministic. ``scripts/bench_perf.py`` reports the same
measurements in a human-readable table.

``test_readme_headline_bytes`` additionally pins the specific figures quoted in
``README.md``'s Performance section, by driving the *same* dashboard scenario the
benchmark script uses. Without it the advertised "37 bytes" could quietly become
150 and every test here would still pass.
"""

import importlib.util
import sys
from pathlib import Path

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


def _load_bench_perf():
    """Import ``scripts/bench_perf.py``, which is not an installed package.

    The README's figures come from that script's dashboard scenario, so the pin
    below reuses its template and context rather than copying them (which would
    let the test and the tool drift apart silently).
    """
    path = Path(__file__).resolve().parents[2] / "scripts" / "bench_perf.py"
    spec = importlib.util.spec_from_file_location("bench_perf", path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve __module__ through sys.modules during class creation.
    sys.modules["bench_perf"] = module
    spec.loader.exec_module(module)
    return module


# (width, height, full-repaint band) for the figures quoted in README.md.
#
# The one-change count is pinned tightly: it is the headline claim, and it is
# stable across NO_COLOR and ASCII-border modes (verified - only the glyphs
# around it change, not the bytes the diff emits for the changed cells).
#
# The full-repaint band is wide on purpose. That number *does* move with the
# environment: dropping color and box-drawing borders takes the 200x60 repaint
# from 15,980 to 14,088 bytes, and UNICODE_SUPPORT="auto" can resolve either way
# depending on the CI runner's locale. The band is set to catch a structural
# regression (a stray full-buffer invalidation), not to assert an exact width.
README_DASHBOARD_BYTES = [
    (80, 24, 3_676, 2_500, 4_500),
    (200, 60, 15_980, 13_000, 18_000),
]


@pytest.mark.parametrize(
    ("width", "height", "documented_full", "full_low", "full_high"),
    README_DASHBOARD_BYTES,
)
def test_readme_headline_bytes(width, height, documented_full, full_low, full_high):
    """Pin the byte figures README.md quotes, so the claim cannot rot silently.

    If this trips, either a regression landed (fix it) or the cost genuinely
    changed - in which case re-measure with ``uv run python scripts/bench_perf.py``
    and update *both* this budget and the README table in the same change.
    """
    bench = _load_bench_perf()
    count = bench.measure_bytes(
        "dashboard (table + charts)",
        bench.DASHBOARD,
        bench._dashboard_context,
        width,
        height,
    )

    # README: "A frame in which nothing changed writes nothing at all."
    assert count.idle_bytes == 0

    # README: "Advancing the sparkline by one tick writes 37 bytes."
    assert 30 <= count.change_bytes <= 45, (
        f"README quotes 37 bytes for a one-tick change at {width}x{height}; "
        f"measured {count.change_bytes}"
    )

    # README: "a full repaint ... writes 15,980 bytes" (3,676 at 80x24).
    assert full_low <= count.full_bytes <= full_high, (
        f"README quotes ~{documented_full:,} bytes for a full repaint at "
        f"{width}x{height}; measured {count.full_bytes:,}"
    )

    # The saving the Performance section is actually selling. Measured: ~99x at
    # 80x24, ~432x at 200x60 - the ratio grows with screen area, since the diff
    # cost tracks the change and the repaint cost tracks the cells.
    assert count.full_bytes > count.change_bytes * 50
