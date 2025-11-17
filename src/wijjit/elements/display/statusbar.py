"""StatusBar element for displaying fixed bottom status information.

This module provides a status bar element that displays information in a
fixed bar at the bottom of the screen with left, center, and right sections.
"""

from __future__ import annotations

from wijjit.elements.base import Element, ElementType
from wijjit.terminal.ansi import ANSIColor, clip_to_width, visible_length


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

    def render_to(self, ctx) -> None:
        """Render the status bar using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the new cell-based rendering method that uses theme styles
        instead of hardcoded ANSI colors. It properly aligns left, center,
        and right sections with intelligent space distribution.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'statusbar': Base status bar style
        - 'statusbar.left': Left section style
        - 'statusbar.center': Center section style
        - 'statusbar.right': Right section style
        """
        from wijjit.styling.style import Style

        bar_width = ctx.bounds.width

        # Resolve styles from theme
        left_style = ctx.style_resolver.resolve_style(self, "statusbar.left")
        center_style = ctx.style_resolver.resolve_style(self, "statusbar.center")
        right_style = ctx.style_resolver.resolve_style(self, "statusbar.right")
        base_style = ctx.style_resolver.resolve_style(self, "statusbar")

        # Override with instance-specific colors if provided
        if self.bg_color or self.text_color:
            # Map color names to RGB tuples (basic colors)
            color_map = {
                "black": (0, 0, 0),
                "red": (255, 0, 0),
                "green": (0, 255, 0),
                "yellow": (255, 255, 0),
                "blue": (0, 0, 255),
                "magenta": (255, 0, 255),
                "cyan": (0, 255, 255),
                "white": (255, 255, 255),
            }

            # Create custom style with overridden colors
            fg_color = None
            bg_color = None

            if self.text_color:
                fg_color = color_map.get(self.text_color.lower())

            if self.bg_color:
                bg_color = color_map.get(self.bg_color.lower())

            # Override all section styles with custom colors
            if fg_color or bg_color:
                base_style = Style(
                    fg_color=fg_color or base_style.fg_color,
                    bg_color=bg_color or base_style.bg_color,
                )
                left_style = Style(
                    fg_color=fg_color or left_style.fg_color,
                    bg_color=bg_color or left_style.bg_color,
                )
                center_style = Style(
                    fg_color=fg_color or center_style.fg_color,
                    bg_color=bg_color or center_style.bg_color,
                )
                right_style = Style(
                    fg_color=fg_color or right_style.fg_color,
                    bg_color=bg_color or right_style.bg_color,
                )

        # Get visible lengths of each section
        left_len = visible_length(self.left)
        center_len = visible_length(self.center)
        right_len = visible_length(self.right)

        # Calculate available space
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

        # Fill entire background with base style
        ctx.fill_rect(0, 0, bar_width, 1, " ", base_style)

        # Calculate positions
        center_pos = (bar_width - center_len) // 2
        right_pos = bar_width - right_len

        # Render left section
        if left_section:
            ctx.write_text(0, 0, left_section, left_style)

        # Render center section
        if center_section:
            # Adjust center position if it would overlap with left
            if center_pos < left_len + 1:
                center_pos = left_len + 1
            # Only render if there's room
            if center_pos + center_len <= right_pos - 1:
                ctx.write_text(center_pos, 0, center_section, center_style)

        # Render right section
        if right_section:
            ctx.write_text(right_pos, 0, right_section, right_style)
