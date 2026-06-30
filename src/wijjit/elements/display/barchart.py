"""BarChart element for horizontal bar chart visualization.

This module provides the BarChart element for displaying data as
horizontal bars with optional labels, values, and color gradients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import ElementType, ScrollableElement, invoke_callback
from wijjit.elements.display.chart_utils import (
    extract_values,
    get_gradient_color,
    get_threshold_color,
    normalize_data,
)
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext
    from wijjit.terminal.input import Key
    from wijjit.terminal.mouse import MouseEvent


class BarChart(ScrollableElement):
    """BarChart element for horizontal bar visualization.

    This element displays data as horizontal bars with support for:
    - Labels on the left side
    - Values on the right side
    - Single color, gradient, or threshold-based coloring
    - Scrolling for large datasets
    - Mouse and keyboard interaction

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    data : list, optional
        Data as numbers, tuples (label, value), or dicts (default: [])
    width : int, optional
        Display width in columns (default: 40)
    height : int, optional
        Display height in rows (default: 10)
    bar_height : int, optional
        Height of each bar in rows (default: 1)
    show_labels : bool, optional
        Show labels on left side (default: True)
    show_values : bool, optional
        Show values on right side (default: True)
    label_width : int, optional
        Width reserved for labels (default: auto)
    value_width : int, optional
        Width reserved for values (default: 6)
    color : str, optional
        Color mode: "default", "gradient", "threshold" (default: "default")
    color_scale : str, optional
        Color scale for gradient mode (default: "green")
    show_scrollbar : bool, optional
        Show scrollbar when content overflows (default: True)
    show_border : bool, optional
        Show border around chart (default: False)

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
    bar_height : int
        Height per bar
    scroll_manager : ScrollManager
        Manages scrolling

    Examples
    --------
    Simple bar chart:

    >>> barchart = BarChart(data=[10, 20, 30, 40])

    With labels:

    >>> barchart = BarChart(data=[
    ...     {"label": "Sales", "value": 100},
    ...     {"label": "Revenue", "value": 150},
    ... ])

    Gradient coloring:

    >>> barchart = BarChart(data=[10, 50, 90], color="gradient")
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        data: list[Any] | None = None,
        width: int = 40,
        height: int = 10,
        bar_height: int = 1,
        show_labels: bool = True,
        show_values: bool = True,
        label_width: int | None = None,
        value_width: int = 6,
        color: Literal["default", "gradient", "threshold"] = "default",
        color_scale: str = "green",
        show_scrollbar: bool = True,
        show_border: bool = False,
        tab_index: int | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # For keyboard scrolling

        # Data
        self._raw_data = data or []
        self.values, self.labels = extract_values(self._raw_data)

        # Display properties
        self.width = width
        self.height = height
        self.bar_height = bar_height
        self.show_labels = show_labels
        self.show_values = show_values
        self.value_width = value_width
        self.color = color
        self.color_scale = color_scale
        self.show_scrollbar = show_scrollbar
        self.show_border = show_border

        # Auto-calculate label width if not specified
        if label_width is None and show_labels and self.labels:
            self.label_width = min(15, max(len(label) for label in self.labels) + 1)
        else:
            self.label_width = label_width or 0

        # Calculate content height (total rows needed for all bars)
        content_height = len(self.values) * self.bar_height
        viewport_height = self.height - (2 if show_border else 0)

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=content_height,
            viewport_size=max(1, viewport_height),
        )

        # Hover tracking for detail overlay
        self._hovered_bar: int | None = None

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

        # Recalculate label width
        if self.show_labels and self.labels:
            self.label_width = min(15, max(len(label) for label in self.labels) + 1)

        # Update scroll manager
        content_height = len(self.values) * self.bar_height
        self.scroll_manager.update_content_size(content_height)

    @property
    def scroll_position(self) -> int:
        """Get the current scroll position.

        Returns
        -------
        int
            Current scroll offset
        """
        return self.scroll_manager.state.scroll_position

    def can_scroll(self, direction: int) -> bool:
        """Check if scrolling is possible in the given direction.

        Parameters
        ----------
        direction : int
            Negative for up, positive for down

        Returns
        -------
        bool
            True if scrolling is possible
        """
        if direction < 0:
            return self.scroll_manager.state.scroll_position > 0
        else:
            return (
                self.scroll_manager.state.is_scrollable
                and self.scroll_manager.state.scroll_position
                < self.scroll_manager.state.max_scroll
            )

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the chart.

        Returns
        -------
        tuple of int
            (width, height) in characters
        """
        return (self.width, self.height)

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for scrolling.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        from wijjit.terminal.input import Keys

        if key == Keys.UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-self.bar_height)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        elif key == Keys.DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(self.bar_height)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        elif key == Keys.PAGE_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_up()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        elif key == Keys.PAGE_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_down()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        elif key == Keys.HOME:
            self.scroll_manager.scroll_to(0)
            if self.on_scroll:
                invoke_callback(
                    self.on_scroll, self.scroll_manager.state.scroll_position
                )
            return True

        elif key == Keys.END:
            self.scroll_manager.scroll_to_bottom()
            if self.on_scroll:
                invoke_callback(
                    self.on_scroll, self.scroll_manager.state.scroll_position
                )
            return True

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse events.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        from wijjit.terminal.mouse import MouseButton

        if event.button == MouseButton.SCROLL_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-self.bar_height)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(self.bar_height)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        return False

    def _get_bar_color(
        self, value: float, normalized: float
    ) -> tuple[int, int, int] | None:
        """Get the color for a bar based on its value.

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
        """Render the bar chart using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Theme styles:

        This element uses the following theme style classes:
        - ``barchart``: Base bar chart style
        - ``barchart:focus``: When chart has focus
        - ``barchart.label``: Label text style
        - ``barchart.value``: Value text style
        - ``barchart.bar``: Bar fill style
        - ``barchart.bar.empty``: Empty bar portion style
        - ``barchart.border``: Border style
        """
        from wijjit.terminal.ansi import clip_to_width, supports_unicode
        from wijjit.terminal.cell import Cell

        if not self.values:
            empty_style = ctx.style_resolver.resolve_style(self, "barchart")
            ctx.write_text(0, 0, "No data", empty_style)
            return

        # Resolve styles
        base_style = ctx.style_resolver.resolve_style(self, "barchart")
        label_style = ctx.style_resolver.resolve_style(self, "barchart.label")
        value_style = ctx.style_resolver.resolve_style(self, "barchart.value")
        bar_style = ctx.style_resolver.resolve_style(self, "barchart.bar")
        empty_style = ctx.style_resolver.resolve_style(self, "barchart.bar.empty")

        use_unicode = supports_unicode()

        # Calculate dimensions
        border_offset = 1 if self.show_border else 0
        viewport_height = self.height - (2 * border_offset)
        viewport_width = self.width - (2 * border_offset)

        # Calculate bar area width
        bar_start_x = border_offset
        if self.show_labels:
            bar_start_x += self.label_width

        bar_end_x = viewport_width + border_offset
        if self.show_values:
            bar_end_x -= self.value_width

        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        if needs_scrollbar:
            bar_end_x -= 1

        bar_width = max(1, bar_end_x - bar_start_x)

        # Normalize data
        normalized, min_val, max_val = normalize_data(self.values)

        # Get visible range
        scroll_offset = self.scroll_manager.state.scroll_position
        first_visible_bar = scroll_offset // self.bar_height
        last_visible_bar = (scroll_offset + viewport_height) // self.bar_height + 1

        # Render border if enabled
        if self.show_border:
            border_style = ctx.style_resolver.resolve_style(self, "barchart.border")
            ctx.draw_border(0, 0, self.width, self.height, border_style)

        # Render bars
        current_y = border_offset
        for bar_idx in range(
            first_visible_bar, min(last_visible_bar, len(self.values))
        ):
            if current_y >= viewport_height + border_offset:
                break

            value = self.values[bar_idx]
            norm_val = normalized[bar_idx]
            label = self.labels[bar_idx] if bar_idx < len(self.labels) else ""

            # Calculate bar fill width
            fill_width = int(norm_val * bar_width)
            empty_width = bar_width - fill_width

            # Get bar color
            bar_color = self._get_bar_color(value, norm_val)

            # Render label
            if self.show_labels:
                label_text = clip_to_width(label, self.label_width - 1, ellipsis=".")
                label_text = label_text.ljust(self.label_width - 1) + " "
                ctx.write_text(border_offset, current_y, label_text, label_style)

            # Render bar
            fill_char = "\u2588" if use_unicode else "#"
            empty_char = "\u2591" if use_unicode else "-"

            bar_attrs = bar_style.to_cell_attrs()
            empty_attrs = empty_style.to_cell_attrs()

            # Apply custom color if available
            if bar_color:
                bar_attrs = {**bar_attrs, "fg_color": bar_color}

            # Draw filled portion
            for x in range(fill_width):
                ctx.buffer.set_cell(
                    ctx.bounds.x + bar_start_x + x,
                    ctx.bounds.y + current_y,
                    Cell(char=fill_char, **bar_attrs),
                )

            # Draw empty portion
            for x in range(empty_width):
                ctx.buffer.set_cell(
                    ctx.bounds.x + bar_start_x + fill_width + x,
                    ctx.bounds.y + current_y,
                    Cell(char=empty_char, **empty_attrs),
                )

            # Render value
            if self.show_values:
                value_text = f"{value:.0f}".rjust(self.value_width - 1) + " "
                value_x = bar_end_x
                ctx.write_text(value_x, current_y, value_text, value_style)

            current_y += self.bar_height

        # Fill remaining rows with empty space
        while current_y < viewport_height + border_offset:
            for x in range(viewport_width):
                ctx.buffer.set_cell(
                    ctx.bounds.x + border_offset + x,
                    ctx.bounds.y + current_y,
                    Cell(char=" ", **base_style.to_cell_attrs()),
                )
            current_y += 1

        # Render scrollbar
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, viewport_height
            )
            scrollbar_x = self.width - 1 - border_offset

            for y, char in enumerate(scrollbar_chars):
                if y + border_offset < self.height - border_offset:
                    ctx.buffer.set_cell(
                        ctx.bounds.x + scrollbar_x,
                        ctx.bounds.y + y + border_offset,
                        Cell(char=char, **base_style.to_cell_attrs()),
                    )
