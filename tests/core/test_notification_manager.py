"""Tests for NotificationManager.

This module tests the NotificationManager including:
- Adding and removing notifications
- Stacking and positioning
- Auto-dismissal with timeouts
- Terminal resize handling
"""

import time
from unittest.mock import MagicMock

from wijjit.core.notification_manager import ActiveNotification, NotificationManager
from wijjit.core.overlay import OverlayManager
from wijjit.elements.display.notification import NotificationElement


class TestActiveNotification:
    """Test suite for ActiveNotification class."""

    def test_initialization(self):
        """Test ActiveNotification initialization.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        element = NotificationElement("Test")
        overlay = MagicMock()
        created_at = time.time()

        notif = ActiveNotification(
            id="test-id",
            element=element,
            overlay=overlay,
            created_at=created_at,
            duration=3.0,
        )

        assert notif.id == "test-id"
        assert notif.element == element
        assert notif.overlay == overlay
        assert notif.created_at == created_at
        assert notif.duration == 3.0
        assert notif.expires_at == created_at + 3.0

    def test_initialization_no_duration(self):
        """Test ActiveNotification without duration (no expiry).

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        element = NotificationElement("Test")
        overlay = MagicMock()

        notif = ActiveNotification(
            id="test-id",
            element=element,
            overlay=overlay,
            created_at=time.time(),
            duration=None,
        )

        assert notif.duration is None
        assert notif.expires_at is None

    def test_is_expired_false(self):
        """Test is_expired returns False for non-expired notification.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        element = NotificationElement("Test")
        overlay = MagicMock()

        notif = ActiveNotification(
            id="test-id",
            element=element,
            overlay=overlay,
            created_at=time.time(),
            duration=10.0,  # 10 seconds in future
        )

        assert notif.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired notification.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        element = NotificationElement("Test")
        overlay = MagicMock()

        # Create notification that expired 1 second ago
        notif = ActiveNotification(
            id="test-id",
            element=element,
            overlay=overlay,
            created_at=time.time() - 4.0,
            duration=3.0,
        )

        assert notif.is_expired() is True

    def test_is_expired_no_expiry(self):
        """Test is_expired returns False when no duration set.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        element = NotificationElement("Test")
        overlay = MagicMock()

        notif = ActiveNotification(
            id="test-id",
            element=element,
            overlay=overlay,
            created_at=time.time(),
            duration=None,
        )

        assert notif.is_expired() is False


class TestNotificationManager:
    """Test suite for NotificationManager class."""

    def test_initialization(self):
        """Test NotificationManager initialization.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)

        manager = NotificationManager(
            overlay_manager=overlay_manager,
            terminal_width=80,
            terminal_height=24,
            position="top-right",
            spacing=1,
            margin=2,
        )

        assert manager.overlay_manager == overlay_manager
        assert manager.terminal_width == 80
        assert manager.terminal_height == 24
        assert manager.position == "top-right"
        assert manager.spacing == 1
        assert manager.margin == 2
        assert manager.notifications == []

    def test_add_notification(self):
        """Test adding a notification.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24)

        element = NotificationElement("Test message")
        notification_id = manager.add(element, duration=3.0)

        # Should return a notification ID
        assert isinstance(notification_id, str)
        assert len(notification_id) > 0

        # Should add to notifications list
        assert len(manager.notifications) == 1
        assert manager.notifications[0].id == notification_id
        assert manager.notifications[0].element == element

        # Should push to overlay manager
        overlay_manager.push.assert_called_once()

    def test_add_multiple_notifications(self):
        """Test adding multiple notifications stacks them.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24)

        # Add three notifications
        id1 = manager.add(NotificationElement("First"), duration=3.0)
        id2 = manager.add(NotificationElement("Second"), duration=3.0)
        id3 = manager.add(NotificationElement("Third"), duration=3.0)

        # Should have 3 notifications
        assert len(manager.notifications) == 3

        # Should be in order added (oldest first)
        assert manager.notifications[0].id == id1
        assert manager.notifications[1].id == id2
        assert manager.notifications[2].id == id3

    def test_remove_notification(self):
        """Test removing a notification.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        overlay_manager.overlays = []  # Add overlays list for new check
        manager = NotificationManager(overlay_manager, 80, 24)

        element = NotificationElement("Test")
        notification_id = manager.add(element, duration=3.0)

        # Simulate the overlay being added to the manager
        overlay_manager.overlays.append(manager.notifications[0].overlay)

        # Remove the notification
        result = manager.remove(notification_id)

        assert result is True
        assert len(manager.notifications) == 0

        # Should pop from overlay manager
        overlay_manager.pop.assert_called_once()

    def test_remove_nonexistent_notification(self):
        """Test removing non-existent notification returns False.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24)

        result = manager.remove("nonexistent-id")

        assert result is False

    def test_check_expired_removes_expired(self):
        """Test check_expired removes expired notifications.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        overlay_manager.overlays = []  # Add overlays list for overlay check
        manager = NotificationManager(overlay_manager, 80, 24)

        # Add notification with very short duration
        element = NotificationElement("Test")
        notification_id = manager.add(element, duration=0.01)  # 10ms

        # Simulate the overlay being added to the manager
        overlay_manager.overlays.append(manager.notifications[0].overlay)

        # Wait for it to expire
        time.sleep(0.02)

        # Check expired
        had_expired = manager.check_expired()

        # Should have removed the expired notification
        assert had_expired is True
        assert len(manager.notifications) == 0

    def test_check_expired_keeps_non_expired(self):
        """Test check_expired keeps non-expired notifications.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24)

        # Add notification with long duration
        element = NotificationElement("Test")
        notification_id = manager.add(element, duration=10.0)

        # Check expired immediately
        had_expired = manager.check_expired()

        # Should not have removed it
        assert had_expired is False
        assert len(manager.notifications) == 1

    def test_check_expired_keeps_persistent(self):
        """Test check_expired keeps notifications with no duration.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24)

        # Add persistent notification (no duration)
        element = NotificationElement("Test")
        notification_id = manager.add(element, duration=None)

        # Check expired
        had_expired = manager.check_expired()

        # Should not have removed it
        assert had_expired is False
        assert len(manager.notifications) == 1

    def test_clear_all_notifications(self):
        """Test clear removes all notifications.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24)

        # Add multiple notifications
        manager.add(NotificationElement("First"), duration=3.0)
        manager.add(NotificationElement("Second"), duration=3.0)
        manager.add(NotificationElement("Third"), duration=3.0)

        # Clear all
        count = manager.clear()

        assert count == 3
        assert len(manager.notifications) == 0

    def test_update_terminal_size(self):
        """Test update_terminal_size updates dimensions.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24)

        manager.update_terminal_size(100, 30)

        assert manager.terminal_width == 100
        assert manager.terminal_height == 30

    def test_calculate_position_top_right(self):
        """Test position calculation for top-right placement.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(
            overlay_manager, terminal_width=80, terminal_height=24, position="top-right"
        )

        element = NotificationElement("Test")
        element.width = 30
        element.height = 3

        x, y = manager._calculate_position(element, stack_index=0)

        # Should be in top-right corner
        # x = terminal_width - width - margin = 80 - 30 - 2 = 48
        assert x == 48

        # y = margin = 2
        assert y == 2

    def test_calculate_position_stacking(self):
        """Test position calculation for stacked notifications.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        manager = NotificationManager(overlay_manager, 80, 24, spacing=1)

        # Create first notification
        element1 = NotificationElement("First")
        element1.width = 30
        element1.height = 3
        id1 = manager.add(element1, duration=3.0)

        # Create second notification
        element2 = NotificationElement("Second")
        element2.width = 30
        element2.height = 3
        id2 = manager.add(element2, duration=3.0)

        # Second notification should be below first
        # First: y = 2 (margin)
        # Second: y = 2 + 3 (height) + 1 (spacing) = 6

        x2, y2 = manager._calculate_position(element2, stack_index=1)
        assert y2 == 6

    def test_on_close_callback_executed(self):
        """Test on_close callback is executed when adding notification.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        overlay_manager = MagicMock(spec=OverlayManager)
        overlay_manager.overlays = []  # Add overlays list for new check
        manager = NotificationManager(overlay_manager, 80, 24)

        callback = MagicMock()
        element = NotificationElement("Test")

        manager.add(element, duration=3.0, on_close=callback)

        # Simulate the overlay being added to the manager
        overlay_manager.overlays.append(manager.notifications[0].overlay)

        # Get the notification and trigger dismiss
        notification = manager.notifications[0]
        notification.element.on_dismiss()

        # Callback should be called
        callback.assert_called_once()
