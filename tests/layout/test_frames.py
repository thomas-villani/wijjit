"""Tests for frame rendering."""

from wijjit.layout.frames import Frame, FrameStyle, BorderStyle


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
            border=BorderStyle.SINGLE, content_align_h="center", content_align_v="middle"
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
