"""Test checkbox group navigation."""

from wijjit import EventType, HandlerScope, Wijjit


def create_app():
    """Create test app."""
    app = Wijjit(
        initial_state={
            "notifications": ["email"],
        },
    )

    @app.view("main", default=True)
    def main_view():
        """Test view."""
        template = """
{% vstack spacing=1 padding=1 %}
    Checkbox Group Navigation Test

    Use Tab to focus the checkbox group below.
    Then use UP/DOWN arrows to navigate.
    Use Space/Enter to toggle selection.

    {% checkboxgroup id="notifications"
                     options=["Email", "Desktop", "Mobile", "SMS"]
                     width=30
                     border_style="single"
                     title="Notifications" %}
    {% endcheckboxgroup %}

    Selected: {{ state.notifications }}

    [Tab] Focus  [UP/DOWN] Navigate  [Space/Enter] Toggle  [q] Quit
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
