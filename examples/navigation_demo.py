"""Navigation Demo - Multi-View Navigation Example for Wijjit.

This example demonstrates the Wijjit framework's multi-view navigation features:
- Multiple views with navigation between them
- View-scoped handlers that are automatically cleaned up on navigation
- View lifecycle hooks (on_enter and on_exit)
- State persistence across view changes
- Both button-based and keyboard-based navigation
- Global vs view-scoped event handlers

Run with: python examples/navigation_demo.py
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Create app with initial state
app = Wijjit(initial_state={
    "home_visits": 0,
    "profile_visits": 0,
    "home_message": "",
    "profile_message": "",
    "username": "Alice",
})


@app.view("home", default=True)
def home_view():
    """Home view with visit counter and navigation."""
    return {
        "template": """
{% frame title="Home View" border="rounded" width=60 height=15 %}
  {% vstack spacing=1 padding=2 %}
    Welcome to the Home View!

    This view has been visited {{ state.home_visits }} time(s).

    {% if state.home_message %}
    Message: {{ state.home_message }}
    {% endif %}

    Press 'h' to show a home-specific message.

    {% hstack spacing=2 %}
      {% button action="go_to_profile" %}Go to Profile{% endbutton %}
    {% endhstack %}

    Navigation: [1] Home  [2] Profile  [q] Quit
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
        "on_enter": setup_home_handlers,
        "on_exit": cleanup_home,
    }


@app.view("profile")
def profile_view():
    """Profile view with user info and navigation."""
    return {
        "template": """
{% frame title="Profile View" border="rounded" width=60 height=15 %}
  {% vstack spacing=1 padding=2 %}
    User Profile: {{ state.username }}

    This view has been visited {{ state.profile_visits }} time(s).

    {% if state.profile_message %}
    Message: {{ state.profile_message }}
    {% endif %}

    Press 'p' to show a profile-specific message.

    {% hstack spacing=2 %}
      {% button action="go_to_home" %}Go to Home{% endbutton %}
    {% endhstack %}

    Navigation: [1] Home  [2] Profile  [q] Quit
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
        "on_enter": setup_profile_handlers,
        "on_exit": cleanup_profile,
    }


def setup_home_handlers():
    """Set up view-scoped handlers for the home view.

    This function is called when entering the home view via the on_enter hook.
    All handlers registered here are automatically cleaned up when navigating away.
    """
    # Increment visit counter
    app.state["home_visits"] += 1
    # Clear any previous message
    app.state["home_message"] = ""

    # View-scoped handler for 'h' key - only works in home view
    def on_h_key(event):
        if event.key == "h":
            app.state["home_message"] = "Hello from Home view! (Press 'h' triggered)"
            app.refresh()

    # Register as view-scoped handler - will be auto-cleared on navigation
    app.on(EventType.KEY, on_h_key, scope=HandlerScope.VIEW, view_name="home")


def cleanup_home():
    """Called when leaving the home view.

    This is where you'd do any cleanup needed before leaving the view.
    Note: View-scoped handlers are automatically cleaned up by the framework.
    """
    pass  # Nothing to clean up manually - handlers are auto-cleaned


def setup_profile_handlers():
    """Set up view-scoped handlers for the profile view.

    This function is called when entering the profile view via the on_enter hook.
    All handlers registered here are automatically cleaned up when navigating away.
    """
    # Increment visit counter
    app.state["profile_visits"] += 1
    # Clear any previous message
    app.state["profile_message"] = ""

    # View-scoped handler for 'p' key - only works in profile view
    def on_p_key(event):
        if event.key == "p":
            app.state["profile_message"] = "Profile info loaded! (Press 'p' triggered)"
            app.refresh()

    # Register as view-scoped handler - will be auto-cleared on navigation
    app.on(EventType.KEY, on_p_key, scope=HandlerScope.VIEW, view_name="profile")


def cleanup_profile():
    """Called when leaving the profile view.

    This is where you'd do any cleanup needed before leaving the view.
    Note: View-scoped handlers are automatically cleaned up by the framework.
    """
    pass  # Nothing to clean up manually - handlers are auto-cleaned


# Action handlers for button navigation
@app.on_action("go_to_home")
def handle_go_to_home(event):
    """Navigate to home view via button click."""
    app.navigate("home")


@app.on_action("go_to_profile")
def handle_go_to_profile(event):
    """Navigate to profile view via button click."""
    app.navigate("profile")


# Global keyboard navigation handlers
# These handlers work from any view
def setup_global_handlers():
    """Set up global navigation key handlers.

    These handlers are scoped globally and work from any view.
    """
    def on_number_keys(event):
        """Handle number key navigation."""
        if event.key == "1":
            app.navigate("home")
        elif event.key == "2":
            app.navigate("profile")

    def on_quit_key(event):
        """Handle quit key."""
        if event.key == "q":
            app.quit()

    # Register as global handlers - work from any view
    app.on(EventType.KEY, on_number_keys, scope=HandlerScope.GLOBAL)
    app.on(EventType.KEY, on_quit_key, scope=HandlerScope.GLOBAL)


if __name__ == '__main__':
    # Set up global navigation handlers before running
    setup_global_handlers()

    # Run the app
    # Navigation methods:
    # 1. Click buttons with Tab/Enter
    # 2. Press '1' for Home, '2' for Profile
    # 3. Press 'h' in Home view or 'p' in Profile view for view-specific messages
    # 4. Press 'q' to quit
    print("Navigation Demo")
    print("===============")
    print("This demo shows multi-view navigation with:")
    print("- View-scoped handlers (h=home msg, p=profile msg)")
    print("- Lifecycle hooks (visit counters)")
    print("- State persistence (counters maintained)")
    print("- Button navigation (Tab + Enter)")
    print("- Keyboard navigation (1=Home, 2=Profile, q=Quit)")
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
