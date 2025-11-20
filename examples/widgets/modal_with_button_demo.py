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
from wijjit.core.events import ActionEvent
from wijjit.elements.input.button import Button
from wijjit.layout.bounds import Bounds
from wijjit.terminal.ansi import supports_unicode

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

    def _handle_button_click(self, event: ActionEvent):
        """Handle button click.

        Parameters
        ----------
        event : ActionEvent
            The action event containing button context
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

    def render_to(self, ctx):
        """Render the modal content with button using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds
        """
        from wijjit.rendering.paint_context import PaintContext
        from wijjit.styling.style import Style

        # Get default style for modal (white text on default background)
        default_style = Style(fg="white")
        title_style = Style(fg="white", bold=True)

        # Draw top border
        border_top = (
            self.chars["tl"] + self.chars["h"] * (self.width - 2) + self.chars["tr"]
        )
        ctx.write_text(0, 0, border_top, default_style)

        # Empty line
        empty_line = self.chars["v"] + " " * (self.width - 2) + self.chars["v"]
        ctx.write_text(0, 1, empty_line, default_style)

        # Title (centered)
        title_plain = "Confirm Action"
        title_visible_len = len(title_plain)
        padding_needed = self.width - 2 - title_visible_len
        left_pad = padding_needed // 2
        right_pad = padding_needed - left_pad

        # Write borders with default style
        ctx.write_text(0, 2, self.chars["v"], default_style)
        ctx.write_text(self.width - 1, 2, self.chars["v"], default_style)
        # Write title with bold style
        ctx.write_text(1 + left_pad, 2, title_plain, title_style)
        # Write padding spaces
        if left_pad > 0:
            ctx.write_text(1, 2, " " * left_pad, default_style)
        if right_pad > 0:
            ctx.write_text(
                1 + left_pad + title_visible_len, 2, " " * right_pad, default_style
            )

        # Empty line
        ctx.write_text(0, 3, empty_line, default_style)

        # Message (wrapped if needed)
        message_lines = self._wrap_message(self.message, self.width - 4)
        current_y = 4
        for msg_line in message_lines:
            line_content = (
                self.chars["v"] + " " + msg_line.ljust(self.width - 3) + self.chars["v"]
            )
            ctx.write_text(0, current_y, line_content, default_style)
            current_y += 1

        # Fill space before button
        while current_y < self.button_relative_y:
            ctx.write_text(0, current_y, empty_line, default_style)
            current_y += 1

        # Render button line with empty space around button
        # Left border and spaces
        button_prefix = self.chars["v"] + " " * self.button_relative_x
        ctx.write_text(0, current_y, button_prefix, default_style)

        # Render button at its position
        button_ctx = PaintContext(
            ctx.buffer,
            ctx.style_resolver,
            Bounds(
                x=ctx.bounds.x + 1 + self.button_relative_x,
                y=ctx.bounds.y + current_y,
                width=self.button.bounds.width,
                height=self.button.bounds.height,
            ),
        )
        self.button.render_to(button_ctx)

        # Right side spaces and border
        button_end_x = 1 + self.button_relative_x + self.button.bounds.width
        right_spaces = " " * (self.width - 1 - button_end_x) + self.chars["v"]
        ctx.write_text(button_end_x, current_y, right_spaces, default_style)

        current_y += 1

        # Fill remaining height
        while current_y < self.height - 1:
            ctx.write_text(0, current_y, empty_line, default_style)
            current_y += 1

        # Bottom border
        border_bottom = (
            self.chars["bl"] + self.chars["h"] * (self.width - 2) + self.chars["br"]
        )
        ctx.write_text(0, current_y, border_bottom, default_style)

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
@app.on_key("o")
def handle_key_o(event):
    """Open modal on 'o' key press."""
    open_modal(None)


if __name__ == "__main__":
    app.state["status"] = "Ready"
    app.state["click_count"] = 0
    app.run()
