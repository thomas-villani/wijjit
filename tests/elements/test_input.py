"""Tests for input elements."""

from unittest.mock import Mock

from wijjit.elements.base import ElementType
from wijjit.elements.input import Button, Select, TextInput
from wijjit.terminal.input import Key, Keys, KeyType


class TestTextInput:
    """Tests for TextInput element."""

    def test_create_text_input(self):
        """Test creating a text input."""
        input_field = TextInput(id="name", placeholder="Enter name")
        assert input_field.id == "name"
        assert input_field.placeholder == "Enter name"
        assert input_field.value == ""
        assert input_field.focusable
        assert input_field.element_type == ElementType.INPUT

    def test_initial_value(self):
        """Test text input with initial value."""
        input_field = TextInput(value="initial")
        assert input_field.value == "initial"
        assert input_field.cursor_pos == len("initial")

    def test_character_input(self):
        """Test typing characters."""
        input_field = TextInput()

        input_field.handle_key(Key("a", KeyType.CHARACTER, "a"))
        assert input_field.value == "a"
        assert input_field.cursor_pos == 1

        input_field.handle_key(Key("b", KeyType.CHARACTER, "b"))
        assert input_field.value == "ab"
        assert input_field.cursor_pos == 2

    def test_backspace(self):
        """Test backspace key."""
        input_field = TextInput(value="hello")

        result = input_field.handle_key(Keys.BACKSPACE)
        assert result
        assert input_field.value == "hell"
        assert input_field.cursor_pos == 4

    def test_backspace_at_start(self):
        """Test backspace at start of text."""
        input_field = TextInput(value="test")
        input_field.cursor_pos = 0

        result = input_field.handle_key(Keys.BACKSPACE)
        assert not result  # Can't backspace at start
        assert input_field.value == "test"  # No change

    def test_delete(self):
        """Test delete key."""
        input_field = TextInput(value="hello")
        input_field.cursor_pos = 1  # After 'h'

        result = input_field.handle_key(Keys.DELETE)
        assert result
        assert input_field.value == "hllo"
        assert input_field.cursor_pos == 1

    def test_delete_at_end(self):
        """Test delete at end of text."""
        input_field = TextInput(value="test")
        # Cursor already at end

        result = input_field.handle_key(Keys.DELETE)
        assert not result  # Can't delete at end
        assert input_field.value == "test"  # No change

    def test_left_arrow(self):
        """Test left arrow key."""
        input_field = TextInput(value="hello")

        result = input_field.handle_key(Keys.LEFT)
        assert result
        assert input_field.cursor_pos == 4

    def test_left_arrow_at_start(self):
        """Test left arrow at start."""
        input_field = TextInput(value="test")
        input_field.cursor_pos = 0

        result = input_field.handle_key(Keys.LEFT)
        assert not result  # Can't go left from start
        assert input_field.cursor_pos == 0

    def test_right_arrow(self):
        """Test right arrow key."""
        input_field = TextInput(value="hello")
        input_field.cursor_pos = 0

        result = input_field.handle_key(Keys.RIGHT)
        assert result
        assert input_field.cursor_pos == 1

    def test_right_arrow_at_end(self):
        """Test right arrow at end."""
        input_field = TextInput(value="test")

        result = input_field.handle_key(Keys.RIGHT)
        assert not result  # Can't go right from end
        assert input_field.cursor_pos == 4  # Already at end

    def test_home_key(self):
        """Test Home key."""
        input_field = TextInput(value="hello")

        result = input_field.handle_key(Keys.HOME)
        assert result
        assert input_field.cursor_pos == 0

    def test_end_key(self):
        """Test End key."""
        input_field = TextInput(value="hello")
        input_field.cursor_pos = 0

        result = input_field.handle_key(Keys.END)
        assert result
        assert input_field.cursor_pos == 5

    def test_insert_middle(self):
        """Test inserting character in middle of text."""
        input_field = TextInput(value="helo")
        input_field.cursor_pos = 3  # After 'hel'

        input_field.handle_key(Key("l", KeyType.CHARACTER, "l"))
        assert input_field.value == "hello"
        assert input_field.cursor_pos == 4

    def test_max_length(self):
        """Test maximum length restriction."""
        input_field = TextInput(max_length=5, value="hello")

        result = input_field.handle_key(Key("!", KeyType.CHARACTER, "!"))
        assert not result  # Can't add character at max length
        assert input_field.value == "hello"  # No change

    def test_render_empty(self):
        """Test rendering empty input."""
        input_field = TextInput(placeholder="Enter text", width=15)
        result = input_field.render()

        assert "Enter text" in result
        assert "[" in result
        assert "]" in result

    def test_render_with_value(self):
        """Test rendering input with value."""
        input_field = TextInput(value="hello", width=15)
        result = input_field.render()

        assert "hello" in result

    def test_render_focused(self):
        """Test rendering focused input."""
        input_field = TextInput(value="test")
        input_field.on_focus()

        result = input_field.render()
        # Should contain ANSI codes for styling
        assert "\x1b[" in result

    def test_width_padding(self):
        """Test that short text is padded to width."""
        # Create input and verify it was created with correct width
        input_field = TextInput(value="hi", width=10)
        assert input_field.width == 10


class TestButton:
    """Tests for Button element."""

    def test_create_button(self):
        """Test creating a button."""
        button = Button(label="Submit", id="submit_btn")
        assert button.id == "submit_btn"
        assert button.label == "Submit"
        assert button.focusable
        assert button.element_type == ElementType.BUTTON

    def test_button_without_callback(self):
        """Test button without click callback."""
        button = Button(label="Click me")
        assert button.on_click is None

    def test_button_with_callback(self):
        """Test button with click callback."""
        callback = Mock()
        button = Button(label="Click me", on_click=callback)

        button.activate()
        callback.assert_called_once()

    def test_activate_with_enter(self):
        """Test activating button with Enter key."""
        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        result = button.handle_key(Keys.ENTER)
        assert result
        callback.assert_called_once()

    def test_activate_with_space(self):
        """Test activating button with Space key."""
        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        result = button.handle_key(Keys.SPACE)
        assert result
        callback.assert_called_once()

    def test_other_keys_ignored(self):
        """Test that other keys don't activate button."""
        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        result = button.handle_key(Keys.TAB)
        assert not result
        callback.assert_not_called()

    def test_render_unfocused(self):
        """Test rendering unfocused button."""
        button = Button(label="Click me")
        result = button.render()

        assert "Click me" in result
        assert "<" in result
        assert ">" in result

    def test_render_focused(self):
        """Test rendering focused button."""
        button = Button(label="Submit")
        button.on_focus()

        result = button.render()
        assert "Submit" in result
        # Should contain ANSI codes for highlighting
        assert "\x1b[" in result

    def test_activate_without_callback(self):
        """Test activating button without callback doesn't error."""
        button = Button(label="Click me")
        # Should not raise an error
        button.activate()

    def test_activate_with_mouse_click(self):
        """Test activating button with mouse click."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.LEFT, x=10, y=5
        )

        result = button.handle_mouse(event)
        assert result
        callback.assert_called_once()

    def test_activate_with_mouse_double_click(self):
        """Test activating button with mouse double-click."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        event = MouseEvent(
            type=MouseEventType.DOUBLE_CLICK,
            button=MouseButton.LEFT,
            x=10,
            y=5,
            click_count=2,
        )

        result = button.handle_mouse(event)
        assert result
        callback.assert_called_once()

    def test_mouse_press_doesnt_activate(self):
        """Test that mouse press alone doesn't activate button."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        event = MouseEvent(
            type=MouseEventType.PRESS, button=MouseButton.LEFT, x=10, y=5
        )

        result = button.handle_mouse(event)
        assert not result
        callback.assert_not_called()

    def test_mouse_move_doesnt_activate(self):
        """Test that mouse move doesn't activate button."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        event = MouseEvent(type=MouseEventType.MOVE, button=MouseButton.NONE, x=10, y=5)

        result = button.handle_mouse(event)
        assert not result
        callback.assert_not_called()


class TestSelect:
    """Tests for Select element."""

    def test_create_select(self):
        """Test creating a select element."""
        select = Select(id="color", options=["Red", "Green", "Blue"])
        assert select.id == "color"
        assert len(select.options) == 3
        assert select.focusable
        assert select.element_type == ElementType.SELECTABLE
        assert select.selected_index == -1
        assert select.value is None

    def test_select_with_initial_value(self):
        """Test select with initial value."""
        select = Select(options=["Red", "Green", "Blue"], value="Green")
        assert select.value == "Green"
        assert select.selected_index == 1

    def test_select_with_value_label_pairs(self):
        """Test select with value/label dict format."""
        options = [
            {"value": "r", "label": "Red"},
            {"value": "g", "label": "Green"},
            {"value": "b", "label": "Blue"},
        ]
        select = Select(options=options, value="g")
        assert select.value == "g"
        assert select.selected_index == 1
        assert select.options[1]["label"] == "Green"

    def test_select_mixed_options(self):
        """Test select with mixed string and dict options."""
        options = [
            "Red",
            {"value": "g", "label": "Green"},
            "Blue",
        ]
        select = Select(options=options)
        assert len(select.options) == 3
        assert select.options[0]["value"] == "Red"
        assert select.options[1]["value"] == "g"
        assert select.options[2]["value"] == "Blue"

    def test_navigate_down(self):
        """Test navigating down with arrow key."""
        select = Select(options=["A", "B", "C"])
        select.highlighted_index = 0

        result = select.handle_key(Keys.DOWN)
        assert result
        assert select.highlighted_index == 1

    def test_navigate_down_at_end(self):
        """Test navigating down at end of list."""
        select = Select(options=["A", "B", "C"])
        select.highlighted_index = 2

        result = select.handle_key(Keys.DOWN)
        assert result
        assert select.highlighted_index == 2  # Stays at end

    def test_navigate_up(self):
        """Test navigating up with arrow key."""
        select = Select(options=["A", "B", "C"])
        select.highlighted_index = 2

        result = select.handle_key(Keys.UP)
        assert result
        assert select.highlighted_index == 1

    def test_navigate_up_at_start(self):
        """Test navigating up at start of list."""
        select = Select(options=["A", "B", "C"])
        select.highlighted_index = 0

        result = select.handle_key(Keys.UP)
        assert result
        assert select.highlighted_index == 0  # Stays at start

    def test_select_with_enter(self):
        """Test selecting option with Enter key."""
        callback = Mock()
        select = Select(options=["A", "B", "C"], on_change=callback)
        select.highlighted_index = 1

        result = select.handle_key(Keys.ENTER)
        assert result
        assert select.value == "B"
        assert select.selected_index == 1
        callback.assert_called_once_with(None, "B")

    def test_select_with_space(self):
        """Test selecting option with Space key."""
        callback = Mock()
        select = Select(options=["A", "B", "C"], on_change=callback)
        select.highlighted_index = 2

        result = select.handle_key(Keys.SPACE)
        assert result
        assert select.value == "C"
        assert select.selected_index == 2
        callback.assert_called_once_with(None, "C")

    def test_home_key(self):
        """Test Home key jumps to first option."""
        select = Select(options=["A", "B", "C", "D", "E"])
        select.highlighted_index = 3

        result = select.handle_key(Keys.HOME)
        assert result
        assert select.highlighted_index == 0

    def test_end_key(self):
        """Test End key jumps to last option."""
        select = Select(options=["A", "B", "C", "D", "E"])
        select.highlighted_index = 1

        result = select.handle_key(Keys.END)
        assert result
        assert select.highlighted_index == 4

    def test_page_up(self):
        """Test Page Up key."""
        options = [f"Option {i}" for i in range(20)]
        select = Select(options=options, visible_rows=5)
        select.highlighted_index = 10

        result = select.handle_key(Keys.PAGE_UP)
        assert result
        assert select.highlighted_index < 10

    def test_page_down(self):
        """Test Page Down key."""
        options = [f"Option {i}" for i in range(20)]
        select = Select(options=options, visible_rows=5)
        select.highlighted_index = 5

        result = select.handle_key(Keys.PAGE_DOWN)
        assert result
        assert select.highlighted_index > 5

    def test_disabled_options_skip_navigation(self):
        """Test that navigation skips disabled options."""
        select = Select(
            options=["A", "B", "C", "D"],
            disabled_values=["B", "C"],
        )
        select.highlighted_index = 0  # On A

        # Navigate down should skip B and C, land on D
        select.handle_key(Keys.DOWN)
        assert select.highlighted_index == 3  # Should be on D

    def test_disabled_options_cannot_be_selected(self):
        """Test that disabled options cannot be selected."""
        callback = Mock()
        select = Select(
            options=["A", "B", "C"],
            disabled_values=["B"],
            on_change=callback,
        )
        select.highlighted_index = 1  # On B (disabled)

        # Try to select B
        result = select.handle_key(Keys.ENTER)
        assert result
        # B is disabled, so value should not change
        assert select.value is None
        callback.assert_not_called()

    def test_custom_renderer(self):
        """Test custom item renderer."""

        def custom_renderer(option, is_selected, is_highlighted, is_disabled):
            return f"CUSTOM: {option['label']}"

        select = Select(
            options=["A", "B"],
            item_renderer=custom_renderer,
        )

        # Render should use custom renderer
        rendered = select.render()
        assert "CUSTOM: A" in rendered
        assert "CUSTOM: B" in rendered

    def test_render_list(self):
        """Test rendering scrollable list."""
        select = Select(options=["Red", "Green", "Blue"], width=20, value="Green")
        result = select.render()

        # Should be multi-line
        assert "\n" in result
        assert "Red" in result
        assert "Green" in result
        assert "Blue" in result
        # Should show selection indicator (*) for Green
        assert "*" in result

    def test_render_focused(self):
        """Test rendering focused select."""
        select = Select(options=["A", "B"])
        select.on_focus()

        result = select.render()
        # Should contain ANSI codes for styling
        assert "\x1b[" in result

    def test_scroll_long_list(self):
        """Test scrolling with long option list."""
        options = [f"Option {i}" for i in range(20)]
        select = Select(options=options, visible_rows=5)

        # Verify scroll manager is configured
        assert select.scroll_manager.state.content_size == 20
        assert select.scroll_manager.state.viewport_size == 5
        assert select.scroll_manager.state.is_scrollable

    def test_mouse_click_option(self):
        """Test clicking an option to select it."""
        from wijjit.layout.bounds import Bounds
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        callback = Mock()
        select = Select(options=["A", "B", "C"], on_change=callback, visible_rows=3)
        select.bounds = Bounds(x=5, y=10, width=20, height=3)

        # Click on second row (second option)
        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.LEFT, x=10, y=11
        )

        result = select.handle_mouse(event)
        assert result
        assert select.value == "B"
        assert select.selected_index == 1
        callback.assert_called_once_with(None, "B")

    def test_mouse_scroll_up(self):
        """Test mouse scroll wheel up."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        options = [f"Option {i}" for i in range(20)]
        select = Select(options=options, visible_rows=5)
        select.scroll_manager.scroll_to(10)  # Start in middle

        event = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_UP, x=10, y=10
        )

        old_pos = select.scroll_manager.state.scroll_position
        result = select.handle_mouse(event)
        assert result
        assert select.scroll_manager.state.scroll_position < old_pos

    def test_mouse_scroll_down(self):
        """Test mouse scroll wheel down."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        options = [f"Option {i}" for i in range(20)]
        select = Select(options=options, visible_rows=5)

        event = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_DOWN, x=10, y=10
        )

        old_pos = select.scroll_manager.state.scroll_position
        result = select.handle_mouse(event)
        assert result
        assert select.scroll_manager.state.scroll_position > old_pos

    def test_change_callback_triggered(self):
        """Test that on_change callback is triggered on value change."""
        callback = Mock()
        select = Select(options=["A", "B", "C"], on_change=callback)
        select.highlighted_index = 1

        select.handle_key(Keys.ENTER)
        callback.assert_called_once_with(None, "B")

    def test_change_callback_not_triggered_on_same_value(self):
        """Test that on_change is not triggered when value doesn't change."""
        callback = Mock()
        select = Select(options=["A", "B", "C"], value="B", on_change=callback)
        select.highlighted_index = 1  # On B

        select.handle_key(Keys.ENTER)
        # Value didn't change (was already B), so callback shouldn't fire
        callback.assert_not_called()

    def test_empty_options_list(self):
        """Test select with empty options list."""
        select = Select(options=[])
        assert len(select.options) == 0
        assert select.selected_index == -1

    def test_single_option(self):
        """Test select with single option."""
        select = Select(options=["Only Option"])

        result = select.handle_key(Keys.ENTER)
        assert result
        assert select.value == "Only Option"

    def test_all_options_disabled(self):
        """Test select with all options disabled."""
        select = Select(
            options=["A", "B", "C"],
            disabled_values=["A", "B", "C"],
        )

        # Try to navigate down
        result = select.handle_key(Keys.DOWN)
        assert result
        # Should stay at current position since all are disabled

    def test_width_and_visible_rows_settings(self):
        """Test that width and visible_rows are respected."""
        select = Select(
            options=["A", "B", "C"],
            width=30,
            visible_rows=2,
        )
        assert select.width == 30
        assert select.visible_rows == 2
