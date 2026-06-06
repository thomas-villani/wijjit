"""Base classes for UI elements.

This module provides the foundational classes for all interactive UI elements
in Wijjit applications.

Handler Design Notes
--------------------
The Element class uses different signatures for key vs mouse handling:

- ``handle_key(key: Key) -> bool`` is **synchronous**
- ``handle_mouse(event: MouseEvent) -> bool`` is **async**

This is intentional:

1. **Key handlers are typically simple** - text insertion, cursor movement,
   navigation. These rarely need I/O or async state updates.

2. **Mouse handlers often need async operations** - clicking a button may
   trigger an async action, drag-and-drop may need async validation,
   context menus may load data asynchronously.

3. **Performance** - Key events are high-frequency (fast typists generate
   many events). Making them async adds overhead with little benefit.

If a key handler needs async operations, it should schedule the work
(e.g., via asyncio.create_task) rather than blocking the handler chain.
"""

from __future__ import annotations

import asyncio
import weakref
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from wijjit.terminal.input import Key
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.layout.bounds import Bounds
    from wijjit.rendering.paint_context import PaintContext


def invoke_callback(callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Invoke a callback, handling both sync and async functions.

    If the callback is async (returns a coroutine), it will be scheduled
    on the event loop via asyncio.create_task(). The result will be returned
    asynchronously and any exceptions will be logged.

    Parameters
    ----------
    callback : Callable
        The callback function to invoke (sync or async)
    *args : Any
        Positional arguments to pass to the callback
    **kwargs : Any
        Keyword arguments to pass to the callback

    Returns
    -------
    Any
        The return value from sync callbacks, or None for async callbacks
        (since they're scheduled as tasks)

    Examples
    --------
    >>> def sync_handler(value):
    ...     print(f"Got {value}")
    >>> invoke_callback(sync_handler, "hello")
    Got hello

    >>> async def async_handler(value):
    ...     await asyncio.sleep(0.1)
    ...     print(f"Got {value}")
    >>> invoke_callback(async_handler, "hello")  # Schedules task, returns None
    """
    result = callback(*args, **kwargs)
    if asyncio.iscoroutine(result):
        # Schedule async callback on event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(result)
        except RuntimeError:
            # No running loop - this shouldn't happen in normal Wijjit usage
            # but handle gracefully by just running it
            asyncio.run(result)
        return None
    return result


class ElementType(Enum):
    """Type of UI element."""

    DISPLAY = auto()  # Non-interactive display element
    INPUT = auto()  # Text input element
    BUTTON = auto()  # Button element
    SELECTABLE = auto()  # Selectable list/menu element


class Element(ABC):
    """Base class for all UI elements.

    Parameters
    ----------
    id : str, optional
        Unique identifier for this element
    classes : str or list of str or set of str, optional
        CSS class names for styling. Can be:
        - String with space-separated classes: "btn-primary large"
        - List of class names: ["btn-primary", "large"]
        - Set of class names: {"btn-primary", "large"}

    Attributes
    ----------
    id : str or None
        Element identifier
    classes : set of str
        CSS class names for styling
    focusable : bool
        Whether this element can receive focus
    focused : bool
        Whether this element currently has focus
    hovered : bool
        Whether the mouse is currently over this element
    bounds : Bounds or None
        Screen position and size
    element_type : ElementType
        Type of this element
    tab_index : int or None
        Tab order for focus navigation. Lower values receive focus first.
        Elements with None are ordered after elements with explicit tab_index,
        in document order. Set to -1 to exclude from tab navigation while
        remaining focusable (can still receive focus via click or programmatic focus).
    on_double_click : callable or None
        Callback for double-click events. Signature: on_double_click(event: MouseEvent) -> None
    on_context_menu : callable or None
        Callback for context menu (right-click) events. Return a list of menu items
        to display, or None to use default behavior.
        Signature: on_context_menu(event: MouseEvent) -> list | None
    draggable : bool
        Whether this element can be dragged (default: False)
    drop_target : bool
        Whether this element can receive drops (default: False)
    on_drag_start : callable or None
        Callback when drag starts. Return drag data to continue, None to cancel.
        Signature: on_drag_start(event: MouseEvent) -> Any | None
    on_drag : callable or None
        Callback during drag. Signature: on_drag(event: MouseEvent, drag_data: Any) -> None
    on_drag_end : callable or None
        Callback when drag ends. Signature: on_drag_end(event: MouseEvent, drag_data: Any, dropped: bool) -> None
    on_drag_over : callable or None
        Callback to check if drop is allowed. Return True to allow.
        Signature: on_drag_over(event: MouseEvent, drag_data: Any) -> bool
    on_drop : callable or None
        Callback when something is dropped on this element.
        Signature: on_drop(event: MouseEvent, drag_data: Any, source_element: Element) -> bool
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        tab_index: int | None = None,
    ) -> None:
        self.id = id

        # Parse and normalize CSS classes
        if classes is None:
            self.classes: set[str] = set()
        elif isinstance(classes, str):
            # Split space-separated string into set
            self.classes = set(classes.split())
        elif isinstance(classes, list):
            self.classes = set(classes)
        else:
            self.classes = classes

        self.focusable = False
        self.focused = False
        self.hovered = False
        self.bounds: Bounds | None = None
        self.element_type = ElementType.DISPLAY
        self.tab_index = tab_index
        self._parent_frame_ref: weakref.ref[Any] | None = (
            None  # Weak reference to parent Frame
        )

        # State management attributes (used by ElementWiringManager)
        self._state_dict: dict[str, Any] | None = None  # Reference to application state
        self._highlight_state_key: str | None = (
            None  # State key for highlight persistence
        )

        # Mouse event callbacks
        self.on_double_click: Callable[[MouseEvent], None] | None = None
        self.on_context_menu: Callable[[MouseEvent], list[Any] | None] | None = None

        # Drag-and-drop callbacks
        self.draggable: bool = False  # Whether element can be dragged
        self.drop_target: bool = False  # Whether element can receive drops
        self.on_drag_start: Callable[[MouseEvent], Any | None] | None = (
            None  # (event) -> drag_data or None to cancel
        )
        self.on_drag: Callable[[MouseEvent, Any], None] | None = (
            None  # (event, drag_data) - called during drag
        )
        self.on_drag_end: Callable[[MouseEvent, Any, bool], None] | None = (
            None  # (event, drag_data, dropped) - called when drag ends
        )
        self.on_drag_over: Callable[[MouseEvent, Any], bool] | None = (
            None  # (event, drag_data) -> True if can accept drop
        )
        self.on_drop: Callable[[MouseEvent, Any, Element], bool] | None = (
            None  # (event, drag_data, source_element) -> True if handled
        )

    def _state_key(self, property_name: str) -> str | None:
        """Generate a consistent state key for this element.

        State keys follow the convention `{id}:{property}` for predictable
        and consistent naming across all elements.

        Parameters
        ----------
        property_name : str
            The property name (e.g., "scroll", "highlight", "expanded")

        Returns
        -------
        str or None
            The state key in format "{id}:{property}", or None if element has no id

        Examples
        --------
        >>> element = Tree(id="my_tree")
        >>> element._state_key("scroll")
        'my_tree:scroll'
        >>> element._state_key("highlight")
        'my_tree:highlight'
        """
        if self.id:
            return f"{self.id}:{property_name}"
        return None

    def add_class(self, class_name: str) -> None:
        """Add a CSS class to this element.

        Parameters
        ----------
        class_name : str
            CSS class name to add

        Examples
        --------
        >>> button = Button("Click me")
        >>> button.add_class("btn-primary")
        >>> "btn-primary" in button.classes
        True
        """
        self.classes.add(class_name)

    def remove_class(self, class_name: str) -> None:
        """Remove a CSS class from this element.

        Parameters
        ----------
        class_name : str
            CSS class name to remove

        Notes
        -----
        Uses discard() instead of remove() to avoid KeyError if class doesn't exist.

        Examples
        --------
        >>> button = Button("Click me", classes="btn-primary large")
        >>> button.remove_class("large")
        >>> "large" in button.classes
        False
        """
        self.classes.discard(class_name)

    def toggle_class(self, class_name: str) -> None:
        """Toggle a CSS class on this element.

        Parameters
        ----------
        class_name : str
            CSS class name to toggle

        Notes
        -----
        If the class is present, it will be removed. If absent, it will be added.

        Examples
        --------
        >>> button = Button("Click me")
        >>> button.toggle_class("active")
        >>> "active" in button.classes
        True
        >>> button.toggle_class("active")
        >>> "active" in button.classes
        False
        """
        if class_name in self.classes:
            self.classes.remove(class_name)
        else:
            self.classes.add(class_name)

    def has_class(self, class_name: str) -> bool:
        """Check if element has a CSS class.

        Parameters
        ----------
        class_name : str
            CSS class name to check

        Returns
        -------
        bool
            True if element has the class, False otherwise

        Examples
        --------
        >>> button = Button("Click me", classes="btn-primary")
        >>> button.has_class("btn-primary")
        True
        >>> button.has_class("btn-secondary")
        False
        """
        return class_name in self.classes

    @abstractmethod
    def render_to(self, ctx: PaintContext) -> None:
        """Render the element to a cell-based buffer.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the cell-based rendering API. All elements must implement
        this method. It provides:
        - Theme-based styling via ctx.style_resolver
        - Efficient diff rendering via cell buffer
        - Better compositing and effects
        - Direct access to the screen buffer for precise control

        Elements should use the PaintContext methods to render:
        - ctx.write_text() - Write styled text
        - ctx.fill_rect() - Fill rectangular regions
        - ctx.draw_border() - Draw borders
        - ctx.clear() - Clear the element's bounds

        Examples
        --------
        Implement cell-based rendering in a custom element:

        >>> def render_to(self, ctx):
        ...     # Resolve element's style from theme
        ...     style = ctx.style_resolver.resolve_style(self, 'button')
        ...     # Write styled text to buffer
        ...     ctx.write_text(0, 0, self.label, style)
        """
        pass

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the element.

        This method calculates the natural size the element would like to be
        based on its content, without requiring actual rendering. Used by the
        layout engine to determine size constraints.

        Returns
        -------
        tuple[int, int]
            (width, height) in characters/lines

        Notes
        -----
        Default implementation returns minimal size (1, 1). Elements should
        override this to return their actual intrinsic size based on content.
        This is used by the layout engine when sizing is set to "auto".

        Examples
        --------
        TextElement calculates size from text content:

        >>> def get_intrinsic_size(self):
        ...     lines = self.text.split("\\n")
        ...     width = max(visible_length(line) for line in lines)
        ...     height = len(lines)
        ...     return (width, height)
        """
        return (1, 1)

    @property
    def parent_frame(self) -> Any:
        """Get the parent Frame if this element is inside a scrollable frame.

        Returns
        -------
        Frame or None
            Parent frame object, or None if no parent or parent was garbage collected

        Notes
        -----
        Uses weak reference internally to prevent circular references and memory leaks.
        """
        if self._parent_frame_ref is None:
            return None
        return self._parent_frame_ref()

    @parent_frame.setter
    def parent_frame(self, frame: Any) -> None:
        """Set the parent Frame reference.

        Parameters
        ----------
        frame : Frame or None
            Parent frame to set, or None to clear
        """
        if frame is None:
            self._parent_frame_ref = None
        else:
            self._parent_frame_ref = weakref.ref(frame)

    @property
    def supports_dynamic_sizing(self) -> bool:
        """Whether this element supports dynamic sizing.

        Dynamic sizing elements can expand to fill available space and
        report minimal constraints to avoid inflating their parent container.
        This is used by the layout engine to optimize layout calculations.

        Returns
        -------
        bool
            True if element supports dynamic sizing, False otherwise

        Notes
        -----
        Default implementation returns False. Elements that can efficiently
        expand to fill space (like TextArea, Markdown viewers) should override
        this to return True when they are configured with fill sizing.

        Examples
        --------
        TextArea with fill sizing supports dynamic sizing:

        >>> class TextArea(Element):
        ...     def __init__(self, width="auto", height="auto") -> None:
        ...         self.width_spec = width
        ...         self.height_spec = height
        ...
        ...     @property
        ...     def supports_dynamic_sizing(self):
        ...         return self.width_spec == "fill" or self.height_spec == "fill"
        """
        return False

    def handle_key(self, key: Key) -> bool:
        """Handle a key press.

        This method is synchronous by design. See the module docstring for
        the rationale behind the async/sync split between key and mouse handlers.

        Parameters
        ----------
        key : Key
            The key that was pressed

        Returns
        -------
        bool
            True if the key was handled, False otherwise

        Notes
        -----
        If your key handler needs to perform async operations, schedule them
        with ``asyncio.create_task()`` rather than converting this method to
        async. Example::

            def handle_key(self, key: Key) -> bool::

                if key.char == 's' and key.ctrl::

                    asyncio.create_task(self._save_async())
                    return True
                return False
        """
        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle a mouse event.

        Parameters
        ----------
        event : MouseEvent
            The mouse event that occurred

        Returns
        -------
        bool
            True if the event was handled, False otherwise

        Notes
        -----
        This is an async method to support async operations during mouse handling
        (e.g., calling async APIs, awaiting async state updates). Subclasses
        should override this method for custom mouse handling.

        The base implementation checks for double-click and context menu events
        and invokes the corresponding callbacks if set. Subclasses that override
        this method should call super().handle_mouse(event) to preserve this
        behavior, or handle these events themselves.
        """
        # Handle double-click callback
        if event.type == MouseEventType.DOUBLE_CLICK and self.on_double_click:
            self.on_double_click(event)
            return True

        # Handle context menu (right-click) callback
        if (
            event.type == MouseEventType.CLICK
            and event.button == MouseButton.RIGHT
            and self.on_context_menu
        ):
            self.on_context_menu(event)
            return True

        return False

    def on_focus(self) -> None:
        """Called when element gains focus."""
        self.focused = True

    def on_blur(self) -> None:
        """Called when element loses focus."""
        self.focused = False

    def on_hover_enter(self) -> None:
        """Called when mouse enters element."""
        self.hovered = True

    def on_hover_exit(self) -> None:
        """Called when mouse exits element."""
        self.hovered = False

    def set_bounds(self, bounds: Bounds) -> None:
        """Set the element's screen bounds.

        Parameters
        ----------
        bounds : Bounds
            New bounds
        """
        self.bounds = bounds

    # === Virtual DOM Lifecycle Methods ===
    # TODO: should these be abstract methods?

    def on_mount(self) -> None:  # noqa: B027
        """Called when element is first added to the element tree.

        Override this method to perform initialization that requires the
        element to be part of the tree, such as registering event handlers
        or starting animations.

        Notes
        -----
        This is called by the Reconciler when a new element is created
        during reconciliation.
        """
        pass

    def on_unmount(self) -> None:  # noqa: B027
        """Called when element is removed from the element tree.

        Override this method to perform cleanup such as cancelling timers,
        removing event handlers, or releasing resources.

        Notes
        -----
        This is called by the Reconciler when an element is deleted
        during reconciliation.
        """
        pass

    def on_update(  # noqa: B027
        self, changed_props: dict[str, tuple[Any, Any]]
    ) -> None:
        """Called when element props are updated during reconciliation.

        Override this method to respond to prop changes, such as
        recomputing derived state or triggering side effects.

        Parameters
        ----------
        changed_props : dict
            Map of prop_name -> (old_value, new_value) for changed props.
            Does not include ephemeral props (cursor, scroll, etc.)

        Notes
        -----
        This is called by the Reconciler after props have been applied
        but before ephemeral state is restored.

        Examples
        --------
        >>> def on_update(self, changed_props):
        ...     if 'items' in changed_props:
        ...         old_items, new_items = changed_props['items']
        ...         self._recompute_layout()
        """
        pass

    def get_ephemeral_state(self) -> dict[str, Any]:
        """Get ephemeral state that should survive reconciliation.

        Ephemeral state includes cursor positions, scroll offsets, selection
        ranges, and other UI state that should persist even when the element's
        props change. Override this in subclasses to preserve relevant state.

        Returns
        -------
        dict
            Map of state_name -> value. Keys should match attribute names
            on the element for automatic restoration.

        Notes
        -----
        This is called by the Reconciler before applying prop changes.
        The returned state is later passed to restore_ephemeral_state().

        Examples
        --------
        >>> def get_ephemeral_state(self):
        ...     return {
        ...         'cursor_pos': self.cursor_pos,
        ...         'scroll_offset': self.scroll_offset,
        ...     }
        """
        return {}

    def restore_ephemeral_state(self, state: dict[str, Any]) -> None:
        """Restore ephemeral state after reconciliation.

        This method receives the state returned by get_ephemeral_state()
        and should restore it to the element. The default implementation
        uses setattr for keys that match attribute names.

        Parameters
        ----------
        state : dict
            Map of state_name -> value from get_ephemeral_state()

        Notes
        -----
        This is called by the Reconciler after applying prop changes
        and calling on_update().

        Examples
        --------
        >>> def restore_ephemeral_state(self, state):
        ...     super().restore_ephemeral_state(state)
        ...     # Handle special restoration logic
        ...     if 'scroll_offset' in state:
        ...         self.scroll_manager.scroll_to(state['scroll_offset'])
        """
        for key, value in state.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def apply_props(self, props: dict[str, Any]) -> None:
        """Apply props from a VNode, skipping ephemeral props.

        This method applies props to the element, but skips properties
        that are marked as ephemeral (cursor, scroll, selection, etc.)
        since those should be preserved from the existing element.

        Parameters
        ----------
        props : dict
            Props to apply from VNode

        Notes
        -----
        Ephemeral props are defined in wijjit.core.vdom.EPHEMERAL_PROPS.
        """
        from wijjit.core.vdom import EPHEMERAL_PROPS

        for key, value in props.items():
            if key not in EPHEMERAL_PROPS and hasattr(self, key):
                setattr(self, key, value)


class ScrollableElement(Element, ABC):
    """Abstract base class for elements that support scrolling.

    This class provides a standard interface for elements that can scroll
    their content, such as lists, text areas, tables, and frames. It enforces
    implementation of scroll-related methods and provides state persistence
    through the callback system.

    Attributes
    ----------
    scroll_state_key : str or None
        State key for persisting vertical scroll position.
        Defaults to "{id}:scroll" if element has an id.
        Can be explicitly set to override the default.
    on_scroll : Callable[[int], None] or None
        Callback function called when vertical scroll position changes.
        Signature: on_scroll(position: int) -> None
    scroll_state_key_x : str or None
        State key for persisting horizontal scroll position.
        Defaults to "{id}:scroll_x" if element has an id.
        Can be explicitly set to override the default.
    on_scroll_x : Callable[[int], None] or None
        Callback function called when horizontal scroll position changes.
        Signature: on_scroll_x(position: int) -> None

    Notes
    -----
    Subclasses must implement:
    - scroll_position property: Return current scroll offset
    - can_scroll(direction): Check if scrolling is possible

    Subclasses should:
    1. Call self.on_scroll(position) when scroll position changes
    2. The application will wire on_scroll to update state automatically

    State keys follow the convention "{id}:{property}" for consistent naming
    across all elements. For example, an element with id="my_list" will have:
    - scroll_state_key = "my_list:scroll"
    - scroll_state_key_x = "my_list:scroll_x"

    Examples
    --------
    Implement a scrollable list element:

    >>> class ScrollableList(ScrollableElement):
    ...     def __init__(self, items) -> None:
    ...         super().__init__()
    ...         self.items = items
    ...         self._scroll_offset = 0
    ...
    ...     @property
    ...     def scroll_position(self) -> int:
    ...         return self._scroll_offset
    ...
    ...     def can_scroll(self, direction: int) -> bool:
    ...         if direction < 0:  # Up
    ...             return self._scroll_offset > 0
    ...         else:  # Down
    ...             return self._scroll_offset < len(self.items) - 1
    ...
    ...     def scroll_by(self, amount: int):
    ...         old_pos = self._scroll_offset
    ...         self._scroll_offset = max(0, min(self._scroll_offset + amount, len(self.items) - 1))
    ...         if self.on_scroll and old_pos != self._scroll_offset:
    ...             self.on_scroll(self._scroll_offset)
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        tab_index: int | None = None,
    ) -> None:
        """Initialize scrollable element.

        Parameters
        ----------
        id : str, optional
            Element identifier
        classes : str or list of str or set of str, optional
            CSS class names for styling
        tab_index : int, optional
            Tab order for focus navigation
        """
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        # Vertical scroll attributes - auto-generate from id
        self._scroll_state_key_override: str | None = None
        self.on_scroll: Callable[[int], None] | None = None
        # Horizontal scroll attributes - auto-generate from id
        self._scroll_state_key_x_override: str | None = None
        self.on_scroll_x: Callable[[int], None] | None = None

    @property
    def scroll_state_key(self) -> str | None:
        """Get the state key for vertical scroll position.

        Returns the explicitly set key if provided, otherwise auto-generates
        from the element id using the convention "{id}:scroll".

        Returns
        -------
        str or None
            State key for scroll position, or None if no id
        """
        if self._scroll_state_key_override is not None:
            return self._scroll_state_key_override
        return self._state_key("scroll")

    @scroll_state_key.setter
    def scroll_state_key(self, value: str | None) -> None:
        """Set an explicit scroll state key.

        Parameters
        ----------
        value : str or None
            Explicit state key to use, or None to use auto-generated key
        """
        self._scroll_state_key_override = value

    @property
    def scroll_state_key_x(self) -> str | None:
        """Get the state key for horizontal scroll position.

        Returns the explicitly set key if provided, otherwise auto-generates
        from the element id using the convention "{id}:scroll_x".

        Returns
        -------
        str or None
            State key for horizontal scroll position, or None if no id
        """
        if self._scroll_state_key_x_override is not None:
            return self._scroll_state_key_x_override
        return self._state_key("scroll_x")

    @scroll_state_key_x.setter
    def scroll_state_key_x(self, value: str | None) -> None:
        """Set an explicit horizontal scroll state key.

        Parameters
        ----------
        value : str or None
            Explicit state key to use, or None to use auto-generated key
        """
        self._scroll_state_key_x_override = value

    @property
    @abstractmethod
    def scroll_position(self) -> int:
        """Get the current scroll position.

        Returns
        -------
        int
            Current scroll offset (0-based)
        """
        pass

    @abstractmethod
    def can_scroll(self, direction: int) -> bool:
        """Check if the element can scroll in the given direction.

        Parameters
        ----------
        direction : int
            Scroll direction: negative for up/left, positive for down/right

        Returns
        -------
        bool
            True if scrolling in the given direction is possible
        """
        pass


class Container(Element):
    """Base class for elements that contain other elements.

    Parameters
    ----------
    id : str, optional
        Unique identifier
    classes : str or list of str or set of str, optional
        CSS class names for styling
    tab_index : int, optional
        Tab order for focus navigation

    Attributes
    ----------
    children : list
        Child elements
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        tab_index: int | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.children: list[Element] = []

    def add_child(self, element: Element) -> None:
        """Add a child element.

        Parameters
        ----------
        element : Element
            Element to add
        """
        self.children.append(element)

    def remove_child(self, element: Element) -> None:
        """Remove a child element.

        Parameters
        ----------
        element : Element
            Element to remove
        """
        if element in self.children:
            self.children.remove(element)

    def get_focusable_children(self) -> list[Element]:
        """Get all focusable child elements.

        Returns
        -------
        list
            List of focusable elements
        """
        result = []
        for child in self.children:
            if child.focusable:
                result.append(child)
            if isinstance(child, Container):
                result.extend(child.get_focusable_children())
        return result

    def render_to(self, ctx: PaintContext) -> None:
        """Render the container using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Default implementation renders nothing. Containers typically don't
        render themselves but serve as logical groupings for child elements.
        Child rendering is handled by the layout system.
        """
        pass


class OverlayElement(Container):
    """Base class for overlay content elements.

    This class provides a foundation for elements displayed in overlays
    (modals, dropdowns, tooltips). It extends Container to support child
    elements and adds overlay-specific properties.

    Parameters
    ----------
    id : str, optional
        Unique identifier
    classes : str or list of str or set of str, optional
        CSS class names for styling
    tab_index : int, optional
        Tab order for focus navigation
    width : int, optional
        Desired width in characters
    height : int, optional
        Desired height in lines
    centered : bool, optional
        Whether to center the overlay (default: True)

    Attributes
    ----------
    width : int or None
        Overlay width
    height : int or None
        Overlay height
    centered : bool
        Whether overlay should be centered
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        tab_index: int | None = None,
        width: int | None = None,
        height: int | None = None,
        centered: bool = True,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.width = width
        self.height = height
        self.centered = centered

    def handle_key(self, key: Key) -> bool:
        """Handle key press by routing to focused child.

        Parameters
        ----------
        key : Key
            The key that was pressed

        Returns
        -------
        bool
            True if the key was handled, False otherwise
        """
        # Route to focused child
        for child in self.children:
            if child.focused and child.handle_key(key):
                return True
        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse event by routing to child at mouse position.

        Parameters
        ----------
        event : MouseEvent
            The mouse event that occurred

        Returns
        -------
        bool
            True if the event was handled by a child, False otherwise

        Notes
        -----
        This method checks each child to see if the mouse event occurred
        within its bounds. If so, it dispatches the event to that child.
        Children are checked in reverse order so that later children
        (rendered on top) get priority.
        """
        # Check children in reverse order (top to bottom)
        for child in reversed(self.children):
            if child.bounds and child.bounds.contains(event.x, event.y):
                if hasattr(child, "handle_mouse") and callable(child.handle_mouse):
                    if await child.handle_mouse(event):
                        return True
        return False


class TextElement(Element):
    """Simple text display element.

    This element displays static text content. It is non-interactive
    and cannot receive focus.

    Parameters
    ----------
    text : str
        Text content to display
    id : str, optional
        Unique identifier for this element
    classes : str or list of str or set of str, optional
        CSS class names for styling
    wrap : bool, optional
        Whether to wrap text to fit bounds width (default: True)
    html : bool or None, optional
        Whether to parse HTML tags in text content. If None, uses
        app.config['HTML_CONTENT'] setting. Default: None

    Attributes
    ----------
    text : str
        Text content
    wrap : bool
        Whether text wrapping is enabled
    html : bool or None
        HTML parsing mode (None = use global config)
    """

    def __init__(
        self,
        text: str,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        wrap: bool = True,
        html: bool | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.text = text
        self.element_type = ElementType.DISPLAY
        self.focusable = False
        self.wrap = wrap
        self.html = html
        self._wrapped_text: str | None = None

    def set_bounds(self, bounds: Bounds) -> None:
        """Set bounds and wrap text if needed.

        Parameters
        ----------
        bounds : Bounds
            New bounds for the element
        """
        super().set_bounds(bounds)

        # Apply text wrapping if enabled and bounds are available
        if self.wrap and bounds and bounds.width > 0:
            from wijjit.terminal.ansi import wrap_text

            lines = self.text.split("\n")
            wrapped_lines = []
            for line in lines:
                segments = wrap_text(line, bounds.width)
                wrapped_lines.extend(segments)

            self._wrapped_text = "\n".join(wrapped_lines)
        else:
            self._wrapped_text = None

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size based on text content.

        Returns
        -------
        tuple[int, int]
            (width, height) based on text lines

        Notes
        -----
        If HTML mode is enabled, HTML tags are stripped when calculating
        visible width to get accurate sizing.
        """
        from wijjit.terminal.ansi import visible_length

        # Get display text (strip HTML tags if HTML mode)
        display_text = self._get_display_text()
        lines = display_text.split("\n")
        width = max((visible_length(line) for line in lines), default=1)
        height = len(lines)
        return (width, height)

    def _get_display_text(self) -> str:
        """Get text for display, stripping HTML tags if needed.

        Returns
        -------
        str
            Plain text for sizing calculations
        """
        if self._is_html_enabled():
            from wijjit.rendering.html_adapter import strip_html_tags

            return strip_html_tags(self.text)
        return self.text

    def _is_html_enabled(self) -> bool:
        """Check if HTML parsing is enabled for this element.

        Returns
        -------
        bool
            True if HTML should be parsed, False otherwise
        """
        if self.html is not None:
            return self.html
        # Check global config (will need app reference)
        # For now, return False if not explicitly set
        return False

    def render_to(self, ctx: PaintContext) -> None:
        """Render the text element using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        If HTML mode is enabled, HTML tags are parsed and converted to
        styled cells. HTML classes like <span class="text-danger"> are
        resolved through the theme's style definitions.
        """
        text = self._wrapped_text if self._wrapped_text is not None else self.text

        if self._is_html_enabled():
            self._render_html(ctx, text)
        else:
            self._render_plain(ctx, text)

    def _render_plain(self, ctx: PaintContext, text: str) -> None:
        """Render plain text content.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        text : str
            Text to render
        """
        from wijjit.terminal.ansi import clip_to_width

        # Resolve style for text element
        style = ctx.style_resolver.resolve_style(self, "text")

        # Split text by newlines and render each line separately
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if i >= ctx.bounds.height:
                break
            clipped = clip_to_width(line, ctx.bounds.width, ellipsis="")
            ctx.write_text(0, i, clipped, style)

    def _render_html(self, ctx: PaintContext, text: str) -> None:
        """Render HTML content.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        text : str
            HTML text to render
        """
        from wijjit.rendering.html_adapter import html_string_to_cells

        # Parse HTML and convert to cells
        cells = html_string_to_cells(text, style_resolver=ctx.style_resolver)

        # Render cells to buffer, handling line breaks
        x = 0
        y = 0
        for cell in cells:
            # Handle newlines
            if cell.char == "\n":
                x = 0
                y += 1
                continue

            # Stop if we've exceeded bounds
            if y >= ctx.bounds.height:
                break
            if x >= ctx.bounds.width:
                # Move to next line if wrapping, otherwise skip
                if self.wrap:
                    x = 0
                    y += 1
                    if y >= ctx.bounds.height:
                        break
                else:
                    continue

            # Write cell to buffer
            ctx.buffer.set_cell(ctx.bounds.x + x, ctx.bounds.y + y, cell)
            x += 1
