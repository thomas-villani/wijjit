"""Split Panel Demo - Demonstrates basic split panel functionality.

Run with: python examples/widgets/splitpanel_demo.py

Features demonstrated:
- Horizontal split panel (side-by-side)
- Drag divider to resize (mouse)
- Collapsible first panel (drag far left to collapse, double-click to restore)
- Keyboard resize (Ctrl+Left/Right when focused)

Press 'q' to quit.
"""

from wijjit import Wijjit


def main():
    """Run split panel demo."""
    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        """Main view with split panel."""
        return {
            "template": """
{% frame title="Split Panel Demo" border_style="double" width=fill height=fill %}
  {% splitpanel orientation="horizontal" ratio="30:70" collapsible="first" id="main_split" %}
    {% frame title="Sidebar" border_style="single" %}
      {% vstack spacing=1 %}
        Navigation:

        {% button id="btn_home" action="nav_home" %}Home{% endbutton %}
        {% button id="btn_settings" action="nav_settings" %}Settings{% endbutton %}
        {% button id="btn_about" action="nav_about" %}About{% endbutton %}

        Try:
        - Tab between buttons
        - Drag divider to resize
        - Drag far left to collapse
      {% endvstack %}
    {% endframe %}

    {% frame title="Main Content" border_style="single" %}
      {% vstack spacing=1 %}
        Enter some text below:

        {% textinput id="name" placeholder="Your name..." %}{% endtextinput %}
        {% textinput id="email" placeholder="Your email..." %}{% endtextinput %}

        {% hstack spacing=2 %}
          {% button id="btn_submit" action="submit" %}Submit{% endbutton %}
          {% button id="btn_clear" action="clear" %}Clear{% endbutton %}
        {% endhstack %}

        Status: {{ status }}
      {% endvstack %}
    {% endframe %}
  {% endsplitpanel %}
{% endframe %}
""",
            "data": {
                "status": app.state.get("status", "Ready"),
            },
        }

    @app.on_action("nav_home")
    def on_nav_home(event):
        app.state["status"] = "Navigated to Home"

    @app.on_action("nav_settings")
    def on_nav_settings(event):
        app.state["status"] = "Navigated to Settings"

    @app.on_action("nav_about")
    def on_nav_about(event):
        app.state["status"] = "Navigated to About"

    @app.on_action("submit")
    def on_submit(event):
        name = app.state.get("name", "")
        email = app.state.get("email", "")
        app.state["status"] = f"Submitted: {name} <{email}>"

    @app.on_action("clear")
    def on_clear(event):
        app.state["name"] = ""
        app.state["email"] = ""
        app.state["status"] = "Cleared"

    @app.on_key("q")
    def on_quit(event):
        if event.key == "q":
            app.quit()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
