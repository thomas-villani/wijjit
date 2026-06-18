"""Jinja2 extensions for dropdown and context menu tags.

This module provides template tags for creating dropdown menus and context menus.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.core.overlay import LayerType
from wijjit.core.render_context import get_render_context
from wijjit.elements.menu import ContextMenu, DropdownMenu, MenuItem
from wijjit.logging_config import get_logger
from wijjit.tags.layout import parse_tag_attributes

if TYPE_CHECKING:
    pass

# Get logger for this module
logger = get_logger(__name__)


class MenuItemExtension(Extension):
    """Jinja2 extension for {% menuitem %} tag.

    Creates a menu item within a dropdown or context menu.

    Syntax::

        {% menuitem action="new_file" key="Ctrl+N" %}New File{% endmenuitem %}
        {% menuitem divider=true %}{% endmenuitem %}
        {% menuitem action="help" disabled=true %}Help{% endmenuitem %}
    """

    tags = {"menuitem"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the menuitem tag.

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
        kwargs = parse_tag_attributes(parser, "endmenuitem", lineno)

        # Parse body (menu item label)
        node = nodes.CallBlock(
            self.call_method("_render_menuitem", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endmenuitem",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_menuitem(
        self,
        caller: Callable[[], str],
        action: str | None = None,
        key: str | None = None,
        divider: bool = False,
        disabled: bool = False,
        label: str = "",
        **kwargs: Any,
    ) -> str:
        """Render the menuitem tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content (label text)
        action : str, optional
            Action ID to dispatch when item is selected
        key : str, optional
            Keyboard shortcut hint (e.g., "Ctrl+N")
        divider : bool
            Whether this is a divider line (default: False)
        disabled : bool
            Whether this item is disabled (default: False)
        label : str, optional
            Item label. If empty, the tag body is used as the label.

        Returns
        -------
        str
            Rendered output (empty string, item is added to parent menu)
        """
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get the current menu being built from RenderContext
        render_ctx = get_render_context()
        current_menu = render_ctx.current_menu

        if current_menu is None:
            logger.warning("menuitem tag used outside of dropdown/contextmenu")
            # Consume body anyway
            caller()
            return ""

        # Label comes from the label attribute, falling back to the tag body.
        # Dividers never carry a label.
        body = caller().strip()
        if divider:
            label = ""
        elif not label:
            label = body

        # Create MenuItem - menus need direct Element instantiation
        # to maintain the menu item structure for the menu element
        item = MenuItem(
            label=label,
            action=action,
            key=key,
            divider=bool(divider),
            disabled=bool(disabled),
            classes=classes,
        )

        # Add to current menu
        current_menu.append(item)

        return ""


class DropdownExtension(Extension):
    """Jinja2 extension for {% dropdown %} tag.

    Creates a dropdown menu that appears when triggered.

    Syntax::

        {% dropdown trigger="File" key="Alt+F" visible="show_file_menu" %}
            {% menuitem action="new" key="Ctrl+N" %}New{% endmenuitem %}
            {% menuitem action="open" key="Ctrl+O" %}Open{% endmenuitem %}
            {% menuitem divider=true %}{% endmenuitem %}
            {% menuitem action="quit" key="Ctrl+Q" %}Quit{% endmenuitem %}
        {% enddropdown %}
    """

    tags = {"dropdown"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the dropdown tag.

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
        kwargs = parse_tag_attributes(parser, "enddropdown", lineno)

        # Parse body (menu items)
        node = nodes.CallBlock(
            self.call_method("_render_dropdown", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:enddropdown",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_dropdown(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        trigger: str = "Menu",
        key: str | None = None,
        visible: str | None = None,
        width: int = 30,
        border: str | None = None,
        border_style: str = "single",
        **kwargs: Any,
    ) -> str:
        """Render the dropdown tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content (menu items)
        id : str, optional
            Element identifier
        trigger : str
            Text for the trigger button (default: "Menu")
        key : str, optional
            Keyboard shortcut to open menu (e.g., "Alt+F")
        visible : str, optional
            State key name for visibility control
        width : int
            Menu width (default: 30)
        border : str, optional
            Canonical border style (``single``, ``double``, ``rounded``,
            ``none``). Takes precedence over ``border_style`` when given.
        border_style : str
            Border style: "single", "double", or "rounded" (default: "single")

        Returns
        -------
        str
            Rendered output (empty string, menu is registered as overlay)
        """
        if border is not None:
            border_style = border
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        state = render_ctx.state

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("dropdown")

        # Check visibility state
        is_visible = False
        if visible:
            try:
                is_visible = bool(state.get(visible, False))
            except (TypeError, AttributeError) as e:
                logger.warning(f"Failed to check visibility state: {e}")

        # Create menu items stack for nested menuitem tags
        # IMPORTANT: Always set up menu_stack before calling caller(),
        # even if not visible, to avoid "menuitem outside dropdown" errors
        items_list = render_ctx.push_menu()

        # Render body (this will populate items_list via menuitem tags)
        caller()

        # Pop items list
        render_ctx.pop_menu()

        # Convert numeric parameters
        width = int(width)

        # IMPORTANT: Always create the dropdown element, even if not visible
        # This allows shortcuts to be registered. The overlay manager will
        # handle showing/hiding based on visibility state.
        dropdown = DropdownMenu(
            id=id,
            classes=classes,
            items=items_list,
            trigger_text=trigger,
            trigger_key=key,
            width=width,
            border_style=border_style,
        )

        # Store overlay info for app to register
        overlay_info: dict[str, Any] = {
            "element": dropdown,
            "layer_type": LayerType.DROPDOWN,
            "close_on_escape": True,
            "close_on_click_outside": True,
            "trap_focus": True,
            "dim_background": False,
            "visible_state_key": visible,
            "is_visible": is_visible,  # Track initial visibility
        }

        # Add overlay via RenderContext
        render_ctx.add_overlay(overlay_info)

        return ""


class ContextMenuExtension(Extension):
    """Jinja2 extension for {% contextmenu %} tag.

    Creates a context menu that appears on right-click.

    Syntax::

        {% contextmenu target="file_list" visible="show_context_menu" %}
            {% menuitem action="rename" %}Rename{% endmenuitem %}
            {% menuitem action="delete" %}Delete{% endmenuitem %}
            {% menuitem divider=true %}{% endmenuitem %}
            {% menuitem action="properties" %}Properties{% endmenuitem %}
        {% endcontextmenu %}
    """

    tags = {"contextmenu"}

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the contextmenu tag.

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
        kwargs = parse_tag_attributes(parser, "endcontextmenu", lineno)

        # Parse body (menu items)
        node = nodes.CallBlock(
            self.call_method("_render_contextmenu", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endcontextmenu",), drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_contextmenu(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        target: str | None = None,
        visible: str | None = None,
        width: int = 30,
        border: str | None = None,
        border_style: str = "single",
        **kwargs: Any,
    ) -> str:
        """Render the contextmenu tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content (menu items)
        id : str, optional
            Element identifier
        target : str, optional
            ID of the element this context menu is attached to
        visible : str, optional
            State key name for visibility control
        width : int
            Menu width (default: 30)
        border : str, optional
            Canonical border style (``single``, ``double``, ``rounded``,
            ``none``). Takes precedence over ``border_style`` when given.
        border_style : str
            Border style: "single", "double", or "rounded" (default: "single")

        Returns
        -------
        str
            Rendered output (empty string, menu is registered as overlay)
        """
        if border is not None:
            border_style = border
        # Handle 'class' attribute (rename to 'classes' since 'class' is a Python keyword)
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        layout_context = render_ctx.layout_context
        state = render_ctx.state

        # Auto-generate ID if not provided
        if id is None:
            id = layout_context.generate_id("contextmenu")

        # Check visibility state
        is_visible = False
        if visible:
            try:
                is_visible = bool(state.get(visible, False))
            except (TypeError, AttributeError) as e:
                logger.warning(f"Failed to check visibility state: {e}")

        # Create menu items stack for nested menuitem tags
        # IMPORTANT: Always set up menu_stack before calling caller(),
        # even if not visible, to avoid "menuitem outside dropdown" errors
        items_list = render_ctx.push_menu()

        # Render body (this will populate items_list via menuitem tags)
        caller()

        # Pop items list
        render_ctx.pop_menu()

        # Convert numeric parameters
        width = int(width)

        # IMPORTANT: Always create the context menu element, even if not visible
        # This allows right-click detection to be registered.
        context_menu = ContextMenu(
            id=id,
            classes=classes,
            items=items_list,
            target_element_id=target,
            width=width,
            border_style=border_style,
        )

        # Store overlay info for app to register
        overlay_info: dict[str, Any] = {
            "element": context_menu,
            "layer_type": LayerType.DROPDOWN,
            "close_on_escape": True,
            "close_on_click_outside": True,
            "trap_focus": True,
            "dim_background": False,
            "visible_state_key": visible,
            "target_element_id": target,  # Store for right-click registration
            "is_visible": is_visible,  # Track initial visibility
        }

        # Add overlay via RenderContext
        render_ctx.add_overlay(overlay_info)

        return ""
