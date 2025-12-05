"""Cursor control utilities for inline rendering.

This module provides ANSI escape sequence utilities for cursor control,
used by InlineApp to update content in place without alternate screen.
"""


def hide_cursor() -> str:
    """Return ANSI sequence to hide cursor.

    Returns
    -------
    str
        ANSI escape sequence to hide cursor
    """
    return "\x1b[?25l"


def show_cursor() -> str:
    """Return ANSI sequence to show cursor.

    Returns
    -------
    str
        ANSI escape sequence to show cursor
    """
    return "\x1b[?25h"


def move_cursor_up(n: int) -> str:
    """Return ANSI sequence to move cursor up n lines.

    Parameters
    ----------
    n : int
        Number of lines to move up

    Returns
    -------
    str
        ANSI escape sequence, or empty string if n <= 0
    """
    return f"\x1b[{n}A" if n > 0 else ""


def move_cursor_down(n: int) -> str:
    """Return ANSI sequence to move cursor down n lines.

    Parameters
    ----------
    n : int
        Number of lines to move down

    Returns
    -------
    str
        ANSI escape sequence, or empty string if n <= 0
    """
    return f"\x1b[{n}B" if n > 0 else ""


def move_to_column(col: int) -> str:
    """Return ANSI sequence to move cursor to column.

    Parameters
    ----------
    col : int
        Column number (1-indexed)

    Returns
    -------
    str
        ANSI escape sequence
    """
    return f"\x1b[{col}G"


def save_cursor_position() -> str:
    """Return ANSI sequence to save cursor position.

    Returns
    -------
    str
        ANSI escape sequence to save cursor position
    """
    return "\x1b[s"


def restore_cursor_position() -> str:
    """Return ANSI sequence to restore cursor position.

    Returns
    -------
    str
        ANSI escape sequence to restore cursor position
    """
    return "\x1b[u"


def clear_line() -> str:
    """Return ANSI sequence to clear current line.

    Returns
    -------
    str
        ANSI escape sequence to clear line
    """
    return "\x1b[2K"


def clear_to_end_of_line() -> str:
    """Return ANSI sequence to clear from cursor to end of line.

    Returns
    -------
    str
        ANSI escape sequence to clear to end of line
    """
    return "\x1b[K"


def carriage_return() -> str:
    """Return carriage return character.

    Returns
    -------
    str
        Carriage return character
    """
    return "\r"
