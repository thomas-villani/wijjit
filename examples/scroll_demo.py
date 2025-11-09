"""Scrolling demonstration.

This example demonstrates scrolling support in Wijjit frames:
- Frame with many lines of content (exceeds viewport)
- Keyboard scrolling (arrows, Page Up/Down, Home/End)
- Mouse wheel scrolling
- Visual scrollbar showing position
- Status line showing scroll information

Try:
- Up/Down arrows to scroll line by line
- Page Up/Down to scroll by viewport
- Home/End to jump to top/bottom
- Mouse wheel to scroll (if supported)
- Press 'q' to quit
"""

from wijjit.layout.frames import BorderStyle, Frame, FrameStyle
from wijjit.terminal.input import InputHandler
from wijjit.terminal.screen import ScreenManager


def create_long_content(num_lines: int = 100) -> str:
    """Create content with many lines for scrolling demo.

    Parameters
    ----------
    num_lines : int
        Number of content lines to generate

    Returns
    -------
    str
        Multi-line content string
    """
    lines = []
    for i in range(1, num_lines + 1):
        lines.append(f"Line {i:3d}: This is content line number {i}.")
    return "\n".join(lines)


def main():
    """Run the scroll demo."""
    # Create screen and input handler
    screen = ScreenManager()
    input_handler = InputHandler(enable_mouse=True)

    try:
        # Enter alternate screen
        screen.enter_alternate_buffer()
        screen.hide_cursor()

        # Create frame with scrolling enabled
        frame_style = FrameStyle(
            border=BorderStyle.DOUBLE,
            title="Scrollable Frame Demo (100 lines)",
            padding=(1, 2, 1, 2),
            scrollable=True,
            show_scrollbar=True,
            overflow_y="auto"
        )

        frame = Frame(width=70, height=20, style=frame_style)

        # Set long content
        content = create_long_content(100)
        frame.set_content(content)

        # Clear screen once at the start
        screen.clear()

        # Main loop
        running = True
        while running:
            # Move cursor to home position (top-left)
            screen.move_cursor(1, 1)

            # Render frame
            frame_output = frame.render()
            screen.write(frame_output)

            # Show status line
            if frame.scroll_manager:
                state = frame.scroll_manager.state
                status = (
                    f"\nScroll: {state.scroll_position}/{state.max_scroll} "
                    f"({state.scroll_percentage*100:.0f}%) | "
                    f"Visible: {state.viewport_size} lines of {state.content_size} total"
                )
            else:
                status = "\nNo scrolling needed - content fits in frame"

            screen.write(status)
            screen.write("\nControls: Arrows, PgUp/PgDn, Home/End, Mouse Wheel  |  'q' to quit")

            # Clear any remaining content from previous render
            screen.write("\n" + " " * 70)  # Clear extra line if needed

            # Handle input
            event = input_handler.read_input()

            if event is None:
                continue

            # Check for keyboard input
            from wijjit.terminal.input import Key
            if isinstance(event, Key):
                # Check for quit
                if event.name == 'q':
                    running = False
                    continue

                # Handle scroll keys
                frame.handle_key(event)

            # Check for mouse input
            from wijjit.terminal.mouse import MouseEvent
            if isinstance(event, MouseEvent):
                frame.handle_mouse(event)

    finally:
        # Clean up
        input_handler.close()
        screen.cleanup()


if __name__ == "__main__":
    main()
