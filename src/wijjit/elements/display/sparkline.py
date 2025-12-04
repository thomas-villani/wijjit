"""Sparkline element for compact inline trend visualization.

This module provides the Sparkline element for displaying compact
trend data in a single row using braille, bar, or dot styles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import Element, ElementType
from wijjit.elements.display.chart_utils import (
    BrailleCanvas,
    extract_values,
    get_block_char,
    normalize_data,
)

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class Sparkline(Element):
    """Sparkline element for compact inline trend visualization.

    This element displays a compact trend visualization in a single row,
    suitable for embedding inline with text or in dashboard displays.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    data : list, optional
        Data values as numbers, tuples, or dicts (default: [])
    width : int, optional
        Display width in columns (default: 20)
    height : int, optional
        Display height in rows (default: 1)
    style : str, optional
        Rendering style: "line", "bar", "dot" (default: "line")
    show_minmax : bool, optional
        Show min/max markers (default: False)
    show_current : bool, optional
        Show current (last) value text (default: False)
    color : str, optional
        Color name for the sparkline (default: None)

    Attributes
    ----------
    data : list
        Raw data values
    values : list of float
        Extracted numeric values
    width : int
        Display width
    height : int
        Display height
    style : str
        Rendering style
    show_minmax : bool
        Whether to show min/max markers
    show_current : bool
        Whether to show current value
    color : str or None
        Color name

    Examples
    --------
    Simple sparkline with default line style:

    >>> sparkline = Sparkline(data=[10, 20, 15, 25, 30, 20])

    Bar-style sparkline:

    >>> sparkline = Sparkline(data=[1, 2, 3, 4, 5], style="bar")

    With current value display:

    >>> sparkline = Sparkline(data=[10, 20, 30], show_current=True)
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        data: list[Any] | None = None,
        width: int = 20,
        height: int = 1,
        style: Literal["line", "bar", "dot"] = "line",
        show_minmax: bool = False,
        show_current: bool = False,
        color: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        # Data
        self._raw_data = data or []
        self.values, self._labels = extract_values(self._raw_data)

        # Display properties
        self.width = width
        self.height = height
        self.style = style
        self.show_minmax = show_minmax
        self.show_current = show_current
        self.color = color

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
        """Update sparkline data.

        Parameters
        ----------
        data : list
            New data values
        """
        self._raw_data = data
        self.values, self._labels = extract_values(data)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the sparkline.

        Returns
        -------
        tuple of int
            (width, height) in characters
        """
        extra_width = 0
        if self.show_current and self.values:
            # Add space for current value display
            current = self.values[-1]
            extra_width = len(f" {current:.0f}") + 1

        return (self.width + extra_width, self.height)

    def _render_line_style(self, chart_width: int, chart_height: int) -> list[str]:
        """Render sparkline using braille line style.

        Parameters
        ----------
        chart_width : int
            Width in characters
        chart_height : int
            Height in characters

        Returns
        -------
        list of str
            Rendered lines
        """
        if not self.values or chart_width < 1:
            return [" " * chart_width] * chart_height

        # Create braille canvas
        canvas = BrailleCanvas(chart_width, chart_height)

        # Normalize data
        normalized, min_val, max_val = normalize_data(self.values)

        # Calculate x and y positions for each data point
        num_points = len(normalized)
        pixel_width = canvas.pixel_width
        pixel_height = canvas.pixel_height

        # Map data points to pixel coordinates
        points = []
        for i, val in enumerate(normalized):
            # X: distribute points across width
            x = (
                int((i / max(1, num_points - 1)) * (pixel_width - 1))
                if num_points > 1
                else pixel_width // 2
            )
            # Y: invert so higher values are at top (y=0)
            y = int((1 - val) * (pixel_height - 1))
            points.append((x, y))

        # Draw lines between consecutive points
        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            canvas.draw_line(x0, y0, x1, y1)

        return canvas.to_lines()

    def _render_bar_style(self, chart_width: int, chart_height: int) -> list[str]:
        """Render sparkline using vertical bar style.

        Parameters
        ----------
        chart_width : int
            Width in characters
        chart_height : int
            Height in characters

        Returns
        -------
        list of str
            Rendered lines
        """
        from wijjit.terminal.ansi import supports_unicode

        if not self.values or chart_width < 1:
            return [" " * chart_width] * chart_height

        use_unicode = supports_unicode()

        # Normalize data
        normalized, _, _ = normalize_data(self.values)

        # For single-row bar chart, use block characters
        if chart_height == 1:
            # Calculate how many values per character (may need to aggregate)
            values_per_char = max(1, len(normalized) // chart_width)
            chars = []

            for i in range(chart_width):
                # Get values for this character
                start_idx = i * values_per_char
                end_idx = min(start_idx + values_per_char, len(normalized))

                if start_idx < len(normalized):
                    # Average the values for this column
                    chunk_vals = normalized[start_idx:end_idx]
                    avg_val = sum(chunk_vals) / len(chunk_vals) if chunk_vals else 0
                    char = get_block_char(avg_val, "vertical", use_unicode)
                else:
                    char = " "

                chars.append(char)

            return ["".join(chars)]

        # Multi-row bar chart
        lines = []
        values_per_char = max(1, len(normalized) // chart_width)

        for row in range(chart_height):
            row_chars = []
            # Threshold for this row (top row = highest values)
            threshold = 1 - (row / chart_height)

            for col in range(chart_width):
                start_idx = col * values_per_char
                end_idx = min(start_idx + values_per_char, len(normalized))

                if start_idx < len(normalized):
                    chunk_vals = normalized[start_idx:end_idx]
                    avg_val = sum(chunk_vals) / len(chunk_vals) if chunk_vals else 0

                    if avg_val >= threshold:
                        row_chars.append("\u2588" if use_unicode else "#")
                    elif avg_val >= threshold - (1 / chart_height):
                        # Partial fill
                        partial = (
                            avg_val - (threshold - 1 / chart_height)
                        ) * chart_height
                        row_chars.append(
                            get_block_char(partial, "vertical", use_unicode)
                        )
                    else:
                        row_chars.append(" ")
                else:
                    row_chars.append(" ")

            lines.append("".join(row_chars))

        return lines

    def _render_dot_style(self, chart_width: int, chart_height: int) -> list[str]:
        """Render sparkline using dot style.

        Parameters
        ----------
        chart_width : int
            Width in characters
        chart_height : int
            Height in characters

        Returns
        -------
        list of str
            Rendered lines
        """
        if not self.values or chart_width < 1:
            return [" " * chart_width] * chart_height

        # Create braille canvas
        canvas = BrailleCanvas(chart_width, chart_height)

        # Normalize data
        normalized, _, _ = normalize_data(self.values)

        num_points = len(normalized)
        pixel_width = canvas.pixel_width
        pixel_height = canvas.pixel_height

        # Plot individual dots
        for i, val in enumerate(normalized):
            x = (
                int((i / max(1, num_points - 1)) * (pixel_width - 1))
                if num_points > 1
                else pixel_width // 2
            )
            y = int((1 - val) * (pixel_height - 1))
            canvas.set_pixel(x, y)

        return canvas.to_lines()

    def render_to(self, ctx: PaintContext) -> None:
        """Render the sparkline using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'sparkline': Base sparkline style
        - 'sparkline.min': Minimum value marker style
        - 'sparkline.max': Maximum value marker style
        - 'sparkline.current': Current value text style
        """
        from wijjit.terminal.cell import Cell

        # Resolve styles
        base_style = ctx.style_resolver.resolve_style(self, "sparkline")

        # Calculate chart dimensions
        chart_width = self.width
        if self.show_current and self.values:
            current_text = f" {self.values[-1]:.0f}"
            chart_width = max(1, self.width - len(current_text))

        chart_height = min(self.height, ctx.bounds.height)

        # Render based on style
        if self.style == "line":
            lines = self._render_line_style(chart_width, chart_height)
        elif self.style == "bar":
            lines = self._render_bar_style(chart_width, chart_height)
        else:  # dot
            lines = self._render_dot_style(chart_width, chart_height)

        # Get cell attributes
        cell_attrs = base_style.to_cell_attrs()

        # Write rendered lines to buffer
        for y, line in enumerate(lines):
            if y >= ctx.bounds.height:
                break
            for x, char in enumerate(line):
                if x >= ctx.bounds.width:
                    break
                ctx.buffer.set_cell(
                    ctx.bounds.x + x, ctx.bounds.y + y, Cell(char=char, **cell_attrs)
                )

        # Render current value if enabled
        if self.show_current and self.values:
            current_style = ctx.style_resolver.resolve_style(self, "sparkline.current")
            current_text = f" {self.values[-1]:.0f}"
            ctx.write_text(chart_width, 0, current_text, current_style)

        # Render min/max markers if enabled
        if self.show_minmax and self.values and len(self.values) > 1:
            min_val = min(self.values)
            max_val = max(self.values)
            min_idx = self.values.index(min_val)
            max_idx = self.values.index(max_val)

            # Calculate x positions for markers
            num_points = len(self.values)
            min_x = int((min_idx / max(1, num_points - 1)) * (chart_width - 1))
            max_x = int((max_idx / max(1, num_points - 1)) * (chart_width - 1))

            min_style = ctx.style_resolver.resolve_style(self, "sparkline.min")
            max_style = ctx.style_resolver.resolve_style(self, "sparkline.max")

            # Mark min with underscore at bottom
            if chart_height > 0:
                min_attrs = min_style.to_cell_attrs()
                ctx.buffer.set_cell(
                    ctx.bounds.x + min_x,
                    ctx.bounds.y + chart_height - 1,
                    Cell(char="_", **min_attrs),
                )

            # Mark max with caret at top
            max_attrs = max_style.to_cell_attrs()
            ctx.buffer.set_cell(
                ctx.bounds.x + max_x, ctx.bounds.y, Cell(char="^", **max_attrs)
            )
