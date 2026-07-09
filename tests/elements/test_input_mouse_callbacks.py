"""Tests that input elements chain ``handle_mouse`` to the base class.

Input elements (Button, TextInput, Checkbox, ...) override ``handle_mouse`` to
consume click events for their own behavior. They must still delegate to
``Element.handle_mouse`` so the base ``on_double_click`` / ``on_context_menu``
callbacks fire; otherwise those callbacks are silently dead on every input.
"""

from unittest.mock import Mock

import pytest

from wijjit import Button, Checkbox, Radio, Slider, TextInput, Toggle
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


def _right_click() -> MouseEvent:
    return MouseEvent(x=0, y=0, button=MouseButton.RIGHT, type=MouseEventType.CLICK)


def _double_click() -> MouseEvent:
    return MouseEvent(
        x=0, y=0, button=MouseButton.LEFT, type=MouseEventType.DOUBLE_CLICK
    )


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


@pytest.mark.asyncio
@pytest.mark.parametrize("factory", INPUT_FACTORIES)
async def test_context_menu_callback_fires(factory):
    """Right-click invokes on_context_menu on every input element."""
    element = factory()
    element.on_context_menu = Mock()

    handled = await element.handle_mouse(_right_click())

    assert handled is True
    element.on_context_menu.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("factory", INPUT_FACTORIES)
async def test_double_click_callback_fires(factory):
    """Double-click invokes on_double_click on every input element."""
    element = factory()
    element.on_double_click = Mock()

    handled = await element.handle_mouse(_double_click())

    assert handled is True
    element.on_double_click.assert_called_once()


@pytest.mark.asyncio
async def test_callbacks_absent_do_not_break_click_behavior():
    """Without the callbacks set, normal click handling is unchanged."""
    button = Button(label="ok")
    activated = Mock()
    button.on_click = activated

    left_click = MouseEvent(
        x=0, y=0, button=MouseButton.LEFT, type=MouseEventType.CLICK
    )
    handled = await button.handle_mouse(left_click)

    assert handled is True
    activated.assert_called_once()
