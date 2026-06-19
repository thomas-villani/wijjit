"""Mixin class to add autocomplete functionality to text input elements.

This module provides the AutocompleteMixin that can be mixed into TextInput
or similar input elements to add autocomplete popup functionality.

Classes
-------
AutocompleteMixin
    Mixin that adds autocomplete to input elements.
"""

from __future__ import annotations

import asyncio
import shutil
from typing import TYPE_CHECKING

from wijjit.autocomplete.completer import AsyncCompleter, Completer
from wijjit.autocomplete.popup import AutocompletePopup
from wijjit.autocomplete.state import AutocompleteState
from wijjit.autocomplete.utils import get_word_at_cursor, replace_word_at_cursor
from wijjit.core.overlay import LayerType
from wijjit.logging_config import get_logger
from wijjit.terminal.input import Key, Keys

if TYPE_CHECKING:
    from wijjit.core.overlay import Overlay, OverlayManager
    from wijjit.layout.bounds import Bounds

logger = get_logger(__name__)


class AutocompleteMixin:
    """Mixin to add autocomplete functionality to text input elements.

    Add to TextInput class via multiple inheritance. This mixin provides
    all the logic for managing autocomplete suggestions, popup display,
    and keyboard/mouse interaction.

    Assumes the host class has:
    - self.value: str - Current text value
    - self.cursor_pos: int - Cursor position in text
    - self.bounds: Bounds - Element's screen bounds
    - self._focused: bool - Whether element is focused

    Attributes
    ----------
    completer : Completer or None
        The completer providing suggestions.
    _autocomplete_state : AutocompleteState
        Internal state for autocomplete popup.
    _autocomplete_popup : AutocompletePopup or None
        The popup element when visible.

    Examples
    --------
    Mix into an input element:

    >>> class MyInput(AutocompleteMixin, Element):
    ...     def __init__(self):
    ...         super().__init__()
    ...         self._init_autocomplete()
    ...         self.completer = WordCompleter(["apple", "banana"])
    ...
    ...     def handle_key(self, key):
    ...         if self._handle_autocomplete_key(key):
    ...             return True
    ...         # ... normal key handling ...
    ...         self._handle_autocomplete_after_edit()
    ...         return True
    """

    # These will be set on the mixed-in class
    completer: Completer | None = None
    _autocomplete_state: AutocompleteState
    _autocomplete_popup: AutocompletePopup | None = None
    _autocomplete_overlay: Overlay | None = None  # Track overlay for removal
    _autocomplete_applying: bool = False  # Prevent re-trigger during apply
    _overlay_manager: OverlayManager | None = None

    # Required attributes from host class (declared for type checking)
    value: str
    cursor_pos: int
    bounds: Bounds | None
    _focused: bool

    def _init_autocomplete(self) -> None:
        """Initialize autocomplete state.

        Call this from the host element's __init__ method.
        """
        self._autocomplete_state = AutocompleteState()
        self._autocomplete_popup = None
        self._autocomplete_overlay = None
        self._autocomplete_applying = False
        # In-flight async suggestion fetch; retained so it is not
        # garbage-collected and so a newer keystroke can cancel a stale one.
        self._suggestion_task: asyncio.Task[None] | None = None

    def _handle_autocomplete_key(self, key: Key) -> bool:
        """Handle key events for autocomplete.

        Call this at the beginning of handle_key() in the host element.
        Returns True if the key was consumed by autocomplete, meaning
        the host element should not process it further.

        Parameters
        ----------
        key : Key
            The key event to handle.

        Returns
        -------
        bool
            True if key was consumed by autocomplete, False otherwise.
        """
        if not self.completer:
            return False

        config = self.completer.config
        state = self._autocomplete_state

        # Check for manual trigger (Ctrl+/ by default; see CompleterConfig)
        if not state.is_open:
            if self._is_trigger_key(key, config.trigger_key):
                self._trigger_autocomplete()
                return True

        # If popup is open, handle navigation and selection
        if state.is_open:
            # Navigation keys - delegate to popup
            # Note: popup now references state directly, no manual sync needed
            if key in (
                Keys.UP,
                Keys.DOWN,
                Keys.PAGE_UP,
                Keys.PAGE_DOWN,
                Keys.HOME,
                Keys.END,
            ):
                if self._autocomplete_popup:
                    self._autocomplete_popup.handle_key(key)
                return True

            # Selection keys
            if key == Keys.ENTER:
                self._apply_selected_suggestion()
                return True

            if config.select_on_tab and key == Keys.TAB:
                self._apply_selected_suggestion()
                return True

            # Escape to close
            if key == Keys.ESCAPE:
                self._close_autocomplete()
                return True

        return False

    def _is_trigger_key(self, key: Key, trigger_key: str) -> bool:
        """Check if key matches the trigger key combination.

        Parameters
        ----------
        key : Key
            The pressed key.
        trigger_key : str
            The trigger key string (e.g., "ctrl+space").

        Returns
        -------
        bool
            True if key matches trigger.
        """
        # Parse trigger_key string
        parts = trigger_key.lower().split("+")
        requires_ctrl = "ctrl" in parts
        requires_alt = "alt" in parts
        requires_shift = "shift" in parts

        # Get the actual key part (last part)
        key_part = parts[-1] if parts else ""

        # Get key modifiers (Key class uses modifiers list)
        key_modifiers = key.modifiers if hasattr(key, "modifiers") else []

        # Check modifiers
        if requires_ctrl and "ctrl" not in key_modifiers:
            return False
        if requires_alt and "alt" not in key_modifiers:
            return False
        if requires_shift and "shift" not in key_modifiers:
            return False

        # Check key - handle special cases and generic matching
        if key_part == "space":
            # For ctrl+space, check for dedicated CTRL_SPACE key
            if requires_ctrl and key == Keys.CTRL_SPACE:
                return True
            # Also check for c-@ (prompt_toolkit's representation of Ctrl+Space)
            if requires_ctrl and key.name == "c-@":
                return True
            # Match space key in various forms
            return key == Keys.SPACE or key.char == " " or "space" in key.name.lower()

        # Generic key matching (e.g., "/", ".", etc.)
        # Check if the key character matches
        if key.char == key_part:
            return True

        # Check if the key name contains the key part (for control keys)
        # e.g., "c-/" for ctrl+/
        if requires_ctrl and key.name == f"c-{key_part}":
            return True

        # Handle terminal quirk: Ctrl+/ often comes through as Ctrl+_ (underscore)
        if requires_ctrl and key_part == "/" and key.name in ("c-_", "ctrl+_"):
            return True

        return False

    def _handle_autocomplete_after_edit(self) -> None:
        """Update autocomplete after text is modified.

        Call this after any edit operation (character insert, delete, etc.)
        to update the autocomplete suggestions if needed.
        """
        if not self.completer:
            return

        # Skip if we're in the middle of applying a suggestion
        if self._autocomplete_applying:
            return

        config = self.completer.config
        state = self._autocomplete_state

        # Get current word at cursor
        word, start, end = get_word_at_cursor(self.value, self.cursor_pos)

        if config.trigger == "auto" and len(word) >= config.min_chars:
            # Auto-trigger mode: update suggestions
            self._update_suggestions(word, start, end)
        elif state.is_open:
            # Popup already open: update or close
            if word:
                self._update_suggestions(word, start, end)
            else:
                self._close_autocomplete()

    def _trigger_autocomplete(self) -> None:
        """Manually trigger the autocomplete popup."""
        word, start, end = get_word_at_cursor(self.value, self.cursor_pos)
        self._update_suggestions(word, start, end)

    def _update_suggestions(self, prefix: str, word_start: int, word_end: int) -> None:
        """Fetch and display suggestions for the current prefix.

        Parameters
        ----------
        prefix : str
            The word prefix to complete.
        word_start : int
            Start position of the word in text.
        word_end : int
            End position (cursor position) of the word.
        """
        if not self.completer:
            return

        state = self._autocomplete_state
        state.prefix = prefix
        state.word_start = word_start
        state.word_end = word_end

        # Get suggestions (handle async case)
        if isinstance(self.completer, AsyncCompleter):
            # Cancel any prior in-flight fetch so a slow earlier request cannot
            # overwrite the results of this newer keystroke, then schedule and
            # retain a strong reference to the new task.
            prior = self._suggestion_task
            if prior is not None and not prior.done():
                prior.cancel()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                self._suggestion_task = loop.create_task(
                    self._fetch_suggestions_async(prefix)
                )
            else:
                logger.warning(
                    "Cannot fetch async autocomplete suggestions outside of "
                    "an event loop"
                )
        else:
            suggestions = self.completer.get_suggestions(prefix)
            self._show_suggestions(suggestions)

    async def _fetch_suggestions_async(self, prefix: str) -> None:
        """Fetch suggestions asynchronously.

        Parameters
        ----------
        prefix : str
            The word prefix to complete.

        Notes
        -----
        Errors are caught and logged to prevent unhandled task exceptions.
        The autocomplete popup is closed on error to avoid stale state.
        """
        if not self.completer:
            return
        try:
            suggestions = await self.completer.get_suggestions_async(prefix)
            # Verify prefix hasn't changed while we were fetching
            if self._autocomplete_state.prefix == prefix:
                self._show_suggestions(suggestions)
        except Exception as e:
            # Log error and close autocomplete to avoid stale state
            logger.debug("Autocomplete fetch failed for prefix '%s': %s", prefix, e)
            # Close autocomplete if prefix still matches (user hasn't moved on)
            if self._autocomplete_state.prefix == prefix:
                self._close_autocomplete()

    def _show_suggestions(self, suggestions: list[str]) -> None:
        """Display suggestions in the popup.

        Parameters
        ----------
        suggestions : list of str
            Suggestions to display.
        """
        state = self._autocomplete_state

        if not suggestions:
            self._close_autocomplete()
            return

        # Update state (single source of truth)
        state.suggestions = suggestions
        state.highlighted_index = 0
        state.is_open = True

        # Create or update popup
        if self._autocomplete_popup:
            # Popup references state directly, just sync scroll manager
            self._autocomplete_popup.sync_from_state()
        else:
            # Create popup with reference to state
            self._autocomplete_popup = AutocompletePopup(state)
            self._position_popup()
            # Push to overlay manager if available
            if self._overlay_manager:
                self._autocomplete_overlay = self._overlay_manager.push(
                    self._autocomplete_popup,
                    layer_type=LayerType.DROPDOWN,
                )

    def _position_popup(self) -> None:
        """Position the popup relative to the input element.

        Positions the popup below the input by default, but adjusts if
        it would render off-screen:
        - Flips above the input if too close to bottom edge
        - Shifts left if too close to right edge
        """
        from wijjit.layout.bounds import Bounds

        if not self._autocomplete_popup or not self.bounds:
            return

        popup = self._autocomplete_popup
        popup_width, popup_height = popup.get_intrinsic_size()

        # Get terminal dimensions for bounds checking
        term_size = shutil.get_terminal_size()
        term_width = term_size.columns
        term_height = term_size.lines

        # Position below the input, aligned with word start
        # For TextInput: word_start maps to x position within the input
        # We add some offset for the input's border/decoration
        x = self.bounds.x + min(
            self._autocomplete_state.word_start + 2, self.bounds.width - 1
        )
        y = self.bounds.y + self.bounds.height

        # Check if popup would go off bottom of screen
        if y + popup_height > term_height:
            # Flip above the input
            y = self.bounds.y - popup_height
            # If still off-screen (input near top), clamp to top
            if y < 0:
                y = 0

        # Check if popup would go off right of screen
        if x + popup_width > term_width:
            # Shift left to fit
            x = term_width - popup_width

        # Ensure popup doesn't go off left edge
        if x < 0:
            x = 0

        popup.bounds = Bounds(x=x, y=y, width=popup_width, height=popup_height)

    def _apply_selected_suggestion(self) -> None:
        """Apply the currently selected suggestion."""
        state = self._autocomplete_state

        if not state.is_open or not state.suggestions:
            return

        suggestion = state.suggestions[state.highlighted_index]

        # Replace word in text
        old_value = self.value
        new_text, new_cursor = replace_word_at_cursor(
            self.value, self.cursor_pos, suggestion
        )

        # Set flag to prevent re-triggering autocomplete during the update
        self._autocomplete_applying = True
        try:
            self.value = new_text
            self.cursor_pos = new_cursor

            # Close popup
            self._close_autocomplete()

            # Trigger change event for proper re-rendering
            # The host class (TextInput) should have _emit_change method
            if hasattr(self, "_emit_change"):
                self._emit_change(old_value, new_text)
        finally:
            self._autocomplete_applying = False

    def _close_autocomplete(self) -> None:
        """Close the autocomplete popup."""
        state = self._autocomplete_state
        state.reset()

        if self._autocomplete_popup:
            if self._overlay_manager and self._autocomplete_overlay:
                self._overlay_manager.pop(self._autocomplete_overlay)
            self._autocomplete_popup = None
            self._autocomplete_overlay = None

    def _handle_autocomplete_blur(self) -> None:
        """Handle focus loss - close popup if configured.

        Call this when the element loses focus.
        """
        if not self.completer:
            return

        if self.completer.config.close_on_blur:
            self._close_autocomplete()

    @property
    def autocomplete_is_open(self) -> bool:
        """Check if the autocomplete popup is currently open.

        Returns
        -------
        bool
            True if popup is visible.
        """
        return self._autocomplete_state.is_open
