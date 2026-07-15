"""Todo App - A complete example demonstrating Wijjit's capabilities.

A fully-featured todo list application that saves/loads from GFM markdown.

Features:
- Add, edit, delete, and toggle todos
- Filter by All / Active / Completed with a real single-choice RadioGroup
- Scrollable list for many items
- Persistent storage in todo.md (GitHub Flavored Markdown)
- A footer with the live status message and completion count
- Keyboard shortcuts that stay out of the way while you type

Controls:
- Enter: Add the new todo (when the input is focused)
- Tab/Shift+Tab: Move focus between the input, filter, list, and buttons
- In the filter: Left/Right (or click) to switch All / Active / Done
- In the list: Space to toggle the focused todo
- e: Edit the focused todo (ignored while you're typing in the input)
- d: Delete the focused todo, with confirmation (likewise ignored while typing)
- Ctrl+Q: Quit
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from wijjit import Wijjit, render_template_string
from wijjit.elements.base import ElementType
from wijjit.elements.modal import ConfirmDialog, TextInputDialog
from wijjit.layout.bounds import Bounds

# File path for persistent storage
TODO_FILE = Path("todo.md")

# The filter control is a single-choice RadioGroup bound to state["filter"].
# Each option's ``value`` is what lands in state; ``label`` is what the user sees.
FILTER_OPTIONS = [
    {"value": "all", "label": "All"},
    {"value": "active", "label": "Active"},
    {"value": "completed", "label": "Done"},
]


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
        "filter": "all",  # "all", "active", "completed" (bound to the RadioGroup)
        "message": "Ready. Tab to the list, then Space to toggle.",
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


def text_input_focused() -> bool:
    """Return True when a text-entry element currently has focus.

    Used to make the bare-letter shortcuts (``e``/``d``) polite: they must not
    fire while the user is typing a todo, otherwise words like "edit" or
    "done" would trigger actions instead of being entered as text.

    Returns
    -------
    bool
        True if the focused element is a text input (TextInput/TextArea).
    """
    focused = app.focus_manager.get_focused_element()
    return getattr(focused, "element_type", None) == ElementType.INPUT


@app.view("main", default=True)
def main_view():
    """Main view with todo list."""
    filtered = get_filtered_todos()
    done, total = get_stats()

    return render_template_string(
        """
{% frame border="rounded" title="Todo App" width=70 height=24 %}
  {% vstack spacing=1 padding=1 %}

    {# Input row - Enter in the textinput triggers the add_todo action #}
    {% hstack spacing=1 %}
      {% textinput id="new_todo" placeholder="What needs to be done?" width=52 action="add_todo" %}{% endtextinput %}
      {% button action="add_todo" %}Add{% endbutton %}
    {% endhstack %}

    {# Filter: a real single-choice control bound to state.filter. Tab to it,
       then Left/Right (or click) to switch - no faked indicator strings. #}
    {% radiogroup id="filter" orientation="horizontal" width=34 options=filter_options %}
    {% endradiogroup %}

    {# Scrollable todo list. Scrollable frames need a fixed height (they own a
       viewport), so this is sized rather than "fill". #}
    {% frame border="single" height=10 scrollable=True show_scrollbar=True %}
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

    {# Footer: action button + completion count, then the live status message
       on its own full-width line, then the key hints. #}
    {% hstack spacing=2 %}
      {% button action="clear_completed" %}Clear Done{% endbutton %}
      {% text %}{{ done }}/{{ total }} done{% endtext %}
    {% endhstack %}

    {% text %}{{ state.message }}{% endtext %}

    {% text %}Tab navigate | Space toggle | e edit | d delete | Ctrl+Q quit{% endtext %}

  {% endvstack %}
{% endframe %}
        """,
        filtered_todos=filtered,
        filter_options=FILTER_OPTIONS,
        done=done,
        total=total,
    )


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
    """Edit the focused todo.

    Ignored while a text input is focused so typing an "e" in a todo does not
    open the edit dialog.
    """
    if text_input_focused():
        return

    todo_id = get_focused_todo_id()
    if not todo_id:
        app.state["message"] = "Focus a todo in the list to edit (use Tab)"
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
    """Delete the focused todo with confirmation.

    Ignored while a text input is focused so typing a "d" in a todo does not
    open the delete dialog.
    """
    if text_input_focused():
        return

    todo_id = get_focused_todo_id()
    if not todo_id:
        app.state["message"] = "Focus a todo in the list to delete (use Tab)"
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
    """Handle state changes - sync checkbox toggles to the todos list.

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


def on_filter_change(key: str, old_value, new_value):
    """Update the status message when the filter RadioGroup changes.

    The RadioGroup writes ``state["filter"]`` directly (two-way binding), so the
    list re-filters on its own; this watcher just narrates the change.

    Parameters
    ----------
    key : str
        The state key that changed ("filter").
    old_value : any
        Previous filter value.
    new_value : any
        New filter value.
    """
    app.state["message"] = f"Showing {new_value} todos"


# Register state change handlers
app.state.on_change(on_state_change)
app.state.watch("filter", on_filter_change)


if __name__ == "__main__":
    print("Starting Todo App...")
    print(f"Todos will be saved to: {TODO_FILE.absolute()}")
    print("Press Ctrl+Q to quit\n")
    app.run()
