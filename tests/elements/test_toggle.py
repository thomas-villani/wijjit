"""Tests for Toggle element."""

from unittest.mock import Mock

import pytest

from tests.helpers import render_element
from wijjit.elements.input.toggle import Toggle
from wijjit.terminal.input import Key, Keys, KeyType


class TestToggle:
    """Tests for Toggle element."""

    def test_create_toggle(self):
        """Test creating a toggle."""
        toggle = Toggle(id="dark_mode", label="Dark Mode")
        assert toggle.id == "dark_mode"
        assert toggle.label == "Dark Mode"
        assert toggle.checked is False
        assert toggle.focusable

    def test_default_values(self):
        """Test toggle with default values."""
        toggle = Toggle()
        assert toggle.checked is False
        assert toggle.label_mode == "single"
        assert toggle.on_label == "ON"
        assert toggle.off_label == "OFF"

    def test_initial_checked_state(self):
        """Test toggle with initial checked state."""
        toggle = Toggle(checked=True)
        assert toggle.checked is True

    def test_toggle_method(self):
        """Test toggle() method."""
        toggle = Toggle(checked=False)

        toggle.toggle()
        assert toggle.checked is True

        toggle.toggle()
        assert toggle.checked is False

    def test_on_change_callback(self):
        """Test on_change callback is called when state changes."""
        toggle = Toggle(checked=False)
        callback = Mock()
        toggle.on_change = callback

        toggle.toggle()
        callback.assert_called_once_with(False, True)

        callback.reset_mock()
        toggle.toggle()
        callback.assert_called_once_with(True, False)

    def test_on_toggle_callback(self):
        """Test on_toggle callback is called when toggled."""
        toggle = Toggle()
        callback = Mock()
        toggle.on_toggle = callback

        toggle.toggle()
        callback.assert_called_once()

        callback.reset_mock()
        toggle.toggle()
        callback.assert_called_once()

    def test_setting_checked_triggers_on_change(self):
        """Test setting checked property triggers on_change."""
        toggle = Toggle(checked=False)
        callback = Mock()
        toggle.on_change = callback

        toggle.checked = True
        callback.assert_called_once_with(False, True)

    def test_setting_same_value_no_callback(self):
        """Test setting same value does not trigger callback."""
        toggle = Toggle(checked=False)
        callback = Mock()
        toggle.on_change = callback

        toggle.checked = False
        callback.assert_not_called()

    def test_space_key_toggles(self):
        """Test space key toggles."""
        toggle = Toggle(checked=False)

        result = toggle.handle_key(Keys.SPACE)
        assert result is True
        assert toggle.checked is True

        result = toggle.handle_key(Keys.SPACE)
        assert result is True
        assert toggle.checked is False

    def test_enter_key_toggles(self):
        """Test enter key toggles."""
        toggle = Toggle(checked=False)

        result = toggle.handle_key(Keys.ENTER)
        assert result is True
        assert toggle.checked is True

    def test_other_keys_not_handled(self):
        """Test other keys are not handled."""
        toggle = Toggle(checked=False)

        result = toggle.handle_key(Key("a", KeyType.CHARACTER, "a"))
        assert result is False
        assert toggle.checked is False


class TestToggleSingleMode:
    """Tests for Toggle in single label mode."""

    def test_single_mode_label(self):
        """Test single mode with label."""
        toggle = Toggle(label="Dark Mode", label_mode="single")
        assert toggle.label == "Dark Mode"
        assert toggle.label_mode == "single"

    def test_single_mode_intrinsic_size(self):
        """Test intrinsic size in single mode."""
        toggle = Toggle(label="Test", label_mode="single")
        width, height = toggle.get_intrinsic_size()
        assert height == 1
        assert width == 4 + 1 + len("Test")  # switch(4) + space + label

    def test_single_mode_no_label_size(self):
        """Test intrinsic size in single mode without label."""
        toggle = Toggle(label_mode="single")
        width, height = toggle.get_intrinsic_size()
        assert height == 1
        assert width == 4  # just switch

    def test_render_single_mode_unchecked(self):
        """Test rendering in single mode unchecked."""
        toggle = Toggle(label="Dark Mode", label_mode="single", checked=False)
        output = render_element(toggle, width=20, height=1)
        assert "Dark Mode" in output

    def test_render_single_mode_checked(self):
        """Test rendering in single mode checked."""
        toggle = Toggle(label="Dark Mode", label_mode="single", checked=True)
        output = render_element(toggle, width=20, height=1)
        assert "Dark Mode" in output


class TestToggleDualMode:
    """Tests for Toggle in dual label mode."""

    def test_dual_mode_labels(self):
        """Test dual mode with custom labels."""
        toggle = Toggle(label_mode="dual", on_label="Light", off_label="Dark")
        assert toggle.on_label == "Light"
        assert toggle.off_label == "Dark"
        assert toggle.label_mode == "dual"

    def test_dual_mode_intrinsic_size(self):
        """Test intrinsic size in dual mode."""
        toggle = Toggle(label_mode="dual", on_label="ON", off_label="OFF")
        width, height = toggle.get_intrinsic_size()
        assert height == 1
        # OFF + space + switch(4) + space + ON
        expected = len("OFF") + 1 + 4 + 1 + len("ON")
        assert width == expected

    def test_dual_mode_custom_labels_size(self):
        """Test intrinsic size in dual mode with custom labels."""
        toggle = Toggle(label_mode="dual", on_label="Enabled", off_label="Disabled")
        width, height = toggle.get_intrinsic_size()
        expected = len("Disabled") + 1 + 4 + 1 + len("Enabled")
        assert width == expected

    def test_render_dual_mode_unchecked(self):
        """Test rendering in dual mode unchecked."""
        toggle = Toggle(label_mode="dual", checked=False)
        output = render_element(toggle, width=20, height=1)
        assert "OFF" in output
        assert "ON" in output

    def test_render_dual_mode_checked(self):
        """Test rendering in dual mode checked."""
        toggle = Toggle(label_mode="dual", checked=True)
        output = render_element(toggle, width=20, height=1)
        assert "OFF" in output
        assert "ON" in output


class TestToggleMouse:
    """Tests for Toggle mouse handling."""

    @pytest.mark.asyncio
    async def test_click_toggles(self):
        """Test mouse click toggles."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        toggle = Toggle(checked=False)
        event = MouseEvent(x=0, y=0, button=MouseButton.LEFT, type=MouseEventType.CLICK)

        result = await toggle.handle_mouse(event)
        assert result is True
        assert toggle.checked is True

    @pytest.mark.asyncio
    async def test_double_click_toggles(self):
        """Test mouse double click toggles."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        toggle = Toggle(checked=False)
        event = MouseEvent(
            x=0, y=0, button=MouseButton.LEFT, type=MouseEventType.DOUBLE_CLICK
        )

        result = await toggle.handle_mouse(event)
        assert result is True
        assert toggle.checked is True

    @pytest.mark.asyncio
    async def test_right_click_not_handled(self):
        """Test right click is not handled."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        toggle = Toggle(checked=False)
        event = MouseEvent(
            x=0, y=0, button=MouseButton.RIGHT, type=MouseEventType.CLICK
        )

        result = await toggle.handle_mouse(event)
        assert result is False
        assert toggle.checked is False
