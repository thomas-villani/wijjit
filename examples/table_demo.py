"""Table demo showcasing all features.

This example demonstrates:
- Basic table display with Rich formatting
- Column sorting with visual indicators
- Scrolling for large datasets
- Different border styles
- State binding for dynamic updates
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Sample data
users_data = [
    {"name": "Alice Johnson", "email": "alice@example.com", "status": "Active", "age": 28},
    {"name": "Bob Smith", "email": "bob@example.com", "status": "Inactive", "age": 34},
    {"name": "Carol White", "email": "carol@example.com", "status": "Active", "age": 42},
    {"name": "David Brown", "email": "david@example.com", "status": "Active", "age": 31},
    {"name": "Eve Davis", "email": "eve@example.com", "status": "Pending", "age": 25},
    {"name": "Frank Miller", "email": "frank@example.com", "status": "Active", "age": 39},
    {"name": "Grace Wilson", "email": "grace@example.com", "status": "Inactive", "age": 29},
    {"name": "Henry Moore", "email": "henry@example.com", "status": "Active", "age": 45},
    {"name": "Ivy Taylor", "email": "ivy@example.com", "status": "Active", "age": 33},
    {"name": "Jack Anderson", "email": "jack@example.com", "status": "Pending", "age": 27},
    {"name": "Kate Thomas", "email": "kate@example.com", "status": "Active", "age": 36},
    {"name": "Leo Jackson", "email": "leo@example.com", "status": "Active", "age": 41},
    {"name": "Mia Martin", "email": "mia@example.com", "status": "Inactive", "age": 30},
    {"name": "Noah Lee", "email": "noah@example.com", "status": "Active", "age": 38},
    {"name": "Olivia Harris", "email": "olivia@example.com", "status": "Active", "age": 26},
]

# Create app with initial state
app = Wijjit(
    initial_state={
        "users": users_data,
        "message": "Welcome to Table Demo! Scroll with mouse wheel or arrow keys. Click headers to sort.",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing table element."""
    return {
        "template": """
{% frame title="Table Demo - User Directory" border="double" width=100 height=35 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.message }}
    {% endvstack %}

    {% vstack spacing=0 %}
      Instructions: Press TAB to focus table | Use Up/Down/PageUp/PageDown to scroll | Mouse wheel also works | Press 'q' to quit
    {% endvstack %}

    {% table id="users"
             data=state.users
             columns=["name", "email", "status", "age"]
             sortable=true
             width=94
             height=20
             show_header=true
             show_scrollbar=true
             border_style="single" %}
    {% endtable %}

    {% hstack spacing=2 %}
      {% button id="add_user_btn" action="add_user" %}Add User{% endbutton %}
      {% button id="clear_btn" action="clear_table" %}Clear Table{% endbutton %}
      {% button id="reset_btn" action="reset_table" %}Reset Table{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,  # noqa: E501
        "data": {},
    }


# Sample user counter for adding users
user_counter = 16


@app.on_action("add_user")
def handle_add_user(event):
    """Add a new user to the table."""
    global user_counter

    new_user = {
        "name": f"User {user_counter}",
        "email": f"user{user_counter}@example.com",
        "status": "Active",
        "age": 20 + (user_counter % 30),
    }

    current_users = app.state.get("users", [])
    current_users.append(new_user)
    app.state["users"] = current_users
    app.state["message"] = f"Added {new_user['name']} to the table"

    user_counter += 1


@app.on_action("clear_table")
def handle_clear(event):
    """Clear all users from the table."""
    app.state["users"] = []
    app.state["message"] = "Table cleared"


@app.on_action("reset_table")
def handle_reset(event):
    """Reset table to original data."""
    app.state["users"] = users_data.copy()
    app.state["message"] = "Table reset to original data"


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
    # Use mouse wheel or Up/Down to scroll
    # Click column headers to sort
    # Press 'q' to quit
    app.run()
