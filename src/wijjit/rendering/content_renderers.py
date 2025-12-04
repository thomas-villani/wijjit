"""Content rendering utilities for different content types.

This module provides centralized content rendering functions that convert
various content formats (plain text, ANSI, HTML, Markdown, Rich markup,
and code) to either lines of ANSI strings or lists of Cell objects.

These utilities are used by ContentView and can be reused by other elements
that need to render formatted content.
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

from wijjit.terminal.ansi import wrap_text
from wijjit.terminal.cell import Cell

if TYPE_CHECKING:
    from wijjit.styling.resolver import StyleResolver


def render_plain_to_lines(content: str, width: int) -> list[str]:
    """Render plain text content with word wrapping.

    Parameters
    ----------
    content : str
        Plain text content to render
    width : int
        Maximum width for line wrapping

    Returns
    -------
    list of str
        List of wrapped text lines
    """
    if not content:
        return [""]

    lines: list[str] = []
    for paragraph in content.split("\n"):
        if not paragraph:
            lines.append("")
        else:
            # wrap_text returns list[str]
            wrapped = wrap_text(paragraph, width)
            lines.extend(wrapped)

    return lines if lines else [""]


def render_ansi_to_cells(content: str, width: int) -> list[list[Cell]]:
    """Render ANSI-encoded content to cell rows.

    Parameters
    ----------
    content : str
        Content with ANSI escape codes
    width : int
        Maximum width per row

    Returns
    -------
    list of list of Cell
        List of rows, each row is a list of cells
    """
    from wijjit.rendering.ansi_adapter import ansi_string_to_cells

    if not content:
        return [[]]

    rows: list[list[Cell]] = []
    for line in content.split("\n"):
        cells = ansi_string_to_cells(line)
        # Clip to width
        rows.append(cells[:width])

    return rows if rows else [[]]


def render_ansi_to_lines(content: str, width: int) -> list[str]:
    """Render ANSI-encoded content to lines (passthrough).

    Parameters
    ----------
    content : str
        Content with ANSI escape codes
    width : int
        Maximum width per line (for reference, no clipping performed)

    Returns
    -------
    list of str
        List of ANSI lines
    """
    if not content:
        return [""]

    lines = content.split("\n")
    return lines if lines else [""]


def render_html_to_cells(
    content: str,
    width: int,
    style_resolver: StyleResolver | None = None,
) -> list[list[Cell]]:
    """Render HTML content to cell rows.

    Parameters
    ----------
    content : str
        HTML-formatted content
    width : int
        Maximum width per row
    style_resolver : StyleResolver, optional
        Style resolver for theme-based class styling

    Returns
    -------
    list of list of Cell
        List of rows, each row is a list of cells
    """
    from wijjit.rendering.html_adapter import html_string_to_cells

    if not content:
        return [[Cell(char=" ")]]

    rows: list[list[Cell]] = []
    for line in content.split("\n"):
        if not line:
            rows.append([Cell(char=" ")])
        else:
            cells = html_string_to_cells(line, style_resolver)
            # Clip to width
            rows.append(cells[:width] if cells else [Cell(char=" ")])

    return rows if rows else [[Cell(char=" ")]]


def render_markdown_to_lines(content: str, width: int) -> list[str]:
    """Render Markdown content using Rich.

    Parameters
    ----------
    content : str
        Markdown content
    width : int
        Maximum width for rendering

    Returns
    -------
    list of str
        List of ANSI-formatted lines
    """
    if not content:
        return [""]

    from rich.console import Console
    from rich.markdown import Markdown

    md = Markdown(content)
    string_buffer = StringIO()
    console = Console(
        file=string_buffer,
        width=width,
        legacy_windows=False,
        force_terminal=True,
    )
    console.print(md)
    output = string_buffer.getvalue()

    lines = output.rstrip("\n").split("\n")
    return lines if lines else [""]


def render_rich_to_lines(content: str, width: int) -> list[str]:
    """Render Rich markup (e.g., [green]text[/green]) using Rich Console.

    Parameters
    ----------
    content : str
        Content with Rich markup tags
    width : int
        Maximum width for rendering

    Returns
    -------
    list of str
        List of ANSI-formatted lines
    """
    if not content:
        return [""]

    from rich.console import Console

    string_buffer = StringIO()
    console = Console(
        file=string_buffer,
        width=width,
        legacy_windows=False,
        force_terminal=True,
        markup=True,
        highlight=False,
    )
    console.print(content)
    output = string_buffer.getvalue()

    lines = output.rstrip("\n").split("\n")
    return lines if lines else [""]


def render_code_to_lines(
    content: str,
    width: int,
    language: str = "python",
    theme: str = "monokai",
    show_line_numbers: bool = False,
    line_number_start: int = 1,
) -> list[str]:
    """Render code with syntax highlighting using Rich.

    Parameters
    ----------
    content : str
        Source code content
    width : int
        Maximum width for rendering
    language : str
        Programming language for syntax highlighting (default: "python")
    theme : str
        Syntax highlighting theme (default: "monokai")
    show_line_numbers : bool
        Whether to show line numbers (default: False)
    line_number_start : int
        Starting line number (default: 1)

    Returns
    -------
    list of str
        List of ANSI-formatted lines with syntax highlighting
    """
    if not content:
        return [""]

    from rich.console import Console
    from rich.syntax import Syntax

    syntax = Syntax(
        content,
        language,
        theme=theme,
        line_numbers=show_line_numbers,
        start_line=line_number_start,
        word_wrap=False,
    )

    string_buffer = StringIO()
    console = Console(
        file=string_buffer,
        width=width,
        legacy_windows=False,
        force_terminal=True,
    )
    console.print(syntax)
    output = string_buffer.getvalue()

    lines = output.rstrip("\n").split("\n")
    return lines if lines else [""]
