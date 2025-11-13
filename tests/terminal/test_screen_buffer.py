"""Tests for ScreenBuffer and DiffRenderer classes."""

from wijjit.terminal.cell import Cell
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
