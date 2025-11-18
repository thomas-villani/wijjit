"""Frame rendering with borders for terminal UI.

This module provides utilities for rendering frames (boxes) with various
border styles, titles, and content. Supports scrolling for content that
exceeds the frame height.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

from wijjit.elements.base import ScrollableElement
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.terminal.ansi import clip_to_width, visible_length, wrap_text
from wijjit.terminal.input import Key
from wijjit.terminal.mouse import MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


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
    overflow_x : {"clip", "visible", "wrap"}, optional
        Horizontal overflow behavior (default: "clip")
        - "clip": Truncate text at frame width (default behavior)
        - "visible": Allow text to extend beyond frame borders
        - "wrap": Wrap text to multiple lines at word boundaries
    """

    border: BorderStyle = BorderStyle.SINGLE
    title: str | None = None
    padding: tuple[int, int, int, int] = (0, 1, 0, 1)  # top, right, bottom, left
    content_align_h: Literal["left", "center", "right", "stretch"] = "stretch"
    content_align_v: Literal["top", "middle", "bottom", "stretch"] = "stretch"
    scrollable: bool = False
    show_scrollbar: bool = True
    overflow_y: Literal["clip", "scroll", "auto"] = "auto"
    overflow_x: Literal["clip", "visible", "wrap"] = "clip"


class Frame(ScrollableElement):
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

    def __init__(
        self,
        width: int,
        height: int,
        style: FrameStyle | None = None,
        id: str | None = None,
    ):
        super().__init__(id)
        self.width = max(3, width)  # Minimum width for borders
        self.height = max(3, height)  # Minimum height for borders
        self.style = style or FrameStyle()
        self.content: list[str] = []
        self.scroll_manager: ScrollManager | None = None
        self._content_height: int = 0
        self._needs_scroll: bool = False
        # Note: bounds, id, scroll_state_key inherited from ScrollableElement

        # Track child elements for scrolling
        self._child_elements: list[tuple[object, int, int]] = (
            []
        )  # (element, y_offset, height)
        self._has_children: bool = False

        # Frame is only focusable if it's scrollable (needs to handle UP/DOWN for scrolling)
        self.focusable: bool = self.style.scrollable
        # Note: focused, hovered inherited from Element

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

        If overflow_x="wrap", content lines will be wrapped to fit the
        frame's inner width, potentially expanding the number of content lines.
        """
        # Split text into lines
        lines = text.split("\n") if text else []

        # If overflow_x is "wrap", pre-wrap all lines to inner width
        if self.style.overflow_x == "wrap":
            padding_top, padding_right, padding_bottom, padding_left = (
                self.style.padding
            )
            inner_width = self.width - 2 - padding_left - padding_right

            # Wrap each line and flatten into content array
            wrapped_lines = []
            for line in lines:
                segments = wrap_text(line, inner_width)
                wrapped_lines.extend(segments)

            self.content = wrapped_lines
        else:
            # No wrapping - use lines as-is
            self.content = lines

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

            # Update focusable status - frame should be focusable if it needs scrolling
            self.focusable = self._needs_scroll

            # Restore pending scroll position if available
            if hasattr(self, "_pending_scroll_restore"):
                self.restore_scroll_position(self._pending_scroll_restore)
                delattr(self, "_pending_scroll_restore")

    def set_child_content_height(self, child_height: int) -> None:
        """Set the total height of child elements for scrolling calculations.

        Parameters
        ----------
        child_height : int
            Total height of all child elements combined

        Notes
        -----
        This method is called by the layout engine when a frame contains
        child elements instead of text content. It sets up the ScrollManager
        to enable scrolling of the composite child content.
        """
        self._has_children = True
        self._content_height = child_height

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

            # Update focusable status - frame should be focusable if it needs scrolling
            self.focusable = self._needs_scroll

            # Restore pending scroll position if available
            if hasattr(self, "_pending_scroll_restore"):
                self.restore_scroll_position(self._pending_scroll_restore)
                delattr(self, "_pending_scroll_restore")

    def get_scroll_offset(self) -> int:
        """Get the current scroll offset for rendering children.

        Returns
        -------
        int
            Number of lines scrolled from the top (0 if not scrolling)

        Notes
        -----
        This is used by the renderer to adjust child element positions
        when the frame is scrollable and has been scrolled.
        """
        if self.scroll_manager and self._needs_scroll:
            return self.scroll_manager.state.scroll_position
        return 0

    @property
    def scroll_position(self) -> int:
        """Get the current scroll position (required by ScrollableElement ABC).

        Returns
        -------
        int
            Current scroll offset (0-based)
        """
        if self.scroll_manager:
            return self.scroll_manager.state.scroll_position
        return 0

    def can_scroll(self, direction: int) -> bool:
        """Check if the frame can scroll in the given direction.

        Parameters
        ----------
        direction : int
            Scroll direction: negative for up, positive for down

        Returns
        -------
        bool
            True if scrolling in the given direction is possible
        """
        if not self.style.scrollable or not self.scroll_manager:
            return False

        if direction < 0:  # Up
            return self.scroll_manager.state.scroll_position > 0
        else:  # Down
            return self.scroll_manager.state.is_scrollable and (
                self.scroll_manager.state.scroll_position
                < self.scroll_manager.state.max_scroll_position
            )

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

        When a scrollable frame has children, it renders borders and scrollbar,
        but children render themselves at their scrolled positions.
        """
        # If frame has children (regardless of scrollable), don't render anything
        # Borders are handled by _render_frames(), children render themselves
        # For scrollable frames, the scrollbar is also handled by _render_frames()
        if self._has_children and not self.content:
            return ""

        # If scrollable with text content, use scrollable rendering
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

    def _render_scrollable_container(self) -> str:
        """Render frame borders and scrollbar for container with children.

        Returns
        -------
        str
            Rendered frame borders with scrollbar

        Notes
        -----
        This method is used for scrollable frames that contain child elements
        (not text content). It renders the frame borders and scrollbar, but
        children render themselves at their scrolled positions.
        """
        if not self.scroll_manager:
            return ""

        lines = []
        chars = BORDER_CHARS[self.style.border]

        # Calculate inner dimensions
        padding_top, padding_right, padding_bottom, padding_left = self.style.padding

        # Reserve space for scrollbar if showing
        scrollbar_width = 1 if self.style.show_scrollbar else 0
        inner_width = self.width - 2 - padding_left - padding_right - scrollbar_width
        inner_height = self.height - 2 - padding_top - padding_bottom

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

        # Render empty content area with scrollbar
        # Children will render themselves in this space
        for i in range(inner_height):
            # Get scrollbar character for this line
            scrollbar_char = scrollbar_chars[i] if i < len(scrollbar_chars) else " "

            # Render empty line with scrollbar
            lines.append(
                self._render_scrollable_content_line(
                    "",  # No content - children render separately
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

        Notes
        -----
        Respects the overflow_x setting:
        - "clip": Truncates text at inner_width (default)
        - "visible": Allows text to extend beyond borders
        - "wrap": Text should already be wrapped via set_content()
        """
        # Get visible content length
        content_len = visible_length(content)

        # Handle overflow_x mode
        if self.style.overflow_x == "visible":
            # Allow content to extend beyond borders - don't clip
            # Just pad if shorter than inner_width
            if content_len < inner_width:
                content = content + " " * (inner_width - content_len)
        elif content_len > inner_width:
            # For "clip" and "wrap" modes, clip content that exceeds width
            # (wrap mode should have pre-wrapped in set_content, but clip as safety)
            content = clip_to_width(content, inner_width, ellipsis="")
            content_len = inner_width

        # Apply horizontal alignment (only if content fits or we're in clip/wrap mode)
        if self.style.overflow_x != "visible" or content_len <= inner_width:
            if self.style.content_align_h == "stretch" or content_len == inner_width:
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

        Notes
        -----
        Respects the overflow_x setting:
        - "clip": Truncates text at inner_width (default)
        - "visible": Allows text to extend beyond borders
        - "wrap": Text should already be wrapped via set_content()
        """
        # Get visible content length
        content_len = visible_length(content)

        # Handle overflow_x mode
        if self.style.overflow_x == "visible":
            # Allow content to extend beyond borders - don't clip
            # Just pad if shorter than inner_width
            if content_len < inner_width:
                content = content + " " * (inner_width - content_len)
        elif content_len > inner_width:
            # For "clip" and "wrap" modes, clip content that exceeds width
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
            if self.on_scroll:
                self.on_scroll(self.scroll_position)
            return True
        elif key_name == "down":
            self.scroll_manager.scroll_by(1)
            if self.on_scroll:
                self.on_scroll(self.scroll_position)
            return True
        elif key_name == "pageup":
            self.scroll_manager.page_up()
            if self.on_scroll:
                self.on_scroll(self.scroll_position)
            return True
        elif key_name == "pagedown":
            self.scroll_manager.page_down()
            if self.on_scroll:
                self.on_scroll(self.scroll_position)
            return True
        elif key_name == "home":
            self.scroll_manager.scroll_to_top()
            if self.on_scroll:
                self.on_scroll(self.scroll_position)
            return True
        elif key_name == "end":
            self.scroll_manager.scroll_to_bottom()
            if self.on_scroll:
                self.on_scroll(self.scroll_position)
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
        if self.on_scroll:
            self.on_scroll(self.scroll_position)
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
            from wijjit.terminal.mouse import MouseButton

            if event.button == MouseButton.SCROLL_UP:
                return self.handle_scroll(-1)
            elif event.button == MouseButton.SCROLL_DOWN:
                return self.handle_scroll(1)

        return False

    def on_focus(self) -> None:
        """Called when frame gains focus.

        Notes
        -----
        Sets the focused flag to True. Used by focus manager.
        """
        self.focused = True

    def on_blur(self) -> None:
        """Called when frame loses focus.

        Notes
        -----
        Sets the focused flag to False. Used by focus manager.
        """
        self.focused = False

    def on_hover_enter(self) -> None:
        """Called when mouse enters frame.

        Notes
        -----
        Sets the hovered flag to True. Used by hover manager.
        """
        self.hovered = True

    def on_hover_exit(self) -> None:
        """Called when mouse exits frame.

        Notes
        -----
        Sets the hovered flag to False. Used by hover manager.
        """
        self.hovered = False

    def restore_scroll_position(self, position: int) -> None:
        """Restore scroll position from saved state.

        Parameters
        ----------
        position : int
            Scroll position to restore

        Notes
        -----
        This method is called by the framework to restore scroll state
        when the element is recreated.
        """
        if self.scroll_manager:
            self.scroll_manager.scroll_to(position)

    def render_to(self, ctx: "PaintContext") -> None:
        """Render frame using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for frames, supporting:
        - Multiple border styles (single, double, rounded)
        - Optional titles in borders
        - Padding and content alignment
        - Scrolling with scrollbar rendering
        - Theme-based styling

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'frame': Base frame style for content
        - 'frame:focus': When frame has focus
        - 'frame.border': For border characters
        - 'frame.title': For title text in border
        """

        # Resolve styles based on state
        if self.focused:
            content_style = ctx.style_resolver.resolve_style(self, "frame:focus")
            border_style = ctx.style_resolver.resolve_style(self, "frame.border:focus")
        else:
            content_style = ctx.style_resolver.resolve_style(self, "frame")
            border_style = ctx.style_resolver.resolve_style(self, "frame.border")

        # Get border characters
        chars = BORDER_CHARS[self.style.border]
        border_attrs = border_style.to_cell_attrs()
        content_attrs = content_style.to_cell_attrs()

        # Calculate inner dimensions
        padding_top, padding_right, padding_bottom, padding_left = self.style.padding
        scrollbar_width = 1 if (self.style.show_scrollbar and self._needs_scroll) else 0
        inner_width = self.width - 2 - padding_left - padding_right - scrollbar_width
        inner_height = self.height - 2 - padding_top - padding_bottom

        # Render top border with optional title
        self._render_to_top_border(ctx, chars, border_attrs)

        # Render content area
        current_y = 1  # Start after top border

        # Top padding
        for _ in range(padding_top):
            self._render_to_empty_line(
                ctx,
                current_y,
                chars,
                border_attrs,
                padding_left,
                inner_width,
                padding_right,
                scrollbar_width,
            )
            current_y += 1

        # Render content based on mode
        if self._has_children and not self.content:
            # Scrollable frame with children - render empty content area with scrollbar
            if self.style.scrollable and self._needs_scroll and self.scroll_manager:
                scrollbar_chars = render_vertical_scrollbar(
                    self.scroll_manager.state, inner_height, style="simple"
                )
                for i in range(inner_height):
                    scrollbar_char = (
                        scrollbar_chars[i] if i < len(scrollbar_chars) else " "
                    )
                    self._render_to_content_line(
                        ctx,
                        current_y,
                        "",
                        chars,
                        border_attrs,
                        content_attrs,
                        padding_left,
                        inner_width,
                        padding_right,
                        scrollbar_char if self.style.show_scrollbar else None,
                    )
                    current_y += 1
            else:
                # Non-scrollable or no scrolling needed - render empty
                for _ in range(inner_height):
                    self._render_to_empty_line(
                        ctx,
                        current_y,
                        chars,
                        border_attrs,
                        padding_left,
                        inner_width,
                        padding_right,
                        scrollbar_width,
                    )
                    current_y += 1
        elif self.style.scrollable and self._needs_scroll and self.scroll_manager:
            # Scrollable frame with text content
            start_line, end_line = self.scroll_manager.get_visible_range()
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, inner_height, style="simple"
            )

            for i in range(inner_height):
                content_idx = start_line + i
                line = ""
                if content_idx < end_line and content_idx < len(self.content):
                    line = self.content[content_idx]

                scrollbar_char = scrollbar_chars[i] if i < len(scrollbar_chars) else " "
                self._render_to_content_line(
                    ctx,
                    current_y,
                    line,
                    chars,
                    border_attrs,
                    content_attrs,
                    padding_left,
                    inner_width,
                    padding_right,
                    scrollbar_char if self.style.show_scrollbar else None,
                )
                current_y += 1
        else:
            # Static (non-scrollable) frame with text content
            # Handle vertical alignment
            num_content_lines = len(self.content)
            if (
                self.style.content_align_v != "stretch"
                and num_content_lines < inner_height
            ):
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
                top_empty = 0
                bottom_empty = max(0, inner_height - num_content_lines)

            # Top empty lines for alignment
            for _ in range(top_empty):
                self._render_to_empty_line(
                    ctx,
                    current_y,
                    chars,
                    border_attrs,
                    padding_left,
                    inner_width,
                    padding_right,
                    scrollbar_width,
                )
                current_y += 1

            # Content lines
            for i in range(min(num_content_lines, inner_height)):
                line = self.content[i]
                self._render_to_content_line(
                    ctx,
                    current_y,
                    line,
                    chars,
                    border_attrs,
                    content_attrs,
                    padding_left,
                    inner_width,
                    padding_right,
                    None,
                )
                current_y += 1

            # Bottom empty lines
            for _ in range(bottom_empty):
                self._render_to_empty_line(
                    ctx,
                    current_y,
                    chars,
                    border_attrs,
                    padding_left,
                    inner_width,
                    padding_right,
                    scrollbar_width,
                )
                current_y += 1

        # Bottom padding
        for _ in range(padding_bottom):
            self._render_to_empty_line(
                ctx,
                current_y,
                chars,
                border_attrs,
                padding_left,
                inner_width,
                padding_right,
                scrollbar_width,
            )
            current_y += 1

        # Render bottom border
        self._render_to_bottom_border(ctx, current_y, chars, border_attrs)

    def _render_to_top_border(
        self, ctx: "PaintContext", chars: dict, border_attrs: dict
    ) -> None:
        """Render top border with optional title using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        """
        from wijjit.terminal.cell import Cell

        if self.style.title:
            # Border with title
            title_text = f" {self.style.title} "
            title_len = len(title_text)
            remaining = self.width - 2 - title_len

            if remaining >= 0:
                # Write top-left corner
                ctx.buffer.set_cell(
                    ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
                )

                # Write left horizontal line (1 char)
                ctx.buffer.set_cell(
                    ctx.bounds.x + 1,
                    ctx.bounds.y,
                    Cell(char=chars["h"], **border_attrs),
                )

                # Write title
                for i, char in enumerate(title_text):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 2 + i,
                        ctx.bounds.y,
                        Cell(char=char, **border_attrs),
                    )

                # Write right horizontal line
                right_len = remaining - 1
                for i in range(right_len):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 2 + title_len + i,
                        ctx.bounds.y,
                        Cell(char=chars["h"], **border_attrs),
                    )

                # Write top-right corner
                ctx.buffer.set_cell(
                    ctx.bounds.x + self.width - 1,
                    ctx.bounds.y,
                    Cell(char=chars["tr"], **border_attrs),
                )
            else:
                # Title too long, truncate and show without extra lines
                title_text = title_text[: self.width - 2]
                ctx.buffer.set_cell(
                    ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
                )
                for i, char in enumerate(title_text):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + 1 + i,
                        ctx.bounds.y,
                        Cell(char=char, **border_attrs),
                    )
                ctx.buffer.set_cell(
                    ctx.bounds.x + self.width - 1,
                    ctx.bounds.y,
                    Cell(char=chars["tr"], **border_attrs),
                )
        else:
            # Border without title
            # Top-left corner
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
            )

            # Horizontal line
            for i in range(1, self.width - 1):
                ctx.buffer.set_cell(
                    ctx.bounds.x + i,
                    ctx.bounds.y,
                    Cell(char=chars["h"], **border_attrs),
                )

            # Top-right corner
            ctx.buffer.set_cell(
                ctx.bounds.x + self.width - 1,
                ctx.bounds.y,
                Cell(char=chars["tr"], **border_attrs),
            )

    def _render_to_bottom_border(
        self, ctx: "PaintContext", y: int, chars: dict, border_attrs: dict
    ) -> None:
        """Render bottom border using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        y : int
            Y position relative to bounds
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        """
        from wijjit.terminal.cell import Cell

        # Bottom-left corner
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["bl"], **border_attrs)
        )

        # Horizontal line
        for i in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + i,
                ctx.bounds.y + y,
                Cell(char=chars["h"], **border_attrs),
            )

        # Bottom-right corner
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + y,
            Cell(char=chars["br"], **border_attrs),
        )

    def _render_to_empty_line(
        self,
        ctx: "PaintContext",
        y: int,
        chars: dict,
        border_attrs: dict,
        padding_left: int,
        inner_width: int,
        padding_right: int,
        scrollbar_width: int,
    ) -> None:
        """Render empty line (padding) using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        y : int
            Y position relative to bounds
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        padding_left : int
            Left padding
        inner_width : int
            Inner content width
        padding_right : int
            Right padding
        scrollbar_width : int
            Scrollbar width
        """
        from wijjit.terminal.cell import Cell

        # Left border
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["v"], **border_attrs)
        )

        # Empty content (padding + inner + padding + scrollbar)
        total_inner = padding_left + inner_width + padding_right + scrollbar_width
        for i in range(total_inner):
            ctx.buffer.set_cell(
                ctx.bounds.x + 1 + i, ctx.bounds.y + y, Cell(char=" ", **border_attrs)
            )

        # Right border
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + y,
            Cell(char=chars["v"], **border_attrs),
        )

    def _render_to_content_line(
        self,
        ctx: "PaintContext",
        y: int,
        content: str,
        chars: dict,
        border_attrs: dict,
        content_attrs: dict,
        padding_left: int,
        inner_width: int,
        padding_right: int,
        scrollbar_char: str | None = None,
    ) -> None:
        """Render content line using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        y : int
            Y position relative to bounds
        content : str
            Content text
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        content_attrs : dict
            Content cell attributes
        padding_left : int
            Left padding
        inner_width : int
            Inner content width
        padding_right : int
            Right padding
        scrollbar_char : str, optional
            Scrollbar character to append
        """
        from wijjit.terminal.ansi import clip_to_width, visible_length
        from wijjit.terminal.cell import Cell

        # Left border
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["v"], **border_attrs)
        )

        # Left padding
        for i in range(padding_left):
            ctx.buffer.set_cell(
                ctx.bounds.x + 1 + i, ctx.bounds.y + y, Cell(char=" ", **content_attrs)
            )

        # Content with alignment
        content_len = visible_length(content)

        # Handle overflow_x mode
        if self.style.overflow_x == "visible":
            # Allow content to extend - don't clip
            if content_len < inner_width:
                content = content + " " * (inner_width - content_len)
        elif content_len > inner_width:
            # Clip content
            content = clip_to_width(content, inner_width, ellipsis="")
            content_len = inner_width

        # Apply horizontal alignment
        if self.style.overflow_x != "visible" or content_len <= inner_width:
            if self.style.content_align_h == "stretch" or content_len == inner_width:
                if content_len < inner_width:
                    content = content + " " * (inner_width - content_len)
            elif content_len < inner_width:
                empty_space = inner_width - content_len
                if self.style.content_align_h == "center":
                    left_space = empty_space // 2
                    right_space = empty_space - left_space
                    content = " " * left_space + content + " " * right_space
                elif self.style.content_align_h == "right":
                    content = " " * empty_space + content
                else:  # "left"
                    content = content + " " * empty_space

        # Write content (plain text without ANSI codes)
        # Strip any ANSI codes from content before writing
        from wijjit.terminal.ansi import strip_ansi

        clean_content = strip_ansi(content)

        for i, char in enumerate(clean_content[:inner_width]):
            ctx.buffer.set_cell(
                ctx.bounds.x + 1 + padding_left + i,
                ctx.bounds.y + y,
                Cell(char=char, **content_attrs),
            )

        # Pad remaining content width if needed
        actual_len = len(clean_content[:inner_width])
        for i in range(actual_len, inner_width):
            ctx.buffer.set_cell(
                ctx.bounds.x + 1 + padding_left + i,
                ctx.bounds.y + y,
                Cell(char=" ", **content_attrs),
            )

        # Right padding
        for i in range(padding_right):
            ctx.buffer.set_cell(
                ctx.bounds.x + 1 + padding_left + inner_width + i,
                ctx.bounds.y + y,
                Cell(char=" ", **content_attrs),
            )

        # Scrollbar (if present)
        if scrollbar_char is not None:
            ctx.buffer.set_cell(
                ctx.bounds.x + 1 + padding_left + inner_width + padding_right,
                ctx.bounds.y + y,
                Cell(char=scrollbar_char, **border_attrs),
            )

        # Right border
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + y,
            Cell(char=chars["v"], **border_attrs),
        )
