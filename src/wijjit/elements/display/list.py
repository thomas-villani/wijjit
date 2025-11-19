# ${DIR_PATH}/${FILE_NAME}
from typing import TYPE_CHECKING, Any

from wijjit.elements.base import ElementType, ScrollableElement
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext
    from wijjit.styling.style import Style


class ListView(ScrollableElement):
    """ListView element for displaying lists with bullets, numbers, or details.

    This element provides a display for lists with support for:
    - Multiple bullet styles (bullets, dashes, numbers, or custom characters)
    - Plain lists without bullets
    - Details mode for definition-style lists with dimmed, indented details
    - Optional horizontal dividers between items
    - Scrolling for long lists
    - Borders with optional titles
    - Mouse and keyboard interaction for scrolling

    Parameters
    ----------
    id : str, optional
        Element identifier
    items : list, optional
        List items (strings, 2-tuples, or dicts) (default: [])
    width : int, optional
        Display width in columns (default: 40)
    height : int, optional
        Display height in rows (default: 10)
    bullet : str, optional
        Bullet style: "bullet", "dash", "number",
        custom character, or None for no bullets (default: "bullet")
    show_dividers : bool, optional
        Whether to show horizontal lines between items (default: False)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)
    indent_details : int, optional
        Number of spaces to indent details text (default: 2)
    dim_details : bool, optional
        Whether to dim details text color (default: True)

    Attributes
    ----------
    items : list
        Normalized list items
    width : int
        Display width
    height : int
        Display height
    bullet : str or None
        Bullet style or character
    show_dividers : bool
        Whether dividers are shown
    show_scrollbar : bool
        Whether scrollbar is visible
    border_style : str
        Border style
    title : str or None
        Border title
    indent_details : int
        Details indentation
    dim_details : bool
        Whether details are dimmed
    scroll_manager : ScrollManager
        Manages scrolling of content
    rendered_lines : list of str
        Cached rendered content lines

    Notes
    -----
    List items can be specified as:
    - Strings: ["Item 1", "Item 2"]
    - 2-tuples: [("Label", "Details"), ...]
    - Dicts: [{"label": "Label", "details": "Details"}, ...]

    Details can be multi-line (separated by newlines) and will be
    indented and optionally dimmed.

    Examples
    --------
    Simple bulleted list:
    >>> listview = ListView(items=["Apple", "Banana", "Cherry"])

    Numbered list:
    >>> listview = ListView(items=["First", "Second", "Third"], bullet="number")

    Definition list with details:
    >>> items = [
    ...     ("Python", "A high-level programming language"),
    ...     ("JavaScript", "A dynamic scripting language")
    ... ]
    >>> listview = ListView(items=items, bullet="dash")
    """

    def __init__(
        self,
        id: str | None = None,
        items: list[Any] | None = None,
        width: int = 40,
        height: int = 10,
        bullet: str | None = "bullet",
        show_dividers: bool = False,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        indent_details: int = 2,
        dim_details: bool = True,
    ) -> None:
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and display properties
        self._raw_items = items or []
        self.items = self._normalize_items(self._raw_items)
        self.width = width
        self.height = height
        self.bullet = bullet
        self.show_dividers = show_dividers
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title
        self.indent_details = indent_details
        self.dim_details = dim_details

        # Rendered content cache
        self.rendered_lines: list[str] = []

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # Callbacks (on_scroll provided by ScrollableElement)

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence (scroll_state_key provided by ScrollableElement)

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
        if self.show_scrollbar:
            if not hasattr(self, "scroll_manager"):
                # During initialization - always reserve space
                content_width -= 1
            elif self.scroll_manager.state.is_scrollable:
                # After initialization - only if content is scrollable
                content_width -= 1

        return max(1, content_width)

    def _normalize_items(self, items: list[Any]) -> list[dict]:
        """Normalize items to internal format.

        Parameters
        ----------
        items : list
            Raw items (strings, tuples, or dicts)

        Returns
        -------
        list of dict
            Normalized items with 'label' and 'details' keys

        Notes
        -----
        Supports three input formats:
        - Strings: ["Item 1", "Item 2"]
        - 2-tuples: [("Label", "Details"), ...]
        - Dicts: [{"label": "Label", "details": "Details"}, ...]
        """
        normalized = []
        for item in items:
            if isinstance(item, dict):
                # Dict format
                normalized.append(
                    {
                        "label": str(item.get("label", "")),
                        "details": (
                            str(item.get("details", ""))
                            if item.get("details")
                            else None
                        ),
                    }
                )
            elif isinstance(item, tuple) and len(item) == 2:
                # 2-tuple format
                normalized.append({"label": str(item[0]), "details": str(item[1])})
            else:
                # String or other format - use as label
                normalized.append({"label": str(item), "details": None})

        return normalized

    def _get_bullet_char(self, index: int) -> str:
        """Get bullet character for an item.

        Parameters
        ----------
        index : int
            Item index (0-based)

        Returns
        -------
        str
            Bullet character or prefix string
        """
        from wijjit.terminal.ansi import supports_unicode

        if self.bullet == "bullet":
            # Use unicode bullet if supported, otherwise asterisk
            return "• " if supports_unicode() else "* "
        elif self.bullet == "dash":
            return "- "
        elif self.bullet == "number":
            return f"{index + 1}. "
        elif self.bullet is None:
            return ""
        else:
            # Custom character
            # Ensure it has a space after if it's not empty
            return f"{self.bullet} " if self.bullet else ""

    def _render_content(self) -> None:
        """Render list items to ANSI strings.

        Updates the rendered_lines cache with the current items.
        """
        from wijjit.terminal.ansi import ANSIStyle, supports_unicode

        self.rendered_lines = []
        content_width = self._get_content_width()

        for i, item in enumerate(self.items):
            # Render main label with bullet
            bullet = self._get_bullet_char(i)
            label = item["label"]

            # Calculate available width for label (account for bullet)
            bullet_width = visible_length(bullet)
            label_width = content_width - bullet_width

            # Clip label if too long
            if visible_length(label) > label_width:
                label = clip_to_width(label, label_width, ellipsis="...")

            # Build label line
            label_line = bullet + label
            self.rendered_lines.append(label_line)

            # Render details if present
            if item["details"]:
                details = item["details"]
                indent = " " * self.indent_details

                # Split details into multiple lines
                detail_lines = details.split("\n")

                for detail_line in detail_lines:
                    # Calculate available width for details (account for indent)
                    detail_width = content_width - self.indent_details

                    # Clip detail if too long
                    if visible_length(detail_line) > detail_width:
                        detail_line = clip_to_width(
                            detail_line, detail_width, ellipsis="..."
                        )

                    # Apply dim styling if enabled
                    if self.dim_details:
                        detail_line = f"{ANSIStyle.DIM}{detail_line}{ANSIStyle.RESET}"

                    # Build detail line with indent
                    full_detail_line = indent + detail_line
                    self.rendered_lines.append(full_detail_line)

            # Add divider if requested and not last item
            if self.show_dividers and i < len(self.items) - 1:
                # Horizontal line divider with unicode support fallback
                divider_char = "─" if supports_unicode() else "-"
                divider = divider_char * content_width
                self.rendered_lines.append(divider)

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [""]

    def set_items(self, items: list[Any]) -> None:
        """Update list items and re-render.

        Parameters
        ----------
        items : list
            New list items (strings, tuples, or dicts)
        """
        self._raw_items = items
        self.items = self._normalize_items(items)
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

    def render_to(self, ctx: "PaintContext") -> None:
        """Render list view using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for list views, supporting:
        - Multiple bullet styles (bullet, dash, number, custom)
        - Labels and details with indentation
        - Optional dividers between items
        - Scrolling with scrollbar
        - Borders with titles
        - Theme-based styling

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'listview': Base listview style
        - 'listview:focus': When listview has focus
        - 'listview.label': For item labels
        - 'listview.details': For item details (dimmed)
        - 'listview.divider': For horizontal dividers
        - 'listview.border': For border characters
        - 'listview.border:focus': For border when focused
        """

        # Resolve styles
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(
                self, "listview.border:focus"
            )
        else:
            border_style = ctx.style_resolver.resolve_style(self, "listview.border")

        label_style = ctx.style_resolver.resolve_style(self, "listview.label")
        details_style = ctx.style_resolver.resolve_style(self, "listview.details")
        divider_style = ctx.style_resolver.resolve_style(self, "listview.divider")

        content_height = self._get_content_height()
        content_width = self._get_content_width()

        # Render borders if needed
        if self.border_style != "none":
            self._render_to_with_border(
                ctx, border_style, content_height, content_width
            )
        else:
            # No borders - render content directly
            self._render_to_content(
                ctx,
                0,
                content_height,
                content_width,
                label_style,
                details_style,
                divider_style,
            )

    def _render_to_with_border(
        self,
        ctx: "PaintContext",
        border_style: "Style",
        content_height: int,
        content_width: int,
    ) -> None:
        """Render listview with border using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        border_style : Style
            Border style
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

        # Calculate total width (content + borders)
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
        label_style = ctx.style_resolver.resolve_style(self, "listview.label")
        details_style = ctx.style_resolver.resolve_style(self, "listview.details")
        divider_style = ctx.style_resolver.resolve_style(self, "listview.divider")

        # Create sub-context for content (inside borders)
        content_ctx = ctx.sub_context(
            1, 1, content_width + scrollbar_width, content_height
        )
        self._render_to_content(
            content_ctx,
            0,
            content_height,
            content_width,
            label_style,
            details_style,
            divider_style,
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
        ctx: "PaintContext",
        start_y: int,
        content_height: int,
        content_width: int,
        label_style: "Style",
        details_style: "Style",
        divider_style: "Style",
    ) -> None:
        """Render listview content using cells.

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
        label_style : Style
            Style for labels
        details_style : Style
            Style for details
        divider_style : Style
            Style for dividers
        """
        from wijjit.terminal.cell import Cell

        # Get visible lines from scroll manager
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

        # Render visible content lines
        current_y = start_y
        for line_idx in range(
            visible_start, min(visible_end, len(self.rendered_lines))
        ):
            if current_y >= start_y + content_height:
                break

            line = self.rendered_lines[line_idx]

            # Strip ANSI codes and render to cells
            from wijjit.terminal.ansi import strip_ansi

            clean_line = strip_ansi(line)

            # Determine if this is a detail line (starts with spaces)
            is_detail = (
                clean_line.startswith(" " * self.indent_details) and self.dim_details
            )
            line_style = details_style if is_detail else label_style

            # Check if this is a divider line
            is_divider = "─" in clean_line or "-" * 3 in clean_line
            if is_divider:
                line_style = divider_style

            # Write line content
            line_attrs = line_style.to_cell_attrs()
            for x, char in enumerate(clean_line[:content_width]):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y,
                    Cell(char=char, **line_attrs),
                )

            # Pad remaining width
            for x in range(len(clean_line[:content_width]), content_width):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y,
                    Cell(char=" ", **line_attrs),
                )

            # Add scrollbar character if needed
            if needs_scrollbar:
                scrollbar_idx = current_y - start_y
                scrollbar_char = (
                    scrollbar_chars[scrollbar_idx]
                    if scrollbar_idx < len(scrollbar_chars)
                    else " "
                )
                # Use label style for scrollbar
                ctx.buffer.set_cell(
                    ctx.bounds.x + content_width,
                    ctx.bounds.y + current_y,
                    Cell(char=scrollbar_char, **label_style.to_cell_attrs()),
                )

            current_y += 1

        # Fill remaining lines with empty space
        while current_y < start_y + content_height:
            # Empty line
            for x in range(content_width):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x,
                    ctx.bounds.y + current_y,
                    Cell(char=" ", **label_style.to_cell_attrs()),
                )

            # Add scrollbar character if needed
            if needs_scrollbar:
                scrollbar_idx = current_y - start_y
                scrollbar_char = (
                    scrollbar_chars[scrollbar_idx]
                    if scrollbar_idx < len(scrollbar_chars)
                    else " "
                )
                ctx.buffer.set_cell(
                    ctx.bounds.x + content_width,
                    ctx.bounds.y + current_y,
                    Cell(char=scrollbar_char, **label_style.to_cell_attrs()),
                )

            current_y += 1
