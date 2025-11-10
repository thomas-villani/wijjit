"""Display UI elements for Wijjit applications.

This module provides display-oriented elements like tables and lists.
"""

from collections.abc import Callable
from io import StringIO
from typing import Literal

from rich import box
from rich.console import Console
from rich.table import Table as RichTable

from wijjit.elements.base import Element, ElementType
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

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
            from wijjit.terminal.ansi import ANSIStyle

            line = f"{ANSIStyle.REVERSE}{line}{ANSIStyle.RESET}"

        return line


class ProgressBar(Element):
    """Progress bar element for displaying progress of operations.

    This element provides a visual progress indicator with support for:
    - Multiple display styles (filled bar, percentage only, gradient, custom)
    - Optional coloring
    - Customizable fill and empty characters
    - Percentage display

    Parameters
    ----------
    id : str, optional
        Element identifier
    value : float, optional
        Current progress value (default: 0)
    max : float, optional
        Maximum progress value (default: 100)
    width : int, optional
        Display width in columns (default: 40)
    style : str, optional
        Display style: "filled", "percentage", "gradient", "custom" (default: "filled")
    color : str, optional
        Color name for the progress bar (default: None)
    show_percentage : bool, optional
        Whether to show percentage text (default: True for filled/gradient, False for percentage style)
    fill_char : str, optional
        Character for filled portion (default: block character)
    empty_char : str, optional
        Character for empty portion (default: light shade character)

    Attributes
    ----------
    value : float
        Current progress value
    max : float
        Maximum progress value
    width : int
        Display width
    style : str
        Display style
    color : str or None
        Color name
    show_percentage : bool
        Whether to show percentage
    fill_char : str
        Fill character
    empty_char : str
        Empty character
    """

    def __init__(
        self,
        id: str | None = None,
        value: float = 0,
        max: float = 100,
        width: int = 40,
        style: Literal["filled", "percentage", "gradient", "custom"] = "filled",
        color: str | None = None,
        show_percentage: bool | None = None,
        fill_char: str | None = None,
        empty_char: str | None = None,
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = False  # Progress bars are not interactive

        # Progress properties
        self.value = float(value)
        self.max = float(max)
        self.width = width
        self.style = style
        self.color = color

        # Default show_percentage based on style
        if show_percentage is None:
            self.show_percentage = style in ("filled", "gradient", "custom")
        else:
            self.show_percentage = show_percentage

        # Default characters based on unicode support
        from wijjit.terminal.ansi import supports_unicode

        if supports_unicode():
            self.fill_char = (
                fill_char if fill_char is not None else "\u2588"
            )  # Full block
            self.empty_char = (
                empty_char if empty_char is not None else "\u2591"
            )  # Light shade
        else:
            self.fill_char = fill_char if fill_char is not None else "#"
            self.empty_char = empty_char if empty_char is not None else "-"

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    def set_progress(self, value: float) -> None:
        """Update progress value.

        Parameters
        ----------
        value : float
            New progress value
        """
        self.value = float(value)

    def get_percentage(self) -> float:
        """Get current progress as percentage.

        Returns
        -------
        float
            Progress percentage (0-100)
        """
        if self.max <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.value / self.max) * 100.0))

    def _get_color_for_percentage(self, percentage: float) -> str | None:
        """Get color based on percentage for gradient style.

        Parameters
        ----------
        percentage : float
            Current percentage (0-100)

        Returns
        -------
        str or None
            ANSI color code
        """
        from wijjit.terminal.ansi import ANSIColor

        if percentage < 33:
            return ANSIColor.RED
        elif percentage < 66:
            return ANSIColor.YELLOW
        else:
            return ANSIColor.GREEN

    def _render_filled_bar(self) -> str:
        """Render filled block style progress bar.

        Returns
        -------
        str
            Rendered progress bar
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        percentage = self.get_percentage()

        # Calculate percentage text first to know its exact width
        if self.show_percentage:
            percentage_text = f" {percentage:.1f}%"
            percentage_width = len(percentage_text)
            bar_width = self.width - percentage_width
        else:
            bar_width = self.width

        # Ensure minimum bar width
        bar_width = max(1, bar_width)

        # Calculate filled and empty portions
        filled_width = int((percentage / 100.0) * bar_width)
        empty_width = bar_width - filled_width

        # Build bar
        bar = self.fill_char * filled_width + self.empty_char * empty_width

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                bar = colorize(bar, color=color_code)

        # Add percentage text if enabled
        if self.show_percentage:
            return bar + percentage_text
        else:
            return bar

    def _render_percentage_only(self) -> str:
        """Render percentage-only style.

        Returns
        -------
        str
            Rendered percentage text
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        percentage = self.get_percentage()
        text = f"Progress: {percentage:5.1f}%"

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                text = colorize(text, color=color_code)

        # Pad to width
        if len(text) < self.width:
            text = text.ljust(self.width)
        else:
            text = clip_to_width(text, self.width)

        return text

    def _render_gradient_bar(self) -> str:
        """Render gradient color style progress bar.

        The color changes based on completion percentage:
        - 0-33%: Red
        - 33-66%: Yellow
        - 66-100%: Green

        Returns
        -------
        str
            Rendered progress bar with gradient color
        """
        from wijjit.terminal.ansi import colorize

        percentage = self.get_percentage()

        # Calculate percentage text first to know its exact width
        if self.show_percentage:
            percentage_text = f" {percentage:.1f}%"
            percentage_width = len(percentage_text)
            bar_width = self.width - percentage_width
        else:
            bar_width = self.width

        bar_width = max(1, bar_width)

        # Calculate filled and empty portions
        filled_width = int((percentage / 100.0) * bar_width)
        empty_width = bar_width - filled_width

        # Build bar
        bar = self.fill_char * filled_width + self.empty_char * empty_width

        # Apply gradient color
        gradient_color = self._get_color_for_percentage(percentage)
        if gradient_color:
            bar = colorize(bar, color=gradient_color)

        # Add percentage text
        if self.show_percentage:
            return bar + percentage_text
        else:
            return bar

    def _render_custom_bar(self) -> str:
        """Render custom character style progress bar.

        Uses user-specified fill_char and empty_char.

        Returns
        -------
        str
            Rendered progress bar
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        percentage = self.get_percentage()

        # Calculate percentage text first to know its exact width
        if self.show_percentage:
            percentage_text = f" {percentage:.1f}%"
            percentage_width = len(percentage_text)
            bar_width = self.width - percentage_width
        else:
            bar_width = self.width

        bar_width = max(1, bar_width)

        # Calculate filled and empty portions
        filled_width = int((percentage / 100.0) * bar_width)
        empty_width = bar_width - filled_width

        # Build bar with custom characters
        bar = self.fill_char * filled_width + self.empty_char * empty_width

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                bar = colorize(bar, color=color_code)

        # Add percentage text
        if self.show_percentage:
            return bar + percentage_text
        else:
            return bar

    def render(self) -> str:
        """Render the progress bar.

        Returns
        -------
        str
            Rendered progress bar as single-line string
        """
        if self.style == "filled":
            return self._render_filled_bar()
        elif self.style == "percentage":
            return self._render_percentage_only()
        elif self.style == "gradient":
            return self._render_gradient_bar()
        elif self.style == "custom":
            return self._render_custom_bar()
        else:
            # Default to filled style
            return self._render_filled_bar()


# Spinner animation frames
SPINNER_FRAMES = {
    # Braille dots spinner
    "dots": [
        "\u280b",
        "\u2819",
        "\u2839",
        "\u2838",
        "\u283c",
        "\u2834",
        "\u2826",
        "\u2827",
        "\u2807",
        "\u280f",
    ],
    "dots_ascii": ["/", "-", "\\", "|"],
    # Rotating line
    "line": ["|", "/", "-", "\\"],
    # Bouncing braille bar
    "bouncing": [
        "\u28fe",
        "\u28fd",
        "\u28fb",
        "\u28bf",
        "\u287f",
        "\u28df",
        "\u28ef",
        "\u28f7",
    ],
    "bouncing_ascii": ["<", "<<", "<<<", ">>", ">"],
    # Clock face
    "clock": [
        "\U0001f550",
        "\U0001f551",
        "\U0001f552",
        "\U0001f553",
        "\U0001f554",
        "\U0001f555",
        "\U0001f556",
        "\U0001f557",
        "\U0001f558",
        "\U0001f559",
        "\U0001f55a",
        "\U0001f55b",
    ],
    "clock_ascii": ["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
}


class Spinner(Element):
    """Spinner element for displaying indefinite loading animation.

    This element provides an animated spinner indicator with support for:
    - Multiple animation styles (dots, line, bouncing, clock)
    - Unicode detection with ASCII fallback
    - Optional label text
    - Optional coloring
    - Active/inactive state control

    Parameters
    ----------
    id : str, optional
        Element identifier
    active : bool, optional
        Whether spinner is active and animating (default: True)
    style : str, optional
        Animation style: "dots", "line", "bouncing", "clock" (default: "dots")
    label : str, optional
        Label text to display next to spinner (default: "")
    color : str, optional
        Color name for the spinner (default: None)
    frame_index : int, optional
        Current animation frame index (default: 0)

    Attributes
    ----------
    active : bool
        Whether spinner is active
    style : str
        Animation style
    label : str
        Label text
    color : str or None
        Color name
    frame_index : int
        Current frame index
    """

    def __init__(
        self,
        id: str | None = None,
        active: bool = True,
        style: Literal["dots", "line", "bouncing", "clock"] = "dots",
        label: str = "",
        color: str | None = None,
        frame_index: int = 0,
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = False  # Spinners are not interactive

        # Spinner properties
        self.active = active
        self.style = style
        self.label = label
        self.color = color
        self.frame_index = frame_index

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    def next_frame(self) -> None:
        """Advance to the next animation frame.

        This method increments the frame index and wraps around to 0
        when reaching the end of the animation sequence.
        """
        frames = self._get_style_frames(self.style)
        self.frame_index = (self.frame_index + 1) % len(frames)

    def _get_style_frames(self, style: str) -> list[str]:
        """Get animation frames for a style, with Unicode fallback.

        Parameters
        ----------
        style : str
            Animation style name

        Returns
        -------
        list of str
            List of frame characters
        """
        from wijjit.terminal.ansi import supports_unicode

        # Check if we should use ASCII fallback
        if not supports_unicode():
            # Use ASCII fallback versions
            ascii_style = f"{style}_ascii"
            if ascii_style in SPINNER_FRAMES:
                return SPINNER_FRAMES[ascii_style]
            # If no ASCII version, default to line
            return SPINNER_FRAMES["line"]

        # Use Unicode version
        if style in SPINNER_FRAMES:
            return SPINNER_FRAMES[style]
        else:
            # Default to dots if style not found
            return SPINNER_FRAMES["dots"]

    def _get_current_frame(self) -> str:
        """Get the current animation frame character.

        Returns
        -------
        str
            Current frame character
        """
        frames = self._get_style_frames(self.style)
        # Ensure frame_index is within bounds
        frame_idx = self.frame_index % len(frames)
        return frames[frame_idx]

    def render(self) -> str:
        """Render the spinner.

        Returns
        -------
        str
            Rendered spinner with optional label as single-line string
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        # If not active, return empty space or just label
        if not self.active:
            if self.label:
                return self.label
            else:
                return ""

        # Get current frame
        frame = self._get_current_frame()

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                frame = colorize(frame, color=color_code)

        # Combine frame and label
        if self.label:
            return f"{frame} {self.label}"
        else:
            return frame


class MarkdownView(Element):
    """Markdown content display element with Rich integration.

    This element renders markdown content using Rich's Markdown renderer,
    with support for scrolling, borders, and mouse/keyboard interaction.

    Parameters
    ----------
    id : str, optional
        Element identifier
    content : str, optional
        Markdown content to display (default: "")
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 20)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)

    Attributes
    ----------
    content : str
        Markdown content
    width : int
        Display width
    height : int
        Display height
    show_scrollbar : bool
        Whether scrollbar is visible
    border_style : str
        Border style
    title : str or None
        Border title
    scroll_manager : ScrollManager
        Manages scrolling of content
    rendered_lines : list of str
        Cached rendered content lines
    """

    def __init__(
        self,
        id: str | None = None,
        content: str = "",
        width: int = 60,
        height: int = 20,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and display properties
        self.content = content
        self.width = width
        self.height = height
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title

        # Rendered content cache
        self.rendered_lines: list[str] = []

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # Callbacks
        self.on_scroll: Callable[[int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence
        self.scroll_state_key: str | None = None

        # Dynamic sizing flag (set by template tag)
        self._dynamic_sizing: bool = False

    def set_bounds(self, bounds) -> None:
        """Set bounds and dynamically resize if needed.

        Parameters
        ----------
        bounds : Bounds
            New bounds for the element
        """
        super().set_bounds(bounds)

        # If dynamic sizing is enabled, resize the element to fit the bounds
        if self._dynamic_sizing and bounds:
            new_width = bounds.width
            new_height = bounds.height

            # Account for borders
            if self.border_style != "none":
                new_width = max(3, new_width - 2)  # Minimum width for borders
                new_height = max(3, new_height - 2)  # Minimum height for borders

            # Update dimensions if changed
            if new_width != self.width or new_height != self.height:
                self.width = new_width
                self.height = new_height

                # Re-render content with new dimensions
                self._render_content()

                # Update scroll manager with new viewport size
                self.scroll_manager.content_size = len(self.rendered_lines)
                self.scroll_manager.viewport_size = self._get_content_height()

    def _get_content_height(self) -> int:
        """Calculate content area height accounting for borders.

        Returns
        -------
        int
            Content height in rows
        """
        if self.border_style != "none":
            # Borders take 2 rows (top and bottom)
            return max(1, self.height - 2)
        return self.height

    def _get_content_width(self) -> int:
        """Calculate content area width accounting for borders and scrollbar.

        Returns
        -------
        int
            Content width in columns
        """
        content_width = self.width

        # Account for borders
        if self.border_style != "none":
            content_width -= 2  # Left and right borders

        # Account for scrollbar
        # During initialization, reserve space if show_scrollbar is True
        # After initialization, only reserve if actually scrollable
        if self.show_scrollbar:
            if not hasattr(self, "scroll_manager"):
                # During initialization - always reserve space
                content_width -= 1
            elif self.scroll_manager.state.is_scrollable:
                # After initialization - only if content is scrollable
                content_width -= 1

        return max(1, content_width)

    def _render_content(self) -> None:
        """Render markdown content to ANSI strings using Rich.

        Updates the rendered_lines cache with the current content.
        """
        from io import StringIO

        from rich.console import Console
        from rich.markdown import Markdown

        # Get content width for rendering
        content_width = self._get_content_width()

        # Render markdown using Rich
        md = Markdown(self.content)
        string_buffer = StringIO()
        console = Console(
            file=string_buffer,
            width=content_width,
            legacy_windows=False,
            force_terminal=True,
        )
        console.print(md)
        output = string_buffer.getvalue()

        # Split into lines
        self.rendered_lines = output.rstrip("\n").split("\n")

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [""]

    def set_content(self, content: str) -> None:
        """Update markdown content and re-render.

        Parameters
        ----------
        content : str
            New markdown content
        """
        self.content = content
        self._render_content()

        # Update scroll manager with new content size
        self.scroll_manager.update_content_size(len(self.rendered_lines))

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore
        """
        self.scroll_manager.scroll_to(position)

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
        if not self.rendered_lines:
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
        """Handle mouse input for scrolling.

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

        return False

    def _render_with_border(self, content_lines: list[str]) -> list[str]:
        """Render content with border.

        Parameters
        ----------
        content_lines : list of str
            Content lines to wrap with border

        Returns
        -------
        list of str
            Lines with border added
        """
        from wijjit.layout.frames import BORDER_CHARS, BorderStyle
        from wijjit.terminal.ansi import ANSIColor, ANSIStyle

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS[style]

        # Choose border color based on focus
        if self.focused:
            border_color = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}"
            reset = ANSIStyle.RESET
        else:
            border_color = ""
            reset = ""

        # Calculate content width (total width - 2 for borders)
        content_width = self.width - 2

        # Build top border
        if self.title:
            # Border with title
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            if title_len < content_width:
                remaining = content_width - title_len
                left_line = chars["h"] * (remaining // 2)
                right_line = chars["h"] * (remaining - len(left_line))
                top_line = f"{border_color}{chars['tl']}{left_line}{title_text}{right_line}{chars['tr']}{reset}"
            else:
                # Title too long, just show border
                top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"
        else:
            # Border without title
            top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"

        # Build bottom border
        bottom_line = f"{border_color}{chars['bl']}{chars['h'] * content_width}{chars['br']}{reset}"

        # Wrap content lines with borders
        bordered_lines = [top_line]
        for line in content_lines:
            # Ensure line is padded to content width
            line_len = visible_length(line)
            if line_len < content_width:
                line = line + " " * (content_width - line_len)
            elif line_len > content_width:
                line = clip_to_width(line, content_width, ellipsis="")

            bordered_lines.append(
                f"{border_color}{chars['v']}{reset}{line}{border_color}{chars['v']}{reset}"
            )

        bordered_lines.append(bottom_line)

        return bordered_lines

    def render(self) -> str:
        """Render the markdown view.

        Returns
        -------
        str
            Rendered markdown view as multi-line string
        """
        content_height = self._get_content_height()
        content_width = self._get_content_width()

        # Get visible lines
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_lines = self.rendered_lines[visible_start:visible_end]

        # Pad or trim to exact content height
        if len(visible_lines) < content_height:
            visible_lines.extend(
                ["" for _ in range(content_height - len(visible_lines))]
            )
        else:
            visible_lines = visible_lines[:content_height]

        # Ensure all lines are padded to content width
        for i in range(len(visible_lines)):
            line = visible_lines[i]
            line_len = visible_length(line)
            if line_len < content_width:
                visible_lines[i] = line + " " * (content_width - line_len)
            elif line_len > content_width:
                visible_lines[i] = clip_to_width(line, content_width, ellipsis="")

        # Add scrollbar if needed
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, content_height
            )

            for i in range(len(visible_lines)):
                visible_lines[i] = visible_lines[i] + scrollbar_chars[i]

        # Add borders if requested
        if self.border_style != "none":
            final_lines = self._render_with_border(visible_lines)
        else:
            final_lines = visible_lines

        return "\n".join(final_lines)


class ListView(Element):
    """ListView element for displaying lists with bullets, numbers, or details.

    This element provides a display for lists with support for:
    - Multiple bullet styles (bullets, dashes, numbers, or custom characters)
    - Plain lists without bullets
    - Details mode for definition-style lists with dimmed, indented details
    - Optional horizontal dividers between items
    - Scrolling for long lists
    - Borders with optional titles
    - Mouse and keyboard interaction for scrolling

    Parameters
    ----------
    id : str, optional
        Element identifier
    items : list, optional
        List items (strings, 2-tuples, or dicts) (default: [])
    width : int, optional
        Display width in columns (default: 40)
    height : int, optional
        Display height in rows (default: 10)
    bullet : str, optional
        Bullet style: "bullet", "dash", "number",
        custom character, or None for no bullets (default: "bullet")
    show_dividers : bool, optional
        Whether to show horizontal lines between items (default: False)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)
    indent_details : int, optional
        Number of spaces to indent details text (default: 2)
    dim_details : bool, optional
        Whether to dim details text color (default: True)

    Attributes
    ----------
    items : list
        Normalized list items
    width : int
        Display width
    height : int
        Display height
    bullet : str or None
        Bullet style or character
    show_dividers : bool
        Whether dividers are shown
    show_scrollbar : bool
        Whether scrollbar is visible
    border_style : str
        Border style
    title : str or None
        Border title
    indent_details : int
        Details indentation
    dim_details : bool
        Whether details are dimmed
    scroll_manager : ScrollManager
        Manages scrolling of content
    rendered_lines : list of str
        Cached rendered content lines

    Notes
    -----
    List items can be specified as:
    - Strings: ["Item 1", "Item 2"]
    - 2-tuples: [("Label", "Details"), ...]
    - Dicts: [{"label": "Label", "details": "Details"}, ...]

    Details can be multi-line (separated by newlines) and will be
    indented and optionally dimmed.

    Examples
    --------
    Simple bulleted list:
    >>> listview = ListView(items=["Apple", "Banana", "Cherry"])

    Numbered list:
    >>> listview = ListView(items=["First", "Second", "Third"], bullet="number")

    Definition list with details:
    >>> items = [
    ...     ("Python", "A high-level programming language"),
    ...     ("JavaScript", "A dynamic scripting language")
    ... ]
    >>> listview = ListView(items=items, bullet="dash")
    """

    def __init__(
        self,
        id: str | None = None,
        items: list | None = None,
        width: int = 40,
        height: int = 10,
        bullet: str | None = "bullet",
        show_dividers: bool = False,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        indent_details: int = 2,
        dim_details: bool = True,
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and display properties
        self._raw_items = items or []
        self.items = self._normalize_items(self._raw_items)
        self.width = width
        self.height = height
        self.bullet = bullet
        self.show_dividers = show_dividers
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title
        self.indent_details = indent_details
        self.dim_details = dim_details

        # Rendered content cache
        self.rendered_lines: list[str] = []

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # Callbacks
        self.on_scroll: Callable[[int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence
        self.scroll_state_key: str | None = None

    def _get_content_height(self) -> int:
        """Calculate content area height accounting for borders.

        Returns
        -------
        int
            Content height in rows
        """
        if self.border_style != "none":
            # Borders take 2 rows (top and bottom)
            return max(1, self.height - 2)
        return self.height

    def _get_content_width(self) -> int:
        """Calculate content area width accounting for borders and scrollbar.

        Returns
        -------
        int
            Content width in columns
        """
        content_width = self.width

        # Account for borders
        if self.border_style != "none":
            content_width -= 2  # Left and right borders

        # Account for scrollbar
        if self.show_scrollbar:
            if not hasattr(self, "scroll_manager"):
                # During initialization - always reserve space
                content_width -= 1
            elif self.scroll_manager.state.is_scrollable:
                # After initialization - only if content is scrollable
                content_width -= 1

        return max(1, content_width)

    def _normalize_items(self, items: list) -> list[dict]:
        """Normalize items to internal format.

        Parameters
        ----------
        items : list
            Raw items (strings, tuples, or dicts)

        Returns
        -------
        list of dict
            Normalized items with 'label' and 'details' keys

        Notes
        -----
        Supports three input formats:
        - Strings: ["Item 1", "Item 2"]
        - 2-tuples: [("Label", "Details"), ...]
        - Dicts: [{"label": "Label", "details": "Details"}, ...]
        """
        normalized = []
        for item in items:
            if isinstance(item, dict):
                # Dict format
                normalized.append(
                    {
                        "label": str(item.get("label", "")),
                        "details": (
                            str(item.get("details", ""))
                            if item.get("details")
                            else None
                        ),
                    }
                )
            elif isinstance(item, tuple) and len(item) == 2:
                # 2-tuple format
                normalized.append({"label": str(item[0]), "details": str(item[1])})
            else:
                # String or other format - use as label
                normalized.append({"label": str(item), "details": None})

        return normalized

    def _get_bullet_char(self, index: int) -> str:
        """Get bullet character for an item.

        Parameters
        ----------
        index : int
            Item index (0-based)

        Returns
        -------
        str
            Bullet character or prefix string
        """
        from wijjit.terminal.ansi import supports_unicode

        if self.bullet == "bullet":
            # Use unicode bullet if supported, otherwise asterisk
            return "• " if supports_unicode() else "* "
        elif self.bullet == "dash":
            return "- "
        elif self.bullet == "number":
            return f"{index + 1}. "
        elif self.bullet is None:
            return ""
        else:
            # Custom character
            # Ensure it has a space after if it's not empty
            return f"{self.bullet} " if self.bullet else ""

    def _render_content(self) -> None:
        """Render list items to ANSI strings.

        Updates the rendered_lines cache with the current items.
        """
        from wijjit.terminal.ansi import ANSIStyle, supports_unicode

        self.rendered_lines = []
        content_width = self._get_content_width()

        for i, item in enumerate(self.items):
            # Render main label with bullet
            bullet = self._get_bullet_char(i)
            label = item["label"]

            # Calculate available width for label (account for bullet)
            bullet_width = visible_length(bullet)
            label_width = content_width - bullet_width

            # Clip label if too long
            if visible_length(label) > label_width:
                label = clip_to_width(label, label_width, ellipsis="...")

            # Build label line
            label_line = bullet + label
            self.rendered_lines.append(label_line)

            # Render details if present
            if item["details"]:
                details = item["details"]
                indent = " " * self.indent_details

                # Split details into multiple lines
                detail_lines = details.split("\n")

                for detail_line in detail_lines:
                    # Calculate available width for details (account for indent)
                    detail_width = content_width - self.indent_details

                    # Clip detail if too long
                    if visible_length(detail_line) > detail_width:
                        detail_line = clip_to_width(
                            detail_line, detail_width, ellipsis="..."
                        )

                    # Apply dim styling if enabled
                    if self.dim_details:
                        detail_line = f"{ANSIStyle.DIM}{detail_line}{ANSIStyle.RESET}"

                    # Build detail line with indent
                    full_detail_line = indent + detail_line
                    self.rendered_lines.append(full_detail_line)

            # Add divider if requested and not last item
            if self.show_dividers and i < len(self.items) - 1:
                # Horizontal line divider with unicode support fallback
                divider_char = "─" if supports_unicode() else "-"
                divider = divider_char * content_width
                self.rendered_lines.append(divider)

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [""]

    def set_items(self, items: list) -> None:
        """Update list items and re-render.

        Parameters
        ----------
        items : list
            New list items (strings, tuples, or dicts)
        """
        self._raw_items = items
        self.items = self._normalize_items(items)
        self._render_content()

        # Update scroll manager with new content size
        self.scroll_manager.update_content_size(len(self.rendered_lines))

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore
        """
        self.scroll_manager.scroll_to(position)

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
        if not self.rendered_lines:
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
        """Handle mouse input for scrolling.

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

        return False

    def _render_with_border(self, content_lines: list[str]) -> list[str]:
        """Render content with border.

        Parameters
        ----------
        content_lines : list of str
            Content lines to wrap with border

        Returns
        -------
        list of str
            Lines with border added
        """
        from wijjit.layout.frames import BORDER_CHARS, BorderStyle
        from wijjit.terminal.ansi import ANSIColor, ANSIStyle

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS[style]

        # Choose border color based on focus
        if self.focused:
            border_color = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}"
            reset = ANSIStyle.RESET
        else:
            border_color = ""
            reset = ""

        # Calculate content width (total width - 2 for borders)
        content_width = self.width - 2

        # Build top border
        if self.title:
            # Border with title
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            if title_len < content_width:
                remaining = content_width - title_len
                left_line = chars["h"] * (remaining // 2)
                right_line = chars["h"] * (remaining - len(left_line))
                top_line = f"{border_color}{chars['tl']}{left_line}{title_text}{right_line}{chars['tr']}{reset}"
            else:
                # Title too long, just show border
                top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"
        else:
            # Border without title
            top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"

        # Build bottom border
        bottom_line = f"{border_color}{chars['bl']}{chars['h'] * content_width}{chars['br']}{reset}"

        # Wrap content lines with borders
        bordered_lines = [top_line]
        for line in content_lines:
            # Ensure line is padded to content width
            line_len = visible_length(line)
            if line_len < content_width:
                line = line + " " * (content_width - line_len)
            elif line_len > content_width:
                line = clip_to_width(line, content_width, ellipsis="")

            bordered_lines.append(
                f"{border_color}{chars['v']}{reset}{line}{border_color}{chars['v']}{reset}"
            )

        bordered_lines.append(bottom_line)

        return bordered_lines

    def render(self) -> str:
        """Render the list view.

        Returns
        -------
        str
            Rendered list view as multi-line string
        """
        content_height = self._get_content_height()
        content_width = self._get_content_width()

        # Get visible lines
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_lines = self.rendered_lines[visible_start:visible_end]

        # Pad or trim to exact content height
        if len(visible_lines) < content_height:
            visible_lines.extend(
                ["" for _ in range(content_height - len(visible_lines))]
            )
        else:
            visible_lines = visible_lines[:content_height]

        # Ensure all lines are padded to content width
        for i in range(len(visible_lines)):
            line = visible_lines[i]
            line_len = visible_length(line)
            if line_len < content_width:
                visible_lines[i] = line + " " * (content_width - line_len)
            elif line_len > content_width:
                visible_lines[i] = clip_to_width(line, content_width, ellipsis="")

        # Add scrollbar if needed
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, content_height
            )

            for i in range(len(visible_lines)):
                visible_lines[i] = visible_lines[i] + scrollbar_chars[i]

        # Add borders if requested
        if self.border_style != "none":
            final_lines = self._render_with_border(visible_lines)
        else:
            final_lines = visible_lines

        return "\n".join(final_lines)


class CodeBlock(Element):
    """Code display element with syntax highlighting via Rich.

    This element renders code with syntax highlighting using Rich's Syntax
    renderer, with support for scrolling, borders, and mouse/keyboard interaction.

    Parameters
    ----------
    id : str, optional
        Element identifier
    code : str, optional
        Code content to display (default: "")
    language : str, optional
        Programming language for syntax highlighting (default: "python")
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 20)
    show_line_numbers : bool, optional
        Whether to show line numbers (default: True)
    line_number_start : int, optional
        Starting line number (default: 1)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)
    theme : str, optional
        Syntax highlighting theme (default: "monokai")

    Attributes
    ----------
    code : str
        Code content
    language : str
        Programming language
    width : int
        Display width
    height : int
        Display height
    show_line_numbers : bool
        Whether line numbers are shown
    line_number_start : int
        Starting line number
    show_scrollbar : bool
        Whether scrollbar is visible
    border_style : str
        Border style
    title : str or None
        Border title
    theme : str
        Syntax highlighting theme
    scroll_manager : ScrollManager
        Manages scrolling of content
    rendered_lines : list of str
        Cached rendered content lines
    """

    def __init__(
        self,
        id: str | None = None,
        code: str = "",
        language: str = "python",
        width: int = 60,
        height: int = 20,
        show_line_numbers: bool = True,
        line_number_start: int = 1,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        theme: str = "monokai",
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and display properties
        self.code = code
        self.language = language
        self.width = width
        self.height = height
        self.show_line_numbers = show_line_numbers
        self.line_number_start = line_number_start
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title
        self.theme = theme

        # Rendered content cache
        self.rendered_lines: list[str] = []

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # Callbacks
        self.on_scroll: Callable[[int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence
        self.scroll_state_key: str | None = None

    def _get_content_height(self) -> int:
        """Calculate content area height accounting for borders.

        Returns
        -------
        int
            Content height in rows
        """
        if self.border_style != "none":
            # Borders take 2 rows (top and bottom)
            return max(1, self.height - 2)
        return self.height

    def _get_content_width(self) -> int:
        """Calculate content area width accounting for borders and scrollbar.

        Returns
        -------
        int
            Content width in columns
        """
        content_width = self.width

        # Account for borders
        if self.border_style != "none":
            content_width -= 2  # Left and right borders

        # Account for scrollbar
        # During initialization, reserve space if show_scrollbar is True
        # After initialization, only reserve if actually scrollable
        if self.show_scrollbar:
            if not hasattr(self, "scroll_manager"):
                # During initialization - always reserve space
                content_width -= 1
            elif self.scroll_manager.state.is_scrollable:
                # After initialization - only if content is scrollable
                content_width -= 1

        return max(1, content_width)

    def _render_content(self) -> None:
        """Render code with syntax highlighting to ANSI strings using Rich.

        Updates the rendered_lines cache with the current content.
        """
        from io import StringIO

        from rich.console import Console
        from rich.syntax import Syntax

        # Get content width for rendering
        content_width = self._get_content_width()

        # Render code using Rich Syntax
        syntax = Syntax(
            self.code,
            self.language,
            theme=self.theme,
            line_numbers=self.show_line_numbers,
            start_line=self.line_number_start,
            word_wrap=False,
        )

        string_buffer = StringIO()
        console = Console(
            file=string_buffer,
            width=content_width,
            legacy_windows=False,
            force_terminal=True,
        )
        console.print(syntax)
        output = string_buffer.getvalue()

        # Split into lines
        self.rendered_lines = output.rstrip("\n").split("\n")

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [""]

    def set_code(self, code: str, language: str | None = None) -> None:
        """Update code content and re-render.

        Parameters
        ----------
        code : str
            New code content
        language : str, optional
            New programming language (if None, keeps current language)
        """
        self.code = code
        if language is not None:
            self.language = language
        self._render_content()

        # Update scroll manager with new content size
        self.scroll_manager.update_content_size(len(self.rendered_lines))

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore
        """
        self.scroll_manager.scroll_to(position)

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
        if not self.rendered_lines:
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
        """Handle mouse input for scrolling.

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

        return False

    def _render_with_border(self, content_lines: list[str]) -> list[str]:
        """Render content with border.

        Parameters
        ----------
        content_lines : list of str
            Content lines to wrap with border

        Returns
        -------
        list of str
            Lines with border added
        """
        from wijjit.layout.frames import BORDER_CHARS, BorderStyle
        from wijjit.terminal.ansi import ANSIColor, ANSIStyle

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS[style]

        # Choose border color based on focus
        if self.focused:
            border_color = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}"
            reset = ANSIStyle.RESET
        else:
            border_color = ""
            reset = ""

        # Calculate content width (total width - 2 for borders)
        content_width = self.width - 2

        # Build top border
        if self.title:
            # Border with title
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            if title_len < content_width:
                remaining = content_width - title_len
                left_line = chars["h"] * (remaining // 2)
                right_line = chars["h"] * (remaining - len(left_line))
                top_line = f"{border_color}{chars['tl']}{left_line}{title_text}{right_line}{chars['tr']}{reset}"
            else:
                # Title too long, just show border
                top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"
        else:
            # Border without title
            top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"

        # Build bottom border
        bottom_line = f"{border_color}{chars['bl']}{chars['h'] * content_width}{chars['br']}{reset}"

        # Wrap content lines with borders
        bordered_lines = [top_line]
        for line in content_lines:
            # Ensure line is padded to content width
            line_len = visible_length(line)
            if line_len < content_width:
                line = line + " " * (content_width - line_len)
            elif line_len > content_width:
                line = clip_to_width(line, content_width, ellipsis="")

            bordered_lines.append(
                f"{border_color}{chars['v']}{reset}{line}{border_color}{chars['v']}{reset}"
            )

        bordered_lines.append(bottom_line)

        return bordered_lines

    def render(self) -> str:
        """Render the code block.

        Returns
        -------
        str
            Rendered code block as multi-line string
        """
        content_height = self._get_content_height()
        content_width = self._get_content_width()

        # Get visible lines
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_lines = self.rendered_lines[visible_start:visible_end]

        # Pad or trim to exact content height
        if len(visible_lines) < content_height:
            visible_lines.extend(
                ["" for _ in range(content_height - len(visible_lines))]
            )
        else:
            visible_lines = visible_lines[:content_height]

        # Ensure all lines are padded to content width
        for i in range(len(visible_lines)):
            line = visible_lines[i]
            line_len = visible_length(line)
            if line_len < content_width:
                visible_lines[i] = line + " " * (content_width - line_len)
            elif line_len > content_width:
                visible_lines[i] = clip_to_width(line, content_width, ellipsis="")

        # Add scrollbar if needed
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, content_height
            )

            for i in range(len(visible_lines)):
                visible_lines[i] = visible_lines[i] + scrollbar_chars[i]

        # Add borders if requested
        if self.border_style != "none":
            final_lines = self._render_with_border(visible_lines)
        else:
            final_lines = visible_lines

        return "\n".join(final_lines)
