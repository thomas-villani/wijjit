"""Thread-safe render context for template processing.

This module provides a context-variable-based approach to passing rendering state
through the template processing pipeline. It replaces the previous pattern of
storing state in Jinja2's environment.globals, which was not thread-safe or
reentrant.

The RenderContext consolidates all the `_wijjit_*` globals that were previously
scattered across the environment:
- layout_context: The LayoutContext for building VNode trees
- template_context: Dict containing 'state' and other template variables
- focused_id: Currently focused element ID
- radiogroup_stack: Stack for nested radio groups
- menu_stack: Stack for building nested menus
- frame_counter: Counter for auto-generating frame IDs

Usage
-----
In the Renderer:

    from wijjit.core.render_context import render_context_scope, get_render_context

    with render_context_scope(layout_context, template_context) as ctx:
        # Render template - extensions can access ctx via get_render_context()
        output = template.render(**template_context)

In template extensions:

    from wijjit.core.render_context import get_render_context

    def _render_button(self, ...):
        ctx = get_render_context()
        layout_ctx = ctx.layout_context
        focused_id = ctx.focused_id
        # ...
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wijjit.elements.menu import MenuItem
    from wijjit.tags.layout import LayoutContext


@dataclass
class RenderContext:
    """Consolidated rendering context for template processing.

    This class holds all state needed during template rendering, replacing
    the scattered _wijjit_* globals that were stored in Jinja2's environment.

    Parameters
    ----------
    layout_context : LayoutContext
        The layout context for building VNode trees
    template_context : dict
        Template variables including 'state'

    Attributes
    ----------
    layout_context : LayoutContext
        Layout tree building context
    template_context : dict
        Template variables (contains 'state', etc.)
    focused_id : str or None
        ID of the currently focused element
    radiogroup_stack : list of str
        Stack of active radio group names (for nesting)
    menu_stack : list of list of MenuItem
        Stack of menu item lists being built
    frame_counter : int
        Counter for auto-generating frame IDs
    overlays : list
        List of overlay info dicts for dialogs/menus
    statusbar : Element or None
        StatusBar element if present
    """

    layout_context: LayoutContext
    template_context: dict[str, Any]
    focused_id: str | None = None
    radiogroup_stack: list[str] = field(default_factory=list)
    menu_stack: list[list[MenuItem]] = field(default_factory=list)
    frame_counter: int = 0
    overlays: list[dict[str, Any]] = field(default_factory=list)
    statusbar: Any = None  # Element, but avoiding circular import

    @property
    def state(self) -> dict[str, Any]:
        """Get the application state dict from template context.

        Returns
        -------
        dict
            Application state, or empty dict if not present
        """
        result: dict[str, Any] = self.template_context.get("state", {})
        return result

    def generate_frame_id(self) -> str:
        """Generate a unique frame ID.

        Returns
        -------
        str
            Generated ID like 'frame_1'
        """
        self.frame_counter += 1
        return f"frame_{self.frame_counter}"

    def push_radiogroup(self, name: str) -> None:
        """Push a radio group name onto the stack.

        Parameters
        ----------
        name : str
            Radio group name
        """
        self.radiogroup_stack.append(name)

    def pop_radiogroup(self) -> str | None:
        """Pop and return the current radio group name.

        Returns
        -------
        str or None
            The popped radio group name, or None if stack is empty
        """
        if self.radiogroup_stack:
            return self.radiogroup_stack.pop()
        return None

    @property
    def current_radiogroup(self) -> str | None:
        """Get the current radio group name without popping.

        Returns
        -------
        str or None
            Current radio group name, or None if not in a group
        """
        return self.radiogroup_stack[-1] if self.radiogroup_stack else None

    def push_menu(self) -> list[MenuItem]:
        """Push a new menu items list onto the stack.

        Returns
        -------
        list
            The new menu items list (to be populated by menuitem tags)
        """
        items: list[MenuItem] = []
        self.menu_stack.append(items)
        return items

    def pop_menu(self) -> list[MenuItem] | None:
        """Pop and return the current menu items list.

        Returns
        -------
        list or None
            The popped menu items list, or None if stack is empty
        """
        if self.menu_stack:
            return self.menu_stack.pop()
        return None

    @property
    def current_menu(self) -> list[MenuItem] | None:
        """Get the current menu items list without popping.

        Returns
        -------
        list or None
            Current menu items list, or None if not building a menu
        """
        return self.menu_stack[-1] if self.menu_stack else None

    def add_overlay(self, overlay_info: dict[str, Any]) -> None:
        """Add an overlay info dict.

        Parameters
        ----------
        overlay_info : dict
            Overlay configuration dict
        """
        self.overlays.append(overlay_info)


# Module-level context variable for the current render context
_render_context: ContextVar[RenderContext | None] = ContextVar(
    "render_context", default=None
)


def get_render_context() -> RenderContext:
    """Get the current render context.

    Returns
    -------
    RenderContext
        The active render context

    Raises
    ------
    RuntimeError
        If called outside of a render_context_scope
    """
    ctx = _render_context.get()
    if ctx is None:
        raise RuntimeError(
            "No render context available. "
            "This function must be called during template rendering."
        )
    return ctx


def try_get_render_context() -> RenderContext | None:
    """Try to get the current render context without raising.

    Returns
    -------
    RenderContext or None
        The active render context, or None if not in a render scope
    """
    return _render_context.get()


@contextmanager
def render_context_scope(
    layout_context: LayoutContext,
    template_context: dict[str, Any],
    focused_id: str | None = None,
) -> Generator[RenderContext, None, None]:
    """Context manager for establishing a render context scope.

    This sets up the render context for the duration of template rendering,
    and automatically cleans it up when done. It's reentrant-safe due to
    using contextvars.

    Parameters
    ----------
    layout_context : LayoutContext
        Layout context for VNode tree building
    template_context : dict
        Template variables including 'state'
    focused_id : str, optional
        ID of the focused element

    Yields
    ------
    RenderContext
        The active render context

    Examples
    --------
    >>> from wijjit.tags.layout import LayoutContext
    >>> layout_ctx = LayoutContext()
    >>> with render_context_scope(layout_ctx, {"state": {}}) as ctx:
    ...     # Extensions can now call get_render_context()
    ...     pass
    """
    ctx = RenderContext(
        layout_context=layout_context,
        template_context=template_context,
        focused_id=focused_id,
    )

    token = _render_context.set(ctx)
    try:
        yield ctx
    finally:
        _render_context.reset(token)
