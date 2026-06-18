"""Slider Demo - Interactive slider inputs.

This example demonstrates the Slider element:
- Integer slider with value display
- Float slider with decimal step
- Sliders with labels
- Keyboard and mouse control
- Value change callbacks

Run with: python examples/widgets/slider_demo.py

Controls:
- Tab/Shift+Tab: Navigate between sliders
- Left/Right Arrow: Adjust value by step
- Home/End: Jump to min/max
- Mouse drag: Drag handle to adjust
- Mouse click: Click on track to set value
- q: Quit
"""

from wijjit import Wijjit

app = Wijjit(
    initial_state={
        "volume": 50,
        "brightness": 75,
        "opacity": 0.8,
        "speed": 1.0,
        "status": "Adjust the sliders using keyboard or mouse",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view with slider demos."""
    return {
        "template": """
{% frame title="Slider Demo" border="double" width=70 height=24 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% vstack spacing=1 %}
      Integer Sliders:

      {% hstack spacing=1 %}
        Volume:
        {% slider id="volume" min=0 max=100 value=state.volume width=25 label="" %}{% endslider %}
      {% endhstack %}

      {% hstack spacing=1 %}
        Brightness:
        {% slider id="brightness" min=0 max=100 value=state.brightness width=25 %}{% endslider %}
      {% endhstack %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Float Sliders:

      {% hstack spacing=1 %}
        Opacity:
        {% slider id="opacity" min=0.0 max=1.0 step=0.1 value=state.opacity float_mode=True width=25 %}{% endslider %}
      {% endhstack %}

      {% hstack spacing=1 %}
        Speed:
        {% slider id="speed" min=0.5 max=2.0 step=0.25 value=state.speed float_mode=True width=25 %}{% endslider %}
      {% endhstack %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Current Values:
      - Volume: {{ state.volume }}%
      - Brightness: {{ state.brightness }}%
      - Opacity: {{ "%.1f"|format(state.opacity) }}
      - Speed: {{ "%.2f"|format(state.speed) }}x
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="reset" %}Reset All{% endbutton %}
      {% button action="preset_low" %}Low Preset{% endbutton %}
      {% button action="preset_high" %}High Preset{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      [Tab] Navigate | [Left/Right] Adjust | [Home/End] Min/Max | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("reset")
def handle_reset(event):
    """Reset all sliders to defaults."""
    app.state["volume"] = 50
    app.state["brightness"] = 75
    app.state["opacity"] = 0.8
    app.state["speed"] = 1.0
    app.state["status"] = "Values reset to defaults"


@app.on_action("preset_low")
def handle_preset_low(event):
    """Set all sliders to low values."""
    app.state["volume"] = 10
    app.state["brightness"] = 25
    app.state["opacity"] = 0.3
    app.state["speed"] = 0.5
    app.state["status"] = "Applied low preset"


@app.on_action("preset_high")
def handle_preset_high(event):
    """Set all sliders to high values."""
    app.state["volume"] = 90
    app.state["brightness"] = 100
    app.state["opacity"] = 1.0
    app.state["speed"] = 2.0
    app.state["status"] = "Applied high preset"


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
