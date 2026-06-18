"""ImageView demo showcasing image rendering in the terminal.

This example demonstrates:
- Displaying images using colored half-block characters
- Braille mode for black and white rendering
- Different sizing options (fixed width/height, auto, fill)
- Aspect ratio preservation
"""

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "braille_mode": False,
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing ImageView element."""
    # Use minimal template to avoid whitespace issues
    return {
        "template": """{% frame title="ImageView Demo" border="double" width=80 height=40 %}
Renders images as ANSI colored characters in the terminal
Toggle braille mode for B&W rendering | Press 'q' to quit
{% hstack %}
{% imageview src="test-image.png" width=30 %}{% endimageview %}
{% imageview src="test-image.png" width=30 braille=True %}{% endimageview %}
{% endhstack %}
{% hstack %}
{% imageview src="test-image.png" height=8 %}{% endimageview %}
{% imageview src="test-image.png" height=8 braille=True invert=True %}{% endimageview %}
{% endhstack %}

Color mode uses half-block chars for 2x vertical resolution
Braille mode uses 2x4 pixel patterns for higher detail B&W

{% button id="quit_btn" action="quit" %}Quit (q){% endbutton %}
{% endframe %}""",
        "data": {},
    }


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


@app.on_key("q")
def handle_q(event):
    """Quit on q key."""
    app.quit()


if __name__ == "__main__":
    app.run()
