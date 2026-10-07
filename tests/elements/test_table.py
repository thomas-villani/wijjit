"""Tests for Table display element."""

import pytest

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.display.table import Table
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestTable:
    """Tests for Table element."""

    def test_create_table(self):
        """Test creating a basic table."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        columns = ["name", "age"]

        table = Table(id="users", data=data, columns=columns)

        assert table.id == "users"
        assert len(table.data) == 2
        assert len(table.columns) == 2
        assert table.element_type == ElementType.DISPLAY
        assert table.focusable  # Table is focusable for keyboard scrolling

    def test_normalize_columns(self):
        """Test column normalization."""
        # String columns
        table1 = Table(columns=["name", "age"])
        assert table1.columns[0] == {
            "key": "name",
            "label": "name",
            "width": None,
            "align": "left",
        }
        assert table1.columns[1] == {
            "key": "age",
            "label": "age",
            "width": None,
            "align": "left",
        }

        # Dict columns
        table2 = Table(
            columns=[
                {"key": "name", "label": "Full Name", "width": 20},
                {"key": "age", "label": "Age", "width": 5},
            ]
        )
        assert table2.columns[0]["label"] == "Full Name"
        assert table2.columns[0]["width"] == 20
        # Columns default to left alignment when unspecified.
        assert table2.columns[0]["align"] == "left"

    def test_column_alignment(self):
        """Columns accept an ``align`` key, normalized to a Rich justify value."""
        table = Table(
            columns=[
                {"key": "name", "label": "Name"},
                {"key": "amount", "label": "Amount", "align": "right"},
                {"key": "status", "label": "Status", "align": "CENTER"},
                {"key": "note", "label": "Note", "align": "bogus"},
            ]
        )
        assert table.columns[0]["align"] == "left"  # unspecified default
        assert table.columns[1]["align"] == "right"
        assert table.columns[2]["align"] == "center"  # case-insensitive
        assert table.columns[3]["align"] == "left"  # invalid -> default

    def test_right_aligned_column_renders(self):
        """A right-aligned numeric column pushes values to the column's right."""
        table = Table(
            columns=[
                {"key": "item", "label": "Item"},
                {"key": "qty", "label": "Qty", "width": 10, "align": "right"},
            ],
            data=[{"item": "Apples", "qty": "5"}],
            width=40,
            height=8,
        )
        table.set_bounds(Bounds(0, 0, 40, 8))

        output = render_element(table, width=40, height=8)
        # The right-aligned "5" should sit toward the right of its 10-wide
        # column - i.e. several spaces separate "Apples" from "5", rather than
        # the single padding space a left-aligned column would use.
        line = next(ln for ln in output.splitlines() if "Apples" in ln)
        assert "Apples" in line and "5" in line
        gap = line.split("Apples", 1)[1].split("5", 1)[0]
        assert gap.count(" ") >= 5

    def test_empty_table(self):
        """Test table with no data."""
        table = Table(columns=["name", "age"])
        assert len(table.data) == 0
        assert len(table.columns) == 2

        # Should render without errors
        table.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(table, width=40, height=10)
        assert isinstance(output, str)

    def test_set_data(self):
        """Test updating table data."""
        table = Table(columns=["name", "age"])
        assert len(table.data) == 0

        new_data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        table.set_data(new_data)

        assert len(table.data) == 2
        assert table.data[0]["name"] == "Alice"

    def test_sorting(self):
        """Test column sorting."""
        data = [
            {"name": "Charlie", "age": 35},
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

        table = Table(data=data, columns=["name", "age"], sortable=True)

        # Sort by name ascending
        table.sort_by_column("name")
        assert table.sort_column == "name"
        assert table.sort_direction == "asc"
        assert table.data[0]["name"] == "Alice"
        assert table.data[1]["name"] == "Bob"
        assert table.data[2]["name"] == "Charlie"

        # Toggle to descending
        table.sort_by_column("name")
        assert table.sort_direction == "desc"
        assert table.data[0]["name"] == "Charlie"

        # Sort by age
        table.sort_by_column("age")
        assert table.sort_column == "age"
        assert table.sort_direction == "asc"
        assert table.data[0]["age"] == 25

    def test_sorting_disabled(self):
        """Test that sorting doesn't work when disabled."""
        data = [
            {"name": "Charlie", "age": 35},
            {"name": "Alice", "age": 30},
        ]

        table = Table(data=data, columns=["name", "age"], sortable=False)

        # Try to sort (should have no effect)
        table.sort_by_column("name")
        assert table.sort_column is None
        # Data should remain unchanged
        assert table.data[0]["name"] == "Charlie"

    def test_keyboard_scrolling(self):
        """Test keyboard navigation for scrolling."""
        # Create table with more data than viewport
        data = [{"name": f"User {i}", "age": 20 + i} for i in range(20)]
        table = Table(data=data, columns=["name", "age"], height=10)

        initial_pos = table.scroll_manager.state.scroll_position

        # Scroll down
        table.handle_key(Keys.DOWN)
        assert table.scroll_manager.state.scroll_position > initial_pos

        # Scroll up
        current_pos = table.scroll_manager.state.scroll_position
        table.handle_key(Keys.UP)
        assert table.scroll_manager.state.scroll_position < current_pos

        # Home key
        table.handle_key(Keys.HOME)
        assert table.scroll_manager.state.scroll_position == 0

    @pytest.mark.asyncio
    async def test_mouse_scrolling(self):
        """Test mouse wheel scrolling."""
        # Create table with more data than viewport
        data = [{"name": f"User {i}", "age": 20 + i} for i in range(20)]
        table = Table(data=data, columns=["name", "age"], height=10)

        initial_pos = table.scroll_manager.state.scroll_position

        # Scroll down with mouse wheel
        event_down = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_DOWN,
            x=0,
            y=0,
        )
        await table.handle_mouse(event_down)
        assert table.scroll_manager.state.scroll_position > initial_pos

        # Scroll up with mouse wheel
        current_pos = table.scroll_manager.state.scroll_position
        event_up = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_UP,
            x=0,
            y=0,
        )
        await table.handle_mouse(event_up)
        assert table.scroll_manager.state.scroll_position < current_pos

    def test_render_basic(self):
        """Test basic rendering."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        table = Table(data=data, columns=["name", "age"], width=40, height=10)
        table.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(table, width=40, height=10)
        assert isinstance(output, str)
        assert "Alice" in output
        assert "Bob" in output
        assert "name" in output
        assert "age" in output

    def test_render_with_scrollbar(self):
        """Test rendering with scrollbar."""
        # Create table with more data than viewport
        data = [{"name": f"User {i}", "age": 20 + i} for i in range(20)]
        table = Table(
            data=data, columns=["name", "age"], width=40, height=10, show_scrollbar=True
        )
        table.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(table, width=40, height=10)
        assert isinstance(output, str)
        # Scrollbar characters should be present when content is scrollable
        # The scrollbar uses box drawing characters

    def test_render_without_header(self):
        """Test rendering without header row."""
        data = [{"name": "Alice", "age": 30}]
        table = Table(data=data, columns=["name", "age"], show_header=False)
        table.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(table, width=40, height=10)
        assert isinstance(output, str)
        assert "Alice" in output
        # Header should not be shown (no "name" or "age" labels)

    def test_scroll_manager_integration(self):
        """Test ScrollManager integration."""
        data = [{"name": f"User {i}", "age": 20 + i} for i in range(20)]
        table = Table(data=data, columns=["name", "age"], height=10)

        # Viewport height = height - 4 (top border, header, separator, bottom border) = 6
        assert table.scroll_manager.state.viewport_size == 6
        assert table.scroll_manager.state.content_size == 20
        assert table.scroll_manager.state.is_scrollable

        # Update data
        new_data = [{"name": f"User {i}", "age": 20 + i} for i in range(5)]
        table.set_data(new_data)

        assert table.scroll_manager.state.content_size == 5
        assert not table.scroll_manager.state.is_scrollable

    def test_mixed_type_sorting(self):
        """Test sorting with mixed data types."""
        data = [
            {"name": "Alice", "value": 100},
            {"name": "Bob", "value": "N/A"},
            {"name": "Charlie", "value": 50},
        ]

        table = Table(data=data, columns=["name", "value"], sortable=True)

        # Should handle mixed types by converting to strings
        table.sort_by_column("value")
        # Should not crash
        assert table.sort_column == "value"

    def test_empty_columns(self):
        """Test table with no columns defined."""
        table = Table(data=[{"name": "Alice"}], columns=[])
        table.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(table, width=40, height=10)
        assert "No columns defined" in output


class TestTableClickCallbacks:
    """Tests for Table row, cell, and header click callbacks."""

    @pytest.mark.asyncio
    async def test_on_row_click_callback(self):
        """Test on_row_click callback is invoked on row click."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        table = Table(data=data, columns=["name", "age"], width=40, height=10)
        table.set_bounds(Bounds(0, 0, 40, 10))

        callback_calls = []

        def on_row_click(row_index, row_data):
            callback_calls.append((row_index, row_data))

        table.on_row_click = on_row_click

        # Click on first data row (row index 3 = top border + header + separator)
        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=3)
        result = await table.handle_mouse(event)

        assert result is True
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 0  # First row
        assert callback_calls[0][1]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_on_row_double_click_callback(self):
        """Test on_row_double_click callback is invoked on row double-click."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        table = Table(data=data, columns=["name", "age"], width=40, height=10)
        table.set_bounds(Bounds(0, 0, 40, 10))

        callback_calls = []

        def on_row_double_click(row_index, row_data):
            callback_calls.append((row_index, row_data))

        table.on_row_double_click = on_row_double_click

        # Double-click on first data row
        event = MouseEvent(
            type=MouseEventType.DOUBLE_CLICK, button=MouseButton.LEFT, x=5, y=3
        )
        result = await table.handle_mouse(event)

        assert result is True
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 0

    @pytest.mark.asyncio
    async def test_on_cell_click_callback(self):
        """Test on_cell_click callback is invoked on cell click."""
        data = [
            {"name": "Alice", "age": 30},
        ]
        table = Table(data=data, columns=["name", "age"], width=40, height=10)
        table.set_bounds(Bounds(0, 0, 40, 10))

        callback_calls = []

        def on_cell_click(row_index, column_key, cell_value):
            callback_calls.append((row_index, column_key, cell_value))

        table.on_cell_click = on_cell_click

        # Click on first data row
        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=3)
        await table.handle_mouse(event)

        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 0  # First row

    @pytest.mark.asyncio
    async def test_on_header_click_callback(self):
        """Test on_header_click callback is invoked on header click."""
        data = [{"name": "Alice", "age": 30}]
        table = Table(data=data, columns=["name", "age"], width=40, height=10)
        table.set_bounds(Bounds(0, 0, 40, 10))

        callback_calls = []

        def on_header_click(column_key):
            callback_calls.append(column_key)

        table.on_header_click = on_header_click

        # Click on header row (row 1)
        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=1)
        result = await table.handle_mouse(event)

        assert result is True
        assert len(callback_calls) == 1

    @pytest.mark.asyncio
    async def test_on_header_click_triggers_sort_when_sortable(self):
        """Test header click triggers sort when sortable is True."""
        data = [
            {"name": "Charlie", "age": 35},
            {"name": "Alice", "age": 30},
        ]
        table = Table(
            data=data, columns=["name", "age"], width=40, height=10, sortable=True
        )
        table.set_bounds(Bounds(0, 0, 40, 10))

        header_clicks = []
        table.on_header_click = lambda col: header_clicks.append(col)

        # Click on header
        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=1)
        await table.handle_mouse(event)

        assert len(header_clicks) == 1
        # Sort should have been applied
        assert table.sort_column is not None

    def test_callbacks_default_to_none(self):
        """Test that click callbacks default to None."""
        table = Table(columns=["name", "age"])

        assert table.on_row_click is None
        assert table.on_row_double_click is None
        assert table.on_cell_click is None
        assert table.on_header_click is None


class TestColumnHitTesting:
    """Regression tests for header/cell click hit-testing (column mapping).

    Rich sizes table columns to their content, so columns are seldom equal
    width. A prior bug used an equal-width estimate to map an x-position to a
    column, so clicking a wide column's header could sort a different (narrow)
    column. The fix captures the real column boundaries from the rendered top
    border each frame; these tests pin the mapping to the rendered layout.
    """

    # Deliberately unequal content widths: a wide first column followed by two
    # narrow ones - the case an equal-width estimate gets wrong.
    UNEQUAL_DATA = [
        {"name": "Alexander the Great", "x": "1", "y": "9"},
        {"name": "Bo", "x": "2", "y": "8"},
    ]
    COLUMNS = ["name", "x", "y"]

    def _render(self, table: Table, width: int) -> None:
        """Render the table so its column boundaries get captured."""
        table.set_bounds(Bounds(0, 0, width, table.height))
        render_element(table, width=width, height=table.height)

    def test_boundaries_match_rendered_top_border(self):
        """Captured boundaries equal the junctions in the rendered top border."""
        table = Table(data=self.UNEQUAL_DATA, columns=self.COLUMNS, width=50, height=8)
        self._render(table, 50)

        output = render_element(table, width=50, height=8)
        top = output.split("\n")[0]
        junctions = [i for i, ch in enumerate(top) if ch in "┌┬┐╔╦╗╭╮┏┳┓+"]

        assert table._column_boundaries == junctions
        # One boundary per column edge: left border, 2 junctions, right border.
        assert len(table._column_boundaries) == len(self.COLUMNS) + 1

    def test_midpoint_of_each_column_maps_to_that_column(self):
        """The visual center of every column maps back to that column's key."""
        table = Table(data=self.UNEQUAL_DATA, columns=self.COLUMNS, width=50, height=8)
        self._render(table, 50)

        bounds = table._column_boundaries
        for i, key in enumerate(self.COLUMNS):
            midpoint = (bounds[i] + bounds[i + 1]) // 2
            assert table._get_column_at_x(midpoint) == key, (
                f"column {key!r} center x={midpoint} mapped to "
                f"{table._get_column_at_x(midpoint)!r}"
            )

    def test_equal_width_estimate_would_mismap(self):
        """Guard: confirm the scenario actually defeats an equal-width guess.

        Without the rendered boundaries the old estimate mislabels at least one
        column center, so this regression test is exercising a real difference
        (not a layout that happens to be equal-width anyway).
        """
        table = Table(data=self.UNEQUAL_DATA, columns=self.COLUMNS, width=50, height=8)
        self._render(table, 50)

        real = table._column_boundaries
        midpoints = [(real[i] + real[i + 1]) // 2 for i in range(len(self.COLUMNS))]

        # Temporarily clear the captured boundaries to force the fallback.
        table._column_boundaries = []
        fallback = [table._get_column_at_x(mx) for mx in midpoints]
        assert fallback != self.COLUMNS  # equal-width guess gets it wrong

    @pytest.mark.asyncio
    async def test_header_click_sorts_visually_correct_column(self):
        """End-to-end: clicking a column header sorts that column, not another."""
        table = Table(
            data=self.UNEQUAL_DATA,
            columns=self.COLUMNS,
            width=50,
            height=8,
            sortable=True,
        )
        self._render(table, 50)

        bounds = table._column_boundaries
        # Click the center of the last ("y") column header row (relative_y == 1).
        last = len(self.COLUMNS) - 1
        midpoint = (bounds[last] + bounds[last + 1]) // 2
        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.LEFT, x=midpoint, y=1
        )
        await table.handle_mouse(event)

        assert table.sort_column == "y"


class TestScrollbarFocusColor:
    """Regression tests for the table scrollbar changing color on focus.

    The scrollbar previously resolved ``table.scrollbar`` / ``table.scrollbar:
    focus`` style classes that no theme defines, so it was always unstyled and
    never changed on focus. It now resolves the shared ``scrollbar.thumb`` /
    ``scrollbar.track`` classes (focus-aware) that frames use, so a focused
    table's scrollbar picks up the focus accent color.
    """

    THUMB = "█"  # full block glyph used for the scrollbar thumb

    def _scrollbar_cells(self, focused: bool):
        """Render a scrollable table and return its scrollbar-column cells."""
        from wijjit.layout.bounds import Bounds
        from wijjit.rendering.paint_context import PaintContext
        from wijjit.styling.resolver import StyleResolver
        from wijjit.styling.theme import DefaultTheme
        from wijjit.terminal.screen_buffer import ScreenBuffer

        data = [{"n": f"row{i}", "v": str(i)} for i in range(30)]
        table = Table(data=data, columns=["n", "v"], width=24, height=10)
        table.focused = focused
        table.set_bounds(Bounds(0, 0, 24, 10))
        assert table.scroll_manager.state.is_scrollable  # precondition

        buffer = ScreenBuffer(width=30, height=10)
        ctx = PaintContext(buffer, StyleResolver(DefaultTheme()), Bounds(0, 0, 24, 10))
        table.render_to(ctx)
        # Scrollbar occupies the rightmost in-table column (table_width - 1).
        return [buffer.get_cell(23, y) for y in range(10)]

    def test_scrollbar_thumb_is_styled_when_unfocused(self):
        """Unfocused scrollbar thumb still carries the base (non-None) color."""
        cells = self._scrollbar_cells(focused=False)
        thumbs = [c for c in cells if c.char == self.THUMB]
        assert thumbs, "no scrollbar thumb rendered"
        assert all(c.fg_color is not None for c in thumbs)

    def test_scrollbar_thumb_color_changes_on_focus(self):
        """Focusing the table recolors the scrollbar thumb (focus accent)."""
        unfocused = self._scrollbar_cells(focused=False)
        focused = self._scrollbar_cells(focused=True)

        unfocused_thumb = next(c for c in unfocused if c.char == self.THUMB)
        focused_thumb = next(c for c in focused if c.char == self.THUMB)

        assert focused_thumb.fg_color is not None
        assert focused_thumb.fg_color != unfocused_thumb.fg_color, (
            "scrollbar thumb color did not change on focus: "
            f"{unfocused_thumb.fg_color} -> {focused_thumb.fg_color}"
        )


class TestTableSortOrder:
    """Sorting columns with None, missing keys, and mixed types.

    The old sort fell back to ``str()`` for the whole column on the first
    TypeError, so one None or one "n/a" turned numeric order into string
    order ([10, 100, 2, 9, None]).
    """

    @staticmethod
    def _sorted_values(rows, column="v", clicks=1):
        table = Table(data=rows, columns=["id", column], sortable=True)
        for _ in range(clicks):
            table.sort_by_column(column)
        return [row.get(column, "<missing>") for row in table.data]

    def test_ints_with_none_sort_numerically_none_last(self):
        rows = [{"v": v} for v in [10, None, 2, 100, 9]]
        assert self._sorted_values(rows) == [2, 9, 10, 100, None]
        assert self._sorted_values(rows, clicks=2) == [100, 10, 9, 2, None]

    def test_missing_key_sorts_last_both_directions(self):
        rows = [{"v": 10}, {"id": 1}, {"v": 2}, {"v": 9}]
        assert self._sorted_values(rows) == [2, 9, 10, "<missing>"]
        assert self._sorted_values(rows, clicks=2) == [10, 9, 2, "<missing>"]

    def test_numbers_before_strings_each_group_ordered(self):
        rows = [{"v": v} for v in [10, "n/a", 2, "abc", 9]]
        assert self._sorted_values(rows) == [2, 9, 10, "abc", "n/a"]
        # Descending is the mirror image: strings first.
        assert self._sorted_values(rows, clicks=2) == ["n/a", "abc", 10, 9, 2]

    def test_mixed_types_with_none_keep_none_last_descending(self):
        rows = [{"v": v} for v in [None, 1, "a", 3]]
        assert self._sorted_values(rows) == [1, 3, "a", None]
        assert self._sorted_values(rows, clicks=2) == ["a", 3, 1, None]

    def test_numeric_looking_strings_stay_strings(self):
        rows = [{"v": v} for v in ["10", 3, "2"]]
        assert self._sorted_values(rows) == [3, "10", "2"]

    def test_bool_int_float_share_one_rank(self):
        rows = [{"v": v} for v in [2.5, True, 0, 1.5, None]]
        assert self._sorted_values(rows) == [0, True, 1.5, 2.5, None]

    def test_nan_sorts_like_none(self):
        rows = [{"v": v} for v in [3.0, float("nan"), 1.0]]
        values = self._sorted_values(rows)
        assert values[:2] == [1.0, 3.0]
        assert values[2] != values[2]  # NaN

    def test_other_types_sorted_after_strings(self):
        import datetime as dt

        d1, d2 = dt.date(2024, 1, 2), dt.date(2023, 5, 6)
        rows = [{"v": v} for v in [d1, "x", 1, d2, None]]
        assert self._sorted_values(rows) == [1, "x", d2, d1, None]

    def test_ties_keep_original_order_regardless_of_history(self):
        rows = [
            {"id": "a", "v": 1, "w": 3},
            {"id": "b", "v": 0, "w": 2},
            {"id": "c", "v": 1, "w": 1},
            {"id": "d", "v": 0, "w": 0},
        ]
        table = Table(data=rows, columns=["id", "v", "w"], sortable=True)
        table.sort_by_column("w")  # shuffle the working copy first
        table.sort_by_column("v")
        assert [r["id"] for r in table.data] == ["b", "d", "a", "c"]
        table.sort_by_column("v")  # descending: ties still in original order
        assert [r["id"] for r in table.data] == ["a", "c", "b", "d"]

    def test_reassigning_data_resorts_from_new_raw_rows(self):
        table = Table(data=[{"v": 2}, {"v": 1}], columns=["v"], sortable=True)
        table.sort_by_column("v")
        table.data = [{"v": None}, {"v": 3}, {"v": 1}]
        assert [r["v"] for r in table.data] == [1, 3, None]

    def test_sort_does_not_mutate_raw_data(self):
        rows = [{"v": 3}, {"v": 1}, {"v": 2}]
        table = Table(data=rows, columns=["v"], sortable=True)
        table.sort_by_column("v")
        assert [r["v"] for r in rows] == [3, 1, 2]
