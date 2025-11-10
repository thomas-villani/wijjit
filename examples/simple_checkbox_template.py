"""Simplified checkbox template demo to debug rendering."""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope


def create_app():
    """Create simple test app."""
    app = Wijjit(
        initial_state={
            "dark_mode": False,
            "auto_save": True,
            "notifications": ["email"],
        },
    )

    @app.view("main", default=True)
    def main_view():
        """Simplified view."""
        template = """
{% vstack spacing=1 padding=1 %}
    Simple Checkbox Test

    {% checkbox id="dark_mode" label="Enable dark mode" %}{% endcheckbox %}
    {% checkbox id="auto_save" label="Auto-save files" %}{% endcheckbox %}

    {% checkboxgroup id="notifications"
                     options=["Email", "Desktop", "Mobile"]
                     width=25 %}
    {% endcheckboxgroup %}

    Status: Dark={{ state.dark_mode }}, Auto={{ state.auto_save }}
    Notifications: {{ state.notifications }}

    [q] Quit
{% endvstack %}
"""

        return {
            "template": template,
            "data": {"state": app.state},
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up handlers."""
        def on_key(event):
            if event.key == "q":
                app.quit()

        app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main")

    return app


if __name__ == "__main__":
    app = create_app()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
