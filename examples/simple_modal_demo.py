"""Simple modal demo to test the overlay system.

This demo shows a basic modal dialog that can be opened and closed.
Press 'o' to open the modal, ESC to close it.
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

app = Wijjit()


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% vstack %}
  {% frame border="single" title="Simple Modal Demo" %}

    Press 'o' to open modal
    Press ESC to close modal
    Press Ctrl+C to quit

    Modal status: {{ 'Open' if state.modal_open else 'Closed' }}

  {% endframe %}
{% endvstack %}
        """,
        "data": {
            "modal_open": app.state.get("modal_open", False),
        },
    }


class SimpleModalElement:
    """A simple modal element for testing."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.bounds = None
        self.focusable = False

        # Use box-drawing characters with ASCII fallback
        from wijjit.terminal.ansi import supports_unicode

        if supports_unicode():
            self.chars = {
                "tl": "╔",  # top-left
                "tr": "╗",  # top-right
                "bl": "╚",  # bottom-left
                "br": "╝",  # bottom-right
                "h": "═",  # horizontal
                "v": "║",  # vertical
            }
        else:
            self.chars = {
                "tl": "+",
                "tr": "+",
                "bl": "+",
                "br": "+",
                "h": "-",
                "v": "|",
            }

    def render(self):
        """Render the modal content."""
        border_top = (
            self.chars["tl"]
            + self.chars["h"] * (self.width - 2)
            + self.chars["tr"]
        )
        border_bottom = (
            self.chars["bl"]
            + self.chars["h"] * (self.width - 2)
            + self.chars["br"]
        )

        content_lines = []
        content_lines.append(border_top)
        content_lines.append(
            self.chars["v"] + " " * (self.width - 2) + self.chars["v"]
        )
        content_lines.append(
            self.chars["v"]
            + "Modal Dialog".center(self.width - 2)
            + self.chars["v"]
        )
        content_lines.append(
            self.chars["v"] + " " * (self.width - 2) + self.chars["v"]
        )
        content_lines.append(
            self.chars["v"]
            + "Press ESC to close".center(self.width - 2)
            + self.chars["v"]
        )
        content_lines.append(
            self.chars["v"] + " " * (self.width - 2) + self.chars["v"]
        )

        # Fill remaining height
        for _ in range(self.height - len(content_lines) - 1):
            content_lines.append(
                self.chars["v"] + " " * (self.width - 2) + self.chars["v"]
            )

        content_lines.append(border_bottom)

        return "\n".join(content_lines[: self.height])


@app.on_action("open_modal")
def open_modal(event):
    """Open a modal dialog."""
    # Create a simple modal element
    modal_element = SimpleModalElement(width=40, height=10)

    # Manually set bounds for centered position
    import shutil

    from wijjit.layout.bounds import Bounds

    term_size = shutil.get_terminal_size()
    x = (term_size.columns - 40) // 2
    y = (term_size.lines - 10) // 2

    modal_element.bounds = Bounds(x=x, y=y, width=40, height=10)

    # Show the modal
    app.state["modal_open"] = True

    def on_close():
        app.state["modal_open"] = False

    app.show_modal(modal_element, on_close=on_close, dim_background=True)



# Register key handler for 'o' key to open modal
def handle_key(event):
    if event.key == "o":
        open_modal(None)

app.on(EventType.KEY, handle_key, scope=HandlerScope.GLOBAL)


if __name__ == "__main__":
    app.state["modal_open"] = False
    app.run()
