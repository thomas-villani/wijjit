"""TextArea Demo - Demonstrates multiline text editing with TextArea.

This example shows the TextArea element with:
- Multiline text editing
- Keyboard navigation (arrows, home/end, word boundaries)
- Scrolling for large content
- Mouse support (click to position, wheel to scroll)
- Line wrapping modes (none, soft, hard)
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
- F1/F2/F3: Switch wrap modes (none/soft/hard)
- q: Quit
"""

import shutil

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.elements.input.text import TextArea
from wijjit.layout.bounds import Bounds


def create_app():
    """Create and configure the textarea demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Initial content for the textarea
    initial_content = """Welcome to Wijjit TextArea!

This is a multiline text editor component with line wrapping support. Try these features:

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

LINE WRAPPING MODES (F1/F2/F3):
- F1: No wrapping - long lines extend beyond viewport
- F2: Soft wrapping - visual wrapping only, original text unchanged
- F3: Hard wrapping - inserts actual newlines when lines exceed width

Try typing a very long line to see how wrapping works! For example: This is a deliberately long line that will demonstrate the wrapping behavior when it exceeds the width of the text area, showing how the different wrap modes handle text that is too wide to fit.

Press 'q' to quit. Happy editing!"""  #  # noqa: E501

    # Initialize app
    app = Wijjit(
        initial_state={
            "content": initial_content,
            "cursor_pos": "0:0",
            "lines": 0,
            "chars": 0,
            "wrap_mode": "none",
        }
    )

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

            # Set bounds for the textarea so mouse events can find it
            # The textarea top border renders at row 2 (after header border, title, header border)
            # Content starts at row 3, so bounds.y points to the top border at row 2
            textarea.set_bounds(
                Bounds(x=0, y=2, width=textarea_width, height=textarea_height + 2)
            )

            # Add textarea to positioned_elements so _find_element_at can find it
            # Must do this on every render since app clears positioned_elements
            app.positioned_elements = [textarea]

            # Get scroll info
            scroll_pos = textarea.scroll_manager.state.scroll_position
            scroll_max = textarea.scroll_manager.state.max_scroll
            scroll_pct = int(textarea.scroll_manager.state.scroll_percentage * 100)

            # Build UI
            border = "=" * term_width
            wrap_mode_display = app.state.get("wrap_mode", "none").upper()
            content_lines = [
                border,
                "  TEXTAREA DEMO",
                border,
                "",
                textarea.render(),
                "",
                border,
                f"  Cursor: {app.state['cursor_pos']}  |  Lines: {app.state['lines']}  "
                f"|  Chars: {app.state['chars']}  |  Scroll: {scroll_pos}/{scroll_max} ({scroll_pct}%)  "
                f"|  Wrap: {wrap_mode_display}",
                border,
                "  [Arrows] Navigate  [F1/F2/F3] Wrap Mode  [PgUp/PgDn] Scroll  [Esc/Ctrl+Q] Quit",
                border,
            ]

            content_text = "\n".join(content_lines)

            return {"content": content_text}

        return {
            "template": "{{ content }}",
            "data": render_data,  # Pass the function itself, not the result of calling it
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers."""

        def on_key(event):
            """Handle keyboard events."""
            # Handle quit with Escape or Ctrl+Q
            if event.key == "escape" or (
                event.key == "q" and "ctrl" in event.modifiers
            ):
                app.quit()
                event.cancel()  # Prevent further handling
                return

            # Handle wrap mode switching with F1/F2/F3
            if event.key == "f1":
                textarea.wrap_mode = "none"
                app.state["wrap_mode"] = "none"
                # Update scroll manager for new wrap mode
                visual_line_count = textarea._calculate_total_visual_lines()
                textarea.scroll_manager.update_content_size(visual_line_count)
                app.refresh()
                event.cancel()
                return
            elif event.key == "f2":
                textarea.wrap_mode = "soft"
                app.state["wrap_mode"] = "soft"
                # Update scroll manager for new wrap mode
                visual_line_count = textarea._calculate_total_visual_lines()
                textarea.scroll_manager.update_content_size(visual_line_count)
                app.refresh()
                event.cancel()
                return
            elif event.key == "f3":
                textarea.wrap_mode = "hard"
                app.state["wrap_mode"] = "hard"
                # Update scroll manager for new wrap mode
                visual_line_count = textarea._calculate_total_visual_lines()
                textarea.scroll_manager.update_content_size(visual_line_count)
                app.refresh()
                event.cancel()
                return

            # Focus manager and textarea handle other keys automatically

        # Register key handler with high priority to intercept before TextArea
        app.on(
            EventType.KEY,
            on_key,
            scope=HandlerScope.VIEW,
            view_name="main",
            priority=100,
        )

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
