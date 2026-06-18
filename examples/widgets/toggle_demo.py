"""Toggle Demo - Toggle switch elements.

This example demonstrates the Toggle element:
- Single label mode (switch with adjacent label)
- Dual label mode (OFF/ON labels on either side)
- Custom on/off labels
- State binding and change callbacks
- Keyboard and mouse control

Run with: python examples/widgets/toggle_demo.py

Controls:
- Tab/Shift+Tab: Navigate between toggles
- Space/Enter: Toggle state
- Mouse click: Toggle state
- q: Quit
"""

from wijjit import Wijjit

app = Wijjit(
    initial_state={
        "dark_mode": False,
        "notifications": True,
        "sound": True,
        "auto_save": False,
        "theme_mode": False,
        "wifi": True,
        "bluetooth": False,
        "status": "Configure your settings",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view with toggle demos."""
    return {
        "template": """
{% frame title="Toggle Demo" border="double" width=70 height=28 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% vstack spacing=1 %}
      Single Label Mode (switch + label):

      {% toggle id="dark_mode" label="Dark Mode" %}{% endtoggle %}
      {% toggle id="notifications" label="Enable Notifications" %}{% endtoggle %}
      {% toggle id="sound" label="Sound Effects" %}{% endtoggle %}
      {% toggle id="auto_save" label="Auto-save Documents" %}{% endtoggle %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Dual Label Mode (label + switch + label):

      {% toggle id="theme_mode" label_mode="dual" off_label="Light" on_label="Dark" %}{% endtoggle %}
      {% toggle id="wifi" label_mode="dual" off_label="Off" on_label="WiFi" %}{% endtoggle %}
      {% toggle id="bluetooth" label_mode="dual" off_label="Off" on_label="Bluetooth" %}{% endtoggle %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Current Settings:
      - Dark Mode: {{ 'ON' if state.dark_mode else 'OFF' }}
      - Notifications: {{ 'ON' if state.notifications else 'OFF' }}
      - Sound: {{ 'ON' if state.sound else 'OFF' }}
      - Auto-save: {{ 'ON' if state.auto_save else 'OFF' }}
      - Theme: {{ 'Dark' if state.theme_mode else 'Light' }}
      - WiFi: {{ 'ON' if state.wifi else 'OFF' }}
      - Bluetooth: {{ 'ON' if state.bluetooth else 'OFF' }}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="all_on" %}All On{% endbutton %}
      {% button action="all_off" %}All Off{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      [Tab] Navigate | [Space/Enter] Toggle | [Click] Toggle | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("all_on")
def handle_all_on(event):
    """Turn all toggles on."""
    app.state["dark_mode"] = True
    app.state["notifications"] = True
    app.state["sound"] = True
    app.state["auto_save"] = True
    app.state["theme_mode"] = True
    app.state["wifi"] = True
    app.state["bluetooth"] = True
    app.state["status"] = "All settings enabled"


@app.on_action("all_off")
def handle_all_off(event):
    """Turn all toggles off."""
    app.state["dark_mode"] = False
    app.state["notifications"] = False
    app.state["sound"] = False
    app.state["auto_save"] = False
    app.state["theme_mode"] = False
    app.state["wifi"] = False
    app.state["bluetooth"] = False
    app.state["status"] = "All settings disabled"


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
