"""Preferences Demo - Application Settings Editor.

This example demonstrates building a comprehensive preferences/settings form:
- Individual checkboxes for boolean settings
- Radio groups for single-choice options
- Multiple setting categories
- Save and reset functionality
- Template-based layout with frames

Run with: python examples/advanced/preferences_demo.py

Controls:
- Tab/Shift+Tab: Navigate between elements
- Space: Toggle checkboxes
- Arrow keys: Navigate within radio groups
- Enter: Activate buttons
- q: Quit
"""

from wijjit import Wijjit

# Create app with initial preferences state
app = Wijjit(
    initial_state={
        # Appearance settings
        "dark_mode": False,
        "show_line_numbers": True,
        "word_wrap": True,
        "theme": "blue",
        # Editor settings
        "auto_save": True,
        "auto_complete": True,
        "font_size": "medium",
        "indent_size": "4",
        # Notification settings
        "email_notifications": True,
        "desktop_notifications": False,
        "sound_alerts": True,
        # Submission tracking
        "status": "Ready - configure your preferences",
        "saved": False,
    }
)


@app.view("main", default=True)
def main_view():
    """Main preferences editor view.

    Returns
    -------
    dict
        View configuration with template
    """
    return {
        "template": """
{% frame title="Application Preferences" border="double" width=90 height=45 %}
  {% vstack spacing=1 padding=0 %}
    {{ state.status }}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=0 width=28 %}
        {% frame title="Appearance" border="single" width="fill" %}
          {% vstack spacing=1 padding=0 %}
            Theme:

            {% radiogroup id="theme" orientation="vertical" %}
              {% radio value="blue" %}Blue{% endradio %}
              {% radio value="green" %}Green{% endradio %}
              {% radio value="purple" %}Purple{% endradio %}
              {% radio value="red" %}Red{% endradio %}
            {% endradiogroup %}

            Options:

            {% checkbox id="dark_mode" label="Dark mode" %}{% endcheckbox %}
            {% checkbox id="show_line_numbers" label="Show line numbers" %}{% endcheckbox %}
            {% checkbox id="word_wrap" label="Word wrap" %}{% endcheckbox %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=28 %}
        {% frame title="Editor" border="single" width="fill" %}
          {% vstack spacing=1 padding=0 %}
            Font Size:

            {% radiogroup id="font_size" orientation="vertical" %}
              {% radio value="small" %}Small (10pt){% endradio %}
              {% radio value="medium" %}Medium (12pt){% endradio %}
              {% radio value="large" %}Large (14pt){% endradio %}
              {% radio value="xlarge" %}X-Large (16pt){% endradio %}
            {% endradiogroup %}

            Indent Size:

            {% radiogroup id="indent_size" orientation="horizontal" %}
              {% radio value="2" %}2{% endradio %}
              {% radio value="4" %}4{% endradio %}
              {% radio value="8" %}8{% endradio %}
            {% endradiogroup %}

            Features:

            {% checkbox id="auto_save" label="Auto-save files" %}{% endcheckbox %}
            {% checkbox id="auto_complete" label="Auto-complete" %}{% endcheckbox %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=28 %}
        {% frame title="Notifications" border="single" width="fill" %}
          {% vstack spacing=1 padding=0 %}
            Alert Channels:

            {% checkbox id="email_notifications" label="Email notifications" %}{% endcheckbox %}
            {% checkbox id="desktop_notifications" label="Desktop notifications" %}{% endcheckbox %}
            {% checkbox id="sound_alerts" label="Sound alerts" %}{% endcheckbox %}

            Tip: Enable at least one
            notification channel to
            stay informed about
            important events.
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% if state.saved %}
      Current Settings:
      - Theme: {{ state.theme|capitalize }} | Dark: {{ 'Yes' if state.dark_mode else 'No' }}
      - Font: {{ state.font_size|capitalize }} | Indent: {{ state.indent_size }} spaces
      - Auto-save: {{ 'On' if state.auto_save else 'Off' }} | Word wrap: {{ 'On' if state.word_wrap else 'Off' }}
      - Notifications: Email={{ 'On' if state.email_notifications else 'Off' }}, Desktop={{ 'On' if state.desktop_notifications else 'Off' }}
    {% endif %}

    {% hstack spacing=2 %}
      {% button action="save" %}Save Preferences{% endbutton %}
      {% button action="reset" %}Reset to Defaults{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    Controls: [Tab/Shift+Tab] Navigate | [Space] Toggle | [Enter] Activate | [q] Quit
  {% endvstack %}
{% endframe %}
        """,
    }


@app.on_action("save")
def handle_save(event):
    """Save current preferences.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["saved"] = True
    app.state["status"] = "Preferences saved successfully!"


@app.on_action("reset")
def handle_reset(event):
    """Reset all preferences to default values.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    # Reset appearance settings
    app.state["dark_mode"] = False
    app.state["show_line_numbers"] = True
    app.state["word_wrap"] = True
    app.state["theme"] = "blue"

    # Reset editor settings
    app.state["auto_save"] = True
    app.state["auto_complete"] = True
    app.state["font_size"] = "medium"
    app.state["indent_size"] = "4"

    # Reset notification settings
    app.state["email_notifications"] = True
    app.state["desktop_notifications"] = False
    app.state["sound_alerts"] = True

    # Update status
    app.state["saved"] = False
    app.state["status"] = "Preferences reset to defaults"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.quit()


@app.on_key("q")
def on_quit(event):
    """Handle 'q' key to quit.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.quit()


if __name__ == "__main__":
    print("Preferences Demo")
    print("=" * 50)
    print()
    print("A comprehensive settings editor demonstrating:")
    print("- Multiple setting categories (Appearance, Editor, Notifications)")
    print("- Checkboxes for boolean options")
    print("- Radio groups for single-choice selections")
    print("- Save and reset functionality")
    print("- Template-based layout with frames")
    print()
    print("Controls:")
    print("  [Tab/Shift+Tab] Navigate between elements")
    print("  [Space] Toggle checkboxes")
    print("  [Arrow keys] Navigate within radio groups")
    print("  [Enter] Activate buttons")
    print("  [q] Quit")
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
