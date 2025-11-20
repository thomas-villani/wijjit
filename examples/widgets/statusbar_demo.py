"""StatusBar Demo - Status Bar Example for Wijjit.

This example demonstrates the Wijjit framework's status bar feature:
- View-scoped status bars (different status bar per view)
- Left, center, and right sections
- State binding for dynamic updates
- Color customization
- Integration with navigation and user actions

Run with: python examples/statusbar_demo.py
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope  # Keep for view-scoped handlers

# Create app with initial state
app = Wijjit(
    initial_state={
        "current_file": "app.py",
        "status_message": "Ready",
        "line_number": 1,
        "column_number": 1,
        "edit_count": 0,
        "char_count": 0,
        "word_count": 0,
        "view_name": "Home",
        # Formatted status bar sections
        "sb_left": "File: app.py",
        "sb_center": "Ready",
        "sb_right": "Edits: 0",
    }
)


@app.view("home", default=True)
def home_view():
    """Home view with basic status bar."""
    return {
        "template": """
{% frame title="StatusBar Demo - Home" border="rounded" width=80 height=20 %}
    Welcome to the StatusBar Demo!

    This demo shows view-scoped status bars with:
    - Left-aligned content (file info)
    - Center-aligned content (status message)
    - Right-aligned content (position info)

    Current view: {{ state.view_name }}
    Edit count: {{ state.edit_count }}

    Press 'e' to increment edit count
    Press '1' for Editor view (with position tracking)
    Press '2' for Stats view (with statistics)
    Press 'q' to quit

    {% hstack spacing=2 %}
      {% button action="go_to_editor" %}Editor View{% endbutton %}
      {% button action="go_to_stats" %}Stats View{% endbutton %}
    {% endhstack %}
{% endframe %}

{% statusbar left=state.sb_left
             center=state.sb_center
             right=state.sb_right %}
{% endstatusbar %}
        """,
        "data": {},
        "on_enter": setup_home_handlers,
    }


@app.view("editor")
def editor_view():
    """Editor view with position tracking in status bar."""
    return {
        "template": """
{% frame title="StatusBar Demo - Editor" border="rounded" width=80 height=20 %}
    Editor View

    This view shows a status bar with cursor position information.
    The status bar displays line and column numbers that update
    when you press the arrow keys.

    Current position: Line {{ state.line_number }}, Column {{ state.column_number }}

    Press arrow keys (Up/Down/Left/Right) to move cursor
    Press '1' for Home view
    Press '2' for Stats view
    Press 'q' to quit

    {% hstack spacing=2 %}
      {% button action="go_to_home" %}Home{% endbutton %}
      {% button action="go_to_stats" %}Stats View{% endbutton %}
    {% endhstack %}
{% endframe %}

{% statusbar left=state.sb_left
             center=state.sb_center
             right=state.sb_right
             bg_color="blue"
             text_color="white" %}
{% endstatusbar %}
        """,
        "data": {},
        "on_enter": setup_editor_handlers,
    }


@app.view("stats")
def stats_view():
    """Stats view with document statistics in status bar."""
    return {
        "template": """
{% frame title="StatusBar Demo - Statistics" border="rounded" width=80 height=20 %}
    Statistics View

    This view shows document statistics in the status bar.
    The statistics update when you press 'a' to add words.

    Document Statistics:
    - Characters: {{ state.char_count }}
    - Words: {{ state.word_count }}

    Press 'a' to add 100 words
    Press '1' for Home view
    Press '2' for Editor view
    Press 'q' to quit

    {% hstack spacing=2 %}
      {% button action="go_to_home" %}Home{% endbutton %}
      {% button action="go_to_editor" %}Editor View{% endbutton %}
    {% endhstack %}
{% endframe %}

{% statusbar left=state.sb_left
             center=state.sb_center
             right=state.sb_right
             bg_color="green"
             text_color="black" %}
{% endstatusbar %}
        """,
        "data": {},
        "on_enter": setup_stats_handlers,
    }


def setup_home_handlers():
    """Set up view-scoped handlers for the home view."""
    app.state["view_name"] = "Home"
    app.state["status_message"] = "Ready"
    # Update statusbar for home view
    app.state["sb_left"] = f"File: {app.state['current_file']}"
    app.state["sb_center"] = "Ready"
    app.state["sb_right"] = f"Edits: {app.state['edit_count']}"

    def on_e_key(event):
        if event.key == "e":
            app.state["edit_count"] += 1
            app.state["status_message"] = f"Edit #{app.state['edit_count']}"
            # Update statusbar
            app.state["sb_center"] = app.state["status_message"]
            app.state["sb_right"] = f"Edits: {app.state['edit_count']}"
            app.refresh()

    app.on(EventType.KEY, on_e_key, scope=HandlerScope.VIEW, view_name="home")


def setup_editor_handlers():
    """Set up view-scoped handlers for the editor view."""
    app.state["view_name"] = "Editor"
    app.state["status_message"] = "Editing"
    # Update statusbar for editor view
    app.state["sb_left"] = f"{app.state['current_file']} [modified]"
    app.state["sb_center"] = "-- INSERT --"
    app.state["sb_right"] = (
        f"Ln {app.state['line_number']}, Col {app.state['column_number']}"
    )

    def on_arrow_keys(event):
        if event.key == "up":
            app.state["line_number"] = max(1, app.state["line_number"] - 1)
        elif event.key == "down":
            app.state["line_number"] += 1
        elif event.key == "left":
            app.state["column_number"] = max(1, app.state["column_number"] - 1)
        elif event.key == "right":
            app.state["column_number"] += 1

        # Update statusbar
        app.state["sb_right"] = (
            f"Ln {app.state['line_number']}, Col {app.state['column_number']}"
        )
        app.refresh()

    app.on(EventType.KEY, on_arrow_keys, scope=HandlerScope.VIEW, view_name="editor")


def setup_stats_handlers():
    """Set up view-scoped handlers for the stats view."""
    app.state["view_name"] = "Stats"
    app.state["status_message"] = "Viewing stats"
    # Update statusbar for stats view
    app.state["sb_left"] = f"Document: {app.state['current_file']}"
    app.state["sb_center"] = "Statistics Mode"
    app.state["sb_right"] = (
        f"Chars: {app.state['char_count']} | Words: {app.state['word_count']}"
    )

    def on_a_key(event):
        if event.key == "a":
            app.state["word_count"] += 100
            app.state["char_count"] += 500
            # Update statusbar
            app.state["sb_right"] = (
                f"Chars: {app.state['char_count']} | Words: {app.state['word_count']}"
            )
            app.refresh()

    app.on(EventType.KEY, on_a_key, scope=HandlerScope.VIEW, view_name="stats")


# Action handlers for button navigation
@app.on_action("go_to_home")
def handle_go_to_home(event):
    """Navigate to home view."""
    app.navigate("home")


@app.on_action("go_to_editor")
def handle_go_to_editor(event):
    """Navigate to editor view."""
    app.navigate("editor")


@app.on_action("go_to_stats")
def handle_go_to_stats(event):
    """Navigate to stats view."""
    app.navigate("stats")


# Global keyboard navigation handlers
@app.on_key("1")
def on_key_1(event):
    """Navigate to home view."""
    app.navigate("home")


@app.on_key("2")
def on_key_2(event):
    """Navigate to editor view."""
    app.navigate("editor")


@app.on_key("q")
def on_quit(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":

    print("StatusBar Demo")
    print("==============")
    print("This demo shows view-scoped status bars with:")
    print("- Different status bars for each view")
    print("- Left/center/right content sections")
    print("- State binding for dynamic updates")
    print("- Color customization (blue for editor, green for stats)")
    print()
    print("Navigation:")
    print("- Press '1' for Home view")
    print("- Press '2' for Editor view")
    print("- Press 'q' to quit")
    print()
    print("View-specific actions:")
    print("- Home: Press 'e' to increment edit count")
    print("- Editor: Use arrow keys to move cursor")
    print("- Stats: Press 'a' to add words")
    print()
    print("Starting app...")
    print()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback

        traceback.print_exc()
