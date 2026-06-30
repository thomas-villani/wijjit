"""DataGrid element for spreadsheet-like data entry.

This module provides the DataGrid element for creating editable grids in terminal
user interfaces. Inspired by classic TUI spreadsheets (VisiCalc, Lotus 1-2-3),
it uses an "entry line" pattern for editing rather than inline cell editing.

The DataGrid supports multiple input formats:
- List of lists (native format)
- List of dicts (auto-infers columns from keys)
- pandas DataFrame (optional, auto-infers columns)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from wijjit.elements.base import ElementType, ScrollableElement, invoke_callback
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.layout.scroll import (
    ScrollManager,
    render_horizontal_scrollbar,
    render_vertical_scrollbar,
)
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext

# Type alias for supported data formats
DataInput = list[list[str]] | list[dict[str, Any]] | Any  # Native format: list of lists


def _is_dataframe(obj: Any) -> bool:
    """Check if object is a pandas DataFrame without importing pandas.

    Parameters
    ----------
    obj : Any
        Object to check

    Returns
    -------
    bool
        True if obj is a pandas DataFrame
    """
    # Check by class name to avoid importing pandas
    return type(obj).__name__ == "DataFrame" and hasattr(obj, "iterrows")


def _is_list_of_dicts(obj: Any) -> bool:
    """Check if object is a list of dicts.

    Parameters
    ----------
    obj : Any
        Object to check

    Returns
    -------
    bool
        True if obj is a non-empty list where first element is a dict
    """
    return isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict)


def _col_letter(col: int) -> str:
    """Convert column index to letter (A, B, C, ... Z, AA, AB, ...).

    Parameters
    ----------
    col : int
        Column index (0-based)

    Returns
    -------
    str
        Column letter(s)
    """
    result = ""
    col += 1  # Convert to 1-based for calculation
    while col > 0:
        col -= 1
        result = chr(ord("A") + col % 26) + result
        col //= 26
    return result


class DataGrid(ScrollableElement):
    """Spreadsheet-like data entry grid with entry line editing.

    This element provides a classic TUI spreadsheet experience with a separate
    entry line at the top for editing cell contents. Navigation uses arrow keys,
    Tab, and Enter, with visual highlighting of the active cell.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    data : list of list, list of dict, or pandas DataFrame, optional
        Grid data in one of these formats:
        - List of lists: [["Alice", "30"], ["Bob", "25"]]
        - List of dicts: [{"name": "Alice", "age": 30}, ...]
        - pandas DataFrame: pd.DataFrame({"name": [...], "age": [...]})
        Columns are auto-inferred from dicts/DataFrame if not provided.
    columns : list of str or list of dict, optional
        Column definitions. Can be simple strings (headers) or dicts with:
        - "key": Column identifier
        - "label": Display header text
        - "width": Column width in characters (default: 10)
        If not provided and data is dict/DataFrame, columns are auto-inferred.
    width : int, optional
        Total display width (default: 60)
    height : int, optional
        Total display height including entry line and borders (default: 15)
    show_row_numbers : bool, optional
        Show row numbers (1, 2, 3...) on left side (default: True)
    editable : bool, optional
        Whether cells can be edited (default: True)
    border_style : BorderStyle or str, optional
        Border style for the grid (default: "single")

    Attributes
    ----------
    data : list of list of str
        Grid data as 2D list (normalized from any input format)
    columns : list of dict
        Column definitions with "key", "label", "width"
    cursor_row : int
        Currently selected row (0-indexed, data rows only)
    cursor_col : int
        Currently selected column (0-indexed)
    editing : bool
        Whether entry line is active for editing
    edit_value : str
        Current value in entry line
    edit_cursor_pos : int
        Cursor position within entry line
    scroll_manager : ScrollManager
        Manages vertical scrolling of data rows
    scroll_x : int
        Horizontal scroll offset (columns)

    Notes
    -----
    Editing Workflow:
    1. Navigate with arrow keys to highlight a cell
    2. Start typing -> content appears in entry line at top
    3. Press Enter/Tab/arrow -> commits value to cell and moves cursor
    4. Press Escape -> cancels edit, restores original value
    5. Press F2 -> edit existing cell content

    Layout Structure:
    - Entry line: 2 rows (border + content)
    - Header row: 1 row
    - Data rows: height - 4 (entry line + header + borders)

    Data Format Conversion:
    - Use `get_data()` to get list of lists
    - Use `get_data_as_dicts()` to get list of dicts
    - Use `get_data_as_dataframe()` to get pandas DataFrame (requires pandas)

    Examples
    --------
    Create with list of lists:

    >>> grid = DataGrid(
    ...     columns=["Name", "Age", "City"],
    ...     data=[["Alice", "30", "NYC"], ["Bob", "25", "LA"]]
    ... )

    Create with list of dicts (columns auto-inferred):

    >>> grid = DataGrid(data=[
    ...     {"name": "Alice", "age": 30, "city": "NYC"},
    ...     {"name": "Bob", "age": 25, "city": "LA"},
    ... ])

    Create from pandas DataFrame:

    >>> import pandas as pd
    >>> df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    >>> grid = DataGrid(data=df)

    Export back to DataFrame:

    >>> df_out = grid.get_data_as_dataframe()
    """

    # Track column keys for dict/DataFrame export
    _column_keys: list[str]

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        tab_index: int | None = None,
        data: DataInput | None = None,
        columns: list[str] | list[dict[str, Any]] | None = None,
        width: int = 60,
        height: int = 15,
        show_row_numbers: bool = True,
        editable: bool = True,
        border_style: BorderStyle | str = "single",
        show_scrollbar: bool = True,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.element_type = ElementType.INPUT
        self.focusable = True

        # Normalize data and potentially infer columns
        self.data, inferred_columns = self._normalize_data(data)
        self._column_keys: list[str] = []

        # Use inferred columns if none provided
        if columns is None and inferred_columns:
            columns = inferred_columns

        # Normalize columns
        self.columns = self._normalize_columns(columns)

        # Display properties
        self.width_spec = width
        self.height_spec = height
        self.show_row_numbers = show_row_numbers
        self.editable = editable
        self.border_style = self._normalize_border_style(border_style)
        self.show_scrollbar = show_scrollbar

        # Cursor state
        self.cursor_row = 0
        self.cursor_col = 0

        # Editing state
        self.editing = False
        self.edit_value = ""
        self.edit_cursor_pos = 0
        self._original_value = ""  # For cancel/restore

        # Vertical scroll state
        self._visible_rows = max(
            1, height - 5
        )  # Entry line(2) + header(1) + borders(2)
        self.scroll_manager = ScrollManager(
            content_size=len(self.data),
            viewport_size=self._visible_rows,
        )

        # Horizontal scroll state
        self._total_columns_width = self._calculate_total_columns_width()
        self._visible_width = self._calculate_visible_width(width)
        self.scroll_manager_x = ScrollManager(
            content_size=self._total_columns_width,
            viewport_size=self._visible_width,
        )

        # Callbacks
        self.on_cell_change: Callable[[int, int, str, str], None] | None = None
        self.on_cell_select: Callable[[int, int], None] | None = None
        self.on_data_change: Callable[[list[list[str]]], None] | None = None

        # State keys for persistence
        self._cursor_state_key_override: str | None = None

        # Template attributes
        self.bind: bool = True

    def _normalize_data(
        self, data: DataInput | None
    ) -> tuple[list[list[str]], list[str] | None]:
        """Normalize input data to list of lists format.

        Handles conversion from:
        - None -> empty list
        - List of lists -> as-is (values converted to str)
        - List of dicts -> extracted values, returns column keys
        - pandas DataFrame -> extracted values, returns column names

        Parameters
        ----------
        data : DataInput or None
            Input data in any supported format

        Returns
        -------
        tuple of (list of list of str, list of str or None)
            (normalized_data, inferred_column_names)
            inferred_column_names is None if data was list of lists
        """
        if data is None:
            return [], None

        # Check for pandas DataFrame
        if _is_dataframe(data):
            return self._convert_dataframe(data)

        # Check for list of dicts
        if _is_list_of_dicts(data):
            return self._convert_list_of_dicts(data)

        # Assume list of lists - convert values to strings
        normalized = []
        for row in data:
            if isinstance(row, (list, tuple)):
                normalized.append([str(cell) for cell in row])
            else:
                # Single value, wrap in list
                normalized.append([str(row)])
        return normalized, None

    def _convert_dataframe(self, df: Any) -> tuple[list[list[str]], list[str]]:
        """Convert pandas DataFrame to list of lists.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame to convert

        Returns
        -------
        tuple of (list of list of str, list of str)
            (data_rows, column_names)
        """
        columns = list(df.columns)
        rows = []
        for _, row in df.iterrows():
            rows.append([str(val) for val in row])
        return rows, columns

    def _convert_list_of_dicts(
        self, data: list[dict[str, Any]]
    ) -> tuple[list[list[str]], list[str]]:
        """Convert list of dicts to list of lists.

        Parameters
        ----------
        data : list of dict
            List of dictionaries

        Returns
        -------
        tuple of (list of list of str, list of str)
            (data_rows, column_keys)
        """
        # Get all unique keys preserving order from first dict
        if not data:
            return [], []

        # Use keys from first dict to maintain order
        columns = list(data[0].keys())

        # Also collect any additional keys from other dicts
        all_keys = set(columns)
        for row_dict in data[1:]:
            for key in row_dict.keys():
                if key not in all_keys:
                    columns.append(key)
                    all_keys.add(key)

        # Convert each dict to a list in column order
        rows = []
        for row_dict in data:
            row = [str(row_dict.get(key, "")) for key in columns]
            rows.append(row)

        return rows, columns

    def _normalize_border_style(self, style: BorderStyle | str) -> BorderStyle:
        """Normalize border style from string or enum.

        Parameters
        ----------
        style : BorderStyle or str
            Border style

        Returns
        -------
        BorderStyle
            Normalized border style
        """
        if isinstance(style, BorderStyle):
            return style
        style_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
            "none": BorderStyle.NONE,
        }
        return style_map.get(style.lower(), BorderStyle.SINGLE)

    def _normalize_columns(
        self, columns: list[str] | list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        """Normalize column definitions to internal format.

        Also stores column keys in self._column_keys for export methods.

        Parameters
        ----------
        columns : list of str or list of dict or None
            Column definitions

        Returns
        -------
        list of dict
            Normalized column definitions with "key", "label", "width"
        """
        if columns is None:
            self._column_keys = []
            return []

        normalized = []
        keys = []
        for i, col in enumerate(columns):
            if isinstance(col, dict):
                key = col.get("key", f"col_{i}")
                normalized.append(
                    {
                        "key": key,
                        "label": col.get("label", col.get("key", f"Col {i+1}")),
                        "width": col.get("width", 10),
                    }
                )
                keys.append(key)
            else:
                # Simple string - use as both key and label
                key = str(col).lower().replace(" ", "_")
                normalized.append(
                    {
                        "key": key,
                        "label": str(col),
                        "width": 10,
                    }
                )
                keys.append(key)

        self._column_keys = keys
        return normalized

    def _calculate_total_columns_width(self) -> int:
        """Calculate total width of all columns.

        Returns
        -------
        int
            Sum of all column widths plus separators
        """
        if not self.columns:
            return 0
        # Sum column widths + 1 separator per column
        return sum(col.get("width", 10) for col in self.columns) + len(self.columns)

    def _calculate_visible_width(self, total_width: int) -> int:
        """Calculate visible content width for horizontal scrolling.

        Parameters
        ----------
        total_width : int
            Total grid width

        Returns
        -------
        int
            Width available for column content
        """
        row_num_width = self._row_number_width() if self.show_row_numbers else 0
        # Subtract: borders(2) + row numbers + scrollbar(1 if shown)
        scrollbar_space = 1 if self.show_scrollbar else 0
        return max(1, total_width - 2 - row_num_width - scrollbar_space)

    def _update_scroll_managers(self) -> None:
        """Update scroll managers with current content sizes.

        This should be called after data or column changes to ensure
        scroll state is correct. Handles the interdependency between
        vertical and horizontal scrollbars (each affects the other's space).
        """
        # Calculate total content sizes
        total_rows = len(self.data)
        self._total_columns_width = self._calculate_total_columns_width()

        # Base viewport sizes (without scrollbars)
        # Height: entry(2) + sep(1) + header(1) + bottom border(1) = 5 rows overhead
        base_visible_rows = max(1, self.height_spec - 5)
        row_num_width = self._row_number_width() if self.show_row_numbers else 0
        base_visible_width = max(1, self.width_spec - 2 - row_num_width)

        # First pass: check if scrollbars are needed with base sizes
        needs_vscroll = self.show_scrollbar and total_rows > base_visible_rows
        needs_hscroll = (
            self.show_scrollbar and self._total_columns_width > base_visible_width
        )

        # Second pass: adjust for scrollbar space and recheck
        # If horizontal scrollbar is shown, vertical space decreases
        if needs_hscroll:
            adjusted_visible_rows = base_visible_rows - 1
            needs_vscroll = self.show_scrollbar and total_rows > adjusted_visible_rows
        else:
            adjusted_visible_rows = base_visible_rows

        # If vertical scrollbar is shown, horizontal space decreases
        if needs_vscroll:
            adjusted_visible_width = base_visible_width - 1
            needs_hscroll = (
                self.show_scrollbar
                and self._total_columns_width > adjusted_visible_width
            )
            # Recheck vertical after horizontal adjustment
            if needs_hscroll and not (
                self.show_scrollbar and total_rows > base_visible_rows - 1
            ):
                adjusted_visible_rows = base_visible_rows - 1
                needs_vscroll = (
                    self.show_scrollbar and total_rows > adjusted_visible_rows
                )
        else:
            adjusted_visible_width = base_visible_width

        # Final viewport sizes accounting for both scrollbars
        self._visible_rows = adjusted_visible_rows
        self._visible_width = adjusted_visible_width

        # Update scroll managers
        self.scroll_manager.update_content_size(total_rows)
        self.scroll_manager.update_viewport_size(self._visible_rows)
        self.scroll_manager_x.update_content_size(self._total_columns_width)
        self.scroll_manager_x.update_viewport_size(self._visible_width)

    @property
    def cursor_state_key(self) -> str | None:
        """Get the state key for cursor position.

        Returns
        -------
        str or None
            State key for cursor, or None if no id
        """
        if self._cursor_state_key_override is not None:
            return self._cursor_state_key_override
        return self._state_key("cursor")

    @cursor_state_key.setter
    def cursor_state_key(self, value: str | None) -> None:
        """Set an explicit cursor state key."""
        self._cursor_state_key_override = value

    @property
    def scroll_position(self) -> int:
        """Get the current vertical scroll position.

        Returns
        -------
        int
            Current scroll offset (0-based)
        """
        return self.scroll_manager.state.scroll_position

    def can_scroll(self, direction: int) -> bool:
        """Check if the grid can scroll in the given direction.

        Parameters
        ----------
        direction : int
            Scroll direction: negative for up, positive for down

        Returns
        -------
        bool
            True if scrolling in the given direction is possible
        """
        if direction < 0:  # Up
            return self.scroll_manager.state.scroll_position > 0
        else:  # Down
            return self.scroll_manager.state.scroll_position < (
                len(self.data) - self._visible_rows
            )

    def _row_number_width(self) -> int:
        """Calculate width needed for row numbers.

        Returns
        -------
        int
            Width for row number column (includes space)
        """
        if not self.show_row_numbers:
            return 0
        # Width of largest row number + space
        max_row = max(len(self.data), 1)
        return len(str(max_row)) + 2

    def _get_cell_ref(self) -> str:
        """Get current cell reference (e.g., "A1", "B3").

        Returns
        -------
        str
            Cell reference in A1 notation
        """
        col_letter = _col_letter(self.cursor_col)
        row_num = self.cursor_row + 1
        return f"{col_letter}{row_num}"

    def _get_column_label(self) -> str:
        """Get current column's label.

        Returns
        -------
        str
            Column label or empty string
        """
        if 0 <= self.cursor_col < len(self.columns):
            return self.columns[self.cursor_col]["label"]
        return ""

    def get_cell(self, row: int, col: int) -> str:
        """Get value at cell.

        Parameters
        ----------
        row : int
            Row index (0-based)
        col : int
            Column index (0-based)

        Returns
        -------
        str
            Cell value or empty string if out of bounds
        """
        if 0 <= row < len(self.data) and 0 <= col < len(self.data[row]):
            return self.data[row][col]
        return ""

    def set_cell(self, row: int, col: int, value: str) -> None:
        """Set value at cell (triggers callback).

        Parameters
        ----------
        row : int
            Row index (0-based)
        col : int
            Column index (0-based)
        value : str
            New cell value
        """
        # Ensure row exists
        while len(self.data) <= row:
            self.data.append([""] * len(self.columns))

        # Ensure column exists in row
        while len(self.data[row]) <= col:
            self.data[row].append("")

        old_value = self.data[row][col]
        if old_value != value:
            self.data[row][col] = value
            if self.on_cell_change:
                self.on_cell_change(row, col, old_value, value)
            if self.on_data_change:
                self.on_data_change(self.data)

    def get_data(self) -> list[list[str]]:
        """Get all data as 2D list.

        Returns
        -------
        list of list of str
            Copy of grid data
        """
        return [row[:] for row in self.data]

    def get_data_as_dicts(self) -> list[dict[str, str]]:
        """Get all data as list of dictionaries.

        Each row becomes a dict with column keys as keys. This is useful
        for converting grid data back to a format that can be used with
        pandas or other data processing tools.

        Returns
        -------
        list of dict
            Data as list of dictionaries

        Examples
        --------
        >>> grid = DataGrid(
        ...     data=[["Alice", "30"], ["Bob", "25"]],
        ...     columns=[{"key": "name", "label": "Name"}, {"key": "age", "label": "Age"}]
        ... )
        >>> grid.get_data_as_dicts()
        [{'name': 'Alice', 'age': '30'}, {'name': 'Bob', 'age': '25'}]
        """
        if not self._column_keys:
            # Fall back to col_0, col_1, ... if no keys defined
            keys = [f"col_{i}" for i in range(len(self.columns))]
        else:
            keys = self._column_keys

        result = []
        for row in self.data:
            row_dict = {}
            for i, key in enumerate(keys):
                if i < len(row):
                    row_dict[key] = row[i]
                else:
                    row_dict[key] = ""
            result.append(row_dict)
        return result

    def get_data_as_dataframe(self) -> Any:
        """Get all data as a pandas DataFrame.

        Requires pandas to be installed. If pandas is not available,
        raises ImportError with a helpful message.

        Returns
        -------
        pandas.DataFrame
            Data as DataFrame with column keys as column names

        Raises
        ------
        ImportError
            If pandas is not installed

        Examples
        --------
        >>> import pandas as pd
        >>> grid = DataGrid(
        ...     data=[["Alice", "30"], ["Bob", "25"]],
        ...     columns=[{"key": "name", "label": "Name"}, {"key": "age", "label": "Age"}]
        ... )
        >>> df = grid.get_data_as_dataframe()
        >>> isinstance(df, pd.DataFrame)
        True
        """
        try:
            import pandas as pd
        except ImportError as err:
            raise ImportError(
                "pandas is required for get_data_as_dataframe(). "
                "Install it with: pip install pandas"
            ) from err

        # Get column keys
        if not self._column_keys:
            keys = [f"col_{i}" for i in range(len(self.columns))]
        else:
            keys = self._column_keys

        # Create DataFrame
        return pd.DataFrame(self.data, columns=keys)

    def set_data(self, data: DataInput, update_columns: bool = False) -> None:
        """Replace all data.

        Accepts data in multiple formats (list of lists, list of dicts,
        or pandas DataFrame). Data is normalized to list of lists internally.

        Parameters
        ----------
        data : list of list, list of dict, or pandas DataFrame
            New grid data in any supported format
        update_columns : bool, optional
            If True and data is dict/DataFrame format, also update columns
            from the new data. Default is False (preserve existing columns).
        """
        normalized, inferred_columns = self._normalize_data(data)
        self.data = normalized

        # Optionally update columns from new data
        if update_columns and inferred_columns:
            self.columns = self._normalize_columns(inferred_columns)

        # Update scroll managers (handles both vertical and horizontal)
        self._update_scroll_managers()

        # Reset cursor if needed
        if self.cursor_row >= len(self.data):
            self.cursor_row = max(0, len(self.data) - 1)
        if self.on_data_change:
            self.on_data_change(self.data)

    def add_row(self, values: list[str] | None = None) -> None:
        """Add row at end.

        Parameters
        ----------
        values : list of str, optional
            Row values (defaults to empty cells)
        """
        if values is None:
            values = [""] * len(self.columns)
        self.data.append(values[:])
        self._update_scroll_managers()
        if self.on_data_change:
            self.on_data_change(self.data)

    def insert_row(self, index: int, values: list[str] | None = None) -> None:
        """Insert row at index.

        Parameters
        ----------
        index : int
            Row index to insert at
        values : list of str, optional
            Row values (defaults to empty cells)
        """
        if values is None:
            values = [""] * len(self.columns)
        index = max(0, min(index, len(self.data)))
        self.data.insert(index, values[:])
        self._update_scroll_managers()
        if self.on_data_change:
            self.on_data_change(self.data)

    def delete_row(self, index: int) -> None:
        """Delete row at index.

        Parameters
        ----------
        index : int
            Row index to delete
        """
        if 0 <= index < len(self.data):
            del self.data[index]
            self._update_scroll_managers()
            # Adjust cursor if needed
            if self.cursor_row >= len(self.data):
                self.cursor_row = max(0, len(self.data) - 1)
            if self.on_data_change:
                self.on_data_change(self.data)

    def add_column(self, header: str, values: list[str] | None = None) -> None:
        """Add column at end.

        Parameters
        ----------
        header : str
            Column header label
        values : list of str, optional
            Column values for each row (defaults to empty)
        """
        self.columns.append(
            {
                "key": header.lower().replace(" ", "_"),
                "label": header,
                "width": 10,
            }
        )
        # Add value to each row
        for i, row in enumerate(self.data):
            val = values[i] if values and i < len(values) else ""
            row.append(val)
        if self.on_data_change:
            self.on_data_change(self.data)

    def delete_column(self, index: int) -> None:
        """Delete column at index.

        Parameters
        ----------
        index : int
            Column index to delete
        """
        if 0 <= index < len(self.columns):
            del self.columns[index]
            for row in self.data:
                if index < len(row):
                    del row[index]
            # Adjust cursor if needed
            if self.cursor_col >= len(self.columns):
                self.cursor_col = max(0, len(self.columns) - 1)
            if self.on_data_change:
                self.on_data_change(self.data)

    def _start_editing(self, clear: bool = False) -> None:
        """Enter edit mode for current cell.

        Parameters
        ----------
        clear : bool
            If True, start with empty value (for typing over)
        """
        if not self.editable:
            return
        self.editing = True
        self._original_value = self.get_cell(self.cursor_row, self.cursor_col)
        if clear:
            self.edit_value = ""
            self.edit_cursor_pos = 0
        else:
            self.edit_value = self._original_value
            self.edit_cursor_pos = len(self.edit_value)

    def _commit_edit(self) -> None:
        """Commit current edit to cell."""
        if self.editing:
            self.set_cell(self.cursor_row, self.cursor_col, self.edit_value)
            self.editing = False
            self.edit_value = ""
            self.edit_cursor_pos = 0

    def _cancel_edit(self) -> None:
        """Cancel current edit, restore original value."""
        self.editing = False
        self.edit_value = ""
        self.edit_cursor_pos = 0

    def _move_cursor(self, d_row: int, d_col: int) -> None:
        """Move cursor by delta, handling wrapping and scrolling.

        Parameters
        ----------
        d_row : int
            Row delta (-1 for up, +1 for down)
        d_col : int
            Column delta (-1 for left, +1 for right)
        """
        # Commit any pending edit
        if self.editing:
            self._commit_edit()

        old_row, old_col = self.cursor_row, self.cursor_col

        # Calculate new position
        new_row = self.cursor_row + d_row
        new_col = self.cursor_col + d_col

        # Clamp to valid range
        if self.data:
            new_row = max(0, min(new_row, len(self.data) - 1))
        else:
            new_row = 0
        if self.columns:
            new_col = max(0, min(new_col, len(self.columns) - 1))
        else:
            new_col = 0

        self.cursor_row = new_row
        self.cursor_col = new_col

        # Emit selection change if changed
        if (old_row, old_col) != (new_row, new_col) and self.on_cell_select:
            self.on_cell_select(new_row, new_col)

        # Ensure cursor is visible (scroll if needed)
        self._ensure_cursor_visible()

    def _ensure_cursor_visible(self) -> None:
        """Scroll to ensure cursor is visible both vertically and horizontally."""
        # Vertical scrolling
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        if self.cursor_row < visible_start:
            self.scroll_manager.scroll_to(self.cursor_row)
        elif self.cursor_row >= visible_end:
            self.scroll_manager.scroll_to(self.cursor_row - self._visible_rows + 1)

        # Horizontal scrolling - ensure cursor column is visible
        if not self.columns:
            return

        # Calculate x position of cursor column
        col_start_x = self._get_column_start_x(self.cursor_col)
        col_width = self.columns[self.cursor_col].get("width", 10)
        col_end_x = col_start_x + col_width

        # Get current horizontal scroll position
        scroll_x = self.scroll_manager_x.state.scroll_position
        visible_end_x = scroll_x + self._visible_width

        # Scroll to show cursor column
        if col_start_x < scroll_x:
            # Column starts before visible area - scroll left
            self.scroll_manager_x.scroll_to(col_start_x)
        elif col_end_x > visible_end_x:
            # Column ends after visible area - scroll right
            self.scroll_manager_x.scroll_to(col_end_x - self._visible_width)

    def _get_column_start_x(self, col_index: int) -> int:
        """Get the x position where a column starts.

        Parameters
        ----------
        col_index : int
            Column index

        Returns
        -------
        int
            X position (0-based) where the column content starts
        """
        x = 0
        for i, col in enumerate(self.columns):
            if i == col_index:
                return x
            x += col.get("width", 10) + 1  # +1 for separator
        return x

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        # Handle editing mode keys first
        if self.editing:
            return self._handle_edit_key(key)

        # Navigation and edit initiation

        # Arrow keys - navigate
        if key == Keys.UP:
            self._move_cursor(-1, 0)
            return True
        elif key == Keys.DOWN:
            self._move_cursor(1, 0)
            return True
        elif key == Keys.LEFT:
            self._move_cursor(0, -1)
            return True
        elif key == Keys.RIGHT:
            self._move_cursor(0, 1)
            return True

        # Tab - move right, wrap to next row
        elif key == Keys.TAB:
            if self.cursor_col < len(self.columns) - 1:
                self._move_cursor(0, 1)
            elif self.cursor_row < len(self.data) - 1:
                # Wrap to first column of the next row in a single move so the
                # full position change drives on_cell_select and scrolling.
                self._move_cursor(1, -self.cursor_col)
            return True

        # Shift+Tab - move left, wrap to previous row
        elif key.name == "shift+tab":
            if self.cursor_col > 0:
                self._move_cursor(0, -1)
            elif self.cursor_row > 0:
                # Wrap to last column of the previous row in a single move.
                self._move_cursor(-1, len(self.columns) - 1)
            return True

        # Enter - move down. Not reachable while editing (handle_key delegates
        # to _handle_edit_key above), so no commit is needed here.
        elif key == Keys.ENTER:
            self._move_cursor(1, 0)
            return True

        # Home - go to first column
        elif key == Keys.HOME:
            self._move_cursor(0, -self.cursor_col)
            return True

        # End - go to last column
        elif key == Keys.END:
            if self.columns:
                self._move_cursor(0, len(self.columns) - 1 - self.cursor_col)
            return True

        # Ctrl+Home - go to A1
        elif key.name == "ctrl+home":
            self.cursor_row = 0
            self.cursor_col = 0
            self._ensure_cursor_visible()
            if self.on_cell_select:
                self.on_cell_select(0, 0)
            return True

        # Ctrl+End - go to last cell with data
        elif key.name == "ctrl+end":
            if self.data:
                self.cursor_row = len(self.data) - 1
            if self.columns:
                self.cursor_col = len(self.columns) - 1
            self._ensure_cursor_visible()
            if self.on_cell_select:
                self.on_cell_select(self.cursor_row, self.cursor_col)
            return True

        # Page Up/Down
        elif key == Keys.PAGE_UP:
            self.scroll_manager.page_up()
            # Move cursor to top of visible area
            visible_start, _ = self.scroll_manager.get_visible_range()
            self.cursor_row = visible_start
            if self.on_cell_select:
                self.on_cell_select(self.cursor_row, self.cursor_col)
            return True

        elif key == Keys.PAGE_DOWN:
            self.scroll_manager.page_down()
            # Move cursor to bottom of visible area
            _, visible_end = self.scroll_manager.get_visible_range()
            self.cursor_row = min(visible_end - 1, len(self.data) - 1)
            if self.on_cell_select:
                self.on_cell_select(self.cursor_row, self.cursor_col)
            return True

        # F2 - edit current cell
        elif key == Keys.F2:
            self._start_editing(clear=False)
            return True

        # Backspace/Delete - clear cell and enter edit mode
        elif key == Keys.BACKSPACE or key == Keys.DELETE:
            self._start_editing(clear=True)
            return True

        # Escape while not editing - do nothing (let parent handle)
        elif key == Keys.ESCAPE:
            return False

        # Printable character - clear and start typing
        elif key.is_char and key.char and self.editable:
            self._start_editing(clear=True)
            self.edit_value = key.char
            self.edit_cursor_pos = 1
            return True

        return False

    def _handle_edit_key(self, key: Key) -> bool:
        """Handle key press while in edit mode.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        # Escape - cancel edit
        if key == Keys.ESCAPE:
            self._cancel_edit()
            return True

        # Enter - commit and move down. _move_cursor commits the pending edit
        # itself, so an explicit _commit_edit() here would write the cell twice.
        elif key == Keys.ENTER:
            self._move_cursor(1, 0)
            return True

        # Tab - commit and move right, wrapping to the next row.
        elif key == Keys.TAB:
            if self.cursor_col < len(self.columns) - 1:
                self._move_cursor(0, 1)
            elif self.cursor_row < len(self.data) - 1:
                # Single move to first column of next row (commits the edit,
                # drives on_cell_select for the full position change).
                self._move_cursor(1, -self.cursor_col)
            return True

        # Arrow keys - commit and navigate (_move_cursor commits the edit).
        elif key == Keys.UP:
            self._move_cursor(-1, 0)
            return True
        elif key == Keys.DOWN:
            self._move_cursor(1, 0)
            return True
        elif key == Keys.LEFT:
            # Move cursor within edit, or commit and move to prev cell
            if self.edit_cursor_pos > 0:
                self.edit_cursor_pos -= 1
            else:
                self._move_cursor(0, -1)
            return True
        elif key == Keys.RIGHT:
            # Move cursor within edit, or commit and move to next cell
            if self.edit_cursor_pos < len(self.edit_value):
                self.edit_cursor_pos += 1
            else:
                self._move_cursor(0, 1)
            return True

        # Home/End within edit
        elif key == Keys.HOME:
            self.edit_cursor_pos = 0
            return True
        elif key == Keys.END:
            self.edit_cursor_pos = len(self.edit_value)
            return True

        # Backspace
        elif key == Keys.BACKSPACE:
            if self.edit_cursor_pos > 0:
                self.edit_value = (
                    self.edit_value[: self.edit_cursor_pos - 1]
                    + self.edit_value[self.edit_cursor_pos :]
                )
                self.edit_cursor_pos -= 1
            return True

        # Delete
        elif key == Keys.DELETE:
            if self.edit_cursor_pos < len(self.edit_value):
                self.edit_value = (
                    self.edit_value[: self.edit_cursor_pos]
                    + self.edit_value[self.edit_cursor_pos + 1 :]
                )
            return True

        # Character input
        elif key.is_char and key.char:
            self.edit_value = (
                self.edit_value[: self.edit_cursor_pos]
                + key.char
                + self.edit_value[self.edit_cursor_pos :]
            )
            self.edit_cursor_pos += 1
            return True

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        # Scroll wheel
        if event.button == MouseButton.SCROLL_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-1)
            if self.scroll_manager.state.scroll_position != old_pos:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if self.scroll_manager.state.scroll_position != old_pos:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        # Click events
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            if not self.bounds:
                return False

            # Convert to relative coordinates
            rel_x = event.x - self.bounds.x
            rel_y = event.y - self.bounds.y

            # Check if click is in grid area (not entry line)
            # Entry line is rows 0-1 (border + content), separator is row 2, header is row 3
            # Data starts at row 4
            if rel_y >= 4:
                # Calculate which row/col was clicked
                data_row_offset = rel_y - 4
                visible_start, _ = self.scroll_manager.get_visible_range()
                clicked_row = visible_start + data_row_offset

                # Calculate column from x position
                row_num_width = self._row_number_width()
                x_in_grid = rel_x - 1 - row_num_width  # -1 for border

                clicked_col = self._x_to_column(x_in_grid)

                # Validate and update cursor
                if 0 <= clicked_row < len(self.data) and 0 <= clicked_col < len(
                    self.columns
                ):
                    # Commit any pending edit first
                    if self.editing:
                        self._commit_edit()

                    old_row, old_col = self.cursor_row, self.cursor_col
                    self.cursor_row = clicked_row
                    self.cursor_col = clicked_col

                    if (old_row, old_col) != (clicked_row, clicked_col):
                        if self.on_cell_select:
                            self.on_cell_select(clicked_row, clicked_col)

                    # Double-click enters edit mode
                    if event.type == MouseEventType.DOUBLE_CLICK:
                        self._start_editing(clear=False)

                    return True

            # Click in entry line area - position cursor in edit text
            elif rel_y == 1 and self.editing:
                # Calculate position in edit text
                # Entry line format: "| [A1] Label    | value_here     |"
                # Edit area starts after the label section
                entry_label_width = 8 + max(10, len(self._get_column_label())) + 3
                edit_x = rel_x - entry_label_width
                if edit_x >= 0:
                    self.edit_cursor_pos = min(edit_x, len(self.edit_value))
                    return True

        return False

    def _x_to_column(self, x: int) -> int:
        """Convert x position to column index.

        Parameters
        ----------
        x : int
            X position relative to grid content start

        Returns
        -------
        int
            Column index (may be out of bounds)
        """
        if x < 0:
            return -1
        current_x = 0
        for i, col in enumerate(self.columns):
            col_width = col["width"] + 1  # +1 for separator
            if x < current_x + col_width:
                return i
            current_x += col_width
        return len(self.columns)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the element.

        Returns
        -------
        tuple of (int, int)
            (width, height) in characters/lines
        """
        width = self.width_spec if isinstance(self.width_spec, int) else 60
        height = self.height_spec if isinstance(self.height_spec, int) else 15
        return (width, height)

    def render_to(self, ctx: PaintContext) -> None:
        """Render the data grid to the paint context.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds
        """
        border_chars = BORDER_CHARS[self.border_style]

        # Style resolution
        _base_style = ctx.style_resolver.resolve_style(self, "datagrid")
        border_style = ctx.style_resolver.resolve_style(
            self, "datagrid.border:focus" if self.focused else "datagrid.border"
        )
        header_style = ctx.style_resolver.resolve_style(self, "datagrid.header")
        cell_style = ctx.style_resolver.resolve_style(self, "datagrid.cell")
        selected_style = ctx.style_resolver.resolve_style(
            self, "datagrid.cell:selected"
        )
        entry_style = ctx.style_resolver.resolve_style(self, "datagrid.entry")
        entry_edit_style = ctx.style_resolver.resolve_style(
            self, "datagrid.entry:editing"
        )

        width = ctx.bounds.width
        height = ctx.bounds.height

        # Update scroll managers to ensure content sizes are correct
        # This syncs scroll state before rendering (like TextArea does)
        self._update_scroll_managers()

        # Determine if scrollbars are needed
        needs_vscrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        needs_hscrollbar = (
            self.show_scrollbar and self.scroll_manager_x.state.is_scrollable
        )

        # Calculate layout dimensions
        row_num_width = self._row_number_width()
        scrollbar_width = 1 if needs_vscrollbar else 0
        inner_width = width - 2 - scrollbar_width  # Subtract borders and scrollbar

        # Adjust height for horizontal scrollbar
        data_height = height
        if needs_hscrollbar:
            data_height -= 1  # Reserve row for horizontal scrollbar

        # Render entry line area (rows 0-1)
        self._render_entry_line(
            ctx,
            border_chars,
            border_style,
            entry_style,
            entry_edit_style,
            inner_width,
            scrollbar_width,
        )

        # Render separator line (row 2)
        self._render_separator(
            ctx, border_chars, border_style, inner_width, scrollbar_width
        )

        # Render header row (row 3)
        self._render_header(
            ctx,
            border_chars,
            border_style,
            header_style,
            row_num_width,
            inner_width,
            scrollbar_width,
        )

        # Render data rows (rows 4 to height-2)
        self._render_data_rows(
            ctx,
            border_chars,
            border_style,
            cell_style,
            selected_style,
            row_num_width,
            inner_width,
            scrollbar_width,
        )

        # Render vertical scrollbar if needed
        if needs_vscrollbar:
            self._render_vertical_scrollbar(ctx, border_style, data_height)

        # Render horizontal scrollbar if needed
        if needs_hscrollbar:
            self._render_horizontal_scrollbar(
                ctx, border_chars, border_style, inner_width, height - 2
            )

        # Render bottom border (last row)
        self._render_bottom_border(
            ctx, border_chars, border_style, height - 1, inner_width + scrollbar_width
        )

    def _render_entry_line(
        self,
        ctx: PaintContext,
        border_chars: dict,
        border_style,
        entry_style,
        entry_edit_style,
        inner_width: int,
        scrollbar_width: int = 0,
    ) -> None:
        """Render the entry line area (top 2 rows).

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_chars : dict
            Border character set
        border_style : Style
            Style for borders
        entry_style : Style
            Style for entry line
        entry_edit_style : Style
            Style for entry line when editing
        inner_width : int
            Inner width excluding borders and scrollbar
        scrollbar_width : int
            Width reserved for vertical scrollbar (0 or 1)
        """
        # Row 0: Top border of entry line
        scrollbar_space_h = border_chars["h"] * scrollbar_width
        top_line = (
            border_chars["tl"]
            + border_chars["h"] * inner_width
            + scrollbar_space_h
            + border_chars["tr"]
        )
        ctx.write_text(0, 0, top_line, border_style)

        # Row 1: Entry line content
        # Format: | [A1] Column Name  | value_here_          |
        cell_ref = f"[{self._get_cell_ref()}]"
        col_label = self._get_column_label()

        # Calculate widths
        ref_width = 8  # Fixed width for cell ref
        label_width = max(10, len(col_label))
        label_section_width = ref_width + label_width + 3  # +3 for spaces/separator

        # Build entry line content
        ref_padded = clip_to_width(cell_ref, ref_width - 1, ellipsis="")
        ref_padded = ref_padded + " " * (ref_width - visible_length(ref_padded))

        label_padded = clip_to_width(col_label, label_width, ellipsis="...")
        label_padded = label_padded + " " * (label_width - visible_length(label_padded))

        # Get current value to display
        if self.editing:
            display_value = self.edit_value
            current_style = entry_edit_style
        else:
            display_value = self.get_cell(self.cursor_row, self.cursor_col)
            current_style = entry_style

        # Calculate edit area width
        edit_area_width = inner_width - label_section_width - 1  # -1 for final space
        value_padded = clip_to_width(display_value, edit_area_width, ellipsis="")
        value_padded = value_padded + " " * (
            edit_area_width - visible_length(value_padded)
        )

        # Combine and render (include scrollbar space)
        scrollbar_space = " " * scrollbar_width
        entry_content = (
            f" {ref_padded}{label_padded} {border_chars['v']} {value_padded}"
        )
        entry_line = border_chars["v"] + entry_content[:inner_width]
        if len(entry_content) < inner_width:
            entry_line += " " * (inner_width - len(entry_content))
        entry_line += scrollbar_space + border_chars["v"]

        ctx.write_text(0, 1, entry_line, current_style)

        # Render cursor in entry line if editing and focused
        if self.editing and self.focused:
            cursor_x = 1 + label_section_width + 1 + self.edit_cursor_pos
            if cursor_x < ctx.bounds.width - 1:
                # Draw cursor by inverting character at cursor position
                cursor_style = ctx.style_resolver.resolve_style(self, "datagrid.cursor")
                char_at_cursor = (
                    self.edit_value[self.edit_cursor_pos]
                    if self.edit_cursor_pos < len(self.edit_value)
                    else " "
                )
                ctx.write_text(cursor_x, 1, char_at_cursor, cursor_style)

    def _render_header(
        self,
        ctx: PaintContext,
        border_chars: dict,
        border_style,
        header_style,
        row_num_width: int,
        inner_width: int,
        scrollbar_width: int = 0,
    ) -> None:
        """Render the header row.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_chars : dict
            Border character set
        border_style : Style
            Style for borders
        header_style : Style
            Style for header text
        row_num_width : int
            Width of row number column
        inner_width : int
            Inner width excluding borders and scrollbar
        scrollbar_width : int
            Width reserved for vertical scrollbar (0 or 1)
        """
        # Header row (row 3)
        header_content = " " * row_num_width
        for col in self.columns:
            label = col["label"]
            col_width = col["width"]
            label_clipped = clip_to_width(label, col_width, ellipsis="...")
            label_padded = label_clipped + " " * (
                col_width - visible_length(label_clipped)
            )
            header_content += label_padded + " "

        # Clip to inner width and pad
        header_content = clip_to_width(header_content, inner_width, ellipsis="")
        header_content = header_content + " " * (
            inner_width - visible_length(header_content)
        )

        scrollbar_space = " " * scrollbar_width
        header_line = (
            border_chars["v"] + header_content + scrollbar_space + border_chars["v"]
        )
        ctx.write_text(0, 3, header_line, header_style)

    def _render_data_rows(
        self,
        ctx: PaintContext,
        border_chars: dict,
        border_style,
        cell_style,
        selected_style,
        row_num_width: int,
        inner_width: int,
        scrollbar_width: int = 0,
    ) -> None:
        """Render the data rows.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_chars : dict
            Border character set
        border_style : Style
            Style for borders
        cell_style : Style
            Style for normal cells
        selected_style : Style
            Style for selected cell
        row_num_width : int
            Width of row number column
        inner_width : int
            Inner width excluding borders and scrollbar
        scrollbar_width : int
            Width reserved for vertical scrollbar (0 or 1)
        """
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        max_data_rows = (
            ctx.bounds.height - 5
        )  # Entry(2) + sep(1) + header(1) + bottom(1)

        for i in range(max_data_rows):
            data_row_idx = visible_start + i
            row_y = 4 + i  # Start after entry(2) + sep(1) + header(1)

            if row_y >= ctx.bounds.height - 1:
                break

            if data_row_idx < len(self.data):
                row_data = self.data[data_row_idx]

                # Build row content
                row_content = ""
                if self.show_row_numbers:
                    row_num = str(data_row_idx + 1)
                    row_content = row_num + " " * (row_num_width - len(row_num))

                for col_idx, col in enumerate(self.columns):
                    col_width = col["width"]
                    cell_value = row_data[col_idx] if col_idx < len(row_data) else ""

                    # Check if this is the selected cell
                    is_selected = (
                        data_row_idx == self.cursor_row
                        and col_idx == self.cursor_col
                        and self.focused
                    )

                    cell_clipped = clip_to_width(cell_value, col_width, ellipsis="...")
                    cell_padded = cell_clipped + " " * (
                        col_width - visible_length(cell_clipped)
                    )

                    if is_selected:
                        # Mark selected cell boundaries for special rendering
                        # We'll render the whole row, then overlay the selected cell
                        pass

                    row_content += cell_padded + " "

                # Clip and pad row content
                row_content = clip_to_width(row_content, inner_width, ellipsis="")
                row_content = row_content + " " * (
                    inner_width - visible_length(row_content)
                )

                # Render row with borders (leave space for scrollbar if present)
                scrollbar_space = " " * scrollbar_width
                row_line = (
                    border_chars["v"]
                    + row_content
                    + scrollbar_space
                    + border_chars["v"]
                )
                ctx.write_text(0, row_y, row_line, cell_style)

                # Render selected cell with highlight
                if self.cursor_row == data_row_idx and self.focused:
                    self._render_selected_cell(
                        ctx, row_y, row_num_width, selected_style
                    )
            else:
                # Empty row (include scrollbar space)
                scrollbar_space = " " * scrollbar_width
                empty_content = " " * inner_width
                empty_line = (
                    border_chars["v"]
                    + empty_content
                    + scrollbar_space
                    + border_chars["v"]
                )
                ctx.write_text(0, row_y, empty_line, cell_style)

    def _render_selected_cell(
        self,
        ctx: PaintContext,
        row_y: int,
        row_num_width: int,
        selected_style,
    ) -> None:
        """Render the selected cell with highlight.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        row_y : int
            Y position of the row
        row_num_width : int
            Width of row number column
        selected_style : Style
            Style for selected cell
        """
        # Calculate x position of selected column
        x_offset = 1 + row_num_width  # Border + row numbers
        for col_idx, col in enumerate(self.columns):
            if col_idx == self.cursor_col:
                break
            x_offset += col["width"] + 1  # +1 for space separator

        # Get cell value
        cell_value = self.get_cell(self.cursor_row, self.cursor_col)
        col_width = (
            self.columns[self.cursor_col]["width"]
            if self.cursor_col < len(self.columns)
            else 10
        )

        # Render cell with selected style
        cell_clipped = clip_to_width(cell_value, col_width, ellipsis="...")
        cell_padded = cell_clipped + " " * (col_width - visible_length(cell_clipped))

        # Wrap with selection indicator
        selected_text = f"[{cell_padded}]"
        # Adjust x for the bracket
        ctx.write_text(x_offset - 1, row_y, selected_text, selected_style)

    def _render_separator(
        self,
        ctx: PaintContext,
        border_chars: dict,
        border_style,
        inner_width: int,
        scrollbar_width: int,
    ) -> None:
        """Render the separator line between entry line and header.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_chars : dict
            Border character set
        border_style : Style
            Style for borders
        inner_width : int
            Inner width excluding borders
        scrollbar_width : int
            Width reserved for scrollbar
        """
        # Row 2: Separator between entry line and grid
        scrollbar_space = border_chars["h"] * scrollbar_width
        sep_line = (
            border_chars["v"]
            + border_chars["h"] * inner_width
            + scrollbar_space
            + border_chars["v"]
        )
        ctx.write_text(0, 2, sep_line, border_style)

    def _render_vertical_scrollbar(
        self,
        ctx: PaintContext,
        border_style,
        height: int,
    ) -> None:
        """Render the vertical scrollbar.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_style : Style
            Style for scrollbar
        height : int
            Total height available
        """
        scrollbar_style = ctx.style_resolver.resolve_style(self, "datagrid.scrollbar")

        # Scrollbar starts at row 3 (after entry line and separator)
        # and extends to height-2 (before bottom border)
        scrollbar_height = (
            height - 5
        )  # Exclude: entry(2) + sep(1) + header(1) + bottom border(1)
        if scrollbar_height <= 0:
            return

        scrollbar_chars = render_vertical_scrollbar(
            self.scroll_manager.state, scrollbar_height
        )

        # Position scrollbar at right edge, inside border
        scrollbar_x = ctx.bounds.width - 2

        # Render each scrollbar character
        for i, char in enumerate(scrollbar_chars):
            ctx.write_text(scrollbar_x, 4 + i, char, scrollbar_style)

    def _render_horizontal_scrollbar(
        self,
        ctx: PaintContext,
        border_chars: dict,
        border_style,
        inner_width: int,
        row_y: int,
    ) -> None:
        """Render the horizontal scrollbar.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_chars : dict
            Border character set
        border_style : Style
            Style for borders
        inner_width : int
            Width available for scrollbar
        row_y : int
            Y position for scrollbar row
        """
        scrollbar_style = ctx.style_resolver.resolve_style(self, "datagrid.scrollbar")

        # Generate scrollbar string
        scrollbar_str = render_horizontal_scrollbar(
            self.scroll_manager_x.state, inner_width
        )

        # Render with borders
        scrollbar_line = border_chars["v"] + scrollbar_str + border_chars["v"]
        ctx.write_text(0, row_y, scrollbar_line, scrollbar_style)

    def _render_bottom_border(
        self,
        ctx: PaintContext,
        border_chars: dict,
        border_style,
        row_y: int,
        inner_width: int,
    ) -> None:
        """Render the bottom border.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_chars : dict
            Border character set
        border_style : Style
            Style for borders
        row_y : int
            Y position for bottom border
        inner_width : int
            Inner width excluding borders
        """
        bottom_line = (
            border_chars["bl"] + border_chars["h"] * inner_width + border_chars["br"]
        )
        ctx.write_text(0, row_y, bottom_line, border_style)

    def get_ephemeral_state(self) -> dict:
        """Get ephemeral state for reconciliation.

        Returns
        -------
        dict
            State that should survive re-renders
        """
        state = {
            "cursor_row": self.cursor_row,
            "cursor_col": self.cursor_col,
        }
        if self.scroll_manager:
            state["_scroll_position"] = self.scroll_manager.state.scroll_position
        if self.scroll_manager_x:
            state["_scroll_position_x"] = self.scroll_manager_x.state.scroll_position
        if self.editing:
            state["editing"] = self.editing
            state["edit_value"] = self.edit_value
            state["edit_cursor_pos"] = self.edit_cursor_pos
            state["_original_value"] = self._original_value
        return state

    def restore_ephemeral_state(self, state: dict) -> None:
        """Restore ephemeral state after reconciliation.

        Parameters
        ----------
        state : dict
            State from get_ephemeral_state()
        """
        if "cursor_row" in state:
            max_row = len(self.data) - 1 if self.data else 0
            self.cursor_row = min(state["cursor_row"], max_row)
        if "cursor_col" in state:
            max_col = len(self.columns) - 1 if self.columns else 0
            self.cursor_col = min(state["cursor_col"], max_col)
        if "_scroll_position" in state and self.scroll_manager:
            self.scroll_manager.scroll_to(state["_scroll_position"])
        if "_scroll_position_x" in state and self.scroll_manager_x:
            self.scroll_manager_x.scroll_to(state["_scroll_position_x"])
        if state.get("editing"):
            self.editing = True
            self.edit_value = state.get("edit_value", "")
            self.edit_cursor_pos = state.get("edit_cursor_pos", 0)
            self._original_value = state.get("_original_value", "")
