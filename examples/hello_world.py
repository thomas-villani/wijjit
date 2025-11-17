"""Simple Hello World - Minimal Wijjit app for testing.

Run with: python examples/hello_world.py
Press 'q' to quit.
"""

from wijjit import Wijjit


def main():
    """Run a simple hello world app."""
    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        """Main view."""
        return {
            "template": """
{% frame %}
Hello, World!

This is a simple Wijjit TUI application.

Press 'q' to quit.
{% endframe %}
""",
        }

    @app.on_key("q")
    def on_quit(event):
        if event.key == "q":
            app.quit()


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
