"""Demo of inline rendering for CLI applications.

This example shows how to use render_inline() to output styled content
to the terminal scrollback without using alternate screen mode.

Run with: python examples/basic/inline_demo.py
"""

from wijjit import render_inline


def demo_simple_frame():
    """Render a simple frame with text."""
    print("=== Simple Frame ===")
    print()

    render_inline(
        """
{% frame title="System Status" border="rounded" %}
  {% vstack %}
    Hostname: {{ hostname }}
    Uptime: {{ uptime }}
    Load: {{ load }}
  {% endvstack %}
{% endframe %}
""",
        hostname="server-01",
        uptime="5 days, 3 hours",
        load="0.42",
    )

    print()


def demo_table():
    """Render a table inline."""
    print("=== Table Output ===")
    print()

    data = [
        {"name": "Alice", "role": "Developer", "status": "Active"},
        {"name": "Bob", "role": "Designer", "status": "Away"},
        {"name": "Carol", "role": "Manager", "status": "Active"},
    ]

    render_inline(
        """
{% frame title="Team Members" %}
  {% table data=members columns=cols %}{% endtable %}
{% endframe %}
""",
        members=data,
        cols=[
            {"key": "name", "label": "Name"},
            {"key": "role", "label": "Role"},
            {"key": "status", "label": "Status"},
        ],
    )

    print()


def demo_nested_layout():
    """Render nested layout inline."""
    print("=== Nested Layout ===")
    print()

    render_inline(
        """
{% frame title="Dashboard" border="double" %}
  {% hstack spacing=2 %}
    {% frame title="CPU" width=20 %}
      {% vstack %}
        Usage: {{ cpu }}%
        Temp: {{ temp }}C
      {% endvstack %}
    {% endframe %}
    {% frame title="Memory" width=20 %}
      {% vstack %}
        Used: {{ mem_used }} GB
        Free: {{ mem_free }} GB
      {% endvstack %}
    {% endframe %}
  {% endhstack %}
{% endframe %}
""",
        cpu=45,
        temp=62,
        mem_used=8.2,
        mem_free=7.8,
    )

    print()


def demo_return_string():
    """Demonstrate returning string instead of printing."""
    print("=== Return String Mode ===")
    print()

    output = render_inline(
        """
{% frame title="Captured" %}
  This was captured, not printed directly.
{% endframe %}
""",
        print_output=False,
    )

    print(f"Captured {len(output)} characters of ANSI output")
    print("Now printing it:")
    print(output)

    print()


def demo_fixed_width():
    """Demonstrate fixed width rendering."""
    print("=== Fixed Width (40 columns) ===")
    print()

    render_inline(
        """
{% frame title="Narrow Frame" %}
  This content is rendered at a fixed width of 40 columns, regardless of terminal size.
{% endframe %}
""",
        width=40,
    )

    print()


def main():
    """Run all inline rendering demos."""
    print()
    print("=" * 60)
    print("  Wijjit Inline Rendering Demo")
    print("  Output becomes part of terminal scrollback")
    print("=" * 60)
    print()

    demo_simple_frame()
    demo_table()
    demo_nested_layout()
    demo_return_string()
    demo_fixed_width()

    print("=" * 60)
    print("  Demo complete! Scroll up to see all output.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
