"""Screen buffer and diff rendering for efficient terminal updates.

This module provides the ScreenBuffer class for managing 2D cell arrays and
the DiffRenderer class for generating minimal ANSI output by comparing buffers.
"""

from wijjit.terminal.cell import Cell


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

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.cells: list[list[Cell]] = [
            [Cell(" ") for _ in range(width)] for _ in range(height)
        ]
        self.dirty_regions: set[tuple[int, int, int, int]] = set()

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

        # Only mark dirty if cell actually changed
        if self.cells[y][x] != cell:
            self.cells[y][x] = cell
            self.mark_dirty(x, y, 1, 1)

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
        Fills all cells with space characters and no styling. The entire
        buffer is marked dirty.
        """
        self.cells = [
            [Cell(" ") for _ in range(self.width)] for _ in range(self.height)
        ]
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

    def __init__(self):
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
            # Render only dirty regions
            for x, y, w, h in new_buffer.dirty_regions:
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

        commands = []
        current_pos = None

        for x in range(start_col, end_col):
            if old_row[x] != new_row[x]:
                # Cell changed, need to update
                if current_pos != x:
                    # Move cursor to position (1-indexed for ANSI)
                    commands.append(f"\x1b[{row_num + 1};{x + 1}H")
                    current_pos = x

                # Write new cell with styling
                commands.append(new_row[x].to_ansi())
                current_pos = x + 1

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
                # Style changed, emit style codes then character
                commands.append(cell.get_style_codes())
                commands.append(cell.char)
                current_style = style_sig
            else:
                # Same style, just write char
                commands.append(cell.char)

        # Reset at end of line to prevent style bleed
        commands.append("\x1b[0m")

        return "".join(commands)
