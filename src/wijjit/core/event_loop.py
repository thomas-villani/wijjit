"""Event loop for Wijjit applications.

This module provides the EventLoop class which handles the main application
event loop including input reading, event dispatching, and rendering.
Supports both synchronous and asynchronous operation with backward compatibility.
"""

from __future__ import annotations

import asyncio
import shutil
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from wijjit.core.events import KeyEvent
from wijjit.logging_config import get_logger
from wijjit.terminal.input import Key, Keys
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
    executor : ThreadPoolExecutor, optional
        Thread pool for running sync handlers off the event loop thread.
        If None, sync handlers run directly on the event loop (blocking).

    Attributes
    ----------
    app : Wijjit
        Application reference
    running : bool
        Whether the event loop is currently running
    executor : ThreadPoolExecutor or None
        Thread pool executor for sync handlers (if configured)
    """

    def __init__(self, app: Wijjit, executor: ThreadPoolExecutor | None = None) -> None:
        """Initialize the event loop.

        Parameters
        ----------
        app : Wijjit
            Reference to the main application
        executor : ThreadPoolExecutor, optional
            Thread pool for running sync handlers. If None, sync handlers
            run directly on event loop thread (may block).
        """
        self.app = app
        self.running = False
        self.executor = executor

        # FPS tracking - use deque with maxlen for O(1) rotation
        self._fps_window_size = 10  # Calculate average over last 10 frames
        self.frame_times: deque[float] = deque(maxlen=self._fps_window_size)
        self.current_fps: float = 0.0

        # Render throttling
        self._last_render_time: float = 0.0

        # Spinner animation timing (separate from refresh_interval)
        # Spinners advance their frames at this interval regardless of refresh_interval
        self._last_spinner_advance_time: float = 0.0
        self._spinner_frame_interval: float = 0.2  # 200ms between frame advances

        # Error recovery
        self._consecutive_errors = 0
        self._max_consecutive_errors = 3  # Terminate after 3 consecutive errors

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
            # Enter alternate screen (if configured)
            if self.app.config["USE_ALTERNATE_SCREEN"]:
                self.app.screen_manager.enter_alternate_buffer()
                logger.debug("Entered alternate screen buffer")

            # Hide cursor for better TUI appearance (if configured)
            if self.app.config["HIDE_CURSOR"]:
                self.app.screen_manager.hide_cursor()
                logger.debug("Hidden cursor")

            # Enable mouse tracking (if configured and not already enabled)
            if (
                self.app.config["ENABLE_MOUSE"]
                and not self.app.input_handler.mouse_enabled
            ):
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
                    # Reset error counter on successful frame
                    self._consecutive_errors = 0
                except KeyboardInterrupt:
                    logger.info("Received KeyboardInterrupt, exiting application")
                    self.running = False
                    break
                except Exception as e:
                    self._consecutive_errors += 1
                    self.app._handle_error(
                        f"Error in event loop (attempt {self._consecutive_errors}/"
                        f"{self._max_consecutive_errors})",
                        e,
                    )
                    # Only terminate after consecutive errors exceed threshold
                    if self._consecutive_errors >= self._max_consecutive_errors:
                        logger.error(
                            f"Too many consecutive errors "
                            f"({self._consecutive_errors}), terminating"
                        )
                        self.running = False
                        break
                    else:
                        logger.warning(
                            f"Attempting recovery after error "
                            f"({self._consecutive_errors}/{self._max_consecutive_errors})"
                        )
                        # Small delay before retry to avoid tight error loops
                        await asyncio.sleep(0.1)

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
            # Shutdown executor if configured
            if self.executor:
                logger.debug("Shutting down executor")
                self.executor.shutdown(wait=True)
                logger.debug("Executor shutdown complete")
            logger.info("Application shutdown complete")

    def stop(self) -> None:
        """Stop the event loop.

        Sets the running flag to False which will cause the event loop
        to exit after the current iteration completes.
        """
        self.running = False

    def _should_render_now(self) -> bool:
        """Check if rendering should happen now based on throttle config.

        Returns
        -------
        bool
            True if render should proceed, False if throttled

        Notes
        -----
        Respects RENDER_THROTTLE_MS config to prevent renders faster than
        the specified threshold.
        """
        throttle_ms = self.app.config.get("RENDER_THROTTLE_MS", 0)

        # No throttling if set to 0
        if throttle_ms <= 0:
            return True

        current_time = time.time()
        time_since_last_render = (current_time - self._last_render_time) * 1000

        # Check if enough time has passed
        if time_since_last_render >= throttle_ms:
            self._last_render_time = current_time
            return True

        return False

    async def _process_frame_async(self) -> None:
        """Process a single frame of the event loop (async).

        This method handles:
        - Auto-refresh for animations
        - Notification expiry
        - Terminal resize detection
        - Input reading and event dispatch
        - Re-rendering when needed
        """
        # Track frame start time for FPS calculation
        frame_start = time.time()

        # Check if auto-refresh is needed (for animations like spinners or notification expiry)
        if self.app.refresh_interval is not None:
            current_time = time.time()
            elapsed = current_time - self.app._last_refresh_time

            if elapsed >= self.app.refresh_interval:
                # Time to refresh - advance spinner frames
                self._advance_spinner_frames()
                # Trigger re-render to show updated animation frames
                self.app.needs_render = True

                # Check for expired notifications (async)
                if await self.app.notification_manager.check_expired_async():
                    self.app.needs_render = True

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

        # Render immediately if needed (before disabling auto-refresh)
        # This ensures the final notification removal is rendered
        if self.app.needs_render and self._should_render_now():
            # Advance spinner frames if enough time has passed
            # This ensures spinners animate even when refresh() is called manually
            current_time = time.time()
            if (
                current_time - self._last_spinner_advance_time
                >= self._spinner_frame_interval
            ):
                self._advance_spinner_frames()
                self._last_spinner_advance_time = current_time

            self.app._render()
            self.app._last_refresh_time = time.time()
            # Yield control to allow other async tasks to run
            await asyncio.sleep(0)

        # Disable auto-refresh if no notifications remain
        # Do this AFTER rendering to ensure the final state is displayed
        if (
            self.app.notification_manager.is_empty()
            and self.app._notification_auto_refresh
        ):
            self.app.refresh_interval = None
            self.app._notification_auto_refresh = False

        # Read input asynchronously - use short timeout if refresh_interval is set
        # This allows animations to run smoothly without requiring user input
        # Use a fallback timeout of 0.5s when refresh_interval is None to support
        # background thread updates via app.refresh()
        if self.app.refresh_interval is not None:
            timeout = self.app.refresh_interval / 2
        else:
            timeout = 0.5  # Fallback: check for pending renders every 0.5s

        input_event = await self.app.input_handler.read_input_async(timeout=timeout)

        if input_event is None:
            # Timeout or error reading input
            # Check if a background thread requested a render
            if self.app.needs_render and self._should_render_now():
                self.app._render()
                self.app._last_refresh_time = time.time()
                # Yield control to allow other async tasks to run
                await asyncio.sleep(0)
            return

        # Check if it's a keyboard event
        if isinstance(input_event, Key):
            await self._handle_key_event_async(input_event)

        # Check if it's a mouse event
        elif isinstance(input_event, TerminalMouseEvent):
            await self._handle_mouse_event_async(input_event)

        # Re-render if needed (with throttling)
        if self.app.needs_render and self._should_render_now():
            self.app._render()
            self.app._last_refresh_time = time.time()
            # Yield control to allow other async tasks to run
            await asyncio.sleep(0)

        # Calculate FPS if enabled
        if self.app.config["SHOW_FPS"]:
            frame_end = time.time()
            frame_time = frame_end - frame_start

            self.frame_times.append(frame_time)
            # deque with maxlen automatically discards oldest entries

            # Calculate average FPS
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0

        # Apply MAX_FPS frame rate limiting
        max_fps = self.app.config.get("MAX_FPS")
        if max_fps is not None and max_fps > 0:
            frame_end = time.time()
            frame_time = frame_end - frame_start
            desired_frame_time = 1.0 / max_fps

            if frame_time < desired_frame_time:
                # Frame completed too quickly, sleep to limit FPS
                sleep_time = desired_frame_time - frame_time
                await asyncio.sleep(sleep_time)

    async def _handle_key_event_async(self, input_event: Key) -> None:
        """Handle a keyboard event (async).

        Parameters
        ----------
        input_event : Key
            The keyboard input event
        """
        # Track overlay count at start to detect if a modal was opened during handling
        # This prevents key leakage (e.g., 'n' key opening dialog AND entering TextInput)
        overlay_count_before = len(self.app.overlay_manager.overlays)

        # Handle quit key (configurable, default Ctrl+Q)
        quit_key = self.app.config["QUIT_KEY"]
        if input_event.name == quit_key:
            logger.info(f"Received {quit_key}, exiting application")
            self.running = False
            return

        # Debug input logging (if configured)
        if self.app.config["DEBUG_INPUT_KEYBOARD"]:
            logger.info(
                f"[DEBUG_INPUT] Key: {input_event.name}, "
                f"modifiers={input_event.modifiers}, "
                f"char={input_event.char!r}"
            )
        else:
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

        # Create key event
        event = KeyEvent(
            key=input_event.name,
            modifiers=input_event.modifiers,
            key_obj=input_event,  # Store original Key object
        )

        # Block global key handlers when a modal with trap_focus is active
        # This prevents hotkeys (like 's', 'e', 'n', etc.) from firing while dialog is open
        # Exception: Tab/Shift+Tab must always be dispatched for focus cycling within modals
        is_tab_key = input_event.name in ("tab", "shift+tab")
        if not self.app.overlay_manager.should_trap_focus() or is_tab_key:
            # No modal trapping focus, OR it's Tab key for focus cycling
            await self.app.handler_registry.dispatch_async(
                event, executor=self.executor
            )
        else:
            # Modal is trapping focus - skip global handlers (except Tab)
            # The overlay's handle_key() already had a chance to process the event above
            logger.debug(
                f"Skipping global key dispatch for '{input_event.name}' - "
                f"focus trapped in overlay"
            )

        # Check if overlay count changed (a modal was opened during handling)
        overlay_count_after = len(self.app.overlay_manager.overlays)
        overlay_added = overlay_count_after > overlay_count_before

        # Route key to focused element if not handled by other handlers
        # Skip if a new overlay was added to prevent key leakage to modal elements
        if not event.cancelled and not overlay_added:
            if self.app.overlay_manager.should_trap_focus():
                # Focus is trapped - only route to focused element if it's in overlay
                focused = self.app.focus_manager.get_focused_element()
                if focused:
                    handled = focused.handle_key(input_event)
                    if handled:
                        self.app.needs_render = True
                    elif self.app.focus_navigation_enabled:
                        # Element didn't handle - check for arrow key focus navigation
                        if input_event == Keys.UP or input_event == Keys.LEFT:
                            self.app.focus_manager.focus_previous()
                            self.app.needs_render = True
                        elif input_event == Keys.DOWN or input_event == Keys.RIGHT:
                            self.app.focus_manager.focus_next()
                            self.app.needs_render = True
            else:
                # Normal focus routing
                self._route_key_to_focused_element(event)
        elif overlay_added:
            logger.debug(
                f"Skipping focused element routing for '{input_event.name}' - "
                f"overlay was added during event handling"
            )

    async def _handle_mouse_event_async(
        self, terminal_event: TerminalMouseEvent
    ) -> None:
        """Handle a mouse event (async).

        Parameters
        ----------
        terminal_event : TerminalMouseEvent
            The mouse event from terminal layer
        """
        # Debug input logging (if configured)
        if self.app.config["DEBUG_INPUT_MOUSE"]:
            logger.info(
                f"[DEBUG_INPUT] Mouse: {terminal_event.type}, "
                f"position=({terminal_event.x}, {terminal_event.y}), "
                f"button={terminal_event.button}"
            )
        else:
            logger.debug(
                f"Mouse event: {terminal_event.type} at ({terminal_event.x}, {terminal_event.y})"
            )

        # Delegate to mouse router (async to support async mouse handlers)
        hover_changed = await self.app.mouse_router.route_mouse_event(terminal_event)

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
                logger.debug(
                    f"Key event {event.key} was cancelled, not routing to focused element"
                )
                return

            # Get the focused element
            focused_elem = self.app.focus_manager.get_focused_element()
            if focused_elem is None:
                # No focused element - check if arrow keys should focus first/last
                if self.app.focus_navigation_enabled and event.key_obj:
                    key = event.key_obj
                    if key == Keys.DOWN or key == Keys.RIGHT:
                        self.app.focus_manager.focus_first()
                        event.cancel()
                        self.app.needs_render = True
                        logger.debug("Arrow key focus: focused first element")
                    elif key == Keys.UP or key == Keys.LEFT:
                        self.app.focus_manager.focus_last()
                        event.cancel()
                        self.app.needs_render = True
                        logger.debug("Arrow key focus: focused last element")
                else:
                    logger.debug("No focused element to route key to")
                return

            logger.debug(
                f"Routing key {event.key} to focused element: "
                f"{focused_elem.id if hasattr(focused_elem, 'id') else type(focused_elem).__name__}"
            )

            # Use the original Key object from the event
            # This ensures we use the exact same Key constants that InputHandler created
            if event.key_obj is None:
                logger.debug("No key_obj in event, cannot route")
                return

            key = event.key_obj

            # Let the element handle the key
            handled = focused_elem.handle_key(key)
            logger.debug(f"Element handled key: {handled}")

            if handled:
                # Mark event as handled and trigger re-render
                event.cancel()
                self.app.needs_render = True
            elif self.app.focus_navigation_enabled:
                # Element didn't handle the key - check for arrow key focus navigation
                if key == Keys.UP or key == Keys.LEFT:
                    self.app.focus_manager.focus_previous()
                    event.cancel()
                    self.app.needs_render = True
                    logger.debug("Arrow key focus: moved to previous element")
                elif key == Keys.DOWN or key == Keys.RIGHT:
                    self.app.focus_manager.focus_next()
                    event.cancel()
                    self.app.needs_render = True
                    logger.debug("Arrow key focus: moved to next element")

        except Exception as e:
            self.app._handle_error("Error routing key to focused element", e)

    def _advance_spinner_frames(self) -> None:
        """Advance animation frames for all active spinners.

        This method iterates through all positioned elements, finds active
        spinners, advances their frame counters, and updates state.
        Called periodically when refresh_interval is set.

        Notes
        -----
        Respects REDUCE_MOTION config - animations are skipped when enabled.
        """
        from wijjit.elements.display.spinner import Spinner

        # Skip frame advancement if REDUCE_MOTION is enabled
        if self.app.config.get("REDUCE_MOTION", False):
            return

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
