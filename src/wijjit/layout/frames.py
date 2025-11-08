"""Frame rendering with borders for terminal UI.

This module provides utilities for rendering frames (boxes) with various
border styles, titles, and content.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Literal

from ..terminal.ansi import visible_length, clip_to_width


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
    """

    border: BorderStyle = BorderStyle.SINGLE
    title: Optional[str] = None
    padding: Tuple[int, int, int, int] = (0, 1, 0, 1)  # top, right, bottom, left
    content_align_h: Literal["left", "center", "right", "stretch"] = "stretch"
    content_align_v: Literal["top", "middle", "bottom", "stretch"] = "stretch"


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

    def __init__(self, width: int, height: int, style: Optional[FrameStyle] = None):
        self.width = max(3, width)  # Minimum width for borders
        self.height = max(3, height)  # Minimum height for borders
        self.style = style or FrameStyle()
        self.content: List[str] = []

    def set_content(self, text: str) -> None:
        """Set the frame content from a string.

        Parameters
        ----------
        text : str
            Content text (may contain newlines)
        """
        self.content = text.split("\n") if text else []

    def render(self) -> str:
        """Render the frame as a string.

        Returns
        -------
        str
            Rendered frame with borders and content
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
        self, chars: dict, padding_left: int, inner_width: int, padding_right: int
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

        Returns
        -------
        str
            Empty line with borders
        """
        total_inner = padding_left + inner_width + padding_right
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
