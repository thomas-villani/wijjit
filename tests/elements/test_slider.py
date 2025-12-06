"""Tests for Slider element."""

from unittest.mock import Mock

from tests.helpers import render_element
from wijjit.elements.input.slider import Slider
from wijjit.terminal.input import Keys


class TestSlider:
    """Tests for Slider element."""

    def test_create_slider(self):
        """Test creating a slider."""
        slider = Slider(id="volume", min_val=0, max_val=100, value=50)
        assert slider.id == "volume"
        assert slider.min_val == 0
        assert slider.max_val == 100
        assert slider.value == 50
        assert slider.focusable

    def test_default_values(self):
        """Test slider with default values."""
        slider = Slider()
        assert slider.min_val == 0
        assert slider.max_val == 100
        assert slider.value == 0
        assert slider.step == 1
        assert slider.width == 20
        assert slider.float_mode is False

    def test_initial_value_defaults_to_min(self):
        """Test value defaults to min_val when not specified."""
        slider = Slider(min_val=10, max_val=50)
        assert slider.value == 10

    def test_value_clamping_max(self):
        """Test value is clamped to max."""
        slider = Slider(min_val=0, max_val=100, value=50)
        slider.value = 150
        assert slider.value == 100

    def test_value_clamping_min(self):
        """Test value is clamped to min."""
        slider = Slider(min_val=0, max_val=100, value=50)
        slider.value = -50
        assert slider.value == 0

    def test_int_mode_returns_int(self):
        """Test int mode returns integer values."""
        slider = Slider(float_mode=False, value=50.7)
        assert isinstance(slider.value, int)
        assert slider.value == 51

    def test_float_mode_returns_float(self):
        """Test float mode returns float values."""
        slider = Slider(float_mode=True, value=50.5)
        assert isinstance(slider.value, float)
        assert slider.value == 50.5

    def test_on_change_callback(self):
        """Test on_change callback is called when value changes."""
        slider = Slider(value=50)
        callback = Mock()
        slider.on_change = callback

        slider.value = 75
        callback.assert_called_once_with(50, 75)

    def test_on_change_not_called_when_value_unchanged(self):
        """Test on_change callback is not called when value doesn't change."""
        slider = Slider(value=50)
        callback = Mock()
        slider.on_change = callback

        slider.value = 50
        callback.assert_not_called()

    def test_on_slide_start_callback(self):
        """Test on_slide_start callback is set correctly."""
        slider = Slider()
        callback = Mock()
        slider.on_slide_start = callback
        assert slider.on_slide_start is callback

    def test_on_slide_end_callback(self):
        """Test on_slide_end callback is set correctly."""
        slider = Slider()
        callback = Mock()
        slider.on_slide_end = callback
        assert slider.on_slide_end is callback

    def test_left_key_decrements(self):
        """Test left arrow decrements value by step."""
        slider = Slider(value=50, step=5)

        result = slider.handle_key(Keys.LEFT)
        assert result is True
        assert slider.value == 45

    def test_right_key_increments(self):
        """Test right arrow increments value by step."""
        slider = Slider(value=50, step=5)

        result = slider.handle_key(Keys.RIGHT)
        assert result is True
        assert slider.value == 55

    def test_home_key_sets_minimum(self):
        """Test home key sets value to minimum."""
        slider = Slider(min_val=10, max_val=100, value=50)

        result = slider.handle_key(Keys.HOME)
        assert result is True
        assert slider.value == 10

    def test_end_key_sets_maximum(self):
        """Test end key sets value to maximum."""
        slider = Slider(min_val=10, max_val=100, value=50)

        result = slider.handle_key(Keys.END)
        assert result is True
        assert slider.value == 100

    def test_other_keys_not_handled(self):
        """Test other keys are not handled."""
        slider = Slider(value=50)

        result = slider.handle_key(Keys.UP)
        assert result is False
        assert slider.value == 50

    def test_value_to_position_at_min(self):
        """Test value to position conversion at minimum."""
        slider = Slider(min_val=0, max_val=100, value=0)
        pos = slider._value_to_position(21)
        assert pos == 0

    def test_value_to_position_at_max(self):
        """Test value to position conversion at maximum."""
        slider = Slider(min_val=0, max_val=100, value=100)
        pos = slider._value_to_position(21)
        assert pos == 20

    def test_value_to_position_at_middle(self):
        """Test value to position conversion at middle."""
        slider = Slider(min_val=0, max_val=100, value=50)
        pos = slider._value_to_position(21)
        assert pos == 10

    def test_position_to_value(self):
        """Test position to value conversion."""
        slider = Slider(min_val=0, max_val=100)
        value = slider._position_to_value(10, 21)
        assert value == 50.0

    def test_intrinsic_size_basic(self):
        """Test intrinsic size calculation."""
        slider = Slider(width=20)
        width, height = slider.get_intrinsic_size()
        assert height == 1
        assert width >= 22  # track width + caps

    def test_intrinsic_size_with_label(self):
        """Test intrinsic size with label."""
        slider = Slider(width=20, label="Volume")
        width, height = slider.get_intrinsic_size()
        assert height == 1
        assert width >= 22 + len("Volume") + 1

    def test_render_output(self):
        """Test rendering slider produces output."""
        slider = Slider(value=50, width=20)
        output = render_element(slider, width=30, height=1)
        # Should contain track characters
        assert len(output) > 0


class TestSliderWithLabel:
    """Tests for Slider with label."""

    def test_label_property(self):
        """Test label property."""
        slider = Slider(label="Volume")
        assert slider.label == "Volume"

    def test_show_value_property(self):
        """Test show_value property."""
        slider = Slider(show_value=False)
        assert slider.show_value is False


class TestSliderFloatMode:
    """Tests for Slider float mode."""

    def test_float_step(self):
        """Test float mode with decimal step."""
        slider = Slider(min_val=0.0, max_val=1.0, value=0.5, step=0.1, float_mode=True)
        slider.value = slider.value + slider.step
        assert abs(slider.value - 0.6) < 0.001

    def test_float_value_display(self):
        """Test float values display correctly."""
        slider = Slider(float_mode=True, value=0.5)
        assert isinstance(slider.value, float)
