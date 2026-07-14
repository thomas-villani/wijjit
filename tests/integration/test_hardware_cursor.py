"""Hardware-cursor parking tests (review Part 4, item 7).

Wijjit paints its caret as a reverse-video cell, but terminals and screen
readers track the *hardware* cursor. With ``HARDWARE_CURSOR`` enabled
(default), every frame in which a focused element reports a caret cell ends
with an absolute cursor-move plus show-cursor escape parking the terminal's
real cursor on that cell; when no caret is visible a single hide-cursor is
emitted. These tests assert on the raw emitted byte stream captured by the
harness (``h.last_frame``), i.e. exactly what a terminal would receive.
"""

import re

from wijjit.testing import WijjitHarness, app_from_template

SHOW = "\x1b[?25h"
HIDE = "\x1b[?25l"
CUP_SHOW_RE = re.compile(r"\x1b\[(\d+);(\d+)H\x1b\[\?25h$")


def _park_escape(x: int, y: int) -> str:
    """The exact frame suffix parking the cursor at 0-based screen (x, y)."""
    return f"\x1b[{y + 1};{x + 1}H{SHOW}"


INPUT_TPL = """
{% vstack spacing=0 %}
{% text %}header{% endtext %}
{% textinput id="inp" placeholder="type here" width=20 %}{% endtextinput %}
{% button id="btn" action="go" %}Go{% endbutton %}
{% endvstack %}
"""


def _focused_input_harness():
    app = app_from_template(INPUT_TPL)
    harness = WijjitHarness(app, size=(80, 24))
    return app, harness


def _focus_and_type(app, h, text: str) -> None:
    assert app.focus_element_by_id("inp")
    h.tick()
    h.type(text)


class TestTextInputParking:
    def test_caret_parks_after_typing(self):
        """The frame ends with CUP + show-cursor at the caret cell."""
        app, harness = _focused_input_harness()
        with harness as h:
            _focus_and_type(app, h, "abc")
            inp = app.get_element_by_id("inp")
            assert inp is not None and inp.bounds is not None

            # Default TextInput style is BRACKETS: one leading "[" column,
            # then the caret sits after the 3 typed characters.
            expected_x = inp.bounds.x + 1 + 3
            expected_y = inp.bounds.y
            assert inp.get_hardware_cursor_position() == (expected_x, expected_y)
            assert h.last_frame.endswith(
                _park_escape(expected_x, expected_y)
            ), f"frame does not end with the cursor park: {h.last_frame[-40:]!r}"

    def test_cjk_caret_advances_by_columns_not_characters(self):
        """Two wide characters park the cursor 4 columns in, not 2."""
        app, harness = _focused_input_harness()
        with harness as h:
            _focus_and_type(app, h, "日本")
            inp = app.get_element_by_id("inp")
            assert inp is not None and inp.bounds is not None

            expected_x = inp.bounds.x + 1 + 4  # bracket + two width-2 glyphs
            expected_y = inp.bounds.y
            assert inp.get_hardware_cursor_position() == (expected_x, expected_y)
            assert h.last_frame.endswith(_park_escape(expected_x, expected_y))

    def test_focusing_a_button_hides_the_cursor(self):
        """A focused element without a caret gets hide-cursor, no park."""
        app, harness = _focused_input_harness()
        with harness as h:
            _focus_and_type(app, h, "abc")
            h.press("tab")  # inp -> btn
            frame = h.last_frame
            assert frame.endswith(
                HIDE
            ), f"frame does not end with hide-cursor: {frame[-40:]!r}"
            assert SHOW not in frame

    def test_idle_frames_emit_no_cursor_bytes(self):
        """Once parked, frames without changes add no cursor escapes."""
        app, harness = _focused_input_harness()
        with harness as h:
            _focus_and_type(app, h, "abc")
            seen = len(h.emitted_frames)
            h.tick(frames=2)
            for frame in h.emitted_frames[seen:]:
                assert (
                    SHOW not in frame and HIDE not in frame
                ), f"idle frame re-emitted cursor escapes: {frame!r}"

    def test_disabled_config_emits_no_cursor_escapes(self):
        app, harness = _focused_input_harness()
        app.config["HARDWARE_CURSOR"] = False
        with harness as h:
            assert app.focus_element_by_id("inp")
            h.tick()
            h.type("abc")
            stream = h.emitted_ansi()
            assert SHOW not in stream and HIDE not in stream


class TestScrolledOutCaret:
    SCROLL_TPL = """
{% vstack spacing=0 %}
{% frame id="fr" border="single" width=40 height=6 scrollable=true %}
{% textarea id="ta" width=34 height=8 border="single" %}line-0
line-1
line-2{% endtextarea %}
{% endframe %}
{% endvstack %}
"""

    def test_caret_scrolled_above_frame_interior_hides_cursor(self):
        """A caret clipped out of a scrolled frame parks nothing and hides."""
        app = app_from_template(self.SCROLL_TPL)
        with WijjitHarness(app, size=(60, 16)) as h:
            assert app.focus_element_by_id("ta")
            h.tick()

            ta = app.get_element_by_id("ta")
            assert ta is not None
            # Caret (row 0, inside the textarea's own border) is visible.
            assert ta.get_hardware_cursor_position() is not None
            assert CUP_SHOW_RE.search(h.last_frame)

            # Scroll the outer frame so the textarea's caret row is above
            # the frame interior.
            frame = app.get_element_by_id("fr")
            assert frame is not None and frame.scroll_manager is not None
            frame.scroll_manager.scroll_to(3)
            h.tick()

            assert ta.get_hardware_cursor_position() is None
            assert h.last_frame.endswith(
                HIDE
            ), f"expected hide-cursor after clipping: {h.last_frame[-40:]!r}"
