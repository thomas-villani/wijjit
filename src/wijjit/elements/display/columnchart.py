"""ColumnChart element for vertical column chart visualization.

This module provides the ColumnChart element for displaying data as
vertical columns with optional labels, axis, and color gradients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import Element, ElementType
from wijjit.elements.display.chart_utils import (
    calculate_axis_ticks,
    extract_values,
    format_axis_value,
    get_block_char,
    get_gradient_color,
    get_threshold_color,
    normalize_data,
)

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class ColumnChart(Element):
    """ColumnChart element for vertical column visualization.

    This element displays data as vertical columns with support for:
    - Labels on the x-axis (bottom)
    - Y-axis with scaled values
    - Single color, gradient, or threshold-based coloring
    - Optional grid lines
    - Configurable column width and spacing

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    data : list, optional
        Data as numbers, tuples (label, value), or dicts (default: [])
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 15)
    column_width : int, optional
        Width of each column in characters (default: 3)
    spacing : int, optional
        Spacing between columns (default: 1)
    show_labels : bool, optional
        Show labels on x-axis (default: True)
    show_axis : bool, optional
        Show y-axis with values (default: True)
    axis_width : int, optional
        Width reserved for y-axis (default: 6)
    show_grid : bool, optional
        Show horizontal grid lines (default: False)
    color : str, optional
        Color mode: "default", "gradient", "threshold" (default: "default")
    color_scale : str, optional
        Color scale for gradient mode (default: "green")

    Attributes
    ----------
    data : list
        Raw data
    values : list of float
        Extracted numeric values
    labels : list of str
        Extracted labels
    width : int
        Display width
    height : int
        Display height

    Examples
    --------
    Simple column chart:

    >>> chart = ColumnChart(data=[10, 20, 30, 40, 50])

    With labels:

    >>> chart = ColumnChart(data=[
    ...     ("Jan", 100), ("Feb", 150), ("Mar", 200)
    ... ])

    Gradient coloring:

    >>> chart = ColumnChart(data=[10, 50, 90], color="gradient")
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        data: list[Any] | None = None,
        width: int = 60,
        height: int = 15,
        column_width: int = 3,
        spacing: int = 1,
        show_labels: bool = True,
        show_axis: bool = True,
        axis_width: int = 6,
        show_grid: bool = False,
        color: Literal["default", "gradient", "threshold"] = "default",
        color_scale: str = "green",
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        # Data
        self._raw_data = data or []
        self.values, self.labels = extract_values(self._raw_data)

        # Display properties
        self.width = width
        self.height = height
        self.column_width = column_width
        self.spacing = spacing
        self.show_labels = show_labels
        self.show_axis = show_axis
        self.axis_width = axis_width
        self.show_grid = show_grid
        self.color = color
        self.color_scale = color_scale

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    @property
    def data(self) -> list[Any]:
        """Get the raw data values.

        Returns
        -------
        list
            Raw data values
        """
        return self._raw_data

    @data.setter
    def data(self, value: list[Any]) -> None:
        """Set data values (triggers re-extraction).

        Parameters
        ----------
        value : list
            New data values
        """
        self.set_data(value)

    def set_data(self, data: list[Any]) -> None:
        """Update chart data.

        Parameters
        ----------
        data : list
            New data values
        """
        self._raw_data = data
        self.values, self.labels = extract_values(data)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the chart.

        Returns
        -------
        tuple of int
            (width, height) in characters
        """
        return (self.width, self.height)

    def _get_column_color(
        self, value: float, normalized: float
    ) -> tuple[int, int, int] | None:
        """Get the color for a column based on its value.

        Parameters
        ----------
        value : float
            Raw value
        normalized : float
            Normalized value (0-1)

        Returns
        -------
        tuple of int or None
            RGB color tuple, or None for default
        """
        if self.color == "gradient":
            return get_gradient_color(
                normalized, 0.0, 1.0, self.color_scale  # type: ignore
            )
        elif self.color == "threshold":
            return get_threshold_color(normalized)
        return None

    def render_to(self, ctx: PaintContext) -> None:
        """Render the column chart using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'columnchart': Base column chart style
        - 'columnchart.column': Column fill style
        - 'columnchart.column.empty': Empty column portion style
        - 'columnchart.axis': Axis line and text style
        - 'columnchart.label': X-axis label style
        - 'columnchart.grid': Grid line style
        """
        from wijjit.terminal.ansi import supports_unicode
        from wijjit.terminal.cell import Cell

        if not self.values:
            empty_style = ctx.style_resolver.resolve_style(self, "columnchart")
            ctx.write_text(0, 0, "No data", empty_style)
            return

        # Resolve styles
        base_style = ctx.style_resolver.resolve_style(self, "columnchart")
        column_style = ctx.style_resolver.resolve_style(self, "columnchart.column")
        empty_style = ctx.style_resolver.resolve_style(self, "columnchart.column.empty")
        axis_style = ctx.style_resolver.resolve_style(self, "columnchart.axis")
        label_style = ctx.style_resolver.resolve_style(self, "columnchart.label")
        grid_style = ctx.style_resolver.resolve_style(self, "columnchart.grid")

        use_unicode = supports_unicode()

        # Calculate chart area dimensions
        chart_left = self.axis_width if self.show_axis else 0
        chart_bottom = 1 if self.show_labels else 0  # Row for labels
        chart_height = self.height - chart_bottom - 1  # -1 for top margin
        chart_width = self.width - chart_left

        if chart_height < 1 or chart_width < 1:
            return

        # Normalize data
        normalized, min_val, max_val = normalize_data(self.values)

        # Calculate axis ticks
        ticks = calculate_axis_ticks(min_val, max_val, min(5, chart_height // 2))

        # Calculate column positions
        total_column_space = self.column_width + self.spacing
        num_columns = len(self.values)
        total_needed_width = num_columns * total_column_space - self.spacing

        # Adjust column width if needed to fit
        if total_needed_width > chart_width and num_columns > 0:
            available_per_column = chart_width // num_columns
            self.column_width = max(1, available_per_column - self.spacing)
            total_column_space = self.column_width + self.spacing

        # Render y-axis
        if self.show_axis:
            axis_attrs = axis_style.to_cell_attrs()

            # Draw vertical axis line
            for y in range(chart_height + 1):
                ctx.buffer.set_cell(
                    ctx.bounds.x + self.axis_width - 1,
                    ctx.bounds.y + y,
                    Cell(char="\u2502" if use_unicode else "|", **axis_attrs),
                )

            # Draw axis labels
            for tick in ticks:
                if max_val == min_val:
                    tick_y = chart_height // 2
                else:
                    tick_y = int(
                        (1 - (tick - min_val) / (max_val - min_val)) * chart_height
                    )

                if 0 <= tick_y <= chart_height:
                    tick_label = format_axis_value(tick, max_val)
                    tick_label = tick_label.rjust(self.axis_width - 2)
                    ctx.write_text(0, tick_y, tick_label, axis_style)

                    # Draw tick mark
                    ctx.buffer.set_cell(
                        ctx.bounds.x + self.axis_width - 1,
                        ctx.bounds.y + tick_y,
                        Cell(char="\u251c" if use_unicode else "+", **axis_attrs),
                    )

                    # Draw grid line if enabled
                    if self.show_grid and tick_y > 0:
                        grid_char = "\u2500" if use_unicode else "-"
                        grid_attrs = grid_style.to_cell_attrs()
                        for x in range(chart_left, self.width):
                            ctx.buffer.set_cell(
                                ctx.bounds.x + x,
                                ctx.bounds.y + tick_y,
                                Cell(char=grid_char, **grid_attrs),
                            )

        # Draw x-axis (bottom line)
        if self.show_labels or self.show_axis:
            axis_attrs = axis_style.to_cell_attrs()
            axis_char = "\u2500" if use_unicode else "-"
            bottom_y = chart_height

            for x in range(chart_left, self.width):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + bottom_y,
                    Cell(char=axis_char, **axis_attrs),
                )

            # Corner
            if self.show_axis:
                ctx.buffer.set_cell(
                    ctx.bounds.x + self.axis_width - 1,
                    ctx.bounds.y + bottom_y,
                    Cell(char="\u2514" if use_unicode else "+", **axis_attrs),
                )

        # Render columns
        for i, (value, norm_val) in enumerate(
            zip(self.values, normalized, strict=True)
        ):
            column_x = chart_left + i * total_column_space

            if column_x >= self.width:
                break

            # Calculate column height (in characters)
            column_height = max(0, int(norm_val * chart_height))

            # Get column color
            column_color = self._get_column_color(value, norm_val)

            # Column rendering attributes
            col_attrs = column_style.to_cell_attrs()
            if column_color:
                col_attrs = {**col_attrs, "fg_color": column_color}

            empty_attrs = empty_style.to_cell_attrs()

            # Draw column from bottom up
            fill_char = "\u2588" if use_unicode else "#"
            empty_char = " "

            for y in range(chart_height):
                row_y = y  # y from top
                is_filled = (chart_height - y - 1) < column_height

                for col_x in range(self.column_width):
                    x_pos = column_x + col_x
                    if x_pos >= self.width:
                        break

                    if is_filled:
                        ctx.buffer.set_cell(
                            ctx.bounds.x + x_pos,
                            ctx.bounds.y + row_y,
                            Cell(char=fill_char, **col_attrs),
                        )
                    else:
                        ctx.buffer.set_cell(
                            ctx.bounds.x + x_pos,
                            ctx.bounds.y + row_y,
                            Cell(char=empty_char, **empty_attrs),
                        )

            # Partial fill at top (fractional part)
            fractional = norm_val * chart_height - int(norm_val * chart_height)
            if fractional > 0 and column_height < chart_height:
                partial_y = chart_height - column_height - 1
                if partial_y >= 0:
                    partial_char = get_block_char(fractional, "vertical", use_unicode)
                    for col_x in range(self.column_width):
                        x_pos = column_x + col_x
                        if x_pos >= self.width:
                            break
                        ctx.buffer.set_cell(
                            ctx.bounds.x + x_pos,
                            ctx.bounds.y + partial_y,
                            Cell(char=partial_char, **col_attrs),
                        )

        # Render x-axis labels
        if self.show_labels:
            label_y = self.height - 1
            for i, label in enumerate(self.labels):
                column_x = chart_left + i * total_column_space

                if column_x >= self.width:
                    break

                # Truncate label to column width
                display_label = label[: self.column_width]

                # Center label under column
                if len(display_label) < self.column_width:
                    padding = (self.column_width - len(display_label)) // 2
                    column_x += padding

                ctx.write_text(column_x, label_y, display_label, label_style)

        # Fill remaining space with background
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
