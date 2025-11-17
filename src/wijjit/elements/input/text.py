# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable
from enum import Enum, auto
from typing import TYPE_CHECKING, Literal

from wijjit.elements.base import Element, ElementType
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.layout.scroll import ScrollManager, render_vertical_scrollbar
from wijjit.rendering import PaintContext
from wijjit.terminal.ansi import (
    ANSIColor,
    ANSIStyle,
    clip_to_width,
    is_wrap_boundary,
    strip_ansi,
    visible_length,
    wrap_text,
)
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.styling.style import Style


class InputStyle(Enum):
    """Visual style for text input rendering.

    This enum defines different border and decoration styles for text inputs.
    Each style provides a distinct visual appearance while maintaining
    single-line height.
    """

    BRACKETS = auto()  # [ text... ] - Square brackets
    BOX = auto()  # ├─────────┤ - Box drawing characters
    BLOCK = auto()  # ▐text    ▌ - Block characters
    UNDERLINE = auto()  # text_____ - Underline only
    MINIMAL = auto()  # text with styling only


class TextInput(Element):
    """Text input field element.

    Parameters
    ----------
    id : str, optional
        Element identifier
    placeholder : str, optional
        Placeholder text when empty
    value : str, optional
        Initial value
    width : int, optional
        Display width for content (default: 20), excludes borders
    max_length : int, optional
        Maximum input length
    style : InputStyle, optional
        Visual style for input rendering (default: BRACKETS)

    Attributes
    ----------
    value : str
        Current input value
    placeholder : str
        Placeholder text
    cursor_pos : int
        Cursor position in the text
    width : int
        Display width for content (excludes borders)
    max_length : int or None
        Maximum input length
    style : InputStyle
        Visual style for rendering

    Examples
    --------
    Create a basic text input:

    >>> inp = TextInput(placeholder="Enter name...")

    Create input with different styles:

    >>> inp = TextInput(placeholder="Email", style=InputStyle.BOX, width=30)
    >>> inp = TextInput(value="Default", style=InputStyle.UNDERLINE)
    """

    def __init__(
        self,
        id: str | None = None,
        placeholder: str = "",
        value: str = "",
        width: int = 20,
        max_length: int | None = None,
        style: InputStyle = InputStyle.BRACKETS,
    ):
        super().__init__(id)
        self.element_type = ElementType.INPUT
        self.focusable = True
        self.value = value
        self.placeholder = placeholder
        self.cursor_pos = len(value)
        self.width = width
        self.max_length = max_length
        self.style = style

        # Callbacks for value changes and actions
        self.on_change: Callable[[str, str], None] | None = (
            None  # (old_value, new_value)
        )
        self.on_action: Callable[[], None] | None = None  # Called on Enter

        # Action ID and bind settings (set by template extension)
        self.action: str | None = None
        self.bind: bool = True

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        old_value = self.value

        # Enter key - trigger action
        if key == Keys.ENTER:
            if self.on_action:
                self.on_action()
            return True

        # Character input
        if key.is_char and key.char:
            if self.max_length is None or len(self.value) < self.max_length:
                # Insert character at cursor position
                self.value = (
                    self.value[: self.cursor_pos]
                    + key.char
                    + self.value[self.cursor_pos :]
                )
                self.cursor_pos += 1
                self._emit_change(old_value, self.value)
                return True

        # Backspace
        elif key == Keys.BACKSPACE:
            if self.cursor_pos > 0:
                self.value = (
                    self.value[: self.cursor_pos - 1] + self.value[self.cursor_pos :]
                )
                self.cursor_pos -= 1
                self._emit_change(old_value, self.value)
                return True

        # Delete
        elif key == Keys.DELETE:
            if self.cursor_pos < len(self.value):
                self.value = (
                    self.value[: self.cursor_pos] + self.value[self.cursor_pos + 1 :]
                )
                self._emit_change(old_value, self.value)
                return True

        # Left arrow
        elif key == Keys.LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
                return True

        # Right arrow
        elif key == Keys.RIGHT:
            if self.cursor_pos < len(self.value):
                self.cursor_pos += 1
                return True

        # Home
        elif key == Keys.HOME:
            self.cursor_pos = 0
            return True

        # End
        elif key == Keys.END:
            self.cursor_pos = len(self.value)
            return True

        return False

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        # On click, just indicate we handled it - App will set focus
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            return True

        return False

    def _emit_change(self, old_value: str, new_value: str) -> None:
        """Emit change event.

        Parameters
        ----------
        old_value : str
            Previous value
        new_value : str
            New value
        """
        if self.on_change is not None and old_value != new_value:
            self.on_change(old_value, new_value)

    def render_to(self, ctx: PaintContext) -> None:
        """Render text input using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the reference implementation for text input cell-based rendering.
        It demonstrates how to:
        1. Handle text that exceeds display width (scrolling)
        2. Render cursor position with proper styling
        3. Show placeholder text when empty
        4. Apply different border styles
        5. Resolve styles based on focus state

        The input renders as a single line with decorative borders and cursor
        indication when focused.
        """
        from wijjit.styling.style import Style

        # Resolve style based on input state
        if self.focused:
            resolved_style = ctx.style_resolver.resolve_style(self, "input:focus")
        else:
            resolved_style = ctx.style_resolver.resolve_style(self, "input")

        # Determine display text (value or placeholder)
        display_text = self.value if self.value else self.placeholder
        # use_placeholder = not self.value

        # Calculate scroll offset for long text
        scroll_offset = 0
        if len(display_text) > self.width:
            # Scroll to keep cursor visible
            if self.cursor_pos >= self.width:
                scroll_offset = self.cursor_pos - self.width + 1

        # Get visible portion of text
        visible_text = display_text[scroll_offset : scroll_offset + self.width]

        # Pad to width
        if len(visible_text) < self.width:
            visible_text = visible_text.ljust(self.width)

        # Calculate visible cursor position
        visible_cursor_pos = self.cursor_pos - scroll_offset

        # Apply cursor if focused
        if self.focused and 0 <= visible_cursor_pos <= len(visible_text):
            # Apply reverse video to cursor position
            before = visible_text[:visible_cursor_pos]
            cursor_char = (
                visible_text[visible_cursor_pos]
                if visible_cursor_pos < len(visible_text)
                else " "
            )
            after = visible_text[visible_cursor_pos + 1 :]

            # Create style with reverse video for cursor
            cursor_style = Style(
                fg_color=resolved_style.bg_color or (0, 0, 0),
                bg_color=resolved_style.fg_color or (255, 255, 255),
                bold=resolved_style.bold,
                italic=resolved_style.italic,
            )

            # Render based on visual style
            x_offset = 0

            if self.style == InputStyle.BRACKETS:
                # [ text... ]
                ctx.write_text(0, 0, "[", resolved_style)
                x_offset = 1

                # Render text with cursor
                ctx.write_text(x_offset, 0, before, resolved_style)
                ctx.write_text(x_offset + len(before), 0, cursor_char, cursor_style)
                ctx.write_text(x_offset + len(before) + 1, 0, after, resolved_style)
                ctx.write_text(x_offset + self.width, 0, "]", resolved_style)

            elif self.style == InputStyle.BOX:
                # ├─────────┤
                ctx.write_text(0, 0, "\u251c", resolved_style)  # ├
                x_offset = 1

                # Render text with cursor
                ctx.write_text(x_offset, 0, before, resolved_style)
                ctx.write_text(x_offset + len(before), 0, cursor_char, cursor_style)
                ctx.write_text(x_offset + len(before) + 1, 0, after, resolved_style)
                ctx.write_text(x_offset + self.width, 0, "\u2524", resolved_style)  # ┤

            elif self.style == InputStyle.BLOCK:
                # ▐text    ▌
                ctx.write_text(0, 0, "\u258c", resolved_style)  # ▌
                x_offset = 1

                # Render text with cursor
                ctx.write_text(x_offset, 0, before, resolved_style)
                ctx.write_text(x_offset + len(before), 0, cursor_char, cursor_style)
                ctx.write_text(x_offset + len(before) + 1, 0, after, resolved_style)
                ctx.write_text(x_offset + self.width, 0, "\u2590", resolved_style)  # ▐

            elif self.style == InputStyle.UNDERLINE:
                # text with underline
                underline_style = Style(
                    fg_color=resolved_style.fg_color,
                    bg_color=resolved_style.bg_color,
                    bold=resolved_style.bold,
                    italic=resolved_style.italic,
                    underline=True,
                )

                # Render text with cursor
                ctx.write_text(0, 0, before, underline_style)
                ctx.write_text(len(before), 0, cursor_char, cursor_style)
                ctx.write_text(len(before) + 1, 0, after, underline_style)

            elif self.style == InputStyle.MINIMAL:
                # Just text with styling
                # Render text with cursor
                ctx.write_text(0, 0, before, resolved_style)
                ctx.write_text(len(before), 0, cursor_char, cursor_style)
                ctx.write_text(len(before) + 1, 0, after, resolved_style)

        else:
            # Not focused or cursor out of bounds - render without cursor
            x_offset = 0

            if self.style == InputStyle.BRACKETS:
                ctx.write_text(0, 0, "[", resolved_style)
                x_offset = 1
                ctx.write_text(x_offset, 0, visible_text, resolved_style)
                ctx.write_text(x_offset + self.width, 0, "]", resolved_style)

            elif self.style == InputStyle.BOX:
                ctx.write_text(0, 0, "\u251c", resolved_style)  # ├
                x_offset = 1
                ctx.write_text(x_offset, 0, visible_text, resolved_style)
                ctx.write_text(x_offset + self.width, 0, "\u2524", resolved_style)  # ┤

            elif self.style == InputStyle.BLOCK:
                ctx.write_text(0, 0, "\u258c", resolved_style)  # ▌
                x_offset = 1
                ctx.write_text(x_offset, 0, visible_text, resolved_style)
                ctx.write_text(x_offset + self.width, 0, "\u2590", resolved_style)  # ▐

            elif self.style == InputStyle.UNDERLINE:
                underline_style = Style(
                    fg_color=resolved_style.fg_color,
                    bg_color=resolved_style.bg_color,
                    bold=resolved_style.bold,
                    italic=resolved_style.italic,
                    underline=True,
                )
                ctx.write_text(0, 0, visible_text, underline_style)

            elif self.style == InputStyle.MINIMAL:
                ctx.write_text(0, 0, visible_text, resolved_style)


class TextArea(Element):
    """Multiline text area element with scrolling support.

    Parameters
    ----------
    id : str, optional
        Element identifier
    value : str, optional
        Initial value (multiline text with \\n separators)
    width : int, optional
        Display width in columns for content area (default: 40).
        Note: Borders add 2 additional columns to total width when enabled.
    height : int, optional
        Display height in rows/lines (default: 10)
    wrap_mode : {"none", "soft", "hard"}, optional
        Line wrapping mode (default: "none")
        - "none": No wrapping, lines can exceed width
        - "soft": Visual wrapping only for display
        - "hard": Insert actual newlines when line exceeds width
    max_lines : int, optional
        Maximum number of lines allowed
    show_scrollbar : bool, optional
        Whether to show vertical scrollbar (default: True)
    border_style : BorderStyle or {"single", "double", "rounded"} or None, optional
        Border style for the text area (default: "single").
        - "single": Single-line box-drawing characters
        - "double": Double-line box-drawing characters
        - "rounded": Rounded corner box-drawing characters
        - None: No borders
        Can also accept BorderStyle enum values.

    Attributes
    ----------
    lines : list of str
        Text content as array of lines
    cursor_row : int
        Current cursor line (0-based)
    cursor_col : int
        Current cursor column within line (0-based)
    scroll_manager : ScrollManager
        Manages vertical scrolling
    width : int
        Display width (content area, excluding borders)
    height : int
        Display height (viewport)
    wrap_mode : str
        Line wrapping mode
    max_lines : int or None
        Maximum line count
    show_scrollbar : bool
        Whether to show scrollbar
    border_style : BorderStyle or None
        Border style for rendering
    """

    def __init__(
        self,
        id: str | None = None,
        value: str = "",
        width: int = 40,
        height: int = 10,
        wrap_mode: Literal["none", "soft", "hard"] = "none",
        max_lines: int | None = None,
        show_scrollbar: bool = True,
        border_style: (
            BorderStyle | Literal["single", "double", "rounded"] | None
        ) = "single",
    ):
        super().__init__(id)
        self.element_type = ElementType.INPUT
        self.focusable = True

        # Display dimensions
        self.width = width
        self.height = height
        self.wrap_mode = wrap_mode
        self.max_lines = max_lines
        self.show_scrollbar = show_scrollbar

        # Border style (normalize string to enum)
        self.border_style = self._normalize_border_style(border_style)

        # Text content storage
        self.lines: list[str] = [""]  # Start with one empty line
        self.cursor_row = 0
        self.cursor_col = 0

        # Scroll management
        self.scroll_manager = ScrollManager(
            content_size=1, viewport_size=height  # One line initially
        )

        # Callbacks
        self.on_change: Callable[[str, str], None] | None = None
        self.on_action: Callable[[], None] | None = None

        # Action settings (set by template extension)
        self.action: str | None = None
        self.bind: bool = True

        # Dynamic sizing flag (set by template tag)
        self._dynamic_sizing: bool = False

        # Set initial value if provided
        if value:
            self.set_value(value)

    def set_bounds(self, bounds) -> None:
        """Set bounds and dynamically resize if needed.

        Parameters
        ----------
        bounds : Bounds
            New bounds for the element
        """
        super().set_bounds(bounds)

        # If dynamic sizing is enabled, resize the element to fit the bounds
        if self._dynamic_sizing and bounds:
            new_width = bounds.width
            new_height = bounds.height

            # Account for borders
            if self.border_style is not None:
                new_width = max(3, new_width - 2)  # Minimum width for borders
                new_height = max(3, new_height - 2)  # Minimum height for borders

            # Update dimensions if changed
            if new_width != self.width or new_height != self.height:
                self.width = new_width
                self.height = new_height

                # Update scroll manager with new viewport size
                self.scroll_manager.update_viewport_size(self.height)

    def _normalize_border_style(
        self, style: BorderStyle | Literal["single", "double", "rounded"] | None
    ) -> BorderStyle | None:
        """Normalize border style from string or enum to BorderStyle enum.

        Parameters
        ----------
        style : BorderStyle or str or None
            Border style as enum, string, or None

        Returns
        -------
        BorderStyle or None
            Normalized border style as enum, or None
        """
        if style is None:
            return None
        if isinstance(style, BorderStyle):
            return style
        # Convert string to enum
        style_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        return style_map.get(style.lower(), BorderStyle.SINGLE)

    def get_value(self) -> str:
        """Get the full text content.

        Returns
        -------
        str
            Complete text with newline separators
        """
        return "\n".join(self.lines)

    def set_value(self, text: str) -> None:
        """Set the full text content.

        Parameters
        ----------
        text : str
            New text content (can contain newlines)

        Notes
        -----
        This replaces all content and resets cursor to start.
        Updates scroll manager with new content size.
        """
        old_value = self.get_value()

        # Split into lines (handle both \n and \r\n)
        self.lines = text.replace("\r\n", "\n").split("\n")

        # Ensure at least one empty line
        if not self.lines:
            self.lines = [""]

        # Apply max_lines constraint
        if self.max_lines is not None and len(self.lines) > self.max_lines:
            self.lines = self.lines[: self.max_lines]

        # Reset cursor to start
        self.cursor_row = 0
        self.cursor_col = 0

        # Update scroll manager with visual line count
        visual_line_count = self._calculate_total_visual_lines()
        self.scroll_manager.update_content_size(visual_line_count)
        self.scroll_manager.scroll_to_top()

        # Emit change event
        new_value = self.get_value()
        if self.on_change and old_value != new_value:
            self.on_change(old_value, new_value)

    def rewrap_content(self, new_width: int | None = None) -> None:
        """Explicitly re-wrap all content to a new width.

        Parameters
        ----------
        new_width : int, optional
            New content width to wrap to. If None, uses current content width.

        Notes
        -----
        Only applies when wrap_mode="hard". Does nothing for other wrap modes.
        Useful when terminal width changes and content needs to be re-wrapped.
        Attempts to preserve cursor position relative to content.
        Emits on_change callback if content changes.
        """
        if self.wrap_mode != "hard":
            return  # Only applies to hard wrap mode

        # Determine target width
        if new_width is None:
            content_width = self.width
            if self.show_scrollbar:
                content_width -= 1
        else:
            content_width = new_width

        # Store old value for change detection
        old_value = self.get_value()

        # Remember cursor position in terms of character offset from start
        cursor_offset = 0
        for i in range(self.cursor_row):
            cursor_offset += len(self.lines[i]) + 1  # +1 for newline
        cursor_offset += self.cursor_col

        # Re-wrap all content
        # Start from scratch: join all lines, then re-split with hard wrapping
        all_text = self.get_value()

        # Apply hard wrapping by setting value and letting set_value handle it
        # But we need to preserve the cursor, so do it manually
        self.lines = all_text.replace("\r\n", "\n").split("\n")
        if not self.lines:
            self.lines = [""]

        # Apply wrapping to each line
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            line_length = visible_length(line)

            if line_length > content_width:
                # This line needs wrapping
                # Check max_lines constraint
                if self.max_lines is None or len(self.lines) < self.max_lines:
                    # Apply wrapping
                    # Save cursor_row temporarily
                    saved_cursor_row = self.cursor_row
                    saved_cursor_col = self.cursor_col

                    # Temporarily set cursor to not interfere
                    self.cursor_row = -1

                    self._apply_hard_wrap_to_line(i, content_width)

                    # Restore cursor
                    self.cursor_row = saved_cursor_row
                    self.cursor_col = saved_cursor_col

                    # Don't increment i since _apply_hard_wrap_to_line inserts a line
                    # Continue to check the same line index (now shorter)
                else:
                    # Can't wrap more lines, move on
                    i += 1
            else:
                # Line is fine, move to next
                i += 1

        # Restore cursor position from offset
        current_offset = 0
        found = False
        for row_idx, line in enumerate(self.lines):
            line_len = len(line)
            if current_offset + line_len >= cursor_offset:
                # Cursor is on this line
                self.cursor_row = row_idx
                self.cursor_col = cursor_offset - current_offset
                found = True
                break
            current_offset += line_len + 1  # +1 for newline

        if not found:
            # Cursor offset beyond content, place at end
            self.cursor_row = len(self.lines) - 1
            self.cursor_col = len(self.lines[self.cursor_row])

        # Update scroll manager
        visual_line_count = self._calculate_total_visual_lines()
        self.scroll_manager.update_content_size(visual_line_count)

        # Ensure cursor visible
        self._ensure_cursor_visible()

        # Emit change event if value changed
        new_value = self.get_value()
        self._emit_change(old_value, new_value)

    def _emit_change(self, old_value: str, new_value: str) -> None:
        """Emit change event.

        Parameters
        ----------
        old_value : str
            Previous value
        new_value : str
            New value
        """
        if self.on_change and old_value != new_value:
            self.on_change(old_value, new_value)

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        old_value = self.get_value()

        # Character input
        if key.is_char and key.char:
            handled = self._insert_char(key.char)
            if handled:
                self._emit_change(old_value, self.get_value())
            return handled

        # Enter key - create new line
        elif key == Keys.ENTER:
            handled = self._insert_newline()
            if handled:
                self._emit_change(old_value, self.get_value())
            return handled

        # Backspace
        elif key == Keys.BACKSPACE:
            handled = self._backspace()
            if handled:
                self._emit_change(old_value, self.get_value())
            return handled

        # Delete
        elif key == Keys.DELETE:
            handled = self._delete()
            if handled:
                self._emit_change(old_value, self.get_value())
            return handled

        # Navigation - Arrow keys
        elif key == Keys.UP:
            return self._move_cursor_up()

        elif key == Keys.DOWN:
            return self._move_cursor_down()

        elif key == Keys.LEFT:
            return self._move_cursor_left()

        elif key == Keys.RIGHT:
            return self._move_cursor_right()

        # Ctrl+Arrow for word boundaries
        elif key.name == "ctrl+left":
            return self._word_boundary_left()

        elif key.name == "ctrl+right":
            return self._word_boundary_right()

        # Navigation - Home/End
        elif key == Keys.HOME:
            return self._move_to_line_start()

        elif key == Keys.END:
            return self._move_to_line_end()

        # Ctrl+Home/End for document start/end
        elif key.name == "ctrl+home":
            return self._move_to_document_start()

        elif key.name == "ctrl+end":
            return self._move_to_document_end()

        # Navigation - Page Up/Down
        elif key == Keys.PAGE_UP:
            return self._page_up()

        elif key == Keys.PAGE_DOWN:
            return self._page_down()

        return False

    def _insert_char(self, char: str) -> bool:
        """Insert a character at the cursor position.

        Parameters
        ----------
        char : str
            Character to insert

        Returns
        -------
        bool
            True if character was inserted
        """
        # Filter out non-printable characters (control characters, ANSI escapes, etc.)
        if not char.isprintable():
            return False

        # Get current line
        current_line = self.lines[self.cursor_row]

        # Insert character at cursor position
        new_line = (
            current_line[: self.cursor_col] + char + current_line[self.cursor_col :]
        )
        self.lines[self.cursor_row] = new_line

        # Advance cursor
        self.cursor_col += 1

        # Apply hard wrapping if enabled and line exceeds width
        if self.wrap_mode == "hard":
            # Calculate content width (account for scrollbar)
            content_width = self.width
            if self.show_scrollbar:
                content_width -= 1

            line_length = visible_length(self.lines[self.cursor_row])

            if line_length > content_width:
                # Line exceeds width, need to wrap
                # Check max_lines constraint first
                if self.max_lines is None or len(self.lines) < self.max_lines:
                    self._apply_hard_wrap_to_line(self.cursor_row, content_width)

        return True

    def _insert_newline(self) -> bool:
        """Insert a newline at cursor position, splitting the current line.

        Returns
        -------
        bool
            True if newline was inserted
        """
        # Check max_lines constraint
        if self.max_lines is not None and len(self.lines) >= self.max_lines:
            return False

        # Split current line at cursor
        current_line = self.lines[self.cursor_row]
        before = current_line[: self.cursor_col]
        after = current_line[self.cursor_col :]

        # Update current line and insert new line below
        self.lines[self.cursor_row] = before
        self.lines.insert(self.cursor_row + 1, after)

        # Move cursor to start of new line
        self.cursor_row += 1
        self.cursor_col = 0

        # Update scroll manager with visual line count
        visual_line_count = self._calculate_total_visual_lines()
        self.scroll_manager.update_content_size(visual_line_count)

        # Auto-scroll to keep cursor visible
        self._ensure_cursor_visible()
        return True

    def _backspace(self) -> bool:
        """Delete character before cursor (or merge with previous line).

        Returns
        -------
        bool
            True if something was deleted
        """
        # If at start of line, merge with previous line
        if self.cursor_col == 0:
            if self.cursor_row == 0:
                # At start of document, can't backspace
                return False

            # Merge with previous line
            prev_line = self.lines[self.cursor_row - 1]
            curr_line = self.lines[self.cursor_row]

            # Remember where cursor will be
            new_col = len(prev_line)

            # Merge lines
            self.lines[self.cursor_row - 1] = prev_line + curr_line
            del self.lines[self.cursor_row]

            # Update cursor
            self.cursor_row -= 1
            self.cursor_col = new_col

            # If hard wrap is enabled, check if merged line needs re-wrapping
            if self.wrap_mode == "hard":
                # Calculate content width
                content_width = self.width
                if self.show_scrollbar:
                    content_width -= 1

                merged_line_length = visible_length(self.lines[self.cursor_row])
                if merged_line_length > content_width:
                    # Merged line exceeds width, re-wrap it
                    self._apply_hard_wrap_to_line(self.cursor_row, content_width)

            # Update scroll manager with visual line count
            visual_line_count = self._calculate_total_visual_lines()
            self.scroll_manager.update_content_size(visual_line_count)

            # Auto-scroll to keep cursor visible
            self._ensure_cursor_visible()
            return True
        else:
            # Delete character before cursor
            current_line = self.lines[self.cursor_row]
            new_line = (
                current_line[: self.cursor_col - 1] + current_line[self.cursor_col :]
            )
            self.lines[self.cursor_row] = new_line

            # Move cursor back
            self.cursor_col -= 1

            return True

    def _delete(self) -> bool:
        """Delete character at cursor (or merge with next line).

        Returns
        -------
        bool
            True if something was deleted
        """
        current_line = self.lines[self.cursor_row]

        # If at end of line, merge with next line
        if self.cursor_col >= len(current_line):
            if self.cursor_row >= len(self.lines) - 1:
                # At end of document, can't delete
                return False

            # Merge with next line
            next_line = self.lines[self.cursor_row + 1]
            self.lines[self.cursor_row] = current_line + next_line
            del self.lines[self.cursor_row + 1]

            # Cursor stays in same position

            # If hard wrap is enabled, check if merged line needs re-wrapping
            if self.wrap_mode == "hard":
                # Calculate content width
                content_width = self.width
                if self.show_scrollbar:
                    content_width -= 1

                merged_line_length = visible_length(self.lines[self.cursor_row])
                if merged_line_length > content_width:
                    # Merged line exceeds width, re-wrap it
                    self._apply_hard_wrap_to_line(self.cursor_row, content_width)

            # Update scroll manager with visual line count
            visual_line_count = self._calculate_total_visual_lines()
            self.scroll_manager.update_content_size(visual_line_count)

            return True
        else:
            # Delete character at cursor
            new_line = (
                current_line[: self.cursor_col] + current_line[self.cursor_col + 1 :]
            )
            self.lines[self.cursor_row] = new_line

            # Cursor stays in same position
            return True

    def _move_cursor_up(self) -> bool:
        """Move cursor up one line.

        Returns
        -------
        bool
            True if cursor moved
        """
        if self.cursor_row == 0:
            return False

        self.cursor_row -= 1
        # Clamp column to new line length
        line_len = len(self.lines[self.cursor_row])
        if self.cursor_col > line_len:
            self.cursor_col = line_len

        # Auto-scroll to keep cursor visible
        self._ensure_cursor_visible()
        return True

    def _move_cursor_down(self) -> bool:
        """Move cursor down one line.

        Returns
        -------
        bool
            True if cursor moved
        """
        if self.cursor_row >= len(self.lines) - 1:
            return False

        self.cursor_row += 1
        # Clamp column to new line length
        line_len = len(self.lines[self.cursor_row])
        if self.cursor_col > line_len:
            self.cursor_col = line_len

        # Auto-scroll to keep cursor visible
        self._ensure_cursor_visible()
        return True

    def _move_cursor_left(self) -> bool:
        """Move cursor left one character (wrap to previous line if needed).

        Returns
        -------
        bool
            True if cursor moved
        """
        if self.cursor_col > 0:
            self.cursor_col -= 1
            return True
        elif self.cursor_row > 0:
            # Wrap to end of previous line
            self.cursor_row -= 1
            self.cursor_col = len(self.lines[self.cursor_row])
            # Auto-scroll to keep cursor visible
            self._ensure_cursor_visible()
            return True
        else:
            return False

    def _move_cursor_right(self) -> bool:
        """Move cursor right one character (wrap to next line if needed).

        Returns
        -------
        bool
            True if cursor moved
        """
        line_len = len(self.lines[self.cursor_row])

        if self.cursor_col < line_len:
            self.cursor_col += 1
            return True
        elif self.cursor_row < len(self.lines) - 1:
            # Wrap to start of next line
            self.cursor_row += 1
            self.cursor_col = 0
            # Auto-scroll to keep cursor visible
            self._ensure_cursor_visible()
            return True
        else:
            return False

    def _move_to_line_start(self) -> bool:
        """Move cursor to start of current line.

        Returns
        -------
        bool
            True if cursor moved
        """
        if self.cursor_col == 0:
            return False

        self.cursor_col = 0
        return True

    def _move_to_line_end(self) -> bool:
        """Move cursor to end of current line.

        Returns
        -------
        bool
            True if cursor moved
        """
        line_len = len(self.lines[self.cursor_row])

        if self.cursor_col == line_len:
            return False

        self.cursor_col = line_len
        return True

    def _move_to_document_start(self) -> bool:
        """Move cursor to start of document.

        Returns
        -------
        bool
            True if cursor moved
        """
        if self.cursor_row == 0 and self.cursor_col == 0:
            return False

        self.cursor_row = 0
        self.cursor_col = 0
        # Auto-scroll to keep cursor visible
        self._ensure_cursor_visible()
        return True

    def _move_to_document_end(self) -> bool:
        """Move cursor to end of document.

        Returns
        -------
        bool
            True if cursor moved
        """
        last_row = len(self.lines) - 1
        last_col = len(self.lines[last_row])

        if self.cursor_row == last_row and self.cursor_col == last_col:
            return False

        self.cursor_row = last_row
        self.cursor_col = last_col
        # Auto-scroll to keep cursor visible
        self._ensure_cursor_visible()
        return True

    def _ensure_cursor_visible(self) -> None:
        """Ensure cursor is visible in viewport by scrolling if needed.

        Notes
        -----
        This is called after cursor movements to keep the cursor visible.
        Accounts for line wrapping when wrap_mode is enabled.
        """
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        if self.wrap_mode == "none":
            # Use actual cursor row for non-wrapping mode
            cursor_line = self.cursor_row

            if cursor_line < visible_start:
                # Cursor is above viewport, scroll up to show it
                self.scroll_manager.scroll_to(cursor_line)
            elif cursor_line >= visible_end:
                # Cursor is below viewport, scroll down to show it
                # Position cursor near bottom of viewport with 1-line margin if possible
                target_scroll = cursor_line - self.height + 1
                self.scroll_manager.scroll_to(max(0, target_scroll))
        else:
            # Use visual cursor row for wrapping modes
            cursor_visual_row, _ = self._actual_to_visual_position(
                self.cursor_row, self.cursor_col
            )

            if cursor_visual_row < visible_start:
                # Cursor is above viewport, scroll up to show it
                self.scroll_manager.scroll_to(cursor_visual_row)
            elif cursor_visual_row >= visible_end:
                # Cursor is below viewport, scroll down to show it
                # Position cursor near bottom of viewport with 1-line margin if possible
                target_scroll = cursor_visual_row - self.height + 1
                self.scroll_manager.scroll_to(max(0, target_scroll))

    def _page_up(self) -> bool:
        """Scroll up by one viewport height.

        Returns
        -------
        bool
            True if scrolled
        """
        old_position = self.scroll_manager.state.scroll_position

        # Scroll viewport up
        self.scroll_manager.page_up()

        # Move cursor up by the same amount
        scroll_delta = old_position - self.scroll_manager.state.scroll_position
        new_row = max(0, self.cursor_row - scroll_delta)
        self.cursor_row = new_row

        # Clamp cursor column to new line
        line_len = len(self.lines[self.cursor_row])
        if self.cursor_col > line_len:
            self.cursor_col = line_len

        return scroll_delta > 0

    def _page_down(self) -> bool:
        """Scroll down by one viewport height.

        Returns
        -------
        bool
            True if scrolled
        """
        old_position = self.scroll_manager.state.scroll_position

        # Scroll viewport down
        self.scroll_manager.page_down()

        # Move cursor down by the same amount
        scroll_delta = self.scroll_manager.state.scroll_position - old_position
        new_row = min(len(self.lines) - 1, self.cursor_row + scroll_delta)
        self.cursor_row = new_row

        # Clamp cursor column to new line
        line_len = len(self.lines[self.cursor_row])
        if self.cursor_col > line_len:
            self.cursor_col = line_len

        return scroll_delta > 0

    def _is_word_char(self, ch: str) -> bool:
        """Check if a character is part of a word.

        Parameters
        ----------
        ch : str
            Character to check

        Returns
        -------
        bool
            True if character is alphanumeric or underscore
        """
        return ch.isalnum() or ch == "_"

    def _word_boundary_left(self) -> bool:
        """Move cursor to start of previous word (Ctrl+Left).

        Returns
        -------
        bool
            True if cursor moved
        """
        # Start from current position
        row, col = self.cursor_row, self.cursor_col

        # If at start of document, can't go left
        if row == 0 and col == 0:
            return False

        # Move left one position to start
        if col > 0:
            col -= 1
        else:
            # Move to end of previous line
            row -= 1
            col = len(self.lines[row])
            if col > 0:
                col -= 1

        # Skip non-word characters
        while row > 0 or col > 0:
            current_char = self.lines[row][col] if col < len(self.lines[row]) else ""
            if self._is_word_char(current_char):
                break

            if col > 0:
                col -= 1
            elif row > 0:
                row -= 1
                col = len(self.lines[row])
                if col > 0:
                    col -= 1
            else:
                break

        # Skip word characters to find word start
        while row > 0 or col > 0:
            # Check if previous character is a word char
            prev_col = col - 1
            prev_row = row

            if prev_col < 0:
                if prev_row > 0:
                    prev_row -= 1
                    prev_col = len(self.lines[prev_row]) - 1
                else:
                    break

            if prev_col >= 0 and prev_col < len(self.lines[prev_row]):
                prev_char = self.lines[prev_row][prev_col]
                if not self._is_word_char(prev_char):
                    break

            col = prev_col
            row = prev_row

        # Update cursor
        self.cursor_row = row
        self.cursor_col = col
        # Auto-scroll to keep cursor visible
        self._ensure_cursor_visible()
        return True

    def _word_boundary_right(self) -> bool:
        """Move cursor to start of next word (Ctrl+Right).

        Returns
        -------
        bool
            True if cursor moved
        """
        # Start from current position
        row, col = self.cursor_row, self.cursor_col

        last_row = len(self.lines) - 1
        last_col = len(self.lines[last_row])

        # If at end of document, can't go right
        if row == last_row and col >= last_col:
            return False

        # Skip current word characters
        while row < last_row or col < len(self.lines[row]):
            current_char = self.lines[row][col] if col < len(self.lines[row]) else ""
            if not self._is_word_char(current_char):
                break

            col += 1
            if col >= len(self.lines[row]):
                if row < last_row:
                    row += 1
                    col = 0
                else:
                    break

        # Skip non-word characters
        while row < last_row or col < len(self.lines[row]):
            current_char = self.lines[row][col] if col < len(self.lines[row]) else ""
            if self._is_word_char(current_char):
                break

            col += 1
            if col >= len(self.lines[row]):
                if row < last_row:
                    row += 1
                    col = 0
                else:
                    break

        # Update cursor
        self.cursor_row = row
        self.cursor_col = col
        # Auto-scroll to keep cursor visible
        self._ensure_cursor_visible()
        return True

    def _calculate_total_visual_lines(self) -> int:
        """Calculate total number of visual lines with wrapping applied.

        Returns
        -------
        int
            Total visual line count (same as actual line count if no wrapping)

        Notes
        -----
        Used to update ScrollManager content_size when wrapping is enabled.
        For wrap_mode="none", returns actual line count.
        For wrap_mode="soft" or "hard", counts wrapped segments.
        """
        if self.wrap_mode == "none":
            return len(self.lines)

        # Calculate content width (account for scrollbar)
        content_width = self.width
        if self.show_scrollbar:
            # We need to check if scrollbar will be shown
            # This creates a chicken-and-egg problem, so use conservative estimate
            content_width -= 1

        total_visual_lines = 0
        for line in self.lines:
            # Wrap each line and count segments
            wrapped_segments = wrap_text(line, content_width)
            total_visual_lines += len(wrapped_segments)

        return max(1, total_visual_lines)  # At least one line

    def _actual_to_visual_position(self, row: int, col: int) -> tuple[int, int]:
        """Convert actual position to visual position accounting for wrapping.

        Parameters
        ----------
        row : int
            Actual line index
        col : int
            Actual column within line

        Returns
        -------
        tuple of int
            (visual_row, visual_col) position for rendering

        Notes
        -----
        For wrap_mode="none", returns position unchanged.
        For wrapping modes, calculates visual row by counting wrapped segments
        and determines which segment contains the column position.
        """
        if self.wrap_mode == "none":
            return (row, col)

        # Calculate content width
        content_width = self.width
        if self.show_scrollbar:
            content_width -= 1

        # Count visual lines before the current row
        visual_row = 0
        for i in range(row):
            if i < len(self.lines):
                wrapped_segments = wrap_text(self.lines[i], content_width)
                visual_row += len(wrapped_segments)

        # Now determine which segment of the current line contains col
        if row < len(self.lines):
            current_line = self.lines[row]
            wrapped_segments = wrap_text(current_line, content_width)

            # Find which segment contains the column

            col_position = 0  # Tracks position in visible chars
            for seg_idx, segment in enumerate(wrapped_segments):
                seg_visible_len = visible_length(segment)

                # Calculate visible length to this point
                # Check if col falls within this segment
                if col_position + seg_visible_len >= col:
                    # Cursor is in this segment
                    visual_col = col - col_position
                    return (visual_row + seg_idx, visual_col)

                col_position += seg_visible_len

            # If we get here, cursor is beyond line end
            # Place it at start of next segment (as per design decision)
            # Or at end of last segment if that's the last one
            if wrapped_segments:
                last_seg_len = visible_length(wrapped_segments[-1])
                return (visual_row + len(wrapped_segments) - 1, last_seg_len)
            else:
                return (visual_row, 0)
        else:
            return (visual_row, 0)

    def _visual_to_actual_position(
        self, visual_row: int, visual_col: int
    ) -> tuple[int, int]:
        """Convert visual position to actual position accounting for wrapping.

        Parameters
        ----------
        visual_row : int
            Visual line index (with wrapping)
        visual_col : int
            Visual column within wrapped segment

        Returns
        -------
        tuple of int
            (actual_row, actual_col) position in content

        Notes
        -----
        For wrap_mode="none", returns position unchanged.
        For wrapping modes, unwraps visual position to find actual line
        and column by iterating through wrapped segments.
        Used primarily for mouse click handling.
        """
        if self.wrap_mode == "none":
            return (visual_row, visual_col)

        # Calculate content width
        content_width = self.width
        if self.show_scrollbar:
            content_width -= 1

        # Iterate through lines, tracking visual line count
        current_visual_row = 0

        for actual_row, line in enumerate(self.lines):
            wrapped_segments = wrap_text(line, content_width)

            # Check if visual_row falls within this line's wrapped segments
            if current_visual_row + len(wrapped_segments) > visual_row:
                # The target visual row is within this actual line
                segment_idx = visual_row - current_visual_row

                # Calculate actual column by summing visible lengths of previous segments
                actual_col = 0
                for i in range(segment_idx):
                    actual_col += visible_length(wrapped_segments[i])

                # Add the column within the target segment
                actual_col += min(
                    visual_col, visible_length(wrapped_segments[segment_idx])
                )

                return (actual_row, actual_col)

            current_visual_row += len(wrapped_segments)

        # If we get here, visual_row is beyond content
        # Return position at end of last line
        if self.lines:
            last_row = len(self.lines) - 1
            last_col = len(self.lines[last_row])
            return (last_row, last_col)
        else:
            return (0, 0)

    def _apply_hard_wrap_to_line(self, line_idx: int, width: int) -> None:
        """Apply hard wrapping to a specific line by inserting actual newlines.

        Parameters
        ----------
        line_idx : int
            Index of line to wrap
        width : int
            Maximum width before wrapping

        Notes
        -----
        Modifies self.lines by splitting the line and inserting a newline.
        Adjusts cursor position if cursor is on this line.
        Updates ScrollManager content size.
        Called when wrap_mode="hard" and line exceeds width.
        """
        if line_idx >= len(self.lines):
            return

        line = self.lines[line_idx]
        line_vis_len = visible_length(line)

        if line_vis_len <= width:
            return  # Line doesn't need wrapping

        stripped = strip_ansi(line)

        # Find last wrap boundary within width
        last_boundary_pos = None
        for i in range(min(width, len(stripped))):
            if is_wrap_boundary(stripped[i]):
                last_boundary_pos = i + 1  # Break after boundary char

        # Determine where to split
        if last_boundary_pos is not None and last_boundary_pos < len(stripped):
            # Found a good wrap point
            split_pos = last_boundary_pos
        else:
            # No wrap boundary, force split at width
            split_pos = width

        # Use clip_to_width to get the first part with ANSI codes preserved
        before = clip_to_width(line, split_pos, ellipsis="")

        # Calculate actual position in original string for the split
        # This is tricky with ANSI codes, so we use length of clipped string
        actual_split_pos = len(before)

        # Get remainder after split
        after = line[actual_split_pos:].lstrip()  # Remove leading spaces

        # Update lines
        self.lines[line_idx] = before.rstrip()  # Remove trailing spaces from first part
        self.lines.insert(line_idx + 1, after)

        # Adjust cursor if it's on this line
        if self.cursor_row == line_idx:
            # Determine if cursor should move to next line
            if self.cursor_col >= visible_length(self.lines[line_idx]):
                # Cursor was beyond the split point, move to next line
                self.cursor_row += 1
                self.cursor_col = max(
                    0,
                    self.cursor_col
                    - visible_length(self.lines[line_idx - 1] if line_idx > 0 else ""),
                )
            # Otherwise cursor stays on current line

        elif self.cursor_row > line_idx:
            # Cursor is on a line after this one, increment row index
            self.cursor_row += 1

        # Update ScrollManager
        visual_line_count = self._calculate_total_visual_lines()
        self.scroll_manager.update_content_size(visual_line_count)

        # Ensure cursor stays visible
        self._ensure_cursor_visible()

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        # Handle mouse wheel scrolling
        if event.button == MouseButton.SCROLL_UP:
            # Scroll up 3 lines
            old_position = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-3)
            return old_position != self.scroll_manager.state.scroll_position

        elif event.button == MouseButton.SCROLL_DOWN:
            # Scroll down 3 lines
            old_position = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(3)
            return old_position != self.scroll_manager.state.scroll_position

        # Handle clicks to position cursor
        elif event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            # Convert absolute screen coordinates to textarea-relative coordinates
            # If bounds are set, convert from absolute to relative coordinates
            if self.bounds:
                relative_x = event.x - self.bounds.x
                relative_y = event.y - self.bounds.y

                # Account for borders if present
                if self.border_style is not None:
                    relative_y -= 1  # Top border
                    relative_x -= 1  # Left border
            else:
                # If bounds not set, assume coordinates are already relative
                relative_x = event.x
                relative_y = event.y

            # Validate coordinates are within textarea
            if relative_x < 0 or relative_y < 0:
                return False

            # Convert to content position
            row, col = self._screen_to_content_position(relative_x, relative_y)

            # Update cursor position
            self.cursor_row = row
            self.cursor_col = col

            return True

        return False

    def _screen_to_content_position(
        self, screen_x: int, screen_y: int
    ) -> tuple[int, int]:
        """Convert screen coordinates to content position (row, col).

        Parameters
        ----------
        screen_x : int
            Screen column (relative to textarea)
        screen_y : int
            Screen row (relative to textarea)

        Returns
        -------
        tuple of int
            (row, col) position in content, clamped to valid range

        Notes
        -----
        This accounts for the scroll position and validates the coordinates.
        """
        # Get visible range
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        # Determine content width (account for scrollbar if shown)
        content_width = self.width
        if self.show_scrollbar and self.scroll_manager.state.is_scrollable:
            content_width -= 1

        if self.wrap_mode == "none":
            # No wrapping: simple direct mapping
            # Convert screen Y to line index
            line_idx = visible_start + screen_y

            # Clamp to valid line range
            line_idx = max(0, min(line_idx, len(self.lines) - 1))

            # Convert screen X to column (clamp to line length)
            col = screen_x
            line_length = len(self.lines[line_idx])
            col = max(0, min(col, line_length))

            return (line_idx, col)
        else:
            # Wrapping enabled: map visual position to actual position
            visual_row = visible_start + screen_y
            visual_col = screen_x

            # Use mapping function to get actual position
            actual_row, actual_col = self._visual_to_actual_position(
                visual_row, visual_col
            )

            return (actual_row, actual_col)

    def render_to(self, ctx: "PaintContext") -> None:
        """Render textarea using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method implements cell-based rendering for text areas with:
        - Optional borders with focus indication
        - Multi-line text content
        - Cursor rendering with reverse video
        - Line wrapping (none and soft modes)
        - Scrollbar integration
        - Theme-based styling

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'textarea': Base textarea style
        - 'textarea:focus': When textarea has focus
        - 'textarea.border': Border characters
        - 'textarea.border:focus': Border when focused
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
            # Render with borders
            self._render_to_with_border(ctx, content_style, border_style)
        else:
            # Render without borders
            self._render_to_content(ctx, content_style, 0, 0, self.width, self.height)

    def _render_to_with_border(
        self, ctx: "PaintContext", content_style: "Style", border_style: "Style"
    ) -> None:
        """Render textarea with border using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        content_style : Style
            Style for content text
        border_style : Style
            Style for border characters
        """
        from wijjit.layout.frames import BORDER_CHARS
        from wijjit.terminal.cell import Cell

        # Get border characters
        chars = BORDER_CHARS[self.border_style]
        border_attrs = border_style.to_cell_attrs()

        # Calculate dimensions
        content_width = self.width
        content_height = self.height
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )

        if needs_scrollbar:
            scrollbar_width = 1
        else:
            scrollbar_width = 0

        total_width = content_width + scrollbar_width + 2  # +2 for borders
        total_height = content_height + 2  # +2 for borders

        # Render top border
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
        )
        for x in range(1, total_width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x, ctx.bounds.y, Cell(char=chars["h"], **border_attrs)
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + total_width - 1,
            ctx.bounds.y,
            Cell(char=chars["tr"], **border_attrs),
        )

        # Render content area
        content_ctx = ctx.sub_context(
            1, 1, content_width + scrollbar_width, content_height
        )
        self._render_to_content(
            content_ctx, content_style, 0, 0, content_width, content_height
        )

        # Render side borders
        for y in range(content_height):
            ctx.buffer.set_cell(
                ctx.bounds.x,
                ctx.bounds.y + 1 + y,
                Cell(char=chars["v"], **border_attrs),
            )
            ctx.buffer.set_cell(
                ctx.bounds.x + total_width - 1,
                ctx.bounds.y + 1 + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Render bottom border
        bottom_y = total_height - 1
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + bottom_y,
            Cell(char=chars["bl"], **border_attrs),
        )
        for x in range(1, total_width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + bottom_y,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + total_width - 1,
            ctx.bounds.y + bottom_y,
            Cell(char=chars["br"], **border_attrs),
        )

    def _render_to_content(
        self,
        ctx: "PaintContext",
        content_style: "Style",
        start_x: int,
        start_y: int,
        width: int,
        height: int,
    ) -> None:
        """Render textarea content using cells.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        content_style : Style
            Style for content text
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

        # Determine content width (account for scrollbar)
        needs_scrollbar = (
            self.show_scrollbar and self.scroll_manager.state.is_scrollable
        )
        content_width = width - 1 if needs_scrollbar else width

        # Get cursor visual position for rendering
        cursor_visual_row, cursor_visual_col = self._actual_to_visual_position(
            self.cursor_row, self.cursor_col
        )

        # Get visible range (in visual lines for wrapping modes)
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        # Create cursor style (reverse video)
        cursor_style = Style(
            fg_color=content_style.bg_color or (0, 0, 0),
            bg_color=content_style.fg_color or (255, 255, 255),
            bold=content_style.bold,
            italic=content_style.italic,
        )

        content_attrs = content_style.to_cell_attrs()
        cursor_attrs = cursor_style.to_cell_attrs()

        if self.wrap_mode == "none":
            # Original rendering logic for no wrapping
            visible_lines = self.lines[visible_start:visible_end]

            # Render each visible line
            for i, line in enumerate(visible_lines):
                if i >= height:
                    break

                # Calculate actual line index in content
                actual_line_idx = visible_start + i

                # Determine if cursor is on this line
                show_cursor = self.focused and actual_line_idx == self.cursor_row

                # Clip or pad line to content width
                if len(line) > content_width:
                    display_line = line[:content_width]
                else:
                    display_line = line.ljust(content_width)

                # Write line cells
                for x, char in enumerate(display_line):
                    # Check if this is cursor position
                    if show_cursor and x == self.cursor_col:
                        ctx.buffer.set_cell(
                            ctx.bounds.x + x,
                            ctx.bounds.y + start_y + i,
                            Cell(char=char, **cursor_attrs),
                        )
                    else:
                        ctx.buffer.set_cell(
                            ctx.bounds.x + x,
                            ctx.bounds.y + start_y + i,
                            Cell(char=char, **content_attrs),
                        )

            # Pad remaining lines to height
            for i in range(len(visible_lines), height):
                for x in range(content_width):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + start_y + i,
                        Cell(char=" ", **content_attrs),
                    )

        else:
            # Rendering with wrapping enabled
            visual_line_idx = 0
            rendered_line_count = 0

            # Iterate through actual lines and render wrapped segments
            for _actual_row, line in enumerate(self.lines):
                if rendered_line_count >= height:
                    break

                wrapped_segments = wrap_text(line, content_width)

                for _seg_idx, segment in enumerate(wrapped_segments):
                    # Check if this visual line is in the visible range
                    if visible_start <= visual_line_idx < visible_end:
                        # Determine if cursor is on this visual line
                        show_cursor = (
                            self.focused and visual_line_idx == cursor_visual_row
                        )

                        # Pad segment to content width
                        seg_len = visible_length(segment)
                        if seg_len > content_width:
                            display_line = clip_to_width(
                                segment, content_width, ellipsis=""
                            )
                        else:
                            display_line = segment + " " * (content_width - seg_len)

                        # Write line cells
                        for x, char in enumerate(display_line):
                            # Check if this is cursor position
                            if show_cursor and x == cursor_visual_col:
                                ctx.buffer.set_cell(
                                    ctx.bounds.x + x,
                                    ctx.bounds.y + start_y + rendered_line_count,
                                    Cell(char=char, **cursor_attrs),
                                )
                            else:
                                ctx.buffer.set_cell(
                                    ctx.bounds.x + x,
                                    ctx.bounds.y + start_y + rendered_line_count,
                                    Cell(char=char, **content_attrs),
                                )

                        rendered_line_count += 1
                        if rendered_line_count >= height:
                            break

                    visual_line_idx += 1

            # Pad remaining lines to height
            for i in range(rendered_line_count, height):
                for x in range(content_width):
                    ctx.buffer.set_cell(
                        ctx.bounds.x + x,
                        ctx.bounds.y + start_y + i,
                        Cell(char=" ", **content_attrs),
                    )

        # Add scrollbar if needed
        if needs_scrollbar:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, height
            )

            for i in range(height):
                scrollbar_char = scrollbar_chars[i] if i < len(scrollbar_chars) else " "
                ctx.buffer.set_cell(
                    ctx.bounds.x + content_width,
                    ctx.bounds.y + start_y + i,
                    Cell(char=scrollbar_char, **content_attrs),
                )

    def _render_cursor_in_line(self, line: str, cursor_col: int) -> str:
        """Render a line with cursor at the specified column.

        Parameters
        ----------
        line : str
            Line content to render
        cursor_col : int
            Column position for cursor (0-based)

        Returns
        -------
        str
            Line with cursor rendered using reverse video

        Notes
        -----
        Uses ANSI reverse video escape sequence to highlight cursor position.
        If cursor is beyond line end, shows cursor on space character.
        """
        # Clamp cursor column to valid range (0 to len(line))
        cursor_col = max(0, min(cursor_col, len(line)))

        # Get character at cursor (space if at end of line)
        if cursor_col < len(line):
            cursor_char = line[cursor_col]
        else:
            cursor_char = " "

        # Build line with cursor using reverse video
        # ANSI code: \x1b[7m = reverse video, \x1b[27m = normal video
        before_cursor = line[:cursor_col]
        after_cursor = line[cursor_col + 1 :] if cursor_col < len(line) else ""

        # Apply reverse video to cursor character
        cursor_with_style = f"\x1b[7m{cursor_char}\x1b[27m"

        return before_cursor + cursor_with_style + after_cursor

    def render(self) -> str:
        """Render the text area (LEGACY ANSI rendering).

        Returns
        -------
        str
            Rendered multiline text area

        Notes
        -----
        This is the legacy ANSI string-based rendering method.
        New code should use render_to() for cell-based rendering.
        Kept for backward compatibility.

        Renders visible portion of content based on scroll position.
        Optionally shows scrollbar if content exceeds viewport.
        Shows cursor at current position when focused.
        Applies line wrapping according to wrap_mode setting.
        Renders with box-drawing borders if border_style is set.
        """
        # Get border characters if borders are enabled
        chars = BORDER_CHARS[self.border_style] if self.border_style else None

        # Determine content width (reserve space for scrollbar if shown)
        content_width = self.width
        if self.show_scrollbar and self.scroll_manager.state.is_scrollable:
            content_width -= 1  # Reserve 1 column for scrollbar

        # Get cursor visual position for rendering
        cursor_visual_row, cursor_visual_col = self._actual_to_visual_position(
            self.cursor_row, self.cursor_col
        )

        # Get visible range (in visual lines for wrapping modes)
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        if self.wrap_mode == "none":
            # Original rendering logic for no wrapping
            visible_lines = self.lines[visible_start:visible_end]

            # Pad with empty lines if needed to fill viewport
            while len(visible_lines) < self.height:
                visible_lines.append("")

            # Truncate or pad each line to content width, and render cursor if visible
            rendered_lines = []
            for i, line in enumerate(visible_lines[: self.height]):
                # Calculate actual line index in content
                actual_line_idx = visible_start + i

                if len(line) > content_width:
                    # Truncate long lines
                    display_line = line[:content_width]
                else:
                    # Pad short lines
                    display_line = line.ljust(content_width)

                # Add cursor if this is the cursor line and textarea is focused
                if self.focused and actual_line_idx == self.cursor_row:
                    display_line = self._render_cursor_in_line(
                        display_line, self.cursor_col
                    )

                rendered_lines.append(display_line)

        else:
            # Rendering with wrapping enabled
            rendered_lines = []
            visual_line_idx = 0  # Tracks which visual line we're rendering

            # Iterate through actual lines and render wrapped segments
            for _actual_row, line in enumerate(self.lines):
                wrapped_segments = wrap_text(line, content_width)

                for _seg_idx, segment in enumerate(wrapped_segments):
                    # Check if this visual line is in the visible range
                    if visible_start <= visual_line_idx < visible_end:
                        # Determine visible length for padding
                        seg_len = visible_length(segment)

                        if seg_len > content_width:
                            # Clip to width (shouldn't happen, but safety check)
                            display_line = clip_to_width(
                                segment, content_width, ellipsis=""
                            )
                        else:
                            # Pad to content width
                            display_line = segment + " " * (content_width - seg_len)

                        # Add cursor if this is the cursor's visual line and textarea is focused
                        if self.focused and visual_line_idx == cursor_visual_row:
                            display_line = self._render_cursor_in_line(
                                display_line, cursor_visual_col
                            )

                        rendered_lines.append(display_line)

                    visual_line_idx += 1

                    # Stop if we've filled the viewport
                    if len(rendered_lines) >= self.height:
                        break

                # Stop if we've filled the viewport
                if len(rendered_lines) >= self.height:
                    break

            # Pad with empty lines if needed to fill viewport
            while len(rendered_lines) < self.height:
                empty_line = " " * content_width
                rendered_lines.append(empty_line)

        # Add scrollbar if needed
        if self.show_scrollbar and self.scroll_manager.state.is_scrollable:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state, self.height
            )

            # Append scrollbar to each line
            for i in range(len(rendered_lines)):
                rendered_lines[i] += scrollbar_chars[i]

        # Apply borders if enabled
        if self.border_style is not None and chars is not None:
            # Calculate total width (content + scrollbar if shown)
            total_width = content_width
            if self.show_scrollbar and self.scroll_manager.state.is_scrollable:
                total_width += 1  # Add back scrollbar width

            # Choose border color based on focus
            if self.focused:
                border_color = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}"
                reset = ANSIStyle.RESET
            else:
                border_color = ""
                reset = ""

            # Top border
            top_border = f"{border_color}{chars['tl']}{chars['h'] * total_width}{chars['tr']}{reset}"

            # Wrap each content line with left and right borders
            bordered_lines = []
            for line in rendered_lines:
                bordered_lines.append(
                    f"{border_color}{chars['v']}{reset}{line}{border_color}{chars['v']}{reset}"
                )

            # Bottom border
            bottom_border = f"{border_color}{chars['bl']}{chars['h'] * total_width}{chars['br']}{reset}"

            # Combine all parts
            return f"{top_border}\n" + "\n".join(bordered_lines) + f"\n{bottom_border}"
        else:
            # No borders - plain rendering
            return "\n".join(rendered_lines)
