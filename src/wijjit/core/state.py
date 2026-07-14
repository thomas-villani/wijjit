"""State management with change detection for Wijjit applications.

This module provides a State class that tracks changes and triggers callbacks
when state values are modified, enabling automatic re-rendering of the UI.
Supports both synchronous and asynchronous callbacks.
"""

import asyncio
from collections import UserDict
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, Literal

from wijjit.exceptions import StateKeyError
from wijjit.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Maximum depth of re-entrant change notification. A sync ``on_change`` /
# ``watch`` callback that writes back to state re-triggers notification; a few
# levels are legitimate (derived state), but an unbounded cycle (e.g. a global
# callback that logs every change *into* state) would otherwise recurse until
# the interpreter crashes. Past this depth we log once and stop, turning a hard
# hang into a diagnosable error.
_MAX_NOTIFY_DEPTH = 50


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

    # Names that collide with an attribute of this class: the dict/UserDict
    # methods (plus "data", UserDict's backing store) and State's own public
    # methods. They are all perfectly legal state *keys* - ``state["items"]``
    # reads and writes ``self.data["items"]`` like any other key, and templates
    # resolve ``{{ state.items }}`` to the key because ``WijjitEnvironment``
    # (core/renderer.py) looks the key up before falling back to the attribute.
    #
    # What they cannot do is round-trip through Python *attribute* access:
    # ``state.items`` finds the bound method (``__getattr__`` only fires when
    # normal lookup fails), so it never reaches the data. We cannot invert that
    # with ``__getattribute__`` without breaking the Mapping protocol itself -
    # ``dict(state)`` calls ``state.keys()``, and internals call ``state.get()``.
    # So attribute-style *writes* of these names are rejected in ``__setattr__``
    # rather than silently storing a value the same syntax cannot read back;
    # subscript access is unrestricted.
    _SHADOWED_NAMES = {
        # dict / UserDict
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
        "data",
        # State public API
        "on_change",
        "off_change",
        "watch",
        "unwatch",
        "batch_update",
        "async_batch_update",
        "set_async",
        "flush_pending_async",
        "reset",
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
        object.__setattr__(
            self, "_loop", None
        )  # Event loop captured while on the loop thread (for cross-thread scheduling)
        object.__setattr__(
            self, "_batch_mode", False
        )  # Track if we're in batch update mode
        object.__setattr__(
            self, "_batch_changes", []
        )  # Queue of (key, old_value, new_value) during batch mode
        object.__setattr__(
            self, "_notify_depth", 0
        )  # Re-entrant notification depth guard (see _MAX_NOTIFY_DEPTH)
        object.__setattr__(
            self, "_error_hook", None
        )  # Optional Callable[[str, BaseException], None] the host app can
        # set (``state._error_hook = fn``) to receive failures from async
        # on_change/watch callbacks that would otherwise only be logged.

        super().__init__(data or {})

    def __deepcopy__(self, memo: dict[int, Any]) -> "State":
        """Create a deep copy of the state data only, excluding callbacks.

        Parameters
        ----------
        memo : dict
            Memoization dictionary for deepcopy

        Returns
        -------
        State
            A new State instance with deep-copied data but no callbacks

        Notes
        -----
        This method is called by copy.deepcopy(). It copies only the state
        data, not the change callbacks or watchers. This is intentional because:
        1. Callbacks are typically bound methods that reference the original app
        2. The copied state is used for template rendering, not modification
        3. Callbacks may contain unpicklable objects (thread locks, etc.)
        """
        import copy

        # Deep copy only the data dictionary
        new_data = copy.deepcopy(dict(self.data), memo)
        # Create new State without callbacks
        result = State(new_data)
        memo[id(self)] = result
        return result

    def copy(self) -> "State":
        """Create a shallow copy of the state data, excluding callbacks.

        Returns
        -------
        State
            A new State instance with the same data but no callbacks or
            watchers.

        Notes
        -----
        This override is required. ``UserDict.copy`` reassigns ``self.data``
        on the instance, which ``State.__setattr__`` rejects (``data`` is the
        backing store and replacing it wholesale would fire no change
        callbacks). Inheriting it therefore raised ``StateKeyError`` on every
        call. Callbacks are dropped for the same reason as in
        :meth:`__deepcopy__`: they are bound to the originating app.
        """
        return State(dict(self.data))

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item and trigger change callbacks.

        Parameters
        ----------
        key : str
            The state key
        value : Any
            The new value

        Notes
        -----
        Any key is allowed, including names that shadow a State or dict method
        (``state["items"]``). See :attr:`_SHADOWED_NAMES` for what that costs.
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

        Raises
        ------
        StateKeyError
            If ``name`` shadows a State or dict method (see
            :attr:`_SHADOWED_NAMES`). The key itself is legal - use
            ``state[name] = value``.
        """
        if name.startswith("_"):
            # Private attributes are set normally.
            object.__setattr__(self, name, value)
        elif name == "data":
            # UserDict stores its backing dict in ``self.data``. This branch
            # must stay ahead of the _SHADOWED_NAMES guard below: UserDict's
            # __init__ assigns ``self.data = {}`` before ``data`` exists in
            # __dict__, and rejecting that would make State unconstructible.
            # Afterwards, reject ``state.data = {...}``: it would silently
            # replace the whole store and fire no change callbacks.
            if "data" not in self.__dict__:
                object.__setattr__(self, name, value)
            else:
                raise StateKeyError(
                    "'data' is State's backing store, so 'state.data = ...' "
                    "would replace all state without firing change callbacks. "
                    "To replace all state use state.reset(new_dict); to store a "
                    "value under the key 'data' use state['data'] = value."
                )
        elif name in self._SHADOWED_NAMES:
            # The key is legal, but this *syntax* cannot read it back:
            # ``state.items`` finds the bound method, never the data. Refuse
            # the write rather than store a value the same expression cannot
            # retrieve.
            raise StateKeyError(
                f"'{name}' shadows State.{name}, so 'state.{name}' reads back "
                f"the method, not your value. Use state['{name}'] = value "
                f"instead - the key itself is fine, and templates resolve "
                f"{{{{ state.{name} }}}} to it."
            )
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

    def off_change(
        self,
        callback: (
            Callable[[str, Any, Any], None] | Callable[[str, Any, Any], Awaitable[None]]
        ),
    ) -> None:
        """Unregister a global state-change callback.

        The counterpart to :meth:`on_change` (mirrors :meth:`watch` /
        :meth:`unwatch`). Removing a callback that was never registered is a
        no-op.

        Parameters
        ----------
        callback : callable or async callable
            The callback previously passed to :meth:`on_change`.
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            callback_name = getattr(callback, "__name__", repr(callback))
            logger.debug(f"Unregistered global state change callback: {callback_name}")

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

    class _BatchContext:
        """Context manager for batch state updates.

        Parameters
        ----------
        state : State
            The state object to batch updates for
        """

        def __init__(self, state: "State") -> None:
            self.state = state

        def __enter__(self) -> "State":
            """Enter batch mode."""
            self.state._batch_mode = True
            self.state._batch_changes = []
            return self.state

        def __exit__(
            self,
            exc_type: type | None,
            exc_val: BaseException | None,
            exc_tb: Any,
        ) -> Literal[False]:
            """Exit batch mode and trigger callbacks for all changes.

            Only triggers callbacks once, passing all changes that occurred.
            """
            self.state._batch_mode = False

            # If there were any changes, trigger a single batch callback
            if self.state._batch_changes and not exc_val:
                # Get unique keys that changed (use the last old/new values)
                changes_by_key: dict[str, tuple[Any, Any]] = {}
                for key, old_value, new_value in self.state._batch_changes:
                    if key not in changes_by_key:
                        # First change for this key - record original old value
                        changes_by_key[key] = (old_value, new_value)
                    else:
                        # Subsequent changes - keep original old, update new
                        original_old, _ = changes_by_key[key]
                        changes_by_key[key] = (original_old, new_value)

                # Trigger callbacks once for each unique key that actually changed
                for key, (old_value, new_value) in changes_by_key.items():
                    if old_value != new_value:
                        # Temporarily disable batch mode to allow _trigger_change to work
                        self.state._batch_mode = False
                        self.state._trigger_change(key, old_value, new_value)

            self.state._batch_changes = []
            return False  # Don't suppress exceptions

    def batch_update(self) -> _BatchContext:
        """Context manager for batch state updates.

        Use this to update multiple state values while suppressing intermediate
        callbacks. Callbacks are triggered once at the end of the batch for
        each key that actually changed.

        Returns
        -------
        _BatchContext
            Context manager for batch updates

        Examples
        --------
        >>> state = State({'a': 1, 'b': 2})
        >>> with state.batch_update():
        ...     state['a'] = 10
        ...     state['b'] = 20
        ...     state['a'] = 100  # Only this final value is used
        # Callbacks triggered once for 'a' (1 -> 100) and once for 'b' (2 -> 20)

        Notes
        -----
        For async callbacks, this method schedules them as background tasks
        but cannot await their completion. Use :meth:`async_batch_update` in
        async contexts for proper async callback handling.
        """
        return self._BatchContext(self)

    class _AsyncBatchContext:
        """Async context manager for batch state updates.

        This context manager properly awaits async callbacks when exiting.

        Parameters
        ----------
        state : State
            The state object to batch updates for
        """

        def __init__(self, state: "State") -> None:
            self.state = state

        async def __aenter__(self) -> "State":
            """Enter batch mode."""
            self.state._batch_mode = True
            self.state._batch_changes = []
            return self.state

        async def __aexit__(
            self,
            exc_type: type | None,
            exc_val: BaseException | None,
            exc_tb: Any,
        ) -> bool:
            """Exit batch mode and await callbacks for all changes.

            Properly awaits all async callbacks before returning.
            """
            self.state._batch_mode = False

            # If there were any changes, trigger callbacks
            if self.state._batch_changes and not exc_val:
                # Get unique keys that changed (use the last old/new values)
                changes_by_key: dict[str, tuple[Any, Any]] = {}
                for key, old_value, new_value in self.state._batch_changes:
                    if key not in changes_by_key:
                        # First change for this key - record original old value
                        changes_by_key[key] = (old_value, new_value)
                    else:
                        # Subsequent changes - keep original old, update new
                        original_old, _ = changes_by_key[key]
                        changes_by_key[key] = (original_old, new_value)

                # Trigger callbacks once for each unique key that actually changed
                for key, (old_value, new_value) in changes_by_key.items():
                    if old_value != new_value:
                        # Use async version to properly await callbacks
                        await self.state._trigger_change_async(
                            key, old_value, new_value
                        )

            self.state._batch_changes = []
            return False  # Don't suppress exceptions

    def async_batch_update(self) -> _AsyncBatchContext:
        """Async context manager for batch state updates.

        Use this in async contexts to update multiple state values while
        suppressing intermediate callbacks. All async callbacks are properly
        awaited when the context manager exits.

        Returns
        -------
        _AsyncBatchContext
            Async context manager for batch updates

        Examples
        --------
        >>> state = State({'a': 1, 'b': 2})
        >>> async with state.async_batch_update():
        ...     state['a'] = 10
        ...     state['b'] = 20
        ...     state['a'] = 100  # Only this final value is used
        # Callbacks awaited for 'a' (1 -> 100) and 'b' (2 -> 20)

        Notes
        -----
        This method should be preferred over :meth:`batch_update` when in an
        async context, as it ensures all async callbacks complete before
        continuing execution.
        """
        return self._AsyncBatchContext(self)

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

        If in batch mode, changes are queued instead of triggering callbacks.
        """
        # If in batch mode, queue the change instead of triggering immediately
        if self._batch_mode:
            self._batch_changes.append((key, old_value, new_value))
            return

        # Guard against unbounded re-entrant notification (a sync callback that
        # keeps writing back to state). Log once at the threshold and stop.
        if self._notify_depth >= _MAX_NOTIFY_DEPTH:
            if self._notify_depth == _MAX_NOTIFY_DEPTH:
                logger.error(
                    "State change notification exceeded max depth "
                    f"({_MAX_NOTIFY_DEPTH}) at key '{key}'. A change callback is "
                    "likely writing back to state in a cycle; stopping to avoid "
                    "infinite recursion."
                )
            return

        self._notify_depth += 1
        try:
            self._dispatch_change(key, old_value, new_value)
        finally:
            self._notify_depth -= 1

    def _on_state_task_done(
        self, task: "asyncio.Task[Any]", *, name: str, kind: str
    ) -> None:
        """Retire a completed async state-callback task and surface errors.

        Registered as the ``add_done_callback`` for every task created by
        :meth:`_schedule_state_coroutine`, whether scheduled directly on the
        loop thread or created on the loop thread on behalf of a worker
        thread. Ensures ``task.exception()`` is always retrieved (so asyncio
        never logs "Task exception was never retrieved") and routes any
        exception to the optional ``_error_hook`` set by the host app, falling
        back to logging when no hook is set.

        Parameters
        ----------
        task : asyncio.Task
            The completed task.
        name : str
            Name of the callback that raised (for diagnostics).
        kind : str
            Either ``"callback"`` or ``"watcher"`` (for diagnostics).
        """
        self._pending_tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is None:
            return
        message = f"Error in async state {kind} '{name}'"
        hook = self._error_hook
        if hook is not None:
            try:
                hook(message, exc)
                return
            except Exception:
                logger.exception("State error hook failed")
        logger.error(f"{message}: {exc}", exc_info=exc)

    def _schedule_state_coroutine(
        self, coro: Any, callback_name: str, kind: str
    ) -> None:
        """Schedule an async state callback safely from any thread.

        Parameters
        ----------
        coro : Coroutine
            The already-created coroutine to run. Always consumed (scheduled
            or closed) so no "coroutine was never awaited" warning is emitted.
        callback_name : str
            Name of the callback (for diagnostics).
        kind : str
            Either ``"callback"`` or ``"watcher"`` (for diagnostics).

        Notes
        -----
        When invoked on the event-loop thread, the coroutine is scheduled with
        ``create_task`` (thread-safe in that context) and the loop is captured
        for later cross-thread use. When invoked from a worker thread, task
        *creation* itself is hopped onto the loop thread via
        ``call_soon_threadsafe`` rather than using
        ``run_coroutine_threadsafe`` directly: this way the resulting task is
        added to ``_pending_tasks`` (and all mutation of that set happens on
        the loop thread), so it is visible to both
        :meth:`flush_pending_async` and the event loop's shutdown cancel
        sweep. In both cases the task's completion is tracked via
        :meth:`_on_state_task_done`, which retrieves ``task.exception()`` so
        failures are never silently dropped.

        If no loop is available the coroutine cannot run and a warning is
        logged. Uses ``get_running_loop`` (not the deprecated
        ``get_event_loop``).

        The one residual race: a callback scheduled (via
        ``call_soon_threadsafe``) after the event loop's shutdown sweep has
        already taken its snapshot of ``_pending_tasks`` can still be
        orphaned - there is no way to make an after-the-fact scheduling
        visible to a sweep that already ran.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # On the event-loop thread: create_task is safe. Capture the loop
            # so callbacks fired later from worker threads can reach it.
            object.__setattr__(self, "_loop", loop)
            task = loop.create_task(coro)
            self._pending_tasks.add(task)
            task.add_done_callback(
                partial(self._on_state_task_done, name=callback_name, kind=kind)
            )
            return

        captured = self._loop
        if captured is not None and captured.is_running():
            # Called from a worker thread: hop *task creation* to the loop
            # thread so the task lands in _pending_tasks uniformly and all
            # set mutation stays on the loop thread.
            def _create_tracked(coro: Any = coro) -> None:
                task = captured.create_task(coro)
                self._pending_tasks.add(task)
                task.add_done_callback(
                    partial(self._on_state_task_done, name=callback_name, kind=kind)
                )

            try:
                captured.call_soon_threadsafe(_create_tracked)
            except RuntimeError:
                # Loop closed between the is_running() check and scheduling.
                coro.close()
                logger.warning(
                    f"Cannot invoke async state {kind} '{callback_name}': "
                    f"event loop closed"
                )
            return

        # No event loop available - cannot run the coroutine.
        coro.close()
        logger.warning(
            f"Cannot invoke async state {kind} '{callback_name}' "
            f"outside of async context"
        )

    def _dispatch_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Invoke global callbacks and key watchers for a change.

        Separated from :meth:`_trigger_change` so the re-entrancy depth guard
        wraps the actual dispatch.

        Parameters
        ----------
        key : str
            The state key that changed.
        old_value : Any
            The previous value.
        new_value : Any
            The new value.
        """
        # Trigger global change callbacks
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Schedule async callback safely (handles cross-thread).
                    self._schedule_state_coroutine(
                        callback(key, old_value, new_value),
                        callback.__name__,
                        "callback",
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
                        # Schedule async watcher safely (handles cross-thread).
                        self._schedule_state_coroutine(
                            callback(key, old_value, new_value),
                            callback.__name__,
                            "watcher",
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
                    loop = asyncio.get_running_loop()
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
                        loop = asyncio.get_running_loop()
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
        old_value = self.data.get(key)
        super().__setitem__(key, value)

        # Only trigger callbacks if value actually changed
        if old_value != value:
            logger.debug(f"State change (async): {key} = {value} (was {old_value})")
            await self._trigger_change_async(key, old_value, value)

    async def flush_pending_async(self) -> None:
        """Wait for all pending async callback tasks to complete.

        This method waits for any background tasks created by state changes
        (via __setitem__) to finish executing, including tasks created on the
        loop thread on behalf of a worker-thread state mutation (see
        :meth:`_schedule_state_coroutine`) and tasks spawned *by* those
        callbacks while they run.

        Notes
        -----
        Useful for testing or ensuring cleanup before shutdown. In normal
        operation, you usually want fire-and-forget behavior for callbacks.

        An initial ``await asyncio.sleep(0)`` gives a just-scheduled
        ``call_soon_threadsafe`` task-creator (worker-thread path) a chance to
        run before the set is even sampled, so its task is visible here. The
        loop then keeps gathering until the set is empty, since a callback
        can itself trigger further state changes whose tasks are added to
        ``_pending_tasks`` while this method is awaiting the current batch.

        Examples
        --------
        >>> state['count'] = 1  # Triggers async callback as background task
        >>> await state.flush_pending_async()  # Wait for callback to finish
        """
        await asyncio.sleep(0)
        while self._pending_tasks:
            logger.debug(
                f"Flushing {len(self._pending_tasks)} pending state callback tasks"
            )
            await asyncio.gather(*list(self._pending_tasks), return_exceptions=True)
            await asyncio.sleep(0)
        logger.debug("All pending state callback tasks completed")

    def update(self, other: dict[str, Any], /, **kwargs: Any) -> None:  # type: ignore[override]
        """Update multiple state values at once.

        Parameters
        ----------
        other : dict
            Dictionary of values to update
        **kwargs : Any
            Additional key-value pairs to update

        Notes
        -----
        Each update triggers change callbacks via __setitem__.
        """
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
