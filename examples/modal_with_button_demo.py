"""Advanced modal demo with interactive button.

This demo shows a modal dialog with a button inside that can be focused
and clicked. Demonstrates focus trapping within the modal.

Press 'o' to open modal
Press Tab to focus button
Press Enter or click button to confirm
Press ESC to cancel/close modal
"""

import shutil

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.elements.input.button import Button
from wijjit.layout.bounds import Bounds
from wijjit.terminal.ansi import ANSIStyle, supports_unicode

app = Wijjit()


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% vstack %}
  {% frame border="single" title="Modal with Button Demo" %}

    Press 'o' to open confirmation modal
    Press ESC to cancel modal
    Press Ctrl+C to quit

    Status: {{ state.status }}
    Button clicks: {{ state.click_count }}

  {% endframe %}
{% endvstack %}
        """,
        "data": {
            "status": app.state.get("status", "Ready"),
            "click_count": app.state.get("click_count", 0),
        },
    }


class ModalWithButton:
    """A modal dialog with an interactive button."""

    def __init__(self, width, height, message, on_confirm=None):
        self.width = width
        self.height = height
        self.message = message
        self.on_confirm = on_confirm
        self.bounds = None
        self.focusable = False

        # Create button as a child element
        self.button = Button(
            label="Confirm",
            id="modal_button",
            on_click=self._handle_button_click,
        )
        self.button.focusable = True

        # Position button in center of modal
        button_width = len("Confirm") + 4  # Label + padding
        button_x = (width - button_width) // 2
        button_y = height - 3
        self.button.bounds = Bounds(x=0, y=0, width=button_width, height=1)
        self.button_relative_x = button_x
        self.button_relative_y = button_y

        # Use box-drawing characters with ASCII fallback
        if supports_unicode():
            self.chars = {
                "tl": "╔",
                "tr": "╗",
                "bl": "╚",
                "br": "╝",
                "h": "═",
                "v": "║",
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

        # Store children for focus manager
        self.children = [self.button]

    def _handle_button_click(self):
        """Handle button click.

        Note: Button.on_click currently doesn't pass any arguments,
        so this callback takes no parameters.
        """
        if self.on_confirm:
            self.on_confirm()

    def handle_key(self, key):
        """Handle key events - route to button if focused."""
        if self.button.focused:
            return self.button.handle_key(key)
        return False

    def handle_mouse(self, event):
        """Handle mouse events - route to button if in bounds."""
        if not self.bounds or not self.button.bounds:
            return False

        # Convert absolute position to relative position within modal
        relative_x = event.x - self.bounds.x
        relative_y = event.y - self.bounds.y

        # Check if click is on button
        if (
            self.button_relative_x
            <= relative_x
            < self.button_relative_x + self.button.bounds.width
            and self.button_relative_y
            <= relative_y
            < self.button_relative_y + self.button.bounds.height
        ):
            # Create event with adjusted coordinates for button
            from wijjit.terminal.mouse import MouseEvent as TerminalMouseEvent

            button_event = TerminalMouseEvent(
                type=event.type,
                x=relative_x - self.button_relative_x,
                y=relative_y - self.button_relative_y,
                button=event.button,
            )
            return self.button.handle_mouse(button_event)

        return False

    def render(self):
        """Render the modal content with button."""
        from wijjit.terminal.ansi import visible_length

        border_top = (
            self.chars["tl"] + self.chars["h"] * (self.width - 2) + self.chars["tr"]
        )
        border_bottom = (
            self.chars["bl"] + self.chars["h"] * (self.width - 2) + self.chars["br"]
        )

        content_lines = []

        # Top border
        content_lines.append(border_top)

        # Empty line
        content_lines.append(self.chars["v"] + " " * (self.width - 2) + self.chars["v"])

        # Title (ANSI-aware centering)
        title_plain = "Confirm Action"
        title_styled = f"{ANSIStyle.BOLD}{title_plain}{ANSIStyle.RESET}"
        title_visible_len = len(title_plain)  # Visible length without ANSI codes
        padding_needed = self.width - 2 - title_visible_len
        left_pad = padding_needed // 2
        right_pad = padding_needed - left_pad

        content_lines.append(
            self.chars["v"]
            + " " * left_pad
            + title_styled
            + " " * right_pad
            + self.chars["v"]
        )

        # Empty line
        content_lines.append(self.chars["v"] + " " * (self.width - 2) + self.chars["v"])

        # Message (wrapped if needed)
        message_lines = self._wrap_message(self.message, self.width - 4)
        for msg_line in message_lines:
            content_lines.append(
                self.chars["v"] + " " + msg_line.ljust(self.width - 3) + self.chars["v"]
            )

        # Fill space before button
        while len(content_lines) < self.button_relative_y:
            content_lines.append(
                self.chars["v"] + " " * (self.width - 2) + self.chars["v"]
            )

        # Render button line (ANSI-aware width calculation)
        button_content = self.button.render()
        button_visible_len = visible_length(button_content)
        button_line = (
            self.chars["v"]
            + " " * self.button_relative_x
            + button_content
            + " " * (self.width - 2 - self.button_relative_x - button_visible_len)
            + self.chars["v"]
        )
        content_lines.append(button_line)

        # Fill remaining height
        while len(content_lines) < self.height - 1:
            content_lines.append(
                self.chars["v"] + " " * (self.width - 2) + self.chars["v"]
            )

        # Bottom border
        content_lines.append(border_bottom)

        return "\n".join(content_lines[: self.height])

    def _wrap_message(self, message, max_width):
        """Wrap message to fit within modal width."""
        words = message.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)
            if current_length + word_length + len(current_line) <= max_width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [""]


@app.on_action("open_modal")
def open_modal(event):
    """Open a modal dialog with a button."""
    term_size = shutil.get_terminal_size()

    def on_confirm():
        """Handle confirmation."""
        app.state["status"] = "Confirmed!"
        app.state["click_count"] = app.state.get("click_count", 0) + 1
        # Close the modal
        app.overlay_manager.clear()

    def on_close():
        """Handle modal close."""
        if app.state.get("status") != "Confirmed!":
            app.state["status"] = "Cancelled"

    # Create modal with button
    modal = ModalWithButton(
        width=50,
        height=12,
        message="Are you sure you want to proceed with this action? This cannot be undone.",
        on_confirm=on_confirm,
    )

    # Center the modal
    x = (term_size.columns - 50) // 2
    y = (term_size.lines - 12) // 2
    modal.bounds = Bounds(x=x, y=y, width=50, height=12)

    # Update button bounds to absolute position
    button_width = len("Confirm") + 4
    modal.button.bounds = Bounds(
        x=x + modal.button_relative_x,
        y=y + modal.button_relative_y,
        width=button_width,
        height=1,
    )

    # Show the modal (focus will be automatically set to the button by overlay manager)
    app.state["status"] = "Waiting for confirmation..."
    app.show_modal(modal, on_close=on_close, dim_background=True)


# Register key handler for 'o' key to open modal
def handle_key(event):
    if event.key == "o":
        open_modal(None)


app.on(EventType.KEY, handle_key, scope=HandlerScope.GLOBAL)


if __name__ == "__main__":
    app.state["status"] = "Ready"
    app.state["click_count"] = 0
    app.run()
