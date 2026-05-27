#!/usr/bin/env python3
"""Complex layout demonstration showing nested vstacks/hstacks with various sizing.

This demo showcases:
- Nested container layouts (VStack within HStack within VStack)
- Mixed sizing: fill, auto, and fixed dimensions
- Multiple element types with different sizing behaviors
- Text wrapping and positioning
- Real-world dashboard-like layout

Run with: python examples/advanced/complex_layout_demo.py
Press 'q' to quit.
"""

from wijjit import Wijjit

app = Wijjit()


@app.view("main", default=True)
def dashboard():
    """Dashboard-like view with three levels of nested layout."""
    return {
        "template": """
{% frame title="Dashboard - Complex Layout Demo" border_style="double"
         width="fill" height="fill" %}
  {% vstack spacing=1 padding=1 %}

    {# Top section: three side-by-side panels with fill height #}
    {% hstack spacing=2 width=fill height=fill %}

      {# Left panel: markdown documentation (fills available space) #}
      {% contentview content_type="markdown" border_style="rounded"
                     title="Documentation" width=fill height=fill %}
# Welcome to Wijjit!

This is a **markdown** viewer that automatically fills available space.

## Features
- Dynamic sizing with `width=fill` and `height=fill`
- Nested layouts with vstacks and hstacks
- Text wrapping and formatting
      {% endcontentview %}

      {# Middle panel: VStack with mixed content #}
      {% vstack spacing=1 width=40 %}
        {% frame border_style="single" title="Status" height=6 %}
          System: Online
          CPU: 45%
          Memory: 2.1GB / 8GB
        {% endframe %}

        {% frame border_style="rounded" title="Log" height=fill %}
          {% textarea border_style="none" width=fill height=fill %}
[INFO] Application started
[INFO] Layout engine initialized
[DEBUG] Rendering complete
[INFO] All systems operational
          {% endtextarea %}
        {% endframe %}
      {% endvstack %}

      {# Right panel: another VStack with different sizing #}
      {% vstack spacing=1 width=30 %}
        {% frame border_style="single" title="Quick Stats" height=6 %}
          Users: 1,234
          Active: 89
          Tasks: 42
        {% endframe %}

        {% frame border_style="single" title="Alerts" height=fill %}
          No new alerts
        {% endframe %}
      {% endvstack %}

    {% endhstack %}

    {# Middle section: horizontal bar with buttons (auto height) #}
    {% hstack spacing=2 %}
      {% button action="noop" %}[R] Refresh{% endbutton %}
      {% button action="noop" %}[S] Settings{% endbutton %}
      {% button action="noop" %}[H] Help{% endbutton %}
      {% button action="quit" %}[Q] Quit{% endbutton %}
    {% endhstack %}

    {# Bottom section: two-column layout with different widths #}
    {% hstack spacing=2 width=fill height=8 %}

      {# Left: wide column - command output #}
      {% vstack width=80 %}
        {% frame border_style="single" title="Command Output" height=fill %}
          $ python app.py
          Starting application...
          Loading configuration...
          Initializing components...
          Ready!
        {% endframe %}
      {% endvstack %}

      {# Right: narrow column - quick actions #}
      {% vstack spacing=1 %}
        Actions:
        {% button action="noop" %}Deploy{% endbutton %}
        {% button action="noop" %}Rollback{% endbutton %}
        {% button action="noop" %}Monitor{% endbutton %}
      {% endvstack %}

    {% endhstack %}

    {# Footer: status bar (auto height, wraps naturally) #}
    Status: Ready | Mode: Development | Connection: Secure | Press [q] to quit

  {% endvstack %}
{% endframe %}
""",
        "data": {},
    }


@app.on_action("noop")
def handle_noop(event):
    """Decorative buttons - no action in this layout demo."""


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    app.run()
