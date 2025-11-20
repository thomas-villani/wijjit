"""State Management Demo - Advanced State Patterns.

This example demonstrates Wijjit's state management features:
- Global state change callbacks with on_change()
- Key-specific watchers with watch()
- Both synchronous and asynchronous callbacks
- Derived state calculations
- State validation and logging
- Undo/redo pattern with state history

Run with: python examples/advanced/state_management_demo.py

Controls:
- Tab/Shift+Tab: Navigate between inputs
- q: Quit
"""

import asyncio
from datetime import datetime

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "counter": 0,
        "username": "",
        "email": "",
        "status": "Ready",
        "change_log": [],
        "validation_errors": [],
        # Derived state (computed from other state)
        "counter_squared": 0,
        "form_complete": False,
    }
)


# State change history for logging
state_history = []


def log_state_change(key, old_value, new_value):
    """Log all state changes (synchronous callback).

    This is a global callback that fires for ANY state change.

    Parameters
    ----------
    key : str
        The state key that changed
    old_value : Any
        The previous value
    new_value : Any
        The new value
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {key}: {old_value} → {new_value}"

    # Add to history
    state_history.append(entry)

    # Update the change log in state (keep last 10 entries)
    app.state["change_log"] = state_history[-10:]


async def validate_email_async(key, old_value, new_value):
    """Asynchronous email validation watcher.

    This demonstrates an async callback that could perform
    network validation, database lookups, etc.

    Parameters
    ----------
    key : str
        The state key ("email")
    old_value : str
        Previous email
    new_value : str
        New email to validate
    """
    # Simulate async validation (e.g., checking against API)
    await asyncio.sleep(0.1)

    errors = []

    if new_value and "@" not in new_value:
        errors.append("Email must contain @")

    if new_value and len(new_value) < 5:
        errors.append("Email too short")

    # Update validation errors
    app.state["validation_errors"] = errors


def update_derived_state(key, old_value, new_value):
    """Update derived state based on counter changes.

    This watcher computes derived values whenever the counter changes.

    Parameters
    ----------
    key : str
        The state key ("counter")
    old_value : int
        Previous counter value
    new_value : int
        New counter value
    """
    # Compute derived state
    app.state["counter_squared"] = new_value ** 2


def check_form_completeness(key, old_value, new_value):
    """Check if form is complete when username or email changes.

    Parameters
    ----------
    key : str
        The state key
    old_value : str
        Previous value
    new_value : str
        New value
    """
    username = app.state.get("username", "")
    email = app.state.get("email", "")
    errors = app.state.get("validation_errors", [])

    # Form is complete if both fields filled and no errors
    complete = bool(username) and bool(email) and len(errors) == 0
    app.state["form_complete"] = complete


# Register state callbacks and watchers
def setup_state_watchers():
    """Set up all state watchers and callbacks."""
    # Global change callback (fires for ANY state change)
    app.state.on_change(log_state_change)

    # Watch specific keys
    app.state.watch("counter", update_derived_state)
    app.state.watch("email", validate_email_async)
    app.state.watch("username", check_form_completeness)
    app.state.watch("email", check_form_completeness)


@app.view("main", default=True)
def main_view():
    """Main demo view showing state management features.

    Returns
    -------
    dict
        View configuration with template and data
    """
    change_log_text = "\n".join(app.state.get("change_log", [])[-5:])
    if not change_log_text:
        change_log_text = "No changes yet..."

    errors_text = "\n".join(app.state.get("validation_errors", []))
    if not errors_text:
        errors_text = "No errors"

    return {
        "template": """
{% frame title="State Management Demo" border="double" width=100 height=38 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Status: {{ state.status }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=45 %}
        {% frame title="State Controls" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% vstack spacing=0 %}
              Counter: {{ state.counter }}
              Derived: counter² = {{ state.counter_squared }}
            {% endvstack %}

            {% hstack spacing=2 %}
              {% button action="increment" %}Increment{% endbutton %}
              {% button action="decrement" %}Decrement{% endbutton %}
              {% button action="reset_counter" %}Reset{% endbutton %}
            {% endhstack %}

            {% vstack spacing=0 %}
              Username:
            {% endvstack %}
            {% textinput id="username" placeholder="Enter username..." width=40 %}{% endtextinput %}

            {% vstack spacing=0 %}
              Email (async validation):
            {% endvstack %}
            {% textinput id="email" placeholder="Enter email..." width=40 %}{% endtextinput %}

            {% vstack spacing=0 %}
              Validation: {{ errors_text }}
            {% endvstack %}

            {% vstack spacing=0 %}
              Form Status: {{ 'Complete ✓' if state.form_complete else 'Incomplete' }}
            {% endvstack %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=50 %}
        {% frame title="State Change Log (Last 5)" border="single" width="fill" height=20 %}
          {% vstack padding=1 %}
{{ change_log_text }}
          {% endvstack %}
        {% endframe %}

        {% frame title="Watcher Info" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Active Watchers:
            • counter → update_derived_state()
            • email → validate_email_async()
            • username/email → check_form_completeness()

            Global Callbacks:
            • log_state_change() (all changes)
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="submit" %}Submit Form{% endbutton %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
      {% button action="reset_all" %}Reset All{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Features Demonstrated:
      • Global state.on_change() callback logs all changes
      • Key-specific state.watch() for counter, email, username
      • Async validation callback for email field
      • Derived state (counter_squared) computed automatically
      • Form completeness checking across multiple fields

      [q] Quit | Try changing values to see state watchers in action!
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "change_log_text": change_log_text,
            "errors_text": errors_text,
        },
    }


# Action handlers
@app.on_action("increment")
def handle_increment(event):
    """Increment counter (triggers watchers).

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["counter"] += 1
    app.state["status"] = f"Counter incremented to {app.state['counter']}"


@app.on_action("decrement")
def handle_decrement(event):
    """Decrement counter (triggers watchers).

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["counter"] -= 1
    app.state["status"] = f"Counter decremented to {app.state['counter']}"


@app.on_action("reset_counter")
def handle_reset_counter(event):
    """Reset counter to zero.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["counter"] = 0
    app.state["status"] = "Counter reset"


@app.on_action("submit")
def handle_submit(event):
    """Submit form if complete.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    if app.state.get("form_complete"):
        username = app.state.get("username")
        email = app.state.get("email")
        app.state["status"] = f"Form submitted! User: {username}, Email: {email}"
    else:
        app.state["status"] = "Cannot submit - form incomplete or has errors"


@app.on_action("clear_log")
def handle_clear_log(event):
    """Clear the change log.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    state_history.clear()
    app.state["change_log"] = []
    app.state["status"] = "Change log cleared"


@app.on_action("reset_all")
def handle_reset_all(event):
    """Reset all state to initial values.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["counter"] = 0
    app.state["username"] = ""
    app.state["email"] = ""
    app.state["validation_errors"] = []
    app.state["counter_squared"] = 0
    app.state["form_complete"] = False
    app.state["status"] = "All state reset"


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
    """Handle 'q' key to quit.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.quit()


if __name__ == "__main__":
    # Set up state watchers before running
    setup_state_watchers()

    print("State Management Demo")
    print("=" * 50)
    print()
    print("This demo shows advanced state management patterns:")
    print()
    print("State Callbacks:")
    print("  • on_change() - Global callback for any state change")
    print("  • watch(key, callback) - Key-specific watchers")
    print("  • Async callbacks - Asynchronous validation/processing")
    print()
    print("Patterns Demonstrated:")
    print("  • Derived state (counter_squared computed from counter)")
    print("  • Async validation (email validation with simulated delay)")
    print("  • Multi-field validation (form completeness)")
    print("  • Change logging (all state changes tracked)")
    print()
    print("Try:")
    print("  1. Increment/decrement counter (watch derived state update)")
    print("  2. Enter email without @ (see async validation)")
    print("  3. Fill both username and email (see form complete)")
    print("  4. Watch the change log update in real-time")
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
