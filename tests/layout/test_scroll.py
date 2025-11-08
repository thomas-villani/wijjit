"""Tests for scroll state management and utilities."""

from wijjit.layout.scroll import (
    ScrollManager,
    ScrollState,
    calculate_scrollbar_thumb,
    render_horizontal_scrollbar,
    render_vertical_scrollbar,
)


class TestScrollState:
    """Tests for ScrollState dataclass."""

    def test_create_scroll_state(self):
        """Test creating a basic scroll state."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
        assert state.content_size == 100
        assert state.viewport_size == 10
        assert state.scroll_position == 0

    def test_max_scroll_calculation(self):
        """Test max_scroll property calculation."""
        state = ScrollState(content_size=100, viewport_size=10)
        assert state.max_scroll == 90  # 100 - 10

    def test_max_scroll_when_content_fits(self):
        """Test max_scroll when content fits in viewport."""
        state = ScrollState(content_size=10, viewport_size=20)
        assert state.max_scroll == 0  # Content fits, no scrolling needed

    def test_max_scroll_exact_fit(self):
        """Test max_scroll when content exactly matches viewport."""
        state = ScrollState(content_size=10, viewport_size=10)
        assert state.max_scroll == 0

    def test_scroll_percentage_at_top(self):
        """Test scroll_percentage at top position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
        assert state.scroll_percentage == 0.0

    def test_scroll_percentage_at_bottom(self):
        """Test scroll_percentage at bottom position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=90)
        assert state.scroll_percentage == 1.0

    def test_scroll_percentage_at_middle(self):
        """Test scroll_percentage at middle position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=45)
        assert state.scroll_percentage == 0.5

    def test_scroll_percentage_when_content_fits(self):
        """Test scroll_percentage when no scrolling is needed."""
        state = ScrollState(content_size=10, viewport_size=20)
        assert state.scroll_percentage == 0.0

    def test_can_scroll_up_at_top(self):
        """Test can_scroll_up at top position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
        assert not state.can_scroll_up

    def test_can_scroll_up_not_at_top(self):
        """Test can_scroll_up when not at top."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=10)
        assert state.can_scroll_up

    def test_can_scroll_down_at_bottom(self):
        """Test can_scroll_down at bottom position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=90)
        assert not state.can_scroll_down

    def test_can_scroll_down_not_at_bottom(self):
        """Test can_scroll_down when not at bottom."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=50)
        assert state.can_scroll_down

    def test_is_scrollable_when_content_exceeds(self):
        """Test is_scrollable when content exceeds viewport."""
        state = ScrollState(content_size=100, viewport_size=10)
        assert state.is_scrollable

    def test_is_scrollable_when_content_fits(self):
        """Test is_scrollable when content fits in viewport."""
        state = ScrollState(content_size=10, viewport_size=20)
        assert not state.is_scrollable

    def test_is_scrollable_exact_fit(self):
        """Test is_scrollable when content exactly matches viewport."""
        state = ScrollState(content_size=10, viewport_size=10)
        assert not state.is_scrollable

    def test_post_init_clamps_scroll_position(self):
        """Test that __post_init__ clamps scroll position to valid range."""
        # Too high
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=200)
        assert state.scroll_position == 90  # Clamped to max_scroll

        # Negative
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=-10)
        assert state.scroll_position == 0  # Clamped to 0

    def test_empty_content(self):
        """Test scroll state with empty content."""
        state = ScrollState(content_size=0, viewport_size=10)
        assert state.max_scroll == 0
        assert not state.is_scrollable
        assert not state.can_scroll_up
        assert not state.can_scroll_down

    def test_zero_viewport(self):
        """Test scroll state with zero viewport."""
        state = ScrollState(content_size=100, viewport_size=0)
        assert state.max_scroll == 100
        assert state.is_scrollable


class TestScrollManager:
    """Tests for ScrollManager class."""

    def test_create_scroll_manager(self):
        """Test creating a basic scroll manager."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        assert manager.state.content_size == 100
        assert manager.state.viewport_size == 10
        assert manager.state.scroll_position == 0

    def test_create_with_initial_position(self):
        """Test creating scroll manager with initial position."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        assert manager.state.scroll_position == 50

    def test_scroll_by_positive(self):
        """Test scrolling down by a positive amount."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        new_pos = manager.scroll_by(5)
        assert new_pos == 5
        assert manager.state.scroll_position == 5

    def test_scroll_by_negative(self):
        """Test scrolling up by a negative amount."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        new_pos = manager.scroll_by(-10)
        assert new_pos == 40
        assert manager.state.scroll_position == 40

    def test_scroll_by_clamps_to_max(self):
        """Test that scroll_by clamps to maximum scroll position."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=80)
        new_pos = manager.scroll_by(50)  # Would exceed max
        assert new_pos == 90  # Clamped to max_scroll
        assert manager.state.scroll_position == 90

    def test_scroll_by_clamps_to_zero(self):
        """Test that scroll_by clamps to zero."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=5)
        new_pos = manager.scroll_by(-10)  # Would go negative
        assert new_pos == 0  # Clamped to 0
        assert manager.state.scroll_position == 0

    def test_scroll_to(self):
        """Test scrolling to an absolute position."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        new_pos = manager.scroll_to(50)
        assert new_pos == 50
        assert manager.state.scroll_position == 50

    def test_scroll_to_clamps_to_max(self):
        """Test that scroll_to clamps to maximum."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        new_pos = manager.scroll_to(200)
        assert new_pos == 90  # Clamped to max_scroll

    def test_scroll_to_clamps_to_zero(self):
        """Test that scroll_to clamps to zero."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        new_pos = manager.scroll_to(-10)
        assert new_pos == 0

    def test_scroll_to_top(self):
        """Test scrolling to top."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        new_pos = manager.scroll_to_top()
        assert new_pos == 0
        assert manager.state.scroll_position == 0

    def test_scroll_to_bottom(self):
        """Test scrolling to bottom."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        new_pos = manager.scroll_to_bottom()
        assert new_pos == 90
        assert manager.state.scroll_position == 90

    def test_page_up(self):
        """Test paging up."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        new_pos = manager.page_up()
        assert new_pos == 40  # 50 - 10
        assert manager.state.scroll_position == 40

    def test_page_up_clamps_to_zero(self):
        """Test that page_up clamps to zero."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=5)
        new_pos = manager.page_up()
        assert new_pos == 0  # Clamped

    def test_page_down(self):
        """Test paging down."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        new_pos = manager.page_down()
        assert new_pos == 60  # 50 + 10
        assert manager.state.scroll_position == 60

    def test_page_down_clamps_to_max(self):
        """Test that page_down clamps to maximum."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=85)
        new_pos = manager.page_down()
        assert new_pos == 90  # Clamped to max_scroll

    def test_update_content_size_larger(self):
        """Test updating content size to a larger value."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        manager.update_content_size(200)
        assert manager.state.content_size == 200
        assert manager.state.scroll_position == 50  # Unchanged

    def test_update_content_size_smaller(self):
        """Test updating content size to a smaller value."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=80)
        manager.update_content_size(50)
        assert manager.state.content_size == 50
        assert manager.state.scroll_position == 40  # Clamped to new max (50-10=40)

    def test_update_content_size_negative(self):
        """Test updating content size to negative (should clamp to 0)."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        manager.update_content_size(-10)
        assert manager.state.content_size == 0

    def test_update_viewport_size_larger(self):
        """Test updating viewport size to a larger value."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        manager.update_viewport_size(20)
        assert manager.state.viewport_size == 20
        assert manager.state.scroll_position == 50  # Unchanged

    def test_update_viewport_size_smaller(self):
        """Test updating viewport size to a smaller value."""
        manager = ScrollManager(content_size=100, viewport_size=50, initial_position=40)
        manager.update_viewport_size(10)
        assert manager.state.viewport_size == 10
        assert manager.state.scroll_position == 40  # Unchanged

    def test_update_viewport_size_causes_clamp(self):
        """Test viewport size update that requires scroll position clamp."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=90)
        manager.update_viewport_size(50)
        assert manager.state.viewport_size == 50
        assert manager.state.scroll_position == 50  # Clamped to new max (100-50=50)

    def test_get_visible_range_at_start(self):
        """Test get_visible_range at start of content."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=0)
        start, end = manager.get_visible_range()
        assert start == 0
        assert end == 10

    def test_get_visible_range_at_middle(self):
        """Test get_visible_range in middle of content."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=50)
        start, end = manager.get_visible_range()
        assert start == 50
        assert end == 60

    def test_get_visible_range_at_end(self):
        """Test get_visible_range at end of content."""
        manager = ScrollManager(content_size=100, viewport_size=10, initial_position=90)
        start, end = manager.get_visible_range()
        assert start == 90
        assert end == 100

    def test_get_visible_range_when_content_fits(self):
        """Test get_visible_range when content fits in viewport."""
        manager = ScrollManager(content_size=5, viewport_size=10)
        start, end = manager.get_visible_range()
        assert start == 0
        assert end == 5  # Only 5 items, not 10


class TestCalculateScrollbarThumb:
    """Tests for calculate_scrollbar_thumb function."""

    def test_thumb_at_top(self):
        """Test scrollbar thumb calculation at top position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
        thumb_start, thumb_size = calculate_scrollbar_thumb(state, 20)
        assert thumb_start == 0
        assert thumb_size == 2  # 10/100 * 20 = 2

    def test_thumb_at_bottom(self):
        """Test scrollbar thumb calculation at bottom position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=90)
        thumb_start, thumb_size = calculate_scrollbar_thumb(state, 20)
        assert thumb_size == 2
        # Available space for thumb = 20 - 2 = 18
        # At 100% scroll (position 90), thumb should be at position 18
        assert thumb_start == 18

    def test_thumb_at_middle(self):
        """Test scrollbar thumb calculation at middle position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=45)
        thumb_start, thumb_size = calculate_scrollbar_thumb(state, 20)
        assert thumb_size == 2
        # Available space = 18, at 50% scroll should be at ~9
        assert thumb_start == 9

    def test_thumb_when_content_fits(self):
        """Test scrollbar thumb when content fits in viewport."""
        state = ScrollState(content_size=10, viewport_size=20)
        thumb_start, thumb_size = calculate_scrollbar_thumb(state, 20)
        assert thumb_start == 0
        assert thumb_size == 20  # Fills entire bar

    def test_thumb_minimum_size(self):
        """Test that thumb has minimum size of 1."""
        state = ScrollState(content_size=1000, viewport_size=1)
        thumb_start, thumb_size = calculate_scrollbar_thumb(state, 20)
        assert thumb_size >= 1  # At least 1 character

    def test_thumb_with_small_bar(self):
        """Test thumb calculation with small scrollbar."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
        thumb_start, thumb_size = calculate_scrollbar_thumb(state, 5)
        assert thumb_size >= 1  # At least 1

    def test_thumb_proportional_to_viewport(self):
        """Test that thumb size is proportional to viewport/content ratio."""
        # 50% viewport ratio
        state1 = ScrollState(content_size=100, viewport_size=50)
        _, size1 = calculate_scrollbar_thumb(state1, 20)
        # 25% viewport ratio
        state2 = ScrollState(content_size=100, viewport_size=25)
        _, size2 = calculate_scrollbar_thumb(state2, 20)
        # Larger viewport should have larger thumb
        assert size1 > size2


class TestRenderVerticalScrollbar:
    """Tests for render_vertical_scrollbar function."""

    def test_render_scrollbar_at_top(self):
        """Test rendering scrollbar at top position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
        scrollbar = render_vertical_scrollbar(state, 10)
        assert len(scrollbar) == 10
        # First character should be thumb
        assert scrollbar[0] == "█"
        # Rest should be track
        assert all(c == "│" for c in scrollbar[2:])

    def test_render_scrollbar_at_bottom(self):
        """Test rendering scrollbar at bottom position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=90)
        scrollbar = render_vertical_scrollbar(state, 10)
        assert len(scrollbar) == 10
        # Last character should be thumb
        assert scrollbar[-1] == "█"

    def test_render_scrollbar_when_content_fits(self):
        """Test rendering scrollbar when content fits."""
        state = ScrollState(content_size=10, viewport_size=20)
        scrollbar = render_vertical_scrollbar(state, 10)
        assert len(scrollbar) == 10
        # All track characters (no scrolling needed)
        assert all(c == "│" for c in scrollbar)

    def test_render_scrollbar_characters(self):
        """Test that scrollbar uses correct characters."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=50)
        scrollbar = render_vertical_scrollbar(state, 10)
        # Should only contain track and thumb characters
        assert all(c in ["│", "█"] for c in scrollbar)

    def test_render_scrollbar_height_matches(self):
        """Test that rendered scrollbar matches requested height."""
        state = ScrollState(content_size=100, viewport_size=10)
        for height in [5, 10, 20, 50]:
            scrollbar = render_vertical_scrollbar(state, height)
            assert len(scrollbar) == height


class TestRenderHorizontalScrollbar:
    """Tests for render_horizontal_scrollbar function."""

    def test_render_horizontal_scrollbar_at_start(self):
        """Test rendering horizontal scrollbar at start position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
        scrollbar = render_horizontal_scrollbar(state, 20)
        assert len(scrollbar) == 20
        # First characters should be thumb
        assert scrollbar[0] == "█"

    def test_render_horizontal_scrollbar_at_end(self):
        """Test rendering horizontal scrollbar at end position."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=90)
        scrollbar = render_horizontal_scrollbar(state, 20)
        assert len(scrollbar) == 20
        # Last character should be thumb
        assert scrollbar[-1] == "█"

    def test_render_horizontal_scrollbar_when_content_fits(self):
        """Test rendering horizontal scrollbar when content fits."""
        state = ScrollState(content_size=10, viewport_size=20)
        scrollbar = render_horizontal_scrollbar(state, 20)
        assert len(scrollbar) == 20
        # All track characters
        assert all(c == "─" for c in scrollbar)

    def test_render_horizontal_scrollbar_characters(self):
        """Test that horizontal scrollbar uses correct characters."""
        state = ScrollState(content_size=100, viewport_size=10, scroll_position=50)
        scrollbar = render_horizontal_scrollbar(state, 20)
        # Should only contain track and thumb characters
        assert all(c in ["─", "█"] for c in scrollbar)

    def test_render_horizontal_scrollbar_width_matches(self):
        """Test that rendered scrollbar matches requested width."""
        state = ScrollState(content_size=100, viewport_size=10)
        for width in [10, 20, 40, 80]:
            scrollbar = render_horizontal_scrollbar(state, width)
            assert len(scrollbar) == width


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_content_zero_viewport(self):
        """Test with both content and viewport at zero."""
        state = ScrollState(content_size=0, viewport_size=0)
        assert state.max_scroll == 0
        assert not state.is_scrollable

    def test_single_line_content(self):
        """Test with single line of content."""
        manager = ScrollManager(content_size=1, viewport_size=10)
        start, end = manager.get_visible_range()
        assert start == 0
        assert end == 1

    def test_single_line_viewport(self):
        """Test with single line viewport."""
        manager = ScrollManager(content_size=100, viewport_size=1)
        assert manager.state.max_scroll == 99
        manager.scroll_to(50)
        start, end = manager.get_visible_range()
        assert start == 50
        assert end == 51

    def test_very_large_content(self):
        """Test with very large content size."""
        manager = ScrollManager(content_size=1000000, viewport_size=10)
        assert manager.state.max_scroll == 999990
        manager.scroll_to_bottom()
        assert manager.state.scroll_position == 999990

    def test_multiple_scrolls_in_sequence(self):
        """Test multiple scroll operations in sequence."""
        manager = ScrollManager(content_size=100, viewport_size=10)
        manager.scroll_by(10)
        manager.scroll_by(5)
        manager.page_down()
        manager.scroll_to(50)
        manager.page_up()
        assert manager.state.scroll_position == 40
