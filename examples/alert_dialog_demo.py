"""Demo of AlertDialog for notifications and alerts.

This example shows how to use the AlertDialog class to display
simple alert messages programmatically.

Controls:
    s - Show success alert
    e - Show error alert
    i - Show info alert
    ESC - Close dialog / quit app
"""

from wijjit.core.app import Wijjit
from wijjit.elements.modal import AlertDialog

app = Wijjit(initial_state={"counter": 0})
state = app.state


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame width=60 height=15 title="Alert Dialog Demo" %}
    {% vstack %}
        Button Press Counter: {{ state['counter'] }}


        Keyboard Shortcuts:
          s - Show success alert
          e - Show error alert
          i - Show info alert
    {% endvstack %}
{% endframe %}
        """
    }


def show_alert(title, message, border="single"):
    """Helper function to show an alert dialog."""

    def on_ok():
        """Handle alert dismissal."""
        state["_refresh"] = True

    dialog = AlertDialog(
        title=title,
        message=message,
        on_ok=on_ok,
        ok_label="OK",
        width=50,
        height=9,
        border=border,
    )

    # Set bounds for centered position
    import shutil

    from wijjit.layout.bounds import Bounds

    term_size = shutil.get_terminal_size()
    x = (term_size.columns - dialog.width) // 2
    y = (term_size.lines - dialog.height) // 2
    dialog.bounds = Bounds(x=x, y=y, width=dialog.width, height=dialog.height)

    # Show the modal
    overlay = app.show_modal(dialog)

    # Set close callback
    def close_dialog():
        app.overlay_manager.pop(overlay)
        state["_refresh"] = True

    dialog.close_callback = close_dialog


@app.on_key("s")
def show_success(event):
    """Show success alert."""
    state["counter"] += 1
    state["_refresh"] = True
    show_alert(
        "Success",
        f"Operation completed successfully! This is a longer message to test text wrapping functionality. The text should wrap automatically within the dialog boundaries. (Count: {state['counter']})",
        border="double",
    )


@app.on_key("e")
def show_error(event):
    """Show error alert."""
    state["counter"] += 1
    state["_refresh"] = True
    show_alert(
        "Error",
        f"An error occurred! Something went wrong and we need to display a detailed error message that will automatically wrap to fit within the dialog width. (Count: {state['counter']})",
        border="single",
    )


@app.on_key("i")
def show_info(event):
    """Show info alert."""
    state["counter"] += 1
    state["_refresh"] = True
    show_alert(
        "Information",
        f"This is an informational message for you that contains quite a bit of text. The text wrapping feature will automatically break this into multiple lines to ensure it fits nicely within the dialog frame. (Count: {state['counter']})",
        border="rounded",
    )


if __name__ == "__main__":
    app.run()
