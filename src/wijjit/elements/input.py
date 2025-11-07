"""Input UI elements for Wijjit applications.

This module provides interactive input elements like TextInput and Button.
"""

from typing import Optional, Callable

from .base import Element, ElementType
from ..terminal.input import Key, Keys
from ..terminal.ansi import ANSIStyle, ANSIColor


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
        id: Optional[str] = None,
        placeholder: str = "",
        value: str = "",
        width: int = 20,
        max_length: Optional[int] = None,
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
        self.on_change: Optional[Callable[[str, str], None]] = (
            None  # (old_value, new_value)
        )
        self.on_action: Optional[Callable[[], None]] = None  # Called on Enter

        # Action ID and bind settings (set by template extension)
        self.action: Optional[str] = None
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
        id: Optional[str] = None,
        on_click: Optional[Callable] = None,
    ):
        super().__init__(id)
        self.element_type = ElementType.BUTTON
        self.focusable = True
        self.label = label
        self.on_click = on_click

        # Action callback (called when button is activated)
        self.on_activate: Optional[Callable[[], None]] = None

        # Action ID (set by template extension)
        self.action: Optional[str] = None

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
