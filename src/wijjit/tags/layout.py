# ${DIR_PATH}/${FILE_NAME}
from __future__ import annotations

import textwrap
from ast import literal_eval
from collections.abc import Callable
from typing import Any, Literal, cast

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.elements.base import TextElement
from wijjit.layout.engine import ElementNode, FrameNode, HStack, LayoutNode, VStack
from wijjit.layout.frames import BorderStyle, Frame, FrameStyle
from wijjit.logging_config import get_logger

logger = get_logger(__name__)


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


def interleave_text_and_elements(
    body_output: str, children: list[LayoutNode], raw: bool = False
) -> list[LayoutNode]:
    """Interleave text content with child elements based on markers.

    Child elements insert markers like '\x00ELEM_0\x00' into body_output
    to indicate their position in the template source. This function
    parses those markers and rebuilds the children list with text
    elements interleaved at the correct positions.

    Parameters
    ----------
    body_output : str
        Template body output containing text and element markers
    children : list[LayoutNode]
        Child elements that were added (in order they were added)
    raw : bool, optional
        If True, preserve whitespace in text. If False, dedent/strip (default: False)

    Returns
    -------
    list[LayoutNode]
        New children list with text and elements properly interleaved
    """
    import re

    # Pattern to match element markers (with capture group for digit extraction)
    marker_pattern = r"\x00ELEM_(\d+)\x00"

    # Pattern for splitting (without capture group to avoid nested groups)
    split_pattern = r"(\x00ELEM_\d+\x00)"

    # Split body_output on markers, keeping the markers
    parts = re.split(split_pattern, body_output)

    result: list[LayoutNode] = []

    for part in parts:
        # Check if this is a marker
        marker_match = re.match(marker_pattern, part)
        if marker_match:
            # This is an element marker
            elem_index = int(marker_match.group(1))
            if 0 <= elem_index < len(children):
                result.append(children[elem_index])
        else:
            # This is text content
            processed_text = process_body_content(part, raw=raw)
            if processed_text:
                text_elem = TextElement(processed_text, wrap=not raw)
                text_node = ElementNode(text_elem, width="auto", height="auto")
                result.append(text_node)

    return result


def get_element_marker(layout_context: LayoutContext) -> str:
    """Get marker for element that was just added to layout context.

    This should be called after add_element() to get the marker string
    for the element that was just added. The marker indicates the element's
    position in the parent's children list.

    Parameters
    ----------
    layout_context : LayoutContext
        Layout context

    Returns
    -------
    str
        Marker string to return from element extension (e.g., '\x00ELEM_0\x00')
    """
    if layout_context.stack:
        parent = layout_context.stack[-1]
        # Get the actual children list (FrameNode uses content_container.children)
        if hasattr(parent, "content_container"):
            children_list = parent.content_container.children
        else:
            children_list = parent.children
        # Get index of element that was just added
        elem_index = len(children_list) - 1
        return f"\x00ELEM_{elem_index}\x00"
    return ""


class LayoutContext:
    """Context for building layout tree during template rendering.

    Attributes
    ----------
    root : LayoutNode or None
        Root of the layout tree
    stack : list of LayoutNode
        Stack of container nodes being processed
    element_counters : dict
        Counter for auto-generating element IDs by type
    """

    def __init__(self) -> None:
        self.root: LayoutNode | None = None
        self.stack: list[LayoutNode] = []
        self.element_counters: dict[str, int] = {}

    def push(self, node: LayoutNode) -> None:
        """Push a container node onto the stack.

        Parameters
        ----------
        node : LayoutNode
            Container node to push
        """
        if self.root is None:
            self.root = node

        if self.stack:
            # Add to current container
            parent = self.stack[-1]
            if hasattr(parent, "add_child"):
                parent.add_child(node)

        self.stack.append(node)

    def pop(self) -> LayoutNode | None:
        """Pop a container node from the stack.

        Returns
        -------
        LayoutNode or None
            Popped node
        """
        if self.stack:
            return self.stack.pop()
        return None

    def add_element(self, node: LayoutNode) -> None:
        """Add an element node to the current container.

        Parameters
        ----------
        node : LayoutNode
            Element node to add
        """
        if self.root is None:
            self.root = node
            return

        if self.stack:
            parent = self.stack[-1]
            if hasattr(parent, "add_child"):
                parent.add_child(node)

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
    spacing_int = int(spacing)

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

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endvstack"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

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
        height: int | str = "fill",
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        # classes = kwargs.get("class", None)

        # Get or create layout context from environment globals
        context_obj = self.environment.globals.get("_wijjit_layout_context")
        if context_obj is None:
            layout_context: LayoutContext = LayoutContext()
            self.environment.globals["_wijjit_layout_context"] = layout_context
        else:
            layout_context = cast(LayoutContext, context_obj)

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

        # Create VStack node
        vstack = VStack(
            children=[],
            width=width_parsed,
            height=height_parsed,
            spacing=spacing_int,
            padding=padding_parsed,
            margin=margin_parsed,
            align_h=cast(Literal["left", "center", "right", "stretch"], align_h),
            align_v=cast(Literal["top", "middle", "bottom", "stretch"], align_v),
            id=id,
        )

        # Push onto stack
        layout_context.push(vstack)

        # Render body - nested elements will add themselves to vstack.children
        # and insert markers in body_output to indicate their positions
        body_output = caller()

        # Interleave text and elements in source order using markers
        vstack.children = interleave_text_and_elements(
            body_output, vstack.children, raw=raw
        )

        # Pop from stack
        layout_context.pop()

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

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endhstack"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        # classes = kwargs.get("class", None)

        # Get or create layout context from environment globals
        context_obj = self.environment.globals.get("_wijjit_layout_context")
        if context_obj is None:
            layout_context: LayoutContext = LayoutContext()
            self.environment.globals["_wijjit_layout_context"] = layout_context
        else:
            layout_context = cast(LayoutContext, context_obj)

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

        # Create HStack node
        hstack = HStack(
            children=[],
            width=width_parsed,
            height=height_parsed,
            spacing=spacing_int,
            padding=padding_parsed,
            margin=margin_parsed,
            align_h=cast(Literal["left", "center", "right", "stretch"], align_h),
            align_v=cast(Literal["top", "middle", "bottom", "stretch"], align_v),
            id=id,
        )

        # Push onto stack
        layout_context.push(hstack)

        # Render body - nested elements will add themselves to hstack.children
        # and insert markers in body_output to indicate their positions
        body_output = caller()

        # Interleave text and elements in source order using markers
        hstack.children = interleave_text_and_elements(
            body_output, hstack.children, raw=raw
        )

        # Pop from stack
        layout_context.pop()

        # Return marker for text interleaving
        return get_element_marker(layout_context)


class FrameExtension(Extension):
    """Jinja2 extension for {% frame %} tag.

    Syntax:
        {% frame title="Title" border="single" width="fill" height="auto"
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

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endframe"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

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
        border: str = "single",
        margin: int | str | tuple[int, ...] = 0,
        padding: int | str | tuple[int, ...] | None = None,
        align_h: str = "stretch",
        align_v: str = "stretch",
        content_align_h: str = "stretch",
        content_align_v: str = "stretch",
        overflow_x: str = "clip",
        scrollable: bool = False,
        show_scrollbar: bool = True,
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
        border : str
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
            Horizontal overflow mode: "clip", "visible", or "wrap" (default: "clip")
        scrollable : bool, optional
            Enable vertical scrolling (default: False)
        show_scrollbar : bool, optional
            Show scrollbar when scrollable (default: True)
        raw : bool, optional
            If True, preserve whitespace in body content. If False, dedent and strip (default: False)
        id : str, optional
            Node identifier

        Returns
        -------
        str
            Rendered output
        """
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        # classes = kwargs.get("class", None)

        # Get or create layout context from environment globals
        context_obj = self.environment.globals.get("_wijjit_layout_context")
        if context_obj is None:
            layout_context: LayoutContext = LayoutContext()
            self.environment.globals["_wijjit_layout_context"] = layout_context
        else:
            layout_context = cast(LayoutContext, context_obj)

        # Auto-generate ID for scrollable frames if not provided
        if scrollable and not id:
            # Get or create auto-ID counter
            if "_wijjit_frame_counter" not in self.environment.globals:
                self.environment.globals["_wijjit_frame_counter"] = 0
            counter = cast(int, self.environment.globals["_wijjit_frame_counter"])
            self.environment.globals["_wijjit_frame_counter"] = counter + 1
            id = f"frame_{counter + 1}"

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
        border_style = border_map.get(border, BorderStyle.SINGLE)

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

        # Create actual Frame object with all styling
        frame_style = FrameStyle(
            border=border_style,
            title=title,
            padding=padding_parsed,
            content_align_h=cast(
                Literal["left", "center", "right", "stretch"], content_align_h
            ),
            content_align_v=cast(
                Literal["top", "middle", "bottom", "stretch"], content_align_v
            ),
            scrollable=scrollable,
            show_scrollbar=show_scrollbar,
            overflow_y=overflow_y,
            overflow_x=cast(Literal["clip", "visible", "wrap"], overflow_x),
        )

        # Parse width/height as integers if they're numeric strings
        frame_width: int
        if isinstance(width_parsed, str) and width_parsed.isdigit():
            frame_width = int(width_parsed)
        elif width_parsed == "auto" or width_parsed == "fill":
            frame_width = 40
        elif isinstance(width_parsed, str) and width_parsed.endswith("%"):
            # Percentage widths get placeholder value - layout engine will calculate actual value
            frame_width = 40
        elif isinstance(width_parsed, int):
            frame_width = width_parsed
        else:
            frame_width = 40

        frame_height: int
        if isinstance(height_parsed, str) and height_parsed.isdigit():
            frame_height = int(height_parsed)
        elif height_parsed == "auto" or height_parsed == "fill":
            frame_height = 10
        elif isinstance(height_parsed, str) and height_parsed.endswith("%"):
            # Percentage heights get placeholder value - layout engine will calculate actual value
            frame_height = 10
        elif isinstance(height_parsed, int):
            frame_height = height_parsed
        else:
            frame_height = 10

        frame = Frame(
            width=frame_width,
            height=frame_height,
            style=frame_style,
            id=id,
        )

        # Set up state persistence for scrollable frames
        if scrollable and id:
            scroll_key = f"_scroll_{id}"
            frame.scroll_state_key = scroll_key

            # Give frame access to state dict for saving scroll position
            try:
                ctx_obj = self.environment.globals.get("_wijjit_current_context")
                ctx = cast(dict[str, Any], ctx_obj)
                if ctx and "state" in ctx:
                    state_dict = ctx["state"]
                    frame._state_dict = state_dict

                    # Restore scroll position if it exists in state
                    if scroll_key in state_dict:
                        # Position will be restored after scroll manager is created
                        # Store it temporarily for later restoration
                        frame._pending_scroll_restore = state_dict[scroll_key]  # type: ignore[attr-defined]
            except (KeyError, AttributeError):
                pass

        # Create FrameNode to hold frame and children
        frame_node = FrameNode(
            frame=frame,
            children=[],
            width=width_parsed,
            height=height_parsed,
            margin=margin_parsed,
            align_h=cast(Literal["left", "center", "right", "stretch"], align_h),
            align_v=cast(Literal["top", "middle", "bottom", "stretch"], align_v),
            content_align_h=cast(
                Literal["left", "center", "right", "stretch"], content_align_h
            ),
            content_align_v=cast(
                Literal["top", "middle", "bottom", "stretch"], content_align_v
            ),
            id=id,
        )

        # Push onto stack
        layout_context.push(frame_node)

        # Render body - nested elements will add themselves to frame_node.content_container.children
        # and insert markers in body_output to indicate their positions
        body_output = caller()

        # Handle text content in frame
        if not frame_node.content_container.children and body_output.strip():
            # No children and has text - set content directly on Frame for overflow_x handling
            processed_text = process_body_content(body_output, raw=raw)
            if processed_text:
                frame.set_content(processed_text)
        else:
            # Has children or markers - interleave text and elements in source order
            frame_node.content_container.children = interleave_text_and_elements(
                body_output, frame_node.content_container.children, raw=raw
            )

        # Pop from stack
        layout_context.pop()

        # Return marker for text interleaving
        return get_element_marker(layout_context)
