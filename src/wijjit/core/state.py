"""State management with change detection for Wijjit applications.

This module provides a State class that tracks changes and triggers callbacks
when state values are modified, enabling automatic re-rendering of the UI.
"""

from collections import UserDict
from collections.abc import Callable
from typing import Any

from wijjit.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class State(UserDict):
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

    def __init__(self, data: dict[str, Any] | None = None):
        # Initialize internal attributes first, before UserDict.__init__
        object.__setattr__(self, "_change_callbacks", [])
        object.__setattr__(self, "_watchers", {})
        super().__init__(data or {})

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item and trigger change callbacks.

        Parameters
        ----------
        key : str
            The state key
        value : Any
            The new value
        """
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

    def on_change(self, callback: Callable) -> None:
        """Register a callback for any state change.

        Parameters
        ----------
        callback : callable
            Function to call when any state changes.
            Signature: callback(key, old_value, new_value)
        """
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.debug(f"Registered global state change callback: {callback_name}")

    def watch(self, key: str, callback: Callable) -> None:
        """Watch a specific state key for changes.

        Parameters
        ----------
        key : str
            The state key to watch
        callback : callable
            Function to call when this key changes.
            Signature: callback(old_value, new_value)
        """
        if key not in self._watchers:
            self._watchers[key] = []

        if callback not in self._watchers[key]:
            self._watchers[key].append(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.debug(f"Registered state watcher for key '{key}': {callback_name}")

    def unwatch(self, key: str, callback: Callable | None = None) -> None:
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
        """Trigger change callbacks.

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
                    callback(old_value, new_value)
                except Exception as e:
                    logger.error(
                        f"Error in state watcher for key '{key}': {e}", exc_info=True
                    )

    def update(self, other: dict[str, Any]) -> None:
        """Update multiple state values at once.

        Parameters
        ----------
        other : dict
            Dictionary of values to update
        """
        for key, value in other.items():
            self[key] = value

    def reset(self, data: dict[str, Any] | None = None) -> None:
        """Reset state to new data.

        Parameters
        ----------
        data : dict, optional
            New state data. If None, clears all state.
        """
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
