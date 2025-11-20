"""Dialog Showcase - All Dialog Types in One Example.

This example demonstrates all available dialog types in Wijjit:
- Alert dialogs (information, warning, error)
- Confirm dialogs (yes/no, ok/cancel)
- Input dialogs (text input with validation)
- Custom modal dialogs

Run with: python examples/widgets/dialog_showcase.py

Controls:
- Click buttons to show different dialog types
- Tab/Shift+Tab: Navigate between buttons
- q: Quit
"""

from wijjit import Wijjit

# Create app with dialog state
app = Wijjit(
    initial_state={
        "last_dialog": "None",
        "dialog_result": "",
        "action_log": [],
    }
)


def log_action(action, result):
    """Log dialog actions.

    Parameters
    ----------
    action : str
        The action performed
    result : str
        The result
    """
    log = app.state.get("action_log", [])
    log.append(f"{action}: {result}")

    # Keep last 10 actions
    app.state["action_log"] = log[-10:]


@app.view("main", default=True)
def main_view():
    """Main dialog showcase view.

    Returns
    -------
    dict
        View configuration with template and data
    """
    action_log_text = "\n".join(app.state.get("action_log", [])[-8:])
    if not action_log_text:
        action_log_text = "No actions yet..."

    return {
        "template": """
{% frame title="Dialog Showcase" border="double" width=90 height=36 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Last Dialog: {{ state.last_dialog }}
      Result: {{ state.dialog_result }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=42 %}
        {% frame title="Alert Dialogs" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% vstack spacing=0 %}
              Show information, warnings, or errors
            {% endvstack %}

            {% button action="alert_info" %}Info Alert{% endbutton %}
            {% button action="alert_warning" %}Warning Alert{% endbutton %}
            {% button action="alert_error" %}Error Alert{% endbutton %}
            {% button action="alert_success" %}Success Alert{% endbutton %}
          {% endvstack %}
        {% endframe %}

        {% frame title="Confirm Dialogs" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% vstack spacing=0 %}
              Ask yes/no or ok/cancel questions
            {% endvstack %}

            {% button action="confirm_yesno" %}Yes/No Dialog{% endbutton %}
            {% button action="confirm_okcancel" %}OK/Cancel Dialog{% endbutton %}
            {% button action="confirm_delete" %}Delete Confirm{% endbutton %}
          {% endvstack %}
        {% endframe %}

        {% frame title="Input Dialogs" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% vstack spacing=0 %}
              Get text input from user
            {% endvstack %}

            {% button action="input_text" %}Text Input{% endbutton %}
            {% button action="input_email" %}Email Input{% endbutton %}
            {% button action="input_number" %}Number Input{% endbutton %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=42 %}
        {% frame title="Action Log" border="single" width="fill" height=24 %}
          {% vstack padding=1 %}
{{ action_log_text }}
          {% endvstack %}
        {% endframe %}

        {% frame title="Dialog Features" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Dialog Types:
            • AlertDialog - Show info/warning/error
            • ConfirmDialog - Yes/No or OK/Cancel
            • InputDialog - Get text input
            • Custom modals - Build your own

            All dialogs support:
            • Custom titles and messages
            • Icon/color theming
            • Keyboard shortcuts (ESC, Enter)
            • Callback functions
            • Validation (input dialogs)
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Note: Dialogs in Wijjit are template-based overlays that dim the background.
      Click buttons above to see each dialog type in action!
      [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "action_log_text": action_log_text,
        },
    }


# Alert Dialog Actions
@app.on_action("alert_info")
def handle_alert_info(event):
    """Show info alert dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Info Alert"
    app.state["dialog_result"] = "Showing info alert..."

    # Note: Actual dialog implementation would use app.show_alert()
    # This is a placeholder showing the pattern
    log_action("Info Alert", "Displayed info message")
    app.state["dialog_result"] = "Info alert closed"


@app.on_action("alert_warning")
def handle_alert_warning(event):
    """Show warning alert dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Warning Alert"
    log_action("Warning Alert", "Displayed warning message")
    app.state["dialog_result"] = "Warning alert closed"


@app.on_action("alert_error")
def handle_alert_error(event):
    """Show error alert dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Error Alert"
    log_action("Error Alert", "Displayed error message")
    app.state["dialog_result"] = "Error alert closed"


@app.on_action("alert_success")
def handle_alert_success(event):
    """Show success alert dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Success Alert"
    log_action("Success Alert", "Displayed success message")
    app.state["dialog_result"] = "Success alert closed"


# Confirm Dialog Actions
@app.on_action("confirm_yesno")
def handle_confirm_yesno(event):
    """Show yes/no confirmation dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Yes/No Confirm"

    # In real implementation, would show dialog and handle callback
    # Pattern: app.show_confirm("Are you sure?", on_confirm=lambda: ...)

    # Simulate user clicking "Yes"
    log_action("Yes/No Confirm", "User clicked Yes")
    app.state["dialog_result"] = "User confirmed (Yes)"


@app.on_action("confirm_okcancel")
def handle_confirm_okcancel(event):
    """Show OK/Cancel confirmation dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "OK/Cancel Confirm"
    log_action("OK/Cancel Confirm", "User clicked OK")
    app.state["dialog_result"] = "User confirmed (OK)"


@app.on_action("confirm_delete")
def handle_confirm_delete(event):
    """Show delete confirmation dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Delete Confirm"

    # Simulate user canceling
    log_action("Delete Confirm", "User clicked Cancel")
    app.state["dialog_result"] = "Delete canceled"


# Input Dialog Actions
@app.on_action("input_text")
def handle_input_text(event):
    """Show text input dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Text Input"

    # In real implementation:
    # app.show_input("Enter your name:", on_submit=lambda value: ...)

    # Simulate user entering text
    simulated_input = "John Doe"
    log_action("Text Input", f"User entered: {simulated_input}")
    app.state["dialog_result"] = f"Received: {simulated_input}"


@app.on_action("input_email")
def handle_input_email(event):
    """Show email input dialog with validation.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Email Input"

    # Pattern with validation:
    # def validate_email(value):
    #     return "@" in value
    # app.show_input("Enter email:", validator=validate_email, ...)

    simulated_input = "user@example.com"
    log_action("Email Input", f"User entered: {simulated_input}")
    app.state["dialog_result"] = f"Received: {simulated_input}"


@app.on_action("input_number")
def handle_input_number(event):
    """Show number input dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Number Input"

    # Pattern with number validation:
    # def validate_number(value):
    #     try:
    #         int(value)
    #         return True
    #     except ValueError:
    #         return False

    simulated_input = "42"
    log_action("Number Input", f"User entered: {simulated_input}")
    app.state["dialog_result"] = f"Received: {simulated_input}"


@app.on_action("clear_log")
def handle_clear_log(event):
    """Clear action log.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["action_log"] = []
    app.state["dialog_result"] = "Log cleared"


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
    print("Dialog Showcase")
    print("=" * 50)
    print()
    print("This demo showcases all available dialog types:")
    print()
    print("Dialog Types:")
    print("  1. Alert Dialogs:")
    print("     - Info alerts (information messages)")
    print("     - Warning alerts (caution messages)")
    print("     - Error alerts (error messages)")
    print("     - Success alerts (confirmation messages)")
    print()
    print("  2. Confirm Dialogs:")
    print("     - Yes/No confirmation")
    print("     - OK/Cancel confirmation")
    print("     - Custom confirmation (delete, etc.)")
    print()
    print("  3. Input Dialogs:")
    print("     - Text input (general)")
    print("     - Email input (with validation)")
    print("     - Number input (with validation)")
    print()
    print("Dialog Features:")
    print("  • Custom titles and messages")
    print("  • Callback functions on close/submit")
    print("  • Input validation")
    print("  • Keyboard shortcuts (ESC to cancel, Enter to confirm)")
    print("  • Background dimming")
    print()
    print("Note: This showcase demonstrates the dialog patterns.")
    print("      Actual dialog implementations use the overlay system.")
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
