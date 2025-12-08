"""Autocomplete popup element for displaying suggestions.

This module provides the AutocompletePopup element which displays a list of
autocomplete suggestions below a text input. The popup supports keyboard
navigation, mouse selection, and scrolling for long lists.

Classes
-------
AutocompletePopup
    Popup element displaying autocomplete suggestions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wijjit.autocomplete.state import AutocompleteState
from wijjit.elements.base import Element, ElementType
from wijjit.layout.frames import BORDER_CHARS
from wijjit.layout.scroll import ScrollManager
from wijjit.terminal.ansi import visible_length
from wijjit.terminal.input import Key, Keys

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext
    from wijjit.terminal.mouse import MouseEvent


class AutocompletePopup(Element):
    """Popup element displaying autocomplete suggestions.

    This element renders a bordered popup with a list of suggestions.
    It supports keyboard navigation (Up/Down/PageUp/PageDown/Home/End),
    mouse click selection, and automatic scrolling for long lists.

    The popup uses an AutocompleteState as the single source of truth for
    suggestions and highlighted index, avoiding duplicate state management.

    Parameters
    ----------
    state : AutocompleteState
        Reference to the autocomplete state (single source of truth).
    max_visible : int, optional
        Maximum number of suggestions visible at once (default: 10).

    Attributes
    ----------
    state : AutocompleteState
        Reference to the shared autocomplete state.
    max_visible : int
        Maximum visible suggestions.
    scroll_manager : ScrollManager
        Manages scroll state for long lists.

    Examples
    --------
    Create a popup with state:

    >>> state = AutocompleteState()
    >>> state.suggestions = ["apple", "apricot", "banana"]
    >>> popup = AutocompletePopup(state)
    >>> popup.highlighted_index
    0
    >>> popup.selected_suggestion
    'apple'

    Navigate suggestions:

    >>> popup.move_highlight(1)  # Move down
    >>> popup.selected_suggestion
    'apricot'
    """

    def __init__(
        self,
        state: AutocompleteState,
        max_visible: int = 10,
    ) -> None:
        super().__init__()
        self.state = state
        self.max_visible = max_visible
        self.element_type = ElementType.SELECTABLE
        self.focusable = False  # Focus stays on input!

        # Initialize scroll manager
        self._update_scroll_manager()

    # Properties that delegate to state for backward compatibility
    @property
    def suggestions(self) -> list[str]:
        """Get suggestions from state."""
        return self.state.suggestions

    @property
    def highlighted_index(self) -> int:
        """Get highlighted index from state."""
        return self.state.highlighted_index

    @highlighted_index.setter
    def highlighted_index(self, value: int) -> None:
        """Set highlighted index in state."""
        self.state.highlighted_index = value

    def _update_scroll_manager(self) -> None:
        """Update scroll manager based on current suggestions."""
        content_size = len(self.suggestions)
        viewport_size = min(self.max_visible, content_size) if content_size > 0 else 1
        self.scroll_manager = ScrollManager(
            content_size=content_size,
            viewport_size=viewport_size,
            initial_position=0,
        )

    def sync_from_state(self) -> None:
        """Synchronize scroll manager with current state.

        Call this after state.suggestions changes to update the scroll manager.

        Notes
        -----
        The popup now uses AutocompleteState as the source of truth, so this
        method only needs to update the scroll manager when suggestions change.
        """
        self._update_scroll_manager()

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the popup.

        Returns
        -------
        tuple of int
            (width, height) in characters.

        Notes
        -----
        Width is based on longest suggestion + padding + border.
        Height is based on number of suggestions (capped at max_visible) + border.
        """
        if not self.suggestions:
            return (20, 3)  # Minimum size with border

        # Width: longest suggestion + 2 for padding + 2 for border
        # Use visible_length() to handle ANSI escape codes correctly
        max_len = max(visible_length(s) for s in self.suggestions)
        width = min(max_len + 4, 50)  # Cap at 50 chars

        # Height: visible suggestions + 2 for border
        visible_count = min(len(self.suggestions), self.max_visible)
        height = visible_count + 2

        return (width, height)

    def render_to(self, ctx: PaintContext) -> None:
        """Render the popup with suggestions.

        Parameters
        ----------
        ctx : PaintContext
            Paint context for rendering.

        Notes
        -----
        Renders a bordered box with suggestions. The highlighted suggestion
        gets a different background color. Scrolling is handled automatically.
        """
        if not ctx.bounds:
            return

        # Resolve styles
        border_style = ctx.style_resolver.resolve_style(self, "autocomplete.border")
        item_style = ctx.style_resolver.resolve_style(self, "autocomplete.item")
        highlight_style = ctx.style_resolver.resolve_style(
            self, "autocomplete.item:highlighted"
        )

        # Clear background
        ctx.clear(item_style)

        # Draw border (using shared BORDER_CHARS from wijjit.layout.frames)
        ctx.draw_border(
            0,
            0,
            ctx.bounds.width,
            ctx.bounds.height,
            border_style,
            BORDER_CHARS["single"],  # Use single-line border style
        )

        if not self.suggestions:
            # Show "No suggestions" message
            msg = "No matches"
            x = max(1, (ctx.bounds.width - len(msg)) // 2)
            ctx.write_text(x, 1, msg, item_style)
            return

        # Calculate visible range
        visible_height = ctx.bounds.height - 2  # Minus border
        self._ensure_highlight_visible(visible_height)
        scroll_offset = self.scroll_manager.state.scroll_position

        # Render suggestions
        inner_width = ctx.bounds.width - 2  # Minus border
        for i, suggestion in enumerate(self.suggestions):
            if i < scroll_offset:
                continue
            if i >= scroll_offset + visible_height:
                break

            row = i - scroll_offset + 1  # +1 for top border
            is_highlighted = i == self.highlighted_index

            # Choose style and optionally fill row background
            if is_highlighted:
                style = highlight_style
                # Fill row background for highlight
                ctx.fill_rect(1, row, inner_width, 1, " ", style)
            else:
                style = item_style

            # Clip text to fit (leave space for padding)
            text = suggestion[: inner_width - 2]
            ctx.write_text(2, row, text, style)

        # Render scroll indicators if needed
        if self.scroll_manager.state.is_scrollable:
            self._render_scroll_indicators(ctx, scroll_offset, visible_height)

    def _ensure_highlight_visible(self, visible_height: int) -> None:
        """Ensure the highlighted item is visible by adjusting scroll.

        Parameters
        ----------
        visible_height : int
            Number of visible rows for suggestions.
        """
        if not self.suggestions:
            return

        scroll_pos = self.scroll_manager.state.scroll_position

        # If highlighted is above visible area, scroll up
        if self.highlighted_index < scroll_pos:
            self.scroll_manager.scroll_to(self.highlighted_index)
        # If highlighted is below visible area, scroll down
        elif self.highlighted_index >= scroll_pos + visible_height:
            self.scroll_manager.scroll_to(self.highlighted_index - visible_height + 1)

    def _render_scroll_indicators(
        self, ctx: PaintContext, scroll_offset: int, visible_height: int
    ) -> None:
        """Render scroll indicators when content is scrollable.

        Parameters
        ----------
        ctx : PaintContext
            Paint context for rendering.
        scroll_offset : int
            Current scroll offset.
        visible_height : int
            Number of visible rows.
        """
        indicator_style = ctx.style_resolver.resolve_style(
            self, "autocomplete.scrollbar"
        )
        x = ctx.bounds.width - 1  # Right edge (over border)

        # Up arrow if can scroll up
        if scroll_offset > 0:
            ctx.write_text(x, 0, "^", indicator_style)

        # Down arrow if can scroll down
        if scroll_offset + visible_height < len(self.suggestions):
            ctx.write_text(x, ctx.bounds.height - 1, "v", indicator_style)

    def handle_key(self, key: Key) -> bool:
        """Handle navigation keys.

        Parameters
        ----------
        key : Key
            The key that was pressed.

        Returns
        -------
        bool
            True if key was handled, False otherwise.

        Notes
        -----
        Handles:
        - Up/Down: Move highlight
        - PageUp/PageDown: Move highlight by page
        - Home/End: Jump to first/last
        - Enter/Tab: Selection (returns False, handled by parent)
        - Escape: Close (returns False, handled by parent)
        """
        if not self.suggestions:
            return False

        if key == Keys.UP:
            self.move_highlight(-1)
            return True
        elif key == Keys.DOWN:
            self.move_highlight(1)
            return True
        elif key == Keys.PAGE_UP:
            self.move_highlight(-self.max_visible)
            return True
        elif key == Keys.PAGE_DOWN:
            self.move_highlight(self.max_visible)
            return True
        elif key == Keys.HOME:
            self.highlighted_index = 0
            return True
        elif key == Keys.END:
            self.highlighted_index = len(self.suggestions) - 1
            return True

        return False

    def move_highlight(self, delta: int) -> None:
        """Move the highlight by a delta amount.

        Parameters
        ----------
        delta : int
            Amount to move (positive = down, negative = up).

        Notes
        -----
        Clamps to valid range [0, len(suggestions) - 1].
        """
        if not self.suggestions:
            return

        new_index = self.highlighted_index + delta
        self.highlighted_index = max(0, min(len(self.suggestions) - 1, new_index))

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse events on the popup.

        Parameters
        ----------
        event : MouseEvent
            The mouse event.

        Returns
        -------
        bool
            True if event was handled, False otherwise.

        Notes
        -----
        Clicking on a suggestion highlights it and returns True to signal
        that a selection should occur.
        """
        from wijjit.terminal.mouse import MouseEventType

        if not self.bounds or not self.suggestions:
            return False

        # Check if click is within popup bounds
        if not self.bounds.contains(event.x, event.y):
            return False

        if event.type == MouseEventType.CLICK:
            # Calculate which item was clicked
            rel_y = event.y - self.bounds.y - 1  # -1 for top border

            if rel_y < 0 or rel_y >= self.bounds.height - 2:
                return False  # Click on border

            scroll_offset = self.scroll_manager.state.scroll_position
            clicked_index = scroll_offset + rel_y

            if 0 <= clicked_index < len(self.suggestions):
                self.highlighted_index = clicked_index
                return True  # Signal selection should happen

        elif event.type == MouseEventType.SCROLL:
            # Check scroll direction via button
            from wijjit.terminal.mouse import MouseButton

            if event.button == MouseButton.SCROLL_UP:
                self.move_highlight(-1)
                return True
            elif event.button == MouseButton.SCROLL_DOWN:
                self.move_highlight(1)
                return True

        return False

    @property
    def selected_suggestion(self) -> str | None:
        """Get the currently highlighted suggestion.

        Returns
        -------
        str or None
            The highlighted suggestion, or None if no suggestions.
        """
        if self.suggestions and 0 <= self.highlighted_index < len(self.suggestions):
            return self.suggestions[self.highlighted_index]
        return None

    @property
    def has_suggestions(self) -> bool:
        """Check if there are any suggestions.

        Returns
        -------
        bool
            True if there are suggestions, False otherwise.
        """
        return len(self.suggestions) > 0

    @property
    def suggestion_count(self) -> int:
        """Get the number of suggestions.

        Returns
        -------
        int
            Number of suggestions.
        """
        return len(self.suggestions)
