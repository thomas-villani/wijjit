"""Tests for StatusIndicator element."""

from tests.helpers import render_element
from wijjit.elements.display.status_indicator import (
    DEFAULT_STATUSES,
    StatusIndicator,
)


class TestStatusIndicator:
    """Tests for StatusIndicator element."""

    def test_create_status_indicator(self):
        """Test creating a status indicator."""
        indicator = StatusIndicator(id="status", status="success", label="Connected")
        assert indicator.id == "status"
        assert indicator.status == "success"
        assert indicator.label == "Connected"
        assert indicator.focusable is False

    def test_default_values(self):
        """Test status indicator with default values."""
        indicator = StatusIndicator()
        assert indicator.status == "info"
        assert indicator.label is None
        assert indicator.indicator_style == "filled"

    def test_default_statuses_available(self):
        """Test default status presets are available."""
        indicator = StatusIndicator()
        assert "error" in indicator._statuses
        assert "warning" in indicator._statuses
        assert "success" in indicator._statuses
        assert "disabled" in indicator._statuses
        assert "info" in indicator._statuses
        assert "pending" in indicator._statuses
        assert "active" in indicator._statuses
        assert "inactive" in indicator._statuses

    def test_status_property_getter(self):
        """Test status property getter."""
        indicator = StatusIndicator(status="error")
        assert indicator.status == "error"

    def test_status_property_setter(self):
        """Test status property setter."""
        indicator = StatusIndicator(status="info")
        indicator.status = "success"
        assert indicator.status == "success"


class TestStatusIndicatorCustomStatuses:
    """Tests for StatusIndicator custom status support."""

    def test_custom_statuses_via_constructor(self):
        """Test custom status registration via constructor."""
        indicator = StatusIndicator(custom_statuses={"processing": "magenta"})
        assert "processing" in indicator._statuses
        assert indicator._statuses["processing"][0] == "magenta"

    def test_custom_status_with_color_only(self):
        """Test custom status with just color."""
        indicator = StatusIndicator(custom_statuses={"custom": "purple"})
        color, char = indicator._statuses["custom"]
        assert color == "purple"
        assert char is None  # Use default indicator

    def test_custom_status_with_indicator(self):
        """Test custom status with custom indicator character."""
        indicator = StatusIndicator(custom_statuses={"pulse": ("cyan", "~")})
        color, char = indicator._statuses["pulse"]
        assert color == "cyan"
        assert char == "~"

    def test_register_status_method(self):
        """Test register_status() method."""
        indicator = StatusIndicator()
        indicator.register_status("new_status", "purple", "+")
        assert "new_status" in indicator._statuses
        assert indicator._statuses["new_status"] == ("purple", "+")

    def test_register_status_without_indicator(self):
        """Test register_status() without custom indicator."""
        indicator = StatusIndicator()
        indicator.register_status("simple", "orange")
        assert "simple" in indicator._statuses
        color, char = indicator._statuses["simple"]
        assert color == "orange"
        assert char is None

    def test_custom_status_overrides_default(self):
        """Test custom status can override default."""
        indicator = StatusIndicator(custom_statuses={"error": "bright_red"})
        assert indicator._statuses["error"][0] == "bright_red"


class TestStatusIndicatorIndicatorStyles:
    """Tests for StatusIndicator indicator styles."""

    def test_filled_style(self):
        """Test filled indicator style."""
        indicator = StatusIndicator(indicator_style="filled")
        assert indicator.indicator_style == "filled"

    def test_hollow_style(self):
        """Test hollow indicator style."""
        indicator = StatusIndicator(indicator_style="hollow")
        assert indicator.indicator_style == "hollow"

    def test_square_style(self):
        """Test square indicator style."""
        indicator = StatusIndicator(indicator_style="square")
        assert indicator.indicator_style == "square"

    def test_ascii_style(self):
        """Test ascii indicator style."""
        indicator = StatusIndicator(indicator_style="ascii")
        assert indicator.indicator_style == "ascii"

    def test_get_indicator_char_filled(self):
        """Test _get_indicator_char for filled style."""
        indicator = StatusIndicator(indicator_style="filled")
        char = indicator._get_indicator_char(use_unicode=True)
        assert char == "\u25cf"

    def test_get_indicator_char_hollow(self):
        """Test _get_indicator_char for hollow style."""
        indicator = StatusIndicator(indicator_style="hollow")
        char = indicator._get_indicator_char(use_unicode=True)
        assert char == "\u25cb"

    def test_get_indicator_char_square(self):
        """Test _get_indicator_char for square style."""
        indicator = StatusIndicator(indicator_style="square")
        char = indicator._get_indicator_char(use_unicode=True)
        assert char == "\u25a0"

    def test_get_indicator_char_ascii_fallback(self):
        """Test _get_indicator_char falls back to ASCII."""
        indicator = StatusIndicator(indicator_style="filled")
        char = indicator._get_indicator_char(use_unicode=False)
        assert char == "*"


class TestStatusIndicatorSize:
    """Tests for StatusIndicator intrinsic size."""

    def test_intrinsic_size_no_label(self):
        """Test intrinsic size without label."""
        indicator = StatusIndicator()
        width, height = indicator.get_intrinsic_size()
        assert width == 1  # Just indicator
        assert height == 1

    def test_intrinsic_size_with_label(self):
        """Test intrinsic size with label."""
        indicator = StatusIndicator(label="Connected")
        width, height = indicator.get_intrinsic_size()
        assert width == 1 + 1 + len("Connected")  # indicator + space + label
        assert height == 1

    def test_intrinsic_size_with_long_label(self):
        """Test intrinsic size with long label."""
        indicator = StatusIndicator(label="This is a very long status label")
        width, height = indicator.get_intrinsic_size()
        expected = 1 + 1 + len("This is a very long status label")
        assert width == expected
        assert height == 1


class TestStatusIndicatorRendering:
    """Tests for StatusIndicator rendering."""

    def test_render_basic(self):
        """Test basic rendering."""
        indicator = StatusIndicator(status="success")
        output = render_element(indicator, width=10, height=1)
        assert len(output) > 0

    def test_render_with_label(self):
        """Test rendering with label."""
        indicator = StatusIndicator(status="error", label="Error")
        output = render_element(indicator, width=20, height=1)
        assert "Error" in output

    def test_render_unknown_status_fallback(self):
        """Test rendering unknown status uses fallback."""
        indicator = StatusIndicator(status="unknown_status_name")
        # Should not raise, will use gray fallback
        output = render_element(indicator, width=10, height=1)
        assert len(output) > 0


class TestStatusIndicatorColorMap:
    """Tests for StatusIndicator color mapping."""

    def test_color_name_to_rgb_basic_colors(self):
        """Test _color_name_to_rgb for basic colors."""
        indicator = StatusIndicator()

        assert indicator._color_name_to_rgb("red") == (255, 0, 0)
        assert indicator._color_name_to_rgb("green") == (0, 255, 0)
        assert indicator._color_name_to_rgb("blue") == (0, 0, 255)
        assert indicator._color_name_to_rgb("yellow") == (255, 255, 0)

    def test_color_name_to_rgb_gray(self):
        """Test _color_name_to_rgb for gray/grey."""
        indicator = StatusIndicator()
        assert indicator._color_name_to_rgb("gray") == (128, 128, 128)
        assert indicator._color_name_to_rgb("grey") == (128, 128, 128)

    def test_color_name_to_rgb_bright_variants(self):
        """Test _color_name_to_rgb for bright color variants."""
        indicator = StatusIndicator()
        assert indicator._color_name_to_rgb("bright_red") is not None
        assert indicator._color_name_to_rgb("bright_green") is not None

    def test_color_name_to_rgb_unknown(self):
        """Test _color_name_to_rgb returns None for unknown colors."""
        indicator = StatusIndicator()
        assert indicator._color_name_to_rgb("unknown_color") is None

    def test_color_name_to_rgb_case_insensitive(self):
        """Test _color_name_to_rgb is case insensitive."""
        indicator = StatusIndicator()
        assert indicator._color_name_to_rgb("RED") == (255, 0, 0)
        assert indicator._color_name_to_rgb("Green") == (0, 255, 0)


class TestDefaultStatusesModule:
    """Tests for DEFAULT_STATUSES module constant."""

    def test_default_statuses_contains_expected(self):
        """Test DEFAULT_STATUSES contains expected statuses."""
        assert "error" in DEFAULT_STATUSES
        assert "warning" in DEFAULT_STATUSES
        assert "success" in DEFAULT_STATUSES
        assert "info" in DEFAULT_STATUSES

    def test_default_statuses_colors(self):
        """Test DEFAULT_STATUSES have expected colors."""
        assert DEFAULT_STATUSES["error"][0] == "red"
        assert DEFAULT_STATUSES["warning"][0] == "yellow"
        assert DEFAULT_STATUSES["success"][0] == "green"
        assert DEFAULT_STATUSES["info"][0] == "blue"
