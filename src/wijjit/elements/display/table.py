# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable
from io import StringIO
from typing import TYPE_CHECKING, Literal

import rich.box
from rich.console import Console
from rich.table import Table as RichTable

from wijjit.elements.base import ElementType, ScrollableElement
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
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
    """

    def __init__(
        self,
        id: str | None = None,
        data: list[dict] | None = None,
        columns: list[str] | list[dict] | None = None,
        width: int = 60,
        height: int = 10,
        sortable: bool = False,
        show_header: bool = True,
        show_scrollbar: bool = True,
        border_style: str = "single",
    ) -> None:
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Data and columns
        self._raw_data = data or []
        self._raw_columns = columns or []
        self.data = self._raw_data.copy()  # Working copy (can be sorted)
        self.columns = self._normalize_columns(self._raw_columns)

        # Display properties
        self.width = width
        self.height = height
        self.show_header = show_header
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style

        # Sorting settings
        self.sortable = sortable

        # Sorting state
        self.sort_column: str | None = None
        self.sort_direction: Literal["asc", "desc"] = "asc"

        # Calculate viewport height for data rows
        # Rich table uses: top border (1) + header (1 if shown) + separator (1 if header) + bottom border (1)
        # So for data rows: height - 2 (borders) - 2 (header + separator if shown)
        if self.show_header:
            viewport_height = max(
                1, self.height - 4
            )  # top border, header, separator, bottom border
        else:
            viewport_height = max(1, self.height - 2)  # top and bottom borders only

        # Scroll management for rows
        self.scroll_manager = ScrollManager(
            content_size=len(self.data), viewport_size=viewport_height
        )

        # Scroll position persistence (will be set by template extension)
        self.initial_scroll_position = 0
        # scroll_state_key and on_scroll provided by ScrollableElement

        # Callbacks
        self.on_sort: Callable[[str | None, str], None] | None = (
            None  # (column, direction)
        )

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

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
            Normalized columns with 'key', 'label', 'width' keys
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
                    }
                )
            else:
                # String format - use same value for key and label
                normalized.append(
                    {
                        "key": str(col),
                        "label": str(col),
                        "width": None,
                    }
                )
        return normalized

    def set_data(self, data: list[dict]) -> None:
        """Update table data and refresh scroll state.

        Parameters
        ----------
        data : list of dict
            New table data
        """
        self._raw_data = data
        self.data = data.copy()

        # Re-apply sort if active
        if self.sort_column:
            self._apply_sort()

        # Update scroll manager with new content size
        self.scroll_manager.update_content_size(len(self.data))

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
            self.on_sort(self.sort_column, self.sort_direction)

    def _apply_sort(self) -> None:
        """Apply current sort settings to data."""
        if not self.sort_column:
            return

        # Sort data by column
        reverse = self.sort_direction == "desc"

        try:
            self.data.sort(
                key=lambda row: row.get(self.sort_column, ""), reverse=reverse
            )
        except TypeError:
            # Handle mixed types by converting to string
            self.data.sort(
                key=lambda row: str(row.get(self.sort_column, "")), reverse=reverse
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
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Down arrow - scroll down one row
        elif key == Keys.DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Home - jump to top
        elif key == Keys.HOME:
            self.scroll_manager.scroll_to(0)
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # End - jump to bottom
        elif key == Keys.END:
            self.scroll_manager.scroll_to_bottom()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # Page Up
        elif key == Keys.PAGE_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_up()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Page Down
        elif key == Keys.PAGE_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_down()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        return False

    def handle_mouse(self, event: MouseEvent) -> bool:
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
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Handle clicks on header for sorting
        if event.type == MouseEventType.CLICK:
            if not self.bounds or not self.sortable:
                return False

            # relative_x = event.x - self.bounds.x
            relative_y = event.y - self.bounds.y

            # Check if click is on header
            if self.show_header and relative_y == 0:
                # Determine which column was clicked
                # This is a simplified version - will refine with actual column positions
                # For now, just toggle sort on first column
                if self.columns:
                    self.sort_by_column(self.columns[0]["key"])
                return True

        return False

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

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'table': Base table style
        - 'table:focus': When table has focus
        - 'table.header': For column headers
        - 'table.row': For table rows
        - 'table.border': For table borders
        - 'table.border:focus': For borders when focused
        """
        from wijjit.rendering.ansi_adapter import ansi_string_to_cells
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

            table.add_column(label, width=col["width"], no_wrap=True)

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

        # Pad or trim to exact height
        if len(lines) < self.height:
            lines.extend(["" for _ in range(self.height - len(lines))])
        else:
            lines = lines[: self.height]

        # Generate scrollbar if needed
        scrollbar_chars = []
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, self.height
            )

        # Convert each line from ANSI to cells and write to buffer
        for y, line in enumerate(lines):
            # Convert ANSI string to cells
            cells = ansi_string_to_cells(line)

            # Write cells to buffer
            for x, cell in enumerate(cells):
                if x >= table_width:
                    break
                ctx.buffer.set_cell(ctx.bounds.x + x, ctx.bounds.y + y, cell)

            # Pad remaining width with empty cells if needed
            for x in range(len(cells), table_width):
                ctx.buffer.set_cell(ctx.bounds.x + x, ctx.bounds.y + y, Cell(char=" "))

            # Add scrollbar character if needed
            if needs_scrollbar:
                scrollbar_char = scrollbar_chars[y] if y < len(scrollbar_chars) else " "
                ctx.buffer.set_cell(
                    ctx.bounds.x + table_width,
                    ctx.bounds.y + y,
                    Cell(char=scrollbar_char),
                )
