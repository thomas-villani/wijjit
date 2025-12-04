"""HTMLViewer element for displaying HTML content.

This module provides the HTMLViewer element, which renders HTML content
with scrolling support and optional embedded widgets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wijjit.elements.base import ElementType, ScrollableElement
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.rendering.html_adapter import html_string_to_cells
from wijjit.terminal.ansi import visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext
    from wijjit.styling.style import Style


class HTMLViewer(ScrollableElement):
    """Scrollable HTML content display element.

    HTMLViewer renders HTML content with support for:
    - Text formatting (<b>, <i>, <u>, <s>, etc.)
    - Inline styles (<style fg="color" bg="color">)
    - Theme-based class styling (<span class="text-danger">)
    - Scrolling with keyboard and mouse
    - Optional borders and titles

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    content : str, optional
        HTML content to display (default: "")
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 20)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)

    Attributes
    ----------
    content : str
        HTML content
    width : int
        Display width
    height : int
        Display height
    show_scrollbar : bool
        Whether scrollbar is visible
    border_style : str
        Border style
    title : str or None
        Border title
    scroll_manager : ScrollManager
        Manages scrolling of content
    rendered_lines : list of list of Cell
        Cached rendered content as cell rows

    Examples
    --------
    Create a simple HTML viewer:

    >>> viewer = HTMLViewer(
    ...     content="<b>Hello</b> <i>World</i>",
    ...     width=40,
    ...     height=10
    ... )

    With styled content:

    >>> viewer = HTMLViewer(
    ...     content='<text-danger>Error:</text-danger> Something went wrong',
    ...     border_style="rounded",
    ...     title="Messages"
    ... )
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        content: str = "",
        width: int = 60,
        height: int = 20,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = True

        # Content and display properties
        self.content = content
        self.width = width
        self.height = height
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title

        # Rendered content cache (list of cell lists per line)
        self.rendered_lines: list[list] = []

        # Cache key for re-rendering optimization
        self._render_cache_key: tuple[str, int] | None = None

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # Dynamic sizing flag
        self._dynamic_sizing: bool = False

    @property
    def supports_dynamic_sizing(self) -> bool:
        """Whether this HTML viewer supports dynamic sizing.

        Returns
        -------
        bool
            True if configured with fill sizing
        """
        return self._dynamic_sizing

    def set_bounds(self, bounds) -> None:
        """Set bounds and update dimensions/scroll.

        Parameters
        ----------
        bounds : Bounds
            New bounds for the element
        """
        super().set_bounds(bounds)

        if bounds:
            # Use bounds dimensions directly - width/height properties represent
            # the outer dimensions (including borders) for consistency
            new_width = bounds.width
            new_height = bounds.height

            if new_width != self.width or new_height != self.height:
                self.width = new_width
                self.height = new_height
                # Re-render content with new dimensions
                self._render_content()
                self.scroll_manager.update_content_size(len(self.rendered_lines))
                self.scroll_manager.update_viewport_size(self._get_content_height())

    def _get_content_height(self) -> int:
        """Calculate content area height accounting for borders.

        Returns
        -------
        int
            Content height in rows
        """
        if self.border_style != "none":
            return max(1, self.height - 2)
        return self.height

    def _get_content_width(self) -> int:
        """Calculate content area width accounting for borders and scrollbar.

        Returns
        -------
        int
            Content width in columns
        """
        content_width = self.width

        if self.border_style != "none":
            content_width -= 2

        if self.show_scrollbar:
            if not hasattr(self, "scroll_manager"):
                content_width -= 1
            elif self.scroll_manager.state.is_scrollable:
                content_width -= 1

        return max(1, content_width)

    def _render_content(self, style_resolver=None) -> None:
        """Render HTML content to cells.

        Parameters
        ----------
        style_resolver : StyleResolver, optional
            Style resolver for theme-based styling

        Notes
        -----
        Caches result to avoid re-rendering when content hasn't changed.
        """
        content_width = self._get_content_width()

        cache_key = (self.content, content_width)
        if self._render_cache_key == cache_key:
            return

        # Parse HTML to cells
        cells = html_string_to_cells(self.content, style_resolver=style_resolver)

        # Split into lines based on width and newlines
        self.rendered_lines = []
        current_line: list = []
        x = 0

        for cell in cells:
            if cell.char == "\n":
                self.rendered_lines.append(current_line)
                current_line = []
                x = 0
                continue

            if x >= content_width:
                # Wrap to next line
                self.rendered_lines.append(current_line)
                current_line = []
                x = 0

            current_line.append(cell)
            x += 1

        # Add final line if not empty
        if current_line:
            self.rendered_lines.append(current_line)

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [[]]

        self._render_cache_key = cache_key

    def set_content(self, content: str, style_resolver=None) -> None:
        """Update HTML content and re-render.

        Parameters
        ----------
        content : str
            New HTML content
        style_resolver : StyleResolver, optional
            Style resolver for theme-based styling
        """
        self.content = content
        self._render_cache_key = None  # Invalidate cache
        self._render_content(style_resolver)
        self.scroll_manager.update_content_size(len(self.rendered_lines))

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore
        """
        self.scroll_manager.scroll_to(position)

    @property
    def scroll_position(self) -> int:
        """Get the current scroll position.

        Returns
        -------
        int
            Current scroll offset (0-based)
        """
        return self.scroll_manager.state.scroll_position

    def can_scroll(self, direction: int) -> bool:
        """Check if the element can scroll in the given direction.

        Parameters
        ----------
        direction : int
            Scroll direction: negative for up, positive for down

        Returns
        -------
        bool
            True if scrolling is possible
        """
        if direction < 0:
            return self.scroll_manager.state.scroll_position > 0
        else:
            return self.scroll_manager.state.is_scrollable and (
                self.scroll_manager.state.scroll_position
                < self.scroll_manager.state.max_scroll
            )

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
        if not self.rendered_lines:
            return False

        old_pos = self.scroll_manager.state.scroll_position

        if key == Keys.UP:
            self.scroll_manager.scroll_by(-1)
        elif key == Keys.DOWN:
            self.scroll_manager.scroll_by(1)
        elif key == Keys.HOME:
            self.scroll_manager.scroll_to(0)
        elif key == Keys.END:
            self.scroll_manager.scroll_to_bottom()
        elif key == Keys.PAGE_UP:
            self.scroll_manager.page_up()
        elif key == Keys.PAGE_DOWN:
            self.scroll_manager.page_down()
        else:
            return False

        if old_pos != self.scroll_manager.state.scroll_position:
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True
        return False

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input for scrolling.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        old_pos = self.scroll_manager.state.scroll_position

        if event.button == MouseButton.SCROLL_UP:
            self.scroll_manager.scroll_by(-1)
        elif event.button == MouseButton.SCROLL_DOWN:
            self.scroll_manager.scroll_by(1)
        else:
            return False

        if old_pos != self.scroll_manager.state.scroll_position:
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True
        return False

    def render_to(self, ctx: PaintContext) -> None:
        """Render HTML viewer using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds
        """
        # Re-render content with style resolver if not cached
        if self._render_cache_key is None or self._render_cache_key[0] != self.content:
            self._render_content(ctx.style_resolver)
            self.scroll_manager.update_content_size(len(self.rendered_lines))

        # Resolve border style
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(
                self, "htmlview.border:focus"
            )
        else:
            border_style = ctx.style_resolver.resolve_style(self, "htmlview.border")

        content_height = self._get_content_height()
        content_width = self._get_content_width()

        if self.border_style != "none":
            self._render_with_border(ctx, border_style, content_height, content_width)
        else:
            self._render_content_area(ctx, 0, content_height, content_width)

    def _render_with_border(
        self,
        ctx: PaintContext,
        border_style: Style,
        content_height: int,
        content_width: int,
    ) -> None:
        """Render HTML viewer with border.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_style : Style
            Border style from theme
        content_height : int
            Content area height
        content_width : int
            Content area width
        """
        from wijjit.layout.frames import BORDER_CHARS, BorderStyle
        from wijjit.terminal.cell import get_pooled_cell

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS[style]
        border_attrs = border_style.to_cell_attrs()

        # Calculate total width
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        scrollbar_width = 1 if needs_scrollbar else 0
        total_width = content_width + scrollbar_width + 2

        # Render top border with optional title
        h_cell = get_pooled_cell(char=chars["h"], **border_attrs)

        if self.title:
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            border_width = total_width - 2

            if title_len < border_width:
                remaining = border_width - title_len
                left_len = remaining // 2
                right_len = remaining - left_len

                top_cells = [get_pooled_cell(char=chars["tl"], **border_attrs)]
                top_cells.extend([h_cell] * left_len)
                top_cells.extend(
                    [get_pooled_cell(char=c, **border_attrs) for c in title_text]
                )
                top_cells.extend([h_cell] * right_len)
                top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
                ctx.buffer.set_cells_horizontal(ctx.bounds.x, ctx.bounds.y, top_cells)
            else:
                top_cells = [get_pooled_cell(char=chars["tl"], **border_attrs)]
                top_cells.extend([h_cell] * border_width)
                top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
                ctx.buffer.set_cells_horizontal(ctx.bounds.x, ctx.bounds.y, top_cells)
        else:
            top_cells = [get_pooled_cell(char=chars["tl"], **border_attrs)]
            top_cells.extend([h_cell] * (total_width - 2))
            top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
            ctx.buffer.set_cells_horizontal(ctx.bounds.x, ctx.bounds.y, top_cells)

        # Render content area
        content_ctx = ctx.sub_context(
            1, 1, content_width + scrollbar_width, content_height
        )
        self._render_content_area(content_ctx, 0, content_height, content_width)

        # Render side borders
        v_cell = get_pooled_cell(char=chars["v"], **border_attrs)
        v_cells = [v_cell] * content_height
        ctx.buffer.set_cells_vertical(ctx.bounds.x, ctx.bounds.y + 1, v_cells)
        ctx.buffer.set_cells_vertical(
            ctx.bounds.x + total_width - 1, ctx.bounds.y + 1, v_cells
        )

        # Render bottom border
        bottom_y = content_height + 1
        bottom_cells = [get_pooled_cell(char=chars["bl"], **border_attrs)]
        bottom_cells.extend([h_cell] * (total_width - 2))
        bottom_cells.append(get_pooled_cell(char=chars["br"], **border_attrs))
        ctx.buffer.set_cells_horizontal(
            ctx.bounds.x, ctx.bounds.y + bottom_y, bottom_cells
        )

    def _render_content_area(
        self,
        ctx: PaintContext,
        start_y: int,
        content_height: int,
        content_width: int,
    ) -> None:
        """Render HTML content cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        start_y : int
            Starting Y position
        content_height : int
            Content area height
        content_width : int
            Content area width
        """
        from wijjit.terminal.cell import get_pooled_cell

        visible_start, visible_end = self.scroll_manager.get_visible_range()

        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )

        scrollbar_chars = []
        scrollbar_attrs = None
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, content_height
            )
            # Resolve scrollbar style once, outside the loop
            if self.focused:
                scrollbar_style = ctx.style_resolver.resolve_style(
                    self, "htmlview.border:focus"
                )
            else:
                scrollbar_style = ctx.style_resolver.resolve_style(
                    self, "htmlview.border"
                )
            scrollbar_attrs = scrollbar_style.to_cell_attrs()

        current_y = start_y
        line_idx = visible_start

        while current_y < start_y + content_height and line_idx < visible_end:
            if line_idx >= len(self.rendered_lines):
                # Empty line
                space_cell = get_pooled_cell(char=" ")
                empty_line = [space_cell] * content_width
                ctx.buffer.set_cells_horizontal(
                    ctx.bounds.x, ctx.bounds.y + current_y, empty_line
                )
            else:
                line_cells = self.rendered_lines[line_idx]

                # Clip or pad to content width
                if len(line_cells) < content_width:
                    pad_cell = get_pooled_cell(char=" ")
                    line_cells = line_cells + [pad_cell] * (
                        content_width - len(line_cells)
                    )
                else:
                    line_cells = line_cells[:content_width]

                ctx.buffer.set_cells_horizontal(
                    ctx.bounds.x, ctx.bounds.y + current_y, line_cells
                )

            # Add scrollbar
            if needs_scrollbar and scrollbar_attrs:
                scrollbar_idx = current_y - start_y
                if scrollbar_idx < len(scrollbar_chars):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + content_width,
                        ctx.bounds.y + current_y,
                        get_pooled_cell(
                            char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs
                        ),
                    )

            current_y += 1
            line_idx += 1

        # Fill remaining rows
        if current_y < start_y + content_height:
            space_cell = get_pooled_cell(char=" ")
            empty_line = [space_cell] * content_width

            while current_y < start_y + content_height:
                ctx.buffer.set_cells_horizontal(
                    ctx.bounds.x, ctx.bounds.y + current_y, empty_line
                )

                if needs_scrollbar and scrollbar_attrs:
                    scrollbar_idx = current_y - start_y
                    if scrollbar_idx < len(scrollbar_chars):
                        ctx.buffer.set_cell(
                            ctx.bounds.x + content_width,
                            ctx.bounds.y + current_y,
                            get_pooled_cell(
                                char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs
                            ),
                        )

                current_y += 1

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the HTML viewer.

        Returns
        -------
        tuple[int, int]
            (width, height) including borders
        """
        total_width = self.width
        total_height = self.height

        if self.border_style != "none":
            total_width += 2
            total_height += 2

        return (total_width, total_height)
