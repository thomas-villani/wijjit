"""Base classes for UI elements.

This module provides the foundational classes for all interactive UI elements
in Wijjit applications.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional, List

from ..terminal.input import Key
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
    bounds : Bounds or None
        Screen position and size
    element_type : ElementType
        Type of this element
    """

    def __init__(self, id: Optional[str] = None):
        self.id = id
        self.focusable = False
        self.focused = False
        self.bounds: Optional[Bounds] = None
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

    def on_focus(self) -> None:
        """Called when element gains focus."""
        self.focused = True

    def on_blur(self) -> None:
        """Called when element loses focus."""
        self.focused = False

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

    def __init__(self, id: Optional[str] = None):
        super().__init__(id)
        self.children: List[Element] = []

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

    def get_focusable_children(self) -> List[Element]:
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

    Attributes
    ----------
    text : str
        Text content
    """

    def __init__(self, text: str, id: Optional[str] = None):
        super().__init__(id)
        self.text = text
        self.element_type = ElementType.DISPLAY
        self.focusable = False

    def render(self) -> str:
        """Render the text element.

        Returns
        -------
        str
            The text content
        """
        return self.text
