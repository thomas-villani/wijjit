"""Simple test to debug input handling."""

from wijjit import Wijjit

app = Wijjit(
    initial_state={
        "test": "initial",
    }
)


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% vstack width=50 height=10 %}
  Status: {{ state.test }}
  {% textinput id="test" placeholder="Type here" width=30 %}{% endtextinput %}

  Press 'q' to quit
{% endvstack %}
        """,
    }


@app.on_key("q")
def on_quit(event):
    """Handle 'q' key to quit."""
    app.quit()


if __name__ == "__main__":
    print("Starting app...")
    print(f"Focus navigation enabled: {app.focus_navigation_enabled}")
    app.run()
