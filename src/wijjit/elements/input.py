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
                return True

        # Backspace
        elif key == Keys.BACKSPACE:
            if self.cursor_pos > 0:
                self.value = (
                    self.value[: self.cursor_pos - 1] + self.value[self.cursor_pos :]
                )
                self.cursor_pos -= 1
                return True

        # Delete
        elif key == Keys.DELETE:
            if self.cursor_pos < len(self.value):
                self.value = (
                    self.value[: self.cursor_pos] + self.value[self.cursor_pos + 1 :]
                )
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
            # Focused: show cursor
            result = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}[{display_text}]{ANSIStyle.RESET}"
        else:
            result = f"[{display_text}]"

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
        """Activate the button (trigger click callback)."""
        if self.on_click:
            self.on_click()

    def render(self) -> str:
        """Render the button.

        Returns
        -------
        str
            Rendered button
        """
        if self.focused:
            # Focused: bold and highlighted
            return f"{ANSIStyle.BOLD}{ANSIColor.BG_BLUE}{ANSIColor.WHITE}< {self.label} >{ANSIStyle.RESET}"
        else:
            return f"< {self.label} >"
