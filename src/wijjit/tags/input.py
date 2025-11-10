# ${DIR_PATH}/${FILE_NAME}
from jinja2 import nodes
from jinja2.ext import Extension

from wijjit.elements.input.button import Button
from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup
from wijjit.elements.input.radio import Radio, RadioGroup
from wijjit.elements.input.select import Select
from wijjit.elements.input.text import TextArea, TextInput
from wijjit.layout.engine import ElementNode
from wijjit.tags.layout import LayoutContext


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
        from wijjit.terminal.ansi import visible_length

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
        from wijjit.terminal.ansi import visible_length

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
        textarea._dynamic_sizing = width_spec == "fill" or height_spec == "fill"

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
