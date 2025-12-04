"""Code editor element with syntax highlighting.

This module provides a CodeEditor element that extends TextArea with syntax
highlighting capabilities powered by Pygments.

The CodeEditor supports:
- Multiple programming languages (500+ via Pygments)
- Automatic language detection
- Multiple color themes (monokai, dracula, github-light, nord)
- Efficient incremental tokenization for large files
- All TextArea features (selection, clipboard, wrapping, etc.)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from pygments.lexers import (
    get_lexer_by_name,
    guess_lexer,
    guess_lexer_for_filename,
)
from pygments.util import ClassNotFound

from wijjit.elements.input.highlighting import (
    DEFAULT_THEME,
    get_available_themes,
    get_style_for_token,
)
from wijjit.elements.input.text import TextArea

if TYPE_CHECKING:
    from pygments.lexer import Lexer

    from wijjit.rendering import PaintContext
    from wijjit.styling.style import Style


class SyntaxHighlighter:
    """Manages syntax highlighting tokenization and caching.

    This class handles tokenizing source code using Pygments lexers and caching
    the results for efficient rendering. It supports incremental re-tokenization
    when edits are made, and full re-tokenization for large changes.

    Parameters
    ----------
    language : str, optional
        Programming language name (e.g., "python", "javascript").
        Use "auto" for automatic detection, or None to disable highlighting.
    theme : str, optional
        Color theme name (default: "monokai")
    filename_hint : str, optional
        Filename hint for language auto-detection (e.g., "main.py")

    Attributes
    ----------
    language : str or None
        Current language name
    theme : str
        Current theme name
    lexer : Lexer or None
        Pygments lexer instance
    line_tokens : list of list of tuple
        Cached tokens per line: [[(token_type, text), ...], ...]
    """

    def __init__(
        self,
        language: str | None = None,
        theme: str = DEFAULT_THEME,
        filename_hint: str | None = None,
    ) -> None:
        self.language: str | None = language
        self.theme: str = theme
        self.filename_hint: str | None = filename_hint
        self._lexer: Lexer | None = None  # Use underscore - lazily initialized
        self.line_tokens: list[list[tuple[type, str]]] = []
        self._dirty_from_line: int | None = None
        self._last_content_hash: int | None = None

        # Initialize lexer if language specified
        if language and language != "auto":
            self._init_lexer(language)

    def __getstate__(self) -> dict:
        """Get state for pickling, excluding the lexer.

        Returns
        -------
        dict
            Picklable state dictionary
        """
        state = self.__dict__.copy()
        # Remove the lexer - it contains unpicklable thread locks
        state["_lexer"] = None
        return state

    def __setstate__(self, state: dict) -> None:
        """Restore state from pickle, recreating the lexer.

        Parameters
        ----------
        state : dict
            Pickled state dictionary
        """
        self.__dict__.update(state)
        # Recreate lexer if we had a language set
        if self.language and self.language != "auto":
            self._init_lexer(self.language)

    def __deepcopy__(self, memo: dict) -> SyntaxHighlighter:
        """Create a deep copy, excluding the lexer.

        Parameters
        ----------
        memo : dict
            Memoization dictionary for deepcopy

        Returns
        -------
        SyntaxHighlighter
            Deep copy of this highlighter
        """
        import copy

        # Create a new instance without calling __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copy all attributes except _lexer
        for k, v in self.__dict__.items():
            if k == "_lexer":
                setattr(result, k, None)
            else:
                setattr(result, k, copy.deepcopy(v, memo))

        # Recreate lexer if we had a language set
        if result.language and result.language != "auto":
            result._init_lexer(result.language)

        return result

    @property
    def lexer(self) -> Lexer | None:
        """Get the Pygments lexer, creating it if needed.

        Returns
        -------
        Lexer or None
            The Pygments lexer instance
        """
        # Lazy initialization - recreate lexer if it was cleared (e.g., after unpickling)
        if self._lexer is None and self.language and self.language != "auto":
            self._init_lexer(self.language)
        return self._lexer

    @lexer.setter
    def lexer(self, value: Lexer | None) -> None:
        """Set the Pygments lexer.

        Parameters
        ----------
        value : Lexer or None
            The lexer to set
        """
        self._lexer = value

    def _init_lexer(self, language: str) -> bool:
        """Initialize the lexer for the specified language.

        Parameters
        ----------
        language : str
            Programming language name

        Returns
        -------
        bool
            True if lexer was initialized successfully
        """
        try:
            self.lexer = get_lexer_by_name(language)
            self.language = language
            return True
        except ClassNotFound:
            self.lexer = None
            self.language = None
            return False

    def detect_language(self, text: str) -> str | None:
        """Detect the programming language from content and/or filename.

        Parameters
        ----------
        text : str
            Source code content

        Returns
        -------
        str or None
            Detected language name, or None if detection failed

        Notes
        -----
        Filename-based detection is more reliable for short code snippets.
        Content-based detection works best with substantial code (50+ lines).
        """
        # Try filename-based detection first (more reliable)
        if self.filename_hint:
            try:
                lexer = guess_lexer_for_filename(self.filename_hint, text)
                self.lexer = lexer
                self.language = lexer.name.lower()
                return self.language
            except ClassNotFound:
                pass

        # Fall back to content-based detection
        if text and len(text) > 100:  # Need substantial content
            try:
                lexer = guess_lexer(text)
                # Only accept if confidence is reasonable (not "Text only")
                if lexer.name.lower() != "text only":
                    self.lexer = lexer
                    self.language = lexer.name.lower()
                    return self.language
            except ClassNotFound:
                pass

        return None

    def set_language(self, language: str | None) -> None:
        """Set the highlighting language.

        Parameters
        ----------
        language : str or None
            Language name, "auto", or None to disable highlighting
        """
        if language == self.language:
            return

        self.language = language
        self.line_tokens = []
        self._last_content_hash = None

        if language and language != "auto":
            self._init_lexer(language)
        else:
            self.lexer = None

    def set_theme(self, theme: str) -> None:
        """Set the color theme.

        Parameters
        ----------
        theme : str
            Theme name (e.g., "monokai", "dracula")
        """
        if theme in get_available_themes():
            self.theme = theme

    def tokenize_document(self, lines: list[str]) -> None:
        """Tokenize the entire document.

        Parameters
        ----------
        lines : list of str
            Document lines to tokenize

        Notes
        -----
        This performs a full tokenization of the document. For large documents,
        this may take 100-200ms. Results are cached per line for fast rendering.
        """
        if not self.lexer:
            # No lexer - clear tokens
            self.line_tokens = []
            return

        # Check if content has changed
        content_hash = hash(tuple(lines))
        if content_hash == self._last_content_hash:
            return  # No change, use cached tokens
        self._last_content_hash = content_hash

        # Join lines for tokenization
        text = "\n".join(lines)

        # Tokenize the full document
        all_tokens = list(self.lexer.get_tokens(text))

        # Build per-line token lists
        self.line_tokens = []
        current_line_tokens: list[tuple[type, str]] = []

        for token_type, value in all_tokens:
            if "\n" in value:
                # Token spans multiple lines
                parts = value.split("\n")
                for i, part in enumerate(parts):
                    if part:
                        current_line_tokens.append((token_type, part))
                    if i < len(parts) - 1:
                        # End of line
                        self.line_tokens.append(current_line_tokens)
                        current_line_tokens = []
            else:
                current_line_tokens.append((token_type, value))

        # Don't forget the last line
        if current_line_tokens:
            self.line_tokens.append(current_line_tokens)

        # Ensure we have tokens for all lines (some may be empty)
        while len(self.line_tokens) < len(lines):
            self.line_tokens.append([])

        self._dirty_from_line = None

    def invalidate_from_line(self, line_idx: int) -> None:
        """Mark lines from the given index as needing re-tokenization.

        Parameters
        ----------
        line_idx : int
            Starting line index for invalidation

        Notes
        -----
        This is used for incremental updates. When a line is edited, all lines
        from that point forward may need re-tokenization (due to multi-line
        constructs like strings and comments).
        """
        if self._dirty_from_line is None:
            self._dirty_from_line = line_idx
        else:
            self._dirty_from_line = min(self._dirty_from_line, line_idx)

    def retokenize_incremental(self, lines: list[str]) -> None:
        """Re-tokenize only from the dirty line forward.

        Parameters
        ----------
        lines : list of str
            Document lines

        Notes
        -----
        This is more efficient than full re-tokenization for small edits.
        However, for safety and simplicity with multi-line constructs,
        we re-tokenize from the dirty line to the end.
        """
        if self._dirty_from_line is None:
            return

        if not self.lexer:
            self.line_tokens = []
            return

        # For simplicity, re-tokenize the full document
        # A more sophisticated approach would track lexer state per line
        self._last_content_hash = None  # Force re-tokenization
        self.tokenize_document(lines)

    def get_line_tokens(self, line_idx: int) -> list[tuple[type, str]]:
        """Get cached tokens for a specific line.

        Parameters
        ----------
        line_idx : int
            Line index (0-based)

        Returns
        -------
        list of tuple
            List of (token_type, text) tuples for the line
        """
        if 0 <= line_idx < len(self.line_tokens):
            return self.line_tokens[line_idx]
        return []

    def is_highlighting_enabled(self) -> bool:
        """Check if syntax highlighting is currently enabled.

        Returns
        -------
        bool
            True if highlighting is enabled and a lexer is available
        """
        return self.lexer is not None


class CodeEditor(TextArea):
    """Text editor with syntax highlighting support.

    CodeEditor extends TextArea with syntax highlighting powered by Pygments.
    It supports 500+ programming languages, multiple color themes, and
    efficient incremental tokenization for large files.

    Parameters
    ----------
    id : str, optional
        Element identifier
    value : str, optional
        Initial source code content
    language : str, optional
        Programming language (e.g., "python", "javascript", "rust").
        Use "auto" for automatic detection, or None to disable highlighting.
    theme : str, optional
        Color theme name (default: "monokai").
        Available: "monokai", "dracula", "github-light", "nord"
    filename_hint : str, optional
        Filename hint for auto-detection (e.g., "main.py")
    width : int, optional
        Display width in columns (default: 60)
    height : int, optional
        Display height in rows (default: 20)
    show_line_numbers : bool, optional
        Whether to show line numbers (default: True)
    wrap_mode : {"none", "soft"}, optional
        Line wrapping mode (default: "none")
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : str or None, optional
        Border style: "single", "double", "rounded", or None (default: "single")

    Attributes
    ----------
    highlighter : SyntaxHighlighter
        Syntax highlighting manager
    show_line_numbers : bool
        Whether line numbers are displayed
    line_number_width : int
        Width reserved for line numbers (calculated from content)

    Examples
    --------
    Create a Python code editor:

    >>> editor = CodeEditor(
    ...     language="python",
    ...     theme="monokai",
    ...     value="def hello():\\n    print('Hello!')"
    ... )

    Create an auto-detecting editor:

    >>> editor = CodeEditor(
    ...     language="auto",
    ...     filename_hint="script.js"
    ... )

    Notes
    -----
    Performance considerations:
    - Initial tokenization takes ~150ms for 1000 lines
    - Cached token lookup is instant (~0.04ms for viewport)
    - Small edits trigger debounced incremental re-tokenization
    - Large operations (paste, undo) trigger full re-tokenization
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        value: str = "",
        language: str | None = "python",
        theme: str = DEFAULT_THEME,
        filename_hint: str | None = None,
        width: int = 60,
        height: int = 20,
        show_line_numbers: bool = True,
        wrap_mode: Literal["none", "soft"] = "none",
        show_scrollbar: bool = True,
        border_style: Literal["single", "double", "rounded"] | None = "single",
    ) -> None:
        # Initialize base TextArea
        super().__init__(
            id=id,
            classes=classes,
            value="",  # Set value later after highlighter is ready
            width=width,
            height=height,
            wrap_mode=wrap_mode,
            show_scrollbar=show_scrollbar,
            border_style=border_style,
        )

        # Line number display
        self.show_line_numbers = show_line_numbers
        self.line_number_width = 4  # Default, will be calculated

        # Initialize syntax highlighter
        self.highlighter = SyntaxHighlighter(
            language=language,
            theme=theme,
            filename_hint=filename_hint,
        )

        # Debounce timer for re-tokenization
        self._retokenize_task: asyncio.Task[None] | None = None
        self._retokenize_delay: float = 0.1  # 100ms debounce

        # Callback to request a render after retokenization completes
        # This is wired by ElementWiringManager to trigger app.needs_render
        self._request_render: Callable[[], None] | None = None

        # Now set the value (will trigger tokenization)
        if value:
            self.set_value(value)

    def __deepcopy__(self, memo: dict) -> CodeEditor:
        """Create a deep copy, excluding unpicklable objects.

        Parameters
        ----------
        memo : dict
            Memoization dictionary for deepcopy

        Returns
        -------
        CodeEditor
            Deep copy of this editor
        """
        import copy

        # Create a new instance without calling __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copy all attributes, handling special cases
        for k, v in self.__dict__.items():
            if k == "_retokenize_task":
                # Tasks can't be copied - set to None
                setattr(result, k, None)
            elif k == "highlighter":
                # Use highlighter's own __deepcopy__
                setattr(result, k, copy.deepcopy(v, memo))
            else:
                setattr(result, k, copy.deepcopy(v, memo))

        return result

    def set_value(self, text: str) -> None:
        """Set the editor content and trigger tokenization.

        Parameters
        ----------
        text : str
            Source code content
        """
        super().set_value(text)
        self._update_line_number_width()

        # Handle auto-detection
        if self.highlighter.language == "auto":
            self.highlighter.detect_language(text)

        # Tokenize the content
        self.highlighter.tokenize_document(self.lines)

    def set_language(self, language: str | None) -> None:
        """Set the syntax highlighting language.

        Parameters
        ----------
        language : str or None
            Language name (e.g., "python"), "auto", or None to disable
        """
        self.highlighter.set_language(language)

        if language == "auto":
            self.highlighter.detect_language(self.get_value())

        # Re-tokenize with new language
        self.highlighter.tokenize_document(self.lines)

    def set_theme(self, theme: str) -> None:
        """Set the color theme.

        Parameters
        ----------
        theme : str
            Theme name (e.g., "monokai", "dracula")
        """
        self.highlighter.set_theme(theme)

    @property
    def language(self) -> str | None:
        """Get the current syntax highlighting language.

        Returns
        -------
        str or None
            Current language name, or None if highlighting is disabled
        """
        return self.highlighter.language

    @language.setter
    def language(self, value: str | None) -> None:
        """Set the syntax highlighting language.

        Parameters
        ----------
        value : str or None
            Language name (e.g., "python"), "auto", or None to disable
        """
        self.set_language(value)

    @property
    def theme(self) -> str:
        """Get the current color theme.

        Returns
        -------
        str
            Current theme name
        """
        return self.highlighter.theme

    @theme.setter
    def theme(self, value: str) -> None:
        """Set the color theme.

        Parameters
        ----------
        value : str
            Theme name (e.g., "monokai", "dracula")
        """
        self.set_theme(value)

    def _update_line_number_width(self) -> None:
        """Calculate width needed for line numbers."""
        if self.show_line_numbers:
            # Width = digits + space + separator
            num_lines = max(len(self.lines), 1)
            digits = len(str(num_lines))
            self.line_number_width = digits + 2  # digits + space + separator
        else:
            self.line_number_width = 0

    def _emit_change(self, old_value: str, new_value: str) -> None:
        """Handle content change - trigger incremental re-tokenization.

        Parameters
        ----------
        old_value : str
            Previous content
        new_value : str
            New content
        """
        # Track line count before change
        old_line_count = old_value.count("\n") + 1
        new_line_count = new_value.count("\n") + 1

        super()._emit_change(old_value, new_value)

        # Update line number width if line count changed significantly
        self._update_line_number_width()

        # Immediately update tokens for the affected line(s) for instant feedback
        self._update_tokens_immediate(old_line_count, new_line_count)

        # Mark highlighting as dirty from cursor position
        self.highlighter.invalidate_from_line(self.cursor_row)

        # Schedule debounced full re-tokenization for multi-line constructs
        self._schedule_retokenize()

    def _update_tokens_immediate(
        self, old_line_count: int, new_line_count: int
    ) -> None:
        """Immediately update tokens for affected lines.

        This provides instant syntax highlighting feedback without waiting
        for the debounced full re-tokenization. It handles three cases:

        1. Same line count: Re-tokenize just the current line
        2. Lines added: Insert empty entries and re-tokenize affected lines
        3. Lines removed: Remove entries and re-tokenize the merged line

        Parameters
        ----------
        old_line_count : int
            Number of lines before the change
        new_line_count : int
            Number of lines after the change
        """
        if not self.highlighter.lexer:
            return

        cursor_row = self.cursor_row
        tokens = self.highlighter.line_tokens

        # Ensure tokens array is the right size
        while len(tokens) < new_line_count:
            tokens.append([])
        while len(tokens) > new_line_count:
            tokens.pop()

        if old_line_count == new_line_count:
            # Case 1: Edit within a single line - just re-tokenize that line
            self._tokenize_line(cursor_row)
        elif new_line_count > old_line_count:
            # Case 2: Lines were added (e.g., Enter key)
            # Shift tokens down and re-tokenize affected lines
            lines_added = new_line_count - old_line_count
            # Insert empty entries at cursor position
            for _ in range(lines_added):
                if cursor_row < len(tokens):
                    tokens.insert(cursor_row, [])
            # Re-tokenize the affected lines (current and next)
            for i in range(
                cursor_row, min(cursor_row + lines_added + 1, len(self.lines))
            ):
                self._tokenize_line(i)
        else:
            # Case 3: Lines were removed (e.g., Backspace merging lines)
            # The token array was already shrunk above
            # Re-tokenize the current line (which is now merged)
            if cursor_row < len(self.lines):
                self._tokenize_line(cursor_row)

    def _tokenize_line(self, line_idx: int) -> None:
        """Tokenize a single line and update the token cache.

        Parameters
        ----------
        line_idx : int
            Index of the line to tokenize
        """
        if not self.highlighter.lexer:
            return

        if line_idx >= len(self.lines):
            return

        line = self.lines[line_idx]
        tokens = self.highlighter.line_tokens

        # Ensure array is large enough
        while len(tokens) <= line_idx:
            tokens.append([])

        # Tokenize just this line
        # Note: This won't handle multi-line constructs perfectly,
        # but the debounced full retokenization will fix those
        line_tokens: list[tuple[type, str]] = []
        for token_type, value in self.highlighter.lexer.get_tokens(line):
            # Split on newlines (shouldn't happen for single line, but be safe)
            if "\n" in value:
                parts = value.split("\n")
                if parts[0]:
                    line_tokens.append((token_type, parts[0]))
                # Ignore parts after newline for single-line tokenization
            else:
                line_tokens.append((token_type, value))

        tokens[line_idx] = line_tokens

    def _schedule_retokenize(self) -> None:
        """Schedule debounced re-tokenization."""
        # Cancel any pending task
        if self._retokenize_task is not None:
            self._retokenize_task.cancel()
            self._retokenize_task = None

        # Try to schedule new task
        try:
            loop = asyncio.get_running_loop()
            self._retokenize_task = loop.create_task(self._debounced_retokenize())
        except RuntimeError:
            # No event loop running - do immediate tokenization
            self.highlighter.retokenize_incremental(self.lines)

    async def _debounced_retokenize(self) -> None:
        """Debounced re-tokenization coroutine."""
        try:
            await asyncio.sleep(self._retokenize_delay)
            self.highlighter.retokenize_incremental(self.lines)
            # Request a render to display the updated syntax highlighting
            if self._request_render is not None:
                self._request_render()
        except asyncio.CancelledError:
            pass  # Task was cancelled, ignore

    def _get_content_width_for_render(self) -> int:
        """Get content width accounting for line numbers.

        Returns
        -------
        int
            Available width for code content
        """
        content_width = self.width
        if self.show_line_numbers:
            content_width -= self.line_number_width
        return content_width

    def render_to(self, ctx: PaintContext) -> None:
        """Render code editor using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Extends TextArea rendering to add:
        - Syntax highlighting via cached tokens
        - Line numbers (optional)
        - Theme-based token coloring
        """
        # Resolve base styles
        if self.focused:
            content_style = ctx.style_resolver.resolve_style(self, "textarea:focus")
            border_style = ctx.style_resolver.resolve_style(
                self, "textarea.border:focus"
            )
        else:
            content_style = ctx.style_resolver.resolve_style(self, "textarea")
            border_style = ctx.style_resolver.resolve_style(self, "textarea.border")

        # Determine if we need borders
        has_borders = self.border_style is not None

        if has_borders:
            self._render_to_with_border(ctx, content_style, border_style)
        else:
            self._render_to_content(ctx, content_style, 0, 0, self.width, self.height)

    def _render_to_content(
        self,
        ctx: PaintContext,
        content_style: Style,
        start_x: int,
        start_y: int,
        width: int,
        height: int,
    ) -> None:
        """Render code editor content with syntax highlighting.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        content_style : Style
            Base content style
        start_x : int
            Starting X position
        start_y : int
            Starting Y position
        width : int
            Content width
        height : int
            Content height
        """
        from wijjit.styling.style import Style
        from wijjit.terminal.cell import Cell

        # Determine scrollbar space
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        scrollbar_width = 1 if needs_scrollbar else 0

        # Calculate widths
        line_num_width = self.line_number_width if self.show_line_numbers else 0
        code_width = width - line_num_width - scrollbar_width

        # Get visible range
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        # Create styles
        content_attrs = content_style.to_cell_attrs()

        # Create cursor style (reverse video)
        cursor_style = Style(
            fg_color=content_style.bg_color or (0, 0, 0),
            bg_color=content_style.fg_color or (255, 255, 255),
            bold=content_style.bold,
            italic=content_style.italic,
        )
        cursor_attrs = cursor_style.to_cell_attrs()

        # Get selection style
        selection_style = ctx.style_resolver.resolve_style(self, "textarea.selection")
        selection_attrs = selection_style.to_cell_attrs()

        # Line number style (dimmed)
        line_num_style = Style(
            fg_color=(128, 128, 128),  # Gray
            bg_color=content_style.bg_color,
        )
        line_num_attrs = line_num_style.to_cell_attrs()

        # Render each visible line
        for display_idx in range(height):
            line_idx = visible_start + display_idx
            y = ctx.bounds.y + start_y + display_idx
            x_offset = ctx.bounds.x + start_x

            # Render line number if enabled
            if self.show_line_numbers:
                if line_idx < len(self.lines):
                    line_num_str = str(line_idx + 1).rjust(line_num_width - 1) + " "
                else:
                    line_num_str = " " * line_num_width

                for i, char in enumerate(line_num_str):
                    ctx.buffer.set_cell(
                        x_offset + i, y, Cell(char=char, **line_num_attrs)
                    )
                x_offset += line_num_width

            # Render code content
            if line_idx < len(self.lines):
                line = self.lines[line_idx]
                show_cursor = self.focused and line_idx == self.cursor_row

                # Get tokens for this line
                tokens = self.highlighter.get_line_tokens(line_idx)

                # Check if tokens are stale (don't match current line content)
                # This can happen during editing when retokenization is debounced
                tokens_valid = False
                if tokens:
                    # Reconstruct line from tokens to verify they match
                    token_text = "".join(text for _, text in tokens)
                    tokens_valid = token_text == line

                # If tokens are stale and highlighting is enabled, re-tokenize immediately
                # This prevents flickering between highlighted and plain text during edits
                if not tokens_valid and self.highlighter.is_highlighting_enabled():
                    self._tokenize_line(line_idx)
                    tokens = self.highlighter.get_line_tokens(line_idx)
                    # Verify tokens are now valid
                    if tokens:
                        token_text = "".join(text for _, text in tokens)
                        tokens_valid = token_text == line

                # Render with syntax highlighting only if tokens are fresh
                if tokens_valid and self.highlighter.is_highlighting_enabled():
                    self._render_highlighted_line(
                        ctx,
                        x_offset,
                        y,
                        line,
                        line_idx,
                        tokens,
                        code_width,
                        show_cursor,
                        cursor_attrs,
                        selection_attrs,
                        content_attrs,
                    )
                else:
                    # No highlighting - render plain
                    self._render_plain_line(
                        ctx,
                        x_offset,
                        y,
                        line,
                        line_idx,
                        code_width,
                        show_cursor,
                        cursor_attrs,
                        selection_attrs,
                        content_attrs,
                    )
            else:
                # Empty line (beyond content)
                for i in range(code_width):
                    ctx.buffer.set_cell(
                        x_offset + i, y, Cell(char=" ", **content_attrs)
                    )

        # Render scrollbar if needed
        if needs_scrollbar:
            from wijjit.layout.scroll import render_vertical_scrollbar

            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, height
            )
            scrollbar_x = ctx.bounds.x + start_x + width - 1

            for i in range(height):
                scrollbar_char = scrollbar_chars[i] if i < len(scrollbar_chars) else " "
                ctx.buffer.set_cell(
                    scrollbar_x,
                    ctx.bounds.y + start_y + i,
                    Cell(char=scrollbar_char, **content_attrs),
                )

    def _render_highlighted_line(
        self,
        ctx: PaintContext,
        x_start: int,
        y: int,
        line: str,
        line_idx: int,
        tokens: list[tuple[type, str]],
        width: int,
        show_cursor: bool,
        cursor_attrs: dict,
        selection_attrs: dict,
        content_attrs: dict,
    ) -> None:
        """Render a line with syntax highlighting.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        x_start : int
            Starting X position
        y : int
            Y position
        line : str
            Line content
        line_idx : int
            Line index in document
        tokens : list of tuple
            Token list for this line
        width : int
            Available width
        show_cursor : bool
            Whether to show cursor on this line
        cursor_attrs : dict
            Cell attributes for cursor
        selection_attrs : dict
            Cell attributes for selection
        content_attrs : dict
            Default cell attributes
        """
        from wijjit.terminal.cell import Cell

        x = x_start
        col = 0  # Column position in line

        # Process each token
        for token_type, token_text in tokens:
            if x >= x_start + width:
                break

            # Get style for this token type
            token_style = get_style_for_token(token_type, self.highlighter.theme)
            token_attrs = self._token_style_to_attrs(token_style, content_attrs)

            # Render each character in the token
            for char in token_text:
                if x >= x_start + width:
                    break

                # Check for cursor
                if show_cursor and col == self.cursor_col:
                    ctx.buffer.set_cell(x, y, Cell(char=char, **cursor_attrs))
                # Check for selection
                elif self._is_position_selected(line_idx, col):
                    ctx.buffer.set_cell(x, y, Cell(char=char, **selection_attrs))
                else:
                    ctx.buffer.set_cell(x, y, Cell(char=char, **token_attrs))

                x += 1
                col += 1

        # Pad remaining width
        while x < x_start + width:
            # Check for cursor at end of line
            if show_cursor and col == self.cursor_col:
                ctx.buffer.set_cell(x, y, Cell(char=" ", **cursor_attrs))
            else:
                ctx.buffer.set_cell(x, y, Cell(char=" ", **content_attrs))
            x += 1
            col += 1

    def _render_plain_line(
        self,
        ctx: PaintContext,
        x_start: int,
        y: int,
        line: str,
        line_idx: int,
        width: int,
        show_cursor: bool,
        cursor_attrs: dict,
        selection_attrs: dict,
        content_attrs: dict,
    ) -> None:
        """Render a line without syntax highlighting.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        x_start : int
            Starting X position
        y : int
            Y position
        line : str
            Line content
        line_idx : int
            Line index in document
        width : int
            Available width
        show_cursor : bool
            Whether to show cursor on this line
        cursor_attrs : dict
            Cell attributes for cursor
        selection_attrs : dict
            Cell attributes for selection
        content_attrs : dict
            Default cell attributes
        """
        from wijjit.terminal.cell import Cell

        # Clip or pad line to width
        if len(line) > width:
            display_line = line[:width]
        else:
            display_line = line.ljust(width)

        # Render each character
        for col, char in enumerate(display_line):
            x = x_start + col

            # Check for cursor
            if show_cursor and col == self.cursor_col:
                ctx.buffer.set_cell(x, y, Cell(char=char, **cursor_attrs))
            # Check for selection
            elif self._is_position_selected(line_idx, col):
                ctx.buffer.set_cell(x, y, Cell(char=char, **selection_attrs))
            else:
                ctx.buffer.set_cell(x, y, Cell(char=char, **content_attrs))

    def _token_style_to_attrs(self, token_style: dict, default_attrs: dict) -> dict:
        """Convert token style to cell attributes.

        Parameters
        ----------
        token_style : dict
            Token style from theme
        default_attrs : dict
            Default cell attributes

        Returns
        -------
        dict
            Cell attributes dictionary
        """
        attrs = dict(default_attrs)  # Start with defaults

        if "fg_color" in token_style and token_style["fg_color"]:
            attrs["fg_color"] = token_style["fg_color"]
        if "bg_color" in token_style and token_style["bg_color"]:
            attrs["bg_color"] = token_style["bg_color"]
        if token_style.get("bold"):
            attrs["bold"] = True
        if token_style.get("italic"):
            attrs["italic"] = True
        if token_style.get("underline"):
            attrs["underline"] = True

        return attrs
