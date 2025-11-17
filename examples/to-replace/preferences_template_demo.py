"""User Preferences Template Demo - Demonstrates Template-Based Checkbox and Radio Elements.

This example shows how to build a preferences form using Wijjit's declarative
Jinja2 template syntax with the new checkbox and radio button tags.

Features demonstrated:
- {% checkbox %} tags with state binding
- {% radiogroup %} tags with borders and titles
- {% checkboxgroup %} tags for multi-select
- Layout with {% frame %} and {% vstack %}
- Template-based form construction
- Automatic state management

Run with: python examples/preferences_template_demo.py

Controls:
- Tab/Shift+Tab: Navigate between elements
- Space/Enter: Toggle checkboxes, select radio options
- Arrow keys: Navigate within groups
- q: Quit
"""

from wijjit import Wijjit


def create_app():
    """Create and configure the preferences template demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    app = Wijjit(
        template_dir=None,  # Using inline templates
        initial_state={
            # Individual checkbox states
            "dark_mode": False,
            "auto_save": True,
            "show_line_numbers": True,
            # Radio group states (stores selected value)
            "theme": "blue",
            "font_size": "medium",
            # Checkbox group state (stores list of selected values)
            "notifications": ["email", "desktop"],
            # Submission tracking
            "submitted": False,
        },
    )

    @app.view("main", default=True)
    def main_view():
        """Main preferences view using template syntax."""
        # Template defines the entire UI declaratively
        template = """
{% vstack spacing=1 padding=1 %}
    {% frame title="User Preferences" border="double" width=78 height=20 %}
        {% vstack spacing=1 %}

            {% hstack spacing=1 height="auto" %}
                {% frame title="Appearance" border="single" width=24 height=12 %}
                    {% vstack spacing=0 padding=0 %}
                        {% radiogroup name="theme"
                                      options=["Red", "Green", "Blue", "Purple"]
                                      width=18
                                      border_style="rounded"
                                      title="Theme" %}
                        {% endradiogroup %}
                        {% checkbox id="dark_mode" label="Dark mode" %}{% endcheckbox %}
                        {% checkbox id="show_line_numbers" label="Line nums" %}{% endcheckbox %}
                    {% endvstack %}
                {% endframe %}

                {% frame title="Editor" border="single" width=24 height=11 %}
                    {% radiogroup name="font_size"
                                  options=["Small", "Medium", "Large", "X-Large"]
                                  width=18
                                  border_style="rounded"
                                  title="Font Size" %}
                    {% endradiogroup %}
                    {% checkbox id="auto_save" label="Auto-save" %}{% endcheckbox %}
                {% endframe %}

                {% frame title="Notifications" border="single" width=24 height=10 %}
                    {% checkboxgroup id="notifications"
                                     options=[
                                         {"value": "email", "label": "Email"},
                                         {"value": "desktop", "label": "Desktop"},
                                         {"value": "sound", "label": "Sound"},
                                         {"value": "mobile", "label": "Mobile"}
                                     ]
                                     width=18
                                     border_style="single"
                                     title="Enable" %}
                    {% endcheckboxgroup %}
                {% endframe %}
            {% endhstack %}

            {% hstack spacing=2 align_h="center" %}
                {% button id="save_btn" action="save" %}Save Preferences{% endbutton %}
                {% button id="reset_btn" action="reset" %}Reset to Defaults{% endbutton %}
            {% endhstack %}

        {% endvstack %}
    {% endframe %}

    {% if state.submitted %}
        {% frame title="Saved" border="single" width=78 %}
            {% vstack padding=1 %}
            Dark: {{ "On" if state.dark_mode else "Off" }} | Lines: {{ "On" if state.show_line_numbers else "Off" }} | Auto-save: {{ "On" if state.auto_save else "Off" }} | Theme: {{ state.theme|title }} | Font: {{ state.font_size|title }}
            Notifications: {{ ", ".join(state.notifications)|title if state.notifications else "None" }}
            {% endvstack %}
        {% endframe %}
    {% endif %}

    Controls: [Tab] Navigate  [Space/Enter] Toggle/Select  [q] Quit

{% endvstack %}
"""  # noqa: E501

        return {
            "template": template,
            "data": {"state": app.state},
        }

    @app.on_action("save")
    def save_action(event):
        app.state["submitted"] = True
        app.refresh()

    @app.on_action("reset")
    def reset_action(event):
        app.state["dark_mode"] = False
        app.state["auto_save"] = True
        app.state["show_line_numbers"] = True
        app.state["theme"] = "blue"
        app.state["font_size"] = "medium"
        app.state["notifications"] = ["email", "desktop"]
        app.state["submitted"] = False
        app.refresh()

    @app.on_key("q")
    def quit_action(event):
        app.quit()

    return app


def main():
    """Run the preferences template demo application."""
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
