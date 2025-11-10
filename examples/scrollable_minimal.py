"""Minimal scrollable frame test.

Run with: python examples/scrollable_minimal.py
"""

from wijjit import Wijjit


def create_app():
    """Create minimal scrollable test."""
    app = Wijjit(initial_state={"count": 0})

    @app.view("main", default=True)
    def main_view():
        """Main view with simple scrollable frame."""
        return {
            "template": """
{% frame title="Test" border="double" width=60 height=20 %}
  {% vstack spacing=1 padding=2 %}
    Press Up/Down to scroll, q to quit
    Focus status: Frame should auto-focus when scrollable

    {% frame id="scrollable_test" title="Scrollable" border="single" width="fill" height=10 scrollable=true %}
        Line 1: This is test content
        Line 2: This is test content
        Line 3: This is test content
        Line 4: This is test content
        Line 5: This is test content
        Line 6: This is test content
        Line 7: This is test content
        Line 8: This is test content
        Line 9: This is test content
        Line 10: This is test content
        Line 11: This is test content
        Line 12: This is test content
    {% endframe %}

    Keys: {{ state.count }}
  {% endvstack %}
{% endframe %}
            """,
            "data": {},
        }

    # Track key presses
    from wijjit.core.events import EventType, HandlerScope

    def handle_key(event):
        """Handle keys."""
        if event.key == "q":
            app.quit()
            event.cancel()
        else:
            # Just count key presses to show keys are working
            app.state["count"] = app.state.get("count", 0) + 1

            # Debug: print focus info
            if event.key == "d":
                if hasattr(app, 'focus_manager'):
                    focused = app.focus_manager.get_focused_element()
                    print(f"\nDEBUG - Focused element: {focused}")
                    print(f"Focusable elements: {len(app.focus_manager.elements)}")
                    for i, elem in enumerate(app.focus_manager.elements):
                        elem_type = type(elem).__name__
                        elem_id = getattr(elem, 'id', 'no-id')
                        is_focused = elem == focused
                        print(f"  [{i}] {elem_type} id={elem_id} focused={is_focused}")
                        if elem_type == "Frame":
                            print(f"      scrollable={elem.style.scrollable}, needs_scroll={elem._needs_scroll}")
                            print(f"      has_children={elem._has_children}, content={len(elem.content)} lines")

    app.on(EventType.KEY, handle_key, scope=HandlerScope.GLOBAL)

    return app


def main():
    """Run the app."""
    app = create_app()

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
