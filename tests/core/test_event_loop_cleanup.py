"""Tests for the event loop's last-resort terminal-restore wiring.

The event loop arms a :class:`wijjit.terminal.cleanup.TerminalCleanup` callback
while it runs so SIGTERM/SIGHUP and an abnormal ``atexit`` still restore the
terminal (issue 2.2). These verify the callback is registered while running,
removed on a clean exit, and restores the right terminal state when invoked.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.event_loop import EventLoop
from wijjit.terminal.cleanup import get_terminal_cleanup
from wijjit.terminal.input import Key, KeyType


class TestEmergencyRestoreWiring:
    """The loop registers the emergency callback for its lifetime only."""

    def test_run_registers_while_running_and_unregisters_on_exit(self):
        app = Wijjit()

        @app.view("main", default=True)
        def main():
            return {"template": "Main"}

        loop = app.event_loop
        cleanup = get_terminal_cleanup()
        armed_during_run: list[bool] = []

        async def mock_read(*args, **kwargs):
            # Sampled from inside the running loop, before the quit takes effect.
            armed_during_run.append(
                loop._cleanup_token is not None
                and loop._emergency_terminal_restore in cleanup._callbacks.values()
            )
            return Key("ctrl+q", KeyType.CONTROL, "\x11")

        with (
            patch.object(app.screen_manager, "enter_alternate_buffer"),
            patch.object(app.screen_manager, "exit_alternate_buffer"),
            patch.object(app.input_handler, "read_input_async", side_effect=mock_read),
            patch.object(app, "_render"),
        ):
            app.run()

        # Armed for the duration of the loop...
        assert any(armed_during_run)
        # ...and cleanly removed afterward (no leaked callback, no dangling token).
        assert loop._cleanup_token is None
        assert loop._emergency_terminal_restore not in cleanup._callbacks.values()


class TestEmergencyRestoreBehavior:
    """_emergency_terminal_restore runs the signal-safe teardown subset."""

    def test_restores_suspend_mouse_cursor_and_alt_buffer(self):
        app = Mock()
        loop = EventLoop(app)

        loop._emergency_terminal_restore()

        app.suspend_manager.unregister.assert_called_once()
        app.input_handler.restore_terminal.assert_called_once()
        app.screen_manager.show_cursor.assert_called_once()
        app.screen_manager.exit_alternate_buffer.assert_called_once()

    def test_a_failing_step_does_not_abort_the_rest(self):
        app = Mock()
        app.input_handler.restore_terminal.side_effect = RuntimeError("boom")
        loop = EventLoop(app)

        # Must not raise, and must still exit the alternate buffer afterward.
        loop._emergency_terminal_restore()

        app.screen_manager.exit_alternate_buffer.assert_called_once()

    def test_does_not_join_threads_or_cancel_tasks(self):
        # It calls restore_terminal (thread-free), never the full close().
        app = Mock()
        loop = EventLoop(app)

        loop._emergency_terminal_restore()

        app.input_handler.close.assert_not_called()


@pytest.fixture(autouse=True)
def _no_leaked_cleanup_callbacks():
    """Guard: no test here should leave a callback armed on the singleton."""
    yield
    cleanup = get_terminal_cleanup()
    assert cleanup._callbacks == {}
