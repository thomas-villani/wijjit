"""Notification System Demo.

This demo showcases the notification system features:
- Different severity levels (success, error, warning, info)
- Auto-dismissal with timeouts
- Action buttons with callbacks
- Bell sound option
- Multiple stacked notifications
- Manual dismissal

Controls:
- '1': Success notification
- '2': Error notification
- '3': Warning notification
- '4': Info notification
- '5': Notification with action button
- '6': Persistent notification (no auto-dismiss)
- '7': Notification with bell sound
- '8': Multiple rapid notifications (stack test)
- '9': Clear all notifications
- Ctrl+C: Quit
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

app = Wijjit()


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% vstack %}
  {% frame border="double" title="Notification System Demo" %}

    Welcome to the Notification Demo!

    Press keys to trigger different notifications:

    [1] Success notification
    [2] Error notification
    [3] Warning notification
    [4] Info notification
    [5] Notification with action button
    [6] Persistent notification (manual dismiss)
    [7] Notification with bell sound
    [8] Multiple notifications (stack test)
    [9] Clear all notifications

    Press Ctrl+C to quit

    ---
    Active notifications: {{ state.active_count or 0 }}
    Total shown: {{ state.total_shown or 0 }}

  {% endframe %}
{% endvstack %}
        """,
        "data": {},
    }


def action_callback():
    """Callback for action button."""
    app.state["total_shown"] = app.state.get("total_shown", 0) + 1
    app.notify("Action executed!", severity="success", duration=2.0)


def handle_key_press(event):
    """Handle key presses for triggering notifications."""
    # Update total counter
    if event.key in "12345678":
        app.state["total_shown"] = app.state.get("total_shown", 0) + 1

    if event.key == "1":
        # Success notification
        app.notify(
            "Operation completed successfully!",
            severity="success",
            duration=3.0,
        )

    elif event.key == "2":
        # Error notification
        app.notify(
            "Connection to server failed!",
            severity="error",
            duration=4.0,
        )

    elif event.key == "3":
        # Warning notification
        app.notify(
            "Disk space running low!",
            severity="warning",
            duration=3.5,
        )

    elif event.key == "4":
        # Info notification
        app.notify(
            "New update available",
            severity="info",
            duration=3.0,
        )

    elif event.key == "5":
        # Notification with action button
        app.notify(
            "Download complete!",
            severity="success",
            action=("Open File", action_callback),
            dismiss_on_action=True,
            duration=None,
        )

    elif event.key == "6":
        # Persistent notification
        app.notify(
            "This notification won't auto-dismiss. Press 9 to clear.",
            severity="info",
            duration=None,  # Won't auto-dismiss
        )

    elif event.key == "7":
        # Notification with bell
        app.notify(
            "Important alert!",
            severity="warning",
            duration=3.0,
            bell=True,  # Play terminal bell
        )

    elif event.key == "8":
        # Multiple notifications rapidly
        app.notify("First notification", severity="info", duration=4.0)
        app.notify("Second notification", severity="success", duration=4.0)
        app.notify("Third notification", severity="warning", duration=4.0)
        app.state["total_shown"] = app.state.get("total_shown", 0) + 2

    elif event.key == "9":
        # Clear all notifications
        count = app.notification_manager.clear()
        if count > 0:
            app.notify(
                f"Cleared {count} notification(s)", severity="info", duration=2.0
            )

    # Update active count
    app.state["active_count"] = len(app.notification_manager.notifications)

    return False  # Don't consume the event


# Register the event handler
app.on(EventType.KEY, handle_key_press, scope=HandlerScope.GLOBAL)


if __name__ == "__main__":
    print(__doc__)
    print("\nStarting notification demo...")
    print("Press any key in the app to continue...")

    app.run()
