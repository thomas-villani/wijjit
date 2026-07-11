"""Last-resort terminal restoration on signals and interpreter exit.

A TUI puts the terminal into several non-default states: the alternate screen
buffer, a hidden cursor, raw (non-canonical) input mode, and mouse tracking.
The normal shutdown path - :meth:`wijjit.core.event_loop.EventLoop.run_async`'s
``finally`` block - restores all of this, and it covers a quit, ``Ctrl+C``, and
even a fatal render exception. Two exit paths bypass that ``finally`` entirely:

* ``SIGTERM`` / ``SIGHUP``: Python's default disposition terminates the process
  *without* running ``atexit`` handlers or unwinding the stack, so nothing
  restores the terminal. ``kill <pid>``, ``timeout``, a process manager, and CI
  teardown all land here, leaving the user in the alternate buffer with a hidden
  cursor, raw mode on, and - most visibly - ``\\x1b[?1002h`` / ``\\x1b[?1006h``
  mouse tracking still active, so the terminal spews escape codes on every mouse
  movement until ``reset`` is run.
* An abnormal exit that skips the ``finally`` but still runs ``atexit``: the
  :class:`wijjit.terminal.screen.ScreenManager` ``atexit`` net restores the
  cursor and alt buffer, but nothing disabled mouse tracking, so the mouse leak
  above persisted.

This module centralizes a small set of idempotent cleanup callbacks and wires
them into both nets at once: a single ``atexit`` handler and ``SIGTERM`` /
``SIGHUP`` handlers. The signal handlers run the callbacks and then chain to the
previous disposition (calling a prior Python handler, or re-raising under the
default handler so the process still terminates with the conventional
``128 + signum`` status).

Signals can only be installed from the main thread; when Wijjit runs off the
main thread (embedded in a host event loop, say), installation is skipped
silently and the ``atexit`` net still applies. On Windows ``SIGHUP`` does not
exist and is skipped; ``SIGTERM`` is registered but is rarely delivered to a
handler, so the practical win there is the ``atexit`` net.
"""

from __future__ import annotations

import atexit
import os
import signal
import threading
from collections.abc import Callable
from types import FrameType
from typing import Any

from wijjit.logging_config import get_logger

logger = get_logger(__name__)

# Signals whose default disposition terminates the process without unwinding
# the stack or running atexit. SIGHUP is absent on Windows.
_SIGNAL_NAMES = ("SIGTERM", "SIGHUP")


class TerminalCleanup:
    """Coordinator that restores the terminal on abnormal exit paths.

    Holds a set of idempotent, side-effect-only cleanup callbacks and runs them
    from a single ``atexit`` handler and from ``SIGTERM`` / ``SIGHUP`` handlers.
    Callbacks run in last-registered-first order (LIFO), mirroring how nested
    resources unwind, and each is guarded so one failing callback cannot stop
    the rest.

    The coordinator installs its handlers lazily on the first registration and
    removes them again once the last callback is unregistered, so an idle
    process (or a test suite that builds many apps) is left with the signal and
    ``atexit`` state it started with.

    Callbacks must be signal-safe: output-only work (writing ANSI escape
    sequences) or ``termios`` restoration is fine, but they must not join
    threads or acquire locks that a signal could have interrupted.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._next_token = 0
        self._atexit_registered = False
        self._signals_installed = False
        # Previous handler per installed signal, so we can chain and restore.
        self._prev_handlers: dict[int, Any] = {}

    def register(self, callback: Callable[[], None]) -> int:
        """Register a cleanup callback and arm the exit/signal nets.

        Parameters
        ----------
        callback : callable
            A no-argument, idempotent, signal-safe callback that restores some
            piece of terminal state.

        Returns
        -------
        int
            An opaque token to pass to :meth:`unregister`.
        """
        with self._lock:
            token = self._next_token
            self._next_token += 1
            self._callbacks[token] = callback
            self._ensure_installed()
            return token

    def unregister(self, token: int) -> None:
        """Remove a previously registered callback.

        Removing the last callback tears the ``atexit`` and signal handlers back
        down, restoring the previous signal dispositions. Unknown or already
        removed tokens are ignored.

        Parameters
        ----------
        token : int
            The token returned by :meth:`register`.
        """
        with self._lock:
            self._callbacks.pop(token, None)
            if not self._callbacks:
                self._teardown()

    def run(self) -> None:
        """Run all registered callbacks LIFO, swallowing any errors.

        Safe to call more than once; callbacks are expected to be idempotent.
        This is the ``atexit`` entry point and is also invoked by the signal
        handler before it chains to the previous disposition.
        """
        # Snapshot under the lock, then run without holding it: a callback that
        # touches the terminal must not be able to deadlock against register().
        with self._lock:
            callbacks = list(self._callbacks.values())
        for callback in reversed(callbacks):
            try:
                callback()
            except Exception:  # pragma: no cover - defensive, exit-time only
                # We are on an exit/signal path; there is nothing useful to do
                # with an error here and raising would abort remaining cleanup.
                pass

    # -- installation -------------------------------------------------------

    def _ensure_installed(self) -> None:
        """Arm the atexit and signal nets (caller holds the lock)."""
        if not self._atexit_registered:
            atexit.register(self.run)
            self._atexit_registered = True
        self._install_signals()

    def _install_signals(self) -> None:
        """Install SIGTERM/SIGHUP handlers (caller holds the lock).

        Signals can only be handled from the main thread; off-thread
        installation raises ``ValueError`` and is skipped. Absent signals
        (``SIGHUP`` on Windows) are skipped too.
        """
        if self._signals_installed:
            return
        for name in _SIGNAL_NAMES:
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            try:
                self._prev_handlers[sig] = signal.signal(sig, self._handle_signal)
            except (ValueError, OSError) as exc:
                # ValueError: not the main thread. OSError: signal unsupported.
                logger.debug(f"Could not install {name} cleanup handler: {exc}")
        # Mark installed even if nothing registered, so we do not retry on
        # every subsequent register() from a worker thread.
        self._signals_installed = True

    def _teardown(self) -> None:
        """Remove the atexit and signal handlers (caller holds the lock)."""
        if self._atexit_registered:
            atexit.unregister(self.run)
            self._atexit_registered = False
        for sig, prev in self._prev_handlers.items():
            try:
                signal.signal(sig, prev)
            except (ValueError, OSError):
                pass
        self._prev_handlers.clear()
        self._signals_installed = False

    # -- signal handling ----------------------------------------------------

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        """Restore the terminal, then chain to the previous disposition.

        Parameters
        ----------
        signum : int
            The delivered signal number.
        frame : frame or None
            The interrupted stack frame (unused).
        """
        logger.info(f"Received signal {signum}; restoring terminal before exit")
        self.run()

        prev = self._prev_handlers.get(signum, signal.SIG_DFL)
        if prev is signal.SIG_IGN:
            # The process previously chose to ignore this signal; honor that and
            # keep running (our handler stays installed for a later delivery).
            return
        if callable(prev):
            # Chain to a handler the host application installed before us.
            prev(signum, frame)
            return
        # Restore the default disposition and re-raise so the process exits with
        # the conventional 128 + signum status instead of being swallowed.
        self._terminate(signum)

    def _terminate(self, signum: int) -> None:
        """Restore the default disposition for ``signum`` and re-raise it.

        Isolated so tests can drive :meth:`_handle_signal` without terminating
        the test process.
        """
        try:
            signal.signal(signum, signal.SIG_DFL)
        except (ValueError, OSError):  # pragma: no cover - platform dependent
            pass
        os.kill(os.getpid(), signum)


_INSTANCE: TerminalCleanup | None = None
_INSTANCE_LOCK = threading.Lock()


def get_terminal_cleanup() -> TerminalCleanup:
    """Return the process-wide :class:`TerminalCleanup` singleton.

    Returns
    -------
    TerminalCleanup
        The shared coordinator, created on first use.
    """
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:
                _INSTANCE = TerminalCleanup()
    return _INSTANCE
