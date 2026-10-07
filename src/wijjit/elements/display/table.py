"""Table element for displaying tabular data.

This module provides the Table element for displaying data in rows and columns
using Rich's Table renderer. Supports sorting, scrolling, row selection, and
various box styles. Ideal for displaying structured data in terminal interfaces.
"""

import math
import numbers
from collections.abc import Callable
from decimal import Decimal
from io import StringIO
from typing import TYPE_CHECKING, Any, Literal

import rich.box
from rich.console import Console
from rich.table import Table as RichTable

from wijjit.elements.base import ElementType, ScrollableElement, invoke_callback
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.layout.bounds import Bounds
    from wijjit.rendering.paint_context import PaintContext

BOX_STYLES = {
    "none": None,
    "ascii": rich.box.ASCII,
    "square": rich.box.SQUARE,
    "minimal": rich.box.MINIMAL,
    "simple": rich.box.SIMPLE,
    "rounded": rich.box.ROUNDED,
    "heavy": rich.box.HEAVY,
    "double": rich.box.DOUBLE,
    "single": rich.box.SQUARE,  # Map 'single' to SQUARE for consistency
}

# Sort ranks for mixed-type columns: numbers first, then strings, then any
# other type. Values are only ever compared against values of the same rank.
_RANK_NUMBER = 0
_RANK_STRING = 1
_RANK_OTHER = 2


def _is_missing(value: Any) -> bool:
    """Return True for a cell value that sorts as missing.

    Parameters
    ----------
    value : Any
        Cell value (``None`` when the row lacks the column key).

    Returns
    -------
    bool
        True for ``None`` and float/Decimal NaN, which always sort last.
    """
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, Decimal):
        return value.is_nan()
    return False


def _sort_rank(value: Any) -> int:
    """Return the type rank used to group a non-missing cell value.

    Parameters
    ----------
    value : Any
        Non-missing cell value.

    Returns
    -------
    int
        ``_RANK_NUMBER`` for bool/int/float/Decimal and other real numbers,
        ``_RANK_STRING`` for strings (even numeric-looking ones), and
        ``_RANK_OTHER`` for everything else.
    """
    if isinstance(value, (numbers.Real, Decimal)):
        return _RANK_NUMBER
    if isinstance(value, str):
        return _RANK_STRING
    return _RANK_OTHER


def _sort_rows(rows: list[dict], column: str, reverse: bool) -> list[dict]:
    """Return ``rows`` sorted by ``column`` with a total, type-safe order.

    Numbers sort numerically, strings lexically, and any other type natively
    when its values are mutually comparable (else by ``str``). Mixed-type
    columns are grouped by type rank (numbers, strings, other) instead of
    falling back to string order for the whole column. Missing values
    (``None``, NaN, or an absent key) always go last, in both directions,
    like pandas' ``na_position="last"``. The sort is stable against ``rows``,
    so ties keep their original order whatever the sort history.

    Parameters
    ----------
    rows : list of dict
        Rows in their original order.
    column : str
        Column key to sort by.
    reverse : bool
        True for descending order.

    Returns
    -------
    list of dict
        A new, sorted list (``rows`` is not modified).
    """
    groups: dict[int, list[tuple[Any, dict]]] = {
        _RANK_NUMBER: [],
        _RANK_STRING: [],
        _RANK_OTHER: [],
    }
    missing: list[dict] = []
    for row in rows:
        value = row.get(column)
        if _is_missing(value):
            missing.append(row)
        else:
            groups[_sort_rank(value)].append((value, row))

    def _first(pair: tuple[Any, dict]) -> Any:
        return pair[0]

    def _first_str(pair: tuple[Any, dict]) -> str:
        return str(pair[0])

    ordered: list[list[tuple[Any, dict]]] = []
    for rank in (_RANK_NUMBER, _RANK_STRING, _RANK_OTHER):
        group = groups[rank]
        try:
            group.sort(key=_first, reverse=reverse)
        except TypeError:
            # Only reachable for _RANK_OTHER (e.g. dicts, or dates mixed with
            # other objects): fall back to string order within this group.
            group.sort(key=_first_str, reverse=reverse)
        ordered.append(group)
    if reverse:
        ordered.reverse()

    result = [row for group in ordered for _, row in group]
    result.extend(missing)
    return result


class Table(ScrollableElement):
    """Table element for displaying tabular data with sorting.

    This element provides a rich table display with support for:
    - Column-based data display
    - Column sorting with visual indicators
    - Scrolling for large datasets
    - Mouse and keyboard interaction

    Parameters
    ----------
    id : str, optional
        Element identifier
    data : list of dict, optional
        Table data as list of row dictionaries
    columns : list of str or list of dict, optional
        Column definitions. Can be simple strings or dicts with 'key', 'label', 'width'
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 10, includes header)
    sortable : bool, optional
        Whether columns can be sorted (default: False)
    show_header : bool, optional
        Whether to show column headers (default: True)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Rich table border style (default: "single")

    Attributes
    ----------
    data : list of dict
        Table data
    columns : list of dict
        Normalized column definitions
    width : int
        Display width
    height : int
        Display height (total including header)
    sortable : bool
        Whether sorting is enabled
    show_header : bool
        Whether header is visible
    show_scrollbar : bool
        Whether scrollbar is visible
    border_style : str
        Rich border style
    sort_column : str or None
        Currently sorted column key
    sort_direction : str
        Sort direction ("asc" or "desc")
    scroll_manager : ScrollManager
        Manages scrolling of table rows
    on_sort : callable or None
        Callback when sort changes. Signature: on_sort(column_key, direction) -> None
    on_row_click : callable or None
        Callback when a row is clicked. Signature: on_row_click(row_index, row_data) -> None
    on_row_double_click : callable or None
        Callback when a row is double-clicked. Signature: on_row_double_click(row_index, row_data) -> None
    on_cell_click : callable or None
        Callback when a cell is clicked. Signature: on_cell_click(row_index, column_key, cell_value) -> None
    on_header_click : callable or None
        Callback when a column header is clicked. Signature: on_header_click(column_key) -> None
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        data: list[dict] | None = None,
        columns: list[str] | list[dict] | None = None,
        width: int | str = 60,
        height: int | str = 10,
        sortable: bool = False,
        show_header: bool = True,
        show_scrollbar: bool = True,
        border_style: str = "single",
        tab_index: int | None = None,
        bind: bool | str = True,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Data and columns
        self._raw_data = data or []
        self._raw_columns = columns or []
        self._data = self._raw_data.copy()  # Working copy (can be sorted)
        self.columns = self._normalize_columns(self._raw_columns)

        # Display properties. A string size ("fill", "50%", "auto") is resolved
        # by the layout engine and arrives through set_bounds(); until then the
        # table draws at the default size.
        self._dynamic_sizing: bool = isinstance(width, str) or isinstance(height, str)
        self.width: int = width if isinstance(width, int) else 60
        self.height: int = height if isinstance(height, int) else 10
        self.show_header = show_header
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style

        # Sorting settings
        self.sortable = sortable

        # Sorting state
        self.sort_column: str | None = None
        self.sort_direction: Literal["asc", "desc"] = "asc"

        # Actual per-column boundary x-positions (table-relative), captured from
        # the rendered Rich output each frame. Used for accurate header/cell
        # click hit-testing because Rich auto-sizes columns to content rather
        # than evenly. Empty until the first render_to(); _get_column_at_x()
        # falls back to an equal-width estimate when this is unavailable.
        self._column_boundaries: list[int] = []

        # Scroll management for rows
        self.scroll_manager = ScrollManager(
            content_size=len(self.data), viewport_size=self._viewport_height()
        )

        # Scroll position persistence (will be set by template extension)
        self.initial_scroll_position = 0
        # scroll_state_key and on_scroll provided by ScrollableElement

        # Callbacks
        self.on_sort: Callable[[str | None, str], None] | None = (
            None  # (column, direction)
        )
        self.on_row_click: Callable[[int, dict], None] | None = (
            None  # (row_index, row_data)
        )
        self.on_row_double_click: Callable[[int, dict], None] | None = (
            None  # (row_index, row_data)
        )
        self.on_cell_click: Callable[[int, str, str], None] | None = (
            None  # (row_index, column_key, cell_value)
        )
        self.on_header_click: Callable[[str], None] | None = None  # (column_key)

        # Template metadata
        self.action: str | None = None
        self.bind: bool | str = bind

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore
        """
        self.scroll_manager.scroll_to(position)

    @property
    def scroll_position(self) -> int:
        """Get the current scroll position.

        Returns
        -------
        int
            Current scroll offset (0-based)
        """
        return self.scroll_manager.state.scroll_position

    def _viewport_height(self) -> int:
        """Rows of data the table shows at its current height.

        Returns
        -------
        int
            The height less the top and bottom borders, and less the header
            row and its separator when the header is shown.
        """
        if self.show_header:
            return max(1, self.height - 4)
        return max(1, self.height - 2)

    @property
    def supports_dynamic_sizing(self) -> bool:
        """Whether the table was given a string size such as ``"fill"``.

        Returns
        -------
        bool
            True when the layout engine should size the table to its slot
            rather than to the number of rows it holds.
        """
        return self._dynamic_sizing

    def set_bounds(self, bounds: "Bounds") -> None:
        """Set bounds and resize the table to the space it was allocated.

        The table draws from ``self.width`` / ``self.height``, so they follow
        the bounds the layout engine hands out; for a fixed size they already
        match and nothing changes.

        Parameters
        ----------
        bounds : Bounds
            New bounds for the element.
        """
        super().set_bounds(bounds)
        if not bounds:
            return
        new_width = max(3, bounds.width)
        new_height = max(3, bounds.height)
        if new_width == self.width and new_height == self.height:
            return
        self.width = new_width
        self.height = new_height
        self.scroll_manager.update_viewport_size(self._viewport_height())

    def get_ephemeral_state(self) -> dict:
        """Get ephemeral state for reconciliation.

        Returns
        -------
        dict
            Scroll position to preserve across re-renders
        """
        return {
            "scroll_position": (
                self.scroll_manager.state.scroll_position if self.scroll_manager else 0
            )
        }

    def restore_ephemeral_state(self, state: dict) -> None:
        """Restore ephemeral state after reconciliation.

        Parameters
        ----------
        state : dict
            State from get_ephemeral_state()
        """
        if "scroll_position" in state and self.scroll_manager:
            self.scroll_manager.scroll_to(state["scroll_position"])

    def on_update(self, changed_props: dict) -> None:
        """Handle prop updates during reconciliation.

        Parameters
        ----------
        changed_props : dict
            Map of prop_name -> (old_value, new_value)
        """
        # Data/scroll synchronization is handled by the ``data`` property
        # setter, which the reconciler invokes via setattr during prop
        # application; no extra work is needed here.

    def can_scroll(self, direction: int) -> bool:
        """Check if the element can scroll in the given direction.

        Parameters
        ----------
        direction : int
            Scroll direction: negative for up, positive for down

        Returns
        -------
        bool
            True if scrolling in the given direction is possible
        """
        if direction < 0:
            return self.scroll_manager.state.scroll_position > 0
        else:
            return self.scroll_manager.state.is_scrollable and (
                self.scroll_manager.state.scroll_position
                < self.scroll_manager.state.max_scroll
            )

    def _normalize_columns(self, columns: list[str] | list[dict]) -> list[dict]:
        """Normalize column definitions to internal format.

        Parameters
        ----------
        columns : list of str or list of dict
            Raw column definitions

        Returns
        -------
        list of dict
            Normalized columns with 'key', 'label', 'width', 'align' keys.
            ``align`` is one of ``"left"``, ``"center"``, ``"right"`` and
            defaults to ``"left"``.
        """
        normalized = []
        for col in columns:
            if isinstance(col, dict):
                # Already dict format, ensure it has all keys
                normalized.append(
                    {
                        "key": col.get("key", col.get("label", "")),
                        "label": col.get("label", col.get("key", "")),
                        "width": col.get("width", None),  # None = auto
                        "align": self._normalize_align(col.get("align")),
                    }
                )
            else:
                # String format - use same value for key and label
                normalized.append(
                    {
                        "key": str(col),
                        "label": str(col),
                        "width": None,
                        "align": "left",
                    }
                )
        return normalized

    @staticmethod
    def _normalize_align(align: str | None) -> str:
        """Normalize a column alignment value to a Rich ``justify`` keyword.

        Parameters
        ----------
        align : str or None
            Requested alignment. Accepts ``"left"``, ``"center"``,
            ``"right"`` (case-insensitive). Unknown or missing values fall
            back to ``"left"``.

        Returns
        -------
        str
            One of ``"left"``, ``"center"``, ``"right"``.
        """
        if not align:
            return "left"
        value = str(align).strip().lower()
        if value in ("left", "center", "right"):
            return value
        return "left"

    @property
    def data(self) -> list[dict]:
        """Table rows (the working copy, which may be sorted).

        Assignment refreshes the raw backing copy, re-applies any active sort,
        and re-clamps scroll state -- so ``table.data = rows`` stays in sync
        the same way :meth:`set_data` does, instead of desyncing ``_raw_data``
        and the scroll manager.
        """
        return self._data

    @data.setter
    def data(self, rows: list[dict]) -> None:
        self._raw_data = rows or []
        self._data = self._raw_data.copy()

        # Re-apply sort if active
        if self.sort_column:
            self._apply_sort()

        # Update scroll manager with new content size (absent during __init__)
        scroll_manager = getattr(self, "scroll_manager", None)
        if scroll_manager is not None:
            scroll_manager.update_content_size(len(self._data))

    def set_data(self, data: list[dict]) -> None:
        """Update table data and refresh scroll state.

        Parameters
        ----------
        data : list of dict
            New table data
        """
        self.data = data

    def sort_by_column(self, column_key: str) -> None:
        """Sort table by specified column.

        Parameters
        ----------
        column_key : str
            Column key to sort by
        """
        if not self.sortable:
            return

        # Toggle direction if same column, else default to ascending
        if self.sort_column == column_key:
            self.sort_direction = "desc" if self.sort_direction == "asc" else "asc"
        else:
            self.sort_column = column_key
            self.sort_direction = "asc"

        self._apply_sort()

        # Emit callback
        if self.on_sort:
            invoke_callback(self.on_sort, self.sort_column, self.sort_direction)

    def _apply_sort(self) -> None:
        """Apply current sort settings to data."""
        if not self.sort_column:
            return

        self._data = _sort_rows(
            self._raw_data, self.sort_column, self.sort_direction == "desc"
        )

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for scrolling.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        if not self.data:
            return False

        # Up arrow - scroll up one row
        if key == Keys.UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        # Down arrow - scroll down one row
        elif key == Keys.DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        # Home - jump to top
        elif key == Keys.HOME:
            self.scroll_manager.scroll_to(0)
            if self.on_scroll:
                invoke_callback(
                    self.on_scroll, self.scroll_manager.state.scroll_position
                )
            return True

        # End - jump to bottom
        elif key == Keys.END:
            self.scroll_manager.scroll_to_bottom()
            if self.on_scroll:
                invoke_callback(
                    self.on_scroll, self.scroll_manager.state.scroll_position
                )
            return True

        # Page Up
        elif key == Keys.PAGE_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_up()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        # Page Down
        elif key == Keys.PAGE_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_down()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

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
        # Handle scroll wheel
        if event.button == MouseButton.SCROLL_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        if not self.bounds:
            return await super().handle_mouse(event)

        relative_x = event.x - self.bounds.x
        relative_y = event.y - self.bounds.y

        # Determine click location within table structure
        # Rich table structure (with header):
        # Row 0: top border
        # Row 1: header row
        # Row 2: header separator
        # Row 3+: data rows
        # Last row: bottom border
        header_offset = 3 if self.show_header else 1  # After top border

        # Handle clicks and double-clicks. Only the left button drives row,
        # cell, and header interactions; a right-click must fall through to the
        # base handler so on_context_menu can fire.
        if (
            event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK)
            and event.button == MouseButton.LEFT
        ):
            is_double = event.type == MouseEventType.DOUBLE_CLICK

            # Check if click is on header (row 1 with header shown)
            if self.show_header and relative_y == 1:
                column_key = self._get_column_at_x(relative_x)
                if column_key:
                    # Fire header click callback
                    if self.on_header_click:
                        invoke_callback(self.on_header_click, column_key)

                    # Also trigger sort if sortable
                    if self.sortable:
                        self.sort_by_column(column_key)
                    return True

            # Check if click is on a data row
            data_row_index = relative_y - header_offset
            if data_row_index >= 0:
                # Convert to actual data index (accounting for scroll)
                actual_row_index = (
                    self.scroll_manager.state.scroll_position + data_row_index
                )

                # Validate row index is within data bounds
                if 0 <= actual_row_index < len(self.data):
                    row_data = self.data[actual_row_index]

                    # Handle double-click. Without a row handler, fall through to
                    # the base class so the element-level on_double_click fires
                    # instead of the event being swallowed here.
                    if is_double:
                        if self.on_row_double_click:
                            invoke_callback(
                                self.on_row_double_click, actual_row_index, row_data
                            )
                            return True
                        return await super().handle_mouse(event)

                    # Handle single click
                    if self.on_row_click:
                        invoke_callback(self.on_row_click, actual_row_index, row_data)

                    # Handle cell click
                    if self.on_cell_click:
                        column_key = self._get_column_at_x(relative_x)
                        if column_key:
                            cell_value = str(row_data.get(column_key, ""))
                            invoke_callback(
                                self.on_cell_click,
                                actual_row_index,
                                column_key,
                                cell_value,
                            )

                    return True

        # Fall back to base class for on_double_click/on_context_menu
        return await super().handle_mouse(event)

    # Box-drawing horizontal fill characters used by Rich's top border. Any
    # other non-space glyph in the border row is a corner or column junction,
    # i.e. a column boundary.
    _BORDER_FILL_CHARS = frozenset(" -─═━╌╍┄┅┈┉")

    def _extract_column_boundaries(self, border_line: str) -> list[int]:
        """Extract column boundary x-positions from a rendered top border.

        Parameters
        ----------
        border_line : str
            The table's rendered top border line (e.g. ``"┌────┬────┐"``).

        Returns
        -------
        list[int]
            Ascending x-positions (table-relative) of the left border, every
            inter-column junction, and the right border. Empty if the line
            holds no recognizable boundary glyphs.

        Notes
        -----
        Rich sizes columns to their content, so columns are seldom equal width.
        The corners and junctions of the top border mark the true column
        boundaries and align with the vertical separators in every row, so they
        give an exact map from an x-position to a column for click handling.
        """
        return [
            i
            for i, char in enumerate(border_line)
            if char not in self._BORDER_FILL_CHARS
        ]

    def _get_column_at_x(self, x: int) -> str | None:
        """Determine which column is at the given x position.

        Parameters
        ----------
        x : int
            X position relative to table bounds

        Returns
        -------
        str or None
            Column key at position, or None if outside columns or on a
            column separator

        Notes
        -----
        Prefers the actual column boundaries captured from the most recent
        render (``self._column_boundaries``), which reflect Rich's
        content-based column widths. Falls back to an equal-width estimate
        only when no render has happened yet.
        """
        if not self.columns:
            return None

        # Preferred path: use the real boundaries from the last render. The
        # i-th column spans the open interval between boundary[i] and
        # boundary[i + 1]; a click exactly on a separator maps to no column.
        boundaries = self._column_boundaries
        if len(boundaries) >= 2:
            for i in range(len(boundaries) - 1):
                if boundaries[i] < x < boundaries[i + 1] and i < len(self.columns):
                    return self.columns[i]["key"]
            return None

        # Fallback (pre-first-render): assume evenly distributed columns.
        content_x = x - 1  # Account for left border (1 char)
        if content_x < 0:
            return None

        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        available_width = self.width - 2  # Minus borders
        if needs_scrollbar:
            available_width -= 1

        # Padding between columns (Rich uses 1 space padding on each side)
        padding_per_col = 2
        total_padding = padding_per_col * len(self.columns)
        content_width = available_width - total_padding

        col_width = max(1, content_width // len(self.columns))

        current_x = 0
        for col in self.columns:
            col_total_width = col_width + padding_per_col
            if current_x <= content_x < current_x + col_total_width:
                return col["key"]
            current_x += col_total_width

        return None

    def render_to(self, ctx: "PaintContext") -> None:
        """Render table using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for tables by:
        1. Rendering the table using Rich library (for layout and formatting)
        2. Converting the Rich ANSI output to cells using the ANSI adapter
        3. Writing cells to the buffer

        This approach leverages Rich's powerful table formatting while
        benefiting from cell-based rendering performance.

        Theme styles:

        This element uses the following theme style classes:
        - ``table``: Base table style
        - ``table:focus``: When table has focus
        - ``table.header``: For column headers
        - ``table.row``: For table rows
        - ``table.border``: For table borders
        - ``table.border:focus``: For borders when focused
        """
        from wijjit.rendering.ansi_adapter import ansi_string_to_cells, clip_cells
        from wijjit.terminal.cell import Cell

        if not self.columns:
            # No columns defined - show placeholder
            empty_msg = "No columns defined"
            empty_style = ctx.style_resolver.resolve_style(self, "table")
            ctx.write_text(0, 0, empty_msg, empty_style)
            return

        # Calculate effective width for table rendering
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        table_width = self.width - 1 if needs_scrollbar else self.width

        # Create Rich table with focus-based border style
        if self.focused:
            box_style = rich.box.DOUBLE
        else:
            box_style = BOX_STYLES.get(self.border_style, rich.box.SQUARE)

        table = RichTable(
            show_header=self.show_header,
            box=box_style,
            width=table_width,
            show_lines=False,
            padding=(0, 1),
        )

        # Add columns with sort indicators
        for col in self.columns:
            label = col["label"]

            if self.sortable and col["key"] == self.sort_column:
                indicator = " ▲" if self.sort_direction == "asc" else " ▼"
                label = label + indicator

            table.add_column(
                label,
                width=col["width"],
                no_wrap=True,
                justify=col.get("align", "left"),
            )

        # Get visible rows
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_data = self.data[visible_start:visible_end]

        # Add rows
        for row_data in visible_data:
            row_values = []
            for col in self.columns:
                value = row_data.get(col["key"], "")
                value_str = str(value)
                row_values.append(value_str)

            table.add_row(*row_values)

        # Render table using Rich
        console = Console(file=StringIO(), width=table_width, legacy_windows=False)
        console.print(table)
        output = console.file.getvalue()

        # Split into lines
        lines = output.rstrip("\n").split("\n")

        # Capture actual column boundaries from the rendered top border so
        # header/cell click hit-testing matches Rich's content-based column
        # widths (which are rarely equal). See _get_column_at_x().
        if lines:
            self._column_boundaries = self._extract_column_boundaries(lines[0])

        # Pad or trim to exact height
        if len(lines) < self.height:
            lines.extend(["" for _ in range(self.height - len(lines))])
        else:
            lines = lines[: self.height]

        # Generate scrollbar if needed
        scrollbar_chars = []
        scrollbar_thumb_attrs: dict[str, Any] = {}
        scrollbar_track_attrs: dict[str, Any] = {}
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, self.height
            )
            # Resolve the shared scrollbar thumb/track styles (focus-aware), the
            # same classes frames use, so a focused table's scrollbar picks up
            # the focus accent color. (The old "table.scrollbar" classes do not
            # exist in any theme, so the scrollbar was always unstyled.)
            thumb_class = "scrollbar.thumb:focus" if self.focused else "scrollbar.thumb"
            track_class = "scrollbar.track:focus" if self.focused else "scrollbar.track"
            scrollbar_thumb_attrs = ctx.style_resolver.resolve_style(
                self, thumb_class
            ).to_cell_attrs()
            scrollbar_track_attrs = ctx.style_resolver.resolve_style(
                self, track_class
            ).to_cell_attrs()

        # Convert each line from ANSI to cells and write to buffer
        for y, line in enumerate(lines):
            # Convert ANSI string to cells
            cells = ansi_string_to_cells(line)

            # Write cells to buffer, truncated to the table width
            ctx.write_cells(0, y, clip_cells(cells, table_width))

            # Pad remaining width with empty cells if needed
            if len(cells) < table_width:
                pad_cells = [Cell(char=" ")] * (table_width - len(cells))
                ctx.write_cells(len(cells), y, pad_cells)

            # Add scrollbar character if needed
            if needs_scrollbar:
                scrollbar_char = scrollbar_chars[y] if y < len(scrollbar_chars) else " "
                # Thumb cells use the full block glyph; everything else is track.
                is_thumb = scrollbar_char == "\u2588"
                sb_attrs = scrollbar_thumb_attrs if is_thumb else scrollbar_track_attrs
                ctx.write_cell(table_width, y, Cell(char=scrollbar_char, **sb_attrs))
