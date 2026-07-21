"""ImageView demo showcasing image rendering in the terminal.

This example demonstrates:
- The three render modes: color (half-block), quadrant, and braille
- Setting an explicit braille threshold instead of automatic Otsu
- Different sizing options (fixed width/height, auto, fill)
- Aspect ratio preservation
"""

from pathlib import Path

from wijjit import Wijjit, render_template_string

# Resolve the bundled sample image relative to this file so the demo works
# regardless of the current working directory.
IMAGE_PATH = str(Path(__file__).parent.parent / "assets" / "test-image.png")

app = Wijjit()

TEMPLATE = """{% frame title="ImageView Demo" border="double" width=80 height=40 %}
Renders images as ANSI colored characters in the terminal | Press 'q' to quit
{% hstack %}
{% imageview src=image width=24 %}{% endimageview %}
{% imageview src=image width=24 mode="quadrant" %}{% endimageview %}
{% imageview src=image width=24 mode="braille" %}{% endimageview %}
{% endhstack %}
     color                   quadrant                braille
{% hstack %}
{% imageview src=image height=8 mode="braille" threshold=60 %}{% endimageview %}
{% imageview src=image height=8 mode="braille" threshold=160 %}{% endimageview %}
{% imageview src=image height=8 mode="braille" invert=True %}{% endimageview %}
{% endhstack %}
  threshold=60            threshold=160           inverted (auto)

Color mode uses half-blocks: 1x2 subpixels, full color
Quadrant mode uses 2x2 subpixels, still full color and full cell coverage
Braille mode uses 2x4 subpixels but is monochrome; threshold defaults to Otsu

{% button id="quit_btn" action="quit" %}Quit (q){% endbutton %}
{% endframe %}"""


@app.view("main", default=True)
def main_view():
    """Main view showcasing ImageView element."""
    return render_template_string(TEMPLATE, image=IMAGE_PATH)


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
