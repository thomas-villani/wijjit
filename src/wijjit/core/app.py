"""Main application class for Wijjit TUI framework.

This module provides the central Wijjit application class that orchestrates
all components of the framework:
- State management
- Template rendering
- Event handling and dispatch
- View routing and navigation
- Input handling
- Screen management

The Wijjit class provides a Flask-like API with view decorators and
declarative UI patterns.
"""

import shutil
import sys
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from wijjit.core.events import (
    ActionEvent,
    Event,
    EventType,
    HandlerRegistry,
    HandlerScope,
    KeyEvent,
    MouseEvent,
)
from wijjit.core.focus import FocusManager
from wijjit.core.hover import HoverManager
from wijjit.core.overlay import Overlay
from wijjit.core.renderer import Renderer
from wijjit.core.state import State
from wijjit.elements.base import Element, ScrollableMixin
from wijjit.elements.display.tree import Tree
from wijjit.elements.input.button import Button
from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup
from wijjit.elements.input.radio import Radio, RadioGroup
from wijjit.elements.input.select import Select
from wijjit.elements.input.text import TextInput
from wijjit.logging_config import get_logger
from wijjit.terminal.ansi import ANSIColor, colorize
from wijjit.terminal.input import InputHandler, Key
from wijjit.terminal.mouse import MouseEvent as TerminalMouseEvent
from wijjit.terminal.mouse import MouseEventType
from wijjit.terminal.screen import ScreenManager

# Get logger for this module
logger = get_logger(__name__)


@dataclass
class ViewConfig:
    """Configuration for a view.

    Parameters
    ----------
    name : str
        Unique name for this view
    template : str
        Template string or path to template file
    data : Optional[Callable[..., Dict[str, Any]]]
        Function that returns data dict for template rendering
    on_enter : Optional[Callable[[], None]]
        Hook called when navigating to this view
    on_exit : Optional[Callable[[], None]]
        Hook called when navigating away from this view
    is_default : bool
        Whether this is the default view (shown on startup)

    Attributes
    ----------
    name : str
        Unique name for this view
    template : str
        Template string or path to template file
    data : Optional[Callable[..., Dict[str, Any]]]
        Function that returns data dict for template rendering
    on_enter : Optional[Callable[[], None]]
        Hook called when navigating to this view
    on_exit : Optional[Callable[[], None]]
        Hook called when navigating away from this view
    is_default : bool
        Whether this is the default view
    """

    name: str
    template: str
    data: Callable[..., dict[str, Any]] | None = None
    on_enter: Callable[[], None] | None = None
    on_exit: Callable[[], None] | None = None
    is_default: bool = False


class Wijjit:
    """Main Wijjit application class.

    The Wijjit class is the central orchestrator for TUI applications.
    It provides a Flask-like API with view decorators and manages all
    framework components.

    Parameters
    ----------
    template_dir : Optional[str]
        Directory containing template files (default: None for inline templates)
    initial_state : Optional[Dict[str, Any]]
        Initial state dictionary (default: empty dict)

    Attributes
    ----------
    state : State
        Application state with reactive updates
    renderer : Renderer
        Jinja2 template renderer
    focus_manager : FocusManager
        Focus management for interactive elements
    hover_manager : HoverManager
        Hover state management for mouse interaction
    handler_registry : HandlerRegistry
        Event handler registry and dispatcher
    screen_manager : ScreenManager
        Terminal screen management
    input_handler : InputHandler
        Keyboard and mouse input handling
    views : Dict[str, ViewConfig]
        Registered views
    current_view : Optional[str]
        Name of current view
    running : bool
        Whether the app is currently running
    needs_render : bool
        Whether a re-render is needed

    Examples
    --------
    >>> app = Wijjit()
    >>>
    >>> @app.view("main", default=True)
    ... def main_view():
    ...     return {
    ...         "template": "Hello, World!",
    ...     }
    >>>
    >>> app.run()
    """

    def __init__(
        self,
        template_dir: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ):
        """Initialize Wijjit application.

        Parameters
        ----------
        template_dir : Optional[str]
            Directory containing template files
        initial_state : Optional[Dict[str, Any]]
            Initial state dictionary
        """
        logger.info(
            f"Initializing Wijjit application (template_dir={template_dir}, "
            f"initial_state_keys={list(initial_state.keys()) if initial_state else []})"
        )

        # Initialize state
        self.state = State(initial_state or {})

        # Initialize renderer
        self.renderer = Renderer(template_dir=template_dir)

        # Initialize focus manager
        self.focus_manager = FocusManager()

        # Initialize hover manager
        self.hover_manager = HoverManager()

        # Initialize overlay manager
        from wijjit.core.overlay import OverlayManager

        self.overlay_manager = OverlayManager(self)

        # Initialize event system
        self.handler_registry = HandlerRegistry()

        # Initialize terminal components
        self.screen_manager = ScreenManager()
        self.input_handler = InputHandler()

        # View registry
        self.views: dict[str, ViewConfig] = {}
        self.current_view: str | None = None
        self.current_view_params: dict[str, Any] = {}

        # Application state
        self.running = False
        self.needs_render = True

        # Layout system
        self.positioned_elements = []  # Elements with bounds from layout engine

        # Focus navigation configuration
        self.focus_navigation_enabled = True  # Auto-enabled, can be customized

        # Action handlers
        self._action_handlers: dict[str, Callable] = {}

        # Key handlers
        self._key_handlers: dict[str, Callable] = {}

        # Auto-refresh for animations (e.g., spinners)
        self.refresh_interval: float | None = None  # None = no auto-refresh
        self._last_refresh_time: float = 0.0

        # Terminal size tracking for resize detection
        term_size = shutil.get_terminal_size()
        self._last_terminal_size = (term_size.columns, term_size.lines)

        # Hook state changes to trigger re-render
        self.state.on_change(self._on_state_change)

        # Register built-in Tab navigation handlers
        self.on(
            EventType.KEY,
            self._handle_tab_key,
            scope=HandlerScope.GLOBAL,
            priority=100,  # High priority so it runs early
        )

    def view(
        self,
        name: str,
        default: bool = False,
    ) -> Callable:
        """Decorator to register a view.

        The decorated function should return a dict with:
        - template: str (required) - Template string or file path
        - data: dict (optional) - Data for template rendering
        - on_enter: callable (optional) - Hook for view entry
        - on_exit: callable (optional) - Hook for view exit

        Parameters
        ----------
        name : str
            Unique name for this view
        default : bool
            Whether this is the default view (default: False)

        Returns
        -------
        Callable
            Decorator function

        Examples
        --------
        >>> @app.view("main", default=True)
        ... def main_view():
        ...     return {
        ...         "template": "Hello, {{ name }}!",
        ...         "data": {"name": "World"},
        ...     }
        """

        def decorator(func: Callable) -> Callable:
            # Store the function and create a lazy ViewConfig
            # We'll extract the actual config when the view is first accessed
            view_config = ViewConfig(
                name=name,
                template="",  # Will be set lazily
                data=None,  # Will be set lazily
                on_enter=None,  # Will be set lazily
                on_exit=None,  # Will be set lazily
                is_default=default,
            )

            # Store the original function so we can call it later
            view_config._view_func = func
            view_config._initialized = False

            self.views[name] = view_config

            logger.debug(f"Registered view '{name}' (default={default})")

            # Set as default view if specified
            if default and self.current_view is None:
                self.current_view = name

            return func

        return decorator

    def _initialize_view(self, view_config: ViewConfig) -> None:
        """Initialize a view config by calling its view function.

        This is called lazily the first time a view is accessed.

        Parameters
        ----------
        view_config : ViewConfig
            The view configuration to initialize
        """
        if hasattr(view_config, "_initialized") and view_config._initialized:
            return  # Already initialized

        if hasattr(view_config, "_view_func"):
            # Call the view function ONCE to get the config dict
            config_dict = view_config._view_func()

            # Extract static config components
            view_config.template = config_dict.get("template", "")
            view_config.on_enter = config_dict.get("on_enter")
            view_config.on_exit = config_dict.get("on_exit")

            # Extract data - could be a dict or a callable
            data_value = config_dict.get("data", {})

            if callable(data_value):
                # User provided a data callback - use it directly
                view_config.data = data_value
            else:
                # User provided static data dict - wrap in lambda
                def data_func(**kwargs):
                    return data_value

                view_config.data = data_func

            view_config._initialized = True

    def navigate(self, view_name: str, **params) -> None:
        """Navigate to a different view.

        Calls on_exit hook of current view, switches to new view,
        and calls on_enter hook of new view.

        Parameters
        ----------
        view_name : str
            Name of view to navigate to
        **params
            Parameters to pass to the view's data function

        Raises
        ------
        ValueError
            If view_name doesn't exist
        """
        if view_name not in self.views:
            logger.error(f"Navigation failed: view '{view_name}' not found")
            raise ValueError(f"View '{view_name}' not found")

        logger.info(
            f"Navigating from '{self.current_view}' to '{view_name}' "
            f"(params={list(params.keys())})"
        )

        # Initialize the new view
        self._initialize_view(self.views[view_name])

        # Call current view's on_exit hook
        if self.current_view and self.current_view in self.views:
            current = self.views[self.current_view]
            self._initialize_view(current)
            if current.on_exit:
                try:
                    current.on_exit()
                except Exception as e:
                    self._handle_error(
                        f"Error in on_exit for view '{self.current_view}'", e
                    )

            # Clear view-scoped handlers
            self.handler_registry.clear_view(self.current_view)

        # Switch to new view
        self.current_view = view_name
        self.current_view_params = params
        self.handler_registry.current_view = view_name

        # Call new view's on_enter hook
        new_view = self.views[view_name]
        if new_view.on_enter:
            try:
                new_view.on_enter()
            except Exception as e:
                self._handle_error(f"Error in on_enter for view '{view_name}'", e)

        # Trigger re-render
        self.needs_render = True

    def on(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        scope: HandlerScope = HandlerScope.GLOBAL,
        view_name: str | None = None,
        element_id: str | None = None,
        priority: int = 0,
    ) -> None:
        """Register an event handler.

        Parameters
        ----------
        event_type : EventType
            Type of event to handle
        callback : Callable[[Event], None]
            Function to call when event occurs
        scope : HandlerScope
            Scope at which handler operates (default: GLOBAL)
        view_name : Optional[str]
            View name for view-scoped handlers
        element_id : Optional[str]
            Element ID for element-scoped handlers
        priority : int
            Handler priority (higher = earlier, default: 0)
        """
        self.handler_registry.register(
            callback=callback,
            scope=scope,
            event_type=event_type,
            view_name=view_name,
            element_id=element_id,
            priority=priority,
        )

    def on_key(self, key: str) -> Callable:
        """Decorator to register a key press handler.

        Use this to handle specific key presses globally in your application.

        Parameters
        ----------
        key : str
            The key to handle (e.g., "d", "q", "enter", "space")

        Returns
        -------
        Callable
            Decorator function

        Examples
        --------
        >>> @app.on_key("d")
        ... def delete_handler(event):
        ...     print("Delete key pressed!")
        """

        def decorator(func: Callable) -> Callable:
            self._key_handlers[key.lower()] = func
            return func

        return decorator

    def on_action(self, action_id: str) -> Callable:
        """Decorator to register an action handler.

        Use this to handle actions from buttons and other interactive elements
        that have an 'action' attribute in templates.

        Parameters
        ----------
        action_id : str
            The action ID to handle

        Returns
        -------
        Callable
            Decorator function

        Examples
        --------
        >>> @app.on_action("submit")
        ... def handle_submit(event):
        ...     print("Form submitted!")
        """

        def decorator(func: Callable) -> Callable:
            self._action_handlers[action_id] = func
            return func

        return decorator

    def configure_focus(self, enabled: bool = True) -> None:
        """Configure focus navigation behavior.

        By default, Tab/Shift+Tab navigation is automatically enabled when
        template contains focusable elements. Use this method to disable
        or re-enable focus navigation.

        Parameters
        ----------
        enabled : bool
            Whether to enable Tab/Shift+Tab navigation (default: True)

        Examples
        --------
        >>> app.configure_focus(enabled=False)  # Disable Tab navigation
        """
        self.focus_navigation_enabled = enabled

    def quit(self) -> None:
        """Quit the application.

        Sets the running flag to False, which will exit the event loop.
        """
        self.running = False

    def refresh(self) -> None:
        """Force a re-render on the next loop iteration."""
        self.needs_render = True

    def run(self) -> None:
        """Run the application.

        Enters the main event loop:
        1. Render initial view
        2. Loop: read input -> dispatch events -> re-render if needed
        3. Exit on quit or Ctrl+C

        The loop continues until quit() is called or the user presses Ctrl+C.
        """
        logger.info("Starting Wijjit application")

        # Find default view if current_view not set
        if self.current_view is None:
            for name, view in self.views.items():
                if view.is_default:
                    self.current_view = name
                    logger.debug(f"Selected default view: '{name}'")
                    break

        if self.current_view is None and self.views:
            # Use first registered view as fallback
            self.current_view = next(iter(self.views.keys()))
            logger.debug(f"No default view, using first view: '{self.current_view}'")

        if self.current_view is None:
            logger.error("No views registered")
            raise RuntimeError(
                "No views registered. Use @app.view() to register a view."
            )

        # Initialize and call on_enter for initial view
        initial_view = self.views[self.current_view]
        self._initialize_view(initial_view)

        # Set current view in handler registry so view-scoped handlers work
        self.handler_registry.current_view = self.current_view

        if initial_view.on_enter:
            try:
                initial_view.on_enter()
            except Exception as e:
                self._handle_error(
                    f"Error in on_enter for view '{self.current_view}'", e
                )

        self.running = True

        try:
            # Enter alternate screen
            self.screen_manager.enter_alternate_buffer()
            logger.debug("Entered alternate screen buffer")

            # Hide cursor for better TUI appearance
            self.screen_manager.hide_cursor()
            logger.debug("Hidden cursor")

            # Enable mouse tracking
            self.input_handler.enable_mouse_tracking()
            logger.debug("Enabled mouse tracking")

            # Render initial view
            logger.info(f"Rendering initial view: '{self.current_view}'")
            self._render()
            self._last_refresh_time = time.time()

            logger.info("Entering main event loop")
            # Main event loop
            while self.running:
                try:
                    # Check if auto-refresh is needed (for animations like spinners)
                    if self.refresh_interval is not None:
                        current_time = time.time()
                        elapsed = current_time - self._last_refresh_time

                        if elapsed >= self.refresh_interval:
                            # Time to refresh - advance spinner frames and re-render
                            self._advance_spinner_frames()
                            self.needs_render = True
                            self._last_refresh_time = current_time

                    # Check for terminal resize
                    term_size = shutil.get_terminal_size()
                    current_size = (term_size.columns, term_size.lines)
                    if current_size != self._last_terminal_size:
                        logger.debug(
                            f"Terminal resized from {self._last_terminal_size} to {current_size}"
                        )
                        # Recalculate overlay positions
                        self.overlay_manager.recalculate_centered_overlays(
                            term_size.columns, term_size.lines
                        )
                        self._last_terminal_size = current_size
                        self.needs_render = True

                    # Read input - use short timeout if refresh_interval is set
                    # This allows animations to run smoothly
                    # Note: InputHandler.read_input() is blocking, so we check refresh
                    # timing before reading. For smooth animations, refresh_interval
                    # should be small (e.g., 0.1 seconds)
                    input_event = self.input_handler.read_input()

                    if input_event is None:
                        # Error reading input, continue
                        # But still check if refresh is needed
                        if self.needs_render:
                            self._render()
                            self._last_refresh_time = time.time()
                        continue

                    # Check if it's a keyboard event
                    if isinstance(input_event, Key):
                        # Handle Ctrl+C
                        if input_event.is_ctrl_c:
                            logger.info("Received Ctrl+C, exiting application")
                            self.running = False
                            break

                        logger.debug(
                            f"Key event: {input_event.name} "
                            f"(modifiers={input_event.modifiers})"
                        )

                        # Check for ESC key to close overlays
                        if input_event.name == "escape":
                            if self.overlay_manager.handle_escape():
                                # Overlay was closed, trigger re-render
                                self.needs_render = True
                                continue  # Don't process event further

                        # Create and dispatch key event
                        event = KeyEvent(
                            key=input_event.name,
                            modifiers=input_event.modifiers,
                            key_obj=input_event,  # Store original Key object
                        )
                        self.handler_registry.dispatch(event)

                        # Check for registered key handlers
                        if not event.cancelled:
                            key_name = (
                                input_event.name.lower() if input_event.name else ""
                            )
                            if key_name in self._key_handlers:
                                try:
                                    self._key_handlers[key_name](event)
                                    self.needs_render = True
                                except Exception as e:
                                    logger.error(
                                        f"Error in key handler for '{key_name}': {e}",
                                        exc_info=True,
                                    )

                        # Route key to focused element if not handled by other handlers
                        # If focus is trapped in an overlay, only route to overlay elements
                        if not event.cancelled:
                            if self.overlay_manager.should_trap_focus():
                                # Focus is trapped - only route to focused element if it's in overlay
                                focused = self.focus_manager.get_focused_element()
                                if focused:
                                    handled = focused.handle_key(input_event)
                                    if handled:
                                        self.needs_render = True
                            else:
                                # Normal focus routing
                                self._route_key_to_focused_element(event)

                    # Check if it's a mouse event
                    elif isinstance(input_event, TerminalMouseEvent):
                        logger.debug(
                            f"Mouse event: {input_event.type} at "
                            f"({input_event.x}, {input_event.y})"
                        )
                        # Handle mouse event
                        hover_changed = self._handle_mouse_event(input_event)

                        # Only re-render if hover changed or event was handled
                        if hover_changed:
                            self.needs_render = True

                    # Re-render if needed
                    if self.needs_render:
                        self._render()
                        self._last_refresh_time = time.time()

                except KeyboardInterrupt:
                    logger.info("Received KeyboardInterrupt, exiting application")
                    self.running = False
                    break
                except Exception as e:
                    self._handle_error("Error in event loop", e)
                    # Critical error - exit the loop
                    self.running = False
                    break

        finally:
            logger.info("Exiting application, cleaning up")
            # Show cursor before exiting
            self.screen_manager.show_cursor()
            logger.debug("Shown cursor")
            # Always exit alternate screen on cleanup
            self.screen_manager.exit_alternate_buffer()
            logger.debug("Exited alternate screen buffer")
            # Close input handler to exit raw mode
            self.input_handler.close()
            logger.debug("Closed input handler")
            logger.info("Application shutdown complete")

    def _render(self) -> None:
        """Render the current view to the screen.

        This is an internal method called by the event loop.
        It renders the current view's template with data and displays it.
        """
        if self.current_view is None or self.current_view not in self.views:
            logger.warning("Render skipped: no current view")
            return

        logger.debug(f"Rendering view: '{self.current_view}'")
        view = self.views[self.current_view]
        self._initialize_view(view)

        try:
            # Get data for template
            data = {}
            if view.data:
                data = view.data(**self.current_view_params)

            # Add state to template context
            data["state"] = self.state

            # Check if template has layout tags
            has_layout = self._has_layout_tags(view.template)
            logger.debug(f"View has layout tags: {has_layout}")

            if has_layout:
                # Get the currently focused element ID (if any) from FocusManager
                focused_id = None
                focused_elem = self.focus_manager.get_focused_element()
                if focused_elem and hasattr(focused_elem, "id"):
                    focused_id = focused_elem.id

                # Check if this is the first render (no focused element yet)
                first_render = focused_id is None

                # Pass focused ID and context to renderer so template extensions
                # can create elements with correct focus state from the start
                self.renderer.add_global("_wijjit_current_context", data)
                self.renderer.add_global("_wijjit_focused_id", focused_id)

                # Render with layout (elements will be created with correct focus state)
                term_size = shutil.get_terminal_size()
                output, elements, layout_ctx = self.renderer.render_with_layout(
                    view.template,
                    context=data,
                    width=term_size.columns,
                    height=term_size.lines,
                    overlay_manager=self.overlay_manager,
                )

                # Store elements and update focus manager
                # (but don't update focus manager if focus is trapped in an overlay)
                self.positioned_elements = elements
                if not self.overlay_manager.should_trap_focus():
                    self._update_focus_manager(elements)

                # If this was the first render, re-render with focus now set
                if (
                    first_render
                    and self.focus_manager.get_focused_element() is not None
                ):
                    # Get newly focused element ID
                    focused_elem = self.focus_manager.get_focused_element()
                    if focused_elem and hasattr(focused_elem, "id"):
                        focused_id = focused_elem.id

                    # Render again with focused element
                    self.renderer.add_global("_wijjit_focused_id", focused_id)
                    output, elements, layout_ctx = self.renderer.render_with_layout(
                        view.template,
                        context=data,
                        width=term_size.columns,
                        height=term_size.lines,
                        overlay_manager=self.overlay_manager,
                    )
                    self.positioned_elements = elements

                # Clean up globals
                self.renderer.add_global("_wijjit_current_context", None)
                self.renderer.add_global("_wijjit_focused_id", None)

                # Process template-declared overlays from layout context
                # Remove any template-declared overlays that are no longer visible
                # and add new ones based on current template state
                self._sync_template_overlays(layout_ctx)

                # Wire up element callbacks for actions and state binding
                self._wire_element_callbacks(self.positioned_elements)
            else:
                # Use simple string rendering for non-layout templates
                output = self.renderer.render_string(view.template, context=data)
                # Note: positioned_elements may have been set by the view for manual
                # element positioning. Don't clear it - preserve what the view set.
                # Wire up element callbacks if elements were positioned
                if self.positioned_elements:
                    self._wire_element_callbacks(self.positioned_elements)

            # Composite overlays if any are active
            if self.overlay_manager.overlays:
                term_size = shutil.get_terminal_size()
                overlay_elements = self.overlay_manager.get_overlay_elements()
                apply_dimming = self.overlay_manager.has_dimmed_overlay()

                output = self.renderer.composite_overlays(
                    output,
                    overlay_elements,
                    term_size.columns,
                    term_size.lines,
                    apply_dimming=apply_dimming,
                )

            # Clear screen and display output
            # Ensure output ends with RESET to clear any lingering formatting (e.g., DIM from backdrop)
            from wijjit.terminal.ansi import ANSIStyle

            if not output.endswith(ANSIStyle.RESET):
                output += ANSIStyle.RESET

            self.screen_manager.clear()
            self.screen_manager.move_cursor(1, 1)
            # Handle encoding for Windows console
            try:
                print(output, end="", flush=True)
            except UnicodeEncodeError:
                # Fall back to encoding with error handling
                import sys

                sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))
                sys.stdout.flush()

            self.needs_render = False

        except Exception as e:
            self._handle_error(f"Error rendering view '{self.current_view}'", e)

    def _on_state_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle state changes.

        Called automatically when state is modified. Triggers a re-render.

        Parameters
        ----------
        key : str
            State key that changed
        old_value : Any
            Previous value
        new_value : Any
            New value
        """
        self.needs_render = True

    def _has_layout_tags(self, template: str) -> bool:
        """Check if template contains layout tags.

        Parameters
        ----------
        template : str
            Template string to check

        Returns
        -------
        bool
            True if template has layout tags
        """
        layout_tags = ["{% vstack", "{% hstack", "{% frame"]
        return any(tag in template for tag in layout_tags)

    def _update_focus_manager(self, elements: list) -> None:
        """Update focus manager with positioned elements.

        Parameters
        ----------
        elements : list
            List of elements with bounds
        """
        # Collect focusable elements
        focusable_elements = [
            elem
            for elem in elements
            if hasattr(elem, "focusable") and elem.focusable and elem.bounds
        ]

        # Update focus manager with all focusable elements
        self.focus_manager.set_elements(focusable_elements)

    def _sync_template_overlays(self, layout_ctx: Any) -> None:
        """Synchronize template-declared overlays with overlay manager.

        This method processes overlays declared in templates (via {% overlay %},
        {% modal %}, {% confirmdialog %}, etc.) and syncs them with the overlay
        manager, while preserving programmatically-created overlays.

        Parameters
        ----------
        layout_ctx : LayoutContext
            Layout context containing overlay information from template rendering
        """
        from wijjit.core.overlay import LayerType

        # Get template-declared overlays from layout context
        template_overlays = getattr(layout_ctx, "_overlays", [])

        # Build set of template overlay element IDs for tracking
        template_overlay_ids = {
            id(overlay_info["element"]) for overlay_info in template_overlays
        }

        # Remove template-declared overlays that are no longer in the template
        # (but keep programmatic overlays)
        if not hasattr(self, "_template_overlay_ids"):
            self._template_overlay_ids = set()

        overlays_to_remove = []
        for overlay in self.overlay_manager.overlays:
            overlay_id = id(overlay.element)
            # If this was a template overlay but is no longer in the new template
            if (
                overlay_id in self._template_overlay_ids
                and overlay_id not in template_overlay_ids
            ):
                overlays_to_remove.append(overlay)

        for overlay in overlays_to_remove:
            self.overlay_manager.pop(overlay)

        # Add new template-declared overlays
        for overlay_info in template_overlays:
            element = overlay_info["element"]
            overlay_id = id(element)

            # Skip if already added
            if any(id(o.element) == overlay_id for o in self.overlay_manager.overlays):
                continue

            # Push overlay to manager
            self.overlay_manager.push(
                element=element,
                layer_type=overlay_info.get("layer_type", LayerType.MODAL),
                close_on_escape=overlay_info.get("close_on_escape", True),
                close_on_click_outside=overlay_info.get("close_on_click_outside", True),
                trap_focus=overlay_info.get("trap_focus", False),
                dimmed_background=overlay_info.get("dim_background", False),
            )

        # Update tracking set
        self._template_overlay_ids = template_overlay_ids

    def _wire_element_callbacks(self, elements: list) -> None:
        """Wire up element callbacks for actions and state binding.

        Parameters
        ----------
        elements : list
            List of positioned elements
        """

        for elem in elements:
            # Wire up action callbacks for buttons
            if isinstance(elem, Button) and hasattr(elem, "action") and elem.action:
                action_id = elem.action
                elem.on_activate = lambda aid=action_id: self._dispatch_action(aid)

            # Wire up TextInput callbacks
            if isinstance(elem, TextInput):
                # Wire up action callback if action is specified
                if hasattr(elem, "action") and elem.action:
                    action_id = elem.action
                    elem.on_action = lambda aid=action_id: self._dispatch_action(aid)

                # Wire up state binding if enabled
                if hasattr(elem, "bind") and elem.bind and elem.id:
                    # Initialize element value from state if key exists
                    if elem.id in self.state:
                        elem.value = str(self.state[elem.id])
                        elem.cursor_pos = len(elem.value)

                    # Set up two-way binding
                    elem_id = elem.id

                    def on_change_handler(old_val, new_val, eid=elem_id):
                        # Update state when element changes
                        self.state[eid] = new_val

                    elem.on_change = on_change_handler

            # Wire up Select callbacks
            if isinstance(elem, Select):
                # Wire up action callback if action is specified
                if hasattr(elem, "action") and elem.action:
                    action_id = elem.action
                    elem.on_action = lambda aid=action_id: self._dispatch_action(aid)

                # Wire up state binding if enabled
                if hasattr(elem, "bind") and elem.bind and elem.id:
                    # Initialize element value from state if key exists
                    if elem.id in self.state:
                        elem.value = self.state[elem.id]
                        # Update selected_index to match the value
                        elem.selected_index = elem._find_option_index(elem.value)

                    # Set up two-way binding
                    elem_id = elem.id

                    def on_change_handler(old_val, new_val, eid=elem_id):
                        # Update state when element changes
                        self.state[eid] = new_val

                    elem.on_change = on_change_handler

                # Wire up highlighted_index persistence if element has the state key
                if hasattr(elem, "highlight_state_key") and elem.highlight_state_key:
                    highlight_key = elem.highlight_state_key

                    def on_highlight_handler(new_index, hkey=highlight_key):
                        # Update state when highlight changes
                        self.state[hkey] = new_index

                    elem.on_highlight_change = on_highlight_handler

            # Wire up scroll position persistence for all ScrollableMixin elements
            if isinstance(elem, ScrollableMixin):
                if hasattr(elem, "scroll_state_key") and elem.scroll_state_key:
                    scroll_key = elem.scroll_state_key

                    def on_scroll_handler(position, skey=scroll_key):
                        # Update state when scroll position changes
                        self.state[skey] = position

                    elem.on_scroll = on_scroll_handler

            # Wire up Tree callbacks
            if isinstance(elem, Tree):
                # Wire up action callback if action is specified
                if hasattr(elem, "action") and elem.action:
                    action_id = elem.action

                    def on_select_handler(node, aid=action_id):
                        # Dispatch action with node data
                        self._dispatch_action(aid, data=node)

                    elem.on_select = on_select_handler

            # Wire up Checkbox callbacks
            if isinstance(elem, Checkbox):
                # Wire up action callback if action is specified
                if hasattr(elem, "action") and elem.action:
                    action_id = elem.action
                    elem.on_action = lambda aid=action_id: self._dispatch_action(aid)

                # Wire up state binding if enabled
                if hasattr(elem, "bind") and elem.bind and elem.id:
                    # Initialize element checked state from state if key exists
                    if elem.id in self.state:
                        elem.checked = bool(self.state[elem.id])

                    # Set up two-way binding
                    elem_id = elem.id

                    def on_change_handler(old_val, new_val, eid=elem_id):
                        # Update state when element changes
                        self.state[eid] = new_val

                    elem.on_change = on_change_handler

            # Wire up Radio callbacks
            if isinstance(elem, Radio):
                # Wire up action callback if action is specified
                if hasattr(elem, "action") and elem.action:
                    action_id = elem.action
                    elem.on_action = lambda aid=action_id: self._dispatch_action(aid)

                # Wire up state binding if enabled (bind to group name, not id)
                if hasattr(elem, "bind") and elem.bind and elem.name:
                    # Initialize element checked state from state[name]
                    if elem.name in self.state:
                        elem.checked = self.state[elem.name] == elem.value

                    # Set up two-way binding
                    radio_name = elem.name
                    radio_value = elem.value

                    def on_change_handler(
                        old_val, new_val, rname=radio_name, rval=radio_value
                    ):
                        # Update state when radio is selected
                        if (
                            new_val
                        ):  # Only update state when radio is selected (not deselected)
                            self.state[rname] = rval

                    elem.on_change = on_change_handler

            # Wire up CheckboxGroup callbacks
            if isinstance(elem, CheckboxGroup):
                # Wire up action callback if action is specified
                if hasattr(elem, "action") and elem.action:
                    action_id = elem.action
                    elem.on_action = lambda aid=action_id: self._dispatch_action(aid)

                # Wire up state binding if enabled
                if hasattr(elem, "bind") and elem.bind and elem.id:
                    # Initialize element selected values from state if key exists
                    if elem.id in self.state:
                        elem.selected_values = set(self.state[elem.id])

                    # Set up two-way binding
                    elem_id = elem.id

                    def on_change_handler(old_val, new_val, eid=elem_id):
                        # Update state when element changes
                        self.state[eid] = new_val

                    elem.on_change = on_change_handler

                # Wire up highlighted_index persistence if element has the state key
                if hasattr(elem, "highlight_state_key") and elem.highlight_state_key:
                    highlight_key = elem.highlight_state_key

                    def on_highlight_handler(new_index, hkey=highlight_key):
                        # Update state when highlight changes
                        self.state[hkey] = new_index

                    elem.on_highlight_change = on_highlight_handler

            # Wire up RadioGroup callbacks
            if isinstance(elem, RadioGroup):
                # Wire up action callback if action is specified
                if hasattr(elem, "action") and elem.action:
                    action_id = elem.action
                    elem.on_action = lambda aid=action_id: self._dispatch_action(aid)

                # Wire up state binding if enabled (bind to group name)
                if hasattr(elem, "bind") and elem.bind and elem.name:
                    # Initialize element selected value from state[name]
                    if elem.name in self.state:
                        elem.selected_value = self.state[elem.name]
                        elem.selected_index = elem._find_option_index(
                            elem.selected_value
                        )

                    # Set up two-way binding
                    group_name = elem.name

                    def on_change_handler(old_val, new_val, gname=group_name):
                        # Update state when element changes
                        self.state[gname] = new_val

                    elem.on_change = on_change_handler

                # Wire up highlighted_index persistence if element has the state key
                if hasattr(elem, "highlight_state_key") and elem.highlight_state_key:
                    highlight_key = elem.highlight_state_key

                    def on_highlight_handler(new_index, hkey=highlight_key):
                        # Update state when highlight changes
                        self.state[hkey] = new_index

                    elem.on_highlight_change = on_highlight_handler

    def _handle_tab_key(self, event: KeyEvent) -> None:
        """Handle Tab/Shift+Tab for focus navigation.

        This is a built-in handler registered at high priority to provide
        automatic Tab navigation between focusable elements.

        Parameters
        ----------
        event : KeyEvent
            Key event to handle
        """
        if not self.focus_navigation_enabled:
            return

        # Handle Tab and Shift+Tab
        if event.key == "tab":
            self.focus_manager.focus_next()
            event.cancel()
            self.needs_render = True
        elif event.key == "shift+tab":
            self.focus_manager.focus_previous()
            event.cancel()
            self.needs_render = True

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
            focused_elem = self.focus_manager.get_focused_element()
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
                self.needs_render = True

        except Exception as e:
            self._handle_error("Error routing key to focused element", e)

    def _handle_mouse_event(self, terminal_event: TerminalMouseEvent) -> bool:
        """Handle a mouse event.

        Finds the element at mouse coordinates, updates hover state,
        and dispatches the event to the element and handler registry.

        Parameters
        ----------
        terminal_event : TerminalMouseEvent
            The mouse event from terminal layer

        Returns
        -------
        bool
            True if hover state changed (indicating need for re-render)
        """
        try:
            # Check overlays first (highest z-index)
            overlay = self.overlay_manager.get_at_position(
                terminal_event.x, terminal_event.y
            )

            if overlay:
                # Mouse event is on an overlay - route to overlay element
                if hasattr(overlay.element, "handle_mouse"):
                    handled = overlay.element.handle_mouse(terminal_event)
                    if handled:
                        self.needs_render = True
                        return False  # Hover didn't change base UI
                # Overlay consumed the event even if not handled
                return False
            else:
                # Click outside all overlays - check if should close any
                if terminal_event.type in (
                    MouseEventType.CLICK,
                    MouseEventType.DOUBLE_CLICK,
                ):
                    closed = self.overlay_manager.handle_click_outside(
                        terminal_event.x, terminal_event.y
                    )
                    if closed:
                        return False  # Overlay was closed, don't process further

            # Fall through to base UI handling
            # Find element at mouse coordinates
            target_element = self._find_element_at(terminal_event.x, terminal_event.y)

            # Track whether hover changed
            hover_changed = False

            # Update hover state (only on move/click, not on scroll)
            if terminal_event.type in (
                MouseEventType.MOVE,
                MouseEventType.CLICK,
                MouseEventType.DOUBLE_CLICK,
                MouseEventType.PRESS,
                MouseEventType.RELEASE,
                MouseEventType.DRAG,
            ):
                # Set hovered element (returns True if changed)
                hover_changed = self.hover_manager.set_hovered(target_element)

            # Focus element on click if it's focusable
            if terminal_event.type in (
                MouseEventType.CLICK,
                MouseEventType.DOUBLE_CLICK,
            ):
                if (
                    target_element
                    and hasattr(target_element, "focusable")
                    and target_element.focusable
                ):
                    focus_changed = self.focus_manager.focus_element(target_element)
                    if focus_changed:
                        self.needs_render = True

            # Create core MouseEvent for handler registry
            mouse_event = MouseEvent(
                mouse_event=terminal_event,
                element_id=(
                    target_element.id
                    if target_element and hasattr(target_element, "id")
                    else None
                ),
            )

            # Dispatch through handler registry
            self.handler_registry.dispatch(mouse_event)

            # If event was cancelled, we're done
            if mouse_event.cancelled:
                return hover_changed

            # Dispatch to target element if it exists
            handled = False
            if target_element and hasattr(target_element, "handle_mouse"):
                handled = target_element.handle_mouse(terminal_event)
                if handled:
                    # Element handled the event, trigger re-render
                    self.needs_render = True

            # If scroll event wasn't handled and element has a scrollable parent, try parent
            if (
                not handled
                and terminal_event.type == MouseEventType.SCROLL
                and target_element
                and hasattr(target_element, "parent_frame")
                and target_element.parent_frame is not None
            ):
                parent = target_element.parent_frame
                if hasattr(parent, "handle_mouse"):
                    handled = parent.handle_mouse(terminal_event)
                    if handled:
                        self.needs_render = True

            return hover_changed

        except Exception as e:
            self._handle_error("Error handling mouse event", e)
            return False

    def _find_element_at(self, x: int, y: int):
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
        # Search in reverse order (top-to-bottom)
        for elem in reversed(self.positioned_elements):
            if elem.bounds and elem.bounds.contains_point(x, y):
                return elem
        return None

    def _dispatch_action(self, action_id: str, data: Any = None) -> None:
        """Dispatch an action event to registered action handlers.

        Parameters
        ----------
        action_id : str
            The action ID to dispatch
        data : Any, optional
            Additional data to include with the action event
        """
        if action_id in self._action_handlers:
            logger.info(f"Dispatching action: '{action_id}' (data={data})")
            # Create action event with optional data
            action_event = ActionEvent(action_id=action_id, data=data)

            # Call the handler
            try:
                self._action_handlers[action_id](action_event)
            except Exception as e:
                self._handle_error(f"Error in action handler '{action_id}'", e)

            # Trigger re-render if needed
            self.needs_render = True
        else:
            logger.warning(f"Action handler not found: '{action_id}'")

    def _advance_spinner_frames(self) -> None:
        """Advance animation frames for all active spinners.

        This method iterates through all positioned elements, finds active
        spinners, advances their frame counters, and updates state.
        Called periodically when refresh_interval is set.
        """
        from wijjit.elements.display.spinner import Spinner

        for elem in self.positioned_elements:
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

    def show_modal(
        self,
        element: Element,
        on_close: Callable[[], None] | None = None,
        dim_background: bool = True,
        close_on_escape: bool = True,
        close_on_click_outside: bool = False,
    ) -> Overlay:
        """Show a modal dialog overlay.

        Modals trap focus and typically dim the background. They are used for
        important interactions that require user attention.

        Parameters
        ----------
        element : Element
            The element to display as a modal (typically a Frame with content)
        on_close : Callable, optional
            Callback to invoke when modal is closed
        dim_background : bool
            Whether to dim the background behind the modal (default: True)
        close_on_escape : bool
            Whether ESC key closes the modal (default: True)
        close_on_click_outside : bool
            Whether clicking outside closes the modal (default: False)

        Returns
        -------
        Overlay
            The created overlay object. Can be used to manually close via
            overlay_manager.pop(overlay)

        Examples
        --------
        Show a confirmation dialog:

            from wijjit.elements.overlay import ConfirmDialog

            def on_confirm():
                state.file_deleted = True

            dialog = ConfirmDialog(
                title="Confirm Delete",
                message="Are you sure?",
                on_confirm=on_confirm
            )
            app.show_modal(dialog)
        """
        from wijjit.core.overlay import LayerType

        return self.overlay_manager.push(
            element,
            LayerType.MODAL,
            close_on_click_outside=close_on_click_outside,
            close_on_escape=close_on_escape,
            trap_focus=True,
            dimmed_background=dim_background,
            on_close=on_close,
        )

    def show_dropdown(
        self,
        element: Element,
        x: int,
        y: int,
        on_close: Callable[[], None] | None = None,
        close_on_click_outside: bool = True,
        close_on_escape: bool = True,
    ) -> "Overlay":
        """Show a dropdown menu or context menu overlay.

        Dropdowns appear at a specific position (typically below a button or
        at cursor position for context menus). They close when clicking outside
        or pressing ESC.

        Parameters
        ----------
        element : Element
            The element to display as a dropdown (typically a Menu)
        x : int
            X position for the dropdown
        y : int
            Y position for the dropdown
        on_close : Callable, optional
            Callback to invoke when dropdown is closed
        close_on_click_outside : bool
            Whether clicking outside closes the dropdown (default: True)
        close_on_escape : bool
            Whether ESC key closes the dropdown (default: True)

        Returns
        -------
        Overlay
            The created overlay object

        Examples
        --------
        Show a dropdown menu below a button:

            from wijjit.elements.overlay import DropdownMenu

            button = app.get_element("menu_button")
            menu = DropdownMenu(items=[
                {"label": "Open", "action": "open"},
                {"label": "Save", "action": "save"},
            ])

            app.show_dropdown(
                menu,
                x=button.bounds.x,
                y=button.bounds.y + button.bounds.height
            )
        """
        from wijjit.core.overlay import LayerType

        # Set element position
        if element.bounds is None:
            from wijjit.layout.bounds import Bounds

            # Estimate size (will be rendered at specified position)
            element.bounds = Bounds(x=x, y=y, width=20, height=5)
        else:
            element.bounds.x = x
            element.bounds.y = y

        return self.overlay_manager.push(
            element,
            LayerType.DROPDOWN,
            close_on_click_outside=close_on_click_outside,
            close_on_escape=close_on_escape,
            trap_focus=False,
            dimmed_background=False,
            on_close=on_close,
        )

    def show_tooltip(
        self,
        element: Element,
        x: int,
        y: int,
        close_on_click_outside: bool = True,
    ) -> "Overlay":
        """Show a tooltip overlay.

        Tooltips appear at a specific position (typically near the cursor or
        element being hovered). They don't trap focus and typically close
        automatically when the mouse moves.

        Parameters
        ----------
        element : Element
            The element to display as a tooltip (typically a small Frame)
        x : int
            X position for the tooltip
        y : int
            Y position for the tooltip
        close_on_click_outside : bool
            Whether clicking outside closes the tooltip (default: True)

        Returns
        -------
        Overlay
            The created overlay object

        Notes
        -----
        Tooltips don't close on ESC by default since they're meant to be
        unobtrusive and auto-close on mouse movement.

        Examples
        --------
        Show a tooltip on hover:

            from wijjit.elements.overlay import Tooltip

            tooltip = Tooltip(text="Click to open file")
            app.show_tooltip(tooltip, x=mouse_x + 1, y=mouse_y + 1)
        """
        from wijjit.core.overlay import LayerType

        # Set element position
        if element.bounds is None:
            from wijjit.layout.bounds import Bounds

            element.bounds = Bounds(x=x, y=y, width=30, height=3)
        else:
            element.bounds.x = x
            element.bounds.y = y

        return self.overlay_manager.push(
            element,
            LayerType.TOOLTIP,
            close_on_click_outside=close_on_click_outside,
            close_on_escape=False,  # Tooltips don't close on ESC
            trap_focus=False,
            dimmed_background=False,
            on_close=None,
        )

    def _handle_error(self, message: str, exception: Exception) -> None:
        """Handle errors during app execution.

        Logs error message but doesn't crash the app.

        Parameters
        ----------
        message : str
            Error message context
        exception : Exception
            The exception that occurred
        """
        # Log the error with full traceback
        try:
            logger.error(
                f"{message}: {str(exception)}\n{traceback.format_exc()}",
                exc_info=True,
            )
            # Also print to stderr for immediate visibility (can be disabled by user)
            error_text = f"\n{message}: {str(exception)}\n"
            error_text += traceback.format_exc()
            print(colorize(error_text, color=ANSIColor.RED), file=sys.stderr)
        except Exception as e:
            # If error handling itself fails, log basic error
            logger.error(f"Error handling failed: {message}: {str(exception)}: {e}")
            print(f"\nError: {message}: {str(exception)}\n", file=sys.stderr)

        # Keep running unless it's a critical error
        self.needs_render = True
