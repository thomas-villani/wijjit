"""Base classes for UI elements.

This module provides the foundational classes for all interactive UI elements
in Wijjit applications.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING

from ..terminal.input import Key
from ..terminal.mouse import MouseEvent

if TYPE_CHECKING:
    from ..layout.bounds import Bounds


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

    @abstractmethod
    def render(self) -> str:
        """Render the element to a string.

        Returns
        -------
        str
            Rendered element content
        """
        pass

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
            from ..text import wrap_text

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
