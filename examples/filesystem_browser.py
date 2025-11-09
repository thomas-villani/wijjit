"""Filesystem browser using load_filesystem_tree helper.

This example demonstrates:
- Using load_filesystem_tree helper to load actual filesystem
- Browsing a real directory structure
- Excluding common patterns (.git, __pycache__, etc.)
- Displaying file metadata (size)
"""

import sys
from pathlib import Path

from wijjit import Wijjit, load_filesystem_tree
from wijjit.core.events import EventType, HandlerScope

# Get directory to browse from command line, default to current directory
if len(sys.argv) > 1:
    browse_path = sys.argv[1]
else:
    browse_path = "."

# Load filesystem tree with common exclusions
try:
    file_tree_data = load_filesystem_tree(
        browse_path,
        max_depth=5,  # Limit depth to avoid huge trees
        show_hidden=False,  # Don't show hidden files by default
        include_metadata=True,  # Show file sizes
        exclude=[
            "*.pyc",
            "*.pyo",
            "__pycache__",
            ".git",
            ".venv",
            "node_modules",
            ".pytest_cache",
            "*.egg-info",
        ],
    )
except (FileNotFoundError, NotADirectoryError) as e:
    print(f"Error: {e}")
    sys.exit(1)

# Get absolute path for display
abs_path = str(Path(browse_path).resolve())

# Create app with loaded tree
app = Wijjit(
    initial_state={
        "file_tree": file_tree_data,
        "expanded_nodes": [file_tree_data["value"]],  # Expand root by default
        "selected_file": None,
        "browse_path": abs_path,
        "message": f"Browsing: {abs_path}",
    }
)


@app.view("main", default=True)
def main_view():
    """Main filesystem browser view."""
    return {
        "template": """
{% frame title="Filesystem Browser" border="double" width=100 height=35 %}
  {% vstack spacing=1 padding=1 %}
    {{ state.message }}

    Press 'q' to quit | Arrow keys navigate | Left/Right expand/collapse | Enter/Space toggle

    {% hstack spacing=2 align_v="top" height=22 %}
      {% vstack spacing=0 width=54 %}
        {% frame title="Directory Tree" border="single" width="fill" height=20 %}
          {% tree id="filetree"
                  data=state.file_tree
                  width=50
                  height=18
                  show_scrollbar=true
                  show_root=true
                  expanded="expanded_nodes"
                  on_select="file_selected" %}
          {% endtree %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=0 width=42 %}
        {% frame title="Details" border="single" width="fill" height=20 %}
          {% if state.selected_file %}
            Name: {{ state.selected_file.label }}

            Path: {{ state.selected_file.value }}

            Type: {{ state.selected_file.get('type', 'unknown') }}

            {% if state.selected_file.get('size') %}
            Size: {{ state.selected_file.size }}
            {% endif %}

            {% if state.selected_file.get('children') %}

            Children: {{ state.selected_file.children|length }} items
            {% endif %}
          {% else %}
            No item selected.

            Click on a file or folder
            to see details.
          {% endif %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button id="expand_all_btn" action="expand_all" %}Expand All{% endbutton %}
      {% button id="collapse_all_btn" action="collapse_all" %}Collapse All{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,  # noqa: E501
        "data": {},
    }


@app.on_action("file_selected")
def handle_file_selected(event):
    """Handle file/folder selection in tree."""
    if event.data:
        app.state["selected_file"] = event.data
        item_type = event.data.get("type", "item")
        app.state["message"] = f"Selected {item_type}: {event.data['label']}"
    else:
        app.state["message"] = "No item selected"


def get_all_node_ids(node, ids=None):
    """Recursively get all node IDs from tree.

    Parameters
    ----------
    node : dict
        Tree node
    ids : list, optional
        List to accumulate IDs

    Returns
    -------
    list
        List of all node IDs
    """
    if ids is None:
        ids = []

    ids.append(node.get("id", node.get("value")))

    for child in node.get("children", []):
        get_all_node_ids(child, ids)

    return ids


@app.on_action("expand_all")
def handle_expand_all(event):
    """Expand all nodes in the tree."""
    tree_data = app.state.get("file_tree")
    if tree_data:
        all_ids = get_all_node_ids(tree_data)
        app.state["expanded_nodes"] = all_ids
        app.state["message"] = f"Expanded all nodes ({len(all_ids)} total)"


@app.on_action("collapse_all")
def handle_collapse_all(event):
    """Collapse all nodes in the tree."""
    app.state["expanded_nodes"] = []
    app.state["message"] = "Collapsed all nodes"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


def handle_key_q(event):
    """Handle 'q' key to quit."""
    if event.key == "q":
        app.quit()
        event.cancel()


app.on(EventType.KEY, handle_key_q, scope=HandlerScope.GLOBAL)


if __name__ == "__main__":
    app.run()
