"""Grid Layout Demo.

This example demonstrates the new Grid layout element in Wijjit.
Grid provides CSS Grid-like 2D layout with auto-sizing columns and rows.

Run with: python examples/basic/grid_demo.py
Press 'q' to quit
"""

from wijjit import Wijjit

# Create app
app = Wijjit()


@app.view("demo", default=True)
def grid_demo():
    """Grid layout demo view."""
    return {
        "template": """
{% frame title="Grid Layout Demo" border="double" height="fill" %}
  {% vstack spacing=1 %}

    {# Basic 2x2 Grid #}
    {% frame title="Basic 2x2 Grid" border="rounded" height=8 %}
      {% grid rows=2 cols=2 row_gap=0 col_gap=1 %}
        {% frame border="single" width=15 height=3 %}Cell 1{% endframe %}
        {% frame border="single" width=15 height=3 %}Cell 2{% endframe %}
        {% frame border="single" width=15 height=3 %}Cell 3{% endframe %}
        {% frame border="single" width=15 height=3 %}Cell 4{% endframe %}
      {% endgrid %}
    {% endframe %}

    {# Grid with Gaps #}
    {% frame title="Grid with Gaps (row_gap=1, col_gap=2)" border="rounded" height=9 %}
      {% grid rows=2 cols=3 row_gap=1 col_gap=2 %}
        {% frame border="single" width=12 height=3 %}A{% endframe %}
        {% frame border="single" width=12 height=3 %}B{% endframe %}
        {% frame border="single" width=12 height=3 %}C{% endframe %}
        {% frame border="single" width=12 height=3 %}D{% endframe %}
        {% frame border="single" width=12 height=3 %}E{% endframe %}
        {% frame border="single" width=12 height=3 %}F{% endframe %}
      {% endgrid %}
    {% endframe %}

    {# Grid with Colspan #}
    {% frame title="Grid with Colspan" border="rounded" height=8 %}
      {% grid rows=2 cols=3 col_gap=1 %}
        {% colspan cols=2 %}
          {% frame border="double" width=25 height=3 %}Wide (colspan=2){% endframe %}
        {% endcolspan %}
        {% frame border="single" width=12 height=3 %}Normal{% endframe %}
        {% frame border="single" width=12 height=3 %}A{% endframe %}
        {% frame border="single" width=12 height=3 %}B{% endframe %}
        {% frame border="single" width=12 height=3 %}C{% endframe %}
      {% endgrid %}
    {% endframe %}

    {# Grid with Rowspan #}
    {% frame title="Grid with Rowspan" border="rounded" height=8 %}
      {% grid rows=2 cols=2 col_gap=1 %}
        {% rowspan rows=2 %}
          {% frame border="double" width=15 height=6 %}Tall (rowspan=2){% endframe %}
        {% endrowspan %}
        {% frame border="single" width=15 height=3 %}Top{% endframe %}
        {% frame border="single" width=15 height=3 %}Bottom{% endframe %}
      {% endgrid %}
    {% endframe %}

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
    print("GRID LAYOUT DEMO")
    print("=" * 70)
    print("\nThis demo shows:")
    print("  - Basic 2x2 grid layout")
    print("  - Grid with row_gap and col_gap spacing")
    print("  - Grid with colspan (cells spanning multiple columns)")
    print("  - Grid with rowspan (cells spanning multiple rows)")
    print("\nPress 'q' to exit\n")
    print("=" * 70 + "\n")

    app.run()
