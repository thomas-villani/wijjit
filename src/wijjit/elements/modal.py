"""Pre-built modal dialog elements for common use cases.

This module provides high-level dialog classes for common interactions like
confirmations, alerts, and text input. These classes use the underlying
ModalElement and automatically handle button creation and callbacks.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from wijjit.core.events import ActionEvent
from wijjit.elements.base import TextElement
from wijjit.elements.display.modal import ModalElement
from wijjit.elements.input.button import Button
from wijjit.elements.input.text import TextInput
from wijjit.terminal.ansi import wrap_text


class AlertSeverity(Enum):
    """Severity levels for alert dialogs."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ConfirmDialog(ModalElement):
    """Confirmation dialog with confirm and cancel buttons.

    This dialog presents a message with two buttons (Confirm/Cancel) and
    executes the appropriate callback based on user selection. The dialog
    automatically closes after a button is clicked.

    Parameters
    ----------
    title : str, optional
        Dialog title (default: "Confirm")
    message : str
        Confirmation message to display
    on_confirm : callable, optional
        Callback function called when Confirm button is clicked
    on_cancel : callable, optional
        Callback function called when Cancel button is clicked
    confirm_label : str, optional
        Label for confirm button (default: "Confirm")
    cancel_label : str, optional
        Label for cancel button (default: "Cancel")
    width : int, optional
        Dialog width in characters (default: 50)
    height : int, optional
        Dialog height in lines (default: 14)
    border : str, optional
        Border style: "single", "double", or "rounded" (default: "single")

    Attributes
    ----------
    message : str
        Dialog message
    confirm_button : Button
        Confirm button element
    cancel_button : Button
        Cancel button element
    close_callback : callable or None
        Callback to close the dialog (set externally by app)
    """

    def __init__(
        self,
        message: str,
        on_confirm: Callable[[], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        title: str = "Confirm",
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        width: int | None = 50,
        height: int | None = None,
        border: str = "single",
    ):
        # Auto-size if width/height not provided
        if width is None:
            width = 50  # Default width

        if height is None:
            # Calculate height based on message content
            # Content width = width - borders (2) - padding (4)
            content_width = width - 6
            wrapped_lines = wrap_text(message, content_width)
            num_text_lines = len(wrapped_lines)

            # Height = top border (1) + top padding (1) + text lines +
            #          spacing (1) + button (1) + bottom padding (1) + bottom border (1)
            height = 1 + 1 + num_text_lines + 1 + 1 + 1 + 1

            # Apply min/max constraints
            height = max(10, min(height, 30))

        super().__init__(
            title=title,
            width=width,
            height=height,
            border=border,
            padding=(1, 2, 1, 2),
        )

        self.message = message
        self.close_callback: Callable[[], None] | None = None

        # Create message text element
        message_element = TextElement(text=message)
        self.add_child(message_element)

        # Create buttons with auto-close wrappers
        self.confirm_button = Button(
            label=confirm_label,
            id="confirm_btn",
            on_click=self._wrap_callback(on_confirm),
        )
        self.confirm_button.focusable = True

        self.cancel_button = Button(
            label=cancel_label,
            id="cancel_btn",
            on_click=self._wrap_callback(on_cancel),
        )
        self.cancel_button.focusable = True

        # Add buttons to children
        self.add_child(self.confirm_button)
        self.add_child(self.cancel_button)

    def _wrap_callback(
        self, callback: Callable[[], None] | None
    ) -> Callable[[ActionEvent], None]:
        """Wrap user callback to auto-close dialog after execution.

        Parameters
        ----------
        callback : callable or None
            User callback to wrap

        Returns
        -------
        callable
            Wrapped callback that receives ActionEvent, closes dialog, then executes user callback
        """

        def wrapped(event: ActionEvent):
            # Close dialog first
            if self.close_callback:
                self.close_callback()

            # Then execute user callback
            if callback:
                callback()

        return wrapped


class AlertDialog(ModalElement):
    """Alert dialog with a message and OK button.

    This dialog presents a message with a single OK button and executes
    the callback when the button is clicked. The dialog automatically
    closes after the button is clicked.

    Parameters
    ----------
    title : str, optional
        Dialog title (default: "Alert")
    message : str
        Alert message to display
    on_ok : callable, optional
        Callback function called when OK button is clicked
    ok_label : str, optional
        Label for OK button (default: "OK")
    severity : str or AlertSeverity, optional
        Alert severity level: "success", "error", "warning", or "info"
        Affects border color styling (default: None, no color styling)
    width : int, optional
        Dialog width in characters (default: 50, or auto-sized if None)
    height : int, optional
        Dialog height in lines (default: auto-sized based on content)
    border : str, optional
        Border style: "single", "double", or "rounded" (default: "single")

    Attributes
    ----------
    message : str
        Dialog message
    severity : AlertSeverity or None
        Alert severity level
    ok_button : Button
        OK button element
    close_callback : callable or None
        Callback to close the dialog (set externally by app)
    """

    def __init__(
        self,
        message: str,
        on_ok: Callable[[], None] | None = None,
        title: str = "Alert",
        ok_label: str = "OK",
        severity: str | AlertSeverity | None = None,
        width: int | None = 50,
        height: int | None = None,
        border: str = "single",
    ):
        # Convert severity string to enum if needed
        if isinstance(severity, str):
            severity = AlertSeverity(severity.lower())
        self.severity = severity

        # Auto-size if width/height not provided
        if width is None:
            width = 50  # Default width

        if height is None:
            # Calculate height based on message content
            # Content width = width - borders (2) - padding (4)
            content_width = width - 6
            wrapped_lines = wrap_text(message, content_width)
            num_text_lines = len(wrapped_lines)

            # Height = top border (1) + top padding (1) + text lines +
            #          spacing (1) + button (1) + bottom padding (1) + bottom border (1)
            height = 1 + 1 + num_text_lines + 1 + 1 + 1 + 1

            # Apply min/max constraints
            height = max(10, min(height, 30))

        super().__init__(
            title=title,
            width=width,
            height=height,
            border=border,
            padding=(1, 2, 1, 2),
        )

        self.message = message
        self.close_callback: Callable[[], None] | None = None

        # Create message text element
        message_element = TextElement(text=message)
        self.add_child(message_element)

        # Create OK button with auto-close wrapper
        self.ok_button = Button(
            label=ok_label,
            id="ok_btn",
            on_click=self._wrap_callback(on_ok),
        )
        self.ok_button.focusable = True

        # Add button to children
        self.add_child(self.ok_button)

    def render_to(self, ctx) -> None:
        """Render the alert dialog with severity-based border styling.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method uses theme style classes for severity-based coloring:
        - 'alert.success.border': Success alert border style (default: green)
        - 'alert.error.border': Error alert border style (default: red)
        - 'alert.warning.border': Warning alert border style (default: yellow)
        - 'alert.info.border': Info alert border style (default: blue)
        """
        # If severity is set, use custom border style class
        if self.severity:
            # Map severity to style class
            severity_style_map = {
                AlertSeverity.SUCCESS: "alert.success.border",
                AlertSeverity.ERROR: "alert.error.border",
                AlertSeverity.WARNING: "alert.warning.border",
                AlertSeverity.INFO: "alert.info.border",
            }
            border_style_class = severity_style_map.get(self.severity)

            # Save original style resolver method
            original_resolve = ctx.style_resolver.resolve_style

            # Create a wrapper that uses custom border style class
            def custom_resolve(element, style_class: str):
                # Check if this is a frame.border request
                if (
                    style_class in ("frame.border", "frame.border:focus")
                    and border_style_class
                ):
                    # Try to resolve severity-specific border style
                    severity_style = ctx.style_resolver.resolve_style_by_class(
                        border_style_class
                    )
                    if severity_style and (
                        severity_style.fg_color or severity_style.bg_color
                    ):
                        # Use severity style if it has colors defined
                        return severity_style
                    # Otherwise fall back to default frame.border
                return original_resolve(element, style_class)

            # Temporarily replace the resolver
            ctx.style_resolver.resolve_style = custom_resolve

            # Call parent render_to
            super().render_to(ctx)

            # Restore original resolver
            ctx.style_resolver.resolve_style = original_resolve
        else:
            # No severity, use default rendering
            super().render_to(ctx)

    def _wrap_callback(
        self, callback: Callable[[], None] | None
    ) -> Callable[[ActionEvent], None]:
        """Wrap user callback to auto-close dialog after execution.

        Parameters
        ----------
        callback : callable or None
            User callback to wrap

        Returns
        -------
        callable
            Wrapped callback that receives ActionEvent, closes dialog, then executes user callback
        """

        def wrapped(event: ActionEvent):
            # Close dialog first
            if self.close_callback:
                self.close_callback()

            # Then execute user callback
            if callback:
                callback()

        return wrapped


class TextInputDialog(ModalElement):
    """Text input dialog with prompt, input field, and submit/cancel buttons.

    This dialog presents a prompt with a text input field and two buttons
    (Submit/Cancel). When Submit is clicked, the on_submit callback receives
    the input value. The dialog automatically closes after a button is clicked.

    Parameters
    ----------
    title : str, optional
        Dialog title (default: "Input")
    prompt : str
        Prompt message to display above the input field
    initial_value : str, optional
        Initial value for the text input (default: "")
    on_submit : callable, optional
        Callback function called when Submit is clicked. Receives the input
        value as a string argument: on_submit(value: str)
    on_cancel : callable, optional
        Callback function called when Cancel button is clicked
    placeholder : str, optional
        Placeholder text for the input field (default: "")
    submit_label : str, optional
        Label for submit button (default: "Submit")
    cancel_label : str, optional
        Label for cancel button (default: "Cancel")
    width : int, optional
        Dialog width in characters (default: 50)
    height : int, optional
        Dialog height in lines (default: 16)
    border : str, optional
        Border style: "single", "double", or "rounded" (default: "single")
    input_width : int, optional
        Width of the text input field (default: 30)

    Attributes
    ----------
    prompt : str
        Dialog prompt message
    text_input : TextInput
        Text input element
    submit_button : Button
        Submit button element
    cancel_button : Button
        Cancel button element
    close_callback : callable or None
        Callback to close the dialog (set externally by app)
    """

    def __init__(
        self,
        prompt: str,
        initial_value: str = "",
        on_submit: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        title: str = "Input",
        placeholder: str = "",
        submit_label: str = "Submit",
        cancel_label: str = "Cancel",
        width: int = 50,
        height: int = 16,
        border: str = "single",
        input_width: int = 30,
    ):
        super().__init__(
            title=title,
            width=width,
            height=height,
            border=border,
            padding=(1, 2, 1, 2),
        )

        self.prompt = prompt
        self.close_callback: Callable[[], None] | None = None

        # Create prompt text element
        prompt_element = TextElement(text=prompt)
        self.add_child(prompt_element)

        # Create text input
        self.text_input = TextInput(
            id="input_field",
            value=initial_value,
            placeholder=placeholder,
            width=input_width,
        )
        self.text_input.focusable = True

        # Wire up Enter key to submit
        original_on_action = self.text_input.on_action

        def submit_on_enter():
            self._handle_submit(on_submit)
            if original_on_action:
                original_on_action()

        self.text_input.on_action = submit_on_enter

        self.add_child(self.text_input)

        # Create buttons with auto-close wrappers
        self.submit_button = Button(
            label=submit_label,
            id="submit_btn",
            on_click=lambda event: self._handle_submit(on_submit),
        )
        self.submit_button.focusable = True

        self.cancel_button = Button(
            label=cancel_label,
            id="cancel_btn",
            on_click=self._wrap_callback(on_cancel),
        )
        self.cancel_button.focusable = True

        # Add buttons to children
        self.add_child(self.submit_button)
        self.add_child(self.cancel_button)

    def _handle_submit(self, callback: Callable[[str], None] | None) -> None:
        """Handle submit action by closing dialog and calling callback with value.

        Parameters
        ----------
        callback : callable or None
            User callback that receives input value
        """
        # Close dialog first
        if self.close_callback:
            self.close_callback()

        # Then execute user callback with the input value
        if callback:
            callback(self.text_input.value)

    def _wrap_callback(
        self, callback: Callable[[], None] | None
    ) -> Callable[[ActionEvent], None]:
        """Wrap user callback to auto-close dialog after execution.

        Parameters
        ----------
        callback : callable or None
            User callback to wrap

        Returns
        -------
        callable
            Wrapped callback that receives ActionEvent, closes dialog, then executes user callback
        """

        def wrapped(event: ActionEvent):
            # Close dialog first
            if self.close_callback:
                self.close_callback()

            # Then execute user callback
            if callback:
                callback()

        return wrapped
