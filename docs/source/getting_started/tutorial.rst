Tutorial: Building a Todo List App
===================================

In this tutorial, you'll build a complete todo list application using Wijjit. This will teach you the core concepts of Wijjit including state management, templates, event handling, and interactive components.

What You'll Build
-----------------

A todo list app that allows you to:

* Add new todos
* Mark todos as complete/incomplete
* Delete todos
* Navigate through todos with keyboard
* See progress (how many completed)

By the end, you'll have a fully functional terminal application!

Prerequisites
-------------

* Python 3.8 or later
* Wijjit installed (see :doc:`installation`)
* Basic Python knowledge
* Familiarity with Jinja2 templates (helpful but not required)

Step 1: Create the Basic App Structure
---------------------------------------

Let's start with a basic Wijjit app and initial state:

.. code-block:: python

    from wijjit import Wijjit
    from wijjit.core.events import EventType, HandlerScope

    # Create app with initial state
    app = Wijjit(initial_state={
        "todos": [
            {"id": 1, "text": "Learn Wijjit", "done": False},
            {"id": 2, "text": "Build a TUI app", "done": False},
        ],
        "next_id": 3,
    })

    @app.view("main", default=True)
    def main_view():
        return {
            "template": "Todo List (coming soon!)",
        }

    if __name__ == '__main__':
        app.run()

Save this as ``todo_app.py`` and run it:

.. code-block:: bash

    python todo_app.py

You should see "Todo List (coming soon!)" in your terminal. Press Ctrl+C to exit.

Understanding the State
~~~~~~~~~~~~~~~~~~~~~~~

We're storing:

* ``todos``: A list of todo objects, each with ``id``, ``text``, and ``done`` fields
* ``next_id``: A counter for generating unique IDs

Step 2: Display the Todos
--------------------------

Now let's display the todos in a frame with a nice border:

.. code-block:: python

    @app.view("main", default=True)
    def main_view():
        todos = app.state["todos"]
        completed = sum(1 for todo in todos if todo["done"])
        total = len(todos)

        # Build todo list display
        todo_lines = []
        for todo in todos:
            checkbox = "[X]" if todo["done"] else "[ ]"
            todo_lines.append(f"{checkbox} {todo['text']}")

        todo_list_text = "\n".join(todo_lines)

        return {
            "template": """
    {% frame title="Todo List" border="rounded" width=60 %}
      {% vstack spacing=1 padding=1 %}
        Progress: {{ completed }}/{{ total }} completed

        {{ todo_list }}

        [a] Add  [d] Delete  [Space] Toggle  [q] Quit
      {% endvstack %}
    {% endframe %}
            """,
            "data": {
                "completed": completed,
                "total": total,
                "todo_list": todo_list_text,
            },
        }

Run it again. You should now see a nicely formatted todo list with checkboxes!

What's Happening Here?
~~~~~~~~~~~~~~~~~~~~~~

1. We calculate ``completed`` and ``total`` counts
2. We build a formatted string with checkboxes for each todo
3. We use a Jinja2 template with ``{% frame %}`` and ``{% vstack %}`` tags
4. We pass data to the template via the ``data`` dict

Step 3: Add Keyboard Handlers
------------------------------

Let's add the ability to quit with 'q':

.. code-block:: python

    @app.view("main", default=True)
    def main_view():
        # ... (same as before) ...
        return {
            "template": """...""",
            "data": {...},
            "on_enter": setup_handlers,  # Add this line
        }

    def setup_handlers():
        """Set up keyboard handlers for the main view."""
        def on_quit_key(event):
            if event.key == "q":
                app.quit()

        app.on(EventType.KEY, on_quit_key, scope=HandlerScope.VIEW, view_name="main")

Now you can press 'q' to quit the app!

Step 4: Toggle Todo Completion
-------------------------------

Add the ability to toggle todos with the spacebar:

.. code-block:: python

    def setup_handlers():
        # ... previous quit handler ...

        # Add state for selected todo
        app.state.setdefault("selected_index", 0)

        def on_toggle_key(event):
            if event.key == "space":
                todos = app.state["todos"]
                selected_index = app.state["selected_index"]
                if 0 <= selected_index < len(todos):
                    todos[selected_index]["done"] = not todos[selected_index]["done"]
                    app.refresh()  # Manually refresh the UI

        app.on(EventType.KEY, on_toggle_key, scope=HandlerScope.VIEW, view_name="main")

        # ... register handlers ...

Update the view to show which todo is selected:

.. code-block:: python

    def main_view():
        # ... (previous code) ...

        # Update todo list to show selection
        todo_lines = []
        for i, todo in enumerate(todos):
            checkbox = "[X]" if todo["done"] else "[ ]"
            marker = ">" if i == app.state.get("selected_index", 0) else " "
            todo_lines.append(f"{marker} {checkbox} {todo['text']}")

        # ... rest of the code ...

Now the selected todo has a ``>`` marker, and you can press Space to toggle it!

Step 5: Navigate Through Todos
-------------------------------

Add up/down arrow navigation:

.. code-block:: python

    def setup_handlers():
        # ... previous handlers ...

        def on_navigate_key(event):
            todos = app.state["todos"]
            if event.key == "up":
                if todos and app.state["selected_index"] > 0:
                    app.state["selected_index"] -= 1
            elif event.key == "down":
                if todos and app.state["selected_index"] < len(todos) - 1:
                    app.state["selected_index"] += 1

        app.on(EventType.KEY, on_navigate_key, scope=HandlerScope.VIEW, view_name="main")

Now you can navigate with arrow keys!

Step 6: Delete Todos
--------------------

Add the ability to delete todos with 'd':

.. code-block:: python

    def setup_handlers():
        # ... previous handlers ...

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

        app.on(EventType.KEY, on_delete_key, scope=HandlerScope.VIEW, view_name="main")

Step 7: Add New Todos
---------------------

This is more complex. We'll add an "add mode" with a text input:

First, add state for the add mode:

.. code-block:: python

    app = Wijjit(initial_state={
        "todos": [...],
        "next_id": 3,
        "new_todo": "",
        "adding_todo": False,  # Controls whether input field is visible
    })

Update the template to show the input when in add mode:

.. code-block:: python

    def main_view():
        # ... (previous code) ...

        return {
            "template": """
    {% frame title="Todo List" border="rounded" width=60 %}
      {% vstack spacing=1 padding=1 %}
        Progress: {{ completed }}/{{ total }} completed

        {% if state.adding_todo %}
          {% hstack spacing=2 %}
            {% textinput id="new_todo" placeholder="Enter new todo..." width=30 action="add_todo" %}{% endtextinput %}
            {% button action="add_todo" %}Add{% endbutton %}
            {% button action="cancel_add" %}Cancel{% endbutton %}
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
            "data": {...},
        }

Add handlers for entering and exiting add mode:

.. code-block:: python

    def setup_handlers():
        # ... previous handlers ...

        def on_add_key(event):
            if event.key == "a" and not app.state.get("adding_todo", False):
                app.state["adding_todo"] = True
                app.state["new_todo"] = ""

        def on_escape_key(event):
            if event.key == "escape" and app.state.get("adding_todo", False):
                app.state["adding_todo"] = False

        app.on(EventType.KEY, on_add_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_escape_key, scope=HandlerScope.VIEW, view_name="main")

Add action handlers for the buttons:

.. code-block:: python

    @app.on_action("add_todo")
    def handle_add_todo(event):
        """Handle add todo action from button or Enter key in input."""
        todo_text = app.state.get('new_todo', '').strip()

        if todo_text:
            new_id = app.state["next_id"]
            app.state["todos"].append({
                "id": new_id,
                "text": todo_text,
                "done": False,
            })
            app.state["next_id"] = new_id + 1
            app.state["new_todo"] = ""
            app.state["adding_todo"] = False

    @app.on_action("cancel_add")
    def handle_cancel_add(event):
        """Handle cancel action."""
        app.state["adding_todo"] = False
        app.state["new_todo"] = ""

Complete Code
-------------

Here's the complete todo app:

.. code-block:: python

    from wijjit import Wijjit
    from wijjit.core.events import EventType, HandlerScope

    app = Wijjit(initial_state={
        "todos": [
            {"id": 1, "text": "Learn Wijjit", "done": False},
            {"id": 2, "text": "Build a TUI app", "done": False},
        ],
        "next_id": 3,
        "new_todo": "",
        "selected_index": 0,
        "adding_todo": False,
    })

    @app.view("main", default=True)
    def main_view():
        todos = app.state["todos"]
        completed = sum(1 for todo in todos if todo["done"])
        total = len(todos)

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
            {% button action="add_todo" %}Add{% endbutton %}
            {% button action="cancel_add" %}Cancel{% endbutton %}
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
        def on_quit_key(event):
            if event.key == "q":
                app.quit()

        def on_add_key(event):
            if event.key == "a" and not app.state.get("adding_todo", False):
                app.state["adding_todo"] = True
                app.state["new_todo"] = ""

        def on_escape_key(event):
            if event.key == "escape" and app.state.get("adding_todo", False):
                app.state["adding_todo"] = False

        def on_delete_key(event):
            if event.key == "d" and not app.state.get("adding_todo", False):
                todos = app.state["todos"]
                selected_index = app.state["selected_index"]
                if 0 <= selected_index < len(todos):
                    todos.pop(selected_index)
                    if app.state["selected_index"] >= len(todos) and todos:
                        app.state["selected_index"] = len(todos) - 1
                    app.refresh()

        def on_toggle_key(event):
            if event.key == "space" and not app.state.get("adding_todo", False):
                todos = app.state["todos"]
                selected_index = app.state["selected_index"]
                if 0 <= selected_index < len(todos):
                    todos[selected_index]["done"] = not todos[selected_index]["done"]
                    app.refresh()

        def on_navigate_key(event):
            if not app.state.get("adding_todo", False):
                todos = app.state["todos"]
                if event.key == "up" and todos and app.state["selected_index"] > 0:
                    app.state["selected_index"] -= 1
                elif event.key == "down" and todos:
                    if app.state["selected_index"] < len(todos) - 1:
                        app.state["selected_index"] += 1

        app.on(EventType.KEY, on_quit_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_add_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_escape_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_delete_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_toggle_key, scope=HandlerScope.VIEW, view_name="main")
        app.on(EventType.KEY, on_navigate_key, scope=HandlerScope.VIEW, view_name="main")

    @app.on_action("add_todo")
    def handle_add_todo(event):
        todo_text = app.state.get('new_todo', '').strip()
        if todo_text:
            new_id = app.state["next_id"]
            app.state["todos"].append({
                "id": new_id,
                "text": todo_text,
                "done": False,
            })
            app.state["next_id"] = new_id + 1
            app.state["new_todo"] = ""
            app.state["adding_todo"] = False

    @app.on_action("cancel_add")
    def handle_cancel_add(event):
        app.state["adding_todo"] = False
        app.state["new_todo"] = ""

    if __name__ == '__main__':
        app.run()

Congratulations!
----------------

You've built a complete, functional todo list application! You've learned:

* State management with reactive updates
* Jinja2 templates with custom tags
* Event handling (keyboard and actions)
* Conditional rendering (``{% if %}`` in templates)
* Layout components (frames, stacks)
* Input components (textinput, button)

Next Steps
----------

Now that you've completed the tutorial, you can:

* Explore more :doc:`../examples/index` for inspiration
* Learn about all available :doc:`../user_guide/components`
* Read about :doc:`../user_guide/state_management` in depth
* Check out the :doc:`../user_guide/layout_system` for complex layouts

Challenges
----------

Try extending the app with these features:

1. **Persistence**: Save todos to a file and load them on startup
2. **Categories**: Add tags or categories to todos
3. **Due Dates**: Add due dates and highlight overdue items
4. **Priority**: Add priority levels (high, medium, low)
5. **Search**: Add a search feature to filter todos
6. **Multi-view**: Create separate views for different todo lists

For examples of these features, check out ``examples/todo_app.py`` in the Wijjit repository!
