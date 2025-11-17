"""Base classes for UI elements.

This module provides the foundational classes for all interactive UI elements
in Wijjit applications.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING

from wijjit.terminal.input import Key
from wijjit.terminal.mouse import MouseEvent

if TYPE_CHECKING:
    from wijjit.layout.bounds import Bounds
    from wijjit.rendering.paint_context import PaintContext


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

    Attributes
    ----------
    id : str or None
        Element identifier
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
    """

    def __init__(self, id: str | None = None):
        self.id = id
        self.focusable = False
        self.focused = False
        self.hovered = False
        self.bounds: Bounds | None = None
        self.element_type = ElementType.DISPLAY
        self.parent_frame = None  # Reference to parent Frame if this element is inside a scrollable frame

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
        ...     def __init__(self, width="auto", height="auto"):
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

        Parameters
        ----------
        key : Key
            The key that was pressed

        Returns
        -------
        bool
            True if the key was handled, False otherwise
        """
        return False

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle a mouse event.

        Parameters
        ----------
        event : MouseEvent
            The mouse event that occurred

        Returns
        -------
        bool
            True if the event was handled, False otherwise
        """
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


class ScrollableMixin:
    """Mixin class for elements that support scroll state persistence.

    This mixin provides standard attributes and methods for elements that
    need to persist their scroll position to application state. Elements
    that inherit from this mixin can be automatically wired for scroll
    state persistence by the application's callback wiring system.

    Attributes
    ----------
    scroll_state_key : str or None
        State key for persisting scroll position (typically "_scroll_{id}")
    on_scroll : callable or None
        Callback function called when scroll position changes.
        Signature: on_scroll(position: int) -> None

    Notes
    -----
    Elements using this mixin should:
    1. Initialize scroll_state_key in their __init__ (usually via template tags)
    2. Call self.on_scroll(position) when scroll position changes
    3. The application will wire on_scroll to update state automatically
    """

    def __init__(self):
        """Initialize scroll state attributes."""
        self.scroll_state_key: str | None = None
        self.on_scroll: callable | None = None


class Container(Element):
    """Base class for elements that contain other elements.

    Parameters
    ----------
    id : str, optional
        Unique identifier

    Attributes
    ----------
    children : list
        Child elements
    """

    def __init__(self, id: str | None = None):
        super().__init__(id)
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
        width: int | None = None,
        height: int | None = None,
        centered: bool = True,
    ):
        super().__init__(id)
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

    def handle_mouse(self, event: MouseEvent) -> bool:
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
                    if child.handle_mouse(event):
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
    wrap : bool, optional
        Whether to wrap text to fit bounds width (default: True)

    Attributes
    ----------
    text : str
        Text content
    wrap : bool
        Whether text wrapping is enabled
    """

    def __init__(self, text: str, id: str | None = None, wrap: bool = True):
        super().__init__(id)
        self.text = text
        self.element_type = ElementType.DISPLAY
        self.focusable = False
        self.wrap = wrap
        self._wrapped_text: str | None = None

    def set_bounds(self, bounds) -> None:
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
        """
        from wijjit.terminal.ansi import visible_length

        lines = self.text.split("\n")
        width = max((visible_length(line) for line in lines), default=1)
        height = len(lines)
        return (width, height)

    def render_to(self, ctx: PaintContext) -> None:
        """Render the text element using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds
        """
        text = self._wrapped_text if self._wrapped_text is not None else self.text
        # Resolve style for text element
        style = ctx.style_resolver.resolve_style(self, "text")
        ctx.write_text(0, 0, text, style)
