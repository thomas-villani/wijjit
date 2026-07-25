"""Which handler paths ``RUN_SYNC_IN_EXECUTOR`` actually covers.

The config builds a ``ThreadPoolExecutor`` and ``HandlerRegistry.dispatch_async``
uses it, so a blocking key/mouse/change handler runs on a worker thread and the
event loop stays free for timers, background tasks and state callbacks.

``@app.on_action`` handlers do **not** go through the registry:
``Wijjit._dispatch_action`` calls the handler directly, so the config has no
effect on them at all. That gap is why ``executor_demo`` was pulled before
0.1.0 - every control in it was a button, so it demonstrated a setting it never
exercised. These tests pin both halves so the asymmetry cannot be lost again;
when ``_dispatch_action`` learns to honour the config, the second class fails
and gets updated rather than the behaviour changing unnoticed.
"""

import asyncio
import time

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.events import KeyEvent

# How long the blocking handler sleeps, and the background tick interval. The
# ratio matters, not the absolute values: ~25 ticks fit in one handler call.
BLOCK_SECONDS = 0.4
TICK_SECONDS = 0.02


async def _ticks_during(call, *, use_executor):
    """Run ``call`` and count how many background ticks the loop got through.

    Parameters
    ----------
    call : callable
        Takes the app, performs the dispatch, and may be a coroutine function.
    use_executor : bool
        Value for ``RUN_SYNC_IN_EXECUTOR``.

    Returns
    -------
    int
        Background ticks completed while the handler was running. Zero means the
        handler held the event-loop thread.
    """
    app = Wijjit(
        initial_state={},
        run_sync_in_executor=use_executor,
        executor_max_workers=4,
    )

    @app.on_key("b")
    def _key_handler(_event):
        time.sleep(BLOCK_SECONDS)

    @app.on_action("blocking")
    def _action_handler(_event):
        time.sleep(BLOCK_SECONDS)

    ticks = 0

    async def background():
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(TICK_SECONDS)

    task = asyncio.create_task(background())
    await asyncio.sleep(TICK_SECONDS * 2)
    ticks = 0
    try:
        result = call(app)
        if asyncio.iscoroutine(result):
            await result
    finally:
        task.cancel()
    return ticks


def _dispatch_key(app):
    return app.handler_registry.dispatch_async(
        KeyEvent(key="b"), executor=app.event_loop.executor
    )


def _dispatch_action(app):
    app._dispatch_action("blocking")


class TestRegistryHandlersUseTheExecutor:
    """Key/mouse/change handlers go through the registry, which honours it."""

    @pytest.mark.asyncio
    async def test_enabled_frees_the_event_loop(self):
        assert await _ticks_during(_dispatch_key, use_executor=True) > 0

    @pytest.mark.asyncio
    async def test_disabled_blocks_the_event_loop(self):
        assert await _ticks_during(_dispatch_key, use_executor=False) == 0


class TestActionHandlersBypassTheExecutor:
    """Documents a known gap, not a desired behaviour.

    ``_dispatch_action`` invokes the handler inline, so a blocking button
    handler holds the event-loop thread whatever ``RUN_SYNC_IN_EXECUTOR`` says.
    Tracked in roadmap.md; when it is fixed these expectations flip.
    """

    @pytest.mark.asyncio
    async def test_enabled_still_blocks_the_event_loop(self):
        assert await _ticks_during(_dispatch_action, use_executor=True) == 0

    @pytest.mark.asyncio
    async def test_disabled_blocks_the_event_loop(self):
        assert await _ticks_during(_dispatch_action, use_executor=False) == 0
