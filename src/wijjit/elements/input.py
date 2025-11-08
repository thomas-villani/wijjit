"""Input UI elements for Wijjit applications.

This module provides interactive input elements like TextInput and Button.
"""

from collections.abc import Callable
from typing import Literal

from ..layout.scroll import ScrollManager, render_vertical_scrollbar
from ..terminal.ansi import ANSIColor, ANSIStyle
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
            return f"{ANSIStyle.RESET}{ANSIStyle.BOLD}{ANSIColor.BG_BLUE}{ANSIColor.WHITE}< {self.label} >{ANSIStyle.RESET}"
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
            content_size=1,  # One line initially
            viewport_size=height
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
            self.lines = self.lines[:self.max_lines]

        # Reset cursor to start
        self.cursor_row = 0
        self.cursor_col = 0

        # Update scroll manager
        self.scroll_manager.update_content_size(len(self.lines))
        self.scroll_manager.scroll_to_top()

        # Emit change event
        new_value = self.get_value()
        if self.on_change and old_value != new_value:
            self.on_change(old_value, new_value)

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
            # Check for Ctrl modifier for word boundary
            if "ctrl" in key.modifiers:
                return self._word_boundary_left()
            else:
                return self._move_cursor_left()

        elif key == Keys.RIGHT:
            # Check for Ctrl modifier for word boundary
            if "ctrl" in key.modifiers:
                return self._word_boundary_right()
            else:
                return self._move_cursor_right()

        # Navigation - Home/End
        elif key == Keys.HOME:
            # Check for Ctrl modifier
            if "ctrl" in key.modifiers:
                return self._move_to_document_start()
            else:
                return self._move_to_line_start()

        elif key == Keys.END:
            # Check for Ctrl modifier
            if "ctrl" in key.modifiers:
                return self._move_to_document_end()
            else:
                return self._move_to_line_end()

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
        # Get current line
        current_line = self.lines[self.cursor_row]

        # Insert character at cursor position
        new_line = current_line[:self.cursor_col] + char + current_line[self.cursor_col:]
        self.lines[self.cursor_row] = new_line

        # Advance cursor
        self.cursor_col += 1

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
        before = current_line[:self.cursor_col]
        after = current_line[self.cursor_col:]

        # Update current line and insert new line below
        self.lines[self.cursor_row] = before
        self.lines.insert(self.cursor_row + 1, after)

        # Move cursor to start of new line
        self.cursor_row += 1
        self.cursor_col = 0

        # Update scroll manager
        self.scroll_manager.update_content_size(len(self.lines))

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

            # Update scroll manager
            self.scroll_manager.update_content_size(len(self.lines))

            # Auto-scroll to keep cursor visible
            self._ensure_cursor_visible()
            return True
        else:
            # Delete character before cursor
            current_line = self.lines[self.cursor_row]
            new_line = current_line[:self.cursor_col - 1] + current_line[self.cursor_col:]
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
            # Update scroll manager
            self.scroll_manager.update_content_size(len(self.lines))

            return True
        else:
            # Delete character at cursor
            new_line = current_line[:self.cursor_col] + current_line[self.cursor_col + 1:]
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
        """
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        if self.cursor_row < visible_start:
            # Cursor is above viewport, scroll up to show it
            self.scroll_manager.scroll_to(self.cursor_row)
        elif self.cursor_row >= visible_end:
            # Cursor is below viewport, scroll down to show it
            # Position cursor near bottom of viewport with 1-line margin if possible
            target_scroll = self.cursor_row - self.height + 1
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
        return ch.isalnum() or ch == '_'

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
            current_char = self.lines[row][col] if col < len(self.lines[row]) else ''
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
            current_char = self.lines[row][col] if col < len(self.lines[row]) else ''
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
            current_char = self.lines[row][col] if col < len(self.lines[row]) else ''
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
            # Convert screen coordinates to content position
            # Note: This assumes event.x and event.y are relative to the textarea's bounds
            # The App or parent container should adjust coordinates before calling this
            row, col = self._screen_to_content_position(event.x, event.y)

            # Update cursor position
            self.cursor_row = row
            self.cursor_col = col

            return True

        return False

    def _screen_to_content_position(self, screen_x: int, screen_y: int) -> tuple[int, int]:
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

        # Convert screen Y to line index
        line_idx = visible_start + screen_y

        # Clamp to valid line range
        line_idx = max(0, min(line_idx, len(self.lines) - 1))

        # Determine content width (account for scrollbar if shown)
        content_width = self.width
        if self.show_scrollbar and self.scroll_manager.state.is_scrollable:
            content_width -= 1

        # Convert screen X to column (clamp to line length)
        col = screen_x

        # TODO: Account for line wrapping in Phase 6
        # For now, just clamp to line length
        line_length = len(self.lines[line_idx])
        col = max(0, min(col, line_length))

        return (line_idx, col)

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
        after_cursor = line[cursor_col + 1:] if cursor_col < len(line) else ""

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
        """
        # Get visible range
        visible_start, visible_end = self.scroll_manager.get_visible_range()

        # Determine content width (reserve space for scrollbar if shown)
        content_width = self.width
        if self.show_scrollbar and self.scroll_manager.state.is_scrollable:
            content_width -= 1  # Reserve 1 column for scrollbar

        # Extract visible lines
        visible_lines = self.lines[visible_start:visible_end]

        # Pad with empty lines if needed to fill viewport
        while len(visible_lines) < self.height:
            visible_lines.append("")

        # Truncate or pad each line to content width, and render cursor if visible
        rendered_lines = []
        for i, line in enumerate(visible_lines[:self.height]):
            # Calculate actual line index in content
            actual_line_idx = visible_start + i

            if len(line) > content_width:
                # Truncate long lines (TODO: Apply wrapping in Phase 6)
                display_line = line[:content_width]
            else:
                # Pad short lines
                display_line = line.ljust(content_width)

            # Add cursor if this is the cursor line and textarea is focused
            if self.focused and actual_line_idx == self.cursor_row:
                display_line = self._render_cursor_in_line(display_line, self.cursor_col)

            rendered_lines.append(display_line)

        # Add scrollbar if needed
        if self.show_scrollbar and self.scroll_manager.state.is_scrollable:
            scrollbar_chars = render_vertical_scrollbar(
                self.scroll_manager.state,
                self.height
            )

            # Append scrollbar to each line
            for i in range(len(rendered_lines)):
                rendered_lines[i] += scrollbar_chars[i]

        # Apply focus styling
        if self.focused:
            # Add border or background for focused state
            border_top = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}{'=' * self.width}{ANSIStyle.RESET}"
            border_bottom = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}{'=' * self.width}{ANSIStyle.RESET}"
            content = "\n".join(rendered_lines)
            return f"{border_top}\n{content}\n{border_bottom}"
        else:
            # Plain rendering
            return "\n".join(rendered_lines)
