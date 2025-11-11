"""Template Demo - Demonstrates template-based UI with layout tags.

This example showcases the new declarative template API with:
- VStack and HStack layout containers
- TextInput and Button elements
- Automatic layout calculation

Run with: python examples/template_demo.py

Controls:
- Tab/Shift+Tab: Navigate between fields (not fully wired yet)
- Type in input fields
- q: Quit
"""

from wijjit.core.renderer import Renderer


def main():
    """Run a simple template demo to test the layout system."""

    # Create renderer
    renderer = Renderer()

    # Define template with layout tags
    template = """
{% frame title="Test Frame" border="single" %}
{% vstack spacing=1 padding=2 %}
    {% button id="btn1" %}Hello{% endbutton %}
    {% button id="btn2" %}World{% endbutton %}
    {% textinput id="input1" placeholder="Enter text" width=30 %}{% endtextinput %}
{% endvstack %}
{% endframe %}
"""

    try:
        # Render with layout engine
        output, elements, _ = renderer.render_with_layout(
            template,
            context={},
            width=80,
            height=20
        )

        # Print output
        print("=== Template Layout Demo ===")
        print(output)
        print("\n=== Elements with bounds ===")
        for element in elements:
            print(f"{element.id}: {element.bounds}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
