"""HStack Flexbox Features Demo.

This example demonstrates the flexbox-style features in HStack:
- justify: Controls horizontal distribution (flex-start, flex-end, center,
           space-between, space-around, space-evenly)
- wrap: Allows children to wrap to next row when exceeding available width
- column_gap: Space between columns (alternative to spacing)
- row_gap: Space between rows when wrapping

Run with: python examples/basic/hstack_flexbox_demo.py
Press 'q' to quit
"""

from wijjit import Wijjit

app = Wijjit()


@app.view("demo", default=True)
def flexbox_demo():
    """HStack flexbox features demo view."""
    return {
        "template": """
{% frame title="HStack Flexbox Features" border_style="double" width=80 height=30 %}
  {% vstack spacing=1 %}

    {# Row 1: Justify modes - space-between, space-around, space-evenly #}
    {# NOTE: width="fill" is required for justify to work - hstack must expand to fill container #}
    {% frame title="Justify: space-between" border_style="rounded" width=76 height=3 %}
      {% hstack justify="space-between" width="fill" %}
        {% button %}Left{% endbutton %}
        {% button %}Center{% endbutton %}
        {% button %}Right{% endbutton %}
      {% endhstack %}
    {% endframe %}

    {% frame title="Justify: space-around" border_style="rounded" width=76 height=3 %}
      {% hstack justify="space-around" width="fill" %}
        {% button %}One{% endbutton %}
        {% button %}Two{% endbutton %}
        {% button %}Three{% endbutton %}
      {% endhstack %}
    {% endframe %}

    {% frame title="Justify: space-evenly" border_style="rounded" width=76 height=3 %}
      {% hstack justify="space-evenly" width="fill" %}
        {% button %}A{% endbutton %}
        {% button %}B{% endbutton %}
        {% button %}C{% endbutton %}
      {% endhstack %}
    {% endframe %}

    {# Row 2: Justify alignment modes #}
    {% hstack spacing=1 height=3 %}
      {% frame title="flex-start" border_style="single" width=24 height=3 %}
        {% hstack justify="flex-start" width="fill" column_gap=1 %}
          {% button %}1{% endbutton %}
          {% button %}2{% endbutton %}
        {% endhstack %}
      {% endframe %}

      {% frame title="center" border_style="single" width=24 height=3 %}
        {% hstack justify="center" width="fill" column_gap=1 %}
          {% button %}1{% endbutton %}
          {% button %}2{% endbutton %}
        {% endhstack %}
      {% endframe %}

      {% frame title="flex-end" border_style="single" width=24 height=3 %}
        {% hstack justify="flex-end" width="fill" column_gap=1 %}
          {% button %}1{% endbutton %}
          {% button %}2{% endbutton %}
        {% endhstack %}
      {% endframe %}
    {% endhstack %}

    {# Row 3: Wrap demonstration #}
    {% frame title="Wrap: Items wrap to next row (row_gap=1)" border_style="rounded" width=76 height=6 %}
      {% hstack wrap=True width="fill" column_gap=1 row_gap=1 %}
        {% button %}Alpha{% endbutton %}
        {% button %}Beta{% endbutton %}
        {% button %}Gamma{% endbutton %}
        {% button %}Delta{% endbutton %}
        {% button %}Epsilon{% endbutton %}
        {% button %}Zeta{% endbutton %}
        {% button %}Eta{% endbutton %}
        {% button %}Theta{% endbutton %}
        {% button %}Iota{% endbutton %}
        {% button %}Kappa{% endbutton %}
      {% endhstack %}
    {% endframe %}

    {# Row 4: Wrap with centering #}
    {% frame title="Wrap + Justify Center" border_style="rounded" width=76 height=5 %}
      {% hstack wrap=True justify="center" width="fill" gap=1 %}
        {% button %}Tag1{% endbutton %}
        {% button %}Tag2{% endbutton %}
        {% button %}Tag3{% endbutton %}
        {% button %}Tag4{% endbutton %}
        {% button %}Tag5{% endbutton %}
        {% button %}Tag6{% endbutton %}
      {% endhstack %}
    {% endframe %}

  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_key("q")
def handle_quit(event):
    """Handle quit key."""
    app.quit()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("HSTACK FLEXBOX FEATURES DEMO")
    print("=" * 70)
    print("\nThis demo shows HStack flexbox-style layout features:")
    print("  - justify: flex-start, flex-end, center, space-between,")
    print("             space-around, space-evenly")
    print("  - wrap: Wrap children to next row when exceeding width")
    print("  - column_gap: Space between columns")
    print("  - row_gap: Space between rows when wrapping")
    print("  - gap: Shorthand for both row_gap and column_gap")
    print("\nPress 'q' to exit\n")
    print("=" * 70 + "\n")

    app.run()
