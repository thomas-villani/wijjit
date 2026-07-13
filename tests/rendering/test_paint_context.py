"""Tests for PaintContext class.

This module tests the PaintContext class which provides the rendering
environment for cell-based element rendering.
"""

from wijjit.layout.bounds import Bounds
from wijjit.rendering.paint_context import PaintContext
from wijjit.styling.resolver import StyleResolver
from wijjit.styling.style import Style
from wijjit.styling.theme import DefaultTheme
from wijjit.terminal.cell import Cell, is_continuation
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


class TestWriteTextWideChars:
    """Column-correct wide-character handling in PaintContext.write_text."""

    def _ctx(self, width=20, height=1, x=0, y=0, clip_region=None):
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=x, y=y, width=width, height=height)
        ctx = PaintContext(buffer, resolver, bounds, clip_region=clip_region)
        return ctx, buffer

    def test_cjk_head_and_continuation(self):
        """A CJK glyph writes a head cell plus a styled continuation cell."""
        ctx, buffer = self._ctx()
        style = Style(fg_color=(10, 20, 30), bold=True)

        ctx.write_text(0, 0, "日", style)  # CJK, 2 columns

        head = buffer.get_cell(0, 0)
        cont = buffer.get_cell(1, 0)
        assert head.char == "日"
        assert is_continuation(cont)
        # Style carried on both head and continuation.
        assert head.fg_color == (10, 20, 30) and head.bold is True
        assert cont.fg_color == (10, 20, 30) and cont.bold is True

    def test_budget_consumed_in_columns(self):
        """A width-4 bounds fits exactly two CJK glyphs; a third is dropped."""
        ctx, buffer = self._ctx(width=4)
        style = Style()

        ctx.write_text(0, 0, "日本語", style)  # three CJK glyphs

        assert buffer.get_cell(0, 0).char == "日"
        assert is_continuation(buffer.get_cell(1, 0))
        assert buffer.get_cell(2, 0).char == "本"
        assert is_continuation(buffer.get_cell(3, 0))
        # Third glyph is out of budget -> nothing written at col 4.
        assert buffer.get_cell(4, 0).char == " "

    def test_wide_glyph_one_column_left_writes_space(self):
        """With only one column of budget left, write a styled space."""
        ctx, buffer = self._ctx(width=3)
        style = Style(fg_color=(1, 2, 3))

        # First CJK fills cols 0-1; second glyph has only col 2 of budget left.
        ctx.write_text(0, 0, "日本", style)

        assert buffer.get_cell(0, 0).char == "日"
        assert is_continuation(buffer.get_cell(1, 0))
        # No half glyph: a styled space, not the glyph.
        edge = buffer.get_cell(2, 0)
        assert edge.char == " "
        assert edge.fg_color == (1, 2, 3)

    def test_wide_glyph_straddling_clip_right_edge(self):
        """Only the head column inside the clip region -> styled space there."""
        # Clip region ends at column 2 (covers cols 0,1). Wide glyph at col 1
        # has head inside (col 1) and tail outside (col 2).
        clip = Bounds(x=0, y=0, width=2, height=1)
        ctx, buffer = self._ctx(width=20, clip_region=clip)
        style = Style(fg_color=(9, 9, 9))

        ctx.write_text(0, 0, "A日", style)

        assert buffer.get_cell(0, 0).char == "A"
        edge = buffer.get_cell(1, 0)
        assert edge.char == " "
        assert edge.fg_color == (9, 9, 9)
        # Tail column was outside clip -> untouched.
        assert buffer.get_cell(2, 0).char == " "

    def test_wide_glyph_straddling_clip_left_edge(self):
        """Only the tail column inside the clip region -> styled space there."""
        # Clip region starts at column 1. Wide glyph at col 0 has head outside
        # (col 0) and tail inside (col 1).
        clip = Bounds(x=1, y=0, width=19, height=1)
        ctx, buffer = self._ctx(width=20, clip_region=clip)
        style = Style(fg_color=(7, 7, 7))

        ctx.write_text(0, 0, "日B", style)

        # Head column outside clip -> untouched.
        assert buffer.get_cell(0, 0).char == " "
        edge = buffer.get_cell(1, 0)
        assert edge.char == " "
        assert edge.fg_color == (7, 7, 7)
        assert buffer.get_cell(2, 0).char == "B"

    def test_nfd_accents_cluster_onto_base(self):
        """NFD 'cafe' with combining accent yields 4 cells; last char is composed."""
        import unicodedata

        text = unicodedata.normalize("NFD", "café")  # c a f e + combining
        assert len(text) == 5  # decomposed: combining acute is a separate mark
        ctx, buffer = self._ctx(width=10)

        ctx.write_text(0, 0, text, Style())

        assert buffer.get_cell(0, 0).char == "c"
        assert buffer.get_cell(1, 0).char == "a"
        assert buffer.get_cell(2, 0).char == "f"
        # Base 'e' + combining acute folded into one cell.
        assert buffer.get_cell(3, 0).char == unicodedata.normalize("NFD", "é")
        # No continuation / extra cell.
        assert buffer.get_cell(4, 0).char == " "

    def test_control_char_dropped(self):
        """A control character (tab) is dropped entirely."""
        ctx, buffer = self._ctx(width=10)

        ctx.write_text(0, 0, "a\tb", Style())

        assert buffer.get_cell(0, 0).char == "a"
        # Tab (wcwidth < 0) dropped; 'b' follows immediately.
        assert buffer.get_cell(1, 0).char == "b"
        assert buffer.get_cell(2, 0).char == " "

    def test_clip_false_emits_head_and_continuation(self):
        """The clip=False branch also emits head + continuation for wide glyphs."""
        ctx, buffer = self._ctx(width=2)  # narrow bounds, but clip disabled
        style = Style(fg_color=(5, 5, 5))

        ctx.write_text(0, 0, "A日B", style, clip=False)

        assert buffer.get_cell(0, 0).char == "A"
        assert buffer.get_cell(1, 0).char == "日"
        cont = buffer.get_cell(2, 0)
        assert is_continuation(cont)
        assert cont.fg_color == (5, 5, 5)
        assert buffer.get_cell(3, 0).char == "B"


class TestWriteCell:
    """Clipped, wide-char-aware single-cell writes via write_cell."""

    def _ctx(self, width=20, height=5, x=0, y=0, clip_region=None):
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=x, y=y, width=width, height=height)
        ctx = PaintContext(buffer, resolver, bounds, clip_region=clip_region)
        return ctx, buffer

    def test_narrow_cell_written_and_returns_one(self):
        ctx, buffer = self._ctx()
        consumed = ctx.write_cell(3, 1, Cell("X", fg_color=(1, 2, 3)))
        assert consumed == 1
        assert buffer.get_cell(3, 1).char == "X"
        assert buffer.get_cell(3, 1).fg_color == (1, 2, 3)

    def test_outside_clip_not_written_still_returns_width(self):
        clip = Bounds(x=0, y=0, width=5, height=1)
        ctx, buffer = self._ctx(clip_region=clip)
        consumed = ctx.write_cell(7, 0, Cell("X"))
        assert consumed == 1
        assert buffer.get_cell(7, 0).char == " "

    def test_wide_cell_writes_head_and_continuation(self):
        ctx, buffer = self._ctx()
        consumed = ctx.write_cell(2, 0, Cell("日", bold=True))
        assert consumed == 2
        head = buffer.get_cell(2, 0)
        cont = buffer.get_cell(3, 0)
        assert head.char == "日" and head.bold is True
        assert is_continuation(cont)
        assert cont.bold is True

    def test_wide_cell_head_only_in_clip_writes_space(self):
        """Tail column outside the clip region -> styled space at head."""
        clip = Bounds(x=0, y=0, width=3, height=1)
        ctx, buffer = self._ctx(clip_region=clip)
        consumed = ctx.write_cell(2, 0, Cell("日", fg_color=(9, 9, 9)))
        assert consumed == 2
        edge = buffer.get_cell(2, 0)
        assert edge.char == " "
        assert edge.fg_color == (9, 9, 9)
        assert buffer.get_cell(3, 0).char == " "

    def test_wide_cell_tail_only_in_clip_writes_space(self):
        """Head column outside the clip region -> styled space at tail."""
        clip = Bounds(x=3, y=0, width=5, height=1)
        ctx, buffer = self._ctx(clip_region=clip)
        ctx.write_cell(2, 0, Cell("日", fg_color=(7, 7, 7)))
        assert buffer.get_cell(2, 0).char == " "
        edge = buffer.get_cell(3, 0)
        assert edge.char == " "
        assert edge.fg_color == (7, 7, 7)

    def test_explicit_continuation_cell_written_as_is(self):
        """A caller-placed continuation cell is a plain single-column write."""
        from wijjit.terminal.cell import CONTINUATION_CHAR

        ctx, buffer = self._ctx()
        consumed = ctx.write_cell(4, 0, Cell(CONTINUATION_CHAR, dim=True))
        assert consumed == 1
        cell = buffer.get_cell(4, 0)
        assert is_continuation(cell)
        assert cell.dim is True


class TestWriteCells:
    """Clipped bulk-run writes via write_cells / write_cells_vertical."""

    def _ctx(self, width=20, height=5, x=0, y=0, clip_region=None):
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=x, y=y, width=width, height=height)
        ctx = PaintContext(buffer, resolver, bounds, clip_region=clip_region)
        return ctx, buffer

    def test_full_run_written(self):
        ctx, buffer = self._ctx()
        ctx.write_cells(1, 0, [Cell("a"), Cell("b"), Cell("c")])
        assert buffer.get_cell(1, 0).char == "a"
        assert buffer.get_cell(2, 0).char == "b"
        assert buffer.get_cell(3, 0).char == "c"

    def test_run_sliced_to_clip(self):
        clip = Bounds(x=2, y=0, width=3, height=1)
        ctx, buffer = self._ctx(clip_region=clip)
        ctx.write_cells(0, 0, [Cell(c) for c in "abcdefg"])
        # Only columns 2..4 are inside the clip region.
        assert buffer.get_cell(0, 0).char == " "
        assert buffer.get_cell(1, 0).char == " "
        assert buffer.get_cell(2, 0).char == "c"
        assert buffer.get_cell(3, 0).char == "d"
        assert buffer.get_cell(4, 0).char == "e"
        assert buffer.get_cell(5, 0).char == " "

    def test_row_outside_clip_writes_nothing(self):
        clip = Bounds(x=0, y=0, width=20, height=1)
        ctx, buffer = self._ctx(clip_region=clip)
        ctx.write_cells(0, 2, [Cell("x"), Cell("y")])
        assert buffer.get_cell(0, 2).char == " "

    def test_severed_leading_continuation_becomes_space(self):
        """A run cut so it starts on a continuation cell writes a space there."""
        from wijjit.terminal.cell import CONTINUATION_CHAR

        clip = Bounds(x=1, y=0, width=10, height=1)
        ctx, buffer = self._ctx(clip_region=clip)
        cells = [Cell("日", bold=True), Cell(CONTINUATION_CHAR, bold=True), Cell("b")]
        ctx.write_cells(0, 0, cells)
        # Head at col 0 clipped away; its continuation at col 1 becomes a space.
        assert buffer.get_cell(0, 0).char == " "
        edge = buffer.get_cell(1, 0)
        assert edge.char == " "
        assert edge.bold is True
        assert buffer.get_cell(2, 0).char == "b"
        # Caller's list is not mutated.
        assert cells[1].char == CONTINUATION_CHAR

    def test_severed_trailing_head_becomes_space(self):
        """A run cut after a wide head (continuation outside) writes a space."""
        from wijjit.terminal.cell import CONTINUATION_CHAR

        clip = Bounds(x=0, y=0, width=2, height=1)
        ctx, buffer = self._ctx(clip_region=clip)
        cells = [Cell("a"), Cell("日", dim=True), Cell(CONTINUATION_CHAR, dim=True)]
        ctx.write_cells(0, 0, cells)
        assert buffer.get_cell(0, 0).char == "a"
        edge = buffer.get_cell(1, 0)
        assert edge.char == " "
        assert edge.dim is True
        assert buffer.get_cell(2, 0).char == " "
        assert cells[1].char == "日"

    def test_vertical_run_sliced_to_clip(self):
        clip = Bounds(x=0, y=1, width=20, height=2)
        ctx, buffer = self._ctx(clip_region=clip)
        ctx.write_cells_vertical(0, 0, [Cell(c) for c in "abcd"])
        assert buffer.get_cell(0, 0).char == " "
        assert buffer.get_cell(0, 1).char == "b"
        assert buffer.get_cell(0, 2).char == "c"
        assert buffer.get_cell(0, 3).char == " "

    def test_vertical_column_outside_clip_writes_nothing(self):
        clip = Bounds(x=0, y=0, width=2, height=5)
        ctx, buffer = self._ctx(clip_region=clip)
        ctx.write_cells_vertical(4, 0, [Cell("x"), Cell("y")])
        assert buffer.get_cell(4, 0).char == " "
        assert buffer.get_cell(4, 1).char == " "


class TestCursorAnchor:
    """cursor_anchor returns absolute clipped caret coordinates."""

    def test_inside_clip_returns_absolute(self):
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=10, y=5, width=20, height=3)
        ctx = PaintContext(buffer, resolver, bounds)
        assert ctx.cursor_anchor(2, 1) == (12, 6)

    def test_outside_clip_returns_none(self):
        buffer = ScreenBuffer(80, 24)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=10, y=5, width=20, height=3)
        # Clip covers only the first row of the element.
        clip = Bounds(x=10, y=5, width=20, height=1)
        ctx = PaintContext(buffer, resolver, bounds, clip_region=clip)
        assert ctx.cursor_anchor(2, 1) is None
        assert ctx.cursor_anchor(2, 0) == (12, 5)
