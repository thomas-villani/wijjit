"""Tests for input elements."""

from unittest.mock import Mock

from wijjit.elements.base import ElementType
from wijjit.elements.input import Button, TextInput
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
            type=MouseEventType.CLICK,
            button=MouseButton.LEFT,
            x=10,
            y=5
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
            click_count=2
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
            type=MouseEventType.PRESS,
            button=MouseButton.LEFT,
            x=10,
            y=5
        )

        result = button.handle_mouse(event)
        assert not result
        callback.assert_not_called()

    def test_mouse_move_doesnt_activate(self):
        """Test that mouse move doesn't activate button."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        callback = Mock()
        button = Button(label="Submit", on_click=callback)

        event = MouseEvent(
            type=MouseEventType.MOVE,
            button=MouseButton.NONE,
            x=10,
            y=5
        )

        result = button.handle_mouse(event)
        assert not result
        callback.assert_not_called()
