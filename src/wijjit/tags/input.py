"""Jinja2 template extensions for input elements.

This module provides Jinja2 template tag extensions for input elements
including text inputs, text areas, buttons, selects, checkboxes, and
radio buttons.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.core.render_context import get_render_context
from wijjit.core.vdom import VNodeBuilder
from wijjit.layout.frames import BorderStyle
from wijjit.logging_config import get_logger
from wijjit.tags.layout import (
    get_element_marker,
    normalize_element_kwargs,
    parse_tag_attributes,
    safe_int,
)

if TYPE_CHECKING:
    from wijjit.autocomplete.completer import Completer

# Get logger for this module
logger = get_logger(__name__)


class TextInputExtension(Extension):
    """Jinja2 extension for {% textinput %} tag.

    Syntax:
        {% textinput id="name" placeholder="Enter name" width=30 %}{% endtextinput %}
    """

    tags = {"textinput"}

    def parse(self, parser: Parser) -> nodes.Node:
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
        kwargs = parse_tag_attributes(parser, "endtextinput", lineno)

        # Parse body (should be empty, but we need to consume until endtextinput)
        node = nodes.CallBlock(
            self.call_method("_render_textinput", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endtextinput",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_textinput(
        self,
        caller: Any,
        id: str | None = None,
        placeholder: str = "",
        width: int = 20,
        value: str = "",
        action: str | None = None,
        bind: bool = True,
        autocomplete: list[str] | str | bool | Completer | None = None,
        **kwargs: Any,
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
        autocomplete : list, str, bool, Completer, or None
            Autocomplete configuration. Can be:
            - None/False: Disabled (default)
            - list: Word list to use for suggestions
            - "state.key": Reference to state key containing word list
            - "name": Name of registered completer in app.completers
            - True: Auto-wire by element ID lookup in app.completers
            - Completer: Direct completer instance
        classes : str, optional
            CSS-like class names for styling

        Returns
        -------
        str
            Rendered output
        """
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Convert width to int safely
        width = safe_int(width, default=30, name="width")

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("textinput")

        # If binding is enabled and id is provided, try to get initial value from state
        if bind and id:
            try:
                if id in state:
                    value = str(state[id])
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for textinput '{id}': {e}")

        # Create VNode for reconciliation
        vnode = VNodeBuilder("TextInput", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("value", value)
        vnode.set_prop("placeholder", placeholder)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("width", width)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)

        # Pass autocomplete spec for resolution in wiring phase
        if autocomplete is not None:
            vnode.set_prop("autocomplete", autocomplete)

        # Check if this element should be focused
        if focused_id and id and focused_id == id:
            vnode.set_prop("focused", True)

        # Add any additional properties from kwargs (e.g., max_length, style, password)
        for key, val in kwargs.items():
            vnode.set_prop(key, val)

        # Calculate layout width including border characters based on style
        # Default style is BRACKETS which has left and right borders
        style = kwargs.get("style", "brackets")
        # Normalize style to string for comparison
        if hasattr(style, "name"):
            # Handle InputStyle enum
            style_name = style.name.lower()
        elif isinstance(style, str):
            style_name = style.lower()
        else:
            style_name = "brackets"  # Default
        # BRACKETS, BOX, and BLOCK styles have 2-character border overhead
        # UNDERLINE and MINIMAL have no side borders
        if style_name in ("brackets", "box", "block"):
            layout_width = width + 2
        else:
            layout_width = width

        vnode.set_layout(width=layout_width, height=1)
        layout_context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(layout_context)


class ButtonExtension(Extension):
    """Jinja2 extension for {% button %} tag.

    Syntax:
        {% button id="submit" %}Submit{% endbutton %}
    """

    tags = {"button"}

    def parse(self, parser: Parser) -> nodes.Node:
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
        kwargs = parse_tag_attributes(parser, "endbutton", lineno)

        # Parse body (button label)
        node = nodes.CallBlock(
            self.call_method("_render_button", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endbutton",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_button(
        self,
        caller: Any,
        id: str | None = None,
        action: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the button tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content (button label)
        id : str, optional
            Element identifier
        action : str, optional
            Action ID to dispatch when button is clicked
        classes : str, optional
            CSS-like class names for styling
        tab_index : int, optional
            Tab order for focus navigation

        Returns
        -------
        str
            Rendered output
        """
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        focused_id = render_ctx.focused_id

        # Get button label from body
        label = caller().strip()

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("button")

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Create VNode for reconciliation
        # Button width is based on label length + brackets
        button_width = len(label) + 4  # "< label >"
        vnode = VNodeBuilder("Button", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("label", label)
        vnode.set_prop("action", action)
        vnode.set_prop("classes", classes)
        vnode.set_prop("focused", is_focused)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)
        vnode.set_layout(width=button_width, height=1)
        layout_context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(layout_context)


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

    def parse(self, parser: Parser) -> nodes.Node:
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
        kwargs = parse_tag_attributes(parser, "endselect", lineno)

        # Parse body (options list)
        node = nodes.CallBlock(
            self.call_method("_render_select", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endselect",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_select(
        self,
        caller: Any,
        id: str | None = None,
        options: list[Any] | None = None,
        value: str | None = None,
        values: list[Any] | None = None,
        multiple: bool = False,
        width: int = 20,
        visible_rows: int = 5,
        action: str | None = None,
        bind: bool = True,
        border_style: (
            BorderStyle | Literal["single", "double", "rounded"] | None
        ) = None,
        title: str | None = None,
        **kwargs: Any,
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
            Initial selected value (single-select mode)
        values : list, optional
            Initial selected values (multi-select mode)
        multiple : bool
            Enable multiple selection mode (default: False)
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
        classes : str, optional
            CSS-like class names for styling
        tab_index : int, optional
            Tab order for focus navigation

        Returns
        -------
        str
            Rendered output
        """
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Convert numeric parameters safely
        width = safe_int(width, default=20, name="width")
        visible_rows = safe_int(visible_rows, default=5, name="visible_rows")

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
        disabled_values: list[str] = []
        cleaned_options: list[Any] = []
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
                if id in state:
                    state_value = state[id]
                    if multiple:
                        # Multi-select: expect list/set from state
                        if isinstance(state_value, (list, set, tuple)):
                            values = list(state_value)
                        elif state_value is not None:
                            values = [str(state_value)]
                    else:
                        # Single-select: expect string from state
                        value = str(state_value) if state_value is not None else None
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for select '{id}': {e}")

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Calculate total height accounting for borders
        # - No borders: height = visible_rows (content only)
        # - With borders: height = visible_rows + 2 (top border + content + bottom border)
        total_height = visible_rows + (2 if border_style is not None else 0)

        # Width also needs to account for borders (adds 2 columns)
        total_width = width + (2 if border_style is not None else 0)

        # Create VNode for reconciliation
        vnode = VNodeBuilder("Select", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("multiple", multiple)
        if multiple:
            vnode.set_prop("values", values or [])
        else:
            vnode.set_prop("value", value)
        vnode.set_prop("options", cleaned_options)
        vnode.set_prop("width", width)
        vnode.set_prop("visible_rows", visible_rows)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("title", title)
        vnode.set_prop("disabled_values", disabled_values)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)
        vnode.set_layout(width=total_width, height=total_height)
        context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(context)

    def _parse_options_from_body(self, body: str) -> list[Any]:
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
                    opt_dict = json.loads(line)
                    options.append(opt_dict)
                    continue
                except (json.JSONDecodeError, ValueError):
                    pass

            # Otherwise treat as plain string option
            options.append(line)

        return options


class CheckboxExtension(Extension):
    """Jinja2 extension for checkbox tag.

    Syntax:
        {% checkbox id="terms" label="I agree" checked=False action="submit" %}{% endcheckbox %}
    """

    tags = {"checkbox"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the checkbox tag."""
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endcheckbox", lineno)

        # Parse body (should be empty, but consume until endcheckbox)
        node = nodes.CallBlock(
            self.call_method("_render_checkbox", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endcheckbox",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_checkbox(
        self,
        caller: Any,
        id: str | None = None,
        label: str = "",
        checked: bool = False,
        value: str = "",
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the checkbox tag."""
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("checkbox")

        # If binding is enabled, try to get initial checked state from state
        if bind and id:
            try:
                if id in state:
                    checked = bool(state[id])
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for checkbox '{id}': {e}")

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Get label from body content if not specified via label attribute
        body_content = caller().strip()
        if not label and body_content:
            label = body_content

        # Checkbox width: "[X] " (4 chars) + label length
        checkbox_width = 4 + len(label)

        # Create VNode for reconciliation
        vnode = VNodeBuilder("Checkbox", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("label", label)
        vnode.set_prop("checked", checked)
        vnode.set_prop("value", value)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)
        vnode.set_layout(width=checkbox_width, height=1)
        context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(context)


class RadioExtension(Extension):
    """Jinja2 extension for radio tag.

    Syntax:
        {% radio name="size" id="size_m" label="Medium" value="m" checked=False %}{% endradio %}
    """

    tags = {"radio"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the radio tag."""
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endradio", lineno)

        # Parse body (should be empty, but consume until endradio)
        node = nodes.CallBlock(
            self.call_method("_render_radio", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endradio",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_radio(
        self,
        caller: Any,
        name: str | None = None,
        id: str | None = None,
        label: str = "",
        checked: bool = False,
        value: str = "",
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the radio tag."""
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("radio")

        # Get label from body content if not provided as parameter
        if not label:
            label = caller().strip()
        else:
            # Still need to consume body
            caller()

        # If name not provided, try to get it from radiogroup context
        if name is None:
            name = render_ctx.current_radiogroup

        # If binding is enabled, try to get checked state from state[name]
        if bind and name:
            try:
                if name in state:
                    # Check if this radio's value matches the group's selected value
                    checked = state[name] == value
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for radio '{name}': {e}")

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Radio width: "(o) " (4 chars) + label length
        radio_width = 4 + len(label)

        # Create VNode for reconciliation
        vnode = VNodeBuilder("Radio", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("name", name or "")
        vnode.set_prop("label", label)
        vnode.set_prop("checked", checked)
        vnode.set_prop("value", value)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)
        vnode.set_layout(width=radio_width, height=1)
        context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(context)


class CheckboxGroupExtension(Extension):
    """Jinja2 extension for checkboxgroup tag.

    Syntax:
        {% checkboxgroup id="features" options=["A", "B", "C"]
                         selected=["A"] width=30
                         border="single" title="Select Features" %}
        {% endcheckboxgroup %}
    """

    tags = {"checkboxgroup"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the checkboxgroup tag."""
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endcheckboxgroup", lineno)

        # Parse body (should be empty, but consume until endcheckboxgroup)
        node = nodes.CallBlock(
            self.call_method("_render_checkboxgroup", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endcheckboxgroup",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_checkboxgroup(
        self,
        caller: Any,
        id: str | None = None,
        options: list[Any] | None = None,
        selected: list[Any] | None = None,
        width: int = 20,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        border_style: (
            BorderStyle | Literal["single", "double", "rounded"] | None
        ) = None,
        title: str | None = None,
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the checkboxgroup tag."""
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Convert numeric parameters
        width = int(width)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("checkboxgroup")

        # If binding is enabled, try to get selected values from state
        if bind and id:
            try:
                if id in state:
                    selected = state[id]
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(
                    f"Failed to restore state for checkbox_group '{id}': {e}"
                )

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

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Calculate total height accounting for borders
        total_height = len(options) + (2 if border_style is not None else 0)
        total_width = width + (2 if border_style is not None else 0)

        # Create VNode for reconciliation
        vnode = VNodeBuilder("CheckboxGroup", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("options", options)
        vnode.set_prop("selected_values", selected)
        vnode.set_prop("width", width)
        vnode.set_prop("orientation", orientation)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("title", title)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)
        vnode.set_layout(width=total_width, height=total_height)
        context.add_vnode(vnode)

        # Save marker now, before any nested elements are processed
        my_marker = get_element_marker(context)

        # Consume body (should be empty)
        caller()

        # Return marker for text interleaving (saved before processing body)
        return my_marker


class RadioGroupExtension(Extension):
    """Jinja2 extension for radiogroup tag.

    Syntax:
        {% radiogroup name="size" id="size_group" options=["S", "M", "L"]
                      selected="M" width=20
                      border="single" title="Select Size" %}
        {% endradiogroup %}
    """

    tags = {"radiogroup"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the radiogroup tag."""
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endradiogroup", lineno)

        # Parse body (should be empty, but consume until endradiogroup)
        node = nodes.CallBlock(
            self.call_method("_render_radiogroup", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endradiogroup",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_radiogroup(
        self,
        caller: Any,
        name: str | None = None,
        id: str | None = None,
        options: list[Any] | None = None,
        selected: str | None = None,
        width: int = 20,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        border_style: (
            BorderStyle | Literal["single", "double", "rounded"] | None
        ) = None,
        title: str | None = None,
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the radiogroup tag."""
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Convert numeric parameters
        width = int(width)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("radiogroup")

        # If name not provided, use id as the state binding key
        if name is None:
            name = id

        # If binding is enabled, try to get selected value from state[name]
        if bind and name:
            try:
                if name in state:
                    selected = state[name]
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for radio_group '{name}': {e}")

        # Ensure options is a list
        if options is None:
            options = []
        elif not isinstance(options, list):
            options = list(options)

        # Determine if using nested radio tags (no options provided)
        using_nested_radios = len(options) == 0
        using_frame = using_nested_radios and (
            border_style is not None or title is not None
        )

        if not using_nested_radios:
            # Check if this element should be focused
            is_focused = focused_id and id and focused_id == id

            # Calculate total height accounting for borders
            total_height = len(options) + (2 if border_style is not None else 0)
            total_width = width + (2 if border_style is not None else 0)

            # Create VNode for reconciliation
            vnode = VNodeBuilder("RadioGroup", key=id)
            vnode.set_prop("id", id)  # Set id as prop so Element gets it
            vnode.set_prop("name", name)
            vnode.set_prop("options", options)
            vnode.set_prop("selected_value", selected)
            vnode.set_prop("width", width)
            vnode.set_prop("orientation", orientation)
            vnode.set_prop("border_style", border_style)
            vnode.set_prop("title", title)
            vnode.set_prop("action", action)
            vnode.set_prop("bind", bind)
            vnode.set_prop("focused", is_focused)
            if classes is not None:
                vnode.set_prop("classes", classes)
            if tab_index is not None:
                vnode.set_prop("tab_index", tab_index)
            vnode.set_layout(width=total_width, height=total_height)
            context.add_vnode(vnode)

            # Return marker immediately for non-nested radiogroups
            return get_element_marker(context)

        # Handle nested radios (with or without frame)
        if using_nested_radios and not using_frame:
            # For nested radios without a frame, create a VStack VNode
            vstack_vnode = VNodeBuilder("VStack", key=id)
            vstack_vnode.set_layout(width="auto", height="auto")
            context.push_vnode(vstack_vnode)

        # For nested radios with borders/titles, create a frame VNode
        elif using_frame:
            # Map border_style string to BorderStyle enum
            border_style_map = {
                "single": BorderStyle.SINGLE,
                "double": BorderStyle.DOUBLE,
                "rounded": BorderStyle.ROUNDED,
            }
            if isinstance(border_style, str):
                border_enum = border_style_map.get(
                    border_style.lower(), BorderStyle.SINGLE
                )
            else:
                border_enum = (
                    border_style if border_style is not None else BorderStyle.SINGLE
                )

            # Create VNode builder for reconciliation
            frame_vnode = VNodeBuilder("Frame", key=id)
            frame_vnode.set_prop("border_style", border_enum)
            frame_vnode.set_prop("title", title)
            frame_vnode.set_prop("scrollable", False)
            frame_vnode.set_layout(
                width="auto",
                height="auto",
                padding=(1, 1, 1, 1),
                margin=0,
            )
            context.push_vnode(frame_vnode)

        # Set radiogroup name in RenderContext for nested radio tags to access
        render_ctx.push_radiogroup(name)

        try:
            # Render body (may contain nested {% radio %} tags)
            caller()
        finally:
            # Restore previous radiogroup context
            render_ctx.pop_radiogroup()

            # Pop VNode from stack if we created one
            if using_nested_radios:
                context.pop_vnode()

        # Return marker for text interleaving (get after popping so parent is on top of stack)
        return get_element_marker(context)


class TextAreaExtension(Extension):
    """Jinja2 extension for textarea tag.

    Syntax:
        {% textarea id="editor" value=state.content
                    width=60 height=15 wrap_mode="soft"
                    border="single" title="Editor" %}
        {% endtextarea %}
    """

    tags = {"textarea"}

    def parse(self, parser: Parser) -> nodes.Node:
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
        kwargs = parse_tag_attributes(parser, "endtextarea", lineno)

        # Parse body (should be empty, but consume until endtextarea)
        node = nodes.CallBlock(
            self.call_method("_render_textarea", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endtextarea",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_textarea(
        self,
        caller: Any,
        id: str | None = None,
        value: str = "",
        width: int | str = "auto",
        height: int | str = "auto",
        wrap_mode: Literal["none", "soft", "hard"] = "none",
        max_lines: int | None = None,
        show_scrollbar: bool = True,
        show_scrollbar_x: bool = False,
        border_style: BorderStyle | Literal["single", "double", "rounded"] = "single",
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
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
            Whether to show vertical scrollbar (default: True)
        show_scrollbar_x : bool
            Whether to show horizontal scrollbar when needed (default: False)
        border_style : str
            Border style (default: "single")
        action : str, optional
            Action ID to dispatch on content change
        bind : bool
            Whether to auto-bind value to state[id] (default: True)
        classes : str, optional
            CSS-like class names for styling
        tab_index : int, optional
            Tab order for focus navigation

        Returns
        -------
        str
            Rendered output
        """
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Store original width/height specs for layout
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
        show_scrollbar_x = bool(show_scrollbar_x)
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
                if id in state:
                    value = str(state[id])
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for textarea '{id}': {e}")

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Create VNode for reconciliation
        vnode = VNodeBuilder("TextArea", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("value", value)
        vnode.set_prop("width", element_width)
        vnode.set_prop("height", element_height)
        vnode.set_prop("wrap_mode", wrap_mode)
        vnode.set_prop("max_lines", max_lines)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("show_scrollbar_x", show_scrollbar_x)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)

        # Account for borders in layout size if present
        layout_width = width_spec
        layout_height = height_spec
        if border_style not in (None, "none"):
            # Add 2 for borders (top+bottom, left+right) if width/height are numeric
            if isinstance(width_spec, int):
                layout_width = width_spec + 2
            if isinstance(height_spec, int):
                layout_height = height_spec + 2

        vnode.set_layout(width=layout_width, height=layout_height)
        context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(context)


class CodeEditorExtension(Extension):
    """Jinja2 extension for codeeditor tag.

    Syntax:
        {% codeeditor id="editor" language="python" theme="monokai"
                      width=80 height=25 show_line_numbers=True %}
        {% endcodeeditor %}
    """

    tags = {"codeeditor"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the codeeditor tag.

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
        kwargs = parse_tag_attributes(parser, "endcodeeditor", lineno)

        # Parse body (should be empty, but consume until endcodeeditor)
        node = nodes.CallBlock(
            self.call_method("_render_codeeditor", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endcodeeditor",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_codeeditor(
        self,
        caller: Any,
        id: str | None = None,
        value: str = "",
        language: str | None = "python",
        theme: str = "monokai",
        filename_hint: str | None = None,
        width: int | str = 60,
        height: int | str = 20,
        show_line_numbers: bool = True,
        wrap_mode: Literal["none", "soft"] = "none",
        show_scrollbar: bool = True,
        border_style: BorderStyle | Literal["single", "double", "rounded"] = "single",
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the codeeditor tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        value : str
            Initial source code (default: "")
        language : str, optional
            Programming language (default: "python").
            Use "auto" for auto-detection, None to disable highlighting.
        theme : str
            Color theme name (default: "monokai")
        filename_hint : str, optional
            Filename hint for auto-detection
        width : int or str
            Editor width (default: 60)
        height : int or str
            Editor height (default: 20)
        show_line_numbers : bool
            Whether to show line numbers (default: True)
        wrap_mode : str
            Line wrapping mode: "none" or "soft" (default: "none")
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        border_style : str
            Border style (default: "single")
        action : str, optional
            Action ID to dispatch on content change
        bind : bool
            Whether to auto-bind value to state[id] (default: True)
        classes : str, optional
            CSS-like class names for styling
        tab_index : int, optional
            Tab order for focus navigation

        Returns
        -------
        str
            Rendered output
        """
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Store original width/height specs for layout
        width_spec = width
        height_spec = height

        # Convert numeric parameters
        if isinstance(width, str) and not width.isdigit():
            element_width = 60  # Default
        else:
            element_width = int(width)

        if isinstance(height, str) and not height.isdigit():
            element_height = 20  # Default
        else:
            element_height = int(height)

        show_scrollbar = bool(show_scrollbar)
        show_line_numbers = bool(show_line_numbers)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("codeeditor")

        # Get initial value from body if not provided
        if not value:
            body = caller().strip()
            value = body if body else ""
        else:
            caller()  # Consume body anyway

        # Get value from state if binding is enabled
        if bind and id:
            try:
                if id in state:
                    value = str(state[id])
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for codeeditor '{id}': {e}")

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Create VNode for reconciliation
        vnode = VNodeBuilder("CodeEditor", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("value", value)
        vnode.set_prop("language", language)
        vnode.set_prop("theme", theme)
        vnode.set_prop("filename_hint", filename_hint)
        vnode.set_prop("width", element_width)
        vnode.set_prop("height", element_height)
        vnode.set_prop("show_line_numbers", show_line_numbers)
        vnode.set_prop("wrap_mode", wrap_mode)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)

        # Account for borders in layout size if present
        layout_width = width_spec
        layout_height = height_spec
        if border_style not in (None, "none"):
            # Add 2 for borders (top+bottom, left+right) if width/height are numeric
            if isinstance(width_spec, int):
                layout_width = width_spec + 2
            if isinstance(height_spec, int):
                layout_height = height_spec + 2

        vnode.set_layout(width=layout_width, height=layout_height)
        context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(context)


class SliderExtension(Extension):
    """Jinja2 extension for {% slider %} tag.

    Syntax:
        {% slider id="volume" min=0 max=100 value=50 %}{% endslider %}
        {% slider id="opacity" min=0.0 max=1.0 step=0.1 float_mode=True %}{% endslider %}
        {% slider id="brightness" label="Brightness" width=30 %}{% endslider %}
    """

    tags = {"slider"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the slider tag."""
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endslider", lineno)

        node = nodes.CallBlock(
            self.call_method("_render_slider", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endslider",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_slider(
        self,
        caller: Any,
        id: str | None = None,
        min: float = 0,
        max: float = 100,
        value: float | None = None,
        step: float = 1,
        width: int = 20,
        float_mode: bool = False,
        label: str | None = None,
        show_value: bool = True,
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the slider tag."""
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        width = safe_int(width, default=20, name="width")
        min_val = float(min)
        max_val = float(max)
        step_val = float(step)

        if value is None:
            value = min_val
        else:
            value = float(value)

        if id is None:
            id = context.generate_id("slider")

        if bind and id:
            try:
                if id in state:
                    value = float(state[id])
            except (KeyError, TypeError, AttributeError, ValueError) as e:
                logger.warning(f"Failed to restore state for slider '{id}': {e}")

        is_focused = focused_id and id and focused_id == id

        caller()

        layout_width = width + 2
        if label:
            layout_width += len(label) + 1
        if show_value:
            if float_mode:
                layout_width += 1 + len(f"{max_val:.1f}")
            else:
                layout_width += 1 + len(str(int(max_val)))

        vnode = VNodeBuilder("Slider", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("min_val", min_val)
        vnode.set_prop("max_val", max_val)
        vnode.set_prop("value", value)
        vnode.set_prop("step", step_val)
        vnode.set_prop("width", width)
        vnode.set_prop("float_mode", bool(float_mode))
        vnode.set_prop("label", label)
        vnode.set_prop("show_value", bool(show_value))
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)
        vnode.set_layout(width=layout_width, height=1)
        context.add_vnode(vnode)

        return get_element_marker(context)


class ToggleExtension(Extension):
    """Jinja2 extension for {% toggle %} tag.

    Syntax:
        {% toggle id="dark_mode" label="Dark Mode" %}{% endtoggle %}
        {% toggle id="notifications" checked=True %}{% endtoggle %}
        {% toggle id="sound" label_mode="dual" on_label="ON" off_label="OFF" %}{% endtoggle %}
    """

    tags = {"toggle"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the toggle tag."""
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endtoggle", lineno)

        node = nodes.CallBlock(
            self.call_method("_render_toggle", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endtoggle",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_toggle(
        self,
        caller: Any,
        id: str | None = None,
        checked: bool = False,
        label: str | None = None,
        on_label: str = "ON",
        off_label: str = "OFF",
        label_mode: Literal["single", "dual"] = "single",
        action: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the toggle tag."""
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        if id is None:
            id = context.generate_id("toggle")

        if bind and id:
            try:
                if id in state:
                    checked = bool(state[id])
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for toggle '{id}': {e}")

        is_focused = focused_id and id and focused_id == id

        caller()

        if label_mode == "dual":
            layout_width = len(off_label) + 1 + 6 + 1 + len(on_label)
        else:
            layout_width = 5
            if label:
                layout_width += 1 + len(label)

        vnode = VNodeBuilder("Toggle", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("checked", bool(checked))
        vnode.set_prop("label", label)
        vnode.set_prop("on_label", on_label)
        vnode.set_prop("off_label", off_label)
        vnode.set_prop("label_mode", label_mode)
        vnode.set_prop("action", action)
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)
        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)
        vnode.set_layout(width=layout_width, height=1)
        context.add_vnode(vnode)

        return get_element_marker(context)


class DataGridExtension(Extension):
    """Jinja2 extension for {% datagrid %} tag.

    Syntax:
        {% datagrid id="my_grid" data=grid_data columns=["Name", "Age", "City"]
                    width=60 height=15 %}
        {% enddatagrid %}

        {% datagrid id="inventory" data=items
                    columns=[
                        {"key": "name", "label": "Product", "width": 20},
                        {"key": "qty", "label": "Qty", "width": 8},
                        {"key": "price", "label": "Price", "width": 10}
                    ]
                    show_row_numbers=True %}
        {% enddatagrid %}
    """

    tags = {"datagrid"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the datagrid tag.

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
        kwargs = parse_tag_attributes(parser, "enddatagrid", lineno)

        node = nodes.CallBlock(
            self.call_method("_render_datagrid", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:enddatagrid",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_datagrid(
        self,
        caller: Any,
        id: str | None = None,
        data: list[list[str]] | None = None,
        columns: list[str] | list[dict[str, Any]] | None = None,
        width: int = 60,
        height: int = 15,
        show_row_numbers: bool = True,
        editable: bool = True,
        border_style: str = "single",
        show_scrollbar: bool = True,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the datagrid tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        data : list of list of str, optional
            2D grid data (rows x columns)
        columns : list of str or list of dict, optional
            Column definitions. Can be simple strings (headers) or dicts with
            "key", "label", and "width" keys.
        width : int
            Total display width (default: 60)
        height : int
            Total display height (default: 15)
        show_row_numbers : bool
            Show row numbers on left side (default: True)
        editable : bool
            Whether cells can be edited (default: True)
        border_style : str
            Border style: "single", "double", "rounded", etc. (default: "single")
        show_scrollbar : bool
            Whether to show scrollbars when content overflows (default: True)
        bind : bool
            Whether to auto-bind data to state[id] (default: True)
        classes : str, optional
            CSS-like class names for styling
        tab_index : int, optional
            Tab order for focus navigation

        Returns
        -------
        str
            Rendered output
        """
        # Normalize kwargs (handles class->classes, tabindex->tab_index)
        kwargs = normalize_element_kwargs(kwargs)
        classes = kwargs.pop("classes", None)
        tab_index = kwargs.pop("tab_index", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Convert numeric parameters
        width = safe_int(width, default=60, name="width")
        height = safe_int(height, default=15, name="height")

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("datagrid")

        # Consume body (typically empty for datagrid)
        caller()

        # If binding is enabled and id is provided, try to get data from state
        if bind and id:
            try:
                if id in state:
                    state_data = state[id]
                    if isinstance(state_data, list):
                        data = state_data
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to restore state for datagrid '{id}': {e}")

        # Ensure data is a list
        if data is None:
            data = []

        # Ensure columns is a list
        if columns is None:
            columns = []

        # Check if this element should be focused
        is_focused = focused_id and id and focused_id == id

        # Create VNode for reconciliation
        vnode = VNodeBuilder("DataGrid", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("data", data)
        vnode.set_prop("columns", columns)
        vnode.set_prop("width_spec", width)
        vnode.set_prop("height_spec", height)
        vnode.set_prop("show_row_numbers", bool(show_row_numbers))
        vnode.set_prop("editable", bool(editable))
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("show_scrollbar", bool(show_scrollbar))
        vnode.set_prop("bind", bind)
        vnode.set_prop("focused", is_focused)

        if classes is not None:
            vnode.set_prop("classes", classes)
        if tab_index is not None:
            vnode.set_prop("tab_index", tab_index)

        # Set layout dimensions
        vnode.set_layout(width=width, height=height)
        context.add_vnode(vnode)

        return get_element_marker(context)
