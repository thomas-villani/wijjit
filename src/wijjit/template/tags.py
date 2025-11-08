"""Jinja2 custom tag extensions for declarative UI definition.

This module provides custom Jinja2 tags that create layout nodes and elements
during template rendering. The layout tree is built up in a context variable
and then processed by the layout engine after rendering.
"""

from typing import Any

from jinja2 import nodes
from jinja2.ext import Extension

from ..elements.base import TextElement
from ..elements.input import Button, Select, TextInput
from ..layout.engine import ElementNode, HStack, LayoutNode, VStack


class LayoutContext:
    """Context for building layout tree during template rendering.

    Attributes
    ----------
    root : LayoutNode or None
        Root of the layout tree
    stack : list of LayoutNode
        Stack of container nodes being processed
    """

    def __init__(self):
        self.root: LayoutNode | None = None
        self.stack: list[LayoutNode] = []

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
        height="auto",
        spacing=0,
        padding=0,
        margin=0,
        align_h="stretch",
        align_v="stretch",
        id=None,
    ) -> str:
        """Render the vstack tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        width : int or str
            Width specification
        height : int or str
            Height specification
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

        # If body contains non-whitespace text, create TextElement and INSERT at beginning
        # (This is because child elements add themselves during caller(), so text appears after them)
        if body_output and body_output.strip():
            text_elem = TextElement(body_output.strip())
            text_node = ElementNode(text_elem, width="auto", height="auto")
            # Insert at beginning of children list instead of appending
            if vstack.children:
                vstack.children.insert(0, text_node)
            else:
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
        height="fill",
        spacing=0,
        padding=0,
        margin=0,
        align_h="stretch",
        align_v="stretch",
        id=None,
    ) -> str:
        """Render the hstack tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        width : int or str
            Width specification
        height : int or str
            Height specification
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

        # If body contains non-whitespace text, create TextElement and INSERT at beginning
        # (This is because child elements add themselves during caller(), so text appears after them)
        if body_output and body_output.strip():
            text_elem = TextElement(body_output.strip())
            text_node = ElementNode(text_elem, width="auto", height="auto")
            # Insert at beginning of children list instead of appending
            if hstack.children:
                hstack.children.insert(0, text_node)
            else:
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

        # Create VStack to hold frame content
        # (Frame is a visual wrapper, we need a container for children)
        # Note: content_align_h/v controls how children are aligned INSIDE the frame
        frame_container = VStack(
            children=[],
            width=width,
            height=height,
            spacing=0,
            padding=1,  # Frame has implicit padding
            margin=margin,
            align_h=content_align_h,  # Use content alignment to position frame's children
            align_v=content_align_v,
            id=id,
        )

        # Store the frame-level alignment as metadata for potential future use
        # (Currently, frame-level alignment requires parent container support)
        frame_container._frame_align_h = align_h
        frame_container._frame_align_v = align_v

        # Store frame styling info on the container
        # (We'll apply this during rendering)
        frame_container._frame_style = {
            "title": title,
            "border": border,
        }

        # Push onto stack
        context.push(frame_container)

        # Render body
        body_output = caller()

        # If body contains non-whitespace text, create TextElement and INSERT at beginning
        # (This is because child elements add themselves during caller(), so text appears after them)
        if body_output and body_output.strip():
            text_elem = TextElement(body_output.strip())
            text_node = ElementNode(text_elem, width="auto", height="auto")
            # Insert at beginning of children list instead of appending
            if frame_container.children:
                frame_container.children.insert(0, text_node)
            else:
                frame_container.children.append(text_node)

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

        # Create ElementNode
        # Height is fixed at visible_rows since it's always displaying that many rows
        node = ElementNode(select, width=width, height=visible_rows)

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
