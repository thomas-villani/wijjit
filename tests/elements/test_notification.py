"""Tests for NotificationElement.

This module tests the NotificationElement including:
- Initialization with different severity levels
- Icon selection and unicode/ASCII fallback
- Color mapping based on severity
- Action button rendering
- Frame rendering and bounds calculation
"""

from unittest.mock import MagicMock

from wijjit.elements.display.notification import (
    NotificationElement,
    NotificationSeverity,
)
from wijjit.layout.bounds import Bounds
from wijjit.terminal.ansi import ANSIColor, strip_ansi


class TestNotificationElement:
    """Test suite for NotificationElement."""

    def test_initialization_defaults(self):
        """Test NotificationElement initialization with default values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notification = NotificationElement(message="Test message")

        assert notification.message == "Test message"
        assert notification.severity == NotificationSeverity.INFO
        assert notification.action_label is None
        assert notification.action_callback is None
        assert notification.dismiss_on_action is True
        assert notification.max_width == 60
        assert notification.focusable is False
        assert notification.centered is False

    def test_initialization_custom_values(self):
        """Test NotificationElement initialization with custom values.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        callback = MagicMock()
        notification = NotificationElement(
            message="Custom message",
            id="test_notif",
            severity="error",
            action_label="Retry",
            action_callback=callback,
            dismiss_on_action=False,
            max_width=80,
        )

        assert notification.message == "Custom message"
        assert notification.id == "test_notif"
        assert notification.severity == NotificationSeverity.ERROR
        assert notification.action_label == "Retry"
        assert notification.action_callback == callback
        assert notification.dismiss_on_action is False
        assert notification.max_width == 80

    def test_severity_enum_conversion(self):
        """Test severity string to enum conversion.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notif_success = NotificationElement("Test", severity="success")
        assert notif_success.severity == NotificationSeverity.SUCCESS

        notif_error = NotificationElement("Test", severity="error")
        assert notif_error.severity == NotificationSeverity.ERROR

        notif_warning = NotificationElement("Test", severity="warning")
        assert notif_warning.severity == NotificationSeverity.WARNING

        notif_info = NotificationElement("Test", severity="info")
        assert notif_info.severity == NotificationSeverity.INFO

    def test_get_color_for_severity(self):
        """Test color mapping for different severity levels.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notif_success = NotificationElement("Test", severity="success")
        assert notif_success._get_color() == ANSIColor.GREEN

        notif_error = NotificationElement("Test", severity="error")
        assert notif_error._get_color() == ANSIColor.RED

        notif_warning = NotificationElement("Test", severity="warning")
        assert notif_warning._get_color() == ANSIColor.YELLOW

        notif_info = NotificationElement("Test", severity="info")
        assert notif_info._get_color() == ANSIColor.CYAN

    def test_get_icon(self):
        """Test icon selection for different severity levels.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # Icons may be unicode or ASCII depending on terminal support
        notif_success = NotificationElement("Test", severity="success")
        icon_success = notif_success._get_icon()
        assert icon_success in ("[SUCCESS]", "\u2713")  # ASCII or unicode checkmark

        notif_error = NotificationElement("Test", severity="error")
        icon_error = notif_error._get_icon()
        assert icon_error in ("[x]", "\u2717")  # ASCII or unicode X mark

        notif_warning = NotificationElement("Test", severity="warning")
        icon_warning = notif_warning._get_icon()
        assert icon_warning in ("[!]", "\u26a0")  # ASCII or unicode warning

        notif_info = NotificationElement("Test", severity="info")
        icon_info = notif_info._get_icon()
        assert icon_info in (
            "(i)",
            "\u2139 ",
        )  # ASCII or unicode info (note space after unicode)

    def test_render_without_bounds(self):
        """Test render returns empty string when no bounds set.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notification = NotificationElement("Test message")
        output = notification.render()
        assert output == ""

    def test_render_with_bounds(self):
        """Test render produces output with bounds set.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notification = NotificationElement("Test message", severity="info")
        notification.set_bounds(Bounds(x=10, y=5, width=30, height=3))

        output = notification.render()

        # Should produce non-empty output
        assert output != ""

        # Should contain the message
        assert "Test message" in strip_ansi(output)

    def test_render_includes_icon(self):
        """Test render includes severity icon.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notification = NotificationElement("Hello", severity="success")
        notification.set_bounds(Bounds(x=0, y=0, width=30, height=3))

        output = notification.render()
        stripped = strip_ansi(output)

        # Should include icon (v or unicode checkmark)
        assert "v" in stripped or "\u2713" in stripped

    def test_render_with_action_button(self):
        """Test render includes action button when provided.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        callback = MagicMock()
        notification = NotificationElement(
            "Test",
            severity="error",
            action_label="Retry",
            action_callback=callback,
        )
        notification.set_bounds(Bounds(x=0, y=0, width=40, height=5))

        output = notification.render()

        # Should include button label
        assert "Retry" in strip_ansi(output)

        # Should have action button as child
        assert notification.action_button is not None
        assert notification.action_button.label == "Retry"

    def test_action_button_click_executes_callback(self):
        """Test action button click executes callback.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        callback = MagicMock()
        notification = NotificationElement(
            "Test",
            action_label="Action",
            action_callback=callback,
        )

        # Simulate button click
        notification._handle_action_click()

        # Callback should be called
        callback.assert_called_once()

    def test_action_button_dismiss_on_action(self):
        """Test action button triggers dismiss when dismiss_on_action=True.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        callback = MagicMock()
        dismiss_callback = MagicMock()

        notification = NotificationElement(
            "Test",
            action_label="Action",
            action_callback=callback,
            dismiss_on_action=True,
        )
        notification.on_dismiss = dismiss_callback

        # Simulate button click
        notification._handle_action_click()

        # Both callbacks should be called
        callback.assert_called_once()
        dismiss_callback.assert_called_once()

    def test_action_button_no_dismiss(self):
        """Test action button does not dismiss when dismiss_on_action=False.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        callback = MagicMock()
        dismiss_callback = MagicMock()

        notification = NotificationElement(
            "Test",
            action_label="Action",
            action_callback=callback,
            dismiss_on_action=False,
        )
        notification.on_dismiss = dismiss_callback

        # Simulate button click
        notification._handle_action_click()

        # Only action callback should be called
        callback.assert_called_once()
        dismiss_callback.assert_not_called()

    def test_notification_sizing_without_action(self):
        """Test notification dimensions without action button.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notification = NotificationElement("Short", severity="info")

        # Height should be 3 (border + content + border)
        assert notification.height == 3

        # Width should accommodate message + icon + padding + borders
        assert notification.width > 10

    def test_notification_sizing_with_action(self):
        """Test notification dimensions with action button.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        notification = NotificationElement(
            "Test",
            action_label="Action",
            action_callback=lambda: None,
        )

        # Height should be 5 (border + content + spacing + button line + border)
        assert notification.height == 5

        # Width should be sufficient for button
        assert notification.width >= 20

    def test_long_message_respects_max_width(self):
        """Test long messages are constrained by max_width.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        long_message = (
            "This is a very long notification message that should be constrained"
        )
        notification = NotificationElement(long_message, max_width=40)

        # Width should not exceed max_width
        assert notification.width <= 40
