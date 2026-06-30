"""Centered Dialog Demo.

A practical example showing how to create a centered dialog box using
the alignment features. This is a common UI pattern for alerts,
prompts, and modal dialogs.

Run with: python examples/widgets/centered_dialog.py

Controls:
    q - Quit
    Ctrl+Q - Quit
"""

import shutil

from wijjit import Wijjit, render_template_string

# Create app
app = Wijjit()


@app.view("dialog", default=True)
def dialog_view():
    """View showing a centered dialog."""
    # Get terminal size for responsive height
    term_size = shutil.get_terminal_size()
    # Use terminal height minus a small buffer for safety
    frame_height = max(term_size.lines - 2, 16)

    return render_template_string(
        """
{% frame title="Desktop" border="double" height=frame_height %}
  {% vstack align_h="center" align_v="middle" %}

    {% frame title="Welcome!"
             border="rounded"
             width=50
             height=10
             content_align_h="center"
             content_align_v="middle" %}

        Welcome to Wijjit!

        This dialog is centered both
        horizontally and vertically.

        Press 'q' to quit

    {% endframe %}

  {% endvstack %}
{% endframe %}
        """,
        frame_height=frame_height,
    )


@app.on_key("q")
def handle_quit_key(event):
    """Handle 'q' key to quit."""
    app.quit()


if __name__ == "__main__":
    app.run()
