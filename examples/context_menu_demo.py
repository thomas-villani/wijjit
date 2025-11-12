"""Context Menu Demo.

This example demonstrates right-click context menus on UI elements,
similar to file explorers and other applications.
"""

from wijjit import Wijjit
from wijjit.core.events import EventType

# Create app
app = Wijjit()


# Template with context menu
TEMPLATE = """
{% vstack width="fill" height="fill" spacing=1 %}
    {% frame title="Context Menu Demo" width="fill" height=8 %}
        Right-click on the file list below to open a context menu.

        Current selection: {{ state.selected_file or "None" }}
        Status: {{ state.status }}
    {% endframe %}

    {% frame id="file_list" title="Files" width="fill" height="fill" border="single" %}
        {% vstack %}
            document.txt
            image.png
            script.py
            data.json
            notes.md
        {% endvstack %}
    {% endframe %}
{% endvstack %}

{% contextmenu target="file_list" visible="show_context_menu" %}
    {% menuitem action="open_file" %}Open{% endmenuitem %}
    {% menuitem action="rename_file" %}Rename{% endmenuitem %}
    {% menuitem action="copy_file" %}Copy{% endmenuitem %}
    {% menuitem divider=true %}{% endmenuitem %}
    {% menuitem action="delete_file" %}Delete{% endmenuitem %}
    {% menuitem divider=true %}{% endmenuitem %}
    {% menuitem action="properties" %}Properties{% endmenuitem %}
{% endcontextmenu %}
"""


# View
@app.view("main", default=True)
def main_view():
    """Main view with context menu."""
    return {
        "template": TEMPLATE,
        "data": {
            "status": app.state.get("status", "Ready"),
            "selected_file": app.state.get("selected_file"),
            "show_context_menu": app.state.get("show_context_menu", False),
        },
    }


# Action handlers
@app.on_action("open_file")
def open_file(event):
    """Open the selected file."""
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Opening {filename}..."
    app.state["show_context_menu"] = False


@app.on_action("rename_file")
def rename_file(event):
    """Rename the selected file."""
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Renaming {filename}..."
    app.state["show_context_menu"] = False


@app.on_action("copy_file")
def copy_file(event):
    """Copy the selected file."""
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Copied {filename}"
    app.state["show_context_menu"] = False


@app.on_action("delete_file")
def delete_file(event):
    """Delete the selected file."""
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Deleting {filename}..."
    app.state["show_context_menu"] = False


@app.on_action("properties")
def properties(event):
    """Show file properties."""
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Showing properties for {filename}..."
    app.state["show_context_menu"] = False


# Mouse handler to detect right-clicks and select files
def handle_mouse(event):
    """Handle mouse events for file selection and context menu."""
    from wijjit.terminal.mouse import MouseButton, MouseEventType

    # Get the element that was clicked
    elem = app._find_element_at(event.mouse_event.x, event.mouse_event.y)

    if elem and hasattr(elem, "id") and elem.id == "file_list":
        if event.mouse_event.type == MouseEventType.CLICK:
            # Left click - select file
            if event.mouse_event.button == MouseButton.LEFT:
                # Determine which file was clicked based on y position
                # This is a simplified approach - real apps would track line positions
                file_y = event.mouse_event.y - elem.bounds.y - 2  # Account for frame border and title
                files = [
                    "document.txt",
                    "image.png",
                    "script.py",
                    "data.json",
                    "notes.md",
                ]
                if 0 <= file_y < len(files):
                    app.state["selected_file"] = files[file_y]
                    app.state["status"] = f"Selected {files[file_y]}"

            # Right click - open context menu
            elif event.mouse_event.button == MouseButton.RIGHT:
                # Select file at cursor if not already selected
                file_y = event.mouse_event.y - elem.bounds.y - 2
                files = [
                    "document.txt",
                    "image.png",
                    "script.py",
                    "data.json",
                    "notes.md",
                ]
                if 0 <= file_y < len(files):
                    app.state["selected_file"] = files[file_y]

                # Show context menu
                app.state["show_context_menu"] = True
    else:
        # Clicked outside file list - close context menu
        if event.mouse_event.type == MouseEventType.CLICK:
            if app.state.get("show_context_menu"):
                app.state["show_context_menu"] = False


# Register mouse handler
app.on(EventType.MOUSE, handle_mouse)


if __name__ == "__main__":
    # Initialize state
    app.state["status"] = "Ready"
    app.state["selected_file"] = None
    app.state["show_context_menu"] = False

    # Run the app
    app.run()
