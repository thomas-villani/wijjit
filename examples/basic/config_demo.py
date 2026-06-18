"""Configuration System Demo.

This example demonstrates how to use Wijjit's Flask-like configuration system.
Shows various ways to configure the application including direct assignment,
environment variables, and config files.
"""

from wijjit import Wijjit

# Create app - config is automatically initialized with defaults
app = Wijjit()

# ==============================================================================
# METHOD 1: Direct configuration via dict-style access
# ==============================================================================

# Disable mouse interaction
app.config["ENABLE_MOUSE"] = False

# Change quit key from ctrl+q to just 'q'
app.config["QUIT_KEY"] = "q"

# Disable focus navigation (no Tab/Shift+Tab)
app.config["ENABLE_FOCUS_NAVIGATION"] = False

# Enable debug mode
app.config["DEBUG"] = True

# Configure logging
app.config["LOG_LEVEL"] = "INFO"  # Show info messages

# Configure notifications
app.config["NOTIFICATION_DURATION"] = 5.0  # 5 seconds
app.config["NOTIFICATION_POSITION"] = "bottom_right"
app.config["NOTIFICATION_MAX_STACK"] = 3  # Max 3 notifications

# ==============================================================================
# METHOD 2: Bulk update using update()
# ==============================================================================

app.config.update(
    # Change refresh rate for smoother animations
    REFRESH_INTERVAL=0.1,  # 100ms
    # Run sync handlers in thread pool (prevents UI freezing)
    RUN_SYNC_IN_EXECUTOR=True,
    EXECUTOR_MAX_WORKERS=4,
)

# ==============================================================================
# METHOD 3: Environment variables (already loaded automatically)
# ==============================================================================

# The config system automatically loads WIJJIT_* environment variables
# For example, you can set:
#   export WIJJIT_DEBUG=1
#   export WIJJIT_ENABLE_MOUSE=0
#   export WIJJIT_LOG_LEVEL=DEBUG
#
# These are loaded in Wijjit.__init__ via config.from_prefixed_env('WIJJIT_')

# ==============================================================================
# METHOD 4: Config namespaces
# ==============================================================================

# Get all notification-related settings
notification_config = app.config.get_namespace("NOTIFICATION_")
print("Notification config:")
for key, value in notification_config.items():
    print(f"  {key}: {value}")

# ==============================================================================
# DEMO VIEW
# ==============================================================================


@app.view("main", default=True)
def main_view():
    """Main view showing current configuration."""
    template = """
{% frame border="double" title="Configuration Demo" padding=1 %}
  {% vstack spacing=1 %}
    Configuration System Demo
    =========================

    Current Configuration:
    - ENABLE_MOUSE: {{ config.ENABLE_MOUSE }}
    - QUIT_KEY: {{ config.QUIT_KEY }}
    - DEBUG: {{ config.DEBUG }}
    - LOG_LEVEL: {{ config.LOG_LEVEL }}
    - NOTIFICATION_DURATION: {{ config.NOTIFICATION_DURATION }}s
    - NOTIFICATION_POSITION: {{ config.NOTIFICATION_POSITION }}
    - NOTIFICATION_MAX_STACK: {{ config.NOTIFICATION_MAX_STACK }}

    Environment Variables:
    - NO_COLOR: {{ config.NO_COLOR }}
    - CI: {{ config.CI }}

    Performance:
    - REFRESH_INTERVAL: {{ config.REFRESH_INTERVAL }}s
    - RUN_SYNC_IN_EXECUTOR: {{ config.RUN_SYNC_IN_EXECUTOR }}
    - EXECUTOR_MAX_WORKERS: {{ config.EXECUTOR_MAX_WORKERS }}

    Press 'n' to test notifications
    Press 't' to toggle mouse
    Press '{{ config.QUIT_KEY }}' to quit
  {% endvstack %}
{% endframe %}
"""
    return {
        "template": template,
        "data": {
            "config": app.config,
        },
    }


# ==============================================================================
# EVENT HANDLERS
# ==============================================================================


@app.on_key("n")
def show_notification(event):
    """Show a test notification."""
    import random

    messages = [
        "Configuration is awesome!",
        "This notification respects config settings",
        f"Duration: {app.config['NOTIFICATION_DURATION']}s",
        f"Position: {app.config['NOTIFICATION_POSITION']}",
    ]

    app.notify(
        random.choice(messages),
        severity="info",
        duration=app.config["NOTIFICATION_DURATION"],
    )


@app.on_key("t")
def toggle_mouse(event):
    """Toggle mouse support at runtime."""
    current = app.config["ENABLE_MOUSE"]
    app.config["ENABLE_MOUSE"] = not current

    # Update input handler
    if app.config["ENABLE_MOUSE"]:
        app.input_handler.enable_mouse_tracking()
        app.notify("Mouse enabled!", severity="success")
    else:
        app.input_handler.disable_mouse_tracking()
        app.notify("Mouse disabled!", severity="info")


if __name__ == "__main__":
    # Show current config on startup
    print("\nStarting Wijjit with configuration:")
    print(f"  Mouse: {app.config['ENABLE_MOUSE']}")
    print(f"  Quit key: {app.config['QUIT_KEY']}")
    print(f"  Debug: {app.config['DEBUG']}")
    print(f"  Log level: {app.config['LOG_LEVEL']}")
    print()

    # Run the app
    app.run()
