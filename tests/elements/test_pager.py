"""Tests for Pager element."""

import pytest

from wijjit.elements.display.pager import Page, Pager
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestPage:
    """Tests for Page dataclass."""

    def test_create_page_with_defaults(self):
        """Test creating a page with default values."""
        page = Page()
        assert page.title == ""
        assert page.content == ""

    def test_create_page_with_title(self):
        """Test creating a page with a title."""
        page = Page(title="Welcome")
        assert page.title == "Welcome"
        assert page.content == ""

    def test_create_page_with_content(self):
        """Test creating a page with content."""
        page = Page(title="Test", content="Hello World")
        assert page.title == "Test"
        assert page.content == "Hello World"


class TestPager:
    """Tests for Pager element."""

    def test_create_pager_with_defaults(self):
        """Test creating a pager with default values."""
        pager = Pager()
        assert pager.id is None
        assert pager.width == 60
        assert pager.height == 20
        assert pager.nav_position == "bottom"
        assert pager.show_indicator is True
        assert pager.show_titles is False
        assert pager.loop is False
        assert pager.current_page == 0
        assert pager.page_count == 0

    def test_create_pager_with_id(self):
        """Test creating a pager with an ID."""
        pager = Pager(id="my_pager")
        assert pager.id == "my_pager"

    def test_create_pager_with_custom_dimensions(self):
        """Test creating a pager with custom dimensions."""
        pager = Pager(width=80, height=30)
        assert pager.width == 80
        assert pager.height == 30

    def test_add_page(self):
        """Test adding pages to the pager."""
        pager = Pager()
        pager.add_page(Page(title="Page 1", content="Content 1"))
        pager.add_page(Page(title="Page 2", content="Content 2"))

        assert pager.page_count == 2
        assert pager.pages[0].title == "Page 1"
        assert pager.pages[1].title == "Page 2"

    def test_add_page_with_kwargs(self):
        """Test adding a page using keyword arguments."""
        pager = Pager()
        pager.add_page(title="My Page", content="My Content")

        assert pager.page_count == 1
        assert pager.pages[0].title == "My Page"
        assert pager.pages[0].content == "My Content"

    def test_remove_page(self):
        """Test removing a page from the pager."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))

        removed = pager.remove_page(1)
        assert removed.title == "Page 2"
        assert pager.page_count == 2
        assert pager.pages[0].title == "Page 1"
        assert pager.pages[1].title == "Page 3"

    def test_remove_page_invalid_index(self):
        """Test removing a page with invalid index."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))

        removed = pager.remove_page(5)
        assert removed is None
        assert pager.page_count == 1

    def test_remove_page_adjusts_current(self):
        """Test that removing pages adjusts current_page."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.current_page = 1

        pager.remove_page(1)
        assert pager.current_page == 0

    def test_clear_pages(self):
        """Test clearing all pages."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.current_page = 1

        pager.clear_pages()
        assert pager.page_count == 0
        assert pager.current_page == 0

    def test_go_to_page(self):
        """Test navigating to a specific page."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))

        result = pager.go_to_page(2)
        assert result is True
        assert pager.current_page == 2

    def test_go_to_page_clamped(self):
        """Test that page index is clamped to valid range."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))

        pager.go_to_page(10)
        assert pager.current_page == 1  # Clamped to last page

        pager.go_to_page(-5)
        assert pager.current_page == 0  # Clamped to first page

    def test_go_to_page_with_loop(self):
        """Test page navigation with loop enabled."""
        pager = Pager(loop=True)
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))

        # Go past the end
        pager.go_to_page(3)
        assert pager.current_page == 0  # Wrapped to first

        # Go before the start
        pager.go_to_page(-1)
        assert pager.current_page == 2  # Wrapped to last

    def test_next_page(self):
        """Test navigating to next page."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))

        result = pager.next_page()
        assert result is True
        assert pager.current_page == 1

    def test_next_page_at_end(self):
        """Test next_page at the end without loop."""
        pager = Pager(loop=False)
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.current_page = 1

        result = pager.next_page()
        assert result is False  # Already at end
        assert pager.current_page == 1

    def test_prev_page(self):
        """Test navigating to previous page."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.current_page = 1

        result = pager.prev_page()
        assert result is True
        assert pager.current_page == 0

    def test_prev_page_at_start(self):
        """Test prev_page at the start without loop."""
        pager = Pager(loop=False)
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))

        result = pager.prev_page()
        assert result is False  # Already at start
        assert pager.current_page == 0

    def test_first_page(self):
        """Test navigating to first page."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))
        pager.current_page = 2

        result = pager.first_page()
        assert result is True
        assert pager.current_page == 0

    def test_last_page(self):
        """Test navigating to last page."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))

        result = pager.last_page()
        assert result is True
        assert pager.current_page == 2

    def test_on_page_change_callback(self):
        """Test on_page_change callback is called."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))

        callback_args = []

        def on_change(old_idx, new_idx):
            callback_args.append((old_idx, new_idx))

        pager.on_page_change = on_change
        pager.next_page()

        assert len(callback_args) == 1
        assert callback_args[0] == (0, 1)

    def test_handle_key_right(self):
        """Test handling right arrow key."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))

        result = pager.handle_key(Keys.RIGHT)
        assert result is True
        assert pager.current_page == 1

    def test_handle_key_left(self):
        """Test handling left arrow key."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.current_page = 1

        result = pager.handle_key(Keys.LEFT)
        assert result is True
        assert pager.current_page == 0

    def test_handle_key_page_down(self):
        """Test handling page down key."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))

        result = pager.handle_key(Keys.PAGE_DOWN)
        assert result is True
        assert pager.current_page == 1

    def test_handle_key_page_up(self):
        """Test handling page up key."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.current_page = 1

        result = pager.handle_key(Keys.PAGE_UP)
        assert result is True
        assert pager.current_page == 0

    def test_handle_key_home(self):
        """Test handling home key."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))
        pager.current_page = 2

        result = pager.handle_key(Keys.HOME)
        assert result is True
        assert pager.current_page == 0

    def test_handle_key_end(self):
        """Test handling end key."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))

        result = pager.handle_key(Keys.END)
        assert result is True
        assert pager.current_page == 2

    def test_handle_key_unhandled(self):
        """Test that unrelated keys are not handled."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))

        result = pager.handle_key(Keys.ENTER)
        assert result is False

    def test_handle_key_empty_pager(self):
        """Test key handling with no pages."""
        pager = Pager()

        result = pager.handle_key(Keys.RIGHT)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_mouse_prev_button(self):
        """Test clicking the prev button."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.current_page = 1
        pager.bounds = Bounds(x=0, y=0, width=60, height=20)
        # Simulate button bounds (these would be set during rendering)
        pager._prev_button_bounds = (1, 18, 6, 1)
        pager._next_button_bounds = (53, 18, 6, 1)

        event = MouseEvent(
            x=3, y=18, button=MouseButton.LEFT, type=MouseEventType.CLICK
        )
        result = await pager.handle_mouse(event)

        assert result is True
        assert pager.current_page == 0

    @pytest.mark.asyncio
    async def test_handle_mouse_next_button(self):
        """Test clicking the next button."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.bounds = Bounds(x=0, y=0, width=60, height=20)
        pager._prev_button_bounds = (1, 18, 6, 1)
        pager._next_button_bounds = (53, 18, 6, 1)

        event = MouseEvent(
            x=55, y=18, button=MouseButton.LEFT, type=MouseEventType.CLICK
        )
        result = await pager.handle_mouse(event)

        assert result is True
        assert pager.current_page == 1

    @pytest.mark.asyncio
    async def test_handle_mouse_outside_buttons(self):
        """Test clicking outside buttons."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.bounds = Bounds(x=0, y=0, width=60, height=20)
        pager._prev_button_bounds = (1, 18, 6, 1)
        pager._next_button_bounds = (53, 18, 6, 1)

        event = MouseEvent(
            x=30, y=10, button=MouseButton.LEFT, type=MouseEventType.CLICK
        )
        result = await pager.handle_mouse(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_mouse_press_not_handled(self):
        """Test that PRESS events are not handled (only CLICK)."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.bounds = Bounds(x=0, y=0, width=60, height=20)
        pager._prev_button_bounds = (1, 18, 6, 1)
        pager._next_button_bounds = (53, 18, 6, 1)

        # PRESS event should NOT be handled (prevents double-fire)
        event = MouseEvent(
            x=55, y=18, button=MouseButton.LEFT, type=MouseEventType.PRESS
        )
        result = await pager.handle_mouse(event)

        assert result is False
        assert pager.current_page == 0  # Should not have changed

    def test_get_intrinsic_size(self):
        """Test getting intrinsic size."""
        pager = Pager(width=80, height=30)

        size = pager.get_intrinsic_size()
        assert size == (80, 30)

    def test_ephemeral_state(self):
        """Test getting and restoring ephemeral state."""
        pager = Pager()
        pager.add_page(Page(title="Page 1"))
        pager.add_page(Page(title="Page 2"))
        pager.add_page(Page(title="Page 3"))
        pager.current_page = 2

        state = pager.get_ephemeral_state()
        assert state == {"current_page": 2}

        pager2 = Pager()
        pager2.add_page(Page(title="Page 1"))
        pager2.add_page(Page(title="Page 2"))
        pager2.add_page(Page(title="Page 3"))
        pager2.restore_ephemeral_state(state)

        assert pager2.current_page == 2

    def test_focusable(self):
        """Test that pager is focusable."""
        pager = Pager()
        assert pager.focusable is True

    def test_border_style_options(self):
        """Test different border style options."""
        from wijjit.layout.frames import BorderStyle

        pager1 = Pager(border_style="single")
        assert pager1.border_style == BorderStyle.SINGLE

        pager2 = Pager(border_style="double")
        assert pager2.border_style == BorderStyle.DOUBLE

        pager3 = Pager(border_style="rounded")
        assert pager3.border_style == BorderStyle.ROUNDED

        pager4 = Pager(border_style="none")
        assert pager4.border_style == BorderStyle.NONE

    def test_nav_position_options(self):
        """Test different nav position options."""
        pager1 = Pager(nav_position="top")
        assert pager1.nav_position == "top"

        pager2 = Pager(nav_position="bottom")
        assert pager2.nav_position == "bottom"

        pager3 = Pager(nav_position="both")
        assert pager3.nav_position == "both"

    def test_frame_cache_initialized(self):
        """Test that frame cache is initialized empty."""
        pager = Pager()
        assert pager._frame_cache == {}

    def test_frame_cache_cleared_on_clear_pages(self):
        """Test that frame cache is cleared when pages are cleared."""
        pager = Pager()
        pager.add_page(Page(title="Page 1", content="Content 1"))
        # Simulate cached frame
        from wijjit.layout.frames import Frame

        pager._frame_cache[0] = Frame(width=10, height=5)

        pager.clear_pages()
        assert pager._frame_cache == {}

    def test_frame_cache_updated_on_remove_page(self):
        """Test that frame cache indices are updated when page is removed."""
        pager = Pager()
        pager.add_page(Page(title="Page 1", content="Content 1"))
        pager.add_page(Page(title="Page 2", content="Content 2"))
        pager.add_page(Page(title="Page 3", content="Content 3"))
        # Simulate cached frames
        from wijjit.layout.frames import Frame

        frame0 = Frame(width=10, height=5)
        frame2 = Frame(width=10, height=5)
        pager._frame_cache[0] = frame0
        pager._frame_cache[2] = frame2

        # Remove middle page
        pager.remove_page(1)

        # Frame 0 should still be at index 0
        # Frame 2 should now be at index 1
        assert 0 in pager._frame_cache
        assert pager._frame_cache[0] is frame0
        assert 1 in pager._frame_cache
        assert pager._frame_cache[1] is frame2
        assert 2 not in pager._frame_cache

    def test_get_active_frame_returns_cached_frame(self):
        """Test that _get_active_frame returns cached frame for string content."""
        pager = Pager()
        pager.add_page(Page(title="Page 1", content="Some text content"))
        from wijjit.layout.frames import Frame

        cached_frame = Frame(width=10, height=5)
        pager._frame_cache[0] = cached_frame

        result = pager._get_active_frame()
        assert result is cached_frame

    def test_get_active_frame_returns_none_without_cache(self):
        """Test that _get_active_frame returns None for string content without cache."""
        pager = Pager()
        pager.add_page(Page(title="Page 1", content="Some text content"))

        # No frame in cache yet
        result = pager._get_active_frame()
        assert result is None


class TestPagerWheelScroll:
    """Mouse wheel must delegate to the active frame consistently with keys."""

    def _pager_with_fake_frame(self, frame):
        pager = Pager()
        pager.add_page(Page(title="Page 1", content="Some text content"))
        pager.bounds = Bounds(0, 0, 40, 10)
        pager._frame_cache[0] = frame
        return pager

    @pytest.mark.asyncio
    async def test_wheel_delegates_to_frame_handle_scroll(self):
        class FakeFrame:
            def __init__(self):
                self.scrolls = []

            def handle_scroll(self, direction):
                self.scrolls.append(direction)
                return True

        frame = FakeFrame()
        pager = self._pager_with_fake_frame(frame)
        event = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_DOWN, x=5, y=5
        )
        result = await pager.handle_mouse(event)
        assert result is True
        assert frame.scrolls == [1]

    @pytest.mark.asyncio
    async def test_wheel_falls_back_to_handle_key(self):
        """Wheel no longer silently no-ops when the frame lacks handle_scroll."""

        class FrameKeyOnly:
            def __init__(self):
                self.keys = []

            def handle_key(self, key):
                self.keys.append(key)
                return True

        frame = FrameKeyOnly()
        pager = self._pager_with_fake_frame(frame)
        event = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_UP, x=5, y=5
        )
        result = await pager.handle_mouse(event)
        assert result is True
        assert frame.keys == [Keys.UP, Keys.UP, Keys.UP]


class TestPagerMixedContentLayout:
    """Regression test for a page that interleaves text and block elements.

    A page whose content mixes raw text with block elements (a vstack of a
    text input, checkboxes, and buttons) used to overlap: the pager assigned
    bounds without first running the constraint pass, so every child defaulted
    to height 1. Multi-line text and nested containers collapsed to one row and
    the following siblings drew on top of them. The fix calls
    ``calculate_constraints()`` before ``assign_bounds()`` so child heights are
    correct. This test drives the real render path and asserts the vertical
    ordering is preserved with no collisions.
    """

    TEMPLATE = """
    {% frame title="Mixed" border_style="single" %}
      {% pager id="pg" width=70 height=16 %}
        {% page title="Form" %}
INTRO_LINE_ONE
INTRO_LINE_TWO

{% vstack spacing=1 %}
  {% textinput id="who" placeholder="NAME_FIELD" width=30 %}{% endtextinput %}
  {% hstack spacing=2 %}
    {% checkbox id="opt" %}CHECK_LABEL{% endcheckbox %}
  {% endhstack %}
  {% hstack spacing=2 %}
    {% button action="go" %}DO_IT{% endbutton %}
  {% endhstack %}
{% endvstack %}

CLOSING_LINE
        {% endpage %}
      {% endpager %}
    {% endframe %}
    """

    def _row_of(self, lines: list[str], needle: str) -> int:
        """Return the index of the first row containing ``needle``."""
        for i, line in enumerate(lines):
            if needle in line:
                return i
        raise AssertionError(f"{needle!r} not found in:\n" + "\n".join(lines))

    def test_text_and_block_elements_do_not_overlap(self):
        """Each landmark lands on its own row in top-to-bottom source order."""
        from wijjit import Wijjit
        from wijjit.testing.harness import WijjitHarness

        app = Wijjit()
        app.view("main", default=True)(lambda: {"template": self.TEMPLATE})

        with WijjitHarness(app, size=(80, 24)) as harness:
            harness.tick(frames=1)
            lines = harness.screen().split("\n")

        intro1 = self._row_of(lines, "INTRO_LINE_ONE")
        intro2 = self._row_of(lines, "INTRO_LINE_TWO")
        field = self._row_of(lines, "NAME_FIELD")
        check = self._row_of(lines, "CHECK_LABEL")
        button = self._row_of(lines, "DO_IT")
        closing = self._row_of(lines, "CLOSING_LINE")

        # Strictly increasing rows => source order preserved, nothing overlaps.
        rows = [intro1, intro2, field, check, button, closing]
        assert rows == sorted(rows), f"rows out of order: {rows}"
        assert len(set(rows)) == len(rows), f"two landmarks share a row: {rows}"

        # The two intro lines are adjacent (multi-line text not collapsed).
        assert intro2 == intro1 + 1

        # The closing text sits below the button (was drawn above it before fix).
        assert closing > button
