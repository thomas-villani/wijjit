"""Template rendering with Jinja2 for Wijjit applications.

This module provides a renderer that processes Jinja2 templates with
custom extensions and filters for terminal UI rendering.
"""

import os
import shutil
from typing import Any, Optional

from jinja2 import DictLoader, Environment, FileSystemLoader, Template

from wijjit.elements.base import Element
from wijjit.layout.engine import Container, FrameNode, LayoutEngine, LayoutNode
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.layout.scroll import render_vertical_scrollbar
from wijjit.logging_config import get_logger
from wijjit.tags.dialogs import (
    AlertDialogExtension,
    ConfirmDialogExtension,
    TextInputDialogExtension,
)
from wijjit.tags.display import (
    CodeBlockExtension,
    ListViewExtension,
    LogViewExtension,
    MarkdownExtension,
    ModalExtension,
    OverlayExtension,
    ProgressBarExtension,
    SpinnerExtension,
    TableExtension,
    TreeExtension,
)
from wijjit.tags.input import (
    ButtonExtension,
    CheckboxExtension,
    CheckboxGroupExtension,
    RadioExtension,
    RadioGroupExtension,
    SelectExtension,
    TextAreaExtension,
    TextInputExtension,
)
from wijjit.tags.layout import (
    FrameExtension,
    HStackExtension,
    LayoutContext,
    VStackExtension,
)
from wijjit.terminal.ansi import clip_to_width

# Get logger for this module
logger = get_logger(__name__)


class Renderer:
    """Template renderer using Jinja2.

    This class manages Jinja2 template rendering with support for
    both string templates and file-based templates.

    Parameters
    ----------
    template_dir : str, optional
        Directory containing template files
    autoescape : bool, optional
        Whether to enable autoescaping (default: False for terminal output)

    Attributes
    ----------
    env : jinja2.Environment
        The Jinja2 environment
    _string_templates : dict
        Cache of string templates
    """

    def __init__(self, template_dir: str | None = None, autoescape: bool = False):
        # Create loader based on template_dir
        if template_dir and os.path.isdir(template_dir):
            loader = FileSystemLoader(template_dir)
        else:
            # Use DictLoader for string templates
            loader = DictLoader({})

        # Create Jinja2 environment with custom extensions
        self.env = Environment(
            loader=loader,
            autoescape=autoescape,
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=[
                FrameExtension,
                VStackExtension,
                HStackExtension,
                TextInputExtension,
                ButtonExtension,
                CheckboxExtension,
                RadioExtension,
                CheckboxGroupExtension,
                RadioGroupExtension,
                SelectExtension,
                TableExtension,
                TreeExtension,
                ProgressBarExtension,
                SpinnerExtension,
                ListViewExtension,
                LogViewExtension,
                MarkdownExtension,
                CodeBlockExtension,
                TextAreaExtension,
                OverlayExtension,
                ModalExtension,
                ConfirmDialogExtension,
                AlertDialogExtension,
                TextInputDialogExtension,
            ],
        )

        # Cache for string templates
        self._string_templates: dict[str, Template] = {}

        # Add custom filters
        self._setup_filters()

        # Add layout constants to globals for easier template usage
        self.env.globals.update(
            {
                "fill": "fill",
                "auto": "auto",
            }
        )

    def _setup_filters(self) -> None:
        """Set up custom Jinja2 filters for terminal rendering."""
        # Add common filters
        self.env.filters["upper"] = str.upper
        self.env.filters["lower"] = str.lower
        self.env.filters["title"] = str.title

    def render_string(
        self, template_string: str, context: dict[str, Any] | None = None
    ) -> str:
        """Render a template from a string.

        Parameters
        ----------
        template_string : str
            The template string to render
        context : dict, optional
            Context variables for template rendering

        Returns
        -------
        str
            The rendered template output
        """
        context = context or {}

        # Check cache first
        if template_string in self._string_templates:
            template = self._string_templates[template_string]
        else:
            # Compile and cache
            template = self.env.from_string(template_string)
            self._string_templates[template_string] = template

        return template.render(**context)

    def render_file(
        self, template_name: str, context: dict[str, Any] | None = None
    ) -> str:
        """Render a template from a file.

        Parameters
        ----------
        template_name : str
            Name of the template file
        context : dict, optional
            Context variables for template rendering

        Returns
        -------
        str
            The rendered template output

        Raises
        ------
        jinja2.TemplateNotFound
            If the template file doesn't exist
        """
        context = context or {}
        template = self.env.get_template(template_name)
        return template.render(**context)

    def add_filter(self, name: str, func: callable) -> None:
        """Add a custom filter to the Jinja2 environment.

        Parameters
        ----------
        name : str
            Name of the filter
        func : callable
            Filter function
        """
        self.env.filters[name] = func

    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable to the Jinja2 environment.

        Parameters
        ----------
        name : str
            Name of the global variable
        value : Any
            Value of the global variable
        """
        self.env.globals[name] = value

    def render_with_layout(
        self,
        template_string: str,
        context: dict[str, Any] | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[str, list[Element]]:
        """Render a template with layout engine support.

        This method handles the full pipeline for layout-based templates:
        1. Create layout context
        2. Render template (building layout tree)
        3. Run layout engine to calculate positions
        4. Compose final output from positioned elements

        Parameters
        ----------
        template_string : str
            The template string to render
        context : dict, optional
            Context variables for template rendering
        width : int, optional
            Available width (default: terminal width)
        height : int, optional
            Available height (default: terminal height)

        Returns
        -------
        tuple of (str, list of Element)
            Rendered output and list of elements with bounds
        """
        context = context or {}

        # Get terminal size if not provided
        if width is None or height is None:
            term_size = shutil.get_terminal_size()
            width = width or term_size.columns
            height = height or term_size.height

        logger.debug(f"Rendering template with layout (width={width}, height={height})")

        # Create layout context
        layout_ctx = LayoutContext()

        # Store layout context in Jinja environment globals (so all tags can access it)
        self.env.globals["_wijjit_layout_context"] = layout_ctx

        # Also add to template context for CallBlock tags
        context["_wijjit_layout_context"] = layout_ctx

        # Compile template
        if template_string in self._string_templates:
            template = self._string_templates[template_string]
        else:
            template = self.env.from_string(template_string)
            self._string_templates[template_string] = template

        # Render template (this builds the layout tree)
        template.render(**context)

        # Clean up globals
        self.env.globals.pop("_wijjit_layout_context", None)

        # Check if we have a layout tree
        if layout_ctx.root is None:
            # No layout tags used, fall back to simple rendering
            output = template.render(**context)
            return output, []

        # Run layout engine
        logger.debug("Running layout engine")
        engine = LayoutEngine(layout_ctx.root, width, height)
        elements = engine.layout()
        logger.debug(f"Layout calculated for {len(elements)} elements")

        # Compose output from positioned elements
        output = self._compose_output(elements, width, height, layout_ctx.root)

        return output, elements

    def _compose_output(
        self,
        elements: list[Element],
        width: int,
        height: int,
        root: Optional["LayoutNode"] = None,
    ) -> str:
        """Compose final output from positioned elements.

        Parameters
        ----------
        elements : list of Element
            Elements with assigned bounds
        width : int
            Output width
        height : int
            Output height
        root : LayoutNode, optional
            Root of layout tree (for frame rendering)

        Returns
        -------
        str
            Composed output
        """

        # Create output buffer - now stores strings per cell to handle ANSI
        # Each cell can contain a character with ANSI codes
        buffer = [["" for _ in range(width)] for _ in range(height)]

        # First pass: Render frame borders if we have a layout tree
        if root is not None:
            self._render_frames(root, buffer, width, height)

        # Second pass: Render elements into the buffer
        for element in elements:
            if element.bounds is None:
                continue

            # Check if element is inside a scrollable frame
            scroll_offset = 0
            frame_clip_top = None
            frame_clip_bottom = None

            if hasattr(element, "parent_frame") and element.parent_frame is not None:
                parent = element.parent_frame
                if parent.style.scrollable and parent._needs_scroll:
                    scroll_offset = parent.get_scroll_offset()

                    # Calculate frame's visible content area for clipping
                    if parent.bounds is not None:
                        padding_top, _, padding_bottom, _ = parent.style.padding
                        frame_clip_top = (
                            parent.bounds.y + 1 + padding_top
                        )  # +1 for top border
                        frame_clip_bottom = (
                            parent.bounds.y + parent.bounds.height - padding_bottom
                        )  # Don't subtract 1, check is >=

            # Render element
            content = element.render()
            lines = content.split("\n")

            # Write to buffer at element's position (adjusted for scroll offset)
            for i, line in enumerate(lines):
                y = element.bounds.y + i - scroll_offset
                if y >= height:
                    break

                # Skip lines that are clipped by parent frame viewport
                if frame_clip_top is not None and (
                    y < frame_clip_top or y >= frame_clip_bottom
                ):
                    continue

                # Calculate remaining width from element position
                x_start = element.bounds.x
                if x_start >= width:
                    continue

                # Use the minimum of:
                # 1. Element's allocated width (respects parent frame boundaries)
                # 2. Remaining screen width (prevents overflow past screen edge)
                remaining_width = min(element.bounds.width, width - x_start)

                # Clip line to fit remaining width, preserving ANSI codes
                clipped_line = clip_to_width(line, remaining_width, ellipsis="")

                # For ANSI-aware positioning, we need to track visible position
                # while writing the entire string including ANSI codes
                visible_pos = 0
                i_char = 0
                pending_ansi = ""  # Accumulate consecutive ANSI sequences
                last_visible_pos = -1  # Track last written position for trailing ANSI

                while i_char < len(clipped_line):
                    # Check if we're at the start of an ANSI sequence
                    if clipped_line[i_char : i_char + 2] == "\x1b[":
                        # Find the end of the ANSI sequence
                        ansi_end = i_char + 2
                        while (
                            ansi_end < len(clipped_line)
                            and not clipped_line[ansi_end].isalpha()
                        ):
                            ansi_end += 1
                        if ansi_end < len(clipped_line):
                            ansi_end += 1  # Include the letter
                        # Accumulate this ANSI sequence (don't overwrite previous ones!)
                        pending_ansi += clipped_line[i_char:ansi_end]
                        i_char = ansi_end
                    else:
                        # Regular character - write it with any pending ANSI codes
                        if visible_pos < remaining_width:
                            buffer[y][x_start + visible_pos] = (
                                pending_ansi + clipped_line[i_char]
                            )
                            last_visible_pos = visible_pos
                            pending_ansi = (
                                ""  # Clear pending after writing to first char
                            )
                            visible_pos += 1
                        else:
                            # Past visible width - stop processing visible chars
                            # but continue to collect trailing ANSI codes
                            visible_pos += 1
                        i_char += 1

                # If there are trailing ANSI codes (like RESET), append them to the last character
                if pending_ansi and last_visible_pos >= 0:
                    buffer[y][x_start + last_visible_pos] += pending_ansi

        # Convert buffer to string
        return "\n".join(
            "".join(cell if cell else " " for cell in row) for row in buffer
        )

    def composite_overlays(
        self,
        base_output: str,
        overlay_elements: list[Element],
        width: int,
        height: int,
        apply_dimming: bool = False,
        dim_factor: float = 0.6,
    ) -> str:
        """Composite overlay elements on top of base output.

        This method renders overlays on top of the base UI output, optionally
        applying backdrop dimming for modal effects.

        Parameters
        ----------
        base_output : str
            Base UI output (newline-separated lines)
        overlay_elements : list of Element
            Overlay elements with assigned bounds (in z-order, lowest first)
        width : int
            Screen width
        height : int
            Screen height
        apply_dimming : bool
            Whether to dim the base output (for modal backdrops)
        dim_factor : float
            Dimming intensity (0.0 = black, 1.0 = original). Default is 0.6.

        Returns
        -------
        str
            Composited output with overlays on top

        Notes
        -----
        Overlays are rendered in the order provided (first = bottom, last = top).
        If apply_dimming is True, the base output is dimmed before overlays
        are composited.
        """
        from wijjit.terminal.ansi import apply_backdrop_dim, clip_to_width

        # Convert base output to buffer
        lines = base_output.split("\n")

        # Apply backdrop dimming if requested
        if apply_dimming:
            lines = apply_backdrop_dim(lines, dim_factor)

        # Ensure we have the right number of lines
        while len(lines) < height:
            lines.append(" " * width)

        # Convert to 2D buffer for overlay compositing
        buffer = []
        for line in lines[:height]:
            # Pad line to width if needed
            padded = line + " " * max(0, width - len(line))
            # Convert to list of individual characters (ANSI-aware)
            # For now, simple character splitting (TODO: improve ANSI handling)
            buffer.append(list(padded[:width]))

        # Render each overlay element onto buffer
        for element in overlay_elements:
            if element.bounds is None:
                continue

            # Render element content
            # Prepend RESET to ensure overlay isn't affected by backdrop dimming
            from wijjit.terminal.ansi import ANSIStyle

            content = element.render()
            lines = content.split("\n")

            # Write to buffer at element's position
            for i, line in enumerate(lines):
                y = element.bounds.y + i
                if y >= height or y < 0:
                    continue

                x_start = element.bounds.x
                if x_start >= width:
                    continue

                # Calculate remaining width
                remaining_width = min(element.bounds.width, width - x_start)

                # Prepend RESET to clear any backdrop dimming for this line
                line = ANSIStyle.RESET + line

                # Clip line to fit
                clipped_line = clip_to_width(line, remaining_width, ellipsis="")

                # Write line to buffer (ANSI-aware positioning)
                visible_pos = 0
                i_char = 0
                pending_ansi = ""

                while i_char < len(clipped_line):
                    # Check for ANSI sequence
                    if clipped_line[i_char : i_char + 2] == "\x1b[":
                        ansi_end = i_char + 2
                        while (
                            ansi_end < len(clipped_line)
                            and not clipped_line[ansi_end].isalpha()
                        ):
                            ansi_end += 1
                        if ansi_end < len(clipped_line):
                            ansi_end += 1
                        pending_ansi += clipped_line[i_char:ansi_end]
                        i_char = ansi_end
                    else:
                        # Regular character
                        if visible_pos < remaining_width:
                            x_pos = x_start + visible_pos
                            if x_pos < width:
                                buffer[y][x_pos] = pending_ansi + clipped_line[i_char]
                                pending_ansi = ""
                            visible_pos += 1
                        i_char += 1

        # Convert buffer back to string
        return "\n".join("".join(row) for row in buffer)

    def _render_frames(
        self, node: "LayoutNode", buffer: list[list[str]], width: int, height: int
    ) -> None:
        """Recursively render frame borders for containers with _frame_style.

        Parameters
        ----------
        node : LayoutNode
            Current node in the layout tree
        buffer : list of list of str
            Output buffer
        width : int
            Buffer width
        height : int
            Buffer height

        Notes
        -----
        FrameNode objects are skipped as they render themselves via Frame.render().
        This method only handles legacy containers with _frame_style metadata.
        """

        # Handle FrameNode - render borders if frame has no content
        # (Frames with content render themselves via Frame.render())
        if isinstance(node, FrameNode):
            # Check if this is a scrollable frame with children
            is_scrollable_container = (
                node.frame.style.scrollable
                and node.frame._needs_scroll
                and node.frame._has_children
            )

            # Handle scrollable frames with children specially
            if is_scrollable_container:
                # Render borders and scrollbar directly into buffer
                self._render_scrollable_frame_borders(node, buffer, width, height)
                # Don't recurse - children will render via element path with scroll offset
                return

            # Only render borders for non-scrollable frames with children
            if (
                not node.frame.content
                and node.bounds is not None
                and not (node.frame.style.scrollable and node.frame._needs_scroll)
            ):
                # Create frame info for border rendering
                border_value = (
                    node.frame.style.border.value
                    if hasattr(node.frame.style.border, "value")
                    else str(node.frame.style.border)
                )
                frame_info = {
                    "title": node.frame.style.title,
                    "border": border_value,
                }
                # Render borders using existing logic by treating as legacy frame
                # Fall through to border rendering logic below
                node._frame_style = frame_info
            else:
                # Frame has content - it will render itself
                # Just recurse for nested frames
                for child in node.content_container.children:
                    self._render_frames(child, buffer, width, height)
                return

        # Check if this node is a container with frame styling (legacy support or FrameNode)
        if isinstance(node, (Container, FrameNode)) and hasattr(node, "_frame_style"):
            # Render the frame
            frame_info = node._frame_style
            if node.bounds is not None:
                # Map border string to BorderStyle enum
                border_map = {
                    "single": BorderStyle.SINGLE,
                    "double": BorderStyle.DOUBLE,
                    "rounded": BorderStyle.ROUNDED,
                }
                border_style = border_map.get(
                    frame_info.get("border", "single"), BorderStyle.SINGLE
                )

                # Create and render frame (just borders, no content)
                # The child elements will render on top in their positioned locations
                # Render just the border lines (top, bottom, and sides)
                chars = {
                    BorderStyle.SINGLE: {
                        "tl": "┌",
                        "tr": "┐",
                        "bl": "└",
                        "br": "┘",
                        "h": "─",
                        "v": "│",
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
                }[border_style]

                # Draw top border with title
                y = node.bounds.y
                if y < height:
                    x = node.bounds.x
                    if frame_info.get("title"):
                        title_text = f" {frame_info['title']} "
                        title_len = len(title_text)
                        # Top-left corner
                        if x < width:
                            buffer[y][x] = chars["tl"]
                        # Horizontal line before title
                        if x + 1 < width:
                            buffer[y][x + 1] = chars["h"]
                        # Title
                        for i, ch in enumerate(title_text):
                            if x + 2 + i < width:
                                buffer[y][x + 2 + i] = ch
                        # Horizontal line after title to right edge
                        for i in range(2 + title_len, node.bounds.width - 1):
                            if x + i < width:
                                buffer[y][x + i] = chars["h"]
                        # Top-right corner
                        if x + node.bounds.width - 1 < width:
                            buffer[y][x + node.bounds.width - 1] = chars["tr"]
                    else:
                        # No title - just horizontal line
                        if x < width:
                            buffer[y][x] = chars["tl"]
                        for i in range(1, node.bounds.width - 1):
                            if x + i < width:
                                buffer[y][x + i] = chars["h"]
                        if x + node.bounds.width - 1 < width:
                            buffer[y][x + node.bounds.width - 1] = chars["tr"]

                # Draw side borders
                for row in range(1, node.bounds.height - 1):
                    y = node.bounds.y + row
                    if y < height:
                        x_left = node.bounds.x
                        x_right = node.bounds.x + node.bounds.width - 1
                        if x_left < width:
                            buffer[y][x_left] = chars["v"]
                        if x_right < width:
                            buffer[y][x_right] = chars["v"]

                # Draw bottom border
                y = node.bounds.y + node.bounds.height - 1
                if y < height:
                    x = node.bounds.x
                    if x < width:
                        buffer[y][x] = chars["bl"]
                    for i in range(1, node.bounds.width - 1):
                        if x + i < width:
                            buffer[y][x + i] = chars["h"]
                    if x + node.bounds.width - 1 < width:
                        buffer[y][x + node.bounds.width - 1] = chars["br"]

        # Recursively process children (for nested frames)
        if isinstance(node, FrameNode):
            # FrameNode children are in content_container
            for child in node.content_container.children:
                self._render_frames(child, buffer, width, height)
        elif isinstance(node, Container):
            for child in node.children:
                self._render_frames(child, buffer, width, height)

    def _render_scrollable_frame_borders(
        self, node: FrameNode, buffer: list[list[str]], width: int, height: int
    ) -> None:
        """Render borders and scrollbar for a scrollable frame with children.

        Parameters
        ----------
        node : FrameNode
            The scrollable frame node
        buffer : list of list of str
            Output buffer
        width : int
            Buffer width
        height : int
            Buffer height

        Notes
        -----
        This method renders only the borders and scrollbar, leaving the content
        area empty for children to render into with scroll offset applied.
        """

        frame = node.frame
        if not frame.bounds or not frame.scroll_manager:
            return

        chars = BORDER_CHARS[frame.style.border]
        padding_top, padding_right, padding_bottom, padding_left = frame.style.padding

        # Calculate inner dimensions
        inner_height = frame.bounds.height - 2 - padding_top - padding_bottom
        # scrollbar_width = 1 if frame.style.show_scrollbar else 0

        # Generate scrollbar
        scrollbar_chars = []
        if frame.style.show_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                frame.scroll_manager.state, inner_height, style="simple"
            )

        # Draw top border with title
        y = frame.bounds.y
        if y < height:
            x = frame.bounds.x
            if frame.style.title:
                title_text = f" {frame.style.title} "
                title_len = len(title_text)
                # Top-left corner
                if x < width:
                    buffer[y][x] = chars["tl"]
                # Horizontal line before title
                if x + 1 < width:
                    buffer[y][x + 1] = chars["h"]
                # Title
                for i, ch in enumerate(title_text):
                    if x + 2 + i < width:
                        buffer[y][x + 2 + i] = ch
                # Horizontal line after title to right edge
                for i in range(2 + title_len, frame.bounds.width - 1):
                    if x + i < width:
                        buffer[y][x + i] = chars["h"]
                # Top-right corner
                if x + frame.bounds.width - 1 < width:
                    buffer[y][x + frame.bounds.width - 1] = chars["tr"]
            else:
                # No title - just horizontal line
                if x < width:
                    buffer[y][x] = chars["tl"]
                for i in range(1, frame.bounds.width - 1):
                    if x + i < width:
                        buffer[y][x + i] = chars["h"]
                if x + frame.bounds.width - 1 < width:
                    buffer[y][x + frame.bounds.width - 1] = chars["tr"]

        # Draw side borders and scrollbar
        for row in range(1, frame.bounds.height - 1):
            y = frame.bounds.y + row
            if y < height:
                x_left = frame.bounds.x
                x_right = frame.bounds.x + frame.bounds.width - 1

                # Left border
                if x_left < width:
                    buffer[y][x_left] = chars["v"]

                # Scrollbar (if in content area, not padding)
                if frame.style.show_scrollbar:
                    content_row = row - 1 - padding_top
                    if 0 <= content_row < inner_height:
                        scrollbar_x = x_right - 1
                        scrollbar_char = (
                            scrollbar_chars[content_row]
                            if content_row < len(scrollbar_chars)
                            else " "
                        )
                        if scrollbar_x < width:
                            buffer[y][scrollbar_x] = scrollbar_char

                # Right border
                if x_right < width:
                    buffer[y][x_right] = chars["v"]

        # Draw bottom border
        y = frame.bounds.y + frame.bounds.height - 1
        if y < height:
            x = frame.bounds.x
            if x < width:
                buffer[y][x] = chars["bl"]
            for i in range(1, frame.bounds.width - 1):
                if x + i < width:
                    buffer[y][x + i] = chars["h"]
            if x + frame.bounds.width - 1 < width:
                buffer[y][x + frame.bounds.width - 1] = chars["br"]

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._string_templates.clear()
