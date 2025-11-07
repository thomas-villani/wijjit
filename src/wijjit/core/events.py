"""Event system for Wijjit TUI framework.

This module provides the event system that enables reactive, event-driven
interactions in Wijjit applications. It includes:
- Base Event class and specific event types (KeyEvent, ActionEvent, etc.)
- HandlerRegistry for managing and dispatching event handlers
- Handler scoping (global, view, element) for flexible event handling
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any, List
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """Event type enumeration.

    Defines the different types of events that can occur in a Wijjit app.
    """

    KEY = "key"
    ACTION = "action"
    CHANGE = "change"
    FOCUS = "focus"
    BLUR = "blur"


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

    event_type: Optional[EventType] = None
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

    Attributes
    ----------
    key : str
        The key that was pressed
    modifiers : List[str]
        Modifier keys (ctrl, alt, shift)
    """

    key: str = ""
    modifiers: List[str] = field(default_factory=list)

    def __post_init__(self):
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
    source_element_id: Optional[str] = None
    data: Any = None

    def __post_init__(self):
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

    def __post_init__(self):
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

    def __post_init__(self):
        """Initialize event type."""
        if self.focus_gained:
            self.event_type = EventType.FOCUS
        else:
            self.event_type = EventType.BLUR


@dataclass
class Handler:
    """Event handler registration.

    Encapsulates an event handler callback with its metadata.

    Parameters
    ----------
    callback : Callable[[Event], None]
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

    Attributes
    ----------
    callback : Callable[[Event], None]
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

    callback: Callable[[Event], None]
    scope: HandlerScope
    event_type: Optional[EventType] = None
    view_name: Optional[str] = None
    element_id: Optional[str] = None
    priority: int = 0


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

    def __init__(self):
        """Initialize handler registry."""
        self.handlers: List[Handler] = []
        self.current_view: Optional[str] = None

    def register(
        self,
        callback: Callable[[Event], None],
        scope: HandlerScope = HandlerScope.GLOBAL,
        event_type: Optional[EventType] = None,
        view_name: Optional[str] = None,
        element_id: Optional[str] = None,
        priority: int = 0,
    ) -> Handler:
        """Register an event handler.

        Parameters
        ----------
        callback : Callable[[Event], None]
            Function to call when event is dispatched
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
            h for h in self.handlers
            if not (h.scope == HandlerScope.VIEW and h.view_name == view_name)
        ]

    def dispatch(self, event: Event) -> None:
        """Dispatch an event to matching handlers.

        Handlers are executed in priority order (highest priority first).
        If a handler cancels the event, subsequent handlers are not executed.

        Parameters
        ----------
        event : Event
            The event to dispatch
        """
        # Find matching handlers
        matching = []

        for handler in self.handlers:
            # Check event type match
            if handler.event_type is not None and handler.event_type != event.event_type:
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

        # Execute handlers
        for handler in matching:
            if event.cancelled:
                break
            handler.callback(event)
