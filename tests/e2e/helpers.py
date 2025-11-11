"""Helper utilities for end-to-end testing.

This module provides utilities for simulating user interactions in e2e tests,
including typing, button clicks, focus navigation, and view rendering.
"""

from typing import Any

from wijjit.core.app import Wijjit
from wijjit.elements.base import Element
from wijjit.elements.input.button import Button
from wijjit.elements.input.text import TextInput
from wijjit.terminal.input import Key, Keys, KeyType


def render_view(
    app: Wijjit, view_name: str | None = None, width: int = 80, height: int = 24
) -> tuple[str, list[Element]]:
    """Render a view and wire up element callbacks.

    This helper simulates what the app does during its render cycle:
    1. Initialize the view
    2. Render template with layout engine
    3. Store positioned elements
    4. Wire up element callbacks (actions, state binding, etc.)

    Parameters
    ----------
    app : Wijjit
        The application instance
    view_name : str, optional
        Name of view to render (default: current view)
    width : int, optional
        Render width (default: 80)
    height : int, optional
        Render height (default: 24)

    Returns
    -------
    tuple of (str, list of Element)
        Rendered output and list of positioned elements
    """
    # Use current view if not specified
    if view_name is None:
        view_name = app.current_view

    if view_name is None or view_name not in app.views:
        raise ValueError(f"View '{view_name}' not found")

    # Initialize view
    view = app.views[view_name]
    app._initialize_view(view)

    # Prepare render context
    context = {**dict(app.state)}
    if view.data:
        context.update(view.data(**app.current_view_params))

    # Add state to context for overlay visibility checks
    context["state"] = app.state

    # Set up global context for template extensions (needed for visibility checks)
    app.renderer.add_global("_wijjit_current_context", context)

    # Render with layout engine
    output, elements, layout_ctx = app.renderer.render_with_layout(
        view.template, context, width, height, overlay_manager=app.overlay_manager
    )

    # Process template-declared overlays (mimic app._render behavior)
    app._sync_template_overlays(layout_ctx)

    # Clean up globals
    app.renderer.add_global("_wijjit_current_context", None)

    # Store positioned elements on app (simulating what run() does)
    app.positioned_elements = elements

    # Update focus manager with focusable elements
    focusable_elements = [
        elem for elem in elements if hasattr(elem, "focusable") and elem.focusable
    ]
    app.focus_manager.set_elements(focusable_elements)

    # Wire up callbacks (action handlers, state binding, etc.)
    app._wire_element_callbacks(elements)

    return output, elements


def get_element_by_id(elements: list[Element], element_id: str) -> Element | None:
    """Find an element by its ID in the positioned elements list.

    Parameters
    ----------
    elements : list of Element
        List of positioned elements from render
    element_id : str
        ID of element to find

    Returns
    -------
    Element or None
        The element with matching ID, or None if not found
    """
    for elem in elements:
        if hasattr(elem, "id") and elem.id == element_id:
            return elem
    return None


def simulate_typing(element: TextInput, text: str) -> None:
    """Simulate typing text into a TextInput element.

    Parameters
    ----------
    element : TextInput
        The text input element to type into
    text : str
        The text to type (each character will trigger a key event)
    """
    if not isinstance(element, TextInput):
        raise TypeError(f"Expected TextInput, got {type(element)}")

    for char in text:
        key = Key(char, KeyType.CHARACTER, char)
        element.handle_key(key)


def simulate_key_press(element: Element, key: Key) -> bool:
    """Simulate a single key press on an element.

    Parameters
    ----------
    element : Element
        The element to send the key to
    key : Key
        The key to press (from Keys constant or custom Key)

    Returns
    -------
    bool
        True if the element handled the key, False otherwise
    """
    if hasattr(element, "handle_key"):
        return element.handle_key(key)
    return False


def simulate_button_click(button: Button) -> None:
    """Simulate clicking a button by sending Enter key.

    Parameters
    ----------
    button : Button
        The button element to activate
    """
    if not isinstance(button, Button):
        raise TypeError(f"Expected Button, got {type(button)}")

    button.handle_key(Keys.ENTER)


def simulate_tab_navigation(app: Wijjit) -> Element | None:
    """Simulate pressing Tab to move focus to next element.

    Parameters
    ----------
    app : Wijjit
        The application instance with focus manager

    Returns
    -------
    Element or None
        The newly focused element, or None if no element focused
    """
    # Use FocusManager's built-in focus_next method
    app.focus_manager.focus_next()
    return app.focus_manager.get_focused_element()


def dispatch_action(app: Wijjit, action_id: str, data: Any = None) -> None:
    """Manually dispatch an action event.

    This helper directly calls the app's action dispatch mechanism,
    useful for testing action handlers.

    Parameters
    ----------
    app : Wijjit
        The application instance
    action_id : str
        The action ID to dispatch
    data : Any, optional
        Additional data to pass with the action
    """
    app._dispatch_action(action_id, data)


def assert_element_focused(app: Wijjit, element_id: str) -> None:
    """Assert that a specific element has focus.

    Parameters
    ----------
    app : Wijjit
        The application instance
    element_id : str
        Expected focused element ID

    Raises
    ------
    AssertionError
        If the element is not focused
    """
    focused_elem = app.focus_manager.get_focused_element()
    focused_id = (
        focused_elem.id if (focused_elem and hasattr(focused_elem, "id")) else None
    )
    assert (
        focused_id == element_id
    ), f"Expected {element_id} to be focused, but {focused_id} is focused"


def get_focused_element(app: Wijjit) -> Element | None:
    """Get the currently focused element.

    Parameters
    ----------
    app : Wijjit
        The application instance

    Returns
    -------
    Element or None
        The currently focused element, or None if nothing focused
    """
    return app.focus_manager.get_focused_element()
