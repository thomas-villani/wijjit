"""Template rendering with Jinja2 for Wijjit applications.

This module provides a renderer that processes Jinja2 templates with
custom extensions and filters for terminal UI rendering.
"""

import os
import shutil
from copy import copy
from typing import TYPE_CHECKING, Any, Callable, Optional

from jinja2 import BaseLoader, DictLoader, Environment, FileSystemLoader, Template

from wijjit.layout.bounds import Bounds
from wijjit.layout.dirty import DirtyRegionManager

if TYPE_CHECKING:
    from wijjit.core.overlay import OverlayManager

from wijjit.elements.base import Element
from wijjit.layout.engine import Container, FrameNode, LayoutEngine, LayoutNode
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.logging_config import get_logger
from wijjit.rendering.paint_context import PaintContext
from wijjit.styling.resolver import StyleResolver
from wijjit.styling.theme import ThemeManager
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
    StatusBarExtension,
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
from wijjit.tags.menu import (
    ContextMenuExtension,
    DropdownExtension,
    MenuItemExtension,
)
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.screen_buffer import DiffRenderer, ScreenBuffer

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

    def __init__(self, template_dir: str | None = None, autoescape: bool = False) -> None:
        # Create loader based on template_dir
        loader: BaseLoader
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
                StatusBarExtension,
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
                MenuItemExtension,
                DropdownExtension,
                ContextMenuExtension,
            ],
        )

        # Cache for string templates
        self._string_templates: dict[str, Template] = {}

        # Theme management for cell-based rendering
        self.theme_manager = ThemeManager()

        # Feature flag for diff rendering (now enabled by default with dirty region tracking)
        # When False, forces full screen re-renders on every frame
        # When True, only renders changed cells (more efficient with dirty region tracking)
        #
        # With DirtyRegionManager integrated, diff rendering can safely be enabled by default.
        # State/Focus/Hover changes mark appropriate regions dirty, ensuring correct updates.
        self.use_diff_rendering = True

        # Two-buffer system for clean overlay compositing:
        # - _last_base_buffer: The base view without overlays (always preserved)
        # - _last_displayed_buffer: What's actually on screen (may include overlays)
        # This separation allows clean diff rendering when overlays are added/removed
        # without requiring full redraws or losing the base buffer state.
        self._last_base_buffer: ScreenBuffer | None = None
        self._last_displayed_buffer: ScreenBuffer | None = None

        # Diff renderer for efficient incremental updates
        self._diff_renderer = DiffRenderer()

        # Dirty region manager for tracking screen areas that need redraw
        self.dirty_manager = DirtyRegionManager()

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

    def add_filter(self, name: str, func: Callable[..., Any]) -> None:
        """Add a custom filter to the Jinja2 environment.

        Parameters
        ----------
        name : str
            Name of the filter
        func : Callable
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
        overlay_manager: Optional["OverlayManager"] = None,
    ) -> tuple[str, list[Element], "LayoutContext"]:
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
        overlay_manager : OverlayManager, optional
            Overlay manager (deprecated, no longer used - overlays handled by caller)

        Returns
        -------
        tuple of (str, list of Element, LayoutContext)
            Rendered output, list of elements with bounds, and layout context
            containing overlay information from template tags
        """
        context = context or {}

        # Get terminal size if not provided
        if width is None or height is None:
            term_size = shutil.get_terminal_size()
            width = width or term_size.columns
            height = height or term_size.lines

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
            return output, [], layout_ctx

        # Check if a statusbar was created during template rendering
        # If yes, reduce available height by 1 to make room for it
        layout_height = height
        has_statusbar = (
            hasattr(layout_ctx, "_statusbar") and layout_ctx._statusbar is not None
        )
        if has_statusbar:
            layout_height = height - 1
            logger.debug("StatusBar detected, reducing layout height by 1")

        # Run layout engine
        logger.debug(f"Running layout engine (height={layout_height})")
        engine = LayoutEngine(layout_ctx.root, width, layout_height)
        elements = engine.layout()
        logger.debug(f"Layout calculated for {len(elements)} elements")

        # Get statusbar if present
        statusbar = getattr(layout_ctx, "_statusbar", None)

        # Compose output from positioned elements using cell-based rendering
        # Use full height for buffer, statusbar will render to last row
        logger.debug("Using cell-based rendering")
        output, base_buffer = self._compose_output_cells(
            elements, width, height, layout_ctx.root, statusbar
        )

        # Return layout context so caller can process overlays
        # This allows app._render() to manage overlay lifecycle properly
        # (separating template-declared overlays from programmatic ones)
        return output, elements, layout_ctx

    def _compose_output_cells(
        self,
        elements: list[Element],
        width: int,
        height: int,
        root: Optional["LayoutNode"] = None,
        statusbar: Element | None = None,
    ) -> tuple[str, "ScreenBuffer"]:
        """Compose final output using cell-based rendering.

        This method implements the NEW cell-based rendering pipeline with
        theme support and efficient diff rendering capabilities.

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
        statusbar : Element, optional
            StatusBar element to render at bottom of screen

        Returns
        -------
        str
            Composed ANSI output for terminal

        Notes
        -----
        This method creates a ScreenBuffer, renders all elements to cells,
        and converts the buffer to ANSI output. Elements are rendered in
        z-order (first to last).

        Elements can implement render_to(ctx) for cell-based rendering,
        or fall back to render() for legacy ANSI string rendering.
        """
        # Create screen buffer
        buffer = ScreenBuffer(width, height)
        style_resolver = StyleResolver(self.theme_manager.get_theme())

        # Transfer dirty regions from dirty manager to buffer for diff rendering optimization
        # IMPORTANT: On first render, ALWAYS force full screen dirty regardless of what's
        # in dirty_manager, because initial focus/hover setup may mark individual elements
        # but we need to render the entire screen on first paint
        if self.use_diff_rendering:
            if self._last_displayed_buffer is None:
                # First render: ALWAYS mark entire screen dirty, ignore dirty_manager
                # This ensures full UI renders even if focus manager marked individual elements
                buffer.mark_all_dirty()
            elif self.dirty_manager.is_dirty():
                if self.dirty_manager.is_full_screen_dirty():
                    # Mark entire buffer as dirty
                    buffer.mark_all_dirty()
                else:
                    # Transfer individual dirty regions
                    for x, y, w, h in self.dirty_manager.get_merged_regions():
                        buffer.mark_dirty(x, y, w, h)
            # Note: If dirty_manager is empty, we don't mark anything dirty
            # This allows diff rendering to output nothing (screen stays as-is), which is correct

        # First pass: Render frame borders if we have a layout tree
        if root is not None:
            self._render_frames_to_buffer(root, buffer, style_resolver)

        # Second pass: Render elements to the buffer
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
                        )

            # Adjust element bounds for scroll offset

            adjusted_bounds = Bounds(
                x=element.bounds.x,
                y=element.bounds.y - scroll_offset,
                width=element.bounds.width,
                height=element.bounds.height,
            )

            # Skip if element is completely outside visible area
            if frame_clip_top is not None and frame_clip_bottom is not None:
                if adjusted_bounds.y + adjusted_bounds.height <= frame_clip_top:
                    continue
                if adjusted_bounds.y >= frame_clip_bottom:
                    continue

            # Create paint context for this element
            ctx = PaintContext(
                buffer=buffer,
                style_resolver=style_resolver,
                bounds=adjusted_bounds,
            )

            # Render element using cell-based rendering
            element.render_to(ctx)

        # Third pass: Render statusbar if present
        if statusbar is not None:
            # Position statusbar at bottom of screen
            statusbar_bounds = Bounds(x=0, y=height - 1, width=width, height=1)
            statusbar.set_bounds(statusbar_bounds)

            # Create paint context for statusbar
            statusbar_ctx = PaintContext(
                buffer=buffer,
                style_resolver=style_resolver,
                bounds=statusbar_bounds,
            )

            # Render statusbar using cell-based rendering
            if hasattr(statusbar, "render_to") and callable(statusbar.render_to):
                statusbar.render_to(statusbar_ctx)

        # Convert buffer to ANSI string for terminal output
        # IMPORTANT: Do this BEFORE storing buffer, so diff renderer compares
        # old buffer (or None) with new buffer, not new buffer with itself!
        output = self._buffer_to_ansi(buffer)

        # Store base buffer for next render (after converting!)
        # Base buffer: The view without overlays (always preserved)
        # NOTE: We update displayed buffer here for normal rendering flow
        # This will be overwritten by composite_overlays if overlays are present
        self._last_base_buffer = buffer
        self._last_displayed_buffer = buffer

        # Clear dirty regions now that rendering is complete
        self.dirty_manager.clear()

        # Return both output and buffer
        return output, buffer

    def _render_frames_to_buffer(
        self, node: "LayoutNode", buffer: ScreenBuffer, style_resolver: StyleResolver
    ) -> None:
        """Recursively render frame borders to cell buffer.

        Parameters
        ----------
        node : LayoutNode
            Current layout node
        buffer : ScreenBuffer
            Target buffer
        style_resolver : StyleResolver
            Style resolver for theme styles

        Notes
        -----
        This recursively walks the layout tree and renders frame borders
        to the cell buffer. Frame content is not rendered here - only
        the border decorations.
        """
        # Render this frame's border if it's a FrameNode
        if isinstance(node, FrameNode):
            frame = node.frame
            bounds = frame.bounds
            if bounds is None:
                return
            style = frame.style

            # Resolve frame border style from theme
            border_style = style_resolver.resolve_style_by_class("frame.border")

            # Get border characters
            border_chars = BORDER_CHARS.get(
                style.border, BORDER_CHARS[BorderStyle.SINGLE]
            )

            # Create paint context for frame
            ctx = PaintContext(buffer, style_resolver, bounds)

            # Draw frame border
            ctx.draw_border(
                0, 0, bounds.width, bounds.height, border_style, border_chars
            )

            # Draw title if present
            if style.title:
                title_text = f" {style.title} "
                title_len = visible_length(title_text)

                # Position title on top border
                title_x = max(1, (bounds.width - title_len) // 2)
                if title_x + title_len < bounds.width - 1:
                    # Resolve title style
                    title_style = style_resolver.resolve_style_by_class("text.title")
                    ctx.write_text(title_x, 0, title_text, title_style, clip=True)

        # Recursively render children
        if isinstance(node, Container):
            for child in node.children:
                self._render_frames_to_buffer(child, buffer, style_resolver)

    def _buffer_to_ansi(self, buffer: ScreenBuffer) -> str:
        """Convert cell buffer to ANSI string for terminal output.

        Parameters
        ----------
        buffer : ScreenBuffer
            Source buffer

        Returns
        -------
        str
            ANSI string representation

        Notes
        -----
        This method uses DiffRenderer for efficient output generation.

        When use_diff_rendering is True:
            First render is full (with screen clear), subsequent renders
            only output changes (diffs).

        When use_diff_rendering is False:
            Always does full render with screen clear. This is more
            reliable but less efficient.
        """
        if self.use_diff_rendering:
            # Diff mode: compare with what's on screen and only output changes
            return self._diff_renderer.render_diff(self._last_displayed_buffer, buffer)
        else:
            # Full render mode: always clear and redraw everything
            return self._diff_renderer.render_diff(None, buffer)

    def get_last_buffer(self) -> ScreenBuffer | None:
        """Get the last rendered buffer for external diff rendering.

        Returns
        -------
        ScreenBuffer or None
            Last rendered buffer, or None if not yet rendered
        """
        return self._last_displayed_buffer

    def get_buffer_as_text(self) -> str:
        """Get the last rendered buffer as plain text (for testing).

        Returns
        -------
        str
            Plain text representation of the last buffer

        Notes
        -----
        This is primarily used for test assertions where you want to check
        for visible text content without parsing ANSI escape sequences.
        Returns empty string if no buffer has been rendered yet.

        Examples
        --------
        >>> renderer = Renderer()
        >>> output, _, _ = renderer.render_with_layout(template, 80, 24)
        >>> text = renderer.get_buffer_as_text()
        >>> 'Welcome' in text
        True
        """
        if self._last_displayed_buffer is None:
            return ""
        return self._last_displayed_buffer.to_text()

    def _composite_overlays_cells(
        self,
        overlay_elements: list[Element],
        width: int,
        height: int,
        apply_dimming: bool = False,
        dim_factor: float = 0.6,
        overlay_manager: Optional["OverlayManager"] = None,
        force_full_redraw: bool = False,
    ) -> str:
        """Composite overlay elements on cell buffer.

        Parameters
        ----------
        overlay_elements : list of Element
            Overlay elements to render
        width : int
            Screen width
        height : int
            Screen height
        apply_dimming : bool
            Whether to dim the base
        dim_factor : float
            Dimming intensity
        force_full_redraw : bool
            Force full screen redraw instead of diff rendering

        Returns
        -------
        str
            ANSI output with overlays composited

        Notes
        -----
        This method composites overlays directly on the cell buffer,
        then renders the entire result. This is cell-aware and works
        correctly with diff rendering.
        """
        logger = get_logger(__name__)
        logger.debug(
            f"_composite_overlays_cells: overlay_count={len(overlay_elements)}, "
            f"force_full_redraw={force_full_redraw}, has_base_buffer={self._last_base_buffer is not None}"
        )

        # Create a new buffer for compositing
        # IMPORTANT: Start from BASE buffer (not displayed buffer!)
        # This ensures overlays are always composited on top of the clean base,
        # not on top of previous overlay composites.
        composite_buffer = ScreenBuffer(width, height)

        # Copy cells from BASE buffer (view without overlays)
        if self._last_base_buffer:
            for y in range(min(height, self._last_base_buffer.height)):
                for x in range(min(width, self._last_base_buffer.width)):
                    # Create a copy of the cell to avoid mutating the original
                    original_cell = self._last_base_buffer.cells[y][x]
                    composite_buffer.cells[y][x] = copy(original_cell)

        # Apply dimming to base if requested
        if apply_dimming:
            for y in range(height):
                for x in range(width):
                    cell = composite_buffer.cells[y][x]
                    # Dim by reducing RGB values
                    if cell.fg_color:
                        r, g, b = cell.fg_color
                        cell.fg_color = (
                            int(r * dim_factor),
                            int(g * dim_factor),
                            int(b * dim_factor),
                        )
                    if cell.bg_color:
                        r, g, b = cell.bg_color
                        cell.bg_color = (
                            int(r * dim_factor),
                            int(g * dim_factor),
                            int(b * dim_factor),
                        )

        # Render overlays onto composite buffer
        style_resolver = StyleResolver(self.theme_manager.get_theme())

        for element in overlay_elements:
            if element.bounds is None:
                continue

            # Create paint context for overlay element
            ctx = PaintContext(
                buffer=composite_buffer,
                style_resolver=style_resolver,
                bounds=element.bounds,
            )

            # Render overlay using cell-based rendering
            element.render_to(ctx)

        # Now render the composite buffer
        # Diff from what's currently on screen (displayed buffer) to new composite
        # IMPORTANT: Don't touch _last_base_buffer - it stays as the base view
        # Only update _last_displayed_buffer to track what's actually on screen

        # When force_full_redraw is True, mark entire buffer dirty to ensure complete redraw
        # This is a defensive measure to prevent ghost remnants from dismissed overlays
        if force_full_redraw:
            composite_buffer.mark_all_dirty()

        if self.use_diff_rendering and not force_full_redraw:
            # Diff from current display to new composite
            output = self._diff_renderer.render_diff(
                self._last_displayed_buffer, composite_buffer
            )
        else:
            # Full redraw (either diff rendering is disabled, or force_full_redraw is True)
            output = self._diff_renderer.render_diff(None, composite_buffer)

        # Update what's displayed (composite with overlays)
        # Don't touch _last_base_buffer - it preserves the base view
        self._last_displayed_buffer = composite_buffer

        return output

    def composite_overlays(
        self,
        base_output: str,
        overlay_elements: list[Element],
        width: int,
        height: int,
        apply_dimming: bool = False,
        dim_factor: float = 0.6,
        overlay_manager: Optional["OverlayManager"] = None,
        force_full_redraw: bool = False,
    ) -> str:
        """Composite overlay elements on top of base output.

        This method renders overlays on top of the base UI output, optionally
        applying backdrop dimming for modal effects.

        Parameters
        ----------
        base_output : str
            Base UI output (ANSI string or newline-separated lines)
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
        force_full_redraw : bool
            Force full screen redraw instead of diff rendering

        Returns
        -------
        str
            Composited output with overlays on top

        Notes
        -----
        Overlays are rendered in the order provided (first = bottom, last = top).
        If apply_dimming is True, the base output is dimmed before overlays
        are composited.

        Overlays are composited directly on the cell buffer for efficient rendering.
        """
        # Composite overlays on base buffer
        if self._last_base_buffer is not None:
            return self._composite_overlays_cells(
                overlay_elements,
                width,
                height,
                apply_dimming,
                dim_factor,
                overlay_manager,
                force_full_redraw,
            )

        # No buffer available - return base output unchanged
        return base_output

    def composite_statusbar(
        self,
        base_output: str,
        statusbar_element: Element,
        width: int,
        height: int,
    ) -> str:
        """Composite a status bar at the bottom of the output.

        This method renders a status bar element at the bottom line of the
        screen output, replacing the last line.

        Parameters
        ----------
        base_output : str
            Base UI output (newline-separated lines)
        statusbar_element : Element
            StatusBar element to render
        width : int
            Screen width
        height : int
            Screen height

        Returns
        -------
        str
            Output with statusbar composited at the bottom

        Notes
        -----
        The statusbar replaces the last line of the output. If the base
        output has fewer lines than the screen height, it will be padded.
        """

        # Convert base output to lines
        lines = base_output.split("\n")

        # Ensure we have height-1 lines (reserve last line for statusbar)
        while len(lines) < height - 1:
            lines.append(" " * width)

        # Trim to height-1 lines
        lines = lines[: height - 1]

        # Set bounds for statusbar element
        statusbar_bounds = Bounds(x=0, y=height - 1, width=width, height=1)
        statusbar_element.set_bounds(statusbar_bounds)

        # Render statusbar
        # Note: Using type ignore because Element base class doesn't define render()
        # but some legacy elements may still implement it
        statusbar_line = statusbar_element.render()  # type: ignore[attr-defined]

        # Ensure statusbar line is exactly width characters (clip or pad)

        statusbar_len = visible_length(statusbar_line)
        if statusbar_len > width:
            statusbar_line = clip_to_width(statusbar_line, width, ellipsis="")
        elif statusbar_len < width:
            statusbar_line += " " * (width - statusbar_len)

        # Append statusbar line
        lines.append(statusbar_line)

        return "\n".join(lines)

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._string_templates.clear()
