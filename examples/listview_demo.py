"""ListView demo showcasing all features.

This example demonstrates:
- Simple bulleted lists
- Numbered lists
- Dashed lists
- Plain lists (no bullets)
- Lists with details (definition-style)
- Horizontal dividers
- Scrolling for long lists
- Different border styles
- Dynamic updates via state
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Sample data - simple strings
fruits = ["Apple", "Banana", "Cherry", "Date", "Elderberry", "Fig"]

# Sample data - with details (tuples)
programming_languages = [
    ("Python", "High-level, interpreted language\nGreat for scripting and data science"),
    ("JavaScript", "Dynamic scripting language\nRuns in browsers and Node.js"),
    ("Rust", "Systems programming language\nMemory-safe without garbage collection"),
    ("Go", "Compiled language by Google\nDesigned for concurrency and simplicity"),
]

# Sample data - tasks with details (dicts)
tasks = [
    {"label": "Design API", "details": "Create RESTful API design\nDefine endpoints and schemas"},
    {"label": "Implement backend", "details": "Build server with FastAPI\nConnect to database"},
    {"label": "Create frontend", "details": "Build React components\nIntegrate with API"},
    {"label": "Write tests", "details": "Unit tests for all modules\nIntegration tests for API"},
    {"label": "Deploy", "details": "Set up CI/CD pipeline\nDeploy to production"},
]

# Create app with initial state
app = Wijjit(
    initial_state={
        "fruits": fruits,
        "languages": programming_languages,
        "tasks": tasks,
        "message": "Welcome to ListView Demo! Scroll with mouse wheel or arrow keys. Press Tab to navigate.",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing ListView elements."""
    return {
        "template": """
{% frame title="ListView Demo - Multiple Styles" border="double" width=110 height=30 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.message }}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% vstack spacing=1 %}
        {% listview id="fruits_bullet"
                    items=state.fruits
                    bullet="bullet"
                    width=24
                    height=7
                    border_style="single"
                    title="Bullets"
                    show_scrollbar=true %}
        {% endlistview %}

        {% listview id="fruits_number"
                    items=state.fruits
                    bullet="number"
                    width=24
                    height=7
                    border_style="rounded"
                    title="Numbered"
                    show_scrollbar=true %}
        {% endlistview %}
      {% endvstack %}

      {% vstack spacing=1 %}
        {% listview id="fruits_dash"
                    items=state.fruits
                    bullet="dash"
                    width=24
                    height=7
                    border_style="double"
                    title="Dashes"
                    show_scrollbar=true %}
        {% endlistview %}

        {% listview id="fruits_plain"
                    items=state.fruits
                    bullet=none
                    width=24
                    height=7
                    border_style="single"
                    title="Plain"
                    show_scrollbar=true %}
        {% endlistview %}
      {% endvstack %}

      {% vstack spacing=1 %}
        {% listview id="languages"
                    items=state.languages
                    bullet="bullet"
                    show_dividers=false
                    width=48
                    height=8
                    border_style="single"
                    title="Languages (Details)"
                    show_scrollbar=true
                    indent_details=2
                    dim_details=true %}
        {% endlistview %}

        {% listview id="tasks"
                    items=state.tasks
                    bullet="number"
                    show_dividers=true
                    width=48
                    height=8
                    border_style="double"
                    title="Tasks (Dividers)"
                    show_scrollbar=true
                    indent_details=2
                    dim_details=true %}
        {% endlistview %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button id="add_fruit_btn" action="add_fruit" %}Add Fruit{% endbutton %}
      {% button id="add_task_btn" action="add_task" %}Add Task{% endbutton %}
      {% button id="clear_btn" action="clear_lists" %}Clear{% endbutton %}
      {% button id="reset_btn" action="reset_lists" %}Reset{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


# Sample fruit counter for adding items
fruit_counter = 1
task_counter = 1


@app.on_action("add_fruit")
def handle_add_fruit(event):
    """Add a new fruit to the list."""
    global fruit_counter

    new_fruit = f"New Fruit {fruit_counter}"

    current_fruits = app.state.get("fruits", [])
    current_fruits.append(new_fruit)
    app.state["fruits"] = current_fruits
    app.state["message"] = f"Added {new_fruit} to the fruits list"

    fruit_counter += 1


@app.on_action("add_task")
def handle_add_task(event):
    """Add a new task to the list."""
    global task_counter

    new_task = {
        "label": f"New Task {task_counter}",
        "details": f"This is a dynamically added task\nTask number {task_counter}",
    }

    current_tasks = app.state.get("tasks", [])
    current_tasks.append(new_task)
    app.state["tasks"] = current_tasks
    app.state["message"] = f"Added New Task {task_counter} to the tasks list"

    task_counter += 1


@app.on_action("clear_lists")
def handle_clear(event):
    """Clear all lists."""
    app.state["fruits"] = []
    app.state["tasks"] = []
    app.state["message"] = "All lists cleared"


@app.on_action("reset_lists")
def handle_reset(event):
    """Reset lists to original data."""
    app.state["fruits"] = fruits.copy()
    app.state["tasks"] = tasks.copy()
    app.state["message"] = "Lists reset to original data"


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
    # Run the app
    # Use mouse wheel or Up/Down to scroll within lists
    # Press Tab to navigate between lists
    # Press 'q' to quit
    app.run()
