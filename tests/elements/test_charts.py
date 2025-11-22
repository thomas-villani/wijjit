"""Unit tests for chart elements.

This module tests all chart visualization elements including:
- chart_utils module
- Sparkline
- BarChart
- ColumnChart
- LineChart
- Gauge
- HeatMap
"""


from wijjit.elements.base import ElementType
from wijjit.elements.display.barchart import BarChart
from wijjit.elements.display.chart_utils import (
    BrailleCanvas,
    calculate_axis_ticks,
    extract_values,
    format_axis_value,
    get_block_char,
    get_gradient_color,
    get_threshold_color,
    normalize_data,
    scale_value,
)
from wijjit.elements.display.columnchart import ColumnChart
from wijjit.elements.display.gauge import Gauge
from wijjit.elements.display.heatmap import HeatMap
from wijjit.elements.display.linechart import LineChart
from wijjit.elements.display.sparkline import Sparkline
from wijjit.layout.bounds import Bounds
from wijjit.rendering.paint_context import PaintContext
from wijjit.styling.resolver import StyleResolver
from wijjit.styling.theme import DefaultTheme
from wijjit.terminal.screen_buffer import ScreenBuffer


class TestChartUtils:
    """Tests for chart_utils module."""

    def test_normalize_data_basic(self):
        """Test basic data normalization."""
        data = [0, 50, 100]
        normalized, min_val, max_val = normalize_data(data)

        assert normalized == [0.0, 0.5, 1.0]
        assert min_val == 0
        assert max_val == 100

    def test_normalize_data_empty(self):
        """Test normalization with empty data."""
        normalized, min_val, max_val = normalize_data([])

        assert normalized == []
        assert min_val == 0.0
        assert max_val == 0.0

    def test_normalize_data_single_value(self):
        """Test normalization with single value."""
        normalized, min_val, max_val = normalize_data([50])

        assert normalized == [0.5]
        assert min_val == 50
        assert max_val == 50

    def test_normalize_data_custom_range(self):
        """Test normalization with custom min/max."""
        data = [25, 50, 75]
        normalized, min_val, max_val = normalize_data(data, min_val=0, max_val=100)

        assert normalized == [0.25, 0.5, 0.75]

    def test_scale_value(self):
        """Test value scaling between ranges."""
        # Scale 50 from 0-100 to 0-10
        assert scale_value(50, 0, 100, 0, 10) == 5

        # Scale 25 from 0-100 to 0-20
        assert scale_value(25, 0, 100, 0, 20) == 5

    def test_get_block_char(self):
        """Test block character selection."""
        # Empty
        assert get_block_char(0.0, "horizontal") == " "

        # Full
        assert get_block_char(1.0, "horizontal") != " "

        # Partial
        assert get_block_char(0.5, "vertical") != " "

    def test_calculate_axis_ticks(self):
        """Test axis tick calculation."""
        ticks = calculate_axis_ticks(0, 100, 5)

        assert len(ticks) >= 2
        assert ticks[0] <= 0
        assert ticks[-1] >= 100

    def test_format_axis_value(self):
        """Test axis value formatting."""
        assert "M" in format_axis_value(1500000, 2000000)
        assert "K" in format_axis_value(1500, 2000)
        assert "." not in format_axis_value(50, 100)

    def test_get_gradient_color(self):
        """Test gradient color generation."""
        low_color = get_gradient_color(0.0, 0.0, 1.0, "green")
        high_color = get_gradient_color(1.0, 0.0, 1.0, "green")

        assert isinstance(low_color, tuple)
        assert len(low_color) == 3
        assert all(0 <= c <= 255 for c in low_color)
        assert low_color != high_color

    def test_get_threshold_color(self):
        """Test threshold-based color selection."""
        low_color = get_threshold_color(0.1)  # Should be red
        mid_color = get_threshold_color(0.5)  # Should be yellow
        high_color = get_threshold_color(0.9)  # Should be green

        # Colors should be different
        assert low_color != mid_color
        assert mid_color != high_color

    def test_extract_values_list(self):
        """Test extracting values from simple list."""
        values, labels = extract_values([10, 20, 30])

        assert values == [10.0, 20.0, 30.0]
        assert labels == ["0", "1", "2"]

    def test_extract_values_tuples(self):
        """Test extracting values from tuple list."""
        data = [("A", 10), ("B", 20)]
        values, labels = extract_values(data)

        assert values == [10.0, 20.0]
        assert labels == ["A", "B"]

    def test_extract_values_dicts(self):
        """Test extracting values from dict list."""
        data = [{"label": "X", "value": 100}, {"label": "Y", "value": 200}]
        values, labels = extract_values(data)

        assert values == [100.0, 200.0]
        assert labels == ["X", "Y"]


class TestBrailleCanvas:
    """Tests for BrailleCanvas class."""

    def test_canvas_creation(self):
        """Test canvas initialization."""
        canvas = BrailleCanvas(10, 5)

        assert canvas.width == 10
        assert canvas.height == 5
        assert canvas.pixel_width == 20
        assert canvas.pixel_height == 20

    def test_set_pixel(self):
        """Test setting individual pixels."""
        canvas = BrailleCanvas(5, 2)

        canvas.set_pixel(0, 0)
        assert canvas.get_pixel(0, 0) is True

        canvas.set_pixel(5, 3)
        assert canvas.get_pixel(5, 3) is True

    def test_unset_pixel(self):
        """Test unsetting pixels."""
        canvas = BrailleCanvas(5, 2)

        canvas.set_pixel(0, 0)
        canvas.unset_pixel(0, 0)
        assert canvas.get_pixel(0, 0) is False

    def test_draw_line(self):
        """Test line drawing."""
        canvas = BrailleCanvas(10, 5)

        canvas.draw_line(0, 0, 9, 9)

        # Check some points along the line
        assert canvas.get_pixel(0, 0) is True
        assert canvas.get_pixel(4, 4) is True

    def test_render(self):
        """Test canvas rendering to strings."""
        canvas = BrailleCanvas(2, 1)

        canvas.set_pixel(0, 0)
        lines = canvas.render()

        assert len(lines) == 1
        assert len(lines[0]) == 2
        # First char should not be empty braille
        assert lines[0][0] != chr(0x2800)

    def test_clear(self):
        """Test canvas clearing."""
        canvas = BrailleCanvas(5, 2)

        canvas.set_pixel(0, 0)
        canvas.set_pixel(5, 5)
        canvas.clear()

        assert canvas.get_pixel(0, 0) is False
        assert canvas.get_pixel(5, 5) is False


class TestSparkline:
    """Tests for Sparkline element."""

    def test_sparkline_creation(self):
        """Test sparkline initialization."""
        sparkline = Sparkline(data=[10, 20, 30])

        assert sparkline.element_type == ElementType.DISPLAY
        assert sparkline.focusable is False
        assert sparkline.values == [10.0, 20.0, 30.0]

    def test_sparkline_set_data(self):
        """Test updating sparkline data."""
        sparkline = Sparkline(data=[10, 20])
        sparkline.set_data([30, 40, 50])

        assert sparkline.values == [30.0, 40.0, 50.0]

    def test_sparkline_intrinsic_size(self):
        """Test intrinsic size calculation."""
        sparkline = Sparkline(width=20, height=1)
        size = sparkline.get_intrinsic_size()

        assert size == (20, 1)

    def test_sparkline_styles(self):
        """Test different sparkline styles."""
        for style in ["line", "bar", "dot"]:
            sparkline = Sparkline(data=[10, 20, 30], style=style)
            assert sparkline.style == style

    def test_sparkline_render(self):
        """Test sparkline rendering."""
        sparkline = Sparkline(data=[10, 20, 30], width=10, height=1)
        buffer = ScreenBuffer(20, 5)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=10, height=1)
        ctx = PaintContext(buffer, resolver, bounds)

        sparkline.render_to(ctx)

        # Should have rendered something
        cell = buffer.get_cell(0, 0)
        assert cell is not None


class TestBarChart:
    """Tests for BarChart element."""

    def test_barchart_creation(self):
        """Test bar chart initialization."""
        data = [{"label": "A", "value": 10}, {"label": "B", "value": 20}]
        chart = BarChart(data=data)

        assert chart.element_type == ElementType.DISPLAY
        assert chart.focusable is True
        assert chart.values == [10.0, 20.0]
        assert chart.labels == ["A", "B"]

    def test_barchart_set_data(self):
        """Test updating bar chart data."""
        chart = BarChart(data=[10, 20])
        chart.set_data([("X", 30), ("Y", 40)])

        assert chart.values == [30.0, 40.0]
        assert chart.labels == ["X", "Y"]

    def test_barchart_scroll(self):
        """Test bar chart scrolling."""
        # Create chart with many bars
        data = [{"label": f"Item{i}", "value": i * 10} for i in range(20)]
        chart = BarChart(data=data, height=5)

        assert chart.can_scroll(1) is True
        assert chart.scroll_position == 0

    def test_barchart_render(self):
        """Test bar chart rendering."""
        chart = BarChart(data=[10, 20, 30], width=30, height=5)
        buffer = ScreenBuffer(40, 10)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=30, height=5)
        ctx = PaintContext(buffer, resolver, bounds)

        chart.render_to(ctx)

        # Should have rendered something
        cell = buffer.get_cell(0, 0)
        assert cell is not None


class TestColumnChart:
    """Tests for ColumnChart element."""

    def test_columnchart_creation(self):
        """Test column chart initialization."""
        data = [("Jan", 100), ("Feb", 150)]
        chart = ColumnChart(data=data)

        assert chart.element_type == ElementType.DISPLAY
        assert chart.values == [100.0, 150.0]
        assert chart.labels == ["Jan", "Feb"]

    def test_columnchart_set_data(self):
        """Test updating column chart data."""
        chart = ColumnChart(data=[10, 20])
        chart.set_data([30, 40, 50])

        assert chart.values == [30.0, 40.0, 50.0]

    def test_columnchart_render(self):
        """Test column chart rendering."""
        chart = ColumnChart(data=[10, 20, 30], width=40, height=10)
        buffer = ScreenBuffer(50, 15)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=40, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        chart.render_to(ctx)

        cell = buffer.get_cell(0, 0)
        assert cell is not None


class TestLineChart:
    """Tests for LineChart element."""

    def test_linechart_creation_single_series(self):
        """Test line chart with single series."""
        chart = LineChart(data=[10, 20, 30])

        assert chart.element_type == ElementType.DISPLAY
        assert "data" in chart.series
        assert chart.series["data"] == [10.0, 20.0, 30.0]

    def test_linechart_creation_multi_series(self):
        """Test line chart with multiple series."""
        data = {
            "Series A": [10, 20, 30],
            "Series B": [15, 25, 35],
        }
        chart = LineChart(data=data)

        assert "Series A" in chart.series
        assert "Series B" in chart.series

    def test_linechart_set_data(self):
        """Test updating line chart data."""
        chart = LineChart(data=[10, 20])
        chart.set_data([30, 40, 50])

        assert chart.series["data"] == [30.0, 40.0, 50.0]

    def test_linechart_styles(self):
        """Test different line chart styles."""
        for style in ["line", "area", "dots"]:
            chart = LineChart(data=[10, 20, 30], style=style)
            assert chart.style == style

    def test_linechart_render(self):
        """Test line chart rendering."""
        chart = LineChart(data=[10, 20, 30, 40], width=40, height=10)
        buffer = ScreenBuffer(50, 15)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=40, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        chart.render_to(ctx)

        cell = buffer.get_cell(0, 0)
        assert cell is not None


class TestGauge:
    """Tests for Gauge element."""

    def test_gauge_creation(self):
        """Test gauge initialization."""
        gauge = Gauge(value=75, max_value=100)

        assert gauge.element_type == ElementType.DISPLAY
        assert gauge.value == 75.0
        assert gauge.max_value == 100.0

    def test_gauge_percentage(self):
        """Test gauge percentage calculation."""
        gauge = Gauge(value=25, min_value=0, max_value=100)

        assert gauge.get_percentage() == 25.0
        assert gauge.get_normalized() == 0.25

    def test_gauge_set_value(self):
        """Test updating gauge value."""
        gauge = Gauge(value=50)
        gauge.set_value(75)

        assert gauge.value == 75.0

    def test_gauge_styles(self):
        """Test different gauge styles."""
        linear = Gauge(value=50, style="linear")
        arc = Gauge(value=50, style="arc")

        assert linear.style == "linear"
        assert arc.style == "arc"

    def test_gauge_render(self):
        """Test gauge rendering."""
        gauge = Gauge(value=75, width=20, height=3)
        buffer = ScreenBuffer(30, 10)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=20, height=3)
        ctx = PaintContext(buffer, resolver, bounds)

        gauge.render_to(ctx)

        cell = buffer.get_cell(0, 0)
        assert cell is not None


class TestHeatMap:
    """Tests for HeatMap element."""

    def test_heatmap_creation(self):
        """Test heat map initialization."""
        data = [[1, 2, 3], [4, 5, 6]]
        heatmap = HeatMap(data=data)

        assert heatmap.element_type == ElementType.DISPLAY
        assert len(heatmap.data) == 2
        assert len(heatmap.data[0]) == 3

    def test_heatmap_set_data(self):
        """Test updating heat map data."""
        heatmap = HeatMap(data=[[1, 2], [3, 4]])
        heatmap.set_data([[5, 6, 7], [8, 9, 10]])

        assert len(heatmap.data) == 2
        assert len(heatmap.data[0]) == 3

    def test_heatmap_color_scales(self):
        """Test different color scales."""
        for scale in ["green", "red", "blue", "heat", "cool"]:
            heatmap = HeatMap(data=[[1, 2], [3, 4]], color_scale=scale)
            assert heatmap.color_scale == scale

    def test_heatmap_render(self):
        """Test heat map rendering."""
        heatmap = HeatMap(data=[[1, 2, 3], [4, 5, 6]], width=20, height=8)
        buffer = ScreenBuffer(30, 15)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=20, height=8)
        ctx = PaintContext(buffer, resolver, bounds)

        heatmap.render_to(ctx)

        cell = buffer.get_cell(0, 0)
        assert cell is not None


class TestChartIntegration:
    """Integration tests for chart elements."""

    def test_all_charts_importable(self):
        """Test that all chart elements can be imported from display module."""
        from wijjit.elements.display import (
            BarChart,
            ColumnChart,
            Gauge,
            HeatMap,
            LineChart,
            Sparkline,
        )

        assert BarChart is not None
        assert ColumnChart is not None
        assert Gauge is not None
        assert HeatMap is not None
        assert LineChart is not None
        assert Sparkline is not None

    def test_chart_empty_data_handling(self):
        """Test charts handle empty data gracefully."""
        sparkline = Sparkline(data=[])
        barchart = BarChart(data=[])
        columnchart = ColumnChart(data=[])
        linechart = LineChart(data=[])
        gauge = Gauge(value=0)
        heatmap = HeatMap(data=[])

        # All should be created without errors
        assert sparkline.values == []
        assert barchart.values == []
        assert columnchart.values == []
        # LineChart creates an empty 'data' series for empty input
        assert linechart.series == {"data": []}
        assert gauge.value == 0.0
        assert heatmap.data == []
