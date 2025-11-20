"""Alignment and Margin Demo.

This example demonstrates the new margin and content alignment features in Wijjit.
Content alignment controls how text/elements are positioned within frames.

Run with: python examples/alignment_demo.py
Press 'q' to quit
"""

from wijjit import Wijjit

# Create app
app = Wijjit()


@app.view("demo", default=True)
def alignment_demo():
    """Alignment and margin demo view."""
    return {
        "template": """
{% frame title="Content Alignment & Margin Demo" border="double" height=20 %}
  {% vstack spacing=1 %}

    {# Row 1: Content horizontal alignment #}
    {% hstack height=5 spacing=1 %}
      {% frame title="Left" border="rounded" width=20 height=5 content_align_h="left" %}
        Left text
      {% endframe %}

      {% frame title="Center" border="rounded" width=20 height=5 content_align_h="center" %}
        Centered
      {% endframe %}

      {% frame title="Right" border="rounded" width=20 height=5 content_align_h="right" %}
        Right text
      {% endframe %}
    {% endhstack %}

    {# Row 2: Content vertical alignment #}
    {% hstack height=8 spacing=1 %}
      {% frame title="Top" border="single" width=20 height=8 content_align_v="top" %}
        At top
      {% endframe %}

      {% frame title="Middle" border="single" width=20 height=8 content_align_v="middle" %}
        In middle
      {% endframe %}

      {% frame title="Bottom" border="single" width=20 height=8 content_align_v="bottom" %}
        At bottom
      {% endframe %}
    {% endhstack %}

    {# Row 3: Margins demonstration #}
    {% hstack height=10 spacing=0 %}
      {% frame title="No Margin" border="single" width=20 height=8 margin=0 %}
        margin=0
      {% endframe %}

      {% frame title="Margin=1" border="single" width=20 height=8 margin=1 %}
        margin=1
      {% endframe %}

      {% frame title="Margin=2" border="single" width=20 height=8 margin=2 %}
        margin=2
      {% endframe %}
    {% endhstack %}

  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("quit")
def handle_quit(event):
    """Handle quit action."""
    app.quit()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("CONTENT ALIGNMENT & MARGIN DEMO")
    print("=" * 70)
    print("\nThis demo shows:")
    print("  - Content horizontal alignment (content_align_h: left/center/right)")
    print("  - Content vertical alignment (content_align_v: top/middle/bottom)")
    print("  - Margin support (uniform: margin=N)")
    print("\nPress 'q' to exit\n")
    print("=" * 70 + "\n")

    app.run()
