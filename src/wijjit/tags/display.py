# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, cast

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.core.overlay import LayerType
from wijjit.core.render_context import get_render_context
from wijjit.core.vdom import VNodeBuilder
from wijjit.elements.display.modal import ModalElement
from wijjit.logging_config import get_logger
from wijjit.tags.layout import get_element_marker, process_body_content

if TYPE_CHECKING:
    pass

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

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endtable",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_table(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        data: list[dict[str, Any]] | None = None,
        columns: list[Any] | None = None,
        width: int | str = 60,
        height: int | str = 10,
        sortable: bool = False,
        show_header: bool = True,
        show_scrollbar: bool = True,
        border_style: str = "single",
        bind: bool = True,
        **kwargs: Any,
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
        width : int or str
            Table width (default: 60). Can be int, "fill", "auto", or percentage
        height : int or str
            Table height (default: 10). Can be int, "fill", "auto", or percentage
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
        classes : str, optional
            CSS-like class names for styling

        Returns
        -------
        str
            Rendered output
        """
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        # Store original width/height specs for layout
        width_spec = width
        height_spec = height

        sortable = bool(sortable)
        show_header = bool(show_header)
        show_scrollbar = bool(show_scrollbar)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("table")

        # If binding is enabled and id is provided, try to get data from state
        if bind and id:
            try:
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

        # Build VNode
        vnode = VNodeBuilder("Table", key=id)
        vnode.set_prop("data", data)
        vnode.set_prop("columns", columns)
        vnode.set_prop("sortable", sortable)
        vnode.set_prop("show_header", show_header)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("bind", bind)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width=width_spec, height=height_spec)

        context.add_vnode(vnode)

        # Consume body (should be empty)
        caller()

        # Return marker for text interleaving
        return get_element_marker(context)


class TreeExtension(Extension):
    """Jinja2 extension for {% tree %} tag.

    Syntax:
        {% tree id="filetree"
                data=state.file_tree
                width=40
                height=20
                on_select="file_selected"
                show_scrollbar=true
                show_root=true
                border="rounded"
                title="File Tree"
                indicator_style="triangles_large" %}
        {% endtree %}
    """

    tags = {"tree"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endtree",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_tree(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        data: dict[str, Any] | list[Any] | None = None,
        width: int | str = 40,
        height: int | str = 15,
        show_scrollbar: bool = True,
        show_root: bool = True,
        indent_size: int = 2,
        on_select: str | None = None,
        expanded: str | list[Any] | None = None,
        bind: bool = True,
        border: str = "none",
        title: str | None = None,
        indicator_style: str = "triangles_large",
        **kwargs: Any,
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
        width : int or str
            Tree width (default: 40). Can be int, "fill", "auto", or percentage
        height : int or str
            Tree height (default: 15). Can be int, "fill", "auto", or percentage
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
        border : str
            Border style: "single", "double", "rounded", or "none" (default: "none")
        title : str, optional
            Title to display in top border
        indicator_style : str
            Indicator style: "triangles_large", "triangles", "circles", "squares",
            "brackets", or "minimal" (default: "triangles_large")
        classes : str, optional
            CSS-like class names for styling

        Returns
        -------
        str
            Rendered output
        """
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        # Store original width/height specs for layout
        width_spec = width
        height_spec = height

        indent_size = int(indent_size)
        show_scrollbar = bool(show_scrollbar)
        show_root = bool(show_root)

        # Convert indicator_style string to enum
        from wijjit.elements.display.tree import TreeIndicatorStyle

        indicator_style_map = {
            "triangles_large": TreeIndicatorStyle.TRIANGLES_LARGE,
            "triangles": TreeIndicatorStyle.TRIANGLES,
            "circles": TreeIndicatorStyle.CIRCLES,
            "squares": TreeIndicatorStyle.SQUARES,
            "brackets": TreeIndicatorStyle.BRACKETS,
            "minimal": TreeIndicatorStyle.MINIMAL,
        }
        indicator_style_enum = indicator_style_map.get(
            str(indicator_style).lower(), TreeIndicatorStyle.TRIANGLES_LARGE
        )

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("tree")

        # If binding is enabled and id is provided, try to get data from state
        if bind and id:
            try:
                if id in state:
                    data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Build VNode
        vnode = VNodeBuilder("TreeView", key=id)
        vnode.set_prop("data", data)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("show_root", show_root)
        vnode.set_prop("indent_size", indent_size)
        vnode.set_prop("indicator_style", indicator_style_enum)
        vnode.set_prop("border_style", border)
        if title:
            vnode.set_prop("title", title)
        if on_select:
            # Store action name as "action" so wiring manager can find it
            vnode.set_prop("action", on_select)
        if expanded is not None:
            vnode.set_prop("expanded", expanded)
        vnode.set_prop("bind", bind)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width=width_spec, height=height_spec)

        context.add_vnode(vnode)

        # Consume body (should be empty)
        caller()

        # Return marker for text interleaving
        return get_element_marker(context)


class ProgressBarExtension(Extension):
    """Jinja2 extension for progressbar tag.

    Syntax:
        {% progressbar id="download" value=state.progress max=100
                       width=40 style="filled" color="green"
                       show_percentage=True %}
        {% endprogressbar %}
    """

    tags = {"progressbar"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endprogressbar",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_progressbar(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        value: float | int = 0,
        max: float | int = 100,
        width: int = 40,
        style: Literal["filled", "percentage", "gradient", "custom"] | str = "filled",
        color: str | None = None,
        show_percentage: bool | None = None,
        fill_char: str | None = None,
        empty_char: str | None = None,
        bind: bool = True,
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

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
                if id in state:
                    value = float(state[id])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Convert show_percentage to bool if provided
        if show_percentage is not None:
            show_percentage = bool(show_percentage)

        # Build VNode
        vnode = VNodeBuilder("ProgressBar", key=id)
        vnode.set_prop("value", value)
        vnode.set_prop("max", max_val)
        vnode.set_prop("style", style)
        if color:
            vnode.set_prop("color", color)
        if show_percentage is not None:
            vnode.set_prop("show_percentage", show_percentage)
        if fill_char:
            vnode.set_prop("fill_char", fill_char)
        if empty_char:
            vnode.set_prop("empty_char", empty_char)
        vnode.set_prop("bind", bind)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width=width, height=1)

        context.add_vnode(vnode)

        # Consume body (should be empty)
        caller()

        # Return marker for text interleaving
        return get_element_marker(context)


class SpinnerExtension(Extension):
    """Jinja2 extension for spinner tag.

    Syntax:
        {% spinner id="loading" active=state.loading
                   style="dots" label="Loading..." color="cyan" %}
        {% endspinner %}
    """

    tags = {"spinner"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endspinner",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_spinner(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        active: bool = True,
        style: Literal["dots", "line", "bouncing", "clock"] | str = "dots",
        label: str = "",
        color: str | None = None,
        bind: bool = True,
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        # Convert active to bool
        active = bool(active)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("spinner")

        # If binding is enabled and id is provided, try to get active state from state
        if bind and id:
            try:
                if id in state:
                    active = bool(state[id])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Calculate width based on label and spinner character
        # Spinner is typically 1-2 chars wide, plus space, plus label length
        spinner_width = 3 + len(label) if label else 2

        # Build VNode
        vnode = VNodeBuilder("Spinner", key=id)
        vnode.set_prop("active", active)
        vnode.set_prop("style", style)
        vnode.set_prop("label", label)
        if color:
            vnode.set_prop("color", color)
        vnode.set_prop("bind", bind)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width=spinner_width, height=1)

        context.add_vnode(vnode)

        # Consume body (should be empty)
        caller()

        # Return marker for text interleaving
        return get_element_marker(context)


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

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endmarkdown",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_markdown(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        content: str | None = None,
        width: int | str = "fill",
        height: int | str = "fill",
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        bind: bool = True,
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        # Store original width/height specs for layout
        width_spec = width
        height_spec = height

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
                if id in state:
                    content = str(state[id])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Build VNode
        vnode = VNodeBuilder("MarkdownView", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop("content", content)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("border_style", border_style)
        if title:
            vnode.set_prop("title", title)
        vnode.set_prop("bind", bind)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width=width_spec, height=height_spec)

        context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(context)


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

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endcode",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_code(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        code: str | None = None,
        language: str = "python",
        width: int = 60,
        height: int = 20,
        show_line_numbers: bool = True,
        line_number_start: int = 1,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        theme: str = "monokai",
        bind: bool = True,
        raw: bool = True,
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Store original width/height specs for layout
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

        show_line_numbers = bool(show_line_numbers)
        line_number_start = int(line_number_start)
        show_scrollbar = bool(show_scrollbar)

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("code")

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
                if id in state:
                    code = str(state[id])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create VNode for reconciliation - NO direct Element instantiation
        # The reconciler will create the Element from this VNode
        vnode = VNodeBuilder("CodeBlock", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("code", code)
        vnode.set_prop("language", language)
        vnode.set_prop("width", element_width)
        vnode.set_prop("height", element_height)
        vnode.set_prop("show_line_numbers", show_line_numbers)
        vnode.set_prop("line_number_start", line_number_start)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("theme", theme)
        vnode.set_prop("bind", bind)
        if title:
            vnode.set_prop("title", title)
        if classes:
            vnode.set_prop("classes", classes)

        # Check if this element should be focused
        if focused_id and id and focused_id == id:
            vnode.set_prop("focused", True)

        # Account for borders in layout size if present
        layout_width = width_spec
        layout_height = height_spec
        if border_style != "none":
            # Add 2 for borders (top+bottom, left+right) if width/height are numeric
            if isinstance(width_spec, int):
                layout_width = width_spec + 2
            if isinstance(height_spec, int):
                layout_height = height_spec + 2

        vnode.set_layout(width=layout_width, height=layout_height)
        layout_context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(layout_context)


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

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endlogview",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_logview(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        lines: list[str] | None = None,
        width: int = 80,
        height: int = 20,
        auto_scroll: bool = True,
        soft_wrap: bool = False,
        show_line_numbers: bool = False,
        line_number_start: int = 1,
        detect_log_levels: bool = True,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        bind: bool = True,
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Store original width/height specs for layout
        width_spec = width
        height_spec = height

        # Convert numeric parameters for element creation
        # If width/height are "fill" or other string specs, use default numeric values
        if isinstance(width, str) and not width.isdigit():
            element_width = 60  # Default for initial render
        else:
            element_width = int(width)

        if isinstance(height, str) and not height.isdigit():
            element_height = 20  # Default for initial render
        else:
            element_height = int(height)

        auto_scroll = bool(auto_scroll)
        soft_wrap = bool(soft_wrap)
        show_line_numbers = bool(show_line_numbers)
        line_number_start = int(line_number_start)
        detect_log_levels = bool(detect_log_levels)
        show_scrollbar = bool(show_scrollbar)

        # LogView expects TOTAL dimensions (including borders), so add border space
        if border_style != "none":
            element_width += 2
            element_height += 2

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("logview")

        # If binding is enabled and id is provided, try to get lines from state
        if bind and id:
            try:
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

        # Create VNode for reconciliation - NO direct Element instantiation
        # The reconciler will create the Element from this VNode
        vnode = VNodeBuilder("LogView", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("lines", lines)
        vnode.set_prop("width", element_width)
        vnode.set_prop("height", element_height)
        vnode.set_prop("auto_scroll", auto_scroll)
        vnode.set_prop("soft_wrap", soft_wrap)
        vnode.set_prop("show_line_numbers", show_line_numbers)
        vnode.set_prop("line_number_start", line_number_start)
        vnode.set_prop("detect_log_levels", detect_log_levels)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("bind", bind)
        if title:
            vnode.set_prop("title", title)
        if classes:
            vnode.set_prop("classes", classes)

        # Check if this element should be focused
        if focused_id and id and focused_id == id:
            vnode.set_prop("focused", True)

        # Account for borders in layout size if present
        layout_width = width_spec
        layout_height = height_spec
        if border_style != "none":
            # Add 2 for borders (top+bottom, left+right) if width/height are numeric
            if isinstance(width_spec, int):
                layout_width = width_spec + 2
            if isinstance(height_spec, int):
                layout_height = height_spec + 2

        vnode.set_layout(width=layout_width, height=layout_height)
        layout_context.add_vnode(vnode)

        # Consume body (should be empty)
        caller()

        # Return marker for text interleaving
        return get_element_marker(layout_context)


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

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endlistview",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_listview(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        items: list[Any] | None = None,
        width: int = 40,
        height: int = 10,
        bullet: str = "bullet",
        show_dividers: bool = False,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        indent_details: int = 2,
        dim_details: bool = True,
        bind: bool = True,
        raw: bool = False,
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Store original width/height specs for layout
        width_spec = width
        height_spec = height

        # Convert numeric parameters for element creation
        # If width/height are "fill" or other string specs, use default numeric values
        if isinstance(width, str) and not width.isdigit():
            element_width = 60  # Default for initial render
        else:
            element_width = int(width)

        if isinstance(height, str) and not height.isdigit():
            element_height = 20  # Default for initial render
        else:
            element_height = int(height)

        show_dividers = bool(show_dividers)
        show_scrollbar = bool(show_scrollbar)
        indent_details = int(indent_details)
        dim_details = bool(dim_details)

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("listview")

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
                if id in state:
                    state_items = state[id]
                    # Ensure it's a list
                    if isinstance(state_items, list):
                        items = state_items
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create VNode for reconciliation - NO direct Element instantiation
        # The reconciler will create the Element from this VNode
        vnode = VNodeBuilder("ListView", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("items", items)
        vnode.set_prop("width", element_width)
        vnode.set_prop("height", element_height)
        vnode.set_prop("bullet", bullet)
        vnode.set_prop("show_dividers", show_dividers)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("indent_details", indent_details)
        vnode.set_prop("dim_details", dim_details)
        vnode.set_prop("bind", bind)
        if title:
            vnode.set_prop("title", title)
        if classes:
            vnode.set_prop("classes", classes)

        # Check if this element should be focused
        if focused_id and id and focused_id == id:
            vnode.set_prop("focused", True)

        # Account for borders in layout size if present
        layout_width = width_spec
        layout_height = height_spec
        if border_style != "none":
            # Add 2 for borders (top+bottom, left+right) if width/height are numeric
            if isinstance(width_spec, int):
                layout_width = width_spec + 2
            if isinstance(height_spec, int):
                layout_height = height_spec + 2

        vnode.set_layout(width=layout_width, height=layout_height)
        layout_context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(layout_context)


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

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endmodal",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_modal(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        visible: str | None = None,
        title: str | None = None,
        width: int = 50,
        height: int = 12,
        border: str = "single",
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context

        # Note: Visibility is checked in _sync_template_overlays based on visible_state_key
        # We always create the element here to enable pre-registration of shortcuts/metadata

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
            classes=classes,
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
        overlay_info: dict[str, Any] = {
            "element": modal_element,
            "layer_type": LayerType.MODAL,
            "close_on_escape": True,
            "close_on_click_outside": False,
            "trap_focus": True,
            "dim_background": True,
            "visible_state_key": visible,
        }

        # Add overlay via RenderContext
        render_ctx.add_overlay(overlay_info)

        # Create VNode for reconciliation
        vnode = VNodeBuilder("Modal", key=id)
        if title:
            vnode.set_prop("title", title)
        vnode.set_prop("border", border)
        vnode.set_prop("centered", True)
        if visible:
            vnode.set_prop("visible_state_key", visible)
        if classes:
            vnode.set_prop("classes", classes)
        # Store body content in VNode for comparison
        vnode.set_prop("content", body_content)
        vnode.set_layout(width=width, height=height)
        context.add_vnode(vnode)

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

    def parse(self, parser: Parser) -> nodes.CallBlock:
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
        kwargs: list[nodes.Keyword] = []
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
            parser.parse_statements(("name:endstatusbar",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_statusbar(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        left: str = "",
        center: str = "",
        right: str = "",
        bg_color: str | None = None,
        text_color: str | None = None,
        bind: bool = True,
        **kwargs: Any,
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
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        state = render_ctx.state

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("statusbar")

        # Convert to strings
        left = str(left) if left else ""
        center = str(center) if center else ""
        right = str(right) if right else ""

        # If binding is enabled and id is provided, try to get content from state
        if bind and id:
            try:
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

        # Create StatusBar element - StatusBar is special because it's positioned
        # outside the normal layout flow at the bottom of the screen
        from wijjit.elements.display.statusbar import StatusBar

        statusbar = StatusBar(
            id=id,
            classes=classes,
            left=left,
            center=center,
            right=right,
            bg_color=bg_color,
            text_color=text_color,
        )

        # Store bind setting
        statusbar.bind = bind

        # Store statusbar in RenderContext for app to extract
        render_ctx.statusbar = statusbar

        # Create VNode for reconciliation
        vnode = VNodeBuilder("StatusBar", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("left", left)
        vnode.set_prop("center", center)
        vnode.set_prop("right", right)
        vnode.set_prop("bind", bind)
        if bg_color:
            vnode.set_prop("bg_color", bg_color)
        if text_color:
            vnode.set_prop("text_color", text_color)
        if classes:
            vnode.set_prop("classes", classes)
        # StatusBar doesn't use layout dimensions (it's fixed to bottom)
        vnode.set_layout(width="fill", height=1)

        layout_context.add_vnode(vnode)

        # Consume body (should be empty)
        caller()

        return ""


class TextExtension(Extension):
    """Jinja2 extension for {% text %} tag.

    Syntax:
        {% text id="label" class="text-bold" %}Hello World{% endtext %}
        {% text html=true %}<b>Bold</b> text{% endtext %}
    """

    tags = {"text"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the text tag.

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
            "name:endtext"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (text content)
        node = nodes.CallBlock(
            self.call_method("_render_text", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endtext",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_text(
        self,
        caller: Callable,
        id: str | None = None,
        wrap: bool = True,
        html: bool | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the text tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        wrap : bool, optional
            Whether to wrap text (default: True)
        html : bool, optional
            Whether to parse HTML tags in content (default: None = use global config)
        **kwargs : dict
            Additional attributes (including 'class' which gets renamed to 'classes')

        Returns
        -------
        str
            Rendered output
        """
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context

        # Get body text content
        text_content = caller().strip()

        # Create VNode for reconciliation (removed duplicate old-style element creation)
        vnode = VNodeBuilder("Text", key=id)
        vnode.set_prop("id", id)  # Set id as prop so Element gets it
        vnode.set_prop(
            "text", text_content
        )  # Changed from 'content' to 'text' to match TextElement.__init__
        vnode.set_prop("wrap", wrap)
        if html is not None:
            vnode.set_prop("html", html)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width="auto", height="auto")

        context.add_vnode(vnode)

        # Return marker for text interleaving
        return get_element_marker(context)


class TabExtension(Extension):
    """Jinja2 extension for {% tab %} tag (used within {% tabbedpanel %}).

    Syntax:
        {% tab label="Tab Label" %}
            Content for this tab
        {% endtab %}

    Notes
    -----
    This tag must be used within a {% tabbedpanel %} tag.
    The content should typically be a single {% frame %} element.
    """

    tags = {"tab"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the tab tag.

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
        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endtab"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (tab content)
        node = nodes.CallBlock(
            self.call_method("_render_tab", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endtab",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_tab(
        self,
        caller: Callable[[], str],
        label: str = "Tab",
        **kwargs: Any,
    ) -> str:
        """Render the tab tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        label : str
            Tab label text (default: "Tab")

        Returns
        -------
        str
            Rendered output (empty string, tabs collected via VNode tree)

        Notes
        -----
        This method creates a TabContent VNode that becomes a child of the
        parent TabbedPanel VNode. The tab content elements are collected
        via the VNode stack and become children of the TabContent VNode.
        """
        from wijjit.core.vdom import VNodeBuilder
        from wijjit.tags.layout import (
            interleave_text_and_vnode_builders,
            process_body_content,
        )

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context

        # Create a TabContent VNode to hold this tab's content
        # Use a unique key based on the tab index
        tab_index = len(
            [
                c
                for c in (
                    context.vnode_stack[-1].children if context.vnode_stack else []
                )
                if getattr(c, "type", None) == "TabContent"
            ]
        )
        tab_key = f"_tab_{tab_index}"

        tab_vnode = VNodeBuilder("TabContent", key=tab_key)
        tab_vnode.set_prop("label", label)

        # Push the tab VNode onto the stack to collect children
        context.push_vnode(tab_vnode)

        # Render body - child elements will add themselves via add_vnode
        body_output = caller()

        # Pop the tab VNode from the stack
        context.pop_vnode()

        # Handle text interleaving for VNode children
        vnode_children = tab_vnode.children

        if not vnode_children and body_output.strip():
            # No VNode children but has text - create a single TextElement VNode
            processed_text = process_body_content(body_output, raw=False)
            if processed_text:
                text_key = context.generate_id("text")
                text_vnode = VNodeBuilder("TextElement", key=text_key)
                text_vnode.set_prop("id", text_key)
                text_vnode.set_prop("text", processed_text)
                text_vnode.set_prop("wrap", True)
                text_vnode.set_layout(width="auto", height="auto")
                tab_vnode.add_child(text_vnode)
        elif vnode_children:
            # Has VNode children - interleave text and VNodes in source order
            interleaved = interleave_text_and_vnode_builders(
                body_output, vnode_children, False, context
            )
            tab_vnode.children = interleaved

        # Return empty string (tab is added as child VNode, no marker needed)
        return ""


class TabbedPanelExtension(Extension):
    """Jinja2 extension for {% tabbedpanel %} tag.

    Syntax:
        {% tabbedpanel id="settings" tab_position="top" active_tab="active_tab"
                       width=80 height=25 border_style="single" %}
            {% tab label="General" %}
                {% frame %}General settings{% endframe %}
            {% endtab %}
            {% tab label="Advanced" %}
                {% frame %}Advanced settings{% endframe %}
            {% endtab %}
        {% endtabbedpanel %}
    """

    tags = {"tabbedpanel"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the tabbedpanel tag.

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
        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endtabbedpanel"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (tab elements)
        node = nodes.CallBlock(
            self.call_method("_render_tabbedpanel", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endtabbedpanel",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_tabbedpanel(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        tab_position: str = "top",
        active_tab: str | int | None = None,
        width: int | str = 60,
        height: int | str = 20,
        border_style: str = "single",
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the tabbedpanel tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        tab_position : str
            Position of tabs: "top", "bottom", "left", "right" (default: "top")
        active_tab : str or int, optional
            State key name for active tab binding, or initial tab index
        width : int or str
            Panel width (default: 60)
        height : int or str
            Panel height (default: 20)
        border_style : str
            Border style: "single", "double", "rounded" (default: "single")
        bind : bool
            Whether to auto-bind active tab to state (default: True)

        Returns
        -------
        str
            Rendered output

        Notes
        -----
        This method creates a TabbedPanel VNode and pushes it to the VNode stack.
        Child {% tab %} tags create TabContent VNodes that become children.
        The renderer builds the TabbedPanel element from the VNode tree.
        """
        from wijjit.core.vdom import VNodeBuilder
        from wijjit.elements.display.tabbed_panel import TabPosition
        from wijjit.tags.layout import get_element_marker

        # Handle 'class' attribute
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state
        focused_id = render_ctx.focused_id

        # Store original width/height specs for layout
        width_spec = width
        height_spec = height

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("tabbedpanel")

        # Parse tab position
        position_map = {
            "top": TabPosition.TOP,
            "bottom": TabPosition.BOTTOM,
            "left": TabPosition.LEFT,
            "right": TabPosition.RIGHT,
        }
        tab_pos = position_map.get(tab_position.lower(), TabPosition.TOP)

        # Create TabbedPanel VNode and push to stack
        vnode = VNodeBuilder("TabbedPanel", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("tab_position", tab_pos)
        vnode.set_prop("border_style", border_style)
        vnode.set_prop("bind", bind)
        if classes:
            vnode.set_prop("classes", classes)

        # Push VNode to stack - TabExtension children will add TabContent VNodes
        context.push_vnode(vnode)

        # Render body - this will collect all {% tab %} tags as TabContent VNode children
        _body_output = caller()

        # Pop VNode from stack
        context.pop_vnode()

        # Collect TabContent children from the VNode
        # tab_vnodes = [c for c in vnode.children if c.type == "TabContent"]

        # Determine initial active tab index
        active_tab_index = 0
        if isinstance(active_tab, int):
            active_tab_index = active_tab
        elif isinstance(active_tab, str) and bind:
            # active_tab is a state key - try to restore from state
            try:
                if active_tab in state:
                    active_tab_index = int(state[active_tab])
            except Exception as e:
                logger.warning(f"Failed to restore active tab state: {e}")

        # Add remaining props to VNode
        vnode.set_prop("active_tab_index", active_tab_index)
        if isinstance(active_tab, str) and bind:
            vnode.set_prop("active_tab_state_key", active_tab)

        # Check if this element should be focused
        if focused_id and id and focused_id == id:
            vnode.set_prop("focused", True)

        # Set layout dimensions
        vnode.set_layout(width=width_spec, height=height_spec)

        # Note: VNode is already in the tree from push_vnode/pop_vnode
        # The renderer will build the TabbedPanel element from the VNode tree,
        # using TabContent children to create tabs with their content.

        # Return marker for text interleaving
        return get_element_marker(context)


class LinkExtension(Extension):
    """Jinja2 extension for {% link %} tag.

    Syntax:
        {% link action="do_something" %}Click here{% endlink %}
        {% link action="go" class="text-primary" %}Go{% endlink %}
    """

    tags = {"link"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the link tag.

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
        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endlink"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (link text)
        node = nodes.CallBlock(
            self.call_method("_render_link", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endlink",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_link(
        self,
        caller: Callable[[], str],
        action: str | None = None,
        id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the link tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        action : str, optional
            Action name to trigger on click
        id : str, optional
            Element identifier
        **kwargs : dict
            Additional attributes

        Returns
        -------
        str
            Rendered output
        """

        # Handle 'class' attribute
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context

        # Get link text
        text_content = caller().strip()

        # Create VNode for reconciliation (removed duplicate old-style element creation)
        vnode = VNodeBuilder("Link", key=id)
        vnode.set_prop("text", text_content)
        vnode.set_prop("action", action)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width="auto", height="auto")
        context.add_vnode(vnode)

        # Return marker
        return get_element_marker(context)


class HTMLViewerExtension(Extension):
    """Jinja2 extension for {% htmlview %} tag.

    Syntax:
        {% htmlview id="html" width=60 height=20 %}
            <b>Bold</b> and <i>italic</i> text
        {% endhtmlview %}

        {% htmlview border_style="rounded" title="HTML Content" %}
            <text-danger>Error:</text-danger> Something went wrong
        {% endhtmlview %}
    """

    tags = {"htmlview"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the htmlview tag.

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
        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endhtmlview"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (HTML content)
        node = nodes.CallBlock(
            self.call_method("_render_htmlview", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endhtmlview",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_htmlview(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        width: int | str = 60,
        height: int | str = 20,
        show_scrollbar: bool = True,
        border_style: str = "single",
        title: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the htmlview tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        width : int or str, optional
            Display width (default: 60)
        height : int or str, optional
            Display height (default: 20)
        show_scrollbar : bool, optional
            Show scrollbar (default: True)
        border_style : str, optional
            Border style (default: "single")
        title : str, optional
            Border title
        **kwargs : dict
            Additional attributes

        Returns
        -------
        str
            Rendered output
        """

        # Handle 'class' attribute
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context

        # Get HTML content
        html_content = caller().strip()

        # Determine sizing
        width_spec: int | str = "fill" if width == "fill" else width
        height_spec: int | str = "fill" if height == "fill" else height

        # Create VNode for reconciliation (removed duplicate old-style element creation)
        vnode = VNodeBuilder("HTMLViewer", key=id)
        vnode.set_prop("content", html_content)
        vnode.set_prop("show_scrollbar", show_scrollbar)
        vnode.set_prop("border_style", border_style)
        if title:
            vnode.set_prop("title", title)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_layout(width=width_spec, height=height_spec)
        context.add_vnode(vnode)

        # Return marker
        return get_element_marker(context)
