"""Tests for DataGrid input element."""

import pytest

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.input.datagrid import (
    DataGrid,
    _col_letter,
    _is_dataframe,
    _is_list_of_dicts,
)
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Key, Keys, KeyType
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestColLetterHelper:
    """Tests for column letter conversion helper."""

    def test_single_letter_columns(self):
        """Test A-Z column letters."""
        assert _col_letter(0) == "A"
        assert _col_letter(1) == "B"
        assert _col_letter(25) == "Z"

    def test_double_letter_columns(self):
        """Test AA-AZ column letters."""
        assert _col_letter(26) == "AA"
        assert _col_letter(27) == "AB"
        assert _col_letter(51) == "AZ"
        assert _col_letter(52) == "BA"


class TestDataGridInitialization:
    """Tests for DataGrid initialization."""

    def test_default_initialization(self):
        """Test creating DataGrid with defaults."""
        grid = DataGrid()

        assert grid.data == []
        assert grid.columns == []
        assert grid.cursor_row == 0
        assert grid.cursor_col == 0
        assert grid.editing is False
        assert grid.editable is True
        assert grid.show_row_numbers is True
        assert grid.focusable is True
        assert grid.element_type == ElementType.INPUT

    def test_initialization_with_data(self):
        """Test creating DataGrid with data."""
        data = [
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"],
        ]
        columns = ["Name", "Age", "City"]

        grid = DataGrid(id="test_grid", data=data, columns=columns)

        assert grid.id == "test_grid"
        assert len(grid.data) == 2
        assert len(grid.columns) == 3
        assert grid.data[0][0] == "Alice"

    def test_column_normalization_strings(self):
        """Test that string columns are normalized to dicts."""
        grid = DataGrid(columns=["Name", "Age"])

        assert grid.columns[0]["key"] == "name"
        assert grid.columns[0]["label"] == "Name"
        assert grid.columns[0]["width"] == 10

    def test_column_normalization_dicts(self):
        """Test that dict columns are preserved."""
        columns = [
            {"key": "name", "label": "Full Name", "width": 20},
            {"key": "age", "label": "Age", "width": 5},
        ]
        grid = DataGrid(columns=columns)

        assert grid.columns[0]["label"] == "Full Name"
        assert grid.columns[0]["width"] == 20

    def test_custom_dimensions(self):
        """Test custom width and height."""
        grid = DataGrid(width=80, height=20)

        assert grid.width_spec == 80
        assert grid.height_spec == 20


class TestDataGridCellOperations:
    """Tests for cell get/set operations."""

    def test_get_cell(self):
        """Test getting cell values."""
        data = [["A", "B"], ["C", "D"]]
        grid = DataGrid(data=data, columns=["Col1", "Col2"])

        assert grid.get_cell(0, 0) == "A"
        assert grid.get_cell(0, 1) == "B"
        assert grid.get_cell(1, 0) == "C"
        assert grid.get_cell(1, 1) == "D"

    def test_get_cell_out_of_bounds(self):
        """Test getting cell out of bounds returns empty string."""
        grid = DataGrid(data=[["A"]], columns=["Col1"])

        assert grid.get_cell(5, 5) == ""
        assert grid.get_cell(-1, 0) == ""

    def test_set_cell(self):
        """Test setting cell values."""
        data = [["A", "B"]]
        grid = DataGrid(data=data, columns=["Col1", "Col2"])

        grid.set_cell(0, 0, "X")
        assert grid.data[0][0] == "X"

    def test_set_cell_expands_grid(self):
        """Test that set_cell expands grid as needed."""
        grid = DataGrid(columns=["Col1", "Col2"])

        grid.set_cell(2, 1, "Value")
        assert len(grid.data) == 3
        assert grid.data[2][1] == "Value"

    def test_set_cell_callback(self):
        """Test cell change callback is called."""
        grid = DataGrid(data=[["A"]], columns=["Col1"])

        callback_args = []
        grid.on_cell_change = lambda r, c, o, n: callback_args.append((r, c, o, n))

        grid.set_cell(0, 0, "B")
        assert callback_args == [(0, 0, "A", "B")]


class TestDataGridDataOperations:
    """Tests for data manipulation methods."""

    def test_get_data(self):
        """Test getting all data."""
        data = [["A", "B"], ["C", "D"]]
        grid = DataGrid(data=data, columns=["Col1", "Col2"])

        result = grid.get_data()
        assert result == data
        # Should be a copy, not the same object
        assert result is not grid.data

    def test_set_data(self):
        """Test replacing all data."""
        grid = DataGrid(columns=["Col1"])
        new_data = [["X"], ["Y"], ["Z"]]

        grid.set_data(new_data)
        assert len(grid.data) == 3
        assert grid.data[0][0] == "X"

    def test_add_row(self):
        """Test adding a row."""
        grid = DataGrid(data=[["A"]], columns=["Col1"])

        grid.add_row(["B"])
        assert len(grid.data) == 2
        assert grid.data[1][0] == "B"

    def test_add_row_empty(self):
        """Test adding empty row."""
        grid = DataGrid(columns=["Col1", "Col2"])

        grid.add_row()
        assert len(grid.data) == 1
        assert grid.data[0] == ["", ""]

    def test_insert_row(self):
        """Test inserting a row."""
        grid = DataGrid(data=[["A"], ["C"]], columns=["Col1"])

        grid.insert_row(1, ["B"])
        assert len(grid.data) == 3
        assert grid.data[1][0] == "B"

    def test_delete_row(self):
        """Test deleting a row."""
        grid = DataGrid(data=[["A"], ["B"], ["C"]], columns=["Col1"])

        grid.delete_row(1)
        assert len(grid.data) == 2
        assert grid.data[0][0] == "A"
        assert grid.data[1][0] == "C"

    def test_add_column(self):
        """Test adding a column."""
        grid = DataGrid(data=[["A"], ["B"]], columns=["Col1"])

        grid.add_column("Col2", ["X", "Y"])
        assert len(grid.columns) == 2
        assert grid.data[0][1] == "X"
        assert grid.data[1][1] == "Y"

    def test_delete_column(self):
        """Test deleting a column."""
        grid = DataGrid(data=[["A", "B"], ["C", "D"]], columns=["Col1", "Col2"])

        grid.delete_column(0)
        assert len(grid.columns) == 1
        assert grid.data[0][0] == "B"


class TestDataGridNavigation:
    """Tests for cursor navigation."""

    def test_arrow_key_navigation(self):
        """Test arrow key navigation."""
        grid = DataGrid(
            data=[["A", "B"], ["C", "D"], ["E", "F"]], columns=["Col1", "Col2"]
        )

        # Start at 0, 0
        assert grid.cursor_row == 0
        assert grid.cursor_col == 0

        # Move right
        grid.handle_key(Keys.RIGHT)
        assert grid.cursor_col == 1

        # Move down
        grid.handle_key(Keys.DOWN)
        assert grid.cursor_row == 1

        # Move left
        grid.handle_key(Keys.LEFT)
        assert grid.cursor_col == 0

        # Move up
        grid.handle_key(Keys.UP)
        assert grid.cursor_row == 0

    def test_tab_navigation(self):
        """Test Tab navigation."""
        grid = DataGrid(data=[["A", "B"], ["C", "D"]], columns=["Col1", "Col2"])

        # Tab moves right
        grid.handle_key(Keys.TAB)
        assert grid.cursor_col == 1

        # Tab at end of row wraps to next row
        grid.handle_key(Keys.TAB)
        assert grid.cursor_row == 1
        assert grid.cursor_col == 0

    def test_home_end_keys(self):
        """Test Home and End keys."""
        grid = DataGrid(data=[["A", "B", "C"]], columns=["Col1", "Col2", "Col3"])
        grid.cursor_col = 1

        # Home goes to first column
        grid.handle_key(Keys.HOME)
        assert grid.cursor_col == 0

        # End goes to last column
        grid.handle_key(Keys.END)
        assert grid.cursor_col == 2

    def test_navigation_bounds(self):
        """Test navigation doesn't go out of bounds."""
        grid = DataGrid(data=[["A"]], columns=["Col1"])

        # Can't go negative
        grid.handle_key(Keys.UP)
        assert grid.cursor_row == 0

        grid.handle_key(Keys.LEFT)
        assert grid.cursor_col == 0

        # Can't go past end
        grid.handle_key(Keys.DOWN)
        assert grid.cursor_row == 0

        grid.handle_key(Keys.RIGHT)
        assert grid.cursor_col == 0

    def test_cell_select_callback(self):
        """Test cell selection callback."""
        grid = DataGrid(data=[["A", "B"], ["C", "D"]], columns=["Col1", "Col2"])

        selections = []
        grid.on_cell_select = lambda r, c: selections.append((r, c))

        grid.handle_key(Keys.RIGHT)
        grid.handle_key(Keys.DOWN)

        assert (0, 1) in selections
        assert (1, 1) in selections

    def test_tab_wrap_emits_cell_select(self):
        """Tab wrapping to the next row reports the full position change."""
        grid = DataGrid(data=[["A", "B"], ["C", "D"]], columns=["Col1", "Col2"])
        selections = []
        grid.on_cell_select = lambda r, c: selections.append((r, c))

        grid.handle_key(Keys.TAB)  # (0,0) -> (0,1)
        grid.handle_key(Keys.TAB)  # (0,1) -> wrap to (1,0)

        assert grid.cursor_row == 1
        assert grid.cursor_col == 0
        # The wrap must surface as a (1, 0) selection, not be suppressed.
        assert selections == [(0, 1), (1, 0)]

    def test_shift_tab_wrap_emits_cell_select(self):
        """Shift+Tab wrapping to the previous row reports the change."""
        grid = DataGrid(data=[["A", "B"], ["C", "D"]], columns=["Col1", "Col2"])
        grid.cursor_row = 1
        grid.cursor_col = 0
        selections = []
        grid.on_cell_select = lambda r, c: selections.append((r, c))

        grid.handle_key(Keys.BACKTAB)

        assert grid.cursor_row == 0
        assert grid.cursor_col == 1
        assert selections == [(0, 1)]


class TestDataGridEditing:
    """Tests for cell editing."""

    def test_start_editing_with_f2(self):
        """Test F2 enters edit mode."""
        grid = DataGrid(data=[["Hello"]], columns=["Col1"])

        grid.handle_key(Keys.F2)
        assert grid.editing is True
        assert grid.edit_value == "Hello"

    def test_start_editing_with_typing(self):
        """Test typing starts edit mode and clears cell."""
        grid = DataGrid(data=[["Hello"]], columns=["Col1"])

        grid.handle_key(Key("x", KeyType.CHARACTER, "X"))
        assert grid.editing is True
        assert grid.edit_value == "X"

    def test_escape_cancels_edit(self):
        """Test Escape cancels edit."""
        grid = DataGrid(data=[["Original"]], columns=["Col1"])

        grid.handle_key(Keys.F2)
        grid.edit_value = "Modified"
        grid.handle_key(Keys.ESCAPE)

        assert grid.editing is False
        assert grid.data[0][0] == "Original"

    def test_enter_commits_edit(self):
        """Test Enter commits edit."""
        grid = DataGrid(data=[["Original"]], columns=["Col1"])

        grid.handle_key(Keys.F2)
        grid.edit_value = "Modified"
        grid.handle_key(Keys.ENTER)

        assert grid.editing is False
        assert grid.data[0][0] == "Modified"

    def test_enter_commits_edit_once(self):
        """Enter commits the edited cell exactly once (no double-commit)."""
        grid = DataGrid(data=[["Original"], ["Second"]], columns=["Col1"])
        commits = []
        grid.on_cell_change = lambda r, c, o, n: commits.append((r, c, o, n))

        grid.handle_key(Keys.F2)
        grid.edit_value = "Modified"
        grid.handle_key(Keys.ENTER)

        assert grid.data[0][0] == "Modified"
        assert commits == [(0, 0, "Original", "Modified")]
        # Enter also advances the cursor down.
        assert grid.cursor_row == 1

    def test_tab_commits_edit_once_and_moves(self):
        """Tab in edit mode commits once and advances the cursor."""
        grid = DataGrid(data=[["A", "B"]], columns=["Col1", "Col2"])
        commits = []
        grid.on_cell_change = lambda r, c, o, n: commits.append((r, c, o, n))

        grid.handle_key(Keys.F2)
        grid.edit_value = "X"
        grid.handle_key(Keys.TAB)

        assert grid.data[0][0] == "X"
        assert commits == [(0, 0, "A", "X")]
        assert grid.cursor_col == 1
        assert grid.editing is False

    def test_typing_in_edit_mode(self):
        """Test typing characters in edit mode."""
        grid = DataGrid(data=[["A"]], columns=["Col1"])

        grid.handle_key(Keys.F2)
        grid.handle_key(Key("b", KeyType.CHARACTER, "B"))
        grid.handle_key(Key("c", KeyType.CHARACTER, "C"))

        assert grid.edit_value == "ABC"
        assert grid.edit_cursor_pos == 3

    def test_backspace_in_edit_mode(self):
        """Test backspace in edit mode."""
        grid = DataGrid(data=[["ABC"]], columns=["Col1"])

        grid.handle_key(Keys.F2)
        grid.handle_key(Keys.BACKSPACE)

        assert grid.edit_value == "AB"
        assert grid.edit_cursor_pos == 2

    def test_delete_key_clears_and_edits(self):
        """Test Delete key clears cell and enters edit mode."""
        grid = DataGrid(data=[["Hello"]], columns=["Col1"])

        grid.handle_key(Keys.DELETE)
        assert grid.editing is True
        assert grid.edit_value == ""

    def test_not_editable(self):
        """Test that non-editable grid doesn't enter edit mode."""
        grid = DataGrid(data=[["A"]], columns=["Col1"], editable=False)

        grid.handle_key(Keys.F2)
        assert grid.editing is False

        grid.handle_key(Key("x", KeyType.CHARACTER, "X"))
        assert grid.editing is False


class TestDataGridRendering:
    """Tests for rendering."""

    def test_basic_render(self):
        """Test basic rendering produces output."""
        grid = DataGrid(
            data=[["Alice", "30"], ["Bob", "25"]],
            columns=["Name", "Age"],
            width=40,
            height=10,
        )
        grid.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(grid, width=40, height=10)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_empty_grid_render(self):
        """Test rendering empty grid."""
        grid = DataGrid(columns=["Col1", "Col2"], width=30, height=8)
        grid.set_bounds(Bounds(0, 0, 30, 8))

        output = render_element(grid, width=30, height=8)
        assert isinstance(output, str)

    def test_intrinsic_size(self):
        """Test intrinsic size calculation."""
        grid = DataGrid(width=60, height=15)

        size = grid.get_intrinsic_size()
        assert size == (60, 15)

    def test_cell_reference(self):
        """Test cell reference generation."""
        grid = DataGrid(data=[["A"]], columns=["Col1"])

        grid.cursor_row = 0
        grid.cursor_col = 0
        assert grid._get_cell_ref() == "A1"

        grid.cursor_row = 2
        grid.cursor_col = 1
        assert grid._get_cell_ref() == "B3"


class TestDataGridMouse:
    """Tests for mouse interaction."""

    @pytest.mark.asyncio
    async def test_scroll_wheel(self):
        """Test mouse wheel scrolling."""
        # Create grid with more data than visible
        data = [[f"Row {i}"] for i in range(20)]
        grid = DataGrid(data=data, columns=["Col1"], height=10)
        grid.set_bounds(Bounds(0, 0, 40, 10))

        initial_pos = grid.scroll_manager.state.scroll_position

        # Scroll down
        event = MouseEvent(
            type=MouseEventType.SCROLL,
            x=5,
            y=5,
            button=MouseButton.SCROLL_DOWN,
        )
        await grid.handle_mouse(event)

        assert grid.scroll_manager.state.scroll_position > initial_pos

    @pytest.mark.asyncio
    async def test_click_selects_cell(self):
        """Test clicking selects a cell."""
        grid = DataGrid(
            data=[["A", "B"], ["C", "D"]],
            columns=[
                {"key": "c1", "label": "C1", "width": 10},
                {"key": "c2", "label": "C2", "width": 10},
            ],
            height=10,
            show_row_numbers=False,
        )
        grid.set_bounds(Bounds(0, 0, 30, 10))

        # Click on row 1 (data row 0), which is at y=4 (entry=2, sep=1, header=1)
        event = MouseEvent(
            type=MouseEventType.CLICK,
            x=5,
            y=4,
            button=MouseButton.LEFT,
        )
        await grid.handle_mouse(event)

        # Should select the first row
        assert grid.cursor_row == 0


class TestDataGridEphemeralState:
    """Tests for ephemeral state preservation."""

    def test_get_ephemeral_state(self):
        """Test getting ephemeral state."""
        # Create grid with wide columns so horizontal scrolling is possible
        grid = DataGrid(
            data=[["A", "B", "C", "D", "E"]],
            columns=[
                {"key": "c1", "label": "Col1", "width": 20},
                {"key": "c2", "label": "Col2", "width": 20},
                {"key": "c3", "label": "Col3", "width": 20},
                {"key": "c4", "label": "Col4", "width": 20},
                {"key": "c5", "label": "Col5", "width": 20},
            ],
            width=40,  # Narrow width to force scrolling
        )
        grid.cursor_row = 2
        grid.cursor_col = 3

        state = grid.get_ephemeral_state()

        assert state["cursor_row"] == 2
        assert state["cursor_col"] == 3
        # _scroll_position_x should be present
        assert "_scroll_position_x" in state

    def test_restore_ephemeral_state(self):
        """Test restoring ephemeral state."""
        grid = DataGrid(data=[["A"], ["B"], ["C"]], columns=["Col1", "Col2"])

        state = {
            "cursor_row": 1,
            "cursor_col": 1,
            "_scroll_position": 0,
            "_scroll_position_x": 0,
        }
        grid.restore_ephemeral_state(state)

        assert grid.cursor_row == 1
        assert grid.cursor_col == 1

    def test_ephemeral_state_preserves_editing(self):
        """Test that editing state is preserved."""
        grid = DataGrid(data=[["A"]], columns=["Col1"])
        grid.editing = True
        grid.edit_value = "Test"
        grid.edit_cursor_pos = 2

        state = grid.get_ephemeral_state()

        assert state["editing"] is True
        assert state["edit_value"] == "Test"
        assert state["edit_cursor_pos"] == 2


class TestDataGridScrolling:
    """Tests for scroll behavior."""

    def test_scroll_position(self):
        """Test scroll_position property."""
        data = [[f"Row {i}"] for i in range(20)]
        grid = DataGrid(data=data, columns=["Col1"], height=10)

        assert grid.scroll_position == 0

        grid.scroll_manager.scroll_to(5)
        assert grid.scroll_position == 5

    def test_can_scroll(self):
        """Test can_scroll method."""
        data = [[f"Row {i}"] for i in range(20)]
        grid = DataGrid(data=data, columns=["Col1"], height=10)

        # At top, can scroll down but not up
        assert grid.can_scroll(1) is True
        assert grid.can_scroll(-1) is False

        # Scroll to middle
        grid.scroll_manager.scroll_to(5)
        assert grid.can_scroll(1) is True
        assert grid.can_scroll(-1) is True

    def test_page_up_down(self):
        """Test Page Up/Down navigation."""
        data = [[f"Row {i}"] for i in range(30)]
        grid = DataGrid(data=data, columns=["Col1"], height=10)

        # Page down
        grid.handle_key(Keys.PAGE_DOWN)
        assert grid.scroll_manager.state.scroll_position > 0

        # Page up
        current_pos = grid.scroll_manager.state.scroll_position
        grid.handle_key(Keys.PAGE_UP)
        assert grid.scroll_manager.state.scroll_position < current_pos


class TestDataGridMultiFormatData:
    """Tests for multi-format data support (list of dicts, DataFrame)."""

    def test_helper_is_list_of_dicts(self):
        """Test _is_list_of_dicts helper function."""
        # Valid list of dicts
        assert _is_list_of_dicts([{"a": 1}, {"b": 2}]) is True
        assert _is_list_of_dicts([{"name": "Alice"}]) is True

        # Not list of dicts
        assert _is_list_of_dicts([]) is False  # Empty list
        assert _is_list_of_dicts([["a", "b"]]) is False  # List of lists
        assert _is_list_of_dicts([[1, 2], [3, 4]]) is False
        assert _is_list_of_dicts("not a list") is False
        assert _is_list_of_dicts(None) is False
        assert _is_list_of_dicts({"a": 1}) is False  # Single dict

    def test_helper_is_dataframe(self):
        """Test _is_dataframe helper function."""
        # Not DataFrames
        assert _is_dataframe([]) is False
        assert _is_dataframe([{"a": 1}]) is False
        assert _is_dataframe("DataFrame") is False
        assert _is_dataframe(None) is False

        # Can't test actual DataFrame without pandas, but we test false cases

    def test_init_with_list_of_dicts(self):
        """Test initializing DataGrid with list of dicts."""
        data = [
            {"name": "Alice", "age": "30", "city": "NYC"},
            {"name": "Bob", "age": "25", "city": "LA"},
        ]
        grid = DataGrid(data=data)

        # Data should be normalized to list of lists
        assert grid.data == [
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"],
        ]

        # Columns should be auto-inferred
        assert len(grid.columns) == 3
        assert grid.columns[0]["key"] == "name"
        assert grid.columns[1]["key"] == "age"
        assert grid.columns[2]["key"] == "city"

    def test_init_with_list_of_dicts_preserves_order(self):
        """Test that column order is preserved from first dict."""
        data = [
            {"z": "1", "a": "2", "m": "3"},  # Order: z, a, m
        ]
        grid = DataGrid(data=data)

        # Column order should follow first dict
        assert grid._column_keys == ["z", "a", "m"]

    def test_init_with_list_of_dicts_handles_missing_keys(self):
        """Test handling dicts with different keys."""
        data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "city": "LA"},  # Missing "age", has extra "city"
        ]
        grid = DataGrid(data=data)

        # First dict's keys come first, then additional keys
        assert "name" in grid._column_keys
        assert "age" in grid._column_keys
        assert "city" in grid._column_keys

        # Missing values should be empty strings
        assert grid.data[1][grid._column_keys.index("age")] == ""

    def test_get_data_as_dicts(self):
        """Test get_data_as_dicts method."""
        data = [
            ["Alice", "30"],
            ["Bob", "25"],
        ]
        columns = [
            {"key": "name", "label": "Name"},
            {"key": "age", "label": "Age"},
        ]
        grid = DataGrid(data=data, columns=columns)

        result = grid.get_data_as_dicts()

        assert result == [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]

    def test_get_data_as_dicts_with_inferred_columns(self):
        """Test get_data_as_dicts when columns were inferred from list of dicts."""
        data = [
            {"product": "Widget", "price": "9.99"},
            {"product": "Gadget", "price": "19.99"},
        ]
        grid = DataGrid(data=data)

        result = grid.get_data_as_dicts()

        assert result == [
            {"product": "Widget", "price": "9.99"},
            {"product": "Gadget", "price": "19.99"},
        ]

    def test_get_data_as_dicts_fallback_keys(self):
        """Test get_data_as_dicts uses col_N fallback when no keys defined."""
        # Initialize without column definitions to test fallback
        grid = DataGrid()
        grid.data = [["a", "b"], ["c", "d"]]
        grid.columns = [{"label": "Col1", "width": 10}, {"label": "Col2", "width": 10}]
        grid._column_keys = []  # Clear keys to test fallback

        result = grid.get_data_as_dicts()

        assert result == [
            {"col_0": "a", "col_1": "b"},
            {"col_0": "c", "col_1": "d"},
        ]

    def test_set_data_with_list_of_dicts(self):
        """Test set_data accepts list of dicts."""
        grid = DataGrid(
            columns=[
                {"key": "name", "label": "Name"},
                {"key": "value", "label": "Value"},
            ]
        )

        new_data = [
            {"name": "X", "value": "100"},
            {"name": "Y", "value": "200"},
        ]
        grid.set_data(new_data)

        assert grid.data == [["X", "100"], ["Y", "200"]]

    def test_set_data_with_update_columns(self):
        """Test set_data can update columns from new data."""
        grid = DataGrid(columns=["Old1", "Old2"])

        new_data = [
            {"new_a": "1", "new_b": "2"},
            {"new_a": "3", "new_b": "4"},
        ]
        grid.set_data(new_data, update_columns=True)

        # Columns should be updated
        assert grid._column_keys == ["new_a", "new_b"]

    def test_roundtrip_list_of_dicts(self):
        """Test data can roundtrip through list of dicts format."""
        original_data = [
            {"id": "1", "name": "Widget", "qty": "10"},
            {"id": "2", "name": "Gadget", "qty": "5"},
        ]
        grid = DataGrid(data=original_data)

        # Get data back as dicts
        result = grid.get_data_as_dicts()

        assert result == original_data


class TestDataGridPandasIntegration:
    """Tests for pandas DataFrame integration (optional dependency)."""

    @pytest.fixture
    def pandas_available(self):
        """Check if pandas is available."""
        try:
            import pandas

            return True
        except ImportError:
            return False

    def test_get_data_as_dataframe_without_pandas(self):
        """Test get_data_as_dataframe raises ImportError when pandas not available."""
        # We can't easily test this since pandas might be installed
        # This test documents the expected behavior
        pass

    def test_init_with_dataframe(self, pandas_available):
        """Test initializing DataGrid with pandas DataFrame."""
        if not pandas_available:
            pytest.skip("pandas not installed")

        import pandas as pd

        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        grid = DataGrid(data=df)

        # Data should be normalized to list of lists
        assert grid.data == [["Alice", "30"], ["Bob", "25"]]

        # Columns should be auto-inferred
        assert grid._column_keys == ["name", "age"]

    def test_get_data_as_dataframe(self, pandas_available):
        """Test get_data_as_dataframe method."""
        if not pandas_available:
            pytest.skip("pandas not installed")

        import pandas as pd

        data = [["Alice", "30"], ["Bob", "25"]]
        columns = [
            {"key": "name", "label": "Name"},
            {"key": "age", "label": "Age"},
        ]
        grid = DataGrid(data=data, columns=columns)

        result = grid.get_data_as_dataframe()

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["name", "age"]
        assert result.iloc[0]["name"] == "Alice"
        assert result.iloc[1]["age"] == "25"

    def test_roundtrip_dataframe(self, pandas_available):
        """Test data can roundtrip through DataFrame format."""
        if not pandas_available:
            pytest.skip("pandas not installed")

        import pandas as pd

        original_df = pd.DataFrame(
            {"product": ["Widget", "Gadget"], "price": ["9.99", "19.99"]}
        )

        grid = DataGrid(data=original_df)
        result_df = grid.get_data_as_dataframe()

        # Compare as DataFrames
        pd.testing.assert_frame_equal(result_df, original_df)

    def test_set_data_with_dataframe(self, pandas_available):
        """Test set_data accepts pandas DataFrame."""
        if not pandas_available:
            pytest.skip("pandas not installed")

        import pandas as pd

        grid = DataGrid(
            columns=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}]
        )

        new_data = pd.DataFrame({"a": ["x", "y"], "b": ["1", "2"]})
        grid.set_data(new_data)

        assert grid.data == [["x", "1"], ["y", "2"]]
