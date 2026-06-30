"""Nested Split Panel Demo - Demonstrates complex multi-pane layouts.

Run with: python examples/advanced/splitpanel_nested_demo.py

Features demonstrated:
- Nested split panels (outer horizontal, inner vertical)
- Three-pane IDE-like layout
- Both horizontal and vertical orientations
- Independent resize for each split

Press 'q' to quit.
"""

from wijjit import Wijjit, render_template_string


def main():
    """Run nested split panel demo."""
    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        """Main view with nested split panels."""
        return render_template_string(
            """
{% frame title="Nested Split Panel Demo - IDE Layout" border="double" width=fill height=fill %}
  {% splitpanel orientation="horizontal" ratio="25:75" id="outer" %}

    {# Left panel: File explorer #}
    {% frame title="Explorer" border="single" %}
      {% vstack spacing=0 %}
        + src/
          + wijjit/
            - app.py
            - renderer.py
            - state.py
          + layout/
            - engine.py
            - splitpanel.py
        + tests/
          - test_app.py
          - test_splitpanel.py
        + examples/
          - hello_world.py
          - splitpanel_demo.py
      {% endvstack %}
    {% endframe %}

    {# Right panel: Nested vertical split for editors #}
    {% splitpanel orientation="vertical" ratio="60:40" id="editors" %}

      {# Top: Main editor #}
      {% frame title="Editor: splitpanel.py" border="single" %}
        {% vstack spacing=0 %}
class SplitPanel(Container):
    # Resizable split panel container.

    def __init__(
        self,
        orientation="horizontal",
        ratio="50:50",
        resizable=True,
    ):
        super().__init__()
        self.orientation = orientation
        self.ratio = self._parse_ratio(ratio)
        self.resizable = resizable
        {% endvstack %}
      {% endframe %}

      {# Bottom: Output/terminal #}
      {% frame title="Terminal" border="single" %}
        {% vstack spacing=0 %}
$ python -m pytest tests/ -v
===== test session starts =====
tests/layout/test_splitpanel.py::test_ratio PASSED
tests/layout/test_splitpanel.py::test_collapse PASSED
===== 35 passed in 0.12s =====
$
        {% endvstack %}
      {% endframe %}

    {% endsplitpanel %}

  {% endsplitpanel %}
{% endframe %}
""",
        )

    @app.on_key("q")
    def on_quit(event):
        if event.key == "q":
            app.quit()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
