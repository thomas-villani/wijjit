"""Demo of ConfirmDialog for confirmation prompts.

This example shows how to use the ConfirmDialog class to create
a confirmation dialog programmatically.

Controls:
    d - Show delete confirmation dialog
    ESC - Close dialog / quit app
"""

from wijjit.core.app import Wijjit
from wijjit.elements.modal import ConfirmDialog

app = Wijjit(
    initial_state={"files": ["File1.txt", "File2.txt", "File3.txt"], "message": ""}
)
state = app.state


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame width=60 height=15 title="Confirm Dialog Demo" %}
    {% vstack %}
        Files in folder:
        {% for item in state['files'] %}
            - {{ item }}
        {% endfor %}

        {% if state['message'] %}

            {{ state['message'] }}
        {% endif %}


        Press 'd' to show delete confirmation dialog
    {% endvstack %}
{% endframe %}
        """
    }


@app.on_key("d")
def show_delete_dialog(event):
    """Show delete confirmation dialog."""
    if not state["files"]:
        state["message"] = "No files to delete"
        state["_refresh"] = True
        return

    def on_confirm():
        """Handle confirmed deletion."""
        if state["files"]:
            deleted = state["files"].pop()
            state["message"] = f"Deleted: {deleted}"
        state["_refresh"] = True

    def on_cancel():
        """Handle cancelled deletion."""
        state["message"] = "Deletion cancelled"
        state["_refresh"] = True

    # Create and show confirm dialog
    dialog = ConfirmDialog(
        title="Confirm Delete",
        message=f"Are you sure you want to delete {state['files'][-1]}?\n"
        f"This action cannot be undone and will permanently remove the file from your system.\n"
        f"Please confirm that you want to proceed with this deletion.",
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        confirm_label="Delete",
        cancel_label="Cancel",
        width=55,
        height=12,
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


if __name__ == "__main__":
    app.run()
