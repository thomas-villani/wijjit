"""Event Patterns Demo - Advanced Event Handling.

This example demonstrates advanced event handling patterns:
- Global vs view-scoped vs element-scoped handlers
- Event priorities and execution order
- Event cancellation and propagation
- Multiple handlers for the same event
- Async event handlers

Run with: python examples/advanced/event_patterns_demo.py

Controls:
- Press keys to see event handling in action
- 1/2/3: Switch between views to see view-scoped handlers
- q: Quit
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Create app
app = Wijjit(
    initial_state={
        "current_view": "view1",
        "event_log": [],
        "key_pressed": "",
        "handler_count": 0,
    }
)


def log_event(source, message):
    """Log an event to the history.

    Parameters
    ----------
    source : str
        The source/handler that logged the event
    message : str
        The event message
    """
    log = app.state.get("event_log", [])
    log.append(f"[{source}] {message}")

    # Keep last 15 events
    app.state["event_log"] = log[-15:]


@app.view("view1", default=True)
def view1():
    """View 1 with view-scoped handlers.

    Returns
    -------
    dict
        View configuration
    """
    event_log_text = "\n".join(app.state.get("event_log", [])[-12:])
    if not event_log_text:
        event_log_text = "No events yet... Press some keys!"

    return {
        "template": """
{% frame title="Event Patterns Demo - View 1" border="double" width=100 height=36 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Current View: {{ state.current_view }}
      Last Key: {{ state.key_pressed }}
      Active Handlers: {{ state.handler_count }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=48 %}
        {% frame title="Event Scopes" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            1. GLOBAL Handlers:
               • Active in ALL views
               • Registered with @app.on_key()
               • Example: 'q' for quit

            2. VIEW Handlers:
               • Active only in specific view
               • Registered via on_enter hook
               • Cleared when leaving view
               • Example: 'v' in View 1

            3. ELEMENT Handlers:
               • Active when element focused
               • Element-specific behavior
               • Example: text input

            Try pressing:
            • 'h' - Global handler (works in all views)
            • 'v' - View-scoped (only in View 1)
            • '1/2/3' - Navigate between views
          {% endvstack %}
        {% endframe %}

        {% frame title="Event Features" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Priority:
            • Higher priority = runs first
            • Default priority = 0
            • Range: -100 to 100

            Cancellation:
            • event.cancel() stops propagation
            • Prevents lower priority handlers
            • Useful for overrides

            Async Support:
            • Handlers can be async
            • Await operations in handlers
            • Non-blocking execution
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=48 %}
        {% frame title="Event Log" border="single" width="fill" height=26 %}
          {% vstack padding=1 %}
{{ event_log_text }}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="goto_view2" %}Go to View 2{% endbutton %}
      {% button action="goto_view3" %}Go to View 3{% endbutton %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      [1/2/3] Switch views | [h] Global handler | [v] View handler | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "event_log_text": event_log_text,
        },
        "on_enter": setup_view1_handlers,
    }


@app.view("view2")
def view2():
    """View 2 with different view-scoped handlers.

    Returns
    -------
    dict
        View configuration
    """
    event_log_text = "\n".join(app.state.get("event_log", [])[-12:])

    return {
        "template": """
{% frame title="Event Patterns Demo - View 2" border="double" width=100 height=36 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Current View: {{ state.current_view }}
      This view has different view-scoped handlers than View 1
    {% endvstack %}

    {% frame title="Event Log" border="single" height=25 %}
      {% vstack padding=1 %}
{{ event_log_text }}
      {% endvstack %}
    {% endframe %}

    {% hstack spacing=2 %}
      {% button action="goto_view1" %}Go to View 1{% endbutton %}
      {% button action="goto_view3" %}Go to View 3{% endbutton %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Try pressing 'v' - notice it does something different in this view!
      [h] Global | [v] View-specific | [1/2/3] Switch | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "event_log_text": event_log_text,
        },
        "on_enter": setup_view2_handlers,
    }


@app.view("view3")
def view3():
    """View 3 demonstrating priority and cancellation.

    Returns
    -------
    dict
        View configuration
    """
    event_log_text = "\n".join(app.state.get("event_log", [])[-12:])

    return {
        "template": """
{% frame title="Event Patterns Demo - View 3 (Priority Demo)" border="double" width=100 height=36 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Current View: {{ state.current_view }}
      This view demonstrates handler priorities
    {% endvstack %}

    {% frame title="Event Log" border="single" height=25 %}
      {% vstack padding=1 %}
{{ event_log_text }}
      {% endvstack %}
    {% endframe %}

    {% hstack spacing=2 %}
      {% button action="goto_view1" %}Go to View 1{% endbutton %}
      {% button action="goto_view2" %}Go to View 2{% endbutton %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Press 'p' to see priority handling (3 handlers with different priorities)
      [h] Global | [p] Priority demo | [1/2/3] Switch | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "event_log_text": event_log_text,
        },
        "on_enter": setup_view3_handlers,
    }


def setup_view1_handlers():
    """Set up View 1 specific handlers."""
    app.state["current_view"] = "view1"
    log_event("SYSTEM", "Entered View 1 - view-scoped handlers active")

    def on_v_key(event):
        """View 1 specific handler for 'v' key."""
        if event.key == "v":
            log_event("VIEW1", "View 1 'v' key handler triggered")
            app.state["key_pressed"] = "v (View 1)"

    app.on(EventType.KEY, on_v_key, scope=HandlerScope.VIEW, view_name="view1")


def setup_view2_handlers():
    """Set up View 2 specific handlers."""
    app.state["current_view"] = "view2"
    log_event("SYSTEM", "Entered View 2 - different handlers active")

    def on_v_key(event):
        """View 2 specific handler for 'v' key - different behavior!"""
        if event.key == "v":
            log_event("VIEW2", "View 2 'v' key handler (DIFFERENT from View 1!)")
            app.state["key_pressed"] = "v (View 2 - different!)"

    app.on(EventType.KEY, on_v_key, scope=HandlerScope.VIEW, view_name="view2")


def setup_view3_handlers():
    """Set up View 3 handlers demonstrating priorities."""
    app.state["current_view"] = "view3"
    log_event("SYSTEM", "Entered View 3 - priority demo active")

    def on_p_key_high(event):
        """High priority handler for 'p' key."""
        if event.key == "p":
            log_event("HIGH", "Priority 100 handler (runs first)")

    def on_p_key_medium(event):
        """Medium priority handler for 'p' key."""
        if event.key == "p":
            log_event("MEDIUM", "Priority 50 handler (runs second)")

    def on_p_key_low(event):
        """Low priority handler for 'p' key."""
        if event.key == "p":
            log_event("LOW", "Priority 0 handler (runs third)")

    # Register with different priorities
    app.on(
        EventType.KEY,
        on_p_key_high,
        scope=HandlerScope.VIEW,
        view_name="view3",
        priority=100,
    )
    app.on(
        EventType.KEY,
        on_p_key_medium,
        scope=HandlerScope.VIEW,
        view_name="view3",
        priority=50,
    )
    app.on(
        EventType.KEY, on_p_key_low, scope=HandlerScope.VIEW, view_name="view3", priority=0
    )


# Global handlers (work in all views)
@app.on_key("h")
def on_h_key(event):
    """Global handler for 'h' key - works in ALL views.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    log_event("GLOBAL", "Global 'h' handler - works in all views!")
    app.state["key_pressed"] = "h (global)"


@app.on_key("1")
def on_key_1(event):
    """Navigate to View 1.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.navigate("view1")


@app.on_key("2")
def on_key_2(event):
    """Navigate to View 2.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.navigate("view2")


@app.on_key("3")
def on_key_3(event):
    """Navigate to View 3.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.navigate("view3")


# Action handlers
@app.on_action("goto_view1")
def handle_goto_view1(event):
    """Navigate to View 1.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.navigate("view1")


@app.on_action("goto_view2")
def handle_goto_view2(event):
    """Navigate to View 2.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.navigate("view2")


@app.on_action("goto_view3")
def handle_goto_view3(event):
    """Navigate to View 3.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.navigate("view3")


@app.on_action("clear_log")
def handle_clear_log(event):
    """Clear event log.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["event_log"] = []
    log_event("SYSTEM", "Event log cleared")


@app.on_action("quit")
def handle_quit(event):
    """Quit the application.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.quit()


@app.on_key("q")
def on_quit(event):
    """Global quit handler.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.quit()


if __name__ == "__main__":
    print("Event Patterns Demo")
    print("=" * 50)
    print()
    print("This demo shows advanced event handling patterns:")
    print()
    print("Event Scopes:")
    print("  • GLOBAL - Active in all views (@app.on_key decorator)")
    print("  • VIEW - Active only in specific view (via on_enter)")
    print("  • ELEMENT - Active when element has focus")
    print()
    print("Features Demonstrated:")
    print("  • Event priorities (high/medium/low)")
    print("  • Handler execution order")
    print("  • View-scoped vs global handlers")
    print("  • Event logging and inspection")
    print()
    print("Try:")
    print("  1. Press 'h' in any view (global handler)")
    print("  2. Press 'v' in View 1 and View 2 (different behaviors!)")
    print("  3. Press 'p' in View 3 (see priority order)")
    print("  4. Switch views with 1/2/3 keys")
    print()
    print("Starting app...")
    print()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
