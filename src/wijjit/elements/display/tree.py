# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from wijjit.elements.base import ElementType, ScrollableElement
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext
    from wijjit.styling.style import Style


class TreeIndicatorStyle(Enum):
    """Visual styles for tree expand/collapse indicators.

    Attributes
    ----------
    BRACKETS : auto
        Square brackets with plus/minus: [+] / [-]
    TRIANGLES : auto
        Small Unicode triangles: ▸ / ▾
    TRIANGLES_LARGE : auto
        Large Unicode triangles: ▶ / ▼ (default)
    CIRCLES : auto
        Circled plus/minus: ⊕ / ⊖
    MINIMAL : auto
        Minimal plus/minus: + / -
    SQUARES : auto
        Squared plus/minus: ⊞ / ⊟

    Notes
    -----
    When Unicode styles are selected but not supported by the terminal,
    automatically falls back to BRACKETS style.
    """

    BRACKETS = auto()
    TRIANGLES = auto()
    TRIANGLES_LARGE = auto()
    CIRCLES = auto()
    MINIMAL = auto()
    SQUARES = auto()


class Tree(ScrollableElement):
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
    indicator_style : TreeIndicatorStyle, optional
        Style for expand/collapse indicators (default: TRIANGLES_LARGE)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "none")
    title : str, optional
        Title to display in top border (default: None)

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
    indicator_style : TreeIndicatorStyle
        Style for expand/collapse indicators
    border_style : str
        Border style
    title : str or None
        Border title
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
        classes: str | list[str] | None = None,
        data: dict[str, Any] | list | None = None,
        width: int = 40,
        height: int = 15,
        show_scrollbar: bool = True,
        show_root: bool = True,
        indent_size: int = 2,
        indicator_style: TreeIndicatorStyle = TreeIndicatorStyle.TRIANGLES_LARGE,
        border_style: str = "none",
        title: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = True

        # Display properties
        self.width = width
        self.height = height
        self.show_scrollbar = show_scrollbar
        self.show_root = show_root
        self.indent_size = indent_size
        self.indicator_style = indicator_style
        self.border_style = border_style
        self.title = title

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
        # on_scroll provided by ScrollableElement

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence keys
        # scroll_state_key provided by ScrollableElement
        self.expand_state_key: str | None = None
        self.highlight_state_key: str | None = None
        self.selected_state_key: str | None = None

        # State save callback (set by app/template)
        self._state_dict: dict[str, Any] | None = None

    def _normalize_data(self, data: dict[str, Any] | list) -> dict:
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

    def _build_tree_from_flat(self, flat_list: list[Any]) -> dict:
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

    def set_data(self, data: dict[str, Any] | list) -> None:
        """Update tree data and refresh display.

        Parameters
        ----------
        data : dict or list
            New tree data
        """
        self._raw_data = data
        self.data = self._normalize_data(data) if data else {}
        self._rebuild_nodes()

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

    def _get_tree_prefix(self, node_info: dict[str, Any]) -> str:
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

    def _get_expand_indicator(self, node_info: dict[str, Any]) -> str:
        """Get expand/collapse indicator for a node.

        Parameters
        ----------
        node_info : dict
            Node information from flattened list

        Returns
        -------
        str
            Expand indicator based on indicator_style

        Notes
        -----
        Automatically falls back to BRACKETS style if Unicode is not
        supported by the terminal.
        """
        from wijjit.terminal.ansi import supports_unicode

        if not node_info["has_children"]:
            # No children - return empty space matching indicator width
            if self.indicator_style == TreeIndicatorStyle.BRACKETS:
                return "   "
            elif self.indicator_style in (
                TreeIndicatorStyle.TRIANGLES,
                TreeIndicatorStyle.TRIANGLES_LARGE,
            ):
                return " "
            elif self.indicator_style == TreeIndicatorStyle.CIRCLES:
                return " "
            elif self.indicator_style == TreeIndicatorStyle.MINIMAL:
                return " "
            elif self.indicator_style == TreeIndicatorStyle.SQUARES:
                return " "
            else:
                return "   "

        is_expanded = node_info["is_expanded"]

        # Check Unicode support and fallback if needed
        use_unicode = supports_unicode()
        style = self.indicator_style

        # Fallback to brackets if Unicode not supported
        if not use_unicode and style != TreeIndicatorStyle.BRACKETS:
            if style != TreeIndicatorStyle.MINIMAL:
                style = TreeIndicatorStyle.BRACKETS

        # Return appropriate indicator based on style
        if style == TreeIndicatorStyle.BRACKETS:
            return "[-]" if is_expanded else "[+]"
        elif style == TreeIndicatorStyle.TRIANGLES:
            return "▾" if is_expanded else "▸"
        elif style == TreeIndicatorStyle.TRIANGLES_LARGE:
            return "▼" if is_expanded else "▶"
        elif style == TreeIndicatorStyle.CIRCLES:
            return "⊖" if is_expanded else "⊕"
        elif style == TreeIndicatorStyle.MINIMAL:
            return "-" if is_expanded else "+"
        elif style == TreeIndicatorStyle.SQUARES:
            return "⊟" if is_expanded else "⊞"
        else:
            # Default fallback
            return "[-]" if is_expanded else "[+]"

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

            # Account for borders if present
            border_offset = 1 if self.border_style != "none" else 0
            content_x = relative_x - border_offset
            content_y = relative_y - border_offset

            # Calculate content dimensions
            content_width = self.width - (2 * border_offset)
            content_height = self.height - (2 * border_offset)

            # Check if click is within tree content area
            if 0 <= content_y < content_height and 0 <= content_x < content_width:
                visible_start, visible_end = self.scroll_manager.get_visible_range()
                clicked_index = visible_start + content_y

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
                        and expand_start <= content_x < expand_end
                    ):
                        # Clicked on expand indicator
                        self.toggle_node(node_id)
                    else:
                        # Clicked on node label - select it
                        self.select_node(node_id)

                    return True

        return False

    def render_to(self, ctx: "PaintContext") -> None:
        """Render tree using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for tree views with:
        - Tree drawing characters (├─, └─, │) for hierarchy visualization
        - Expand/collapse indicators ([+], [-])
        - Node selection markers (">")
        - Highlight styling for focused nodes
        - Theme-based styling for all states
        - Scrollbar integration

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'tree': Base tree style
        - 'tree:focus': When tree has focus
        - 'tree.node': Default node style
        - 'tree.node:highlight': Highlighted node (keyboard focus)
        - 'tree.node:selected': Selected node with marker
        - 'tree.indicator': Expand/collapse indicators
        - 'tree.border': Border characters
        - 'tree.border:focus': Border when focused
        """
        # Resolve base styles
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(self, "tree.border:focus")
        else:
            border_style = ctx.style_resolver.resolve_style(self, "tree.border")

        # Determine if we need borders
        has_borders = self.border_style != "none"

        if has_borders:
            # Render with borders
            self._render_to_with_border(ctx, border_style)
        else:
            # Render without borders
            self._render_to_content(ctx, 0, 0, self.width, self.height)

    def _render_to_with_border(
        self, ctx: "PaintContext", border_style: "Style"
    ) -> None:
        """Render tree with border using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_style : Style
            Border style
        """
        from wijjit.layout.frames import BORDER_CHARS, BorderStyle
        from wijjit.terminal.cell import Cell

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS[style]

        # Ensure borders don't inherit background from content cells
        # If border style doesn't have explicit bg, use None to clear
        border_attrs = border_style.to_cell_attrs()
        # Explicitly set bg_color to None if not defined to ensure transparency
        if "bg_color" not in border_attrs or border_attrs["bg_color"] is None:
            border_attrs = {**border_attrs, "bg_color": None}

        # Calculate dimensions
        content_width = self.width - 2  # Subtract borders
        content_height = self.height - 2  # Subtract borders
        total_width = self.width  # Total width includes borders and content

        # Render borders FIRST to establish baseline, then content on top
        # This prevents content backgrounds from bleeding into border area

        # Render top border with optional title
        if self.title:
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            border_width = total_width - 2  # Width without corners

            if title_len < border_width:
                remaining = border_width - title_len
                left_len = remaining // 2
                right_len = remaining - left_len

                # Top-left corner
                ctx.buffer.set_cell(
                    ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
                )

                # Left line
                for i in range(left_len):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + i,
                        ctx.bounds.y,
                        Cell(char=chars["h"], **border_attrs),
                    )

                # Title
                for i, char in enumerate(title_text):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + left_len + i,
                        ctx.bounds.y,
                        Cell(char=char, **border_attrs),
                    )

                # Right line
                for i in range(right_len):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + left_len + title_len + i,
                        ctx.bounds.y,
                        Cell(char=chars["h"], **border_attrs),
                    )

                # Top-right corner
                ctx.buffer.set_cell(
                    ctx.bounds.x + total_width - 1,
                    ctx.bounds.y,
                    Cell(char=chars["tr"], **border_attrs),
                )
            else:
                # Title too long
                ctx.buffer.set_cell(
                    ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
                )
                for i in range(border_width):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + i,
                        ctx.bounds.y,
                        Cell(char=chars["h"], **border_attrs),
                    )
                ctx.buffer.set_cell(
                    ctx.bounds.x + total_width - 1,
                    ctx.bounds.y,
                    Cell(char=chars["tr"], **border_attrs),
                )
        else:
            # No title
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
            )
            for i in range(1, total_width - 1):
                ctx.buffer.set_cell(
                    ctx.bounds.x + i,
                    ctx.bounds.y,
                    Cell(char=chars["h"], **border_attrs),
                )
            ctx.buffer.set_cell(
                ctx.bounds.x + total_width - 1,
                ctx.bounds.y,
                Cell(char=chars["tr"], **border_attrs),
            )

        # Render content area (inside borders)
        content_ctx = ctx.sub_context(1, 1, content_width, content_height)
        self._render_to_content(
            content_ctx, 0, 0, content_width, content_height, has_border=True
        )

        # Render side borders
        for y in range(content_height):
            # Left border
            ctx.buffer.set_cell(
                ctx.bounds.x,
                ctx.bounds.y + 1 + y,
                Cell(char=chars["v"], **border_attrs),
            )
            # Right border
            ctx.buffer.set_cell(
                ctx.bounds.x + total_width - 1,
                ctx.bounds.y + 1 + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Render bottom border
        bottom_y = content_height + 1
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + bottom_y,
            Cell(char=chars["bl"], **border_attrs),
        )
        for i in range(1, total_width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + i,
                ctx.bounds.y + bottom_y,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + total_width - 1,
            ctx.bounds.y + bottom_y,
            Cell(char=chars["br"], **border_attrs),
        )

    def _render_to_content(
        self,
        ctx: "PaintContext",
        start_x: int,
        start_y: int,
        content_width: int,
        content_height: int,
        has_border: bool = False,
    ) -> None:
        """Render tree content using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        start_x : int
            Starting X position
        start_y : int
            Starting Y position
        content_width : int
            Content area width
        content_height : int
            Content area height
        has_border : bool, optional
            Whether tree has borders (affects right padding), by default False
        """
        from wijjit.styling.style import Style
        from wijjit.terminal.cell import Cell

        if not self.nodes:
            # Empty tree - show message
            empty_style = ctx.style_resolver.resolve_style(self, "tree")
            ctx.write_text(0, 0, "Empty tree", empty_style)
            return

        # Calculate effective width for tree rendering
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        # Reserve space for scrollbar if needed, and for border if present
        tree_width = (
            content_width - (1 if needs_scrollbar else 0) - (1 if has_border else 0)
        )

        # Get visible nodes
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_nodes = self.nodes[visible_start:visible_end]

        # Resolve base style
        if self.focused:
            base_style = ctx.style_resolver.resolve_style(self, "tree:focus")
        else:
            base_style = ctx.style_resolver.resolve_style(self, "tree")

        # Resolve indicator style
        indicator_style = ctx.style_resolver.resolve_style(self, "tree.indicator")
        if not indicator_style.fg_color and not indicator_style.bg_color:
            indicator_style = base_style

        # Render each visible node
        for i, node_info in enumerate(visible_nodes):
            if i >= content_height:
                break

            node_index = visible_start + i
            is_highlighted = node_index == self.highlighted_index
            is_selected = node_info["node"]["id"] == self.selected_node_id

            # Determine node style - highlighted takes precedence for main content
            if is_highlighted and self.focused:
                # Highlighted node: use highlight style
                node_style = ctx.style_resolver.resolve_style(
                    self, "tree.node:highlight"
                )
                # If the theme style doesn't have colors, create fallback
                if not node_style.bg_color:
                    node_style = Style(
                        fg_color=base_style.bg_color or (0, 0, 0),
                        bg_color=base_style.fg_color or (255, 255, 255),
                        bold=base_style.bold,
                        reverse=False,
                    )
            elif is_selected:
                node_style = ctx.style_resolver.resolve_style(
                    self, "tree.node:selected"
                )
            else:
                node_style = ctx.style_resolver.resolve_style(self, "tree.node")
                # Fall back to base style if node style is empty
                if not node_style.fg_color and not node_style.bg_color:
                    node_style = base_style

            # Selection marker style - use selected style for marker even when highlighted
            if is_selected:
                selection_marker_style = ctx.style_resolver.resolve_style(
                    self, "tree.node:selected"
                )
                # If highlighted, blend selected fg with highlighted bg
                if is_highlighted and self.focused:
                    selection_marker_style = Style(
                        fg_color=selection_marker_style.fg_color,
                        bg_color=node_style.bg_color,
                        bold=selection_marker_style.bold,
                        reverse=False,
                    )
            else:
                selection_marker_style = node_style

            # Build line components with styled parts
            selection_marker = "> " if is_selected else "  "
            tree_prefix = self._get_tree_prefix(node_info)
            expand_indicator = self._get_expand_indicator(node_info)
            label = node_info["node"]["label"]

            # Calculate available width for label
            prefix_len = (
                visible_length(selection_marker)
                + visible_length(tree_prefix)
                + visible_length(expand_indicator)
                + 1  # space after indicator
            )
            label_width = tree_width - prefix_len

            # Clip label if too long
            if visible_length(label) > label_width:
                label = clip_to_width(label, label_width, ellipsis="...")

            # Write line parts with appropriate styles
            x_offset = 0

            # Get node attributes
            node_attrs = node_style.to_cell_attrs()
            selection_marker_attrs = selection_marker_style.to_cell_attrs()

            # For highlighted nodes, indicator should inherit the node's background
            # for visual consistency across the entire line
            if is_highlighted and self.focused:
                # Use node style but keep indicator foreground color if it exists
                indicator_attrs_for_line = Style(
                    fg_color=indicator_style.fg_color or node_style.fg_color,
                    bg_color=node_style.bg_color,
                    bold=node_style.bold,
                    reverse=False,  # Explicitly disable reverse
                ).to_cell_attrs()
            else:
                indicator_attrs_for_line = indicator_style.to_cell_attrs()

            # Selection marker (use selection marker style to show selected state)
            for char in selection_marker:
                ctx.buffer.set_cell(
                    ctx.bounds.x + x_offset,
                    ctx.bounds.y + start_y + i,
                    Cell(char=char, **selection_marker_attrs),
                )
                x_offset += 1

            # Tree prefix (use node style)
            for char in tree_prefix:
                ctx.buffer.set_cell(
                    ctx.bounds.x + x_offset,
                    ctx.bounds.y + start_y + i,
                    Cell(char=char, **node_attrs),
                )
                x_offset += 1

            # Expand indicator (use indicator style with node background if highlighted)
            for char in expand_indicator:
                ctx.buffer.set_cell(
                    ctx.bounds.x + x_offset,
                    ctx.bounds.y + start_y + i,
                    Cell(char=char, **indicator_attrs_for_line),
                )
                x_offset += 1

            # Space after indicator (use node style)
            ctx.buffer.set_cell(
                ctx.bounds.x + x_offset,
                ctx.bounds.y + start_y + i,
                Cell(char=" ", **node_attrs),
            )
            x_offset += 1

            # Label (use node style)
            for char in label:
                ctx.buffer.set_cell(
                    ctx.bounds.x + x_offset,
                    ctx.bounds.y + start_y + i,
                    Cell(char=char, **node_attrs),
                )
                x_offset += 1

            # Pad remaining width with spaces (use node style)
            # Leave space for scrollbar if present
            # Only fill if node has a background color (otherwise inherit from parent)
            if node_style.bg_color or is_highlighted:
                while x_offset < tree_width:
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x_offset,
                        ctx.bounds.y + start_y + i,
                        Cell(char=" ", **node_attrs),
                    )
                    x_offset += 1

        # Pad remaining lines to height
        rendered_lines = len(visible_nodes)
        if base_style.bg_color:
            # Only fill empty lines if tree has explicit background color
            for i in range(rendered_lines, content_height):
                # Fill with spaces using base style
                for x in range(tree_width):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + start_y + i,
                        Cell(char=" ", **base_style.to_cell_attrs()),
                    )

        # Add scrollbar if needed
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, content_height
            )

            for i in range(content_height):
                scrollbar_char = scrollbar_chars[i] if i < len(scrollbar_chars) else " "
                ctx.buffer.set_cell(
                    ctx.bounds.x + tree_width,
                    ctx.bounds.y + start_y + i,
                    Cell(char=scrollbar_char, **base_style.to_cell_attrs()),
                )

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
