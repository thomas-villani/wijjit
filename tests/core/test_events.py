"""Tests for the event system.

Tests cover:
- Event class creation and properties
- Specific event types (KeyEvent, ActionEvent, etc.)
- Event cancellation
- HandlerRegistry registration and dispatch
- Handler scoping (global, view, element)
- Priority-based execution
"""

import pytest
from datetime import datetime
from wijjit.core.events import (
    Event,
    EventType,
    KeyEvent,
    ActionEvent,
    ChangeEvent,
    FocusEvent,
    Handler,
    HandlerRegistry,
    HandlerScope,
)


class TestEvent:
    """Tests for base Event class."""

    def test_event_creation(self):
        """Test creating a basic event."""
        event = Event(event_type=EventType.KEY)

        assert event.event_type == EventType.KEY
        assert isinstance(event.timestamp, datetime)
        assert event.cancelled is False

    def test_event_cancel(self):
        """Test cancelling an event."""
        event = Event(event_type=EventType.ACTION)

        assert not event.cancelled
        event.cancel()
        assert event.cancelled


class TestKeyEvent:
    """Tests for KeyEvent."""

    def test_key_event_creation(self):
        """Test creating a key event."""
        event = KeyEvent(key="a", modifiers=["ctrl"])

        assert event.event_type == EventType.KEY
        assert event.key == "a"
        assert event.modifiers == ["ctrl"]
        assert isinstance(event.timestamp, datetime)

    def test_key_event_no_modifiers(self):
        """Test key event without modifiers."""
        event = KeyEvent(key="enter")

        assert event.key == "enter"
        assert event.modifiers == []


class TestActionEvent:
    """Tests for ActionEvent."""

    def test_action_event_creation(self):
        """Test creating an action event."""
        event = ActionEvent(
            action_id="submit",
            source_element_id="btn_submit",
            data={"form": "login"}
        )

        assert event.event_type == EventType.ACTION
        assert event.action_id == "submit"
        assert event.source_element_id == "btn_submit"
        assert event.data == {"form": "login"}

    def test_action_event_minimal(self):
        """Test action event with minimal data."""
        event = ActionEvent(action_id="click")

        assert event.action_id == "click"
        assert event.source_element_id is None
        assert event.data is None


class TestChangeEvent:
    """Tests for ChangeEvent."""

    def test_change_event_creation(self):
        """Test creating a change event."""
        event = ChangeEvent(
            element_id="username",
            old_value="alice",
            new_value="bob"
        )

        assert event.event_type == EventType.CHANGE
        assert event.element_id == "username"
        assert event.old_value == "alice"
        assert event.new_value == "bob"


class TestFocusEvent:
    """Tests for FocusEvent."""

    def test_focus_gained_event(self):
        """Test focus gained event."""
        event = FocusEvent(element_id="input1", focus_gained=True)

        assert event.event_type == EventType.FOCUS
        assert event.element_id == "input1"
        assert event.focus_gained is True

    def test_focus_lost_event(self):
        """Test focus lost (blur) event."""
        event = FocusEvent(element_id="input1", focus_gained=False)

        assert event.event_type == EventType.BLUR
        assert event.element_id == "input1"
        assert event.focus_gained is False


class TestHandler:
    """Tests for Handler dataclass."""

    def test_handler_creation(self):
        """Test creating a handler."""
        def callback(event):
            pass

        handler = Handler(
            callback=callback,
            scope=HandlerScope.GLOBAL,
            event_type=EventType.KEY,
            priority=10
        )

        assert handler.callback == callback
        assert handler.scope == HandlerScope.GLOBAL
        assert handler.event_type == EventType.KEY
        assert handler.priority == 10


class TestHandlerRegistry:
    """Tests for HandlerRegistry."""

    def test_registry_initialization(self):
        """Test creating a handler registry."""
        registry = HandlerRegistry()

        assert registry.handlers == []
        assert registry.current_view is None

    def test_register_global_handler(self):
        """Test registering a global handler."""
        registry = HandlerRegistry()
        called = []

        def handler(event):
            called.append(event)

        h = registry.register(
            callback=handler,
            scope=HandlerScope.GLOBAL,
            event_type=EventType.KEY
        )

        assert len(registry.handlers) == 1
        assert h in registry.handlers
        assert h.scope == HandlerScope.GLOBAL
        assert h.event_type == EventType.KEY

    def test_register_view_handler(self):
        """Test registering a view-scoped handler."""
        registry = HandlerRegistry()

        def handler(event):
            pass

        h = registry.register(
            callback=handler,
            scope=HandlerScope.VIEW,
            view_name="main",
            event_type=EventType.ACTION
        )

        assert h.scope == HandlerScope.VIEW
        assert h.view_name == "main"

    def test_register_element_handler(self):
        """Test registering an element-scoped handler."""
        registry = HandlerRegistry()

        def handler(event):
            pass

        h = registry.register(
            callback=handler,
            scope=HandlerScope.ELEMENT,
            element_id="btn1",
            event_type=EventType.ACTION
        )

        assert h.scope == HandlerScope.ELEMENT
        assert h.element_id == "btn1"

    def test_unregister_handler(self):
        """Test unregistering a handler."""
        registry = HandlerRegistry()

        def handler(event):
            pass

        h = registry.register(callback=handler)
        assert len(registry.handlers) == 1

        registry.unregister(h)
        assert len(registry.handlers) == 0

    def test_clear_view_handlers(self):
        """Test clearing view-scoped handlers."""
        registry = HandlerRegistry()

        def handler(event):
            pass

        # Register handlers for different scopes
        h1 = registry.register(callback=handler, scope=HandlerScope.GLOBAL)
        h2 = registry.register(
            callback=handler,
            scope=HandlerScope.VIEW,
            view_name="view1"
        )
        h3 = registry.register(
            callback=handler,
            scope=HandlerScope.VIEW,
            view_name="view2"
        )

        assert len(registry.handlers) == 3

        # Clear view1 handlers
        registry.clear_view("view1")

        assert len(registry.handlers) == 2
        assert h1 in registry.handlers
        assert h2 not in registry.handlers
        assert h3 in registry.handlers

    def test_dispatch_to_global_handler(self):
        """Test dispatching event to global handler."""
        registry = HandlerRegistry()
        called = []

        def handler(event):
            called.append(event)

        registry.register(
            callback=handler,
            scope=HandlerScope.GLOBAL,
            event_type=EventType.KEY
        )

        event = KeyEvent(key="a")
        registry.dispatch(event)

        assert len(called) == 1
        assert called[0] == event

    def test_dispatch_filters_by_event_type(self):
        """Test that handlers only receive matching event types."""
        registry = HandlerRegistry()
        key_called = []
        action_called = []

        def key_handler(event):
            key_called.append(event)

        def action_handler(event):
            action_called.append(event)

        registry.register(
            callback=key_handler,
            event_type=EventType.KEY
        )
        registry.register(
            callback=action_handler,
            event_type=EventType.ACTION
        )

        # Dispatch key event
        key_event = KeyEvent(key="a")
        registry.dispatch(key_event)

        assert len(key_called) == 1
        assert len(action_called) == 0

        # Dispatch action event
        action_event = ActionEvent(action_id="click")
        registry.dispatch(action_event)

        assert len(key_called) == 1
        assert len(action_called) == 1

    def test_dispatch_handles_all_event_types(self):
        """Test handler with no event type filter receives all events."""
        registry = HandlerRegistry()
        called = []

        def handler(event):
            called.append(event)

        registry.register(callback=handler)  # No event_type filter

        registry.dispatch(KeyEvent(key="a"))
        registry.dispatch(ActionEvent(action_id="click"))

        assert len(called) == 2

    def test_dispatch_respects_view_scope(self):
        """Test view-scoped handlers only fire for current view."""
        registry = HandlerRegistry()
        called = []

        def handler(event):
            called.append(event)

        registry.register(
            callback=handler,
            scope=HandlerScope.VIEW,
            view_name="view1",
            event_type=EventType.KEY
        )

        # No current view set - handler shouldn't fire
        event = KeyEvent(key="a")
        registry.dispatch(event)
        assert len(called) == 0

        # Set current view to different view - shouldn't fire
        registry.current_view = "view2"
        registry.dispatch(KeyEvent(key="b"))
        assert len(called) == 0

        # Set current view to matching view - should fire
        registry.current_view = "view1"
        registry.dispatch(KeyEvent(key="c"))
        assert len(called) == 1

    def test_dispatch_respects_element_scope(self):
        """Test element-scoped handlers only fire for matching element."""
        registry = HandlerRegistry()
        called = []

        def handler(event):
            called.append(event)

        registry.register(
            callback=handler,
            scope=HandlerScope.ELEMENT,
            element_id="btn1",
            event_type=EventType.ACTION
        )

        # Event with different element - shouldn't fire
        event1 = ActionEvent(action_id="click", source_element_id="btn2")
        registry.dispatch(event1)
        assert len(called) == 0

        # Event with matching element - should fire
        event2 = ActionEvent(action_id="click", source_element_id="btn1")
        registry.dispatch(event2)
        assert len(called) == 1

    def test_dispatch_priority_ordering(self):
        """Test handlers execute in priority order (highest first)."""
        registry = HandlerRegistry()
        order = []

        def handler1(event):
            order.append(1)

        def handler2(event):
            order.append(2)

        def handler3(event):
            order.append(3)

        # Register in random order with different priorities
        registry.register(callback=handler2, priority=5)
        registry.register(callback=handler3, priority=10)  # Highest
        registry.register(callback=handler1, priority=1)   # Lowest

        event = KeyEvent(key="a")
        registry.dispatch(event)

        # Should execute in priority order: 3, 2, 1
        assert order == [3, 2, 1]

    def test_dispatch_stops_on_cancelled_event(self):
        """Test event dispatch stops if event is cancelled."""
        registry = HandlerRegistry()
        order = []

        def handler1(event):
            order.append(1)
            event.cancel()

        def handler2(event):
            order.append(2)

        registry.register(callback=handler1, priority=10)  # Higher priority
        registry.register(callback=handler2, priority=5)

        event = KeyEvent(key="a")
        registry.dispatch(event)

        # Only first handler should execute
        assert order == [1]
        assert event.cancelled

    def test_dispatch_element_with_element_id_attribute(self):
        """Test element dispatch with element_id attribute."""
        registry = HandlerRegistry()
        called = []

        def handler(event):
            called.append(event)

        registry.register(
            callback=handler,
            scope=HandlerScope.ELEMENT,
            element_id="input1",
            event_type=EventType.CHANGE
        )

        # Event with matching element_id
        event = ChangeEvent(element_id="input1", old_value="a", new_value="b")
        registry.dispatch(event)
        assert len(called) == 1
