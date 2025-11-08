"""Input UI elements for Wijjit applications.

This module provides interactive input elements like TextInput and Button.
"""

from collections.abc import Callable
from typing import Literal

from ..layout.scroll import ScrollManager, render_vertical_scrollbar
from ..terminal.ansi import ANSIColor, ANSIStyle, clip_to_width, visible_length
from ..terminal.input import Key, Keys
from ..terminal.mouse import MouseButton, MouseEvent, MouseEventType
from .base import Element, ElementType


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
        Display width (default: 20)
    max_length : int, optional
        Maximum input length

    Attributes
    ----------
    value : str
        Current input value
    placeholder : str
        Placeholder text
    cursor_pos : int
        Cursor position in the text
    width : int
        Display width
    max_length : int or None
        Maximum input length
    """

    def __init__(
        self,
        id: str | None = None,
        placeholder: str = "",
        value: str = "",
        width: int = 20,
        max_length: int | None = None,
    ):
        super().__init__(id)
        self.element_type = ElementType.INPUT
        self.focusable = True
        self.value = value
        self.placeholder = placeholder
        self.cursor_pos = len(value)
        self.width = width
        self.max_length = max_length

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
        if self.on_change and old_value != new_value:
            self.on_change(old_value, new_value)

    def render(self) -> str:
        """Render the text input.

        Returns
        -------
        str
            Rendered input field
        """
        display_text = self.value if self.value else self.placeholder

        # Truncate or pad to width
        if len(display_text) > self.width:
            # Show end of text if cursor is there
            if self.cursor_pos >= self.width - 3:
                display_text = "..." + display_text[-(self.width - 3) :]
            else:
                display_text = display_text[: self.width - 3] + "..."
        else:
            display_text = display_text.ljust(self.width)

        # Style based on focus
        if self.focused:
            # Focused: show cursor with proper ANSI isolation
            # Reset at start to clear any previous styling, and at end to prevent bleeding
            result = f"{ANSIStyle.RESET}{ANSIStyle.BOLD}{ANSIColor.CYAN}[{display_text}]{ANSIStyle.RESET}"
        else:
            # Not focused: plain style with explicit reset to prevent inheriting styles
            result = f"{ANSIStyle.RESET}[{display_text}]{ANSIStyle.RESET}"

        return result


class Button(Element):
    """Button element.

    Parameters
    ----------
    id : str, optional
        Element identifier
    label : str
        Button label text
    on_click : callable, optional
        Callback when button is activated

    Attributes
    ----------
    label : str
        Button label
    on_click : callable or None
        Click callback
    """

    def __init__(
        self,
        label: str,
        id: str | None = None,
        on_click: Callable | None = None,
    ):
        super().__init__(id)
        self.element_type = ElementType.BUTTON
        self.focusable = True
        self.label = label
        self.on_click = on_click

        # Action callback (called when button is activated)
        self.on_activate: Callable[[], None] | None = None

        # Action ID (set by template extension)
        self.action: str | None = None

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
        # Activate on Enter or Space
        if key == Keys.ENTER or key == Keys.SPACE:
            self.activate()
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
        # Activate on click or double-click
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            self.activate()
            return True

        return False

    def activate(self) -> None:
        """Activate the button (trigger click callback and action callback)."""
        if self.on_click:
            self.on_click()

        if self.on_activate:
            self.on_activate()

    def render(self) -> str:
        """Render the button.

        Returns
        -------
        str
            Rendered button
        """
        if self.focused:
            # Focused: bold and highlighted with proper ANSI isolation
            # Reset at start to clear any previous styling, and at end to prevent bleeding
            styles = (
                f"{ANSIStyle.RESET}{ANSIStyle.BOLD}{ANSIColor.BG_BLUE}{ANSIColor.WHITE}"
            )
            return f"{styles}< {self.label} >{ANSIStyle.RESET}"
        else:
            # Not focused: plain style with explicit reset to prevent inheriting styles
            return f"{ANSIStyle.RESET}< {self.label} >{ANSIStyle.RESET}"


class TextArea(Element):
    """Multiline text area element with scrolling support.

    Parameters
    ----------
    id : str, optional
        Element identifier
    value : str, optional
        Initial value (multiline text with \\n separators)
    width : int, optional
        Display width in columns (default: 40)
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
        Display width
    height : int
        Display height (viewport)
    wrap_mode : str
        Line wrapping mode
    max_lines : int or None
        Maximum line count
    show_scrollbar : bool
        Whether to show scrollbar
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

        # Set initial value if provided
        if value:
            self.set_value(value)

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

    def _is_wrap_boundary(self, char: str) -> bool:
        """Check if a character is a valid wrap boundary for line wrapping.

        Parameters
        ----------
        char : str
            Character to check

        Returns
        -------
        bool
            True if character is a wrap boundary (space, hyphen, or punctuation)

        Notes
        -----
        Smart word boundary detection for soft wrapping.
        Allows breaking at spaces, hyphens, and punctuation marks.
        """
        if not char:
            return False

        # Spaces are always wrap boundaries
        if char.isspace():
            return True

        # Hyphens allow wrapping after them
        if char == "-":
            return True

        # Common punctuation marks
        # Note: Using ASCII punctuation to avoid unicode issues
        punctuation = ".,;:!?)]}\"'"
        if char in punctuation:
            return True

        return False

    def _wrap_line(self, line: str, width: int) -> list[str]:
        """Wrap a single line into multiple segments based on width.

        Parameters
        ----------
        line : str
            Line to wrap (may contain ANSI escape codes)
        width : int
            Maximum width for each segment

        Returns
        -------
        list of str
            List of wrapped line segments, preserving ANSI codes

        Notes
        -----
        Uses smart word boundary detection (spaces, hyphens, punctuation).
        Falls back to hard break at width if no boundary found.
        Preserves ANSI escape codes using clip_to_width utility.
        Empty lines return a single empty string segment.
        """
        if width <= 0:
            return [""]

        # Empty line returns single empty segment
        if not line:
            return [""]

        # Calculate visible length
        vis_len = visible_length(line)

        # If line fits within width, return as-is
        if vis_len <= width:
            return [line]

        # Line needs wrapping
        segments = []
        remaining = line

        while remaining:
            vis_len = visible_length(remaining)

            if vis_len <= width:
                # Remaining text fits
                segments.append(remaining)
                break

            # Find best wrap point within width
            # We need to find the last wrap boundary before width
            wrap_point = None

            # Scan through the visible characters
            # We need to track both visible position and actual string position
            vis_pos = 0
            actual_pos = 0
            last_boundary_vis = None
            last_boundary_actual = None

            # Strip ANSI to find visible character positions
            from ..terminal.ansi import strip_ansi

            stripped = strip_ansi(remaining)

            # Build mapping of visible positions to actual positions
            # This accounts for ANSI codes in the original string
            for i, char in enumerate(stripped):
                if vis_pos >= width:
                    break

                # Check if this is a wrap boundary
                if self._is_wrap_boundary(char):
                    last_boundary_vis = vis_pos + 1  # Break after the boundary char
                    last_boundary_actual = i + 1

                vis_pos += 1

            # Decide where to break
            if last_boundary_actual is not None and last_boundary_actual < len(
                stripped
            ):
                # Found a wrap boundary within width
                # Use clip_to_width to get the segment with ANSI codes preserved
                segment = clip_to_width(remaining, last_boundary_vis, ellipsis="")
                segments.append(segment)

                # Remove the segment from remaining
                # We need to find the actual position in the original string
                # that corresponds to last_boundary_actual in the stripped version
                char_count = 0
                actual_cut_pos = 0
                for idx, ch in enumerate(remaining):
                    if ch == "\x1b":  # Start of ANSI sequence
                        # Skip ANSI sequence
                        continue
                    if char_count >= last_boundary_actual:
                        actual_cut_pos = idx
                        break
                    # Only count visible characters
                    if ch not in ("\x1b", "[") or char_count > 0:
                        char_count += 1
                        actual_cut_pos = idx + 1

                # Actually, using strip_ansi and finding positions is complex
                # Let's use a simpler approach: clip_to_width already handles ANSI
                # We can calculate how many actual chars to skip by using the segment
                actual_cut_pos = len(segment)

                # Skip past the segment
                remaining = remaining[actual_cut_pos:].lstrip()  # Remove leading spaces

            else:
                # No wrap boundary found, force break at width
                segment = clip_to_width(remaining, width, ellipsis="")
                segments.append(segment)

                # Calculate actual position to cut
                actual_cut_pos = len(segment)
                remaining = remaining[actual_cut_pos:]

        return segments if segments else [""]

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
            wrapped_segments = self._wrap_line(line, content_width)
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
                wrapped_segments = self._wrap_line(self.lines[i], content_width)
                visual_row += len(wrapped_segments)

        # Now determine which segment of the current line contains col
        if row < len(self.lines):
            current_line = self.lines[row]
            wrapped_segments = self._wrap_line(current_line, content_width)

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
            wrapped_segments = self._wrap_line(line, content_width)

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

        # Find wrap point using same logic as soft wrap
        from ..terminal.ansi import strip_ansi

        stripped = strip_ansi(line)

        # Find last wrap boundary within width
        last_boundary_pos = None
        for i in range(min(width, len(stripped))):
            if self._is_wrap_boundary(stripped[i]):
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

                # Account for top border when focused
                # Bounds include the border, so relative_y=0 is the border, relative_y=1 is first content line
                if self.focused:
                    relative_y -= 1
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
        """Render the text area.

        Returns
        -------
        str
            Rendered multiline text area

        Notes
        -----
        Renders visible portion of content based on scroll position.
        Optionally shows scrollbar if content exceeds viewport.
        Shows cursor at current position when focused.
        Applies line wrapping according to wrap_mode setting.
        """
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
            for actual_row, line in enumerate(self.lines):
                wrapped_segments = self._wrap_line(line, content_width)

                for seg_idx, segment in enumerate(wrapped_segments):
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

        # Apply focus styling
        if self.focused:
            # Add border or background for focused state
            border_top = (
                f"{ANSIStyle.BOLD}{ANSIColor.CYAN}{'=' * self.width}{ANSIStyle.RESET}"
            )
            border_bottom = (
                f"{ANSIStyle.BOLD}{ANSIColor.CYAN}{'=' * self.width}{ANSIStyle.RESET}"
            )
            content = "\n".join(rendered_lines)
            return f"{border_top}\n{content}\n{border_bottom}"
        else:
            # Plain rendering
            return "\n".join(rendered_lines)
