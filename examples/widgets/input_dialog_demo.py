"""Demo of TextInputDialog for text input prompts.

This example shows how to use the TextInputDialog class to prompt
users for text input programmatically.

Controls:
    n - Show new file dialog
    r - Show rename dialog
    ESC - Close dialog / quit app
"""

from wijjit.core.app import Wijjit
from wijjit.elements.modal import TextInputDialog

app = Wijjit(
    initial_state={
        "files": ["document.txt", "notes.txt"],
        "selected_index": 0,
        "message": "",
    }
)
state = app.state


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame width=60 height=18 title="Text Input Dialog Demo" %}
        Files:
        {% for file in state['files'] %}
            {% if loop.index0 == state['selected_index'] %}
              > {{ file }}  (selected)
            {% else %}
              - {{ file }}
            {% endif %}
        {% endfor %}

        {% if state['message'] %}

            {{ state['message'] }}
        {% endif %}


        Keyboard Shortcuts:
          n - Create new file
          r - Rename selected file
          up/down - Select file

{% endframe %}
        """
    }


@app.on_key("n")
def show_new_file_dialog(event):
    """Show new file dialog."""

    def on_submit(filename):
        if filename.strip():
            state["files"].append(filename.strip())
            state["message"] = f"Created: {filename}"
        else:
            state["message"] = "Filename cannot be empty"
        state["_refresh"] = True

    def on_cancel():
        state["message"] = "Action cancelled"
        state["_refresh"] = True

    dialog = TextInputDialog(
        title="New File",
        prompt="Enter filename:",
        placeholder="untitled.txt",
        on_submit=on_submit,
        on_cancel=on_cancel,
        submit_label="Create",
        cancel_label="Cancel",
        width=55,
        height=12,
        input_width=35,
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


@app.on_key("r")
def show_rename_dialog(event):
    """Show rename dialog for selected file."""
    if not state["files"]:
        state["message"] = "No files to rename"
        state["_refresh"] = True
        return

    selected_file = state["files"][state["selected_index"]]

    def on_submit(new_name):
        if new_name.strip():
            state["files"][state["selected_index"]] = new_name.strip()
            state["message"] = f"Renamed to: {new_name}"
        else:
            state["message"] = "Filename cannot be empty"
        state["_refresh"] = True

    def on_cancel():
        state["message"] = "Rename cancelled"
        state["_refresh"] = True

    dialog = TextInputDialog(
        title="Rename File",
        prompt=f"Rename '{selected_file}' to:",
        initial_value=selected_file,
        on_submit=on_submit,
        on_cancel=on_cancel,
        submit_label="Rename",
        cancel_label="Cancel",
        width=55,
        height=12,
        input_width=35,
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


@app.on_key("up")
def move_up(event):
    """Move selection up."""
    if state["selected_index"] > 0:
        state["selected_index"] -= 1
        state["_refresh"] = True


@app.on_key("down")
def move_down(event):
    """Move selection down."""
    if state["selected_index"] < len(state["files"]) - 1:
        state["selected_index"] += 1
        state["_refresh"] = True


if __name__ == "__main__":
    app.run()
