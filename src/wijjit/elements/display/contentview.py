"""Unified content display element supporting multiple content types.

This module provides the ContentView element which can render content in
multiple formats: plain text, ANSI, HTML, Markdown, Rich markup, and code
with syntax highlighting. It replaces the separate MarkdownView, HTMLViewer,
and CodeBlock elements with a unified, flexible component.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from wijjit.elements.base import ElementType, ScrollableElement
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.rendering import PaintContext
from wijjit.styling.style import Style
from wijjit.terminal.ansi import visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent

if TYPE_CHECKING:
    from wijjit.styling.resolver import StyleResolver


class ContentType(Enum):
    """Content type enumeration for ContentView rendering."""

    PLAIN = auto()
    TEXT = auto()  # Alias for PLAIN
    ANSI = auto()
    HTML = auto()
    MARKDOWN = auto()
    RICH = auto()
    CODE = auto()


# String to enum mapping for template convenience
_CONTENT_TYPE_MAP = {
    "plain": ContentType.PLAIN,
    "text": ContentType.TEXT,
    "ansi": ContentType.ANSI,
    "html": ContentType.HTML,
    "markdown": ContentType.MARKDOWN,
    "rich": ContentType.RICH,
    "code": ContentType.CODE,
}


class ContentView(ScrollableElement):
    """Unified content display element supporting multiple content types.

    This element renders content in various formats with support for scrolling,
    borders, and keyboard/mouse interaction. It provides a single component
    that can display plain text, ANSI-formatted text, HTML, Markdown, Rich
    markup, or syntax-highlighted code.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    content : str
        Content to display (default: "")
    content_type : str or ContentType
        Type of content: "plain", "text", "ansi", "html", "markdown",
        "rich", or "code" (default: "plain")
    language : str
        Programming language for code syntax highlighting (default: "python")
    theme : str
        Syntax highlighting theme (default: "monokai")
    show_line_numbers : bool
        Show line numbers for code (default: False)
    line_number_start : int
        Starting line number (default: 1)
    width : int
        Display width in columns (default: 60)
    height : int
        Display height in rows (default: 20)
    show_scrollbar : bool
        Whether to show vertical scrollbar (default: True)
    border_style : str
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)

    Attributes
    ----------
    content : str
        Content to display
    content_type : ContentType
        Content type enumeration value
    language : str
        Programming language for code highlighting
    theme : str
        Syntax highlighting theme
    show_line_numbers : bool
        Whether line numbers are shown (code only)
    line_number_start : int
        Starting line number (code only)
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
    rendered_lines : list of str
        Cached rendered content lines (for ANSI-based content types)
    rendered_cells : list of list of Cell
        Cached rendered cells (for cell-based content types like HTML)
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        content: str = "",
        content_type: str | ContentType = "plain",
        language: str = "python",
        theme: str = "monokai",
        show_line_numbers: bool = False,
        line_number_start: int = 1,
        width: int = 60,
        height: int = 20,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and type
        self.content = content
        self._content_type = self._resolve_content_type(content_type)

        # Code-specific options
        self.language = language
        self.theme = theme
        self.show_line_numbers = show_line_numbers
        self.line_number_start = line_number_start

        # Display properties
        self.width = width
        self.height = height
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title

        # Rendered content caches
        self.rendered_lines: list[str] = []
        self.rendered_cells: list[list] = []  # For HTML content type
        self._uses_cells = False  # Flag to indicate cell-based rendering

        # Cache key for avoiding re-renders
        self._render_cache_key: tuple | None = None

        # Store style resolver for HTML rendering (set during render_to)
        self._style_resolver: StyleResolver | None = None

        # Render initial content
        self._render_content()

        # Scroll management
        content_count = (
            len(self.rendered_cells) if self._uses_cells else len(self.rendered_lines)
        )
        self.scroll_manager = ScrollManager(
            content_size=content_count,
            viewport_size=self._get_content_height(),
        )

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # Dynamic sizing flag (set by template tag)
        self._dynamic_sizing: bool = False

        # Store style resolver for HTML rendering
        self._style_resolver: StyleResolver | None = None

    @property
    def content_type(self) -> ContentType:
        """Get the current content type.

        Returns
        -------
        ContentType
            Current content type enumeration value
        """
        return self._content_type

    @content_type.setter
    def content_type(self, value: str | ContentType) -> None:
        """Set the content type.

        Parameters
        ----------
        value : str or ContentType
            New content type
        """
        new_type = self._resolve_content_type(value)
        if new_type != self._content_type:
            self._content_type = new_type
            self._render_content()
            content_count = (
                len(self.rendered_cells)
                if self._uses_cells
                else len(self.rendered_lines)
            )
            self.scroll_manager.update_content_size(content_count)

    def _resolve_content_type(self, value: str | ContentType) -> ContentType:
        """Resolve content type from string or enum.

        Parameters
        ----------
        value : str or ContentType
            Content type specification

        Returns
        -------
        ContentType
            Resolved content type enum

        Raises
        ------
        ValueError
            If string value is not a valid content type
        """
        if isinstance(value, ContentType):
            return value

        value_lower = value.lower()
        if value_lower in _CONTENT_TYPE_MAP:
            return _CONTENT_TYPE_MAP[value_lower]

        raise ValueError(
            f"Invalid content_type: {value}. "
            f"Valid types: {', '.join(_CONTENT_TYPE_MAP.keys())}"
        )

    @property
    def supports_dynamic_sizing(self) -> bool:
        """Whether this content view supports dynamic sizing.

        Returns
        -------
        bool
            True if configured with fill sizing, False otherwise
        """
        return self._dynamic_sizing

    def set_bounds(self, bounds) -> None:
        """Set bounds and resize element to fit.

        Parameters
        ----------
        bounds : Bounds
            New bounds for the element
        """
        super().set_bounds(bounds)

        # Always resize element to fit allocated bounds
        # This handles both dynamic (fill) sizing and fixed sizing from template
        if bounds:
            new_width = bounds.width
            new_height = bounds.height

            # Account for borders - bounds are OUTER size, we store INNER size
            if self.border_style != "none":
                new_width = max(3, new_width - 2)
                new_height = max(3, new_height - 2)

            # Update dimensions if changed
            if new_width != self.width or new_height != self.height:
                self.width = new_width
                self.height = new_height

                # Re-render content with new dimensions
                self._render_content()

                # Update scroll manager with new viewport size
                content_count = (
                    len(self.rendered_cells)
                    if self._uses_cells
                    else len(self.rendered_lines)
                )
                self.scroll_manager.update_content_size(content_count)
                self.scroll_manager.update_viewport_size(self._get_content_height())

    def _get_content_height(self) -> int:
        """Calculate content area height.

        Note: self.height is already the inner content height (not including borders).

        Returns
        -------
        int
            Content height in rows
        """
        return self.height

    def _get_content_width(self) -> int:
        """Calculate content area width accounting for scrollbar.

        Note: self.width is already the inner content width (not including borders).
        This method only subtracts space for the scrollbar if needed.

        Returns
        -------
        int
            Content width in columns
        """
        content_width = self.width

        # Account for scrollbar (borders are NOT subtracted here since
        # self.width is already the inner width)
        if self.show_scrollbar:
            if not hasattr(self, "scroll_manager"):
                content_width -= 1
            elif self.scroll_manager.state.is_scrollable:
                content_width -= 1

        return max(1, content_width)

    def _render_content(self) -> None:
        """Render content based on content_type.

        Updates the rendered_lines or rendered_cells cache.
        """
        from wijjit.rendering.content_renderers import (
            render_ansi_to_lines,
            render_code_to_lines,
            render_html_to_cells,
            render_markdown_to_lines,
            render_plain_to_lines,
            render_rich_to_lines,
        )

        content_width = self._get_content_width()

        # Build cache key based on content type and relevant parameters
        if self._content_type == ContentType.CODE:
            cache_key = (
                self.content,
                content_width,
                self._content_type,
                self.language,
                self.theme,
                self.show_line_numbers,
                self.line_number_start,
            )
        else:
            cache_key = (self.content, content_width, self._content_type)

        if self._render_cache_key == cache_key:
            return

        # Render based on content type
        self._uses_cells = False

        if self._content_type in (ContentType.PLAIN, ContentType.TEXT):
            self.rendered_lines = render_plain_to_lines(self.content, content_width)

        elif self._content_type == ContentType.ANSI:
            self.rendered_lines = render_ansi_to_lines(self.content, content_width)

        elif self._content_type == ContentType.HTML:
            self._uses_cells = True
            self.rendered_cells = render_html_to_cells(
                self.content, content_width, self._style_resolver
            )

        elif self._content_type == ContentType.MARKDOWN:
            self.rendered_lines = render_markdown_to_lines(self.content, content_width)

        elif self._content_type == ContentType.RICH:
            self.rendered_lines = render_rich_to_lines(self.content, content_width)

        elif self._content_type == ContentType.CODE:
            self.rendered_lines = render_code_to_lines(
                self.content,
                content_width,
                language=self.language,
                theme=self.theme,
                show_line_numbers=self.show_line_numbers,
                line_number_start=self.line_number_start,
            )

        self._render_cache_key = cache_key

    def set_content(
        self, content: str, content_type: str | ContentType | None = None
    ) -> None:
        """Update content and optionally content type.

        Parameters
        ----------
        content : str
            New content
        content_type : str or ContentType, optional
            New content type (if None, keeps current type)
        """
        self.content = content
        if content_type is not None:
            self._content_type = self._resolve_content_type(content_type)

        self._render_content()

        content_count = (
            len(self.rendered_cells) if self._uses_cells else len(self.rendered_lines)
        )
        self.scroll_manager.update_content_size(content_count)

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
            True if scrolling in the given direction is possible
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
        content_count = (
            len(self.rendered_cells) if self._uses_cells else len(self.rendered_lines)
        )
        if not content_count:
            return False

        # Up arrow - scroll up one row
        if key == Keys.UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Down arrow - scroll down one row
        elif key == Keys.DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Home - jump to top
        elif key == Keys.HOME:
            self.scroll_manager.scroll_to(0)
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # End - jump to bottom
        elif key == Keys.END:
            self.scroll_manager.scroll_to_bottom()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # Page Up
        elif key == Keys.PAGE_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_up()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Page Down
        elif key == Keys.PAGE_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.page_down()
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
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
        # Handle scroll wheel
        if event.button == MouseButton.SCROLL_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        return False

    def render_to(self, ctx: PaintContext) -> None:
        """Render content view using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for content views,
        supporting all content types with their respective formatting.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'contentview': Base style (for background/fallback)
        - 'contentview:focus': When content view has focus
        - 'contentview.border': For border characters
        - 'contentview.border:focus': For border when focused
        """
        # Store style resolver for HTML rendering
        self._style_resolver = ctx.style_resolver

        # Re-render if needed (width may have changed)
        self._render_content()

        # Resolve border style based on focus
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(
                self, "contentview.border:focus"
            )
        else:
            border_style = ctx.style_resolver.resolve_style(self, "contentview.border")

        content_height = self._get_content_height()
        content_width = self._get_content_width()

        # Render borders if needed
        if self.border_style != "none":
            self._render_to_with_border(
                ctx, border_style, content_height, content_width
            )
        else:
            # No borders - render content directly
            self._render_to_content(ctx, 0, content_height, content_width)

    def _render_to_with_border(
        self,
        ctx: PaintContext,
        border_style: Style,
        content_height: int,
        content_width: int,
    ) -> None:
        """Render content view with border using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_style : Style
            Border style resolved from theme
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
        if self.title:
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            border_width = total_width - 2

            if title_len < border_width:
                remaining = border_width - title_len
                left_len = remaining // 2
                right_len = remaining - left_len

                h_cell = get_pooled_cell(char=chars["h"], **border_attrs)
                top_cells = []
                top_cells.append(get_pooled_cell(char=chars["tl"], **border_attrs))
                top_cells.extend([h_cell] * left_len)
                top_cells.extend(
                    [get_pooled_cell(char=c, **border_attrs) for c in title_text]
                )
                top_cells.extend([h_cell] * right_len)
                top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
                ctx.buffer.set_cells_horizontal(ctx.bounds.x, ctx.bounds.y, top_cells)
            else:
                h_cell = get_pooled_cell(char=chars["h"], **border_attrs)
                top_cells = [get_pooled_cell(char=chars["tl"], **border_attrs)]
                top_cells.extend([h_cell] * border_width)
                top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
                ctx.buffer.set_cells_horizontal(ctx.bounds.x, ctx.bounds.y, top_cells)
        else:
            h_cell = get_pooled_cell(char=chars["h"], **border_attrs)
            top_cells = [get_pooled_cell(char=chars["tl"], **border_attrs)]
            top_cells.extend([h_cell] * (total_width - 2))
            top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
            ctx.buffer.set_cells_horizontal(ctx.bounds.x, ctx.bounds.y, top_cells)

        # Render content area
        content_ctx = ctx.sub_context(
            1, 1, content_width + scrollbar_width, content_height
        )
        self._render_to_content(content_ctx, 0, content_height, content_width)

        # Render side borders
        v_cell = get_pooled_cell(char=chars["v"], **border_attrs)
        v_cells = [v_cell] * content_height
        ctx.buffer.set_cells_vertical(ctx.bounds.x, ctx.bounds.y + 1, v_cells)
        ctx.buffer.set_cells_vertical(
            ctx.bounds.x + total_width - 1, ctx.bounds.y + 1, v_cells
        )

        # Render bottom border
        bottom_y = content_height + 1
        h_cell = get_pooled_cell(char=chars["h"], **border_attrs)
        bottom_cells = [get_pooled_cell(char=chars["bl"], **border_attrs)]
        bottom_cells.extend([h_cell] * (total_width - 2))
        bottom_cells.append(get_pooled_cell(char=chars["br"], **border_attrs))
        ctx.buffer.set_cells_horizontal(
            ctx.bounds.x, ctx.bounds.y + bottom_y, bottom_cells
        )

    def _render_to_content(
        self,
        ctx: PaintContext,
        start_y: int,
        content_height: int,
        content_width: int,
    ) -> None:
        """Render content using cells.

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
        from wijjit.rendering.ansi_adapter import ansi_string_to_cells
        from wijjit.terminal.cell import Cell, get_pooled_cell

        # Get visible range
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        # Determine if scrollbar is needed
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )

        # Generate scrollbar if needed
        scrollbar_chars = []
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, content_height
            )

        # Render content based on type
        current_y = start_y
        rendered_idx = visible_start

        while current_y < start_y + content_height and rendered_idx < visible_end:
            if self._uses_cells:
                # HTML content - use pre-rendered cells
                if rendered_idx >= len(self.rendered_cells):
                    space_cell = get_pooled_cell(char=" ")
                    empty_line = [space_cell] * content_width
                    ctx.buffer.set_cells_horizontal(
                        ctx.bounds.x, ctx.bounds.y + current_y, empty_line
                    )
                else:
                    cells = self.rendered_cells[rendered_idx]
                    line_cells = cells[:content_width]

                    # Pad remaining width
                    if len(line_cells) < content_width:
                        pad_cell = get_pooled_cell(char=" ")
                        line_cells = list(line_cells)
                        line_cells.extend(
                            [pad_cell] * (content_width - len(line_cells))
                        )

                    ctx.buffer.set_cells_horizontal(
                        ctx.bounds.x, ctx.bounds.y + current_y, line_cells
                    )
            else:
                # ANSI-based content types
                if rendered_idx >= len(self.rendered_lines):
                    space_cell = get_pooled_cell(char=" ")
                    empty_line = [space_cell] * content_width
                    ctx.buffer.set_cells_horizontal(
                        ctx.bounds.x, ctx.bounds.y + current_y, empty_line
                    )
                else:
                    ansi_line = self.rendered_lines[rendered_idx]
                    cells = ansi_string_to_cells(ansi_line)

                    line_cells = cells[:content_width]

                    # Pad remaining width
                    if len(line_cells) < content_width:
                        if line_cells:
                            last_bg = line_cells[-1].bg_color
                            pad_cell = get_pooled_cell(char=" ", bg_color=last_bg)
                        else:
                            pad_cell = get_pooled_cell(char=" ")

                        line_cells.extend(
                            [pad_cell] * (content_width - len(line_cells))
                        )

                    ctx.buffer.set_cells_horizontal(
                        ctx.bounds.x, ctx.bounds.y + current_y, line_cells
                    )

            # Add scrollbar character
            if needs_scrollbar:
                scrollbar_idx = current_y - start_y
                if scrollbar_idx < len(scrollbar_chars):
                    if self.focused:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "contentview.border:focus"
                        )
                    else:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "contentview.border"
                        )
                    scrollbar_attrs = scrollbar_style.to_cell_attrs()

                    ctx.buffer.set_cell(
                        ctx.bounds.x + content_width,
                        ctx.bounds.y + current_y,
                        Cell(char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs),
                    )

            current_y += 1
            rendered_idx += 1

        # Fill remaining rows
        if current_y < start_y + content_height:
            space_cell = get_pooled_cell(char=" ")
            empty_line = [space_cell] * content_width

            while current_y < start_y + content_height:
                ctx.buffer.set_cells_horizontal(
                    ctx.bounds.x, ctx.bounds.y + current_y, empty_line
                )

                if needs_scrollbar:
                    scrollbar_idx = current_y - start_y
                    if scrollbar_idx < len(scrollbar_chars):
                        if self.focused:
                            scrollbar_style = ctx.style_resolver.resolve_style(
                                self, "contentview.border:focus"
                            )
                        else:
                            scrollbar_style = ctx.style_resolver.resolve_style(
                                self, "contentview.border"
                            )
                        scrollbar_attrs = scrollbar_style.to_cell_attrs()

                        ctx.buffer.set_cell(
                            ctx.bounds.x + content_width,
                            ctx.bounds.y + current_y,
                            get_pooled_cell(
                                char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs
                            ),
                        )

                current_y += 1

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Return preferred size for auto sizing.

        Returns
        -------
        tuple of (int, int)
            Preferred (width, height)
        """
        # Account for borders
        if self.border_style != "none":
            return (self.width + 2, self.height + 2)
        return (self.width, self.height)
