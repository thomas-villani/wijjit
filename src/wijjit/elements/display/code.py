# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable

from wijjit.elements.base import Element, ElementType
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent


class CodeBlock(Element):
    """Code display element with syntax highlighting via Rich.

    This element renders code with syntax highlighting using Rich's Syntax
    renderer, with support for scrolling, borders, and mouse/keyboard interaction.

    Parameters
    ----------
    id : str, optional
        Element identifier
    code : str, optional
        Code content to display (default: "")
    language : str, optional
        Programming language for syntax highlighting (default: "python")
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 20)
    show_line_numbers : bool, optional
        Whether to show line numbers (default: True)
    line_number_start : int, optional
        Starting line number (default: 1)
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str, optional
        Border style: "single", "double", "rounded", or "none" (default: "single")
    title : str, optional
        Title to display in top border (default: None)
    theme : str, optional
        Syntax highlighting theme (default: "monokai")

    Attributes
    ----------
    code : str
        Code content
    language : str
        Programming language
    width : int
        Display width
    height : int
        Display height
    show_line_numbers : bool
        Whether line numbers are shown
    line_number_start : int
        Starting line number
    show_scrollbar : bool
        Whether scrollbar is visible
    border_style : str
        Border style
    title : str or None
        Border title
    theme : str
        Syntax highlighting theme
    scroll_manager : ScrollManager
        Manages scrolling of content
    rendered_lines : list of str
        Cached rendered content lines
    """

    def __init__(
        self,
        id: str | None = None,
        code: str = "",
        language: str = "python",
        width: int = 60,
        height: int = 20,
        show_line_numbers: bool = True,
        line_number_start: int = 1,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        theme: str = "monokai",
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = True  # Focusable for keyboard scrolling

        # Content and display properties
        self.code = code
        self.language = language
        self.width = width
        self.height = height
        self.show_line_numbers = show_line_numbers
        self.line_number_start = line_number_start
        self.show_scrollbar = show_scrollbar
        self.border_style = border_style
        self.title = title
        self.theme = theme

        # Rendered content cache
        self.rendered_lines: list[str] = []

        # Render initial content
        self._render_content()

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=len(self.rendered_lines),
            viewport_size=self._get_content_height(),
        )

        # Callbacks
        self.on_scroll: Callable[[int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence
        self.scroll_state_key: str | None = None

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
        """Render code with syntax highlighting to ANSI strings using Rich.

        Updates the rendered_lines cache with the current content.
        """
        from io import StringIO

        from rich.console import Console
        from rich.syntax import Syntax

        # Get content width for rendering
        content_width = self._get_content_width()

        # Render code using Rich Syntax
        syntax = Syntax(
            self.code,
            self.language,
            theme=self.theme,
            line_numbers=self.show_line_numbers,
            start_line=self.line_number_start,
            word_wrap=False,
        )

        string_buffer = StringIO()
        console = Console(
            file=string_buffer,
            width=content_width,
            legacy_windows=False,
            force_terminal=True,
        )
        console.print(syntax)
        output = string_buffer.getvalue()

        # Split into lines
        self.rendered_lines = output.rstrip("\n").split("\n")

        # Ensure at least one line
        if not self.rendered_lines:
            self.rendered_lines = [""]

    def set_code(self, code: str, language: str | None = None) -> None:
        """Update code content and re-render.

        Parameters
        ----------
        code : str
            New code content
        language : str, optional
            New programming language (if None, keeps current language)
        """
        self.code = code
        if language is not None:
            self.language = language
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
        """Render the code block.

        Returns
        -------
        str
            Rendered code block as multi-line string
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
