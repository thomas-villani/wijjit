"""Navigation Demo - Multi-View Navigation Example.

This example demonstrates the Wijjit framework's multi-view navigation features:
- Multiple views with navigation between them
- View-scoped handlers (automatically cleaned up on navigation)
- View lifecycle hooks (on_enter and on_exit)
- State persistence across view changes
- Both button-based and keyboard-based navigation
- Global vs view-scoped event handlers

Run with: python examples/advanced/navigation_demo.py

Controls:
- 1: Navigate to Home view
- 2: Navigate to Profile view
- 3: Navigate to Settings view
- h: (Home view only) Show home-specific message
- p: (Profile view only) Show profile-specific message
- s: (Settings view only) Show settings-specific message
- Tab/Enter: Navigate via buttons
- q: Quit
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Create app with initial state
app = Wijjit(
    initial_state={
        "home_visits": 0,
        "profile_visits": 0,
        "settings_visits": 0,
        "home_message": "",
        "profile_message": "",
        "settings_message": "",
        "username": "Alice",
        "theme": "Dark",
        "notifications": True,
    }
)


@app.view("home", default=True)
def home_view():
    """Home view with visit counter and navigation.

    Returns
    -------
    dict
        View configuration with template, data, and lifecycle hooks
    """
    return {
        "template": """
{% frame title="Home View" border="rounded" width=70 height=22 %}
  {% vstack spacing=1 padding=2 %}
    Welcome to the Home View!

    This view has been visited {{ state.home_visits }} time(s).
    Current user: {{ state.username }}

    {% if state.home_message %}
    {% vstack spacing=0 %}
      Message: {{ state.home_message }}
    {% endvstack %}
    {% endif %}

    View-Specific Actions:
    - Press 'h' to show a home-specific message

    {% vstack spacing=1 %}
      Navigation:
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="go_to_profile" %}Go to Profile{% endbutton %}
      {% button action="go_to_settings" %}Go to Settings{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Keyboard: [1] Home  [2] Profile  [3] Settings  [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
        "on_enter": setup_home_handlers,
        "on_exit": cleanup_home,
    }


@app.view("profile")
def profile_view():
    """Profile view with user info and navigation.

    Returns
    -------
    dict
        View configuration with template, data, and lifecycle hooks
    """
    return {
        "template": """
{% frame title="Profile View" border="rounded" width=70 height=22 %}
  {% vstack spacing=1 padding=2 %}
    User Profile: {{ state.username }}

    This view has been visited {{ state.profile_visits }} time(s).

    {% if state.profile_message %}
    {% vstack spacing=0 %}
      Message: {{ state.profile_message }}
    {% endvstack %}
    {% endif %}

    Profile Information:
    - Username: {{ state.username }}
    - Theme: {{ state.theme }}
    - Notifications: {{ 'Enabled' if state.notifications else 'Disabled' }}

    View-Specific Actions:
    - Press 'p' to show a profile-specific message

    {% vstack spacing=1 %}
      Navigation:
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="go_to_home" %}Go to Home{% endbutton %}
      {% button action="go_to_settings" %}Go to Settings{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Keyboard: [1] Home  [2] Profile  [3] Settings  [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
        "on_enter": setup_profile_handlers,
        "on_exit": cleanup_profile,
    }


@app.view("settings")
def settings_view():
    """Settings view with configuration options and navigation.

    Returns
    -------
    dict
        View configuration with template, data, and lifecycle hooks
    """
    return {
        "template": """
{% frame title="Settings View" border="rounded" width=70 height=24 %}
  {% vstack spacing=1 padding=2 %}
    Application Settings

    This view has been visited {{ state.settings_visits }} time(s).

    {% if state.settings_message %}
    {% vstack spacing=0 %}
      Message: {{ state.settings_message }}
    {% endvstack %}
    {% endif %}

    Current Settings:
    - Theme: {{ state.theme }}
    - Notifications: {{ 'Enabled' if state.notifications else 'Disabled' }}

    {% vstack spacing=0 %}
      {% checkbox id="notifications" label="Enable notifications" %}{% endcheckbox %}
    {% endvstack %}

    View-Specific Actions:
    - Press 's' to show a settings-specific message
    - Toggle the checkbox above to change notification settings

    {% vstack spacing=1 %}
      Navigation:
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="go_to_home" %}Go to Home{% endbutton %}
      {% button action="go_to_profile" %}Go to Profile{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Keyboard: [1] Home  [2] Profile  [3] Settings  [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
        "on_enter": setup_settings_handlers,
        "on_exit": cleanup_settings,
    }


def setup_home_handlers():
    """Set up view-scoped handlers for the home view.

    This function is called when entering the home view via the on_enter hook.
    View-scoped handlers registered here are automatically cleaned up when
    navigating away from this view.

    NOTE: View-scoped handlers MUST use app.on() with HandlerScope.VIEW.
    The @app.on_key() decorator creates GLOBAL handlers that work in all views.
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
    View-scoped handlers registered here are automatically cleaned up when
    navigating away from this view.
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


def setup_settings_handlers():
    """Set up view-scoped handlers for the settings view.

    This function is called when entering the settings view via the on_enter hook.
    View-scoped handlers registered here are automatically cleaned up when
    navigating away from this view.
    """
    # Increment visit counter
    app.state["settings_visits"] += 1
    # Clear any previous message
    app.state["settings_message"] = ""

    # View-scoped handler for 's' key - only works in settings view
    def on_s_key(event):
        if event.key == "s":
            app.state["settings_message"] = "Settings saved! (Press 's' triggered)"
            app.refresh()

    # Register as view-scoped handler - will be auto-cleared on navigation
    app.on(EventType.KEY, on_s_key, scope=HandlerScope.VIEW, view_name="settings")


def cleanup_settings():
    """Called when leaving the settings view.

    This is where you'd do any cleanup needed before leaving the view.
    Note: View-scoped handlers are automatically cleaned up by the framework.
    """
    pass  # Nothing to clean up manually - handlers are auto-cleaned


# Action handlers for button navigation
# These are GLOBAL handlers that work from any view
@app.on_action("go_to_home")
def handle_go_to_home(event):
    """Navigate to home view via button click.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.navigate("home")


@app.on_action("go_to_profile")
def handle_go_to_profile(event):
    """Navigate to profile view via button click.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.navigate("profile")


@app.on_action("go_to_settings")
def handle_go_to_settings(event):
    """Navigate to settings view via button click.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.navigate("settings")


# Global keyboard navigation handlers
# These handlers work from any view and use the modern decorator pattern
@app.on_key("1")
def on_key_1(event):
    """Navigate to home view via '1' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.navigate("home")


@app.on_key("2")
def on_key_2(event):
    """Navigate to profile view via '2' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.navigate("profile")


@app.on_key("3")
def on_key_3(event):
    """Navigate to settings view via '3' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.navigate("settings")


@app.on_key("q")
def on_quit(event):
    """Quit the application via 'q' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.quit()


if __name__ == "__main__":
    print("Navigation Demo")
    print("===============")
    print("This demo shows multi-view navigation with:")
    print("- View-scoped handlers (h=home msg, p=profile msg, s=settings msg)")
    print("- Lifecycle hooks (visit counters)")
    print("- State persistence (counters and settings maintained)")
    print("- Button navigation (Tab + Enter)")
    print("- Keyboard navigation (1=Home, 2=Profile, 3=Settings, q=Quit)")
    print()
    print("Key Pattern Demonstration:")
    print("- Global handlers: Use @app.on_key() decorator")
    print("- View-scoped handlers: Use app.on() in on_enter hook")
    print()
    print("Starting app...")
    print()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
