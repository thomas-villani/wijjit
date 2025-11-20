"""Dropdown Menu Demo.

This example demonstrates dropdown menus with keyboard shortcuts.
Click the buttons to open menus, use arrow keys to navigate, Enter to select.
"""

from wijjit import Wijjit

# Create app
app = Wijjit()


# Template with dropdown menus
TEMPLATE = """
{% vstack width="fill" height="fill" %}
    {% hstack spacing=2 padding=1 %}
        {% button id="file_btn" action="toggle_file_menu" %}File{% endbutton %}
        {% button id="edit_btn" action="toggle_edit_menu" %}Edit{% endbutton %}
    {% endhstack %}

    {% frame title="Dropdown Menu Demo" width="fill" height="fill" %}
        Click the buttons above to open dropdown menus.

        Try these features:
        - Click "File" or "Edit" buttons to open menus
        - Press Alt+F to open File menu, Alt+E for Edit menu
        - Use arrow keys to navigate menu items
        - Press Enter to select an item
        - Press ESC to close menu
        - Click outside menu to close
        - Menu item shortcuts (Ctrl+N, etc.) work anytime

        Status: {{ state.status }}
        File menu: {{ 'Open' if state.show_file_menu else 'Closed' }}
        Edit menu: {{ 'Open' if state.show_edit_menu else 'Closed' }}
    {% endframe %}
{% endvstack %}

{% dropdown trigger="File" key="Alt+F" visible="show_file_menu" %}
    {% menuitem action="new_file" key="Ctrl+N" %}New File{% endmenuitem %}
    {% menuitem action="open_file" key="Ctrl+O" %}Open File{% endmenuitem %}
    {% menuitem action="save_file" key="Ctrl+S" %}Save File{% endmenuitem %}
    {% menuitem divider=true %}{% endmenuitem %}
    {% menuitem action="quit" key="Ctrl+Q" %}Quit{% endmenuitem %}
{% enddropdown %}

{% dropdown trigger="Edit" key="Alt+E" visible="show_edit_menu" %}
    {% menuitem action="undo" key="Ctrl+Z" %}Undo{% endmenuitem %}
    {% menuitem action="redo" key="Ctrl+Y" %}Redo{% endmenuitem %}
    {% menuitem divider=true %}{% endmenuitem %}
    {% menuitem action="cut" key="Ctrl+X" %}Cut{% endmenuitem %}
    {% menuitem action="copy" key="Ctrl+D" %}Copy{% endmenuitem %}
    {% menuitem action="paste" key="Ctrl+V" %}Paste{% endmenuitem %}
{% enddropdown %}
"""


# View
@app.view("main", default=True)
def main_view():
    """Main view with dropdown menus."""
    return {
        "template": TEMPLATE,
        "data": {
            "status": app.state.get("status", "Ready"),
            "show_file_menu": app.state.get("show_file_menu", False),
            "show_edit_menu": app.state.get("show_edit_menu", False),
        },
    }


# Toggle menu actions
@app.on_action("toggle_file_menu")
def toggle_file_menu(event):
    """Toggle File menu visibility."""
    app.state["show_file_menu"] = not app.state.get("show_file_menu", False)
    app.state["show_edit_menu"] = False  # Close other menu


@app.on_action("toggle_edit_menu")
def toggle_edit_menu(event):
    """Toggle Edit menu visibility."""
    app.state["show_edit_menu"] = not app.state.get("show_edit_menu", False)
    app.state["show_file_menu"] = False  # Close other menu


# File menu actions
@app.on_action("new_file")
def new_file(event):
    """Create a new file."""
    app.state["status"] = "Creating new file..."
    app.state["show_file_menu"] = False


@app.on_action("open_file")
def open_file(event):
    """Open a file."""
    app.state["status"] = "Opening file..."
    app.state["show_file_menu"] = False


@app.on_action("save_file")
def save_file(event):
    """Save the current file."""
    app.state["status"] = "Saving file..."
    app.state["show_file_menu"] = False


@app.on_action("quit")
def quit_app(event):
    """Quit the application."""
    app.state["show_file_menu"] = False
    app.quit()


# Edit menu actions
@app.on_action("undo")
def undo(event):
    """Undo last action."""
    app.state["status"] = "Undoing..."
    app.state["show_edit_menu"] = False


@app.on_action("redo")
def redo(event):
    """Redo last action."""
    app.state["status"] = "Redoing..."
    app.state["show_edit_menu"] = False


@app.on_action("cut")
def cut(event):
    """Cut selection."""
    app.state["status"] = "Cut to clipboard"
    app.state["show_edit_menu"] = False


@app.on_action("copy")
def copy(event):
    """Copy selection."""
    app.state["status"] = "Copied to clipboard"
    app.state["show_edit_menu"] = False


@app.on_action("paste")
def paste(event):
    """Paste from clipboard."""
    app.state["status"] = "Pasted from clipboard"
    app.state["show_edit_menu"] = False


if __name__ == "__main__":
    # Initialize state
    app.state["status"] = "Ready"
    app.state["show_file_menu"] = False
    app.state["show_edit_menu"] = False

    # Run the app
    app.run()
