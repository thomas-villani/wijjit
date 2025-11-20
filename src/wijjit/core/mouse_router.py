"""Mouse event routing for Wijjit applications.

This module provides the MouseEventRouter class which handles routing
mouse events to appropriate elements and overlays.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wijjit.core.events import MouseEvent
from wijjit.elements.menu import ContextMenu
from wijjit.logging_config import get_logger
from wijjit.terminal.mouse import MouseButton, MouseEventType
from wijjit.terminal.mouse import MouseEvent as TerminalMouseEvent

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit
    from wijjit.elements.base import Element

logger = get_logger(__name__)


class MouseEventRouter:
    """Routes mouse events to appropriate handlers.

    The router handles:
    - Hit testing for mouse events
    - Overlay routing (check overlays first)
    - Context menu detection (right-click)
    - Hover state management
    - Element mouse event dispatch

    Parameters
    ----------
    app : Wijjit
        Reference to the main application

    Attributes
    ----------
    app : Wijjit
        Application reference
    """

    def __init__(self, app: Wijjit) -> None:
        """Initialize the mouse event router.

        Parameters
        ----------
        app : Wijjit
            Reference to the main application
        """
        self.app = app

    async def route_mouse_event(self, event: TerminalMouseEvent) -> bool:
        """Route mouse event to appropriate handler.

        This method:
        1. Checks overlays first (highest z-index)
        2. Checks for context menu triggers (right-click)
        3. Updates hover state
        4. Routes to element under cursor

        Parameters
        ----------
        event : TerminalMouseEvent
            The mouse event from terminal layer

        Returns
        -------
        bool
            True if hover state changed (indicating need for re-render)
        """
        try:
            # Check overlays first (highest z-index)
            if self._route_to_overlay(event):
                return False

            # Check for click outside overlays
            if self._handle_click_outside_overlays(event):
                return False

            # Fall through to base UI handling
            # Find element at mouse coordinates
            target_element = self._find_element_at(event.x, event.y)

            # Check for right-click to open context menus
            if self._handle_context_menu(event, target_element):
                return False

            # Update hover state
            hover_changed = self._update_hover(event, target_element)

            # Focus element on click if it's focusable
            self._handle_focus_on_click(event, target_element)

            # Route to element (async to support async mouse handlers)
            await self._route_to_element(event, target_element)

            return hover_changed

        except Exception as e:
            self.app._handle_error("Error handling mouse event", e)
            return False

    def _route_to_overlay(self, event: TerminalMouseEvent) -> bool:
        """Route event to overlay if mouse is over one.

        Parameters
        ----------
        event : TerminalMouseEvent
            The mouse event

        Returns
        -------
        bool
            True if event was routed to overlay, False otherwise
        """
        overlay = self.app.overlay_manager.get_at_position(event.x, event.y)

        if overlay:
            # Mouse event is on an overlay - route to overlay element
            if hasattr(overlay.element, "handle_mouse"):
                handled = overlay.element.handle_mouse(event)
                if handled:
                    self.app.needs_render = True
            # Overlay consumed the event even if not handled
            return True

        return False

    def _handle_click_outside_overlays(self, event: TerminalMouseEvent) -> bool:
        """Handle clicks outside all overlays.

        Parameters
        ----------
        event : TerminalMouseEvent
            The mouse event

        Returns
        -------
        bool
            True if an overlay was closed, False otherwise
        """
        # Click outside all overlays - check if should close any
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            closed = self.app.overlay_manager.handle_click_outside(event.x, event.y)
            if closed:
                return True

        return False

    def _handle_context_menu(
        self, event: TerminalMouseEvent, target_element: Element | None
    ) -> bool:
        """Handle right-click for context menus.

        Parameters
        ----------
        event : TerminalMouseEvent
            The mouse event
        target_element : Element or None
            Element under mouse cursor

        Returns
        -------
        bool
            True if context menu was shown, False otherwise
        """
        # Check for right-click to open context menus (AFTER elements have bounds)
        if event.button == MouseButton.RIGHT and event.type == MouseEventType.CLICK:
            logger.debug(f"Right-click detected at ({event.x}, {event.y})")
            logger.debug(
                f"Target element: {target_element.id if target_element and hasattr(target_element, 'id') else None}"
            )

            # Check if any context menu targets this element
            if target_element and hasattr(target_element, "id"):
                logger.debug(
                    f"Has _last_template_overlays: {hasattr(self.app, '_last_template_overlays')}"
                )
                # Check template overlays for context menus targeting this element
                if hasattr(self.app, "_last_template_overlays"):
                    logger.debug(
                        f"Number of template overlays: {len(self.app._last_template_overlays)}"
                    )
                    for overlay_info in self.app._last_template_overlays:
                        elem = overlay_info["element"]
                        if isinstance(elem, ContextMenu):
                            logger.debug(
                                f"Found ContextMenu targeting: {elem.target_element_id}"
                            )
                            if elem.target_element_id == target_element.id:
                                logger.debug(
                                    f"Match! Showing context menu at ({event.x}, {event.y})"
                                )
                                # Get visibility state key
                                visible_state_key = overlay_info.get(
                                    "visible_state_key"
                                )
                                if visible_state_key:
                                    # Store mouse position in state using visible_state_key
                                    # This is stable across renders (unlike auto-generated IDs)
                                    position_key = (
                                        f"_context_menu_pos_{visible_state_key}"
                                    )
                                    self.app.state[position_key] = (event.x, event.y)
                                    logger.debug(
                                        f"Stored position in state[{position_key!r}] = {self.app.state[position_key]}"
                                    )

                                    # Show the context menu
                                    logger.debug(
                                        f"Setting state[{visible_state_key!r}] = True"
                                    )
                                    self.app.state[visible_state_key] = True
                                    self.app.needs_render = True
                                    return True

        return False

    def _update_hover(
        self, event: TerminalMouseEvent, target_element: Element | None
    ) -> bool:
        """Update hover state.

        Parameters
        ----------
        event : TerminalMouseEvent
            The mouse event
        target_element : Element or None
            Element under mouse cursor

        Returns
        -------
        bool
            True if hover state changed, False otherwise
        """
        # Update hover state (only on move/click, not on scroll)
        if event.type in (
            MouseEventType.MOVE,
            MouseEventType.CLICK,
            MouseEventType.DOUBLE_CLICK,
            MouseEventType.PRESS,
            MouseEventType.RELEASE,
            MouseEventType.DRAG,
        ):
            # Set hovered element (returns True if changed)
            return self.app.hover_manager.set_hovered(target_element)

        return False

    def _handle_focus_on_click(
        self, event: TerminalMouseEvent, target_element: Element | None
    ) -> None:
        """Focus element on click if it's focusable.

        Parameters
        ----------
        event : TerminalMouseEvent
            The mouse event
        target_element : Element or None
            Element under mouse cursor
        """
        # Focus element on click if it's focusable
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            if (
                target_element
                and hasattr(target_element, "focusable")
                and target_element.focusable
            ):
                focus_changed = self.app.focus_manager.focus_element(target_element)
                if focus_changed:
                    self.app.needs_render = True

    async def _route_to_element(
        self, event: TerminalMouseEvent, target_element: Element | None
    ) -> None:
        """Route event to target element.

        Parameters
        ----------
        event : TerminalMouseEvent
            The mouse event
        target_element : Element or None
            Element under mouse cursor
        """
        # Create core MouseEvent for handler registry
        mouse_event = MouseEvent(
            mouse_event=event,
            element_id=(
                target_element.id
                if target_element and hasattr(target_element, "id")
                else None
            ),
        )

        # Dispatch through handler registry (async to support async handlers)
        await self.app.handler_registry.dispatch_async(mouse_event)

        # If event was cancelled, we're done
        if mouse_event.cancelled:
            return

        # Dispatch to target element if it exists
        handled = False
        if target_element and hasattr(target_element, "handle_mouse"):
            handled = target_element.handle_mouse(event)
            if handled:
                # Element handled the event, trigger re-render
                self.app.needs_render = True

        # If scroll event wasn't handled and element has a scrollable parent, try parent
        if (
            not handled
            and event.type == MouseEventType.SCROLL
            and target_element
            and hasattr(target_element, "parent_frame")
            and target_element.parent_frame is not None
        ):
            parent = target_element.parent_frame
            if hasattr(parent, "handle_mouse"):
                handled = parent.handle_mouse(event)
                if handled:
                    self.app.needs_render = True

    def _find_element_at(self, x: int, y: int) -> Element | None:
        """Find the element at the given coordinates.

        Searches positioned elements in reverse order (top-to-bottom in
        render order) to find the topmost element at the coordinates.

        Parameters
        ----------
        x : int
            Column position (0-based)
        y : int
            Row position (0-based)

        Returns
        -------
        Element or None
            Element at coordinates, or None if no element found
        """
        from wijjit.elements.base import TextElement

        # Search in reverse order (top-to-bottom)
        # Skip TextElements as they are just content holders, not interactive targets
        for elem in reversed(self.app.positioned_elements):
            if isinstance(elem, TextElement):
                continue
            if elem.bounds and elem.bounds.contains(x, y):
                return elem
        return None
