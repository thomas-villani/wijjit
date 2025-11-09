"""Tree demo showcasing all features.

This example demonstrates:
- Hierarchical tree display with expand/collapse
- Keyboard navigation (arrows, home/end, page up/down)
- Mouse support (click to select, click indicator to expand/collapse)
- Scrolling for large trees
- Dynamic tree updates
- State persistence for expansion and scroll position
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Sample file system tree data
file_tree_data = {
    "label": "project",
    "value": "project",
    "type": "folder",
    "children": [
        {
            "label": "src",
            "value": "src",
            "type": "folder",
            "children": [
                {
                    "label": "components",
                    "value": "src/components",
                    "type": "folder",
                    "children": [
                        {"label": "Button.py", "value": "src/components/Button.py", "type": "file", "size": "2.3 KB"},
                        {"label": "Input.py", "value": "src/components/Input.py", "type": "file", "size": "3.1 KB"},
                        {"label": "Tree.py", "value": "src/components/Tree.py", "type": "file", "size": "5.2 KB"},
                        {"label": "Table.py", "value": "src/components/Table.py", "type": "file", "size": "4.8 KB"},
                    ],
                },
                {
                    "label": "utils",
                    "value": "src/utils",
                    "type": "folder",
                    "children": [
                        {"label": "helpers.py", "value": "src/utils/helpers.py", "type": "file", "size": "1.5 KB"},
                        {"label": "validators.py", "value": "src/utils/validators.py",
                         "type": "file", "size": "2.0 KB"},
                    ],
                },
                {"label": "main.py", "value": "src/main.py", "type": "file", "size": "1.2 KB"},
                {"label": "config.py", "value": "src/config.py", "type": "file", "size": "0.8 KB"},
            ],
        },
        {
            "label": "tests",
            "value": "tests",
            "type": "folder",
            "children": [
                {"label": "test_components.py", "value": "tests/test_components.py", "type": "file", "size": "4.5 KB"},
                {"label": "test_utils.py", "value": "tests/test_utils.py", "type": "file", "size": "2.1 KB"},
            ],
        },
        {
            "label": "docs",
            "value": "docs",
            "type": "folder",
            "children": [
                {"label": "README.md", "value": "docs/README.md", "type": "file", "size": "3.2 KB"},
                {"label": "API.md", "value": "docs/API.md", "type": "file", "size": "6.7 KB"},
                {
                    "label": "examples",
                    "value": "docs/examples",
                    "type": "folder",
                    "children": [
                        {"label": "basic.md", "value": "docs/examples/basic.md", "type": "file", "size": "1.8 KB"},
                        {"label": "advanced.md", "value": "docs/examples/advanced.md",
                         "type": "file", "size": "3.4 KB"},
                    ],
                },
            ],
        },
        {"label": "README.md", "value": "README.md", "type": "file", "size": "2.1 KB"},
        {"label": "setup.py", "value": "setup.py", "type": "file", "size": "1.4 KB"},
        {"label": ".gitignore", "value": ".gitignore", "type": "file", "size": "0.3 KB"},
    ],
}

# Create app with initial state
app = Wijjit(
    initial_state={
        "file_tree": file_tree_data,
        "expanded_nodes": ["project", "src"],  # User-controlled expansion state
        "selected_file": None,
        "message": "Welcome to Tree Demo! Use arrow keys to navigate, "
                   "Left/Right to collapse/expand, Enter/Space to toggle.",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing tree element."""
    return {
        "template": """
{% frame title="Tree Demo - File System Explorer" border="double" width=100 height=35 %}
  {% vstack spacing=1 padding=1 %}
    {{ state.message }}

    Instructions: TAB to focus | Arrow keys navigate | Left/Right expand/collapse | Enter/Space toggle | Mouse wheel scrolls | Click to select | 'q' to quit

    {% hstack spacing=2 align_v="top" height=22 %}
      {% vstack spacing=0 width=48 %}
        {% frame title="File Tree" border="single" width="fill" height=18 %}
          {% tree id="filetree"
                  data=state.file_tree
                  width=44
                  height=16
                  show_scrollbar=true
                  show_root=true
                  expanded="expanded_nodes"
                  on_select="file_selected" %}
          {% endtree %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=0 width=48 %}
        {% frame title="File Details" border="single" width="fill" height=18 %}
          {% if state.selected_file %}
            Name: {{ state.selected_file.label }}

            Type: {{ state.selected_file.get('type', 'unknown') }}

            {% if state.selected_file.get('size') %}
            Size: {{ state.selected_file.size }}
            {% endif %}

            Path: {{ state.selected_file.value }}
          {% else %}
            No file selected. Click on a file or folder to see details.
          {% endif %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button id="expand_all_btn" action="expand_all" %}Expand All{% endbutton %}
      {% button id="collapse_all_btn" action="collapse_all" %}Collapse All{% endbutton %}
      {% button id="add_node_btn" action="add_node" %}Add Test Node{% endbutton %}
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
    # The event.data contains the selected node data
    if event.data:
        app.state["selected_file"] = event.data
        app.state["message"] = f"Selected: {event.data['label']}"
    else:
        app.state["message"] = "No file selected"


def find_node_in_tree(tree, node_id):
    """Recursively find a node by ID in tree data.

    Parameters
    ----------
    tree : dict
        Tree or subtree to search
    node_id : str
        Node ID to find

    Returns
    -------
    dict or None
        Found node or None
    """
    if tree.get("id") == node_id or tree.get("value") == node_id:
        return tree

    for child in tree.get("children", []):
        result = find_node_in_tree(child, node_id)
        if result:
            return result

    return None


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
    # Get all node IDs from tree
    tree_data = app.state.get("file_tree")
    if tree_data:
        all_ids = get_all_node_ids(tree_data)
        # Update the user's expansion state
        app.state["expanded_nodes"] = all_ids
        app.state["message"] = "Expanded all nodes"


@app.on_action("collapse_all")
def handle_collapse_all(event):
    """Collapse all nodes in the tree."""
    # Clear the user's expansion state
    app.state["expanded_nodes"] = []
    app.state["message"] = "Collapsed all nodes"


# Counter for adding test nodes
node_counter = 1


@app.on_action("add_node")
def handle_add_node(event):
    """Add a test node to the tree."""
    global node_counter

    # Add a new file to the root of the tree
    tree_data = app.state.get("file_tree")
    if tree_data:
        new_file = {
            "label": f"test_file_{node_counter}.txt",
            "value": f"test_file_{node_counter}.txt",
            "type": "file",
            "size": "0.5 KB",
        }

        if "children" not in tree_data:
            tree_data["children"] = []

        tree_data["children"].append(new_file)
        app.state["file_tree"] = tree_data
        app.state["message"] = f"Added test_file_{node_counter}.txt to root"
        node_counter += 1


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
