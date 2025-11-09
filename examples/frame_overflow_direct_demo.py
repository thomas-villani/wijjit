"""Frame Text Overflow Direct API Demo.

This example demonstrates the three overflow_x modes using the Frame API directly
(without templates), showing side-by-side comparison.

Run with: python examples/frame_overflow_direct_demo.py

Controls:
- q: Quit
- Up/Down arrows: Scroll the wrap frame
"""

from wijjit.layout.frames import BorderStyle, Frame, FrameStyle
from wijjit.terminal.ansi import ANSIColor
from wijjit.terminal.input import InputHandler
from wijjit.terminal.screen import ScreenManager


def create_sample_content() -> str:
    """Create sample content to demonstrate overflow.

    Returns
    -------
    str
        Multi-line sample text
    """
    return f"""Text Overflow Demo

This is a {ANSIColor.RED}long line{ANSIColor.RESET} that demonstrates how overflow modes work.

The quick brown fox jumps over the lazy dog and continues running across the meadow.

Features demonstrated:
- Word boundary wrapping
- ANSI code preservation
- Different overflow behaviors

Try scrolling the WRAP frame with arrow keys!"""


def main():
    """Run the frame overflow direct API demo."""
    # Create screen and input handler
    screen = ScreenManager()
    input_handler = InputHandler(enable_mouse=True)

    try:
        # Enter alternate screen
        screen.enter_alternate_buffer()
        screen.hide_cursor()

        # Create three frames with different overflow modes
        frame_clip = Frame(
            width=35,
            height=20,
            style=FrameStyle(
                border=BorderStyle.SINGLE,
                title="CLIP Mode (default)",
                overflow_x="clip",
                padding=(1, 1, 1, 1),
            ),
        )

        frame_visible = Frame(
            width=35,
            height=20,
            style=FrameStyle(
                border=BorderStyle.SINGLE,
                title="VISIBLE Mode",
                overflow_x="visible",
                padding=(1, 1, 1, 1),
            ),
        )

        frame_wrap = Frame(
            width=35,
            height=20,
            style=FrameStyle(
                border=BorderStyle.SINGLE,
                title="WRAP Mode (scrollable)",
                overflow_x="wrap",
                scrollable=True,
                show_scrollbar=True,
                padding=(1, 1, 1, 1),
            ),
        )

        # Set the same content for all frames
        sample_content = create_sample_content()
        frame_clip.set_content(sample_content)
        frame_visible.set_content(sample_content)
        frame_wrap.set_content(sample_content)

        # Main loop
        running = True
        while running:
            # Clear screen and move to home
            screen.clear()
            screen.move_cursor(1, 1)

            # Render header
            header = f"{ANSIColor.BOLD}Frame Text Overflow Demo - Direct API{ANSIColor.RESET}"
            screen.write(header)
            screen.write("\n")
            screen.write("=" * 105)
            screen.write("\n\n")

            # Render frames side by side
            clip_lines = frame_clip.render().split("\n")
            visible_lines = frame_visible.render().split("\n")
            wrap_lines = frame_wrap.render().split("\n")

            # Combine lines horizontally
            max_lines = max(len(clip_lines), len(visible_lines), len(wrap_lines))
            for i in range(max_lines):
                clip_line = clip_lines[i] if i < len(clip_lines) else " " * 35
                visible_line = visible_lines[i] if i < len(visible_lines) else " " * 35
                wrap_line = wrap_lines[i] if i < len(wrap_lines) else " " * 35

                screen.write(f"{clip_line}  {visible_line}  {wrap_line}\n")

            # Instructions
            screen.write("\n")
            screen.write("=" * 105)
            screen.write("\n")
            screen.write("CLIP: Text truncated at frame edge (clean borders)\n")
            screen.write("VISIBLE: Text extends beyond right border (shows overflow)\n")
            screen.write("WRAP: Text wrapped to multiple lines (use arrows to scroll)\n")
            screen.write("\nControls: Up/Down arrows to scroll WRAP frame | 'q' to quit\n")

            # Handle input
            event = input_handler.read_input()

            if event is None:
                continue

            # Check for keyboard input
            from wijjit.terminal.input import Key

            if isinstance(event, Key):
                # Check for quit
                if event.name == "q":
                    running = False
                    continue

                # Handle scroll keys for wrap frame
                frame_wrap.handle_key(event)

            # Check for mouse input
            from wijjit.terminal.mouse import MouseEvent

            if isinstance(event, MouseEvent):
                frame_wrap.handle_mouse(event)

    finally:
        # Clean up
        input_handler.close()
        screen.cleanup()


if __name__ == "__main__":
    main()
