"""Tests for Tree display element."""

import pytest

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.display.tree import Tree
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestTreeCreation:
    """Tests for Tree element creation and initialization."""

    def test_create_tree_nested_dict(self):
        """Test creating a tree with nested dict data."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {
                    "label": "Child 2",
                    "value": "c2",
                    "children": [
                        {"label": "Grandchild 1", "value": "gc1"},
                    ],
                },
            ],
        }

        tree = Tree(id="filetree", data=data)

        assert tree.id == "filetree"
        assert tree.data["label"] == "Root"
        assert len(tree.data["children"]) == 2
        assert tree.element_type == ElementType.DISPLAY
        assert tree.focusable

    def test_create_tree_flat_list(self):
        """Test creating a tree with flat list data."""
        data = [
            {"id": "1", "label": "Root", "parent_id": None},
            {"id": "2", "label": "Child 1", "parent_id": "1"},
            {"id": "3", "label": "Child 2", "parent_id": "1"},
            {"id": "4", "label": "Grandchild 1", "parent_id": "2"},
        ]

        tree = Tree(id="filetree", data=data)

        assert tree.id == "filetree"
        assert tree.data["label"] == "Root"
        assert len(tree.data["children"]) == 2

    def test_create_empty_tree(self):
        """Test creating an empty tree."""
        tree = Tree(id="empty")

        assert tree.id == "empty"
        assert len(tree.nodes) == 0

    def test_default_properties(self):
        """Test default tree properties."""
        tree = Tree()

        assert tree.width == 40
        assert tree.height == 15
        assert tree.show_scrollbar is True
        assert tree.show_root is True
        assert tree.indent_size == 2
        assert tree.highlighted_index == 0
        assert len(tree.expanded_nodes) == 0


class TestTreeDataNormalization:
    """Tests for tree data normalization."""

    def test_normalize_nested_dict(self):
        """Test normalization of nested dict data."""
        data = {
            "label": "Root",
            "children": [
                {"label": "Child 1"},
                {"label": "Child 2"},
            ],
        }

        tree = Tree(data=data)

        # Should have auto-generated IDs
        assert "id" in tree.data
        assert "id" in tree.data["children"][0]
        assert tree.data["children"][0]["label"] == "Child 1"

    def test_normalize_flat_list(self):
        """Test normalization of flat list data."""
        data = [
            {"id": "1", "label": "Root", "parent_id": None},
            {"id": "2", "label": "Child", "parent_id": "1"},
        ]

        tree = Tree(data=data)

        # Should build tree structure
        assert tree.data["id"] == "1"
        assert len(tree.data["children"]) == 1
        assert tree.data["children"][0]["id"] == "2"

    def test_preserve_extra_metadata(self):
        """Test that extra node metadata is preserved."""
        data = {
            "label": "File",
            "value": "file.txt",
            "size": 1024,
            "type": "file",
        }

        tree = Tree(data=data)

        assert tree.data["size"] == 1024
        assert tree.data["type"] == "file"


class TestTreeFlattening:
    """Tests for tree flattening logic."""

    def test_flatten_simple_tree(self):
        """Test flattening a simple tree."""
        data = {
            "label": "Root",
            "children": [
                {"label": "Child 1"},
                {"label": "Child 2"},
            ],
        }

        tree = Tree(data=data, show_root=True)

        # Should have 1 root node (children are collapsed by default)
        assert len(tree.nodes) == 1
        assert tree.nodes[0]["node"]["label"] == "Root"

    def test_flatten_with_expansion(self):
        """Test flattening with expanded nodes."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data, show_root=True)

        # Expand root
        tree.expand_node("root")

        # Should now have 3 nodes: root + 2 children
        assert len(tree.nodes) == 3
        assert tree.nodes[0]["node"]["label"] == "Root"
        assert tree.nodes[1]["node"]["label"] == "Child 1"
        assert tree.nodes[2]["node"]["label"] == "Child 2"

    def test_flatten_hide_root(self):
        """Test flattening with hidden root."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data, show_root=False)

        # Should show children directly
        assert len(tree.nodes) == 2
        assert tree.nodes[0]["node"]["label"] == "Child 1"
        assert tree.nodes[1]["node"]["label"] == "Child 2"


class TestTreeExpansion:
    """Tests for expand/collapse functionality."""

    def test_expand_node(self):
        """Test expanding a node."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data)
        callback_called = []

        def on_expand(node_id):
            callback_called.append(node_id)

        tree.on_expand = on_expand

        # Initially collapsed
        assert "root" not in tree.expanded_nodes

        # Expand root
        tree.expand_node("root")

        # Should be expanded
        assert "root" in tree.expanded_nodes
        assert callback_called == ["root"]

    def test_collapse_node(self):
        """Test collapsing a node."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data)
        tree.expand_node("root")

        callback_called = []

        def on_collapse(node_id):
            callback_called.append(node_id)

        tree.on_collapse = on_collapse

        # Collapse root
        tree.collapse_node("root")

        # Should be collapsed
        assert "root" not in tree.expanded_nodes
        assert callback_called == ["root"]

    def test_toggle_node(self):
        """Test toggling node expansion."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data)

        # Toggle to expand
        tree.toggle_node("root")
        assert "root" in tree.expanded_nodes

        # Toggle to collapse
        tree.toggle_node("root")
        assert "root" not in tree.expanded_nodes


class TestTreeSelection:
    """Tests for node selection."""

    def test_select_node(self):
        """Test selecting a node."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data)
        selected_node = []

        def on_select(node):
            selected_node.append(node)

        tree.on_select = on_select
        tree.expand_node("root")

        # Select child node
        child_id = tree.data["children"][0]["id"]
        tree.select_node(child_id)

        assert tree.selected_node_id == child_id
        assert len(selected_node) == 1
        assert selected_node[0]["label"] == "Child"


class TestTreeKeyboardNavigation:
    """Tests for keyboard navigation."""

    def test_down_key(self):
        """Test DOWN key navigation."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data)
        tree.expand_node("root")

        # Start at root (index 0)
        assert tree.highlighted_index == 0

        # Move down
        tree.handle_key(Keys.DOWN)
        assert tree.highlighted_index == 1

        # Move down again
        tree.handle_key(Keys.DOWN)
        assert tree.highlighted_index == 2

    def test_up_key(self):
        """Test UP key navigation."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data)
        tree.expand_node("root")
        tree.highlighted_index = 2

        # Move up
        tree.handle_key(Keys.UP)
        assert tree.highlighted_index == 1

        # Move up again
        tree.handle_key(Keys.UP)
        assert tree.highlighted_index == 0

    def test_right_key_expand(self):
        """Test RIGHT key to expand node."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data)

        # Press RIGHT on collapsed node with children
        tree.handle_key(Keys.RIGHT)

        # Should expand
        assert "root" in tree.expanded_nodes

    def test_left_key_collapse(self):
        """Test LEFT key to collapse node."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data)
        tree.expand_node("root")

        # Press LEFT on expanded node
        tree.handle_key(Keys.LEFT)

        # Should collapse
        assert "root" not in tree.expanded_nodes

    def test_enter_key_toggle(self):
        """Test ENTER key to toggle expansion."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data)

        # Press ENTER on collapsed node
        tree.handle_key(Keys.ENTER)
        assert "root" in tree.expanded_nodes

        # Press ENTER again on expanded node
        tree.handle_key(Keys.ENTER)
        assert "root" not in tree.expanded_nodes

    def test_home_key(self):
        """Test HOME key navigation."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data)
        tree.expand_node("root")
        tree.highlighted_index = 2

        # Press HOME
        tree.handle_key(Keys.HOME)

        assert tree.highlighted_index == 0
        assert tree.scroll_manager.state.scroll_position == 0

    def test_end_key(self):
        """Test END key navigation."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data)
        tree.expand_node("root")

        # Press END
        tree.handle_key(Keys.END)

        assert tree.highlighted_index == len(tree.nodes) - 1

    def test_page_down_key(self):
        """Test PAGE_DOWN key navigation."""
        # Create tree with many nodes
        children = [{"label": f"Child {i}", "value": f"c{i}"} for i in range(20)]
        data = {"label": "Root", "value": "root", "children": children}

        tree = Tree(data=data, height=10)
        tree.expand_node("root")

        initial_pos = tree.highlighted_index

        # Press PAGE_DOWN
        tree.handle_key(Keys.PAGE_DOWN)

        # Should move down by viewport height
        assert tree.highlighted_index > initial_pos

    def test_page_up_key(self):
        """Test PAGE_UP key navigation."""
        # Create tree with many nodes
        children = [{"label": f"Child {i}", "value": f"c{i}"} for i in range(20)]
        data = {"label": "Root", "value": "root", "children": children}

        tree = Tree(data=data, height=10)
        tree.expand_node("root")
        tree.highlighted_index = 15
        # Scroll down first so PAGE_UP can scroll up
        tree.scroll_manager.scroll_to(10)

        initial_pos = tree.highlighted_index

        # Press PAGE_UP
        tree.handle_key(Keys.PAGE_UP)

        # Should move up
        assert tree.highlighted_index < initial_pos


class TestTreeMouseInteraction:
    """Tests for mouse interaction."""

    @pytest.mark.asyncio
    async def test_mouse_scroll_down(self):
        """Test mouse wheel scroll down."""
        # Create tree with many nodes
        children = [{"label": f"Child {i}", "value": f"c{i}"} for i in range(20)]
        data = {"label": "Root", "value": "root", "children": children}

        tree = Tree(data=data, height=10)
        tree.expand_node("root")

        initial_pos = tree.scroll_manager.state.scroll_position

        # Scroll down
        event = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_DOWN,
            x=0,
            y=0,
        )
        await tree.handle_mouse(event)

        assert tree.scroll_manager.state.scroll_position > initial_pos

    @pytest.mark.asyncio
    async def test_mouse_scroll_up(self):
        """Test mouse wheel scroll up."""
        # Create tree with many nodes
        children = [{"label": f"Child {i}", "value": f"c{i}"} for i in range(20)]
        data = {"label": "Root", "value": "root", "children": children}

        tree = Tree(data=data, height=10)
        tree.expand_node("root")

        # Scroll down first
        tree.scroll_manager.scroll_to(5)
        initial_pos = tree.scroll_manager.state.scroll_position

        # Scroll up
        event = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_UP,
            x=0,
            y=0,
        )
        await tree.handle_mouse(event)

        assert tree.scroll_manager.state.scroll_position < initial_pos

    @pytest.mark.asyncio
    async def test_mouse_click_to_select(self):
        """Test clicking on a node to select it."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data, width=40, height=10)
        tree.expand_node("root")

        # Set bounds for coordinate calculation
        from wijjit.layout.bounds import Bounds

        tree.bounds = Bounds(x=0, y=0, width=40, height=10)

        # Click on second node (child)
        event = MouseEvent(
            type=MouseEventType.CLICK,
            button=MouseButton.LEFT,
            x=10,  # Middle of line
            y=1,  # Second row
        )
        result = await tree.handle_mouse(event)

        assert result is True
        assert tree.highlighted_index == 1


class TestTreeRendering:
    """Tests for tree rendering."""

    def test_render_empty_tree(self):
        """Test rendering an empty tree."""
        tree = Tree(width=40, height=10)
        tree.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(tree, width=40, height=10)

        assert isinstance(output, str)
        assert "Empty tree" in output

    def test_render_simple_tree(self):
        """Test rendering a simple tree."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data, width=40, height=10)
        tree.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(tree, width=40, height=10)

        assert isinstance(output, str)
        assert "Root" in output
        # Children should not be visible (collapsed)
        assert "Child 1" not in output

    def test_render_expanded_tree(self):
        """Test rendering an expanded tree."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data, width=40, height=10)
        tree.set_bounds(Bounds(0, 0, 40, 10))
        tree.expand_node("root")

        output = render_element(tree, width=40, height=10)

        assert isinstance(output, str)
        assert "Root" in output
        assert "Child 1" in output
        assert "Child 2" in output

    def test_render_with_tree_characters(self):
        """Test that tree drawing characters are present."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }

        tree = Tree(data=data, width=40, height=10)
        tree.set_bounds(Bounds(0, 0, 40, 10))
        tree.expand_node("root")

        output = render_element(tree, width=40, height=10)

        # Should contain tree drawing characters (Unicode box-drawing)
        assert "\u251c" in output or "\u2514" in output  # ├ or └

    def test_render_with_expand_indicators(self):
        """Test that expand/collapse indicators are present."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        tree = Tree(data=data, width=40, height=10)
        tree.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(tree, width=40, height=10)

        # Should contain collapsed indicator (default is large triangles)
        assert "▶" in output or "[+]" in output  # Unicode or fallback

        # Expand and re-render
        tree.expand_node("root")
        output = render_element(tree, width=40, height=10)

        # Should contain expanded indicator
        assert "▼" in output or "[-]" in output  # Unicode or fallback

    def test_indicator_styles(self):
        """Test different indicator styles."""
        from wijjit.elements.display import TreeIndicatorStyle

        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }

        # Test BRACKETS style
        tree = Tree(
            data=data, width=40, height=10, indicator_style=TreeIndicatorStyle.BRACKETS
        )
        tree.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(tree, width=40, height=10)
        assert "[+]" in output

        tree.expand_node("root")
        output = render_element(tree, width=40, height=10)
        assert "[-]" in output

        # Test TRIANGLES_LARGE style (default)
        tree = Tree(
            data=data,
            width=40,
            height=10,
            indicator_style=TreeIndicatorStyle.TRIANGLES_LARGE,
        )
        tree.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(tree, width=40, height=10)
        assert "▶" in output or "[+]" in output  # Unicode or fallback

        tree.expand_node("root")
        output = render_element(tree, width=40, height=10)
        assert "▼" in output or "[-]" in output  # Unicode or fallback

        # Test MINIMAL style
        tree = Tree(
            data=data, width=40, height=10, indicator_style=TreeIndicatorStyle.MINIMAL
        )
        tree.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(tree, width=40, height=10)
        assert "+" in output

        tree.expand_node("root")
        output = render_element(tree, width=40, height=10)
        assert "-" in output

    def test_render_with_scrollbar(self):
        """Test rendering with scrollbar."""
        # Create tree with many nodes
        children = [{"label": f"Child {i}", "value": f"c{i}"} for i in range(20)]
        data = {"label": "Root", "value": "root", "children": children}

        tree = Tree(data=data, width=40, height=10, show_scrollbar=True)
        tree.set_bounds(Bounds(0, 0, 40, 10))
        tree.expand_node("root")

        output = render_element(tree, width=40, height=10)

        assert isinstance(output, str)
        # Scrollbar characters should be present
        # The scrollbar uses box drawing characters


class TestTreeMethods:
    """Tests for tree utility methods."""

    def test_set_data(self):
        """Test updating tree data."""
        tree = Tree()

        new_data = {
            "label": "New Root",
            "value": "new_root",
            "children": [
                {"label": "New Child", "value": "new_child"},
            ],
        }

        tree.set_data(new_data)

        assert tree.data["label"] == "New Root"
        assert len(tree.data["children"]) == 1

    def test_find_node_by_id(self):
        """Test finding a node by ID."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {
                    "label": "Child",
                    "value": "child",
                    "children": [
                        {"label": "Grandchild", "value": "grandchild"},
                    ],
                },
            ],
        }

        tree = Tree(data=data)

        # Find root
        root = tree._find_node_by_id(tree.data, tree.data["id"])
        assert root is not None
        assert root["label"] == "Root"

        # Find grandchild
        grandchild_id = tree.data["children"][0]["children"][0]["id"]
        grandchild = tree._find_node_by_id(tree.data, grandchild_id)
        assert grandchild is not None
        assert grandchild["label"] == "Grandchild"

        # Try to find non-existent node
        not_found = tree._find_node_by_id(tree.data, "nonexistent")
        assert not_found is None


class TestTreeMultiSelect:
    """Tests for Tree multi-select mode."""

    def test_multi_select_create(self):
        """Test creating a multi-select tree."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }
        tree = Tree(data=data, multiple=True)

        assert tree.multiple is True
        assert len(tree.selected_node_ids) == 0

    def test_multi_select_with_initial_selection(self):
        """Test multi-select tree with initial selections."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }
        tree = Tree(data=data, multiple=True, selected_ids=["root", "c1"])
        tree.expand_node("root")

        assert tree.multiple is True
        assert "root" in tree.selected_node_ids
        assert "c1" in tree.selected_node_ids
        assert "c2" not in tree.selected_node_ids

    def test_toggle_selection(self):
        """Test toggling selection in multi-select mode."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
            ],
        }
        tree = Tree(data=data, multiple=True)

        # Toggle to select
        tree.toggle_selection("root")
        assert "root" in tree.selected_node_ids

        # Toggle to deselect
        tree.toggle_selection("root")
        assert "root" not in tree.selected_node_ids

    def test_multi_select_enter_key_toggles(self):
        """Test Enter key toggles selection in multi-select mode."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }
        tree = Tree(data=data, multiple=True)
        tree.expand_node("root")

        # Start at root
        assert tree.highlighted_index == 0
        root_id = tree.nodes[0]["node"]["id"]

        # Press Enter to select root
        tree.handle_key(Keys.ENTER)
        assert root_id in tree.selected_node_ids

        # Press Enter again to deselect
        tree.handle_key(Keys.ENTER)
        assert root_id not in tree.selected_node_ids

    def test_multi_select_space_key_toggles(self):
        """Test Space key toggles selection in multi-select mode."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
            ],
        }
        tree = Tree(data=data, multiple=True)

        root_id = tree.nodes[0]["node"]["id"]

        # Press Space to select
        tree.handle_key(Keys.SPACE)
        assert root_id in tree.selected_node_ids

    def test_multi_select_multiple_nodes(self):
        """Test selecting multiple nodes in multi-select mode."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
                {"label": "Child 3", "value": "c3"},
            ],
        }
        tree = Tree(data=data, multiple=True)
        tree.expand_node("root")

        # Select root
        tree.handle_key(Keys.ENTER)

        # Move down and select child 1
        tree.handle_key(Keys.DOWN)
        tree.handle_key(Keys.ENTER)

        # Move down and select child 3 (skip child 2)
        tree.handle_key(Keys.DOWN)
        tree.handle_key(Keys.DOWN)
        tree.handle_key(Keys.ENTER)

        # Should have root, c1, and c3 selected
        assert len(tree.selected_node_ids) == 3
        child1_id = tree.nodes[1]["node"]["id"]
        child3_id = tree.nodes[3]["node"]["id"]
        assert child1_id in tree.selected_node_ids
        assert child3_id in tree.selected_node_ids

    def test_is_selected_method(self):
        """Test the is_selected() method."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
            ],
        }

        # Single select mode
        tree_single = Tree(data=data, multiple=False)
        tree_single.select_node("root")
        assert tree_single.is_selected("root") is True
        assert tree_single.is_selected("c1") is False

        # Multi select mode
        tree_multi = Tree(data=data, multiple=True)
        tree_multi.toggle_selection("root")
        tree_multi.toggle_selection("c1")
        assert tree_multi.is_selected("root") is True
        assert tree_multi.is_selected("c1") is True

    def test_selected_ids_property(self):
        """Test the selected_ids property getter and setter."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }
        tree = Tree(data=data, multiple=True)

        # Initially empty
        assert tree.selected_ids == []

        # Set values
        tree.selected_ids = ["root", "c1"]
        assert set(tree.selected_ids) == {"root", "c1"}

        # Clear values
        tree.selected_ids = []
        assert tree.selected_ids == []

    def test_single_select_selected_ids_property(self):
        """Test selected_ids property in single-select mode."""
        data = {
            "label": "Root",
            "value": "root",
        }
        tree = Tree(data=data, multiple=False)

        # Initially empty
        assert tree.selected_ids == []

        # Select via property
        tree.selected_ids = ["root"]
        assert tree.selected_ids == ["root"]
        assert tree.selected_node_id == "root"

    def test_multi_select_on_select_callback(self):
        """Test that on_select callback is called for each toggle."""
        data = {
            "label": "Root",
            "value": "root",
        }
        tree = Tree(data=data, multiple=True)
        callback_calls = []

        def on_select(node):
            callback_calls.append(node)

        tree.on_select = on_select

        # Toggle selection
        tree.toggle_selection("root")
        assert len(callback_calls) == 1
        assert callback_calls[0]["label"] == "Root"

    def test_multi_select_ephemeral_state(self):
        """Test that ephemeral state includes selected_node_ids."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
            ],
        }
        tree = Tree(data=data, multiple=True, selected_ids=["root", "c1"])

        state = tree.get_ephemeral_state()
        assert "selected_node_ids" in state
        assert state["selected_node_ids"] == {"root", "c1"}

    def test_multi_select_restore_ephemeral_state(self):
        """Test restoring ephemeral state for multi-select."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
            ],
        }
        tree = Tree(data=data, multiple=True)

        # Simulate state from previous render
        state = {
            "highlighted_index": 0,
            "selected_node_ids": {"root", "c1"},
            "expanded_nodes": set(),
        }
        tree.restore_ephemeral_state(state)

        assert tree.selected_node_ids == {"root", "c1"}

    def test_render_multi_select_tree(self):
        """Test rendering a multi-select tree with multiple selections."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child 1", "value": "c1"},
                {"label": "Child 2", "value": "c2"},
            ],
        }
        tree = Tree(
            data=data, multiple=True, selected_ids=["root", "c1"], width=40, height=10
        )
        tree.set_bounds(Bounds(0, 0, 40, 10))
        tree.expand_node("root")

        output = render_element(tree, width=40, height=10)

        # Should show selection markers for root and c1
        lines = output.strip().split("\n")
        # Check that at least 2 lines have selection markers
        lines_with_markers = [line for line in lines if "> " in line]
        assert len(lines_with_markers) >= 2

    @pytest.mark.asyncio
    async def test_mouse_click_toggles_in_multi_select(self):
        """Test mouse click toggles selection in multi-select mode."""
        data = {
            "label": "Root",
            "value": "root",
            "children": [
                {"label": "Child", "value": "child"},
            ],
        }
        tree = Tree(data=data, multiple=True, width=40, height=10)
        tree.expand_node("root")
        tree.bounds = Bounds(x=0, y=0, width=40, height=10)

        # Get root ID
        root_id = tree.nodes[0]["node"]["id"]

        # Click on root to select
        event = MouseEvent(
            type=MouseEventType.CLICK,
            button=MouseButton.LEFT,
            x=10,
            y=0,
        )
        result = await tree.handle_mouse(event)
        assert result is True
        assert root_id in tree.selected_node_ids

        # Click again to deselect
        result = await tree.handle_mouse(event)
        assert result is True
        assert root_id not in tree.selected_node_ids
