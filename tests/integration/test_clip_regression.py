"""Clip-region regression suite for element rendering (review item 2.1).

Each test places one element inside a scrollable frame with filler rows above
it, scrolls the frame to its maximum so the element's top rows land *above*
the frame's visible interior, and asserts that nothing painted over the frame's
top border or the content row above the frame.

Before the PaintContext migration, elements that write cells directly via
``ctx.buffer.set_cell(...)`` bypass the clip region and overwrite both rows.
Tests for not-yet-migrated elements are marked ``xfail(strict=True)``; each
migration workstream removes its marker.

Screen geometry used by every test (size 60x16)::

    row 0   TOP-SENTINEL          <- must never be painted over
    row 1   +-- frame top border  <- must never be painted over
    rows 2-7  frame interior (6 rows)
    row 8   +-- frame bottom border

The frame content is 4 filler text rows plus the element (height 8), so the
scroll range is 6 and at maximum scroll the element's two top rows are above
the interior.
"""

import pytest

from wijjit.testing import WijjitHarness, app_from_template

FRAME_HEIGHT = 8
FILLER_ROWS = 4
ELEMENT_HEIGHT = 8
MAX_SCROLL = 6  # (FILLER_ROWS + ELEMENT_HEIGHT) - (FRAME_HEIGHT - 2 borders)


def _scaffold(element_tpl: str) -> str:
    fillers = "".join(
        "{% text %}filler-" + str(i) + "{% endtext %}" for i in range(FILLER_ROWS)
    )
    return (
        "{% vstack spacing=0 %}"
        "{% text %}TOP-SENTINEL{% endtext %}"
        '{% frame id="clip" border="single" width=52 height='
        + str(FRAME_HEIGHT)
        + " scrollable=true %}"
        "{% vstack spacing=0 %}" + fillers + element_tpl + "{% endvstack %}"
        "{% endframe %}"
        "{% endvstack %}"
    )


TOP_BORDER_CHARS = {"┌", "─", "┐"}
BOTTOM_BORDER_CHARS = {"└", "─", "┘"}


def _assert_element_clipped(element_tpl: str, context: dict | None = None) -> None:
    """Drive both overflow directions and assert the element stayed inside.

    Phase 1 (no scroll): the element overflows the *bottom* of the frame;
    the bottom border and the rows below the frame must stay untouched.
    Phase 2 (max scroll): the element's top rows are above the frame
    interior; the top border and the sentinel row above must stay untouched.
    """
    app = app_from_template(_scaffold(element_tpl), context=context)
    with WijjitHarness(app, size=(60, 16)) as h:
        frame = app.get_element_by_id("clip")
        assert frame is not None, "scaffold frame not found"

        # Phase 1: unscrolled, the element sticks out past the interior's end.
        lines = h.screen().splitlines()
        assert (
            set(lines[8].strip()) <= BOTTOM_BORDER_CHARS
        ), f"frame bottom border was painted over: {lines[8]!r}"
        for i in range(9, len(lines)):
            assert (
                lines[i].strip() == ""
            ), f"content below the frame was painted (row {i}): {lines[i]!r}"

        # Phase 2: scroll to max so the element's top rows are above the
        # interior.
        assert frame.scroll_manager is not None, "frame did not become scrollable"
        frame.scroll_manager.scroll_to(MAX_SCROLL)
        h.tick()
        assert (
            frame.get_scroll_offset() == MAX_SCROLL
        ), "scenario setup failed: frame did not scroll to max"

        lines = h.screen().splitlines()
        # The row above the frame must be untouched by the scrolled element.
        assert lines[0].strip() == "TOP-SENTINEL", (
            "content above the frame was painted over by the scrolled "
            f"element: {lines[0]!r}"
        )
        # The frame's top border must be intact (border characters only).
        assert (
            set(lines[1].strip()) <= TOP_BORDER_CHARS
        ), f"frame top border was painted over: {lines[1]!r}"


def test_textarea_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% textarea id="el" width=46 height='
        + str(ELEMENT_HEIGHT)
        + ' border="single" %}TA-0\nTA-1\nTA-2\nTA-3{% endtextarea %}'
    )


def test_tree_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% tree id="el" data=tree_data height='
        + str(ELEMENT_HEIGHT)
        + ' border="single" title="TREE" %}{% endtree %}',
        context={
            "tree_data": {
                "label": "root",
                "children": [{"label": f"TREE-{i}"} for i in range(6)],
            }
        },
    )


def test_listview_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% listview id="el" items=lv_items height='
        + str(ELEMENT_HEIGHT)
        + ' border="single" title="LIST" %}{% endlistview %}',
        context={"lv_items": [f"LV-{i}" for i in range(6)]},
    )


def test_logview_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% logview id="el" lines=log_lines width=46 height='
        + str(ELEMENT_HEIGHT)
        + ' border="single" title="LOG" %}{% endlogview %}',
        context={"log_lines": [f"LOG-{i}" for i in range(6)]},
    )


def test_tabbedpanel_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% tabbedpanel id="el" width=46 height='
        + str(ELEMENT_HEIGHT)
        + ' border="single" %}'
        '{% tab label="TB1" %}TAB-CONTENT{% endtab %}'
        "{% endtabbedpanel %}"
    )


def test_codeeditor_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% codeeditor id="el" language="python" width=46 height='
        + str(ELEMENT_HEIGHT)
        + " %}CODE = 0\nCODE = 1\nCODE = 2{% endcodeeditor %}"
    )


def test_contentview_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% contentview id="el" content_type="plain" width=46 height='
        + str(ELEMENT_HEIGHT)
        + ' title="CV" %}CV-0\nCV-1\nCV-2{% endcontentview %}'
    )


def test_columnchart_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% columnchart id="el" data=chart_data width=46 height='
        + str(ELEMENT_HEIGHT)
        + " show_axis=true %}{% endcolumnchart %}",
        context={"chart_data": [("AA", 10), ("BB", 20), ("CC", 15)]},
    )


def test_pager_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% pager id="el" width=46 height='
        + str(ELEMENT_HEIGHT)
        + ' border="single" %}'
        '{% page title="P1" %}PAGE-CONTENT{% endpage %}'
        "{% endpager %}"
    )


def test_table_clipped_by_scrolled_frame():
    _assert_element_clipped(
        '{% table id="el" columns=["A"] data=table_data height='
        + str(ELEMENT_HEIGHT)
        + " %}{% endtable %}",
        context={"table_data": [{"A": f"T-{i}"} for i in range(6)]},
    )
