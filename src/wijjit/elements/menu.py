"""Menu elements for dropdowns and context menus.

This module provides menu UI elements including dropdown menus and context menus
with keyboard and mouse navigation support.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wijjit.elements.base import ElementType, OverlayElement
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.terminal.ansi import ANSIStyle, clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseEvent, MouseEventType

if TYPE_CHECKING:
    pass


@dataclass
class MenuItem:
    """Represents a single menu item.

    Parameters
    ----------
    label : str
        Display text for the menu item
    action : str or None, optional
        Action ID to dispatch when item is selected
    key : str or None, optional
        Keyboard shortcut hint (e.g., "Ctrl+N")
    divider : bool, optional
        Whether this is a divider line (default: False)
    disabled : bool, optional
        Whether this item is disabled (default: False)

    Attributes
    ----------
    label : str
        Display text for the menu item
    action : str or None
        Action ID to dispatch when selected
    key : str or None
        Keyboard shortcut hint
    divider : bool
        Whether this is a divider line
    disabled : bool
        Whether this item is disabled
    """

    label: str
    action: str | None = None
    key: str | None = None
    divider: bool = False
    disabled: bool = False


class MenuElement(OverlayElement):
    """Base class for menu elements (dropdown, context menu).

    This provides the core menu rendering and interaction logic including
    keyboard navigation, mouse hover/click, and item selection.

    Parameters
    ----------
    id : str, optional
        Unique identifier
    items : list of MenuItem, optional
        Menu items to display (default: empty list)
    width : int, optional
        Menu width in characters (default: 30)
    border_style : BorderStyle or {"single", "double", "rounded"}, optional
        Border style (default: BorderStyle.SINGLE)
    centered : bool, optional
        Whether to center the menu (default: False, menus position relative to trigger)

    Attributes
    ----------
    items : list of MenuItem
        Menu items
    width : int
        Menu width
    border_style : BorderStyle
        Border style for rendering
    highlighted_index : int
        Index of currently highlighted item (-1 if none)
    on_item_select : callable or None
        Callback when item is selected: (action_id: str, item: MenuItem) -> None
    close_callback : callable or None
        Callback to close the menu (set externally by app)
    """

    def __init__(
        self,
        id: str | None = None,
        items: list[MenuItem] | None = None,
        width: int = 30,
        border_style: BorderStyle | str = BorderStyle.SINGLE,
        centered: bool = False,
    ):
        # Calculate height based on items
        items = items or []
        height = len(items) + 2  # Add 2 for borders

        super().__init__(id=id, width=width, height=height, centered=centered)

        self.items = items
        self.width = width
        self.element_type = ElementType.SELECTABLE
        self.focusable = True

        # Normalize border style
        if isinstance(border_style, str):
            border_map = {
                "single": BorderStyle.SINGLE,
                "double": BorderStyle.DOUBLE,
                "rounded": BorderStyle.ROUNDED,
            }
            self.border_style = border_map.get(border_style.lower(), BorderStyle.SINGLE)
        else:
            self.border_style = border_style

        # Navigation state
        self.highlighted_index = self._find_first_enabled_item()

        # State persistence
        self._state_dict = None  # Will be set by app if needed
        self._highlight_state_key = None  # Will be set by app if needed

        # Callbacks
        self.on_item_select: Callable[[str, MenuItem], None] | None = None
        self.close_callback: Callable[[], None] | None = None

    def _find_first_enabled_item(self) -> int:
        """Find the first enabled (non-divider, non-disabled) item.

        Returns
        -------
        int
            Index of first enabled item, or -1 if none found
        """
        for i, item in enumerate(self.items):
            if not item.divider and not item.disabled:
                return i
        return -1

    def _find_next_enabled_item(self, start_index: int, direction: int) -> int:
        """Find next enabled item in given direction.

        Parameters
        ----------
        start_index : int
            Starting index
        direction : int
            Direction to search (1 for down, -1 for up)

        Returns
        -------
        int
            Index of next enabled item, or start_index if none found
        """
        if not self.items:
            return -1

        current = start_index
        for _ in range(len(self.items)):
            current = (current + direction) % len(self.items)
            item = self.items[current]
            if not item.divider and not item.disabled:
                return current

        return start_index

    def _save_highlight_to_state(self) -> None:
        """Save highlighted_index to state for persistence across renders."""
        if self._state_dict and self._highlight_state_key:
            self._state_dict[self._highlight_state_key] = self.highlighted_index

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for menu navigation.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        if not self.items:
            return False

        # Escape - close menu
        if key == Keys.ESCAPE:
            if self.close_callback:
                self.close_callback()
            return True

        # Enter - select highlighted item
        if key == Keys.ENTER:
            if 0 <= self.highlighted_index < len(self.items):
                item = self.items[self.highlighted_index]
                if not item.divider and not item.disabled:
                    self._select_item(item)
                    return True
            return True

        # Down arrow - move highlight down
        if key == Keys.DOWN:
            if self.highlighted_index < len(self.items) - 1:
                self.highlighted_index = self._find_next_enabled_item(
                    self.highlighted_index, 1
                )
            self._save_highlight_to_state()
            return True

        # Up arrow - move highlight up
        if key == Keys.UP:
            if self.highlighted_index > 0:
                self.highlighted_index = self._find_next_enabled_item(
                    self.highlighted_index, -1
                )
            self._save_highlight_to_state()
            return True

        # Home - jump to first enabled item
        if key == Keys.HOME:
            self.highlighted_index = self._find_first_enabled_item()
            self._save_highlight_to_state()
            return True

        # End - jump to last enabled item
        if key == Keys.END:
            # Find last enabled item by searching backwards from end
            for i in range(len(self.items) - 1, -1, -1):
                item = self.items[i]
                if not item.divider and not item.disabled:
                    self.highlighted_index = i
                    break
            self._save_highlight_to_state()
            return True

        return False

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input for menu interaction.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        if not self.bounds or not self.items:
            return False

        # Convert to relative coordinates
        relative_x = event.x - self.bounds.x
        relative_y = event.y - self.bounds.y

        # Account for top border
        item_y = relative_y - 1

        # Check if within menu bounds
        if 0 <= item_y < len(self.items) and 0 <= relative_x < self.bounds.width:
            item = self.items[item_y]

            # Mouse move - update highlight
            if event.type == MouseEventType.MOVE:
                if not item.divider and not item.disabled:
                    self.highlighted_index = item_y
                return True

            # Click - select item
            if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
                if not item.divider and not item.disabled:
                    self.highlighted_index = item_y
                    self._select_item(item)
                return True

        return False

    def _select_item(self, item: MenuItem) -> None:
        """Select a menu item and trigger callbacks.

        Parameters
        ----------
        item : MenuItem
            The item that was selected
        """
        # Call selection callback
        if self.on_item_select and item.action:
            self.on_item_select(item.action, item)

        # Close menu
        if self.close_callback:
            self.close_callback()

    def render_to(self, ctx) -> None:
        """Render the menu using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method uses cell-based rendering with theme styles for menu
        items, borders, and states. It properly handles highlights, disabled
        items, and keyboard shortcuts.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'menu': Base menu style
        - 'menu:focus': Focused menu style
        - 'menu.border': Border style
        - 'menu.border:focus': Focused border style
        - 'menu.item': Menu item style
        - 'menu.item:highlighted': Highlighted item style
        - 'menu.item:disabled': Disabled item style
        - 'menu.divider': Divider line style
        - 'menu.shortcut': Keyboard shortcut hint style
        """

        if not self.bounds:
            return

        # Resolve border style
        border_style_class = "menu.border:focus" if self.focused else "menu.border"
        border_style = ctx.style_resolver.resolve_style(self, border_style_class)

        # Get border characters for the style
        border_chars = BORDER_CHARS[self.border_style]

        # Draw border around menu
        ctx.draw_border(
            0, 0, ctx.bounds.width, ctx.bounds.height, border_style, border_chars
        )

        # Render each item inside the border
        row = 1  # Start after top border
        for i, item in enumerate(self.items):
            if row >= ctx.bounds.height - 1:  # Don't exceed bottom border
                break

            is_highlighted = i == self.highlighted_index and self.focused

            if item.divider:
                # Render divider using border horizontal character
                divider_style = ctx.style_resolver.resolve_style(self, "menu.divider")
                chars = BORDER_CHARS[self.border_style]
                divider_line = chars["h"] * self.width
                ctx.write_text(1, row, divider_line, divider_style)
            else:
                # Render menu item
                self._render_item_to_ctx(ctx, item, is_highlighted, row)

            row += 1

    def _render_item_to_ctx(
        self, ctx, item: MenuItem, is_highlighted: bool, row: int
    ) -> None:
        """Render a single menu item to the context.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        item : MenuItem
            The item to render
        is_highlighted : bool
            Whether this item is currently highlighted
        row : int
            Row index to render at
        """
        # Calculate available width for label (2 spaces for padding)
        available_width = self.width - 2

        # If item has shortcut, reserve space for it
        shortcut_text = ""
        label_width = available_width
        if item.key:
            shortcut_text = f" {item.key}"
            shortcut_len = visible_length(shortcut_text)
            label_width = available_width - shortcut_len

        # Clip or pad label
        label = item.label
        label_len = visible_length(label)
        if label_len > label_width:
            label = clip_to_width(label, label_width, ellipsis="...")
        else:
            label = label + " " * (label_width - label_len)

        # Combine label and shortcut
        text = label + shortcut_text

        # Determine style based on state
        if item.disabled:
            style = ctx.style_resolver.resolve_style(self, "menu.item:disabled")
        elif is_highlighted:
            style = ctx.style_resolver.resolve_style(self, "menu.item:highlighted")
        else:
            style = ctx.style_resolver.resolve_style(self, "menu.item")

        # Render the item line: " {text} " (with padding)
        x_offset = 1  # After left border
        formatted_text = f" {text} "
        ctx.write_text(x_offset, row, formatted_text, style)

    def _render_item(self, item: MenuItem, is_highlighted: bool) -> str:
        """Render a single menu item.

        Parameters
        ----------
        item : MenuItem
            The item to render
        is_highlighted : bool
            Whether this item is currently highlighted

        Returns
        -------
        str
            Rendered item line with styling
        """
        # Calculate available width for label (2 spaces for padding)
        available_width = self.width - 2

        # If item has shortcut, reserve space for it
        shortcut_text = ""
        label_width = available_width
        if item.key:
            shortcut_text = f" {item.key}"
            shortcut_len = visible_length(shortcut_text)
            label_width = available_width - shortcut_len

        # Clip or pad label
        label = item.label
        label_len = visible_length(label)
        if label_len > label_width:
            label = clip_to_width(label, label_width, ellipsis="...")
        else:
            label = label + " " * (label_width - label_len)

        # Combine label and shortcut
        text = label + shortcut_text

        # Apply styling
        if item.disabled:
            # Disabled: dim
            return f"{ANSIStyle.RESET}{ANSIStyle.DIM} {text} {ANSIStyle.RESET}"
        elif is_highlighted:
            # Highlighted: reverse video
            return f"{ANSIStyle.RESET}{ANSIStyle.REVERSE} {text} {ANSIStyle.RESET}"
        else:
            # Normal
            return f"{ANSIStyle.RESET} {text} {ANSIStyle.RESET}"


class DropdownMenu(MenuElement):
    """Dropdown menu element.

    A dropdown menu appears below (or above) a trigger element when activated.
    It supports keyboard shortcuts and auto-positioning to stay on screen.

    Parameters
    ----------
    id : str, optional
        Unique identifier
    items : list of MenuItem, optional
        Menu items to display
    trigger_text : str, optional
        Text for the trigger button (default: "Menu")
    trigger_key : str or None, optional
        Keyboard shortcut to open menu (e.g., "Alt+F")
    width : int, optional
        Menu width (default: 30)
    border_style : BorderStyle or str, optional
        Border style (default: BorderStyle.SINGLE)

    Attributes
    ----------
    trigger_text : str
        Text for the trigger button
    trigger_key : str or None
        Keyboard shortcut to open menu
    trigger_bounds : Bounds or None
        Bounds of the trigger element (for positioning)
    """

    def __init__(
        self,
        id: str | None = None,
        items: list[MenuItem] | None = None,
        trigger_text: str = "Menu",
        trigger_key: str | None = None,
        width: int = 30,
        border_style: BorderStyle | str = BorderStyle.SINGLE,
    ):
        super().__init__(
            id=id,
            items=items,
            width=width,
            border_style=border_style,
            centered=False,  # Dropdowns position relative to trigger
        )

        self.trigger_text = trigger_text
        self.trigger_key = trigger_key
        self.trigger_bounds: Bounds | None = None


class ContextMenu(MenuElement):
    """Context menu element.

    A context menu appears at the mouse cursor position when triggered by
    a right-click on a target element. It auto-positions to stay on screen.

    Parameters
    ----------
    id : str, optional
        Unique identifier
    items : list of MenuItem, optional
        Menu items to display
    target_element_id : str or None, optional
        ID of the element this context menu is attached to
    width : int, optional
        Menu width (default: 30)
    border_style : BorderStyle or str, optional
        Border style (default: BorderStyle.SINGLE)

    Attributes
    ----------
    target_element_id : str or None
        ID of the target element
    mouse_position : tuple of (int, int) or None
        Mouse cursor position (x, y) where menu was triggered
    """

    def __init__(
        self,
        id: str | None = None,
        items: list[MenuItem] | None = None,
        target_element_id: str | None = None,
        width: int = 30,
        border_style: BorderStyle | str = BorderStyle.SINGLE,
    ):
        super().__init__(
            id=id,
            items=items,
            width=width,
            border_style=border_style,
            centered=False,  # Context menus position at cursor
        )

        self.target_element_id = target_element_id
        self.mouse_position: tuple[int, int] | None = None
