"""Frame Text Overflow Demo - Demonstrates overflow_x modes.

This example shows the three overflow_x modes side by side:
- clip: Truncates text at frame width (default)
- visible: Allows text to extend beyond frame borders
- wrap: Wraps text to multiple lines at word boundaries

Run with: python examples/frame_overflow_demo.py

Controls:
- q: Quit
"""

from wijjit import Wijjit


def create_app():
    """Create and configure the frame overflow demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Sample content to demonstrate overflow behavior
    sample_text = """Here is some example text that demonstrates how different overflow modes handle content that exceeds the frame width.

The quick brown fox jumps over the lazy dog. This sentence is deliberately long to show wrapping behavior.

Features:
- Smart word boundaries
- ANSI code preservation
- Clean rendering"""  # noqa: E501

    # Initialize app
    app = Wijjit(
        initial_state={
            "sample_text": sample_text,
            "message": "Compare the three overflow modes below",
        }
    )

    @app.view("main", default=True)
    def main_view():
        """Main demo view showing three overflow modes."""
        return {
            "template": """
{% frame title="Frame Text Overflow Demo" border="double" width=105 height=26 %}
  {% vstack spacing=0 padding=1 %}
    {{ state.message }}

    {% hstack spacing=2 align_v="top" height=18 %}
      {% vstack spacing=0 width=32 %}
        {% frame title="CLIP (default)" border="single" width="fill" height=16 overflow_x="clip" %}
{{ state.sample_text }}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=0 width=32 %}
        {% frame title="VISIBLE" border="single" width="fill" height=16 overflow_x="visible" %}
{{ state.sample_text }}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=0 width=32 %}
        {% frame title="WRAP" border="single" width="fill" height=16 overflow_x="wrap" scrollable=true %}
{{ state.sample_text }}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    CLIP: truncated | VISIBLE: extends | WRAP: wraps+scrolls | Press 'q' to quit
  {% endvstack %}
{% endframe %}
            """,
            "data": {},
        }

    # Handle quit key
    from wijjit.core.events import EventType, HandlerScope

    def handle_key_q(event):
        """Handle 'q' key to quit."""
        if event.key == "q":
            app.quit()
            event.cancel()

    app.on(EventType.KEY, handle_key_q, scope=HandlerScope.GLOBAL)

    return app


def main():
    """Run the frame overflow demo application."""
    app = create_app()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
