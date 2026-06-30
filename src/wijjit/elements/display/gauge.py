"""Gauge element for value indicator visualization.

This module provides the Gauge element for displaying values as
linear or semi-circular gauges with threshold-based coloring.
"""

from __future__ import annotations

from math import cos, pi, sin
from typing import TYPE_CHECKING, Literal

from wijjit.elements.base import Element, ElementType
from wijjit.elements.display.chart_utils import (
    get_gradient_color,
    get_threshold_color,
)

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class Gauge(Element):
    """Gauge element for value indicator visualization.

    This element displays a value as a gauge with support for:
    - Linear (horizontal bar) style
    - Arc (semi-circular) style
    - Threshold-based coloring (green/yellow/red)
    - Gradient coloring
    - Optional tick marks and labels

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    value : float, optional
        Current value (default: 0)
    min_value : float, optional
        Minimum value (default: 0)
    max_value : float, optional
        Maximum value (default: 100)
    width : int, optional
        Display width in columns (default: 20)
    height : int, optional
        Display height in rows (default: 3 for linear, 5 for arc)
    style : str, optional
        Gauge style: "linear", "arc" (default: "linear")
    show_value : bool, optional
        Show current value text (default: True)
    show_minmax : bool, optional
        Show min/max labels (default: False)
    show_ticks : bool, optional
        Show tick marks (default: False)
    color : str, optional
        Color mode: "default", "gradient", "threshold" (default: "threshold")
    color_scale : str, optional
        Color scale for gradient mode (default: "green")
    thresholds : list of tuples, optional
        Custom thresholds: [(value_fraction, (r,g,b)), ...]
    label : str, optional
        Label text displayed above gauge (default: None)
    unit : str, optional
        Unit suffix for value display (default: "")

    Attributes
    ----------
    value : float
        Current value
    min_value : float
        Minimum value
    max_value : float
        Maximum value
    width : int
        Display width
    height : int
        Display height

    Examples
    --------
    Simple linear gauge:

    >>> gauge = Gauge(value=75, max_value=100)

    Arc gauge with label:

    >>> gauge = Gauge(value=60, style="arc", label="CPU Usage", unit="%")

    Custom thresholds:

    >>> gauge = Gauge(value=50, thresholds=[
    ...     (0.5, (0, 200, 0)),    # Green up to 50%
    ...     (0.8, (200, 200, 0)),  # Yellow 50-80%
    ...     (1.0, (200, 0, 0))     # Red above 80%
    ... ])
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        value: float = 0,
        min_value: float = 0,
        max_value: float = 100,
        width: int = 20,
        height: int | str | None = None,
        style: Literal["linear", "arc"] = "linear",
        show_value: bool = True,
        show_minmax: bool = False,
        show_ticks: bool = False,
        color: Literal["default", "gradient", "threshold"] = "threshold",
        color_scale: str = "green",
        thresholds: list[tuple[float, tuple[int, int, int]]] | None = None,
        label: str | None = None,
        unit: str = "",
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        # Value properties
        self.value = float(value)
        self.min_value = float(min_value)
        self.max_value = float(max_value)

        # Display properties
        self.width = width
        self.style = style
        self.show_value = show_value
        self.show_minmax = show_minmax
        self.show_ticks = show_ticks
        self.color = color
        self.color_scale = color_scale
        self.thresholds = thresholds
        self.label = label
        self.unit = unit

        # Auto-calculate height based on style unless an explicit integer is
        # given. The layout layer may pass a non-integer height spec such as
        # "auto" (synced from set_layout); treat anything but an int as
        # auto so get_intrinsic_size() always returns integer dimensions.
        if isinstance(height, int):
            self.height = height
        elif style == "arc":
            self.height = 5
        else:
            self.height = 3 if label else 2

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    def set_value(self, value: float) -> None:
        """Update gauge value.

        Parameters
        ----------
        value : float
            New value
        """
        self.value = float(value)

    def get_percentage(self) -> float:
        """Get current value as percentage.

        Returns
        -------
        float
            Percentage (0-100)
        """
        if self.max_value == self.min_value:
            return 0.0
        normalized = (self.value - self.min_value) / (self.max_value - self.min_value)
        return max(0.0, min(100.0, normalized * 100.0))

    def get_normalized(self) -> float:
        """Get current value normalized to 0-1 range.

        Returns
        -------
        float
            Normalized value (0-1)
        """
        return self.get_percentage() / 100.0

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the gauge.

        Returns
        -------
        tuple of int
            (width, height) in characters
        """
        return (self.width, self.height)

    def _get_gauge_color(self) -> tuple[int, int, int] | None:
        """Get the color for the gauge based on current value.

        Returns
        -------
        tuple of int or None
            RGB color tuple, or None for default
        """
        normalized = self.get_normalized()

        if self.color == "gradient":
            return get_gradient_color(normalized, 0.0, 1.0, self.color_scale)  # type: ignore
        elif self.color == "threshold":
            return get_threshold_color(normalized, self.thresholds)
        return None

    def _render_linear(self, ctx: PaintContext) -> None:
        """Render linear (horizontal bar) gauge style.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        """
        from wijjit.terminal.ansi import supports_unicode
        from wijjit.terminal.cell import Cell

        use_unicode = supports_unicode()

        # Resolve styles
        base_style = ctx.style_resolver.resolve_style(self, "gauge")
        fill_style = ctx.style_resolver.resolve_style(self, "gauge.fill")
        empty_style = ctx.style_resolver.resolve_style(self, "gauge.empty")
        label_style = ctx.style_resolver.resolve_style(self, "gauge.label")
        value_style = ctx.style_resolver.resolve_style(self, "gauge.value")

        current_y = 0

        # Render label if present
        if self.label:
            ctx.write_text(0, current_y, self.label, label_style)
            current_y += 1

        # Calculate bar dimensions
        bar_width = self.width
        if self.show_value:
            # Reserve space for value display
            value_text = f"{self.value:.0f}{self.unit}"
            bar_width = max(1, self.width - len(value_text) - 1)

        # Get normalized value and color
        normalized = self.get_normalized()
        gauge_color = self._get_gauge_color()

        # Calculate fill width
        fill_width = int(normalized * bar_width)

        # Get fill attributes with color
        fill_attrs = fill_style.to_cell_attrs()
        if gauge_color:
            fill_attrs = {**fill_attrs, "fg_color": gauge_color}

        empty_attrs = empty_style.to_cell_attrs()

        # Render bar
        fill_char = "\u2588" if use_unicode else "#"
        empty_char = "\u2591" if use_unicode else "-"

        for x in range(fill_width):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + current_y,
                Cell(char=fill_char, **fill_attrs),
            )

        for x in range(fill_width, bar_width):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + current_y,
                Cell(char=empty_char, **empty_attrs),
            )

        # Render value
        if self.show_value:
            value_text = f" {self.value:.0f}{self.unit}"
            ctx.write_text(bar_width, current_y, value_text, value_style)

        current_y += 1

        # Render ticks
        if self.show_ticks:
            tick_attrs = base_style.to_cell_attrs()
            for x in range(0, bar_width + 1, bar_width // 4 if bar_width >= 4 else 1):
                if x < bar_width:
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + current_y,
                        Cell(char="|", **tick_attrs),
                    )
            current_y += 1

        # Render min/max labels
        if self.show_minmax:
            min_text = f"{self.min_value:.0f}"
            max_text = f"{self.max_value:.0f}"

            ctx.write_text(0, current_y, min_text, label_style)
            max_x = max(0, bar_width - len(max_text))
            ctx.write_text(max_x, current_y, max_text, label_style)

    def _render_arc(self, ctx: PaintContext) -> None:
        """Render arc (semi-circular) gauge style.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        """
        from wijjit.terminal.ansi import supports_unicode
        from wijjit.terminal.cell import Cell

        use_unicode = supports_unicode()

        # Resolve styles
        # base_style = ctx.style_resolver.resolve_style(self, "gauge")
        fill_style = ctx.style_resolver.resolve_style(self, "gauge.fill")
        empty_style = ctx.style_resolver.resolve_style(self, "gauge.empty")
        label_style = ctx.style_resolver.resolve_style(self, "gauge.label")
        value_style = ctx.style_resolver.resolve_style(self, "gauge.value")

        current_y = 0

        # Render label if present
        if self.label:
            # Center label
            label_x = max(0, (self.width - len(self.label)) // 2)
            ctx.write_text(label_x, current_y, self.label, label_style)
            current_y += 1

        # Arc parameters
        arc_width = self.width
        arc_height = self.height - current_y - 1  # Leave room for value
        center_x = arc_width // 2
        center_y = arc_height

        # Get normalized value and color
        normalized = self.get_normalized()
        gauge_color = self._get_gauge_color()

        # Arc characters for different angles (simplified)
        arc_chars = {
            "full": "\u2588" if use_unicode else "#",
            "empty": "\u2591" if use_unicode else ".",
            "left_edge": "\u258c" if use_unicode else "[",
            "right_edge": "\u2590" if use_unicode else "]",
        }

        # Get fill attributes with color
        fill_attrs = fill_style.to_cell_attrs()
        if gauge_color:
            fill_attrs = {**fill_attrs, "fg_color": gauge_color}

        empty_attrs = empty_style.to_cell_attrs()
        # base_attrs = base_style.to_cell_attrs()

        # Draw arc using character approximation
        # The arc spans from pi (left) to 0 (right)
        num_segments = arc_width - 2

        for i in range(num_segments):
            # Angle goes from pi to 0
            progress = i / max(1, num_segments - 1)
            angle = pi * (1 - progress)

            # Calculate position (using ellipse)
            radius_x = (arc_width - 2) / 2
            radius_y = arc_height - 1
            x = int(center_x + radius_x * cos(angle))
            y = int(center_y - radius_y * sin(angle))

            # Clamp to bounds
            x = max(0, min(arc_width - 1, x))
            y = max(0, min(arc_height - 1, y))

            # Determine if this segment should be filled
            is_filled = progress <= normalized

            if is_filled:
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y + y,
                    Cell(char=arc_chars["full"], **fill_attrs),
                )
            else:
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y + y,
                    Cell(char=arc_chars["empty"], **empty_attrs),
                )

        # Render value at center bottom
        if self.show_value:
            value_text = f"{self.value:.0f}{self.unit}"
            value_x = max(0, (self.width - len(value_text)) // 2)
            value_y = self.height - 1
            ctx.write_text(value_x, value_y, value_text, value_style)

        # Render min/max at arc ends
        if self.show_minmax:
            min_text = f"{self.min_value:.0f}"
            max_text = f"{self.max_value:.0f}"

            min_y = current_y + arc_height - 1
            ctx.write_text(0, min_y, min_text, label_style)
            max_x = max(0, self.width - len(max_text))
            ctx.write_text(max_x, min_y, max_text, label_style)

    def render_to(self, ctx: PaintContext) -> None:
        """Render the gauge using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Theme styles:

        This element uses the following theme style classes:
        - ``gauge``: Base gauge style
        - ``gauge.fill``: Filled portion style
        - ``gauge.empty``: Empty portion style
        - ``gauge.label``: Label text style
        - ``gauge.value``: Value text style
        """
        if self.style == "arc":
            self._render_arc(ctx)
        else:
            self._render_linear(ctx)
