"""Notification elements for displaying temporary messages.

This module provides notification elements that can display temporary
messages with severity levels, icons, and optional action buttons.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from wijjit.elements.base import OverlayElement
from wijjit.elements.input.button import Button
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import BorderStyle, Frame, FrameStyle
from wijjit.terminal.ansi import (
    ANSIColor,
    colorize,
    supports_unicode,
    visible_length,
)
from wijjit.terminal.mouse import MouseEvent, MouseEventType


class NotificationSeverity(Enum):
    """Severity levels for notifications."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class NotificationElement(OverlayElement):
    """Notification element for temporary messages.

    This element renders as a compact notification box with icon, message,
    and optional action button. Notifications are typically displayed in
    a corner of the screen and can auto-dismiss after a timeout.

    Parameters
    ----------
    message : str
        Notification message text
    id : str, optional
        Unique identifier
    severity : str or NotificationSeverity, optional
        Severity level: "success", "error", "warning", or "info" (default: "info")
    action_label : str, optional
        Label for action button (if None, no button shown)
    action_callback : callable, optional
        Callback when action button is clicked
    dismiss_on_action : bool, optional
        Whether to auto-dismiss when action is clicked (default: True)
    max_width : int, optional
        Maximum notification width (default: 60)

    Attributes
    ----------
    message : str
        Notification message
    severity : NotificationSeverity
        Severity level
    action_label : str or None
        Action button label
    action_callback : callable or None
        Action button callback
    dismiss_on_action : bool
        Auto-dismiss on action flag
    max_width : int
        Maximum width
    frame : Frame
        Frame renderer
    action_button : Button or None
        Action button element (if action_label provided)
    on_dismiss : callable or None
        Callback when notification is dismissed
    """

    def __init__(
        self,
        message: str,
        id: str | None = None,
        severity: str | NotificationSeverity = NotificationSeverity.INFO,
        action_label: str | None = None,
        action_callback: Callable | None = None,
        dismiss_on_action: bool = True,
        max_width: int = 60,
    ):
        # Convert severity string to enum if needed
        if isinstance(severity, str):
            severity = NotificationSeverity(severity.lower())

        # Calculate notification dimensions
        # Height: 3 lines minimum (top border + content + bottom border)
        # Add 2 lines if we have an action button (spacing + button line)
        height = 5 if action_label else 3

        # Width: message length + icon + padding + borders
        # Icon (2) + space (1) + message + padding (4) + borders (2)
        message_len = visible_length(message)
        content_width = min(message_len + 7, max_width - 2)  # -2 for borders
        width = content_width + 2  # +2 for borders

        # If we have an action button, ensure minimum width
        if action_label:
            button_width = visible_length(action_label) + 4  # "< label >"
            min_width_for_button = button_width + 10  # Button + some padding
            width = max(width, min_width_for_button)

        super().__init__(id=id, width=width, height=height, centered=False)

        self.message = message
        self.severity = severity
        self.action_label = action_label
        self.action_callback = action_callback
        self.dismiss_on_action = dismiss_on_action
        self.max_width = max_width

        # Create frame for rendering with rounded borders
        style = FrameStyle(
            border=BorderStyle.ROUNDED,
            padding=(0, 1, 0, 1),  # Horizontal padding only
        )
        self.frame = Frame(width=width, height=height, style=style)

        # Create action button if provided
        self.action_button: Button | None = None
        if action_label:
            self.action_button = Button(
                label=action_label,
                id=f"{id}_action" if id else None,
                on_click=self._handle_action_click,
            )
            # Button should start focused since it's the only interactive element
            self.action_button.focused = True
            self.add_child(self.action_button)

        # Dismiss callback (set externally by notification manager)
        self.on_dismiss: Callable | None = None

    def _handle_action_click(self) -> None:
        """Handle action button click."""
        # Execute user callback if provided
        if self.action_callback:
            self.action_callback()

        # Auto-dismiss if configured
        if self.dismiss_on_action and self.on_dismiss is not None:
            self.on_dismiss()

    def _get_icon(self) -> str:
        """Get icon for the notification based on severity.

        Returns
        -------
        str
            Icon character (unicode or ASCII fallback)
        """
        use_unicode = supports_unicode()

        if self.severity == NotificationSeverity.SUCCESS:
            return "[SUCCESS]" if not use_unicode else "\u2713"  # Checkmark
        elif self.severity == NotificationSeverity.ERROR:
            return "[x]" if not use_unicode else "\u2717"  # X mark
        elif self.severity == NotificationSeverity.WARNING:
            return "[!]" if not use_unicode else "\u26a0"  # Warning sign
        else:  # INFO
            return "(i)" if not use_unicode else "\u2139 "  # Info symbol

    def _get_color(self) -> str:
        """Get color for the notification based on severity.

        Returns
        -------
        str
            ANSI color code
        """
        if self.severity == NotificationSeverity.SUCCESS:
            return ANSIColor.GREEN
        elif self.severity == NotificationSeverity.ERROR:
            return ANSIColor.RED
        elif self.severity == NotificationSeverity.WARNING:
            return ANSIColor.YELLOW
        else:  # INFO
            return ANSIColor.CYAN

    def render(self) -> str:
        """Render the notification.

        Returns
        -------
        str
            Rendered notification as multi-line string
        """
        if not self.bounds:
            return ""

        # Update frame size to match bounds
        self.frame.width = self.bounds.width
        self.frame.height = self.bounds.height

        # Get icon and color
        icon = self._get_icon()
        color = self._get_color()

        # Format the message line with icon
        icon_colored = colorize(icon, color, bold=True)
        message_line = f"{icon_colored} {self.message}"

        # Build content lines
        content_lines = [message_line]

        # Add action button if present
        if self.action_button:
            # Set button bounds for rendering (center it horizontally)
            button_text = self.action_button.render()
            button_width = visible_length(button_text)
            # Account for border (2) + padding (2) = 4
            inner_width = self.bounds.width - 4
            button_x = max(0, (inner_width - button_width) // 2)

            # Add spacing and button
            content_lines.append("")  # Empty line for spacing
            content_lines.append(" " * button_x + button_text)

            # Update button bounds for click handling
            if self.bounds:
                button_bounds = Bounds(
                    x=self.bounds.x + 2 + button_x,  # +2 for border + padding
                    y=self.bounds.y
                    + 3,  # Border + message + spacing = line 4 (0-indexed: 3)
                    width=button_width,
                    height=1,
                )
                self.action_button.set_bounds(button_bounds)

        # Set frame properties
        self.frame.content = content_lines
        self.frame.bounds = self.bounds

        # Render frame
        return self.frame.render()

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse events on notification.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        # If we have an action button, check if click is on button
        if self.action_button and self.action_button.bounds:
            if self.action_button.bounds.contains_point(event.x, event.y):
                # Route to button
                return self.action_button.handle_mouse(event)

        # Any other click on notification dismisses it
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            if self.on_dismiss:
                self.on_dismiss()
            return True

        return False
