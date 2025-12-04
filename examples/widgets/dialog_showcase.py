"""Dialog Showcase - All Dialog Types in One Example.

This example demonstrates all available dialog types in Wijjit:
- Alert dialogs (information, warning, error, success)
- Confirm dialogs (yes/no, ok/cancel)
- Input dialogs (text input)

Run with: python examples/widgets/dialog_showcase.py

Controls:
- Click buttons to show different dialog types
- Tab/Shift+Tab: Navigate between buttons
- ESC: Close dialog
- Ctrl+Q: Quit app
"""

import shutil

from wijjit import Wijjit
from wijjit.elements.modal import AlertDialog, ConfirmDialog, TextInputDialog
from wijjit.layout.bounds import Bounds

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


def show_centered_dialog(dialog):
    """Show a dialog centered on the screen.

    Parameters
    ----------
    dialog : Element
        The dialog element to show

    Returns
    -------
    Overlay
        The overlay containing the dialog
    """
    term_size = shutil.get_terminal_size()
    x = (term_size.columns - dialog.width) // 2
    y = (term_size.lines - dialog.height) // 2
    dialog.bounds = Bounds(x=x, y=y, width=dialog.width, height=dialog.height)

    overlay = app.show_modal(dialog)

    def close_dialog():
        app.overlay_manager.pop(overlay)

    dialog.close_callback = close_dialog
    return overlay


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
{% frame title="Dialog Showcase" border="double" width=90 height=28 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Last Dialog: {{ state.last_dialog }}
      Result: {{ state.dialog_result }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=42 %}
        {% frame title="Alert Dialogs" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% button action="alert_info" %}Info Alert{% endbutton %}
            {% button action="alert_warning" %}Warning Alert{% endbutton %}
            {% button action="alert_error" %}Error Alert{% endbutton %}
            {% button action="alert_success" %}Success Alert{% endbutton %}
          {% endvstack %}
        {% endframe %}

        {% frame title="Confirm Dialogs" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% button action="confirm_yesno" %}Yes/No Dialog{% endbutton %}
            {% button action="confirm_okcancel" %}OK/Cancel Dialog{% endbutton %}
            {% button action="confirm_delete" %}Delete Confirm{% endbutton %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=42 %}
        {% frame title="Input Dialogs" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% button action="input_text" %}Text Input{% endbutton %}
            {% button action="input_name" %}Name Input{% endbutton %}
          {% endvstack %}
        {% endframe %}

        {% frame title="Action Log" border="single" width="fill" height=12 %}
          {% vstack padding=1 %}
{{ action_log_text }}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}
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
    app.state["dialog_result"] = "Showing..."

    def on_ok():
        log_action("Info Alert", "User clicked OK")
        app.state["dialog_result"] = "Info acknowledged"

    dialog = AlertDialog(
        title="Information",
        message="This is an informational message. It provides helpful context about the current state or action.",
        on_ok=on_ok,
        ok_label="Got it",
        severity="info",
        width=50,
    )
    show_centered_dialog(dialog)


@app.on_action("alert_warning")
def handle_alert_warning(event):
    """Show warning alert dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Warning Alert"
    app.state["dialog_result"] = "Showing..."

    def on_ok():
        log_action("Warning Alert", "User acknowledged warning")
        app.state["dialog_result"] = "Warning acknowledged"

    dialog = AlertDialog(
        title="Warning",
        message="This is a warning message. Please proceed with caution as this action may have consequences.",
        on_ok=on_ok,
        ok_label="Understood",
        severity="warning",
        width=50,
    )
    show_centered_dialog(dialog)


@app.on_action("alert_error")
def handle_alert_error(event):
    """Show error alert dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Error Alert"
    app.state["dialog_result"] = "Showing..."

    def on_ok():
        log_action("Error Alert", "User dismissed error")
        app.state["dialog_result"] = "Error dismissed"

    dialog = AlertDialog(
        title="Error",
        message="An error occurred while processing your request. Please try again or contact support if the problem persists.",
        on_ok=on_ok,
        ok_label="Dismiss",
        severity="error",
        width=50,
    )
    show_centered_dialog(dialog)


@app.on_action("alert_success")
def handle_alert_success(event):
    """Show success alert dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Success Alert"
    app.state["dialog_result"] = "Showing..."

    def on_ok():
        log_action("Success Alert", "User acknowledged success")
        app.state["dialog_result"] = "Operation successful"

    dialog = AlertDialog(
        title="Success",
        message="Operation completed successfully! Your changes have been saved.",
        on_ok=on_ok,
        ok_label="Great!",
        severity="success",
        width=50,
    )
    show_centered_dialog(dialog)


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
    app.state["dialog_result"] = "Showing..."

    def on_confirm():
        log_action("Yes/No Confirm", "User clicked Yes")
        app.state["dialog_result"] = "User confirmed (Yes)"

    def on_cancel():
        log_action("Yes/No Confirm", "User clicked No")
        app.state["dialog_result"] = "User declined (No)"

    dialog = ConfirmDialog(
        title="Confirm Action",
        message="Are you sure you want to proceed with this action?",
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        confirm_label="Yes",
        cancel_label="No",
        width=50,
    )
    show_centered_dialog(dialog)


@app.on_action("confirm_okcancel")
def handle_confirm_okcancel(event):
    """Show OK/Cancel confirmation dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "OK/Cancel Confirm"
    app.state["dialog_result"] = "Showing..."

    def on_confirm():
        log_action("OK/Cancel Confirm", "User clicked OK")
        app.state["dialog_result"] = "User confirmed (OK)"

    def on_cancel():
        log_action("OK/Cancel Confirm", "User clicked Cancel")
        app.state["dialog_result"] = "User cancelled"

    dialog = ConfirmDialog(
        title="Confirm",
        message="Do you want to save your changes before closing?",
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        confirm_label="OK",
        cancel_label="Cancel",
        width=50,
    )
    show_centered_dialog(dialog)


@app.on_action("confirm_delete")
def handle_confirm_delete(event):
    """Show delete confirmation dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Delete Confirm"
    app.state["dialog_result"] = "Showing..."

    def on_confirm():
        log_action("Delete Confirm", "User confirmed deletion")
        app.state["dialog_result"] = "Item deleted"

    def on_cancel():
        log_action("Delete Confirm", "User cancelled deletion")
        app.state["dialog_result"] = "Deletion cancelled"

    dialog = ConfirmDialog(
        title="Confirm Delete",
        message="Are you sure you want to delete this item? This action cannot be undone.",
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        confirm_label="Delete",
        cancel_label="Cancel",
        width=50,
    )
    show_centered_dialog(dialog)


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
    app.state["dialog_result"] = "Showing..."

    def on_submit(value):
        log_action("Text Input", f"User entered: {value}")
        app.state["dialog_result"] = f"Received: {value}"

    def on_cancel():
        log_action("Text Input", "User cancelled")
        app.state["dialog_result"] = "Input cancelled"

    dialog = TextInputDialog(
        title="Text Input",
        prompt="Enter some text:",
        placeholder="Type here...",
        on_submit=on_submit,
        on_cancel=on_cancel,
        submit_label="Submit",
        cancel_label="Cancel",
        width=50,
    )
    show_centered_dialog(dialog)


@app.on_action("input_name")
def handle_input_name(event):
    """Show name input dialog.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_dialog"] = "Name Input"
    app.state["dialog_result"] = "Showing..."

    def on_submit(value):
        if value.strip():
            log_action("Name Input", f"User entered: {value}")
            app.state["dialog_result"] = f"Hello, {value}!"
        else:
            log_action("Name Input", "Empty name entered")
            app.state["dialog_result"] = "Name cannot be empty"

    def on_cancel():
        log_action("Name Input", "User cancelled")
        app.state["dialog_result"] = "Input cancelled"

    dialog = TextInputDialog(
        title="Enter Your Name",
        prompt="What is your name?",
        placeholder="John Doe",
        on_submit=on_submit,
        on_cancel=on_cancel,
        submit_label="OK",
        cancel_label="Cancel",
        width=50,
    )
    show_centered_dialog(dialog)


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
    app.run()
