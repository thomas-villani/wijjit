"""Display UI elements for Wijjit applications.

This module provides display-oriented elements like tables and lists.
"""

from collections.abc import Callable
from io import StringIO
from typing import Literal

from rich import box
from rich.console import Console
from rich.table import Table as RichTable

from ..layout.scroll import ScrollManager, render_vertical_scrollbar
from ..terminal.ansi import clip_to_width, visible_length
from ..terminal.input import Key, Keys
from ..terminal.mouse import MouseButton, MouseEvent, MouseEventType
from .base import Element, ElementType

# Mapping of border style names to Rich box styles
BOX_STYLES = {
    "none": None,
    "ascii": box.ASCII,
    "square": box.SQUARE,
    "minimal": box.MINIMAL,
    "simple": box.SIMPLE,
    "rounded": box.ROUNDED,
    "heavy": box.HEAVY,
    "double": box.DOUBLE,
    "single": box.SQUARE,  # Map 'single' to SQUARE for consistency
}


class Table(Element):
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
    ):
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
        self.scroll_state_key: str | None = (
            None  # Key in app state for persisting scroll
        )

        # Callbacks
        self.on_sort: Callable[[str | None, str], None] | None = (
            None  # (column, direction)
        )
        self.on_scroll: Callable[[int], None] | None = (
            None  # Called when scroll position changes
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

    def render(self) -> str:
        """Render the table.

        Returns
        -------
        str
            Rendered table as multi-line string
        """
        if not self.columns:
            # No columns defined - show placeholder
            empty_msg = "No columns defined"
            return empty_msg.ljust(self.width)

        # Calculate effective width for table rendering
        # If scrollbar will be shown, reserve 1 character for it
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        table_width = self.width - 1 if needs_scrollbar else self.width

        # Create Rich table
        # Map border_style string to Rich box style
        # Use double border when focused for visual indication
        if self.focused:
            box_style = box.DOUBLE
        else:
            box_style = BOX_STYLES.get(self.border_style, box.SQUARE)

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

            # Add sort indicator if this column is sorted
            if self.sortable and col["key"] == self.sort_column:
                indicator = " ▲" if self.sort_direction == "asc" else " ▼"
                label = label + indicator

            table.add_column(label, width=col["width"], no_wrap=True)

        # Get visible rows
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_data = self.data[visible_start:visible_end]

        # Add rows
        for row_data in visible_data:
            # Build row values
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

        # Split into lines and trim to height
        lines = output.rstrip("\n").split("\n")

        # Pad or trim to exact height
        if len(lines) < self.height:
            lines.extend(["" for _ in range(self.height - len(lines))])
        else:
            lines = lines[: self.height]

        # Add scrollbar if needed
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, self.height
            )

            for i in range(len(lines)):
                # Pad line to table_width if needed
                line = lines[i]
                line_len = visible_length(line)
                if line_len < table_width:
                    line = line + " " * (table_width - line_len)

                # Add scrollbar character
                lines[i] = line + scrollbar_chars[i]
        else:
            # No scrollbar - just ensure lines are padded to full width
            for i in range(len(lines)):
                line = lines[i]
                line_len = visible_length(line)
                if line_len < self.width:
                    lines[i] = line + " " * (self.width - line_len)

        return "\n".join(lines)


class Tree(Element):
    """Tree element for displaying hierarchical data with expand/collapse.

    This element provides a tree view display with support for:
    - Hierarchical data visualization with tree drawing characters
    - Expand/collapse functionality for nodes with children
    - Node selection with visual indicators
    - Scrolling for large trees
    - Mouse and keyboard interaction

    Parameters
    ----------
    id : str, optional
        Element identifier
    data : dict or list, optional
        Tree data as nested dict or flat list
    width : int, optional
        Display width in columns (default: 40)
    height : int, optional
        Display height in rows (default: 15)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    show_root : bool, optional
        Whether to show root node (default: True)
    indent_size : int, optional
        Number of spaces per indentation level (default: 2)

    Attributes
    ----------
    data : dict or list
        Original tree data
    nodes : list of dict
        Flattened tree nodes for rendering
    width : int
        Display width
    height : int
        Display height
    show_scrollbar : bool
        Whether scrollbar is visible
    show_root : bool
        Whether root node is shown
    indent_size : int
        Indentation per level
    expanded_nodes : set
        Set of expanded node IDs
    selected_node_id : str or None
        ID of currently selected node
    highlighted_index : int
        Index of highlighted node in visible list
    scroll_manager : ScrollManager
        Manages scrolling of tree nodes

    Notes
    -----
    Tree data can be specified as:
    - Nested dict: {"label": "Root", "value": "1", "children": [...]}
    - Flat list: [{"id": "1", "label": "Root", "parent_id": None}, ...]

    Navigation:
    - Up/Down: Navigate nodes
    - Left: Collapse node or move to parent
    - Right: Expand node or move to first child
    - Enter/Space: Toggle expand/collapse
    - Home/End: Jump to first/last node
    - PageUp/PageDown: Scroll by page
    """

    def __init__(
        self,
        id: str | None = None,
        data: dict | list | None = None,
        width: int = 40,
        height: int = 15,
        show_scrollbar: bool = True,
        show_root: bool = True,
        indent_size: int = 2,
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True

        # Display properties
        self.width = width
        self.height = height
        self.show_scrollbar = show_scrollbar
        self.show_root = show_root
        self.indent_size = indent_size

        # Tree data
        self._raw_data = data
        self.data = self._normalize_data(data) if data else {}

        # Tree state
        self.expanded_nodes: set[str] = set()
        self.selected_node_id: str | None = None
        self.highlighted_index: int = 0

        # Flattened nodes for rendering
        self.nodes: list[dict] = []

        # Scroll management (initialize before rebuilding nodes)
        self.scroll_manager = ScrollManager(content_size=0, viewport_size=height)

        # Now rebuild nodes (which will update scroll_manager)
        self._rebuild_nodes()

        # Callbacks
        self.on_select: Callable[[dict], None] | None = None
        self.on_expand: Callable[[str], None] | None = None
        self.on_collapse: Callable[[str], None] | None = None
        self.on_scroll: Callable[[int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence keys
        self.scroll_state_key: str | None = None
        self.expand_state_key: str | None = None
        self.highlight_state_key: str | None = None
        self.selected_state_key: str | None = None

        # State save callback (set by app/template)
        self._state_dict: dict | None = None

    def _normalize_data(self, data: dict | list) -> dict:
        """Normalize tree data to internal nested dict format.

        Parameters
        ----------
        data : dict or list
            Raw tree data (nested dict or flat list)

        Returns
        -------
        dict
            Normalized tree data with 'id', 'label', 'value', 'children' keys
        """
        if isinstance(data, dict):
            # Already nested dict format, just ensure required fields
            return self._normalize_node(data)
        elif isinstance(data, list):
            # Flat list format - build tree structure
            return self._build_tree_from_flat(data)
        else:
            # Invalid format, return empty tree
            return {"id": "root", "label": "Root", "value": "root", "children": []}

    def _normalize_node(self, node: dict, node_id: str | None = None) -> dict:
        """Normalize a single node to ensure required fields.

        Parameters
        ----------
        node : dict
            Raw node data
        node_id : str, optional
            Node ID to use if not present in data

        Returns
        -------
        dict
            Normalized node with 'id', 'label', 'value', 'children' keys
        """
        # Generate ID if not provided
        if "id" not in node and "value" not in node:
            if node_id:
                node_id_value = node_id
            else:
                # Use label as fallback
                node_id_value = str(node.get("label", "node"))
        else:
            node_id_value = node.get("id", node.get("value", "node"))

        # Normalize children recursively
        children = node.get("children", [])
        normalized_children = []
        for i, child in enumerate(children):
            child_id = f"{node_id_value}_child_{i}"
            normalized_children.append(self._normalize_node(child, child_id))

        return {
            "id": str(node_id_value),
            "label": str(node.get("label", node_id_value)),
            "value": node.get("value", node_id_value),
            "children": normalized_children,
            # Preserve any extra metadata
            **{
                k: v
                for k, v in node.items()
                if k not in ["id", "label", "value", "children"]
            },
        }

    def _build_tree_from_flat(self, flat_list: list) -> dict:
        """Build nested tree structure from flat list.

        Parameters
        ----------
        flat_list : list of dict
            Flat list with parent_id references

        Returns
        -------
        dict
            Root node of nested tree structure
        """
        # Build lookup table
        nodes_by_id = {}
        for item in flat_list:
            node_id = item.get("id", item.get("value", str(len(nodes_by_id))))
            nodes_by_id[node_id] = {
                "id": str(node_id),
                "label": str(item.get("label", node_id)),
                "value": item.get("value", node_id),
                "children": [],
                "parent_id": item.get("parent_id"),
            }

        # Build tree structure
        root_node = None
        for _node_id, node in nodes_by_id.items():
            parent_id = node.get("parent_id")
            if parent_id is None or parent_id not in nodes_by_id:
                # This is a root node
                if root_node is None:
                    root_node = node
                # Else we have multiple roots, just use first one
            else:
                # Add to parent's children
                parent = nodes_by_id[parent_id]
                parent["children"].append(node)

        # Clean up parent_id from nodes
        for node in nodes_by_id.values():
            if "parent_id" in node:
                del node["parent_id"]

        return (
            root_node
            if root_node
            else {"id": "root", "label": "Root", "value": "root", "children": []}
        )

    def _rebuild_nodes(self) -> None:
        """Rebuild flattened nodes list based on current expansion state.

        This method flattens the tree into a linear list of visible nodes,
        respecting the expanded/collapsed state of each node. The result is
        stored in self.nodes for rendering and navigation.
        """

        self.nodes = []
        if not self.data:
            return

        # Start from root
        if self.show_root:
            self._flatten_node(self.data, depth=0, parent_lines=[])
        else:
            # Show children of root directly
            for i, child in enumerate(self.data.get("children", [])):
                is_last = i == len(self.data["children"]) - 1
                self._flatten_node(child, depth=0, parent_lines=[], is_last=is_last)

        # Update scroll manager
        self.scroll_manager.update_content_size(len(self.nodes))

        # Clamp highlighted index
        if self.highlighted_index >= len(self.nodes):
            self.highlighted_index = max(0, len(self.nodes) - 1)

    def _flatten_node(
        self, node: dict, depth: int, parent_lines: list[bool], is_last: bool = True
    ) -> None:
        """Recursively flatten a node and its children.

        Parameters
        ----------
        node : dict
            Node to flatten
        depth : int
            Depth level of this node
        parent_lines : list of bool
            List indicating which parent levels need vertical lines
        is_last : bool, optional
            Whether this is the last child of its parent (default: True)
        """
        node_id = node["id"]
        has_children = len(node.get("children", [])) > 0
        is_expanded = node_id in self.expanded_nodes

        # Add this node to the flattened list
        self.nodes.append(
            {
                "node": node,
                "depth": depth,
                "is_last": is_last,
                "parent_lines": parent_lines.copy(),
                "has_children": has_children,
                "is_expanded": is_expanded,
            }
        )

        # If expanded, add children
        if is_expanded and has_children:
            children = node.get("children", [])
            # Update parent_lines for children
            new_parent_lines = parent_lines + [not is_last]

            for i, child in enumerate(children):
                child_is_last = i == len(children) - 1
                self._flatten_node(child, depth + 1, new_parent_lines, child_is_last)

    def set_data(self, data: dict | list) -> None:
        """Update tree data and refresh display.

        Parameters
        ----------
        data : dict or list
            New tree data
        """
        self._raw_data = data
        self.data = self._normalize_data(data) if data else {}
        self._rebuild_nodes()

    def _save_highlight_state(self) -> None:
        """Save highlighted index to app state if available."""
        if self._state_dict is not None and self.highlight_state_key:
            self._state_dict[self.highlight_state_key] = self.highlighted_index

    def _save_scroll_state(self) -> None:
        """Save scroll position to app state if available."""
        if self._state_dict is not None and self.scroll_state_key:
            self._state_dict[self.scroll_state_key] = (
                self.scroll_manager.state.scroll_position
            )

    def _save_expand_state(self) -> None:
        """Save expansion state to app state if available."""
        if self._state_dict is not None and self.expand_state_key:
            self._state_dict[self.expand_state_key] = list(self.expanded_nodes)

    def _save_selected_state(self) -> None:
        """Save selected node ID to app state if available."""
        if self._state_dict is not None and self.selected_state_key:
            self._state_dict[self.selected_state_key] = self.selected_node_id

    def toggle_node(self, node_id: str) -> None:
        """Toggle expand/collapse state of a node.

        Parameters
        ----------
        node_id : str
            ID of node to toggle
        """
        if node_id in self.expanded_nodes:
            # Collapse
            self.expanded_nodes.remove(node_id)
            if self.on_collapse:
                self.on_collapse(node_id)
        else:
            # Expand
            self.expanded_nodes.add(node_id)
            if self.on_expand:
                self.on_expand(node_id)

        # Rebuild flattened nodes
        self._rebuild_nodes()
        self._save_expand_state()

    def expand_node(self, node_id: str) -> None:
        """Expand a node.

        Parameters
        ----------
        node_id : str
            ID of node to expand
        """
        if node_id not in self.expanded_nodes:
            self.expanded_nodes.add(node_id)
            if self.on_expand:
                self.on_expand(node_id)
            self._rebuild_nodes()
            self._save_expand_state()

    def collapse_node(self, node_id: str) -> None:
        """Collapse a node.

        Parameters
        ----------
        node_id : str
            ID of node to collapse
        """
        if node_id in self.expanded_nodes:
            self.expanded_nodes.remove(node_id)
            if self.on_collapse:
                self.on_collapse(node_id)
            self._rebuild_nodes()
            self._save_expand_state()

    def select_node(self, node_id: str) -> None:
        """Select a node.

        Parameters
        ----------
        node_id : str
            ID of node to select
        """
        self.selected_node_id = node_id
        self._save_selected_state()

        # Find node in flattened list and update highlighted index
        for i, node_info in enumerate(self.nodes):
            if node_info["node"]["id"] == node_id:
                self.highlighted_index = i
                self._save_highlight_state()
                break

        # Emit callback
        if self.on_select:
            # Find the actual node data
            node = self._find_node_by_id(self.data, node_id)
            if node:
                self.on_select(node)

    def _find_node_by_id(self, tree: dict, node_id: str) -> dict | None:
        """Find a node in the tree by ID.

        Parameters
        ----------
        tree : dict
            Tree to search
        node_id : str
            ID to find

        Returns
        -------
        dict or None
            Found node or None
        """
        if tree["id"] == node_id:
            return tree

        for child in tree.get("children", []):
            result = self._find_node_by_id(child, node_id)
            if result:
                return result

        return None

    def _get_tree_prefix(self, node_info: dict) -> str:
        """Generate tree drawing characters for a node.

        Parameters
        ----------
        node_info : dict
            Node information from flattened list

        Returns
        -------
        str
            Tree drawing prefix string
        """
        depth = node_info["depth"]
        is_last = node_info["is_last"]
        parent_lines = node_info["parent_lines"]

        if depth == 0:
            return ""

        prefix = ""

        # Determine the starting index for parent_lines
        # When show_root=True, parent_lines[0] represents root's continuation,
        # which is always False (root has no siblings), so we skip it
        offset = 1 if (self.show_root and depth > 1) else 0

        # Draw vertical lines for parent levels (depth - 1 columns)
        # Each level gets indent_size spaces
        indent = " " * self.indent_size
        for i in range(depth - 1):
            check_idx = i + offset
            if check_idx < len(parent_lines) and parent_lines[check_idx]:
                prefix += "\u2502" + indent  # │ + spaces
            else:
                prefix += " " + indent  # spaces only

        # Draw connector for this level
        if is_last:
            prefix += "\u2514\u2500 "  # └─ (last child corner)
        else:
            prefix += "\u251c\u2500 "  # ├─ (branch)

        return prefix

    def _get_expand_indicator(self, node_info: dict) -> str:
        """Get expand/collapse indicator for a node.

        Parameters
        ----------
        node_info : dict
            Node information from flattened list

        Returns
        -------
        str
            Expand indicator: "[+]", "[-]", or "   "
        """
        if not node_info["has_children"]:
            return "   "  # No children, no indicator

        if node_info["is_expanded"]:
            return "[-]"  # Expanded
        else:
            return "[+]"  # Collapsed

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for tree navigation.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        if not self.nodes:
            return False

        # Up arrow - move highlight up
        if key == Keys.UP:
            if self.highlighted_index > 0:
                self.highlighted_index -= 1
                self._save_highlight_state()
                # Auto-scroll to keep highlighted node visible
                visible_start, _ = self.scroll_manager.get_visible_range()
                if self.highlighted_index < visible_start:
                    self.scroll_manager.scroll_to(self.highlighted_index)
                    self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Down arrow - move highlight down
        elif key == Keys.DOWN:
            if self.highlighted_index < len(self.nodes) - 1:
                self.highlighted_index += 1
                # Save highlight state
                self._save_highlight_state()
                # Auto-scroll to keep highlighted node visible
                _, visible_end = self.scroll_manager.get_visible_range()
                if self.highlighted_index >= visible_end:
                    self.scroll_manager.scroll_to(
                        self.highlighted_index - self.height + 1
                    )
                    self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Left arrow - collapse or move to parent
        elif key == Keys.LEFT:
            if 0 <= self.highlighted_index < len(self.nodes):
                node_info = self.nodes[self.highlighted_index]
                node_id = node_info["node"]["id"]

                # If expanded, collapse it
                if node_info["is_expanded"]:
                    self.collapse_node(node_id)
                    return True
                # Otherwise, try to move to parent
                # (find first node at lower depth above current)
                elif node_info["depth"] > 0:
                    target_depth = node_info["depth"] - 1
                    for i in range(self.highlighted_index - 1, -1, -1):
                        if self.nodes[i]["depth"] == target_depth:
                            self.highlighted_index = i
                            self._save_highlight_state()
                            # Ensure visible
                            visible_start, _ = self.scroll_manager.get_visible_range()
                            if self.highlighted_index < visible_start:
                                self.scroll_manager.scroll_to(self.highlighted_index)
                                self._save_scroll_state()
                            return True
            return False

        # Right arrow - expand or move to first child
        elif key == Keys.RIGHT:
            if 0 <= self.highlighted_index < len(self.nodes):
                node_info = self.nodes[self.highlighted_index]
                node_id = node_info["node"]["id"]

                # If has children and collapsed, expand it
                if node_info["has_children"] and not node_info["is_expanded"]:
                    self.expand_node(node_id)
                    return True
                # If already expanded and has children, move to first child
                elif node_info["is_expanded"] and node_info["has_children"]:
                    if self.highlighted_index + 1 < len(self.nodes):
                        self.highlighted_index += 1
                        self._save_highlight_state()
                        # Ensure visible
                        _, visible_end = self.scroll_manager.get_visible_range()
                        if self.highlighted_index >= visible_end:
                            self.scroll_manager.scroll_to(
                                self.highlighted_index - self.height + 1
                            )
                            self._save_scroll_state()
                        return True
            return False

        # Enter or Space - toggle expand/collapse
        elif key == Keys.ENTER or key == Keys.SPACE:
            if 0 <= self.highlighted_index < len(self.nodes):
                node_info = self.nodes[self.highlighted_index]
                node_id = node_info["node"]["id"]

                # Toggle if has children
                if node_info["has_children"]:
                    self.toggle_node(node_id)
                    return True

                # Also select the node
                self.select_node(node_id)
                return True
            return False

        # Home - jump to top
        elif key == Keys.HOME:
            self.highlighted_index = 0
            self._save_highlight_state()
            self.scroll_manager.scroll_to(0)
            self._save_scroll_state()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # End - jump to bottom
        elif key == Keys.END:
            self.highlighted_index = len(self.nodes) - 1
            self._save_highlight_state()
            self.scroll_manager.scroll_to_bottom()
            self._save_scroll_state()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # Page Up
        elif key == Keys.PAGE_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_up()
            # Move highlight by same amount
            delta = old_pos - self.scroll_manager.state.scroll_position
            self.highlighted_index = max(0, self.highlighted_index - delta)
            self._save_highlight_state()
            self._save_scroll_state()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # Page Down
        elif key == Keys.PAGE_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_down()
            # Move highlight by same amount
            delta = self.scroll_manager.state.scroll_position - old_pos
            self.highlighted_index = min(
                len(self.nodes) - 1, self.highlighted_index + delta
            )
            self._save_highlight_state()
            self._save_scroll_state()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

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
                self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Handle clicks
        if event.type == MouseEventType.CLICK:
            if not self.bounds:
                return False

            relative_x = event.x - self.bounds.x
            relative_y = event.y - self.bounds.y

            # Check if click is within tree area
            if 0 <= relative_y < self.height and 0 <= relative_x < self.width:
                visible_start, visible_end = self.scroll_manager.get_visible_range()
                clicked_index = visible_start + relative_y

                if 0 <= clicked_index < len(self.nodes):
                    node_info = self.nodes[clicked_index]
                    node_id = node_info["node"]["id"]

                    # Update highlighted index
                    self.highlighted_index = clicked_index
                    self._save_highlight_state()

                    # Check if clicked on expand indicator
                    # Line structure: [selection_marker(2)] [tree_prefix] [expand_indicator(3)] [ ] [label]
                    selection_marker_len = 2  # "> " or "  "
                    prefix_len = visible_length(self._get_tree_prefix(node_info))
                    expand_start = selection_marker_len + prefix_len
                    expand_end = expand_start + 3

                    if (
                        node_info["has_children"]
                        and expand_start <= relative_x < expand_end
                    ):
                        # Clicked on expand indicator
                        self.toggle_node(node_id)
                    else:
                        # Clicked on node label - select it
                        self.select_node(node_id)

                    return True

        return False

    def render(self) -> str:
        """Render the tree.

        Returns
        -------
        str
            Rendered tree as multi-line string
        """
        if not self.nodes:
            # Empty tree
            empty_msg = "Empty tree"
            return empty_msg.ljust(self.width)

        # Calculate effective width for tree rendering
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        tree_width = self.width - 1 if needs_scrollbar else self.width

        # Get visible nodes
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_nodes = self.nodes[visible_start:visible_end]

        # Render each visible node
        lines = []
        for i, node_info in enumerate(visible_nodes):
            node_index = visible_start + i
            is_highlighted = node_index == self.highlighted_index
            is_selected = node_info["node"]["id"] == self.selected_node_id

            # Build line
            line = self._render_node_line(
                node_info, is_highlighted, is_selected, tree_width
            )
            lines.append(line)

        # Pad to height
        while len(lines) < self.height:
            lines.append(" " * tree_width)

        # Add scrollbar if needed
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, self.height
            )

            for i in range(len(lines)):
                line = lines[i]
                line_len = visible_length(line)
                if line_len < tree_width:
                    line = line + " " * (tree_width - line_len)
                lines[i] = line + scrollbar_chars[i]
        else:
            # No scrollbar - ensure lines are padded to full width
            for i in range(len(lines)):
                line = lines[i]
                line_len = visible_length(line)
                if line_len < self.width:
                    lines[i] = line + " " * (self.width - line_len)

        return "\n".join(lines)

    def _render_node_line(
        self, node_info: dict, is_highlighted: bool, is_selected: bool, width: int
    ) -> str:
        """Render a single tree node line.

        Parameters
        ----------
        node_info : dict
            Node information from flattened list
        is_highlighted : bool
            Whether this node is highlighted (keyboard focus)
        is_selected : bool
            Whether this node is selected
        width : int
            Available width for rendering

        Returns
        -------
        str
            Rendered line with tree characters and styling
        """
        # Get components
        tree_prefix = self._get_tree_prefix(node_info)
        expand_indicator = self._get_expand_indicator(node_info)
        label = node_info["node"]["label"]

        # Selection marker
        selection_marker = "> " if is_selected else "  "

        # Build line: [selection] [tree_prefix] [expand] [label]
        line_parts = [selection_marker, tree_prefix, expand_indicator, " ", label]
        line = "".join(line_parts)

        # Clip to width
        line_len = visible_length(line)
        if line_len > width:
            line = clip_to_width(line, width, ellipsis="...")
        else:
            line = line + " " * (width - line_len)

        # Apply styling for highlighted node
        if is_highlighted and self.focused:
            # Use reverse video for highlighted node
            from ..terminal.ansi import ANSIStyle

            line = f"{ANSIStyle.REVERSE}{line}{ANSIStyle.RESET}"

        return line
