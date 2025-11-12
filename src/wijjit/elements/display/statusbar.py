"""StatusBar element for displaying fixed bottom status information.

This module provides a status bar element that displays information in a
fixed bar at the bottom of the screen with left, center, and right sections.
"""

from __future__ import annotations

from wijjit.elements.base import Element, ElementType
from wijjit.terminal.ansi import ANSIColor, clip_to_width, colorize, visible_length


class StatusBar(Element):
    """Status bar element for fixed bottom display.

    This element provides a horizontal bar typically displayed at the bottom
    of the screen with three sections: left-aligned, center-aligned, and
    right-aligned content.

    Parameters
    ----------
    id : str, optional
        Element identifier
    left : str, optional
        Left-aligned content (default: "")
    center : str, optional
        Center-aligned content (default: "")
    right : str, optional
        Right-aligned content (default: "")
    bg_color : str, optional
        Background color name (default: None)
    text_color : str, optional
        Text color name (default: None)
    width : int, optional
        Status bar width in columns (default: 80, set to terminal width at render)

    Attributes
    ----------
    left : str
        Left-aligned content
    center : str
        Center-aligned content
    right : str
        Right-aligned content
    bg_color : str or None
        Background color name
    text_color : str or None
        Text color name
    width : int
        Status bar width
    """

    def __init__(
        self,
        id: str | None = None,
        left: str = "",
        center: str = "",
        right: str = "",
        bg_color: str | None = None,
        text_color: str | None = None,
        width: int = 80,
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        self.left = left
        self.center = center
        self.right = right
        self.bg_color = bg_color
        self.text_color = text_color
        self.width = width

        # Template metadata
        self.bind: bool = True

    def _get_bg_color_code(self) -> str | None:
        """Get ANSI background color code.

        Returns
        -------
        str or None
            ANSI background color code
        """
        if not self.bg_color:
            return None

        color_name = self.bg_color.upper()
        return getattr(ANSIColor, f"BG_{color_name}", None)

    def _get_text_color_code(self) -> str | None:
        """Get ANSI text color code.

        Returns
        -------
        str or None
            ANSI text color code
        """
        if not self.text_color:
            return None

        color_name = self.text_color.upper()
        return getattr(ANSIColor, color_name, None)

    def render(self) -> str:
        """Render the status bar.

        Renders a single line with left, center, and right sections properly
        aligned and padded to the full width.

        Returns
        -------
        str
            Rendered status bar as single-line string
        """
        # Use bounds width if available, otherwise use specified width
        bar_width = self.bounds.width if self.bounds else self.width

        # Get visible lengths of each section
        left_len = visible_length(self.left)
        center_len = visible_length(self.center)
        right_len = visible_length(self.right)

        # Calculate available space
        # We need to fit: left + center + right with appropriate spacing
        total_content_len = left_len + center_len + right_len

        if total_content_len > bar_width:
            # Content too long - prioritize sections and clip
            # Priority: left > right > center

            # Reserve space for right section (up to 1/3 of width)
            right_max = min(right_len, bar_width // 3)
            right_section = (
                clip_to_width(self.right, right_max)
                if right_len > right_max
                else self.right
            )
            right_len = visible_length(right_section)

            # Reserve space for left section (up to 1/3 of width)
            remaining = bar_width - right_len
            left_max = min(left_len, remaining // 2)
            left_section = (
                clip_to_width(self.left, left_max) if left_len > left_max else self.left
            )
            left_len = visible_length(left_section)

            # Center gets whatever is left
            remaining = bar_width - left_len - right_len
            center_section = (
                clip_to_width(self.center, remaining)
                if center_len > remaining
                else self.center
            )
            center_len = visible_length(center_section)
        else:
            left_section = self.left
            center_section = self.center
            right_section = self.right

        # Calculate padding
        # Center should be centered in the middle of the bar
        # Left section starts at position 0
        # Right section ends at position bar_width

        # Calculate center position
        center_pos = (bar_width - center_len) // 2

        # Build the status bar line
        # Start with left section
        line = left_section

        # Calculate space between left and center
        space_before_center = center_pos - left_len
        if space_before_center > 0:
            line += " " * space_before_center
        elif space_before_center < 0:
            # Left section overlaps center position, add at least one space
            line += " "
            center_pos = left_len + 1

        # Add center section
        line += center_section

        # Calculate space between center and right
        right_pos = bar_width - right_len
        current_pos = center_pos + center_len
        space_before_right = right_pos - current_pos

        if space_before_right > 0:
            line += " " * space_before_right
        elif space_before_right < 0:
            # Center section overlaps right position, add at least one space
            line += " "

        # Add right section
        line += right_section

        # Pad to full width if needed
        current_len = visible_length(line)
        if current_len < bar_width:
            line += " " * (bar_width - current_len)
        elif current_len > bar_width:
            # Clip to width as a safety measure
            line = clip_to_width(line, bar_width)

        # Apply colors if specified
        if self.bg_color or self.text_color:
            bg_code = self._get_bg_color_code()
            text_code = self._get_text_color_code()

            # Apply text color first, then background
            if text_code:
                line = colorize(line, color=text_code)
            if bg_code:
                line = colorize(line, color=bg_code)

        return line
