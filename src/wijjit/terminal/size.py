"""Per-context terminal size resolution.

Historically Wijjit read the terminal size directly from
:func:`shutil.get_terminal_size`, which returns the size of the *process's*
controlling terminal. That is correct for a single foreground TUI, but it makes
it impossible to serve several sessions of different sizes from one process
(for example a Wijjit app exposed over SSH, where each connection negotiates
its own PTY dimensions).

This module introduces a thin indirection: :func:`get_terminal_size` first
consults a :class:`~contextvars.ContextVar` and only falls back to
``shutil.get_terminal_size`` when no override is set. Because context variables
are task-local, each ``asyncio`` task (i.e. each connection driven by a
non-local :class:`~wijjit.terminal.backend.TerminalBackend`) observes its own
size without any global mutation.

Local, single-session apps never set the override, so they keep reading the
real terminal exactly as before - and the headless test harness, which pins the
size by monkeypatching ``shutil.get_terminal_size``, continues to work through
the fallback path.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

# The active per-task size override as ``(columns, lines)``, or ``None`` when the
# real terminal should be consulted. Task-local: reads in a child task inherit
# the value copied at task-creation time.
_size_override: ContextVar[tuple[int, int] | None] = ContextVar(
    "wijjit_terminal_size", default=None
)


def get_terminal_size() -> os.terminal_size:
    """Return the terminal size for the current context.

    Returns
    -------
    os.terminal_size
        The overridden ``(columns, lines)`` if one has been installed for the
        current context (see :func:`set_terminal_size`), otherwise the process
        terminal size from :func:`shutil.get_terminal_size`.
    """
    override = _size_override.get()
    if override is not None:
        return os.terminal_size(override)
    return shutil.get_terminal_size()


def set_terminal_size(columns: int, lines: int) -> None:
    """Install a terminal-size override for the current context.

    Intended to be called from within the task that runs a session's event
    loop (so the value is visible to render/layout code running in that task).
    A non-local backend seeds this at session start and refreshes it whenever
    the remote terminal is resized.

    Parameters
    ----------
    columns : int
        Terminal width in columns.
    lines : int
        Terminal height in rows.
    """
    _size_override.set((columns, lines))


def clear_terminal_size() -> None:
    """Remove any terminal-size override for the current context."""
    _size_override.set(None)


@contextmanager
def terminal_size_scope(columns: int, lines: int) -> Iterator[None]:
    """Temporarily override the terminal size within a ``with`` block.

    Parameters
    ----------
    columns : int
        Terminal width in columns.
    lines : int
        Terminal height in rows.

    Yields
    ------
    None
    """
    token = _size_override.set((columns, lines))
    try:
        yield
    finally:
        _size_override.reset(token)
