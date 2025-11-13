"""Debug key input to see what keys are being received."""

import sys

from wijjit.terminal.input import InputHandler


def main():
    """Test raw key input."""
    print("Press keys (q to quit). Testing UP/DOWN/LEFT/RIGHT:")
    print()

    input_handler = InputHandler()

    try:
        while True:
            event = input_handler.read_key()

            if event:
                print(f"Received: {event}")
                sys.stdout.flush()

                if hasattr(event, "key") and event.key == "q":
                    break
    except KeyboardInterrupt:
        pass

    print("\nDone")


if __name__ == "__main__":
    main()
