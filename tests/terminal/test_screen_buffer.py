"""Tests for ScreenBuffer and DiffRenderer classes."""

from wijjit.terminal.ansi import strip_ansi
from wijjit.terminal.cell import CONTINUATION_CHAR, Cell
from wijjit.terminal.screen_buffer import DiffRenderer, ScreenBuffer


class TestScreenBuffer:
    """Tests for the ScreenBuffer class."""

    def test_create_buffer(self):
        """Test creating a screen buffer.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies buffer creation with correct dimensions.
        """
        buffer = ScreenBuffer(80, 24)
        assert buffer.width == 80
        assert buffer.height == 24
        assert len(buffer.cells) == 24
        assert len(buffer.cells[0]) == 80

    def test_initial_cells_are_empty(self):
        """Test that initial cells contain spaces.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies all cells are initialized to space characters.
        """
        buffer = ScreenBuffer(10, 5)
        for row in buffer.cells:
            for cell in row:
                assert cell.char == " "
                assert cell.fg_color is None
                assert cell.bg_color is None

    def test_reset_blanks_without_marking_dirty(self):
        """``reset()`` reproduces a fresh buffer: all blank, no dirty regions.

        Unlike ``clear()`` (which marks all dirty), ``reset()`` is used to reuse
        a pooled buffer for a full repaint without the differ treating every
        cell as changed.
        """
        buffer = ScreenBuffer(8, 4)
        blank = buffer.cells[0][0]
        buffer.set_cell(2, 1, Cell("Q", bold=True))
        assert buffer.dirty_regions
        buffer.reset()
        assert not buffer.dirty_regions
        assert all(cell is blank for row in buffer.cells for cell in row)

    def test_copy_from_shares_references_and_clears_dirty(self):
        """``copy_from`` makes each cell reference the source's, dirty cleared."""
        src = ScreenBuffer(6, 3)
        src.set_cell(1, 1, Cell("A", fg_color=(1, 2, 3)))
        dst = ScreenBuffer(6, 3)
        dst.set_cell(4, 2, Cell("Z"))  # pre-existing content + dirty
        dst.copy_from(src)
        assert not dst.dirty_regions
        assert all(
            dst.cells[y][x] is src.cells[y][x] for y in range(3) for x in range(6)
        )

    def test_damage_tracking_dirties_only_changed_cells(self):
        """With a copied baseline, damage mode dirties only real changes.

        This is the core of the incremental path: start a buffer from the
        previous frame, and a bulk fill that rewrites identical content marks
        nothing dirty, while a genuine change marks exactly its cell.
        """
        prev = ScreenBuffer(10, 3)
        prev.fill_rect(0, 0, 10, 3, Cell("."))
        cur = ScreenBuffer(10, 3)
        cur.copy_from(prev)
        cur.start_tracking(damage=True)
        # Re-fill with identical content: no damage.
        cur.fill_rect(0, 0, 10, 3, Cell("."))
        assert not cur.dirty_regions
        # One genuine change: exactly that cell is dirty.
        cur.set_cell(4, 1, Cell("X"))
        cov = cur.end_tracking()
        assert (4, 1, 1, 1) in cur.dirty_regions
        # Coverage recorded every touched cell (the fill + the set).
        assert (4, 1) in cov and (0, 0) in cov and len(cov) == 30

    def test_fast_path_unchanged_when_not_tracking(self):
        """Bulk writes keep their unconditional behavior with tracking off.

        A ``fill_rect`` over identical content still marks the whole region
        dirty when not in damage mode - the standard full-repaint path is
        byte-for-byte unchanged.
        """
        buffer = ScreenBuffer(10, 2)
        buffer.fill_rect(0, 0, 10, 2, Cell("."))
        buffer.dirty_regions.clear()
        # Not tracking, not damage mode: re-fill marks the region dirty anyway.
        buffer.fill_rect(0, 0, 10, 2, Cell("."))
        assert buffer.dirty_regions

    def test_empty_cells_share_one_blank_instance(self):
        """Empty positions reference a single shared blank cell.

        Notes
        -----
        Ratchet for the review-2.5 paint optimization: a fresh buffer must fill
        empty positions with references to one shared ``Cell`` rather than
        allocating a distinct ``Cell(" ")`` per position (which was the dominant
        per-frame cost). Painting one position must not disturb any other, since
        the pipeline replaces cell slots and never mutates cells in place.
        """
        buffer = ScreenBuffer(10, 5)
        blank = buffer.cells[0][0]
        # Every empty position is the same object.
        assert all(cell is blank for row in buffer.cells for cell in row)
        # Buffers built independently share the same blank (module-level).
        assert ScreenBuffer(3, 3).cells[0][0] is blank
        # Painting one position leaves every other position untouched.
        buffer.set_cell(4, 2, Cell("A", fg_color=(255, 0, 0)))
        assert buffer.cells[2][4].char == "A"
        assert all(
            cell is blank
            for y, row in enumerate(buffer.cells)
            for x, cell in enumerate(row)
            if (x, y) != (4, 2)
        )

    def test_clear_refills_with_shared_blank(self):
        """``clear()`` refills every position with the shared blank.

        Notes
        -----
        ``clear()`` fills with the same shared blank as construction (no
        per-cell allocation) and marks the whole buffer dirty for a full redraw.
        """
        buffer = ScreenBuffer(6, 4)
        blank = buffer.cells[0][0]
        buffer.set_cell(1, 1, Cell("Z", bold=True))
        buffer.clear()
        assert all(cell is blank for row in buffer.cells for cell in row)
        # A cleared buffer is marked fully dirty (full redraw on next paint).
        assert buffer.dirty_regions

    def test_set_cell(self):
        """Test setting a cell.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies cell can be set and retrieved.
        """
        buffer = ScreenBuffer(10, 5)
        test_cell = Cell("A", fg_color=(255, 0, 0))
        buffer.set_cell(3, 2, test_cell)

        retrieved = buffer.get_cell(3, 2)
        assert retrieved == test_cell
        assert retrieved.char == "A"
        assert retrieved.fg_color == (255, 0, 0)

    def test_set_cell_marks_dirty(self):
        """Test that setting a cell marks it dirty.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies dirty region tracking when cells change.
        """
        buffer = ScreenBuffer(10, 5)
        buffer.clear_dirty()  # Clear any initial dirty regions

        test_cell = Cell("A")
        buffer.set_cell(5, 3, test_cell)

        dirty_regions = buffer.get_dirty_regions()
        assert (5, 3, 1, 1) in dirty_regions

    def test_set_cell_same_content_not_dirty(self):
        """Test that setting identical cell doesn't mark dirty.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies optimization: no dirty marking for unchanged cells.
        """
        buffer = ScreenBuffer(10, 5)
        buffer.clear_dirty()

        # Set same cell twice
        test_cell = Cell("A", fg_color=(255, 0, 0))
        buffer.set_cell(2, 1, test_cell)
        buffer.clear_dirty()

        buffer.set_cell(2, 1, test_cell)  # Same cell again
        dirty_regions = buffer.get_dirty_regions()
        assert len(dirty_regions) == 0  # Should not be dirty

    def test_get_cell_out_of_bounds(self):
        """Test getting cell outside buffer bounds.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies bounds checking returns None for out-of-bounds access.
        """
        buffer = ScreenBuffer(10, 5)
        assert buffer.get_cell(-1, 0) is None
        assert buffer.get_cell(0, -1) is None
        assert buffer.get_cell(10, 0) is None  # Width is 10, so max index is 9
        assert buffer.get_cell(0, 5) is None  # Height is 5, so max index is 4

    def test_set_cell_out_of_bounds(self):
        """Test setting cell outside buffer bounds.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies bounds checking silently ignores out-of-bounds writes.
        """
        buffer = ScreenBuffer(10, 5)
        test_cell = Cell("X")

        # Should not raise exceptions
        buffer.set_cell(-1, 0, test_cell)
        buffer.set_cell(0, -1, test_cell)
        buffer.set_cell(10, 0, test_cell)
        buffer.set_cell(0, 5, test_cell)

    def test_mark_dirty(self):
        """Test marking a region as dirty.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies explicit dirty region marking.
        """
        buffer = ScreenBuffer(20, 10)
        buffer.clear_dirty()

        buffer.mark_dirty(5, 3, 10, 2)
        dirty_regions = buffer.get_dirty_regions()
        assert (5, 3, 10, 2) in dirty_regions

    def test_mark_all_dirty(self):
        """Test marking entire buffer as dirty.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies full buffer dirty marking.
        """
        buffer = ScreenBuffer(20, 10)
        buffer.clear_dirty()

        buffer.mark_all_dirty()
        dirty_regions = buffer.get_dirty_regions()
        assert (0, 0, 20, 10) in dirty_regions

    def test_clear_dirty(self):
        """Test clearing dirty regions.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies dirty regions can be cleared.
        """
        buffer = ScreenBuffer(10, 5)
        buffer.mark_dirty(1, 1, 5, 2)
        assert len(buffer.get_dirty_regions()) > 0

        buffer.clear_dirty()
        assert len(buffer.get_dirty_regions()) == 0

    def test_clear(self):
        """Test clearing buffer contents.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies buffer can be cleared to spaces.
        """
        buffer = ScreenBuffer(10, 5)

        # Set some cells
        buffer.set_cell(2, 2, Cell("A"))
        buffer.set_cell(3, 3, Cell("B"))

        # Clear buffer
        buffer.clear()

        # All cells should be spaces
        for row in buffer.cells:
            for cell in row:
                assert cell.char == " "

        # Should be marked dirty
        dirty_regions = buffer.get_dirty_regions()
        assert len(dirty_regions) > 0

    def test_resize_larger(self):
        """Test resizing buffer to larger dimensions.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies buffer can grow while preserving content.
        """
        buffer = ScreenBuffer(10, 5)
        buffer.set_cell(2, 2, Cell("A"))
        buffer.set_cell(5, 3, Cell("B"))

        buffer.resize(15, 8)

        assert buffer.width == 15
        assert buffer.height == 8
        # Old content should be preserved
        assert buffer.get_cell(2, 2).char == "A"
        assert buffer.get_cell(5, 3).char == "B"

    def test_resize_smaller(self):
        """Test resizing buffer to smaller dimensions.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies buffer can shrink, keeping what fits.
        """
        buffer = ScreenBuffer(20, 10)
        buffer.set_cell(2, 2, Cell("A"))
        buffer.set_cell(15, 8, Cell("B"))  # Will be lost

        buffer.resize(10, 5)

        assert buffer.width == 10
        assert buffer.height == 5
        # Content that fits should be preserved
        assert buffer.get_cell(2, 2).char == "A"
        # Content that doesn't fit is gone
        assert buffer.get_cell(15, 8) is None  # Out of bounds

    def test_to_string(self):
        """Test converting buffer to string.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies string conversion for debugging.
        """
        buffer = ScreenBuffer(5, 3)
        buffer.set_cell(0, 0, Cell("H"))
        buffer.set_cell(1, 0, Cell("I"))
        buffer.set_cell(0, 1, Cell("X"))

        output = buffer.to_string()
        lines = output.split("\n")

        assert len(lines) == 3
        assert lines[0].startswith("HI")
        assert lines[1].startswith("X")


class TestDiffRenderer:
    """Tests for the DiffRenderer class."""

    def test_first_render_is_full(self):
        """Test that first render outputs full screen.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies full render on first call.
        """
        renderer = DiffRenderer()
        buffer = ScreenBuffer(10, 5)
        buffer.set_cell(0, 0, Cell("A"))

        output = renderer.render_diff(None, buffer)

        assert "\x1b[2J" in output  # Clear screen command
        assert "\x1b[H" in output  # Home cursor command
        assert "A" in output

    def test_full_render_resets_style_before_content(self):
        """A full repaint resets attributes before the first cell so stale
        terminal styling cannot bleed onto the first styled cell."""
        renderer = DiffRenderer()
        buffer = ScreenBuffer(10, 5)
        buffer.set_cell(0, 0, Cell("A", bold=True))

        output = renderer.render_diff(None, buffer)

        home = output.index("\x1b[H")
        first_content = output.index("A")
        reset = output.index("\x1b[0m")
        # The reset must come after home-cursor and before the first content.
        assert home < reset < first_content

    def test_diff_render_unchanged(self):
        """Test diff render with no changes.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies minimal output when nothing changed.
        """
        renderer = DiffRenderer()
        buffer1 = ScreenBuffer(10, 5)
        buffer2 = ScreenBuffer(10, 5)

        # Both buffers empty, should produce minimal output
        output = renderer.render_diff(buffer1, buffer2)
        assert output == ""  # No changes, no output

    def test_diff_render_single_change(self):
        """Test diff render with single cell change.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies minimal output for single cell change.
        """
        renderer = DiffRenderer()
        buffer1 = ScreenBuffer(10, 5)
        buffer2 = ScreenBuffer(10, 5)

        buffer2.set_cell(3, 2, Cell("X"))

        output = renderer.render_diff(buffer1, buffer2)

        # Should contain cursor positioning and the character
        assert "\x1b[" in output  # ANSI escape sequence
        assert "X" in output

    def test_diff_render_multiple_changes(self):
        """Test diff render with multiple changes.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies output for multiple cell changes.
        """
        renderer = DiffRenderer()
        buffer1 = ScreenBuffer(10, 5)
        buffer2 = ScreenBuffer(10, 5)

        buffer2.set_cell(0, 0, Cell("A"))
        buffer2.set_cell(5, 2, Cell("B"))
        buffer2.set_cell(7, 4, Cell("C"))

        output = renderer.render_diff(buffer1, buffer2)

        # Should contain all changed characters
        assert "A" in output
        assert "B" in output
        assert "C" in output

    def test_resize_triggers_full_render(self):
        """Test that buffer resize triggers full render.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies full redraw on dimension change.
        """
        renderer = DiffRenderer()
        buffer1 = ScreenBuffer(10, 5)
        buffer2 = ScreenBuffer(15, 8)  # Different size

        output = renderer.render_diff(buffer1, buffer2)

        # Should be a full render (has clear screen)
        assert "\x1b[2J" in output

    def test_styled_cell_in_diff(self):
        """Test diff render with styled cells.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies style codes are included in diff output.
        """
        renderer = DiffRenderer()
        buffer1 = ScreenBuffer(10, 5)
        buffer2 = ScreenBuffer(10, 5)

        styled_cell = Cell("R", fg_color=(255, 0, 0), bold=True)
        buffer2.set_cell(2, 1, styled_cell)

        output = renderer.render_diff(buffer1, buffer2)

        # Should contain style codes
        assert "\x1b[" in output
        assert "R" in output

    def test_dirty_regions_optimization(self):
        """Test that dirty regions optimize rendering.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies dirty regions are used for optimization.
        """
        renderer = DiffRenderer()
        buffer1 = ScreenBuffer(80, 24)
        buffer2 = ScreenBuffer(80, 24)

        # Mark only a small region as dirty
        buffer2.mark_dirty(10, 10, 5, 2)
        buffer2.set_cell(11, 11, Cell("X"))

        output = renderer.render_diff(buffer1, buffer2)

        # Should produce output (dirty regions should be scanned)
        # This is a basic test - real optimization would be measured by performance
        assert isinstance(output, str)


class TestDiffRendererStyleGrouping:
    """The diff path groups contiguous same-style runs (review item 2.12).

    ``_render_row_diff`` used to emit ``cell.to_ansi()`` per changed cell, so a
    run of N same-styled cells shipped the SGR prefix and a reset N times. It
    now emits the prefix once per run and one trailing reset, matching what
    ``_render_row_optimized`` (the full-render path) already did.
    """

    def test_same_style_run_emits_one_prefix_and_one_reset(self):
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 1)
        new = ScreenBuffer(20, 1)
        for x in range(10):
            new.set_cell(x, 0, Cell(chr(65 + x), fg_color=(255, 0, 0), bold=True))

        out = renderer.render_diff(old, new)

        assert out == "\x1b[1;1H\x1b[1;38;2;255;0;0mABCDEFGHIJ\x1b[0m"
        # One SGR prefix, one reset - not one of each per cell.
        assert out.count("\x1b[1;38;2;255;0;0m") == 1
        assert out.count("\x1b[0m") == 1

    def test_grouping_beats_per_cell_bytes(self):
        """The grouped run is dramatically smaller than per-cell to_ansi."""
        renderer = DiffRenderer()
        old = ScreenBuffer(40, 1)
        new = ScreenBuffer(40, 1)
        cells = [Cell(chr(65 + x), fg_color=(10, 200, 30)) for x in range(20)]
        for x, cell in enumerate(cells):
            new.set_cell(x, 0, cell)

        out = renderer.render_diff(old, new)
        per_cell = sum(len(c.to_ansi()) for c in cells)  # old lower bound

        assert len(out) < per_cell // 2

    def test_style_carries_across_a_cursor_jump(self):
        """Two same-style runs separated by an unchanged gap keep the style.

        A CUP move does not touch SGR state, so the second run must not re-emit
        the style prefix.
        """
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 1)
        new = ScreenBuffer(20, 1)
        for x in (0, 1, 2, 10, 11, 12):
            new.set_cell(x, 0, Cell("Z", fg_color=(0, 0, 255)))

        out = renderer.render_diff(old, new)

        assert out.count("\x1b[38;2;0;0;255m") == 1  # style emitted once total
        assert out.count("\x1b[0m") == 1  # single trailing reset
        assert "\x1b[1;11H" in out  # cursor jumped to the second run

    def test_style_change_within_run_resets_then_applies(self):
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 1)
        new = ScreenBuffer(20, 1)
        new.set_cell(0, 0, Cell("A", fg_color=(255, 0, 0)))
        new.set_cell(1, 0, Cell("B", fg_color=(0, 255, 0)))

        out = renderer.render_diff(old, new)

        # Red applied, then reset before green (SGR params are additive).
        assert out == "\x1b[1;1H\x1b[38;2;255;0;0mA\x1b[0m\x1b[38;2;0;255;0mB\x1b[0m"

    def test_unstyled_run_emits_no_sgr(self):
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 1)
        new = ScreenBuffer(20, 1)
        for x in range(5):
            new.set_cell(x, 0, Cell(chr(65 + x)))

        out = renderer.render_diff(old, new)

        assert out == "\x1b[1;1HABCDE"
        assert "\x1b[0m" not in out  # nothing to clear, so no reset owed

    def test_style_then_default_clears_once(self):
        """A styled run followed by unstyled cells resets exactly once."""
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 1)
        new = ScreenBuffer(20, 1)
        new.set_cell(0, 0, Cell("A", fg_color=(255, 0, 0)))
        new.set_cell(1, 0, Cell("B", fg_color=(255, 0, 0)))
        new.set_cell(2, 0, Cell("C"))  # back to default
        new.set_cell(3, 0, Cell("D"))

        out = renderer.render_diff(old, new)

        assert out == "\x1b[1;1H\x1b[38;2;255;0;0mAB\x1b[0mCD"

    def test_reset_seeds_clean_between_rows(self):
        """A styled run on one row does not leak style onto the next row.

        Each ``_render_row_diff`` assumes the terminal is clean on entry; a
        preceding styled row must therefore close with a reset.
        """
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 2)
        new = ScreenBuffer(20, 2)
        new.set_cell(0, 0, Cell("A", fg_color=(255, 0, 0)))
        new.set_cell(0, 1, Cell("B"))  # unstyled, next row

        out = renderer.render_diff(old, new)

        # Row 0's red run is closed before row 1's plain 'B'.
        assert "\x1b[38;2;255;0;0mA\x1b[0m" in out
        assert out.rindex("\x1b[0m") < out.index("B")


class TestDiffRendererWideChars:
    """Column-correct diff / full-render emission for wide (2-column) glyphs."""

    def test_diff_wide_glyph_advances_cursor_by_two(self):
        """The cell after a wide glyph needs no extra cursor move.

        A CJK head glyph advances the terminal two columns, so ``current_pos``
        must land on the column after the continuation. The changed cell that
        follows is then emitted with no intervening cursor positioning.
        """
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 1)
        new = ScreenBuffer(20, 1)
        new.set_cell(5, 0, Cell("日"))
        new.set_cell(6, 0, Cell(CONTINUATION_CHAR))
        new.set_cell(7, 0, Cell("X"))

        out = renderer.render_diff(old, new)

        # One cursor move to column 6 (1-indexed), the glyph, then X directly.
        assert out == "\x1b[1;6H日X"

    def test_diff_continuation_change_reemits_head(self):
        """A dirty continuation column re-emits the whole head glyph.

        When only the continuation cell differs (its head is unchanged and was
        therefore not emitted in this pass), the head must be re-emitted so the
        glyph is never left half-drawn.
        """
        renderer = DiffRenderer()
        old = ScreenBuffer(20, 1)
        new = ScreenBuffer(20, 1)
        for buf in (old, new):
            buf.set_cell(5, 0, Cell("日"))
            buf.set_cell(6, 0, Cell(CONTINUATION_CHAR))
        old.clear_dirty()
        new.clear_dirty()
        # Only the continuation column changes -> its head is untouched.
        new.set_cell(6, 0, Cell(CONTINUATION_CHAR, fg_color=(200, 100, 50)))

        out = renderer.render_diff(old, new)

        # The head glyph is re-emitted whole at its own column.
        assert out == "\x1b[1;6H日"

    def test_full_render_row_skips_continuation(self):
        """Full-render of a row with a wide glyph emits it once, no extra char."""
        renderer = DiffRenderer()
        buffer = ScreenBuffer(6, 1)
        buffer.set_cell(0, 0, Cell("日"))
        buffer.set_cell(1, 0, Cell(CONTINUATION_CHAR))
        buffer.set_cell(2, 0, Cell("X"))

        row_out = renderer._render_row_optimized(buffer.cells[0])
        printable = strip_ansi(row_out)

        # Glyph emitted exactly once; the continuation adds no character.
        assert printable.count("日") == 1
        assert printable == "日X   "
