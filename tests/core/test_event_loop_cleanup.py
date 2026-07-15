"""Tests for the event loop's last-resort terminal-restore wiring.

The event loop arms a :class:`wijjit.terminal.cleanup.TerminalCleanup` callback
while it runs so SIGTERM/SIGHUP and an abnormal ``atexit`` still restore the
terminal (issue 2.2). These verify the callback is registered while running,
removed on a clean exit, and restores the right terminal state when invoked.
"""

from __future__ import annotations

import asyncio
import io
import threading
from unittest.mock import Mock, patch

import pytest

from wijjit import Wijjit, render_template_string
from wijjit.core.event_loop import EventLoop
from wijjit.core.state import State
from wijjit.terminal.ansi import ANSICursor, ANSIScreen, ANSIStyle
from wijjit.terminal.backend import TerminalBackend
from wijjit.terminal.cleanup import get_terminal_cleanup
from wijjit.terminal.input import Key, KeyType


class _NullInput:
    """An :class:`InputSource` that never yields input and touches nothing."""

    mouse_enabled = False

    async def read_input_async(self, timeout=None):
        return None

    def enable_mouse_tracking(self, mode=None):
        pass

    def disable_mouse_tracking(self) -> None:
        pass

    def close(self) -> None:
        pass

    def restore_terminal(self) -> None:
        pass


class _CaptureBackend(TerminalBackend):
    """Backend that records every byte written to the terminal.

    ``owns_terminal=False`` keeps it from installing process-global
    signal/atexit handlers or driving a real tty, so the loop's teardown is
    exercised in full without side effects on the test process.
    """

    owns_terminal = False
    provides_size = True

    def __init__(self, size: tuple[int, int] = (80, 24)) -> None:
        self.buffer = io.StringIO()
        self._size = size

    @property
    def screen_output(self) -> io.StringIO:
        return self.buffer

    def write_frame(self, data: str) -> None:
        self.buffer.write(data)

    def get_size(self) -> tuple[int, int]:
        return self._size

    def create_input_handler(self, *, enable_mouse, mouse_tracking_mode):
        return _NullInput()


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
        app.screen_manager.reset_sgr.assert_called_once()
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


class TestWorkerScheduledStateTasksVisibleToShutdown:
    """Review item 2.7: a state callback task created on the loop thread on
    behalf of a *worker-thread* state mutation must be visible to the event
    loop's shutdown cancel sweep (owned |= state._pending_tasks), not
    orphaned. This replicates the relevant slice of the ``finally`` block in
    ``EventLoop.run_async`` (event_loop.py ~277-301), including the
    ``await asyncio.sleep(0)`` added so a just-scheduled
    ``call_soon_threadsafe`` task-creator gets to run before the sweep
    samples ``_pending_tasks``.
    """

    @pytest.mark.asyncio
    async def test_worker_scheduled_task_is_cancelled_by_shutdown_sweep(self):
        state = State({"a": 0, "b": 0})

        # Capture state._loop via a loop-thread async callback first (mirrors
        # real app startup, where the first state change always happens on
        # the loop thread). Uses a different key than the long watcher below
        # so this quick round-trip doesn't itself have to wait on the
        # 10-second sleep.
        async def quick(key, old, new):
            return

        state.on_change(quick)
        state["b"] = 1
        await state.flush_pending_async()
        state.off_change(quick)

        async def long_watcher(key, old, new):
            await asyncio.sleep(10)

        state.watch("a", long_watcher)

        # Mutate from a worker thread: this hops task *creation* onto the
        # loop thread via call_soon_threadsafe (see
        # State._schedule_state_coroutine).
        t = threading.Thread(target=lambda: state.__setitem__("a", 2))
        t.start()
        t.join(timeout=5)
        assert not t.is_alive()

        # Give the loop a tick to let the call_soon_threadsafe task-creator
        # run, exactly as event_loop.py's shutdown sweep now does (a single
        # ``await asyncio.sleep(0)``). Poll a bounded number of ticks here
        # rather than hard-coding "exactly one" so the test isn't sensitive
        # to exactly how many ready-queue passes the scheduler needs to
        # drain the threadsafe-posted callback on a given platform/Python
        # version.
        for _ in range(50):
            if state._pending_tasks:
                break
            await asyncio.sleep(0)

        assert len(state._pending_tasks) == 1

        # Replicate the shutdown cancel sweep.
        owned: set[asyncio.Task] = set()
        owned |= state._pending_tasks
        pending_tasks = [
            task
            for task in owned
            if task is not asyncio.current_task() and not task.done()
        ]
        assert len(pending_tasks) == 1
        for task in pending_tasks:
            task.cancel()
        await asyncio.gather(*pending_tasks, return_exceptions=True)

        assert all(task.cancelled() for task in pending_tasks)
        assert state._pending_tasks == set()


class TestTerminalRestoreOnCrash:
    """Review Part 4 #5a: a crash *after* the terminal is set up must still
    restore it on the way out.

    The dangerous case is an exception that escapes ``run_async`` once the app
    is already in the alternate buffer with the cursor hidden - without the
    teardown, the user is dumped back to a hidden-cursor alternate screen with
    whatever text style the frame left active. A render-time template error is
    the cleanest trigger: the view builds a valid ``RenderedView`` (so setup
    completes and the alternate buffer is entered), and the error only fires
    when ``_render(fatal=True)`` executes the template, inside the try/finally.
    """

    def _run_until_crash(
        self, template: str, **context
    ) -> tuple[BaseException | None, str]:
        backend = _CaptureBackend()
        app = Wijjit(backend=backend)

        @app.view("main", default=True)
        def main():
            return render_template_string(template, **context)

        raised: BaseException | None = None
        try:
            asyncio.run(app.event_loop.run_async())
        except BaseException as exc:  # noqa: BLE001
            raised = exc
        return raised, backend.buffer.getvalue()

    def test_render_crash_propagates_and_restores_terminal(self):
        def boom():
            raise RuntimeError("boom during render")

        raised, out = self._run_until_crash(
            "{% text %}{{ boom() }}{% endtext %}", boom=boom
        )

        # The error is not swallowed - the app exits by propagating it.
        assert isinstance(raised, RuntimeError)

        # The terminal was actually set up before the crash...
        assert ANSIScreen.alternate_buffer_on() in out
        assert ANSICursor.hide() in out

        # ...and every teardown step was emitted on the way out.
        assert ANSIStyle.RESET in out, "SGR was not reset on crash teardown"
        assert ANSICursor.show() in out, "cursor was not shown on crash teardown"
        assert (
            ANSIScreen.alternate_buffer_off() in out
        ), "alternate buffer was not exited on crash teardown"

    def test_teardown_order_leaves_a_clean_normal_screen(self):
        def boom():
            raise RuntimeError("boom during render")

        _, out = self._run_until_crash("{% text %}{{ boom() }}{% endtext %}", boom=boom)

        enter = out.index(ANSIScreen.alternate_buffer_on())
        reset = out.rindex(ANSIStyle.RESET)
        show = out.rindex(ANSICursor.show())
        exit_alt = out.index(ANSIScreen.alternate_buffer_off())

        # Restore happens after setup, and the alternate buffer is left last so
        # the SGR reset and cursor-show land while still on the alt screen (SGR
        # state is shared, so the normal screen is clean once we switch back).
        assert enter < reset < exit_alt
        assert enter < show < exit_alt


@pytest.fixture(autouse=True)
def _no_leaked_cleanup_callbacks():
    """Guard: no test here should leave a callback armed on the singleton."""
    yield
    cleanup = get_terminal_cleanup()
    assert cleanup._callbacks == {}
