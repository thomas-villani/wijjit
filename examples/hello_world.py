"""Simple Hello World - Minimal Wijjit app for testing.

Run with: python examples/hello_world.py
Press 'q' to quit.
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope


def main():
    """Run a simple hello world app."""
    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        """Main view."""
        return {
            "template": """
Hello, World!

This is a simple Wijjit TUI application.

Press 'q' to quit.
""",
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers."""

        def on_quit(event):
            if event.key == "q":
                app.quit()

        app.on(EventType.KEY, on_quit, scope=HandlerScope.VIEW, view_name="main")

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
