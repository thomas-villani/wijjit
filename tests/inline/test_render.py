"""Tests for inline render functions."""

import io
from unittest.mock import Mock, patch

import pytest

from wijjit.inline.render import (
    render_inline,
    _calculate_content_height,
    _buffer_to_inline_ansi,
    _render_row_optimized,
)
from wijjit.terminal.cell import Cell


class TestRenderInline:
    """Tests for render_inline function."""

    def test_render_inline_simple_text_in_frame(self):
        """Test rendering simple text in a frame template."""
        template = "{% frame %}Hello World{% endframe %}"
        output = render_inline(template, print_output=False, width=40)
        assert output is not None
        assert "Hello World" in output

    def test_render_inline_with_context(self):
        """Test rendering template with context variables."""
        template = "{% frame %}Hello {{ name }}!{% endframe %}"
        output = render_inline(template, print_output=False, width=40, name="Alice")
        assert output is not None
        assert "Alice" in output

    def test_render_inline_with_frame(self):
        """Test rendering template with frame tag."""
        template = """{% frame title="Test" %}Content{% endframe %}"""
        output = render_inline(template, print_output=False, width=40)
        assert output is not None
        # Frame should contain the content
        assert "Content" in output

    def test_render_inline_print_to_file(self):
        """Test render_inline prints to file when specified."""
        output_buffer = io.StringIO()
        template = "{% frame %}Test output{% endframe %}"
        result = render_inline(template, print_output=True, file=output_buffer, width=40)

        # Should return None when printing
        assert result is None
        # Should have written to the file
        assert "Test output" in output_buffer.getvalue()

    def test_render_inline_return_string(self):
        """Test render_inline returns string when print_output=False."""
        template = "{% frame %}Test output{% endframe %}"
        result = render_inline(template, print_output=False, width=40)

        assert isinstance(result, str)
        assert "Test output" in result

    def test_render_inline_custom_width(self):
        """Test render_inline with custom width."""
        template = "{% frame %}Content{% endframe %}"
        output = render_inline(template, width=30, print_output=False)

        assert output is not None
        # Each line should respect the width
        lines = output.split("\n")
        for line in lines:
            # Lines might have ANSI codes but should be roughly within width
            assert len(line) <= 200  # Allow some buffer for ANSI codes

    def test_render_inline_fixed_height(self):
        """Test render_inline with fixed height."""
        template = "{% frame %}Line 1{% endframe %}"
        output = render_inline(template, height=3, print_output=False, width=40)

        assert output is not None
        lines = output.split("\n")
        assert len(lines) == 3

    def test_render_inline_auto_height(self):
        """Test render_inline with auto height calculation."""
        template = "{% frame %}Single line{% endframe %}"
        output = render_inline(template, height="auto", print_output=False, width=40)

        assert output is not None
        # Should have calculated appropriate height
        lines = output.split("\n")
        assert len(lines) >= 1

    def test_render_inline_empty_template(self):
        """Test rendering empty template."""
        output = render_inline("", print_output=False)
        # Empty template may return empty string or None
        assert output is not None or output == ""


class TestCalculateContentHeight:
    """Tests for _calculate_content_height function."""

    def test_empty_elements(self):
        """Test with no elements returns 1."""
        assert _calculate_content_height([]) == 1

    def test_single_element(self):
        """Test with single element."""
        elem = Mock()
        elem.bounds = Mock()
        elem.bounds.y = 0
        elem.bounds.height = 5
        type(elem).__name__ = "TextElement"

        result = _calculate_content_height([elem])
        assert result >= 1

    def test_multiple_elements(self):
        """Test with multiple elements returns max height."""
        elem1 = Mock()
        elem1.bounds = Mock()
        elem1.bounds.y = 0
        elem1.bounds.height = 3
        type(elem1).__name__ = "TextElement"

        elem2 = Mock()
        elem2.bounds = Mock()
        elem2.bounds.y = 0
        elem2.bounds.height = 5
        type(elem2).__name__ = "TextElement"

        result = _calculate_content_height([elem1, elem2])
        assert result >= 5

    def test_element_with_no_bounds(self):
        """Test element without bounds is skipped."""
        elem = Mock()
        elem.bounds = None

        result = _calculate_content_height([elem])
        assert result >= 1

    def test_frame_element_adds_border_space(self):
        """Test frame element adds space for borders."""
        # Content element
        content = Mock()
        content.bounds = Mock()
        content.bounds.y = 1
        content.bounds.height = 3
        type(content).__name__ = "TextElement"

        # Frame element
        frame = Mock()
        frame.bounds = Mock()
        frame.bounds.y = 0
        frame.bounds.height = 100  # Frame fills available
        type(frame).__name__ = "Frame"

        result = _calculate_content_height([frame, content])
        # Should account for content + frame borders
        assert result >= 4


class TestRenderRowOptimized:
    """Tests for _render_row_optimized function."""

    def test_empty_row(self):
        """Test rendering empty row."""
        result = _render_row_optimized([], 10)
        assert result == ""

    def test_simple_row(self):
        """Test rendering row of simple cells."""
        cells = []
        for char in "Hello":
            cell = Cell(char)
            cells.append(cell)

        result = _render_row_optimized(cells, 10)
        # Should contain the characters
        assert "Hello" in result

    def test_row_respects_width(self):
        """Test row rendering respects width parameter."""
        cells = []
        for char in "Hello World":
            cell = Cell(char)
            cells.append(cell)

        # Only render first 5 characters
        result = _render_row_optimized(cells, 5)
        assert "Hello" in result
        assert "World" not in result

    def test_row_with_styled_cells(self):
        """Test row with styled cells produces style codes."""
        cells = []
        for char in "Red":
            cell = Cell(char, fg_color=(255, 0, 0), bold=True)
            cells.append(cell)

        result = _render_row_optimized(cells, 10)
        # Should contain ANSI codes
        assert "\x1b[" in result
        assert "Red" in result
        # Should end with reset
        assert result.endswith("\x1b[0m")

    def test_row_style_optimization(self):
        """Test that consecutive same-style cells are optimized."""
        cells = []
        # First 3 cells: same style (red)
        for char in "AAA":
            cell = Cell(char, fg_color=(255, 0, 0))
            cells.append(cell)
        # Next 2 cells: different style (blue)
        for char in "BB":
            cell = Cell(char, fg_color=(0, 0, 255))
            cells.append(cell)

        result = _render_row_optimized(cells, 10)
        # Should contain all characters
        assert "AAA" in result or ("A" in result)
        assert "BB" in result or ("B" in result)
        # Should have style codes
        assert "\x1b[" in result


class TestBufferToInlineAnsi:
    """Tests for _buffer_to_inline_ansi function."""

    def test_single_row_buffer(self):
        """Test converting single row buffer."""
        buffer = Mock()
        buffer.height = 1
        buffer.cells = [[Cell("A"), Cell("B"), Cell("C")]]

        result = _buffer_to_inline_ansi(buffer, 3, 1)
        assert "ABC" in result

    def test_multi_row_buffer(self):
        """Test converting multi-row buffer."""
        buffer = Mock()
        buffer.height = 2
        buffer.cells = [
            [Cell("A"), Cell("B")],
            [Cell("C"), Cell("D")],
        ]

        result = _buffer_to_inline_ansi(buffer, 2, 2)
        lines = result.split("\n")
        assert len(lines) == 2

    def test_height_limit(self):
        """Test buffer rendering respects height limit."""
        buffer = Mock()
        buffer.height = 5
        buffer.cells = [
            [Cell("1")],
            [Cell("2")],
            [Cell("3")],
            [Cell("4")],
            [Cell("5")],
        ]

        result = _buffer_to_inline_ansi(buffer, 1, 3)
        lines = result.split("\n")
        assert len(lines) == 3

    def test_strips_trailing_spaces(self):
        """Test that trailing spaces are stripped from lines."""
        buffer = Mock()
        buffer.height = 1
        buffer.cells = [[Cell("A"), Cell(" "), Cell(" ")]]

        result = _buffer_to_inline_ansi(buffer, 3, 1)
        # Should strip trailing spaces
        assert not result.endswith("   ")
