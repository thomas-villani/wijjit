"""Select list demo showcasing all features.

This example demonstrates:
- Simple string options
- Value/label pairs
- Disabled options
- Long lists with scrolling
- Multiple selects with state binding
- Box-drawing borders (single, double, rounded styles)
- Border color changes when focused (BOLD + CYAN)
"""

from wijjit import Wijjit

# Create app with initial state for selects
app = Wijjit(
    initial_state={
        "color": "Blue",
        "size": "m",
        "priority": None,
        "country": None,
        "status": "Make your selections below",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing select elements."""
    return {
        "template": """
{% frame title="Select List Demo" border="single" width=100 height=32 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% vstack spacing=0 %}
      Instructions: Tab to navigate | Up/Down to browse | Enter/Space to select | Home/End for first/last
    {% endvstack %}

    {% hstack spacing=2 %}
      {% select id="color" width=30 border_style="single" title="Color" %}
        Red
        Green
        Blue
        Yellow
        Purple
      {% endselect %}

      {% select id="size" width=30 border_style="rounded" title="Size" %}
        {"value": "xs", "label": "Extra Small"}
        {"value": "s", "label": "Small"}
        {"value": "m", "label": "Medium"}
        {"value": "l", "label": "Large"}
        {"value": "xl", "label": "Extra Large"}
      {% endselect %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% select id="priority" width=30 border_style="double" title="Priority" %}
        Critical
        High
        Medium
        Low
        None (disabled)
      {% endselect %}

      {% select id="country" width=40 visible_rows=8 border_style="single" title="Country" %}
        Afghanistan
          Albania
          Algeria
          Argentina
          Australia
          Austria
          Belgium
          Brazil
          Canada
          Chile
          China
          Colombia
          Denmark
          Egypt
          Finland
          France
          Germany
          Greece
          India
          Indonesia
          Ireland
          Israel
          Italy
          Japan
          Mexico
          Netherlands
          New Zealand
          Norway
          Poland
          Portugal
          Russia
          Saudi Arabia
          Singapore
          South Africa
          South Korea
          Spain
          Sweden
          Switzerland
          Thailand
          Turkey
          United Kingdom
          United States
          Vietnam
        {% endselect %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button id="submit_btn" action="submit" %}Submit{% endbutton %}
      {% button id="reset_btn" action="reset" %}Reset{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("submit")
def handle_submit(event):
    """Handle form submission."""
    color = app.state.get("color", "")
    size = app.state.get("size", "")
    priority = app.state.get("priority", "")
    country = app.state.get("country", "")

    # Build status message
    parts = []
    if color:
        parts.append(f"Color: {color}")
    if size:
        # Map size code to label
        size_labels = {
            "xs": "Extra Small",
            "s": "Small",
            "m": "Medium",
            "l": "Large",
            "xl": "Extra Large",
        }
        parts.append(f"Size: {size_labels.get(size, size)}")
    if priority:
        parts.append(f"Priority: {priority}")
    if country:
        parts.append(f"Country: {country}")

    if parts:
        app.state["status"] = "Selected: " + ", ".join(parts)
    else:
        app.state["status"] = "No selections made"


@app.on_action("reset")
def handle_reset(event):
    """Reset all selections."""
    app.state["color"] = None
    app.state["size"] = None
    app.state["priority"] = None
    app.state["country"] = None
    app.state["status"] = "Form reset - make your selections"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    # Run the app
    # Press Tab to navigate between selects
    # Use arrow keys to browse through options
    # Press Enter or Space to select the highlighted option
    app.run()
