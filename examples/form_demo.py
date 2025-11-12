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

from wijjit import Wijjit
from wijjit.core.events import ActionEvent, EventType, HandlerScope
from wijjit.elements.input.button import Button
from wijjit.elements.input.text import TextInput


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

    # Set up state synchronization - sync element values to app state on change
    def sync_name(old_value, new_value):
        """Sync name input to app state."""
        app.state["name"] = new_value
        app.refresh()

    def sync_email(old_value, new_value):
        """Sync email input to app state."""
        app.state["email"] = new_value
        app.refresh()

    name_input.on_change = sync_name
    email_input.on_change = sync_email

    # Register elements with the app's built-in focus manager
    # The app will automatically handle Tab/Shift+Tab and route keys to focused elements
    app.focus_manager.set_elements([name_input, email_input, submit_button])

    # Button click handler
    def on_submit(event: ActionEvent):
        """Handle form submission.

        Parameters
        ----------
        event : ActionEvent
            The action event from the button click
        """
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
            border = "=" * term_width
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

        # data = render_data()  # Fixed: pass function directly

        return {
            "template": "{{ content }}",
            "data": render_data,  # Pass the function itself, not the result
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers for the form view."""

        def on_key(event):
            """Handle custom keyboard events."""
            # Handle quit
            if event.key == "q":
                app.quit()
                return

            # Note: Tab/Shift+Tab navigation is handled automatically by the app
            # Note: Key routing to focused elements is handled automatically by the app

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
