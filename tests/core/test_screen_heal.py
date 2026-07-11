"""Tests for screen self-healing: error deferral + full-repaint heartbeat (2.3).

Two related fixes keep out-of-band writes from permanently corrupting the
alternate screen:

* ``_handle_error`` never prints a traceback to the shared TTY while the
  alternate screen is active. Non-fatal errors are buffered and flushed after
  the terminal is restored; fatal errors propagate (and print once) after
  teardown.
* A requested/heartbeat full repaint discards the renderer's cached on-screen
  buffer so the next frame is a complete redraw, overwriting foreign bytes.
"""

from __future__ import annotations

from unittest.mock import patch

from wijjit.core.app import Wijjit
from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = """
{% frame title="Heal" width=30 height=6 %}
  {% text %}hello{% endtext %}
{% endframe %}
"""


# ---------------------------------------------------------------------------
# Part 1: error output never lands in the alternate screen
# ---------------------------------------------------------------------------


class TestErrorDeferral:
    """Non-fatal errors are buffered while the alternate screen is active."""

    def test_nonfatal_error_in_alt_buffer_is_deferred_not_printed(self, capsys):
        app = Wijjit()
        app.screen_manager.in_alternate_buffer = True

        app._handle_error("render failed", ValueError("boom"))

        captured = capsys.readouterr()
        assert captured.err == ""  # nothing dumped into the TUI
        assert len(app._deferred_error_output) == 1
        assert "render failed" in app._deferred_error_output[0]
        assert "boom" in app._deferred_error_output[0]

    def test_nonfatal_error_without_alt_buffer_prints_immediately(self, capsys):
        app = Wijjit()
        app.screen_manager.in_alternate_buffer = False

        app._handle_error("render failed", ValueError("boom"))

        captured = capsys.readouterr()
        assert "render failed" in captured.err
        assert "boom" in captured.err
        assert app._deferred_error_output == []

    def test_fatal_error_raises_without_deferring_or_printing(self, capsys):
        app = Wijjit()
        app.screen_manager.in_alternate_buffer = True

        exc = ValueError("fatal boom")
        try:
            app._handle_error("initial render failed", exc, fatal=True)
        except ValueError as raised:
            assert raised is exc
        else:  # pragma: no cover - defensive
            raise AssertionError("fatal error should re-raise")

        captured = capsys.readouterr()
        # Propagation surfaces the traceback after teardown; _handle_error
        # itself neither prints nor buffers it.
        assert captured.err == ""
        assert app._deferred_error_output == []

    def test_flush_writes_buffered_errors_and_clears(self, capsys):
        app = Wijjit()
        app._deferred_error_output = ["first error\n", "second error\n"]

        app._flush_deferred_errors()

        captured = capsys.readouterr()
        assert "first error" in captured.err
        assert "second error" in captured.err
        assert app._deferred_error_output == []

    def test_flush_is_noop_when_nothing_deferred(self, capsys):
        app = Wijjit()

        app._flush_deferred_errors()  # must not raise

        assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# Part 2: forced full repaint evicts foreign bytes
# ---------------------------------------------------------------------------


class TestFullRepaint:
    """request_full_repaint / invalidate_display drive a complete redraw."""

    def test_request_full_repaint_sets_flags(self):
        app = app_from_template(TEMPLATE, state={})
        app.needs_render = False
        app._force_full_repaint = False

        app.request_full_repaint()

        assert app._force_full_repaint is True
        assert app.needs_render is True

    def test_invalidate_display_clears_cached_buffers(self):
        app = app_from_template(TEMPLATE, state={})
        with WijjitHarness(app, size=(40, 10)) as h:
            # A frame has been rendered, so the caches are populated.
            assert h.app.renderer._last_displayed_buffer is not None

            h.app.renderer.invalidate_display()

            assert h.app.renderer._last_displayed_buffer is None
            assert h.app.renderer._last_base_buffer is None

    def test_render_consumes_flag_and_invalidates_once(self):
        app = app_from_template(TEMPLATE, state={})
        with WijjitHarness(app, size=(40, 10)) as h:
            with patch.object(h.app.renderer, "invalidate_display") as mock_inv:
                h.app.request_full_repaint()
                h.tick()

            mock_inv.assert_called_once()
            assert h.app._force_full_repaint is False

    def test_full_repaint_still_renders_content(self):
        """A forced full repaint leaves the screen intact (content still drawn)."""
        app = app_from_template(TEMPLATE, state={})
        with WijjitHarness(app, size=(40, 10)) as h:
            h.app.request_full_repaint()
            h.tick()
            assert "hello" in h.screen()


# ---------------------------------------------------------------------------
# Part 2b: the event-loop heartbeat
# ---------------------------------------------------------------------------


class TestHeartbeat:
    """FULL_REPAINT_INTERVAL forces periodic full repaints; 0 disables it."""

    def test_heartbeat_fires_full_repaint_when_enabled(self):
        app = app_from_template(TEMPLATE, state={})
        app.config["FULL_REPAINT_INTERVAL"] = 0.01
        with WijjitHarness(app, size=(40, 10)) as h:
            # The harness never ran run_async's setup, so the timestamp is 0;
            # reset it explicitly to be independent of harness internals.
            h.app.event_loop._last_full_repaint_time = 0.0
            with patch.object(h.app, "request_full_repaint") as mock_repaint:
                h.tick()

            assert mock_repaint.called

    def test_heartbeat_disabled_by_default(self):
        app = app_from_template(TEMPLATE, state={})
        assert app.config["FULL_REPAINT_INTERVAL"] == 0.0
        with WijjitHarness(app, size=(40, 10)) as h:
            h.app.event_loop._last_full_repaint_time = 0.0
            with patch.object(h.app, "request_full_repaint") as mock_repaint:
                h.tick()

            mock_repaint.assert_not_called()


def test_event_loop_flushes_deferred_errors_on_teardown(capsys):
    """The loop flushes buffered tracebacks in its finally, after teardown."""
    from wijjit.terminal.input import Key, KeyType

    app = Wijjit()

    @app.view("main", default=True)
    def main():
        return {"template": "Main"}

    # Simulate a non-fatal error captured earlier in the run.
    app._deferred_error_output = ["deferred boom traceback\n"]

    async def quit_immediately(*args, **kwargs):
        return Key("ctrl+q", KeyType.CONTROL, "\x11")

    with (
        patch.object(app.screen_manager, "enter_alternate_buffer"),
        patch.object(app.screen_manager, "exit_alternate_buffer"),
        patch.object(
            app.input_handler, "read_input_async", side_effect=quit_immediately
        ),
        patch.object(app, "_render"),
    ):
        app.run()

    captured = capsys.readouterr()
    assert "deferred boom traceback" in captured.err
    assert app._deferred_error_output == []
