"""Radio Button Demo - Demonstrates Radio and RadioGroup elements.

This example shows how to use radio buttons for single selection
with the Wijjit framework. It demonstrates:
- Individual Radio elements (manual grouping)
- RadioGroup container with borders
- Focus management with Tab navigation
- State synchronization
- Mutual exclusion within groups

Run with: python examples/radio_demo.py

Controls:
- Tab/Shift+Tab: Navigate between elements
- Space: Select radio option
- Arrow keys: Navigate and select within RadioGroup
- Enter: Submit form
- q: Quit
"""

import shutil

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.elements.input.button import Button
from wijjit.elements.input.radio import RadioGroup


def create_app():
    """Create and configure the radio demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    app = Wijjit(initial_state={
        "size": None,
        "color": None,
        "submitted": False,
    })

    # Create radio group for size selection
    size_group = RadioGroup(
        name="size",
        id="size_group",
        options=[
            {"value": "s", "label": "Small"},
            {"value": "m", "label": "Medium"},
            {"value": "l", "label": "Large"},
            {"value": "xl", "label": "Extra Large"},
        ],
        selected_value="m",
        width=25,
        border_style="rounded",
        title="Select Size",
        orientation="vertical",
    )

    # Create radio group for color selection
    color_group = RadioGroup(
        name="color",
        id="color_group",
        options=["Red", "Green", "Blue", "Yellow"],
        selected_value="Blue",
        width=25,
        border_style="single",
        title="Select Color",
        orientation="vertical",
    )

    submit_button = Button(
        label="Submit Order",
        id="submit_btn",
    )

    # Set up state synchronization
    def sync_size(old_value, new_value):
        """Sync size selection to app state."""
        app.state["size"] = new_value
        app.refresh()

    def sync_color(old_value, new_value):
        """Sync color selection to app state."""
        app.state["color"] = new_value
        app.refresh()

    size_group.on_change = sync_size
    color_group.on_change = sync_color

    # Initialize state with default values
    app.state["size"] = size_group.selected_value
    app.state["color"] = color_group.selected_value

    # Register elements with focus manager
    app.focus_manager.set_elements([
        size_group,
        color_group,
        submit_button,
    ])

    # Button click handler
    def on_submit():
        """Handle form submission."""
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
                "  RADIO BUTTON DEMO",
                border,
                "",
                "  " + size_group.render().replace("\n", "\n  "),
                "",
                "  " + color_group.render().replace("\n", "\n  "),
                "",
                "  " + submit_button.render(),
                "",
            ]

            # Show submitted values if form was submitted
            if app.state["submitted"]:
                # Map size codes to labels
                size_labels = {"s": "Small", "m": "Medium", "l": "Large", "xl": "Extra Large"}
                size_label = size_labels.get(app.state["size"], app.state["size"])

                content_lines.extend([
                    border,
                    "  ORDER SUBMITTED:",
                    border,
                    f"  Size: {size_label}",
                    f"  Color: {app.state['color']}",
                    border,
                    "",
                ])

            content_lines.extend([
                "  Controls:",
                "    [Tab/Shift+Tab] Navigate  [Space/Arrows] Select  [Enter] Submit",
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
    """Run the radio demo application."""
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
