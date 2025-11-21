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
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from wijjit.config import Config, DefaultConfig
from wijjit.core.event_loop import EventLoop
from wijjit.core.events import (
    ActionEvent,
    Event,
    EventType,
    HandlerRegistry,
    HandlerScope,
    KeyEvent,
)
from wijjit.core.focus import FocusManager
from wijjit.core.hover import HoverManager
from wijjit.core.mouse_router import MouseEventRouter
from wijjit.core.notification_manager import NotificationManager
from wijjit.core.overlay import LayerType, Overlay, OverlayManager
from wijjit.core.renderer import Renderer
from wijjit.core.state import State
from wijjit.core.view_router import ViewConfig, ViewRouter
from wijjit.core.wiring import ElementWiringManager
from wijjit.elements.base import Element
from wijjit.elements.display.notification import NotificationElement
from wijjit.elements.menu import ContextMenu, DropdownMenu, MenuElement
from wijjit.layout.bounds import Bounds
from wijjit.logging_config import configure_logging, get_logger
from wijjit.terminal.ansi import ANSIColor, ANSICursor, ANSIStyle, colorize
from wijjit.terminal.input import InputHandler
from wijjit.terminal.mouse import MouseTrackingMode
from wijjit.terminal.screen import ScreenManager

# Get logger for this module
logger = get_logger(__name__)


class Wijjit:
    """Main Wijjit application class.

    The Wijjit class is the central orchestrator for TUI applications.
    It provides a Flask-like API with view decorators and manages all
    framework components.

    Parameters
    ----------
    initial_state : Optional[Dict[str, Any]]
        Initial state dictionary (default: empty dict)

    Attributes
    ----------
    config : Config
        Application configuration (Flask-like dict)
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
    Basic usage:

    >>> app = Wijjit()
    >>> app.config['ENABLE_MOUSE'] = False
    >>> @app.view("main", default=True)
    ... def main_view():
    ...     return {"template": "Hello, World!"}
    >>> app.run()

    Load configuration from file:

    >>> app = Wijjit()
    >>> app.config.from_pyfile('config.py')
    >>> app.run()

    Configure via environment variables:

    >>> # export WIJJIT_DEBUG=1
    >>> # export WIJJIT_ENABLE_MOUSE=0
    >>> app = Wijjit()  # Auto-loads WIJJIT_* env vars
    >>> app.run()
    """

    def __init__(
        self,
        initial_state: dict[str, Any] | None = None,
        template_dir: str | None = None,
        enable_mouse: bool | None = None,
        debug: bool | None = None,
        **config_overrides,
    ) -> None:
        """Initialize Wijjit application.

        Parameters
        ----------
        initial_state : Optional[Dict[str, Any]]
            Initial state dictionary
        template_dir : Optional[str]
            Template directory path (convenience parameter for TEMPLATE_DIR config)
        enable_mouse : Optional[bool]
            Enable mouse support (convenience parameter for ENABLE_MOUSE config)
        debug : Optional[bool]
            Enable debug mode (convenience parameter for DEBUG config)
        **config_overrides
            Additional config overrides (e.g., quit_key='q', log_level='DEBUG')

        Notes
        -----
        Configuration is managed via app.config. Use app.config.from_pyfile(),
        app.config.from_object(), or app.config.update() to configure the app.
        Environment variables with WIJJIT_ prefix are automatically loaded.

        Convenience parameters (template_dir, enable_mouse, debug) and config_overrides
        take precedence over environment variables and defaults.
        """
        logger.info("Initializing Wijjit application")

        # Initialize configuration
        self.config = Config()
        self.config.from_object(DefaultConfig)

        # Auto-load from WIJJIT_* environment variables
        self.config.from_prefixed_env("WIJJIT_")

        # Apply convenience parameters
        if template_dir is not None:
            self.config["TEMPLATE_DIR"] = template_dir
        if enable_mouse is not None:
            self.config["ENABLE_MOUSE"] = enable_mouse
        if debug is not None:
            self.config["DEBUG"] = debug

        # Apply any additional config overrides
        # Convert snake_case kwargs to UPPERCASE config keys
        for key, value in config_overrides.items():
            config_key = key.upper()
            self.config[config_key] = value

        # Configure logging based on config
        self._configure_logging()

        # Configure unicode support mode
        self._configure_unicode_support()

        logger.info(
            f"Config: DEBUG={self.config['DEBUG']}, "
            f"ENABLE_MOUSE={self.config['ENABLE_MOUSE']}, "
            f"LOG_LEVEL={self.config['LOG_LEVEL']}, "
            f"UNICODE_SUPPORT={self.config['UNICODE_SUPPORT']}"
        )

        # Initialize state
        self.state = State(initial_state or {})

        # Initialize renderer
        self.renderer = Renderer(template_dir=self.config["TEMPLATE_DIR"])

        # Load theme file if specified
        self._load_theme_file()

        # Load style file if specified
        self._load_style_file()

        # Apply high contrast theme if enabled
        self._apply_high_contrast_theme()

        # Initialize focus manager
        self.focus_manager = FocusManager()
        self.focus_manager.dirty_manager = self.renderer.dirty_manager

        # Initialize hover manager
        self.hover_manager = HoverManager()
        self.hover_manager.dirty_manager = self.renderer.dirty_manager

        # Initialize overlay manager
        self.overlay_manager = OverlayManager(self)

        # Initialize notification manager
        term_size = shutil.get_terminal_size()
        self.notification_manager = NotificationManager(
            overlay_manager=self.overlay_manager,
            terminal_width=term_size.columns,
            terminal_height=term_size.lines,
            position=self.config["NOTIFICATION_POSITION"],
            spacing=self.config["NOTIFICATION_SPACING"],
            margin=self.config["NOTIFICATION_MARGIN"],
            max_stack=self.config["NOTIFICATION_MAX_STACK"],
        )

        # Initialize event system
        self.handler_registry = HandlerRegistry()

        # Initialize terminal components
        self.screen_manager = ScreenManager()
        self.input_handler = InputHandler(
            enable_mouse=self.config["ENABLE_MOUSE"],
            mouse_tracking_mode=self._get_mouse_tracking_mode(),
        )

        # Initialize routing and event managers
        self.view_router = ViewRouter(self)
        self._executor: ThreadPoolExecutor | None = None
        self.event_loop = EventLoop(self, executor=None)
        self.mouse_router = MouseEventRouter(self)
        self.wiring_manager = ElementWiringManager(self)

        # View state (delegated to ViewRouter, kept for backward compatibility)
        self.current_view_params: dict[str, Any] = {}

        # Application state
        self.running = False
        self.needs_render = True

        # Layout system
        self.positioned_elements = []  # Elements with bounds from layout engine

        # Focus navigation configuration (from config)
        self.focus_navigation_enabled = self.config["ENABLE_FOCUS_NAVIGATION"]

        # Action handlers
        self._action_handlers: dict[str, Callable] = {}

        # Key handlers
        self._key_handlers: dict[str, Callable] = {}

        # Auto-refresh for animations (from config)
        self.refresh_interval: float | None = self.config["REFRESH_INTERVAL"]
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

        # Apply executor configuration from config
        if self.config["RUN_SYNC_IN_EXECUTOR"]:
            self._executor = ThreadPoolExecutor(
                max_workers=self.config["EXECUTOR_MAX_WORKERS"]
            )
            self.event_loop.executor = self._executor
            logger.info(
                f"Created ThreadPoolExecutor "
                f"(max_workers={self.config['EXECUTOR_MAX_WORKERS'] or 'default'})"
            )

    def _configure_logging(self) -> None:
        """Configure logging based on config settings.

        Applies LOG_LEVEL, LOG_FILE, LOG_TO_CONSOLE, and LOG_FORMAT
        configuration options.
        """
        # Configure logging from config
        configure_logging(
            level=self.config["LOG_LEVEL"],
            filename=self.config["LOG_FILE"],
            format_string=self.config["LOG_FORMAT"],
        )

        # Log configuration details
        if self.config["LOG_FILE"]:
            logger.info(f"Logging to file: {self.config['LOG_FILE']}")

    def _configure_unicode_support(self) -> None:
        """Configure unicode support based on config settings.

        Applies UNICODE_SUPPORT configuration: 'auto', 'force', or 'disable'.
        """
        from wijjit.terminal import ansi

        mode = self.config["UNICODE_SUPPORT"]
        if mode not in ("auto", "force", "disable"):
            logger.warning(f"Invalid UNICODE_SUPPORT mode '{mode}', using 'auto'")
            mode = "auto"

        ansi.set_unicode_mode(mode)
        logger.debug(f"Unicode support mode set to: {mode}")

    def _get_mouse_tracking_mode(self) -> MouseTrackingMode:
        """Convert config string to MouseTrackingMode enum.

        Returns
        -------
        MouseTrackingMode
            Mouse tracking mode enum value

        Raises
        ------
        ValueError
            If mouse tracking mode is invalid
        """
        mode = self.config["MOUSE_TRACKING_MODE"]

        if mode == "button_event":
            return MouseTrackingMode.BUTTON_EVENT
        elif mode == "all_events":
            return MouseTrackingMode.ALL_EVENTS
        elif mode == "drag":
            return MouseTrackingMode.DRAG
        else:
            logger.warning(
                f"Invalid MOUSE_TRACKING_MODE '{mode}', using 'button_event'"
            )
            return MouseTrackingMode.BUTTON_EVENT

    def _load_theme_file(self) -> None:
        """Load theme from THEME_FILE config if specified.

        Supports CSS and JSON theme files (JSON not yet implemented).
        Sets the loaded theme as the active theme.
        """
        from wijjit.styling.theme import Theme

        theme_path = self.config["THEME_FILE"]
        if not theme_path:
            # No theme file specified, apply DEFAULT_THEME if not 'default'
            default_theme = self.config["DEFAULT_THEME"]
            if default_theme != "default":
                try:
                    self.renderer.theme_manager.set_theme(default_theme)
                    logger.info(f"Applied theme: {default_theme}")
                except KeyError:
                    logger.warning(f"Theme '{default_theme}' not found, using default")
            return

        # Theme file specified - load it
        try:
            if theme_path.endswith(".css"):
                # Load CSS theme
                theme = Theme.from_css(theme_path, "custom")
                self.renderer.theme_manager.register_theme(theme)
                self.renderer.theme_manager.set_theme("custom")
                logger.info(f"Loaded CSS theme from: {theme_path}")

            elif theme_path.endswith(".json"):
                # JSON themes not yet implemented
                logger.error(
                    f"JSON theme files not yet supported: {theme_path}\n"
                    f"Use CSS format instead or contribute JSON theme loader!"
                )

            else:
                logger.warning(
                    f"Unknown theme file format: {theme_path}\n"
                    f"Supported formats: .css"
                )

        except FileNotFoundError:
            logger.error(f"Theme file not found: {theme_path}")
        except Exception as e:
            logger.error(f"Error loading theme from {theme_path}: {e}")

    def _load_style_file(self) -> None:
        """Load additional styles from STYLE_FILE config if specified.

        Style files are CSS files that add to the current theme
        rather than replacing it entirely.
        """
        from wijjit.styling.theme import Theme

        style_path = self.config["STYLE_FILE"]
        if not style_path:
            return

        try:
            if style_path.endswith(".css"):
                # Load CSS styles and merge with current theme
                additional_styles = Theme.from_css(style_path, "additional")

                # Merge styles into current theme
                current_theme = self.renderer.theme_manager.current_theme
                for class_name, style in additional_styles.styles.items():
                    current_theme.set_style(class_name, style)

                logger.info(f"Loaded additional styles from: {style_path}")

            else:
                logger.warning(
                    f"Unknown style file format: {style_path}\n"
                    f"Supported formats: .css"
                )

        except FileNotFoundError:
            logger.error(f"Style file not found: {style_path}")
        except Exception as e:
            logger.error(f"Error loading styles from {style_path}: {e}")

    def _apply_high_contrast_theme(self) -> None:
        """Apply high contrast theme if HIGH_CONTRAST config is enabled.

        The high contrast theme uses pure black and white with bright,
        saturated colors for maximum accessibility. This is useful for
        users with vision impairments.

        Notes
        -----
        This is applied after custom theme/style files, so custom themes
        take precedence. If you want to force high contrast regardless of
        other theme settings, set HIGH_CONTRAST=True.
        """
        if self.config.get("HIGH_CONTRAST", False):
            try:
                self.renderer.theme_manager.set_theme("high_contrast")
                logger.info("Applied high contrast theme for accessibility")
            except KeyError as e:
                logger.error(f"High contrast theme not found: {e}")

    @property
    def views(self) -> dict[str, ViewConfig]:
        """Get registered views (delegates to ViewRouter).

        Returns
        -------
        dict[str, ViewConfig]
            Dictionary of registered views
        """
        return self.view_router.views

    @property
    def current_view(self) -> str | None:
        """Get current view name (delegates to ViewRouter).

        Returns
        -------
        str or None
            Name of current view
        """
        return self.view_router.current_view

    @current_view.setter
    def current_view(self, value: str | None) -> None:
        """Set current view name (delegates to ViewRouter).

        Parameters
        ----------
        value : str or None
            Name of view to set as current
        """
        self.view_router.current_view = value

    def view(
        self,
        name: str,
        default: bool = False,
    ) -> Callable:
        """Decorator to register a view (delegates to ViewRouter).

        The decorated function should return a dict with:
        - template: str - Inline template string (use this OR template_file)
        - template_file: str - Template filename to load from template_dir (use this OR template)
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
        Inline template:

        >>> @app.view("main", default=True)
        ... def main_view():
        ...     return {
        ...         "template": "Hello, {{ name }}!",
        ...         "data": {"name": "World"},
        ...     }

        Load from file:

        >>> @app.view("dashboard")
        ... def dashboard_view():
        ...     return {
        ...         "template_file": "dashboard.tui",
        ...         "data": {"stats": get_stats()},
        ...     }
        """
        return self.view_router.view_decorator(name, default)

    def _initialize_view(self, view_config: ViewConfig) -> None:
        """Initialize a view config (delegates to ViewRouter).

        This is called lazily the first time a view is accessed.

        Parameters
        ----------
        view_config : ViewConfig
            The view configuration to initialize
        """
        self.view_router._initialize_view(view_config)

    def navigate(self, view_name: str, **params) -> None:
        """Navigate to a different view (delegates to ViewRouter).

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
        self.view_router.navigate(view_name, params)

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

    def on_key(self, key: str, allow_ctrl_q: bool = False, **kwargs) -> Callable:
        """Decorator to register a key press handler.

        Use this to handle specific key presses globally in your application.

        Parameters
        ----------
        key : str
            The key to handle (e.g., "d", "q", "enter", "space")
        allow_ctrl_q : bool, optional
            Allow binding to Ctrl+Q (default: False). Use with caution as
            Ctrl+Q is normally reserved for exiting the application.

        Returns
        -------
        Callable
            Decorator function

        Raises
        ------
        ValueError
            If attempting to bind Ctrl+Q without allow_ctrl_q=True

        Examples
        --------
        >>> @app.on_key("d")
        ... def delete_handler(event):
        ...     print("Delete key pressed!")

        >>> @app.on_key("ctrl+q", allow_ctrl_q=True)
        ... def custom_exit(event):
        ...     print("Custom Ctrl+Q handler")
        """
        # Validate that Ctrl+Q is not being bound (reserved for app exit)
        key_lower = key.lower()
        allow_ctrl_q = kwargs.get("allow_ctrl_q", False)
        if not allow_ctrl_q and key_lower in ("ctrl+q", "c-q"):
            raise ValueError(
                "Cannot bind Ctrl+Q: it is reserved for exiting the application. "
                "Use allow_ctrl_q=True to override this restriction."
            )

        def decorator(func: Callable[..., Any]) -> Callable:
            self._key_handlers[key_lower] = func
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

        def decorator(func: Callable[..., Any]) -> Callable:
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
        """Quit the application (delegates to EventLoop).

        Sets the running flag to False, which will exit the event loop.
        """
        self.event_loop.stop()
        self.running = False

    def refresh(self) -> None:
        """Force a re-render on the next loop iteration."""
        self.needs_render = True

    def run(self) -> None:
        """Run the application (delegates to EventLoop).

        Enters the main event loop:
        1. Render initial view
        2. Loop: read input -> dispatch events -> re-render if needed
        3. Exit on quit or Ctrl+Q

        The loop continues until quit() is called or the user presses Ctrl+Q.
        """
        self.event_loop.run()

    def _render(self) -> None:
        """Render the current view to the screen.

        This is an internal method called by the event loop.
        It renders the current view's template with data and displays it.
        """
        import time

        # Track render start time for performance monitoring
        render_start = time.time()

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

            # Determine which template to use (file or inline string)
            # template_content = view.template_file or view.template

            # Check if template has layout tags (only for inline templates)
            # File-based templates are always rendered with layout engine
            has_layout = bool(view.template_file) or self._has_layout_tags(
                view.template
            )
            logger.debug(f"View has layout tags: {has_layout}")

            if has_layout:
                # Get the currently focused element ID (if any) from FocusManager
                focused_id = None
                focused_elem = self.focus_manager.get_focused_element()
                if focused_elem and hasattr(focused_elem, "id"):
                    focused_id = focused_elem.id

                # Pass focused ID and context to renderer so template extensions
                # can create elements with correct focus state
                self.renderer.add_global("_wijjit_current_context", data)
                self.renderer.add_global("_wijjit_focused_id", focused_id)

                # Render with layout (elements will be created with correct focus state)
                term_size = shutil.get_terminal_size()
                if view.template_file:
                    # Load from file
                    output, elements, layout_ctx = self.renderer.render_with_layout(
                        template_name=view.template_file,
                        context=data,
                        width=term_size.columns,
                        height=term_size.lines,
                        overlay_manager=self.overlay_manager,
                    )
                else:
                    # Inline template string
                    output, elements, layout_ctx = self.renderer.render_with_layout(
                        template_string=view.template,
                        context=data,
                        width=term_size.columns,
                        height=term_size.lines,
                        overlay_manager=self.overlay_manager,
                    )

                # Store elements and update focus manager
                self.positioned_elements = elements
                if not self.overlay_manager.should_trap_focus():
                    # Normal rendering - update with view elements
                    self._update_focus_manager(elements)
                else:
                    # Focus is trapped in overlay - update with overlay's focusable elements
                    overlay_focusable = self.overlay_manager.get_focus_trap_elements()
                    # Filter by bounds (focusable elements must have bounds set)
                    overlay_focusable = [
                        elem
                        for elem in overlay_focusable
                        if hasattr(elem, "bounds") and elem.bounds
                    ]
                    self.focus_manager.set_elements(overlay_focusable)

                # Clean up globals
                self.renderer.add_global("_wijjit_current_context", None)
                self.renderer.add_global("_wijjit_focused_id", None)

                # Process template-declared overlays from layout context
                # Remove any template-declared overlays that are no longer visible
                # and add new ones based on current template state
                self._sync_template_overlays(layout_ctx)

                # Extract statusbar from layout context if present
                # current_statusbar = getattr(layout_ctx, "_statusbar", None)

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
                # No statusbar for non-layout templates
                # current_statusbar = None

            # Track overlay identities to detect changes (additions, removals, replacements)
            # Use object IDs to detect when overlays are replaced (same count but different objects)
            current_overlay_ids = tuple(id(o) for o in self.overlay_manager.overlays)
            prev_overlay_ids = getattr(self, "_last_overlay_ids", ())
            overlays_changed = current_overlay_ids != prev_overlay_ids
            self._last_overlay_ids = current_overlay_ids

            if overlays_changed:
                logger.debug(
                    f"Overlays changed: {len(prev_overlay_ids)} -> {len(current_overlay_ids)}"
                )

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
                    overlay_manager=self.overlay_manager,
                    force_full_redraw=overlays_changed,
                )
            # Note: When overlays are dismissed (overlays_changed=True but no overlays present),
            # the diff rendering in _compose_output_cells already handled clearing them
            # because it diffed from old displayed (with overlays) to new base (without overlays)

            # Add FPS display if enabled
            if self.config["SHOW_FPS"] and hasattr(self.event_loop, "current_fps"):
                output = self._add_fps_overlay(output)

            # Add bounds visualization if enabled
            if self.config["SHOW_BOUNDS"]:
                output = self._add_bounds_overlay(output)

            # Clear dirty regions after ALL compositing (including overlays) is complete
            self.renderer.dirty_manager.clear()

            # Display output
            # Ensure output ends with RESET to clear any lingering formatting (e.g., DIM from backdrop)
            if not output.endswith(ANSIStyle.RESET):
                output += ANSIStyle.RESET

            # Cell-based rendering uses DiffRenderer which handles screen clearing internally:
            # - When use_diff_rendering=True: Clears on first render, then only outputs diffs
            # - When use_diff_rendering=False: Clears on every render (via DiffRenderer)

            # Handle encoding for Windows console
            try:
                print(output, end="", flush=True)
            except UnicodeEncodeError:
                # Fall back to encoding with error handling
                sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))
                sys.stdout.flush()

            # Check render performance if configured
            if self.config["WARN_SLOW_RENDER_MS"]:
                render_time_ms = (time.time() - render_start) * 1000
                threshold = self.config["WARN_SLOW_RENDER_MS"]
                if render_time_ms > threshold:
                    logger.warning(
                        f"Slow render detected: {render_time_ms:.1f}ms "
                        f"(threshold: {threshold}ms) for view '{self.current_view}'"
                    )

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

        # Mark full screen dirty for state changes
        # TODO: Optimize by tracking which elements depend on which state keys
        term_size = shutil.get_terminal_size()
        self.renderer.dirty_manager.mark_full_screen(term_size.columns, term_size.lines)

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

    def _update_focus_manager(self, elements: list[Any]) -> None:
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

        # Get template-declared overlays from layout context
        template_overlays = getattr(layout_ctx, "_overlays", [])

        # Build set of template overlay element IDs for tracking
        # Use element.id (user/auto-generated ID) instead of id() (Python object ID)
        # so that re-rendered elements with same ID are recognized as the same overlay
        template_overlay_ids = {
            overlay_info["element"].id
            for overlay_info in template_overlays
            if hasattr(overlay_info["element"], "id") and overlay_info["element"].id
        }

        # Remove template-declared overlays that are no longer in the template
        # (but keep programmatic overlays)
        if not hasattr(self, "_template_overlay_ids"):
            self._template_overlay_ids = set()

        overlays_to_remove = []
        for overlay in self.overlay_manager.overlays:
            element_id = overlay.element.id if hasattr(overlay.element, "id") else None
            # If this was a template overlay but is no longer in the new template
            if (
                element_id
                and element_id in self._template_overlay_ids
                and element_id not in template_overlay_ids
            ):
                overlays_to_remove.append(overlay)

        for overlay in overlays_to_remove:
            self.overlay_manager.pop(overlay)

        # Add new template-declared overlays
        for overlay_info in template_overlays:
            element = overlay_info["element"]
            element_id = element.id if hasattr(element, "id") else None

            # Get visibility state first
            is_visible = overlay_info.get("is_visible", True)
            visible_state_key = overlay_info.get("visible_state_key")

            # Check current visibility from state if state key is provided
            if visible_state_key:
                is_visible = bool(self.state.get(visible_state_key, False))
                if isinstance(element, ContextMenu):
                    logger.debug(
                        f"ContextMenu visibility check: state[{visible_state_key!r}] = {is_visible}"
                    )

            # Restore state on the element BEFORE using it anywhere
            if isinstance(element, (DropdownMenu, ContextMenu)) and visible_state_key:
                # Set up state persistence for menu highlight
                highlight_key = f"_menu_highlight_{visible_state_key}"
                element._state_dict = self.state
                element._highlight_state_key = highlight_key

                # Restore highlighted_index from state
                if highlight_key in self.state:
                    element.highlighted_index = self.state[highlight_key]

                # For context menus, restore mouse position too
                if isinstance(element, ContextMenu):
                    position_key = f"_context_menu_pos_{visible_state_key}"
                    if position_key in self.state:
                        element.mouse_position = self.state[position_key]

            # Check if this overlay already exists
            existing_overlay = None
            if element_id:
                for o in self.overlay_manager.overlays:
                    if hasattr(o.element, "id") and o.element.id == element_id:
                        existing_overlay = o
                        break

            if existing_overlay:
                # Overlay exists - update element reference and check visibility
                # Replace old element with new one (template re-creates elements each render)
                existing_overlay.element = element

                if not is_visible:
                    # Should not be visible, remove it
                    self.overlay_manager.pop(existing_overlay)
                else:
                    # Still visible - update bounds if it's a menu
                    if isinstance(element, (DropdownMenu, ContextMenu)):
                        element.bounds = self.overlay_manager._calculate_menu_position(
                            element
                        )
                        logger.debug(
                            f"Updated bounds for existing {type(element).__name__}: {element.bounds}"
                        )

                    # If overlay traps focus, update focus manager with new element
                    if existing_overlay.trap_focus and element.focusable:
                        # Update focus manager's elements list with the new element
                        self.focus_manager.set_elements([element])
                        self.focus_manager.focus_element(element)
            else:
                # Overlay doesn't exist yet
                if is_visible:
                    # Should be visible, add it
                    def on_close(key=visible_state_key):
                        # Update state to hide the menu
                        if key:
                            self.state[key] = False

                    # Push overlay to manager
                    self.overlay_manager.push(
                        element=element,
                        layer_type=overlay_info.get("layer_type", LayerType.MODAL),
                        close_on_escape=overlay_info.get("close_on_escape", True),
                        close_on_click_outside=overlay_info.get(
                            "close_on_click_outside", True
                        ),
                        trap_focus=overlay_info.get("trap_focus", False),
                        dimmed_background=overlay_info.get("dim_background", False),
                        on_close=on_close,
                    )

                    # Calculate bounds for menu elements (dropdowns and context menus)
                    if isinstance(element, (DropdownMenu, ContextMenu)):
                        element.bounds = self.overlay_manager._calculate_menu_position(
                            element
                        )
                        logger.debug(
                            f"Calculated bounds for {type(element).__name__}: {element.bounds}"
                        )

                # If not visible, don't add it (but it was created for shortcut registration)

        # Update tracking set
        self._template_overlay_ids = template_overlay_ids

        # Store overlay info for menu shortcut registration
        self._last_template_overlays = template_overlays

    def _wire_element_callbacks(self, elements: list[Any]) -> None:
        """Wire up element callbacks for actions and state binding (delegates to ElementWiringManager).

        Parameters
        ----------
        elements : list
            List of positioned elements
        """
        # Wire basic element callbacks
        self.wiring_manager.wire_elements(elements, self.state)

        # Wire menu callbacks (for overlay menus)
        # Process ALL menu elements from template overlays, not just visible ones
        # This ensures shortcuts are registered even when menu is initially hidden
        if hasattr(self, "_last_template_overlays"):
            # Collect menu elements
            menu_elements_to_process = []
            for overlay_info in self._last_template_overlays:
                elem = overlay_info["element"]
                if isinstance(elem, MenuElement):
                    menu_elements_to_process.append((elem, overlay_info))

            # Track all dropdown menu visible state keys for mutual exclusion
            dropdown_state_keys = []
            for elem, overlay_info in menu_elements_to_process:
                if isinstance(elem, DropdownMenu):
                    visible_state_key = overlay_info.get("visible_state_key")
                    if visible_state_key:
                        dropdown_state_keys.append(visible_state_key)

            # Wire menu elements
            self.wiring_manager.wire_menu_elements(
                menu_elements_to_process,
                dropdown_state_keys,
                elements,
                self.state,
                EventType.KEY,
                HandlerScope.GLOBAL,
            )

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

    def _dispatch_action(
        self, action_id: str, data: Any = None, event: ActionEvent | None = None
    ) -> None:
        """Dispatch an action event to registered action handlers.

        Parameters
        ----------
        action_id : str
            The action ID to dispatch
        data : Any, optional
            Additional data to include with the action event (used only if event is None)
        event : ActionEvent, optional
            Pre-created ActionEvent to pass through (takes precedence over creating new one)
        """
        if action_id in self._action_handlers:
            logger.info(f"Dispatching action: '{action_id}' (data={data})")

            # Use provided event or create a new one
            if event is not None:
                action_event = event
            else:
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

        # Set element position
        if element.bounds is None:
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
        # Set element position
        if element.bounds is None:
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

    def notify(
        self,
        message: str,
        severity: str = "info",
        duration: float | None = 3.0,
        action: tuple[str, Callable] | None = None,
        dismiss_on_action: bool = True,
        bell: bool = False,
    ) -> str:
        """Show a notification message.

        Notifications are temporary messages that appear in a corner of the screen.
        They auto-dismiss after a duration and can optionally include an action button.

        Parameters
        ----------
        message : str
            Notification message text
        severity : str, optional
            Severity level: "success", "error", "warning", or "info" (default: "info")
        duration : float or None, optional
            Duration in seconds before auto-dismiss (default: 3.0)
            Set to None for no auto-dismiss
        action : tuple of (str, callable), optional
            Optional action button as (label, callback) tuple
        dismiss_on_action : bool, optional
            Whether to auto-dismiss when action is clicked (default: True)
        bell : bool, optional
            Whether to play a terminal bell sound (default: False)

        Returns
        -------
        str
            Notification ID for manual dismissal via dismiss_notification()

        Examples
        --------
        Show a success notification:

            app.notify("File saved successfully!", severity="success")

        Show an error with an action button:

            def retry():
                # Retry logic
                pass

            app.notify(
                "Connection failed",
                severity="error",
                action=("Retry", retry),
                duration=5.0
            )

        Show a persistent notification with sound:

            app.notify(
                "Update available",
                severity="info",
                duration=None,  # Won't auto-dismiss
                bell=True
            )
        """

        # Play bell if requested
        if bell:
            # Output bell character to terminal (use sys.stdout for immediate output)
            sys.stdout.write(ANSICursor.bell())
            sys.stdout.flush()

        # Extract action components if provided
        action_label = None
        action_callback = None
        if action:
            action_label, action_callback = action

        # Create notification element
        notification = NotificationElement(
            message=message,
            severity=severity,
            action_label=action_label,
            action_callback=action_callback,
            dismiss_on_action=dismiss_on_action,
        )

        # Add to notification manager
        notification_id = self.notification_manager.add(
            notification,
            duration=duration,
            on_close=lambda: setattr(self, "needs_render", True),
        )

        # Enable auto-refresh if we have notifications with timeouts
        # This ensures notifications auto-dismiss even without user input
        if duration is not None and self.refresh_interval is None:
            self.refresh_interval = 0.1  # Check every 100ms

        # Trigger render to show notification
        self.needs_render = True

        logger.debug(
            f"Showed notification: {message[:50]}... "
            f"(severity={severity}, duration={duration})"
        )

        return notification_id

    def dismiss_notification(self, notification_id: str) -> bool:
        """Manually dismiss a notification.

        Parameters
        ----------
        notification_id : str
            ID returned by notify()

        Returns
        -------
        bool
            True if notification was dismissed, False if not found

        Examples
        --------
        >>> notification_id = app.notify("Processing...", duration=None)
        >>> # ... do work ...
        >>> app.dismiss_notification(notification_id)
        """
        result = self.notification_manager.remove(notification_id)
        if result:
            self.needs_render = True
        return result

    def _add_fps_overlay(self, output: str) -> str:
        """Add FPS counter overlay to output.

        Parameters
        ----------
        output : str
            Current rendered output

        Returns
        -------
        str
            Output with FPS counter added

        Notes
        -----
        FPS counter appears in top-right corner using ANSI positioning.
        """
        # Get current FPS value
        fps = self.event_loop.current_fps

        # Format FPS display
        fps_text = f"FPS: {fps:4.1f}"

        # Position in top-right corner
        # Use ANSI cursor positioning to overlay FPS counter
        term_size = shutil.get_terminal_size()
        column = term_size.columns - len(fps_text)

        # Create FPS overlay using ANSI positioning
        # Save cursor, move to top-right, print FPS, restore cursor
        fps_overlay = (
            f"{ANSICursor.save()}"
            f"{ANSICursor.position(1, column)}"
            f"{colorize(fps_text, color=ANSIColor.fg(0, 255, 0), bold=True)}"  # Green FPS
            f"{ANSICursor.restore()}"
        )

        return output + fps_overlay

    def _add_bounds_overlay(self, output: str) -> str:
        """Add element bounds visualization overlay to output.

        Parameters
        ----------
        output : str
            Current rendered output

        Returns
        -------
        str
            Output with bounds rectangles added

        Notes
        -----
        Draws colored rectangles around all positioned elements for debugging.
        Different colors indicate different element types:
        - Cyan: Input elements (focusable)
        - Yellow: Display elements
        - Magenta: Container elements
        - Green: Other elements
        """
        from wijjit.elements.base import Container, ElementType

        bounds_overlay = ANSICursor.save()

        # Draw bounds for all positioned elements
        for elem in self.positioned_elements:
            if not hasattr(elem, "bounds") or elem.bounds is None:
                continue

            bounds = elem.bounds

            # Skip elements with zero or negative dimensions
            if bounds.width <= 0 or bounds.height <= 0:
                continue

            # Determine color based on element type
            if hasattr(elem, "focusable") and elem.focusable:
                # Input elements - cyan
                color = ANSIColor.fg(0, 255, 255)
            elif isinstance(elem, Container):
                # Container elements - magenta
                color = ANSIColor.fg(255, 0, 255)
            elif (
                hasattr(elem, "element_type")
                and elem.element_type == ElementType.DISPLAY
            ):
                # Display elements - yellow
                color = ANSIColor.fg(255, 255, 0)
            else:
                # Other elements - green
                color = ANSIColor.fg(0, 255, 0)

            # Draw top border
            bounds_overlay += ANSICursor.position(bounds.y + 1, bounds.x + 1)
            bounds_overlay += colorize(
                "+" + "-" * (bounds.width - 2) + "+", color=color
            )

            # Draw side borders
            for dy in range(1, bounds.height - 1):
                # Left border
                bounds_overlay += ANSICursor.position(bounds.y + dy + 1, bounds.x + 1)
                bounds_overlay += colorize("|", color=color)
                # Right border
                bounds_overlay += ANSICursor.position(
                    bounds.y + dy + 1, bounds.x + bounds.width
                )
                bounds_overlay += colorize("|", color=color)

            # Draw bottom border (only if height > 1)
            if bounds.height > 1:
                bounds_overlay += ANSICursor.position(
                    bounds.y + bounds.height, bounds.x + 1
                )
                bounds_overlay += colorize(
                    "+" + "-" * (bounds.width - 2) + "+", color=color
                )

        bounds_overlay += ANSICursor.restore()

        return output + bounds_overlay

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
