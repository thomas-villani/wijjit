"""TextArea Demo - Demonstrates multiline text editing with TextArea.

This example shows the TextArea element with:
- Multiline text editing
- Keyboard navigation (arrows, home/end, word boundaries)
- Scrolling for large content
- Mouse support (click to position, wheel to scroll)
- Real-time status display

Run with: python examples/textarea_demo.py

Controls:
- Type to edit text
- Arrow keys: Navigate cursor
- Home/End: Move to line start/end
- Ctrl+Home/End: Move to document start/end
- Ctrl+Left/Right: Jump to word boundaries
- Page Up/Down: Scroll viewport
- Click: Position cursor
- Mouse wheel: Scroll content
- q: Quit
"""

import shutil

from wijjit import (
    EventType,
    HandlerScope,
    TextArea,
    Wijjit,
)


def create_app():
    """Create and configure the textarea demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Initial content for the textarea
    initial_content = """Welcome to Wijjit TextArea!

This is a multiline text editor component. Try these features:

EDITING:
- Type to insert text
- Backspace/Delete to remove characters
- Enter to create new lines

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
- Wheel to scroll content

Press 'q' to quit. Happy editing!"""

    # Initialize app
    app = Wijjit(initial_state={
        "content": initial_content,
        "cursor_pos": "0:0",
        "lines": 0,
        "chars": 0,
    })

    # Create TextArea element
    term_size = shutil.get_terminal_size()
    textarea_width = min(80, term_size.columns - 4)
    textarea_height = term_size.lines - 10  # Leave room for status

    textarea = TextArea(
        id="editor",
        value=initial_content,
        width=textarea_width,
        height=textarea_height,
        show_scrollbar=True,
    )

    # Sync changes to app state
    def sync_content(old_value, new_value):
        """Sync textarea content to app state."""
        app.state["content"] = new_value
        app.state["lines"] = len(textarea.lines)
        app.state["chars"] = len(new_value)
        app.state["cursor_pos"] = f"{textarea.cursor_row}:{textarea.cursor_col}"
        app.refresh()

    textarea.on_change = sync_content

    # Register with focus manager
    app.focus_manager.set_elements([textarea])

    @app.view("main", default=True)
    def main_view():
        """Main textarea view."""
        def render_data():
            term_size = shutil.get_terminal_size()
            term_width = term_size.columns

            # Get scroll info
            scroll_pos = textarea.scroll_manager.state.scroll_position
            scroll_max = textarea.scroll_manager.state.max_scroll
            scroll_pct = int(textarea.scroll_manager.state.scroll_percentage * 100)

            # Build UI
            border = "=" * term_width
            content_lines = [
                border,
                "  TEXTAREA DEMO",
                border,
                "",
                textarea.render(),
                "",
                border,
                f"  Cursor: {app.state['cursor_pos']}  |  Lines: {app.state['lines']}  |  Chars: {app.state['chars']}  |  Scroll: {scroll_pos}/{scroll_max} ({scroll_pct}%)",
                border,
                "  [Arrows] Navigate  [Home/End] Line  [Ctrl+Home/End] Document  [PgUp/PgDn] Scroll  [q] Quit",
                border,
            ]

            content_text = "\n".join(content_lines)

            return {"content": content_text}

        data = render_data()

        return {
            "template": "{{ content }}",
            "data": data,
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers."""

        def on_key(event):
            """Handle keyboard events."""
            # Handle quit
            if event.key == "q" and not textarea.focused:
                app.quit()
                return

            # Focus manager and textarea handle other keys automatically

        # Register key handler
        app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main")

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
