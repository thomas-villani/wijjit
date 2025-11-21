"""CSS Theme Demo.

This example demonstrates how to load a custom theme from a CSS file.
Shows how CSS files can define styles for Wijjit applications.
"""

import os

from wijjit import Wijjit
from wijjit.styling.theme import Theme

app = Wijjit()

# Load custom theme from CSS file
css_path = os.path.join(os.path.dirname(__file__), "custom_theme.css")
custom_theme = Theme.from_css(css_path, "custom")

# Register and activate the custom theme
app.renderer.theme_manager.register_theme(custom_theme)
app.renderer.theme_manager.set_theme("custom")


@app.view("main", default=True)
def main_view():
    """Main view demonstrating CSS theme."""
    template = """
    {% frame border="single" title="CSS Theme Demo - Styles from custom_theme.css" %}
      {% vstack spacing=1 %}
        {% text class="text-bold" %}This theme was loaded from a CSS file!{% endtext %}

        {% text %}Button Variants (from CSS):{% endtext %}

        {% hstack spacing=2 %}
          {% button action="primary" class="btn-primary" %}Primary{% endbutton %}
          {% button action="danger" class="btn-danger" %}Danger{% endbutton %}
          {% button action="success" class="btn-success" %}Success{% endbutton %}
          {% button action="warning" class="btn-warning" %}Warning{% endbutton %}
        {% endhstack %}

        {% text %}Text Utilities (from CSS):{% endtext %}

        {% vstack spacing=0 %}
          {% text class="text-bold" %}Bold text (.text-bold){% endtext %}
          {% text class="text-italic" %}Italic text (.text-italic){% endtext %}
          {% text class="text-underline" %}Underlined text (.text-underline){% endtext %}
          {% text class="text-dim" %}Dimmed text (.text-dim){% endtext %}
        {% endvstack %}

        {% text %}Color Utilities (from CSS):{% endtext %}

        {% vstack spacing=0 %}
          {% text class="text-primary" %}Primary color (.text-primary){% endtext %}
          {% text class="text-success" %}Success color (.text-success){% endtext %}
          {% text class="text-danger" %}Danger color (.text-danger){% endtext %}
          {% text class="text-warning" %}Warning color (.text-warning){% endtext %}
          {% text class="text-info" %}Info color (.text-info){% endtext %}
          {% text class="text-muted" %}Muted color (.text-muted){% endtext %}
        {% endvstack %}

        {% text %}Custom Classes (from CSS):{% endtext %}

        {% vstack spacing=0 %}
          {% text class="highlight-box" %}Highlighted box with custom styling{% endtext %}
          {% text class="error-text" %}Error message with custom styling{% endtext %}
          {% text class="success-text" %}Success message with custom styling{% endtext %}
        {% endvstack %}

        {% text %}Base Element Styling (from CSS):{% endtext %}

        {% vstack spacing=0 %}
          {% text %}These buttons get their style from the 'button' CSS rule:{% endtext %}
          {% hstack spacing=2 %}
            {% button action="test1" %}Button 1{% endbutton %}
            {% button action="test2" %}Button 2{% endbutton %}
          {% endhstack %}
        {% endvstack %}

        {% text class="text-muted" %}Press 'q' to quit{% endtext %}
      {% endvstack %}
    {% endframe %}
    """

    return {"template": template}


@app.on_action("primary")
def handle_primary(event):
    """Handle primary button click."""
    print("Primary button clicked!")


@app.on_action("danger")
def handle_danger(event):
    """Handle danger button click."""
    print("Danger button clicked!")


@app.on_action("success")
def handle_success(event):
    """Handle success button click."""
    print("Success button clicked!")


@app.on_action("warning")
def handle_warning(event):
    """Handle warning button click."""
    print("Warning button clicked!")


@app.on_key("q")
def quit_app(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    print("Loading theme from custom_theme.css...")
    print(f"Theme name: {custom_theme.name}")
    print(f"Number of styles loaded: {len(custom_theme.styles)}")
    print()
    app.run()
