"""Event system for Wijjit TUI framework.

This module provides the event system that enables reactive, event-driven
interactions in Wijjit applications. It includes:
- Base Event class and specific event types (KeyEvent, ActionEvent, etc.)
- HandlerRegistry for managing and dispatching event handlers
- Handler scoping (global, view, element) for flexible event handling
- Support for both synchronous and asynchronous event handlers
"""

import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, cast

from wijjit.terminal.mouse import (
    MouseButton,
    MouseEventType,
)

# Import mouse event types from terminal layer
from wijjit.terminal.mouse import (
    MouseEvent as TerminalMouseEvent,
)


class EventType(Enum):
    """Event type enumeration.

    Defines the different types of events that can occur in a Wijjit app.
    """

    KEY = "key"
    ACTION = "action"
    CHANGE = "change"
    FOCUS = "focus"
    BLUR = "blur"
    MOUSE = "mouse"


class HandlerScope(Enum):
    """Handler scope enumeration.

    Defines the scope at which an event handler operates.
    """

    GLOBAL = "global"
    VIEW = "view"
    ELEMENT = "element"


@dataclass
class Event:
    """Base event class.

    All specific event types inherit from this base class.

    Parameters
    ----------
    event_type : Optional[EventType]
        The type of event (set automatically by subclasses)
    timestamp : datetime
        When the event occurred
    cancelled : bool
        Whether the event has been cancelled

    Attributes
    ----------
    event_type : Optional[EventType]
        The type of event
    timestamp : datetime
        When the event occurred
    cancelled : bool
        Whether the event has been cancelled
    """

    event_type: EventType | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    cancelled: bool = False

    def cancel(self) -> None:
        """Cancel the event.

        Cancelled events will not propagate to subsequent handlers.
        """
        self.cancelled = True


@dataclass
class KeyEvent(Event):
    """Keyboard input event.

    Fired when a key is pressed.

    Parameters
    ----------
    key : str
        The key that was pressed
    modifiers : List[str]
        Modifier keys (ctrl, alt, shift)
    key_obj : Optional[Any]
        The original Key object from InputHandler

    Attributes
    ----------
    key : str
        The key that was pressed
    modifiers : List[str]
        Modifier keys (ctrl, alt, shift)
    key_obj : Optional[Any]
        The original Key object from InputHandler
    """

    key: str = ""
    modifiers: list[str] = field(default_factory=list)
    key_obj: Any | None = None

    def __post_init__(self) -> None:
        """Initialize event type."""
        self.event_type = EventType.KEY


@dataclass
class ActionEvent(Event):
    """Action event triggered by UI elements.

    Fired when a button is clicked or similar actions.

    Parameters
    ----------
    action_id : str
        Identifier for the action
    source_element_id : Optional[str]
        ID of the element that triggered the action
    data : Any
        Additional data associated with the action

    Attributes
    ----------
    action_id : str
        Identifier for the action
    source_element_id : Optional[str]
        ID of the element that triggered the action
    data : Any
        Additional data associated with the action
    """

    action_id: str = ""
    source_element_id: str | None = None
    data: Any = None

    def __post_init__(self) -> None:
        """Initialize event type."""
        self.event_type = EventType.ACTION


@dataclass
class ChangeEvent(Event):
    """Value change event for form elements.

    Fired when an input value changes.

    Parameters
    ----------
    element_id : str
        ID of the element whose value changed
    old_value : Any
        Previous value
    new_value : Any
        New value

    Attributes
    ----------
    element_id : str
        ID of the element whose value changed
    old_value : Any
        Previous value
    new_value : Any
        New value
    """

    element_id: str = ""
    old_value: Any = None
    new_value: Any = None

    def __post_init__(self) -> None:
        """Initialize event type."""
        self.event_type = EventType.CHANGE


@dataclass
class FocusEvent(Event):
    """Focus change event.

    Fired when an element gains or loses focus.

    Parameters
    ----------
    element_id : str
        ID of the element
    focus_gained : bool
        True if element gained focus, False if lost

    Attributes
    ----------
    element_id : str
        ID of the element
    focus_gained : bool
        True if element gained focus, False if lost
    """

    element_id: str = ""
    focus_gained: bool = True

    def __post_init__(self) -> None:
        """Initialize event type."""
        if self.focus_gained:
            self.event_type = EventType.FOCUS
        else:
            self.event_type = EventType.BLUR


@dataclass
class MouseEvent(Event):
    """Mouse input event.

    Fired when a mouse event occurs (click, move, scroll, etc.).
    Wraps the terminal layer's MouseEvent to integrate with the
    core event system.

    Parameters
    ----------
    mouse_event : TerminalMouseEvent
        The underlying terminal mouse event
    element_id : Optional[str]
        ID of the element at the mouse position (if any)

    Attributes
    ----------
    mouse_event : TerminalMouseEvent
        The underlying terminal mouse event
    element_id : Optional[str]
        ID of the element at the mouse position
    x : int
        Column position (0-based)
    y : int
        Row position (0-based)
    button : MouseButton
        Button that triggered the event
    mouse_type : MouseEventType
        Type of mouse event (CLICK, PRESS, MOVE, etc.)
    shift : bool
        Whether Shift key was pressed
    alt : bool
        Whether Alt key was pressed
    ctrl : bool
        Whether Ctrl key was pressed
    click_count : int
        Number of clicks (1=single, 2=double)
    """

    mouse_event: TerminalMouseEvent | None = None
    element_id: str | None = None

    def __post_init__(self) -> None:
        """Initialize event type and convenience attributes."""
        self.event_type = EventType.MOUSE

    @property
    def x(self) -> int:
        """Get x coordinate from mouse event."""
        return self.mouse_event.x if self.mouse_event else 0

    @property
    def y(self) -> int:
        """Get y coordinate from mouse event."""
        return self.mouse_event.y if self.mouse_event else 0

    @property
    def button(self) -> MouseButton:
        """Get button from mouse event."""
        return self.mouse_event.button if self.mouse_event else MouseButton.NONE

    @property
    def mouse_type(self) -> MouseEventType:
        """Get mouse event type."""
        return self.mouse_event.type if self.mouse_event else MouseEventType.MOVE

    @property
    def shift(self) -> bool:
        """Get shift modifier state."""
        return self.mouse_event.shift if self.mouse_event else False

    @property
    def alt(self) -> bool:
        """Get alt modifier state."""
        return self.mouse_event.alt if self.mouse_event else False

    @property
    def ctrl(self) -> bool:
        """Get ctrl modifier state."""
        return self.mouse_event.ctrl if self.mouse_event else False

    @property
    def click_count(self) -> int:
        """Get click count."""
        return self.mouse_event.click_count if self.mouse_event else 0


@dataclass
class Handler:
    """Event handler registration.

    Encapsulates an event handler callback with its metadata.
    Supports both synchronous and asynchronous callbacks.

    Parameters
    ----------
    callback : Callable[[Event], None] | Callable[[Event], Awaitable[None]]
        Function to call when event is dispatched (sync or async)
    scope : HandlerScope
        Scope at which this handler operates
    event_type : Optional[EventType]
        Type of event to handle (None for all types)
    view_name : Optional[str]
        View name for view-scoped handlers
    element_id : Optional[str]
        Element ID for element-scoped handlers
    priority : int
        Handler priority (higher = earlier execution)

    Attributes
    ----------
    callback : Callable[[Event], None] | Callable[[Event], Awaitable[None]]
        Function to call when event is dispatched
    scope : HandlerScope
        Scope at which this handler operates
    event_type : Optional[EventType]
        Type of event to handle (None for all types)
    view_name : Optional[str]
        View name for view-scoped handlers
    element_id : Optional[str]
        Element ID for element-scoped handlers
    priority : int
        Handler priority (higher = earlier execution)
    """

    callback: Callable[[Event], None] | Callable[[Event], Awaitable[None]]
    scope: HandlerScope
    event_type: EventType | None = None
    view_name: str | None = None
    element_id: str | None = None
    priority: int = 0

    @property
    def is_async(self) -> bool:
        """Check if this handler is async.

        Returns
        -------
        bool
            True if callback is a coroutine function
        """
        return asyncio.iscoroutinefunction(self.callback)


class HandlerRegistry:
    """Registry for managing and dispatching event handlers.

    The HandlerRegistry maintains a collection of event handlers and provides
    methods for registering, unregistering, and dispatching events to
    appropriate handlers based on scope and priority.

    Attributes
    ----------
    handlers : List[Handler]
        List of registered handlers
    current_view : Optional[str]
        Name of the current view for view-scoped handlers
    """

    def __init__(self) -> None:
        """Initialize handler registry."""
        self.handlers: list[Handler] = []
        self.current_view: str | None = None

    def register(
        self,
        callback: Callable[[Event], None] | Callable[[Event], Awaitable[None]],
        scope: HandlerScope = HandlerScope.GLOBAL,
        event_type: EventType | None = None,
        view_name: str | None = None,
        element_id: str | None = None,
        priority: int = 0,
    ) -> Handler:
        """Register an event handler.

        Supports both synchronous and asynchronous callbacks.

        Parameters
        ----------
        callback : Callable[[Event], None] | Callable[[Event], Awaitable[None]]
            Function to call when event is dispatched (sync or async)
        scope : HandlerScope
            Scope at which this handler operates (default: GLOBAL)
        event_type : Optional[EventType]
            Type of event to handle (None for all types)
        view_name : Optional[str]
            View name for view-scoped handlers
        element_id : Optional[str]
            Element ID for element-scoped handlers
        priority : int
            Handler priority (higher = earlier execution, default: 0)

        Returns
        -------
        Handler
            The registered handler object
        """
        handler = Handler(
            callback=callback,
            scope=scope,
            event_type=event_type,
            view_name=view_name,
            element_id=element_id,
            priority=priority,
        )
        self.handlers.append(handler)
        return handler

    def unregister(self, handler: Handler) -> None:
        """Unregister an event handler.

        Parameters
        ----------
        handler : Handler
            The handler to remove
        """
        if handler in self.handlers:
            self.handlers.remove(handler)

    def clear_view(self, view_name: str) -> None:
        """Clear all handlers for a specific view.

        This is called when navigating away from a view to clean up
        view-scoped handlers.

        Parameters
        ----------
        view_name : str
            Name of the view whose handlers should be cleared
        """
        self.handlers = [
            h
            for h in self.handlers
            if not (h.scope == HandlerScope.VIEW and h.view_name == view_name)
        ]

    def dispatch(self, event: Event) -> None:
        """Dispatch an event to matching handlers (synchronous).

        This method is deprecated and only handles synchronous callbacks.
        For async support, use dispatch_async() instead.

        Handlers are executed in priority order (highest priority first).
        If a handler cancels the event, subsequent handlers are not executed.

        Parameters
        ----------
        event : Event
            The event to dispatch

        Notes
        -----
        This method will skip async handlers. Use dispatch_async() to
        properly handle both sync and async handlers.
        """
        # Find matching handlers
        matching = self._find_matching_handlers(event)

        # Execute handlers (sync only)
        for handler in matching:
            if event.cancelled:
                break
            # Skip async handlers
            if not handler.is_async:
                handler.callback(event)

    async def dispatch_async(
        self, event: Event, executor: ThreadPoolExecutor | None = None
    ) -> None:
        """Dispatch an event to matching handlers (async).

        Supports both synchronous and asynchronous handlers.
        Handlers are executed in priority order (highest priority first).
        If a handler cancels the event, subsequent handlers are not executed.

        Parameters
        ----------
        event : Event
            The event to dispatch
        executor : ThreadPoolExecutor, optional
            Thread pool to use for synchronous handlers. If None, sync
            handlers run directly on the event loop thread (may block).
            If provided, sync handlers are executed in the thread pool
            to prevent blocking the event loop.

        Notes
        -----
        Threading model:
        - Async handlers always execute on the event loop
        - Sync handlers run in executor if provided, otherwise on event loop
        - Running sync handlers on event loop may cause UI freezes if they
          perform blocking operations (file I/O, network calls, sleep, etc.)
        - For production use, configure an executor to run sync handlers safely
        """
        # Find matching handlers
        matching = self._find_matching_handlers(event)

        # Execute handlers
        for handler in matching:
            if event.cancelled:
                break

            # Invoke callback based on type
            if handler.is_async:
                # Cast to async callback type since is_async is True
                async_callback = cast(
                    Callable[[Event], Awaitable[None]], handler.callback
                )
                await async_callback(event)
            else:
                # Handle sync callback
                if executor is not None:
                    # Run sync callback in thread pool to avoid blocking event loop
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(executor, handler.callback, event)
                else:
                    # Run sync callback directly on main thread
                    # WARNING: This may block the event loop if handler does I/O
                    handler.callback(event)

    def _find_matching_handlers(self, event: Event) -> list[Handler]:
        """Find handlers that match the given event.

        Parameters
        ----------
        event : Event
            The event to match

        Returns
        -------
        list of Handler
            Matching handlers sorted by priority (highest first)
        """
        matching = []

        for handler in self.handlers:
            # Check event type match
            if (
                handler.event_type is not None
                and handler.event_type != event.event_type
            ):
                continue

            # Check scope-specific matching
            if handler.scope == HandlerScope.VIEW:
                if handler.view_name != self.current_view:
                    continue
            elif handler.scope == HandlerScope.ELEMENT:
                # For element-scoped handlers, check if event has element_id
                if hasattr(event, "element_id"):
                    if handler.element_id != event.element_id:
                        continue
                elif hasattr(event, "source_element_id"):
                    if handler.element_id != event.source_element_id:
                        continue
                else:
                    # Event doesn't have element info, skip element handlers
                    continue

            matching.append(handler)

        # Sort by priority (highest first)
        matching.sort(key=lambda h: h.priority, reverse=True)

        return matching
