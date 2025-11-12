# ${DIR_PATH}/${FILE_NAME}
from jinja2 import nodes
from jinja2.ext import Extension

from wijjit.core.overlay import LayerType
from wijjit.elements.display.modal import ModalElement
from wijjit.elements.display.table import Table
from wijjit.elements.display.tree import Tree
from wijjit.layout.engine import ElementNode
from wijjit.logging_config import get_logger
from wijjit.tags.layout import process_body_content

# Get logger for this module
logger = get_logger(__name__)


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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

            # Restore highlighted index
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if highlight_key in state:
                        tree.highlighted_index = state[highlight_key]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create ElementNode
        # Tree has fixed dimensions, so use exact width and height
        node = ElementNode(tree, width=width, height=height)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        # Return empty string (layout will be processed later)
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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Convert show_percentage to bool if provided
        if show_percentage is not None:
            show_percentage = bool(show_percentage)

        # Create ProgressBar element
        from wijjit.elements.display.progress import ProgressBar

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

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
        from wijjit.elements.display.spinner import Spinner

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create MarkdownView element
        from wijjit.elements.display.markdown import MarkdownView

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
        markdown._dynamic_sizing = width_spec == "fill" or height_spec == "fill"

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create CodeBlock element
        from wijjit.elements.display.code import CodeBlock

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
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create ElementNode
        # Calculate total height accounting for borders
        total_height = height + (2 if border_style != "none" else 0)
        total_width = width + (2 if border_style != "none" else 0)

        node = ElementNode(codeblock, width=total_width, height=total_height)

        # Add to layout context
        context.add_element(node)

        return ""


class LogViewExtension(Extension):
    """Jinja2 extension for logview tag.

    Syntax:
        {% logview id="app_logs"
                   lines=state.logs
                   auto_scroll=true
                   soft_wrap=false
                   width=80
                   height=20
                   show_line_numbers=false
                   detect_log_levels=true
                   border_style="single"
                   title="Application Logs"
                   show_scrollbar=true %}
        {% endlogview %}
    """

    tags = {"logview"}

    def parse(self, parser):
        """Parse the logview tag.

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
            "name:endlogview"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endlogview)
        node = nodes.CallBlock(
            self.call_method("_render_logview", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endlogview"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_logview(
        self,
        caller,
        id=None,
        lines=None,
        width=80,
        height=20,
        auto_scroll=True,
        soft_wrap=False,
        show_line_numbers=False,
        line_number_start=1,
        detect_log_levels=True,
        show_scrollbar=True,
        border_style="single",
        title=None,
        bind=True,
    ) -> str:
        """Render the logview tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        lines : list of str, optional
            Log lines
        width : int
            LogView width (default: 80)
        height : int
            LogView height (default: 20)
        auto_scroll : bool
            Automatically scroll to bottom (default: True)
        soft_wrap : bool
            Wrap long lines (default: False)
        show_line_numbers : bool
            Display line numbers (default: False)
        line_number_start : int
            Starting line number (default: 1)
        detect_log_levels : bool
            Auto-detect and color log levels (default: True)
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        border_style : str
            Border style (default: "single")
        title : str, optional
            Border title
        bind : bool
            Whether to auto-bind lines to state[id] (default: True)

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
        auto_scroll = bool(auto_scroll)
        soft_wrap = bool(soft_wrap)
        show_line_numbers = bool(show_line_numbers)
        line_number_start = int(line_number_start)
        detect_log_levels = bool(detect_log_levels)
        show_scrollbar = bool(show_scrollbar)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("logview")

        # If binding is enabled and id is provided, try to get lines from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        state_lines = state[id]
                        # Ensure it's a list
                        if isinstance(state_lines, list):
                            lines = state_lines
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Ensure lines is a list of strings
        if lines is None:
            lines = []
        elif not isinstance(lines, list):
            lines = []
        else:
            # Convert all items to strings
            lines = [str(line) for line in lines]

        # Create LogView element
        from wijjit.elements.display.logview import LogView

        logview = LogView(
            id=id,
            lines=lines,
            width=width,
            height=height,
            auto_scroll=auto_scroll,
            soft_wrap=soft_wrap,
            show_line_numbers=show_line_numbers,
            line_number_start=line_number_start,
            detect_log_levels=detect_log_levels,
            show_scrollbar=show_scrollbar,
            border_style=border_style,
            title=title,
        )

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            logview.focused = True

        # Store bind setting
        logview.bind = bind

        # Restore scroll position and auto-scroll state from state if available
        if id:
            scroll_key = f"_scroll_{id}"
            autoscroll_key = f"_autoscroll_{id}"
            logview.scroll_state_key = scroll_key
            logview.autoscroll_state_key = autoscroll_key

            # Give logview access to state dict for saving
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    logview._state_dict = ctx["state"]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]

                    # Restore scroll position
                    if scroll_key in state:
                        logview.restore_scroll_position(state[scroll_key])

                    # Restore auto-scroll state
                    if autoscroll_key in state:
                        logview.auto_scroll = bool(state[autoscroll_key])
                        if logview.auto_scroll:
                            logview._user_scrolled_up = False
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create ElementNode
        # Calculate total height accounting for borders
        total_height = height + (2 if border_style != "none" else 0)
        total_width = width + (2 if border_style != "none" else 0)

        node = ElementNode(logview, width=total_width, height=total_height)

        # Add to layout context
        context.add_element(node)

        # Consume body (should be empty)
        caller()

        return ""


class ListViewExtension(Extension):
    """Jinja2 extension for listview tag.

    Syntax:
        {% listview id="tasks" items=state.tasks
                    bullet="bullet" show_dividers=true
                    width=60 height=20 border="single" title="Tasks" %}
        {% endlistview %}

        Or with static items:
        {% listview bullet="dash" %}
    Task 1
    Task 2
    Task 3
        {% endlistview %}

        Or with details (2-tuples or dicts):
        {% listview bullet="number" items=items %}
        {% endlistview %}
    """

    tags = {"listview"}

    def parse(self, parser):
        """Parse the listview tag.

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
            "name:endlistview"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (list items if not provided as attribute)
        node = nodes.CallBlock(
            self.call_method("_render_listview", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endlistview"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_listview(
        self,
        caller,
        id=None,
        items=None,
        width=40,
        height=10,
        bullet="bullet",
        show_dividers=False,
        show_scrollbar=True,
        border_style="single",
        title=None,
        indent_details=2,
        dim_details=True,
        bind=True,
        raw=False,
    ) -> str:
        """Render the listview tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        items : list, optional
            List items (if not provided in body)
        width : int
            ListView width (default: 40)
        height : int
            ListView height (default: 10)
        bullet : str
            Bullet style: "bullet", "dash", "number", or custom character
            (default: "bullet")
        show_dividers : bool
            Whether to show horizontal dividers (default: False)
        show_scrollbar : bool
            Whether to show scrollbar (default: True)
        border_style : str
            Border style (default: "single")
        title : str, optional
            Border title
        indent_details : int
            Details indentation (default: 2)
        dim_details : bool
            Whether to dim details text (default: True)
        bind : bool
            Whether to auto-bind items to state[id] (default: True)
        raw : bool
            Preserve whitespace in body content (default: False)

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
        show_dividers = bool(show_dividers)
        show_scrollbar = bool(show_scrollbar)
        indent_details = int(indent_details)
        dim_details = bool(dim_details)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("listview")

        # Get items from body if not provided as attribute
        if items is None:
            body_output = caller()
            body_text = process_body_content(body_output, raw=raw)

            # Split body into lines and filter empty lines
            if body_text.strip():
                items = [line.strip() for line in body_text.split("\n") if line.strip()]
            else:
                items = []
        else:
            # Items provided as attribute, consume body anyway
            caller()

            # Ensure items is a list
            if not isinstance(items, list):
                items = []

        # If binding is enabled and id is provided, try to get items from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        state_items = state[id]
                        # Ensure it's a list
                        if isinstance(state_items, list):
                            items = state_items
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create ListView element
        from wijjit.elements.display.list import ListView

        listview = ListView(
            id=id,
            items=items,
            width=width,
            height=height,
            bullet=bullet,
            show_dividers=show_dividers,
            show_scrollbar=show_scrollbar,
            border_style=border_style,
            title=title,
            indent_details=indent_details,
            dim_details=dim_details,
        )

        # Check if this element should be focused
        focused_id = self.environment.globals.get("_wijjit_focused_id")
        if focused_id and id and focused_id == id:
            listview.focused = True

        # Store bind setting
        listview.bind = bind

        # Restore scroll position from state if available
        if id:
            scroll_key = f"_scroll_{id}"
            listview.scroll_state_key = scroll_key
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if scroll_key in state:
                        listview.restore_scroll_position(state[scroll_key])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create ElementNode
        # Calculate total height accounting for borders
        total_height = height + (2 if border_style != "none" else 0)
        total_width = width + (2 if border_style != "none" else 0)

        node = ElementNode(listview, width=total_width, height=total_height)

        # Add to layout context
        context.add_element(node)

        return ""


class OverlayExtension(Extension):
    """Jinja2 extension for {% overlay %} tag.

    Creates a generic overlay that can be shown/hidden based on state.

    Syntax:
        {% overlay visible="show_popup"
                   layer="modal"
                   width=50
                   height=10
                   close_on_escape=true
                   close_on_click_outside=false
                   trap_focus=true
                   dim_background=false %}
          Overlay content here
        {% endoverlay %}
    """

    tags = {"overlay"}

    def parse(self, parser):
        """Parse the overlay tag.

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
            "name:endoverlay"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (overlay content)
        node = nodes.CallBlock(
            self.call_method("_render_overlay", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endoverlay"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_overlay(
        self,
        caller,
        id=None,
        visible=None,
        layer="modal",
        width=50,
        height=10,
        close_on_escape=True,
        close_on_click_outside=False,
        trap_focus=True,
        dim_background=False,
    ) -> str:
        """Render the overlay tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        visible : str, optional
            State key name for visibility control (e.g., "show_popup")
        layer : str
            Overlay layer: "base", "modal", "dropdown", "tooltip" (default: "modal")
        width : int
            Overlay width (default: 50)
        height : int
            Overlay height (default: 10)
        close_on_escape : bool
            Close on ESC key (default: True)
        close_on_click_outside : bool
            Close on click outside (default: False)
        trap_focus : bool
            Trap keyboard focus (default: True)
        dim_background : bool
            Dim background (default: False)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Check visibility state
        is_visible = False
        if visible:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    # Check if state variable is truthy
                    is_visible = bool(state.get(visible, False))
            except Exception as e:
                logger.warning(f"Failed to check visibility state: {e}")

        # If not visible, don't create the overlay
        if not is_visible:
            # Still consume body
            caller()
            return ""

        # Convert numeric parameters
        width = int(width)
        height = int(height)
        close_on_escape = bool(close_on_escape)
        close_on_click_outside = bool(close_on_click_outside)
        trap_focus = bool(trap_focus)
        dim_background = bool(dim_background)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("overlay")

        # Map layer string to LayerType
        layer_map = {
            "base": LayerType.BASE,
            "modal": LayerType.MODAL,
            "dropdown": LayerType.DROPDOWN,
            "tooltip": LayerType.TOOLTIP,
        }
        layer_type = layer_map.get(layer.lower(), LayerType.MODAL)

        # Get body content
        body_content = caller().strip()

        # Create overlay element (using base OverlayElement)
        from wijjit.elements.base import OverlayElement, TextElement

        overlay_element = OverlayElement(
            id=id,
            width=width,
            height=height,
            centered=True,
        )

        # Add text content if provided
        if body_content:
            text_elem = TextElement(text=body_content)
            overlay_element.add_child(text_elem)

        # Store overlay info for app to register
        # We'll add this to a special list in the context
        overlay_info = {
            "element": overlay_element,
            "layer_type": layer_type,
            "close_on_escape": close_on_escape,
            "close_on_click_outside": close_on_click_outside,
            "trap_focus": trap_focus,
            "dim_background": dim_background,
            "visible_state_key": visible,
        }

        # Add to context's overlay list (app will process these)
        if not hasattr(context, "_overlays"):
            context._overlays = []
        context._overlays.append(overlay_info)

        return ""


class ModalExtension(Extension):
    """Jinja2 extension for {% modal %} tag.

    Creates a modal dialog with frame and content.

    Syntax:
        {% modal visible="show_confirm"
                 title="Confirm"
                 width=50
                 height=12
                 border="single" %}
          Modal content here
        {% endmodal %}
    """

    tags = {"modal"}

    def parse(self, parser):
        """Parse the modal tag.

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
            "name:endmodal"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (modal content)
        node = nodes.CallBlock(
            self.call_method("_render_modal", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endmodal"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_modal(
        self,
        caller,
        id=None,
        visible=None,
        title=None,
        width=50,
        height=12,
        border="single",
    ) -> str:
        """Render the modal tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        visible : str, optional
            State key name for visibility control
        title : str, optional
            Modal title
        width : int
            Modal width (default: 50)
        height : int
            Modal height (default: 12)
        border : str
            Border style: "single", "double", "rounded" (default: "single")

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Check visibility state
        is_visible = False
        if visible:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    is_visible = bool(state.get(visible, False))
            except Exception as e:
                logger.warning(f"Failed to check visibility state: {e}")

        # If not visible, don't create the modal
        if not is_visible:
            # Still consume body
            caller()
            return ""

        # Convert numeric parameters
        width = int(width)
        height = int(height)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("modal")

        # Get body content
        body_content = caller().strip()

        # Create modal element
        modal_element = ModalElement(
            id=id,
            title=title,
            width=width,
            height=height,
            border=border,
            centered=True,
        )

        # Set content
        if body_content:
            modal_element.set_content(body_content)

        # Store overlay info for app to register
        overlay_info = {
            "element": modal_element,
            "layer_type": LayerType.MODAL,
            "close_on_escape": True,
            "close_on_click_outside": False,
            "trap_focus": True,
            "dim_background": True,
            "visible_state_key": visible,
        }

        # Add to context's overlay list
        if not hasattr(context, "_overlays"):
            context._overlays = []
        context._overlays.append(overlay_info)

        return ""


class StatusBarExtension(Extension):
    """Jinja2 extension for {% statusbar %} tag.

    Creates a status bar that displays at the bottom of the screen with
    left, center, and right-aligned sections.

    Syntax:
        {% statusbar left="File: app.py"
                     center="Ready"
                     right="Line 42"
                     bg_color="blue"
                     text_color="white" %}
        {% endstatusbar %}
    """

    tags = {"statusbar"}

    def parse(self, parser):
        """Parse the statusbar tag.

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
            "name:endstatusbar"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty, but consume until endstatusbar)
        node = nodes.CallBlock(
            self.call_method("_render_statusbar", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endstatusbar"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_statusbar(
        self,
        caller,
        id=None,
        left="",
        center="",
        right="",
        bg_color=None,
        text_color=None,
        bind=True,
    ) -> str:
        """Render the statusbar tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        left : str
            Left-aligned content (default: "")
        center : str
            Center-aligned content (default: "")
        right : str
            Right-aligned content (default: "")
        bg_color : str, optional
            Background color name (default: None)
        text_color : str, optional
            Text color name (default: None)
        bind : bool
            Whether to auto-bind sections to state (default: True)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            # Still consume body
            caller()
            return ""

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("statusbar")

        # Convert to strings
        left = str(left) if left else ""
        center = str(center) if center else ""
        right = str(right) if right else ""

        # If binding is enabled and id is provided, try to get content from state
        if bind and id:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    # Check for individual section keys
                    left_key = f"{id}_left"
                    center_key = f"{id}_center"
                    right_key = f"{id}_right"

                    if left_key in state:
                        left = str(state[left_key])
                    if center_key in state:
                        center = str(state[center_key])
                    if right_key in state:
                        right = str(state[right_key])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create StatusBar element
        from wijjit.elements.display.statusbar import StatusBar

        statusbar = StatusBar(
            id=id,
            left=left,
            center=center,
            right=right,
            bg_color=bg_color,
            text_color=text_color,
        )

        # Store bind setting
        statusbar.bind = bind

        # Store statusbar in context for app to extract
        # Similar to how overlays are stored
        context._statusbar = statusbar

        # Consume body (should be empty)
        caller()

        return ""
