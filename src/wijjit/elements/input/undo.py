"""Undo/redo history for text-editing elements.

This module provides :class:`EditSnapshot` and :class:`UndoHistory`, a small
bounded undo stack used by :class:`~wijjit.elements.input.text.TextArea` (and
therefore by :class:`~wijjit.elements.input.code_editor.CodeEditor`, which
inherits its editing path).

Notes
-----
Snapshots are whole-document, which sounds expensive and is not. A snapshot
stores ``tuple(lines)`` - a tuple of references to the *existing* line strings.
Python strings are immutable, so every line the edit did not touch is shared
with the previous snapshot rather than copied; a snapshot of an N-line document
costs N pointers plus the one line the edit actually rewrote. The stack is
bounded (:data:`DEFAULT_UNDO_LIMIT`) so a long session cannot grow without
limit.
"""

from dataclasses import dataclass

# Maximum number of undo entries retained. Each entry is cheap (see the module
# docstring), but the bound keeps a long editing session from growing without
# limit. Once exceeded, the oldest entry is dropped.
DEFAULT_UNDO_LIMIT = 200


@dataclass(frozen=True)
class EditSnapshot:
    """An immutable point-in-time capture of a text element's edit state.

    Attributes
    ----------
    lines : tuple of str
        The document, one entry per line. Line strings are shared with the
        element's live list rather than copied - they are immutable.
    cursor_row : int
        Cursor line index at capture time.
    cursor_col : int
        Cursor column index at capture time.
    selection_anchor : tuple of int or None
        ``(row, col)`` where the selection started, or None if there was no
        selection.
    """

    lines: tuple[str, ...]
    cursor_row: int
    cursor_col: int
    selection_anchor: tuple[int, int] | None


class UndoHistory:
    """A bounded undo/redo stack of :class:`EditSnapshot` states.

    Parameters
    ----------
    limit : int, optional
        Maximum number of undo entries to retain (default
        :data:`DEFAULT_UNDO_LIMIT`). The oldest entry is dropped once the
        limit is exceeded.

    Notes
    -----
    This class is deliberately ignorant of *what* changed - it stores whole
    states, not diffs. Callers decide when a snapshot is worth pushing; see
    ``TextArea.handle_key``, which coalesces a run of character insertions into
    a single entry so that typing a word is one undo, not one per letter.
    """

    def __init__(self, limit: int = DEFAULT_UNDO_LIMIT) -> None:
        self._limit = max(1, limit)
        self._undo: list[EditSnapshot] = []
        self._redo: list[EditSnapshot] = []

    def push(self, snapshot: EditSnapshot) -> None:
        """Record a pre-edit state and invalidate the redo stack.

        Parameters
        ----------
        snapshot : EditSnapshot
            The state as it was *before* the edit being recorded.
        """
        self._undo.append(snapshot)
        if len(self._undo) > self._limit:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self, current: EditSnapshot) -> EditSnapshot | None:
        """Pop the most recent pre-edit state.

        Parameters
        ----------
        current : EditSnapshot
            The element's present state, pushed onto the redo stack so the
            undo can be reversed.

        Returns
        -------
        EditSnapshot or None
            The state to restore, or None if there is nothing to undo.
        """
        if not self._undo:
            return None
        self._redo.append(current)
        return self._undo.pop()

    def redo(self, current: EditSnapshot) -> EditSnapshot | None:
        """Pop the most recently undone state.

        Parameters
        ----------
        current : EditSnapshot
            The element's present state, pushed back onto the undo stack.

        Returns
        -------
        EditSnapshot or None
            The state to restore, or None if there is nothing to redo.
        """
        if not self._redo:
            return None
        self._undo.append(current)
        return self._redo.pop()

    def clear(self) -> None:
        """Discard all history, undo and redo alike."""
        self._undo.clear()
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        """bool: True if there is at least one state to undo to."""
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        """bool: True if there is at least one state to redo to."""
        return bool(self._redo)
