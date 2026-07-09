"""Tests that elements chain ``handle_mouse`` to the base class.

Elements override ``handle_mouse`` to consume click events for their own
behavior. They must still delegate to ``Element.handle_mouse`` so the base
``on_double_click`` / ``on_context_menu`` callbacks fire; otherwise those
callbacks are silently dead. This was true of every input element, and of every
display element except ``Table`` -- which delegated only on a fallback path that
row-hit handling made unreachable.

Related: elements that act on a click must check for ``MouseButton.LEFT``. A
right-click has to fall through so a context menu can open, rather than
activating a button or sorting a table column.
"""

from unittest.mock import Mock

import pytest

from wijjit import Button, Checkbox, Radio, Slider, TextInput, Toggle
from wijjit.elements.display.barchart import BarChart
from wijjit.elements.display.contentview import ContentView
from wijjit.elements.display.link import Link
from wijjit.elements.display.list import ListView
from wijjit.elements.display.logview import LogView
from wijjit.elements.display.pager import Pager
from wijjit.elements.display.tabbed_panel import TabbedPanel
from wijjit.elements.display.table import Table
from wijjit.elements.display.tree import Tree
from wijjit.layout.bounds import Bounds
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


def _right_click(x: int = 0, y: int = 0) -> MouseEvent:
    return MouseEvent(x=x, y=y, button=MouseButton.RIGHT, type=MouseEventType.CLICK)


def _double_click(x: int = 0, y: int = 0) -> MouseEvent:
    return MouseEvent(
        x=x, y=y, button=MouseButton.LEFT, type=MouseEventType.DOUBLE_CLICK
    )


def _left_click(x: int = 0, y: int = 0) -> MouseEvent:
    return MouseEvent(x=x, y=y, button=MouseButton.LEFT, type=MouseEventType.CLICK)


# Representative inputs across the different override shapes (plain, scroll,
# drag, autocomplete). Instantiated with no required args.
INPUT_FACTORIES = [
    pytest.param(lambda: Button(label="ok"), id="button"),
    pytest.param(lambda: TextInput(), id="textinput"),
    pytest.param(lambda: Checkbox(label="x"), id="checkbox"),
    pytest.param(lambda: Radio(name="group", label="x"), id="radio"),
    pytest.param(lambda: Toggle(), id="toggle"),
    pytest.param(lambda: Slider(), id="slider"),
]

# Display elements that override handle_mouse.
DISPLAY_FACTORIES = [
    pytest.param(lambda: Table(data=[{"a": 1}], columns=["a"]), id="table"),
    pytest.param(lambda: Tree(data=[{"label": "a", "value": "a"}]), id="tree"),
    pytest.param(lambda: ListView(items=["a"]), id="listview"),
    pytest.param(lambda: LogView(), id="logview"),
    pytest.param(lambda: ContentView(content="x"), id="contentview"),
    pytest.param(lambda: BarChart(data=[("a", 1)]), id="barchart"),
    pytest.param(lambda: Link(text="x"), id="link"),
    pytest.param(lambda: Pager(), id="pager"),
    pytest.param(lambda: TabbedPanel(), id="tabbedpanel"),
]

ALL_FACTORIES = INPUT_FACTORIES + DISPLAY_FACTORIES


@pytest.mark.asyncio
@pytest.mark.parametrize("factory", ALL_FACTORIES)
async def test_context_menu_callback_fires(factory):
    """Right-click invokes on_context_menu on every element."""
    element = factory()
    element.bounds = Bounds(0, 0, 20, 6)
    element.on_context_menu = Mock()

    handled = await element.handle_mouse(_right_click())

    assert handled is True
    element.on_context_menu.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("factory", ALL_FACTORIES)
async def test_double_click_callback_fires(factory):
    """Double-click invokes on_double_click on every element."""
    element = factory()
    element.bounds = Bounds(0, 0, 20, 6)
    element.on_double_click = Mock()

    handled = await element.handle_mouse(_double_click())

    assert handled is True
    element.on_double_click.assert_called_once()


@pytest.mark.asyncio
async def test_right_click_does_not_activate_button():
    """A right-click must not activate a button; it falls through to the router."""
    button = Button(label="ok")
    button.on_click = Mock()

    handled = await button.handle_mouse(_right_click())

    assert handled is False
    button.on_click.assert_not_called()


class TestTableRowCallbacks:
    """Table's row-hit handling must not swallow right- or double-clicks.

    With a header, Rich's layout puts data rows at y >= 3 (top border, header,
    separator). Row hits used to ``return True`` before reaching the base class,
    and did not check the mouse button.
    """

    @staticmethod
    def _table() -> Table:
        table = Table(data=[{"a": 1}, {"a": 2}], columns=["a"], sortable=True)
        table.bounds = Bounds(0, 0, 20, 8)
        return table

    @pytest.mark.asyncio
    async def test_right_click_on_data_row_opens_context_menu(self):
        table = self._table()
        table.on_context_menu = Mock()

        assert await table.handle_mouse(_right_click(x=2, y=3)) is True
        table.on_context_menu.assert_called_once()

    @pytest.mark.asyncio
    async def test_right_click_on_data_row_does_not_fire_row_click(self):
        table = self._table()
        table.on_row_click = Mock()

        await table.handle_mouse(_right_click(x=2, y=3))

        table.on_row_click.assert_not_called()

    @pytest.mark.asyncio
    async def test_right_click_on_header_does_not_sort(self):
        table = self._table()
        table.on_header_click = Mock()
        before = [dict(row) for row in table.data]

        await table.handle_mouse(_right_click(x=2, y=1))

        table.on_header_click.assert_not_called()
        assert [dict(row) for row in table.data] == before

    @pytest.mark.asyncio
    async def test_double_click_on_row_falls_back_to_element_callback(self):
        """Without on_row_double_click, the element-level callback still fires."""
        table = self._table()
        table.on_double_click = Mock()

        assert await table.handle_mouse(_double_click(x=2, y=3)) is True
        table.on_double_click.assert_called_once()

    @pytest.mark.asyncio
    async def test_row_double_click_takes_precedence(self):
        table = self._table()
        table.on_row_double_click = Mock()
        table.on_double_click = Mock()

        assert await table.handle_mouse(_double_click(x=2, y=3)) is True
        table.on_row_double_click.assert_called_once()
        table.on_double_click.assert_not_called()

    @pytest.mark.asyncio
    async def test_left_click_on_row_still_fires_row_click(self):
        table = self._table()
        table.on_row_click = Mock()

        assert await table.handle_mouse(_left_click(x=2, y=3)) is True
        table.on_row_click.assert_called_once()


@pytest.mark.asyncio
async def test_callbacks_absent_do_not_break_click_behavior():
    """Without the callbacks set, normal click handling is unchanged."""
    button = Button(label="ok")
    activated = Mock()
    button.on_click = activated

    handled = await button.handle_mouse(_left_click())

    assert handled is True
    activated.assert_called_once()


@pytest.mark.asyncio
async def test_button_double_click_callback_takes_precedence_over_activation():
    """Setting on_double_click overrides double-click activation on a Button.

    The base handler runs first and claims the event, so the button does not
    also activate. Without the callback, a double-click still activates.
    """
    with_callback = Button(label="ok")
    with_callback.on_click = Mock()
    with_callback.on_double_click = Mock()

    await with_callback.handle_mouse(_double_click())

    with_callback.on_double_click.assert_called_once()
    with_callback.on_click.assert_not_called()

    without_callback = Button(label="ok")
    without_callback.on_click = Mock()

    await without_callback.handle_mouse(_double_click())

    without_callback.on_click.assert_called_once()
