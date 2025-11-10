# examples/frame_sizing_demo.py

from wijjit import Renderer


def main():
    """Run a simple template demo to test the layout system."""

    # Create renderer
    renderer = Renderer()

    # Define template with layout tags
#     template = """
# {% frame title="Template Spacing/Sizing Demo" border="double" width=100 height=60 %}
#   {% hstack spacing=1 padding=1 width=fill height=10 %}
#     {% frame %}
#         Some stuff here
#     {% endframe %}
#     {% frame %}
#         More stuff here
#     {% endframe %}
#     {% frame %}
#         Third stuff here
#     {% endframe %}
#   {% endhstack %}
# {% endframe %}"""
#
#     template_more_spacing = """
#     {% frame title="Template Demo" border="double" width=100 height=60 %}
#       {% hstack spacing=3 padding=1 width=fill height=10 %}
#         {% frame %}
#             Some stuff here
#         {% endframe %}
#         {% frame %}
#             More stuff here
#         {% endframe %}
#         {% frame %}
#             Third stuff here
#         {% endframe %}
#       {% endhstack %}
#     {% endframe %}"""
#
#     template_with_stacks = """
#     {% frame title="Template Spacing/Sizing Demo" border="double" width=100 height=60 %}
#       {% hstack spacing=5 padding=1 width=fill height=auto %}
#             {% hstack %}
#                 Some stuff here
#             {% endhstack %}
#             {% hstack %}
#                 More stuff here
#             {% endhstack %}
#             {% hstack %}
#                 Third stuff here
#             {% endhstack %}
#       {% endhstack %}
#     {% endframe %}"""


    template_markdown = """
{% frame title="Rich Content Template Demo" border="double" width=80 height=60 %}
  {% vstack spacing=1 %}
    {% hstack spacing=1 height=fill %}
      {% markdown id="docs" border_style="rounded" title="Documentation" %}
        # Markdown!
        Here's the markdown content baby!
      {% endmarkdown %}
    {% endhstack %}
    {% hstack spacing=1 %}
      {% button action="example_basic" %}[1] Basic{% endbutton %}
      {% button action="example_interactive" %}[2] Interactive{% endbutton %}
      {% button action="example_combined" %}[3] Combined{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}
    Instructions: [Tab] Switch Focus | [Arrows/PgUp/PgDn] Scroll | [1-3] Switch Example | [q] Quit
  {% endvstack %}
{% endframe %}
"""

    template_textarea = """
    {% frame title="Rich Content Template Demo" border="double" width=80 height=60 %}
      {% vstack spacing=1 padding=1 %}
        {% hstack spacing=2 height=fill %}
          {% textarea id="docs" border_style="rounded" width=fill height=fill %}
            Here's the text in the text area. Where is it?
          {% endtextarea %}

        {% endhstack %}

        {% hstack spacing=2 %}
          {% button action="example_basic" %}[1] Basic{% endbutton %}
          {% button action="example_interactive" %}[2] Interactive{% endbutton %}
          {% button action="example_combined" %}[3] Combined{% endbutton %}
          {% button action="quit" %}Quit{% endbutton %}
        {% endhstack %}

        Instructions: [Tab] Switch Focus | [Arrows/PgUp/PgDn] Scroll | [1-3] Switch Example | [q] Quit
      {% endvstack %}
    {% endframe %}
    """

    try:
        # Render with layout engine
        # output, _ = renderer.render_with_layout(
        #     template,
        #     context={},
        #     width=80,
        #     height=20
        # )
        # output_spacing, _ = renderer.render_with_layout(
        #     template_more_spacing, context={}, width=80, height=20
        # )
        # output_stacks, _ = renderer.render_with_layout(
        #     template_with_stacks,
        #     context={},
        #     width=80,
        #     height=20
        # )

        output_markdown, _ = renderer.render_with_layout(
            template_markdown,
            context={},
            width=80,
            height=20
        )

        output_textarea, _ = renderer.render_with_layout(template_textarea,
                                                          context={},
                                                          width=80,
                                                          height=20)

        # Print output
        # print("=== Template Layout Demo ===")
        # print(output)

        # print("=== Same as above with more spacing ===")
        # print(output_spacing)

        # print("=== With hstacks instead ===")
        # print(output_stacks)

        print("=== Markdown Demo ===")
        print(output_markdown)
        print("\n=== TextArea Demo ===")
        print(output_textarea)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
