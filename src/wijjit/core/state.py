"""State management with change detection for Wijjit applications.

This module provides a State class that tracks changes and triggers callbacks
when state values are modified, enabling automatic re-rendering of the UI.
Supports both synchronous and asynchronous callbacks.
"""

import asyncio
from collections import UserDict
from collections.abc import Awaitable, Callable
from typing import Any

from wijjit.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class State(UserDict[str, Any]):
    """Application state with change detection.

    This class behaves like a dictionary but tracks changes and can trigger
    callbacks when values are modified. It also supports attribute-style access
    for convenience.

    Parameters
    ----------
    data : dict, optional
        Initial state data

    Attributes
    ----------
    data : dict
        The underlying state dictionary
    _change_callbacks : list
        List of callbacks to trigger on state changes
    _watchers : dict
        Dictionary mapping keys to their specific watchers

    Examples
    --------
    >>> state = State({'count': 0})
    >>> state['count'] = 1  # Triggers change callback
    >>> state.count = 2  # Also triggers change callback (attribute access)
    >>> print(state.count)  # Access via attribute
    2
    """

    # Reserved names that conflict with dict methods
    # These cannot be used as state keys because they will cause issues in templates
    _RESERVED_NAMES = {
        "items",
        "keys",
        "values",
        "get",
        "pop",
        "update",
        "clear",
        "copy",
        "setdefault",
        "popitem",
        "fromkeys",
    }

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        # Initialize internal attributes first, before UserDict.__init__
        object.__setattr__(self, "_change_callbacks", [])
        object.__setattr__(self, "_watchers", {})
        object.__setattr__(
            self, "_async_mode", False
        )  # Track if we're in async context
        object.__setattr__(
            self, "_pending_tasks", set()
        )  # Track pending async callback tasks

        # Validate keys don't conflict with dict methods
        if data:
            reserved_keys = set(data.keys()) & self._RESERVED_NAMES
            if reserved_keys:
                raise ValueError(
                    f"State keys cannot use reserved dict method names: {sorted(reserved_keys)}. "
                    f"These names conflict with dict methods and will cause issues in Jinja2 templates. "
                    f"Please use different key names, such as: "
                    f"{', '.join(f'{k}_list' if k == 'items' else f'{k}_data' for k in sorted(reserved_keys))}"
                )

        super().__init__(data or {})

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item and trigger change callbacks.

        Parameters
        ----------
        key : str
            The state key
        value : Any
            The new value

        Raises
        ------
        ValueError
            If key is a reserved dict method name
        """
        # Validate key doesn't conflict with dict methods
        if key in self._RESERVED_NAMES:
            raise ValueError(
                f"State key '{key}' is reserved (conflicts with dict method). "
                f"Please use a different key name such as '{key}_list' or '{key}_data'. "
                f"In templates, use state['{key}_list'] instead of state.{key}."
            )

        old_value = self.data.get(key)
        super().__setitem__(key, value)

        # Only trigger callbacks if value actually changed
        if old_value != value:
            logger.debug(f"State change: {key} = {value} (was {old_value})")
            self._trigger_change(key, old_value, value)

    def __getattr__(self, name: str) -> Any:
        """Get state value via attribute access.

        Parameters
        ----------
        name : str
            The state key

        Returns
        -------
        Any
            The state value

        Raises
        ------
        AttributeError
            If the key doesn't exist
        """
        if name.startswith("_"):
            # Access to private attributes
            return super().__getattribute__(name)

        try:
            return self.data[name]
        except KeyError as e:
            raise AttributeError(f"State has no attribute '{name}'") from e

    def __setattr__(self, name: str, value: Any) -> None:
        """Set state value via attribute access.

        Parameters
        ----------
        name : str
            The state key
        value : Any
            The new value
        """
        if name.startswith("_") or name == "data":
            # Set private attributes and 'data' (UserDict attribute) normally
            object.__setattr__(self, name, value)
        else:
            # Set as state data
            self[name] = value

    def on_change(
        self,
        callback: (
            Callable[[str, Any, Any], None] | Callable[[str, Any, Any], Awaitable[None]]
        ),
    ) -> None:
        """Register a callback for any state change.

        Supports both synchronous and asynchronous callbacks.

        Parameters
        ----------
        callback : callable or async callable
            Function to call when any state changes.
            Signature: callback(key, old_value, new_value)
            Can be sync or async.
        """
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)
            callback_name = getattr(callback, "__name__", repr(callback))
            is_async = asyncio.iscoroutinefunction(callback)
            logger.debug(
                f"Registered global state change callback: {callback_name} "
                f"(async={is_async})"
            )

    def watch(
        self,
        key: str,
        callback: (
            Callable[[str, Any, Any], None] | Callable[[str, Any, Any], Awaitable[None]]
        ),
    ) -> None:
        """Watch a specific state key for changes.

        Supports both synchronous and asynchronous callbacks.

        Parameters
        ----------
        key : str
            The state key to watch
        callback : callable or async callable
            Function to call when this key changes.
            Signature: callback(key, old_value, new_value)
            Can be sync or async.
        """
        if key not in self._watchers:
            self._watchers[key] = []

        if callback not in self._watchers[key]:
            self._watchers[key].append(callback)
            callback_name = getattr(callback, "__name__", repr(callback))
            is_async = asyncio.iscoroutinefunction(callback)
            logger.debug(
                f"Registered state watcher for key '{key}': {callback_name} "
                f"(async={is_async})"
            )

    def unwatch(
        self,
        key: str,
        callback: (
            Callable[[str, Any, Any], None]
            | Callable[[str, Any, Any], Awaitable[None]]
            | None
        ) = None,
    ) -> None:
        """Stop watching a state key.

        Parameters
        ----------
        key : str
            The state key to stop watching
        callback : callable, optional
            Specific callback to remove. If None, removes all watchers for this key.
        """
        if key not in self._watchers:
            return

        if callback is None:
            del self._watchers[key]
        elif callback in self._watchers[key]:
            self._watchers[key].remove(callback)
            if not self._watchers[key]:
                del self._watchers[key]

    def _trigger_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Trigger change callbacks (synchronous).

        This method handles both sync and async callbacks, but async callbacks
        are scheduled as background tasks without awaiting completion. For proper
        async handling with guaranteed completion, use set_async() instead.

        Parameters
        ----------
        key : str
            The state key that changed
        old_value : Any
            The previous value
        new_value : Any
            The new value

        Notes
        -----
        Async callbacks are tracked in _pending_tasks set for cleanup and monitoring.
        Use flush_pending_async() to wait for all callbacks to complete.
        """
        # Trigger global change callbacks
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Schedule async callback as a task and track it
                    try:
                        loop = asyncio.get_event_loop()
                        task = loop.create_task(callback(key, old_value, new_value))
                        self._pending_tasks.add(task)
                        # Remove task from pending set when done
                        task.add_done_callback(lambda t: self._pending_tasks.discard(t))
                    except RuntimeError:
                        # No event loop running - log warning
                        logger.warning(
                            f"Cannot invoke async state callback '{callback.__name__}' "
                            f"outside of async context"
                        )
                else:
                    # Call sync callback immediately on this thread
                    callback(key, old_value, new_value)
            except Exception as e:
                # Log error but don't stop other callbacks
                logger.error(
                    f"Error in state change callback for key '{key}': {e}",
                    exc_info=True,
                )

        # Trigger specific watchers for this key
        if key in self._watchers:
            for callback in self._watchers[key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # Schedule async callback as a task and track it
                        try:
                            loop = asyncio.get_event_loop()
                            task = loop.create_task(callback(key, old_value, new_value))
                            self._pending_tasks.add(task)
                            task.add_done_callback(
                                lambda t: self._pending_tasks.discard(t)
                            )
                        except RuntimeError:
                            # No event loop running - log warning
                            logger.warning(
                                f"Cannot invoke async state watcher '{callback.__name__}' "
                                f"outside of async context"
                            )
                    else:
                        # Call sync callback immediately on this thread
                        callback(key, old_value, new_value)
                except Exception as e:
                    logger.error(
                        f"Error in state watcher for key '{key}': {e}", exc_info=True
                    )

    async def _trigger_change_async(
        self, key: str, old_value: Any, new_value: Any
    ) -> None:
        """Trigger change callbacks (asynchronous).

        This method properly awaits both sync and async callbacks.
        Use this method when in an async context for proper async handling.

        Parameters
        ----------
        key : str
            The state key that changed
        old_value : Any
            The previous value
        new_value : Any
            The new value
        """
        # Trigger global change callbacks
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(key, old_value, new_value)
                else:
                    # Run sync callback in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, callback, key, old_value, new_value
                    )
            except Exception as e:
                # Log error but don't stop other callbacks
                logger.error(
                    f"Error in state change callback for key '{key}': {e}",
                    exc_info=True,
                )

        # Trigger specific watchers for this key
        if key in self._watchers:
            for callback in self._watchers[key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(key, old_value, new_value)
                    else:
                        # Run sync callback in executor
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None, callback, key, old_value, new_value
                        )
                except Exception as e:
                    logger.error(
                        f"Error in state watcher for key '{key}': {e}", exc_info=True
                    )

    async def set_async(self, key: str, value: Any) -> None:
        """Set a state value and await all triggered callbacks (async).

        This method provides guaranteed completion semantics for state changes.
        Unlike the sync __setitem__, this method awaits all callbacks before
        returning, ensuring state changes are fully processed.

        Parameters
        ----------
        key : str
            The state key
        value : Any
            The new value

        Raises
        ------
        ValueError
            If key is a reserved dict method name

        Notes
        -----
        Use this method when you need to ensure all state change side effects
        have completed before proceeding. Async callbacks are awaited, sync
        callbacks are run in the default executor to avoid blocking.

        Examples
        --------
        >>> state = State()
        >>> async def save_to_db(key, old, new):
        ...     await db.save(key, new)
        >>> state.on_change(save_to_db)
        >>> await state.set_async("user", {"name": "Alice"})
        # Database save is guaranteed to have completed
        """
        # Validate key
        if key in self._RESERVED_NAMES:
            raise ValueError(
                f"State key '{key}' is reserved (conflicts with dict method). "
                f"Please use a different key name such as '{key}_list' or '{key}_data'. "
                f"In templates, use state['{key}_list'] instead of state.{key}."
            )

        old_value = self.data.get(key)
        super().__setitem__(key, value)

        # Only trigger callbacks if value actually changed
        if old_value != value:
            logger.debug(f"State change (async): {key} = {value} (was {old_value})")
            await self._trigger_change_async(key, old_value, value)

    async def flush_pending_async(self) -> None:
        """Wait for all pending async callback tasks to complete.

        This method waits for any background tasks created by state changes
        (via __setitem__) to finish executing.

        Notes
        -----
        Useful for testing or ensuring cleanup before shutdown. In normal
        operation, you usually want fire-and-forget behavior for callbacks.

        Examples
        --------
        >>> state['count'] = 1  # Triggers async callback as background task
        >>> await state.flush_pending_async()  # Wait for callback to finish
        """
        if self._pending_tasks:
            logger.debug(
                f"Flushing {len(self._pending_tasks)} pending state callback tasks"
            )
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            logger.debug("All pending state callback tasks completed")

    def update(self, other: dict[str, Any], /, **kwargs: Any) -> None:  # type: ignore[override]
        """Update multiple state values at once.

        Parameters
        ----------
        other : dict
            Dictionary of values to update
        **kwargs : Any
            Additional key-value pairs to update

        Raises
        ------
        ValueError
            If any key is a reserved dict method name

        Notes
        -----
        This method validates all keys before updating to ensure none are
        reserved. Each update triggers change callbacks via __setitem__.
        """
        # Validate all keys first (from both dict and kwargs)
        all_keys = set(other.keys()) | set(kwargs.keys())
        reserved_found = all_keys & self._RESERVED_NAMES
        if reserved_found:
            raise ValueError(
                f"State keys cannot use reserved dict method names: {sorted(reserved_found)}. "
                f"These names conflict with dict methods and will cause issues in Jinja2 templates. "
                f"Please use different key names, such as: "
                f"{', '.join(f'{k}_list' if k == 'items' else f'{k}_data' for k in sorted(reserved_found))}"
            )

        # All keys are valid, proceed with update
        for key, value in other.items():
            self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def reset(self, data: dict[str, Any] | None = None) -> None:
        """Reset state to new data.

        Parameters
        ----------
        data : dict, optional
            New state data. If None, clears all state.

        Raises
        ------
        ValueError
            If any key is a reserved dict method name
        """
        # Validate keys don't conflict with dict methods
        if data:
            reserved_keys = set(data.keys()) & self._RESERVED_NAMES
            if reserved_keys:
                raise ValueError(
                    f"State keys cannot use reserved dict method names: {sorted(reserved_keys)}. "
                    f"These names conflict with dict methods and will cause issues in Jinja2 templates. "
                    f"Please use different key names, such as: "
                    f"{', '.join(f'{k}_list' if k == 'items' else f'{k}_data' for k in sorted(reserved_keys))}"
                )

        old_data = dict(self.data)
        self.data.clear()

        if data:
            for key, value in data.items():
                super().__setitem__(key, value)

        # Trigger changes for all keys that were removed or modified
        all_keys = set(old_data.keys()) | set(self.data.keys() if data else {})
        for key in all_keys:
            old_value = old_data.get(key)
            new_value = self.data.get(key)
            if old_value != new_value:
                self._trigger_change(key, old_value, new_value)
