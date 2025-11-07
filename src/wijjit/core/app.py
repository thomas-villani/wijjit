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

from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any
from pathlib import Path
import sys
import traceback

from .state import State
from .renderer import Renderer
from .focus import FocusManager
from .events import (
    HandlerRegistry,
    Event,
    KeyEvent,
    ActionEvent,
    EventType,
    HandlerScope,
)
from ..terminal.screen import ScreenManager
from ..terminal.input import InputHandler, Key
from ..terminal.ansi import ANSIColor, colorize


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
    data: Optional[Callable[..., Dict[str, Any]]] = None
    on_enter: Optional[Callable[[], None]] = None
    on_exit: Optional[Callable[[], None]] = None
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
    handler_registry : HandlerRegistry
        Event handler registry and dispatcher
    screen_manager : ScreenManager
        Terminal screen management
    input_handler : InputHandler
        Keyboard input handling
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
        template_dir: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Wijjit application.

        Parameters
        ----------
        template_dir : Optional[str]
            Directory containing template files
        initial_state : Optional[Dict[str, Any]]
            Initial state dictionary
        """
        # Initialize state
        self.state = State(initial_state or {})

        # Initialize renderer
        self.renderer = Renderer(template_dir=template_dir)

        # Initialize focus manager
        self.focus_manager = FocusManager()

        # Initialize event system
        self.handler_registry = HandlerRegistry()

        # Initialize terminal components
        self.screen_manager = ScreenManager()
        self.input_handler = InputHandler()

        # View registry
        self.views: Dict[str, ViewConfig] = {}
        self.current_view: Optional[str] = None
        self.current_view_params: Dict[str, Any] = {}

        # Application state
        self.running = False
        self.needs_render = True

        # Hook state changes to trigger re-render
        self.state.on_change(self._on_state_change)

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
                data=None,    # Will be set lazily
                on_enter=None,  # Will be set lazily
                on_exit=None,   # Will be set lazily
                is_default=default,
            )

            # Store the original function so we can call it later
            view_config._view_func = func
            view_config._initialized = False

            self.views[name] = view_config

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
            # Call the view function to get the config dict
            config_dict = view_config._view_func()

            # Extract config components
            view_config.template = config_dict.get("template", "")
            view_config.on_enter = config_dict.get("on_enter")
            view_config.on_exit = config_dict.get("on_exit")

            # Create data function wrapper
            def data_func(**kwargs):
                result = view_config._view_func(**kwargs)
                return result.get("data", {})

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
            raise ValueError(f"View '{view_name}' not found")

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
                    self._handle_error(f"Error in on_exit for view '{self.current_view}'", e)

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
        view_name: Optional[str] = None,
        element_id: Optional[str] = None,
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
        # Find default view if current_view not set
        if self.current_view is None:
            for name, view in self.views.items():
                if view.is_default:
                    self.current_view = name
                    break

        if self.current_view is None and self.views:
            # Use first registered view as fallback
            self.current_view = next(iter(self.views.keys()))

        if self.current_view is None:
            raise RuntimeError("No views registered. Use @app.view() to register a view.")

        # Initialize and call on_enter for initial view
        initial_view = self.views[self.current_view]
        self._initialize_view(initial_view)

        # Set current view in handler registry so view-scoped handlers work
        self.handler_registry.current_view = self.current_view

        if initial_view.on_enter:
            try:
                initial_view.on_enter()
            except Exception as e:
                self._handle_error(f"Error in on_enter for view '{self.current_view}'", e)

        self.running = True

        try:
            # Enter alternate screen
            self.screen_manager.enter_alternate_buffer()

            # Render initial view
            self._render()

            # Main event loop
            while self.running:
                try:
                    # Read input (blocking)
                    key = self.input_handler.read_key()

                    if key is None:
                        # Error reading key, continue
                        continue

                    # Handle Ctrl+C
                    if key.is_ctrl_c:
                        self.running = False
                        break

                    # Create and dispatch key event
                    event = KeyEvent(
                        key=key.name,
                        modifiers=key.modifiers,
                    )
                    self.handler_registry.dispatch(event)

                    # Re-render if needed
                    if self.needs_render:
                        self._render()

                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    self._handle_error("Error in event loop", e)

        finally:
            # Always exit alternate screen on cleanup
            self.screen_manager.exit_alternate_buffer()
            # Close input handler to exit raw mode
            self.input_handler.close()

    def _render(self) -> None:
        """Render the current view to the screen.

        This is an internal method called by the event loop.
        It renders the current view's template with data and displays it.
        """
        if self.current_view is None or self.current_view not in self.views:
            return

        view = self.views[self.current_view]
        self._initialize_view(view)

        try:
            # Get data for template
            data = {}
            if view.data:
                data = view.data(**self.current_view_params)

            # Add state to template context
            data["state"] = self.state

            # Render template (always use render_string for now)
            output = self.renderer.render_string(view.template, context=data)

            # Clear screen and display output
            self.screen_manager.clear()
            self.screen_manager.move_cursor(0, 0)
            print(output, end="", flush=True)

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

    def _handle_error(self, message: str, exception: Exception) -> None:
        """Handle errors during app execution.

        Displays error message but doesn't crash the app.

        Parameters
        ----------
        message : str
            Error message context
        exception : Exception
            The exception that occurred
        """
        # In a real app, we might show an error view
        # For now, just log to stderr
        try:
            error_text = f"\n{message}: {str(exception)}\n"
            error_text += traceback.format_exc()
            print(colorize(error_text, color=ANSIColor.RED), file=sys.stderr)
        except Exception:
            # If error handling itself fails, print plain text
            print(f"\nError: {message}: {str(exception)}\n", file=sys.stderr)

        # Keep running unless it's a critical error
        self.needs_render = True
