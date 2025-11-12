"""Checkbox Demo - Demonstrates Checkbox and CheckboxGroup elements.

This example shows how to use checkboxes for multiple selections
with the Wijjit framework. It demonstrates:
- Individual Checkbox elements
- CheckboxGroup container with borders
- Focus management with Tab navigation
- State synchronization
- Change event handling

Run with: python examples/checkbox_demo.py

Controls:
- Tab/Shift+Tab: Navigate between elements
- Space: Toggle checkbox
- Arrow keys: Navigate within CheckboxGroup
- Enter: Submit form
- q: Quit
"""

import shutil

from wijjit import Wijjit
from wijjit.core.events import ActionEvent, EventType, HandlerScope
from wijjit.elements.input.button import Button
from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup


def create_app():
    """Create and configure the checkbox demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    app = Wijjit(initial_state={
        "newsletter": False,
        "terms": False,
        "features": [],
        "submitted": False,
    })

    # Create individual checkbox elements
    newsletter_checkbox = Checkbox(
        id="newsletter",
        label="Subscribe to newsletter",
        checked=False,
    )

    terms_checkbox = Checkbox(
        id="terms",
        label="I agree to the terms and conditions",
        checked=False,
    )

    # Create checkbox group for features
    features_group = CheckboxGroup(
        id="features",
        options=[
            {"value": "notifications", "label": "Email notifications"},
            {"value": "updates", "label": "Product updates"},
            {"value": "marketing", "label": "Marketing emails"},
        ],
        width=35,
        border_style="single",
        title="Email Preferences",
    )

    submit_button = Button(
        label="Submit",
        id="submit_btn",
    )

    # Set up state synchronization
    def sync_newsletter(old_value, new_value):
        """Sync newsletter checkbox to app state."""
        app.state["newsletter"] = new_value
        app.refresh()

    def sync_terms(old_value, new_value):
        """Sync terms checkbox to app state."""
        app.state["terms"] = new_value
        app.refresh()

    def sync_features(old_value, new_value):
        """Sync features group to app state."""
        app.state["features"] = new_value
        app.refresh()

    newsletter_checkbox.on_change = sync_newsletter
    terms_checkbox.on_change = sync_terms
    features_group.on_change = sync_features

    # Register elements with focus manager
    app.focus_manager.set_elements([
        newsletter_checkbox,
        terms_checkbox,
        features_group,
        submit_button,
    ])

    # Button click handler
    def on_submit(event: ActionEvent):
        """Handle form submission.

        Parameters
        ----------
        event : ActionEvent
            The action event from the button click
        """
        app.state["submitted"] = True
        app.refresh()

    submit_button.on_click = on_submit

    @app.view("main", default=True)
    def main_view():
        """Main form view."""
        def render_data():
            term_size = shutil.get_terminal_size()
            term_width = term_size.columns

            border = "=" * term_width
            content_lines = [
                border,
                "  CHECKBOX DEMO",
                border,
                "",
                "  " + newsletter_checkbox.render(),
                "",
                "  " + terms_checkbox.render(),
                "",
                "  " + features_group.render().replace("\n", "\n  "),
                "",
                "  " + submit_button.render(),
                "",
            ]

            # Show submitted values if form was submitted
            if app.state["submitted"]:
                content_lines.extend([
                    border,
                    "  SUBMITTED:",
                    border,
                    f"  Newsletter: {app.state['newsletter']}",
                    f"  Terms Accepted: {app.state['terms']}",
                    f"  Selected Features: {', '.join(app.state['features']) if app.state['features'] else 'None'}",
                    border,
                    "",
                ])

            content_lines.extend([
                "  Controls:",
                "    [Tab/Shift+Tab] Navigate  [Space] Toggle  [Enter] Submit",
                "    [q] Quit",
                "",
                border,
            ])

            return {"content": "\n".join(content_lines)}

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
            if event.key == "q":
                app.quit()
                return

        app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main")

    return app


def main():
    """Run the checkbox demo application."""
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
