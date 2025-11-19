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
    supports_unicode,
    visible_length,
    wrap_text,
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
        action_callback: Callable[..., Any] | None = None,
        dismiss_on_action: bool = True,
        max_width: int = 60,
    ) -> None:
        # Convert severity string to enum if needed
        if isinstance(severity, str):
            severity = NotificationSeverity(severity.lower())

        # Calculate notification width first
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

        # Calculate notification height based on wrapped message lines
        # Frame has: border (1) + padding_left (1) + padding_right (1) + border (1) = 4
        # Icon takes some space, so available width for message is:
        # width - 2 (borders) - 2 (padding) - icon_width (2) - 1 (space after icon)
        icon = "\u2713" if supports_unicode() else "[v]"  # Approximate icon width
        icon_width = visible_length(icon)
        padding_horizontal = 2  # padding left + padding right
        available_width_for_message = width - 2 - padding_horizontal - icon_width - 1

        # Wrap message to calculate required lines
        wrapped_lines = wrap_text(message, max(available_width_for_message, 10))
        message_line_count = len(wrapped_lines)

        # Calculate height: border (1) + message lines + border (1)
        # Add 2 lines if we have an action button (spacing + button line)
        height = 2 + message_line_count  # borders + message lines
        if action_label:
            height += 2  # spacing + button line

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
        self.on_dismiss: Callable[..., Any] | None = None

    def _handle_action_click(self, event=None) -> None:
        """Handle action button click.

        Parameters
        ----------
        event : ActionEvent, optional
            Action event from button (unused, for compatibility)
        """
        # Auto-dismiss FIRST if configured (before executing user callback)
        # This ensures the notification is removed before any new notifications
        # are created by the callback, preventing ghost remnants
        if self.dismiss_on_action and self.on_dismiss is not None:
            self.on_dismiss()

        # Execute user callback after dismissal
        if self.action_callback:
            self.action_callback()

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

    def render_to(self, ctx) -> None:
        """Render the notification using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This method uses cell-based rendering with theme styles for severity-based
        coloring. It delegates to Frame's render_to() method for the container
        and handles icon/message/button layout.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'notification.info': Info notification style
        - 'notification.success': Success notification style
        - 'notification.warning': Warning notification style
        - 'notification.error': Error notification style
        - 'frame.border': Border style (inherited from Frame)
        """

        if not self.bounds:
            return

        # Update frame size to match bounds
        self.frame.width = self.bounds.width
        self.frame.height = self.bounds.height

        # Get icon (unicode or ASCII fallback)
        icon = self._get_icon()

        # Resolve style based on severity
        severity_style_map = {
            NotificationSeverity.INFO: "notification.info",
            NotificationSeverity.SUCCESS: "notification.success",
            NotificationSeverity.WARNING: "notification.warning",
            NotificationSeverity.ERROR: "notification.error",
        }
        severity_class = severity_style_map.get(self.severity, "notification.info")

        # Resolve styles for icon and message using cell-based theming
        icon_style = ctx.style_resolver.resolve_style(self, f"{severity_class}.icon")
        message_style = ctx.style_resolver.resolve_style(self, severity_class)

        # Set frame properties (empty content - we'll write directly)
        self.frame.content = []
        self.frame.bounds = self.bounds

        # Delegate to frame's cell-based rendering to draw border and background
        self.frame.render_to(ctx)

        # Now write styled icon and message directly into the frame's content area
        # Frame has border (1) + padding_left (1) = 2 offset
        padding_top, padding_right, padding_bottom, padding_left = (
            self.frame.style.padding
        )
        content_x = 1 + padding_left  # Border + left padding
        content_y = 1 + padding_top  # Border + top padding

        # Write icon with severity-based styling
        ctx.write_text(content_x, content_y, icon, icon_style)

        # Write message next to icon with word-wrapping
        icon_width = visible_length(icon)
        message_x = content_x + icon_width + 1
        # Calculate available width for message
        available_width = (
            self.bounds.width - 2 - padding_left - padding_right - icon_width - 1
        )
        ctx.write_text_wrapped(
            message_x, content_y, self.message, message_style, max_width=available_width
        )

        # Add action button if present
        if self.action_button:
            # Calculate button width based on style
            # Most button styles add 4 characters (e.g., "< label >")
            label_len = visible_length(self.action_button.label)
            button_width = label_len + 4

            # Account for border (2) + padding (2) = 4
            inner_width = self.bounds.width - 2 - padding_left - padding_right
            button_x = max(0, (inner_width - button_width) // 2)

            # Button position (with spacing row above)
            button_y = content_y + 2  # Message + spacing row

            # Set button bounds for both rendering and click handling
            button_bounds = Bounds(
                x=self.bounds.x + 1 + padding_left + button_x,
                y=self.bounds.y + button_y,
                width=button_width,
                height=1,
            )
            self.action_button.set_bounds(button_bounds)

            # Create a sub-context for button rendering with relative coordinates
            button_ctx = ctx.sub_context(
                content_x + button_x, button_y, button_width, 1
            )

            # Render button using cell-based rendering
            self.action_button.render_to(button_ctx)

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
            if self.action_button.bounds.contains(event.x, event.y):
                # Route to button
                return self.action_button.handle_mouse(event)

        # Any other click on notification dismisses it
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            if self.on_dismiss:
                self.on_dismiss()
            return True

        return False
