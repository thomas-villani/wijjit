"""Tests for PaintContext class.

This module tests the PaintContext class which provides the rendering
environment for cell-based element rendering.
"""


from wijjit.layout.bounds import Bounds
from wijjit.rendering.paint_context import PaintContext
from wijjit.styling.resolver import StyleResolver
from wijjit.styling.style import Style
from wijjit.styling.theme import DefaultTheme
from wijjit.terminal.screen_buffer import ScreenBuffer


class TestPaintContext:
    """Tests for PaintContext class."""

    def test_init(self):
        """Test PaintContext initialization.

        Verifies that PaintContext correctly stores buffer, style resolver,
        and bounds references.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=20, height=5)

        ctx = PaintContext(buffer, resolver, bounds)

        assert ctx.buffer is buffer
        assert ctx.style_resolver is resolver
        assert ctx.bounds == bounds

    def test_write_text(self):
        """Test writing plain text to buffer.

        Verifies that text is correctly written to the buffer at the
        specified position with proper styling.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=10, y=5, width=20, height=5)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style(fg_color=(255, 0, 0), bold=True)
        ctx.write_text(0, 0, "Hello", style)

        # Check that cells were written correctly
        for i, char in enumerate("Hello"):
            cell = buffer.get_cell(10 + i, 5)
            assert cell is not None
            assert cell.char == char
            assert cell.fg_color == (255, 0, 0)
            assert cell.bold is True

    def test_write_text_with_clipping(self):
        """Test text writing with boundary clipping.

        Verifies that text extending beyond element bounds is properly
        clipped when clip=True.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=5, height=1)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style()
        ctx.write_text(0, 0, "HelloWorld", style, clip=True)

        # Should only write "Hello" (5 chars)
        assert buffer.get_cell(0, 0).char == "H"
        assert buffer.get_cell(4, 0).char == "o"
        # 6th character should not be written (clipped)
        assert buffer.get_cell(5, 0).char == " "

    def test_write_text_without_clipping(self):
        """Test text writing without boundary clipping.

        Verifies that text can extend beyond element bounds when
        clip=False.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=5, height=1)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style()
        ctx.write_text(0, 0, "HelloWorld", style, clip=False)

        # Should write full text
        assert buffer.get_cell(0, 0).char == "H"
        assert buffer.get_cell(9, 0).char == "d"

    def test_fill_rect(self):
        """Test filling a rectangular region.

        Verifies that a rectangle is filled with the specified character
        and style.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=10, y=5, width=20, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style(bg_color=(0, 0, 255))
        ctx.fill_rect(0, 0, 5, 3, "#", style)

        # Check filled region
        for y in range(3):
            for x in range(5):
                cell = buffer.get_cell(10 + x, 5 + y)
                assert cell is not None
                assert cell.char == "#"
                assert cell.bg_color == (0, 0, 255)

        # Check that outside region is not affected
        cell = buffer.get_cell(15, 5)
        assert cell.char == " "

    def test_fill_rect_clipping(self):
        """Test rectangle filling with bounds clipping.

        Verifies that fill_rect properly clips to element bounds.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=5, height=5)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style()
        # Try to fill larger than bounds
        ctx.fill_rect(0, 0, 10, 10, "X", style)

        # Should only fill within bounds (5x5)
        assert buffer.get_cell(4, 4).char == "X"
        assert buffer.get_cell(5, 5).char == " "  # Outside bounds

    def test_draw_border(self):
        """Test drawing a border.

        Verifies that borders are correctly drawn with box-drawing
        characters.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=5, y=5, width=10, height=5)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style()
        ctx.draw_border(0, 0, 10, 5, style)

        # Check corners
        assert buffer.get_cell(5, 5).char == "\u250c"  # Top-left
        assert buffer.get_cell(14, 5).char == "\u2510"  # Top-right
        assert buffer.get_cell(5, 9).char == "\u2514"  # Bottom-left
        assert buffer.get_cell(14, 9).char == "\u2518"  # Bottom-right

        # Check edges
        assert buffer.get_cell(6, 5).char == "\u2500"  # Top horizontal
        assert buffer.get_cell(5, 6).char == "\u2502"  # Left vertical

    def test_draw_border_custom_chars(self):
        """Test drawing border with custom characters.

        Verifies that custom border characters can be used.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=10, height=5)
        ctx = PaintContext(buffer, resolver, bounds)

        custom_chars = {
            "tl": "+",
            "tr": "+",
            "bl": "+",
            "br": "+",
            "h": "-",
            "v": "|",
        }

        style = Style()
        ctx.draw_border(0, 0, 10, 5, style, custom_chars)

        # Check custom corners
        assert buffer.get_cell(0, 0).char == "+"
        assert buffer.get_cell(9, 0).char == "+"
        assert buffer.get_cell(0, 4).char == "+"
        assert buffer.get_cell(9, 4).char == "+"

        # Check custom edges
        assert buffer.get_cell(1, 0).char == "-"
        assert buffer.get_cell(0, 1).char == "|"

    def test_clear(self):
        """Test clearing element bounds.

        Verifies that clear() fills the bounds with spaces.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=5, height=3)
        ctx = PaintContext(buffer, resolver, bounds)

        # Fill with something first
        style = Style()
        ctx.fill_rect(0, 0, 5, 3, "X", style)

        # Clear it
        ctx.clear()

        # Check that it's cleared
        for y in range(3):
            for x in range(5):
                cell = buffer.get_cell(x, y)
                assert cell.char == " "

    def test_clear_with_background(self):
        """Test clearing with background color.

        Verifies that clear() can apply a background color.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=5, height=3)
        ctx = PaintContext(buffer, resolver, bounds)

        bg_style = Style(bg_color=(40, 40, 40))
        ctx.clear(bg_style)

        # Check that background was applied
        cell = buffer.get_cell(0, 0)
        assert cell.char == " "
        assert cell.bg_color == (40, 40, 40)

    def test_sub_context(self):
        """Test creating sub-context with relative bounds.

        Verifies that sub_context creates a new context with correctly
        adjusted bounds.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=10, y=10, width=30, height=20)
        ctx = PaintContext(buffer, resolver, bounds)

        # Create sub-context
        sub_ctx = ctx.sub_context(5, 5, 10, 8)

        # Check that bounds are relative to parent
        assert sub_ctx.bounds.x == 15  # 10 + 5
        assert sub_ctx.bounds.y == 15  # 10 + 5
        assert sub_ctx.bounds.width == 10
        assert sub_ctx.bounds.height == 8

        # Check that buffer and resolver are shared
        assert sub_ctx.buffer is buffer
        assert sub_ctx.style_resolver is resolver

    def test_write_text_wrapped(self):
        """Test writing wrapped text.

        Verifies that text is properly wrapped to fit within max_width.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=20, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style()
        text = "This is a long line that should wrap"
        lines_written = ctx.write_text_wrapped(0, 0, text, style, max_width=10)

        # Should wrap to multiple lines
        assert lines_written > 1

        # Check that first line has content
        assert buffer.get_cell(0, 0).char == "T"

        # Check that second line has content
        assert buffer.get_cell(0, 1).char != " "

    def test_coordinate_translation(self):
        """Test that coordinates are properly translated.

        Verifies that relative coordinates within the context are
        correctly translated to absolute buffer coordinates.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=20, y=10, width=30, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        style = Style()
        ctx.write_text(5, 3, "Test", style)

        # Check absolute position in buffer
        # Relative (5, 3) should be absolute (25, 13)
        cell = buffer.get_cell(25, 13)
        assert cell is not None
        assert cell.char == "T"

    def test_style_application(self):
        """Test that styles are correctly applied to cells.

        Verifies that all style attributes are properly transferred
        to cell attributes.
        """
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=10, height=5)
        ctx = PaintContext(buffer, resolver, bounds)

        # Create style with multiple attributes
        style = Style(
            fg_color=(255, 128, 0),
            bg_color=(0, 0, 64),
            bold=True,
            italic=True,
            underline=True,
        )

        ctx.write_text(0, 0, "X", style)

        cell = buffer.get_cell(0, 0)
        assert cell.fg_color == (255, 128, 0)
        assert cell.bg_color == (0, 0, 64)
        assert cell.bold is True
        assert cell.italic is True
        assert cell.underline is True
