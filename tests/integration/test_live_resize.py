"""Live terminal resize driven through the running event loop (review Part 4 #4).

Before this, the harness was fixed-size and no test drove a resize, so the
loop's resize-detection path - re-layout, scroll re-clamp, overlay re-centre,
and repaint at the new dimensions - was entirely unguarded. ``WijjitHarness``
now exposes ``resize(width, height)``, which changes the size the app's backend
reports and pumps a frame so ``EventLoop._process_frame_async`` runs exactly as
it does on a real terminal resize.

The review's headline sequence is 80x24 -> 40x10 -> 120x50; these tests walk it
and assert each consequence the loop is responsible for.
"""

from wijjit import Frame
from wijjit.testing import WijjitHarness, app_from_template

FILL = (
    '{% frame id="box" width="fill" height="fill" title="Box" %}'
    "{% text %}content{% endtext %}"
    "{% endframe %}"
)

SCROLL = """
{% frame id="sc" width="fill" height="fill" scrollable=true %}
  {% vstack spacing=0 %}{% for i in range(40) %}{% text %}row {{ i }}{% endtext %}{% endfor %}{% endvstack %}
{% endframe %}
"""


def _dims(harness: WijjitHarness) -> tuple[int, int]:
    """Return the rendered screen's ``(rows, max_width)``."""
    lines = harness.lines()
    return len(lines), max((len(line) for line in lines), default=0)


def _find(harness: WijjitHarness, needle: str) -> tuple[int, int] | None:
    for row, line in enumerate(harness.lines()):
        col = line.find(needle)
        if col != -1:
            return row, col
    return None


class TestReLayoutOnResize:
    """A fill-sized view re-lays-out to the new dimensions with no stale cells."""

    def test_fill_content_tracks_terminal_size(self):
        app = app_from_template(FILL)
        with WijjitHarness(app, size=(80, 24)) as h:
            box = app.get_element_by_id("box")
            assert (box.bounds.width, box.bounds.height) == (80, 24)
            assert _dims(h) == (24, 80)

            # Shrink: the frame must re-lay-out smaller, and the screen buffer
            # must be exactly the new size - no rows or columns left over from
            # the larger frame (the "no stale cells" guarantee).
            h.resize(40, 10)
            box = app.get_element_by_id("box")
            assert (box.bounds.width, box.bounds.height) == (40, 10)
            assert _dims(h) == (10, 40)

            # Grow larger than the original: the frame fills the new area.
            h.resize(120, 50)
            box = app.get_element_by_id("box")
            assert (box.bounds.width, box.bounds.height) == (120, 50)
            assert _dims(h) == (50, 120)

    def test_no_row_exceeds_the_new_width_after_shrink(self):
        app = app_from_template(FILL)
        with WijjitHarness(app, size=(120, 40)) as h:
            h.resize(30, 12)
            lines = h.lines()
            assert len(lines) == 12
            assert all(len(line) <= 30 for line in lines)
            # The frame's title still renders, so this is a live frame, not a
            # blank/torn buffer.
            assert _find(h, "Box") is not None


class TestScrollReclampOnResize:
    """A scroll offset past the new content range is clamped on resize."""

    def test_scroll_position_clamps_when_viewport_grows(self):
        app = app_from_template(SCROLL)
        with WijjitHarness(app, size=(40, 10)) as h:
            sc = app.get_element_by_id("sc")
            sc.scroll_manager.scroll_to(9999)  # peg to the bottom
            h.tick()
            assert sc.scroll_manager.state.scroll_position > 0

            # Grow tall enough that all 40 content rows fit: max scroll becomes
            # 0 and the pegged-to-bottom offset must re-clamp down to 0 rather
            # than leaving the view scrolled past its (now shorter) range.
            h.resize(40, 46)
            sc = app.get_element_by_id("sc")
            assert sc.scroll_manager.state.max_scroll == 0
            assert sc.scroll_manager.state.scroll_position == 0

    def test_first_row_visible_after_growing_to_fit(self):
        app = app_from_template(SCROLL)
        with WijjitHarness(app, size=(40, 10)) as h:
            sc = app.get_element_by_id("sc")
            sc.scroll_manager.scroll_to(9999)
            h.tick()
            assert _find(h, "row 0") is None  # scrolled off the top

            h.resize(40, 46)
            # Re-clamped to the top, so the first row is visible again.
            assert _find(h, "row 0") is not None


class TestOverlayRecentreOnResize:
    """A centered overlay stays centered as the terminal resizes."""

    def _open_centered_modal(self, app) -> Frame:
        modal = Frame(width=30, height=8, id="dlg")
        modal.set_content("Modal body")
        modal.centered = True
        app.show_modal(modal)
        return modal

    def test_centered_modal_recenters_across_resizes(self):
        app = app_from_template(
            '{% frame width="fill" height="fill" %}base{% endframe %}'
        )
        with WijjitHarness(app, size=(80, 24)) as h:
            modal = self._open_centered_modal(app)
            h.tick()
            assert (modal.bounds.x, modal.bounds.y) == ((80 - 30) // 2, (24 - 8) // 2)
            assert _find(h, "Modal body") is not None

            h.resize(120, 50)
            assert (modal.bounds.x, modal.bounds.y) == ((120 - 30) // 2, (50 - 8) // 2)
            # It also actually paints at the new centre, not just internally.
            body = _find(h, "Modal body")
            assert body is not None
            assert 20 <= body[0] <= 30 and 45 <= body[1] <= 50

            h.resize(40, 12)
            assert (modal.bounds.x, modal.bounds.y) == ((40 - 30) // 2, (12 - 8) // 2)
            assert _find(h, "Modal body") is not None


class TestResizeContract:
    """resize() needs a live harness."""

    def test_resize_before_start_raises(self):
        app = app_from_template(FILL)
        harness = WijjitHarness(app, size=(80, 24))
        try:
            harness.resize(40, 10)
        except RuntimeError as exc:
            assert "start" in str(exc)
        else:
            raise AssertionError("resize() before start() should raise")
