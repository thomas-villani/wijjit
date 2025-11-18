"""Notification manager for handling multiple notifications.

This module provides the NotificationManager class which manages a stack
of active notifications, including positioning, timeouts, and auto-dismissal.
Supports both synchronous and asynchronous operations.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING

from wijjit.core.overlay import LayerType, Overlay
from wijjit.layout.bounds import Bounds
from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from wijjit.core.overlay import OverlayManager
    from wijjit.elements.display.notification import NotificationElement

# Get logger for this module
logger = get_logger(__name__)


class ActiveNotification:
    """Container for an active notification with metadata.

    Parameters
    ----------
    id : str
        Unique notification identifier
    element : NotificationElement
        Notification element
    overlay : Overlay
        Overlay containing the notification
    created_at : float
        Timestamp when notification was created
    duration : float or None
        Duration in seconds before auto-dismiss (None = no auto-dismiss)
    expires_at : float or None
        Timestamp when notification expires (None = no expiry)

    Attributes
    ----------
    id : str
        Notification ID
    element : NotificationElement
        Notification element
    overlay : Overlay
        Overlay reference
    created_at : float
        Creation timestamp
    duration : float or None
        Duration in seconds
    expires_at : float or None
        Expiration timestamp
    """

    def __init__(
        self,
        id: str,
        element: NotificationElement,
        overlay: Overlay,
        created_at: float,
        duration: float | None = None,
    ):
        self.id = id
        self.element = element
        self.overlay = overlay
        self.created_at = created_at
        self.duration = duration
        self.expires_at = created_at + duration if duration else None

    def is_expired(self) -> bool:
        """Check if notification has expired.

        Returns
        -------
        bool
            True if notification has expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at


class NotificationManager:
    """Manager for notification stack and lifecycle.

    This class manages multiple active notifications, handling their positioning
    in a stack, auto-dismissal based on timeouts, and integration with the
    overlay manager.

    Parameters
    ----------
    overlay_manager : OverlayManager
        Overlay manager instance for displaying notifications
    terminal_width : int
        Current terminal width
    terminal_height : int
        Current terminal height
    position : str, optional
        Stack position: "top-right", "top-left", "bottom-right", "bottom-left"
        (default: "top-right")
    spacing : int, optional
        Vertical spacing between stacked notifications (default: 1)
    margin : int, optional
        Margin from screen edges (default: 2)

    Attributes
    ----------
    overlay_manager : OverlayManager
        Overlay manager reference
    terminal_width : int
        Terminal width
    terminal_height : int
        Terminal height
    position : str
        Stack position
    spacing : int
        Spacing between notifications
    margin : int
        Edge margin
    notifications : list
        List of active notifications (oldest first)
    """

    def __init__(
        self,
        overlay_manager: OverlayManager,
        terminal_width: int,
        terminal_height: int,
        position: str = "top-right",
        spacing: int = 1,
        margin: int = 2,
    ):
        self.overlay_manager = overlay_manager
        self.terminal_width = terminal_width
        self.terminal_height = terminal_height
        self.position = position
        self.spacing = spacing
        self.margin = margin
        self.notifications: list[ActiveNotification] = []

    def add(
        self,
        element: NotificationElement,
        duration: float | None = 3.0,
        on_close: Callable | None = None,
    ) -> str:
        """Add a notification to the stack.

        Parameters
        ----------
        element : NotificationElement
            Notification element to display
        duration : float or None, optional
            Duration in seconds before auto-dismiss (default: 3.0)
            Set to None for no auto-dismiss
        on_close : callable, optional
            Callback when notification is dismissed

        Returns
        -------
        str
            Notification ID for manual dismissal
        """
        # Generate unique ID
        notification_id = str(uuid.uuid4())

        # Calculate position for this notification
        x, y = self._calculate_position(element, len(self.notifications))

        # Set element bounds
        bounds = Bounds(x=x, y=y, width=element.width, height=element.height)
        element.set_bounds(bounds)

        # Wire dismiss callback
        def dismiss_callback():
            self.remove(notification_id)
            if on_close:
                on_close()

        element.on_dismiss = dismiss_callback

        # Trap focus if notification has an action button
        has_button = element.action_button is not None

        # Create overlay using overlay manager
        overlay = self.overlay_manager.push(
            element,
            LayerType.TOOLTIP,  # Highest z-index
            close_on_escape=False,  # ESC handled by app to dismiss oldest first
            close_on_click_outside=False,  # Don't close on outside click
            trap_focus=has_button,  # Trap focus if there's a button to interact with
            dimmed_background=False,  # Don't dim background
            on_close=dismiss_callback,
        )

        # Create notification record
        notification = ActiveNotification(
            id=notification_id,
            element=element,
            overlay=overlay,
            created_at=time.time(),
            duration=duration,
        )

        # Add to stack (append to end - newest on bottom when rendering)
        self.notifications.append(notification)

        logger.debug(
            f"Added notification {notification_id}: {element.message[:50]}... "
            f"(duration: {duration}s)"
        )

        return notification_id

    def remove(self, notification_id: str) -> bool:
        """Remove a notification from the stack.

        Parameters
        ----------
        notification_id : str
            ID of notification to remove

        Returns
        -------
        bool
            True if notification was removed, False if not found
        """
        for notification in self.notifications:
            if notification.id == notification_id:
                # Remove from overlay manager only if it's still there
                # (it might have been removed by ESC key or other means)
                if notification.overlay in self.overlay_manager.overlays:
                    self.overlay_manager.pop(notification.overlay)

                # Remove from list (use remove() not pop(i) to avoid race condition)
                # Check if still in list before removing (double-call protection)
                if notification in self.notifications:
                    self.notifications.remove(notification)

                # Update positions of remaining notifications
                self.update_positions()

                logger.debug(f"Removed notification {notification_id}")
                return True

        return False

    def check_expired(self) -> bool:
        """Check for expired notifications and remove them (synchronous).

        Returns
        -------
        bool
            True if any notifications were removed, False otherwise
        """
        if not self.notifications:
            return False

        # Make a copy to iterate over to avoid race conditions
        # (notifications can be removed by other handlers while we're checking)
        notifications_to_check = list(self.notifications)
        removed_any = False

        for notification in notifications_to_check:
            if notification.is_expired():
                # Check if still in the list (might have been removed by another handler)
                if notification in self.notifications:
                    try:
                        # Remove from list
                        self.notifications.remove(notification)
                        # Remove overlay only if it's still there
                        if notification.overlay in self.overlay_manager.overlays:
                            self.overlay_manager.pop(notification.overlay)
                        removed_any = True
                        logger.debug(f"Expired notification: {notification.id}")
                    except (ValueError, IndexError):
                        # Already removed by another handler, skip
                        pass

        # Update positions if we removed any
        if removed_any:
            self.update_positions()

        return removed_any

    async def check_expired_async(self) -> bool:
        """Check for expired notifications and remove them (asynchronous).

        This async version allows the event loop to process other tasks
        while checking and removing expired notifications.

        Returns
        -------
        bool
            True if any notifications were removed, False otherwise
        """
        if not self.notifications:
            return False

        # Make a copy to iterate over to avoid race conditions
        # (notifications can be removed by other handlers while we're checking)
        notifications_to_check = list(self.notifications)
        removed_any = False

        for notification in notifications_to_check:
            if notification.is_expired():
                # Check if still in the list (might have been removed by another handler)
                if notification in self.notifications:
                    try:
                        # Remove from list
                        self.notifications.remove(notification)
                        # Remove overlay only if it's still there
                        if notification.overlay in self.overlay_manager.overlays:
                            self.overlay_manager.pop(notification.overlay)
                        removed_any = True
                        logger.debug(f"Expired notification: {notification.id}")
                    except (ValueError, IndexError):
                        # Already removed by another handler, skip
                        pass

                # Yield to event loop periodically
                await asyncio.sleep(0)

        # Update positions if we removed any
        if removed_any:
            self.update_positions()

        return removed_any

    def update_positions(self) -> None:
        """Update positions of all notifications in the stack.

        This should be called after adding/removing notifications or
        when terminal size changes.
        """
        for i, notification in enumerate(self.notifications):
            x, y = self._calculate_position(notification.element, i)
            bounds = Bounds(
                x=x,
                y=y,
                width=notification.element.width,
                height=notification.element.height,
            )
            notification.element.set_bounds(bounds)

    def update_terminal_size(self, width: int, height: int) -> None:
        """Update terminal size and reposition notifications.

        Parameters
        ----------
        width : int
            New terminal width
        height : int
            New terminal height
        """
        self.terminal_width = width
        self.terminal_height = height
        self.update_positions()

    def clear(self) -> int:
        """Remove all notifications.

        Returns
        -------
        int
            Number of notifications removed
        """
        count = len(self.notifications)

        # Remove all overlays
        for notification in self.notifications:
            self.overlay_manager.pop(notification.overlay)

        # Clear list
        self.notifications.clear()

        logger.debug(f"Cleared {count} notification(s)")
        return count

    def dismiss_oldest(self) -> bool:
        """Dismiss the oldest notification.

        Returns
        -------
        bool
            True if a notification was dismissed, False if none exist
        """
        if not self.notifications:
            return False

        # Remove the first notification (oldest)
        oldest = self.notifications[0]
        return self.remove(oldest.id)

    def dismiss_topmost(self) -> bool:
        """Dismiss the topmost (most recent) notification.

        Returns
        -------
        bool
            True if a notification was dismissed, False if none exist
        """
        if not self.notifications:
            return False

        # Remove the last notification (newest)
        topmost = self.notifications[-1]
        return self.remove(topmost.id)

    def _calculate_position(
        self, element: NotificationElement, stack_index: int
    ) -> tuple[int, int]:
        """Calculate screen position for a notification in the stack.

        Parameters
        ----------
        element : NotificationElement
            Notification element
        stack_index : int
            Index in the stack (0 = oldest/top, higher = newer/bottom)

        Returns
        -------
        tuple of int
            (x, y) position
        """
        # Calculate accumulated height of notifications above this one
        accumulated_height = 0
        for i in range(stack_index):
            if i < len(self.notifications):
                accumulated_height += (
                    self.notifications[i].element.height + self.spacing
                )

        # Calculate x position based on position setting
        if "right" in self.position:
            x = self.terminal_width - element.width - self.margin
        else:  # left
            x = self.margin

        # Calculate y position based on position setting
        if "top" in self.position:
            y = self.margin + accumulated_height
        else:  # bottom
            # Start from bottom and stack upward
            total_stack_height = accumulated_height + element.height
            y = self.terminal_height - total_stack_height - self.margin

        return x, y
