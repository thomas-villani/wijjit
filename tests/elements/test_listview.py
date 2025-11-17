"""Tests for ListView display element."""

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.display.list import ListView
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestListView:
    """Tests for ListView element."""

    def test_create_listview(self):
        """Test creating a basic ListView."""
        items = ["Apple", "Banana", "Cherry"]

        listview = ListView(id="fruits", items=items)

        assert listview.id == "fruits"
        assert len(listview.items) == 3
        assert listview.items[0]["label"] == "Apple"
        assert listview.items[0]["details"] is None
        assert listview.element_type == ElementType.DISPLAY
        assert listview.focusable  # ListView is focusable for keyboard scrolling

    def test_empty_listview(self):
        """Test ListView with no items."""
        listview = ListView()
        assert len(listview.items) == 0

        # Should render without errors
        listview.set_bounds(
            Bounds(
                0,
                0,
                listview.width if hasattr(listview, "width") else 40,
                listview.height if hasattr(listview, "height") else 10,
            )
        )
        output = render_element(
            listview, width=listview.bounds.width, height=listview.bounds.height
        )
        assert isinstance(output, str)

    def test_normalize_items_strings(self):
        """Test normalizing string items."""
        items = ["Item 1", "Item 2", "Item 3"]
        listview = ListView(items=items)

        assert len(listview.items) == 3
        assert listview.items[0] == {"label": "Item 1", "details": None}
        assert listview.items[1] == {"label": "Item 2", "details": None}
        assert listview.items[2] == {"label": "Item 3", "details": None}

    def test_normalize_items_tuples(self):
        """Test normalizing 2-tuple items."""
        items = [
            ("Python", "A high-level programming language"),
            ("JavaScript", "A dynamic scripting language"),
        ]
        listview = ListView(items=items)

        assert len(listview.items) == 2
        assert listview.items[0]["label"] == "Python"
        assert listview.items[0]["details"] == "A high-level programming language"
        assert listview.items[1]["label"] == "JavaScript"
        assert listview.items[1]["details"] == "A dynamic scripting language"

    def test_normalize_items_dicts(self):
        """Test normalizing dict items."""
        items = [
            {"label": "Task 1", "details": "Details for task 1"},
            {"label": "Task 2", "details": "Details for task 2"},
        ]
        listview = ListView(items=items)

        assert len(listview.items) == 2
        assert listview.items[0]["label"] == "Task 1"
        assert listview.items[0]["details"] == "Details for task 1"

    def test_normalize_items_mixed(self):
        """Test normalizing mixed item formats."""
        items = [
            "Simple item",
            ("Label", "Details"),
            {"label": "Dict item", "details": "Dict details"},
        ]
        listview = ListView(items=items)

        assert len(listview.items) == 3
        assert listview.items[0] == {"label": "Simple item", "details": None}
        assert listview.items[1]["label"] == "Label"
        assert listview.items[1]["details"] == "Details"
        assert listview.items[2]["label"] == "Dict item"

    def test_bullet_styles(self):
        """Test different bullet styles."""
        items = ["Item 1", "Item 2", "Item 3"]

        # Bullet style
        lv_bullet = ListView(items=items, bullet="bullet")
        assert lv_bullet._get_bullet_char(0) in ["• ", "* "]  # Unicode or fallback

        # Dash style
        lv_dash = ListView(items=items, bullet="dash")
        assert lv_dash._get_bullet_char(0) == "- "

        # Number style
        lv_number = ListView(items=items, bullet="number")
        assert lv_number._get_bullet_char(0) == "1. "
        assert lv_number._get_bullet_char(1) == "2. "
        assert lv_number._get_bullet_char(2) == "3. "

        # Custom character
        lv_custom = ListView(items=items, bullet=">")
        assert lv_custom._get_bullet_char(0) == "> "

        # No bullet
        lv_none = ListView(items=items, bullet=None)
        assert lv_none._get_bullet_char(0) == ""

    def test_set_items(self):
        """Test updating ListView items."""
        listview = ListView(items=["Item 1"])
        assert len(listview.items) == 1

        new_items = ["New 1", "New 2", "New 3"]
        listview.set_items(new_items)

        assert len(listview.items) == 3
        assert listview.items[0]["label"] == "New 1"

    def test_keyboard_scrolling(self):
        """Test keyboard navigation for scrolling."""
        # Create ListView with more items than viewport
        items = [f"Item {i}" for i in range(20)]
        listview = ListView(items=items, height=10)

        initial_pos = listview.scroll_manager.state.scroll_position

        # Scroll down
        listview.handle_key(Keys.DOWN)
        assert listview.scroll_manager.state.scroll_position > initial_pos

        # Scroll up
        current_pos = listview.scroll_manager.state.scroll_position
        listview.handle_key(Keys.UP)
        assert listview.scroll_manager.state.scroll_position < current_pos

        # Home key
        listview.handle_key(Keys.HOME)
        assert listview.scroll_manager.state.scroll_position == 0

        # End key
        listview.handle_key(Keys.END)
        assert listview.scroll_manager.state.scroll_position > 0

    def test_mouse_scrolling(self):
        """Test mouse wheel scrolling."""
        # Create ListView with more items than viewport
        items = [f"Item {i}" for i in range(20)]
        listview = ListView(items=items, height=10)

        initial_pos = listview.scroll_manager.state.scroll_position

        # Scroll down with mouse wheel
        event_down = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_DOWN,
            x=0,
            y=0,
        )
        listview.handle_mouse(event_down)
        assert listview.scroll_manager.state.scroll_position > initial_pos

        # Scroll up with mouse wheel
        current_pos = listview.scroll_manager.state.scroll_position
        event_up = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_UP,
            x=0,
            y=0,
        )
        listview.handle_mouse(event_up)
        assert listview.scroll_manager.state.scroll_position < current_pos

    def test_render_basic(self):
        """Test basic rendering."""
        items = ["Apple", "Banana", "Cherry"]
        listview = ListView(items=items, width=40, height=10)
        listview.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(listview, width=40, height=10)
        assert isinstance(output, str)
        assert "Apple" in output
        assert "Banana" in output
        assert "Cherry" in output

    def test_render_with_borders(self):
        """Test rendering with different border styles."""
        items = ["Item 1", "Item 2"]

        # Single border
        lv_single = ListView(items=items, border_style="single", width=40, height=10)
        lv_single.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(lv_single, width=40, height=10)
        assert isinstance(output, str)

        # Double border
        lv_double = ListView(items=items, border_style="double", width=40, height=10)
        lv_double.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(lv_double, width=40, height=10)
        assert isinstance(output, str)

        # Rounded border
        lv_rounded = ListView(items=items, border_style="rounded", width=40, height=10)
        lv_rounded.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(lv_rounded, width=40, height=10)
        assert isinstance(output, str)

        # No border
        lv_none = ListView(items=items, border_style="none", width=40, height=10)
        lv_none.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(lv_none, width=40, height=10)
        assert isinstance(output, str)

    def test_render_with_title(self):
        """Test rendering with title."""
        items = ["Item 1", "Item 2"]
        listview = ListView(
            items=items, title="My List", border_style="single", width=40, height=10
        )
        listview.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(listview, width=40, height=10)
        assert isinstance(output, str)
        assert "My List" in output

    def test_render_with_scrollbar(self):
        """Test rendering with scrollbar."""
        # Create ListView with more items than viewport
        items = [f"Item {i}" for i in range(20)]
        listview = ListView(
            items=items, width=40, height=10, show_scrollbar=True, border_style="single"
        )
        listview.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(listview, width=40, height=10)
        assert isinstance(output, str)
        # Scrollbar characters should be present when content is scrollable

    def test_render_with_dividers(self):
        """Test rendering with dividers."""
        items = ["Item 1", "Item 2", "Item 3"]
        listview = ListView(
            items=items, show_dividers=True, width=40, height=10, border_style="none"
        )
        listview.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(listview, width=40, height=10)
        assert isinstance(output, str)
        # Dividers should be present between items

    def test_render_with_details(self):
        """Test rendering items with details."""
        items = [
            ("Task 1", "This is the first task"),
            ("Task 2", "This is the second task\nWith multiple lines"),
        ]
        listview = ListView(items=items, width=50, height=15)
        listview.set_bounds(Bounds(0, 0, 50, 15))

        output = render_element(listview, width=50, height=15)
        assert isinstance(output, str)
        assert "Task 1" in output
        assert "Task 2" in output
        # Details should be rendered (might be stripped of ANSI codes in output)

    def test_details_indentation(self):
        """Test custom details indentation."""
        items = [("Label", "Details")]

        lv_indent_2 = ListView(items=items, indent_details=2)
        lv_indent_4 = ListView(items=items, indent_details=4)

        # Verify indentation is applied
        assert lv_indent_2.indent_details == 2
        assert lv_indent_4.indent_details == 4

    def test_scroll_manager_integration(self):
        """Test ScrollManager integration."""
        items = [f"Item {i}" for i in range(20)]
        listview = ListView(items=items, height=10, border_style="single")

        # Content size should match rendered lines
        assert listview.scroll_manager.state.content_size == len(
            listview.rendered_lines
        )
        assert listview.scroll_manager.state.is_scrollable

        # Update items
        new_items = [f"Item {i}" for i in range(5)]
        listview.set_items(new_items)

        assert listview.scroll_manager.state.content_size == len(
            listview.rendered_lines
        )
        # Should not be scrollable with fewer items
        if listview.scroll_manager.state.viewport_size >= len(listview.rendered_lines):
            assert not listview.scroll_manager.state.is_scrollable

    def test_restore_scroll_position(self):
        """Test restoring scroll position."""
        items = [f"Item {i}" for i in range(20)]
        listview = ListView(items=items, height=10)

        # Scroll to position 5
        listview.scroll_manager.scroll_to(5)
        assert listview.scroll_manager.state.scroll_position == 5

        # Restore to position 10
        listview.restore_scroll_position(10)
        assert listview.scroll_manager.state.scroll_position == 10

    def test_long_items_clipping(self):
        """Test that long items are clipped properly."""
        long_item = "A" * 100  # Very long item
        listview = ListView(
            items=[long_item], width=40, height=10, border_style="single"
        )
        listview.set_bounds(Bounds(0, 0, 40, 10))

        output = render_element(listview, width=40, height=10)
        assert isinstance(output, str)
        # Should not crash with long items

    def test_multiline_details(self):
        """Test items with multi-line details."""
        items = [("Item", "Line 1\nLine 2\nLine 3")]
        listview = ListView(items=items, width=40, height=10)

        # Should render multiple detail lines
        assert len(listview.rendered_lines) > 1  # Label + detail lines

    def test_page_up_page_down(self):
        """Test page up and page down scrolling."""
        items = [f"Item {i}" for i in range(30)]
        listview = ListView(items=items, height=10)

        # Page down
        initial_pos = listview.scroll_manager.state.scroll_position
        listview.handle_key(Keys.PAGE_DOWN)
        assert listview.scroll_manager.state.scroll_position > initial_pos

        # Page up
        current_pos = listview.scroll_manager.state.scroll_position
        listview.handle_key(Keys.PAGE_UP)
        assert listview.scroll_manager.state.scroll_position < current_pos

    def test_bullet_with_details(self):
        """Test different bullet styles with details."""
        items = [("Item 1", "Details 1"), ("Item 2", "Details 2")]

        # Numbered list with details
        lv_number = ListView(items=items, bullet="number", width=50, height=15)
        lv_number.set_bounds(Bounds(0, 0, 50, 15))
        output = render_element(lv_number, width=50, height=15)
        assert isinstance(output, str)

        # Dashed list with details
        lv_dash = ListView(items=items, bullet="dash", width=50, height=15)
        lv_dash.set_bounds(Bounds(0, 0, 50, 15))
        output = render_element(lv_dash, width=50, height=15)
        assert isinstance(output, str)

    def test_dividers_with_details(self):
        """Test dividers with details items."""
        items = [("Item 1", "Details 1"), ("Item 2", "Details 2")]
        listview = ListView(items=items, show_dividers=True, width=50, height=20)
        listview.set_bounds(Bounds(0, 0, 50, 20))

        # Dividers should be between item groups (after details)
        output = render_element(listview, width=50, height=20)
        assert isinstance(output, str)
