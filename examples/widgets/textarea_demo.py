"""TextArea Demo - Demonstrates multiline text editing with TextArea.

This example shows the TextArea element with:
- Multiline text editing
- Text selection (keyboard and mouse)
- Clipboard operations (copy, cut, paste)
- Keyboard navigation (arrows, home/end, word boundaries)
- Scrolling for large content
- Mouse support (click, drag, double-click)
- Line wrapping modes (none, soft, hard)
- Real-time status display

Run with: python examples/textarea_demo.py

Controls:
- Type to edit text
- Arrow keys: Navigate cursor
- Shift+Arrows: Select text
- Ctrl+A: Select all
- Ctrl+C: Copy selection
- Ctrl+X: Cut selection
- Ctrl+V: Paste
- Home/End: Move to line start/end
- Ctrl+Home/End: Move to document start/end
- Ctrl+Left/Right: Jump to word boundaries
- Page Up/Down: Scroll viewport
- Click: Position cursor
- Shift+Click: Extend selection
- Double-click: Select word
- Click and drag: Select text
- Mouse wheel: Scroll content
- F1/F2/F3: Switch wrap modes (none/soft/hard)
- Ctrl+Q: Quit
"""

import shutil

from wijjit import Wijjit
from wijjit.logging_config import configure_logging

# Enable debug logging
configure_logging(filename="textarea-demo.log", level="DEBUG")

# Initial content for the textarea
INITIAL_CONTENT = """Welcome to Wijjit TextArea!

This is a multiline text editor component with selection and clipboard support. Try these features:

EDITING:
- Type to insert text (replaces selection if active)
- Backspace/Delete to remove characters or delete selection
- Enter to create new lines

TEXT SELECTION:
- Shift+Arrows to select text with keyboard
- Shift+Home/End to select to line boundaries
- Shift+Ctrl+Home/End to select to document boundaries
- Ctrl+A to select all text
- Click and drag with mouse to select
- Double-click to select a word
- Shift+Click to extend selection

CLIPBOARD OPERATIONS:
- Ctrl+C to copy selected text
- Ctrl+X to cut selected text
- Ctrl+V to paste from clipboard

NAVIGATION:
- Arrow keys to move cursor
- Home/End for line start/end
- Ctrl+Home/End for document start/end
- Ctrl+Left/Right to jump between words

SCROLLING:
- Page Up/Down to scroll by viewport
- Mouse wheel to scroll
- Auto-scrolling follows cursor

MOUSE:
- Click to position cursor
- Shift+Click to extend selection
- Double-click to select word
- Click and drag to select text
- Wheel to scroll content

LINE WRAPPING MODES (F1/F2/F3):
- F1: No wrapping - long lines extend beyond viewport
- F2: Soft wrapping - visual wrapping only, original text unchanged
- F3: Hard wrapping - inserts actual newlines when lines exceed width

Try selecting and copying this text! For example: This is a deliberately long line that will demonstrate the wrapping behavior when it exceeds the width of the text area, showing how the different wrap modes handle text that is too wide to fit.

Press Ctrl+Q to quit. Happy editing!"""  # noqa: E501


def create_app():
    """Create and configure the textarea demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Get terminal size for responsive layout
    term_size = shutil.get_terminal_size()
    textarea_width = min(80, term_size.columns - 4)
    textarea_height = term_size.lines - 10  # Leave room for status
    term_width = term_size.columns

    # Initialize app with all state needed for rendering
    app = Wijjit(
        initial_state={
            "content": INITIAL_CONTENT,
            "wrap_mode": "none",
            "width": textarea_width,
            "height": textarea_height,
            "border": "=" * term_width,
        }
    )

    @app.view("main", default=True)
    def main_view():
        """Main textarea view."""
        # Calculate dynamic values
        content = app.state.get("content", "")
        lines = content.count("\n") + 1 if content else 0
        chars = len(content)
        wrap_mode_display = app.state.get("wrap_mode", "none").upper()

        # Update state with computed values
        app.state["lines"] = lines
        app.state["chars"] = chars
        app.state["wrap_display"] = wrap_mode_display

        return {
            "template": """{% frame title="TextArea demo" %}
{% textarea id="content" height=7 width=80 show_scrollbar=true border_style="single" %}{% endtextarea %}
  Lines: {{ state.lines }}  |  Chars: {{ state.chars }}  |  Wrap: {{ state.wrap_display }}
  [Shift+Arrows] Select  [Ctrl+C/X/V] Clipboard  [Ctrl+A] Select All  [Ctrl+Q] Quit
{% endframe %}
""",
        }

    return app


def main():
    """Run the textarea demo application."""
    app = create_app()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
