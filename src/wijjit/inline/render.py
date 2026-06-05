"""One-shot inline rendering for CLI applications.

This module provides the render_inline() function for rendering Wijjit
templates to terminal scrollback without using alternate screen mode.
"""

from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING, Any, TextIO

from wijjit.core.renderer import Renderer
from wijjit.terminal.cell import Cell

if TYPE_CHECKING:
    from wijjit.terminal.screen_buffer import ScreenBuffer


def render_inline(
    template: str,
    *,
    width: int | None = None,
    height: int | str = "auto",
    print_output: bool = True,
    file: TextIO | None = None,
    template_dir: str | None = None,
    **context: Any,
) -> str | None:
    """Render a Wijjit template inline to terminal scrollback.

    This function renders templates without using alternate screen buffer,
    allowing the output to become part of the terminal's scrollback history.
    Perfect for CLI tools that want styled output.

    Parameters
    ----------
    template : str
        Template string containing Wijjit template tags
    width : int, optional
        Render width in columns. If None, uses terminal width.
    height : int or "auto"
        Render height in lines. If "auto", calculates from content.
        Can exceed terminal height (unlimited).
    print_output : bool, optional
        If True (default), prints to file/stdout.
        If False, returns the ANSI string without printing.
    file : TextIO, optional
        Output destination. Defaults to sys.stdout.
    template_dir : str, optional
        Directory for template file loading (for {% include %} etc.)
    **context
        Variables passed to the template for rendering

    Returns
    -------
    str or None
        If print_output=False, returns the rendered ANSI string.
        If print_output=True, returns None after printing.

    Examples
    --------
    Simple inline output:

    >>> render_inline('''
    ... {% frame title="Status" %}
    ...   CPU: {{ cpu }}%
    ... {% endframe %}
    ... ''', cpu=45)

    Return string instead of printing:

    >>> output = render_inline(template, print_output=False, **data)

    With fixed dimensions:

    >>> render_inline(template, width=60, height=10, **data)
    """
    # Get terminal dimensions
    term_size = shutil.get_terminal_size()
    render_width = width if width is not None else term_size.columns

    # Create renderer
    renderer = Renderer(template_dir=template_dir)

    # Calculate height
    if height == "auto":
        # First pass: render with large height to determine content height
        max_height = 1000  # Large enough for most content
        _, elements, _ = renderer.render_with_layout(
            template_string=template,
            context=context,
            width=render_width,
            height=max_height,
        )

        # Calculate actual content height from element bounds
        render_height = _calculate_content_height(elements)
    else:
        render_height = int(height)

    # Final render with correct dimensions
    _, elements, _ = renderer.render_with_layout(
        template_string=template,
        context=context,
        width=render_width,
        height=render_height,
    )

    # Access the buffer from renderer
    buffer = renderer._last_base_buffer
    if buffer is None:
        return "" if not print_output else None

    # Convert to inline ANSI (no screen clearing commands)
    ansi_output = _buffer_to_inline_ansi(buffer, render_width, render_height)

    # Output
    if print_output:
        target = file if file is not None else sys.stdout
        target.write(ansi_output)
        target.write("\n")  # Final newline
        target.flush()
        return None
    else:
        return ansi_output


def _calculate_content_height(elements: list[Any]) -> int:
    """Calculate the height needed to fit all elements.

    This function analyzes element bounds to determine the minimum height
    needed for the content. It uses a heuristic: look at actual content
    elements (not frames/containers that expand to fill space), then add
    padding for frame borders.

    Parameters
    ----------
    elements : list
        List of elements with bounds

    Returns
    -------
    int
        Minimum height to fit all content (at least 1)
    """
    if not elements:
        return 1

    # Strategy: Find elements that have actual content and measure those.
    # Frames expand to fill, but their content doesn't.
    # We'll find the minimum bounding box that contains all elements,
    # then add space for frame borders.

    max_y: int = 0
    content_heights: list[int] = []
    has_frame = False

    for elem in elements:
        if elem.bounds is not None:
            bottom = elem.bounds.y + elem.bounds.height

            # Track all element bottoms
            max_y = max(max_y, bottom)

            # Check for frame elements
            elem_type = type(elem).__name__
            if elem_type == "Frame":
                has_frame = True
            else:
                # For non-frame elements (actual content), track height
                content_heights.append(bottom)

    # If we found content elements, use their max height
    if content_heights:
        height = max(content_heights)
        # Add 2 lines for frame border (top + bottom) if frame present
        if has_frame:
            height += 2
        return max(1, height)
    else:
        # No explicit content found, cap at reasonable default
        return max(1, min(max_y, 24))


def _buffer_to_inline_ansi(
    buffer: ScreenBuffer,
    width: int,
    height: int,
) -> str:
    """Convert buffer to inline ANSI string.

    Unlike the DiffRenderer which clears screen and uses cursor positioning,
    this outputs rows with newlines between them, suitable for scrollback.

    Parameters
    ----------
    buffer : ScreenBuffer
        The screen buffer to convert
    width : int
        Width to render
    height : int
        Height to render

    Returns
    -------
    str
        ANSI string with newlines between rows
    """
    lines = []

    for y in range(min(height, buffer.height)):
        row = buffer.cells[y]
        line_output = _render_row_optimized(row, width)
        # Strip trailing spaces for cleaner output
        lines.append(line_output.rstrip())

    return "\n".join(lines)


def _render_row_optimized(row: list[Cell], width: int) -> str:
    """Render a row with style optimization.

    Groups consecutive cells with identical styling to minimize ANSI output.

    Parameters
    ----------
    row : list of Cell
        Row cells to render
    width : int
        Maximum width to render

    Returns
    -------
    str
        Optimized ANSI output for row
    """
    if not row:
        return ""

    commands = []
    current_style = None

    for i, cell in enumerate(row):
        if i >= width:
            break

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
