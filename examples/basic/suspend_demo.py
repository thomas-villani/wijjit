"""Suspend/Background Demo - Demonstrates Ctrl+Z suspend functionality.

This example shows how Wijjit handles Ctrl+Z suspend on Unix-like systems
(Linux, macOS, BSD). When you press Ctrl+Z, the application will:
1. Properly clean up terminal state (exit alternate screen, show cursor)
2. Suspend to background
3. Resume cleanly when you run 'fg' in your shell

Run with: python examples/basic/suspend_demo.py

On Linux/macOS:
- Press Ctrl+Z to suspend the app
- Run 'fg' in your shell to resume
- Press 'q' to quit

On Windows:
- Ctrl+Z suspend is not available
- Press 'q' to quit

Notes
-----
This feature only works on Unix-like systems (Linux, macOS, BSD).
On Windows, the Ctrl+Z suspend functionality is disabled.
"""

import sys

from wijjit import Wijjit


def main():
    """Run the suspend demo app."""
    app = Wijjit()

    # Check if suspend is available on this platform
    suspend_available = app.suspend_manager.available

    @app.view("main", default=True)
    def main_view():
        """Main view with suspend instructions."""
        if suspend_available:
            suspend_info = """On this system (Unix), you can:
- Press Ctrl+Z to suspend the app to background
- Run 'fg' in your shell to resume
- The display will be fully restored after resume"""
        else:
            suspend_info = """Note: Ctrl+Z suspend is not available on Windows.
This feature only works on Unix-like systems (Linux, macOS, BSD)."""

        return {
            "template": f"""
{{% frame title="Suspend Demo" border="double" %}}
{{% vstack %}}

Welcome to the Wijjit Suspend Demo!

{suspend_info}

Current platform: {sys.platform}
Suspend available: {suspend_available}

Press 'q' to quit.

{{% endvstack %}}
{{% endframe %}}
""",
        }

    @app.on_key("q")
    def on_quit(event):
        """Quit the app on 'q' key."""
        app.quit()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
