"""Horizontal scrolling demonstration.

This example demonstrates horizontal scrolling support in Wijjit:

1. Frame with overflow_x="scroll" - Always shows horizontal scrollbar
2. Frame with overflow_x="auto" - Shows scrollbar only when content exceeds width
3. TextArea with show_scrollbar_x=True - Horizontal scrolling for long lines

Controls:
- Left/Right arrows: Scroll horizontally (when frame is focused)
- Up/Down arrows: Scroll vertically
- Shift+Left/Right: Page scroll horizontally
- Mouse wheel: Vertical scroll
- Shift+Mouse wheel: Horizontal scroll
- Tab: Switch between elements
- 'q' to quit
"""

from wijjit import Wijjit, render_template_string

app = Wijjit(log_level="DEBUG", log_file="horizontal-scroll-demo.log")


@app.view("main", default=True)
def main_view():
    """Main view demonstrating horizontal scrolling."""
    # Generate long content lines for demonstration
    long_lines = []
    for i in range(1, 21):
        # Create lines of varying lengths
        base = f"Line {i:2d}: "
        content = "=" * (40 + i * 5)  # Lines get progressively longer
        long_lines.append(base + content + f" [end of line {i}]")

    long_content = "\n".join(long_lines)

    # Short content that fits
    short_content = "This content\nfits within\nthe frame width."

    # Very long single line for textarea
    long_text = (
        "This is a very long line of text that demonstrates horizontal scrolling "
        "in a TextArea element. When the content exceeds the visible width, you can "
        "scroll horizontally using Shift+scroll wheel or by moving the cursor beyond "
        "the visible area. The scrollbar appears at the bottom to indicate scroll position."
    )

    return render_template_string(
        """
{% frame width="fill" height="fill" border="single" title="Horizontal Scrolling Demo" %}

    {# Frame with overflow_x="scroll" - Always shows horizontal scrollbar #}
    {% frame width="fill" height=8 border="rounded" title="overflow_x='scroll' (always show h-scrollbar)"
             scrollable=true show_scrollbar=true
             overflow_x="scroll" show_scrollbar_x=true padding=(0,1,0,1) id="scroll_frame" %}
{{ long_content }}
    {% endframe %}

    {# Frame with overflow_x="auto" - Shows scrollbar only when needed #}
    {% hstack spacing=2 %}
      {% frame width="50%" height=6 border="single" title="overflow_x='auto' (needs scroll)"
               scrollable=true show_scrollbar=true
               overflow_x="auto" show_scrollbar_x=true padding=(0,1,0,1) id="auto_frame_long" %}
{{ long_content }}
      {% endframe %}

      {% frame width="50%" height=6 border="single" title="overflow_x='auto' (fits)"
               scrollable=true show_scrollbar=true
               overflow_x="auto" show_scrollbar_x=true padding=(0,1,0,1) id="auto_frame_short" %}
{{ short_content }}
      {% endframe %}
    {% endhstack %}

    {# TextArea with horizontal scrolling #}
    {% frame width="fill" border="single" title="TextArea with Horizontal Scroll" padding=(0,1,0,1) %}
      {% textarea id="text_area" width="fill" height=4 wrap_mode="none"
                  show_scrollbar=true show_scrollbar_x=true value=long_text %}
      {% endtextarea %}
    {% endframe %}

    {# Instructions #}
    {% frame width="fill" height=5 border="single" title="Controls" padding=(0,1,0,1) %}
Left/Right: Scroll horizontally | Shift+Left/Right: Page scroll
Up/Down: Scroll vertically | Shift+Wheel: Horizontal scroll
Tab: Switch focus | q: Quit
    {% endframe %}

{% endframe %}
""",
        long_content=long_content,
        short_content=short_content,
        long_text=long_text,
    )


@app.on_key("q")
def quit_app(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    app.run()
