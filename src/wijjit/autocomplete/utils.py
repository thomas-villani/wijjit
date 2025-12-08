"""Utility functions for autocomplete.

This module provides utility functions for word extraction and manipulation
used by the autocomplete system.
"""

from __future__ import annotations

import re

# Characters that are part of a "word" for completion purposes
# Matches alphanumeric characters and underscores
WORD_CHARS = re.compile(r"[\w]")


def get_word_at_cursor(text: str, cursor_pos: int) -> tuple[str, int, int]:
    """Extract the word at cursor position.

    Finds the word that the cursor is currently within or at the end of.
    A "word" consists of alphanumeric characters and underscores.

    Parameters
    ----------
    text : str
        The full text content.
    cursor_pos : int
        Current cursor position (0-indexed).

    Returns
    -------
    tuple of (str, int, int)
        A tuple containing:
        - word: The extracted word (empty string if cursor not in/after word)
        - start_index: Start position of word in text
        - end_index: End position (exclusive) of word in text

    Examples
    --------
    Word at end of text:

    >>> get_word_at_cursor("hello world", 5)
    ('hello', 0, 5)

    Cursor in middle of word:

    >>> get_word_at_cursor("hello world", 8)
    ('wor', 6, 8)

    Cursor after space (no word):

    >>> get_word_at_cursor("hello ", 6)
    ('', 6, 6)

    Empty text:

    >>> get_word_at_cursor("", 0)
    ('', 0, 0)

    Cursor at start:

    >>> get_word_at_cursor("hello", 0)
    ('', 0, 0)

    Notes
    -----
    For autocomplete, we typically only care about text up to the cursor,
    so the end position is always the cursor position. This means if the
    cursor is in the middle of a word, only the prefix up to the cursor
    is returned.
    """
    if not text or cursor_pos == 0:
        return ("", 0, 0)

    # Clamp cursor position to valid range
    cursor_pos = min(cursor_pos, len(text))

    # Find start of word (scan backwards from cursor)
    start = cursor_pos
    while start > 0 and WORD_CHARS.match(text[start - 1]):
        start -= 1

    # For autocomplete, end is always the cursor position
    # (we complete the partial word up to cursor)
    end = cursor_pos

    word = text[start:end]
    return (word, start, end)


def replace_word_at_cursor(
    text: str, cursor_pos: int, replacement: str
) -> tuple[str, int]:
    """Replace word at cursor with replacement text.

    Replaces the word at the cursor position with the given replacement.
    This is used when a user selects an autocomplete suggestion.

    Parameters
    ----------
    text : str
        Original text.
    cursor_pos : int
        Current cursor position.
    replacement : str
        Text to replace the word with.

    Returns
    -------
    tuple of (str, int)
        A tuple containing:
        - new_text: The text with the replacement applied
        - new_cursor_pos: New cursor position (after the replacement)

    Examples
    --------
    Replace partial word:

    >>> replace_word_at_cursor("hel", 3, "hello")
    ('hello', 5)

    Replace word in middle of text:

    >>> replace_word_at_cursor("say hel to me", 7, "hello")
    ('say hello to me', 9)

    Replace with cursor at end:

    >>> replace_word_at_cursor("app", 3, "application")
    ('application', 11)

    Notes
    -----
    The replacement always places the cursor at the end of the
    replacement text, ready for the user to continue typing.
    """
    word, start, end = get_word_at_cursor(text, cursor_pos)

    new_text = text[:start] + replacement + text[end:]
    new_cursor = start + len(replacement)

    return (new_text, new_cursor)


def is_word_char(char: str) -> bool:
    """Check if a character is a word character.

    Parameters
    ----------
    char : str
        Single character to check.

    Returns
    -------
    bool
        True if the character is alphanumeric or underscore.

    Examples
    --------
    >>> is_word_char('a')
    True
    >>> is_word_char('_')
    True
    >>> is_word_char(' ')
    False
    >>> is_word_char('-')
    False
    """
    return bool(WORD_CHARS.match(char))


def get_word_boundaries(text: str, cursor_pos: int) -> tuple[int, int]:
    """Get the full word boundaries including characters after cursor.

    Unlike get_word_at_cursor which only considers text up to cursor,
    this function finds the complete word boundaries including any
    word characters after the cursor.

    Parameters
    ----------
    text : str
        The full text content.
    cursor_pos : int
        Current cursor position (0-indexed).

    Returns
    -------
    tuple of (int, int)
        Start and end positions of the complete word.

    Examples
    --------
    Cursor in middle of word:

    >>> get_word_boundaries("hello world", 2)
    (0, 5)

    Cursor at word boundary:

    >>> get_word_boundaries("hello world", 5)
    (0, 5)

    Cursor between words:

    >>> get_word_boundaries("hello world", 6)
    (6, 11)
    """
    if not text:
        return (0, 0)

    cursor_pos = min(max(0, cursor_pos), len(text))

    # Find start (scan backwards)
    start = cursor_pos
    while start > 0 and WORD_CHARS.match(text[start - 1]):
        start -= 1

    # Find end (scan forwards)
    end = cursor_pos
    while end < len(text) and WORD_CHARS.match(text[end]):
        end += 1

    return (start, end)


def filter_suggestions(
    words: list[str],
    prefix: str,
    case_sensitive: bool = False,
    match_anywhere: bool = False,
    max_suggestions: int | None = None,
) -> list[str]:
    """Filter a word list based on a prefix.

    This is the shared matching logic used by WordCompleter and StateCompleter
    to filter suggestions based on a prefix string.

    Parameters
    ----------
    words : list of str
        List of words to filter.
    prefix : str
        The prefix to match against.
    case_sensitive : bool, optional
        Whether matching is case-sensitive (default: False).
    match_anywhere : bool, optional
        If True, matches substring anywhere in word instead of just prefix
        (default: False).
    max_suggestions : int or None, optional
        Maximum number of suggestions to return. None means no limit.

    Returns
    -------
    list of str
        Matching words, filtered and optionally limited.

    Examples
    --------
    Basic prefix matching:

    >>> filter_suggestions(["apple", "apricot", "banana"], "ap")
    ['apple', 'apricot']

    Case-insensitive matching (default):

    >>> filter_suggestions(["Apple", "APRICOT", "banana"], "ap")
    ['Apple', 'APRICOT']

    Case-sensitive matching:

    >>> filter_suggestions(["Apple", "apricot", "APPLE"], "ap", case_sensitive=True)
    ['apricot']

    Match anywhere in word:

    >>> filter_suggestions(["pineapple", "apple", "banana"], "apple", match_anywhere=True)
    ['pineapple', 'apple']

    With max suggestions:

    >>> filter_suggestions(["a1", "a2", "a3", "a4"], "a", max_suggestions=2)
    ['a1', 'a2']
    """
    if not prefix:
        return []

    compare_prefix = prefix if case_sensitive else prefix.lower()

    matches = []
    for word in words:
        if not isinstance(word, str):
            continue

        compare_word = word if case_sensitive else word.lower()

        if match_anywhere:
            if compare_prefix in compare_word:
                matches.append(word)
        else:
            if compare_word.startswith(compare_prefix):
                matches.append(word)

    if max_suggestions is not None:
        return matches[:max_suggestions]
    return matches


def split_into_words(text: str) -> list[tuple[str, int, int]]:
    """Split text into words with their positions.

    Parameters
    ----------
    text : str
        Text to split into words.

    Returns
    -------
    list of tuple
        List of (word, start, end) tuples for each word in the text.

    Examples
    --------
    >>> split_into_words("hello world")
    [('hello', 0, 5), ('world', 6, 11)]

    >>> split_into_words("one,two;three")
    [('one', 0, 3), ('two', 4, 7), ('three', 8, 13)]
    """
    words = []
    i = 0
    while i < len(text):
        # Skip non-word characters
        while i < len(text) and not WORD_CHARS.match(text[i]):
            i += 1

        if i >= len(text):
            break

        # Found start of word
        start = i

        # Find end of word
        while i < len(text) and WORD_CHARS.match(text[i]):
            i += 1

        words.append((text[start:i], start, i))

    return words
