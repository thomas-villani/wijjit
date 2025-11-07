"""Todo List Application - Demo for Wijjit TUI Framework.

This is a simple todo list application that demonstrates the Wijjit framework's
key features:
- View system with decorators
- State management with reactive updates
- Event handlers for user interactions
- Template rendering
- Navigation between views

Run with: python examples/todo_app.py
"""

import shutil
from wijjit.core.app import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.layout.frames import Frame, FrameStyle, BorderStyle


def create_app():
    """Create and configure the todo list application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Initialize app with starting state
    app = Wijjit(initial_state={
        "todos": [
            {"id": 1, "text": "Learn Wijjit", "done": False},
            {"id": 2, "text": "Build a TUI app", "done": False},
            {"id": 3, "text": "Share with the world", "done": False},
        ],
        "next_id": 4,
        "new_todo": "",
        "selected_index": 0,
    })

    @app.view("main", default=True)
    def main_view():
        """Main todo list view."""
        def render_data():
            todos = app.state["todos"]
            completed = sum(1 for todo in todos if todo["done"])
            total = len(todos)

            # Get terminal size for responsive layout
            term_size = shutil.get_terminal_size()
            term_width = term_size.columns
            term_height = term_size.lines

            # Build todo list display
            todo_lines = []
            for i, todo in enumerate(todos):
                checkbox = "[X]" if todo["done"] else "[ ]"
                marker = ">" if i == app.state["selected_index"] else " "
                todo_lines.append(f"{marker} {checkbox} {todo['text']}")

            if not todo_lines:
                todo_lines = ["  No todos yet! Press 'a' to add one."]

            # Build content for frame
            content_lines = [
                f"Progress: {completed}/{total} completed",
                "",
                *todo_lines,
                "",
                "Controls:",
                "[a] Add placeholder  [d] Delete  [Space] Toggle  [q] Quit",
                "[Up/Down] Navigate",
            ]
            content_text = "\n".join(content_lines)

            # Create the UI using frames
            frame_style = FrameStyle(
                border=BorderStyle.ROUNDED,
                title="Todo List",
            )
            frame = Frame(
                width=min(term_width, 80),  # Max 80 columns
                height=min(term_height - 2, len(content_lines) + 4),  # Adjust to content
                style=frame_style,
            )
            frame.set_content(content_text)

            return {"content": frame.render()}

        data = render_data()

        return {
            "template": "{{ content }}",
            "data": data,
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers for the main view."""
        # Handler for 'a' key - add todo
        def on_add_key(event):
            if event.key == "a":
                # For now, add a placeholder todo
                # In a real app, we'd navigate to an input view
                new_id = app.state["next_id"]
                app.state["todos"].append({
                    "id": new_id,
                    "text": f"New todo #{new_id}",
                    "done": False,
                })
                app.state["next_id"] = new_id + 1
                app.refresh()

        # Handler for 'd' key - delete selected todo
        def on_delete_key(event):
            if event.key == "d":
                todos = app.state["todos"]
                selected_index = app.state["selected_index"]
                if 0 <= selected_index < len(todos):
                    todos.pop(selected_index)
                    # Adjust selection if needed
                    if app.state["selected_index"] >= len(todos) and todos:
                        app.state["selected_index"] = len(todos) - 1
                    app.refresh()

        # Handler for space key - toggle selected todo
        def on_toggle_key(event):
            if event.key == "space":
                todos = app.state["todos"]
                selected_index = app.state["selected_index"]
                if 0 <= selected_index < len(todos):
                    todos[selected_index]["done"] = not todos[selected_index]["done"]
                    app.refresh()

        # Handler for up/down arrows - move selection
        def on_navigate_key(event):
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

        # Handler for 'q' key - quit
        def on_quit_key(event):
            if event.key == "q":
                app.quit()

        # Register all handlers as view-scoped for main view
        app.on(EventType.KEY, on_add_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_delete_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_toggle_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_navigate_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_quit_key, scope=HandlerScope.VIEW, view_name="main")

    return app


def main():
    """Run the todo list application."""
    app = create_app()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
