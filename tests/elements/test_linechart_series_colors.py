"""Per-series coloring for multi-series line charts.

``series_colors`` was accepted and documented but never read, so every series in
a multi-series LineChart rendered in the single theme color and the lines were
indistinguishable. Series now take a color from ``series_colors`` or, failing
that, the next slot of the default categorical palette.
"""

import re

import pytest

from wijjit.elements.display.chart_utils import DEFAULT_SERIES_COLORS, get_series_color
from wijjit.elements.display.linechart import LineChart
from wijjit.styling.style import Style, parse_color
from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = (
    "{% vstack %}"
    '{% linechart id="c" data=series width=54 height=12 %}{% endlinechart %}'
    "{% endvstack %}"
)

TEMPLATE_OVERRIDES = (
    "{% vstack %}"
    '{% linechart id="c" data=series width=54 height=12 series_colors=sc %}'
    "{% endlinechart %}"
    "{% endvstack %}"
)


def fg_colors(chart: LineChart) -> list[tuple[int, int, int] | None]:
    """Resolve the chart's per-series styles and return their foreground colors."""
    return [style.fg_color for style in chart._resolve_series_styles(Style())]


def emitted_fg(screen_ansi: str) -> set[str]:
    """Collect the distinct truecolor foreground SGR sequences in a screen."""
    return set(re.findall(r"\x1b\[38;2;[0-9;]+m", screen_ansi))


def test_single_series_takes_no_palette_slot():
    # A one-series chart must look exactly as it did before the palette existed.
    chart = LineChart(data=[10, 20, 15, 30])
    assert fg_colors(chart) == [None]


def test_multi_series_assigns_palette_in_order():
    chart = LineChart(data={"Sales": [1, 2], "Costs": [3, 4], "Net": [5, 6]})
    assert fg_colors(chart) == [
        parse_color(get_series_color(0)),
        parse_color(get_series_color(1)),
        parse_color(get_series_color(2)),
    ]


def test_series_colors_override_palette():
    chart = LineChart(
        data={"Sales": [1, 2], "Costs": [3, 4]},
        series_colors={"Sales": "#ff0000"},
    )
    # Named series takes the override; the unnamed one still gets its own slot,
    # which is the slot for its position rather than the first free color.
    assert fg_colors(chart) == [(255, 0, 0), parse_color(get_series_color(1))]


def test_explicit_color_suppresses_palette():
    # ``color`` means "draw every series this color" -- it must not be silently
    # overridden by the palette. render_to merges ``color`` into the base style
    # before resolving series, so the contract here is that every series is
    # handed back that base untouched.
    chart = LineChart(data={"A": [1, 2], "B": [3, 4]}, color="#00ff00")
    base = Style(fg_color=(0, 255, 0))
    assert [s.fg_color for s in chart._resolve_series_styles(base)] == [
        (0, 255, 0),
        (0, 255, 0),
    ]


def test_explicit_color_still_yields_to_series_colors():
    chart = LineChart(
        data={"A": [1, 2], "B": [3, 4]},
        color="#00ff00",
        series_colors={"B": "#0000ff"},
    )
    assert fg_colors(chart)[1] == (0, 0, 255)


def test_palette_wraps_past_its_length():
    n = len(DEFAULT_SERIES_COLORS)
    assert get_series_color(n) == get_series_color(0)
    assert get_series_color(n + 3) == get_series_color(3)


def test_series_colors_none_is_tolerated():
    # The template tag applies props by setattr, so a None must not break lookup.
    chart = LineChart(data={"A": [1, 2], "B": [3, 4]})
    chart.series_colors = None  # type: ignore[assignment]
    assert len(fg_colors(chart)) == 2


@pytest.mark.parametrize("count", [2, 3, 4])
def test_rendered_multi_series_emits_distinct_colors(count):
    # The regression this file exists for: distinct colors must reach the screen.
    data = {f"S{i}": [i, i + 2, i + 1, i + 4] for i in range(count)}
    app = app_from_template(TEMPLATE, context={"series": data})
    with WijjitHarness(app, size=(60, 16)) as harness:
        emitted = emitted_fg(harness.screen_ansi())

    expected = {
        "\x1b[38;2;{};{};{}m".format(*parse_color(get_series_color(i)))
        for i in range(count)
    }
    assert expected <= emitted


def test_rendered_series_colors_reach_the_screen():
    app = app_from_template(
        TEMPLATE_OVERRIDES,
        context={
            "series": {"Sales": [10, 20, 15, 30], "Costs": [5, 8, 7, 12]},
            "sc": {"Sales": "#ff0000", "Costs": "#0000ff"},
        },
    )
    with WijjitHarness(app, size=(60, 16)) as harness:
        emitted = emitted_fg(harness.screen_ansi())

    assert "\x1b[38;2;255;0;0m" in emitted
    assert "\x1b[38;2;0;0;255m" in emitted


def test_single_series_render_is_monochrome():
    app = app_from_template(TEMPLATE, context={"series": [10, 20, 15, 30]})
    with WijjitHarness(app, size=(60, 16)) as harness:
        emitted = emitted_fg(harness.screen_ansi())

    # No palette color leaks into a single-series chart.
    palette = {
        "\x1b[38;2;{};{};{}m".format(*parse_color(c)) for c in DEFAULT_SERIES_COLORS
    }
    assert not (palette & emitted)


def test_legend_does_not_collide_with_the_x_axis():
    # With show_labels off, no row was reserved for the x-axis line, so it was
    # drawn at avail_height (off the bottom) and, with a multi-series legend
    # present, straight over the legend row.
    template = (
        "{% vstack %}"
        '{% linechart id="c" data=series width=40 height=8 '
        "show_axis=true show_labels=false %}{% endlinechart %}"
        "{% endvstack %}"
    )
    app = app_from_template(
        template, context={"series": {"Alpha": [1, 5, 3, 8], "Beta": [2, 3, 4, 2]}}
    )
    with WijjitHarness(app, size=(48, 12)) as harness:
        lines = [ln for ln in harness.screen().splitlines() if ln.strip()]

    # The axis row (horizontal rule) and the legend row must be distinct rows.
    axis_rows = [i for i, ln in enumerate(lines) if "└" in ln]
    legend_rows = [i for i, ln in enumerate(lines) if "Alpha" in ln]
    assert axis_rows and legend_rows
    assert not set(axis_rows) & set(legend_rows)
    # And the legend sits below the axis, not above it.
    assert min(legend_rows) > min(axis_rows)


def test_legend_labels_stay_in_the_legend_style():
    # The marker carries the series color; the name must not, so identity is
    # never color-alone.
    app = app_from_template(
        TEMPLATE, context={"series": {"Alpha": [1, 5, 3], "Beta": [2, 3, 4]}}
    )
    with WijjitHarness(app, size=(60, 16)) as harness:
        screen = harness.screen()

    assert "Alpha" in screen
    assert "Beta" in screen
