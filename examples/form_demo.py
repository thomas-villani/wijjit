"""Form Input Demo - Demonstrates TextInput, Button, and Focus Management.

This example shows how to integrate Wijjit's Element system (TextInput, Button)
with the Wijjit app framework. It demonstrates:
- Text input with keyboard handling
- Button with click callbacks
- Focus management with Tab/Shift+Tab navigation
- State synchronization between elements and app state
- Manual event routing to elements

Run with: python examples/form_demo.py

Controls:
- Tab/Shift+Tab: Navigate between fields
- Type in name field
- Enter/Space on button: Submit form
- q: Quit
"""

import shutil
from wijjit import (
    Wijjit,
    EventType,
    HandlerScope,
    TextInput,
    Button,
    FocusManager,
    Keys,
)


def create_app():
    """Create and configure the form demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Initialize app with starting state
    app = Wijjit(initial_state={
        "name": "",
        "email": "",
        "submitted_name": None,
        "submitted_email": None,
    })

    # Create UI elements (these persist across renders)
    name_input = TextInput(
        id="name_input",
        placeholder="Enter your name",
        value="",
        width=30,
    )

    email_input = TextInput(
        id="email_input",
        placeholder="Enter your email",
        value="",
        width=30,
    )

    submit_button = Button(
        label="Submit",
        id="submit_btn",
    )

    # Create focus manager and register elements
    focus_manager = FocusManager()
    focus_manager.set_elements([name_input, email_input, submit_button])

    # Button click handler
    def on_submit():
        """Handle form submission."""
        # Update state with the submitted values
        app.state["submitted_name"] = name_input.value
        app.state["submitted_email"] = email_input.value
        app.refresh()

    submit_button.on_click = on_submit

    @app.view("main", default=True)
    def main_view():
        """Main form view."""
        def render_data():
            # Get terminal size for responsive layout
            term_size = shutil.get_terminal_size()
            term_width = term_size.columns

            # Build form content with simple ASCII borders
            border = "=" * 60
            content_lines = [
                border,
                "  FORM INPUT DEMO",
                border,
                "",
                "  Name:  " + name_input.render(),
                "",
                "  Email: " + email_input.render(),
                "",
                "  " + submit_button.render(),
                "",
            ]

            # Show submitted values if available
            if app.state["submitted_name"] or app.state["submitted_email"]:
                content_lines.extend([
                    border,
                    "  SUBMITTED DATA:",
                    border,
                ])
                if app.state["submitted_name"]:
                    content_lines.append(f"  Name:  {app.state['submitted_name']}")
                if app.state["submitted_email"]:
                    content_lines.append(f"  Email: {app.state['submitted_email']}")
                content_lines.extend([
                    border,
                    "",
                ])

            content_lines.extend([
                "  Controls:",
                "    [Tab] Next field  [Shift+Tab] Previous field",
                "    [Enter/Space] Submit (when button focused)",
                "    [q] Quit",
                "",
                border,
            ])

            content_text = "\n".join(content_lines)

            return {"content": content_text}

        data = render_data()

        return {
            "template": "{{ content }}",
            "data": data,
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers for the form view."""

        def on_key(event):
            """Route keyboard events to appropriate handlers."""
            # Handle Tab navigation
            if event.key == "tab":
                focus_manager.focus_next()
                app.refresh()
                return
            elif event.key == "shift+tab":
                focus_manager.focus_previous()
                app.refresh()
                return

            # Handle quit
            if event.key == "q":
                app.quit()
                return

            # Route other keys to the focused element
            focused = focus_manager.get_focused_element()
            if focused:
                # Convert event key to Key object for element handling
                from wijjit.terminal.input import Key, KeyType

                # Create a Key object from the event
                if event.key == "backspace":
                    key_obj = Keys.BACKSPACE
                elif event.key == "delete":
                    key_obj = Keys.DELETE
                elif event.key == "left":
                    key_obj = Keys.LEFT
                elif event.key == "right":
                    key_obj = Keys.RIGHT
                elif event.key == "home":
                    key_obj = Keys.HOME
                elif event.key == "end":
                    key_obj = Keys.END
                elif event.key == "enter":
                    key_obj = Keys.ENTER
                elif event.key == "space":
                    key_obj = Keys.SPACE
                elif len(event.key) == 1:
                    # Regular character
                    key_obj = Key(event.key, KeyType.CHARACTER, event.key)
                else:
                    # Unknown key, ignore
                    return

                # Let the element handle the key
                handled = focused.handle_key(key_obj)

                if handled:
                    # Sync element state back to app state
                    if focused == name_input:
                        app.state["name"] = name_input.value
                    elif focused == email_input:
                        app.state["email"] = email_input.value

                    # Refresh the display
                    app.refresh()

        # Register key handler
        app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main")

    return app


def main():
    """Run the form demo application."""
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
