"""``ContentView`` reports click and hover positions as (line, column).

The view handled only the scroll wheel, so an app that knows what sits where in
its content (a document viewer that placed its own links and footnote markers)
could not make any of it clickable: it never learned where the user clicked.
It now reports the content line (scroll offset applied) and the display column
within it, through ``on_click``, a template ``action``, and ``on_hover``.

Columns are display columns, a wide character counting two, which needs the
ANSI path to lay wide glyphs out as two cells; that is covered first.
"""

import pytest

from wijjit.rendering.ansi_adapter import ansi_string_to_cells, clip_cells
from wijjit.terminal.cell import CONTINUATION_CHAR, Hyperlink
from wijjit.testing import WijjitHarness, app_from_template

WIDE = "日本"  # two width-2 CJK glyphs


# ------------------------------------------------- wide glyphs in ANSI content


def test_wide_glyph_gets_a_continuation_cell():
    cells = ansi_string_to_cells(f"a{WIDE}b")

    assert [c.char for c in cells] == [
        "a",
        WIDE[0],
        CONTINUATION_CHAR,
        WIDE[1],
        CONTINUATION_CHAR,
        "b",
    ]


def test_continuation_cell_shares_the_glyph_style_and_link():
    link = Hyperlink("https://example.com")
    cells = ansi_string_to_cells(
        f"\x1b]8;;{link.url}\x1b\\\x1b[1;31m{WIDE[0]}\x1b[0m\x1b]8;;\x1b\\"
    )

    head, tail = cells
    assert tail.char == CONTINUATION_CHAR
    assert (tail.bold, tail.fg_color, tail.link) == (True, head.fg_color, link)


def test_combining_mark_folds_onto_its_base():
    cells = ansi_string_to_cells("éx")  # NFD e + acute

    assert [c.char for c in cells] == ["é", "x"]


def test_combining_mark_after_a_wide_glyph_folds_onto_the_head():
    cells = ansi_string_to_cells(f"{WIDE[0]}́")

    assert [c.char for c in cells] == [WIDE[0] + "́", CONTINUATION_CHAR]


def test_clip_cells_never_halves_a_wide_glyph():
    cells = ansi_string_to_cells(f"a{WIDE}")  # columns: a, head, cont, head, cont

    assert [c.char for c in clip_cells(cells, 3)] == ["a", WIDE[0], ""]
    # The cut falls between the second glyph's head and continuation.
    assert [c.char for c in clip_cells(cells, 4)] == ["a", WIDE[0], "", " "]


def test_wide_ansi_content_stays_inside_its_border():
    """Each wide glyph used to be one cell, so a line of them spilled past the
    right border once the terminal drew each at two columns."""
    template = (
        '{% vstack width="fill" height="fill" %}'
        '{% contentview content=state.doc content_type="ansi" width=12 height=3 '
        "show_scrollbar=False %}{% endcontentview %}"
        "{% endvstack %}"
    )
    with WijjitHarness(
        app_from_template(template, state={"doc": WIDE * 10}), size=(20, 6)
    ) as h:
        # The buffer holds one cell per column (screen text, one per glyph).
        rows = [
            [cell.char for cell in row]
            for row in h.app.renderer._last_displayed_buffer.cells
            if "│" in [cell.char for cell in row]
        ]
        assert rows
        for chars in rows:
            left = chars.index("│")
            right = len(chars) - 1 - chars[::-1].index("│")
            assert right - left == 11  # 10 content columns between the borders
        assert rows[0][left + 1 : right] == [WIDE[0], "", WIDE[1], ""] * 2 + [
            WIDE[0],
            "",
        ]


# ------------------------------------------------- positions

DOC = "\n".join(f"line {n:02d} " + "abcdefghij" for n in range(30))

TEMPLATE = (
    '{% vstack width="fill" height="fill" %}'
    '{% contentview id="doc" content=state.doc content_type="ansi" '
    "width=30 height=8 border=state.border "
    "on_click=state.on_click on_hover=state.on_hover action=state.action %}"
    "{% endcontentview %}"
    "{% endvstack %}"
)


class Recorder:
    """Collects the calls a callback receives."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, *args) -> None:
        self.calls.append(args)


@pytest.fixture
def clicks():
    return Recorder()


@pytest.fixture
def hovers():
    return Recorder()


def _drive(doc, clicks=None, hovers=None, border="single", action=None, actions=None):
    state = {
        "doc": doc,
        "border": border,
        "on_click": clicks,
        "on_hover": hovers,
        "action": action,
    }
    return WijjitHarness(
        app_from_template(TEMPLATE, state=state, actions=actions or {}), size=(40, 14)
    )


def _origin(h):
    """Screen cell of content line 0, column 0 (inside the border)."""
    view = h.app.get_element_by_id("doc")
    inset = 0 if view.border_style == "none" else 1
    return view.bounds.x + inset, view.bounds.y + inset


def test_click_reports_line_and_column(clicks):
    with _drive(DOC, clicks) as h:
        x0, y0 = _origin(h)
        h.click(x0 + 3, y0 + 2)

    ((line, column, event),) = clicks.calls
    assert (line, column) == (2, 3)
    assert (event.x, event.y) == (x0 + 3, y0 + 2)


def test_click_on_a_scrolled_view_applies_the_offset(clicks):
    with _drive(DOC, clicks) as h:
        x0, y0 = _origin(h)
        h.scroll(x0 + 1, y0 + 1, "down", amount=5)
        h.click(x0, y0)
        h.assert_text("line 05")

    assert [call[:2] for call in clicks.calls] == [(5, 0)]


def test_click_without_a_border(clicks):
    with _drive(DOC, clicks, border="none") as h:
        x0, y0 = _origin(h)
        h.click(x0 + 7, y0)

    assert [call[:2] for call in clicks.calls] == [(0, 7)]


def test_border_scrollbar_and_empty_rows_report_nothing(clicks):
    short = "one\ntwo"
    with _drive(DOC, clicks) as h:
        view = h.app.get_element_by_id("doc")
        b = view.bounds
        h.click(b.x, b.y + 2)  # left border
        h.click(b.x + 5, b.y)  # top border
        h.click(b.x + b.width - 1, b.y + 2)  # right border
        h.click(b.x + b.width - 2, b.y + 2)  # scrollbar column
        assert view.content_position_at(b.x + b.width - 2, b.y + 2) is None
    with _drive(short, clicks) as h:
        x0, y0 = _origin(h)
        h.click(x0, y0 + 5)  # below the last line

    assert clicks.calls == []


def test_column_past_a_short_line_is_still_reported(clicks):
    with _drive("ab\ncd", clicks) as h:
        x0, y0 = _origin(h)
        h.click(x0 + 9, y0 + 1)

    assert [call[:2] for call in clicks.calls] == [(1, 9)]


def test_second_cell_of_a_wide_character_reports_its_column(clicks):
    with _drive(f"ab{WIDE}c", clicks) as h:
        x0, y0 = _origin(h)
        for dx in range(7):
            h.click(x0 + dx, y0)

    # a=0, b=1, first glyph=2..3, second glyph=4..5, c=6
    assert [call[1] for call in clicks.calls] == [0, 1, 2, 2, 4, 4, 6]


def test_template_action_carries_the_position():
    events = []
    with _drive(DOC, action="jump", actions={"jump": events.append}) as h:
        x0, y0 = _origin(h)
        h.click(x0 + 4, y0 + 1)

    (event,) = events
    assert event.action_id == "jump"
    assert event.data == {"line": 1, "column": 4}


def test_right_click_does_not_report(clicks):
    with _drive(DOC, clicks) as h:
        x0, y0 = _origin(h)
        h.click(x0, y0, button="right")

    assert clicks.calls == []


def test_hover_reports_changes_and_leaving(hovers):
    with _drive(DOC, hovers=hovers) as h:
        x0, y0 = _origin(h)
        view = h.app.get_element_by_id("doc")
        h.hover(x0 + 1, y0)
        h.hover(x0 + 1, y0)  # same cell: not reported again
        h.hover(x0 + 2, y0 + 3)
        h.hover(view.bounds.x, y0)  # onto the border
        h.hover(x0, y0)
        h.hover(x0 + 35, y0 + 10)  # off the view entirely

    assert hovers.calls == [
        (0, 1),
        (3, 2),
        (None, None),
        (0, 0),
        (None, None),
    ]


def test_wheel_under_a_still_pointer_reports_the_new_position(hovers):
    with _drive(DOC, hovers=hovers) as h:
        x0, y0 = _origin(h)
        h.hover(x0, y0)
        h.scroll(x0, y0, "down", amount=2)

    assert hovers.calls == [(0, 0), (1, 0), (2, 0)]


def test_callable_content_positions_are_in_its_own_layout(clicks):
    widths = []

    def layout(width):
        widths.append(width)
        return "\n".join("x" * width for _ in range(3))

    with _drive(layout, clicks) as h:
        x0, y0 = _origin(h)
        last = widths[-1] - 1
        h.click(x0 + last, y0 + 2)

    assert [call[:2] for call in clicks.calls] == [(2, last)]
