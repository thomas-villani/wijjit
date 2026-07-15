"""Screen buffer and diff rendering for efficient terminal updates.

This module provides the ScreenBuffer class for managing 2D cell arrays and
the DiffRenderer class for generating minimal ANSI output by comparing buffers.
"""

from wijjit.terminal.ansi import display_width
from wijjit.terminal.cell import Cell, is_continuation

# A single shared blank cell used to fill empty buffer positions. Cells are
# treated as immutable throughout the pipeline - painting *replaces* a slot
# (``row[x] = new_cell``), never mutates the cell in place - so every empty
# position can safely reference this one object instead of allocating a fresh
# ``Cell(" ")`` per position. That turned a width*height Cell allocation on
# every frame into a handful of list builds (review 2.5: per-frame paint cost).
# The one place that mutates cell fields (overlay dimming in
# ``Renderer.composite_overlays``) copies each cell first, and skips cells whose
# colors are None - which a blank cell's are - so the shared instance is never
# reached.
_BLANK_CELL = Cell(" ")

# SGR signature of a fully-unstyled cell. Used by the diff renderer to know
# when the terminal is back in its default state and no trailing reset is owed.
_DEFAULT_STYLE: tuple[object, ...] = (None, None, False, False, False, False, False)


def _style_sig(cell: Cell) -> tuple[object, ...]:
    """Return a cell's style signature (the same fields ``_render_row_optimized``
    groups on): fg, bg, bold, italic, underline, reverse, dim.
    """
    return (
        cell.fg_color,
        cell.bg_color,
        cell.bold,
        cell.italic,
        cell.underline,
        cell.reverse,
        cell.dim,
    )


def _cell_width(cell: Cell) -> int:
    """Return the terminal column width of ``cell``.

    Parameters
    ----------
    cell : Cell
        Cell to measure.

    Returns
    -------
    int
        ``0`` for a continuation cell (the trailing column of a wide glyph is
        already covered by its head), otherwise the display width of the cell's
        character (at least 1). ``wcswidth`` returning ``-1`` for an unprintable
        character is treated as width 1.
    """
    if is_continuation(cell):
        return 0
    width: int = display_width(cell.char)
    return max(width, 1)


class ScreenBuffer:
    """2D buffer of terminal cells with dirty region tracking.

    This class manages a 2D array of Cell objects representing the terminal
    screen. It tracks which regions have changed (dirty regions) to enable
    efficient diff rendering.

    Parameters
    ----------
    width : int
        Buffer width in columns
    height : int
        Buffer height in rows

    Attributes
    ----------
    width : int
        Buffer width
    height : int
        Buffer height
    cells : list of list of Cell
        2D array of cells [row][col]
    dirty_regions : set of tuple
        Set of (x, y, width, height) rectangles that have changed

    Notes
    -----
    **Wide-character model.** A width-2 glyph (most CJK, many emoji) is stored
    as two cells: a *head* cell holding the glyph and a *continuation* cell
    whose ``char`` is the empty string (see
    :func:`wijjit.terminal.cell.is_continuation`) carrying the head's style.
    Zero-width combining marks (e.g. an NFD-decomposed accent) are folded onto
    the base glyph as a single multi-code-point ``char``. The standard text
    path -- :meth:`wijjit.rendering.paint_context.PaintContext.write_text` plus
    the diff and full-render emitters here -- is column-correct: it skips
    continuation cells and advances the diff cursor by each glyph's true column
    width, so wide glyphs no longer overflow borders or desync the cursor.

    Element rendering also goes through this path now: all elements paint via
    the clipped, wide-aware ``PaintContext`` write APIs (``write_text``,
    ``write_cell``, ``write_cells``/``write_cells_vertical``); direct
    ``buffer.set_cell`` loops were migrated out (review items 2.1/2.11) and a
    ratchet test keeps them out. Remaining gap (roadmap):
    :func:`wijjit.rendering.ansi_adapter.ansi_string_to_cells` -- used for
    pre-rendered ANSI content such as Rich-rendered tables with
    ``content_type="ansi"`` -- still maps one code point per cell.

    Examples
    --------
    Create a buffer and write a cell:

    >>> buffer = ScreenBuffer(80, 24)
    >>> buffer.set_cell(0, 0, Cell('A', fg_color=(255, 0, 0)))
    >>> buffer.get_cell(0, 0).char
    'A'

    Track dirty regions:

    >>> buffer.mark_dirty(0, 0, 10, 1)
    >>> dirty = buffer.get_dirty_regions()
    >>> (0, 0, 10, 1) in dirty
    True
    """

    #: The shared blank cell (see module-level _BLANK_CELL). Exposed on the
    #: instance so callers (e.g. the incremental renderer blanking a vacated
    #: cell) can reference it without importing the module constant.
    blank_cell: Cell = _BLANK_CELL

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        # Fill with references to the one shared blank cell (see _BLANK_CELL).
        # ``[_BLANK_CELL] * width`` is a row of references, not copies; each row
        # is its own list so a paint into one row never touches another.
        self.cells: list[list[Cell]] = [[_BLANK_CELL] * width for _ in range(height)]
        self.dirty_regions: set[tuple[int, int, int, int]] = set()

        # Damage-tracking support for incremental rendering (review 2.5).
        # _coverage: when not None, every write path records the cell it touches
        # as a packed ``y * width + x`` int, so the renderer can blank cells that
        # were painted last frame but not this one (vacated content). The packed
        # int avoids a per-cell tuple allocation on the paint hot path (this set
        # takes an add for every glyph written); the renderer unpacks with
        # ``x = p % width; y = p // width``. _damage_mode: when True, the bulk
        # write paths (fill_rect, set_cells_*) change-detect per cell like
        # set_cell does - only writing and dirtying cells that actually differ -
        # instead of unconditionally overwriting a whole region. Both are off by
        # default so the standard full-repaint path is byte-for-byte unchanged.
        self._coverage: set[int] | None = None
        self._damage_mode: bool = False

    def start_tracking(self, damage: bool) -> None:
        """Begin recording paint coverage for one frame.

        Parameters
        ----------
        damage : bool
            When True, bulk writes also change-detect per cell (used on the
            incremental paint path where the buffer starts as a copy of the
            previous frame). When False, coverage is recorded but bulk writes
            keep their unconditional fast path (used to capture coverage on the
            full-repaint path without altering its output).
        """
        self._coverage = set()
        self._damage_mode = damage

    def end_tracking(self) -> set[int]:
        """Stop recording coverage and return the cells painted this frame.

        Returns
        -------
        set of int
            The positions touched by any write since ``start_tracking``, each
            packed as ``y * width + x``. Unpack with ``x = p % width`` and
            ``y = p // width``.
        """
        cov = self._coverage if self._coverage is not None else set()
        self._coverage = None
        self._damage_mode = False
        return cov

    def reset(self) -> None:
        """Reset to a freshly-constructed state: all blank, no dirty regions.

        Unlike :meth:`clear`, this does **not** mark the buffer dirty - it
        reproduces exactly what ``__init__`` yields, so a pooled buffer can be
        reused for a full repaint without the differ treating every cell as
        changed.
        """
        blank = _BLANK_CELL
        for row in self.cells:
            row[:] = [blank] * self.width
        self.dirty_regions.clear()
        if self._coverage is not None:
            self._coverage.clear()

    def copy_from(self, other: "ScreenBuffer") -> None:
        """Make this buffer's cells reference ``other``'s, row by row.

        A shallow per-row copy: each row becomes a fresh list of references to
        ``other``'s cell objects (cells are immutable and replaced wholesale, so
        sharing references is safe). Used by the incremental paint path to start
        a frame from the previous frame's content, so that ``set_cell``'s
        change-detection then dirties only the cells that actually change.
        Dirty regions and coverage are reset.
        """
        for y in range(self.height):
            self.cells[y][:] = other.cells[y]
        self.dirty_regions.clear()
        if self._coverage is not None:
            self._coverage.clear()

    def set_cell(self, x: int, y: int, cell: Cell) -> None:
        """Set a cell at the specified position and mark it dirty.

        Parameters
        ----------
        x : int
            Column position (0-indexed)
        y : int
            Row position (0-indexed)
        cell : Cell
            Cell to set

        Notes
        -----
        Bounds checking is performed. Out-of-bounds coordinates are silently
        ignored. The cell region is automatically marked dirty if the cell
        content differs from the current cell.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return

        if self._coverage is not None:
            self._coverage.add(y * self.width + x)

        # Only mark dirty if cell actually changed
        if self.cells[y][x] != cell:
            self.cells[y][x] = cell
            self.mark_dirty(x, y, 1, 1)

    def set_cells_horizontal(self, x: int, y: int, cells: list[Cell]) -> None:
        """Set multiple cells horizontally in a single operation.

        This is optimized for performance, avoiding individual cell comparisons
        and marking the entire region dirty once instead of cell-by-cell.

        Parameters
        ----------
        x : int
            Starting column position (0-indexed)
        y : int
            Row position (0-indexed)
        cells : list of Cell
            Cells to set horizontally

        Notes
        -----
        Out-of-bounds cells are clipped. The entire region is marked dirty
        regardless of whether individual cells changed, which is more efficient
        than checking each cell when most cells are expected to change.
        """
        if not (0 <= y < self.height) or not cells:
            return

        # Clip to screen bounds
        start_x = max(0, x)
        end_x = min(x + len(cells), self.width)
        if start_x >= end_x:
            return

        offset = start_x - x
        row = self.cells[y]

        if self._coverage is not None:
            cov = self._coverage
            base = y * self.width
            for i in range(start_x, end_x):
                cov.add(base + i)

        if self._damage_mode:
            # Change-detect per cell so an incremental frame dirties only what
            # actually differs from the copied-in previous content.
            for i, cell in enumerate(cells[offset : end_x - x], start=start_x):
                if row[i] != cell:
                    row[i] = cell
                    self.mark_dirty(i, y, 1, 1)
            return

        # Fast path: set cells directly without individual comparisons and
        # mark the whole region dirty once.
        for i, cell in enumerate(cells[offset : end_x - x], start=start_x):
            row[i] = cell
        self.mark_dirty(start_x, y, end_x - start_x, 1)

    def set_cells_vertical(self, x: int, y: int, cells: list[Cell]) -> None:
        """Set multiple cells vertically in a single operation.

        This is optimized for performance, avoiding individual cell comparisons
        and marking the entire region dirty once instead of cell-by-cell.

        Parameters
        ----------
        x : int
            Column position (0-indexed)
        y : int
            Starting row position (0-indexed)
        cells : list of Cell
            Cells to set vertically

        Notes
        -----
        Out-of-bounds cells are clipped. The entire region is marked dirty
        regardless of whether individual cells changed, which is more efficient
        than checking each cell when most cells are expected to change.
        """
        if not (0 <= x < self.width) or not cells:
            return

        # Clip to screen bounds
        start_y = max(0, y)
        end_y = min(y + len(cells), self.height)
        if start_y >= end_y:
            return

        offset = start_y - y

        if self._coverage is not None:
            cov = self._coverage
            w = self.width
            for i in range(start_y, end_y):
                cov.add(i * w + x)

        if self._damage_mode:
            for i, cell in enumerate(cells[offset : end_y - y], start=start_y):
                if self.cells[i][x] != cell:
                    self.cells[i][x] = cell
                    self.mark_dirty(x, i, 1, 1)
            return

        # Fast path: set cells directly without individual comparisons.
        for i, cell in enumerate(cells[offset : end_y - y], start=start_y):
            self.cells[i][x] = cell
        self.mark_dirty(x, start_y, 1, end_y - start_y)

    def fill_rect(self, x: int, y: int, width: int, height: int, cell: Cell) -> None:
        """Fill a rectangular region with the same cell.

        This is highly optimized for filling regions with a single character,
        such as backgrounds or padding areas.

        Parameters
        ----------
        x : int
            Left edge of rectangle
        y : int
            Top edge of rectangle
        width : int
            Rectangle width
        height : int
            Rectangle height
        cell : Cell
            Cell to fill with

        Notes
        -----
        The entire region is marked dirty once. This is much more efficient
        than individual set_cell() calls for filling large areas.
        """
        # Clip to screen bounds
        start_x = max(0, x)
        end_x = min(x + width, self.width)
        start_y = max(0, y)
        end_y = min(y + height, self.height)

        if start_x >= end_x or start_y >= end_y:
            return

        if self._coverage is not None:
            cov = self._coverage
            w = self.width
            for row_idx in range(start_y, end_y):
                base = row_idx * w
                for col_idx in range(start_x, end_x):
                    cov.add(base + col_idx)

        if self._damage_mode:
            # Change-detect per cell (incremental frame).
            for row_idx in range(start_y, end_y):
                row = self.cells[row_idx]
                for col_idx in range(start_x, end_x):
                    if row[col_idx] != cell:
                        row[col_idx] = cell
                        self.mark_dirty(col_idx, row_idx, 1, 1)
            return

        # Fast path: fill cells directly and mark the whole region dirty once.
        for row_idx in range(start_y, end_y):
            row = self.cells[row_idx]
            for col_idx in range(start_x, end_x):
                row[col_idx] = cell
        self.mark_dirty(start_x, start_y, end_x - start_x, end_y - start_y)

    def get_cell(self, x: int, y: int) -> Cell | None:
        """Get the cell at the specified position.

        Parameters
        ----------
        x : int
            Column position (0-indexed)
        y : int
            Row position (0-indexed)

        Returns
        -------
        Cell or None
            The cell at the position, or None if out of bounds
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return None

    def mark_dirty(self, x: int, y: int, width: int, height: int) -> None:
        """Mark a rectangular region as needing update.

        Parameters
        ----------
        x : int
            Left edge of rectangle
        y : int
            Top edge of rectangle
        width : int
            Rectangle width
        height : int
            Rectangle height

        Notes
        -----
        Dirty regions are used by the diff renderer to identify which parts
        of the screen need updating. Multiple overlapping regions are
        automatically merged during rendering.
        """
        self.dirty_regions.add((x, y, width, height))

    def mark_all_dirty(self) -> None:
        """Mark the entire buffer as dirty.

        Notes
        -----
        Used when a full redraw is needed, such as after a terminal resize
        or when first rendering.
        """
        self.mark_dirty(0, 0, self.width, self.height)

    def get_dirty_regions(self) -> set[tuple[int, int, int, int]]:
        """Get all dirty regions.

        Returns
        -------
        set of tuple
            Set of (x, y, width, height) tuples representing dirty rectangles
        """
        return self.dirty_regions.copy()

    def get_merged_dirty_regions(self) -> list[tuple[int, int, int, int]]:
        """Get dirty regions collapsed to full-width rows.

        Returns
        -------
        list of tuple
            One ``(x, y, width, height)`` tuple per dirty row: each spans the
            full buffer width with height 1, i.e. ``(0, row, width, 1)``.

        Notes
        -----
        Rather than computing minimal bounding rectangles, every touched row is
        returned as a single full-width strip. This is cheaper to compute and,
        for the common case of scattered single-cell changes spread over a few
        rows, keeps the number of regions the diff renderer processes small.
        """
        if not self.dirty_regions:
            return []

        # For now, just return full-width horizontal strips for each dirty row
        # This is simpler than complex rectangle merging and works well for most cases
        rows_dirty = set()
        for _x, y, _w, h in self.dirty_regions:
            for row in range(y, y + h):
                if 0 <= row < self.height:
                    rows_dirty.add(row)

        # Return one region per dirty row, spanning full width
        return [(0, row, self.width, 1) for row in sorted(rows_dirty)]

    def clear_dirty(self) -> None:
        """Clear all dirty region tracking.

        Notes
        -----
        Should be called after rendering is complete to reset dirty state
        for the next frame.
        """
        self.dirty_regions.clear()

    def clear(self) -> None:
        """Clear the entire buffer to empty cells.

        Notes
        -----
        Fills all cells with the shared blank (space, no styling) - the same
        no-per-cell-allocation fill used at construction (see _BLANK_CELL) - and
        marks the entire buffer dirty.
        """
        self.cells = [[_BLANK_CELL] * self.width for _ in range(self.height)]
        self.mark_all_dirty()

    def to_text(self) -> str:
        """Convert buffer to plain text (for testing/debugging).

        Returns
        -------
        str
            Plain text representation with newlines

        Notes
        -----
        This converts the cell buffer to plain text by extracting character
        data and joining with newlines. Useful for test assertions and
        debugging output.

        Examples
        --------
        >>> buffer = ScreenBuffer(10, 3)
        >>> buffer.set_cell(0, 0, Cell('H'))
        >>> buffer.set_cell(1, 0, Cell('i'))
        >>> text = buffer.to_text()
        >>> 'Hi' in text
        True
        """
        lines = []
        for row in self.cells:
            line = "".join(cell.char for cell in row)
            lines.append(line)
        return "\n".join(lines)

    def resize(self, new_width: int, new_height: int) -> None:
        """Resize the buffer, preserving content where possible.

        Parameters
        ----------
        new_width : int
            New width in columns
        new_height : int
            New height in rows

        Notes
        -----
        Content in the upper-left region that fits in both old and new sizes
        is preserved. New cells are filled with spaces. The entire buffer is
        marked dirty after resize.
        """
        old_cells = self.cells
        old_width = self.width
        old_height = self.height

        # Create new buffer
        self.width = new_width
        self.height = new_height
        self.cells = [[Cell(" ") for _ in range(new_width)] for _ in range(new_height)]

        # Copy old content
        for y in range(min(old_height, new_height)):
            for x in range(min(old_width, new_width)):
                self.cells[y][x] = old_cells[y][x]

        # Mark entire buffer dirty
        self.mark_all_dirty()

    def to_string(self) -> str:
        """Convert buffer to plain text string for debugging.

        Returns
        -------
        str
            Multi-line string representation of buffer content (no ANSI codes)

        Notes
        -----
        This strips all styling and returns just the character content.
        Useful for debugging and testing.
        """
        lines = []
        for row in self.cells:
            line = "".join(cell.char for cell in row)
            lines.append(line)
        return "\n".join(lines)


class DiffRenderer:
    """Efficiently renders changes between two buffers.

    This class compares two ScreenBuffer instances and generates minimal ANSI
    escape sequences to update only the changed cells, dramatically reducing
    terminal output for incremental updates.

    Attributes
    ----------
    last_buffer : ScreenBuffer or None
        Previously rendered buffer for comparison

    Examples
    --------
    Render differences between buffers:

    >>> renderer = DiffRenderer()
    >>> old_buffer = ScreenBuffer(80, 24)
    >>> new_buffer = ScreenBuffer(80, 24)
    >>> new_buffer.set_cell(0, 0, Cell('A'))
    >>> ansi_output = renderer.render_diff(old_buffer, new_buffer)
    >>> '\\x1b[' in ansi_output  # Contains cursor positioning
    True

    First render generates full output:

    >>> renderer = DiffRenderer()
    >>> buffer = ScreenBuffer(10, 5)
    >>> output = renderer.render_diff(None, buffer)  # Full render
    """

    def __init__(self) -> None:
        self.last_buffer: ScreenBuffer | None = None

    def render_diff(
        self, old_buffer: ScreenBuffer | None, new_buffer: ScreenBuffer
    ) -> str:
        """Generate minimal ANSI commands to update terminal.

        Parameters
        ----------
        old_buffer : ScreenBuffer or None
            Previous buffer state, or None for full render
        new_buffer : ScreenBuffer
            New buffer state to render

        Returns
        -------
        str
            ANSI escape sequences to update terminal from old to new state

        Notes
        -----
        When old_buffer is None or dimensions don't match, performs a full
        render. Otherwise, only outputs ANSI sequences for changed cells.

        The generated output includes:
        - Cursor positioning (\x1b[row;colH)
        - Style codes for each changed cell
        - Optimizations to group adjacent cells with same style
        """
        if (
            old_buffer is None
            or old_buffer.width != new_buffer.width
            or old_buffer.height != new_buffer.height
        ):
            # Full redraw on first render or resize
            return self._full_render(new_buffer)

        # Diff-based render
        return self._diff_render(old_buffer, new_buffer)

    def _full_render(self, buffer: ScreenBuffer) -> str:
        """Render entire buffer from scratch.

        Parameters
        ----------
        buffer : ScreenBuffer
            Buffer to render

        Returns
        -------
        str
            Complete ANSI output for full screen
        """
        commands = []

        # Clear screen and home cursor
        commands.append("\x1b[2J")  # Clear screen
        commands.append("\x1b[H")  # Home cursor

        # Reset attributes before the first row. ``_render_row_optimized`` only
        # emits a reset *between* style runs, so the very first cell inherits
        # whatever attributes the terminal happened to have on entry (e.g. bold
        # left over from prior output). Without this, a full repaint can bleed
        # stale styling onto the first styled cell.
        commands.append("\x1b[0m")

        # Render each row
        for y, row in enumerate(buffer.cells):
            if y > 0:
                # Move to start of line
                commands.append(f"\x1b[{y + 1};1H")

            # Render row with style optimization
            line_output = self._render_row_optimized(row)
            commands.append(line_output)

        return "".join(commands)

    def _diff_render(self, old_buffer: ScreenBuffer, new_buffer: ScreenBuffer) -> str:
        """Render only differences between buffers.

        Parameters
        ----------
        old_buffer : ScreenBuffer
            Previous buffer state
        new_buffer : ScreenBuffer
            New buffer state

        Returns
        -------
        str
            ANSI sequences for changed cells only
        """
        commands = []

        # Use dirty regions if available for optimization
        if new_buffer.dirty_regions:
            # Use merged regions to avoid overlaps and reduce iteration
            merged_regions = new_buffer.get_merged_dirty_regions()
            for x, y, w, h in merged_regions:
                for row in range(y, min(y + h, new_buffer.height)):
                    diff_commands = self._render_row_diff(
                        old_buffer.cells[row],
                        new_buffer.cells[row],
                        row,
                        x,
                        min(x + w, new_buffer.width),
                    )
                    commands.extend(diff_commands)
        else:
            # Fall back to full diff scan
            for y in range(new_buffer.height):
                diff_commands = self._render_row_diff(
                    old_buffer.cells[y], new_buffer.cells[y], y
                )
                commands.extend(diff_commands)

        return "".join(commands)

    def _render_row_diff(
        self,
        old_row: list[Cell],
        new_row: list[Cell],
        row_num: int,
        start_col: int = 0,
        end_col: int | None = None,
    ) -> list[str]:
        """Render differences in a single row.

        Parameters
        ----------
        old_row : list of Cell
            Previous row state
        new_row : list of Cell
            New row state
        row_num : int
            Row number (0-indexed)
        start_col : int, optional
            Start column for scanning (default: 0)
        end_col : int or None, optional
            End column for scanning (default: row length)

        Returns
        -------
        list of str
            ANSI command strings for changed cells in this row
        """
        if end_col is None:
            end_col = len(new_row)

        commands: list[str] = []
        # current_pos: terminal column the cursor is parked at (None = unknown,
        # a move is owed). current_style: SGR signature active on the terminal.
        # It starts at _DEFAULT_STYLE because every prior row-diff and the
        # full-render path leave the terminal reset, so the cursor arrives here
        # in the default state. Both persist across the whole row scan, so a
        # contiguous run of changed cells sharing one style emits the SGR prefix
        # once instead of once per cell, and the style even carries across a
        # cursor jump to the next run (a CUP move does not touch SGR state).
        # This is the diff-path analogue of the grouping _render_row_optimized
        # already does (review item 2.12).
        current_pos: int | None = None
        current_style: tuple[object, ...] = _DEFAULT_STYLE

        def emit_cell(cell: Cell, x: int) -> None:
            nonlocal current_pos, current_style
            if current_pos != x:
                # Move cursor to position (1-indexed for ANSI). SGR is unaffected.
                commands.append(f"\x1b[{row_num + 1};{x + 1}H")
            sig = _style_sig(cell)
            if sig != current_style:
                if sig == _DEFAULT_STYLE:
                    # Back to no style: a single reset clears the active run.
                    commands.append("\x1b[0m")
                else:
                    # SGR params are additive, so clear a prior run before
                    # applying the new one; skip the reset when the terminal is
                    # already clean (start of row, or after a default run).
                    if current_style != _DEFAULT_STYLE:
                        commands.append("\x1b[0m")
                    commands.append(cell.get_style_codes())
                current_style = sig
            commands.append(cell.char)
            # Advance by the glyph's column width so a wide glyph accounts for
            # the continuation column the terminal also advanced past.
            current_pos = x + _cell_width(cell)

        for x in range(start_col, end_col):
            new_cell = new_row[x]

            if is_continuation(new_cell):
                # Trailing column of a wide glyph. Printing the head glyph
                # advances the terminal two columns, so this column is normally
                # covered and must not be emitted (that would push everything
                # after it one column right). But if this continuation differs
                # from the old buffer and its head was NOT just emitted (which
                # happens when the dirty scan starts on the continuation column,
                # or the head lies outside [start_col, end_col)), re-emit the
                # whole head so the glyph is not left half-drawn. current_pos is
                # x + 1 exactly when the head at x-1 was just emitted (width 2).
                if new_cell != old_row[x] and current_pos != x + 1:
                    head_x = x - 1
                    if head_x >= 0 and not is_continuation(new_row[head_x]):
                        emit_cell(new_row[head_x], head_x)
                continue

            if new_cell != old_row[x]:
                emit_cell(new_cell, x)

        # Clear a still-active run so its style does not bleed past the diff.
        # A run that ended in the default state left the terminal clean already.
        if current_style != _DEFAULT_STYLE:
            commands.append("\x1b[0m")

        return commands

    def _render_row_optimized(self, row: list[Cell]) -> str:
        """Render a row with style optimization.

        Parameters
        ----------
        row : list of Cell
            Row cells to render

        Returns
        -------
        str
            Optimized ANSI output for row

        Notes
        -----
        Groups consecutive cells with identical styling to minimize ANSI
        code output. This significantly reduces output size for regions
        with consistent styling.
        """
        if not row:
            return ""

        commands = []
        current_style = None

        for cell in row:
            # Skip the trailing column of a wide glyph: the head glyph already
            # advanced the terminal two columns. Emitting the continuation cell
            # would waste bytes and push the terminal an extra column right. The
            # writer guarantees the continuation shares the head's style.
            if is_continuation(cell):
                continue

            # Extract style signature for comparison
            style_sig = (
                cell.fg_color,
                cell.bg_color,
                cell.bold,
                cell.italic,
                cell.underline,
                cell.reverse,
                cell.dim,
            )

            if style_sig != current_style:
                # Style changed, emit reset first to clear previous attributes,
                # then emit new style codes and character
                if current_style is not None:
                    commands.append("\x1b[0m")
                commands.append(cell.get_style_codes())
                commands.append(cell.char)
                current_style = style_sig
            else:
                # Same style, just write char
                commands.append(cell.char)

        # Reset at end of line to prevent style bleed
        commands.append("\x1b[0m")

        return "".join(commands)
