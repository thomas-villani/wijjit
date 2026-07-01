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

from wijjit.core.templating import RenderedView
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
    data : Callable[..., dict[str, Any]] or None
        Function that returns data dict for template rendering
    on_enter : Callable[[], None] | Callable[[], Awaitable[None]] or None
        Hook called when navigating to this view (sync or async)
    on_exit : Callable[[], None] | Callable[[], Awaitable[None]] or None
        Hook called when navigating away from this view (sync or async)
    is_default : bool
        Whether this is the default view (shown on startup)
    view_func : Callable | Callable[..., Awaitable] or None
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
    data : Callable[..., dict[str, Any]] or None
        Function that returns data dict for template rendering
    on_enter : Callable[[], None] | Callable[[], Awaitable[None]] or None
        Hook called when navigating to this view (sync or async)
    on_exit : Callable[[], None] | Callable[[], Awaitable[None]] or None
        Hook called when navigating away from this view (sync or async)
    is_default : bool
        Whether this is the default view
    view_func : Callable | Callable[..., Awaitable] or None
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
    # True when view_func is a coroutine function. Such views are resolved once
    # (their async body cannot be awaited from the synchronous render path); use
    # a ``data`` callable for per-render liveness. Synchronous views are instead
    # re-invoked every render so their context stays live.
    is_async: bool = False
    # Tracks which lifecycle hooks were supplied on the @app.view decorator, so
    # lazy initialization does not overwrite them from a legacy dict return.
    hooks_from_decorator: dict[str, bool] = field(default_factory=dict)


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
        on_enter: Callable[..., Any] | None = None,
        on_exit: Callable[..., Any] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Create a decorator to register a view.

        The decorated function returns what to render - preferably via
        :func:`wijjit.render_template_string` / :func:`wijjit.render_template`,
        which package the template and its live context. A synchronous view
        function is re-invoked on every render, so any context it computes stays
        current. The legacy ``{"template": ..., "data": {...}}`` dict and a bare
        template string are also accepted.

        Parameters
        ----------
        name : str
            Unique name for this view
        default : bool
            Whether this is the default view (default: False)
        on_enter : callable, optional
            Hook called when navigating to this view. Takes precedence over an
            ``on_enter`` key in a legacy dict return.
        on_exit : callable, optional
            Hook called when navigating away from this view. Takes precedence
            over an ``on_exit`` key in a legacy dict return.

        Returns
        -------
        Callable
            Decorator function

        Examples
        --------
        Inline template (preferred):

        >>> @app.view("main", default=True, on_enter=setup)
        ... def main_view():
        ...     return render_template_string("Hello, {{ name }}!", name="World")

        Load from a file:

        >>> @app.view("dashboard")
        ... def dashboard_view():
        ...     return render_template("dashboard.tui", stats=get_stats())
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # Store the function and create a lazy ViewConfig
            # We'll extract the actual config when the view is first accessed.
            # Hooks declared on the decorator are set now and take precedence
            # over any on_enter/on_exit in a legacy dict return.
            view_config = ViewConfig(
                name=name,
                template="",  # Will be set lazily
                data=None,  # Will be set lazily
                on_enter=on_enter,  # Decorator-provided (preferred)
                on_exit=on_exit,  # Decorator-provided (preferred)
                is_default=default,
                view_func=func,  # Store the original function
                initialized=False,
            )
            # Remember which hooks came from the decorator so lazy init does
            # not overwrite them from the returned dict.
            view_config.hooks_from_decorator = {
                "on_enter": on_enter is not None,
                "on_exit": on_exit is not None,
            }

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

        This is called lazily the first time a view is accessed. It records the
        view's async-ness, its lifecycle hooks (from a legacy dict return, unless
        already set on the decorator), and a frozen template/data fallback used
        by async views. For synchronous views the per-render template and context
        come from :meth:`evaluate_render`, which re-invokes the view function.

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
            view_config.is_async = asyncio.iscoroutinefunction(view_config.view_func)
            if view_config.is_async:
                raise RuntimeError(
                    f"View '{view_config.name}' has async view function. "
                    f"Use navigate_async() or call from async context."
                )

            # Call the view function ONCE to capture hooks + a frozen fallback.
            result = view_config.view_func()
            self._store_initial_config(view_config, result)

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
            view_config.is_async = asyncio.iscoroutinefunction(view_config.view_func)
            if view_config.is_async:
                result = await view_config.view_func()
            else:
                result = view_config.view_func()
            self._store_initial_config(view_config, result)

    def _store_initial_config(self, view_config: ViewConfig, result: Any) -> None:
        """Populate a ViewConfig from a view function's first return value.

        Handles the :class:`~wijjit.core.templating.RenderedView`, bare-string,
        and legacy ``dict`` return shapes. Lifecycle hooks from a legacy dict are
        applied only when the matching hook was not already supplied on the
        ``@app.view`` decorator.

        Parameters
        ----------
        view_config : ViewConfig
            The view configuration to populate.
        result : Any
            The value returned by the view function.
        """
        if isinstance(result, RenderedView):
            view_config.template = result.template
            view_config.template_file = result.template_file
            frozen: dict[str, Any] = dict(result.context)

            def data_func(**kwargs: Any) -> dict[str, Any]:
                return copy.deepcopy(frozen)

            view_config.data = data_func
        elif isinstance(result, str):
            view_config.template = result
            view_config.template_file = ""
            view_config.data = lambda **kwargs: {}
        elif isinstance(result, dict):
            view_config.template = result.get("template", "")
            view_config.template_file = result.get("template_file", "")
            # Decorator-provided hooks win; otherwise take them from the dict.
            if not view_config.hooks_from_decorator.get("on_enter"):
                view_config.on_enter = result.get("on_enter")
            if not view_config.hooks_from_decorator.get("on_exit"):
                view_config.on_exit = result.get("on_exit")

            data_value = result.get("data", {})
            if callable(data_value):
                view_config.data = data_value
            else:
                static_data: dict[str, Any] = (
                    data_value if isinstance(data_value, dict) else {}
                )

                def data_func(**kwargs: Any) -> dict[str, Any]:
                    # Deep copy so template mutations don't leak across renders.
                    return copy.deepcopy(static_data)

                view_config.data = data_func
        else:
            raise TypeError(
                "View function must return a RenderedView, dict, or str, "
                f"got {type(result)}"
            )

        view_config.initialized = True

    def evaluate_render(
        self, view_config: ViewConfig, params: dict[str, Any] | None = None
    ) -> RenderedView:
        """Resolve the template + context to render for the current frame.

        Synchronous views are re-invoked on every render so any context they
        compute stays live (the whole point of the Flask-style API). Async views
        cannot be awaited from the synchronous render path, so they fall back to
        the template + ``data`` callable captured at initialization.

        Parameters
        ----------
        view_config : ViewConfig
            The view to evaluate (already initialized).
        params : dict, optional
            Navigation parameters passed to the view/data callable.

        Returns
        -------
        RenderedView
            The template (inline or file) and context for this render.
        """
        call_params = params or {}

        if view_config.view_func is not None and not view_config.is_async:
            result = view_config.view_func(**call_params)
            return self._normalize_render(result, call_params)

        # Async or function-less views: use the once-resolved fallback.
        context: dict[str, Any] = {}
        if view_config.data is not None:
            context = view_config.data(**call_params)
        return RenderedView(
            template=view_config.template,
            template_file=view_config.template_file,
            context=context,
        )

    def _normalize_render(self, result: Any, params: dict[str, Any]) -> RenderedView:
        """Coerce a view function's return value into a :class:`RenderedView`.

        Parameters
        ----------
        result : Any
            The view function's return: a ``RenderedView``, a legacy
            ``{"template"/"template_file"/"data": ...}`` dict, or a bare template
            string.
        params : dict
            Navigation parameters, forwarded to a legacy ``data`` callable.

        Returns
        -------
        RenderedView
            Normalized template + context (lifecycle hooks are ignored here -
            they are captured once at initialization).
        """
        if isinstance(result, RenderedView):
            return result
        if isinstance(result, str):
            return RenderedView(template=result)
        if isinstance(result, dict):
            data_value = result.get("data", {})
            if callable(data_value):
                context = data_value(**params)
            elif isinstance(data_value, dict):
                context = dict(data_value)
            else:
                context = {}
            return RenderedView(
                template=result.get("template", ""),
                template_file=result.get("template_file", ""),
                context=context,
            )
        raise TypeError(
            "View function must return a RenderedView, dict, or str, "
            f"got {type(result)}"
        )

    def navigate(
        self,
        view_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Navigate to a different view.

        Automatically detects async context and handles both sync and async
        view functions and lifecycle hooks. When called from an async context
        (which is typical in Wijjit applications), navigation is scheduled as
        an async task to support async hooks.

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

        Notes
        -----
        This method replaces the previous separate navigate() and navigate_async()
        methods. It auto-detects the execution context:
        - If running in async event loop: schedules async navigation task
        - If running in sync context: performs synchronous navigation

        The async path supports both sync and async lifecycle hooks (on_enter,
        on_exit) and view functions, while the sync path only supports sync hooks.
        """
        # Validate the target up front so a bad view name raises synchronously
        # in both the sync and async paths, rather than vanishing into a
        # fire-and-forget task (the previous behavior silently did nothing).
        if view_name not in self.views:
            logger.error(f"Navigation failed: view '{view_name}' not found")
            raise ValueError(f"View '{view_name}' not found")

        # Check if we're running in an async event loop
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running - use sync navigation
            self._navigate_sync_impl(view_name, params)
        else:
            # We're in an async context - schedule a tracked async navigation
            # so the task is not garbage-collected and its exceptions surface.
            self.app._schedule_coroutine(
                self._navigate_async_impl(view_name, params),
                label=f"navigation to view '{view_name}'",
            )

    def _navigate_sync_impl(
        self,
        view_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Synchronous navigation implementation (internal).

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
        RuntimeError
            If view has async hooks or view functions (use async context)
        """
        if view_name not in self.views:
            logger.error(f"Navigation failed: view '{view_name}' not found")
            raise ValueError(f"View '{view_name}' not found")

        params = params or {}

        logger.info(
            f"Navigating from '{self.current_view}' to '{view_name}' "
            f"(params={list(params.keys())})"
        )

        # Initialize the new view (sync)
        self._initialize_view(self.views[view_name])

        # Call current view's on_exit hook
        if self.current_view and self.current_view in self.views:
            current = self.views[self.current_view]
            self._initialize_view(current)
            if current.on_exit:
                if asyncio.iscoroutinefunction(current.on_exit):
                    raise RuntimeError(
                        f"View '{self.current_view}' has async on_exit hook. "
                        f"Navigation must be called from async context (within event loop)."
                    )
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

            # Clear element cache and reconciler state to prevent state bleed between views
            self.app.renderer.clear_element_cache()

        # Switch to new view
        self.current_view = view_name
        self.app.current_view_params = params
        self.app.handler_registry.current_view = view_name

        # Call new view's on_enter hook
        new_view = self.views[view_name]
        if new_view.on_enter:
            if asyncio.iscoroutinefunction(new_view.on_enter):
                raise RuntimeError(
                    f"View '{view_name}' has async on_enter hook. "
                    f"Navigation must be called from async context (within event loop)."
                )
            try:
                new_view.on_enter()
            except Exception as e:
                self.app._handle_error(f"Error in on_enter for view '{view_name}'", e)

        # Trigger re-render
        self.app.needs_render = True

    async def _navigate_async_impl(
        self,
        view_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Asynchronous navigation implementation (internal).

        Supports both sync and async on_exit/on_enter hooks and view functions.
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
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, current.on_exit)
                except Exception as e:
                    self.app._handle_error(
                        f"Error in on_exit for view '{self.current_view}'", e
                    )

            # Clear view-scoped handlers
            self.app.handler_registry.clear_view(self.current_view)

            # Clear view-specific shortcuts
            self.app.wiring_manager.clear_view_shortcuts()

            # Clear element cache and reconciler state to prevent state bleed between views
            self.app.renderer.clear_element_cache()

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
                    loop = asyncio.get_running_loop()
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
