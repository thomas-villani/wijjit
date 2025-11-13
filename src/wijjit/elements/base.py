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
    def render(self) -> str:
        """Render the element to a string.

        Returns
        -------
        str
            Rendered element content

        Notes
        -----
        This method is used for legacy ANSI string-based rendering.
        New elements should implement render_to() instead for cell-based
        rendering with proper theme support.
        """
        pass

    def render_to(self, ctx: PaintContext) -> None:
        """Render the element to a cell-based buffer (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the NEW cell-based rendering API. Elements that implement
        this method can take advantage of:
        - Theme-based styling via ctx.style_resolver
        - Efficient diff rendering via cell buffer
        - Better compositing and effects

        The default implementation bridges to the legacy render() method
        by converting ANSI strings to cells. New elements should override
        this method instead of render() for better performance and styling.

        Examples
        --------
        Implement cell-based rendering in a custom element:

        >>> def render_to(self, ctx):
        ...     style = ctx.style_resolver.resolve_style(self, 'button')
        ...     ctx.write_text(0, 0, self.label, style)
        """
        from wijjit.rendering.ansi_adapter import ansi_string_to_cells

        # Default implementation: bridge to legacy render()
        ansi_str = self.render()
        # cells = ansi_string_to_cells(ansi_str)

        # Write cells to buffer at element's bounds
        lines = ansi_str.split("\n")
        y_offset = 0

        for line in lines:
            if y_offset >= ctx.bounds.height:
                break

            # Convert this line to cells
            line_cells = ansi_string_to_cells(line)

            # Write cells to buffer
            x_offset = 0
            for cell in line_cells:
                if x_offset >= ctx.bounds.width:
                    break

                ctx.buffer.set_cell(
                    ctx.bounds.x + x_offset, ctx.bounds.y + y_offset, cell
                )
                x_offset += 1

            y_offset += 1

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

    def render(self) -> str:
        """Render the container and its children.

        Returns
        -------
        str
            Rendered content
        """
        # Default implementation: render children in order
        return "\n".join(child.render() for child in self.children)


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
        """Handle mouse event by routing to children.

        Parameters
        ----------
        event : MouseEvent
            The mouse event that occurred

        Returns
        -------
        bool
            True if the event was handled, False otherwise
        """
        # Route to children based on position
        for child in self.children:
            if child.bounds and child.bounds.contains(event.x, event.y):
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

    def render(self) -> str:
        """Render the text element.

        Returns
        -------
        str
            The text content (wrapped if bounds have been set)
        """
        return self._wrapped_text if self._wrapped_text is not None else self.text
