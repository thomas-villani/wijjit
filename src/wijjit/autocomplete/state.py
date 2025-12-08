"""Autocomplete state management.

This module provides the AutocompleteState dataclass for tracking
the state of an autocomplete popup.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AutocompleteState:
    """Tracks autocomplete popup state.

    This dataclass maintains all the state needed to manage an autocomplete
    popup, including whether it's open, the current suggestions, the highlighted
    selection, and the word being completed.

    Attributes
    ----------
    is_open : bool
        Whether the popup is currently visible.
    suggestions : list of str
        Current list of suggestions.
    highlighted_index : int
        Index of the currently highlighted suggestion (0-based).
    word_start : int
        Start position of the word being completed in the text.
    word_end : int
        End position of the word being completed (cursor position).
    prefix : str
        Current prefix being matched.

    Examples
    --------
    Create and manipulate state:

    >>> state = AutocompleteState()
    >>> state.is_open = True
    >>> state.suggestions = ["apple", "apricot", "avocado"]
    >>> state.highlighted_index = 0
    >>> state.move_highlight(1)  # Move down
    >>> state.selected_suggestion
    'apricot'

    Reset state when closing:

    >>> state.reset()
    >>> state.is_open
    False
    """

    is_open: bool = False
    suggestions: list[str] = field(default_factory=list)
    highlighted_index: int = 0
    word_start: int = 0
    word_end: int = 0
    prefix: str = ""

    def reset(self) -> None:
        """Reset to closed state.

        Resets all state values to their defaults, effectively closing
        the popup and clearing all suggestions.
        """
        self.is_open = False
        self.suggestions = []
        self.highlighted_index = 0
        self.word_start = 0
        self.word_end = 0
        self.prefix = ""

    def move_highlight(self, direction: int) -> None:
        """Move highlight up or down with clamping.

        Parameters
        ----------
        direction : int
            Direction to move: negative for up, positive for down.
            Movement is clamped at list boundaries (no wrap-around).

        Examples
        --------
        >>> state = AutocompleteState()
        >>> state.suggestions = ["a", "b", "c"]
        >>> state.highlighted_index = 0
        >>> state.move_highlight(1)  # Move down
        >>> state.highlighted_index
        1
        >>> state.move_highlight(-1)  # Move up
        >>> state.highlighted_index
        0
        >>> state.move_highlight(-1)  # Stays at top (clamped)
        >>> state.highlighted_index
        0

        Notes
        -----
        Uses clamping behavior (stops at boundaries) rather than wrapping.
        This is consistent with standard dropdown/autocomplete UX patterns.
        """
        if not self.suggestions:
            return
        self.highlighted_index = max(
            0, min(len(self.suggestions) - 1, self.highlighted_index + direction)
        )

    @property
    def selected_suggestion(self) -> str | None:
        """Get currently highlighted suggestion.

        Returns
        -------
        str or None
            The currently highlighted suggestion, or None if no suggestions
            are available or the index is out of bounds.

        Examples
        --------
        >>> state = AutocompleteState()
        >>> state.suggestions = ["apple", "banana"]
        >>> state.highlighted_index = 1
        >>> state.selected_suggestion
        'banana'
        >>> state.suggestions = []
        >>> state.selected_suggestion is None
        True
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
            True if there is at least one suggestion.
        """
        return len(self.suggestions) > 0

    @property
    def suggestion_count(self) -> int:
        """Get the number of suggestions.

        Returns
        -------
        int
            Number of current suggestions.
        """
        return len(self.suggestions)

    def update_suggestions(
        self, suggestions: list[str], prefix: str, word_start: int, word_end: int
    ) -> None:
        """Update suggestions and open popup if there are matches.

        Parameters
        ----------
        suggestions : list of str
            New list of suggestions.
        prefix : str
            The prefix that was matched.
        word_start : int
            Start position of the word in text.
        word_end : int
            End position of the word (cursor position).

        Notes
        -----
        If suggestions list is empty, the popup is closed. Otherwise,
        the popup is opened and the highlight is reset to the first item.
        """
        self.prefix = prefix
        self.word_start = word_start
        self.word_end = word_end
        self.suggestions = suggestions
        self.highlighted_index = 0

        if suggestions:
            self.is_open = True
        else:
            self.is_open = False

    def select_first(self) -> None:
        """Move highlight to first suggestion."""
        self.highlighted_index = 0

    def select_last(self) -> None:
        """Move highlight to last suggestion."""
        if self.suggestions:
            self.highlighted_index = len(self.suggestions) - 1
