"""Overlay and Z-index management for Wijjit.

This module provides a layered overlay system for managing modals, context menus,
dropdowns, tooltips, and other UI elements that need to appear above the base UI.

Design Philosophy
-----------------
- Layer-based categories (Modal, Dropdown, Tooltip) for structure
- Auto-incrementing z-index within each layer for simplicity
- Event routing from top to bottom (highest z-index first)
- Focus management with automatic trapping/restoration
- Clean separation from base layout system
"""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

from wijjit.elements.menu import ContextMenu, DropdownMenu

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit
    from wijjit.elements.base import Element

from wijjit.layout.bounds import Bounds


class LayerType(IntEnum):
    """Layer types for z-index management.

    Each layer has a base z-index, and elements within that layer
    get auto-incremented z-indexes to handle stacking.

    Attributes
    ----------
    BASE : int
        Normal UI (not an overlay) - z-index 0
    MODAL : int
        Modal dialogs - z-index base 100
    DROPDOWN : int
        Dropdowns, context menus - z-index base 200
    TOOLTIP : int
        Tooltips, popovers (highest) - z-index base 300
    """

    BASE = 0
    MODAL = 100
    DROPDOWN = 200
    TOOLTIP = 300


@dataclass
class Overlay:
    """Represents a UI overlay (modal, dropdown, tooltip, etc.).

    Parameters
    ----------
    element : Element
        The element to render as an overlay
    layer_type : LayerType
        Which layer this overlay belongs to
    z_index : int
        Computed z-index (layer_base + stack_position)
    close_on_click_outside : bool
        Whether clicking outside closes this overlay
    close_on_escape : bool
        Whether ESC key closes this overlay
    trap_focus : bool
        Whether to trap focus within this overlay
    on_close : Optional[Callable]
        Callback when overlay is closed
    dimmed_background : bool
        Whether to dim the background behind this overlay
    previous_focus : Optional[Element]
        Element that had focus before this overlay opened
    previous_focus_state : Optional[tuple]
        Saved focus manager state (elements list, current index)
    """

    element: "Element"
    layer_type: LayerType
    z_index: int
    close_on_click_outside: bool = True
    close_on_escape: bool = True
    trap_focus: bool = False
    on_close: Callable[[], None] | None = None
    dimmed_background: bool = False
    previous_focus: Optional["Element"] = None
    previous_focus_state: tuple | None = None


class OverlayManager:
    """Manages overlay rendering, z-indexing, and event routing.

    The OverlayManager maintains a stack of overlays and handles:
    - Automatic z-index assignment
    - Event routing (highest z-index first)
    - Focus management and trapping
    - Rendering order
    - Background dimming

    Examples
    --------
    Basic modal usage:

        modal = Modal(title="Confirm", content="Delete file?")
        overlay = app.overlay_manager.push(
            modal,
            LayerType.MODAL,
            trap_focus=True,
            dimmed_background=True
        )

    Context menu usage:

        menu = ContextMenu(items=[...])
        overlay = app.overlay_manager.push(
            menu,
            LayerType.DROPDOWN,
            close_on_click_outside=True
        )

    Tooltip usage:

        tooltip = Tooltip(text="Help text")
        overlay = app.overlay_manager.push(
            tooltip,
            LayerType.TOOLTIP,
            close_on_click_outside=False,
            close_on_escape=False
        )
    """

    def __init__(self, app: "Wijjit"):
        """Initialize the overlay manager.

        Parameters
        ----------
        app : Wijjit
            Reference to the main app for focus/event management
        """
        self.app = app
        self.overlays: list[Overlay] = []

        # Track next available z-index for each layer
        # This auto-increments to handle stacking within a layer
        self._next_z_index = {
            LayerType.MODAL: LayerType.MODAL,
            LayerType.DROPDOWN: LayerType.DROPDOWN,
            LayerType.TOOLTIP: LayerType.TOOLTIP,
        }

    def push(
        self,
        element: "Element",
        layer_type: LayerType = LayerType.MODAL,
        close_on_click_outside: bool = True,
        close_on_escape: bool = True,
        trap_focus: bool = False,
        dimmed_background: bool = False,
        on_close: Callable[[], None] | None = None,
    ) -> Overlay:
        """Add an overlay to the stack.

        Parameters
        ----------
        element : Element
            The element to display as an overlay
        layer_type : LayerType
            Which layer to place this overlay in (default: MODAL)
        close_on_click_outside : bool
            Close when clicking outside the overlay (default: True)
        close_on_escape : bool
            Close when pressing ESC (default: True)
        trap_focus : bool
            Trap focus within this overlay (default: False)
        dimmed_background : bool
            Dim the background behind this overlay (default: False)
        on_close : Optional[Callable]
            Callback to invoke when overlay closes

        Returns
        -------
        Overlay
            The created overlay object
        """
        # Assign z-index
        z_index = self._next_z_index[layer_type]
        self._next_z_index[layer_type] += 1

        # Save current focus state if we're trapping focus
        previous_focus = None
        previous_focus_state = None
        if trap_focus and hasattr(self.app, "focus_manager"):
            previous_focus = self.app.focus_manager.get_focused_element()
            # Save the complete focus manager state
            previous_focus_state = self.app.focus_manager.save_state()

        # Create overlay
        overlay = Overlay(
            element=element,
            layer_type=layer_type,
            z_index=z_index,
            close_on_click_outside=close_on_click_outside,
            close_on_escape=close_on_escape,
            trap_focus=trap_focus,
            on_close=on_close,
            dimmed_background=dimmed_background,
            previous_focus=previous_focus,
            previous_focus_state=previous_focus_state,
        )

        # Auto-calculate bounds for centered overlays that don't have bounds
        if element.bounds is None and hasattr(element, "centered") and element.centered:

            term_size = shutil.get_terminal_size()

            # Get element dimensions (width/height attributes)
            elem_width = getattr(element, "width", 50)
            elem_height = getattr(element, "height", 10)

            # Center on screen
            x = max(0, (term_size.columns - elem_width) // 2)
            y = max(0, (term_size.lines - elem_height) // 2)

            element.bounds = Bounds(x=x, y=y, width=elem_width, height=elem_height)

        # Auto-position menus (dropdown and context menus)
        if element.bounds is None:

            if isinstance(element, (DropdownMenu, ContextMenu)):
                element.bounds = self._calculate_menu_position(element)

        # Add to stack (maintain sorted order by z-index)
        self.overlays.append(overlay)
        self.overlays.sort(key=lambda o: o.z_index)

        # If trapping focus, update focus manager with overlay's focusable elements
        if trap_focus and hasattr(self.app, "focus_manager"):
            # Collect focusable elements from the overlay
            focusable_elements = self._collect_focusable(element)

            if focusable_elements:
                # Update focus manager with only overlay elements
                self.app.focus_manager.set_elements(focusable_elements)
                # Focus the first focusable element in the overlay
                self.app.focus_manager.focus_first()

        # Trigger re-render
        if hasattr(self.app, "needs_render"):
            self.app.needs_render = True

        return overlay

    def pop(self, overlay: Overlay | None = None) -> Overlay | None:
        """Remove an overlay from the stack.

        Parameters
        ----------
        overlay : Optional[Overlay]
            Specific overlay to remove, or None to remove the topmost

        Returns
        -------
        Optional[Overlay]
            The removed overlay, or None if stack was empty
        """
        if not self.overlays:
            return None

        # Remove specific overlay or topmost
        if overlay:
            if overlay in self.overlays:
                self.overlays.remove(overlay)
            else:
                return None
        else:
            overlay = self.overlays.pop()

        # Mark the overlay's screen area as dirty to ensure it gets redrawn
        # This prevents ghost remnants when the overlay is dismissed
        if (
            overlay.element.bounds
            and hasattr(self.app, "renderer")
            and hasattr(self.app.renderer, "dirty_manager")
        ):
            self.app.renderer.dirty_manager.mark_dirty_bounds(overlay.element.bounds)

        # Restore focus state if this overlay was trapping it
        if overlay.trap_focus and hasattr(self.app, "focus_manager"):
            if overlay.previous_focus_state:
                # Restore the complete focus manager state
                self.app.focus_manager.restore_state(overlay.previous_focus_state)
            elif overlay.previous_focus:
                # Fallback: just focus the previous element
                self.app.focus_manager.focus_element(overlay.previous_focus)

        # Call close callback
        if overlay.on_close:
            overlay.on_close()

        # Trigger re-render
        if hasattr(self.app, "needs_render"):
            self.app.needs_render = True

        return overlay

    def pop_layer(self, layer_type: LayerType) -> list[Overlay]:
        """Remove all overlays in a specific layer.

        Useful for closing all dropdowns or all tooltips at once.

        Parameters
        ----------
        layer_type : LayerType
            Layer to clear

        Returns
        -------
        List[Overlay]
            List of removed overlays
        """
        removed = []
        for overlay in list(self.overlays):
            if overlay.layer_type == layer_type:
                self.pop(overlay)
                removed.append(overlay)

        # Reset z-index if this layer is now empty
        if not any(o.layer_type == layer_type for o in self.overlays):
            self._next_z_index[layer_type] = layer_type

        return removed

    def clear(self) -> list[Overlay]:
        """Remove all overlays.

        Returns
        -------
        List[Overlay]
            List of all removed overlays
        """
        removed = list(self.overlays)
        for overlay in removed:
            self.pop(overlay)

        # Reset all z-index counters
        self._next_z_index = {
            LayerType.MODAL: LayerType.MODAL,
            LayerType.DROPDOWN: LayerType.DROPDOWN,
            LayerType.TOOLTIP: LayerType.TOOLTIP,
        }

        return removed

    def get_at_position(self, x: int, y: int) -> Overlay | None:
        """Get the topmost overlay at the given position.

        Used for event routing - returns the highest z-index overlay
        that contains the specified point.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate

        Returns
        -------
        Optional[Overlay]
            Topmost overlay at position, or None
        """
        # Iterate from highest to lowest z-index
        for overlay in reversed(self.overlays):
            if overlay.element.bounds:
                if overlay.element.bounds.contains(x, y):
                    return overlay
        return None

    def get_top_overlay(self) -> Overlay | None:
        """Get the overlay with highest z-index.

        Returns
        -------
        Optional[Overlay]
            Topmost overlay, or None if stack is empty
        """
        return self.overlays[-1] if self.overlays else None

    def handle_click_outside(self, x: int, y: int) -> bool:
        """Handle a click outside any overlay.

        Closes overlays that have close_on_click_outside=True,
        starting from the topmost overlay.

        Parameters
        ----------
        x : int
            Click X coordinate
        y : int
            Click Y coordinate

        Returns
        -------
        bool
            True if any overlay was closed
        """
        closed_any = False

        # Check from top to bottom
        for overlay in reversed(list(self.overlays)):
            # If click is inside this overlay, stop checking
            if overlay.element.bounds and overlay.element.bounds.contains(x, y):
                break

            # If click is outside and overlay should close, close it
            if overlay.close_on_click_outside:
                self.pop(overlay)
                closed_any = True
                # Continue to check lower overlays

        return closed_any

    def handle_escape(self) -> bool:
        """Handle ESC key press.

        Closes the topmost overlay that has close_on_escape=True.

        Returns
        -------
        bool
            True if an overlay was closed
        """
        for overlay in reversed(list(self.overlays)):
            if overlay.close_on_escape:
                self.pop(overlay)
                return True
        return False

    def should_trap_focus(self) -> bool:
        """Check if focus should be trapped in an overlay.

        Returns
        -------
        bool
            True if the topmost overlay is trapping focus
        """
        top = self.get_top_overlay()
        return top.trap_focus if top else False

    def get_focus_trap_elements(self) -> list["Element"]:
        """Get focusable elements in the focus-trapping overlay.

        Returns
        -------
        List[Element]
            Focusable elements in the topmost focus-trapping overlay,
            or empty list if no overlay is trapping focus
        """
        top = self.get_top_overlay()
        if not top or not top.trap_focus:
            return []

        # Recursively collect focusable elements from overlay element
        return self._collect_focusable(top.element)

    def _collect_focusable(self, element: "Element") -> list["Element"]:
        """Recursively collect focusable elements.

        Parameters
        ----------
        element : Element
            Root element to search

        Returns
        -------
        List[Element]
            All focusable descendant elements
        """
        focusable = []

        if hasattr(element, "focusable") and element.focusable:
            focusable.append(element)

        # Check if element is a container with children
        if hasattr(element, "children"):
            for child in element.children:
                focusable.extend(self._collect_focusable(child))

        return focusable

    def get_overlay_elements(self) -> list["Element"]:
        """Get all overlay elements in z-order.

        Returns
        -------
        List[Element]
            All overlay elements sorted by z-index (lowest to highest)
        """
        return [overlay.element for overlay in self.overlays]

    def has_dimmed_overlay(self) -> bool:
        """Check if any overlay requests background dimming.

        Returns
        -------
        bool
            True if at least one visible overlay has dimmed_background=True
        """
        return any(overlay.dimmed_background for overlay in self.overlays)

    def recalculate_centered_overlays(self, term_width: int, term_height: int) -> None:
        """Recalculate positions for centered overlays after terminal resize.

        This method repositions all overlays that are marked as centered
        to ensure they remain centered after the terminal size changes.

        Parameters
        ----------
        term_width : int
            New terminal width in columns
        term_height : int
            New terminal height in lines
        """

        for overlay in self.overlays:
            element = overlay.element

            # Only recalculate for centered elements
            if hasattr(element, "centered") and element.centered and element.bounds:
                # Get element dimensions
                elem_width = getattr(element, "width", element.bounds.width)
                elem_height = getattr(element, "height", element.bounds.height)

                # Recalculate centered position
                x = max(0, (term_width - elem_width) // 2)
                y = max(0, (term_height - elem_height) // 2)

                # Update bounds
                element.bounds = Bounds(x=x, y=y, width=elem_width, height=elem_height)

    def _calculate_menu_position(self, menu_element: "Element") -> Bounds:
        """Calculate position for a menu element (dropdown or context menu).

        This method auto-positions menus relative to their trigger element
        or mouse cursor, ensuring they stay within screen bounds.

        Parameters
        ----------
        menu_element : Element
            The menu element to position (DropdownMenu or ContextMenu)

        Returns
        -------
        Bounds
            Calculated bounds for the menu

        Notes
        -----
        Dropdown positioning:
        - Default: Below trigger element
        - If off-screen bottom: Flip above trigger
        - If off-screen right: Shift left
        - If off-screen left: Shift right

        Context menu positioning:
        - Default: At mouse cursor
        - Adjust to stay fully on-screen
        """
        import shutil

        from wijjit.elements.menu import ContextMenu, DropdownMenu
        from wijjit.layout.bounds import Bounds

        term_size = shutil.get_terminal_size()
        term_width = term_size.columns
        term_height = term_size.lines

        # Get menu dimensions
        # Note: menu_element.width is the INNER width (content area)
        # The actual rendered width includes 2 chars for borders (left + right)
        inner_width = getattr(menu_element, "width", 30)
        menu_width = inner_width + 2  # Add borders
        menu_height = getattr(menu_element, "height", 10)

        if isinstance(menu_element, DropdownMenu):
            # Dropdown menu - position relative to trigger
            trigger_bounds = menu_element.trigger_bounds

            if trigger_bounds:
                # Position below trigger by default
                x = trigger_bounds.x
                y = trigger_bounds.y + trigger_bounds.height

                # Check if menu would go off bottom of screen
                if y + menu_height > term_height:
                    # Flip above trigger
                    y = trigger_bounds.y - menu_height
                    # Still off-screen? Clamp to top
                    if y < 0:
                        y = 0

                # Check if menu would go off right of screen
                if x + menu_width > term_width:
                    # Shift left to fit
                    x = term_width - menu_width

                # Check if menu would go off left of screen
                if x < 0:
                    x = 0
            else:
                # No trigger bounds, center on screen as fallback
                x = max(0, (term_width - menu_width) // 2)
                y = max(0, (term_height - menu_height) // 2)

        elif isinstance(menu_element, ContextMenu):
            # Context menu - position at mouse cursor
            mouse_pos = menu_element.mouse_position

            if mouse_pos:
                x, y = mouse_pos

                # Check if menu would go off bottom of screen
                if y + menu_height > term_height:
                    # Shift up to fit
                    y = term_height - menu_height

                # Check if menu would go off right of screen
                if x + menu_width > term_width:
                    # Shift left to fit
                    x = term_width - menu_width

                # Clamp to screen bounds
                x = max(0, min(x, term_width - menu_width))
                y = max(0, min(y, term_height - menu_height))
            else:
                # No mouse position, center on screen as fallback
                x = max(0, (term_width - menu_width) // 2)
                y = max(0, (term_height - menu_height) // 2)
        else:
            # Unknown menu type, center on screen
            x = max(0, (term_width - menu_width) // 2)
            y = max(0, (term_height - menu_height) // 2)

        return Bounds(x=x, y=y, width=menu_width, height=menu_height)
