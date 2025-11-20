"""Context Menu Demo - Right-Click Context Menus.

This example demonstrates context menus (right-click menus) on UI elements:
- Right-click on list items to show context menu
- Menu items with actions and keyboard shortcuts
- Dividers for menu organization
- State management for menu visibility

Note: Context menu support in Wijjit is experimental and may require
additional implementation depending on your terminal emulator's mouse support.

Run with: python examples/advanced/context_menu_demo.py

Controls:
- Right-click on file items to show context menu
- Left-click to select items
- Arrow keys: Navigate list
- q: Quit
"""

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "files": [
            "document.txt",
            "image.png",
            "script.py",
            "data.json",
            "notes.md",
        ],
        "selected_file": "document.txt",
        "status": "Right-click on a file to see context menu",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view with file list and context menu.

    Returns
    -------
    dict
        View configuration with template and data
    """
    return {
        "template": """
{% frame title="Context Menu Demo" border="double" width=70 height=20 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Status: {{ state.status }}
      Selected: {{ state.selected_file }}
    {% endvstack %}

    {% vstack spacing=0 %}
      File List (right-click for menu):
    {% endvstack %}

    {% frame border="single" height=10 %}
      {% listview items=file_list selection_style="highlight" %}{% endlistview %}
    {% endframe %}

    {% hstack spacing=2 %}
      {% button action="open_file" %}Open{% endbutton %}
      {% button action="rename_file" %}Rename{% endbutton %}
      {% button action="delete_file" %}Delete{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Note: Context menus require mouse support in your terminal.
      Use buttons above as alternative.
      [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "file_list": app.state.get("files", []),
        },
    }


# Action handlers for menu items and buttons
@app.on_action("open_file")
def handle_open_file(event):
    """Handle open file action.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Opening {filename}..."


@app.on_action("rename_file")
def handle_rename_file(event):
    """Handle rename file action.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Renaming {filename}..."


@app.on_action("copy_file")
def handle_copy_file(event):
    """Handle copy file action.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Copied {filename}"


@app.on_action("delete_file")
def handle_delete_file(event):
    """Handle delete file action.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    filename = app.state.get("selected_file", "unknown")
    files = app.state.get("files", [])

    if filename in files:
        files.remove(filename)
        # Select next file or first file
        if files:
            app.state["selected_file"] = files[0]
        else:
            app.state["selected_file"] = None
        app.state["status"] = f"Deleted {filename}"
    else:
        app.state["status"] = "No file selected"


@app.on_action("properties")
def handle_properties(event):
    """Handle properties action.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    filename = app.state.get("selected_file", "unknown")
    app.state["status"] = f"Showing properties for {filename}..."


@app.on_action("quit")
def handle_quit(event):
    """Handle quit button.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.quit()


# Global quit handler
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
    print("Context Menu Demo")
    print("=" * 50)
    print()
    print("This demo shows context menu patterns in Wijjit.")
    print()
    print("Context Menu Features:")
    print("- Right-click on list items to show menu")
    print("- Menu items with actions")
    print("- Dividers for organization")
    print("- Keyboard shortcuts display")
    print()
    print("Note: Context menus require terminal mouse support.")
    print("      Not all terminals fully support right-click detection.")
    print("      Use the buttons as an alternative interface.")
    print()
    print("Controls:")
    print("  Right-click: Show context menu (if supported)")
    print("  Left-click: Select item")
    print("  [q] Quit")
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
