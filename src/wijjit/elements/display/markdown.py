# ${DIR_PATH}/${FILE_NAME}

from wijjit.elements.base import Element, ElementType, ScrollableMixin
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.rendering import PaintContext
from wijjit.styling.style import Style
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent


class MarkdownView(ScrollableMixin, Element):
    """Markdown content display element with Rich integration.

    This element renders markdown content using Rich's Markdown renderer,
    with support for scrolling, borders, and mouse/keyboard interaction.

    Parameters
    ----------
    id : str, optional
        Element identifier
    content : str, optional
        Markdown content to display (default: "")
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
        Markdown content
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
        Cached rendered content lines
    """

    def __init__(
        self,
        id: str | None = None,
        content: str = "",
        width: int = 60,
        height: int = 20,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
    ):
        ScrollableMixin.__init__(self)
        Element.__init__(self, id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and display properties
        self.content = content
        self.width = width
        self.height = height
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title

        # Rendered content cache
        self.rendered_lines: list[str] = []

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # Callbacks (on_scroll provided by ScrollableMixin)

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence (scroll_state_key provided by ScrollableMixin)

        # Dynamic sizing flag (set by template tag)
        self._dynamic_sizing: bool = False

    def set_bounds(self, bounds) -> None:
        """Set bounds and dynamically resize if needed.

        Parameters
        ----------
        bounds : Bounds
            New bounds for the element
        """
        super().set_bounds(bounds)

        # If dynamic sizing is enabled, resize the element to fit the bounds
        if self._dynamic_sizing and bounds:
            new_width = bounds.width
            new_height = bounds.height

            # Account for borders
            if self.border_style != "none":
                new_width = max(3, new_width - 2)  # Minimum width for borders
                new_height = max(3, new_height - 2)  # Minimum height for borders

            # Update dimensions if changed
            if new_width != self.width or new_height != self.height:
                self.width = new_width
                self.height = new_height

                # Re-render content with new dimensions
                self._render_content()

                # Update scroll manager with new viewport size
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
            # Borders take 2 rows (top and bottom)
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

        # Account for borders
        if self.border_style != "none":
            content_width -= 2  # Left and right borders

        # Account for scrollbar
        # During initialization, reserve space if show_scrollbar is True
        # After initialization, only reserve if actually scrollable
        if self.show_scrollbar:
            if not hasattr(self, "scroll_manager"):
                # During initialization - always reserve space
                content_width -= 1
            elif self.scroll_manager.state.is_scrollable:
                # After initialization - only if content is scrollable
                content_width -= 1

        return max(1, content_width)

    def _render_content(self) -> None:
        """Render markdown content to ANSI strings using Rich.

        Updates the rendered_lines cache with the current content.
        """
        from io import StringIO

        from rich.console import Console
        from rich.markdown import Markdown

        # Get content width for rendering
        content_width = self._get_content_width()

        # Render markdown using Rich
        md = Markdown(self.content)
        string_buffer = StringIO()
        console = Console(
            file=string_buffer,
            width=content_width,
            legacy_windows=False,
            force_terminal=True,
        )
        console.print(md)
        output = string_buffer.getvalue()

        # Split into lines
        self.rendered_lines = output.rstrip("\n").split("\n")

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [""]

    def set_content(self, content: str) -> None:
        """Update markdown content and re-render.

        Parameters
        ----------
        content : str
            New markdown content
        """
        self.content = content
        self._render_content()

        # Update scroll manager with new content size
        self.scroll_manager.update_content_size(len(self.rendered_lines))

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore
        """
        self.scroll_manager.scroll_to(position)

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

    def _render_with_border(self, content_lines: list[str]) -> list[str]:
        """Render content with border.

        Parameters
        ----------
        content_lines : list of str
            Content lines to wrap with border

        Returns
        -------
        list of str
            Lines with border added
        """
        from wijjit.layout.frames import BORDER_CHARS, BorderStyle
        from wijjit.terminal.ansi import ANSIColor, ANSIStyle

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS[style]

        # Choose border color based on focus
        if self.focused:
            border_color = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}"
            reset = ANSIStyle.RESET
        else:
            border_color = ""
            reset = ""

        # Calculate content width (total width - 2 for borders)
        content_width = self.width - 2

        # Build top border
        if self.title:
            # Border with title
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            if title_len < content_width:
                remaining = content_width - title_len
                left_line = chars["h"] * (remaining // 2)
                right_line = chars["h"] * (remaining - len(left_line))
                top_line = f"{border_color}{chars['tl']}{left_line}{title_text}{right_line}{chars['tr']}{reset}"
            else:
                # Title too long, just show border
                top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"
        else:
            # Border without title
            top_line = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"

        # Build bottom border
        bottom_line = f"{border_color}{chars['bl']}{chars['h'] * content_width}{chars['br']}{reset}"

        # Wrap content lines with borders
        bordered_lines = [top_line]
        for line in content_lines:
            # Ensure line is padded to content width
            line_len = visible_length(line)
            if line_len < content_width:
                line = line + " " * (content_width - line_len)
            elif line_len > content_width:
                line = clip_to_width(line, content_width, ellipsis="")

            bordered_lines.append(
                f"{border_color}{chars['v']}{reset}{line}{border_color}{chars['v']}{reset}"
            )

        bordered_lines.append(bottom_line)

        return bordered_lines

    def render(self) -> str:
        """Render the markdown view (LEGACY ANSI rendering).

        Returns
        -------
        str
            Rendered markdown view as multi-line string

        Notes
        -----
        This is the legacy ANSI string-based rendering method.
        New code should use render_to() for cell-based rendering.
        Kept for backward compatibility.
        """
        content_height = self._get_content_height()
        content_width = self._get_content_width()

        # Get visible lines
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_lines = self.rendered_lines[visible_start:visible_end]

        # Pad or trim to exact content height
        if len(visible_lines) < content_height:
            visible_lines.extend(
                ["" for _ in range(content_height - len(visible_lines))]
            )
        else:
            visible_lines = visible_lines[:content_height]

        # Ensure all lines are padded to content width
        for i in range(len(visible_lines)):
            line = visible_lines[i]
            line_len = visible_length(line)
            if line_len < content_width:
                visible_lines[i] = line + " " * (content_width - line_len)
            elif line_len > content_width:
                visible_lines[i] = clip_to_width(line, content_width, ellipsis="")

        # Add scrollbar if needed
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, content_height
            )

            for i in range(len(visible_lines)):
                visible_lines[i] = visible_lines[i] + scrollbar_chars[i]

        # Add borders if requested
        if self.border_style != "none":
            final_lines = self._render_with_border(visible_lines)
        else:
            final_lines = visible_lines

        return "\n".join(final_lines)

    def render_to(self, ctx: PaintContext) -> None:
        """Render markdown view using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for markdown views, supporting:
        - Rich markdown formatting (preserves headers, bold, code, etc.)
        - Scrolling with scrollbar
        - Borders with titles and focus styling
        - Theme-based styling for borders and background

        The markdown content is rendered by Rich, which generates ANSI codes.
        These ANSI codes are converted to cells, preserving Rich's formatting.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'markdown': Base markdown style (for background/fallback)
        - 'markdown:focus': When markdown view has focus
        - 'markdown.border': For border characters
        - 'markdown.border:focus': For border when focused
        """
        # Resolve border style based on focus
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(
                self, "markdown.border:focus"
            )
        else:
            border_style = ctx.style_resolver.resolve_style(self, "markdown.border")

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
        """Render markdown view with border using cells.

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
        from wijjit.terminal.cell import Cell

        # Get border characters
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        style = border_map.get(self.border_style, BorderStyle.SINGLE)
        chars = BORDER_CHARS[style]
        border_attrs = border_style.to_cell_attrs()

        # Calculate total width (content + borders + optional scrollbar)
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        scrollbar_width = 1 if needs_scrollbar else 0
        total_width = content_width + scrollbar_width + 2  # +2 for borders

        # Render top border with optional title
        if self.title:
            title_text = f" {self.title} "
            title_len = visible_length(title_text)
            border_width = total_width - 2  # Width without corners

            if title_len < border_width:
                remaining = border_width - title_len
                left_len = remaining // 2
                right_len = remaining - left_len

                # Top-left corner
                ctx.buffer.set_cell(
                    ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
                )

                # Left line
                for i in range(left_len):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + i,
                        ctx.bounds.y,
                        Cell(char=chars["h"], **border_attrs),
                    )

                # Title
                for i, char in enumerate(title_text):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + left_len + i,
                        ctx.bounds.y,
                        Cell(char=char, **border_attrs),
                    )

                # Right line
                for i in range(right_len):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + left_len + title_len + i,
                        ctx.bounds.y,
                        Cell(char=chars["h"], **border_attrs),
                    )

                # Top-right corner
                ctx.buffer.set_cell(
                    ctx.bounds.x + total_width - 1,
                    ctx.bounds.y,
                    Cell(char=chars["tr"], **border_attrs),
                )
            else:
                # Title too long
                ctx.buffer.set_cell(
                    ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
                )
                for i in range(border_width):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + i,
                        ctx.bounds.y,
                        Cell(char=chars["h"], **border_attrs),
                    )
                ctx.buffer.set_cell(
                    ctx.bounds.x + total_width - 1,
                    ctx.bounds.y,
                    Cell(char=chars["tr"], **border_attrs),
                )
        else:
            # No title
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
            )
            for i in range(1, total_width - 1):
                ctx.buffer.set_cell(
                    ctx.bounds.x + i,
                    ctx.bounds.y,
                    Cell(char=chars["h"], **border_attrs),
                )
            ctx.buffer.set_cell(
                ctx.bounds.x + total_width - 1,
                ctx.bounds.y,
                Cell(char=chars["tr"], **border_attrs),
            )

        # Render content area (starting at y=1, inside border)
        # Create sub-context for content (inside borders)
        content_ctx = ctx.sub_context(
            1, 1, content_width + scrollbar_width, content_height
        )
        self._render_to_content(
            content_ctx,
            0,
            content_height,
            content_width,
        )

        # Render side borders for content area
        for y in range(content_height):
            # Left border
            ctx.buffer.set_cell(
                ctx.bounds.x,
                ctx.bounds.y + 1 + y,
                Cell(char=chars["v"], **border_attrs),
            )
            # Right border
            ctx.buffer.set_cell(
                ctx.bounds.x + total_width - 1,
                ctx.bounds.y + 1 + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Render bottom border
        bottom_y = content_height + 1
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + bottom_y,
            Cell(char=chars["bl"], **border_attrs),
        )
        for i in range(1, total_width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + i,
                ctx.bounds.y + bottom_y,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + total_width - 1,
            ctx.bounds.y + bottom_y,
            Cell(char=chars["br"], **border_attrs),
        )

    def _render_to_content(
        self,
        ctx: PaintContext,
        start_y: int,
        content_height: int,
        content_width: int,
    ) -> None:
        """Render markdown content using cells.

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

        Notes
        -----
        Rich-generated ANSI codes are converted to cells, preserving
        all markdown formatting (headers, bold, italic, code, etc.).
        """
        from wijjit.rendering.ansi_adapter import ansi_string_to_cells

        # Get visible range from scroll manager
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

        # Render visible markdown lines
        current_y = start_y
        rendered_line_idx = visible_start

        while current_y < start_y + content_height and rendered_line_idx < visible_end:
            if rendered_line_idx >= len(self.rendered_lines):
                # Pad with empty lines
                for x in range(content_width):
                    from wijjit.terminal.cell import Cell

                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + current_y,
                        Cell(char=" "),
                    )
                current_y += 1
                rendered_line_idx += 1
                continue

            ansi_line = self.rendered_lines[rendered_line_idx]

            # Convert ANSI string to cells (preserves Rich formatting)
            cells = ansi_string_to_cells(ansi_line)

            # Write cells to buffer
            for x, cell in enumerate(cells[:content_width]):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y,
                    cell,
                )

            # Pad remaining width with spaces
            for x in range(len(cells), content_width):
                from wijjit.terminal.cell import Cell

                # Use last cell's style for padding if available, otherwise empty
                if cells:
                    # Preserve background color from last cell
                    last_bg = cells[-1].bg_color if cells else None
                    pad_cell = Cell(char=" ", bg_color=last_bg)
                else:
                    pad_cell = Cell(char=" ")

                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y,
                    pad_cell,
                )

            # Add scrollbar character if needed
            if needs_scrollbar:
                scrollbar_idx = current_y - start_y
                if scrollbar_idx < len(scrollbar_chars):
                    # Resolve scrollbar style (use border style)
                    if self.focused:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "markdown.border:focus"
                        )
                    else:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "markdown.border"
                        )
                    scrollbar_attrs = scrollbar_style.to_cell_attrs()

                    from wijjit.terminal.cell import Cell

                    ctx.buffer.set_cell(
                        ctx.bounds.x + content_width,
                        ctx.bounds.y + current_y,
                        Cell(char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs),
                    )

            current_y += 1
            rendered_line_idx += 1

        # Fill remaining rows if any
        while current_y < start_y + content_height:
            for x in range(content_width):
                from wijjit.terminal.cell import Cell

                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y,
                    Cell(char=" "),
                )

            if needs_scrollbar:
                scrollbar_idx = current_y - start_y
                if scrollbar_idx < len(scrollbar_chars):
                    if self.focused:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "markdown.border:focus"
                        )
                    else:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "markdown.border"
                        )
                    scrollbar_attrs = scrollbar_style.to_cell_attrs()

                    from wijjit.terminal.cell import Cell

                    ctx.buffer.set_cell(
                        ctx.bounds.x + content_width,
                        ctx.bounds.y + current_y,
                        Cell(char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs),
                    )

            current_y += 1
