"""Tests for Table display element."""

from wijjit.elements.base import ElementType
from wijjit.elements.display.table import Table
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
        assert table1.columns[0] == {"key": "name", "label": "name", "width": None}
        assert table1.columns[1] == {"key": "age", "label": "age", "width": None}

        # Dict columns
        table2 = Table(
            columns=[
                {"key": "name", "label": "Full Name", "width": 20},
                {"key": "age", "label": "Age", "width": 5},
            ]
        )
        assert table2.columns[0]["label"] == "Full Name"
        assert table2.columns[0]["width"] == 20

    def test_empty_table(self):
        """Test table with no data."""
        table = Table(columns=["name", "age"])
        assert len(table.data) == 0
        assert len(table.columns) == 2

        # Should render without errors
        output = table.render()
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

    def test_mouse_scrolling(self):
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
        table.handle_mouse(event_down)
        assert table.scroll_manager.state.scroll_position > initial_pos

        # Scroll up with mouse wheel
        current_pos = table.scroll_manager.state.scroll_position
        event_up = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_UP,
            x=0,
            y=0,
        )
        table.handle_mouse(event_up)
        assert table.scroll_manager.state.scroll_position < current_pos

    def test_render_basic(self):
        """Test basic rendering."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        table = Table(data=data, columns=["name", "age"], width=40, height=10)

        output = table.render()
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

        output = table.render()
        assert isinstance(output, str)
        # Scrollbar characters should be present when content is scrollable
        # The scrollbar uses box drawing characters

    def test_render_without_header(self):
        """Test rendering without header row."""
        data = [{"name": "Alice", "age": 30}]
        table = Table(data=data, columns=["name", "age"], show_header=False)

        output = table.render()
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

        output = table.render()
        assert "No columns defined" in output
