"""Mouse interaction demo.

This example demonstrates mouse support in Wijjit:
- Clicking buttons with the mouse
- Click counters showing interactions
- Mouse and keyboard input working together
- Tab navigation still works alongside mouse

Try:
- Click the buttons with your mouse
- Use Tab to navigate and Enter/Space to activate
- Press 'q' or click Quit to exit
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

# Create app with click counters
app = Wijjit(initial_state={
    'button1_clicks': 0,
    'button2_clicks': 0,
    'button3_clicks': 0,
    'status': 'Click buttons with mouse or keyboard (Tab + Enter/Space)',
})


@app.view("main", default=True)
def main_view():
    """Main view with clickable buttons."""
    return {
        "template": """
{% frame title="Mouse Interaction Demo" border="double" width=60 height=18 %}
  {% vstack spacing=1 padding=2 %}
    {{ state.status }}

    {% vstack spacing=1 %}
      {% hstack spacing=2 %}
        Button 1 clicks: {{ state.button1_clicks }}
      {% endhstack %}
      {% button id="btn1" action="click1" %}Click Me! (Button 1){% endbutton %}
    {% endvstack %}

    {% vstack spacing=1 %}
      {% hstack spacing=2 %}
        Button 2 clicks: {{ state.button2_clicks }}
      {% endhstack %}
      {% button id="btn2" action="click2" %}Click Me! (Button 2){% endbutton %}
    {% endvstack %}

    {% vstack spacing=1 %}
      {% hstack spacing=2 %}
        Button 3 clicks: {{ state.button3_clicks }}
      {% endhstack %}
      {% button id="btn3" action="click3" %}Click Me! (Button 3){% endbutton %}
    {% endvstack %}

    {% vstack spacing=1 %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endvstack %}

  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("click1")
def handle_click1(event):
    """Handle button 1 clicks."""
    app.state['button1_clicks'] += 1
    app.state['status'] = f"Button 1 clicked! Total: {app.state['button1_clicks']}"


@app.on_action("click2")
def handle_click2(event):
    """Handle button 2 clicks."""
    app.state['button2_clicks'] += 1
    app.state['status'] = f"Button 2 clicked! Total: {app.state['button2_clicks']}"


@app.on_action("click3")
def handle_click3(event):
    """Handle button 3 clicks."""
    app.state['button3_clicks'] += 1
    app.state['status'] = f"Button 3 clicked! Total: {app.state['button3_clicks']}"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


def handle_key(event):
    """Handle keyboard shortcuts."""
    if event.key == 'q':
        app.quit()
        event.cancel()

# Register key handler with high priority to intercept before TextArea
app.on(EventType.KEY, handle_key, scope=HandlerScope.VIEW, view_name="main", priority=100)

if __name__ == "__main__":
    app.run()
