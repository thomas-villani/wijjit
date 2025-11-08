"""Focus management for interactive UI elements.

This module handles focus navigation between focusable elements,
typically using Tab and Shift+Tab keys.
"""


from ..elements.base import Element


class FocusManager:
    """Manages focus across UI elements.

    This class tracks which element has focus and provides methods
    for navigating focus between focusable elements.

    Attributes
    ----------
    elements : list
        List of focusable elements
    current_index : int or None
        Index of currently focused element
    """

    def __init__(self):
        self.elements: list[Element] = []
        self.current_index: int | None = None

    def set_elements(self, elements: list[Element]) -> None:
        """Set the list of focusable elements.

        Preserves focus on the same element (by ID or index) if possible.

        Parameters
        ----------
        elements : list
            List of focusable elements
        """
        # Remember which element was focused (by ID if available)
        focused_id = None
        old_index = self.current_index
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            old_elem = self.elements[self.current_index]
            if hasattr(old_elem, "id") and old_elem.id:
                focused_id = old_elem.id

        # Update elements list
        self.elements = [elem for elem in elements if elem.focusable]

        # Try to restore focus
        if focused_id:
            # Try to find element with same ID
            for i, elem in enumerate(self.elements):
                if hasattr(elem, "id") and elem.id == focused_id:
                    self._set_focus(i)
                    return

        # If we had a focused index, try to focus the same index
        if old_index is not None and old_index < len(self.elements):
            self._set_focus(old_index)
        elif self.elements:
            # Otherwise focus first element
            self.focus_first()
        else:
            self.current_index = None

    def get_focused_element(self) -> Element | None:
        """Get the currently focused element.

        Returns
        -------
        Element or None
            Currently focused element, or None if no element has focus
        """
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            return self.elements[self.current_index]
        return None

    def focus_first(self) -> None:
        """Focus the first focusable element."""
        if self.elements:
            self._set_focus(0)

    def focus_last(self) -> None:
        """Focus the last focusable element."""
        if self.elements:
            self._set_focus(len(self.elements) - 1)

    def focus_next(self) -> bool:
        """Move focus to the next element.

        Returns
        -------
        bool
            True if focus moved, False if already at last element
        """
        if not self.elements:
            return False

        if self.current_index is None:
            self.focus_first()
            return True

        next_index = (self.current_index + 1) % len(self.elements)
        self._set_focus(next_index)
        return True

    def focus_previous(self) -> bool:
        """Move focus to the previous element.

        Returns
        -------
        bool
            True if focus moved, False if already at first element
        """
        if not self.elements:
            return False

        if self.current_index is None:
            self.focus_last()
            return True

        prev_index = (self.current_index - 1) % len(self.elements)
        self._set_focus(prev_index)
        return True

    def focus_element(self, element: Element) -> bool:
        """Focus a specific element.

        Parameters
        ----------
        element : Element
            Element to focus

        Returns
        -------
        bool
            True if element was focused, False if not found
        """
        try:
            index = self.elements.index(element)
            self._set_focus(index)
            return True
        except ValueError:
            return False

    def _set_focus(self, index: int) -> None:
        """Set focus to element at index.

        Parameters
        ----------
        index : int
            Index of element to focus
        """
        # Blur currently focused element
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            self.elements[self.current_index].on_blur()

        # Focus new element
        self.current_index = index
        if 0 <= index < len(self.elements):
            self.elements[index].on_focus()

    def clear(self) -> None:
        """Clear all elements and focus."""
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            self.elements[self.current_index].on_blur()

        self.elements = []
        self.current_index = None
