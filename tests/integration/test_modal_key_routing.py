"""Regression tests for modal / focus / key routing invariants.

These lock in the behaviors fixed during the demo-bug pass: app-level
``on_key`` handlers must not fire while a modal traps focus; the key that
opened a modal must not leak into the new modal's focused input; ``Ctrl+Q``
must always quit, even when an INPUT element would otherwise consume the
keystroke; and a dialog's default button must be activatable on the first
``Enter``/``Tab``.
"""

from __future__ import annotations

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.elements.modal import ConfirmDialog, TextInputDialog
from wijjit.testing import WijjitHarness


@pytest.fixture
def small_view_template() -> str:
    """Minimal view template used by most tests."""
    return """
{% frame width=40 height=8 title="Demo" %}
Counter: {{ state['counter'] }}
Press s to open dialog
{% endframe %}
"""


class TestModalBlocksAppHotkeys:
    """A trap-focus modal must block app-level ``on_key`` handlers."""

    def test_app_hotkey_does_not_fire_while_modal_open(
        self, small_view_template: str
    ) -> None:
        app = Wijjit(initial_state={"counter": 0, "dialogs_shown": 0})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {"template": small_view_template}

        @app.on_key("s")
        def open_dialog(_event) -> None:
            app.state["dialogs_shown"] += 1
            dialog = ConfirmDialog(message="Are you sure?", width=40, height=10)
            app.show_modal(dialog)

        @app.on_key("c")
        def bump_counter(_event) -> None:
            app.state["counter"] += 1

        with WijjitHarness(app, size=(60, 16)) as h:
            h.press("s")
            assert h.state["dialogs_shown"] == 1
            # While the modal is up, a second 's' must NOT spawn a second dialog
            h.press("s")
            assert h.state["dialogs_shown"] == 1, (
                f"second 's' leaked through modal; dialogs_shown="
                f"{h.state['dialogs_shown']}"
            )
            # An unrelated app hotkey must also be blocked
            h.press("c")
            assert h.state["counter"] == 0, (
                f"app hotkey 'c' fired while modal was up; counter="
                f"{h.state['counter']}"
            )


class TestQuitKeyAlwaysQuits:
    """``Ctrl+Q`` must reach the event loop's quit path under all focus states."""

    def test_ctrl_q_quits_with_textinput_focused(self) -> None:
        app = Wijjit(initial_state={"name": ""})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {
                "template": """
{% frame width=40 height=6 title="Form" %}
{% textinput id="name" bind="name" %}{% endtextinput %}
{% endframe %}
"""
            }

        with WijjitHarness(app, size=(50, 10)) as h:
            # Focus the TextInput
            h.press("tab")
            assert h.focused is not None
            # Type into it - keys must be consumed, app must not quit
            h.type("hi")
            assert h.running
            assert h.state["name"] == "hi"
            # Ctrl+Q must escape the focused INPUT element and quit
            h.press("ctrl+q")
            assert not h.running, "Ctrl+Q was swallowed by focused TextInput"

    def test_ctrl_q_quits_with_modal_open(self) -> None:
        app = Wijjit(initial_state={})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {"template": "{% frame width=20 height=4 %}hi{% endframe %}"}

        @app.on_key("d")
        def open_dialog(_event) -> None:
            app.show_modal(ConfirmDialog(message="Q?", width=30, height=8))

        with WijjitHarness(app, size=(50, 12)) as h:
            h.press("d")
            # Modal is up; Ctrl+Q must still quit
            h.press("ctrl+q")
            assert not h.running, "Ctrl+Q was swallowed by an open modal"


class TestTriggerKeyDoesNotLeakIntoDialog:
    """The key that opens a modal must not reach the modal's focused input."""

    def test_n_does_not_appear_in_text_input_dialog(self) -> None:
        app = Wijjit(initial_state={"submitted": None})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {"template": "{% frame width=20 height=4 %}hi{% endframe %}"}

        @app.on_key("n")
        def open_input_dialog(_event) -> None:
            def on_submit(value: str) -> None:
                app.state["submitted"] = value

            dialog = TextInputDialog(
                prompt="Enter your name:",
                on_submit=on_submit,
                width=40,
                height=10,
            )
            app.show_modal(dialog)

        with WijjitHarness(app, size=(60, 16)) as h:
            h.press("n")
            # Dialog is up. The 'n' must NOT have populated its TextInput.
            # Walk the open dialog and find its TextInput's value.
            top = app.overlay_manager.get_top_overlay()
            assert top is not None, "Dialog did not open"
            dialog_elem = top.element
            text_input = getattr(dialog_elem, "input", None) or getattr(
                dialog_elem, "text_input", None
            )
            assert (
                text_input is not None
            ), "TextInputDialog did not expose its input element"
            assert (
                text_input.value == ""
            ), f"Trigger key 'n' leaked into dialog input; value={text_input.value!r}"


class TestDialogTabCyclesFocus:
    """Tab/Shift+Tab must cycle focus inside a trap_focus modal."""

    def test_initial_focus_and_tab_cycle(self) -> None:
        """Opening a modal focuses the first button; Tab cycles."""
        app = Wijjit(initial_state={})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {"template": "{% frame width=20 height=4 %}hi{% endframe %}"}

        @app.on_key("d")
        def open_dialog(_event) -> None:
            app.show_modal(ConfirmDialog(message="Proceed?", width=40, height=8))

        with WijjitHarness(app, size=(60, 14)) as h:
            h.press("d")
            top = app.overlay_manager.get_top_overlay()
            assert top is not None
            dialog = top.element
            # Opening a modal focuses its first focusable element (Confirm).
            assert (
                h.focused is dialog.confirm_button
            ), f"Modal did not auto-focus Confirm; focused={h.focused!r}"
            # Tab moves to Cancel.
            h.press("tab")
            assert (
                h.focused is dialog.cancel_button
            ), f"Tab did not move focus to Cancel; focused={h.focused!r}"
            # Tab cycles back to Confirm.
            h.press("tab")
            assert (
                h.focused is dialog.confirm_button
            ), f"Tab did not cycle back to Confirm; focused={h.focused!r}"
            # Shift+Tab moves backward to Cancel.
            h.press("shift+tab")
            assert h.focused is dialog.cancel_button


class TestDialogFirstKeyActivatesButton:
    """A freshly-opened dialog should fire its default button on first Enter."""

    def test_enter_fires_focused_confirm(self) -> None:
        app = Wijjit(initial_state={"confirmed": False, "cancelled": False})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {"template": "{% frame width=20 height=4 %}hi{% endframe %}"}

        def on_confirm() -> None:
            app.state["confirmed"] = True

        def on_cancel() -> None:
            app.state["cancelled"] = True

        @app.on_key("d")
        def open_dialog(_event) -> None:
            dialog = ConfirmDialog(
                message="Proceed?",
                on_confirm=on_confirm,
                on_cancel=on_cancel,
                width=40,
                height=8,
            )

            overlay = app.show_modal(dialog)

            def close() -> None:
                app.overlay_manager.pop(overlay)

            dialog.close_callback = close

        with WijjitHarness(app, size=(60, 14)) as h:
            h.press("d")
            top = app.overlay_manager.get_top_overlay()
            assert top is not None
            dialog = top.element
            # Confirm should be focused immediately - no Tab required.
            assert h.focused is dialog.confirm_button
            # Enter on the focused Confirm fires on_confirm AND closes the dialog.
            h.press("enter")
            assert (
                h.state["confirmed"] is True
            ), "Enter on focused Confirm did not fire on_confirm"
            assert h.state["cancelled"] is False

    def test_tab_then_enter_fires_cancel(self) -> None:
        app = Wijjit(initial_state={"confirmed": False, "cancelled": False})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {"template": "{% frame width=20 height=4 %}hi{% endframe %}"}

        def on_confirm() -> None:
            app.state["confirmed"] = True

        def on_cancel() -> None:
            app.state["cancelled"] = True

        @app.on_key("d")
        def open_dialog(_event) -> None:
            dialog = ConfirmDialog(
                message="Proceed?",
                on_confirm=on_confirm,
                on_cancel=on_cancel,
                width=40,
                height=8,
            )

            overlay = app.show_modal(dialog)

            def close() -> None:
                app.overlay_manager.pop(overlay)

            dialog.close_callback = close

        with WijjitHarness(app, size=(60, 14)) as h:
            h.press("d")
            # Tab moves focus to Cancel; Enter fires it.
            h.press("tab")
            h.press("enter")
            assert h.state["cancelled"] is True
            assert h.state["confirmed"] is False


class TestFocusedInputKeyScope:
    """A focused TextInput must suppress only VIEW-scoped key handlers.

    Regression for the bug where a focused input set
    ``skip_view_handlers_for_input`` and the event loop then skipped *all*
    handler dispatch - so a global ``@app.on_key("q")`` quit never fired while
    typing in a field (``horizontal_scroll_demo`` "q doesn't quit"). Global and
    element handlers must still fire; only view-scoped handlers are suppressed.
    """

    def _build_app(self) -> Wijjit:
        app = Wijjit(initial_state={"name": "", "global_fired": 0, "view_fired": 0})

        @app.view("main", default=True)
        def main_view() -> dict:
            return {
                "template": """
{% frame width=40 height=6 title="Form" %}
{% textinput id="name" bind="name" %}{% endtextinput %}
{% endframe %}
"""
            }

        @app.on_key("g")
        def global_handler(_event) -> None:
            app.state["global_fired"] += 1

        def view_handler(event) -> None:
            if event.key and event.key.lower() == "v":
                app.state["view_fired"] += 1

        app.on(
            EventType.KEY,
            view_handler,
            scope=HandlerScope.VIEW,
            view_name="main",
        )
        return app

    def test_global_handler_fires_with_input_focused(self) -> None:
        app = self._build_app()
        with WijjitHarness(app, size=(50, 10)) as h:
            h.press("tab")
            assert h.focused is not None, "TextInput was not focused"
            h.press("g")
            assert h.state["global_fired"] == 1, (
                "global @app.on_key('g') did not fire while a TextInput was " "focused"
            )

    def test_view_handler_suppressed_with_input_focused(self) -> None:
        app = self._build_app()
        with WijjitHarness(app, size=(50, 10)) as h:
            h.press("tab")
            assert h.focused is not None
            # 'v' is a plain char: it types into the input, the view handler
            # must NOT fire.
            h.press("v")
            assert h.state["view_fired"] == 0, (
                "view-scoped handler fired for a plain char while a TextInput "
                "was focused"
            )
            assert h.state["name"] == "v", "char was not typed into the input"

    def test_view_handler_fires_without_input_focused(self) -> None:
        app = self._build_app()
        with WijjitHarness(app, size=(50, 10)) as h:
            # No focus yet: the view handler should receive 'v'.
            h.press("v")
            assert (
                h.state["view_fired"] == 1
            ), "view-scoped handler did not fire when no input was focused"
