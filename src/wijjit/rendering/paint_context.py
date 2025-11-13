"""Paint context for cell-based element rendering.

This module provides the PaintContext class which encapsulates the rendering
environment (buffer, styles, bounds) that elements use for cell-based rendering.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wijjit.layout.bounds import Bounds
    from wijjit.styling.resolver import StyleResolver
    from wijjit.styling.style import Style
    from wijjit.terminal.screen_buffer import ScreenBuffer


class PaintContext:
    """Rendering context for cell-based element painting.

    This class provides the environment and helper methods for elements
    to render themselves to a cell-based screen buffer using theme styles.

    Parameters
    ----------
    buffer : ScreenBuffer
        Target screen buffer for rendering
    style_resolver : StyleResolver
        Style resolver for applying theme styles
    bounds : Bounds
        Rendering bounds for the element (position and size)

    Attributes
    ----------
    buffer : ScreenBuffer
        Target screen buffer
    style_resolver : StyleResolver
        Style resolver
    bounds : Bounds
        Element bounds

    Examples
    --------
    Create a paint context and write styled text:

    >>> from wijjit.terminal.screen_buffer import ScreenBuffer
    >>> from wijjit.styling.resolver import StyleResolver
    >>> from wijjit.styling.theme import DefaultTheme
    >>> from wijjit.layout.bounds import Bounds
    >>> buffer = ScreenBuffer(80, 24)
    >>> resolver = StyleResolver(DefaultTheme())
    >>> bounds = Bounds(x=0, y=0, width=10, height=1)
    >>> ctx = PaintContext(buffer, resolver, bounds)
    >>> style = resolver.resolve_style_by_class('button')
    >>> ctx.write_text(0, 0, 'Click', style)

    Fill a rectangular region:

    >>> ctx.fill_rect(0, 0, 10, 5, ' ', style)
    """

    def __init__(
        self,
        buffer: "ScreenBuffer",
        style_resolver: "StyleResolver",
        bounds: "Bounds",
    ):
        self.buffer = buffer
        self.style_resolver = style_resolver
        self.bounds = bounds

    def write_text(
        self, x: int, y: int, text: str, style: "Style", clip: bool = True
    ) -> None:
        """Write styled text to the buffer at specified position.

        Parameters
        ----------
        x : int
            X coordinate (column) relative to element bounds
        y : int
            Y coordinate (row) relative to element bounds
        text : str
            Text to write (plain text, no ANSI codes)
        style : Style
            Style to apply to the text
        clip : bool, optional
            Whether to clip text to element bounds (default: True)

        Notes
        -----
        Coordinates are relative to the element's bounds. The method
        automatically translates to absolute screen coordinates.

        Text is written character by character, with each character
        becoming a styled Cell in the buffer. If clip=True, text
        extending beyond element bounds is truncated.

        Examples
        --------
        Write text at element's origin:

        >>> ctx.write_text(0, 0, 'Hello', style)

        Write text at offset within element:

        >>> ctx.write_text(5, 2, 'World', style)

        Write without clipping (may overflow bounds):

        >>> ctx.write_text(0, 0, 'Very long text', style, clip=False)
        """
        from wijjit.terminal.cell import Cell

        # Convert style to cell attributes
        cell_attrs = style.to_cell_attrs()

        # Translate to absolute coordinates
        abs_x = self.bounds.x + x
        abs_y = self.bounds.y + y

        # Calculate max width if clipping
        max_width = self.bounds.width - x if clip else len(text)

        # Write each character
        for i, char in enumerate(text):
            if clip and i >= max_width:
                break

            cell = Cell(char=char, **cell_attrs)
            self.buffer.set_cell(abs_x + i, abs_y, cell)

    def write_text_wrapped(
        self, x: int, y: int, text: str, style: "Style", max_width: int
    ) -> int:
        """Write text with word wrapping to buffer.

        Parameters
        ----------
        x : int
            X coordinate (column) relative to element bounds
        y : int
            Y coordinate (row) relative to element bounds
        text : str
            Text to write (may contain newlines)
        style : Style
            Style to apply to the text
        max_width : int
            Maximum width for wrapping

        Returns
        -------
        int
            Number of lines written

        Notes
        -----
        This method wraps text at word boundaries where possible,
        falling back to character wrapping for long words.

        Existing newlines in the text are preserved as line breaks.

        Examples
        --------
        Write wrapped text:

        >>> lines = ctx.write_text_wrapped(0, 0, 'Long text here', style, 10)
        >>> lines  # Number of lines used
        2
        """
        from wijjit.terminal.ansi import wrap_text

        current_y = y
        lines_written = 0

        # Split by existing newlines first
        for line in text.split("\n"):
            # Wrap this line
            wrapped = wrap_text(line, max_width)

            for wrapped_line in wrapped:
                self.write_text(x, current_y, wrapped_line, style)
                current_y += 1
                lines_written += 1

                # Stop if we've exceeded element bounds
                if current_y >= self.bounds.height:
                    return lines_written

        return lines_written

    def fill_rect(
        self, x: int, y: int, width: int, height: int, char: str, style: "Style"
    ) -> None:
        """Fill a rectangular region with a styled character.

        Parameters
        ----------
        x : int
            X coordinate (column) relative to element bounds
        y : int
            Y coordinate (row) relative to element bounds
        width : int
            Rectangle width
        height : int
            Rectangle height
        char : str
            Character to fill with (should be single character)
        style : Style
            Style to apply

        Notes
        -----
        Coordinates are relative to element bounds. The rectangle
        is automatically clipped to element bounds.

        Useful for backgrounds, borders, or clearing regions.

        Examples
        --------
        Fill background with spaces:

        >>> ctx.fill_rect(0, 0, 10, 5, ' ', style)

        Draw a filled box with a character:

        >>> ctx.fill_rect(2, 2, 5, 3, '#', style)
        """
        from wijjit.terminal.cell import Cell

        # Convert style to cell attributes
        cell_attrs = style.to_cell_attrs()

        # Translate to absolute coordinates
        abs_x = self.bounds.x + x
        abs_y = self.bounds.y + y

        # Clip to element bounds
        max_x = min(x + width, self.bounds.width)
        max_y = min(y + height, self.bounds.height)

        # Fill rectangle
        for row in range(y, max_y):
            for col in range(x, max_x):
                cell = Cell(char=char, **cell_attrs)
                self.buffer.set_cell(abs_x + (col - x), abs_y + (row - y), cell)

    def draw_border(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        style: "Style",
        border_chars: dict[str, str] | None = None,
    ) -> None:
        """Draw a border around a rectangular region.

        Parameters
        ----------
        x : int
            X coordinate (column) relative to element bounds
        y : int
            Y coordinate (row) relative to element bounds
        width : int
            Border width (including border characters)
        height : int
            Border height (including border characters)
        style : Style
            Style to apply to border
        border_chars : dict, optional
            Border characters dict with keys: 'tl', 'tr', 'bl', 'br',
            'h', 'v' (top-left, top-right, etc.). If None, uses single
            line box drawing characters.

        Notes
        -----
        Draws box-drawing characters around the specified rectangle.
        The rectangle dimensions include the border itself.

        Minimum size is 2x2 (for corners only).

        Examples
        --------
        Draw default single-line border:

        >>> ctx.draw_border(0, 0, 20, 10, style)

        Draw with custom characters:

        >>> custom = {'tl': '+', 'tr': '+', 'bl': '+', 'br': '+',
        ...           'h': '-', 'v': '|'}
        >>> ctx.draw_border(0, 0, 20, 10, style, custom)
        """
        from wijjit.terminal.cell import Cell

        # Default single-line box drawing characters
        if border_chars is None:
            border_chars = {
                "tl": "\u250c",  # ┌
                "tr": "\u2510",  # ┐
                "bl": "\u2514",  # └
                "br": "\u2518",  # ┘
                "h": "\u2500",  # ─
                "v": "\u2502",  # │
            }

        # Convert style to cell attributes
        cell_attrs = style.to_cell_attrs()

        # Translate to absolute coordinates
        abs_x = self.bounds.x + x
        abs_y = self.bounds.y + y

        # Draw corners
        if width >= 2 and height >= 2:
            self.buffer.set_cell(
                abs_x, abs_y, Cell(char=border_chars["tl"], **cell_attrs)
            )
            self.buffer.set_cell(
                abs_x + width - 1, abs_y, Cell(char=border_chars["tr"], **cell_attrs)
            )
            self.buffer.set_cell(
                abs_x, abs_y + height - 1, Cell(char=border_chars["bl"], **cell_attrs)
            )
            self.buffer.set_cell(
                abs_x + width - 1,
                abs_y + height - 1,
                Cell(char=border_chars["br"], **cell_attrs),
            )

        # Draw horizontal edges
        if width > 2:
            for col in range(1, width - 1):
                # Top edge
                self.buffer.set_cell(
                    abs_x + col, abs_y, Cell(char=border_chars["h"], **cell_attrs)
                )
                # Bottom edge
                if height >= 2:
                    self.buffer.set_cell(
                        abs_x + col,
                        abs_y + height - 1,
                        Cell(char=border_chars["h"], **cell_attrs),
                    )

        # Draw vertical edges
        if height > 2:
            for row in range(1, height - 1):
                # Left edge
                self.buffer.set_cell(
                    abs_x, abs_y + row, Cell(char=border_chars["v"], **cell_attrs)
                )
                # Right edge
                if width >= 2:
                    self.buffer.set_cell(
                        abs_x + width - 1,
                        abs_y + row,
                        Cell(char=border_chars["v"], **cell_attrs),
                    )

    def clear(self, style: "Style | None" = None) -> None:
        """Clear the element's bounds region.

        Parameters
        ----------
        style : Style, optional
            Style to apply to cleared cells (for background color).
            If None, uses default empty style.

        Notes
        -----
        Fills the entire element bounds with space characters.
        Useful for clearing before rendering new content.

        Examples
        --------
        Clear with default style:

        >>> ctx.clear()

        Clear with background color:

        >>> bg_style = Style(bg_color=(40, 40, 40))
        >>> ctx.clear(bg_style)
        """
        from wijjit.styling.style import Style

        if style is None:
            style = Style()

        self.fill_rect(0, 0, self.bounds.width, self.bounds.height, " ", style)

    def sub_context(self, x: int, y: int, width: int, height: int) -> "PaintContext":
        """Create a sub-context with relative bounds.

        Parameters
        ----------
        x : int
            X offset relative to current bounds
        y : int
            Y offset relative to current bounds
        width : int
            Width of sub-context
        height : int
            Height of sub-context

        Returns
        -------
        PaintContext
            New context with adjusted bounds

        Notes
        -----
        This is useful for nested rendering where a child element
        needs its own coordinate system within a parent's bounds.

        The new context shares the same buffer and style resolver.

        Examples
        --------
        Create sub-context for nested element:

        >>> sub_ctx = ctx.sub_context(10, 5, 20, 10)
        >>> # Now (0, 0) in sub_ctx is (10, 5) in parent context
        """
        from wijjit.layout.bounds import Bounds

        # Create new bounds relative to current bounds
        new_bounds = Bounds(
            x=self.bounds.x + x, y=self.bounds.y + y, width=width, height=height
        )

        return PaintContext(self.buffer, self.style_resolver, new_bounds)
