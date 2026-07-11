"""Tests for the last-resort terminal-restore coordinator.

These exercise :class:`wijjit.terminal.cleanup.TerminalCleanup` directly with
fresh instances (never the process singleton) so each test installs and then
fully tears down its own atexit/signal handlers, leaving global state untouched.
See ``etc``/``RELEASE_PLAN`` issue 2.2.
"""

from __future__ import annotations

import signal
import threading

import pytest

from wijjit.terminal.cleanup import TerminalCleanup, get_terminal_cleanup

_ON_MAIN_THREAD = threading.current_thread() is threading.main_thread()
_HAS_SIGTERM = hasattr(signal, "SIGTERM")


class TestRunOrdering:
    """run() invokes callbacks LIFO and is resilient to failures."""

    def test_callbacks_run_last_registered_first(self):
        order: list[str] = []
        cleanup = TerminalCleanup()
        t1 = cleanup.register(lambda: order.append("first"))
        t2 = cleanup.register(lambda: order.append("second"))
        try:
            cleanup.run()
            assert order == ["second", "first"]
        finally:
            cleanup.unregister(t1)
            cleanup.unregister(t2)

    def test_a_failing_callback_does_not_stop_the_rest(self):
        ran: list[str] = []

        def boom() -> None:
            raise RuntimeError("callback blew up")

        cleanup = TerminalCleanup()
        t1 = cleanup.register(lambda: ran.append("a"))
        t2 = cleanup.register(boom)
        t3 = cleanup.register(lambda: ran.append("c"))
        try:
            cleanup.run()  # must not raise
            # c (last) runs, boom is swallowed, a still runs.
            assert ran == ["c", "a"]
        finally:
            for tok in (t1, t2, t3):
                cleanup.unregister(tok)

    def test_run_is_idempotent(self):
        count = {"n": 0}
        cleanup = TerminalCleanup()
        tok = cleanup.register(lambda: count.__setitem__("n", count["n"] + 1))
        try:
            cleanup.run()
            cleanup.run()
            assert count["n"] == 2  # idempotent *callbacks* are the contract
        finally:
            cleanup.unregister(tok)


class TestRegistration:
    """register/unregister arm and disarm the exit and signal nets."""

    def test_unregistering_last_callback_tears_down_handlers(self):
        cleanup = TerminalCleanup()
        tok = cleanup.register(lambda: None)
        assert cleanup._atexit_registered is True
        cleanup.unregister(tok)
        assert cleanup._atexit_registered is False
        assert cleanup._prev_handlers == {}

    def test_unknown_token_is_ignored(self):
        cleanup = TerminalCleanup()
        cleanup.unregister(999)  # must not raise
        assert cleanup._callbacks == {}

    def test_intermediate_unregister_keeps_net_armed(self):
        cleanup = TerminalCleanup()
        t1 = cleanup.register(lambda: None)
        t2 = cleanup.register(lambda: None)
        try:
            cleanup.unregister(t1)
            assert cleanup._atexit_registered is True  # t2 still registered
        finally:
            cleanup.unregister(t2)
        assert cleanup._atexit_registered is False

    @pytest.mark.skipif(
        not (_ON_MAIN_THREAD and _HAS_SIGTERM),
        reason="signal installation requires the main thread and SIGTERM",
    )
    def test_signal_handler_installed_and_restored(self):
        previous = signal.getsignal(signal.SIGTERM)
        cleanup = TerminalCleanup()
        tok = cleanup.register(lambda: None)
        try:
            assert signal.getsignal(signal.SIGTERM) == cleanup._handle_signal
        finally:
            cleanup.unregister(tok)
        # Previous disposition is restored once the last callback is gone.
        assert signal.getsignal(signal.SIGTERM) == previous


class TestSignalHandling:
    """_handle_signal runs cleanup, then chains to the previous disposition."""

    def test_default_disposition_terminates_after_cleanup(self):
        ran: list[str] = []
        terminated: list[int] = []
        cleanup = TerminalCleanup()
        cleanup._terminate = terminated.append  # type: ignore[method-assign]
        tok = cleanup.register(lambda: ran.append("cleaned"))
        try:
            sig = getattr(signal, "SIGTERM")
            cleanup._prev_handlers[sig] = signal.SIG_DFL
            cleanup._handle_signal(sig, None)
            assert ran == ["cleaned"]  # cleanup ran first
            assert terminated == [sig]  # then re-raised for default disposition
        finally:
            cleanup.unregister(tok)

    def test_ignored_signal_cleans_but_does_not_terminate(self):
        terminated: list[int] = []
        cleanup = TerminalCleanup()
        cleanup._terminate = terminated.append  # type: ignore[method-assign]
        tok = cleanup.register(lambda: None)
        try:
            sig = getattr(signal, "SIGTERM")
            cleanup._prev_handlers[sig] = signal.SIG_IGN
            cleanup._handle_signal(sig, None)
            assert terminated == []  # honored the ignore; process keeps running
        finally:
            cleanup.unregister(tok)

    def test_previous_python_handler_is_chained(self):
        chained: list[int] = []
        terminated: list[int] = []
        cleanup = TerminalCleanup()
        cleanup._terminate = terminated.append  # type: ignore[method-assign]
        tok = cleanup.register(lambda: None)
        try:
            sig = getattr(signal, "SIGTERM")
            cleanup._prev_handlers[sig] = lambda s, f: chained.append(s)
            cleanup._handle_signal(sig, None)
            assert chained == [sig]  # host handler invoked
            assert terminated == []  # we did not also force termination
        finally:
            cleanup.unregister(tok)


def test_get_terminal_cleanup_returns_singleton():
    assert get_terminal_cleanup() is get_terminal_cleanup()
