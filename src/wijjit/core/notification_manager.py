"""Notification manager for handling multiple notifications.

This module provides the NotificationManager class which manages a stack
of active notifications, including positioning, timeouts, and auto-dismissal.
Supports both synchronous and asynchronous operations.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any

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
    ) -> None:
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
    max_stack : int or None, optional
        Maximum number of concurrent notifications. When limit is reached,
        oldest notifications are automatically dismissed. None = unlimited
        (default: 5)

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
    max_stack : int or None
        Maximum stack size
    notifications : list
        List of active notifications (oldest first)
    _lock : threading.Lock
        Thread lock for protecting notification list access

    Notes
    -----
    All notification list access is protected by a threading.Lock to ensure
    thread safety when notifications are added, removed, or checked from
    multiple threads or async tasks.
    """

    def __init__(
        self,
        overlay_manager: OverlayManager,
        terminal_width: int,
        terminal_height: int,
        position: str = "top-right",
        spacing: int = 1,
        margin: int = 2,
        max_stack: int | None = 5,
    ) -> None:
        self.overlay_manager = overlay_manager
        self.terminal_width = terminal_width
        self.terminal_height = terminal_height
        self.position = position
        self.spacing = spacing
        self.margin = margin
        self.max_stack = max_stack
        self.notifications: list[ActiveNotification] = []
        self._lock = threading.Lock()  # Protect notification list access

    def add(
        self,
        element: NotificationElement,
        duration: float | None = 3.0,
        on_close: Callable[..., Any] | None = None,
    ) -> str:
        """Add a notification to the stack.

        If max_stack is set and the stack is full, the oldest notification
        will be automatically dismissed before adding the new one.

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

        # Check if we need to dismiss oldest notification due to max_stack limit
        with self._lock:
            if self.max_stack is not None and len(self.notifications) >= self.max_stack:
                # Remove oldest notification (first in list)
                if self.notifications:
                    oldest = self.notifications[0]
                    logger.debug(
                        f"Max stack ({self.max_stack}) reached, "
                        f"dismissing oldest notification: {oldest.id}"
                    )
                    # Remove from list immediately (we have the lock)
                    self.notifications.pop(0)
                    # Dismiss overlay (outside lock to avoid deadlock)
                    self.overlay_manager.pop(oldest.overlay)

        # Calculate position for this notification (needs lock for list read)
        with self._lock:
            stack_index = len(self.notifications)
        x, y = self._calculate_position(element, stack_index)

        # Set element bounds - element width/height must be set before adding
        assert element.width is not None, "Notification element must have width set"
        assert element.height is not None, "Notification element must have height set"
        bounds = Bounds(x=x, y=y, width=element.width, height=element.height)
        element.set_bounds(bounds)

        # Wire dismiss callback
        def dismiss_callback() -> None:
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
        # Thread-safe append
        with self._lock:
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
        # Thread-safe search and remove
        notification = None
        with self._lock:
            # Find notification with matching ID
            for notif in self.notifications:
                if notif.id == notification_id:
                    notification = notif
                    break

            if notification is None:
                return False

            # Remove from list (use remove() not pop(i) to avoid race condition)
            # Check if still in list before removing (double-call protection)
            if notification in self.notifications:
                self.notifications.remove(notification)

        # Remove from overlay manager outside the lock to avoid blocking
        # (it might have been removed by ESC key or other means)
        if notification.overlay in self.overlay_manager.overlays:
            self.overlay_manager.pop(notification.overlay)

        # Update positions of remaining notifications (outside lock)
        self.update_positions()

        logger.debug(f"Removed notification {notification_id}")
        return True

    def check_expired(self) -> bool:
        """Check for expired notifications and remove them (synchronous).

        Returns
        -------
        bool
            True if any notifications were removed, False otherwise
        """
        # Thread-safe check for empty list
        with self._lock:
            if not self.notifications:
                return False
            # Make a copy to iterate over (outside lock to minimize lock time)
            notifications_to_check = list(self.notifications)

        removed_any = False
        overlays_to_remove = []

        for notification in notifications_to_check:
            if notification.is_expired():
                # Thread-safe removal
                with self._lock:
                    # Check if still in the list (might have been removed by another handler)
                    if notification in self.notifications:
                        try:
                            # Remove from list
                            self.notifications.remove(notification)
                            # Collect overlay for removal outside lock
                            if notification.overlay in self.overlay_manager.overlays:
                                overlays_to_remove.append(notification.overlay)
                            removed_any = True
                            logger.debug(f"Expired notification: {notification.id}")
                        except (ValueError, IndexError):
                            # Already removed by another handler, skip
                            pass

        # Remove overlays outside the lock to avoid blocking
        for overlay in overlays_to_remove:
            if overlay in self.overlay_manager.overlays:
                self.overlay_manager.pop(overlay)

        # Update positions if we removed any (outside lock)
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
        # Thread-safe check for empty list
        with self._lock:
            if not self.notifications:
                return False
            # Make a copy to iterate over (outside lock to minimize lock time)
            notifications_to_check = list(self.notifications)

        removed_any = False
        overlays_to_remove = []

        for notification in notifications_to_check:
            if notification.is_expired():
                # Thread-safe removal
                with self._lock:
                    # Check if still in the list (might have been removed by another handler)
                    if notification in self.notifications:
                        try:
                            # Remove from list
                            self.notifications.remove(notification)
                            # Collect overlay for removal outside lock
                            if notification.overlay in self.overlay_manager.overlays:
                                overlays_to_remove.append(notification.overlay)
                            removed_any = True
                            logger.debug(f"Expired notification: {notification.id}")
                        except (ValueError, IndexError):
                            # Already removed by another handler, skip
                            pass

                # Yield to event loop periodically (outside lock)
                await asyncio.sleep(0)

        # Remove overlays outside the lock to avoid blocking
        for overlay in overlays_to_remove:
            if overlay in self.overlay_manager.overlays:
                self.overlay_manager.pop(overlay)

        # Update positions if we removed any (outside lock)
        if removed_any:
            self.update_positions()

        return removed_any

    def update_positions(self) -> None:
        """Update positions of all notifications in the stack.

        This should be called after adding/removing notifications or
        when terminal size changes.
        """
        # Thread-safe iteration: copy list for iteration
        with self._lock:
            notifications_copy = list(self.notifications)

        for i, notification in enumerate(notifications_copy):
            x, y = self._calculate_position(notification.element, i)
            # Element width/height should be set (checked when added)
            assert notification.element.width is not None
            assert notification.element.height is not None
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
        # Thread-safe clear: get count and copy, then clear
        with self._lock:
            count = len(self.notifications)
            notifications_to_clear = list(self.notifications)
            # Clear list immediately (while locked)
            self.notifications.clear()

        # Remove all overlays (outside lock)
        for notification in notifications_to_clear:
            # Always attempt to pop - overlay_manager will handle if not found
            self.overlay_manager.pop(notification.overlay)

        logger.debug(f"Cleared {count} notification(s)")
        return count

    def dismiss_oldest(self) -> bool:
        """Dismiss the oldest notification.

        Returns
        -------
        bool
            True if a notification was dismissed, False if none exist
        """
        # Thread-safe check and access
        with self._lock:
            if not self.notifications:
                return False
            # Get oldest notification ID
            oldest_id = self.notifications[0].id

        # Remove using the ID (remove() handles its own locking)
        return self.remove(oldest_id)

    def dismiss_topmost(self) -> bool:
        """Dismiss the topmost (most recent) notification.

        Returns
        -------
        bool
            True if a notification was dismissed, False if none exist
        """
        # Thread-safe check and access
        with self._lock:
            if not self.notifications:
                return False
            # Get topmost notification ID
            topmost_id = self.notifications[-1].id

        # Remove using the ID (remove() handles its own locking)
        return self.remove(topmost_id)

    def is_empty(self) -> bool:
        """Check if there are any active notifications (thread-safe).

        Returns
        -------
        bool
            True if no notifications are active, False otherwise
        """
        with self._lock:
            return len(self.notifications) == 0

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
        # Element must have width and height set
        assert element.width is not None, "Element must have width"
        assert element.height is not None, "Element must have height"

        # Calculate accumulated height of notifications above this one
        # Thread-safe list access for reading
        accumulated_height = 0
        with self._lock:
            for i in range(stack_index):
                if i < len(self.notifications):
                    notif_element = self.notifications[i].element
                    assert notif_element.height is not None
                    accumulated_height += notif_element.height + self.spacing

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
