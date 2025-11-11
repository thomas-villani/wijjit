#!/usr/bin/env python3
"""Complex layout demonstration showing nested vstacks/hstacks with various sizing.

This demo showcases:
- Nested container layouts (VStack within HStack within VStack)
- Mixed sizing: fill, auto, and fixed dimensions
- Multiple element types with different sizing behaviors
- Text wrapping and positioning
- Real-world dashboard-like layout
"""

from wijjit.core.renderer import Renderer


def main():
    """Demonstrate complex nested layout with various sizing options."""

    # Create a dashboard-like layout
    template = """
{% frame title="Dashboard - Complex Layout Demo" border="double" width=120 height=40 %}
  {% vstack spacing=1 padding=1 %}

    {# Top section: Three side-by-side panels with fill height #}
    {% hstack spacing=2 height=fill %}

      {# Left panel: Markdown documentation (fills available space) #}
      {% markdown border_style="rounded" title="Documentation" %}
# Welcome to Wijjit!

This is a **markdown** viewer that automatically fills available space.

## Features
- Dynamic sizing with `width=fill` and `height=fill`
- Nested layouts with vstacks and hstacks
- Text wrapping and formatting
      {% endmarkdown %}

      {# Middle panel: VStack with mixed content #}
      {% vstack spacing=1 width=40 %}
        {% frame border="single" title="Status" %}
          System: Online
          CPU: 45%
          Memory: 2.1GB / 8GB
        {% endframe %}

        {% frame border="rounded" title="Log" height=fill %}
          {% textarea border_style="none" width=fill height=fill %}
[INFO] Application started
[INFO] Layout engine initialized
[DEBUG] Rendering complete
[INFO] All systems operational
          {% endtextarea %}
        {% endframe %}
      {% endvstack %}

      {# Right panel: Another VStack with different sizing #}
      {% vstack spacing=1 width=30 %}
        {% frame border="single" title="Quick Stats" %}
          Users: 1,234
          Active: 89
          Tasks: 42
        {% endframe %}

        {% frame border="single" title="Alerts" height=fill %}
          No new alerts
        {% endframe %}
      {% endvstack %}

    {% endhstack %}

    {# Middle section: Horizontal bar with buttons (auto height) #}
    {% hstack spacing=2 %}
      {% button %}[R] Refresh{% endbutton %}
      {% button %}[S] Settings{% endbutton %}
      {% button %}[H] Help{% endbutton %}
      {% button %}[Q] Quit{% endbutton %}
    {% endhstack %}

    {# Bottom section: Two-column layout with different widths #}
    {% hstack spacing=2 height=8 %}

      {# Left: 70% width - command output #}
      {% vstack width=80 %}
        {% frame border="single" title="Command Output" height=fill %}
          $ python app.py
          Starting application...
          Loading configuration...
          Initializing components...
          Ready!
        {% endframe %}
      {% endvstack %}

      {# Right: 30% width - quick actions #}
      {% vstack spacing=1 %}
        Actions:
        {% button %}Deploy{% endbutton %}
        {% button %}Rollback{% endbutton %}
        {% button %}Monitor{% endbutton %}
      {% endvstack %}

    {% endhstack %}

    {# Footer: Status bar (auto height, wraps naturally) #}
    Status: Ready | Mode: Development | Connection: Secure | Press [?] for help

  {% endvstack %}
{% endframe %}
"""

    try:
        # Create renderer
        renderer = Renderer()

        # Render the complex layout
        output, elements, _ = renderer.render_with_layout(
            template,
            context={},
            width=120,
            height=40
        )

        # Print element bounds for debugging
        print("=== Element Bounds ===")
        for elem in elements:
            elem_type = elem.__class__.__name__
            print(f"{elem_type:20s} {elem.bounds}")

        print("\n" + "="*120)
        print("=== Complex Layout Rendering ===")
        print("="*120 + "\n")

        # Save to file to avoid Windows encoding issues
        with open("complex_layout_output.txt", "w", encoding="utf-8") as f:
            f.write(output)
        print("Layout saved to: complex_layout_output.txt")

        # Also print a simple ASCII version of structure
        print("\nLayout Structure:")
        for line in output.split('\n')[:5]:
            try:
                print(line)
            except UnicodeEncodeError:
                print("[Box drawing characters - see file]")
                break

        # Print some insights
        print("\n" + "="*120)
        print("=== Layout Insights ===")
        print("="*120)
        print(f"Total elements rendered: {len(elements)}")
        print(f"Output size: {len(output.split(chr(10)))} lines × 120 columns")
        print("\nLayout Features Demonstrated:")
        print("  • Nested VStacks and HStacks (3 levels deep)")
        print("  • Fill sizing: Markdown and TextArea expand to fill space")
        print("  • Auto sizing: Buttons and text size to content")
        print("  • Fixed sizing: Specific width/height for panels")
        print("  • Text wrapping: Footer text wraps naturally")
        print("  • Mixed content: Frames, markdown, textarea, buttons, and text")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
