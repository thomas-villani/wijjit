"""Link element for inline clickable text.

This module provides the Link element, which renders as clickable text
that triggers actions when activated via keyboard or mouse.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from wijjit.elements.base import Element, ElementType, invoke_callback
from wijjit.terminal.ansi import visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class Link(Element):
    """Inline clickable text element.

    Link renders as styled text that can be focused and activated
    via keyboard (Enter/Space) or mouse click. When activated, it
    triggers the specified action.

    Parameters
    ----------
    text : str
        Link text to display
    action : str, optional
        Action name to trigger on activation
    id : str, optional
        Element identifier
    classes : str or list of str or set of str, optional
        CSS class names for styling
    on_click : callable, optional
        Callback function called when link is activated.
        Signature: on_click() -> None

    Attributes
    ----------
    text : str
        Link text content
    action : str or None
        Action name for event dispatch
    on_click : callable or None
        Click callback function

    Examples
    --------
    Create a simple link:

    >>> link = Link("Click here", action="do_something")

    With callback:

    >>> def handle_click():
    ...     print("Link clicked!")
    >>> link = Link("Click me", on_click=handle_click)

    With CSS class styling:

    >>> link = Link("Danger!", action="delete", classes="text-danger")
    """

    def __init__(
        self,
        text: str,
        action: str | None = None,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.text = text
        self.action = action
        self.on_click = on_click

        self.element_type = ElementType.BUTTON
        self.focusable = True

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size based on text content.

        Returns
        -------
        tuple[int, int]
            (width, height) - links are always single line
        """
        return (visible_length(self.text), 1)

    def render_to(self, ctx: PaintContext) -> None:
        """Render the link element.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Link styling is resolved from theme:
        - ``link``: Default link style (typically cyan underlined)
        - ``link:focus``: When link has focus
        - ``link:hover``: When mouse is over link
        """
        from wijjit.terminal.ansi import clip_to_width

        # Resolve style based on state
        if self.focused:
            style = ctx.style_resolver.resolve_style(self, "link:focus")
        elif self.hovered:
            style = ctx.style_resolver.resolve_style(self, "link:hover")
        else:
            style = ctx.style_resolver.resolve_style(self, "link")

        # Clip text to bounds
        display_text = clip_to_width(self.text, ctx.bounds.width, ellipsis="...")

        # Write text
        ctx.write_text(0, 0, display_text, style)

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input.

        Parameters
        ----------
        key : Key
            Key that was pressed

        Returns
        -------
        bool
            True if key was handled

        Notes
        -----
        Link is activated by Enter or Space when focused.
        """
        if key == Keys.ENTER or key == Keys.SPACE:
            self._activate()
            return True
        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input.

        Parameters
        ----------
        event : MouseEvent
            Mouse event

        Returns
        -------
        bool
            True if event was handled

        Notes
        -----
        Link is activated by left click.
        """
        if event.type == MouseEventType.CLICK:
            if event.button == MouseButton.LEFT:
                self._activate()
                return True
        return False

    def _activate(self) -> None:
        """Activate the link (internal).

        Calls on_click callback if set. Action events are dispatched
        by the application's event system.
        """
        if self.on_click:
            invoke_callback(self.on_click)
