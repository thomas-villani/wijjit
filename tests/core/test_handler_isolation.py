"""A raising event handler must not take the rest of the dispatch with it.

``HandlerRegistry.dispatch_async`` used to loop handlers with no try/except,
so one raising ``@app.on_key`` handler stopped every lower-priority handler
for the key, escaped ``EventLoop._handle_key_event_async`` (skipping the
routing of the key to the focused element), and in a real run counted toward
the main loop's three-strikes termination.
"""

import pytest

from wijjit.core.events import EventType, HandlerRegistry, HandlerScope, KeyEvent
from wijjit.testing import WijjitHarness, app_from_template


class TestRegistryIsolation:
    """Unit-level behavior of ``HandlerRegistry.dispatch_async``."""

    @pytest.mark.asyncio
    async def test_later_handler_runs_after_one_raises(self):
        errors: list[tuple[str, Exception]] = []
        registry = HandlerRegistry(
            error_handler=lambda message, exc: errors.append((message, exc))
        )
        ran: list[str] = []

        def broken(event):
            raise ValueError("broken")

        registry.register(broken, event_type=EventType.KEY, priority=10)
        registry.register(
            lambda e: ran.append("second"), event_type=EventType.KEY, priority=0
        )

        await registry.dispatch_async(KeyEvent(key="x"))

        assert ran == ["second"]
        assert len(errors) == 1
        message, exc = errors[0]
        assert isinstance(exc, ValueError)
        assert "broken" in message and "'x'" in message

    @pytest.mark.asyncio
    async def test_async_handler_failure_is_isolated(self):
        errors: list[Exception] = []
        registry = HandlerRegistry(error_handler=lambda m, e: errors.append(e))
        ran: list[str] = []

        async def broken(event):
            raise RuntimeError("async broken")

        async def ok(event):
            ran.append("ok")

        registry.register(broken, priority=10)
        registry.register(ok, priority=0)

        await registry.dispatch_async(KeyEvent(key="x"))

        assert ran == ["ok"]
        assert [type(e) for e in errors] == [RuntimeError]

    @pytest.mark.asyncio
    async def test_cancel_before_raising_still_stops_later_handlers(self):
        registry = HandlerRegistry(error_handler=lambda m, e: None)
        ran: list[str] = []

        def cancel_then_raise(event):
            event.cancel()
            raise ValueError

        registry.register(cancel_then_raise, priority=10)
        registry.register(lambda e: ran.append("later"), priority=0)

        event = KeyEvent(key="x")
        await registry.dispatch_async(event)

        assert ran == []
        assert event.cancelled

    @pytest.mark.asyncio
    async def test_no_error_handler_logs_and_continues(self, caplog):
        registry = HandlerRegistry()
        ran: list[str] = []

        def broken(event):
            raise ValueError("logged")

        registry.register(broken, scope=HandlerScope.GLOBAL, priority=10)
        registry.register(lambda e: ran.append("second"), priority=0)

        with caplog.at_level("ERROR"):
            await registry.dispatch_async(KeyEvent(key="x"))

        assert ran == ["second"]

    @pytest.mark.asyncio
    async def test_failing_error_handler_does_not_break_dispatch(self):
        def bad_sink(message, exc):
            raise RuntimeError("sink failed")

        registry = HandlerRegistry(error_handler=bad_sink)
        ran: list[str] = []

        def broken(event):
            raise ValueError

        registry.register(broken, priority=10)
        registry.register(lambda e: ran.append("second"), priority=0)

        await registry.dispatch_async(KeyEvent(key="x"))

        assert ran == ["second"]


class TestAppKeyHandlerIsolation:
    """End to end through the app, the event loop and the harness."""

    def test_second_on_key_handler_runs_and_error_is_reported(self):
        app = app_from_template("{% frame %}Hello{% endframe %}", state={"hits": 0})

        @app.on_key("x", priority=10)
        def broken_hotkey(event):
            raise ValueError("hotkey broke")

        @app.on_key("x")
        def counting_hotkey(event):
            app.state["hits"] += 1

        with WijjitHarness(app, size=(40, 6)) as h:
            h.press("x")
            assert h.state["hits"] == 1
            messages = [message for message, _ in h.errors]
            assert any("broken_hotkey" in m for m in messages), messages
            assert [type(e) for _, e in h.errors] == [ValueError]
            # A handler error is reported, not counted as a loop failure.
            assert app.event_loop._consecutive_errors == 0

            # Pressing it repeatedly keeps working: no three-strikes shutdown.
            h.press("x")
            h.press("x")
            h.press("x")
            assert h.state["hits"] == 4
            assert app.event_loop._consecutive_errors == 0

    def test_focused_element_still_receives_the_key(self):
        app = app_from_template(
            "{% frame %}{% textinput id='name' autofocus=True %}"
            "{% endtextinput %}{% endframe %}",
            state={"name": "abc"},
        )

        @app.on_key("backspace")
        def broken(event):
            raise ValueError("broken")

        with WijjitHarness(app, size=(40, 6)) as h:
            h.press("end")
            h.press("backspace")
            assert h.state["name"] == "ab"
            assert len(h.errors) == 1
