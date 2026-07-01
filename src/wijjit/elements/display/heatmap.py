"""HeatMap element for grid-based color intensity visualization.

This module provides the HeatMap element for displaying 2D data grids
with color intensity representing values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import Element, ElementType
from wijjit.elements.display.chart_utils import begin_chart_border, get_gradient_color

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class HeatMap(Element):
    """HeatMap element for grid-based color intensity visualization.

    This element displays a 2D grid where cell colors represent values,
    creating a heat map visualization.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    data : list of list, optional
        2D grid of values (default: [])
    width : int, optional
        Display width in columns (default: 40)
    height : int, optional
        Display height in rows (default: 10)
    cell_width : int, optional
        Width of each cell in characters (default: 2)
    cell_height : int, optional
        Height of each cell in rows (default: 1)
    color_scale : str, optional
        Color scale: "green", "red", "blue", "heat", "cool" (default: "heat")
    show_values : bool, optional
        Show values inside cells (default: False)
    show_legend : bool, optional
        Show color legend (default: True)
    show_labels : bool, optional
        Show row/column labels (default: False)
    row_labels : list of str, optional
        Labels for rows (default: None)
    col_labels : list of str, optional
        Labels for columns (default: None)
    min_value : float, optional
        Minimum value for color scaling (default: auto)
    max_value : float, optional
        Maximum value for color scaling (default: auto)
    border : str, optional
        Border style drawn within the element bounds (e.g. ``"single"``,
        ``"double"``, ``"rounded"``, ``"none"``) (default: ``"single"``)

    Attributes
    ----------
    data : list of list
        2D grid data
    width : int
        Display width
    height : int
        Display height

    Examples
    --------
    Simple heat map:

    >>> heatmap = HeatMap(data=[
    ...     [1, 2, 3],
    ...     [4, 5, 6],
    ...     [7, 8, 9]
    ... ])

    With custom color scale:

    >>> heatmap = HeatMap(data=grid, color_scale="cool")

    With labels:

    >>> heatmap = HeatMap(
    ...     data=grid,
    ...     row_labels=["A", "B", "C"],
    ...     col_labels=["X", "Y", "Z"],
    ...     show_labels=True
    ... )
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        data: list[list[float | int]] | None = None,
        width: int = 40,
        height: int = 10,
        cell_width: int = 2,
        cell_height: int = 1,
        color_scale: Literal["green", "red", "blue", "heat", "cool"] = "heat",
        show_values: bool = False,
        show_legend: bool = True,
        show_labels: bool = False,
        row_labels: list[str] | None = None,
        col_labels: list[str] | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        border: str = "single",
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        # Data
        self._raw_data = data or []
        self._grid = self._normalize_grid(self._raw_data)

        # Display properties
        self.width = width
        self.height = height
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.color_scale = color_scale
        self.show_values = show_values
        self.show_legend = show_legend
        self.show_labels = show_labels
        self.row_labels = row_labels or []
        self.col_labels = col_labels or []
        self.min_value = min_value
        self.max_value = max_value
        self.border = border

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    def _normalize_grid(self, data: list[list[Any]]) -> list[list[float]]:
        """Normalize grid data to floats.

        Parameters
        ----------
        data : list of list
            Raw grid data

        Returns
        -------
        list of list of float
            Normalized grid
        """
        return [[float(cell) for cell in row] for row in data]

    @property
    def data(self) -> list[list[float | int]]:
        """Get the raw data values.

        Returns
        -------
        list of list
            Raw data values
        """
        return self._raw_data

    @data.setter
    def data(self, value: list[list[float | int]]) -> None:
        """Set data values (triggers re-normalization).

        Parameters
        ----------
        value : list of list
            New grid data
        """
        self.set_data(value)

    def set_data(self, data: list[list[float | int]]) -> None:
        """Update heat map data.

        Parameters
        ----------
        data : list of list
            New grid data
        """
        self._raw_data = data
        self._grid = self._normalize_grid(data)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the heat map.

        Returns
        -------
        tuple of int
            (width, height) in characters
        """
        return (self.width, self.height)

    def _get_value_range(self) -> tuple[float, float]:
        """Get the value range for color scaling.

        Returns
        -------
        tuple of float
            (min_value, max_value)
        """
        all_values = []
        for row in self._grid:
            all_values.extend(row)

        if not all_values:
            return (0.0, 1.0)

        min_val = self.min_value if self.min_value is not None else min(all_values)
        max_val = self.max_value if self.max_value is not None else max(all_values)

        if min_val == max_val:
            return (min_val - 1, max_val + 1)

        return (min_val, max_val)

    def render_to(self, ctx: PaintContext) -> None:
        """Render the heat map using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Theme styles:

        This element uses the following theme style classes:
        - ``heatmap``: Base heat map style
        - ``heatmap.cell``: Cell style
        - ``heatmap.label``: Label text style
        - ``heatmap.legend``: Legend style
        """
        from wijjit.terminal.cell import Cell

        if not self._grid:
            empty_style = ctx.style_resolver.resolve_style(self, "heatmap")
            ctx.write_text(0, 0, "No data", empty_style)
            return

        # Resolve styles
        base_style = ctx.style_resolver.resolve_style(self, "heatmap")
        label_style = ctx.style_resolver.resolve_style(self, "heatmap.label")
        legend_style = ctx.style_resolver.resolve_style(self, "heatmap.legend")

        # Draw the border (if any) and inset content into the remaining region.
        ctx, avail_width, avail_height = begin_chart_border(
            ctx, self, self.width, self.height, "heatmap.border"
        )

        # use_unicode = supports_unicode()

        # Calculate layout
        label_width = 0
        if self.show_labels and self.row_labels:
            label_width = min(6, max(len(a) for a in self.row_labels) + 1)

        label_height = 1 if self.show_labels and self.col_labels else 0
        legend_height = 1 if self.show_legend else 0

        grid_left = label_width
        grid_top = label_height
        grid_height = avail_height - label_height - legend_height
        grid_width = avail_width - label_width

        # Get value range for color scaling
        min_val, max_val = self._get_value_range()

        # Adjust cell size if needed to fit grid
        visible_cols = grid_width // self.cell_width
        visible_rows = grid_height // self.cell_height

        # Render column labels
        if self.show_labels and self.col_labels:
            for col_idx, label in enumerate(self.col_labels[:visible_cols]):
                x = grid_left + col_idx * self.cell_width
                display_label = label[: self.cell_width]
                ctx.write_text(x, 0, display_label, label_style)

        # Render row labels and cells
        for row_idx, row in enumerate(self._grid[:visible_rows]):
            y = grid_top + row_idx * self.cell_height

            if y >= avail_height - legend_height:
                break

            # Row label
            if self.show_labels and row_idx < len(self.row_labels):
                label = self.row_labels[row_idx][: label_width - 1]
                ctx.write_text(0, y, label, label_style)

            # Cells
            for col_idx, value in enumerate(row[:visible_cols]):
                x = grid_left + col_idx * self.cell_width

                if x >= avail_width:
                    break

                # Get color for this cell
                if max_val != min_val:
                    normalized = (value - min_val) / (max_val - min_val)
                else:
                    normalized = 0.5
                normalized = max(0.0, min(1.0, normalized))

                cell_color = get_gradient_color(normalized, 0.0, 1.0, self.color_scale)

                # Create cell attributes
                base_attrs = base_style.to_cell_attrs()
                cell_attrs = {**base_attrs, "bg_color": cell_color}

                # Determine cell character
                if self.show_values:
                    # Show value in cell
                    value_str = f"{value:.0f}"[: self.cell_width]
                    # Pad to cell width
                    value_str = value_str.center(self.cell_width)[: self.cell_width]
                else:
                    # Use block character
                    value_str = " " * self.cell_width

                # Render cell
                for char_idx, char in enumerate(value_str):
                    cell_x = x + char_idx
                    if cell_x < avail_width:
                        for cell_y_offset in range(self.cell_height):
                            if y + cell_y_offset < avail_height - legend_height:
                                ctx.buffer.set_cell(
                                    ctx.bounds.x + cell_x,
                                    ctx.bounds.y + y + cell_y_offset,
                                    Cell(char=char, **cell_attrs),
                                )

        # Render legend
        if self.show_legend:
            legend_y = avail_height - 1
            # legend_width = min(20, avail_width - 10)

            # Legend label
            min_label = f"{min_val:.0f}"
            max_label = f"{max_val:.0f}"

            ctx.write_text(0, legend_y, min_label, legend_style)

            # Gradient bar
            bar_start = len(min_label) + 1
            bar_end = avail_width - len(max_label) - 1
            bar_width = bar_end - bar_start

            for i in range(bar_width):
                normalized = i / max(1, bar_width - 1)
                bar_color = get_gradient_color(normalized, 0.0, 1.0, self.color_scale)
                bar_attrs = {**base_style.to_cell_attrs(), "bg_color": bar_color}
                ctx.buffer.set_cell(
                    ctx.bounds.x + bar_start + i,
                    ctx.bounds.y + legend_y,
                    Cell(char=" ", **bar_attrs),
                )

            ctx.write_text(bar_end + 1, legend_y, max_label, legend_style)

        # Fill background for empty areas
        base_attrs = base_style.to_cell_attrs()
        for y in range(avail_height):
            for x in range(avail_width):
                cell = ctx.buffer.get_cell(ctx.bounds.x + x, ctx.bounds.y + y)
                if cell is None or cell.char == "\x00":
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + y,
                        Cell(char=" ", **base_attrs),
                    )
