"""Palette colors in ANSI content reach the terminal as palette colors.

The ANSI adapter turned the 16 basic colors (and the 256-color palette) into
fixed RGB from the old VGA table, and the emitters wrote that RGB as
truecolor. So blue (``34``) always came out as ``38;2;0;0;128``, a navy that
is hard to read on a dark background, whatever the user's terminal theme says
blue is. Rich's Markdown links (``4;34``) were the visible casualty.

A palette color now stays a palette index on the cell and is emitted as the
palette code, so the terminal's theme decides, as it does when the same text
is printed straight to the terminal.
"""

import pytest

from wijjit.core.renderer import Renderer
from wijjit.rendering.ansi_adapter import ansi_string_to_cells
from wijjit.terminal import ansi
from wijjit.terminal.cell import Cell, color_sgr, color_to_rgb
from wijjit.terminal.screen_buffer import ScreenBuffer
from wijjit.testing import WijjitHarness, app_from_template

# --------------------------------------------------------------- parsing


@pytest.mark.parametrize(
    ("sgr", "fg", "bg"),
    [
        ("34", 4, None),
        ("94", 12, None),
        ("44", None, 4),
        ("104", None, 12),
        ("30", 0, None),  # palette black is index 0, not "no color"
        ("38;5;200", 200, None),
        ("48;5;17", None, 17),
        ("38;2;10;20;30", (10, 20, 30), None),
        ("31;42", 1, 2),
    ],
)
def test_colors_parse_to_palette_indices_or_rgb(sgr, fg, bg):
    (cell,) = ansi_string_to_cells(f"\x1b[{sgr}mx")

    assert (cell.fg_color, cell.bg_color) == (fg, bg)


def test_out_of_range_256_color_is_ignored():
    (cell,) = ansi_string_to_cells("\x1b[38;5;300mx")

    assert cell.fg_color is None


def test_default_color_codes_clear_the_color():
    cells = ansi_string_to_cells("\x1b[31;44ma\x1b[39mb\x1b[49mc")

    assert [(c.fg_color, c.bg_color) for c in cells] == [
        (1, 4),
        (None, 4),
        (None, None),
    ]


def test_attribute_off_codes():
    cells = ansi_string_to_cells("\x1b[1;2;3;4;7ma\x1b[22mb\x1b[23mc\x1b[24md\x1b[27me")

    flags = [(c.bold, c.dim, c.italic, c.underline, c.reverse) for c in cells]
    assert flags == [
        (True, True, True, True, True),
        (False, False, True, True, True),
        (False, False, False, True, True),
        (False, False, False, False, True),
        (False, False, False, False, False),
    ]


# --------------------------------------------------------------- emitting


@pytest.mark.parametrize(
    ("color", "background", "expected"),
    [
        (4, False, "34"),
        (12, False, "94"),
        (4, True, "44"),
        (12, True, "104"),
        (0, False, "30"),
        (200, False, "38;5;200"),
        (17, True, "48;5;17"),
        ((10, 20, 30), False, "38;2;10;20;30"),
        ((10, 20, 30), True, "48;2;10;20;30"),
    ],
)
def test_color_sgr(color, background, expected):
    assert color_sgr(color, background=background) == expected


def test_cell_emits_the_palette_code():
    cell = Cell("x", fg_color=4, underline=True)

    assert cell.get_style_codes() == "\x1b[4;34m"
    assert cell.to_ansi() == "\x1b[4;34mx\x1b[0m"


def test_no_color_drops_palette_colors_too():
    ansi.set_no_color(True)
    try:
        assert Cell("x", fg_color=4, bold=True).get_style_codes() == "\x1b[1m"
    finally:
        ansi.set_no_color(None)


def test_round_trip_keeps_the_original_codes():
    """Parsing ANSI and emitting it again gives back the palette codes."""
    (cell,) = ansi_string_to_cells("\x1b[1;94;41mx")

    assert cell.get_style_codes() == "\x1b[1;94;41m"


def test_color_to_rgb():
    assert color_to_rgb((1, 2, 3)) == (1, 2, 3)
    assert color_to_rgb(0) == (0, 0, 0)
    assert color_to_rgb(15) == (255, 255, 255)
    assert color_to_rgb(16) == (0, 0, 0)  # cube origin
    assert color_to_rgb(231) == (255, 255, 255)  # cube corner
    assert color_to_rgb(232) == (8, 8, 8)  # gray ramp start
    assert color_to_rgb(255) == (238, 238, 238)


# --------------------------------------------------------------- end to end

TEMPLATE = (
    '{% vstack width="fill" height="fill" %}'
    "{% contentview content=state.doc content_type=state.kind "
    'width="fill" height="fill" %}{% endcontentview %}'
    "{% endvstack %}"
)


def _emitted(doc, kind="ansi"):
    app = app_from_template(TEMPLATE, state={"doc": doc, "kind": kind})
    with WijjitHarness(app, size=(50, 8)) as h:
        return h.emitted_ansi()


def test_ansi_content_keeps_its_palette_blue():
    out = _emitted("see \x1b[4;34mthe link\x1b[0m here")

    assert "\x1b[4;34mthe link" in out
    assert "38;2;0;0;128" not in out


def test_markdown_links_use_the_terminal_blue():
    out = _emitted("See [the guide](https://example.com).", kind="markdown")

    assert "38;2;0;0;128" not in out
    assert "\x1b[4;34m" in out


# --------------------------------------------------------------- dimming


def test_overlay_dimming_dims_palette_colors_including_black():
    """Dimming needs numbers, so a palette color is dimmed from an RGB
    approximation. Palette black is index 0, which a truthiness test would
    have skipped."""
    renderer = Renderer()
    base = ScreenBuffer(3, 1)
    base.set_cells_horizontal(
        0,
        0,
        [
            Cell("a", fg_color=4),
            Cell("b", bg_color=0),
            Cell("c", fg_color=(100, 100, 100)),
        ],
    )
    renderer._last_base_buffer = base

    renderer._composite_overlays_cells([], 3, 1, apply_dimming=True, dim_factor=0.5)

    row = renderer._last_displayed_buffer.cells[0]
    blue = color_to_rgb(4)
    assert row[0].fg_color == tuple(v // 2 for v in blue)
    assert row[1].bg_color == (0, 0, 0)
    assert row[2].fg_color == (50, 50, 50)
    # The base buffer itself is untouched.
    assert base.cells[0][0].fg_color == 4
