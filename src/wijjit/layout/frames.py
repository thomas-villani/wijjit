"""Frame rendering with borders for terminal UI.

This module provides utilities for rendering frames (boxes) with various
border styles, titles, and content. Supports scrolling for content that
exceeds the frame height.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from ..terminal.ansi import clip_to_width, visible_length
from ..terminal.input import Key
from ..terminal.mouse import MouseEvent, MouseEventType
from .scroll import ScrollManager, render_vertical_scrollbar


class BorderStyle(Enum):
    """Border style for frames."""

    SINGLE = "single"
    DOUBLE = "double"
    ROUNDED = "rounded"


# Border character sets for each style
BORDER_CHARS = {
    BorderStyle.SINGLE: {
        "tl": "┌",  # top-left
        "tr": "┐",  # top-right
        "bl": "└",  # bottom-left
        "br": "┘",  # bottom-right
        "h": "─",  # horizontal
        "v": "│",  # vertical
    },
    BorderStyle.DOUBLE: {
        "tl": "╔",
        "tr": "╗",
        "bl": "╚",
        "br": "╝",
        "h": "═",
        "v": "║",
    },
    BorderStyle.ROUNDED: {
        "tl": "╭",
        "tr": "╮",
        "bl": "╰",
        "br": "╯",
        "h": "─",
        "v": "│",
    },
}


@dataclass
class FrameStyle:
    """Style configuration for a frame.

    Parameters
    ----------
    border : BorderStyle
        Border style to use
    title : str, optional
        Frame title
    padding : tuple, optional
        Padding (top, right, bottom, left)
    content_align_h : {"left", "center", "right", "stretch"}, optional
        Horizontal alignment of content within frame (default: "stretch")
    content_align_v : {"top", "middle", "bottom", "stretch"}, optional
        Vertical alignment of content within frame (default: "stretch")
    scrollable : bool, optional
        Enable scrolling for content that exceeds frame height (default: False)
    show_scrollbar : bool, optional
        Show scrollbar when scrollable (default: True)
    overflow_y : {"clip", "scroll", "auto"}, optional
        Vertical overflow behavior (default: "auto")
        - "clip": Clip content beyond viewport
        - "scroll": Always show scrollbar
        - "auto": Show scrollbar only when needed
    """

    border: BorderStyle = BorderStyle.SINGLE
    title: str | None = None
    padding: tuple[int, int, int, int] = (0, 1, 0, 1)  # top, right, bottom, left
    content_align_h: Literal["left", "center", "right", "stretch"] = "stretch"
    content_align_v: Literal["top", "middle", "bottom", "stretch"] = "stretch"
    scrollable: bool = False
    show_scrollbar: bool = True
    overflow_y: Literal["clip", "scroll", "auto"] = "auto"


class Frame:
    """Renders a frame with borders and content.

    Parameters
    ----------
    width : int
        Total frame width (including borders)
    height : int
        Total frame height (including borders)
    style : FrameStyle, optional
        Frame style configuration

    Attributes
    ----------
    width : int
        Total frame width
    height : int
        Total frame height
    style : FrameStyle
        Frame style
    content : list
        Content lines
    """

    def __init__(self, width: int, height: int, style: FrameStyle | None = None):
        self.width = max(3, width)  # Minimum width for borders
        self.height = max(3, height)  # Minimum height for borders
        self.style = style or FrameStyle()
        self.content: list[str] = []
        self.scroll_manager: ScrollManager | None = None
        self._content_height: int = 0
        self._needs_scroll: bool = False

    def set_content(self, text: str) -> None:
        """Set the frame content from a string.

        Parameters
        ----------
        text : str
            Content text (may contain newlines)

        Notes
        -----
        If the frame is scrollable, this method will create or update
        the ScrollManager based on content height and viewport size.
        """
        self.content = text.split("\n") if text else []
        self._content_height = len(self.content)

        # Create or update scroll manager if frame is scrollable
        if self.style.scrollable:
            # Calculate viewport height (inner height after borders and padding)
            padding_top, padding_right, padding_bottom, padding_left = (
                self.style.padding
            )
            viewport_height = self.height - 2 - padding_top - padding_bottom

            if self.scroll_manager is None:
                # Create new scroll manager
                self.scroll_manager = ScrollManager(
                    content_size=self._content_height,
                    viewport_size=viewport_height,
                    initial_position=0,
                )
            else:
                # Update existing scroll manager
                self.scroll_manager.update_content_size(self._content_height)
                self.scroll_manager.update_viewport_size(viewport_height)

            # Determine if scrolling is needed
            self._needs_scroll = self.scroll_manager.state.is_scrollable

    def render(self) -> str:
        """Render the frame as a string.

        Returns
        -------
        str
            Rendered frame with borders and content

        Notes
        -----
        If the frame is scrollable and content exceeds viewport, only
        the visible portion of content (based on scroll position) will
        be rendered, along with a scrollbar if enabled.
        """
        # If scrollable, use scrollable rendering
        if self.style.scrollable and self._needs_scroll:
            return self._render_scrollable()
        else:
            return self._render_static()

    def _render_static(self) -> str:
        """Render frame without scrolling (original behavior).

        Returns
        -------
        str
            Rendered frame
        """
        lines = []
        chars = BORDER_CHARS[self.style.border]

        # Calculate inner dimensions
        padding_top, padding_right, padding_bottom, padding_left = self.style.padding
        inner_width = (
            self.width - 2 - padding_left - padding_right
        )  # Subtract borders and padding
        inner_height = (
            self.height - 2 - padding_top - padding_bottom
        )  # Subtract borders and padding

        # Top border
        lines.append(self._render_top_border(chars))

        # Top padding
        for _ in range(padding_top):
            lines.append(
                self._render_empty_line(chars, padding_left, inner_width, padding_right)
            )

        # Calculate vertical alignment
        num_content_lines = len(self.content)
        if self.style.content_align_v != "stretch" and num_content_lines < inner_height:
            empty_space = inner_height - num_content_lines
            if self.style.content_align_v == "middle":
                top_empty = empty_space // 2
                bottom_empty = empty_space - top_empty
            elif self.style.content_align_v == "bottom":
                top_empty = empty_space
                bottom_empty = 0
            else:  # "top"
                top_empty = 0
                bottom_empty = empty_space
        else:
            # "stretch": fill remaining space after content
            top_empty = 0
            bottom_empty = max(0, inner_height - num_content_lines)

        # Top empty lines for vertical alignment
        for _ in range(top_empty):
            lines.append(
                self._render_empty_line(chars, padding_left, inner_width, padding_right)
            )

        # Content lines
        for i in range(min(num_content_lines, inner_height)):
            line = self.content[i]
            lines.append(
                self._render_content_line(
                    line, chars, padding_left, inner_width, padding_right
                )
            )

        # Bottom empty lines (either for alignment or to fill remaining space in stretch mode)
        for _ in range(bottom_empty):
            lines.append(
                self._render_empty_line(chars, padding_left, inner_width, padding_right)
            )

        # Bottom padding
        for _ in range(padding_bottom):
            lines.append(
                self._render_empty_line(chars, padding_left, inner_width, padding_right)
            )

        # Bottom border
        lines.append(self._render_bottom_border(chars))

        return "\n".join(lines)

    def _render_scrollable(self) -> str:
        """Render frame with scrolling support.

        Returns
        -------
        str
            Rendered frame with scrollbar
        """
        if not self.scroll_manager:
            return self._render_static()

        lines = []
        chars = BORDER_CHARS[self.style.border]

        # Calculate inner dimensions
        padding_top, padding_right, padding_bottom, padding_left = self.style.padding

        # Reserve space for scrollbar if showing
        scrollbar_width = 1 if self.style.show_scrollbar else 0
        inner_width = self.width - 2 - padding_left - padding_right - scrollbar_width
        inner_height = self.height - 2 - padding_top - padding_bottom

        # Get visible content range from scroll manager
        start_line, end_line = self.scroll_manager.get_visible_range()

        # Generate scrollbar
        scrollbar_chars = []
        if self.style.show_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, inner_height, style="simple"
            )

        # Top border
        lines.append(self._render_top_border(chars))

        # Top padding
        for _ in range(padding_top):
            lines.append(
                self._render_empty_line(
                    chars, padding_left, inner_width, padding_right, scrollbar_width
                )
            )

        # Render visible content lines
        for i in range(inner_height):
            content_idx = start_line + i
            if content_idx < end_line and content_idx < len(self.content):
                line = self.content[content_idx]
            else:
                line = ""

            # Get scrollbar character for this line
            scrollbar_char = scrollbar_chars[i] if i < len(scrollbar_chars) else " "

            lines.append(
                self._render_scrollable_content_line(
                    line,
                    chars,
                    padding_left,
                    inner_width,
                    padding_right,
                    scrollbar_char if self.style.show_scrollbar else None,
                )
            )

        # Bottom padding
        for _ in range(padding_bottom):
            lines.append(
                self._render_empty_line(
                    chars, padding_left, inner_width, padding_right, scrollbar_width
                )
            )

        # Bottom border
        lines.append(self._render_bottom_border(chars))

        return "\n".join(lines)

    def _render_top_border(self, chars: dict) -> str:
        """Render the top border with optional title.

        Parameters
        ----------
        chars : dict
            Border characters

        Returns
        -------
        str
            Top border line
        """
        if self.style.title:
            # Title in border
            title_text = f" {self.style.title} "
            title_len = len(title_text)
            remaining = self.width - 2 - title_len

            if remaining >= 0:
                left_len = 1
                right_len = remaining - left_len
                return (
                    chars["tl"]
                    + chars["h"] * left_len
                    + title_text
                    + chars["h"] * right_len
                    + chars["tr"]
                )
            else:
                # Title too long, truncate
                title_text = clip_to_width(title_text, self.width - 2)
                return chars["tl"] + title_text + chars["tr"]
        else:
            # No title
            return chars["tl"] + chars["h"] * (self.width - 2) + chars["tr"]

    def _render_bottom_border(self, chars: dict) -> str:
        """Render the bottom border.

        Parameters
        ----------
        chars : dict
            Border characters

        Returns
        -------
        str
            Bottom border line
        """
        return chars["bl"] + chars["h"] * (self.width - 2) + chars["br"]

    def _render_empty_line(
        self,
        chars: dict,
        padding_left: int,
        inner_width: int,
        padding_right: int,
        scrollbar_width: int = 0,
    ) -> str:
        """Render an empty line (for padding).

        Parameters
        ----------
        chars : dict
            Border characters
        padding_left : int
            Left padding
        inner_width : int
            Inner content width
        padding_right : int
            Right padding
        scrollbar_width : int, optional
            Width reserved for scrollbar (default: 0)

        Returns
        -------
        str
            Empty line with borders
        """
        total_inner = padding_left + inner_width + padding_right + scrollbar_width
        return chars["v"] + " " * total_inner + chars["v"]

    def _render_content_line(
        self,
        content: str,
        chars: dict,
        padding_left: int,
        inner_width: int,
        padding_right: int,
    ) -> str:
        """Render a content line with borders and padding.

        Parameters
        ----------
        content : str
            Content text for this line
        chars : dict
            Border characters
        padding_left : int
            Left padding
        inner_width : int
            Inner content width
        padding_right : int
            Right padding

        Returns
        -------
        str
            Rendered content line
        """
        # Get visible content length
        content_len = visible_length(content)

        # Handle horizontal alignment
        if content_len > inner_width:
            # Content too wide, clip it
            content = clip_to_width(content, inner_width, ellipsis="")
        elif self.style.content_align_h == "stretch" or content_len == inner_width:
            # Stretch to full width or already full width
            if content_len < inner_width:
                content = content + " " * (inner_width - content_len)
        elif content_len < inner_width:
            # Apply alignment
            empty_space = inner_width - content_len
            if self.style.content_align_h == "center":
                left_space = empty_space // 2
                right_space = empty_space - left_space
                content = " " * left_space + content + " " * right_space
            elif self.style.content_align_h == "right":
                content = " " * empty_space + content
            else:  # "left"
                content = content + " " * empty_space

        return (
            chars["v"] + " " * padding_left + content + " " * padding_right + chars["v"]
        )

    def _render_scrollable_content_line(
        self,
        content: str,
        chars: dict,
        padding_left: int,
        inner_width: int,
        padding_right: int,
        scrollbar_char: str | None = None,
    ) -> str:
        """Render a content line with scrollbar in scrollable mode.

        Parameters
        ----------
        content : str
            Content text for this line
        chars : dict
            Border characters
        padding_left : int
            Left padding
        inner_width : int
            Inner content width
        padding_right : int
            Right padding
        scrollbar_char : str, optional
            Scrollbar character to append (default: None for no scrollbar)

        Returns
        -------
        str
            Rendered content line with scrollbar
        """
        # Get visible content length
        content_len = visible_length(content)

        # Clip to width if necessary
        if content_len > inner_width:
            content = clip_to_width(content, inner_width, ellipsis="")
        elif content_len < inner_width:
            # Pad to full width
            content = content + " " * (inner_width - content_len)

        # Build line with optional scrollbar
        line = chars["v"] + " " * padding_left + content + " " * padding_right

        if scrollbar_char is not None:
            line += scrollbar_char

        line += chars["v"]

        return line

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for scrolling.

        Parameters
        ----------
        key : Key
            The key that was pressed

        Returns
        -------
        bool
            True if key was handled (caused scrolling), False otherwise

        Notes
        -----
        Handles the following keys:
        - up/down: Scroll by one line
        - pageup/pagedown: Scroll by one viewport
        - home/end: Scroll to top/bottom
        """
        if not self.style.scrollable or not self.scroll_manager:
            return False

        key_name = key.name.lower()

        if key_name == "up":
            self.scroll_manager.scroll_by(-1)
            return True
        elif key_name == "down":
            self.scroll_manager.scroll_by(1)
            return True
        elif key_name == "pageup":
            self.scroll_manager.page_up()
            return True
        elif key_name == "pagedown":
            self.scroll_manager.page_down()
            return True
        elif key_name == "home":
            self.scroll_manager.scroll_to_top()
            return True
        elif key_name == "end":
            self.scroll_manager.scroll_to_bottom()
            return True

        return False

    def handle_scroll(self, direction: int) -> bool:
        """Handle mouse wheel scrolling.

        Parameters
        ----------
        direction : int
            Scroll direction: -1 for up, 1 for down

        Returns
        -------
        bool
            True if scroll was handled, False otherwise
        """
        if not self.style.scrollable or not self.scroll_manager:
            return False

        # Scroll by 3 lines per wheel notch (common convention)
        self.scroll_manager.scroll_by(direction * 3)
        return True

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse events (primarily scrolling).

        Parameters
        ----------
        event : MouseEvent
            The mouse event

        Returns
        -------
        bool
            True if event was handled, False otherwise
        """
        if not self.style.scrollable:
            return False

        # Handle scroll wheel
        if event.type == MouseEventType.SCROLL:
            from ..terminal.mouse import MouseButton

            if event.button == MouseButton.SCROLL_UP:
                return self.handle_scroll(-1)
            elif event.button == MouseButton.SCROLL_DOWN:
                return self.handle_scroll(1)

        return False
