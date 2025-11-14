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

    def render_to(self, ctx) -> None:
        """Render the modal using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements proper cell-based rendering with sub-contexts
        for child elements. It handles:
        - Frame border and background rendering
        - Text element rendering with theme styles
        - Interactive element (button, input) rendering with sub-contexts
        - Proper bounds setting for mouse and focus handling

        Theme Styles
        ------------
        This element uses the following theme style classes (via Frame):
        - 'modal': Base modal style
        - 'modal.text': Text content style
        - 'modal.backdrop': Semi-transparent backdrop style (handled by overlay manager)
        - 'frame.border': Border style (inherited from Frame)
        - 'frame.border:focus': Focused border style (inherited from Frame)
        """
        from wijjit.elements.base import TextElement
        from wijjit.rendering.paint_context import PaintContext

        if not self.bounds:
            # No bounds set, cannot render
            return

        # Render frame (border and background) with empty content
        self.frame.content = []
        self.frame.bounds = self.bounds
        self.frame.render_to(ctx)

        # If no children, render static content lines if any
        if not self.children:
            if self.content_lines:
                content_bounds = self.calculate_content_bounds()
                text_style = ctx.style_resolver.resolve_style(self, "modal.text")
                for i, line in enumerate(self.content_lines):
                    # Convert absolute content bounds to relative coords for write_text
                    rel_x = content_bounds.x - ctx.bounds.x
                    rel_y = content_bounds.y - ctx.bounds.y + i
                    ctx.write_text(rel_x, rel_y, line, text_style)
            return

        # Calculate content bounds for children
        content_bounds = self.calculate_content_bounds()
        current_y = 0  # Relative to content area

        # Separate children by type for layout
        from wijjit.elements.input.button import Button
        from wijjit.elements.input.text import TextInput

        text_elements = []
        text_inputs = []
        buttons = []
        other_elements = []

        for child in self.children:
            if isinstance(child, TextElement):
                text_elements.append(child)
            elif isinstance(child, TextInput):
                text_inputs.append(child)
            elif isinstance(child, Button):
                buttons.append(child)
            else:
                other_elements.append(child)

        # Resolve default text style
        text_style = ctx.style_resolver.resolve_style(self, "modal.text")

        # Render text elements
        for text_elem in text_elements:
            lines = text_elem.text.split("\n")
            for line in lines:
                # Convert absolute to relative coords
                rel_x = content_bounds.x - ctx.bounds.x
                rel_y = content_bounds.y - ctx.bounds.y + current_y
                ctx.write_text(rel_x, rel_y, line, text_style)
                current_y += 1

        # Add spacing before inputs
        if text_elements and (text_inputs or buttons or other_elements):
            current_y += 1

        # Render text inputs (full width, each on its own line)
        for text_input in text_inputs:
            elem_width = getattr(text_input, "width", content_bounds.width)
            elem_height = getattr(text_input, "height", 1)

            # Center input horizontally
            start_x = max(0, (content_bounds.width - elem_width) // 2)

            # Create absolute bounds for this element
            elem_bounds = Bounds(
                x=content_bounds.x + start_x,
                y=content_bounds.y + current_y,
                width=elem_width,
                height=elem_height,
            )
            text_input.set_bounds(elem_bounds)

            # Create sub-context for element
            sub_ctx = PaintContext(ctx.buffer, ctx.style_resolver, elem_bounds)

            # Render element using cell-based rendering
            if hasattr(text_input, "render_to") and callable(text_input.render_to):
                text_input.render_to(sub_ctx)

            current_y += elem_height

        # Add spacing before buttons
        if text_inputs and buttons:
            current_y += 1

        # Render buttons (horizontal layout, centered)
        if buttons:
            # Calculate total width needed
            total_width = sum(getattr(btn, "width", 10) for btn in buttons)
            spacing = 2  # Space between buttons
            total_width += spacing * (len(buttons) - 1)

            # Center horizontally
            start_x = max(0, (content_bounds.width - total_width) // 2)

            elem_x = start_x
            for button in buttons:
                elem_width = getattr(button, "width", 10)
                elem_height = getattr(button, "height", 1)

                # Create absolute bounds for this element
                elem_bounds = Bounds(
                    x=content_bounds.x + elem_x,
                    y=content_bounds.y + current_y,
                    width=elem_width,
                    height=elem_height,
                )
                button.set_bounds(elem_bounds)

                # Create sub-context for element
                sub_ctx = PaintContext(ctx.buffer, ctx.style_resolver, elem_bounds)

                # Render element using cell-based rendering
                if hasattr(button, "render_to") and callable(button.render_to):
                    button.render_to(sub_ctx)

                elem_x += elem_width + spacing

        # Render other elements (fallback)
        if other_elements:
            current_y += 1
            for elem in other_elements:
                elem_width = getattr(elem, "width", 10)
                elem_height = getattr(elem, "height", 1)

                elem_bounds = Bounds(
                    x=content_bounds.x,
                    y=content_bounds.y + current_y,
                    width=elem_width,
                    height=elem_height,
                )
                elem.set_bounds(elem_bounds)

                sub_ctx = PaintContext(ctx.buffer, ctx.style_resolver, elem_bounds)

                if hasattr(elem, "render_to") and callable(elem.render_to):
                    elem.render_to(sub_ctx)

                current_y += elem_height

    def render(self) -> str:
        """Render the modal with frame and content (LEGACY ANSI rendering).

        Returns
        -------
        str
            Rendered modal as multi-line string

        Notes
        -----
        This is the legacy ANSI string-based rendering method.
        New code should use render_to() for cell-based rendering.
        Kept for backward compatibility during migration.
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
