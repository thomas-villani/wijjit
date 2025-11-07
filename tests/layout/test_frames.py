"""Tests for frame rendering."""

import pytest
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

        lines = result.split("\n")
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
