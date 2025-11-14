"""Log viewer element for displaying and scrolling through log files.

This module provides a LogView display element optimized for viewing logs
with automatic log level detection, coloring, auto-scroll, and soft-wrap.
"""

import re

from wijjit.elements.base import Element, ElementType, ScrollableMixin
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.rendering import PaintContext
from wijjit.styling.style import Style
from wijjit.terminal.ansi import (
    ANSIColor,
    ANSIStyle,
    clip_to_width,
    visible_length,
    wrap_text,
)
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent

LOG_PATTERNS = {
    "ERROR": re.compile(r"\b(ERROR|FATAL|CRITICAL|ERR)\b", re.IGNORECASE),
    "WARNING": re.compile(r"\b(WARNING|WARN)\b", re.IGNORECASE),
    "INFO": re.compile(r"\bINFO\b", re.IGNORECASE),
    "DEBUG": re.compile(r"\bDEBUG\b", re.IGNORECASE),
    "TRACE": re.compile(r"\bTRACE\b", re.IGNORECASE),
}


class LogView(ScrollableMixin, Element):
    """LogView element for displaying logs with automatic coloring and scrolling.

    This element provides a display for log files with support for:
    - Automatic log level detection and coloring (ERROR, WARNING, INFO, DEBUG, TRACE)
    - ANSI passthrough - preserves existing ANSI codes in log lines
    - Auto-scroll mode - automatically scrolls to bottom when new lines are added
    - Soft-wrap - optional line wrapping for long lines
    - Line numbers - optional display of line numbers
    - Scrolling for large log files (optimized for 10k+ lines)
    - Borders with optional titles
    - Mouse and keyboard interaction for scrolling

    Parameters
    ----------
    id : str, optional
        Element identifier
    lines : list of str, optional
        Log lines (default: [])
    width : int, optional
        Display width in columns (default: 80)
    height : int, optional
        Display height in rows (default: 20)
    auto_scroll : bool, optional
        Automatically scroll to bottom when new lines added (default: True)
    soft_wrap : bool, optional
        Wrap long lines instead of clipping (default: False)
    show_line_numbers : bool, optional
        Display line numbers on the left (default: False)
    line_number_start : int, optional
        Starting line number (default: 1)
    detect_log_levels : bool, optional
        Automatically detect and color log levels (default: True)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)

    Attributes
    ----------
    lines : list of str
        Raw log lines
    width : int
        Display width
    height : int
        Display height
    auto_scroll : bool
        Auto-scroll enabled flag
    soft_wrap : bool
        Soft-wrap enabled flag
    show_line_numbers : bool
        Line numbers display flag
    line_number_start : int
        Starting line number
    detect_log_levels : bool
        Log level detection flag
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

    Notes
    -----
    Log level detection uses regex patterns to identify common log levels:
    - ERROR/FATAL/CRITICAL → Red + Bold
    - WARNING/WARN → Yellow
    - INFO → Cyan
    - DEBUG → Dim
    - TRACE → Dim

    Auto-scroll behavior:
    - When enabled, automatically scrolls to bottom when new lines are added
    - Disabled when user manually scrolls up from bottom
    - Re-enabled when user scrolls back to bottom or presses End key

    Examples
    --------
    Basic log view:
    >>> logview = LogView(lines=["INFO: App started", "ERROR: Connection failed"])

    With auto-scroll and soft-wrap:
    >>> logview = LogView(
    ...     lines=logs,
    ...     auto_scroll=True,
    ...     soft_wrap=True,
    ...     width=80,
    ...     height=20
    ... )

    With line numbers:
    >>> logview = LogView(
    ...     lines=logs,
    ...     show_line_numbers=True,
    ...     line_number_start=1
    ... )
    """

    def __init__(
        self,
        id: str | None = None,
        lines: list[str] | None = None,
        width: int = 80,
        height: int = 20,
        auto_scroll: bool = True,
        soft_wrap: bool = False,
        show_line_numbers: bool = False,
        line_number_start: int = 1,
        detect_log_levels: bool = True,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
    ):
        ScrollableMixin.__init__(self)
        Element.__init__(self, id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and display properties
        self.lines = lines or []
        self.width = width
        self.height = height
        self.auto_scroll = auto_scroll
        self.soft_wrap = soft_wrap
        self.show_line_numbers = show_line_numbers
        self.line_number_start = line_number_start
        self.detect_log_levels = detect_log_levels
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title

        # Auto-scroll state tracking
        self._user_scrolled_up = False
        self._last_content_size = 0

        # Rendered content cache
        self.rendered_lines: list[str] = []

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # If auto-scroll is enabled, start at bottom
        if self.auto_scroll:
            self.scroll_manager.scroll_to_bottom()
            self._last_content_size = len(self.rendered_lines)

        # Callbacks (on_scroll provided by ScrollableMixin)

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence
        # scroll_state_key provided by ScrollableMixin
        self.autoscroll_state_key: str | None = None
        self._state_dict: dict | None = None

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
        """Calculate content area width accounting for borders, scrollbar, and line numbers.

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

        # Account for line numbers
        if self.show_line_numbers:
            # Calculate width needed for line numbers (with padding)
            max_line_num = self.line_number_start + len(self.lines) - 1
            line_num_width = len(str(max_line_num)) + 2  # +2 for space and separator
            content_width -= line_num_width

        return max(1, content_width)

    def _detect_log_level(self, line: str) -> str | None:
        """Detect log level in a line.

        Parameters
        ----------
        line : str
            Log line to analyze

        Returns
        -------
        str or None
            Detected log level ("ERROR", "WARNING", "INFO", "DEBUG", "TRACE")
            or None if no level detected
        """
        if not self.detect_log_levels:
            return None

        # Check patterns in priority order
        for level, pattern in LOG_PATTERNS.items():
            if pattern.search(line):
                return level

        return None

    def _colorize_line(self, line: str) -> str:
        """Apply color to a log line based on detected level (LEGACY).

        Parameters
        ----------
        line : str
            Log line to colorize

        Returns
        -------
        str
            Colorized line with ANSI codes (or original if no level detected)

        Notes
        -----
        This is the legacy ANSI string-based colorization method.
        New code should use _get_log_level_style() for cell-based rendering.
        Kept for backward compatibility.
        """
        level = self._detect_log_level(line)

        if level == "ERROR":
            return f"{ANSIStyle.BOLD}{ANSIColor.RED}{line}{ANSIStyle.RESET}"
        elif level == "WARNING":
            return f"{ANSIColor.YELLOW}{line}{ANSIStyle.RESET}"
        elif level == "INFO":
            return f"{ANSIColor.CYAN}{line}{ANSIStyle.RESET}"
        elif level == "DEBUG":
            return f"{ANSIStyle.DIM}{line}{ANSIStyle.RESET}"
        elif level == "TRACE":
            return f"{ANSIStyle.DIM}{ANSIColor.BRIGHT_BLACK}{line}{ANSIStyle.RESET}"
        else:
            # No level detected, return as-is (preserves existing ANSI)
            return line

    def _get_log_level_style_class(self, line: str) -> str:
        """Get theme style class for a log line based on detected level.

        Parameters
        ----------
        line : str
            Log line to analyze

        Returns
        -------
        str
            Theme style class name (e.g., 'logview.error', 'logview.info')

        Notes
        -----
        Returns 'logview' for lines with no detected log level.
        """
        level = self._detect_log_level(line)

        if level == "ERROR":
            return "logview.error"
        elif level == "WARNING":
            return "logview.warning"
        elif level == "INFO":
            return "logview.info"
        elif level == "DEBUG":
            return "logview.debug"
        elif level == "TRACE":
            return "logview.trace"
        else:
            return "logview"

    def _format_line_number(self, line_num: int) -> str:
        """Format line number with padding.

        Parameters
        ----------
        line_num : int
            Line number

        Returns
        -------
        str
            Formatted line number string
        """
        max_line_num = self.line_number_start + len(self.lines) - 1
        width = len(str(max_line_num))
        return f"{line_num:>{width}} "

    def _render_content(self) -> None:
        """Render log lines to ANSI strings.

        Updates the rendered_lines cache with the current lines.
        """
        self.rendered_lines = []
        content_width = self._get_content_width()

        for i, line in enumerate(self.lines):
            # Colorize the line if detection is enabled
            colored_line = self._colorize_line(line)

            if self.soft_wrap:
                # Wrap long lines
                wrapped_segments = wrap_text(colored_line, content_width)
                for j, segment in enumerate(wrapped_segments):
                    # Add line number only to first segment of wrapped line
                    if self.show_line_numbers and j == 0:
                        line_num = self.line_number_start + i
                        line_prefix = self._format_line_number(line_num)
                        full_line = line_prefix + segment
                    elif self.show_line_numbers and j > 0:
                        # Continuation lines get empty line number space
                        max_line_num = self.line_number_start + len(self.lines) - 1
                        width = len(str(max_line_num))
                        line_prefix = " " * (width + 1)
                        full_line = line_prefix + segment
                    else:
                        full_line = segment

                    self.rendered_lines.append(full_line)
            else:
                # Clip long lines
                if visible_length(colored_line) > content_width:
                    colored_line = clip_to_width(
                        colored_line, content_width, ellipsis="..."
                    )

                # Add line number if enabled
                if self.show_line_numbers:
                    line_num = self.line_number_start + i
                    line_prefix = self._format_line_number(line_num)
                    full_line = line_prefix + colored_line
                else:
                    full_line = colored_line

                self.rendered_lines.append(full_line)

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [""]

    def set_lines(self, lines: list[str]) -> None:
        """Update log lines and re-render.

        Parameters
        ----------
        lines : list of str
            New log lines

        Notes
        -----
        If auto-scroll is enabled and user hasn't manually scrolled up,
        this will automatically scroll to the bottom after updating.
        """
        self.lines = lines
        self._render_content()

        # Update scroll manager with new content size
        old_content_size = self.scroll_manager.state.content_size
        self.scroll_manager.update_content_size(len(self.rendered_lines))

        # Auto-scroll if enabled and user hasn't scrolled up
        if self.auto_scroll and not self._user_scrolled_up:
            # Only auto-scroll if content actually grew
            if len(self.rendered_lines) > old_content_size:
                self.scroll_manager.scroll_to_bottom()

        self._last_content_size = len(self.rendered_lines)

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore
        """
        self.scroll_manager.scroll_to(position)

        # Update user scroll state based on position
        if position >= self.scroll_manager.state.max_scroll:
            self._user_scrolled_up = False
        else:
            self._user_scrolled_up = True

    def _save_scroll_state(self) -> None:
        """Save scroll position to app state if available."""
        if self._state_dict is not None and self.scroll_state_key:
            self._state_dict[self.scroll_state_key] = (
                self.scroll_manager.state.scroll_position
            )

    def _save_autoscroll_state(self) -> None:
        """Save auto-scroll state to app state if available."""
        if self._state_dict is not None and self.autoscroll_state_key:
            self._state_dict[self.autoscroll_state_key] = self.auto_scroll

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

        # Up arrow - scroll up one row
        if key == Keys.UP:
            self.scroll_manager.scroll_by(-1)
            if old_pos != self.scroll_manager.state.scroll_position:
                # User manually scrolled up
                self._user_scrolled_up = True
                self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Down arrow - scroll down one row
        elif key == Keys.DOWN:
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                # Check if we're at the bottom
                if (
                    self.scroll_manager.state.scroll_position
                    >= self.scroll_manager.state.max_scroll
                ):
                    self._user_scrolled_up = False
                self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Home - jump to top
        elif key == Keys.HOME:
            self.scroll_manager.scroll_to(0)
            self._user_scrolled_up = True
            self._save_scroll_state()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # End - jump to bottom
        elif key == Keys.END:
            self.scroll_manager.scroll_to_bottom()
            self._user_scrolled_up = False  # Re-enable auto-scroll
            self._save_scroll_state()
            if self.on_scroll:
                self.on_scroll(self.scroll_manager.state.scroll_position)
            return True

        # Page Up
        elif key == Keys.PAGE_UP:
            self.scroll_manager.page_up()
            if old_pos != self.scroll_manager.state.scroll_position:
                self._user_scrolled_up = True
                self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        # Page Down
        elif key == Keys.PAGE_DOWN:
            self.scroll_manager.page_down()
            if old_pos != self.scroll_manager.state.scroll_position:
                # Check if we're at the bottom
                if (
                    self.scroll_manager.state.scroll_position
                    >= self.scroll_manager.state.max_scroll
                ):
                    self._user_scrolled_up = False
                self._save_scroll_state()
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
        old_pos = self.scroll_manager.state.scroll_position

        # Handle scroll wheel
        if event.button == MouseButton.SCROLL_UP:
            self.scroll_manager.scroll_by(-1)
            if old_pos != self.scroll_manager.state.scroll_position:
                # User manually scrolled up
                self._user_scrolled_up = True
                self._save_scroll_state()
                if self.on_scroll:
                    self.on_scroll(self.scroll_manager.state.scroll_position)
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            self.scroll_manager.scroll_by(1)
            if old_pos != self.scroll_manager.state.scroll_position:
                # Check if we're at the bottom
                if (
                    self.scroll_manager.state.scroll_position
                    >= self.scroll_manager.state.max_scroll
                ):
                    self._user_scrolled_up = False
                self._save_scroll_state()
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
        """Render the log view (LEGACY ANSI rendering).

        Returns
        -------
        str
            Rendered log view as multi-line string

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
        """Render log view using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for log views, supporting:
        - Log level detection and theme-based coloring (ERROR, WARNING, INFO, DEBUG, TRACE)
        - Optional line numbers with theme styling
        - Soft-wrap for long lines
        - Auto-scroll behavior
        - Scrolling with scrollbar
        - Borders with titles and focus styling
        - Theme-based styling throughout

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'logview': Base logview style (for lines without detected log level)
        - 'logview:focus': When logview has focus
        - 'logview.error': For ERROR/FATAL/CRITICAL log lines
        - 'logview.warning': For WARNING/WARN log lines
        - 'logview.info': For INFO log lines
        - 'logview.debug': For DEBUG log lines
        - 'logview.trace': For TRACE log lines
        - 'logview.line_number': For line number column
        - 'logview.border': For border characters
        - 'logview.border:focus': For border when focused
        """
        # Resolve border style based on focus
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(
                self, "logview.border:focus"
            )
        else:
            border_style = ctx.style_resolver.resolve_style(self, "logview.border")

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
        """Render logview with border using cells.

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
        """Render logview content using cells.

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
        from wijjit.terminal.cell import Cell

        # Get base style for padding (to properly reset dim/other attributes)
        base_style = ctx.style_resolver.resolve_style(self, "logview")
        base_attrs = base_style.to_cell_attrs()

        # Get line number style
        line_num_style = ctx.style_resolver.resolve_style(self, "logview.line_number")
        line_num_attrs = line_num_style.to_cell_attrs()

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

        # Calculate line number column width if needed
        line_num_width = 0
        if self.show_line_numbers:
            max_line_num = self.line_number_start + len(self.lines) - 1
            line_num_width = len(str(max_line_num)) + 2  # +2 for space and separator

        # Render visible log lines
        current_y = start_y
        rendered_line_idx = visible_start

        while current_y < start_y + content_height and rendered_line_idx < visible_end:
            if rendered_line_idx >= len(self.rendered_lines):
                # Pad with empty lines
                for x in range(content_width):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + current_y,
                        Cell(char=" "),
                    )
                current_y += 1
                rendered_line_idx += 1
                continue

            rendered_line = self.rendered_lines[rendered_line_idx]

            # Strip ANSI from rendered line (which has old ANSI coloring)
            from wijjit.terminal.ansi import strip_ansi

            clean_line = strip_ansi(rendered_line)

            # Determine which original line this corresponds to
            # For non-wrapped content, this is straightforward
            # For wrapped content, we need to track which original line we're on
            # For simplicity, we'll detect log level from the rendered line itself
            style_class = self._get_log_level_style_class(clean_line)
            line_style = ctx.style_resolver.resolve_style(self, style_class)
            line_attrs = line_style.to_cell_attrs()

            # Render the line content
            x_offset = 0

            # If line numbers are shown and this line has a line number
            # (check if it starts with digits)
            if self.show_line_numbers:
                # Extract line number from the rendered line if present
                # The rendered_lines already have line numbers added by _render_content
                # We need to separate the line number part from content
                # This is a bit tricky - let's render it directly
                line_num_part = (
                    clean_line[:line_num_width]
                    if len(clean_line) >= line_num_width
                    else clean_line.ljust(line_num_width)
                )
                content_part = (
                    clean_line[line_num_width:]
                    if len(clean_line) > line_num_width
                    else ""
                )

                # Write line number
                for i, char in enumerate(line_num_part[:line_num_width]):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + i,
                        ctx.bounds.y + current_y,
                        Cell(char=char, **line_num_attrs),
                    )
                x_offset = line_num_width

                # Write content
                content_width_remaining = content_width - line_num_width
                for i, char in enumerate(content_part[:content_width_remaining]):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x_offset + i,
                        ctx.bounds.y + current_y,
                        Cell(char=char, **line_attrs),
                    )

                # Pad remaining (use base style to properly reset dim/other attributes)
                for x in range(
                    x_offset + len(content_part[:content_width_remaining]),
                    content_width,
                ):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + current_y,
                        Cell(char=" ", **base_attrs),
                    )
            else:
                # No line numbers - render full line
                for i, char in enumerate(clean_line[:content_width]):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + i,
                        ctx.bounds.y + current_y,
                        Cell(char=char, **line_attrs),
                    )

                # Pad remaining width (use base style to properly reset dim/other attributes)
                for x in range(len(clean_line[:content_width]), content_width):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + current_y,
                        Cell(char=" ", **base_attrs),
                    )

            # Add scrollbar character if needed
            if needs_scrollbar:
                scrollbar_idx = current_y - start_y
                if scrollbar_idx < len(scrollbar_chars):
                    # Resolve scrollbar style (use border style)
                    if self.focused:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "logview.border:focus"
                        )
                    else:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "logview.border"
                        )
                    scrollbar_attrs = scrollbar_style.to_cell_attrs()

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
                            self, "logview.border:focus"
                        )
                    else:
                        scrollbar_style = ctx.style_resolver.resolve_style(
                            self, "logview.border"
                        )
                    scrollbar_attrs = scrollbar_style.to_cell_attrs()

                    ctx.buffer.set_cell(
                        ctx.bounds.x + content_width,
                        ctx.bounds.y + current_y,
                        Cell(char=scrollbar_chars[scrollbar_idx], **scrollbar_attrs),
                    )

            current_y += 1
