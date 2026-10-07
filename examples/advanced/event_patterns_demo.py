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

from wijjit import Wijjit, render_template_string
from wijjit.core.events import EventType, HandlerScope

# Create app
app = Wijjit(
    initial_state={
        "current_view": "view1",
        "event_log": [],
        "key_pressed": "",
        "handler_count": 0,
        # Rendered text for the log panel. This MUST live in state (not a
        # precomputed view ``data`` value): a view function runs once and its
        # ``data`` dict is frozen, so only ``state`` stays live across renders.
        "event_log_text": "No events yet... Press some keys!",
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
    # Refresh the live, rendered log text so the panel updates on re-render.
    app.state["event_log_text"] = "\n".join(app.state["event_log"][-12:])


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
        EventType.KEY,
        on_p_key_low,
        scope=HandlerScope.VIEW,
        view_name="view3",
        priority=0,
    )


@app.view("view1", default=True, on_enter=setup_view1_handlers)
def view1():
    """View 1 with view-scoped handlers.

    Returns
    -------
    dict
        View configuration
    """
    return render_template_string(
        """
{% frame title="Event Patterns Demo - View 1" border="double" width="fill" height="fill" %}
  {% vstack spacing=1 padding=1 height="fill" %}
    Current View: {{ state.current_view }}  |  Last Key: {{ state.key_pressed or "-" }}  |  Active Handlers: {{ state.handler_count }}

    {% hstack spacing=2 align_v="top" height="fill" %}
      {% frame title="Event Scopes & Features" border="single" width="fill" height="fill" scrollable=True %}
        {% vstack spacing=0 padding=1 %}
          1. GLOBAL - all views
             @app.on_key(), e.g. 'q'
          2. VIEW - one view only
             set in on_enter, e.g. 'v'
             cleared when leaving
          3. ELEMENT - while focused
             e.g. a text input

          Priority: higher runs first
             (default 0, -100..100)
          Cancel: event.cancel() stops
             lower-priority handlers
          Async: handlers may await
             without blocking the UI

          Try pressing:
          • 'h' - global (all views)
          • 'v' - View 1 only
          • '1/2/3' - switch views
        {% endvstack %}
      {% endframe %}

      {% frame title="Event Log" border="single" width="fill" height="fill" %}
        {% vstack padding=1 %}
{{ state.event_log_text }}
        {% endvstack %}
      {% endframe %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="goto_view2" %}Go to View 2{% endbutton %}
      {% button action="goto_view3" %}Go to View 3{% endbutton %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    [1/2/3] Switch views | [h] Global handler | [v] View handler | [q] Quit
  {% endvstack %}
{% endframe %}
        """,
    )


@app.view("view2", on_enter=setup_view2_handlers)
def view2():
    """View 2 with different view-scoped handlers.

    Returns
    -------
    dict
        View configuration
    """
    return render_template_string(
        """
{% frame title="Event Patterns Demo - View 2" border="double" width="fill" height="fill" %}
  {% vstack spacing=1 padding=1 height="fill" %}
    {% vstack spacing=0 %}
      Current View: {{ state.current_view }}
      This view has different view-scoped handlers than View 1
    {% endvstack %}

    {% frame title="Event Log" border="single" height="fill" %}
      {% vstack padding=1 %}
{{ state.event_log_text }}
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
    )


@app.view("view3", on_enter=setup_view3_handlers)
def view3():
    """View 3 demonstrating priority and cancellation.

    Returns
    -------
    dict
        View configuration
    """
    return render_template_string(
        """
{% frame title="Event Patterns Demo - View 3 (Priority Demo)" border="double" width="fill" height="fill" %}
  {% vstack spacing=1 padding=1 height="fill" %}
    {% vstack spacing=0 %}
      Current View: {{ state.current_view }}
      This view demonstrates handler priorities
    {% endvstack %}

    {% frame title="Event Log" border="single" height="fill" %}
      {% vstack padding=1 %}
{{ state.event_log_text }}
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
