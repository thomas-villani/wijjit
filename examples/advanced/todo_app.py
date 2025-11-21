"""Todo List Application - Complete Todo App Demo.

This comprehensive todo list application demonstrates:
- Template-based UI with frames, vstacks, hstacks
- ListView for displaying todos
- Add, delete, toggle, and filter functionality
- Statistics display (completed/total)
- Filter modes (all/active/completed)
- Keyboard shortcuts and button controls
- State management with reactive updates
- Modern event handling patterns

Run with: python examples/advanced/todo_app.py

Controls:
- Tab/Shift+Tab: Navigate between elements
- a: Quick add mode (show input field)
- d: Delete selected todo
- Space: Toggle selected todo completion
- f: Cycle filter mode (all/active/completed)
- c: Clear all completed todos
- q: Quit
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Create app with initial state
app = Wijjit(
    initial_state={
        "todos": [
            {"id": 1, "text": "Learn Wijjit TUI framework", "done": False},
            {"id": 2, "text": "Build a terminal application", "done": False},
            {"id": 3, "text": "Share your creation", "done": False},
        ],
        "next_id": 4,
        "new_todo": "",
        "filter_mode": "all",  # all, active, completed
        "adding_todo": False,
    }
)


def get_filtered_todos():
    """Get filtered todo list based on current filter mode.

    Returns
    -------
    list
        Filtered list of todos
    """
    todos = app.state.get("todos", [])
    filter_mode = app.state.get("filter_mode", "all")

    if filter_mode == "active":
        return [t for t in todos if not t["done"]]
    elif filter_mode == "completed":
        return [t for t in todos if t["done"]]
    else:  # all
        return todos


def get_stats():
    """Get todo statistics.

    Returns
    -------
    dict
        Statistics with completed, active, and total counts
    """
    todos = app.state.get("todos", [])
    completed = sum(1 for t in todos if t["done"])
    total = len(todos)
    active = total - completed
    return {"completed": completed, "active": active, "total": total}


@app.view("main", default=True)
def main_view():
    """Main todo list view.

    Returns
    -------
    dict
        View configuration with template and data
    """
    filtered_todos = get_filtered_todos()
    stats = get_stats()
    filter_mode = app.state.get("filter_mode", "all")

    # Build display list for todos
    todo_items = []
    for todo in filtered_todos:
        checkbox = "[X]" if todo["done"] else "[ ]"
        status = "done" if todo["done"] else "pending"
        todo_items.append(f"{checkbox} {todo['text']}")

    if not todo_items:
        if filter_mode == "active" and stats["active"] == 0:
            todo_items = ["No active todos! Great job!"]
        elif filter_mode == "completed" and stats["completed"] == 0:
            todo_items = ["No completed todos yet."]
        else:
            todo_items = ["No todos yet. Press 'a' to add one!"]

    return {
        "template": """
{% frame title="Todo List Application" border="double" width=80 height=30 %}
  {% vstack spacing=1 padding=1 %}
    {% hstack spacing=2 %}
      {% vstack spacing=0 width=50 %}
        Statistics:
        Total: {{ stats.total }} | Active: {{ stats.active }} | Completed: {{ stats.completed }}
      {% endvstack %}
      {% vstack spacing=0 width=25 %}
        Filter: {{ filter_label }}
      {% endvstack %}
    {% endhstack %}

    {% if state.adding_todo %}
      {% vstack spacing=0 %}
        Add New Todo:
      {% endvstack %}
      {% hstack spacing=2 %}
        {% textinput id="new_todo" placeholder="What needs to be done?" width=50 action="add_todo" %}{% endtextinput %}
        {% button action="add_todo" %}Add{% endbutton %}
        {% button action="cancel_add" %}Cancel{% endbutton %}
      {% endhstack %}
    {% else %}
      {% vstack spacing=0 %}
        Press 'a' to add a new todo
      {% endvstack %}
    {% endif %}

    {% vstack spacing=0 %}
      Todos:
    {% endvstack %}

    {% frame border="single" height=12 scrollable=true %}
      {% listview items=todo_items selection_style="pointer" %}{% endlistview %}
    {% endframe %}

    {% hstack spacing=2 %}
      {% button action="toggle_selected" %}Toggle{% endbutton %}
      {% button action="delete_selected" %}Delete{% endbutton %}
      {% button action="cycle_filter" %}Filter ({{ filter_label }}){% endbutton %}
      {% button action="clear_completed" %}Clear Completed{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Shortcuts: [a] Add | [d] Delete | [Space] Toggle | [f] Filter | [c] Clear completed | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "stats": stats,
            "filter_label": filter_mode.capitalize(),
            "todo_items": todo_items,
        },
        "on_enter": setup_view_handlers,
    }


def setup_view_handlers():
    """Set up view-scoped keyboard handlers.

    These handlers are view-scoped and automatically cleaned up when
    navigating away from the view.
    """

    def on_add_key(event):
        """Handle 'a' key - enter add mode."""
        if event.key == "a" and not app.state.get("adding_todo", False):
            app.state["adding_todo"] = True
            app.state["new_todo"] = ""

    def on_escape_key(event):
        """Handle Escape key - cancel add mode."""
        if event.key == "escape" and app.state.get("adding_todo", False):
            app.state["adding_todo"] = False
            app.state["new_todo"] = ""

    def on_delete_key(event):
        """Handle 'd' key - delete selected todo."""
        if event.key == "d" and not app.state.get("adding_todo", False):
            delete_selected_todo()

    def on_toggle_key(event):
        """Handle space key - toggle selected todo."""
        if event.key == "space" and not app.state.get("adding_todo", False):
            toggle_selected_todo()

    def on_filter_key(event):
        """Handle 'f' key - cycle filter mode."""
        if event.key == "f":
            cycle_filter_mode()

    def on_clear_key(event):
        """Handle 'c' key - clear completed todos."""
        if event.key == "c":
            clear_completed_todos()

    # Register all handlers as view-scoped
    app.on(EventType.KEY, on_add_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_escape_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_delete_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_toggle_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_filter_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_clear_key, scope=HandlerScope.VIEW, view_name="main")


def delete_selected_todo():
    """Delete the selected todo from the list."""
    todos = app.state.get("todos", [])
    filtered_todos = get_filtered_todos()

    if not filtered_todos:
        return

    # Get the selected index from the listview (always 0 if not tracking separately)
    # For now, we'll delete the first item in the filtered list
    # In a more advanced version, we'd track the selected index in state
    selected_index = 0  # Default to first item

    if 0 <= selected_index < len(filtered_todos):
        todo_to_delete = filtered_todos[selected_index]
        # Find this todo in the main list and remove it
        todos[:] = [t for t in todos if t["id"] != todo_to_delete["id"]]
        app.refresh()


def toggle_selected_todo():
    """Toggle the completion status of the selected todo."""
    filtered_todos = get_filtered_todos()

    if not filtered_todos:
        return

    # Get the selected index (defaulting to first item)
    selected_index = 0

    if 0 <= selected_index < len(filtered_todos):
        todo_to_toggle = filtered_todos[selected_index]
        # Find this todo in the main list and toggle it
        todos = app.state.get("todos", [])
        for todo in todos:
            if todo["id"] == todo_to_toggle["id"]:
                todo["done"] = not todo["done"]
                break
        app.refresh()


def cycle_filter_mode():
    """Cycle through filter modes: all -> active -> completed -> all."""
    current_filter = app.state.get("filter_mode", "all")
    if current_filter == "all":
        app.state["filter_mode"] = "active"
    elif current_filter == "active":
        app.state["filter_mode"] = "completed"
    else:
        app.state["filter_mode"] = "all"


def clear_completed_todos():
    """Remove all completed todos from the list."""
    todos = app.state.get("todos", [])
    todos[:] = [t for t in todos if not t["done"]]
    app.refresh()


# Action handlers
@app.on_action("add_todo")
def handle_add_todo(event):
    """Handle add todo action from button or Enter key in input.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    todo_text = app.state.get("new_todo", "").strip()

    if todo_text:
        new_id = app.state["next_id"]
        app.state["todos"].append(
            {
                "id": new_id,
                "text": todo_text,
                "done": False,
            }
        )
        app.state["next_id"] = new_id + 1
        app.state["new_todo"] = ""
        app.state["adding_todo"] = False


@app.on_action("cancel_add")
def handle_cancel_add(event):
    """Handle cancel action - exit add mode without adding.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["adding_todo"] = False
    app.state["new_todo"] = ""


@app.on_action("delete_selected")
def handle_delete_selected(event):
    """Handle delete selected button.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    delete_selected_todo()


@app.on_action("toggle_selected")
def handle_toggle_selected(event):
    """Handle toggle selected button.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    toggle_selected_todo()


@app.on_action("cycle_filter")
def handle_cycle_filter(event):
    """Handle cycle filter button.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    cycle_filter_mode()


@app.on_action("clear_completed")
def handle_clear_completed(event):
    """Handle clear completed button.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    clear_completed_todos()


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
    print("Todo List Application")
    print("=" * 50)
    print("A comprehensive todo app demonstrating Wijjit features:")
    print("- Add, delete, toggle todos")
    print("- Filter by all/active/completed")
    print("- Track statistics")
    print("- Keyboard shortcuts and buttons")
    print()
    print("Controls:")
    print("  [a] Add new todo")
    print("  [d] Delete selected")
    print("  [Space] Toggle completion")
    print("  [f] Cycle filter")
    print("  [c] Clear completed")
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
