"""Tests for Checkbox and CheckboxGroup elements."""

from unittest.mock import Mock

from tests.helpers import render_element
from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup
from wijjit.terminal.input import Key, Keys, KeyType


class TestCheckbox:
    """Tests for Checkbox element."""

    def test_create_checkbox(self):
        """Test creating a checkbox."""
        checkbox = Checkbox(id="agree", label="I agree to terms")
        assert checkbox.id == "agree"
        assert checkbox.label == "I agree to terms"
        assert checkbox.checked is False
        assert checkbox.focusable

    def test_initial_checked_state(self):
        """Test checkbox with initial checked state."""
        checkbox = Checkbox(label="Option", checked=True)
        assert checkbox.checked is True

    def test_toggle(self):
        """Test toggling checkbox state."""
        checkbox = Checkbox(label="Option")
        assert checkbox.checked is False

        checkbox.toggle()
        assert checkbox.checked is True

        checkbox.toggle()
        assert checkbox.checked is False

    def test_toggle_emits_change(self):
        """Test that toggle emits change event."""
        checkbox = Checkbox(label="Option")
        callback = Mock()
        checkbox.on_change = callback

        checkbox.toggle()
        callback.assert_called_once_with(False, True)

        callback.reset_mock()
        checkbox.toggle()
        callback.assert_called_once_with(True, False)

    def test_space_key_toggles(self):
        """Test space key toggles checkbox."""
        checkbox = Checkbox(label="Option")

        result = checkbox.handle_key(Keys.SPACE)
        assert result is True
        assert checkbox.checked is True

        result = checkbox.handle_key(Keys.SPACE)
        assert result is True
        assert checkbox.checked is False

    def test_enter_key_toggles_and_triggers_action(self):
        """Test enter key toggles checkbox and triggers action callback."""
        checkbox = Checkbox(label="Option")
        action_callback = Mock()
        checkbox.on_action = action_callback

        result = checkbox.handle_key(Keys.ENTER)
        assert result is True
        assert checkbox.checked is True
        action_callback.assert_called_once()

        # Test toggling back
        action_callback.reset_mock()
        result = checkbox.handle_key(Keys.ENTER)
        assert result is True
        assert checkbox.checked is False
        action_callback.assert_called_once()

    def test_other_keys_not_handled(self):
        """Test other keys are not handled."""
        checkbox = Checkbox(label="Option")

        result = checkbox.handle_key(Key("a", KeyType.CHARACTER, "a"))
        assert result is False

    def test_render_unchecked(self):
        """Test rendering unchecked checkbox."""
        checkbox = Checkbox(label="My Option")
        output = render_element(checkbox, width=20, height=1)

        assert "My Option" in output
        # Should contain either unicode or ASCII checkbox
        assert "\u2610" in output or "[ ]" in output

    def test_render_checked(self):
        """Test rendering checked checkbox."""
        checkbox = Checkbox(label="My Option", checked=True)
        output = render_element(checkbox, width=20, height=1)

        assert "My Option" in output
        # Should contain either unicode or ASCII checked
        assert "\u2611" in output or "[X]" in output

    def test_render_focused(self):
        """Test rendering focused checkbox."""
        checkbox = Checkbox(label="My Option")
        checkbox.on_focus()

        output = render_element(checkbox, width=20, height=1)
        assert "My Option" in output
        # Note: Cell-based rendering stores styles in Cell objects, not as ANSI codes.
        # The render_element() helper uses to_text() which extracts only characters.
        # Styling is verified through visual/integration tests.

    def test_value_attribute(self):
        """Test checkbox with value attribute."""
        checkbox = Checkbox(label="Option", value="opt1", checked=True)
        assert checkbox.value == "opt1"


class TestCheckboxGroup:
    """Tests for CheckboxGroup element."""

    def test_create_checkbox_group(self):
        """Test creating a checkbox group."""
        options = ["Option A", "Option B", "Option C"]
        group = CheckboxGroup(id="features", options=options)

        assert group.id == "features"
        assert len(group.options) == 3
        assert group.options[0]["label"] == "Option A"
        assert group.focusable

    def test_initial_selected_values(self):
        """Test checkbox group with initial selections."""
        options = ["A", "B", "C"]
        group = CheckboxGroup(options=options, selected_values=["A", "C"])

        assert "A" in group.selected_values
        assert "C" in group.selected_values
        assert "B" not in group.selected_values

    def test_toggle_option(self):
        """Test toggling option selection."""
        group = CheckboxGroup(options=["A", "B", "C"])

        group.toggle_option(0)
        assert "A" in group.selected_values

        group.toggle_option(0)
        assert "A" not in group.selected_values

    def test_toggle_emits_change(self):
        """Test that toggle emits change event."""
        group = CheckboxGroup(options=["A", "B", "C"])
        callback = Mock()
        group.on_change = callback

        group.toggle_option(0)
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == []  # old values
        assert "A" in args[1]  # new values

    def test_space_key_toggles_highlighted(self):
        """Test space key toggles highlighted option."""
        group = CheckboxGroup(options=["A", "B", "C"])
        group.highlighted_index = 1

        result = group.handle_key(Keys.SPACE)
        assert result is True
        assert "B" in group.selected_values

    def test_vertical_navigation(self):
        """Test vertical navigation with arrow keys."""
        group = CheckboxGroup(options=["A", "B", "C"], orientation="vertical")
        assert group.highlighted_index == 0

        # Navigate down
        result = group.handle_key(Keys.DOWN)
        assert result is True
        assert group.highlighted_index == 1

        result = group.handle_key(Keys.DOWN)
        assert result is True
        assert group.highlighted_index == 2

        # Can't go past end
        result = group.handle_key(Keys.DOWN)
        assert result is True
        assert group.highlighted_index == 2

        # Navigate up
        result = group.handle_key(Keys.UP)
        assert result is True
        assert group.highlighted_index == 1

    def test_horizontal_navigation(self):
        """Test horizontal navigation with arrow keys."""
        group = CheckboxGroup(options=["A", "B", "C"], orientation="horizontal")
        assert group.highlighted_index == 0

        # Navigate right
        result = group.handle_key(Keys.RIGHT)
        assert result is True
        assert group.highlighted_index == 1

        # Navigate left
        result = group.handle_key(Keys.LEFT)
        assert result is True
        assert group.highlighted_index == 0

    def test_enter_triggers_action(self):
        """Test enter key triggers action callback."""
        group = CheckboxGroup(options=["A", "B"])
        action_callback = Mock()
        group.on_action = action_callback

        result = group.handle_key(Keys.ENTER)
        assert result is True
        action_callback.assert_called_once()

    def test_render_vertical(self):
        """Test rendering vertical checkbox group."""
        group = CheckboxGroup(
            options=["Option A", "Option B"],
            orientation="vertical",
            selected_values=["Option A"],
        )

        output = render_element(group, width=30, height=5)
        assert "Option A" in output
        assert "Option B" in output
        # Check it spans multiple lines for vertical
        assert "\n" in output

    def test_render_with_borders(self):
        """Test rendering with borders."""
        group = CheckboxGroup(
            options=["A", "B"], border_style="single", title="Select Options"
        )

        output = render_element(group, width=30, height=5)
        assert "Select Options" in output
        # Should contain border characters
        assert any(
            c in output for c in ["\u2500", "\u2502", "\u250c", "\u2510", "-", "|"]
        )

    def test_dict_options(self):
        """Test checkbox group with dict options."""
        options = [
            {"value": "opt1", "label": "First Option"},
            {"value": "opt2", "label": "Second Option"},
        ]
        group = CheckboxGroup(options=options, selected_values=["opt1"])

        assert len(group.options) == 2
        assert group.options[0]["value"] == "opt1"
        assert group.options[0]["label"] == "First Option"
        assert "opt1" in group.selected_values

    def test_width_attribute(self):
        """Test checkbox group width."""
        group = CheckboxGroup(options=["A", "B"], width=30)
        assert group.width == 30

        output = render_element(group, width=30, height=5)
        # Lines should be padded to width
        lines = output.split("\n")
        for line in lines:
            # Strip ANSI codes to check visible length
            from wijjit.terminal.ansi import visible_length

            assert visible_length(line) >= 30 or visible_length(line) == 0
