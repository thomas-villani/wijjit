# ${DIR_PATH}/${FILE_NAME}
import textwrap
from typing import Any

from jinja2 import nodes
from jinja2.ext import Extension

from wijjit.elements.base import TextElement
from wijjit.layout.engine import ElementNode, FrameNode, HStack, LayoutNode, VStack
from wijjit.layout.frames import BorderStyle, Frame, FrameStyle


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

    def __init__(self):
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


class VStackExtension(Extension):
    """Jinja2 extension for {% vstack %} tag.

    Syntax:
        {% vstack width="fill" height="auto" spacing=0 padding=0
                  margin=0 align_h="stretch" align_v="stretch" %}
            ... children ...
        {% endvstack %}
    """

    tags = {"vstack"}

    def parse(self, parser):
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
            parser.parse_statements(["name:endvstack"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_vstack(
        self,
        caller,
        width="fill",
        height="fill",
        spacing=0,
        padding=0,
        margin=0,
        align_h="stretch",
        align_v="stretch",
        raw=False,
        id=None,
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
        padding : int
            Padding around children
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
        # Get or create layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            context = LayoutContext()
            self.environment.globals["_wijjit_layout_context"] = context

        # Parse attributes
        width = parse_size_attr(width)
        height = parse_size_attr(height)
        spacing = int(spacing)
        padding = int(padding)

        # Parse margin
        if isinstance(margin, str) and margin.startswith("("):
            try:
                margin = eval(margin)
            except (ValueError, SyntaxError, NameError):
                margin = 0
        elif isinstance(margin, str):
            try:
                margin = int(margin)
            except ValueError:
                margin = 0

        # Create VStack node
        vstack = VStack(
            children=[],
            width=width,
            height=height,
            spacing=spacing,
            padding=padding,
            margin=margin,
            align_h=align_h,
            align_v=align_v,
            id=id,
        )

        # Push onto stack
        context.push(vstack)

        # Render body
        body_output = caller()

        # If body contains non-whitespace text, create TextElement
        # Text is appended to maintain source order
        processed_text = process_body_content(body_output, raw=raw)
        if processed_text:
            # When raw=True, disable text wrapping
            text_elem = TextElement(processed_text, wrap=not raw)
            text_node = ElementNode(text_elem, width="auto", height="auto")
            # Append to maintain source order
            vstack.children.append(text_node)

        # Pop from stack
        context.pop()

        # Return empty string (layout will be processed later)
        return ""


class HStackExtension(Extension):
    """Jinja2 extension for {% hstack %} tag.

    Syntax:
        {% hstack width="auto" height="fill" spacing=0 padding=0
                  margin=0 align_h="stretch" align_v="stretch" %}
            ... children ...
        {% endhstack %}
    """

    tags = {"hstack"}

    def parse(self, parser):
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
            parser.parse_statements(["name:endhstack"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_hstack(
        self,
        caller,
        width="auto",
        height="auto",
        spacing=0,
        padding=0,
        margin=0,
        align_h="stretch",
        align_v="stretch",
        raw=False,
        id=None,
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
        padding : int
            Padding around children
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
        # Get or create layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            context = LayoutContext()
            self.environment.globals["_wijjit_layout_context"] = context

        # Parse attributes
        width = parse_size_attr(width)
        height = parse_size_attr(height)
        spacing = int(spacing)
        padding = int(padding)

        # Parse margin
        if isinstance(margin, str) and margin.startswith("("):
            try:
                margin = eval(margin)
            except (ValueError, SyntaxError, NameError):
                margin = 0
        elif isinstance(margin, str):
            try:
                margin = int(margin)
            except ValueError:
                margin = 0

        # Create HStack node
        hstack = HStack(
            children=[],
            width=width,
            height=height,
            spacing=spacing,
            padding=padding,
            margin=margin,
            align_h=align_h,
            align_v=align_v,
            id=id,
        )

        # Push onto stack
        context.push(hstack)

        # Render body
        body_output = caller()

        # If body contains non-whitespace text, create TextElement
        # Text is appended to maintain source order
        processed_text = process_body_content(body_output, raw=raw)
        if processed_text:
            # When raw=True, disable text wrapping
            text_elem = TextElement(processed_text, wrap=not raw)
            text_node = ElementNode(text_elem, width="auto", height="auto")
            # Append to maintain source order
            hstack.children.append(text_node)

        # Pop from stack
        context.pop()

        # Return empty string (layout will be processed later)
        return ""


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

    def parse(self, parser):
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
            parser.parse_statements(["name:endframe"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_frame(
        self,
        caller,
        width="fill",
        height="auto",
        title=None,
        border="single",
        margin=0,
        padding=None,
        align_h="stretch",
        align_v="stretch",
        content_align_h="stretch",
        content_align_v="stretch",
        overflow_x="clip",
        scrollable=False,
        show_scrollbar=True,
        raw=False,
        id=None,
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
        # Get or create layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            context = LayoutContext()
            self.environment.globals["_wijjit_layout_context"] = context

        # Auto-generate ID for scrollable frames if not provided
        if scrollable and not id:
            # Get or create auto-ID counter
            if "_wijjit_frame_counter" not in self.environment.globals:
                self.environment.globals["_wijjit_frame_counter"] = 0
            self.environment.globals["_wijjit_frame_counter"] += 1
            id = f"frame_{self.environment.globals['_wijjit_frame_counter']}"

        # Parse attributes
        width = parse_size_attr(width)
        height = parse_size_attr(height)

        # Parse margin - could be int or tuple string like "(1,2,3,4)"
        if isinstance(margin, str) and margin.startswith("("):
            # Parse tuple string
            try:
                margin = eval(margin)
            except (ValueError, SyntaxError, NameError):
                margin = 0
        elif isinstance(margin, str):
            try:
                margin = int(margin)
            except ValueError:
                margin = 0

        # Parse border style
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        border_style = border_map.get(border, BorderStyle.SINGLE)

        # Parse padding - could be int or tuple string like "(1,2,3,4)"
        if padding is None:
            padding = (1, 1, 1, 1)  # Default padding
        elif isinstance(padding, int):
            padding = (padding, padding, padding, padding)
        elif isinstance(padding, str) and padding.startswith("("):
            # Parse tuple string
            try:
                padding = eval(padding)
            except (ValueError, SyntaxError, NameError):
                padding = (1, 1, 1, 1)
        elif isinstance(padding, str):
            try:
                p = int(padding)
                padding = (p, p, p, p)
            except ValueError:
                padding = (1, 1, 1, 1)

        # Parse overflow_y from scrollable parameter
        if scrollable:
            overflow_y = "auto"
        else:
            overflow_y = "clip"

        # Create actual Frame object with all styling
        frame_style = FrameStyle(
            border=border_style,
            title=title,
            padding=padding,
            content_align_h=content_align_h,
            content_align_v=content_align_v,
            scrollable=scrollable,
            show_scrollbar=show_scrollbar,
            overflow_y=overflow_y,
            overflow_x=overflow_x,
        )

        # Parse width/height as integers if they're numeric strings
        frame_width = (
            int(width) if isinstance(width, str) and width.isdigit() else width
        )
        frame_height = (
            int(height) if isinstance(height, str) and height.isdigit() else height
        )

        # Default frame size if auto/fill
        if frame_width == "auto" or frame_width == "fill":
            frame_width = 40
        if frame_height == "auto" or frame_height == "fill":
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
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state_dict = ctx["state"]
                    frame._state_dict = state_dict

                    # Restore scroll position if it exists in state
                    if scroll_key in state_dict:
                        # Position will be restored after scroll manager is created
                        # Store it temporarily for later restoration
                        frame._pending_scroll_restore = state_dict[scroll_key]
            except (KeyError, AttributeError):
                pass

        # Create FrameNode to hold frame and children
        frame_node = FrameNode(
            frame=frame,
            children=[],
            width=width,
            height=height,
            margin=margin,
            align_h=align_h,
            align_v=align_v,
            content_align_h=content_align_h,
            content_align_v=content_align_v,
            id=id,
        )

        # Push onto stack
        context.push(frame_node)

        # Render body
        body_output = caller()

        # Handle text content in frame
        processed_text = process_body_content(body_output, raw=raw)
        if processed_text:
            # If frame has no child elements, use Frame's set_content (handles overflow_x)
            # Otherwise, add text as a child element alongside other elements
            if not frame_node.content_container.children:
                # No children - set content directly on Frame for overflow_x handling
                frame.set_content(processed_text)
            else:
                # Has children - add text as first child element
                text_elem = TextElement(processed_text)
                text_node = ElementNode(text_elem, width="auto", height="auto")
                frame_node.content_container.children.insert(0, text_node)

        # Pop from stack
        context.pop()

        # Return empty string (layout will be processed later)
        return ""
