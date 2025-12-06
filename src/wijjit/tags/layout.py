"""Jinja2 template extensions for layout elements.

This module provides Jinja2 template tag extensions for layout containers
including frames, vertical stacks (vstack), and horizontal stacks (hstack).
Also provides utility functions for processing template body content.
"""

from __future__ import annotations

import re
import textwrap
from ast import literal_eval
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, cast

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.core.render_context import get_render_context
from wijjit.core.vdom import VNodeBuilder
from wijjit.layout.frames import BorderStyle
from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Pre-compiled regex patterns for element marker handling
# Pattern to match element markers (with capture group for digit extraction)
_MARKER_EXTRACT_PATTERN = re.compile(r"\x00ELEM_(\d+)\x00")
# Pattern for splitting (without capture group to avoid nested groups)
_MARKER_SPLIT_PATTERN = re.compile(r"(\x00ELEM_\d+\x00)")


def safe_int(value: Any, default: int = 0, name: str = "value") -> int:
    """Safely convert a value to int with error handling.

    Parameters
    ----------
    value : Any
        Value to convert to int
    default : int, optional
        Default value if conversion fails (default: 0)
    name : str, optional
        Name of the value for logging (default: "value")

    Returns
    -------
    int
        Converted integer or default value
    """
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid {name} '{value}', using default {default}: {e}")
        return default


def parse_tag_attributes(
    parser: Parser, end_tag: str, lineno: int
) -> list[nodes.Keyword]:
    """Parse tag attributes as keyword arguments.

    This helper consolidates the common attribute parsing pattern used by all
    template tag extensions. It parses key=value pairs until it encounters
    the end tag.

    Parameters
    ----------
    parser : Parser
        Jinja2 parser instance
    end_tag : str
        The end tag name (e.g., "endvstack", "endbutton")
    lineno : int
        Line number for creating Keyword nodes

    Returns
    -------
    list[nodes.Keyword]
        List of parsed keyword arguments
    """
    kwargs: list[nodes.Keyword] = []
    while parser.stream.current.test("name") and not parser.stream.current.test(
        f"name:{end_tag}"
    ):
        key = parser.stream.expect("name").value
        if parser.stream.current.test("assign"):
            parser.stream.expect("assign")
            value = parser.parse_expression()
            kwargs.append(nodes.Keyword(key, value, lineno=lineno))
        else:
            break
    return kwargs


def process_body_content(body_output: str, raw: bool = False) -> str:
    """Process template body content with optional whitespace stripping.

    Parameters
    ----------
    body_output : str
        Raw body content from caller()
    raw : bool, optional
        If True, preserve whitespace. If False, dedent and strip (default: False)

    Returns
    -------
    str
        Processed body content
    """
    if not body_output or not body_output.strip():
        return ""

    if raw:
        # Raw mode: preserve all whitespace
        return body_output
    else:
        # Default mode: dedent and strip
        return textwrap.dedent(body_output).strip()


def interleave_text_and_vnode_builders(
    body_output: str,
    vnode_children: list,
    raw: bool,
    layout_context,
) -> list:
    """Interleave text content with child VNodeBuilders based on markers.

    Child elements insert markers like '\x00ELEM_0\x00' into body_output
    to indicate their position in the template source. This function
    parses those markers and rebuilds the children list with text
    VNodes interleaved at the correct positions.

    Parameters
    ----------
    body_output : str
        Template body output containing text and element markers
    vnode_children : list
        Child VNodeBuilders that were added (in order they were added)
    raw : bool
        If True, preserve whitespace in text. If False, dedent/strip
    layout_context : LayoutContext
        Layout context for generating unique keys

    Returns
    -------
    list
        New children list with text and elements properly interleaved as VNodeBuilders
    """
    from wijjit.core.vdom import VNodeBuilder

    # Split body_output on markers, keeping the markers
    parts = _MARKER_SPLIT_PATTERN.split(body_output)

    result = []

    for part in parts:
        # Check if this is a marker
        marker_match = _MARKER_EXTRACT_PATTERN.match(part)
        if marker_match:
            # This is an element marker
            elem_index = int(marker_match.group(1))
            if 0 <= elem_index < len(vnode_children):
                result.append(vnode_children[elem_index])
            else:
                # Out-of-range marker - this indicates a template processing bug
                logger.warning(
                    f"Element marker index {elem_index} out of range "
                    f"(0-{len(vnode_children) - 1}). Element may be missing from output."
                )
        else:
            # This is text content
            processed_text = process_body_content(part, raw=raw)
            if processed_text:
                # Generate unique key for text element
                text_key = layout_context.generate_id("text")

                # Create TextElement VNodeBuilder with key
                text_vnode = VNodeBuilder("TextElement", key=text_key)
                text_vnode.set_prop("id", text_key)  # Set id prop for reconciler cache
                text_vnode.set_prop("text", processed_text)
                text_vnode.set_prop("wrap", not raw)
                text_vnode.set_layout(width="auto", height="auto")
                result.append(text_vnode)

    return result


def get_element_marker(layout_context: LayoutContext) -> str:
    """Get marker for element that was just added to layout context.

    This should be called after add_vnode() to get the marker string
    for the element that was just added. The marker indicates the element's
    position in the parent's VNode children list.

    Parameters
    ----------
    layout_context : LayoutContext
        Layout context

    Returns
    -------
    str
        Marker string to return from element extension (e.g., '\x00ELEM_0\x00')
    """
    if layout_context.vnode_stack:
        parent = layout_context.vnode_stack[-1]
        # Get index of element that was just added to the VNode tree
        elem_index = len(parent.children) - 1
        return f"\x00ELEM_{elem_index}\x00"
    return ""


class LayoutContext:
    """Context for building layout tree during template rendering.

    The VNode stack is used for VNode-based reconciliation. The renderer
    builds the final layout tree from the VNode tree via `_build_layout_tree_from_vnode()`.

    Attributes
    ----------
    element_counters : dict
        Counter for auto-generating element IDs by type
    vnode_root : VNodeBuilder or None
        Root of the VNode tree (for reconciliation)
    vnode_stack : list of VNodeBuilder
        Stack of VNodeBuilders being processed
    element_vnodes : dict
        Map of element ID -> VNodeBuilder for element lookup
    """

    def __init__(self) -> None:
        self.element_counters: dict[str, int] = {}

        # VNode tree tracking for reconciliation
        self.vnode_root: Any | None = None  # VNodeBuilder
        self.vnode_stack: list[Any] = []  # list[VNodeBuilder]
        self.element_vnodes: dict[str, Any] = {}  # id -> VNodeBuilder

    def generate_id(self, element_type: str) -> str:
        """Generate a unique ID for an element.

        Parameters
        ----------
        element_type : str
            Type of element (e.g., 'button', 'textinput')

        Returns
        -------
        str
            Generated ID in format 'element_type_N'
        """
        if element_type not in self.element_counters:
            self.element_counters[element_type] = 0

        id_value = f"{element_type}_{self.element_counters[element_type]}"
        self.element_counters[element_type] += 1
        return id_value

    # === VNode Tree Building Methods ===

    def push_vnode(self, vnode_builder: Any) -> None:
        """Push a VNodeBuilder onto the VNode stack.

        Parameters
        ----------
        vnode_builder : VNodeBuilder
            VNode builder to push (container type)
        """
        if self.vnode_root is None:
            self.vnode_root = vnode_builder

        if self.vnode_stack:
            parent = self.vnode_stack[-1]
            parent.add_child(vnode_builder)

        self.vnode_stack.append(vnode_builder)

        # Track by ID if present
        if vnode_builder.key:
            self.element_vnodes[vnode_builder.key] = vnode_builder

    def pop_vnode(self) -> Any | None:
        """Pop a VNodeBuilder from the VNode stack.

        Returns
        -------
        VNodeBuilder or None
            Popped builder
        """
        if self.vnode_stack:
            return self.vnode_stack.pop()
        return None

    def add_vnode(self, vnode_builder: Any) -> None:
        """Add a leaf VNodeBuilder to the current container.

        Parameters
        ----------
        vnode_builder : VNodeBuilder
            VNode builder to add (leaf element)
        """
        if self.vnode_root is None:
            self.vnode_root = vnode_builder
            if vnode_builder.key:
                self.element_vnodes[vnode_builder.key] = vnode_builder
            return

        if self.vnode_stack:
            parent = self.vnode_stack[-1]
            parent.add_child(vnode_builder)

        # Track by ID if present
        if vnode_builder.key:
            self.element_vnodes[vnode_builder.key] = vnode_builder

    def freeze_vnode_tree(self) -> Any | None:
        """Freeze the VNode tree into immutable VNodes.

        Returns
        -------
        VNode or None
            Frozen VNode tree root
        """
        if self.vnode_root is None:
            return None
        return self.vnode_root.freeze()


def parse_size_attr(value: Any) -> Any:
    """Parse a size attribute value.

    Parameters
    ----------
    value : Any
        Attribute value (could be int, str, etc.)

    Returns
    -------
    Any
        Parsed size value
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Handle percentage or fill
        if value.endswith("%") or value in ("fill", "auto"):
            return value
        # Try to parse as int
        try:
            return int(value)
        except ValueError:
            return value
    return value


def _parse_for_render(
    width: int | str = "fill",
    height: int | str = "fill",
    spacing: int = 0,
    padding: int | str | tuple[int, ...] = 0,
    padding_top: int | None = None,
    padding_right: int | None = None,
    padding_bottom: int | None = None,
    padding_left: int | None = None,
    margin: int | str | tuple[int, ...] = 0,
) -> tuple:
    """Calculate the attributes for rendering"""
    # Parse attributes
    width_parsed = parse_size_attr(width)
    height_parsed = parse_size_attr(height)
    spacing_int = safe_int(spacing, default=0, name="spacing")

    # Parse padding - could be int, tuple, or directional attributes
    padding_parsed: int | tuple[int, int, int, int]
    if isinstance(padding, str) and padding.startswith("("):
        # Parse tuple string like "(1,2,3,4)"
        try:
            padding_parsed = literal_eval(padding)
        except (ValueError, SyntaxError, NameError):
            padding_parsed = 0
    elif isinstance(padding, tuple):
        padding_parsed = padding
    elif isinstance(padding, str):
        try:
            padding_parsed = int(padding)
        except ValueError:
            padding_parsed = 0
    else:
        padding_parsed = int(padding) if padding else 0

    # Apply directional padding overrides
    if any(
        [
            padding_top is not None,
            padding_right is not None,
            padding_bottom is not None,
            padding_left is not None,
        ]
    ):
        # Convert base padding to tuple if needed
        if isinstance(padding_parsed, int):
            base = padding_parsed
            padding_tuple = (base, base, base, base)
        else:
            padding_tuple = padding_parsed

        # Override with directional values
        padding_parsed = (
            padding_top if padding_top is not None else padding_tuple[0],
            padding_right if padding_right is not None else padding_tuple[1],
            padding_bottom if padding_bottom is not None else padding_tuple[2],
            padding_left if padding_left is not None else padding_tuple[3],
        )

    # Parse margin
    margin_parsed: int | tuple[int, int, int, int]
    if isinstance(margin, str) and margin.startswith("("):
        try:
            margin_parsed = literal_eval(margin)
        except (ValueError, SyntaxError, NameError):
            margin_parsed = 0
    elif isinstance(margin, str):
        try:
            margin_parsed = int(margin)
        except ValueError:
            margin_parsed = 0
    else:
        margin_parsed = cast(int, margin)

    return width_parsed, height_parsed, spacing_int, padding_parsed, margin_parsed


class VStackExtension(Extension):
    """Jinja2 extension for {% vstack %} tag.

    Syntax:
        {% vstack width="fill" height="auto" spacing=0 padding=0
                  margin=0 align_h="stretch" align_v="stretch" %}
            ... children ...
        {% endvstack %}
    """

    tags = {"vstack"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the vstack tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endvstack", lineno)

        # Parse body
        node = nodes.CallBlock(
            self.call_method("_render_vstack", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endvstack",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_vstack(
        self,
        caller: Callable[[], str],
        width: int | str = "fill",
        height: int | str = "auto",
        spacing: int = 0,
        padding: int | str | tuple[int, ...] = 0,
        padding_top: int | None = None,
        padding_right: int | None = None,
        padding_bottom: int | None = None,
        padding_left: int | None = None,
        margin: int | str | tuple[int, ...] = 0,
        align_h: str = "stretch",
        align_v: str = "stretch",
        raw: bool = False,
        id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the vstack tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        width : int or str
            Width specification (default: "fill")
        height : int or str
            Height specification (default: "fill")
        spacing : int
            Spacing between children
        padding : int or str or tuple
            Padding around children (uniform or tuple: top, right, bottom, left)
        padding_top : int, optional
            Top padding (overrides padding)
        padding_right : int, optional
            Right padding (overrides padding)
        padding_bottom : int, optional
            Bottom padding (overrides padding)
        padding_left : int, optional
            Left padding (overrides padding)
        margin : int or tuple
            Margin around container
        align_h : str
            Horizontal alignment of children
        align_v : str
            Vertical alignment of children
        raw : bool, optional
            If True, preserve whitespace in body content. If False, dedent and strip (default: False)
        id : str, optional
            Node identifier

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context

        width_parsed, height_parsed, spacing_int, padding_parsed, margin_parsed = (
            _parse_for_render(
                width,
                height,
                spacing,
                padding,
                padding_top,
                padding_right,
                padding_bottom,
                padding_left,
                margin,
            )
        )

        # Create VNode builder for reconciliation
        vnode = VNodeBuilder("VStack", key=id)
        vnode.set_layout(
            width=width_parsed,
            height=height_parsed,
            spacing=spacing_int,
            padding=padding_parsed,
            margin=margin_parsed,
            align_h=align_h,
            align_v=align_v,
        )
        layout_context.push_vnode(vnode)

        # Render body - nested elements will add themselves via push_vnode/add_vnode
        # and insert markers in body_output to indicate their positions
        body_output = caller()

        # Handle text content for VNodes
        vnode_children = vnode.children

        if not vnode_children and body_output.strip():
            # No VNode children and has text - create a single TextElement VNode
            processed_text = process_body_content(body_output, raw=raw)
            if processed_text:
                text_key = layout_context.generate_id("text")
                text_vnode = VNodeBuilder("TextElement", key=text_key)
                text_vnode.set_prop("id", text_key)
                text_vnode.set_prop("text", processed_text)
                text_vnode.set_prop("wrap", not raw)
                text_vnode.set_layout(width="auto", height="auto")
                vnode.add_child(text_vnode)
        elif vnode_children:
            # Has VNode children - interleave text and VNodes in source order
            interleaved_vnode_builders = interleave_text_and_vnode_builders(
                body_output, vnode_children, raw, layout_context
            )
            vnode.children = interleaved_vnode_builders

        # Pop VNode from stack
        layout_context.pop_vnode()

        # Return marker for text interleaving
        return get_element_marker(layout_context)


class HStackExtension(Extension):
    """Jinja2 extension for {% hstack %} tag.

    Syntax:
        {% hstack width="auto" height="fill" spacing=0 padding=0
                  margin=0 align_h="stretch" align_v="stretch" %}
            ... children ...
        {% endhstack %}
    """

    tags = {"hstack"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the hstack tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endhstack", lineno)

        # Parse body
        node = nodes.CallBlock(
            self.call_method("_render_hstack", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endhstack",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_hstack(
        self,
        caller: Callable[[], str],
        width: int | str = "auto",
        height: int | str = "auto",
        spacing: int = 0,
        padding: int | str | tuple[int, ...] = 0,
        padding_top: int | None = None,
        padding_right: int | None = None,
        padding_bottom: int | None = None,
        padding_left: int | None = None,
        margin: int | str | tuple[int, ...] = 0,
        align_h: str = "stretch",
        align_v: str = "stretch",
        raw: bool = False,
        id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the hstack tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        width : int or str
            Width specification (default: "auto")
        height : int or str
            Height specification (default: "auto")
        spacing : int
            Spacing between children
        padding : int or str or tuple
            Padding around children (uniform or tuple: top, right, bottom, left)
        padding_top : int, optional
            Top padding (overrides padding)
        padding_right : int, optional
            Right padding (overrides padding)
        padding_bottom : int, optional
            Bottom padding (overrides padding)
        padding_left : int, optional
            Left padding (overrides padding)
        margin : int or tuple
            Margin around container
        align_h : str
            Horizontal alignment of children
        align_v : str
            Vertical alignment of children
        raw : bool, optional
            If True, preserve whitespace in body content. If False, dedent and strip (default: False)
        id : str, optional
            Node identifier

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context

        width_parsed, height_parsed, spacing_int, padding_parsed, margin_parsed = (
            _parse_for_render(
                width,
                height,
                spacing,
                padding,
                padding_top,
                padding_right,
                padding_bottom,
                padding_left,
                margin,
            )
        )

        # Create VNode builder for reconciliation
        vnode = VNodeBuilder("HStack", key=id)
        vnode.set_layout(
            width=width_parsed,
            height=height_parsed,
            spacing=spacing_int,
            padding=padding_parsed,
            margin=margin_parsed,
            align_h=align_h,
            align_v=align_v,
        )
        layout_context.push_vnode(vnode)

        # Render body - nested elements will add themselves via push_vnode/add_vnode
        # and insert markers in body_output to indicate their positions
        body_output = caller()

        # Handle text content for VNodes
        vnode_children = vnode.children

        if not vnode_children and body_output.strip():
            # No VNode children and has text - create a single TextElement VNode
            processed_text = process_body_content(body_output, raw=raw)
            if processed_text:
                text_key = layout_context.generate_id("text")
                text_vnode = VNodeBuilder("TextElement", key=text_key)
                text_vnode.set_prop("id", text_key)
                text_vnode.set_prop("text", processed_text)
                text_vnode.set_prop("wrap", not raw)
                text_vnode.set_layout(width="auto", height="auto")
                vnode.add_child(text_vnode)
        elif vnode_children:
            # Has VNode children - interleave text and VNodes in source order
            interleaved_vnode_builders = interleave_text_and_vnode_builders(
                body_output, vnode_children, raw, layout_context
            )
            vnode.children = interleaved_vnode_builders

        # Pop VNode from stack
        layout_context.pop_vnode()

        # Return marker for text interleaving
        return get_element_marker(layout_context)


class FrameExtension(Extension):
    """Jinja2 extension for {% frame %} tag.

    Syntax:
        {% frame title="Title" border_style="single" width="fill" height="auto"
                 margin=0 align_h="stretch" align_v="stretch"
                 content_align_h="stretch" content_align_v="stretch" %}
            ... content ...
        {% endframe %}
    """

    tags = {"frame"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the frame tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endframe", lineno)

        # Parse body
        node = nodes.CallBlock(
            self.call_method("_render_frame", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endframe",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_frame(
        self,
        caller: Callable[[], str],
        width: int | str = "fill",
        height: int | str = "auto",
        title: str | None = None,
        border_style: str = "single",
        margin: int | str | tuple[int, ...] = 0,
        padding: int | str | tuple[int, ...] | None = None,
        align_h: str = "stretch",
        align_v: str = "stretch",
        content_align_h: str = "stretch",
        content_align_v: str = "stretch",
        overflow_x: str = "clip",
        scrollable: bool = False,
        show_scrollbar: bool = True,
        show_scrollbar_x: bool = True,
        raw: bool = False,
        id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the frame tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        width : int or str
            Width specification
        height : int or str
            Height specification
        title : str, optional
            Frame title
        border_style : str
            Border style
        margin : int or tuple, optional
            Margin around frame (default: 0)
        padding : int or tuple, optional
            Padding inside frame (top, right, bottom, left). Can be int for uniform padding or tuple
        align_h : str, optional
            Horizontal alignment of frame within parent (default: "stretch")
        align_v : str, optional
            Vertical alignment of frame within parent (default: "stretch")
        content_align_h : str, optional
            Horizontal alignment of content within frame (default: "stretch")
        content_align_v : str, optional
            Vertical alignment of content within frame (default: "stretch")
        overflow_x : str, optional
            Horizontal overflow mode: "clip", "visible", "wrap", "scroll", or "auto" (default: "clip")
            - "scroll": Enable horizontal scrolling with scrollbar
            - "auto": Enable horizontal scrolling only when content exceeds width
        scrollable : bool, optional
            Enable vertical scrolling (default: False)
        show_scrollbar : bool, optional
            Show vertical scrollbar when scrollable (default: True)
        show_scrollbar_x : bool, optional
            Show horizontal scrollbar when overflow_x is "scroll" or "auto" (default: True)
        raw : bool, optional
            If True, preserve whitespace in body content. If False, dedent and strip (default: False)
        id : str, optional
            Node identifier

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context

        # Auto-generate ID for scrollable frames if not provided
        if scrollable and not id:
            id = render_ctx.generate_frame_id()

        # Parse attributes
        width_parsed = parse_size_attr(width)
        height_parsed = parse_size_attr(height)

        # Parse margin - could be int or tuple string like "(1,2,3,4)"
        margin_parsed: int | tuple[int, int, int, int]
        if isinstance(margin, str) and margin.startswith("("):
            # Parse tuple string
            try:
                margin_parsed = literal_eval(margin)
            except (ValueError, SyntaxError, NameError):
                margin_parsed = 0
        elif isinstance(margin, str):
            try:
                margin_parsed = int(margin)
            except ValueError:
                margin_parsed = 0
        else:
            margin_parsed = cast(int, margin)

        # Parse border style
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        border_style_enum = border_map.get(border_style, BorderStyle.SINGLE)

        # Parse padding - could be int or tuple string like "(1,2,3,4)"
        padding_parsed: tuple[int, int, int, int]
        if padding is None:
            padding_parsed = (0, 1, 0, 1)  # Default padding: horizontal only
        elif isinstance(padding, int):
            padding_parsed = (padding, padding, padding, padding)
        elif isinstance(padding, str) and padding.startswith("("):
            # Parse tuple string
            try:
                padding_parsed = cast(tuple[int, int, int, int], literal_eval(padding))
            except (ValueError, SyntaxError, NameError):
                padding_parsed = (1, 1, 1, 1)
        elif isinstance(padding, str):
            try:
                p = int(padding)
                padding_parsed = (p, p, p, p)
            except ValueError:
                padding_parsed = (1, 1, 1, 1)
        else:
            padding_parsed = (1, 1, 1, 1)

        # Parse overflow_y from scrollable parameter
        overflow_y: Literal["clip", "scroll", "auto"]
        if scrollable:
            overflow_y = "auto"
        else:
            overflow_y = "clip"

        # Create VNode builder for reconciliation
        # The renderer will create the actual Frame element from these props
        vnode = VNodeBuilder("Frame", key=id)
        vnode.set_prop("border_style", border_style_enum)
        vnode.set_prop("title", title)
        vnode.set_prop("scrollable", scrollable)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("show_scrollbar_x", show_scrollbar_x)
        vnode.set_prop("overflow_x", overflow_x)
        vnode.set_prop("overflow_y", overflow_y)
        vnode.set_layout(
            width=width_parsed,
            height=height_parsed,
            padding=padding_parsed,
            margin=margin_parsed,
            align_h=align_h,
            align_v=align_v,
            content_align_h=content_align_h,
            content_align_v=content_align_v,
        )
        layout_context.push_vnode(vnode)

        # Render body - nested elements will add themselves via push_vnode/add_vnode
        # and insert markers in body_output to indicate their positions
        body_output = caller()

        # Handle text content for VNodes
        vnode_children = vnode.children

        if not vnode_children and body_output.strip():
            # No VNode children and has text - create a single TextElement VNode
            processed_text = process_body_content(body_output, raw=raw)
            if processed_text:
                text_key = layout_context.generate_id("text")
                text_vnode = VNodeBuilder("TextElement", key=text_key)
                text_vnode.set_prop("id", text_key)
                text_vnode.set_prop("text", processed_text)
                text_vnode.set_prop("wrap", not raw)
                text_vnode.set_layout(width="auto", height="auto")
                vnode.add_child(text_vnode)
        elif vnode_children:
            # Has VNode children - interleave text and VNodes in source order
            interleaved_vnode_builders = interleave_text_and_vnode_builders(
                body_output, vnode_children, raw, layout_context
            )
            vnode.children = interleaved_vnode_builders

        # Pop VNode from stack
        layout_context.pop_vnode()

        # Return marker for text interleaving
        return get_element_marker(layout_context)


class GridExtension(Extension):
    """Jinja2 extension for {% grid %} tag.

    Syntax:
        {% grid rows=2 cols=3 row_gap=1 col_gap=2 %}
            ... children ...
        {% endgrid %}
    """

    tags = {"grid"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the grid tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endgrid", lineno)

        # Parse body
        node = nodes.CallBlock(
            self.call_method("_render_grid", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endgrid",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_grid(
        self,
        caller: Callable[[], str],
        rows: int = 2,
        cols: int = 2,
        row_gap: int = 0,
        col_gap: int = 0,
        width: int | str = "fill",
        height: int | str = "auto",
        padding: int | str | tuple[int, ...] = 0,
        margin: int | str | tuple[int, ...] = 0,
        align_h: str = "stretch",
        align_v: str = "stretch",
        id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the grid tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        rows : int
            Number of rows in the grid (default: 2)
        cols : int
            Number of columns in the grid (default: 2)
        row_gap : int
            Vertical gap between rows (default: 0)
        col_gap : int
            Horizontal gap between columns (default: 0)
        width : int or str
            Width specification (default: "fill")
        height : int or str
            Height specification (default: "auto")
        padding : int or str or tuple
            Padding around the grid (default: 0)
        margin : int or str or tuple
            Margin around the grid (default: 0)
        align_h : str
            Horizontal alignment within cells (default: "stretch")
        align_v : str
            Vertical alignment within cells (default: "stretch")
        id : str, optional
            Node identifier

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context

        # Parse attributes
        width_parsed = parse_size_attr(width)
        height_parsed = parse_size_attr(height)
        rows_int = int(rows)
        cols_int = int(cols)
        row_gap_int = int(row_gap)
        col_gap_int = int(col_gap)

        # Parse padding and margin
        _, _, _, padding_parsed, margin_parsed = _parse_for_render(
            width, height, 0, padding, None, None, None, None, margin
        )

        # Create VNode builder for reconciliation
        vnode = VNodeBuilder("Grid", key=id)
        vnode.set_prop("rows", rows_int)
        vnode.set_prop("cols", cols_int)
        vnode.set_prop("row_gap", row_gap_int)
        vnode.set_prop("col_gap", col_gap_int)
        vnode.set_layout(
            width=width_parsed,
            height=height_parsed,
            padding=padding_parsed,
            margin=margin_parsed,
            align_h=align_h,
            align_v=align_v,
        )
        layout_context.push_vnode(vnode)

        # Render body - nested elements will add themselves via push_vnode/add_vnode
        body_output = caller()

        # Handle text content for VNodes
        vnode_children = vnode.children

        if vnode_children:
            # Has VNode children - interleave in source order
            interleaved_vnode_builders = interleave_text_and_vnode_builders(
                body_output, vnode_children, False, layout_context
            )
            vnode.children = interleaved_vnode_builders

        # Pop VNode from stack
        layout_context.pop_vnode()

        # Return marker for text interleaving
        return get_element_marker(layout_context)


class ColspanExtension(Extension):
    """Jinja2 extension for {% colspan %} tag.

    Syntax:
        {% colspan cols=2 %}
            {% frame %}Content{% endframe %}
        {% endcolspan %}
    """

    tags = {"colspan"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the colspan tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endcolspan", lineno)

        # Parse body
        node = nodes.CallBlock(
            self.call_method("_render_colspan", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endcolspan",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_colspan(
        self,
        caller: Callable[[], str],
        cols: int = 1,
        **kwargs: Any,
    ) -> str:
        """Render the colspan wrapper.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        cols : int
            Number of columns to span (default: 1)

        Returns
        -------
        str
            Rendered output
        """
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context

        # Create wrapper VNode
        vnode = VNodeBuilder("GridSpanWrapper")
        vnode.set_prop("colspan", int(cols))
        vnode.set_prop("rowspan", 1)
        layout_context.push_vnode(vnode)

        # Render child content
        body_output = caller()

        # Get the children
        vnode_children = vnode.children

        # Wrapper should have exactly one child element
        if vnode_children:
            # Interleave to preserve order (though we expect only 1 child)
            interleaved = interleave_text_and_vnode_builders(
                body_output, vnode_children, False, layout_context
            )
            # Filter to only element vnodes (ignore text-only vnodes)
            element_children = [c for c in interleaved if c.type != "TextElement"]
            if len(element_children) != 1:
                logger.warning(
                    f"colspan wrapper should contain exactly 1 element, "
                    f"got {len(element_children)}"
                )
            vnode.children = interleaved

        layout_context.pop_vnode()

        return get_element_marker(layout_context)


class RowspanExtension(Extension):
    """Jinja2 extension for {% rowspan %} tag.

    Syntax:
        {% rowspan rows=2 %}
            {% frame %}Tall content{% endframe %}
        {% endrowspan %}
    """

    tags = {"rowspan"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the rowspan tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endrowspan", lineno)

        # Parse body
        node = nodes.CallBlock(
            self.call_method("_render_rowspan", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endrowspan",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_rowspan(
        self,
        caller: Callable[[], str],
        rows: int = 1,
        **kwargs: Any,
    ) -> str:
        """Render the rowspan wrapper.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        rows : int
            Number of rows to span (default: 1)

        Returns
        -------
        str
            Rendered output
        """
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context

        # Create wrapper VNode
        vnode = VNodeBuilder("GridSpanWrapper")
        vnode.set_prop("colspan", 1)
        vnode.set_prop("rowspan", int(rows))
        layout_context.push_vnode(vnode)

        # Render child content
        body_output = caller()

        # Get the children
        vnode_children = vnode.children

        # Wrapper should have exactly one child element
        if vnode_children:
            # Interleave to preserve order (though we expect only 1 child)
            interleaved = interleave_text_and_vnode_builders(
                body_output, vnode_children, False, layout_context
            )
            # Filter to only element vnodes (ignore text-only vnodes)
            element_children = [c for c in interleaved if c.type != "TextElement"]
            if len(element_children) != 1:
                logger.warning(
                    f"rowspan wrapper should contain exactly 1 element, "
                    f"got {len(element_children)}"
                )
            vnode.children = interleaved

        layout_context.pop_vnode()

        return get_element_marker(layout_context)


class SplitPanelExtension(Extension):
    """Jinja2 extension for {% splitpanel %} tag.

    Syntax:
        {% splitpanel orientation="horizontal" ratio="50:50" resizable=true
                      min_first=5 min_second=5 collapsible="none" id="my_split" %}
            {% frame %}First panel{% endframe %}
            {% frame %}Second panel{% endframe %}
        {% endsplitpanel %}

    The splitpanel takes exactly **two direct children** - any element type
    is allowed (frame, textarea, another splitpanel, etc.).
    """

    tags = {"splitpanel"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the splitpanel tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endsplitpanel", lineno)

        # Parse body
        node = nodes.CallBlock(
            self.call_method("_render_splitpanel", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endsplitpanel",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_splitpanel(
        self,
        caller: Callable[[], str],
        orientation: str = "horizontal",
        ratio: str = "50:50",
        resizable: bool = True,
        min_first: int = 5,
        min_second: int = 5,
        collapsible: str = "none",
        divider_style: str = "single",
        width: int | str = "fill",
        height: int | str = "fill",
        id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the splitpanel tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        orientation : str
            "horizontal" (side-by-side) or "vertical" (stacked). Default: "horizontal"
        ratio : str
            Initial size ratio like "50:50" or "30:70". Default: "50:50"
        resizable : bool
            Allow drag-to-resize. Default: True
        min_first : int
            Minimum size for first panel. Default: 5
        min_second : int
            Minimum size for second panel. Default: 5
        collapsible : str
            Which panels can collapse: "none", "first", "second", "both". Default: "none"
        divider_style : str
            Style of divider: "single", "double", "dashed", "thick". Default: "single"
        width : int or str
            Width specification. Default: "fill"
        height : int or str
            Height specification. Default: "fill"
        id : str, optional
            Element ID for state binding

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context

        # Parse attributes
        width_parsed = parse_size_attr(width)
        height_parsed = parse_size_attr(height)
        min_first_int = safe_int(min_first, default=5, name="min_first")
        min_second_int = safe_int(min_second, default=5, name="min_second")

        # Create VNode builder for reconciliation
        vnode = VNodeBuilder("SplitPanel", key=id)
        vnode.set_prop("orientation", orientation)
        vnode.set_prop("ratio", ratio)
        vnode.set_prop("resizable", resizable)
        vnode.set_prop("min_first", min_first_int)
        vnode.set_prop("min_second", min_second_int)
        vnode.set_prop("collapsible", collapsible)
        vnode.set_prop("divider_style", divider_style)
        vnode.set_layout(
            width=width_parsed,
            height=height_parsed,
        )
        layout_context.push_vnode(vnode)

        # Render body - nested elements will add themselves via push_vnode/add_vnode
        body_output = caller()

        # Get the children (should be exactly 2)
        vnode_children = vnode.children

        if vnode_children:
            # Interleave to preserve order
            interleaved = interleave_text_and_vnode_builders(
                body_output, vnode_children, False, layout_context
            )
            # Filter to only element vnodes (ignore text-only vnodes)
            element_children = [c for c in interleaved if c.type != "TextElement"]
            if len(element_children) != 2:
                logger.warning(
                    f"splitpanel should contain exactly 2 children, "
                    f"got {len(element_children)}"
                )
            vnode.children = element_children  # Only keep element children

        # Pop VNode from stack
        layout_context.pop_vnode()

        # Return marker for text interleaving
        return get_element_marker(layout_context)
