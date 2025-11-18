"""Event loop for Wijjit applications.

This module provides the EventLoop class which handles the main application
event loop including input reading, event dispatching, and rendering.
Supports both synchronous and asynchronous operation with backward compatibility.
"""

from __future__ import annotations

import asyncio
import shutil
import time
from typing import TYPE_CHECKING

from wijjit.core.events import KeyEvent
from wijjit.logging_config import get_logger
from wijjit.terminal.input import Key
from wijjit.terminal.mouse import MouseEvent as TerminalMouseEvent

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit

logger = get_logger(__name__)


class EventLoop:
    """Main event loop for Wijjit applications.

    The event loop handles:
    - Input reading from keyboard and mouse
    - Terminal resize detection
    - Animation frame advancement
    - Notification expiry checks
    - Event dispatching to handlers
    - Rendering orchestration

    Parameters
    ----------
    app : Wijjit
        Reference to the main application

    Attributes
    ----------
    app : Wijjit
        Application reference
    running : bool
        Whether the event loop is currently running
    """

    def __init__(self, app: Wijjit):
        """Initialize the event loop.

        Parameters
        ----------
        app : Wijjit
            Reference to the main application
        """
        self.app = app
        self.running = False

    def run(self) -> None:
        """Run the main event loop.

        This is the entry point for the application. It wraps the async
        event loop for backward compatibility with synchronous code.

        The loop continues until quit() is called or the user presses Ctrl+C.

        Raises
        ------
        RuntimeError
            If no views are registered
        """
        # Run the async event loop
        asyncio.run(self.run_async())

    async def run_async(self) -> None:
        """Run the main async event loop.

        This method enters the main event loop which:
        1. Renders initial view
        2. Loops: read input -> dispatch events -> re-render if needed
        3. Exits on quit() or Ctrl+C

        The loop continues until quit() is called or the user presses Ctrl+C.

        Raises
        ------
        RuntimeError
            If no views are registered
        """
        logger.info("Starting Wijjit application (async mode)")

        # Find default view if current_view not set
        if self.app.current_view is None:
            for name, view in self.app.views.items():
                if view.is_default:
                    self.app.current_view = name
                    logger.debug(f"Selected default view: '{name}'")
                    break

        if self.app.current_view is None and self.app.views:
            # Use first registered view as fallback
            self.app.current_view = next(iter(self.app.views.keys()))
            logger.debug(
                f"No default view, using first view: '{self.app.current_view}'"
            )

        if self.app.current_view is None:
            logger.error("No views registered")
            raise RuntimeError(
                "No views registered. Use @app.view() to register a view."
            )

        # Initialize and call on_enter for initial view (async)
        initial_view = self.app.views[self.app.current_view]
        await self.app.view_router._initialize_view_async(initial_view)

        # Set current view in handler registry so view-scoped handlers work
        self.app.handler_registry.current_view = self.app.current_view

        if initial_view.on_enter:
            try:
                if asyncio.iscoroutinefunction(initial_view.on_enter):
                    await initial_view.on_enter()
                else:
                    # Run sync hook in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, initial_view.on_enter)
            except Exception as e:
                self.app._handle_error(
                    f"Error in on_enter for view '{self.app.current_view}'", e
                )

        self.running = True

        try:
            # Enter alternate screen
            self.app.screen_manager.enter_alternate_buffer()
            logger.debug("Entered alternate screen buffer")

            # Hide cursor for better TUI appearance
            self.app.screen_manager.hide_cursor()
            logger.debug("Hidden cursor")

            # Enable mouse tracking
            self.app.input_handler.enable_mouse_tracking()
            logger.debug("Enabled mouse tracking")

            # Render initial view
            logger.info(f"Rendering initial view: '{self.app.current_view}'")
            self.app._render()
            self.app._last_refresh_time = time.time()

            logger.info("Entering main async event loop")
            # Main event loop
            while self.running:
                try:
                    await self._process_frame_async()
                except KeyboardInterrupt:
                    logger.info("Received KeyboardInterrupt, exiting application")
                    self.running = False
                    break
                except Exception as e:
                    self.app._handle_error("Error in event loop", e)
                    # Critical error - exit the loop
                    self.running = False
                    break

        finally:
            logger.info("Exiting application, cleaning up")
            # Show cursor before exiting
            self.app.screen_manager.show_cursor()
            logger.debug("Shown cursor")
            # Always exit alternate screen on cleanup
            self.app.screen_manager.exit_alternate_buffer()
            logger.debug("Exited alternate screen buffer")
            # Close input handler to exit raw mode
            self.app.input_handler.close()
            logger.debug("Closed input handler")
            logger.info("Application shutdown complete")

    def stop(self) -> None:
        """Stop the event loop.

        Sets the running flag to False which will cause the event loop
        to exit after the current iteration completes.
        """
        self.running = False

    def _process_frame(self) -> None:
        """Process a single frame of the event loop (synchronous - deprecated).

        This method is deprecated. Use _process_frame_async() instead.

        This method handles:
        - Auto-refresh for animations
        - Notification expiry
        - Terminal resize detection
        - Input reading and event dispatch
        - Re-rendering when needed
        """
        # Check if auto-refresh is needed (for animations like spinners or notification expiry)
        if self.app.refresh_interval is not None:
            current_time = time.time()
            elapsed = current_time - self.app._last_refresh_time

            if elapsed >= self.app.refresh_interval:
                # Time to refresh - advance spinner frames
                self._advance_spinner_frames()

                # Check for expired notifications
                if self.app.notification_manager.check_expired():
                    self.app.needs_render = True

                # Disable auto-refresh if no notifications remain
                if (
                    len(self.app.notification_manager.notifications) == 0
                    and self.app.refresh_interval == 0.1
                ):
                    self.app.refresh_interval = None

                self.app._last_refresh_time = current_time

        # Check for terminal resize
        term_size = shutil.get_terminal_size()
        current_size = (term_size.columns, term_size.lines)
        if current_size != self.app._last_terminal_size:
            logger.debug(
                f"Terminal resized from {self.app._last_terminal_size} to {current_size}"
            )
            # Recalculate overlay positions
            self.app.overlay_manager.recalculate_centered_overlays(
                term_size.columns, term_size.lines
            )
            # Update notification positions
            self.app.notification_manager.update_terminal_size(
                term_size.columns, term_size.lines
            )
            self.app._last_terminal_size = current_size
            self.app.needs_render = True

        # Read input - use short timeout if refresh_interval is set
        # This allows animations to run smoothly without requiring user input
        timeout = (
            self.app.refresh_interval / 2
            if self.app.refresh_interval is not None
            else None
        )
        input_event = self.app.input_handler.read_input(timeout=timeout)

        if input_event is None:
            # Timeout or error reading input
            # Check if refresh is needed (for animations/expiry checks)
            if self.app.needs_render:
                self.app._render()
                self.app._last_refresh_time = time.time()
            return

        # Check if it's a keyboard event
        if isinstance(input_event, Key):
            self._handle_key_event(input_event)

        # Check if it's a mouse event
        elif isinstance(input_event, TerminalMouseEvent):
            self._handle_mouse_event(input_event)

        # Re-render if needed
        if self.app.needs_render:
            self.app._render()
            self.app._last_refresh_time = time.time()

    async def _process_frame_async(self) -> None:
        """Process a single frame of the event loop (async).

        This method handles:
        - Auto-refresh for animations
        - Notification expiry
        - Terminal resize detection
        - Input reading and event dispatch
        - Re-rendering when needed
        """
        # Check if auto-refresh is needed (for animations like spinners or notification expiry)
        if self.app.refresh_interval is not None:
            current_time = time.time()
            elapsed = current_time - self.app._last_refresh_time

            if elapsed >= self.app.refresh_interval:
                # Time to refresh - advance spinner frames
                self._advance_spinner_frames()

                # Check for expired notifications (async)
                if await self.app.notification_manager.check_expired_async():
                    self.app.needs_render = True

                # Disable auto-refresh if no notifications remain
                if (
                    len(self.app.notification_manager.notifications) == 0
                    and self.app.refresh_interval == 0.1
                ):
                    self.app.refresh_interval = None

                self.app._last_refresh_time = current_time

        # Check for terminal resize
        term_size = shutil.get_terminal_size()
        current_size = (term_size.columns, term_size.lines)
        if current_size != self.app._last_terminal_size:
            logger.debug(
                f"Terminal resized from {self.app._last_terminal_size} to {current_size}"
            )
            # Recalculate overlay positions
            self.app.overlay_manager.recalculate_centered_overlays(
                term_size.columns, term_size.lines
            )
            # Update notification positions
            self.app.notification_manager.update_terminal_size(
                term_size.columns, term_size.lines
            )
            self.app._last_terminal_size = current_size
            self.app.needs_render = True

        # Read input asynchronously - use short timeout if refresh_interval is set
        # This allows animations to run smoothly without requiring user input
        timeout = (
            self.app.refresh_interval / 2
            if self.app.refresh_interval is not None
            else None
        )
        input_event = await self.app.input_handler.read_input_async(timeout=timeout)

        if input_event is None:
            # Timeout or error reading input
            # Check if refresh is needed (for animations/expiry checks)
            if self.app.needs_render:
                self.app._render()
                self.app._last_refresh_time = time.time()
            return

        # Check if it's a keyboard event
        if isinstance(input_event, Key):
            await self._handle_key_event_async(input_event)

        # Check if it's a mouse event
        elif isinstance(input_event, TerminalMouseEvent):
            await self._handle_mouse_event_async(input_event)

        # Re-render if needed
        if self.app.needs_render:
            self.app._render()
            self.app._last_refresh_time = time.time()

    def _handle_key_event(self, input_event: Key) -> None:
        """Handle a keyboard event.

        Parameters
        ----------
        input_event : Key
            The keyboard input event
        """
        # Handle Ctrl+C
        if input_event.is_ctrl_c:
            logger.info("Received Ctrl+C, exiting application")
            self.running = False
            return

        logger.debug(
            f"Key event: {input_event.name} (modifiers={input_event.modifiers})"
        )

        # Check for ESC key to close overlays/notifications
        if input_event.name == "escape":
            # If there are notifications, dismiss oldest first
            if self.app.notification_manager.notifications:
                if self.app.notification_manager.dismiss_oldest():
                    self.app.needs_render = True
                    return  # Don't process event further

            # Otherwise, handle normal overlay escape
            if self.app.overlay_manager.handle_escape():
                # Overlay was closed, trigger re-render
                self.app.needs_render = True
                return  # Don't process event further

        # Route keyboard events to overlay if trap_focus is active
        top_overlay = self.app.overlay_manager.get_top_overlay()
        if top_overlay and top_overlay.trap_focus:
            overlay_elem = top_overlay.element
            if hasattr(overlay_elem, "handle_key"):
                if overlay_elem.handle_key(input_event):
                    # Overlay handled the key, trigger re-render
                    self.app.needs_render = True
                    return  # Don't process event further

        # Create and dispatch key event
        event = KeyEvent(
            key=input_event.name,
            modifiers=input_event.modifiers,
            key_obj=input_event,  # Store original Key object
        )
        self.app.handler_registry.dispatch(event)

        # Check for registered key handlers
        if not event.cancelled:
            key_name = input_event.name.lower() if input_event.name else ""
            if key_name in self.app._key_handlers:
                try:
                    self.app._key_handlers[key_name](event)
                    self.app.needs_render = True
                except Exception as e:
                    logger.error(
                        f"Error in key handler for '{key_name}': {e}",
                        exc_info=True,
                    )

        # Route key to focused element if not handled by other handlers
        # If focus is trapped in an overlay, only route to overlay elements
        if not event.cancelled:
            if self.app.overlay_manager.should_trap_focus():
                # Focus is trapped - only route to focused element if it's in overlay
                focused = self.app.focus_manager.get_focused_element()
                if focused:
                    handled = focused.handle_key(input_event)
                    if handled:
                        self.app.needs_render = True
            else:
                # Normal focus routing
                self._route_key_to_focused_element(event)

    def _handle_mouse_event(self, terminal_event: TerminalMouseEvent) -> None:
        """Handle a mouse event (synchronous - deprecated).

        Parameters
        ----------
        terminal_event : TerminalMouseEvent
            The mouse event from terminal layer
        """
        logger.debug(
            f"Mouse event: {terminal_event.type} at ({terminal_event.x}, {terminal_event.y})"
        )
        # Delegate to mouse router
        hover_changed = self.app.mouse_router.route_mouse_event(terminal_event)

        # Only re-render if hover changed or event was handled
        if hover_changed:
            self.app.needs_render = True

    async def _handle_key_event_async(self, input_event: Key) -> None:
        """Handle a keyboard event (async).

        Parameters
        ----------
        input_event : Key
            The keyboard input event
        """
        # Handle Ctrl+C
        if input_event.is_ctrl_c:
            logger.info("Received Ctrl+C, exiting application")
            self.running = False
            return

        logger.debug(
            f"Key event: {input_event.name} (modifiers={input_event.modifiers})"
        )

        # Check for ESC key to close overlays/notifications
        if input_event.name == "escape":
            # If there are notifications, dismiss oldest first
            if self.app.notification_manager.notifications:
                if self.app.notification_manager.dismiss_oldest():
                    self.app.needs_render = True
                    return  # Don't process event further

            # Otherwise, handle normal overlay escape
            if self.app.overlay_manager.handle_escape():
                # Overlay was closed, trigger re-render
                self.app.needs_render = True
                return  # Don't process event further

        # Route keyboard events to overlay if trap_focus is active
        top_overlay = self.app.overlay_manager.get_top_overlay()
        if top_overlay and top_overlay.trap_focus:
            overlay_elem = top_overlay.element
            if hasattr(overlay_elem, "handle_key"):
                if overlay_elem.handle_key(input_event):
                    # Overlay handled the key, trigger re-render
                    self.app.needs_render = True
                    return  # Don't process event further

        # Create and dispatch key event (async)
        event = KeyEvent(
            key=input_event.name,
            modifiers=input_event.modifiers,
            key_obj=input_event,  # Store original Key object
        )
        await self.app.handler_registry.dispatch_async(event)

        # Check for registered key handlers
        if not event.cancelled:
            key_name = input_event.name.lower() if input_event.name else ""
            if key_name in self.app._key_handlers:
                try:
                    handler = self.app._key_handlers[key_name]
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        # Run sync handler in executor
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, handler, event)
                    self.app.needs_render = True
                except Exception as e:
                    logger.error(
                        f"Error in key handler for '{key_name}': {e}",
                        exc_info=True,
                    )

        # Route key to focused element if not handled by other handlers
        # If focus is trapped in an overlay, only route to overlay elements
        if not event.cancelled:
            if self.app.overlay_manager.should_trap_focus():
                # Focus is trapped - only route to focused element if it's in overlay
                focused = self.app.focus_manager.get_focused_element()
                if focused:
                    handled = focused.handle_key(input_event)
                    if handled:
                        self.app.needs_render = True
            else:
                # Normal focus routing
                self._route_key_to_focused_element(event)

    async def _handle_mouse_event_async(
        self, terminal_event: TerminalMouseEvent
    ) -> None:
        """Handle a mouse event (async).

        Parameters
        ----------
        terminal_event : TerminalMouseEvent
            The mouse event from terminal layer
        """
        logger.debug(
            f"Mouse event: {terminal_event.type} at ({terminal_event.x}, {terminal_event.y})"
        )
        # Delegate to mouse router
        hover_changed = self.app.mouse_router.route_mouse_event(terminal_event)

        # Only re-render if hover changed or event was handled
        if hover_changed:
            self.app.needs_render = True

    def _route_key_to_focused_element(self, event: KeyEvent) -> None:
        """Route key events to the currently focused element.

        This allows focused elements to handle keyboard input.
        Called after other handlers have had a chance to process the event.

        Parameters
        ----------
        event : KeyEvent
            Key event to route
        """
        try:
            # Skip if event was cancelled by another handler
            if event.cancelled:
                return

            # Get the focused element
            focused_elem = self.app.focus_manager.get_focused_element()
            if focused_elem is None:
                return

            # Use the original Key object from the event
            # This ensures we use the exact same Key constants that InputHandler created
            if event.key_obj is None:
                return

            key = event.key_obj

            # Let the element handle the key
            handled = focused_elem.handle_key(key)

            if handled:
                # Mark event as handled and trigger re-render
                event.cancel()
                self.app.needs_render = True

        except Exception as e:
            self.app._handle_error("Error routing key to focused element", e)

    def _advance_spinner_frames(self) -> None:
        """Advance animation frames for all active spinners.

        This method iterates through all positioned elements, finds active
        spinners, advances their frame counters, and updates state.
        Called periodically when refresh_interval is set.
        """
        from wijjit.elements.display.spinner import Spinner

        for elem in self.app.positioned_elements:
            if isinstance(elem, Spinner) and elem.active:
                # Advance to next frame
                elem.next_frame()

                # Update frame index in state if element has state dict reference
                if hasattr(elem, "_state_dict") and hasattr(elem, "_frame_key"):
                    try:
                        elem._state_dict[elem._frame_key] = elem.frame_index
                    except Exception as e:
                        # If state update fails, just continue
                        logger.warning(
                            f"Failed to update frame index in state for element: {e}"
                        )
