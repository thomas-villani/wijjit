"""CSS Classes Demo.

This example demonstrates CSS-style class usage for flexible, composable styling.
Shows how to use utility classes like btn-primary, text-bold, etc. to style elements.
"""

from wijjit import Wijjit

app = Wijjit()

# Initialize state with default values for dynamic styling
app.state.button_class = "btn-primary"
app.state.button_label = "Click to Toggle Style"


@app.view("main", default=True)
def main_view():
    """Main view demonstrating CSS class usage."""
    template = """
    {% frame border="single" title="CSS Classes Demo" %}
      {% vstack spacing=1 %}
        {% textinput id="title" placeholder="Demo Title" %}{% endtextinput %}

        {% text %}Button Variants:{% endtext %}

        {% hstack spacing=2 %}
          {% button action="primary" class="btn-primary" %}Primary{% endbutton %}
          {% button action="secondary" class="btn-secondary" %}Secondary{% endbutton %}
          {% button action="danger" class="btn-danger" %}Danger{% endbutton %}
          {% button action="success" class="btn-success" %}Success{% endbutton %}
        {% endhstack %}

        {% text %}Text Styling Utilities:{% endtext %}

        {% vstack spacing=0 %}
          {% text class="text-bold" %}Bold text using .text-bold class{% endtext %}
          {% text class="text-italic" %}Italic text using .text-italic class{% endtext %}
          {% text class="text-dim" %}Dimmed text using .text-dim class{% endtext %}
          {% text class="text-underline" %}Underlined text using .text-underline class{% endtext %}
        {% endvstack %}

        {% text %}Color Utilities:{% endtext %}

        {% vstack spacing=0 %}
          {% text class="text-primary" %}Primary colored text (.text-primary){% endtext %}
          {% text class="text-success" %}Success colored text (.text-success){% endtext %}
          {% text class="text-warning" %}Warning colored text (.text-warning){% endtext %}
          {% text class="text-danger" %}Danger colored text (.text-danger){% endtext %}
          {% text class="text-info" %}Info colored text (.text-info){% endtext %}
          {% text class="text-muted" %}Muted colored text (.text-muted){% endtext %}
        {% endvstack %}

        {% text %}Combined Classes:{% endtext %}

        {% text class="text-bold text-primary" %}Bold + Primary (multiple classes){% endtext %}

        {% text %}Dynamic Classes from State:{% endtext %}

        {% button action="toggle" class=state.button_class %}{{ state.button_label }}{% endbutton %}

        {% text class="text-muted" %}Press 'q' to quit{% endtext %}
      {% endvstack %}
    {% endframe %}
    """

    return {"template": template}


@app.on_action("primary")
def handle_primary(event):
    """Handle primary button click."""
    app.state.title = "Primary button clicked!"


@app.on_action("secondary")
def handle_secondary(event):
    """Handle secondary button click."""
    app.state.title = "Secondary button clicked!"


@app.on_action("danger")
def handle_danger(event):
    """Handle danger button click."""
    app.state.title = "Danger button clicked!"


@app.on_action("success")
def handle_success(event):
    """Handle success button click."""
    app.state.title = "Success button clicked!"


@app.on_action("toggle")
def toggle_style(event):
    """Toggle between button styles dynamically."""
    # Cycle through different button styles
    current = app.state.button_class
    styles = [
        "btn-primary",
        "btn-secondary",
        "btn-danger",
        "btn-success",
        "btn-warning",
    ]
    labels = [
        "Primary Style",
        "Secondary Style",
        "Danger Style",
        "Success Style",
        "Warning Style",
    ]

    try:
        current_index = styles.index(current)
        next_index = (current_index + 1) % len(styles)
    except ValueError:
        next_index = 0

    app.state.button_class = styles[next_index]
    app.state.button_label = labels[next_index]


@app.on_key("q")
def quit_app(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    app.run()
