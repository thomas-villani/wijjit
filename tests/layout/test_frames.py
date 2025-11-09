"""Tests for frame rendering."""

from wijjit.layout.frames import BorderStyle, Frame, FrameStyle
from wijjit.terminal.input import Key, KeyType
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestFrame:
    """Tests for Frame class."""

    def test_create_frame(self):
        """Test creating a basic frame."""
        frame = Frame(width=20, height=10)
        assert frame.width == 20
        assert frame.height == 10

    def test_minimum_dimensions(self):
        """Test minimum frame dimensions."""
        frame = Frame(width=1, height=1)
        assert frame.width == 3  # Enforced minimum
        assert frame.height == 3

    def test_render_empty_frame(self):
        """Test rendering an empty frame."""
        frame = Frame(width=10, height=5)
        result = frame.render()

        lines = result.split("\n")
        assert len(lines) == 5  # Should have 5 lines

        # Check borders
        assert lines[0].startswith("┌")
        assert lines[0].endswith("┐")
        assert lines[-1].startswith("└")
        assert lines[-1].endswith("┘")

    def test_render_with_content(self):
        """Test rendering frame with content."""
        frame = Frame(width=15, height=5)
        frame.set_content("Hello\nWorld")
        result = frame.render()

        lines = result.split("\n")
        assert "Hello" in lines[1]
        assert "World" in lines[2]

    def test_render_with_title(self):
        """Test rendering frame with title."""
        style = FrameStyle(title="Test")
        frame = Frame(width=20, height=5, style=style)
        result = frame.render()

        lines = result.split("\n")
        assert "Test" in lines[0]  # Title should be in top border

    def test_border_style_single(self):
        """Test single border style."""
        style = FrameStyle(border=BorderStyle.SINGLE)
        frame = Frame(width=10, height=3, style=style)
        result = frame.render()

        lines = result.split("\n")
        assert lines[0][0] == "┌"
        assert lines[0][-1] == "┐"
        assert lines[-1][0] == "└"
        assert lines[-1][-1] == "┘"

    def test_border_style_double(self):
        """Test double border style."""
        style = FrameStyle(border=BorderStyle.DOUBLE)
        frame = Frame(width=10, height=3, style=style)
        result = frame.render()

        lines = result.split("\n")
        assert lines[0][0] == "╔"
        assert lines[0][-1] == "╗"
        assert lines[-1][0] == "╚"
        assert lines[-1][-1] == "╝"

    def test_border_style_rounded(self):
        """Test rounded border style."""
        style = FrameStyle(border=BorderStyle.ROUNDED)
        frame = Frame(width=10, height=3, style=style)
        result = frame.render()

        lines = result.split("\n")
        assert lines[0][0] == "╭"
        assert lines[0][-1] == "╮"
        assert lines[-1][0] == "╰"
        assert lines[-1][-1] == "╯"

    def test_padding(self):
        """Test frame with padding."""
        style = FrameStyle(padding=(1, 2, 1, 2))  # top, right, bottom, left
        frame = Frame(width=20, height=8, style=style)
        frame.set_content("Content")
        result = frame.render()

        lines = result.split("\n")
        # First line after top border should be empty (top padding)
        # Last line before bottom border should be empty (bottom padding)
        assert len(lines) == 8

    def test_content_overflow(self):
        """Test content that overflows frame width."""
        frame = Frame(width=10, height=3)
        frame.set_content("This is a very long line that will overflow")
        result = frame.render()

        lines = result.split("\n")
        # Content should be clipped to fit
        middle_line = lines[1]
        # Remove borders to check content length
        content_part = middle_line[1:-1]  # Remove border characters
        assert len(content_part) <= 10

    def test_multiline_content(self):
        """Test frame with multiple content lines."""
        frame = Frame(width=15, height=6)
        frame.set_content("Line 1\nLine 2\nLine 3")
        result = frame.render()

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_set_content_empty(self):
        """Test setting empty content."""
        frame = Frame(width=10, height=3)
        frame.set_content("")
        assert frame.content == []

    def test_frame_dimensions_match(self):
        """Test that rendered frame matches specified dimensions."""
        frame = Frame(width=20, height=10)
        result = frame.render()

        lines = result.split("\n")
        assert len(lines) == 10

        # Check width (accounting for potential ANSI codes)
        from wijjit.terminal.ansi import visible_length

        for line in lines:
            assert visible_length(line) == 20


class TestContentAlignment:
    """Tests for content-level alignment within frames."""

    def test_content_align_horizontal_left(self):
        """Test content horizontal left alignment (default)."""
        style = FrameStyle(content_align_h="left")
        frame = Frame(width=20, height=5, style=style)
        frame.set_content("Hi")
        result = frame.render()

        lines = result.split("\n")
        content_line = lines[1]  # First content line
        # Remove borders and check content is left-aligned
        inner = content_line[2:-2]  # Remove borders and default padding
        assert inner.startswith("Hi")
        assert inner.endswith(" ")  # Padded on the right

    def test_content_align_horizontal_center(self):
        """Test content horizontal center alignment."""
        style = FrameStyle(content_align_h="center")
        frame = Frame(width=20, height=5, style=style)
        frame.set_content("Hi")
        result = frame.render()

        lines = result.split("\n")
        content_line = lines[1]
        # Remove borders and padding
        inner = content_line[2:-2]
        # "Hi" should be roughly centered in the available space
        # With inner width of 16 (20 - 2 borders - 2 padding), "Hi" (2 chars)
        # should have ~7 spaces on each side
        left_spaces = len(inner) - len(inner.lstrip())
        assert left_spaces > 0  # Should have leading spaces

    def test_content_align_horizontal_right(self):
        """Test content horizontal right alignment."""
        style = FrameStyle(content_align_h="right")
        frame = Frame(width=20, height=5, style=style)
        frame.set_content("Hi")
        result = frame.render()

        lines = result.split("\n")
        content_line = lines[1]
        # Remove borders and padding
        inner = content_line[2:-2]
        # "Hi" should be right-aligned
        assert inner.rstrip().endswith("Hi")

    def test_content_align_vertical_top(self):
        """Test content vertical top alignment (default)."""
        style = FrameStyle(content_align_v="top")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2")
        result = frame.render()

        lines = result.split("\n")
        # Content should start at first content line (line 1)
        # Lines 1-2 should have content, remaining lines should be empty
        assert "Line 1" in lines[1]
        assert "Line 2" in lines[2]
        # Lines after content should be empty (just borders and spaces)
        assert "Line" not in lines[3]

    def test_content_align_vertical_middle(self):
        """Test content vertical middle alignment."""
        style = FrameStyle(content_align_v="middle")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2")
        result = frame.render()

        lines = result.split("\n")
        # With height 10 (8 inner after borders), 2 content lines
        # should have ~3 empty lines above
        # First content line should not be at line 1
        assert "Line 1" not in lines[1]
        # Content should appear somewhere in the middle
        content_found = False
        for i in range(2, 6):  # Check middle lines
            if "Line 1" in lines[i]:
                content_found = True
                break
        assert content_found

    def test_content_align_vertical_bottom(self):
        """Test content vertical bottom alignment."""
        style = FrameStyle(content_align_v="bottom")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2")
        result = frame.render()

        lines = result.split("\n")
        # Content should be at the bottom
        # With height 10 (8 inner after borders), 2 content lines
        # should be at lines 7-8 (0-indexed: 7-8, before last border at 9)
        assert "Line 2" in lines[8]
        assert "Line 1" in lines[7]

    def test_content_align_combined(self):
        """Test combined horizontal and vertical alignment."""
        style = FrameStyle(content_align_h="center", content_align_v="middle")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Hi")
        result = frame.render()

        lines = result.split("\n")
        # Content should be centered both horizontally and vertically
        # Vertically: should not be at the first or last content lines
        assert "Hi" not in lines[1]
        assert "Hi" not in lines[8]
        # Content should appear in middle lines
        content_found = False
        for line in lines[3:7]:  # Check middle lines
            if "Hi" in line:
                content_found = True
                break
        assert content_found


class TestContentAlignmentEdgeCases:
    """Tests for edge cases in content alignment."""

    def test_content_align_with_multiline_middle(self):
        """Test vertical middle alignment with multiple content lines."""
        style = FrameStyle(content_align_v="middle")
        frame = Frame(width=20, height=12, style=style)
        frame.set_content("Line 1\nLine 2\nLine 3")
        result = frame.render()

        lines = result.split("\n")
        # With 10 inner lines (12 - 2 borders) and 3 content lines
        # Offset should be (10 - 3) // 2 = 3
        # Content should start at line 1 + 3 = line 4 (0-indexed)
        assert "Line 1" in lines[4]
        assert "Line 2" in lines[5]
        assert "Line 3" in lines[6]

    def test_content_align_with_padding(self):
        """Test content alignment with padding."""
        style = FrameStyle(
            padding=(1, 2, 1, 2), content_align_h="center", content_align_v="middle"
        )
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Test")
        result = frame.render()

        lines = result.split("\n")
        # Padding should reduce available space
        # Content should still be centered within the padded area
        assert len(lines) == 10

    def test_content_align_stretch_horizontal(self):
        """Test horizontal stretch alignment (default)."""
        style = FrameStyle(content_align_h="stretch")
        frame = Frame(width=20, height=5, style=style)
        frame.set_content("Short")
        result = frame.render()

        lines = result.split("\n")
        from wijjit.terminal.ansi import visible_length

        # Content line should be padded to fill the inner width
        content_line = lines[1]
        # Remove borders to check content area
        inner = content_line[1:-1]
        # Inner width = 20 - 2 (borders) = 18
        assert visible_length(inner) == 18

    def test_content_align_stretch_vertical(self):
        """Test vertical stretch alignment (default)."""
        style = FrameStyle(content_align_v="stretch")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2")
        result = frame.render()

        lines = result.split("\n")
        # With stretch, remaining lines after content should be filled
        # Inner height = 10 - 2 (borders) = 8
        # Content lines = 2
        # Remaining lines = 6
        # All 8 inner lines should be present (content + empty)
        assert len(lines) == 10

    def test_empty_content_with_alignment(self):
        """Test alignment with empty content."""
        style = FrameStyle(content_align_h="center", content_align_v="middle")
        frame = Frame(width=15, height=8, style=style)
        frame.set_content("")
        result = frame.render()

        lines = result.split("\n")
        # Should render properly with just empty space
        assert len(lines) == 8
        # All content lines should be empty (borders + spaces)
        for line in lines[1:-1]:
            assert line.startswith("│")
            assert line.endswith("│")

    def test_long_content_with_alignment(self):
        """Test alignment when content is wider than frame."""
        style = FrameStyle(content_align_h="center")
        frame = Frame(width=10, height=5, style=style)
        frame.set_content("This is a very long line that will be clipped")
        result = frame.render()

        lines = result.split("\n")
        from wijjit.terminal.ansi import visible_length

        # Content should be clipped to fit, not centered (no room)
        content_line = lines[1]
        assert visible_length(content_line) == 10

    def test_content_align_multiple_lines_different_lengths(self):
        """Test horizontal center alignment with lines of different lengths."""
        style = FrameStyle(content_align_h="center")
        frame = Frame(width=30, height=8, style=style)
        frame.set_content("Short\nMedium line\nVery long content here")
        result = frame.render()

        lines = result.split("\n")
        # Each line should be individually centered
        # "Short" should have more spaces than "Very long content here"
        line1 = lines[1]
        line3 = lines[3]
        # Check that shorter lines have leading spaces
        assert line1.index("Short") > line3.index("Very")


class TestContentAlignmentWithBorders:
    """Tests for content alignment with different border styles."""

    def test_content_align_with_single_border(self):
        """Test content alignment with single border style."""
        style = FrameStyle(
            border=BorderStyle.SINGLE,
            content_align_h="center",
            content_align_v="middle",
        )
        frame = Frame(width=20, height=8, style=style)
        frame.set_content("Test")
        result = frame.render()

        lines = result.split("\n")
        assert "┌" in lines[0]
        assert "└" in lines[-1]
        # Content should still be centered
        content_found = any("Test" in line for line in lines[3:5])
        assert content_found

    def test_content_align_with_double_border(self):
        """Test content alignment with double border style."""
        style = FrameStyle(
            border=BorderStyle.DOUBLE, content_align_h="right", content_align_v="bottom"
        )
        frame = Frame(width=20, height=8, style=style)
        frame.set_content("Test")
        result = frame.render()

        lines = result.split("\n")
        assert "╔" in lines[0]
        assert "╚" in lines[-1]
        # Content should be at bottom and right-aligned
        assert "Test" in lines[-2]


class TestFrameScrolling:
    """Tests for frame scrolling functionality."""

    def test_create_scrollable_frame(self):
        """Test creating a scrollable frame."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=10, style=style)
        assert frame.style.scrollable
        assert frame.scroll_manager is None  # Created when content is set

    def test_scroll_manager_created_on_content(self):
        """Test that scroll manager is created when setting content."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2\nLine 3")
        assert frame.scroll_manager is not None

    def test_no_scroll_manager_when_not_scrollable(self):
        """Test that scroll manager is not created for non-scrollable frames."""
        style = FrameStyle(scrollable=False)
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2\nLine 3")
        assert frame.scroll_manager is None

    def test_scroll_manager_updates_on_content_change(self):
        """Test that scroll manager updates when content changes."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2\nLine 3")
        initial_content_size = frame.scroll_manager.state.content_size

        frame.set_content("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        updated_content_size = frame.scroll_manager.state.content_size

        assert updated_content_size > initial_content_size

    def test_scrollable_frame_renders_with_scrollbar(self):
        """Test that scrollable frame renders with scrollbar when content exceeds height."""
        style = FrameStyle(scrollable=True, show_scrollbar=True)
        frame = Frame(width=20, height=8, style=style)

        # Create content with many lines
        content_lines = [f"Line {i}" for i in range(1, 21)]
        frame.set_content("\n".join(content_lines))

        result = frame.render()
        lines = result.split("\n")

        # Should render with scrollbar characters
        assert any("█" in line or "│" in line for line in lines[1:-1])

    def test_scrollable_frame_shows_only_visible_content(self):
        """Test that scrollable frame shows only visible portion of content."""
        style = FrameStyle(scrollable=True, padding=(0, 1, 0, 1))
        frame = Frame(width=20, height=8, style=style)

        # Create numbered content lines
        content_lines = [f"Line {i:02d}" for i in range(1, 51)]
        frame.set_content("\n".join(content_lines))

        # Initially at top
        result = frame.render()
        assert "Line 01" in result
        assert "Line 50" not in result  # Should not see bottom content

        # Scroll to bottom
        frame.scroll_manager.scroll_to_bottom()
        result = frame.render()
        assert "Line 01" not in result  # Should not see top content
        assert "Line 50" in result

    def test_handle_key_up_down(self):
        """Test handling up/down arrow keys for scrolling."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=8, style=style)
        content_lines = [f"Line {i}" for i in range(1, 51)]
        frame.set_content("\n".join(content_lines))

        # Initial position
        initial_pos = frame.scroll_manager.state.scroll_position

        # Scroll down
        down_key = Key("down", KeyType.SPECIAL)
        handled = frame.handle_key(down_key)
        assert handled
        assert frame.scroll_manager.state.scroll_position == initial_pos + 1

        # Scroll up
        up_key = Key("up", KeyType.SPECIAL)
        handled = frame.handle_key(up_key)
        assert handled
        assert frame.scroll_manager.state.scroll_position == initial_pos

    def test_handle_key_pageup_pagedown(self):
        """Test handling Page Up/Down keys for scrolling."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=8, style=style)
        content_lines = [f"Line {i}" for i in range(1, 101)]
        frame.set_content("\n".join(content_lines))

        viewport_size = frame.scroll_manager.state.viewport_size

        # Page down
        pagedown_key = Key("pagedown", KeyType.SPECIAL)
        handled = frame.handle_key(pagedown_key)
        assert handled
        assert frame.scroll_manager.state.scroll_position == viewport_size

        # Page up
        pageup_key = Key("pageup", KeyType.SPECIAL)
        handled = frame.handle_key(pageup_key)
        assert handled
        assert frame.scroll_manager.state.scroll_position == 0

    def test_handle_key_home_end(self):
        """Test handling Home/End keys for scrolling."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=8, style=style)
        content_lines = [f"Line {i}" for i in range(1, 101)]
        frame.set_content("\n".join(content_lines))

        # End key - scroll to bottom
        end_key = Key("end", KeyType.SPECIAL)
        handled = frame.handle_key(end_key)
        assert handled
        assert (
            frame.scroll_manager.state.scroll_position
            == frame.scroll_manager.state.max_scroll
        )

        # Home key - scroll to top
        home_key = Key("home", KeyType.SPECIAL)
        handled = frame.handle_key(home_key)
        assert handled
        assert frame.scroll_manager.state.scroll_position == 0

    def test_handle_key_non_scrollable_frame(self):
        """Test that non-scrollable frame doesn't handle scroll keys."""
        style = FrameStyle(scrollable=False)
        frame = Frame(width=20, height=8, style=style)
        frame.set_content("Line 1\nLine 2")

        down_key = Key("down", KeyType.SPECIAL)
        handled = frame.handle_key(down_key)
        assert not handled

    def test_handle_scroll_mouse_wheel(self):
        """Test handling mouse wheel scrolling."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=8, style=style)
        content_lines = [f"Line {i}" for i in range(1, 101)]
        frame.set_content("\n".join(content_lines))

        initial_pos = frame.scroll_manager.state.scroll_position

        # Scroll down with mouse wheel
        handled = frame.handle_scroll(1)
        assert handled
        assert frame.scroll_manager.state.scroll_position > initial_pos

        # Scroll up with mouse wheel
        handled = frame.handle_scroll(-1)
        assert handled
        assert frame.scroll_manager.state.scroll_position == initial_pos

    def test_handle_mouse_scroll_events(self):
        """Test handling mouse scroll events."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=8, style=style)
        content_lines = [f"Line {i}" for i in range(1, 101)]
        frame.set_content("\n".join(content_lines))

        initial_pos = frame.scroll_manager.state.scroll_position

        # Scroll down event
        scroll_down = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_DOWN, x=10, y=5
        )
        handled = frame.handle_mouse(scroll_down)
        assert handled
        assert frame.scroll_manager.state.scroll_position > initial_pos

        # Scroll up event
        scroll_up = MouseEvent(
            type=MouseEventType.SCROLL, button=MouseButton.SCROLL_UP, x=10, y=5
        )
        handled = frame.handle_mouse(scroll_up)
        assert handled

    def test_scrollbar_not_shown_when_content_fits(self):
        """Test that scrollbar is not shown when content fits in frame."""
        style = FrameStyle(scrollable=True, show_scrollbar=True)
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Line 1\nLine 2\nLine 3")

        # Content fits, so scrolling not needed
        assert frame._needs_scroll is False

        # Should render without scrollbar (uses static rendering)
        result = frame.render()
        # Frame should render normally
        assert len(result.split("\n")) == 10

    def test_scrollbar_shown_when_content_exceeds(self):
        """Test that scrollbar is shown when content exceeds frame height."""
        style = FrameStyle(scrollable=True, show_scrollbar=True)
        frame = Frame(width=20, height=6, style=style)

        # Create content that exceeds frame height
        content_lines = [f"Line {i}" for i in range(1, 21)]
        frame.set_content("\n".join(content_lines))

        # Content exceeds viewport
        assert frame._needs_scroll is True

        # Should render with scrollbar
        result = frame.render()
        # Check for scrollbar characters
        assert "█" in result or "│" in result

    def test_scroll_position_preserved_across_renders(self):
        """Test that scroll position is preserved across multiple renders."""
        style = FrameStyle(scrollable=True)
        frame = Frame(width=20, height=8, style=style)
        content_lines = [f"Line {i}" for i in range(1, 101)]
        frame.set_content("\n".join(content_lines))

        # Scroll to a position
        frame.scroll_manager.scroll_to(25)
        render1 = frame.render()

        # Render again without changing scroll position
        render2 = frame.render()

        # Scroll position should be same
        assert frame.scroll_manager.state.scroll_position == 25
        # Renders should be identical
        assert render1 == render2

    def test_content_align_with_rounded_border(self):
        """Test content alignment with rounded border style."""
        style = FrameStyle(
            border=BorderStyle.ROUNDED, content_align_h="center", content_align_v="top"
        )
        frame = Frame(width=20, height=8, style=style)
        frame.set_content("Test")
        result = frame.render()

        lines = result.split("\n")
        assert "╭" in lines[0]
        assert "╰" in lines[-1]
        # Content should be at top and centered
        assert "Test" in lines[1]


class TestFrameTextOverflow:
    """Tests for Frame text overflow_x functionality."""

    def test_overflow_clip_default(self):
        """Test that clip is the default overflow mode."""
        frame = Frame(width=20, height=5)
        assert frame.style.overflow_x == "clip"

    def test_overflow_clip_truncates_long_text(self):
        """Test that clip mode truncates text exceeding width."""
        style = FrameStyle(overflow_x="clip")
        frame = Frame(width=20, height=5, style=style)
        frame.set_content("This is a very long line that will be clipped")
        result = frame.render()

        lines = result.split("\n")
        from wijjit.terminal.ansi import visible_length

        # Content line should not exceed frame width
        for line in lines:
            assert visible_length(line) <= 20

    def test_overflow_visible_extends_beyond_border(self):
        """Test that visible mode allows text to extend beyond borders."""
        style = FrameStyle(overflow_x="visible")
        frame = Frame(width=20, height=5, style=style)
        frame.set_content("This is a very long line that will overflow")
        result = frame.render()

        lines = result.split("\n")
        from wijjit.terminal.ansi import visible_length

        # Some content lines may exceed frame width
        content_lines = lines[1:-1]  # Exclude top and bottom borders
        has_overflow = any(visible_length(line) > 20 for line in content_lines)
        assert has_overflow

    def test_overflow_wrap_simple(self):
        """Test basic text wrapping."""
        style = FrameStyle(overflow_x="wrap")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("This is a line that should wrap to multiple lines")
        result = frame.render()

        # Content should be split across multiple lines
        assert len(frame.content) > 1
        # Each line should fit within frame width
        from wijjit.terminal.ansi import visible_length

        padding_left, padding_right = frame.style.padding[3], frame.style.padding[1]
        inner_width = frame.width - 2 - padding_left - padding_right
        for line in frame.content:
            assert visible_length(line) <= inner_width

    def test_overflow_wrap_with_ansi_codes(self):
        """Test wrapping preserves ANSI codes."""
        from wijjit.terminal.ansi import ANSIColor

        style = FrameStyle(overflow_x="wrap")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content(
            f"{ANSIColor.RED}This is red text that will wrap{ANSIColor.RESET}"
        )
        result = frame.render()

        # ANSI codes should be preserved
        assert ANSIColor.RED in result
        assert ANSIColor.RESET in result

    def test_overflow_wrap_word_boundaries(self):
        """Test that wrapping respects word boundaries."""
        style = FrameStyle(overflow_x="wrap")
        frame = Frame(width=20, height=10, style=style)
        frame.set_content("Hello world this is a test")
        result = frame.render()

        # Should wrap at spaces, not mid-word
        # The content array should have multiple lines
        assert len(frame.content) > 1

    def test_overflow_wrap_with_padding(self):
        """Test wrapping accounts for padding."""
        style = FrameStyle(overflow_x="wrap", padding=(1, 2, 1, 3))
        frame = Frame(width=25, height=10, style=style)
        frame.set_content("This is a long line that should wrap correctly with padding")

        # Calculate expected inner width
        padding_left, padding_right = 3, 2
        inner_width = 25 - 2 - padding_left - padding_right  # 18 chars
        from wijjit.terminal.ansi import visible_length

        # All content lines should fit within inner width
        for line in frame.content:
            assert visible_length(line) <= inner_width

    def test_overflow_wrap_with_scrolling(self):
        """Test wrapping works with scrollable frames."""
        style = FrameStyle(overflow_x="wrap", scrollable=True, show_scrollbar=True)
        frame = Frame(width=20, height=8, style=style)
        # Create enough content to need scrolling
        long_text = "This is line one that wraps. " * 10
        frame.set_content(long_text)

        # Should have scroll manager
        assert frame.scroll_manager is not None
        # Content should be wrapped
        assert len(frame.content) > 1

    def test_overflow_wrap_empty_content(self):
        """Test wrapping with empty content."""
        style = FrameStyle(overflow_x="wrap")
        frame = Frame(width=20, height=5, style=style)
        frame.set_content("")

        assert frame.content == []
        result = frame.render()
        assert len(result.split("\n")) == 5

    def test_overflow_wrap_very_narrow_frame(self):
        """Test wrapping in very narrow frame."""
        style = FrameStyle(overflow_x="wrap", padding=(0, 0, 0, 0))
        frame = Frame(width=8, height=10, style=style)
        frame.set_content("Supercalifragilisticexpialidocious")

        # Should force hard breaks for long words
        from wijjit.terminal.ansi import visible_length

        inner_width = 8 - 2  # Just borders, no padding
        for line in frame.content:
            assert visible_length(line) <= inner_width

    def test_overflow_modes_with_alignment(self):
        """Test that alignment works with different overflow modes."""
        # Clip mode with center alignment
        style_clip = FrameStyle(overflow_x="clip", content_align_h="center")
        frame_clip = Frame(width=20, height=5, style=style_clip)
        frame_clip.set_content("Short")
        result_clip = frame_clip.render()
        assert "Short" in result_clip

        # Wrap mode with left alignment
        style_wrap = FrameStyle(overflow_x="wrap", content_align_h="left")
        frame_wrap = Frame(width=20, height=8, style=style_wrap)
        frame_wrap.set_content("This will wrap to multiple lines")
        result_wrap = frame_wrap.render()
        assert len(frame_wrap.content) > 1

    def test_overflow_clip_with_multiline_content(self):
        """Test clip mode with content containing newlines."""
        style = FrameStyle(overflow_x="clip")
        frame = Frame(width=15, height=10, style=style)
        frame.set_content("Line 1 is long\nLine 2\nLine 3 is also long")
        result = frame.render()

        from wijjit.terminal.ansi import visible_length

        lines = result.split("\n")
        for line in lines:
            assert visible_length(line) <= 15

    def test_overflow_wrap_with_multiline_content(self):
        """Test wrap mode with content containing newlines."""
        style = FrameStyle(overflow_x="wrap")
        frame = Frame(width=15, height=15, style=style)
        frame.set_content("Line 1 is long\nLine 2\nLine 3 is also long")

        # Each original line should be wrapped independently
        # Resulting in more than 3 lines total
        assert len(frame.content) > 3

    def test_overflow_visible_no_clipping(self):
        """Test that visible mode doesn't clip at all."""
        style = FrameStyle(overflow_x="visible")
        frame = Frame(width=15, height=5, style=style)
        long_line = "A" * 50
        frame.set_content(long_line)
        result = frame.render()

        # The long line should appear in the output, not clipped
        assert "A" * 20 in result  # At least 20 A's should be present

    def test_overflow_wrap_single_long_word(self):
        """Test wrapping when content is a single very long word."""
        style = FrameStyle(overflow_x="wrap")
        frame = Frame(width=12, height=10, style=style)
        frame.set_content("Pneumonoultramicroscopicsilicovolcanoconiosis")

        # Should break mid-word
        from wijjit.terminal.ansi import visible_length

        inner_width = 12 - 2 - 2  # borders + default padding
        for line in frame.content:
            assert visible_length(line) <= inner_width

    def test_overflow_modes_render_correctly(self):
        """Test that all overflow modes render without errors."""
        for mode in ["clip", "visible", "wrap"]:
            style = FrameStyle(overflow_x=mode)
            frame = Frame(width=20, height=8, style=style)
            frame.set_content("This is test content that may be long")
            result = frame.render()
            # Should render without exceptions
            assert isinstance(result, str)
            assert len(result) > 0
