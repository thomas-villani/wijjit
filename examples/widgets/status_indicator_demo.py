"""Status Indicator Demo - Visual status indicators.

This example demonstrates the StatusIndicator element:
- Built-in status presets (error, warning, success, info, etc.)
- Custom status definitions
- Different indicator styles (filled, hollow, square, ascii)
- Labels with status indicators
- Dynamic status updates

Run with: python examples/widgets/status_indicator_demo.py

Controls:
- Tab/Shift+Tab: Navigate between buttons
- Enter/Space: Activate button
- q: Quit
"""

from wijjit import Wijjit

app = Wijjit(
    initial_state={
        "connection": "success",
        "database": "success",
        "api": "warning",
        "cache": "error",
        "custom_status": "processing",
        "message": "System status overview",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view with status indicator demos."""
    return {
        "template": """
{% frame title="Status Indicator Demo" border="double" width=70 height=30 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.message }}
    {% endvstack %}

    {% vstack spacing=1 %}
      Built-in Status Types (filled style):

      {% hstack spacing=3 %}
        {% status status="error" label="Error" %}{% endstatus %}
        {% status status="warning" label="Warning" %}{% endstatus %}
        {% status status="success" label="Success" %}{% endstatus %}
        {% status status="info" label="Info" %}{% endstatus %}
      {% endhstack %}

      {% hstack spacing=3 %}
        {% status status="pending" label="Pending" %}{% endstatus %}
        {% status status="active" label="Active" %}{% endstatus %}
        {% status status="inactive" label="Inactive" %}{% endstatus %}
        {% status status="disabled" label="Disabled" %}{% endstatus %}
      {% endhstack %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Indicator Styles:

      {% hstack spacing=3 %}
        {% status status="success" label="Filled" indicator_style="filled" %}{% endstatus %}
        {% status status="success" label="Hollow" indicator_style="hollow" %}{% endstatus %}
        {% status status="success" label="Square" indicator_style="square" %}{% endstatus %}
        {% status status="success" label="ASCII" indicator_style="ascii" %}{% endstatus %}
      {% endhstack %}
    {% endvstack %}

    {% vstack spacing=1 %}
      System Status Dashboard:

      {% hstack spacing=2 %}
        {% status status=state.connection label="Connection" %}{% endstatus %}
        {% status status=state.database label="Database" %}{% endstatus %}
        {% status status=state.api label="API" %}{% endstatus %}
        {% status status=state.cache label="Cache" %}{% endstatus %}
      {% endhstack %}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="all_ok" %}All OK{% endbutton %}
      {% button action="some_issues" %}Some Issues{% endbutton %}
      {% button action="all_down" %}All Down{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Status Legend:
      - error (red): Critical failure
      - warning (yellow): Needs attention
      - success (green): Operating normally
      - info (blue): Informational
      - pending (cyan): In progress
      - disabled (gray): Not available
    {% endvstack %}

    {% vstack spacing=0 %}
      [Tab] Navigate | [Enter/Space] Activate | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("all_ok")
def handle_all_ok(event):
    """Set all services to success."""
    app.state["connection"] = "success"
    app.state["database"] = "success"
    app.state["api"] = "success"
    app.state["cache"] = "success"
    app.state["message"] = "All systems operational"


@app.on_action("some_issues")
def handle_some_issues(event):
    """Set some services to warning/error."""
    app.state["connection"] = "success"
    app.state["database"] = "warning"
    app.state["api"] = "error"
    app.state["cache"] = "pending"
    app.state["message"] = "Some services experiencing issues"


@app.on_action("all_down")
def handle_all_down(event):
    """Set all services to error."""
    app.state["connection"] = "error"
    app.state["database"] = "error"
    app.state["api"] = "error"
    app.state["cache"] = "error"
    app.state["message"] = "Critical: All systems down!"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


@app.on_key("q")
def on_quit(event):
    """Handle 'q' key to quit."""
    app.quit()


if __name__ == "__main__":
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
