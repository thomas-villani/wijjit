"""Focus management for interactive UI elements.

This module handles focus navigation between focusable elements,
typically using Tab and Shift+Tab keys, as well as arrow keys.
"""

from typing import TYPE_CHECKING, Any

from wijjit.elements.base import Element
from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from wijjit.layout.dirty import DirtyRegionManager

# Get logger for this module
logger = get_logger(__name__)


def _tab_index_sort_key(item: tuple[int, Element]) -> tuple[int, int, int]:
    """Sort key for elements by tab_index.

    Parameters
    ----------
    item : tuple
        Tuple of (original_index, element)

    Returns
    -------
    tuple
        Sort key (group, tab_index or 0, original_index)

    Notes
    -----
    Sorting groups:
    - Group 0: Elements with positive tab_index (sorted by tab_index)
    - Group 1: Elements with None tab_index (document order)
    - Elements with tab_index = -1 are excluded from tab navigation
    """
    original_index, elem = item
    tab_index = getattr(elem, "tab_index", None)

    if tab_index is None:
        # No tab_index: sort after explicit indices, in document order
        return (1, 0, original_index)
    elif tab_index >= 0:
        # Positive tab_index: sort first, by tab_index value
        return (0, tab_index, original_index)
    else:
        # Negative tab_index (-1): excluded from tab order, sort last
        return (2, 0, original_index)


class FocusManager:
    """Manages focus across UI elements.

    This class tracks which element has focus and provides methods
    for navigating focus between focusable elements.

    Attributes
    ----------
    elements : list
        List of focusable elements (sorted by tab_index)
    current_index : int or None
        Index of currently focused element
    all_focusable : list
        All focusable elements including those with tab_index=-1
    """

    def __init__(self) -> None:
        self.elements: list[Element] = []
        self.all_focusable: list[Element] = []
        self.current_index: int | None = None
        self.dirty_manager: DirtyRegionManager | None = None

    def set_elements(self, elements: list[Element]) -> None:
        """Set the list of focusable elements.

        Preserves focus on the same element (by ID or index) if possible.
        Elements are sorted by tab_index: explicit indices first (sorted
        numerically), then elements without tab_index (document order).
        Elements with tab_index=-1 are excluded from Tab navigation but
        can still receive focus via click or programmatic focus.

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

        # Filter to focusable elements
        focusable = [elem for elem in elements if elem.focusable]

        # Store all focusable elements (for click/programmatic focus)
        self.all_focusable = focusable

        # Sort by tab_index and filter out tab_index=-1 for Tab navigation
        indexed = list(enumerate(focusable))
        indexed.sort(key=_tab_index_sort_key)

        # Filter out elements with tab_index=-1 from tab navigation
        def _keep(elem: Any) -> bool:
            ti = getattr(elem, "tab_index", None)
            return ti is None or ti >= 0

        self.elements = [elem for _, elem in indexed if _keep(elem)]

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
        else:
            # Start with no focused element - focus will be set on first
            # user navigation action (Tab/Shift+Tab). This avoids the visual
            # issue where focus appears to "skip" the first element because
            # it was focused before bounds were calculated/rendered.
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

        # Mark old focused element's bounds as dirty
        if (
            self.dirty_manager
            and self.current_index is not None
            and 0 <= self.current_index < len(self.elements)
        ):
            old_elem = self.elements[self.current_index]
            if old_elem.bounds:
                self.dirty_manager.mark_dirty_bounds(old_elem.bounds)

        # Blur currently focused element
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            self.elements[self.current_index].on_blur()

        # Focus new element
        self.current_index = index
        if 0 <= index < len(self.elements):
            self.elements[index].on_focus()

            # Mark new focused element's bounds as dirty
            bounds = self.elements[index].bounds
            if self.dirty_manager and bounds is not None:
                self.dirty_manager.mark_dirty_bounds(bounds)

            # Scroll-into-view: walk the parent_frame chain and ask each
            # scrollable ancestor frame to scroll the newly-focused element
            # into its viewport. Innermost-first; each frame's scroll is
            # local so the outer frames can still adjust independently.
            self._ensure_focused_visible(self.elements[index])

    def _ensure_focused_visible(self, element: Element) -> None:
        """Walk the parent-frame chain and scroll ancestors to reveal ``element``.

        Tabbing onto an element that lies below (or above) a scrollable
        ancestor's viewport should automatically reveal it; without this
        the user sees the focus marker "disappear" into invisible content.
        Each ancestor's scroll position is local, so they're adjusted
        independently from innermost to outermost.

        Parameters
        ----------
        element : Element
            The element that just received focus.
        """
        bounds = element.bounds
        if bounds is None:
            return

        # Avoid an import cycle with wijjit.layout.frames.
        from wijjit.layout.frames import Frame

        target_top = bounds.y
        target_bottom = bounds.y + bounds.height
        seen: set[int] = set()
        ancestor = element.parent_frame
        while ancestor is not None and id(ancestor) not in seen:
            seen.add(id(ancestor))
            if isinstance(ancestor, Frame):
                scrolled = ancestor.scroll_to_make_visible(target_top, target_bottom)
                if scrolled and self.dirty_manager and ancestor.bounds is not None:
                    self.dirty_manager.mark_dirty_bounds(ancestor.bounds)
            ancestor = getattr(ancestor, "parent_frame", None)

    def clear(self) -> None:
        """Clear all elements and focus."""
        if self.current_index is not None and 0 <= self.current_index < len(
            self.elements
        ):
            self.elements[self.current_index].on_blur()

        self.elements = []
        self.all_focusable = []
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
