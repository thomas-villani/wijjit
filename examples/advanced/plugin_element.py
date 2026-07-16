"""Third-party element plugin - register a custom element + tag with no fork.

Demonstrates the public plugin seam: a ``SparkGauge`` leaf element and its
``{% sparkgauge %}`` template tag are registered through
``wijjit.register_element`` - exactly what a separate pip-installable package
would do at import time - and then used in an ordinary template.

Run with: python examples/advanced/plugin_element.py
Press up/down to change the value, 'q' to quit.
"""

from wijjit import Element, Wijjit, register_element, render_template_string


class SparkGauge(Element):
    """A tiny horizontal bar gauge: ``[#######   ]`` for value 70."""

    def __init__(self, id=None, value=0, width="auto", height=1):
        super().__init__(id=id)
        self.value = int(value)
        self.width_spec = width
        self.height_spec = height

    def get_intrinsic_size(self):
        return (12, 1)

    def render_to(self, ctx):
        style = ctx.style_resolver.resolve_style(self, "sparkgauge")
        filled = max(0, min(10, self.value // 10))
        bar = "#" * filled
        ctx.write_text(0, 0, f"[{bar:<10}]", style)


# Register the plugin. A real plugin package would run this at import time and
# additionally declare a ``[project.entry-points."wijjit.plugins"]`` entry so it
# auto-loads on install.
register_element("SparkGauge", SparkGauge, tag="sparkgauge")


TEMPLATE = """
{% frame title="Plugin element demo" %}
{% vstack gap=1 %}
Custom third-party element, registered via wijjit.register_element:

{% sparkgauge id="g" value=state.value %}{% endsparkgauge %}

Value: {{ state.value }}   (up/down to change, q to quit)
{% endvstack %}
{% endframe %}
"""


def main():
    """Run the plugin-element demo."""
    app = Wijjit()
    app.state["value"] = 40

    @app.view("main", default=True)
    def main_view():
        return render_template_string(TEMPLATE, value=app.state["value"])

    @app.on_key("up")
    def _up(event):
        app.state["value"] = min(100, app.state["value"] + 10)

    @app.on_key("down")
    def _down(event):
        app.state["value"] = max(0, app.state["value"] - 10)

    @app.on_key("q")
    def _quit(event):
        app.quit()

    try:
        app.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
