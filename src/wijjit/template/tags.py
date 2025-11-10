"""Jinja2 custom tag extensions for declarative UI definition.

This module provides custom Jinja2 tags that create layout nodes and elements
during template rendering. The layout tree is built up in a context variable
and then processed by the layout engine after rendering.
"""

import textwrap
from typing import Any

from jinja2 import nodes
from jinja2.ext import Extension

from ..elements.base import TextElement
from ..elements.display import Table, Tree
from ..elements.input import (
    Button,
    Checkbox,
    CheckboxGroup,
    Radio,
    RadioGroup,
    Select,
    TextArea,
    TextInput,
)
from ..layout.engine import ElementNode, FrameNode, HStack, LayoutNode, VStack
from ..layout.frames import BorderStyle, Frame, FrameStyle


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

        # Parse overflow_y from scrollable parameter
        if scrollable:
            overflow_y = "auto"
        else:
            overflow_y = "clip"

        # Create actual Frame object with all styling
        frame_style = FrameStyle(
            border=border_style,
            title=title,
            padding=(1, 1, 1, 1),  # Default padding
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


class TextInputExtension(Extension):
    """Jinja2 extension for {% textinput %} tag.

    Syntax:
        {% textinput id="name" placeholder="Enter name" width=30 %}{% endtextinput %}
    """

    tags = {"textinput"}

    def parse(self, parser):
        """Parse the textinput tag.

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
            "name:endtextinput"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but we need to consume until endtextinput)
        node = nodes.CallBlock(
            self.call_method("_render_textinput", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endtextinput"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_textinput(
        self,
        caller,
        id=None,
        placeholder="",
        width=20,
        value="",
        action=None,
        bind=True,
    ) -> str:
        """Render the textinput tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        placeholder : str
            Placeholder text
        width : int
            Input width
        value : str
            Initial value
        action : str, optional
            Action ID to dispatch when Enter is pressed
        bind : bool
            Whether to auto-bind value to state[id] (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            # No layout context available, skip
            return ""

        # Convert width to int
        width = int(width)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("textinput")

        # If binding is enabled and id is provided, try to get initial value from state
        if bind and id:
            # Try to get state from the template context
            # The state is passed via context in app.py _render()
            try:
                # Access the Jinja2 context to get state
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        value = str(state[id])
            except Exception:
                pass  # If we can't get state, use provided value

        # Create TextInput element
        text_input = TextInput(id=id, placeholder=placeholder, value=value, width=width)

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            text_input.focused = True

        # Store action ID on input if provided
        if action:
            text_input.action = action

        # Store bind setting
        text_input.bind = bind

        # Create ElementNode
        node = ElementNode(text_input, width=width, height=1)

        # Add to layout context
        context.add_element(node)

        # Return empty string (layout will be processed later)
        return ""


class ButtonExtension(Extension):
    """Jinja2 extension for {% button %} tag.

    Syntax:
        {% button id="submit" %}Submit{% endbutton %}
    """

    tags = {"button"}

    def parse(self, parser):
        """Parse the button tag.

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
            "name:endbutton"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (button label)
        node = nodes.CallBlock(
            self.call_method("_render_button", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endbutton"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_button(self, caller, id=None, action=None) -> str:
        """Render the button tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content (button label)
        id : str, optional
            Element identifier
        action : str, optional
            Action ID to dispatch when button is clicked

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

        # Get button label from body
        label = caller().strip()

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("button")

        # Create Button element
        button = Button(label=label, id=id)

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            button.focused = True

        # Store action ID on button if provided
        if action:
            button.action = action

        # Create ElementNode
        # Button width is based on label length + brackets
        button_width = len(label) + 4  # "< label >"
        node = ElementNode(button, width=button_width, height=1)

        # Add to layout context
        context.add_element(node)

        # Return empty string (layout will be processed later)
        return ""


class SelectExtension(Extension):
    """Jinja2 extension for {% select %} tag.

    Syntax:
        {% select id="color" width=30 %}
            Red
            Green
            Blue
        {% endselect %}

        Or with options attribute:
        {% select id="fruit" options=["Apple", "Banana", "Orange"] %}{% endselect %}

        Or with value/label pairs:
        {% select id="size" %}
            {"value": "s", "label": "Small"}
            {"value": "m", "label": "Medium"}
            {"value": "l", "label": "Large"}
        {% endselect %}

        Disabled options:
        {% select id="priority" %}
            Low
            Medium
            High (disabled)
        {% endselect %}
    """

    tags = {"select"}

    def parse(self, parser):
        """Parse the select tag.

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
            "name:endselect"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (options list)
        node = nodes.CallBlock(
            self.call_method("_render_select", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endselect"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_select(
        self,
        caller,
        id=None,
        options=None,
        value=None,
        width=20,
        visible_rows=5,
        action=None,
        bind=True,
        border_style=None,
        title=None,
    ) -> str:
        """Render the select tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content (options list)
        id : str, optional
            Element identifier
        options : list, optional
            List of options (if not provided in body)
        value : str, optional
            Initial selected value
        width : int
            Select width (default: 20)
        visible_rows : int
            Number of visible rows in the list (default: 5)
        action : str, optional
            Action ID to dispatch when value changes
        bind : bool
            Whether to auto-bind value to state[id] (default: True)
        border_style : str, optional
            Border style: "single", "double", "rounded", or None (default: None)
        title : str, optional
            Title to display in top border (only when border_style is set)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            # No layout context available, skip
            return ""

        # Convert numeric parameters
        width = int(width)
        visible_rows = int(visible_rows)

        # Parse options from body if not provided as attribute
        if options is None:
            body = caller().strip()
            if body:
                options = self._parse_options_from_body(body)
            else:
                options = []
        else:
            # Options provided as attribute, consume body anyway
            caller()

        # Extract disabled values
        disabled_values = []
        cleaned_options = []
        for opt in options:
            if isinstance(opt, str):
                # Check for " (disabled)" suffix
                if opt.endswith(" (disabled)"):
                    opt_value = opt[:-11].strip()  # Remove " (disabled)"
                    cleaned_options.append(opt_value)
                    disabled_values.append(opt_value)
                else:
                    cleaned_options.append(opt)
            elif isinstance(opt, dict):
                # Check for disabled key
                if opt.get("disabled", False):
                    disabled_values.append(opt["value"])
                cleaned_options.append(opt)
            else:
                cleaned_options.append(opt)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("select")

        # If binding is enabled and id is provided, try to get initial value from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        value = str(state[id]) if state[id] is not None else None
            except Exception:
                pass

        # Create Select element
        select = Select(
            id=id,
            options=cleaned_options,
            value=value,
            width=width,
            visible_rows=visible_rows,
            disabled_values=disabled_values,
            border_style=border_style,
            title=title,
        )

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            select.focused = True

        # Store action ID on select if provided
        if action:
            select.action = action

        # Store bind setting
        select.bind = bind

        # Restore highlighted_index and scroll position from state if available
        if id:
            highlight_key = f"_highlight_{id}"
            scroll_key = f"_scroll_{id}"
            select.highlight_state_key = highlight_key
            select.scroll_state_key = scroll_key
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if highlight_key in state:
                        select.highlighted_index = state[highlight_key]
                    if scroll_key in state:
                        select.scroll_manager.scroll_to(state[scroll_key])
            except Exception:
                pass

        # Create ElementNode
        # Calculate total height accounting for borders
        # - No borders: height = visible_rows (content only)
        # - With borders: height = visible_rows + 2 (top border + content + bottom border)
        total_height = visible_rows + (2 if border_style is not None else 0)

        # Width also needs to account for borders (adds 2 columns)
        total_width = width + (2 if border_style is not None else 0)

        node = ElementNode(select, width=total_width, height=total_height)

        # Add to layout context
        context.add_element(node)

        # Return empty string (layout will be processed later)
        return ""

    def _parse_options_from_body(self, body: str) -> list:
        """Parse options from template body content.

        Parameters
        ----------
        body : str
            Body content with options (one per line or JSON)

        Returns
        -------
        list
            List of option strings or dicts
        """
        options = []
        lines = body.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to parse as JSON dict (for value/label pairs)
            if line.startswith("{") and line.endswith("}"):
                try:
                    import json

                    opt_dict = json.loads(line)
                    options.append(opt_dict)
                    continue
                except (json.JSONDecodeError, ValueError):
                    pass

            # Otherwise treat as plain string option
            options.append(line)

        return options


class TableExtension(Extension):
    """Jinja2 extension for {% table %} tag.

    Syntax:
        {% table id="users"
                 data=state.users
                 columns=["Name", "Email", "Status"]
                 sortable=true
                 width=80
                 height=15 %}
        {% endtable %}
    """

    tags = {"table"}

    def parse(self, parser):
        """Parse the table tag.

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
            "name:endtable"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endtable)
        node = nodes.CallBlock(
            self.call_method("_render_table", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endtable"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_table(
        self,
        caller,
        id=None,
        data=None,
        columns=None,
        width=60,
        height=10,
        sortable=False,
        show_header=True,
        show_scrollbar=True,
        border_style="single",
        bind=True,
    ) -> str:
        """Render the table tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        data : list of dict, optional
            Table data
        columns : list, optional
            Column definitions
        width : int
            Table width (default: 60)
        height : int
            Table height (default: 10)
        sortable : bool
            Whether columns are sortable (default: False)
        show_header : bool
            Whether to show header row (default: True)
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        border_style : str
            Rich border style (default: "single")
        bind : bool
            Whether to auto-bind data to state[id] (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            # No layout context available, skip
            return ""

        # Convert numeric parameters
        width = int(width)
        height = int(height)
        sortable = bool(sortable)
        show_header = bool(show_header)
        show_scrollbar = bool(show_scrollbar)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("table")

        # If binding is enabled and id is provided, try to get data from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        data = state[id]
            except Exception:
                pass

        # Ensure data is a list
        if data is None:
            data = []
        elif not isinstance(data, list):
            data = list(data)

        # Ensure columns is a list
        if columns is None:
            columns = []
        elif not isinstance(columns, list):
            columns = list(columns)

        # Create Table element
        table = Table(
            id=id,
            data=data,
            columns=columns,
            width=width,
            height=height,
            sortable=sortable,
            show_header=show_header,
            show_scrollbar=show_scrollbar,
            border_style=border_style,
        )

        # Store bind setting
        table.bind = bind

        # Restore scroll position from state if available
        if id:
            scroll_key = f"_scroll_{id}"
            table.scroll_state_key = scroll_key
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if scroll_key in state:
                        table.restore_scroll_position(state[scroll_key])
            except Exception:
                pass

        # Create ElementNode
        # Table has fixed dimensions, so use exact width and height
        node = ElementNode(table, width=width, height=height)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        # Return empty string (layout will be processed later)
        return ""


class TreeExtension(Extension):
    """Jinja2 extension for {% tree %} tag.

    Syntax:
        {% tree id="filetree"
                data=state.file_tree
                width=40
                height=20
                on_select="file_selected"
                show_scrollbar=true
                show_root=true %}
        {% endtree %}
    """

    tags = {"tree"}

    def parse(self, parser):
        """Parse the tree tag.

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
            "name:endtree"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endtree)
        node = nodes.CallBlock(
            self.call_method("_render_tree", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endtree"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_tree(
        self,
        caller,
        id=None,
        data=None,
        width=40,
        height=15,
        show_scrollbar=True,
        show_root=True,
        indent_size=2,
        on_select=None,
        expanded=None,
        bind=True,
    ) -> str:
        """Render the tree tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        data : dict or list, optional
            Tree data (nested dict or flat list)
        width : int
            Tree width (default: 40)
        height : int
            Tree height (default: 15)
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        show_root : bool
            Whether to show root node (default: True)
        indent_size : int
            Indentation per level (default: 2)
        on_select : str, optional
            Action ID to dispatch when node is selected
        expanded : str or list, optional
            Expansion state binding. If a string, it's treated as a state key
            name for two-way binding (tree reads from and writes to this key).
            If a list, it's used for one-time initialization only.
            Examples:
                expanded="expanded_nodes"  # Two-way binding to state["expanded_nodes"]
                expanded=["node1", "node2"]  # One-time initialization
        bind : bool
            Whether to auto-bind data to state[id] (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            # No layout context available, skip
            return ""

        # Convert numeric parameters
        width = int(width)
        height = int(height)
        indent_size = int(indent_size)
        show_scrollbar = bool(show_scrollbar)
        show_root = bool(show_root)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("tree")

        # If binding is enabled and id is provided, try to get data from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        data = state[id]
            except Exception:
                pass

        # Create Tree element
        tree = Tree(
            id=id,
            data=data,
            width=width,
            height=height,
            show_scrollbar=show_scrollbar,
            show_root=show_root,
            indent_size=indent_size,
        )

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            tree.focused = True

        # Store action ID if provided
        # The action will be dispatched by the app when on_select is called
        if on_select:
            tree.action = on_select

        # Store bind setting
        tree.bind = bind

        # Restore scroll position, expansion state, and highlighted index from state
        if id:
            # Set state keys
            scroll_key = f"_scroll_{id}"
            expand_key = f"_expand_{id}"
            highlight_key = f"_highlight_{id}"
            selected_key = f"_selected_{id}"

            tree.scroll_state_key = scroll_key
            tree.expand_state_key = expand_key
            tree.highlight_state_key = highlight_key
            tree.selected_state_key = selected_key

            # Give tree access to state dict for saving
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    tree._state_dict = ctx["state"]
            except Exception:
                pass

            # Restore expansion state (do this first, before highlight)
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]

                    # Check if expanded parameter is a string (state key name for two-way binding)
                    if isinstance(expanded, str):
                        # Two-way binding: use user's state key
                        tree.expand_state_key = expanded
                        if expanded in state:
                            tree.expanded_nodes = set(state[expanded])
                        else:
                            tree.expanded_nodes = set()
                        tree._rebuild_nodes()
                    elif expanded is not None:
                        # One-way binding: use provided list for initialization only
                        # Tree will save to internal _expand_{id} key
                        if expand_key in state:
                            # Prefer saved state over parameter
                            tree.expanded_nodes = set(state[expand_key])
                        else:
                            # Initialize from parameter
                            tree.expanded_nodes = (
                                set(expanded) if isinstance(expanded, list) else set()
                            )
                        tree._rebuild_nodes()
                    else:
                        # No expanded parameter: use internal state key
                        if expand_key in state:
                            tree.expanded_nodes = set(state[expand_key])
                            tree._rebuild_nodes()
            except Exception:
                # Fall back to parameter if state restoration fails
                if expanded:
                    tree.expanded_nodes = (
                        set(expanded) if isinstance(expanded, list) else set()
                    )
                    tree._rebuild_nodes()

            # Restore scroll position
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if scroll_key in state:
                        tree.scroll_manager.scroll_to(state[scroll_key])
            except Exception:
                pass

            # Restore highlighted index
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if highlight_key in state:
                        tree.highlighted_index = state[highlight_key]
            except Exception:
                pass

        # Create ElementNode
        # Tree has fixed dimensions, so use exact width and height
        node = ElementNode(tree, width=width, height=height)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        # Return empty string (layout will be processed later)
        return ""


class CheckboxExtension(Extension):
    """Jinja2 extension for checkbox tag.

    Syntax:
        {% checkbox id="terms" label="I agree" checked=False action="submit" %}{% endcheckbox %}
    """

    tags = {"checkbox"}

    def parse(self, parser):
        """Parse the checkbox tag."""
        lineno = next(parser.stream).lineno

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endcheckbox"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endcheckbox)
        node = nodes.CallBlock(
            self.call_method("_render_checkbox", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endcheckbox"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_checkbox(
        self,
        caller,
        id=None,
        label="",
        checked=False,
        value="",
        action=None,
        bind=True,
    ) -> str:
        """Render the checkbox tag."""
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("checkbox")

        # If binding is enabled, try to get initial checked state from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        checked = bool(state[id])
            except Exception:
                pass

        # Create Checkbox element
        checkbox = Checkbox(id=id, label=label, checked=checked, value=value)

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            checkbox.focused = True

        # Store action ID if provided
        if action:
            checkbox.action = action

        # Store bind setting
        checkbox.bind = bind

        # Create ElementNode
        from ..terminal.ansi import visible_length

        checkbox_width = visible_length(checkbox.render())
        node = ElementNode(checkbox, width=checkbox_width, height=1)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        return ""


class RadioExtension(Extension):
    """Jinja2 extension for radio tag.

    Syntax:
        {% radio name="size" id="size_m" label="Medium" value="m" checked=False %}{% endradio %}
    """

    tags = {"radio"}

    def parse(self, parser):
        """Parse the radio tag."""
        lineno = next(parser.stream).lineno

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endradio"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endradio)
        node = nodes.CallBlock(
            self.call_method("_render_radio", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endradio"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_radio(
        self,
        caller,
        name,
        id=None,
        label="",
        checked=False,
        value="",
        action=None,
        bind=True,
    ) -> str:
        """Render the radio tag."""
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("radio")

        # If binding is enabled, try to get checked state from state[name]
        if bind and name:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if name in state:
                        # Check if this radio's value matches the group's selected value
                        checked = state[name] == value
            except Exception:
                pass

        # Create Radio element
        radio = Radio(name=name, id=id, label=label, checked=checked, value=value)

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            radio.focused = True

        # Store action ID if provided
        if action:
            radio.action = action

        # Store bind setting
        radio.bind = bind

        # Create ElementNode
        from ..terminal.ansi import visible_length

        radio_width = visible_length(radio.render())
        node = ElementNode(radio, width=radio_width, height=1)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        return ""


class CheckboxGroupExtension(Extension):
    """Jinja2 extension for checkboxgroup tag.

    Syntax:
        {% checkboxgroup id="features" options=["A", "B", "C"]
                         selected=["A"] width=30
                         border="single" title="Select Features" %}
        {% endcheckboxgroup %}
    """

    tags = {"checkboxgroup"}

    def parse(self, parser):
        """Parse the checkboxgroup tag."""
        lineno = next(parser.stream).lineno

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endcheckboxgroup"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endcheckboxgroup)
        node = nodes.CallBlock(
            self.call_method("_render_checkboxgroup", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endcheckboxgroup"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_checkboxgroup(
        self,
        caller,
        id=None,
        options=None,
        selected=None,
        width=20,
        orientation="vertical",
        border_style=None,
        title=None,
        action=None,
        bind=True,
    ) -> str:
        """Render the checkboxgroup tag."""
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Convert numeric parameters
        width = int(width)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("checkboxgroup")

        # If binding is enabled, try to get selected values from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        selected = state[id]
            except Exception:
                pass

        # Ensure selected is a list
        if selected is None:
            selected = []
        elif not isinstance(selected, list):
            selected = list(selected)

        # Ensure options is a list
        if options is None:
            options = []
        elif not isinstance(options, list):
            options = list(options)

        # Create CheckboxGroup element
        checkbox_group = CheckboxGroup(
            id=id,
            options=options,
            selected_values=selected,
            width=width,
            orientation=orientation,
            border_style=border_style,
            title=title,
        )

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            checkbox_group.focused = True

        # Store action ID if provided
        if action:
            checkbox_group.action = action

        # Store bind setting
        checkbox_group.bind = bind

        # Restore highlighted_index from state if available
        if id:
            highlight_key = f"_highlight_{id}"
            checkbox_group.highlight_state_key = highlight_key
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if highlight_key in state:
                        checkbox_group.highlighted_index = state[highlight_key]
            except Exception:
                pass

        # Create ElementNode
        # Calculate total height accounting for borders
        total_height = len(options) + (2 if border_style is not None else 0)
        total_width = width + (2 if border_style is not None else 0)

        node = ElementNode(checkbox_group, width=total_width, height=total_height)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        return ""


class RadioGroupExtension(Extension):
    """Jinja2 extension for radiogroup tag.

    Syntax:
        {% radiogroup name="size" id="size_group" options=["S", "M", "L"]
                      selected="M" width=20
                      border="single" title="Select Size" %}
        {% endradiogroup %}
    """

    tags = {"radiogroup"}

    def parse(self, parser):
        """Parse the radiogroup tag."""
        lineno = next(parser.stream).lineno

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endradiogroup"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endradiogroup)
        node = nodes.CallBlock(
            self.call_method("_render_radiogroup", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endradiogroup"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_radiogroup(
        self,
        caller,
        name,
        id=None,
        options=None,
        selected=None,
        width=20,
        orientation="vertical",
        border_style=None,
        title=None,
        action=None,
        bind=True,
    ) -> str:
        """Render the radiogroup tag."""
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Convert numeric parameters
        width = int(width)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("radiogroup")

        # If binding is enabled, try to get selected value from state[name]
        if bind and name:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if name in state:
                        selected = state[name]
            except Exception:
                pass

        # Ensure options is a list
        if options is None:
            options = []
        elif not isinstance(options, list):
            options = list(options)

        # Create RadioGroup element
        radio_group = RadioGroup(
            name=name,
            id=id,
            options=options,
            selected_value=selected,
            width=width,
            orientation=orientation,
            border_style=border_style,
            title=title,
        )

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            radio_group.focused = True

        # Store action ID if provided
        if action:
            radio_group.action = action

        # Store bind setting
        radio_group.bind = bind

        # Restore highlighted_index from state if available
        if id:
            highlight_key = f"_highlight_{id}"
            radio_group.highlight_state_key = highlight_key
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if highlight_key in state:
                        radio_group.highlighted_index = state[highlight_key]
            except Exception:
                pass

        # Create ElementNode
        # Calculate total height accounting for borders
        total_height = len(options) + (2 if border_style is not None else 0)
        total_width = width + (2 if border_style is not None else 0)

        node = ElementNode(radio_group, width=total_width, height=total_height)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        return ""


class ProgressBarExtension(Extension):
    """Jinja2 extension for progressbar tag.

    Syntax:
        {% progressbar id="download" value=state.progress max=100
                       width=40 style="filled" color="green"
                       show_percentage=True %}
        {% endprogressbar %}
    """

    tags = {"progressbar"}

    def parse(self, parser):
        """Parse the progressbar tag.

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
            "name:endprogressbar"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endprogressbar)
        node = nodes.CallBlock(
            self.call_method("_render_progressbar", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endprogressbar"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_progressbar(
        self,
        caller,
        id=None,
        value=0,
        max=100,
        width=40,
        style="filled",
        color=None,
        show_percentage=None,
        fill_char=None,
        empty_char=None,
        bind=True,
    ) -> str:
        """Render the progressbar tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        value : float or int
            Current progress value (default: 0)
        max : float or int
            Maximum progress value (default: 100)
        width : int
            Progress bar width (default: 40)
        style : str
            Display style: "filled", "percentage", "gradient", "custom" (default: "filled")
        color : str, optional
            Color name for the bar (default: None)
        show_percentage : bool, optional
            Whether to show percentage text (default: auto based on style)
        fill_char : str, optional
            Character for filled portion (default: block character)
        empty_char : str, optional
            Character for empty portion (default: light shade character)
        bind : bool
            Whether to auto-bind value to state[id] (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Convert numeric parameters
        value = float(value)
        max_val = float(max)
        width = int(width)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("progressbar")

        # If binding is enabled and id is provided, try to get value from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        value = float(state[id])
            except Exception:
                pass

        # Convert show_percentage to bool if provided
        if show_percentage is not None:
            show_percentage = bool(show_percentage)

        # Create ProgressBar element
        from ..elements.display import ProgressBar

        progressbar = ProgressBar(
            id=id,
            value=value,
            max=max_val,
            width=width,
            style=style,
            color=color,
            show_percentage=show_percentage,
            fill_char=fill_char,
            empty_char=empty_char,
        )

        # Store bind setting
        progressbar.bind = bind

        # Create ElementNode
        # Progress bar is always single line
        node = ElementNode(progressbar, width=width, height=1)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        return ""


class SpinnerExtension(Extension):
    """Jinja2 extension for spinner tag.

    Syntax:
        {% spinner id="loading" active=state.loading
                   style="dots" label="Loading..." color="cyan" %}
        {% endspinner %}
    """

    tags = {"spinner"}

    def parse(self, parser):
        """Parse the spinner tag.

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
            "name:endspinner"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endspinner)
        node = nodes.CallBlock(
            self.call_method("_render_spinner", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endspinner"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_spinner(
        self,
        caller,
        id=None,
        active=True,
        style="dots",
        label="",
        color=None,
        bind=True,
    ) -> str:
        """Render the spinner tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        active : bool
            Whether spinner is active and animating (default: True)
        style : str
            Animation style: "dots", "line", "bouncing", "clock" (default: "dots")
        label : str
            Label text to display next to spinner (default: "")
        color : str, optional
            Color name for the spinner (default: None)
        bind : bool
            Whether to auto-bind active state to state[id] (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Convert active to bool
        active = bool(active)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("spinner")

        # If binding is enabled and id is provided, try to get active state from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        active = bool(state[id])
            except Exception:
                pass

        # Get or restore frame index from state
        frame_index = 0
        frame_key = f"_spinner_frame_{id}"
        try:
            ctx = self.environment.globals.get("_wijjit_current_context")
            if ctx and "state" in ctx:
                state = ctx["state"]
                if frame_key in state:
                    frame_index = int(state[frame_key])
        except Exception:
            pass

        # Create Spinner element
        from ..elements.display import Spinner

        spinner = Spinner(
            id=id,
            active=active,
            style=style,
            label=label,
            color=color,
            frame_index=frame_index,
        )

        # Store bind setting
        spinner.bind = bind

        # Store state dict reference for frame updates
        try:
            ctx = self.environment.globals.get("_wijjit_current_context")
            if ctx and "state" in ctx:
                spinner._state_dict = ctx["state"]
                spinner._frame_key = frame_key
        except Exception:
            pass

        # Calculate width based on label and spinner character
        # Spinner is typically 1-2 chars wide, plus space, plus label length
        spinner_width = 3 + len(label) if label else 2

        # Create ElementNode
        # Spinner is always single line
        node = ElementNode(spinner, width=spinner_width, height=1)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        return ""


class MarkdownExtension(Extension):
    """Jinja2 extension for markdown tag.

    Syntax:
        {% markdown content=state.readme width=80 height=20
                    border="single" title="Documentation"
                    show_scrollbar=true %}
        {% endmarkdown %}

        Or with body content:
        {% markdown width=80 height=20 %}
            # Hello World
            This is **markdown** content.
        {% endmarkdown %}
    """

    tags = {"markdown"}

    def parse(self, parser):
        """Parse the markdown tag.

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
            "name:endmarkdown"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (markdown content)
        node = nodes.CallBlock(
            self.call_method("_render_markdown", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endmarkdown"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_markdown(
        self,
        caller,
        id=None,
        content=None,
        width="fill",
        height="fill",
        show_scrollbar=True,
        border_style="single",
        title=None,
        bind=True,
    ) -> str:
        """Render the markdown tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        content : str, optional
            Markdown content (if not provided in body)
        width : int or str
            Markdown view width (default: "fill")
        height : int or str
            Markdown view height (default: "fill")
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        border_style : str
            Border style (default: "single")
        title : str, optional
            Border title
        bind : bool
            Whether to auto-bind content to state[id] (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Store original width/height specs for ElementNode
        width_spec = width
        height_spec = height

        # Convert numeric parameters for element creation
        # If width/height are "fill" or other string specs, use default numeric values
        # for initial element creation (will be resized on bounds assignment)
        if isinstance(width, str) and not width.isdigit():
            element_width = 60  # Default for initial render
        else:
            element_width = int(width)

        if isinstance(height, str) and not height.isdigit():
            element_height = 20  # Default for initial render
        else:
            element_height = int(height)

        show_scrollbar = bool(show_scrollbar)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("markdown")

        # Get content from body if not provided as attribute
        if content is None:
            body = caller().strip()
            content = body if body else ""
        else:
            # Content provided as attribute, consume body anyway
            caller()

        # If binding is enabled and id is provided, try to get content from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        content = str(state[id])
            except Exception:
                pass

        # Create MarkdownView element
        from ..elements.display import MarkdownView

        markdown = MarkdownView(
            id=id,
            content=content,
            width=element_width,
            height=element_height,
            show_scrollbar=show_scrollbar,
            border_style=border_style,
            title=title,
        )

        # Store the dynamic sizing flag
        markdown._dynamic_sizing = (width_spec == "fill" or height_spec == "fill")

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            markdown.focused = True

        # Store bind setting
        markdown.bind = bind

        # Restore scroll position from state if available
        if id:
            scroll_key = f"_scroll_{id}"
            markdown.scroll_state_key = scroll_key
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if scroll_key in state:
                        markdown.restore_scroll_position(state[scroll_key])
            except Exception:
                pass

        # Create ElementNode
        # Use width_spec/height_spec directly for ElementNode (supports "fill")
        node = ElementNode(markdown, width=width_spec, height=height_spec)

        # Add to layout context
        context.add_element(node)

        return ""


class CodeBlockExtension(Extension):
    """Jinja2 extension for code tag.

        Syntax:
            {% code language="python" width=80 height=20
                    line_numbers=true border="single" title="Example" %}
    {{ state.code }}
            {% endcode %}

            Or with static code:
            {% code language="javascript" %}
    function hello() {
        console.log("Hello, world!");
    }
            {% endcode %}
    """

    tags = {"code"}

    def parse(self, parser):
        """Parse the code tag.

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
            "name:endcode"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (code content)
        node = nodes.CallBlock(
            self.call_method("_render_code", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endcode"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_code(
        self,
        caller,
        id=None,
        code=None,
        language="python",
        width=60,
        height=20,
        show_line_numbers=True,
        line_number_start=1,
        show_scrollbar=True,
        border_style="single",
        title=None,
        theme="monokai",
        bind=True,
        raw=True,
    ) -> str:
        """Render the code tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        code : str, optional
            Code content (if not provided in body)
        language : str
            Programming language (default: "python")
        width : int
            Code block width (default: 60)
        height : int
            Code block height (default: 20)
        show_line_numbers : bool
            Whether to show line numbers (default: True)
        line_number_start : int
            Starting line number (default: 1)
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        border_style : str
            Border style (default: "single")
        title : str, optional
            Border title
        theme : str
            Syntax highlighting theme (default: "monokai")
        bind : bool
            Whether to auto-bind code to state[id] (default: True)
        raw : bool
            Preserve whitespace in body content (default: True for code)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Convert numeric parameters
        width = int(width)
        height = int(height)
        show_line_numbers = bool(show_line_numbers)
        line_number_start = int(line_number_start)
        show_scrollbar = bool(show_scrollbar)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("code")

        # Get code from body if not provided as attribute
        if code is None:
            body_output = caller()
            # For code blocks, preserve whitespace by default
            code = process_body_content(body_output, raw=raw)
        else:
            # Code provided as attribute, consume body anyway
            caller()

        # If binding is enabled and id is provided, try to get code from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        code = str(state[id])
            except Exception:
                pass

        # Create CodeBlock element
        from ..elements.display import CodeBlock

        codeblock = CodeBlock(
            id=id,
            code=code,
            language=language,
            width=width,
            height=height,
            show_line_numbers=show_line_numbers,
            line_number_start=line_number_start,
            show_scrollbar=show_scrollbar,
            border_style=border_style,
            title=title,
            theme=theme,
        )

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            codeblock.focused = True

        # Store bind setting
        codeblock.bind = bind

        # Restore scroll position from state if available
        if id:
            scroll_key = f"_scroll_{id}"
            codeblock.scroll_state_key = scroll_key
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if scroll_key in state:
                        codeblock.restore_scroll_position(state[scroll_key])
            except Exception:
                pass

        # Create ElementNode
        # Calculate total height accounting for borders
        total_height = height + (2 if border_style != "none" else 0)
        total_width = width + (2 if border_style != "none" else 0)

        node = ElementNode(codeblock, width=total_width, height=total_height)

        # Add to layout context
        context.add_element(node)

        return ""


class TextAreaExtension(Extension):
    """Jinja2 extension for textarea tag.

    Syntax:
        {% textarea id="editor" value=state.content
                    width=60 height=15 wrap_mode="soft"
                    border="single" title="Editor" %}
        {% endtextarea %}
    """

    tags = {"textarea"}

    def parse(self, parser):
        """Parse the textarea tag.

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
            "name:endtextarea"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endtextarea)
        node = nodes.CallBlock(
            self.call_method("_render_textarea", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endtextarea"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_textarea(
        self,
        caller,
        id=None,
        value="",
        width="auto",
        height="auto",
        wrap_mode="none",
        max_lines=None,
        show_scrollbar=True,
        border_style="single",
        action=None,
        bind=True,
    ) -> str:
        """Render the textarea tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        value : str
            Initial value (default: "")
        width : int or str
            TextArea width (default: "auto")
        height : int or str
            TextArea height (default: "auto")
        wrap_mode : str
            Line wrapping mode: "none", "soft", or "hard" (default: "none")
        max_lines : int, optional
            Maximum number of lines
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        border_style : str
            Border style (default: "single")
        action : str, optional
            Action ID to dispatch on content change
        bind : bool
            Whether to auto-bind value to state[id] (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Store original width/height specs for ElementNode
        width_spec = width
        height_spec = height

        # Convert numeric parameters for element creation
        # If width/height are "fill" or other string specs, use default numeric values
        # for initial element creation (will be resized on bounds assignment)
        if isinstance(width, str) and not width.isdigit():
            element_width = 40  # Default for initial render
        else:
            element_width = int(width)

        if isinstance(height, str) and not height.isdigit():
            element_height = 10  # Default for initial render
        else:
            element_height = int(height)

        show_scrollbar = bool(show_scrollbar)
        if max_lines is not None:
            max_lines = int(max_lines)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("textarea")

        # Get initial value from body if not provided as attribute
        if not value:
            body = caller().strip()
            value = body if body else ""
        else:
            # Value provided as attribute, consume body anyway
            caller()

        # If binding is enabled and id is provided, try to get value from state
        # (state value takes precedence over body/value parameter)
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        value = str(state[id])
            except Exception:
                pass

        # Create TextArea element
        textarea = TextArea(
            id=id,
            value=value,
            width=element_width,
            height=element_height,
            wrap_mode=wrap_mode,
            max_lines=max_lines,
            show_scrollbar=show_scrollbar,
            border_style=border_style,
        )

        # Store the dynamic sizing flag
        textarea._dynamic_sizing = (width_spec == "fill" or height_spec == "fill")

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            textarea.focused = True

        # Store action ID if provided
        if action:
            textarea.action = action

        # Store bind setting
        textarea.bind = bind

        # Create ElementNode
        # Use width_spec/height_spec directly for ElementNode (supports "fill")
        node = ElementNode(textarea, width=width_spec, height=height_spec)

        # Add to layout context
        context.add_element(node)

        return ""
