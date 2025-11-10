"""Spinner animation demo showcasing all animation styles.

This example demonstrates:
- All spinner animation styles (dots, line, bouncing, clock)
- Unicode detection with ASCII fallback
- Auto-refresh for smooth animations
- Color support
"""

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "dots_active": True,
        "line_active": True,
        "bouncing_active": True,
        "clock_active": True,
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing spinner animations."""
    return {
        "template": """
{% frame title="Spinner Animations Demo" border="double" width=70 height=30 %}
  {% vstack spacing=2 padding=1 %}
    {% vstack spacing=0 %}
      All spinner styles with automatic animations
      Press buttons to toggle spinners | Press 'q' to quit
    {% endvstack %}

    {% vstack spacing=1 %}
      Dots Spinner (Braille):
      {% spinner id="dots_active" active=state.dots_active style="dots"
                 label="Loading with dots..." color="cyan" %}
      {% endspinner %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Line Spinner (Rotating):
      {% spinner id="line_active" active=state.line_active style="line"
                 label="Processing with line..." color="green" %}
      {% endspinner %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Bouncing Spinner (Braille Bar):
      {% spinner id="bouncing_active" active=state.bouncing_active style="bouncing"
                 label="Syncing with bounce..." color="yellow" %}
      {% endspinner %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Clock Spinner (Rotating Clock):
      {% spinner id="clock_active" active=state.clock_active style="clock"
                 label="Working with clock..." color="magenta" %}
      {% endspinner %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Status: {{ "Animations active" if state.dots_active or state.line_active or state.bouncing_active or state.clock_active else "All stopped" }}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button id="toggle_dots_btn" action="toggle_dots" %}Toggle Dots{% endbutton %}
      {% button id="toggle_line_btn" action="toggle_line" %}Toggle Line{% endbutton %}
      {% button id="toggle_bouncing_btn" action="toggle_bouncing" %}Toggle Bounce{% endbutton %}
      {% button id="toggle_clock_btn" action="toggle_clock" %}Toggle Clock{% endbutton %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button id="all_on_btn" action="all_on" %}All On{% endbutton %}
      {% button id="all_off_btn" action="all_off" %}All Off{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """, # noqa: E501
        "data": {},
    }


def update_refresh_interval():
    """Update refresh interval based on active spinners."""
    if any(
        [
            app.state["dots_active"],
            app.state["line_active"],
            app.state["bouncing_active"],
            app.state["clock_active"],
        ]
    ):
        app.refresh_interval = 0.2  # 200ms for smooth animation without flicker
    else:
        app.refresh_interval = None  # Disable when no spinners active


@app.on_action("toggle_dots")
def handle_toggle_dots(event):
    """Toggle dots spinner."""
    app.state["dots_active"] = not app.state["dots_active"]
    update_refresh_interval()


@app.on_action("toggle_line")
def handle_toggle_line(event):
    """Toggle line spinner."""
    app.state["line_active"] = not app.state["line_active"]
    update_refresh_interval()


@app.on_action("toggle_bouncing")
def handle_toggle_bouncing(event):
    """Toggle bouncing spinner."""
    app.state["bouncing_active"] = not app.state["bouncing_active"]
    update_refresh_interval()


@app.on_action("toggle_clock")
def handle_toggle_clock(event):
    """Toggle clock spinner."""
    app.state["clock_active"] = not app.state["clock_active"]
    update_refresh_interval()


@app.on_action("all_on")
def handle_all_on(event):
    """Turn all spinners on."""
    app.state["dots_active"] = True
    app.state["line_active"] = True
    app.state["bouncing_active"] = True
    app.state["clock_active"] = True
    update_refresh_interval()


@app.on_action("all_off")
def handle_all_off(event):
    """Turn all spinners off."""
    app.state["dots_active"] = False
    app.state["line_active"] = False
    app.state["bouncing_active"] = False
    app.state["clock_active"] = False
    update_refresh_interval()


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    # Start with animations enabled
    app.refresh_interval = 0.2
    app.run()
