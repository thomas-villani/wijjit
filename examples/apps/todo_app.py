"""Todo App - A complete example demonstrating Wijjit's capabilities.

A fully-featured todo list application that saves/loads from GFM markdown.

Features:
- Add, edit, delete, and toggle todos
- Filter by All / Active / Completed
- Scrollable list for many items
- Persistent storage in todo.md (GitHub Flavored Markdown)
- Keyboard shortcuts for power users

Controls:
- Enter: Add new todo (when input focused)
- Tab/Shift+Tab: Navigate between elements
- Space: Toggle todo completion
- e: Edit selected todo
- d: Delete selected todo (with confirmation)
- 1/2/3: Switch filter (All/Active/Completed)
- Ctrl+Q: Quit
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from wijjit import Wijjit
from wijjit.elements.modal import ConfirmDialog, TextInputDialog
from wijjit.layout.bounds import Bounds

# File path for persistent storage
TODO_FILE = Path("todo.md")


def parse_gfm_todos(content: str) -> list[dict]:
    """Parse GFM markdown todo list into structured data.

    Parameters
    ----------
    content : str
        Markdown content with checkbox syntax

    Returns
    -------
    list[dict]
        List of todo items with id, text, and done status
    """
    todos = []
    # Match GFM checkbox syntax: - [ ] or - [x] or - [X]
    pattern = re.compile(r"^-\s*\[([ xX])\]\s*(.+)$", re.MULTILINE)

    for match in pattern.finditer(content):
        checkbox, text = match.groups()
        todos.append(
            {
                "id": str(uuid.uuid4())[:8],
                "text": text.strip(),
                "done": checkbox.lower() == "x",
            }
        )

    return todos


def save_gfm_todos(todos: list[dict], filepath: Path) -> None:
    """Save todos to GFM markdown file.

    Parameters
    ----------
    todos : list[dict]
        List of todo items
    filepath : Path
        Path to save the markdown file
    """
    lines = ["# Todo List", ""]

    for todo in todos:
        checkbox = "[x]" if todo["done"] else "[ ]"
        lines.append(f"- {checkbox} {todo['text']}")

    lines.append("")  # Trailing newline
    filepath.write_text("\n".join(lines), encoding="utf-8")


def load_todos() -> list[dict]:
    """Load todos from file, creating sample data if file doesn't exist.

    Returns
    -------
    list[dict]
        List of todo items
    """
    if TODO_FILE.exists():
        content = TODO_FILE.read_text(encoding="utf-8")
        todos = parse_gfm_todos(content)
        if todos:
            return todos

    # Return sample todos if file doesn't exist or is empty
    return [
        {
            "id": str(uuid.uuid4())[:8],
            "text": "Welcome to the Todo App!",
            "done": False,
        },
        {"id": str(uuid.uuid4())[:8], "text": "Press Tab to navigate", "done": False},
        {"id": str(uuid.uuid4())[:8], "text": "Press Space to toggle", "done": True},
        {
            "id": str(uuid.uuid4())[:8],
            "text": "Press 'e' to edit, 'd' to delete",
            "done": False,
        },
    ]


# Initialize app with state
app = Wijjit(
    initial_state={
        "todos": load_todos(),
        "new_todo": "",
        "filter": "all",  # "all", "active", "completed"
        "message": "Ready. Tab to navigate, Space to toggle, e=edit, d=delete",
    }
)


def get_filtered_todos() -> list[dict]:
    """Get todos filtered by current filter setting.

    Returns
    -------
    list[dict]
        Filtered list of todos
    """
    todos = app.state.get("todos", [])
    filter_mode = app.state.get("filter", "all")

    if filter_mode == "active":
        return [t for t in todos if not t["done"]]
    elif filter_mode == "completed":
        return [t for t in todos if t["done"]]
    return todos


def get_stats() -> tuple[int, int]:
    """Get completion statistics.

    Returns
    -------
    tuple[int, int]
        (completed_count, total_count)
    """
    todos = app.state.get("todos", [])
    done = sum(1 for t in todos if t["done"])
    return done, len(todos)


def auto_save() -> None:
    """Save todos to file."""
    try:
        save_gfm_todos(app.state.get("todos", []), TODO_FILE)
    except Exception as e:
        app.state["message"] = f"Save failed: {e}"


@app.view("main", default=True)
def main_view():
    """Main view with todo list."""

    def get_data():
        """Compute fresh data on each render."""
        filtered = get_filtered_todos()
        done, total = get_stats()
        current_filter = app.state.get("filter", "all")

        # Build filter button indicators
        all_indicator = ">" if current_filter == "all" else " "
        active_indicator = ">" if current_filter == "active" else " "
        completed_indicator = ">" if current_filter == "completed" else " "

        return {
            "filtered_todos": filtered,
            "done": done,
            "total": total,
            "all_ind": all_indicator,
            "active_ind": active_indicator,
            "completed_ind": completed_indicator,
        }

    return {
        "template": """
{% frame border="rounded" title="Todo App" width=70 height=24 %}
  {% vstack spacing=1 padding=1 %}

    {# Input row - Enter in textinput triggers add_todo action #}
    {% hstack spacing=1 %}
      {% textinput id="new_todo" placeholder="What needs to be done?" width=50 action="add_todo" %}{% endtextinput %}
      {% button action="add_todo" %}Add{% endbutton %}
    {% endhstack %}

    {# Filter buttons #}
    {% hstack spacing=2 %}
      {% button action="filter_all" %}{{ all_ind }}All{% endbutton %}
      {% button action="filter_active" %}{{ active_ind }}Active{% endbutton %}
      {% button action="filter_completed" %}{{ completed_ind }}Done{% endbutton %}
      {% text %}{{ done }}/{{ total }} completed{% endtext %}
    {% endhstack %}

    {# Scrollable todo list #}
    {% frame border="single" height=12 scrollable=True show_scrollbar=True %}
      {% vstack spacing=0 %}
        {% if filtered_todos %}
          {% for todo in filtered_todos %}
            {% checkbox id="todo_" ~ todo.id checked=todo.done %}{{ todo.text }}{% endcheckbox %}
          {% endfor %}
        {% else %}
          {% text %}No todos to display{% endtext %}
        {% endif %}
      {% endvstack %}
    {% endframe %}

    {# Footer #}
    {% hstack spacing=2 %}
      {% button action="clear_completed" %}Clear Done{% endbutton %}
      {% text %}{{ state.message }}{% endtext %}
    {% endhstack %}

    {% text %}Keys: [Tab] Navigate | [Space] Toggle | [e] Edit | [d] Delete | [1/2/3] Filter{% endtext %}

  {% endvstack %}
{% endframe %}
        """,
        "data": get_data,  # Pass callable, not static dict
    }


# --- Event Handlers ---


@app.on_action("add_todo")
def add_todo(event):
    """Add a new todo from input field."""
    text = app.state.get("new_todo", "").strip()
    if text:
        new_todo = {
            "id": str(uuid.uuid4())[:8],
            "text": text,
            "done": False,
        }
        todos = app.state.get("todos", [])
        todos.append(new_todo)
        app.state["todos"] = todos
        app.state["new_todo"] = ""
        app.state["message"] = f"Added: {text}"
        auto_save()


@app.on_action("filter_all")
def filter_all(event):
    """Show all todos."""
    app.state["filter"] = "all"
    app.state["message"] = "Showing all todos"


@app.on_action("filter_active")
def filter_active(event):
    """Show active (uncompleted) todos."""
    app.state["filter"] = "active"
    app.state["message"] = "Showing active todos"


@app.on_action("filter_completed")
def filter_completed(event):
    """Show completed todos."""
    app.state["filter"] = "completed"
    app.state["message"] = "Showing completed todos"


@app.on_action("clear_completed")
def clear_completed(event):
    """Remove all completed todos."""
    todos = app.state.get("todos", [])
    completed_count = sum(1 for t in todos if t["done"])

    if completed_count == 0:
        app.state["message"] = "No completed todos to clear"
        return

    app.state["todos"] = [t for t in todos if not t["done"]]
    app.state["message"] = f"Cleared {completed_count} completed todo(s)"
    auto_save()


# --- Keyboard Shortcuts ---


@app.on_key("1")
def key_filter_all(event):
    """Filter: All."""
    filter_all(event)


@app.on_key("2")
def key_filter_active(event):
    """Filter: Active."""
    filter_active(event)


@app.on_key("3")
def key_filter_completed(event):
    """Filter: Completed."""
    filter_completed(event)


def get_focused_todo_id() -> str | None:
    """Get the todo ID from the currently focused element.

    Returns
    -------
    str | None
        Todo ID if a todo checkbox is focused, None otherwise
    """
    focused = app.focus_manager.get_focused_element()
    if not focused or not hasattr(focused, "id"):
        return None

    elem_id = focused.id or ""
    if elem_id.startswith("todo_"):
        return elem_id.replace("todo_", "")
    return None


def find_todo_by_id(todo_id: str) -> dict | None:
    """Find a todo by its ID.

    Parameters
    ----------
    todo_id : str
        The todo ID to find

    Returns
    -------
    dict | None
        The todo dict if found, None otherwise
    """
    for todo in app.state.get("todos", []):
        if todo["id"] == todo_id:
            return todo
    return None


@app.on_key("e")
def edit_todo(event):
    """Edit the focused todo."""
    todo_id = get_focused_todo_id()
    if not todo_id:
        app.state["message"] = "Focus a todo to edit (use Tab)"
        return

    todo = find_todo_by_id(todo_id)
    if not todo:
        return

    def on_submit(new_text: str):
        """Handle edit submission."""
        new_text = new_text.strip()
        if new_text and new_text != todo["text"]:
            todo["text"] = new_text
            app.state["message"] = f"Updated: {new_text}"
            auto_save()
        else:
            app.state["message"] = "Edit cancelled (no changes)"

    def on_cancel():
        """Handle edit cancellation."""
        app.state["message"] = "Edit cancelled"

    dialog = TextInputDialog(
        title="Edit Todo",
        prompt="Edit your todo:",
        initial_value=todo["text"],
        on_submit=on_submit,
        on_cancel=on_cancel,
        submit_label="Save",
        cancel_label="Cancel",
        width=60,
        height=11,
        input_width=45,
    )

    # Center dialog
    term_size = shutil.get_terminal_size()
    dialog.bounds = Bounds(
        x=(term_size.columns - 60) // 2,
        y=(term_size.lines - 11) // 2,
        width=60,
        height=11,
    )

    overlay = app.show_modal(dialog)

    def close():
        app.overlay_manager.pop(overlay)

    dialog.close_callback = close


@app.on_key("d")
def delete_todo(event):
    """Delete the focused todo with confirmation."""
    todo_id = get_focused_todo_id()
    if not todo_id:
        app.state["message"] = "Focus a todo to delete (use Tab)"
        return

    todo = find_todo_by_id(todo_id)
    if not todo:
        return

    def on_confirm():
        """Handle delete confirmation."""
        todos = app.state.get("todos", [])
        app.state["todos"] = [t for t in todos if t["id"] != todo_id]
        app.state["message"] = f"Deleted: {todo['text']}"
        auto_save()

    def on_cancel():
        """Handle delete cancellation."""
        app.state["message"] = "Delete cancelled"

    # Truncate long text for dialog
    display_text = todo["text"]
    if len(display_text) > 35:
        display_text = display_text[:32] + "..."

    dialog = ConfirmDialog(
        title="Delete Todo",
        message=f'Delete this todo?\n\n"{display_text}"',
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        confirm_label="Delete",
        cancel_label="Cancel",
        width=50,
        height=11,
    )

    # Center dialog
    term_size = shutil.get_terminal_size()
    dialog.bounds = Bounds(
        x=(term_size.columns - 50) // 2,
        y=(term_size.lines - 11) // 2,
        width=50,
        height=11,
    )

    overlay = app.show_modal(dialog)

    def close():
        app.overlay_manager.pop(overlay)

    dialog.close_callback = close


# --- State Change Handlers ---


def on_state_change(key: str, old_value, new_value):
    """Handle state changes - sync checkbox toggles to todos list.

    Parameters
    ----------
    key : str
        State key that changed
    old_value : any
        Previous value
    new_value : any
        New value
    """
    # Handle checkbox toggles (todo_<id> keys)
    if key.startswith("todo_") and isinstance(new_value, bool):
        todo_id = key.replace("todo_", "")
        todo = find_todo_by_id(todo_id)
        if todo:
            todo["done"] = new_value
            status = "completed" if new_value else "uncompleted"
            app.state["message"] = f"Marked {status}: {todo['text']}"
            auto_save()


# Register state change handler
app.state.on_change(on_state_change)


@app.on_key("q")
def quit_app(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    print("Starting Todo App...")
    print(f"Todos will be saved to: {TODO_FILE.absolute()}")
    print("Press Ctrl+Q to quit\n")
    app.run()
