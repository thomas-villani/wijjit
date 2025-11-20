"""Scrollable Frame with Children Demo.

This example demonstrates a scrollable frame containing multiple child elements
that extend beyond the viewport height. Tests that scrolling works properly
with nested elements, not just text content.

Run with: python examples/scrollable_children_demo.py

Controls:
- Tab: Navigate between elements
- Arrow keys: Scroll when frame is focused
- q: Quit
"""

import sys

from wijjit import Wijjit
from wijjit.core.renderer import Renderer

TEMPLATE = """
{% frame title="Scrollable Children" border="double" width=80 height=25 %}
  {% vstack spacing=1 padding=2 %}
    This frame contains multiple child elements that extend beyond
    the visible viewport height. Use Tab to focus the scrollable
    frame below, then use arrow keys to scroll.

    {% frame id="scrollable_content" title="Scrollable Content Area" border="single" width="fill" height=15 scrollable=true %}
      {% vstack spacing=0 %}
        {% for item in item_list %}
          {% frame border="rounded" width="fill" height=auto padding=0 %}
            {{ item }}
          {% endframe %}
        {% endfor %}
      {% endvstack %}
    {% endframe %}

    Press 'q' to quit | Tab to focus | Arrow keys to scroll
  {% endvstack %}
{% endframe %}
"""


def create_app():
    """Create and configure the scrollable children demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Initialize app with sample data
    app = Wijjit(
        initial_state={
            "title": "Scrollable Frame with Children Demo",
        }
    )

    @app.view("main", default=True)
    def main_view():
        """Main demo view with scrollable frame containing many child elements."""
        return {
            "template": TEMPLATE,
            "data": {
                "item_list": [
                    f"Item {i+1}: Lorem ipsum dolor sit amet" for i in range(30)
                ]
            },
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
    """Run the scrollable children demo application."""
    if len(sys.argv) >= 2:
        renderer = Renderer()
        output, _, _ = renderer.render_with_layout(
            TEMPLATE,
            context={
                "item_list": [
                    f"Item {i + 1}: Lorem ipsum dolor sit amet" for i in range(30)
                ]
            },
            width=80,
            height=40,
        )
        # Write to file to avoid encoding issues
        with open("scrollable_demo_output.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("Output written to scrollable_demo_output.txt")
        return

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
