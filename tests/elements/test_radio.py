"""Tests for Radio and RadioGroup elements."""

from unittest.mock import Mock

from wijjit.elements.input.radio import Radio, RadioGroup
from wijjit.terminal.input import Key, Keys, KeyType


class TestRadio:
    """Tests for Radio element."""

    def test_create_radio(self):
        """Test creating a radio button."""
        radio = Radio(name="size", id="size_m", label="Medium")
        assert radio.id == "size_m"
        assert radio.name == "size"
        assert radio.label == "Medium"
        assert radio.checked is False
        assert radio.focusable

    def test_initial_checked_state(self):
        """Test radio with initial checked state."""
        radio = Radio(name="size", label="Large", checked=True)
        assert radio.checked is True

    def test_select(self):
        """Test selecting radio button."""
        radio = Radio(name="size", label="Small")
        assert radio.checked is False

        radio.select()
        assert radio.checked is True

        # Selecting again should not change state or trigger callback again
        radio.select()
        assert radio.checked is True

    def test_deselect(self):
        """Test deselecting radio button."""
        radio = Radio(name="size", label="Small", checked=True)
        assert radio.checked is True

        radio.deselect()
        assert radio.checked is False

    def test_select_emits_change(self):
        """Test that select emits change event."""
        radio = Radio(name="size", label="Small")
        callback = Mock()
        radio.on_change = callback

        radio.select()
        callback.assert_called_once_with(False, True)

        # Selecting again should not trigger callback
        callback.reset_mock()
        radio.select()
        callback.assert_not_called()

    def test_deselect_emits_change(self):
        """Test that deselect emits change event."""
        radio = Radio(name="size", label="Small", checked=True)
        callback = Mock()
        radio.on_change = callback

        radio.deselect()
        callback.assert_called_once_with(True, False)

    def test_space_key_selects(self):
        """Test space key selects radio."""
        radio = Radio(name="size", label="Small")

        result = radio.handle_key(Keys.SPACE)
        assert result is True
        assert radio.checked is True

    def test_enter_key_triggers_action(self):
        """Test enter key triggers action callback."""
        radio = Radio(name="size", label="Small")
        action_callback = Mock()
        radio.on_action = action_callback

        result = radio.handle_key(Keys.ENTER)
        assert result is True
        action_callback.assert_called_once()

    def test_arrow_keys_navigate_group(self):
        """Test arrow keys navigate within radio group."""
        radio1 = Radio(name="size", label="Small")
        radio2 = Radio(name="size", label="Medium")
        radio3 = Radio(name="size", label="Large")

        # Set up group
        radio_group = [radio1, radio2, radio3]
        radio1.radio_group = radio_group
        radio2.radio_group = radio_group
        radio3.radio_group = radio_group

        # Down arrow from first radio
        result = radio1.handle_key(Keys.DOWN)
        assert result is True
        assert radio2.checked is True

        # Up arrow from second radio
        result = radio2.handle_key(Keys.UP)
        assert result is True
        assert radio1.checked is True

    def test_other_keys_not_handled(self):
        """Test other keys are not handled."""
        radio = Radio(name="size", label="Small")

        result = radio.handle_key(Key("a", KeyType.CHARACTER, "a"))
        assert result is False

    def test_render_unchecked(self):
        """Test rendering unchecked radio."""
        radio = Radio(name="size", label="Medium")
        output = radio.render()

        assert "Medium" in output
        # Should contain either unicode or ASCII radio
        assert "\u25cb" in output or "( )" in output

    def test_render_checked(self):
        """Test rendering checked radio."""
        radio = Radio(name="size", label="Large", checked=True)
        output = radio.render()

        assert "Large" in output
        # Should contain either unicode or ASCII checked
        assert "\u25c9" in output or "(*)" in output

    def test_render_focused(self):
        """Test rendering focused radio."""
        radio = Radio(name="size", label="Medium")
        radio.on_focus()

        output = radio.render()
        assert "Medium" in output
        # Focused radios should have ANSI styling
        assert "\x1b[" in output

    def test_value_attribute(self):
        """Test radio with value attribute."""
        radio = Radio(name="size", label="Medium", value="m", checked=True)
        assert radio.value == "m"


class TestRadioGroup:
    """Tests for RadioGroup element."""

    def test_create_radio_group(self):
        """Test creating a radio group."""
        options = ["Small", "Medium", "Large"]
        group = RadioGroup(name="size", id="size_group", options=options)

        assert group.id == "size_group"
        assert group.name == "size"
        assert len(group.options) == 3
        assert group.options[0]["label"] == "Small"
        assert group.focusable

    def test_initial_selected_value(self):
        """Test radio group with initial selection."""
        options = ["Small", "Medium", "Large"]
        group = RadioGroup(name="size", options=options, selected_value="Medium")

        assert group.selected_value == "Medium"
        assert group.selected_index == 1

    def test_select_option(self):
        """Test selecting option."""
        group = RadioGroup(name="size", options=["S", "M", "L"])

        group.select_option(1)
        assert group.selected_value == "M"
        assert group.selected_index == 1

    def test_select_emits_change(self):
        """Test that select emits change event."""
        group = RadioGroup(name="size", options=["S", "M", "L"])
        callback = Mock()
        group.on_change = callback

        group.select_option(1)
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] is None  # old value
        assert args[1] == "M"  # new value

        # Change selection
        callback.reset_mock()
        group.select_option(2)
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "M"  # old value
        assert args[1] == "L"  # new value

    def test_space_key_selects_highlighted(self):
        """Test space key selects highlighted option."""
        group = RadioGroup(name="size", options=["S", "M", "L"])
        group.highlighted_index = 1

        result = group.handle_key(Keys.SPACE)
        assert result is True
        assert group.selected_value == "M"

    def test_vertical_navigation_auto_selects(self):
        """Test vertical navigation auto-selects options."""
        group = RadioGroup(name="size", options=["S", "M", "L"], orientation="vertical")
        assert group.highlighted_index == 0

        # Navigate down - should auto-select
        result = group.handle_key(Keys.DOWN)
        assert result is True
        assert group.highlighted_index == 1
        assert group.selected_value == "M"

        result = group.handle_key(Keys.DOWN)
        assert result is True
        assert group.highlighted_index == 2
        assert group.selected_value == "L"

        # Can't go past end
        result = group.handle_key(Keys.DOWN)
        assert result is True
        assert group.highlighted_index == 2

        # Navigate up
        result = group.handle_key(Keys.UP)
        assert result is True
        assert group.highlighted_index == 1
        assert group.selected_value == "M"

    def test_horizontal_navigation_auto_selects(self):
        """Test horizontal navigation auto-selects options."""
        group = RadioGroup(
            name="size", options=["S", "M", "L"], orientation="horizontal"
        )
        assert group.highlighted_index == 0

        # Navigate right - should auto-select
        result = group.handle_key(Keys.RIGHT)
        assert result is True
        assert group.highlighted_index == 1
        assert group.selected_value == "M"

        # Navigate left
        result = group.handle_key(Keys.LEFT)
        assert result is True
        assert group.highlighted_index == 0
        assert group.selected_value == "S"

    def test_enter_triggers_action(self):
        """Test enter key triggers action callback."""
        group = RadioGroup(name="size", options=["S", "M"])
        action_callback = Mock()
        group.on_action = action_callback

        result = group.handle_key(Keys.ENTER)
        assert result is True
        action_callback.assert_called_once()

    def test_render_vertical(self):
        """Test rendering vertical radio group."""
        group = RadioGroup(
            name="size",
            options=["Small", "Medium"],
            orientation="vertical",
            selected_value="Small",
        )

        output = group.render()
        assert "Small" in output
        assert "Medium" in output
        # Check it spans multiple lines for vertical
        assert "\n" in output

    def test_render_with_borders(self):
        """Test rendering with borders."""
        group = RadioGroup(
            name="size", options=["S", "M"], border_style="single", title="Select Size"
        )

        output = group.render()
        assert "Select Size" in output
        # Should contain border characters
        assert any(
            c in output for c in ["\u2500", "\u2502", "\u250c", "\u2510", "-", "|"]
        )

    def test_dict_options(self):
        """Test radio group with dict options."""
        options = [
            {"value": "s", "label": "Small"},
            {"value": "m", "label": "Medium"},
        ]
        group = RadioGroup(name="size", options=options, selected_value="s")

        assert len(group.options) == 2
        assert group.options[0]["value"] == "s"
        assert group.options[0]["label"] == "Small"
        assert group.selected_value == "s"

    def test_width_attribute(self):
        """Test radio group width."""
        group = RadioGroup(name="size", options=["S", "M"], width=30)
        assert group.width == 30

        output = group.render()
        # Lines should be padded to width
        lines = output.split("\n")
        for line in lines:
            # Strip ANSI codes to check visible length
            from wijjit.terminal.ansi import visible_length

            assert visible_length(line) >= 30 or visible_length(line) == 0

    def test_find_option_index(self):
        """Test finding option index by value."""
        group = RadioGroup(name="size", options=["S", "M", "L"])

        assert group._find_option_index("S") == 0
        assert group._find_option_index("M") == 1
        assert group._find_option_index("L") == 2
        assert group._find_option_index("XL") == -1
        assert group._find_option_index(None) == -1
