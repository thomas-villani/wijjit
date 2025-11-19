"""Hover state management for UI elements.

This module handles hover state tracking when the mouse moves over elements.
It manages transitions between elements and calls appropriate lifecycle methods.
"""

from typing import TYPE_CHECKING

from wijjit.elements.base import Element

if TYPE_CHECKING:
    from wijjit.layout.dirty import DirtyRegionManager


class HoverManager:
    """Manages hover state across UI elements.

    This class tracks which element is currently hovered and provides methods
    for updating hover state when the mouse moves. It ensures proper lifecycle
    methods are called when hover enters and exits elements.

    Attributes
    ----------
    current_element : Element or None
        Currently hovered element, or None if no element is hovered
    """

    def __init__(self) -> None:
        """Initialize hover manager."""
        self.current_element: Element | None = None
        self.dirty_manager: DirtyRegionManager | None = None

    def get_hovered_element(self) -> Element | None:
        """Get the currently hovered element.

        Returns
        -------
        Element or None
            Currently hovered element, or None if no element is hovered
        """
        return self.current_element

    def set_hovered(self, element: Element | None) -> bool:
        """Set the hovered element.

        If the element is different from the current one, calls lifecycle
        methods on both elements (exit on old, enter on new). Returns True
        if the hover state changed.

        Parameters
        ----------
        element : Element or None
            Element to set as hovered, or None to clear hover

        Returns
        -------
        bool
            True if hover state changed, False if element was already hovered
        """
        # No change if same element
        if self.current_element is element:
            return False

        # Mark old hovered element's bounds as dirty
        if self.dirty_manager and self.current_element and self.current_element.bounds:
            self.dirty_manager.mark_dirty_bounds(self.current_element.bounds)

        # Exit current element
        if self.current_element is not None:
            self.current_element.on_hover_exit()

        # Enter new element
        self.current_element = element
        if self.current_element is not None:
            self.current_element.on_hover_enter()

            # Mark new hovered element's bounds as dirty
            if self.dirty_manager and self.current_element.bounds:
                self.dirty_manager.mark_dirty_bounds(self.current_element.bounds)

        return True

    def clear_hovered(self) -> bool:
        """Clear the hovered element.

        Calls on_hover_exit() on the currently hovered element if any.

        Returns
        -------
        bool
            True if an element was cleared, False if nothing was hovered
        """
        return self.set_hovered(None)
