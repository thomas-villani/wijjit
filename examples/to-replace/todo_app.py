"""Todo List Application - Demo for Wijjit TUI Framework.

This is a simple todo list application that demonstrates the Wijjit framework's
key features:
- Template-based UI with frames, vstacks, hstacks, textinputs, and buttons
- Automatic state binding from element IDs to app.state
- Action handlers using @app.on_action() decorator
- State management with reactive updates
- Event handlers for keyboard shortcuts
- Automatic Tab/Shift+Tab navigation between fields

Run with: python examples/todo_app.py
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Create app with initial state
app = Wijjit(
    initial_state={
        "todos": [
            {"id": 1, "text": "Learn Wijjit", "done": False},
            {"id": 2, "text": "Build a TUI app", "done": False},
            {"id": 3, "text": "Share with the world", "done": False},
        ],
        "next_id": 4,
        "new_todo": "",
        "selected_index": 0,
        "adding_todo": False,  # Controls whether input field is visible
    }
)


@app.view("main", default=True)
def main_view():
    """Main todo list view."""
    todos = app.state["todos"]
    completed = sum(1 for todo in todos if todo["done"])
    total = len(todos)

    # Build todo list display
    todo_lines = []
    for i, todo in enumerate(todos):
        checkbox = "[X]" if todo["done"] else "[ ]"
        marker = ">" if i == app.state["selected_index"] else " "
        todo_lines.append(f"{marker} {checkbox} {todo['text']}")

    if not todo_lines:
        todo_lines = ["  No todos yet! Type a todo and click Add."]

    todo_list_text = "\n".join(todo_lines)

    return {
        "template": """
{% frame title="Todo List" border="rounded" width=60 %}
  {% vstack spacing=1 padding=1 %}
    Progress: {{ completed }}/{{ total }} completed

    {% if state.adding_todo %}
      {% hstack spacing=2 %}
        {% textinput id="new_todo" placeholder="Enter new todo..." width=30 action="add_todo" %}{% endtextinput %}
        {% button id="add_btn" action="add_todo" %}Add{% endbutton %}
        {% button id="cancel_btn" action="cancel_add" %}Cancel{% endbutton %}
      {% endhstack %}
    {% else %}
      Press 'a' to add a new todo
    {% endif %}

{{ todo_list }}

    {% if state.adding_todo %}
      [Enter] Add  [Esc] Cancel
    {% else %}
      [a] Add  [d] Delete  [Space] Toggle  [Up/Down] Navigate  [q] Quit
    {% endif %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "completed": completed,
            "total": total,
            "todo_list": todo_list_text,
        },
        "on_enter": setup_handlers,
    }


def setup_handlers():
    """Set up keyboard handlers for the main view."""

    # Handler for 'a' key - enter add mode
    def on_add_key(event):
        if event.key == "a" and not app.state.get("adding_todo", False):
            app.state["adding_todo"] = True
            app.state["new_todo"] = ""  # Clear any previous input

    # Handler for Escape key - cancel add mode
    def on_escape_key(event):
        if event.key == "escape" and app.state.get("adding_todo", False):
            app.state["adding_todo"] = False
            app.state["new_todo"] = ""  # Clear input

    # Handler for 'd' key - delete selected todo (only when not adding)
    def on_delete_key(event):
        if event.key == "d" and not app.state.get("adding_todo", False):
            todos = app.state["todos"]
            selected_index = app.state["selected_index"]
            if 0 <= selected_index < len(todos):
                todos.pop(selected_index)
                # Adjust selection if needed
                if app.state["selected_index"] >= len(todos) and todos:
                    app.state["selected_index"] = len(todos) - 1
                app.refresh()

    # Handler for space key - toggle selected todo (only when not adding)
    def on_toggle_key(event):
        if event.key == "space" and not app.state.get("adding_todo", False):
            todos = app.state["todos"]
            selected_index = app.state["selected_index"]
            if 0 <= selected_index < len(todos):
                todos[selected_index]["done"] = not todos[selected_index]["done"]
                app.refresh()

    # Handler for up/down arrows - move selection (only when not adding)
    def on_navigate_key(event):
        if not app.state.get("adding_todo", False):
            if event.key == "up":
                todos = app.state["todos"]
                if todos and app.state["selected_index"] > 0:
                    app.state["selected_index"] -= 1
                    app.refresh()
            elif event.key == "down":
                todos = app.state["todos"]
                if todos and app.state["selected_index"] < len(todos) - 1:
                    app.state["selected_index"] += 1
                    app.refresh()

    # Handler for 'q' key - quit (works in both modes)
    def on_quit_key(event):
        if event.key == "q":
            app.quit()

    # Register all handlers as view-scoped for main view
    app.on(EventType.KEY, on_add_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_escape_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_delete_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_toggle_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_navigate_key, scope=HandlerScope.VIEW, view_name="main")
    app.on(EventType.KEY, on_quit_key, scope=HandlerScope.VIEW, view_name="main")


@app.on_action("add_todo")
def handle_add_todo(event):
    """Handle add todo action from button or Enter key in input."""
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
        app.state["new_todo"] = ""  # Clear input field
        app.state["adding_todo"] = False  # Exit add mode


@app.on_action("cancel_add")
def handle_cancel_add(event):
    """Handle cancel action - exit add mode without adding."""
    app.state["adding_todo"] = False
    app.state["new_todo"] = ""  # Clear input field


if __name__ == "__main__":
    # Run the app
    # Press 'a' to enter add mode (shows input field)
    # Type your todo and press Enter or click Add button
    # Press Escape or click Cancel to exit add mode
    # When NOT adding: [d] Delete, [Space] Toggle, [Up/Down] Navigate, [q] Quit
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback

        traceback.print_exc()
