"""Unified content display element supporting multiple content types.

This module provides the ContentView element which can render content in
multiple formats: plain text, ANSI, HTML, Markdown, Rich markup, and code
with syntax highlighting. It replaces the separate MarkdownView, HTMLViewer,
and CodeBlock elements with a unified, flexible component.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from wijjit.elements.base import ElementType, ScrollableElement, invoke_callback
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.rendering import PaintContext
from wijjit.styling.style import Style
from wijjit.terminal.ansi import visible_length
from wijjit.terminal.cell import is_continuation
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.layout.bounds import Bounds
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
    content : str or callable
        Content to display (default: ""). A callable is called with the inner
        width in columns and returns the content as a string, so content laid
        out ahead of time (pre-rendered ANSI, say) can be laid out at the width
        it is shown at. It is called again when that width changes, and once
        more, a column narrower, when its result needs the scrollbar. Pass the
        same callable on every render: a new one is called again.
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
    action : str, optional
        Action dispatched on a left click in the content area (default: None).
        The :class:`~wijjit.core.events.ActionEvent`'s ``data`` is
        ``{"line": line, "column": column}``, as for ``on_click``.
    on_click : callable, optional
        ``on_click(line, column, event)``, called on a left click in the
        content area (default: None). ``line`` is the content line, scroll
        offset applied (0-based); ``column`` is the display column within it
        (0-based, a wide character counting two, a click on either of its
        columns reporting the first). With callable ``content`` these are
        positions in the layout the callable produced. A click on the border,
        the scrollbar, or below the last line reports nothing.
    on_hover : callable, optional
        ``on_hover(line, column)``, called when the pointer moves to a new
        position in the content area, and ``on_hover(None, None)`` when it
        leaves it (default: None). Pointer motion is only reported to the app
        with ``MOUSE_TRACKING_MODE = "all_events"``.

    Attributes
    ----------
    content : str or callable
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
        classes: str | list[str] | set[str] | None = None,
        content: str | Callable[[int], str] = "",
        content_type: str | ContentType = "plain",
        language: str = "python",
        theme: str = "monokai",
        show_line_numbers: bool = False,
        line_number_start: int = 1,
        width: int | str = 60,
        height: int | str = 20,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        tab_index: int | None = None,
        bind: bool | str = True,
        action: str | None = None,
        on_click: Callable[[int, int, MouseEvent], Any] | None = None,
        on_hover: Callable[[int | None, int | None], Any] | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Pointer reporting. on_action is set by wiring from ``action``; the
        # last hover position is kept so on_hover fires only on a change.
        self.on_click = on_click
        self.on_hover = on_hover
        self.on_action: Callable[[int, int], Any] | None = None
        self._hover_position: tuple[int, int] | None = None

        # Content and type. For callable content, the width it was last laid
        # out at (see _render_callable).
        self._content = content
        self._callable_width: int | None = None
        self._content_type = self._resolve_content_type(content_type)

        # Code-specific options
        self.language = language
        self.theme = theme
        self.show_line_numbers = show_line_numbers
        self.line_number_start = line_number_start

        # Dynamic sizing flag - detect "fill" or other string values
        self._dynamic_sizing: bool = isinstance(width, str) or isinstance(height, str)

        # Display properties - convert string specs to sensible defaults
        # These will be updated by set_bounds() when layout is computed
        if isinstance(width, str):
            self.width = 60  # Default until layout sets actual size
        else:
            self.width = width
        if isinstance(height, str):
            self.height = 20  # Default until layout sets actual size
        else:
            self.height = height
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title

        # Rendered content caches
        self.rendered_lines: list[str] = []
        self.rendered_cells: list[list[Any]] = []  # For HTML content type
        self._uses_cells = False  # Flag to indicate cell-based rendering

        # Cache key for avoiding re-renders
        self._render_cache_key: tuple[Any, ...] | None = None

        # Parsed cells per rendered ANSI line, keyed by the line itself so it
        # can never go stale (see _parse_line).
        self._line_cell_cache: dict[str, list[Any]] = {}

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
        self.action = action
        self.bind: bool | str = bind

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

    @property
    def content(self) -> str | Callable[[int], str]:
        """Get the current content.

        Returns
        -------
        str or callable
            Current content string, or the function of the width that makes it
        """
        return self._content

    @content.setter
    def content(self, value: str | Callable[[int], str]) -> None:
        """Set the content and update scroll manager.

        When content is changed dynamically, this setter ensures the scroll
        manager is updated with the new content size.

        Parameters
        ----------
        value : str
            New content string
        """
        if value != self._content:
            self._content = value
            # Clear cache to force re-render
            self._render_cache_key = None
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

    def set_bounds(self, bounds: Bounds) -> None:
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
        if callable(self._content) and self._callable_width is not None:
            return self._callable_width

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
        if callable(self._content):
            self._render_callable(self._content)
            return

        content_width = self._get_content_width()

        # Build cache key based on content type and relevant parameters
        cache_key: tuple[Any, ...]
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

        self._render_text(self._content, content_width)
        self._render_cache_key = cache_key

    def _render_callable(self, make_content: Callable[[int], str]) -> None:
        """Lay out callable content at the width it will be shown at.

        Whether the scrollbar takes a column depends on how many lines the
        content makes, which depends on the width. So the callable is first
        called at the full inner width and, if its result needs the scrollbar,
        once more a column narrower; the width chosen is kept so later frames
        agree with it rather than flipping between the two.

        Parameters
        ----------
        make_content : callable
            Function of the width in columns returning the content.
        """
        cache_key = (
            make_content,
            self.width,
            self.height,
            self.show_scrollbar,
            self._content_type,
            self.language,
            self.theme,
            self.show_line_numbers,
            self.line_number_start,
        )
        if self._render_cache_key == cache_key:
            return
        if self._dynamic_sizing and self.bounds is None:
            # The real width arrives with the first layout; laying the content
            # out at the placeholder size first would be wasted work.
            self.rendered_lines = [""]
            self._uses_cells = False
            return

        width = max(1, self.width)
        self._render_text(make_content(width), width)
        needs_scrollbar = self._rendered_count() > self._get_content_height()
        if self.show_scrollbar and width > 1 and needs_scrollbar:
            width -= 1
            self._render_text(make_content(width), width)
        self._callable_width = width
        self._render_cache_key = cache_key

    def _rendered_count(self) -> int:
        """Return the number of rendered rows.

        Returns
        -------
        int
            Rows in the line or cell cache, whichever the content type uses.
        """
        if self._uses_cells:
            return len(self.rendered_cells)
        return len(self.rendered_lines)

    def _render_text(self, text: str, content_width: int) -> None:
        """Render content text into the line or cell cache by content type.

        Parameters
        ----------
        text : str
            Content to render.
        content_width : int
            Width to render at.
        """
        from wijjit.rendering.content_renderers import (
            render_ansi_to_lines,
            render_code_to_lines,
            render_html_to_cells,
            render_markdown_to_lines,
            render_plain_to_lines,
            render_rich_to_lines,
        )

        self._uses_cells = False

        if self._content_type in (ContentType.PLAIN, ContentType.TEXT):
            self.rendered_lines = render_plain_to_lines(text, content_width)

        elif self._content_type == ContentType.ANSI:
            self.rendered_lines = render_ansi_to_lines(text, content_width)

        elif self._content_type == ContentType.HTML:
            self._uses_cells = True
            self.rendered_cells = render_html_to_cells(
                text, content_width, self._style_resolver
            )

        elif self._content_type == ContentType.MARKDOWN:
            self.rendered_lines = render_markdown_to_lines(text, content_width)

        elif self._content_type == ContentType.RICH:
            self.rendered_lines = render_rich_to_lines(text, content_width)

        elif self._content_type == ContentType.CODE:
            self.rendered_lines = render_code_to_lines(
                text,
                content_width,
                language=self.language,
                theme=self.theme,
                show_line_numbers=self.show_line_numbers,
                line_number_start=self.line_number_start,
            )

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
        self._content = content
        if content_type is not None:
            self._content_type = self._resolve_content_type(content_type)

        # Clear cache to force re-render
        self._render_cache_key = None
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
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        # Down arrow - scroll down one row
        elif key == Keys.DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                return True
            return False

        # Home - jump to top
        elif key == Keys.HOME:
            self.scroll_manager.scroll_to(0)
            if self.on_scroll:
                invoke_callback(
                    self.on_scroll, self.scroll_manager.state.scroll_position
                )
            return True

        # End - jump to bottom
        elif key == Keys.END:
            self.scroll_manager.scroll_to_bottom()
            if self.on_scroll:
                invoke_callback(
                    self.on_scroll, self.scroll_manager.state.scroll_position
                )
            return True

        # Page Up
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

        # Page Down
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

        return False

    def content_position_at(self, x: int, y: int) -> tuple[int, int] | None:
        """Map a screen cell to a position in the content.

        Parameters
        ----------
        x, y : int
            Screen column and row (0-based), as a mouse event reports them.

        Returns
        -------
        tuple of (int, int) or None
            ``(line, column)``: the content line, scroll offset applied, and
            the display column within it (a wide character counts two; either
            of its columns maps to the first). None when the cell is not over
            content: outside the view, on the border or the scrollbar, or
            below the last line. A column past the end of a shorter line is
            still reported.
        """
        if self.bounds is None:
            return None

        inset = 0 if self.border_style == "none" else 1
        column = x - self.bounds.x - inset
        row = y - self.bounds.y - inset
        # The scrollbar sits in the column just past the content width.
        if not (
            0 <= column < self._get_content_width()
            and 0 <= row < self._get_content_height()
        ):
            return None

        line = self.scroll_manager.state.scroll_position + row
        if line >= self._rendered_count():
            return None

        # Cells are one per display column, a wide glyph's second column being
        # a continuation cell; step back from it to the glyph's own column.
        cells = self._line_cells(line)
        if 0 < column < len(cells) and is_continuation(cells[column]):
            column -= 1
        return line, column

    def _line_cells(self, line: int) -> list[Any]:
        """Return the cells of one rendered line (one cell per column).

        Parameters
        ----------
        line : int
            Index into the rendered lines.

        Returns
        -------
        list of Cell
            The line's cells, as the view paints them. Do not mutate: an ANSI
            line's cells are shared with the paint cache.
        """
        if self._uses_cells:
            return list(self.rendered_cells[line])
        return self._parse_line(self.rendered_lines[line])

    def _parse_line(self, ansi_line: str) -> list[Any]:
        """Return the cells of a rendered ANSI line, parsing it once.

        Parameters
        ----------
        ansi_line : str
            One line of the rendered content.

        Returns
        -------
        list of Cell
            The parsed cells, shared between calls: callers must copy before
            changing the list (slicing does).

        Notes
        -----
        Painting used to re-parse every visible line on every frame, a few
        milliseconds a frame for a full-screen document. Keying on the line
        string rather than its index means a re-render (new content, a resize)
        needs no invalidation, and identical lines share an entry. The cache is
        cleared when it outgrows the document, so content that changes
        constantly (a streaming log) cannot grow it without limit.
        """
        cells = self._line_cell_cache.get(ansi_line)
        if cells is None:
            from wijjit.rendering.ansi_adapter import ansi_string_to_cells

            if len(self._line_cell_cache) > max(256, 2 * len(self.rendered_lines)):
                self._line_cell_cache.clear()
            cells = ansi_string_to_cells(ansi_line)
            self._line_cell_cache[ansi_line] = cells
        return cells

    def _report_hover(self, position: tuple[int, int] | None) -> bool:
        """Tell ``on_hover`` about a new pointer position, if it changed.

        Parameters
        ----------
        position : tuple of (int, int) or None
            The new position, or None when the pointer is off the content.

        Returns
        -------
        bool
            True if ``on_hover`` was called.
        """
        if position == self._hover_position:
            return False
        self._hover_position = position
        if self.on_hover is None:
            return False
        if position is None:
            invoke_callback(self.on_hover, None, None)
        else:
            invoke_callback(self.on_hover, *position)
        return True

    def on_hover_exit(self) -> None:
        """Report the pointer leaving the view to ``on_hover``."""
        super().on_hover_exit()
        self._report_hover(None)

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input: scrolling, and clicks and hovers on content.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled

        Notes
        -----
        A left click over content calls ``on_click`` and dispatches ``action``
        with the ``(line, column)`` from :meth:`content_position_at`. Pointer
        motion calls ``on_hover`` when the position changes, as does a wheel
        scroll that moves the content under the pointer.
        """
        # Handle scroll wheel
        # Delegate to the base handler first so double-click / context-menu
        # callbacks fire even though this element consumes click events.
        if await super().handle_mouse(event):
            return True

        if event.button == MouseButton.SCROLL_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                # The content moved under a still pointer.
                self._report_hover(self.content_position_at(event.x, event.y))
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                if self.on_scroll:
                    invoke_callback(
                        self.on_scroll, self.scroll_manager.state.scroll_position
                    )
                # The content moved under a still pointer.
                self._report_hover(self.content_position_at(event.x, event.y))
                return True
            return False

        if event.type == MouseEventType.CLICK and event.button == MouseButton.LEFT:
            if self.on_click is None and self.on_action is None:
                return False
            position = self.content_position_at(event.x, event.y)
            if position is None:
                return False
            line, column = position
            if self.on_click is not None:
                invoke_callback(self.on_click, line, column, event)
            if self.on_action is not None:
                invoke_callback(self.on_action, line, column)
            return True

        if event.type == MouseEventType.MOVE:
            return self._report_hover(self.content_position_at(event.x, event.y))

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

        Theme styles:

        This element uses the following theme style classes:
        - ``contentview``: Base style (for background/fallback)
        - ``contentview:focus``: When content view has focus
        - ``contentview.border``: For border characters
        - ``contentview.border:focus``: For border when focused
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
        from wijjit.layout.frames import BORDER_CHARS_UNICODE, BorderStyle
        from wijjit.terminal.cell import get_pooled_cell

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS_UNICODE[style]
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
                ctx.write_cells(0, 0, top_cells)
            else:
                h_cell = get_pooled_cell(char=chars["h"], **border_attrs)
                top_cells = [get_pooled_cell(char=chars["tl"], **border_attrs)]
                top_cells.extend([h_cell] * border_width)
                top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
                ctx.write_cells(0, 0, top_cells)
        else:
            h_cell = get_pooled_cell(char=chars["h"], **border_attrs)
            top_cells = [get_pooled_cell(char=chars["tl"], **border_attrs)]
            top_cells.extend([h_cell] * (total_width - 2))
            top_cells.append(get_pooled_cell(char=chars["tr"], **border_attrs))
            ctx.write_cells(0, 0, top_cells)

        # Render content area
        content_ctx = ctx.sub_context(
            1, 1, content_width + scrollbar_width, content_height
        )
        self._render_to_content(content_ctx, 0, content_height, content_width)

        # Render side borders
        v_cell = get_pooled_cell(char=chars["v"], **border_attrs)
        v_cells = [v_cell] * content_height
        ctx.write_cells_vertical(0, 1, v_cells)
        ctx.write_cells_vertical(total_width - 1, 1, v_cells)

        # Render bottom border
        bottom_y = content_height + 1
        h_cell = get_pooled_cell(char=chars["h"], **border_attrs)
        bottom_cells = [get_pooled_cell(char=chars["bl"], **border_attrs)]
        bottom_cells.extend([h_cell] * (total_width - 2))
        bottom_cells.append(get_pooled_cell(char=chars["br"], **border_attrs))
        ctx.write_cells(0, bottom_y, bottom_cells)

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
        from wijjit.rendering.ansi_adapter import clip_cells
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
                    ctx.write_cells(0, current_y, empty_line)
                else:
                    cells = self.rendered_cells[rendered_idx]
                    line_cells = clip_cells(cells, content_width)

                    # Pad remaining width
                    if len(line_cells) < content_width:
                        pad_cell = get_pooled_cell(char=" ")
                        line_cells = list(line_cells)
                        line_cells.extend(
                            [pad_cell] * (content_width - len(line_cells))
                        )

                    ctx.write_cells(0, current_y, line_cells)
            else:
                # ANSI-based content types
                if rendered_idx >= len(self.rendered_lines):
                    space_cell = get_pooled_cell(char=" ")
                    empty_line = [space_cell] * content_width
                    ctx.write_cells(0, current_y, empty_line)
                else:
                    ansi_line = self.rendered_lines[rendered_idx]
                    cells = self._parse_line(ansi_line)

                    line_cells = clip_cells(cells, content_width)

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

                    ctx.write_cells(0, current_y, line_cells)

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

                    ctx.write_cell(
                        content_width,
                        current_y,
                        Cell(char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs),
                    )

            current_y += 1
            rendered_idx += 1

        # Fill remaining rows
        if current_y < start_y + content_height:
            space_cell = get_pooled_cell(char=" ")
            empty_line = [space_cell] * content_width

            while current_y < start_y + content_height:
                ctx.write_cells(0, current_y, empty_line)

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

                        ctx.write_cell(
                            content_width,
                            current_y,
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
