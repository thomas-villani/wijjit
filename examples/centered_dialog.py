"""Centered Dialog Demo.

A practical example showing how to create a centered dialog box using
the new alignment features. This is a common UI pattern for alerts,
prompts, and modal dialogs.

Run with: python examples/centered_dialog.py
Press 'q' to quit
"""

from wijjit import Wijjit

# Create app
app = Wijjit()


@app.view("dialog", default=True)
def dialog_view():
    """View showing a centered dialog."""
    return {
        "template": """
{% frame title="Desktop" border="double" height=24 %}
  {# Outer frame acts as the "desktop" background #}
  {# The VStack's alignment controls how its child (the dialog) is positioned #}
  {% vstack align_h="center" align_v="middle" %}

    {# Centered dialog box with centered content #}
    {% frame title="Welcome!"
             border="rounded"
             width=50
             height=12
             margin=2
             content_align_h="center"
             content_align_v="middle" %}

      {% vstack spacing=1 %}
        Welcome to Wijjit!

        This dialog is centered both horizontally
        and vertically within its parent.

        It also has margins for spacing and
        the content is center-aligned.

        Press 'q' to quit
      {% endvstack %}

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
    print("CENTERED DIALOG DEMO")
    print("=" * 70)
    print("\nThis example demonstrates creating a centered dialog box using:")
    print("  - Parent VStack with align_h='center' + align_v='middle'")
    print("    to position the dialog frame")
    print("  - Frame's content_align_h='center' + content_align_v='middle'")
    print("    to center text within the dialog")
    print("  - margin=2 for spacing around the dialog")
    print("\nThis is a common pattern for alerts, prompts, and modal dialogs.")
    print("\nPress 'q' to exit\n")
    print("=" * 70 + "\n")

    app.run()
