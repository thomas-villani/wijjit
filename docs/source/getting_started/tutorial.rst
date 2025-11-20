Tutorial: Persistent Todo App
=============================

This tutorial walks through a production-style Wijjit project: a todo list that survives restarts by saving to a JSON file. Along the way you will touch state management, templates, actions, keyboard shortcuts, and small helper modules.

What you’ll build
-----------------

* Add, complete, and delete todos.
* Filter between “all / active / done”.
* Display progress and friendly status messages.
* Persist todos to ``~/.wijjit_todos.json`` automatically.

Prerequisites
-------------

* Python 3.11+
* Wijjit installed (see :doc:`installation`)
* Familiarity with virtual environments and running Python scripts

Project layout
--------------

Create a new directory (``tutorial_todo/``) with a single file to start:

.. code-block:: text

    tutorial_todo/
    └── todo_app.py

Open ``todo_app.py`` in your editor; we’ll expand it step by step.

Step 1 – bootstrap the app and storage helpers
---------------------------------------------

Start with the imports, storage helpers, and ``Wijjit`` instance:

.. code-block:: python
   :caption: todo_app.py

    from __future__ import annotations

    import json
    from pathlib import Path
    from typing import Any

    from wijjit import Wijjit

    DATA_PATH = Path.home() / ".wijjit_todos.json"


    def load_todos() -> tuple[list[dict[str, Any]], int]:
        if not DATA_PATH.exists():
            return [], 1
        payload = json.loads(DATA_PATH.read_text())
        todos = payload.get("todos", [])
        next_id = payload.get("next_id", len(todos) + 1)
        return todos, next_id


    def save_todos(todos: list[dict[str, Any]], next_id: int) -> None:
        DATA_PATH.write_text(json.dumps({"todos": todos, "next_id": next_id}, indent=2))


    todos, next_id = load_todos()

    app = Wijjit(
        initial_state={
            "todos": todos,
            "next_id": next_id,
            "filter": "all",
            "status": "Press Enter to add a task",
        }
    )

This gives us persistence before writing any UI. The state keys will drive the template shortly.

Step 2 – render the UI with template tags
-----------------------------------------

Add the main view below the app definition:

.. code-block:: python

    @app.view("main", default=True)
    def main_view():
        todos = app.state["todos"]
        filter_mode = app.state["filter"]

        filtered = [
            todo for todo in todos
            if filter_mode == "all"
            or (filter_mode == "active" and not todo["done"])
            or (filter_mode == "done" and todo["done"])
        ]
        completed = sum(1 for todo in todos if todo["done"])

        return {
            "template": """
    {% frame title="Wijjit Todos" border="rounded" width=70 height=24 %}
      {% vstack spacing=1 padding=1 %}
        {{ state.status }}

        {% hstack spacing=1 %}
          {% textinput id="new_todo" placeholder="Add a task and press Enter" width="fill" action="add_todo" %}
          {% endtextinput %}
          {% button action="clear_done" variant="secondary" %}Clear Done{% endbutton %}
        {% endhstack %}

        {% hstack spacing=1 %}
          {% button action="filter_all" variant="secondary" %}All{% endbutton %}
          {% button action="filter_active" variant="secondary" %}Active{% endbutton %}
          {% button action="filter_done" variant="secondary" %}Done{% endbutton %}
          {% spacer width="fill" %}
          Completed: {{ completed }}/{{ todos|length }}
        {% endhstack %}

        {% frame title="Tasks" height="fill" scrollable=True %}
          {% vstack spacing=0 %}
            {% for todo in filtered %}
              {% hstack spacing=1 padding=0 %}
                {% checkbox id="todo_{{ todo.id }}" bind=False
                             action="toggle_{{ todo.id }}"
                             checked=todo.done %}
                {% endcheckbox %}
                {% text element="span" %}
                  {{ todo.text }}
                {% endtext %}
                {% spacer width="fill" %}
                {% button action="delete_{{ todo.id }}" variant="ghost" %}×{% endbutton %}
              {% endhstack %}
            {% else %}
              No tasks matching this filter.
            {% endfor %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endframe %}
            """,
            "data": {
                "todos": todos,
                "filtered": filtered,
                "completed": completed,
            },
        }

Run ``python todo_app.py`` now. You’ll see the frame, inputs, and buttons, though actions don’t do anything yet.

Step 3 – wire actions and keyboard shortcuts
--------------------------------------------

Add the handlers at the bottom of the file:

.. code-block:: python

    from wijjit.core.events import ActionEvent, EventType, HandlerScope


    def persist() -> None:
        save_todos(app.state["todos"], app.state["next_id"])


    @app.on_action("add_todo")
    def add_todo(_event):
        text = app.state.get("new_todo", "").strip()
        if not text:
            app.state["status"] = "Enter something before pressing Enter."
            return

        todo = {"id": app.state["next_id"], "text": text, "done": False}
        app.state["todos"] = app.state["todos"] + [todo]
        app.state["next_id"] += 1
        app.state["new_todo"] = ""
        app.state["status"] = f"Created '{text}'."
        persist()


    @app.on_action("clear_done")
    def clear_completed(_event):
        before = len(app.state["todos"])
        app.state["todos"] = [todo for todo in app.state["todos"] if not todo["done"]]
        removed = before - len(app.state["todos"])
        app.state["status"] = f"Cleared {removed} completed task(s)."
        persist()


    FILTER_ACTIONS = {
        "filter_all": "all",
        "filter_active": "active",
        "filter_done": "done",
    }


    for action_name, mode in FILTER_ACTIONS.items():
        @app.on_action(action_name)
        def _set_filter(_event, mode=mode):
            app.state["filter"] = mode
            app.state["status"] = f"Showing {mode} tasks."


    @app.on(EventType.ACTION, scope=HandlerScope.VIEW)
    def handle_item_actions(event: ActionEvent):
        action = (event.action_id or "")
        if action.startswith("toggle_"):
            todo_id = int(action.split("_", 1)[1])
            todos = app.state["todos"]
            for todo in todos:
                if todo["id"] == todo_id:
                    todo["done"] = not todo["done"]
                    app.state["status"] = (
                        f"Marked '{todo['text']}' as "
                        + ("done." if todo["done"] else "active.")
                    )
                    break
            app.state["todos"] = list(todos)
            persist()
        elif action.startswith("delete_"):
            todo_id = int(action.split("_", 1)[1])
            todos = app.state["todos"]
            app.state["todos"] = [todo for todo in todos if todo["id"] != todo_id]
            app.state["status"] = "Task deleted."
            persist()

This setup keeps the code compact: a single handler inspects ``ActionEvent.action_id`` to determine whether the user clicked a checkbox or delete button, so you don’t need to dynamically register per-item callbacks.

Step 4 – polish and run
-----------------------

Add a manual save shortcut (handy before quitting) and start the app:

.. code-block:: python

    @app.on_key("ctrl+s")
    def save_now(_event):
        persist()
        app.state["status"] = "Saved manually."


    if __name__ == "__main__":
        app.run()

Save the file, run ``python todo_app.py``, and exercise the workflow:

* Type a task, press Enter → task appears and persists.
* Press the checkbox or hit the toggle button → status updates.
* Switch filters using the filter buttons.
* Quit with ``Ctrl+C`` and restart → todos rehydrate from disk.

Full source listing
-------------------

If you prefer a single block to copy, here is the finished script:

.. code-block:: python
   :caption: todo_app.py

    from __future__ import annotations

    import json
    from pathlib import Path
    from typing import Any

    from wijjit import Wijjit
    from wijjit.core.events import ActionEvent, EventType, HandlerScope

    DATA_PATH = Path.home() / ".wijjit_todos.json"


    def load_todos() -> tuple[list[dict[str, Any]], int]:
        if not DATA_PATH.exists():
            return [], 1
        payload = json.loads(DATA_PATH.read_text())
        todos = payload.get("todos", [])
        next_id = payload.get("next_id", len(todos) + 1)
        return todos, next_id


    def save_todos(todos: list[dict[str, Any]], next_id: int) -> None:
        DATA_PATH.write_text(json.dumps({"todos": todos, "next_id": next_id}, indent=2))


    todos, next_id = load_todos()

    app = Wijjit(
        initial_state={
            "todos": todos,
            "next_id": next_id,
            "filter": "all",
            "status": "Press Enter to add a task",
            "new_todo": "",
        }
    )


    @app.view("main", default=True)
    def main_view():
        todos = app.state["todos"]
        filter_mode = app.state["filter"]

        filtered = [
            todo
            for todo in todos
            if filter_mode == "all"
            or (filter_mode == "active" and not todo["done"])
            or (filter_mode == "done" and todo["done"])
        ]
        completed = sum(1 for todo in todos if todo["done"])

        return {
            "template": """
    {% frame title="Wijjit Todos" border="rounded" width=70 height=24 %}
      {% vstack spacing=1 padding=1 %}
        {{ state.status }}

        {% hstack spacing=1 %}
          {% textinput id="new_todo" placeholder="Add a task and press Enter" width="fill" action="add_todo" %}
          {% endtextinput %}
          {% button action="clear_done" variant="secondary" %}Clear Done{% endbutton %}
        {% endhstack %}

        {% hstack spacing=1 %}
          {% button action="filter_all" variant="secondary" %}All{% endbutton %}
          {% button action="filter_active" variant="secondary" %}Active{% endbutton %}
          {% button action="filter_done" variant="secondary" %}Done{% endbutton %}
          {% spacer width="fill" %}
          Completed: {{ completed }}/{{ todos|length }}
        {% endhstack %}

        {% frame title="Tasks" height="fill" scrollable=True %}
          {% vstack spacing=0 %}
            {% for todo in filtered %}
              {% hstack spacing=1 padding=0 %}
                {% checkbox id="todo_{{ todo.id }}" bind=False action="toggle_{{ todo.id }}" checked=todo.done %}
                {% endcheckbox %}
                {% text element="span" %}
                  {{ todo.text }}
                {% endtext %}
                {% spacer width="fill" %}
                {% button action="delete_{{ todo.id }}" variant="ghost" %}×{% endbutton %}
              {% endhstack %}
            {% else %}
              No tasks matching this filter.
            {% endfor %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endframe %}
            """,
            "data": {"todos": todos, "filtered": filtered, "completed": completed},
        }


    def persist() -> None:
        save_todos(app.state["todos"], app.state["next_id"])


    @app.on_action("add_todo")
    def add_todo(_event):
        text = app.state.get("new_todo", "").strip()
        if not text:
            app.state["status"] = "Enter something before pressing Enter."
            return

        todo = {"id": app.state["next_id"], "text": text, "done": False}
        app.state["todos"] = app.state["todos"] + [todo]
        app.state["next_id"] += 1
        app.state["new_todo"] = ""
        app.state["status"] = f"Created '{text}'."
        persist()


    @app.on_action("clear_done")
    def clear_completed(_event):
        before = len(app.state["todos"])
        app.state["todos"] = [todo for todo in app.state["todos"] if not todo["done"]]
        removed = before - len(app.state["todos"])
        app.state["status"] = f"Cleared {removed} completed task(s)."
        persist()


    FILTER_ACTIONS = {
        "filter_all": "all",
        "filter_active": "active",
        "filter_done": "done",
    }


    for action_name, mode in FILTER_ACTIONS.items():
        @app.on_action(action_name)
        def _set_filter(_event, mode=mode):
            app.state["filter"] = mode
            app.state["status"] = f"Showing {mode} tasks."


    @app.on(EventType.ACTION, scope=HandlerScope.VIEW)
    def handle_item_actions(event: ActionEvent):
        action = (event.action_id or "")
        if action.startswith("toggle_"):
            todo_id = int(action.split("_", 1)[1])
            todos = app.state["todos"]
            for todo in todos:
                if todo["id"] == todo_id:
                    todo["done"] = not todo["done"]
                    app.state["status"] = (
                        f"Marked '{todo['text']}' as "
                        + ("done." if todo["done"] else "active.")
                    )
                    break
            app.state["todos"] = list(todos)
            persist()
        elif action.startswith("delete_"):
            todo_id = int(action.split("_", 1)[1])
            todos = app.state["todos"]
            app.state["todos"] = [todo for todo in todos if todo["id"] != todo_id]
            app.state["status"] = "Task deleted."
            persist()


    @app.on_key("ctrl+s")
    def save_now(_event):
        persist()
        app.state["status"] = "Saved manually."


    if __name__ == "__main__":
        app.run()

Next steps
----------

* Explore :doc:`../user_guide/state_management` to learn more about watchers and derived data.
* Try splitting the storage helpers into a separate module or injecting different persistence backends (SQLite, HTTP API) to fit your workflow.
* Add overlays for confirmation (see :doc:`../user_guide/modal_dialogs`) or richer lists (tables, drag-and-drop) by browsing :doc:`../examples/index`.
