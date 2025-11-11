"""Focus management for interactive UI elements.

This module handles focus navigation between focusable elements,
typically using Tab and Shift+Tab keys.
"""

from wijjit.elements.base import Element
from wijjit.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


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
        old_index = self.current_index
        element_id = (
            self.elements[index].id if 0 <= index < len(self.elements) else None
        )
        logger.debug(
            f"Focus change: index {old_index} -> {index} (element: {element_id})"
        )

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

    def set_focus_filter(self, allowed_elements: list[Element] | None) -> None:
        """Filter focusable elements to a specific subset.

        This is used for focus trapping in overlays. When an overlay traps
        focus, only elements within that overlay are focusable.

        Parameters
        ----------
        allowed_elements : list of Element or None
            Elements that should be focusable, or None to clear filter.
            If provided, only these elements will be in the focus cycle.

        Notes
        -----
        This temporarily restricts focus navigation to the specified elements.
        The original element list is preserved and can be restored by passing
        None or by calling set_elements() again.
        """
        if allowed_elements is None:
            # Clear filter - this would typically be done when restoring
            # from a saved state after overlay closes
            return

        # Save currently focused element before filtering
        old_focused = self.get_focused_element()

        # Filter to only allowed elements
        self.elements = [elem for elem in allowed_elements if elem.focusable]

        # Try to restore focus if the old element is still in the list
        if old_focused and old_focused in self.elements:
            self.focus_element(old_focused)
        elif self.elements:
            # Otherwise focus first element in filtered list
            self.focus_first()
        else:
            self.current_index = None

    def save_state(self) -> tuple[list[Element], int | None]:
        """Save current focus state.

        Returns
        -------
        tuple
            Tuple of (elements list, current_index) that can be restored later

        Notes
        -----
        Used by overlay manager to save focus state before showing an overlay
        with focus trapping enabled.
        """
        return (list(self.elements), self.current_index)

    def restore_state(self, state: tuple[list[Element], int | None]) -> None:
        """Restore focus state from saved state.

        Parameters
        ----------
        state : tuple
            State tuple returned by save_state()

        Notes
        -----
        Restores the complete focus state including the element list and
        focused element. Used when closing an overlay that trapped focus.
        """
        elements, index = state

        # Blur current element before restoring
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            self.elements[self.current_index].on_blur()

        # Restore elements and index
        self.elements = elements
        self.current_index = index

        # Focus the restored element
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            self.elements[self.current_index].on_focus()
