"""Tests for base element classes."""

import asyncio

import pytest

from wijjit.elements.base import (
    Container,
    Element,
    _background_tasks,
    invoke_callback,
)
from wijjit.layout.bounds import Bounds
from wijjit.rendering.paint_context import PaintContext


# Concrete test implementation of Element
class TestElement(Element):
    """Test element implementation."""

    def __init__(self, content="test", id=None):
        super().__init__(id)
        self.content = content

    def render(self):
        return self.content

    def render_to(self, ctx: PaintContext) -> None:
        """Render using cell-based rendering."""
        style = ctx.style_resolver.resolve_style(self, "text")
        ctx.write_text(0, 0, self.content, style)


class TestInvokeCallback:
    """Tests for the invoke_callback async-aware dispatcher."""

    def test_sync_callback_returns_value(self):
        """Sync callbacks are invoked immediately and their result returned."""
        assert invoke_callback(lambda x: x + 1, 1) == 2

    @pytest.mark.asyncio
    async def test_async_callback_is_tracked_and_awaitable(self):
        """Async callbacks are scheduled with a retained task reference."""
        done = asyncio.Event()

        async def cb():
            done.set()

        result = invoke_callback(cb)
        assert result is None
        # A strong reference is retained so the task is not GC'd mid-flight.
        assert len(_background_tasks) >= 1

        await asyncio.wait_for(done.wait(), timeout=1.0)
        # Let the done-callback run so the task removes itself.
        await asyncio.sleep(0)
        assert all(
            not t.done() or t not in _background_tasks for t in _background_tasks
        )

    @pytest.mark.asyncio
    async def test_async_callback_exception_is_logged_not_raised(self):
        """An exception in an async callback is logged, not propagated.

        Attaches a handler directly to the 'wijjit' logger (rather than using
        caplog) so the assertion is robust against global logging config that
        other tests may have applied (e.g. configure_logging(None)).
        """
        import logging

        async def boom():
            raise RuntimeError("kaboom")

        records: list[logging.LogRecord] = []
        handler = logging.Handler()
        handler.emit = records.append  # type: ignore[method-assign]
        wlogger = logging.getLogger("wijjit")
        prev_level, prev_propagate = wlogger.level, wlogger.propagate
        wlogger.addHandler(handler)
        wlogger.setLevel(logging.ERROR)
        try:
            # invoke_callback itself must not raise.
            assert invoke_callback(boom) is None
            task = next(iter(_background_tasks))
            # Drain the task without re-raising, then let the done-callback run.
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.sleep(0)
        finally:
            wlogger.removeHandler(handler)
            wlogger.setLevel(prev_level)
            wlogger.propagate = prev_propagate

        assert any("async callback" in r.getMessage() for r in records)


class TestElementBase:
    """Tests for Element base class."""

    def test_create_element(self):
        """Test creating an element."""
        elem = TestElement(id="test1")
        assert elem.id == "test1"
        assert not elem.focused
        assert not elem.focusable
        assert elem.bounds is None

    def test_element_without_id(self):
        """Test creating element without ID."""
        elem = TestElement()
        assert elem.id is None

    def test_on_focus(self):
        """Test focusing an element."""
        elem = TestElement()
        elem.on_focus()
        assert elem.focused

    def test_on_blur(self):
        """Test blurring an element."""
        elem = TestElement()
        elem.on_focus()
        assert elem.focused

        elem.on_blur()
        assert not elem.focused

    def test_set_bounds(self):
        """Test setting element bounds."""
        elem = TestElement()
        bounds = Bounds(x=10, y=20, width=30, height=40)

        elem.set_bounds(bounds)
        assert elem.bounds == bounds

    def test_render(self):
        """Test rendering element."""
        elem = TestElement(content="Hello")
        assert elem.render() == "Hello"

    def test_handle_key_default(self):
        """Test default key handling."""
        from wijjit.terminal.input import Keys

        elem = TestElement()
        # Default implementation returns False
        assert not elem.handle_key(Keys.ENTER)

    def test_on_hover_enter(self):
        """Test hover enter lifecycle method."""
        elem = TestElement()
        assert not elem.hovered

        elem.on_hover_enter()
        assert elem.hovered

    def test_on_hover_exit(self):
        """Test hover exit lifecycle method."""
        elem = TestElement()
        elem.on_hover_enter()
        assert elem.hovered

        elem.on_hover_exit()
        assert not elem.hovered

    @pytest.mark.asyncio
    async def test_handle_mouse_default(self):
        """Test default mouse event handling."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        elem = TestElement()
        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.LEFT, x=10, y=5
        )

        # Default implementation returns False
        result = await elem.handle_mouse(event)
        assert not result

    def test_element_starts_not_hovered(self):
        """Test that elements start with hovered = False."""
        elem = TestElement()
        assert not elem.hovered


class TestContainer:
    """Tests for Container class."""

    def test_create_container(self):
        """Test creating a container."""
        container = Container(id="container1")
        assert container.id == "container1"
        assert len(container.children) == 0

    def test_add_child(self):
        """Test adding a child element."""
        container = Container()
        elem = TestElement()

        container.add_child(elem)
        assert len(container.children) == 1
        assert elem in container.children

    def test_add_multiple_children(self):
        """Test adding multiple children."""
        container = Container()
        elem1 = TestElement()
        elem2 = TestElement()

        container.add_child(elem1)
        container.add_child(elem2)

        assert len(container.children) == 2
        assert elem1 in container.children
        assert elem2 in container.children

    def test_remove_child(self):
        """Test removing a child element."""
        container = Container()
        elem = TestElement()

        container.add_child(elem)
        assert len(container.children) == 1

        container.remove_child(elem)
        assert len(container.children) == 0
        assert elem not in container.children

    def test_remove_nonexistent_child(self):
        """Test removing a child that isn't in the container."""
        container = Container()
        elem = TestElement()

        # Should not raise an error
        container.remove_child(elem)

    def test_get_focusable_children_none(self):
        """Test getting focusable children when none exist."""
        container = Container()
        container.add_child(TestElement())
        container.add_child(TestElement())

        focusable = container.get_focusable_children()
        assert len(focusable) == 0

    def test_get_focusable_children_some(self):
        """Test getting focusable children."""
        container = Container()

        elem1 = TestElement()
        elem2 = TestElement()
        elem2.focusable = True
        elem3 = TestElement()
        elem3.focusable = True

        container.add_child(elem1)
        container.add_child(elem2)
        container.add_child(elem3)

        focusable = container.get_focusable_children()
        assert len(focusable) == 2
        assert elem2 in focusable
        assert elem3 in focusable
        assert elem1 not in focusable

    def test_get_focusable_children_nested(self):
        """Test getting focusable children from nested containers."""
        outer = Container()
        inner = Container()

        elem1 = TestElement()
        elem1.focusable = True

        elem2 = TestElement()
        elem2.focusable = True

        inner.add_child(elem1)
        outer.add_child(inner)
        outer.add_child(elem2)

        focusable = outer.get_focusable_children()
        assert len(focusable) == 2
        assert elem1 in focusable
        assert elem2 in focusable

    # NOTE: Container rendering tests removed - in cell-based rendering,
    # containers don't render themselves. They're logical groupings, and
    # the layout system handles child rendering.


class TestElementMouseCallbacks:
    """Tests for Element mouse event callbacks."""

    @pytest.mark.asyncio
    async def test_on_double_click_callback(self):
        """Test on_double_click callback is invoked on double-click."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        elem = TestElement()
        elem.set_bounds(Bounds(0, 0, 20, 5))

        callback_called = []

        def on_double_click(event):
            callback_called.append(event)

        elem.on_double_click = on_double_click

        event = MouseEvent(
            type=MouseEventType.DOUBLE_CLICK, button=MouseButton.LEFT, x=5, y=2
        )

        result = await elem.handle_mouse(event)
        assert result is True
        assert len(callback_called) == 1
        assert callback_called[0] == event

    @pytest.mark.asyncio
    async def test_on_double_click_not_called_for_single_click(self):
        """Test on_double_click is not called for single clicks."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        elem = TestElement()
        callback_called = []
        elem.on_double_click = lambda e: callback_called.append(e)

        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=2)

        result = await elem.handle_mouse(event)
        assert result is False
        assert len(callback_called) == 0

    @pytest.mark.asyncio
    async def test_on_context_menu_callback(self):
        """Test on_context_menu callback is invoked on right-click."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        elem = TestElement()
        callback_called = []

        def on_context_menu(event):
            callback_called.append(event)
            return [{"label": "Test Item"}]

        elem.on_context_menu = on_context_menu

        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.RIGHT, x=5, y=2
        )

        result = await elem.handle_mouse(event)
        assert result is True
        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_on_context_menu_not_called_for_left_click(self):
        """Test on_context_menu is not called for left clicks."""
        from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

        elem = TestElement()
        callback_called = []
        elem.on_context_menu = lambda e: callback_called.append(e)

        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=2)

        result = await elem.handle_mouse(event)
        assert result is False
        assert len(callback_called) == 0


class TestElementDragDropCallbacks:
    """Tests for Element drag-and-drop callbacks."""

    def test_draggable_default_false(self):
        """Test elements are not draggable by default."""
        elem = TestElement()
        assert elem.draggable is False

    def test_drop_target_default_false(self):
        """Test elements are not drop targets by default."""
        elem = TestElement()
        assert elem.drop_target is False

    def test_drag_callbacks_exist(self):
        """Test drag callback attributes exist and are None by default."""
        elem = TestElement()
        assert elem.on_drag_start is None
        assert elem.on_drag is None
        assert elem.on_drag_end is None
        assert elem.on_drag_over is None
        assert elem.on_drop is None

    def test_can_set_draggable(self):
        """Test setting draggable flag."""
        elem = TestElement()
        elem.draggable = True
        assert elem.draggable is True

    def test_can_set_drop_target(self):
        """Test setting drop_target flag."""
        elem = TestElement()
        elem.drop_target = True
        assert elem.drop_target is True

    def test_can_set_drag_callbacks(self):
        """Test setting drag callback functions."""
        elem = TestElement()

        elem.on_drag_start = lambda e: {"item": "test"}
        elem.on_drag = lambda e, d: None
        elem.on_drag_end = lambda e, d, dropped: None
        elem.on_drag_over = lambda e, d: True
        elem.on_drop = lambda e, d, src: True

        assert elem.on_drag_start is not None
        assert elem.on_drag is not None
        assert elem.on_drag_end is not None
        assert elem.on_drag_over is not None
        assert elem.on_drop is not None
