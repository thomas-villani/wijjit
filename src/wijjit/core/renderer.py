"""Template rendering with Jinja2 for Wijjit applications.

This module provides a renderer that processes Jinja2 templates with
custom extensions and filters for terminal UI rendering.
"""

import os
import shutil
from collections.abc import Callable
from copy import copy
from typing import TYPE_CHECKING, Any

from jinja2 import (
    BaseLoader,
    DictLoader,
    Environment,
    FileSystemLoader,
    Template,
    TemplateNotFound,
)

from wijjit.layout.bounds import Bounds
from wijjit.layout.dirty import DirtyRegionManager

if TYPE_CHECKING:
    from wijjit.core.overlay import OverlayManager

from wijjit.core.element_registry import ElementRegistry
from wijjit.core.reconciler import Reconciler
from wijjit.core.render_context import render_context_scope
from wijjit.core.vdom import VNode
from wijjit.elements.base import Element
from wijjit.layout.engine import (
    Container,
    FrameNode,
    LayoutEngine,
    LayoutNode,
)
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.logging_config import get_logger
from wijjit.rendering.paint_context import PaintContext
from wijjit.styling.resolver import StyleResolver
from wijjit.styling.theme import ThemeManager
from wijjit.tags.charts import (
    BarChartExtension,
    ColumnChartExtension,
    GaugeExtension,
    HeatMapExtension,
    LineChartExtension,
    SparklineExtension,
)
from wijjit.tags.dialogs import (
    AlertDialogExtension,
    ConfirmDialogExtension,
    TextInputDialogExtension,
)
from wijjit.tags.display import (
    ContentViewExtension,
    ImageViewExtension,
    LinkExtension,
    ListViewExtension,
    LogViewExtension,
    ModalExtension,
    PageExtension,
    PagerExtension,
    ProgressBarExtension,
    SpinnerExtension,
    StatusBarExtension,
    StatusIndicatorExtension,
    TabbedPanelExtension,
    TabExtension,
    TableExtension,
    TextExtension,
    TreeExtension,
    TreeItemExtension,
)
from wijjit.tags.input import (
    ButtonExtension,
    CheckboxExtension,
    CheckboxGroupExtension,
    CodeEditorExtension,
    DataGridExtension,
    RadioExtension,
    RadioGroupExtension,
    SelectExtension,
    SelectItemExtension,
    SliderExtension,
    TextAreaExtension,
    TextInputExtension,
    ToggleExtension,
)
from wijjit.tags.layout import (
    ColspanExtension,
    FrameExtension,
    GridExtension,
    HStackExtension,
    LayoutContext,
    RowspanExtension,
    SplitPanelExtension,
    VStackExtension,
)
from wijjit.tags.menu import (
    ContextMenuExtension,
    DropdownExtension,
    MenuItemExtension,
)
from wijjit.terminal.ansi import visible_length
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
    auto_reload : bool, optional
        Whether Jinja2 reloads file templates when they change on disk
        (default: False). Useful during development; maps to the
        ``TEMPLATE_AUTO_RELOAD`` config key.

    Attributes
    ----------
    env : jinja2.Environment
        The Jinja2 environment
    _string_templates : dict
        Cache of string templates
    """

    def __init__(
        self,
        template_dir: str | None = None,
        autoescape: bool = False,
        auto_reload: bool = False,
    ) -> None:
        # Store template_dir for introspection
        self.template_dir = template_dir

        # Create loader based on template_dir
        loader: BaseLoader
        if template_dir:
            # User specified a template_dir, validate it exists
            if not os.path.isdir(template_dir):
                raise FileNotFoundError(
                    f"Template directory '{template_dir}' does not exist. "
                    f"Please create the directory or use inline template strings instead. "
                    f"To use inline templates, don't pass template_dir to Wijjit()."
                )
            loader = FileSystemLoader(template_dir)
            self.using_file_loader = True
            logger.info(f"Using FileSystemLoader for templates from: {template_dir}")
        else:
            # No template_dir specified, use DictLoader for string templates
            loader = DictLoader({})
            self.using_file_loader = False
            logger.debug("Using DictLoader for inline string templates")

        # Create Jinja2 environment with custom extensions
        self.env = Environment(
            loader=loader,
            autoescape=autoescape,
            auto_reload=auto_reload,
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=[
                FrameExtension,
                VStackExtension,
                HStackExtension,
                GridExtension,
                ColspanExtension,
                RowspanExtension,
                SplitPanelExtension,
                TextInputExtension,
                ButtonExtension,
                CheckboxExtension,
                RadioExtension,
                CheckboxGroupExtension,
                RadioGroupExtension,
                SelectExtension,
                SelectItemExtension,
                TableExtension,
                TreeExtension,
                TreeItemExtension,
                ProgressBarExtension,
                SpinnerExtension,
                StatusBarExtension,
                TextExtension,
                ListViewExtension,
                LogViewExtension,
                TextAreaExtension,
                CodeEditorExtension,
                ModalExtension,
                ConfirmDialogExtension,
                AlertDialogExtension,
                TextInputDialogExtension,
                MenuItemExtension,
                DropdownExtension,
                ContextMenuExtension,
                TabExtension,
                TabbedPanelExtension,
                # Pager (linear pagination)
                PageExtension,
                PagerExtension,
                # Link and unified content view
                LinkExtension,
                ContentViewExtension,
                # Chart extensions
                SparklineExtension,
                BarChartExtension,
                ColumnChartExtension,
                LineChartExtension,
                GaugeExtension,
                HeatMapExtension,
                # Image view
                ImageViewExtension,
                # New input elements
                SliderExtension,
                ToggleExtension,
                DataGridExtension,
                # Status indicator
                StatusIndicatorExtension,
            ],
        )

        # Cache for string templates
        self._string_templates: dict[str, Template] = {}

        # Theme management for cell-based rendering
        self.theme_manager = ThemeManager()

        # Global focus color override (set from config)
        self.focus_color: tuple[int, int, int] | None = None

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

        # Virtual DOM reconciliation system
        # Reconciler manages element lifecycle: create, update, delete, and reuse
        self._reconciler = Reconciler(ElementRegistry())
        self._last_vnode_tree: VNode | None = None

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

    def get_extension_tag_names(self) -> set[str]:
        """Return the set of Jinja2 tag names registered by Wijjit extensions.

        Useful for callers that need to determine whether a template uses any
        Wijjit-specific tag (and therefore must be routed through the layout
        pipeline rather than plain Jinja2 string rendering).

        Returns
        -------
        set[str]
            Every tag name registered by the Wijjit extension classes (e.g.
            ``"frame"``, ``"textinput"``, ``"button"``).
        """
        names: set[str] = set()
        for ext in self.env.extensions.values():
            tags = getattr(ext, "tags", None)
            if tags:
                names.update(tags)
        return names

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
        template = self._get_file_template(template_name)
        return template.render(**context)

    def _get_file_template(self, template_name: str) -> Template:
        """Load a file template, raising actionable errors on common mistakes.

        Parameters
        ----------
        template_name : str
            Name of the template file to load from ``template_dir``.

        Returns
        -------
        jinja2.Template
            The loaded (and Jinja-cached) template.

        Raises
        ------
        RuntimeError
            If no template directory is configured (the renderer is using the
            in-memory ``DictLoader``), so ``render_template()`` cannot resolve a
            file. The message points at ``template_dir`` / the ``templates/``
            convention and ``render_template_string()``.
        jinja2.TemplateNotFound
            If the file is not present in ``template_dir``; re-raised with the
            searched directory included in the message.
        """
        if not self.using_file_loader:
            raise RuntimeError(
                f"render_template({template_name!r}) needs a template directory, "
                f"but none is configured. Create a 'templates/' directory next to "
                f"your app module (it is auto-discovered), or pass "
                f"Wijjit(template_dir='...'). To render an inline string instead, "
                f"use render_template_string()."
            )
        try:
            return self.env.get_template(template_name)
        except TemplateNotFound as exc:
            raise TemplateNotFound(
                template_name,
                message=(
                    f"Template {template_name!r} not found in template directory "
                    f"{self.template_dir}. Check the filename and that the file "
                    f"exists in that directory."
                ),
            ) from exc

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
        template_string: str = "",
        context: dict[str, Any] | None = None,
        width: int | None = None,
        height: int | None = None,
        overlay_manager: "OverlayManager | None" = None,
        template_name: str | None = None,
    ) -> tuple[str, list[Element], "LayoutContext"]:
        """Render a template with layout engine support.

        This method handles the full pipeline for layout-based templates:
        1. Create layout context
        2. Render template (building layout tree)
        3. Run layout engine to calculate positions
        4. Compose final output from positioned elements

        Parameters
        ----------
        template_string : str, optional
            The template string to render (use this OR template_name)
        context : dict, optional
            Context variables for template rendering
        width : int, optional
            Available width (default: terminal width)
        height : int, optional
            Available height (default: terminal height)
        overlay_manager : OverlayManager, optional
            Overlay manager (deprecated, no longer used - overlays handled by caller)
        template_name : str, optional
            Name of template file to load from template_dir (use this OR template_string)

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

        # Get focused_id from context if available
        focused_id = context.get("_wijjit_focused_id")

        # Use RenderContext for thread-safe context passing
        with render_context_scope(layout_ctx, context, focused_id) as render_ctx:
            # Compile or load template
            if template_name:
                # Load template from file (via FileSystemLoader), with friendly
                # errors when no template dir is set or the file is missing.
                template = self._get_file_template(template_name)
            elif template_string in self._string_templates:
                # Use cached string template
                template = self._string_templates[template_string]
            else:
                # Compile and cache new string template
                template = self.env.from_string(template_string)
                self._string_templates[template_string] = template

            # Render template (this builds the layout tree)
            # Capture output in case there are no layout tags (to avoid double-rendering)
            rendered_output = template.render(**context)

            # Transfer overlay info from RenderContext to LayoutContext
            # for backward compatibility with existing overlay handling
            if render_ctx.overlays:
                layout_ctx._overlays = render_ctx.overlays
            if render_ctx.statusbar is not None:
                layout_ctx._statusbar = render_ctx.statusbar

        # Check if we have a VNode tree (layout tags were used)
        # Use vnode_root since it's the canonical source for VNode-based rendering
        if layout_ctx.vnode_root is None:
            # No layout tags used, return the already-rendered output
            # This avoids double-rendering templates without layout tags
            return rendered_output, [], layout_ctx

        # === Virtual DOM Reconciliation ===
        # Freeze the VNode tree built during template rendering
        frozen_vnode_tree = layout_ctx.freeze_vnode_tree()

        # Reconcile with previous VNode tree to reuse elements
        old_tree = self._last_vnode_tree
        new_tree = frozen_vnode_tree

        if new_tree is not None:
            # Reconcile: reuse, update, create, delete elements as needed
            if old_tree is not None:
                root_element, reconciled_elements = self._reconciler.reconcile(
                    old_tree, new_tree
                )
                logger.debug(
                    f"Reconciled {len(reconciled_elements)} elements "
                    f"({len(self._reconciler._element_cache)} cached)"
                )
            else:
                # First render: create all elements
                root_element, reconciled_elements = self._reconciler.reconcile(
                    None, new_tree
                )
                logger.debug(
                    f"First render: created {len(reconciled_elements)} elements"
                )

            # Use reconciler's element cache directly - it's already keyed by vnode.key
            # This handles both elements with and without explicit IDs
            reconciled_map = self._reconciler._element_cache

            # Build LayoutNode tree from VNode tree + reconciled elements
            # This replaces the old approach of swapping elements into template-created tree
            # Extract state dict from context for scroll/tab state persistence
            state_dict = context.get("state") if context else None
            root_frame_tracker = [False]  # Track if root frame found for auto-scroll
            layout_ctx.root = self._build_layout_tree_from_vnode(
                new_tree,
                reconciled_map,
                state_dict,
                root_frame_found=root_frame_tracker,
            )
            logger.debug("Built layout tree from VNode + reconciled elements")

            # If no root frame was found, wrap the content in an implicit scrollable frame
            if not root_frame_tracker[0]:
                from wijjit.layout.engine import FrameNode, VStack
                from wijjit.layout.frames import BorderStyle, Frame, FrameStyle

                implicit_frame = Frame(
                    width="fill",
                    height="fill",
                    style=FrameStyle(
                        border_style=BorderStyle.NONE,
                        padding=(0, 0, 0, 0),
                        scrollable=True,
                        show_scrollbar=True,
                    ),
                    id="_implicit_root_frame",
                )
                implicit_frame_node = FrameNode(
                    frame=implicit_frame,
                    width="fill",
                    height="fill",
                )
                # Wrap existing root in a content container
                content_container = VStack(width="fill", height="auto")
                content_container.add_child(layout_ctx.root)
                implicit_frame_node.content_container = content_container
                layout_ctx.root = implicit_frame_node
                logger.debug("Wrapped content in implicit scrollable root frame")

        # Store for next render
        self._last_vnode_tree = new_tree

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

    def _build_layout_tree_from_vnode(
        self,
        vnode: VNode,
        reconciled_map: dict[str, Element],
        state_dict: dict[str, Any] | None = None,
        root_frame_found: list[bool] | None = None,
    ) -> LayoutNode:
        """Build LayoutNode tree from VNode tree and reconciled elements.

        Parameters
        ----------
        vnode : VNode
            VNode tree with layout specifications
        reconciled_map : dict
            Map of element key to reconciled element
        state_dict : dict, optional
            Application state dict for scroll/tab state persistence
        root_frame_found : list[bool], optional
            Mutable flag to track if root frame has been found and marked
            for auto-scrolling. Uses a list so the flag can be modified
            across recursive calls.

        Returns
        -------
        LayoutNode
            Root of the layout tree
        """
        from wijjit.core.vdom import LayoutSpec
        from wijjit.layout.frames import Frame

        # Get layout spec from VNode
        layout_dict = vnode.layout_spec_dict()

        # Build LayoutSpec from VNode layout_spec
        # Use the actual fields defined in LayoutSpec dataclass
        layout_spec = LayoutSpec()
        for key, value in layout_dict.items():
            if hasattr(layout_spec, key):
                setattr(layout_spec, key, value)

        # Handle container types (VStack, HStack, Frame)
        if vnode.type == "VStack":
            from wijjit.layout.engine import VStack

            container = VStack(
                width=layout_spec.width or "fill",
                height=layout_spec.height or "auto",
                spacing=layout_spec.spacing or 0,
                padding=layout_spec.padding or 0,
                margin=layout_spec.margin or 0,
                align_h=layout_spec.align_h or "stretch",
                align_v=layout_spec.align_v or "stretch",
            )
            for child_vnode in vnode.children:
                child_node = self._build_layout_tree_from_vnode(
                    child_vnode,
                    reconciled_map,
                    state_dict,
                    root_frame_found=root_frame_found,
                )
                container.add_child(child_node)
            return container

        elif vnode.type == "HStack":
            from wijjit.layout.engine import HStack

            container = HStack(
                width=layout_spec.width or "auto",
                height=layout_spec.height or "auto",
                spacing=layout_spec.spacing or 0,
                padding=layout_spec.padding or 0,
                margin=layout_spec.margin or 0,
                align_h=layout_spec.align_h or "stretch",
                align_v=layout_spec.align_v or "stretch",
                justify=getattr(layout_spec, "justify", None) or "flex-start",
                wrap=getattr(layout_spec, "wrap", False) or False,
                row_gap=getattr(layout_spec, "row_gap", None),
                column_gap=getattr(layout_spec, "column_gap", None),
            )
            for child_vnode in vnode.children:
                child_node = self._build_layout_tree_from_vnode(
                    child_vnode,
                    reconciled_map,
                    state_dict,
                    root_frame_found=root_frame_found,
                )
                container.add_child(child_node)
            return container

        elif vnode.type == "Grid":
            from wijjit.layout.engine import Grid

            props = vnode.props_dict()

            container = Grid(
                rows=props.get("rows", 2),
                cols=props.get("cols", 2),
                row_gap=props.get("row_gap", 0),
                col_gap=props.get("col_gap", 0),
                width=layout_spec.width or "fill",
                height=layout_spec.height or "auto",
                padding=layout_spec.padding or 0,
                margin=layout_spec.margin or 0,
                align_h=layout_spec.align_h or "stretch",
                align_v=layout_spec.align_v or "stretch",
            )
            for child_vnode in vnode.children:
                child_node = self._build_layout_tree_from_vnode(
                    child_vnode,
                    reconciled_map,
                    state_dict,
                    root_frame_found=root_frame_found,
                )
                container.add_child(child_node)
            return container

        elif vnode.type == "GridSpanWrapper":
            from wijjit.layout.engine import GridSpanWrapper

            props = vnode.props_dict()

            # GridSpanWrapper should have exactly one child
            if vnode.children:
                child_node = self._build_layout_tree_from_vnode(
                    vnode.children[0],
                    reconciled_map,
                    state_dict,
                    root_frame_found=root_frame_found,
                )
                return GridSpanWrapper(
                    child=child_node,
                    colspan=props.get("colspan", 1),
                    rowspan=props.get("rowspan", 1),
                )
            else:
                # No child - create placeholder
                from wijjit.elements.base import TextElement
                from wijjit.layout.engine import ElementNode

                placeholder = TextElement(text="[Empty span]")
                return GridSpanWrapper(
                    child=ElementNode(placeholder),
                    colspan=props.get("colspan", 1),
                    rowspan=props.get("rowspan", 1),
                )

        elif vnode.type == "Frame":
            # Frame needs layout dimensions to be created
            # Get width/height from layout_spec
            layout_dict = vnode.layout_spec_dict()
            frame_width = layout_dict.get("width", "fill")
            frame_height = layout_dict.get("height", "fill")

            # Detect if this is the root frame (first frame encountered)
            # Root frames get auto-scroll enabled for views taller than terminal
            is_root_frame = False
            if root_frame_found is not None and not root_frame_found[0]:
                is_root_frame = True
                root_frame_found[0] = True

            # Auto-generate key for root frames without explicit ID so scroll state persists
            frame_key = vnode.key
            if is_root_frame and not frame_key:
                frame_key = "_auto_root_frame"

            # Check if we have a reconciled Frame with same key (for state preservation)
            if frame_key and frame_key in reconciled_map:
                # Reuse reconciled Frame element (preserves scroll state)
                frame_element = reconciled_map[frame_key]
                # Update dimensions if changed
                frame_element.width = frame_width
                frame_element.height = frame_height
                # Enable scrollable on root frame if not already set
                if is_root_frame and not frame_element.style.scrollable:
                    from dataclasses import replace

                    frame_element.style = replace(frame_element.style, scrollable=True)
                logger.debug(f"Reused reconciled Frame {frame_key}")
            else:
                # Create new Frame element with layout dimensions
                props = vnode.props_dict()

                # Import here to avoid circular dependency
                from wijjit.layout.frames import BorderStyle, Frame, FrameStyle

                # Build FrameStyle from props
                border_style = props.get("border_style", BorderStyle.SINGLE)
                title = props.get("title")
                padding = props.get("padding", (0, 1, 0, 1))
                scrollable = props.get("scrollable", False)
                # Root frame gets auto-scroll enabled
                if is_root_frame:
                    scrollable = True
                show_scrollbar = props.get("show_scrollbar", True)
                show_scrollbar_x = props.get("show_scrollbar_x", True)
                overflow_x = props.get("overflow_x", "clip")
                overflow_y = props.get("overflow_y", "clip")
                content_align_h = props.get("content_align_h", "stretch")
                content_align_v = props.get("content_align_v", "stretch")

                style = FrameStyle(
                    border_style=border_style,
                    title=title,
                    padding=padding,
                    content_align_h=content_align_h,
                    content_align_v=content_align_v,
                    scrollable=scrollable,
                    show_scrollbar=show_scrollbar,
                    show_scrollbar_x=show_scrollbar_x,
                    overflow_y=overflow_y,
                    overflow_x=overflow_x,
                )

                frame_element = Frame(
                    width=frame_width,
                    height=frame_height,
                    style=style,
                    id=frame_key,
                )
                # Add to reconciled_map so it can be reused on next render
                if frame_key:
                    reconciled_map[frame_key] = frame_element
                logger.debug(f"Created new Frame {frame_key}")

            # Create FrameNode with content container
            from wijjit.layout.engine import FrameNode, VStack

            # FrameNode constructor expects individual parameters, not layout_spec
            frame_node = FrameNode(
                frame=frame_element,
                width=frame_width,
                height=frame_height,
                margin=layout_spec.margin or 0,
                align_h=layout_spec.align_h or "stretch",
                align_v=layout_spec.align_v or "stretch",
                content_align_h=layout_spec.content_align_h or "stretch",
                content_align_v=layout_spec.content_align_v or "stretch",
            )

            # Create content container (vertical stack for children)
            # Use height="auto" so children stack naturally without overlapping
            content_container = VStack(
                width="fill",
                height="auto",
                spacing=layout_spec.spacing or 0,
            )

            for child_vnode in vnode.children:
                child_node = self._build_layout_tree_from_vnode(
                    child_vnode,
                    reconciled_map,
                    state_dict,
                    root_frame_found=root_frame_found,
                )
                content_container.add_child(child_node)

            frame_node.content_container = content_container
            return frame_node

        elif vnode.type == "SplitPanel":
            # Build SplitPanel from VNode tree with two children
            from wijjit.layout.engine import SplitPanelNode
            from wijjit.layout.splitpanel import SplitPanel

            # Get props from VNode
            props = vnode.props_dict()
            layout_dict = vnode.layout_spec_dict()

            # Parse dimensions
            width_spec = layout_dict.get("width", "fill")
            height_spec = layout_dict.get("height", "fill")

            # Check if we have a reconciled SplitPanel with same key (for state preservation)
            if vnode.key and vnode.key in reconciled_map:
                # Reuse reconciled SplitPanel element (preserves ratio/collapse state)
                split_panel = reconciled_map[vnode.key]
                logger.debug(f"Reused reconciled SplitPanel {vnode.key}")
            else:
                # Create new SplitPanel element
                split_panel = SplitPanel(
                    orientation=props.get("orientation", "horizontal"),
                    ratio=props.get("ratio", "50:50"),
                    resizable=props.get("resizable", True),
                    min_first=props.get("min_first", 5),
                    min_second=props.get("min_second", 5),
                    collapsible=props.get("collapsible", "none"),
                    divider_style=props.get("divider_style", "single"),
                    id=vnode.key,
                )
                # Add to reconciled_map so it can be reused on next render
                if vnode.key:
                    reconciled_map[vnode.key] = split_panel
                logger.debug(f"Created new SplitPanel {vnode.key}")

            # Create SplitPanelNode
            split_node = SplitPanelNode(
                split_panel=split_panel,
                width=width_spec,
                height=height_spec,
                id=vnode.key,
            )

            # Build children (should be exactly 2)
            for child_vnode in vnode.children:
                child_node = self._build_layout_tree_from_vnode(
                    child_vnode,
                    reconciled_map,
                    state_dict,
                    root_frame_found=root_frame_found,
                )
                split_node.add_child(child_node)

            return split_node

        elif vnode.type == "TabbedPanel":
            # Build TabbedPanel from VNode tree with TabContent children
            from wijjit.elements.base import TextElement
            from wijjit.elements.display.tabbed_panel import TabbedPanel, TabPosition
            from wijjit.layout.engine import ElementNode, FrameNode, VStack
            from wijjit.layout.frames import BorderStyle, Frame, FrameStyle

            # Get props from VNode
            props = vnode.props_dict()
            layout_dict = vnode.layout_spec_dict()

            # Parse dimensions
            width_spec = layout_dict.get("width", 60)
            height_spec = layout_dict.get("height", 20)

            # Convert to numeric for element creation
            if isinstance(width_spec, str) and not str(width_spec).isdigit():
                element_width = 60
            else:
                element_width = int(width_spec)

            if isinstance(height_spec, str) and not str(height_spec).isdigit():
                element_height = 20
            else:
                element_height = int(height_spec)

            # Get other props
            tab_pos = props.get("tab_position", TabPosition.TOP)
            border_style = props.get("border_style", "single")
            active_tab_index = props.get("active_tab_index", 0)
            bind = props.get("bind", True)
            classes = props.get("classes")
            active_tab_state_key = props.get("active_tab_state_key")
            focused = props.get("focused", False)

            # Convert border_style string to enum
            border_map = {
                "single": BorderStyle.SINGLE,
                "double": BorderStyle.DOUBLE,
                "rounded": BorderStyle.ROUNDED,
            }
            border_style_enum = border_map.get(border_style, BorderStyle.SINGLE)

            # Check if we have a reconciled TabbedPanel with same key (for state preservation)
            if vnode.key and vnode.key in reconciled_map:
                # Reuse reconciled TabbedPanel element (preserves active_tab_index state)
                tabbed_panel = reconciled_map[vnode.key]
                # Update dimensions if changed
                tabbed_panel.width = element_width
                tabbed_panel.height = element_height
                tabbed_panel.tab_position = tab_pos
                tabbed_panel.border_style = border_style_enum
                # Clear existing tabs - we'll rebuild them from VNode children
                tabbed_panel.tabs.clear()
                logger.debug(f"Reused reconciled TabbedPanel {vnode.key}")
            else:
                # Create new TabbedPanel element
                tabbed_panel = TabbedPanel(
                    id=vnode.key,
                    classes=classes,
                    tab_position=tab_pos,
                    width=element_width,
                    height=element_height,
                    border_style=border_style,
                    active_tab_index=active_tab_index,
                )
                tabbed_panel.bind = bind
                tabbed_panel.focused = focused

                if active_tab_state_key:
                    tabbed_panel.active_tab_state_key = active_tab_state_key

                # Add to reconciled_map so it can be found for event handling
                if vnode.key:
                    reconciled_map[vnode.key] = tabbed_panel
                    logger.debug(
                        f"Created TabbedPanel {vnode.key} and added to reconciled_map"
                    )

            # Wire up state_dict for tab state and scroll persistence
            if state_dict is not None:
                tabbed_panel._state_dict = state_dict

            # Calculate content area dimensions
            if tab_pos in (TabPosition.TOP, TabPosition.BOTTOM):
                frame_width = element_width - 2
                frame_height = element_height - 5
            else:
                # For left/right tabs, estimate tab area width from labels
                tab_children = [c for c in vnode.children if c.type == "TabContent"]
                max_label_width = max(
                    (len(c.props_dict().get("label", "Tab")) for c in tab_children),
                    default=3,
                )
                tab_area_width = max_label_width + 4
                frame_width = element_width - tab_area_width - 1
                frame_height = element_height - 2

            # Process each TabContent child to create tabs
            for tab_index, tab_vnode in enumerate(vnode.children):
                if tab_vnode.type != "TabContent":
                    continue

                tab_props = tab_vnode.props_dict()
                label = tab_props.get("label", "Tab")

                # Create Frame for tab content
                scroll_state_key = (
                    f"_scroll_{vnode.key}_tab_{tab_index}" if vnode.key else None
                )
                frame = Frame(
                    width=frame_width,
                    height=frame_height,
                    style=FrameStyle(
                        scrollable=True,
                        show_scrollbar=True,
                        border_style=BorderStyle.SINGLE,
                    ),
                )
                frame.scroll_state_key = scroll_state_key

                # Wire up state_dict for scroll state persistence
                if state_dict is not None:
                    frame._state_dict = state_dict

                # Build content from TabContent's VNode children
                content_children = []
                for child_vnode in tab_vnode.children:
                    child_node = self._build_layout_tree_from_vnode(
                        child_vnode,
                        reconciled_map,
                        state_dict,
                        root_frame_found=root_frame_found,
                    )
                    content_children.append(child_node)

                # Create FrameNode with content
                frame_node = FrameNode(
                    frame=frame,
                    children=content_children,
                    width=frame_width,
                    height=frame_height,
                )

                # If only text children, extract text for frame content
                has_non_text = any(
                    hasattr(c, "element") and not isinstance(c.element, TextElement)
                    for c in content_children
                )
                if not has_non_text and content_children:
                    text_parts = []
                    for child in content_children:
                        if hasattr(child, "element") and hasattr(child.element, "text"):
                            text_parts.append(child.element.text)
                    if text_parts:
                        frame.set_content("\n".join(text_parts))

                tabbed_panel.add_tab(label, frame_node)

            logger.debug(
                f"Built TabbedPanel from VNode: {vnode.key} with {len(tabbed_panel.tabs)} tabs"
            )

            return ElementNode(tabbed_panel, width=width_spec, height=height_spec)

        elif vnode.type == "Pager":
            # Build Pager from VNode tree with PageContent children
            from wijjit.elements.base import TextElement
            from wijjit.elements.display.pager import Page, Pager
            from wijjit.layout.engine import ElementNode, FrameNode, VStack
            from wijjit.layout.frames import BorderStyle, Frame, FrameStyle

            # Get props from VNode
            props = vnode.props_dict()
            layout_dict = vnode.layout_spec_dict()

            # Parse dimensions
            width_spec = layout_dict.get("width", 60)
            height_spec = layout_dict.get("height", 20)

            # Convert to numeric for element creation
            if isinstance(width_spec, str) and not str(width_spec).isdigit():
                element_width = 60
            else:
                element_width = int(width_spec)

            if isinstance(height_spec, str) and not str(height_spec).isdigit():
                element_height = 20
            else:
                element_height = int(height_spec)

            # Get other props
            nav_position = props.get("nav_position", "bottom")
            show_indicator = props.get("show_indicator", True)
            show_titles = props.get("show_titles", False)
            loop = props.get("loop", False)
            current_page = props.get("current_page", 0)
            border_style = props.get("border_style", "single")
            bind = props.get("bind", True)
            classes = props.get("classes")
            page_state_key = props.get("page_state_key")
            focused = props.get("focused", False)

            # Check if we have a reconciled Pager with same key (for state preservation)
            if vnode.key and vnode.key in reconciled_map:
                # Reuse reconciled Pager element (preserves current_page state)
                pager = reconciled_map[vnode.key]
                # Update dimensions if changed
                pager.width = element_width
                pager.height = element_height
                pager.nav_position = nav_position
                pager.show_indicator = show_indicator
                pager.show_titles = show_titles
                pager.loop = loop
                # Clear existing pages - we'll rebuild them from VNode children
                pager.pages.clear()
                logger.debug(f"Reused reconciled Pager {vnode.key}")
            else:
                # Create new Pager element
                pager = Pager(
                    id=vnode.key,
                    classes=classes,
                    width=element_width,
                    height=element_height,
                    border_style=border_style,
                    nav_position=nav_position,
                    show_indicator=show_indicator,
                    show_titles=show_titles,
                    loop=loop,
                    current_page=current_page,
                )
                pager.bind = bind
                pager.focused = focused

                if page_state_key:
                    pager.page_state_key = page_state_key

                # Add to reconciled_map so it can be found for event handling
                if vnode.key:
                    reconciled_map[vnode.key] = pager
                    logger.debug(
                        f"Created Pager {vnode.key} and added to reconciled_map"
                    )

            # Wire up state_dict for page state persistence
            if state_dict is not None:
                pager._state_dict = state_dict

            # Process each PageContent child to create pages
            for page_index, page_vnode in enumerate(vnode.children):
                if page_vnode.type != "PageContent":
                    continue

                page_props = page_vnode.props_dict()
                title = page_props.get("title", "")
                content = page_props.get("content", "")

                # Check if PageContent has VNode children (complex content)
                if page_vnode.children:
                    # Build content from PageContent's VNode children
                    # Create a Frame to hold the content
                    scroll_state_key = (
                        f"_scroll_{vnode.key}_page_{page_index}" if vnode.key else None
                    )
                    frame = Frame(
                        width=element_width - 2,
                        height=element_height - 4,
                        style=FrameStyle(
                            scrollable=True,
                            show_scrollbar=True,
                            border_style=BorderStyle.SINGLE,
                            title=title if title else None,
                        ),
                    )
                    frame.scroll_state_key = scroll_state_key

                    # Wire up state_dict for scroll state persistence
                    if state_dict is not None:
                        frame._state_dict = state_dict

                    content_children = []
                    for child_vnode in page_vnode.children:
                        child_node = self._build_layout_tree_from_vnode(
                            child_vnode,
                            reconciled_map,
                            state_dict,
                            root_frame_found=root_frame_found,
                        )
                        content_children.append(child_node)

                    # Create FrameNode with content
                    frame_node = FrameNode(
                        frame=frame,
                        children=content_children,
                        width=element_width - 2,
                        height=element_height - 4,
                    )

                    # If only text children, extract text for frame content
                    # Need to recursively check for non-text elements in containers
                    def has_non_text_elements(nodes: list) -> bool:
                        for node in nodes:
                            if hasattr(node, "element"):
                                if not isinstance(node.element, TextElement):
                                    return True
                            # Check container children recursively
                            if hasattr(node, "children") and node.children:
                                if has_non_text_elements(node.children):
                                    return True
                        return False

                    has_non_text = has_non_text_elements(content_children)
                    if not has_non_text and content_children:
                        text_parts = []
                        for child in content_children:
                            if hasattr(child, "element") and hasattr(
                                child.element, "text"
                            ):
                                text_parts.append(child.element.text)
                        if text_parts:
                            frame.set_content("\n".join(text_parts))

                    pager.add_page(Page(title=title, content=frame_node))
                else:
                    # Simple text content
                    pager.add_page(Page(title=title, content=content))

            logger.debug(
                f"Built Pager from VNode: {vnode.key} with {len(pager.pages)} pages"
            )

            return ElementNode(pager, width=width_spec, height=height_spec)

        else:
            # Regular element (TextInput, Button, etc.)
            from wijjit.layout.engine import ElementNode

            if vnode.key and vnode.key in reconciled_map:
                element = reconciled_map[vnode.key]
            else:
                # Element not in reconciled map - this is an error
                logger.warning(
                    f"Element {vnode.key} (type={vnode.type}) not found in "
                    f"reconciled map. This indicates a bug in reconciliation."
                )
                # Create a placeholder - in production this shouldn't happen
                from wijjit.elements.base import TextElement

                element = TextElement(
                    id=vnode.key, text=f"[Missing element: {vnode.type}]"
                )

            # Extract width and height from layout_spec for ElementNode
            width = layout_spec.width if layout_spec.width is not None else "auto"
            height = layout_spec.height if layout_spec.height is not None else "auto"
            return ElementNode(element, width=width, height=height)

    def _compose_output_cells(
        self,
        elements: list[Element],
        width: int,
        height: int,
        root: "LayoutNode | None" = None,
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
        z-order (first to last) using their render_to(ctx) method.
        """
        # Create screen buffer
        buffer = ScreenBuffer(width, height)
        style_resolver = StyleResolver(
            self.theme_manager.get_theme(), focus_color=self.focus_color
        )

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

            # Reset the painted-bounds cache; it is set below only if the
            # element is actually painted this frame (not clipped/scrolled out),
            # so hit-testing never matches a stale or invisible position.
            element._screen_bounds = None

            # Check if element is inside one or more frames (scrollable or not).
            # Walk the FULL parent_frame chain so the element is clipped to the
            # intersection of every ancestor frame's visible content area, and
            # offset by the total scroll of all scrollable ancestors. Clipping to
            # only the innermost frame let a child that was scrolled out of an
            # OUTER frame paint outside it.
            scroll_offset = 0
            clip_region = None
            skip_element = False

            if getattr(element, "parent_frame", None) is not None:
                # Collect the ancestor frame chain, innermost first.
                frame_chain = []
                parent = element.parent_frame
                while parent is not None:
                    frame_chain.append(parent)
                    parent = getattr(parent, "parent_frame", None)

                # Walk outermost -> innermost, accumulating the scroll contributed
                # by frames *outer* than the one being processed (a frame's own
                # scroll offset moves its children, not itself).
                #
                # Only the innermost frame (base clip, preserving historical
                # behavior) and any ancestor that *actually scrolls*
                # (_needs_scroll) contribute to the clip. A non-scrolling
                # ancestor is left out so child frames that slightly overflow a
                # static parent keep rendering as before; the multi-level
                # intersection exists to stop content scrolled out of an outer
                # scrollable frame from painting outside it.
                innermost_frame = frame_chain[0] if frame_chain else None
                outer_scroll = 0
                for frame in reversed(frame_chain):
                    contributes_clip = frame is innermost_frame or (
                        frame.style.scrollable and frame._needs_scroll
                    )
                    if frame.bounds is not None and contributes_clip:
                        padding_top, padding_right, padding_bottom, padding_left = (
                            frame.style.padding
                        )
                        scrollbar_width = (
                            1
                            if frame.style.show_scrollbar and frame._needs_scroll
                            else 0
                        )
                        # This frame's visible content rect, at its on-screen
                        # position (shifted up by the scroll of outer frames).
                        rect = Bounds(
                            x=frame.bounds.x + 1 + padding_left,  # +1 left border
                            y=frame.bounds.y - outer_scroll + 1 + padding_top,
                            width=max(
                                1,
                                frame.bounds.width
                                - 2  # left + right borders
                                - padding_left
                                - padding_right
                                - scrollbar_width,
                            ),
                            height=max(
                                1,
                                frame.bounds.height
                                - 2  # top + bottom borders
                                - padding_top
                                - padding_bottom,
                            ),
                        )
                        if clip_region is None:
                            clip_region = rect
                        else:
                            # Intersect with the running clip; empty => the
                            # element is entirely hidden by an ancestor frame.
                            ix = max(clip_region.x, rect.x)
                            iy = max(clip_region.y, rect.y)
                            ix2 = min(
                                clip_region.x + clip_region.width, rect.x + rect.width
                            )
                            iy2 = min(
                                clip_region.y + clip_region.height,
                                rect.y + rect.height,
                            )
                            if ix2 <= ix or iy2 <= iy:
                                skip_element = True
                                break
                            clip_region = Bounds(
                                x=ix, y=iy, width=ix2 - ix, height=iy2 - iy
                            )

                    # A frame's own scroll shifts the frames nested inside it.
                    if frame.style.scrollable and frame._needs_scroll:
                        outer_scroll += frame.get_scroll_offset()

                scroll_offset = outer_scroll

            if skip_element:
                continue

            # Adjust element bounds for scroll offset
            adjusted_bounds = Bounds(
                x=element.bounds.x,
                y=element.bounds.y - scroll_offset,
                width=element.bounds.width,
                height=element.bounds.height,
            )

            # Skip if element is completely outside visible area
            if clip_region is not None:
                clip_top = clip_region.y
                clip_bottom = clip_region.y + clip_region.height
                if adjusted_bounds.y + adjusted_bounds.height <= clip_top:
                    continue
                if adjusted_bounds.y >= clip_bottom:
                    continue

            # Create paint context for this element with clip region
            ctx = PaintContext(
                buffer=buffer,
                style_resolver=style_resolver,
                bounds=adjusted_bounds,
                clip_region=clip_region,
            )

            # Render element using cell-based rendering
            element.render_to(ctx)

            # Record the on-screen rect actually painted (scroll-adjusted and
            # clipped to the visible area) so mouse hit-testing matches where
            # the element visually appears, not its unscrolled logical bounds.
            if clip_region is not None:
                element._screen_bounds = adjusted_bounds.intersect(clip_region)
            else:
                element._screen_bounds = adjusted_bounds

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

        # NOTE: Dirty regions are NOT cleared here because overlay compositing
        # may still need them. The caller (app._render) will clear them after
        # all compositing is complete.

        # Return both output and buffer
        return output, buffer

    def _render_frames_to_buffer(
        self,
        node: "LayoutNode",
        buffer: ScreenBuffer,
        style_resolver: StyleResolver,
        scroll_offset: int = 0,
        clip_region: Bounds | None = None,
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
        scroll_offset : int, optional
            Vertical scroll offset from parent scrollable frame (default: 0)
        clip_region : Bounds, optional
            Clip region from parent scrollable frame (default: None)

        Notes
        -----
        This recursively walks the layout tree and renders frame borders
        to the cell buffer. Frame content is not rendered here - only
        the border decorations.

        When rendering frames inside a scrollable parent, the scroll_offset
        and clip_region are passed down to adjust positions and prevent
        rendering outside the visible area.
        """
        # Render this frame's border if it's a FrameNode
        if isinstance(node, FrameNode):
            frame = node.frame
            bounds = frame.bounds
            if bounds is None:
                return
            style = frame.style

            # Reset painted-bounds cache; set below once the frame is confirmed
            # at least partially visible (see the element pass for rationale).
            frame._screen_bounds = None

            # Adjust bounds for scroll offset if inside a scrollable parent
            if scroll_offset != 0:
                adjusted_bounds = Bounds(
                    x=bounds.x,
                    y=bounds.y - scroll_offset,
                    width=bounds.width,
                    height=bounds.height,
                )
            else:
                adjusted_bounds = bounds

            # Skip if frame is completely outside clip region
            if clip_region is not None:
                clip_top = clip_region.y
                clip_bottom = clip_region.y + clip_region.height
                if adjusted_bounds.y + adjusted_bounds.height <= clip_top:
                    return  # Frame is above visible area
                if adjusted_bounds.y >= clip_bottom:
                    return  # Frame is below visible area

            # Record the frame's painted on-screen rect for hit-testing (e.g.
            # routing scroll-wheel events to a scrolled, nested frame).
            frame._screen_bounds = (
                adjusted_bounds.intersect(clip_region)
                if clip_region is not None
                else adjusted_bounds
            )

            # Resolve frame border style from theme. Mirror Frame.render_to's
            # focus handling: a frame whose body holds child elements draws its
            # top/bottom borders (focus-aware) in Frame.render_to but skips the
            # body, so the vertical side borders come only from THIS pass. If we
            # ignored focus here, those verticals would stay the unfocused color
            # while the top/bottom went focus-colored - the "half-highlighted"
            # frame glitch. Resolving the ``:focus`` border when focused keeps
            # all four sides consistent.
            prefix = frame.style_prefix
            if frame.focused:
                border_style = style_resolver.resolve_style(
                    frame, f"{prefix}.border:focus"
                )
            else:
                border_style = style_resolver.resolve_style_by_class(f"{prefix}.border")

            # Get border characters
            border_chars = BORDER_CHARS.get(
                style.border_style, BORDER_CHARS[BorderStyle.SINGLE]
            )

            # Create paint context for frame with adjusted bounds and clip region
            ctx = PaintContext(buffer, style_resolver, adjusted_bounds, clip_region)

            # Draw frame border
            ctx.draw_border(
                0,
                0,
                adjusted_bounds.width,
                adjusted_bounds.height,
                border_style,
                border_chars,
            )

            # Draw title if present (left-aligned like Frame.render_to)
            if style.title:
                title_text = f" {style.title} "
                title_len = visible_length(title_text)

                # Left align after the first horizontal character when space allows
                title_x = 2 if adjusted_bounds.width > 4 else 1

                if title_x + title_len >= adjusted_bounds.width - 1:
                    # Not enough space - fall back to starting right after corner
                    title_x = 1

                # Resolve frame title style (matches runtime rendering)
                title_style = style_resolver.resolve_style(frame, "frame.title")
                ctx.write_text(title_x, 0, title_text, title_style, clip=True)

            # Calculate scroll context for children if this frame is scrollable
            child_scroll_offset = scroll_offset
            child_clip_region = clip_region

            if style.scrollable and frame._needs_scroll:
                # This frame is scrollable - set up scroll context for children
                child_scroll_offset = scroll_offset + frame.get_scroll_offset()

                # Calculate clip region (visible content area inside frame)
                padding_top, padding_right, padding_bottom, padding_left = style.padding
                scrollbar_width = (
                    1 if style.show_scrollbar and frame._needs_scroll else 0
                )

                # Use adjusted_bounds for clip calculation since children render relative to scrolled position
                new_clip_x = adjusted_bounds.x + 1 + padding_left
                new_clip_y = adjusted_bounds.y + 1 + padding_top
                new_clip_width = (
                    adjusted_bounds.width
                    - 2  # Left and right borders
                    - padding_left
                    - padding_right
                    - scrollbar_width
                )
                new_clip_height = (
                    adjusted_bounds.height
                    - 2  # Top and bottom borders
                    - padding_top
                    - padding_bottom
                )

                child_clip_region = Bounds(
                    x=new_clip_x,
                    y=new_clip_y,
                    width=max(1, new_clip_width),
                    height=max(1, new_clip_height),
                )

            # Recursively render children with scroll context
            for child in node.content_container.children:
                self._render_frames_to_buffer(
                    child,
                    buffer,
                    style_resolver,
                    child_scroll_offset,
                    child_clip_region,
                )

        elif isinstance(node, Container):
            # Regular container - pass scroll context through
            for child in node.children:
                self._render_frames_to_buffer(
                    child, buffer, style_resolver, scroll_offset, clip_region
                )

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

        When use_diff_rendering is True::

            First render is full (with screen clear), subsequent renders
            only output changes (diffs).

        When use_diff_rendering is False::

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
        overlay_manager: "OverlayManager | None" = None,
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
        style_resolver = StyleResolver(
            self.theme_manager.get_theme(), focus_color=self.focus_color
        )

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
        overlay_manager: "OverlayManager | None" = None,
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

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._string_templates.clear()

    def clear_element_cache(self) -> None:
        """Clear the reconciler element cache and VNode tree.

        This should be called when navigating to a different view
        to avoid stale ephemeral state transfer.
        """
        self._reconciler.clear_cache()
        self._last_vnode_tree = None
