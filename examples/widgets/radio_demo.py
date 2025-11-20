"""Radio Button Demo - Template-based radio buttons and radio groups.

This example demonstrates radio buttons using modern template-based patterns:
- Radio groups for single selection
- Multiple independent radio groups
- Automatic state synchronization
- Form submission with selected values
- Tab navigation between groups

Run with: python examples/widgets/radio_demo.py

Controls:
- Tab/Shift+Tab: Navigate between groups
- Arrow keys: Navigate within radio group
- Space/Enter: Select radio option
- q: Quit
"""

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "size": "m",  # Default selection
        "color": "Blue",  # Default selection
        "shipping": "standard",  # Default selection
        "status": "Please select your options and submit",
        "submitted": False,
    }
)


@app.view("main", default=True)
def main_view():
    """Main form view with radio groups."""
    return {
        "template": """
{% frame title="Radio Button Demo" border="double" width=80 height=32 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=25 %}
        {% frame title="Select Size" border="rounded" width="fill" %}
          {% radiogroup id="size" orientation="vertical" %}
            {% radio value="xs" %}Extra Small{% endradio %}
            {% radio value="s" %}Small{% endradio %}
            {% radio value="m" %}Medium{% endradio %}
            {% radio value="l" %}Large{% endradio %}
            {% radio value="xl" %}Extra Large{% endradio %}
          {% endradiogroup %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=25 %}
        {% frame title="Select Color" border="single" width="fill" %}
          {% radiogroup id="color" orientation="vertical" %}
            {% radio value="Red" %}Red{% endradio %}
            {% radio value="Green" %}Green{% endradio %}
            {% radio value="Blue" %}Blue{% endradio %}
            {% radio value="Yellow" %}Yellow{% endradio %}
            {% radio value="Purple" %}Purple{% endradio %}
          {% endradiogroup %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=25 %}
        {% frame title="Shipping Method" border="double" width="fill" %}
          {% radiogroup id="shipping" orientation="vertical" %}
            {% radio value="standard" %}Standard (5-7 days){% endradio %}
            {% radio value="express" %}Express (2-3 days){% endradio %}
            {% radio value="overnight" %}Overnight{% endradio %}
          {% endradiogroup %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% if state.submitted %}
      {% vstack spacing=1 %}
        Your Order:
      {% endvstack %}

      {% vstack spacing=0 padding_left=2 %}
        Size: {{ state.size_label }}
        Color: {{ state.color }}
        Shipping: {{ state.shipping_label }}
      {% endvstack %}
    {% endif %}

    {% hstack spacing=2 %}
      {% button action="submit" %}Submit Order{% endbutton %}
      {% button action="reset" %}Reset{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Controls: [Tab/Shift+Tab] Navigate groups | [Arrow keys] Navigate within group | [Space/Enter] Select | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


# Size label mapping
SIZE_LABELS = {
    "xs": "Extra Small",
    "s": "Small",
    "m": "Medium",
    "l": "Large",
    "xl": "Extra Large",
}

# Shipping label mapping
SHIPPING_LABELS = {
    "standard": "Standard (5-7 days)",
    "express": "Express (2-3 days)",
    "overnight": "Overnight",
}


@app.on_action("submit")
def handle_submit(event):
    """Handle form submission."""
    size = app.state.get("size", "m")
    color = app.state.get("color", "Blue")
    shipping = app.state.get("shipping", "standard")

    # Add human-readable labels for display
    app.state["size_label"] = SIZE_LABELS.get(size, size)
    app.state["shipping_label"] = SHIPPING_LABELS.get(shipping, shipping)

    app.state["submitted"] = True
    app.state["status"] = f"Order submitted: {SIZE_LABELS.get(size)} {color} shirt with {SHIPPING_LABELS.get(shipping).split('(')[0].strip()} shipping"


@app.on_action("reset")
def handle_reset(event):
    """Reset form to initial state."""
    app.state["size"] = "m"
    app.state["color"] = "Blue"
    app.state["shipping"] = "standard"
    app.state["submitted"] = False
    app.state["status"] = "Form reset - please select your options"


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
