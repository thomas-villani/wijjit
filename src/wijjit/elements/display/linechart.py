"""LineChart element for line/area chart visualization.

This module provides the LineChart element for displaying trend data
using braille characters for high-resolution rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import Element, ElementType
from wijjit.elements.display.chart_utils import (
    BrailleCanvas,
    calculate_axis_ticks,
    extract_values,
    format_axis_value,
)

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class LineChart(Element):
    """LineChart element for line and area chart visualization.

    This element displays trend data using braille characters for
    high-resolution rendering within terminal constraints.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    data : list or dict, optional
        Single series: list of values/tuples/dicts
        Multi-series: dict of {series_name: [values]}
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 12)
    style : str, optional
        Chart style: "line", "area", "dots" (default: "line")
    show_axis : bool, optional
        Show y-axis with values (default: True)
    axis_width : int, optional
        Width reserved for y-axis (default: 6)
    show_labels : bool, optional
        Show x-axis labels (default: True)
    show_points : bool, optional
        Highlight data points (default: False)
    show_legend : bool, optional
        Show legend for multi-series (default: True)
    color : str, optional
        Color for single series (default: None)
    series_colors : dict, optional
        Colors per series for multi-series (default: None)

    Attributes
    ----------
    data : list or dict
        Raw data
    series : dict of list
        Normalized series data {name: [values]}
    width : int
        Display width
    height : int
        Display height

    Examples
    --------
    Simple line chart:

    >>> chart = LineChart(data=[10, 20, 15, 25, 30, 20])

    Area chart:

    >>> chart = LineChart(data=[10, 20, 30], style="area")

    Multi-series:

    >>> chart = LineChart(data={
    ...     "Sales": [10, 20, 30],
    ...     "Costs": [5, 10, 15]
    ... })
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        data: list[Any] | dict[str, list[Any]] | None = None,
        width: int = 60,
        height: int = 12,
        style: Literal["line", "area", "dots"] = "line",
        show_axis: bool = True,
        axis_width: int = 6,
        show_labels: bool = True,
        show_points: bool = False,
        show_legend: bool = True,
        color: str | None = None,
        series_colors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        # Display properties
        self.width = width
        self.height = height
        self.style = style
        self.show_axis = show_axis
        self.axis_width = axis_width
        self.show_labels = show_labels
        self.show_points = show_points
        self.show_legend = show_legend
        self.color = color
        self.series_colors = series_colors or {}

        # Parse data into series format
        self._raw_data = data
        self.series: dict[str, list[float]] = {}
        self.labels: list[str] = []
        self._parse_data(data)

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    @property
    def data(self) -> list[Any] | dict[str, list[Any]] | None:
        """Get the raw data values.

        Returns
        -------
        list or dict or None
            Raw data values
        """
        return self._raw_data

    @data.setter
    def data(self, value: list[Any] | dict[str, list[Any]] | None) -> None:
        """Set data values (triggers re-parsing).

        Parameters
        ----------
        value : list or dict or None
            New data values
        """
        self.set_data(value if value is not None else [])

    def _parse_data(self, data: list[Any] | dict[str, list[Any]] | None) -> None:
        """Parse input data into series format.

        Parameters
        ----------
        data : list or dict or None
            Input data in various formats
        """
        self.series = {}
        self.labels = []

        if data is None:
            return

        if isinstance(data, dict):
            # Multi-series format: {name: [values]}
            for name, series_data in data.items():
                values, labels = extract_values(series_data)
                self.series[str(name)] = values
                if not self.labels and labels:
                    self.labels = labels
        else:
            # Single series
            values, labels = extract_values(data)
            self.series["data"] = values
            self.labels = labels

    def set_data(self, data: list[Any] | dict[str, list[Any]]) -> None:
        """Update chart data.

        Parameters
        ----------
        data : list or dict
            New data
        """
        self._raw_data = data
        self._parse_data(data)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the chart.

        Returns
        -------
        tuple of int
            (width, height) in characters
        """
        return (self.width, self.height)

    def _get_all_values(self) -> list[float]:
        """Get all values across all series for scaling.

        Returns
        -------
        list of float
            All values
        """
        all_values = []
        for values in self.series.values():
            all_values.extend(values)
        return all_values

    def _render_series(
        self,
        canvas: BrailleCanvas,
        values: list[float],
        min_val: float,
        max_val: float,
        fill: bool = False,
    ) -> None:
        """Render a single series to the canvas.

        Parameters
        ----------
        canvas : BrailleCanvas
            Target canvas
        values : list of float
            Series values
        min_val : float
            Minimum value for scaling
        max_val : float
            Maximum value for scaling
        fill : bool
            Whether to fill below the line (area style)
        """
        if not values:
            return

        num_points = len(values)
        pixel_width = canvas.pixel_width
        pixel_height = canvas.pixel_height

        # Map values to pixel coordinates
        points = []
        for i, val in enumerate(values):
            # X position
            if num_points > 1:
                x = int((i / (num_points - 1)) * (pixel_width - 1))
            else:
                x = pixel_width // 2

            # Y position (inverted, higher values at top)
            if max_val != min_val:
                normalized = (val - min_val) / (max_val - min_val)
            else:
                normalized = 0.5
            y = int((1 - normalized) * (pixel_height - 1))
            y = max(0, min(pixel_height - 1, y))

            points.append((x, y))

        # Draw based on style
        if self.style == "dots":
            # Just plot points
            for x, y in points:
                canvas.set_pixel(x, y)
                # Make points more visible
                if x > 0:
                    canvas.set_pixel(x - 1, y)
                if x < pixel_width - 1:
                    canvas.set_pixel(x + 1, y)
        else:
            # Draw lines between points
            for i in range(len(points) - 1):
                x0, y0 = points[i]
                x1, y1 = points[i + 1]
                canvas.draw_line(x0, y0, x1, y1)

            # Fill area below if area style
            if fill:
                for x, y in points:
                    canvas.fill_below(x, y)

        # Highlight points if requested
        if self.show_points:
            for x, y in points:
                # Create a small cross at each point
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        px, py = x + dx, y + dy
                        if 0 <= px < pixel_width and 0 <= py < pixel_height:
                            canvas.set_pixel(px, py)

    def render_to(self, ctx: PaintContext) -> None:
        """Render the line chart using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Theme styles:

        This element uses the following theme style classes:
        - ``linechart``: Base line chart style
        - ``linechart.line``: Line/data style
        - ``linechart.axis``: Axis line and text style
        - ``linechart.label``: X-axis label style
        - ``linechart.legend``: Legend text style
        """
        from wijjit.terminal.ansi import supports_unicode
        from wijjit.terminal.cell import Cell

        all_values = self._get_all_values()
        if not all_values:
            empty_style = ctx.style_resolver.resolve_style(self, "linechart")
            ctx.write_text(0, 0, "No data", empty_style)
            return

        # Resolve styles
        base_style = ctx.style_resolver.resolve_style(self, "linechart")
        line_style = ctx.style_resolver.resolve_style(self, "linechart.line")
        axis_style = ctx.style_resolver.resolve_style(self, "linechart.axis")
        label_style = ctx.style_resolver.resolve_style(self, "linechart.label")
        legend_style = ctx.style_resolver.resolve_style(self, "linechart.legend")

        use_unicode = supports_unicode()

        # Calculate chart area
        chart_left = self.axis_width if self.show_axis else 0
        chart_bottom = 1 if self.show_labels else 0
        legend_height = 1 if self.show_legend and len(self.series) > 1 else 0
        chart_height = self.height - chart_bottom - legend_height
        chart_width = self.width - chart_left

        if chart_height < 1 or chart_width < 1:
            return

        # Get data range
        min_val = min(all_values)
        max_val = max(all_values)

        # Add some padding to range
        if min_val == max_val:
            min_val -= 1
            max_val += 1

        # Create braille canvas for chart area
        canvas = BrailleCanvas(chart_width, chart_height)

        # Render each series
        fill = self.style == "area"
        for _series_name, values in self.series.items():
            self._render_series(canvas, values, min_val, max_val, fill)

        # Render y-axis
        if self.show_axis:
            axis_attrs = axis_style.to_cell_attrs()
            ticks = calculate_axis_ticks(min_val, max_val, min(5, chart_height // 2))

            # Draw vertical axis line
            for y in range(chart_height):
                ctx.buffer.set_cell(
                    ctx.bounds.x + self.axis_width - 1,
                    ctx.bounds.y + y,
                    Cell(char="\u2502" if use_unicode else "|", **axis_attrs),
                )

            # Draw axis labels and tick marks
            for tick in ticks:
                if max_val != min_val:
                    tick_y = int(
                        (1 - (tick - min_val) / (max_val - min_val))
                        * (chart_height - 1)
                    )
                else:
                    tick_y = chart_height // 2

                if 0 <= tick_y < chart_height:
                    tick_label = format_axis_value(tick, max_val)
                    tick_label = tick_label.rjust(self.axis_width - 2)
                    ctx.write_text(0, tick_y, tick_label, axis_style)

                    # Tick mark
                    ctx.buffer.set_cell(
                        ctx.bounds.x + self.axis_width - 1,
                        ctx.bounds.y + tick_y,
                        Cell(char="\u251c" if use_unicode else "+", **axis_attrs),
                    )

        # Draw x-axis
        if self.show_labels or self.show_axis:
            axis_attrs = axis_style.to_cell_attrs()
            axis_char = "\u2500" if use_unicode else "-"
            axis_y = chart_height

            for x in range(chart_left, self.width):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + axis_y,
                    Cell(char=axis_char, **axis_attrs),
                )

            # Corner
            if self.show_axis:
                ctx.buffer.set_cell(
                    ctx.bounds.x + self.axis_width - 1,
                    ctx.bounds.y + axis_y,
                    Cell(char="\u2514" if use_unicode else "+", **axis_attrs),
                )

        # Write braille canvas to buffer
        lines = canvas.to_lines()
        line_attrs = line_style.to_cell_attrs()

        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                ctx.buffer.set_cell(
                    ctx.bounds.x + chart_left + x,
                    ctx.bounds.y + y,
                    Cell(char=char, **line_attrs),
                )

        # Render x-axis labels
        if self.show_labels and self.labels:
            label_y = self.height - legend_height - 1

            # Calculate label positions
            num_labels = min(len(self.labels), chart_width // 5)  # Max labels that fit
            if num_labels > 0:
                step = max(1, len(self.labels) // num_labels)
                for i in range(0, len(self.labels), step):
                    label = self.labels[i]
                    if len(self.labels) > 1:
                        label_x = chart_left + int(
                            (i / (len(self.labels) - 1)) * (chart_width - 1)
                        )
                    else:
                        label_x = chart_left + chart_width // 2

                    # Truncate and center label
                    display_label = label[:4]
                    ctx.write_text(label_x, label_y, display_label, label_style)

        # Render legend for multi-series
        if self.show_legend and len(self.series) > 1:
            legend_y = self.height - 1
            legend_x = chart_left
            legend_parts = []

            for series_name in self.series.keys():
                marker = "\u2500" if use_unicode else "-"
                legend_parts.append(f"{marker} {series_name}")

            legend_text = "  ".join(legend_parts)
            if len(legend_text) > chart_width:
                legend_text = legend_text[: chart_width - 3] + "..."

            ctx.write_text(legend_x, legend_y, legend_text, legend_style)

        # Fill background
        base_attrs = base_style.to_cell_attrs()
        for y in range(self.height):
            for x in range(self.width):
                cell = ctx.buffer.get_cell(ctx.bounds.x + x, ctx.bounds.y + y)
                if cell is None or cell.char == "\x00":
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + y,
                        Cell(char=" ", **base_attrs),
                    )
