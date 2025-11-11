"""Modal dialog elements for overlays.

This module provides modal dialog elements optimized for overlay display,
with built-in frame rendering and child element management.
"""

from __future__ import annotations

from wijjit.elements.base import OverlayElement
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import BorderStyle, Frame, FrameStyle


class ModalElement(OverlayElement):
    """Modal dialog element with frame and content.

    This element renders as a bordered frame suitable for modal dialogs.
    It automatically handles frame rendering and child element layout.

    Parameters
    ----------
    id : str, optional
        Unique identifier
    title : str, optional
        Modal title displayed in the frame border
    width : int, optional
        Modal width in characters (default: 50)
    height : int, optional
        Modal height in lines (default: 10)
    border : str or BorderStyle, optional
        Border style: "single", "double", or "rounded" (default: "single")
    centered : bool, optional
        Whether to center the modal (default: True)
    padding : tuple of int, optional
        Padding as (top, right, bottom, left) (default: (1, 2, 1, 2))

    Attributes
    ----------
    title : str or None
        Modal title
    border : BorderStyle
        Border style
    padding : tuple
        Content padding
    frame : Frame
        Frame renderer
    content_lines : list of str
        Rendered content lines
    """

    def __init__(
        self,
        id: str | None = None,
        title: str | None = None,
        width: int = 50,
        height: int = 10,
        border: str | BorderStyle = "single",
        centered: bool = True,
        padding: tuple[int, int, int, int] = (1, 2, 1, 2),
    ):
        super().__init__(id=id, width=width, height=height, centered=centered)

        self.title = title
        self.padding = padding

        # Convert border string to BorderStyle enum
        if isinstance(border, str):
            border_map = {
                "single": BorderStyle.SINGLE,
                "double": BorderStyle.DOUBLE,
                "rounded": BorderStyle.ROUNDED,
            }
            self.border = border_map.get(border.lower(), BorderStyle.SINGLE)
        else:
            self.border = border

        # Create frame for rendering
        style = FrameStyle(
            border=self.border,
            title=self.title,
            padding=self.padding,
        )
        self.frame = Frame(width=width, height=height, style=style)

        # Content storage
        self.content_lines: list[str] = []

    def set_content(self, content: str) -> None:
        """Set the modal content text.

        Parameters
        ----------
        content : str
            Content text (may contain newlines)
        """
        self.content_lines = content.split("\n")

    def render(self) -> str:
        """Render the modal with frame and content.

        Returns
        -------
        str
            Rendered modal as multi-line string
        """
        if not self.bounds:
            # No bounds set, return empty
            return ""

        # Calculate content bounds for children
        content_bounds = self.calculate_content_bounds()

        # Collect content from children if present
        if self.children:
            # Set bounds on children and render them
            child_output = []
            for child in self.children:
                # Set bounds so text elements can wrap properly
                child.set_bounds(content_bounds)
                rendered = child.render()
                if rendered:
                    # Split multi-line strings into individual lines
                    if "\n" in rendered:
                        child_output.extend(rendered.split("\n"))
                    else:
                        child_output.append(rendered)

            # Combine with existing content lines
            all_content = self.content_lines + child_output
        else:
            all_content = self.content_lines

        # Set frame properties
        self.frame.content = all_content
        self.frame.bounds = self.bounds

        # Render frame
        return self.frame.render()

    def calculate_content_bounds(self) -> Bounds:
        """Calculate the bounds available for content inside the frame.

        Returns
        -------
        Bounds
            Content area bounds
        """
        if not self.bounds:
            return Bounds(0, 0, 0, 0)

        # Account for borders (1 char on each side)
        border_width = 2
        border_height = 2

        # Account for padding
        padding_top, padding_right, padding_bottom, padding_left = self.padding
        total_padding_width = padding_left + padding_right
        total_padding_height = padding_top + padding_bottom

        content_width = max(0, self.bounds.width - border_width - total_padding_width)
        content_height = max(
            0, self.bounds.height - border_height - total_padding_height
        )

        # Content starts after border + padding
        content_x = self.bounds.x + 1 + padding_left
        content_y = self.bounds.y + 1 + padding_top

        return Bounds(
            x=content_x,
            y=content_y,
            width=content_width,
            height=content_height,
        )
