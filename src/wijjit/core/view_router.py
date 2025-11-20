"""View routing and navigation for Wijjit applications.

This module provides the ViewRouter class which handles view registration,
navigation, and lifecycle hooks. Supports both synchronous and asynchronous
view functions and lifecycle hooks.
"""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit

logger = get_logger(__name__)


@dataclass
class ViewConfig:
    """Configuration for a view.

    Supports both synchronous and asynchronous view functions and lifecycle hooks.

    Parameters
    ----------
    name : str
        Unique name for this view
    template : str
        Template string (inline template content)
    template_file : str
        Template filename to load from template_dir
    data : Optional[Callable[..., Dict[str, Any]]]
        Function that returns data dict for template rendering
    on_enter : Optional[Callable[[], None] | Callable[[], Awaitable[None]]]
        Hook called when navigating to this view (sync or async)
    on_exit : Optional[Callable[[], None] | Callable[[], Awaitable[None]]]
        Hook called when navigating away from this view (sync or async)
    is_default : bool
        Whether this is the default view (shown on startup)
    view_func : Optional[Callable | Callable[..., Awaitable]]
        The original view function (used for lazy initialization, sync or async)
    initialized : bool
        Whether this view has been initialized

    Attributes
    ----------
    name : str
        Unique name for this view
    template : str
        Template string (inline template content)
    template_file : str
        Template filename to load from template_dir
    data : Optional[Callable[..., Dict[str, Any]]]
        Function that returns data dict for template rendering
    on_enter : Optional[Callable[[], None] | Callable[[], Awaitable[None]]]
        Hook called when navigating to this view (sync or async)
    on_exit : Optional[Callable[[], None] | Callable[[], Awaitable[None]]]
        Hook called when navigating away from this view (sync or async)
    is_default : bool
        Whether this is the default view
    view_func : Optional[Callable | Callable[..., Awaitable]]
        The original view function (for lazy initialization, sync or async)
    initialized : bool
        Whether this view has been initialized
    """

    name: str
    template: str = ""
    template_file: str = ""
    data: Callable[..., dict[str, Any]] | None = None
    on_enter: Callable[[], None] | Callable[[], Awaitable[None]] | None = None
    on_exit: Callable[[], None] | Callable[[], Awaitable[None]] | None = None
    is_default: bool = False
    view_func: Callable[..., Any] | Callable[..., Awaitable[Any]] | None = field(
        default=None, repr=False
    )
    initialized: bool = False


class ViewRouter:
    """Manages view registration and navigation.

    The view router handles:
    - View registration via decorator
    - View lookup and caching
    - View navigation with parameters
    - Lifecycle hook execution (on_enter, on_exit)
    - Template initialization

    Parameters
    ----------
    app : Wijjit
        Reference to the main application

    Attributes
    ----------
    app : Wijjit
        Application reference
    views : dict[str, ViewConfig]
        Registered views
    current_view : str or None
        Name of current view
    default_view : str or None
        Name of default view
    """

    def __init__(self, app: Wijjit) -> None:
        """Initialize the view router.

        Parameters
        ----------
        app : Wijjit
            Reference to the main application
        """
        self.app = app
        self.views: dict[str, ViewConfig] = {}
        self.current_view: str | None = None
        self.default_view: str | None = None

    def view_decorator(
        self,
        name: str,
        default: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Create a decorator to register a view.

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
        Inline template string:

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

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # Store the function and create a lazy ViewConfig
            # We'll extract the actual config when the view is first accessed
            view_config = ViewConfig(
                name=name,
                template="",  # Will be set lazily
                data=None,  # Will be set lazily
                on_enter=None,  # Will be set lazily
                on_exit=None,  # Will be set lazily
                is_default=default,
                view_func=func,  # Store the original function
                initialized=False,
            )

            self.views[name] = view_config

            logger.debug(f"Registered view '{name}' (default={default})")

            # Set as default view if specified
            if default:
                self.default_view = name
                if self.current_view is None:
                    self.current_view = name

            return func

        return decorator

    def _initialize_view(self, view_config: ViewConfig) -> None:
        """Initialize a view config by calling its view function (synchronous).

        This is called lazily the first time a view is accessed.
        For async view functions, this will raise an error. Use
        _initialize_view_async() instead.

        Parameters
        ----------
        view_config : ViewConfig
            The view configuration to initialize

        Raises
        ------
        RuntimeError
            If view_func is async (use _initialize_view_async instead)
        """
        if view_config.initialized:
            return  # Already initialized

        if view_config.view_func:
            # Check if view function is async
            if asyncio.iscoroutinefunction(view_config.view_func):
                raise RuntimeError(
                    f"View '{view_config.name}' has async view function. "
                    f"Use navigate_async() or call from async context."
                )

            # Call the view function ONCE to get the config dict
            result = view_config.view_func()
            # Ensure result is a dict (not Awaitable)
            if not isinstance(result, dict):
                raise TypeError(f"View function must return dict, got {type(result)}")
            config_dict: dict[str, Any] = result

            # Extract static config components
            view_config.template = config_dict.get("template", "")
            view_config.template_file = config_dict.get("template_file", "")
            view_config.on_enter = config_dict.get("on_enter")
            view_config.on_exit = config_dict.get("on_exit")

            # Extract data - could be a dict or a callable
            data_value = config_dict.get("data", {})

            if callable(data_value):
                # User provided a data callback - use it directly
                view_config.data = data_value
            else:
                # User provided static data dict - wrap in lambda
                # Type assertion: we know data_value should be dict-like if not callable
                static_data: dict[str, Any] = (
                    data_value if isinstance(data_value, dict) else {}
                )

                def data_func(**kwargs: Any) -> dict[str, Any]:
                    # Return a deep copy to prevent mutations from persisting across renders
                    # Deep copy is necessary because nested dicts/lists would be shared
                    # with shallow copy, allowing template mutations to leak across renders
                    return copy.deepcopy(static_data)

                view_config.data = data_func

            view_config.initialized = True

    async def _initialize_view_async(self, view_config: ViewConfig) -> None:
        """Initialize a view config by calling its view function (async).

        This is called lazily the first time a view is accessed.
        Supports both sync and async view functions.

        Parameters
        ----------
        view_config : ViewConfig
            The view configuration to initialize
        """
        if view_config.initialized:
            return  # Already initialized

        if view_config.view_func:
            # Call the view function ONCE to get the config dict
            if asyncio.iscoroutinefunction(view_config.view_func):
                config_dict = await view_config.view_func()
            else:
                config_dict = view_config.view_func()

            # Extract static config components
            view_config.template = config_dict.get("template", "")
            view_config.template_file = config_dict.get("template_file", "")
            view_config.on_enter = config_dict.get("on_enter")
            view_config.on_exit = config_dict.get("on_exit")

            # Extract data - could be a dict or a callable
            data_value = config_dict.get("data", {})

            if callable(data_value):
                # User provided a data callback - use it directly
                view_config.data = data_value
            else:
                # User provided static data dict - wrap in lambda
                # Type assertion: we know data_value should be dict-like if not callable
                static_data: dict[str, Any] = (
                    data_value if isinstance(data_value, dict) else {}
                )

                def data_func(**kwargs: Any) -> dict[str, Any]:
                    # Return a deep copy to prevent mutations from persisting across renders
                    # Deep copy is necessary because nested dicts/lists would be shared
                    # with shallow copy, allowing template mutations to leak across renders
                    return copy.deepcopy(static_data)

                view_config.data = data_func

            view_config.initialized = True

    def navigate(
        self,
        view_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Navigate to a different view.

        Calls on_exit hook of current view, switches to new view,
        and calls on_enter hook of new view.

        Parameters
        ----------
        view_name : str
            Name of view to navigate to
        params : dict, optional
            Parameters to pass to the view's data function

        Raises
        ------
        ValueError
            If view_name doesn't exist
        """
        if view_name not in self.views:
            logger.error(f"Navigation failed: view '{view_name}' not found")
            raise ValueError(f"View '{view_name}' not found")

        params = params or {}

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
                    self.app._handle_error(
                        f"Error in on_exit for view '{self.current_view}'", e
                    )

            # Clear view-scoped handlers
            self.app.handler_registry.clear_view(self.current_view)

            # Clear view-specific shortcuts
            self.app.wiring_manager.clear_view_shortcuts()

        # Switch to new view
        self.current_view = view_name
        self.app.current_view_params = params
        self.app.handler_registry.current_view = view_name

        # Call new view's on_enter hook
        new_view = self.views[view_name]
        if new_view.on_enter:
            try:
                new_view.on_enter()
            except Exception as e:
                self.app._handle_error(f"Error in on_enter for view '{view_name}'", e)

        # Trigger re-render
        self.app.needs_render = True

    async def navigate_async(
        self,
        view_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Navigate to a different view (async version).

        Supports both sync and async on_exit/on_enter hooks.
        Calls on_exit hook of current view, switches to new view,
        and calls on_enter hook of new view.

        Parameters
        ----------
        view_name : str
            Name of view to navigate to
        params : dict, optional
            Parameters to pass to the view's data function

        Raises
        ------
        ValueError
            If view_name doesn't exist
        """
        if view_name not in self.views:
            logger.error(f"Navigation failed: view '{view_name}' not found")
            raise ValueError(f"View '{view_name}' not found")

        params = params or {}

        logger.info(
            f"Navigating from '{self.current_view}' to '{view_name}' "
            f"(params={list(params.keys())})"
        )

        # Initialize the new view (async)
        await self._initialize_view_async(self.views[view_name])

        # Call current view's on_exit hook
        if self.current_view and self.current_view in self.views:
            current = self.views[self.current_view]
            await self._initialize_view_async(current)
            if current.on_exit:
                try:
                    if asyncio.iscoroutinefunction(current.on_exit):
                        await current.on_exit()
                    else:
                        # Run sync hook in executor
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, current.on_exit)
                except Exception as e:
                    self.app._handle_error(
                        f"Error in on_exit for view '{self.current_view}'", e
                    )

            # Clear view-scoped handlers
            self.app.handler_registry.clear_view(self.current_view)

            # Clear view-specific shortcuts
            self.app.wiring_manager.clear_view_shortcuts()

        # Switch to new view
        self.current_view = view_name
        self.app.current_view_params = params
        self.app.handler_registry.current_view = view_name

        # Call new view's on_enter hook
        new_view = self.views[view_name]
        if new_view.on_enter:
            try:
                if asyncio.iscoroutinefunction(new_view.on_enter):
                    await new_view.on_enter()
                else:
                    # Run sync hook in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, new_view.on_enter)
            except Exception as e:
                self.app._handle_error(f"Error in on_enter for view '{view_name}'", e)

        # Trigger re-render
        self.app.needs_render = True

    def get_view(self, view_name: str) -> ViewConfig | None:
        """Get a view configuration by name.

        Parameters
        ----------
        view_name : str
            Name of the view to retrieve

        Returns
        -------
        ViewConfig or None
            View configuration, or None if not found
        """
        return self.views.get(view_name)

    def register_view(
        self,
        name: str,
        view_func: Callable[..., Any],
        default: bool = False,
        **kwargs: Any,
    ) -> None:
        """Register a view programmatically.

        This method is used internally by the decorator and can also be
        used to register views without the decorator syntax.

        Parameters
        ----------
        name : str
            Unique name for this view
        view_func : Callable
            Function that returns view configuration
        default : bool
            Whether this is the default view
        **kwargs
            Additional view configuration options
        """
        view_config = ViewConfig(
            name=name,
            template="",
            data=None,
            on_enter=None,
            on_exit=None,
            is_default=default,
            view_func=view_func,
            initialized=False,
        )

        self.views[name] = view_config

        if default:
            self.default_view = name
            if self.current_view is None:
                self.current_view = name

        logger.debug(f"Registered view '{name}' programmatically (default={default})")
