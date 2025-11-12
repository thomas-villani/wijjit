"""Integration tests for menu system.

Tests cover integration between:
- Menu elements (MenuElement, DropdownMenu, ContextMenu)
- App state management
- Overlay system
- Action dispatching
- Focus management
"""


import pytest

from wijjit.core.app import Wijjit
from wijjit.core.overlay import LayerType
from wijjit.elements.menu import ContextMenu, DropdownMenu, MenuItem
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

pytestmark = pytest.mark.integration


# Helper to render template with overlay support
def render_template(app: Wijjit, template: str, width: int = 80, height: int = 24):
    """Render a template with overlay support.

    Parameters
    ----------
    app : Wijjit
        Application instance
    template : str
        Jinja2 template string to render
    width : int
        Terminal width (default: 80)
    height : int
        Terminal height (default: 24)

    Returns
    -------
    tuple of (str, list)
        Rendered output and elements list
    """
    data = {"state": app.state}
    app.renderer.add_global("_wijjit_current_context", data)

    output, elements, layout_ctx = app.renderer.render_with_layout(
        template,
        context=data,
        width=width,
        height=height,
        overlay_manager=app.overlay_manager,
    )

    app._sync_template_overlays(layout_ctx)
    app.renderer.add_global("_wijjit_current_context", None)

    return output, elements


class TestMenuStateIntegration:
    """Test integration between menus and app state."""

    def test_dropdown_visibility_controlled_by_state(self):
        """Test dropdown menu visibility is controlled by app state.

        Verifies state -> menu visibility integration.
        """
        app = Wijjit()
        app.state.show_menu = False

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        # Initially hidden
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 0

        # Show menu
        app.state.show_menu = True
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1

        # Hide again
        app.state.show_menu = False
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 0

    def test_contextmenu_visibility_controlled_by_state(self):
        """Test context menu visibility is controlled by app state.

        Verifies state -> context menu visibility integration.
        """
        app = Wijjit()
        app.state.show_context = False

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="list" visible="show_context" %}
                {% menuitem action="delete" %}Delete{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        # Initially hidden
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 0

        # Show context menu
        app.state.show_context = True
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1

    @pytest.mark.skip(
        reason="Dynamic menu items from for loops not yet fully supported"
    )
    def test_menu_items_from_state_data(self):
        """Test menu items can be dynamically generated from state.

        Verifies dynamic menu content from state.
        """
        app = Wijjit()
        app.state.show_menu = True
        app.state.actions = [
            {"label": "New", "action": "new"},
            {"label": "Open", "action": "open"},
            {"label": "Save", "action": "save"},
        ]

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% for item in actions %}
                    {% menuitem action=item.action %}{{ item.label }}{% endmenuitem %}
                {% endfor %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert len(dropdown.items) == 3
        assert dropdown.items[0].label == "New"
        assert dropdown.items[1].label == "Open"
        assert dropdown.items[2].label == "Save"

    def test_multiple_menus_with_independent_state(self):
        """Test multiple menus with independent visibility state.

        Verifies independent state control for multiple menus.
        """
        app = Wijjit()
        app.state.show_file = True
        app.state.show_edit = False

        template = """
        {% frame width="80" height="24" %}
            {% dropdown id="file" trigger="File" visible="show_file" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
            {% dropdown id="edit" trigger="Edit" visible="show_edit" %}
                {% menuitem action="copy" %}Copy{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Only file menu should be visible
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].element.id == "file"


class TestMenuActionIntegration:
    """Test integration between menus and action dispatching."""

    def test_menu_selection_triggers_app_action(self):
        """Test menu item selection triggers app action handler.

        Verifies menu -> action -> handler integration.
        """
        app = Wijjit()
        action_called = []

        @app.on_action("new_file")
        def handle_new(event):
            action_called.append("new_file")

        # Create menu manually with app integration
        items = [MenuItem(label="New", action="new_file")]
        menu = DropdownMenu(items=items)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        # Set up callback to dispatch action
        def on_select(action_id, item):
            app._dispatch_action(action_id, {"source": "menu"})

        menu.on_item_select = on_select

        # Select item
        menu.handle_key(Keys.ENTER)

        # Action handler should have been called
        assert "new_file" in action_called

    def test_menu_selection_updates_state(self):
        """Test menu item selection can update app state.

        Verifies menu -> action -> state update integration.
        """
        app = Wijjit()
        app.state.selected_item = None

        @app.on_action("select_item")
        def handle_select(event):
            app.state.selected_item = "Item 1"

        items = [MenuItem(label="Item 1", action="select_item")]
        menu = DropdownMenu(items=items)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        def on_select(action_id, item):
            app._dispatch_action(action_id, {"source": "menu"})

        menu.on_item_select = on_select

        # Select item
        menu.handle_key(Keys.ENTER)

        # State should be updated
        assert app.state.selected_item == "Item 1"

    def test_menu_close_on_selection(self):
        """Test menu closes after item selection.

        Verifies menu selection -> close integration.
        """
        closed = []

        items = [MenuItem(label="Item", action="action")]
        menu = DropdownMenu(items=items)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        def close_callback():
            closed.append(True)

        menu.close_callback = close_callback

        # Select item
        menu.handle_key(Keys.ENTER)

        # Close callback should have been called
        assert len(closed) == 1


class TestMenuOverlayIntegration:
    """Test integration between menus and overlay system."""

    def test_dropdown_registered_as_overlay(self):
        """Test dropdown is properly registered in overlay manager.

        Verifies menu -> overlay registration integration.
        """
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown id="menu" trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Check overlay was registered
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.DROPDOWN
        assert isinstance(overlay.element, DropdownMenu)
        assert overlay.close_on_escape is True
        assert overlay.close_on_click_outside is True
        assert overlay.trap_focus is True

    def test_contextmenu_registered_as_overlay(self):
        """Test context menu is properly registered in overlay manager.

        Verifies context menu -> overlay registration integration.
        """
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu id="ctx" target="list" visible="show_context" %}
                {% menuitem action="delete" %}Delete{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Check overlay was registered
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.DROPDOWN
        assert isinstance(overlay.element, ContextMenu)

    def test_menu_overlay_cleared_on_visibility_false(self):
        """Test menu overlay is cleared when visibility becomes false.

        Verifies overlay cleanup on visibility change.
        """
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        # Show menu
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1

        # Hide menu
        app.state.show_menu = False
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 0

    def test_multiple_menu_overlays_stacking(self):
        """Test multiple menu overlays stack correctly.

        Verifies overlay stacking for multiple menus.
        """
        app = Wijjit()
        app.state.show_file = True
        app.state.show_edit = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown id="file" trigger="File" visible="show_file" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
            {% dropdown id="edit" trigger="Edit" visible="show_edit" %}
                {% menuitem action="copy" %}Copy{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Both menus should be registered
        assert len(app.overlay_manager.overlays) == 2


class TestMenuFocusIntegration:
    """Test integration between menus and focus management."""

    def test_menu_receives_focus_when_shown(self):
        """Test menu receives focus when displayed.

        Verifies menu focus integration.
        """
        items = [MenuItem(label="Item", action="action")]
        menu = DropdownMenu(items=items)

        # Menu should be focusable
        assert menu.focusable is True

        # Simulate focus
        menu.on_focus()
        assert menu.focused is True

    def test_menu_keyboard_navigation_when_focused(self):
        """Test menu responds to keyboard when focused.

        Verifies focus -> keyboard handling integration.
        """
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2"),
            MenuItem(label="Item 3", action="a3"),
        ]
        menu = DropdownMenu(items=items)
        menu.bounds = Bounds(x=0, y=0, width=32, height=5)
        menu.on_focus()

        # Navigate with keyboard
        initial_index = menu.highlighted_index
        menu.handle_key(Keys.DOWN)
        assert menu.highlighted_index != initial_index

    def test_menu_mouse_interaction_updates_highlight(self):
        """Test mouse interaction with menu updates highlight.

        Verifies mouse -> menu highlight integration.
        """
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2"),
        ]
        menu = DropdownMenu(items=items)
        menu.bounds = Bounds(x=10, y=5, width=32, height=4)

        # Hover over second item (border at y=5, item 1 at y=6, item 2 at y=7)
        event = MouseEvent(type=MouseEventType.MOVE, button=MouseButton.NONE, x=15, y=7)
        result = menu.handle_mouse(event)

        assert result is True
        assert menu.highlighted_index == 1

    def test_menu_click_selects_and_closes(self):
        """Test menu click selects item and triggers close.

        Verifies mouse click -> selection -> close integration.
        """
        items = [MenuItem(label="Item", action="action")]
        menu = DropdownMenu(items=items)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        select_called = []
        close_called = []

        def on_select(action_id, item):
            select_called.append(action_id)

        def on_close():
            close_called.append(True)

        menu.on_item_select = on_select
        menu.close_callback = on_close

        # Click on item (y=1, accounting for border)
        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=1)
        menu.handle_mouse(event)

        # Both callbacks should have fired
        assert len(select_called) == 1
        assert len(close_called) == 1


class TestMenuRenderingIntegration:
    """Test integration between menus and rendering system."""

    def test_menu_renders_with_bounds(self):
        """Test menu renders correctly with bounds set.

        Verifies menu -> rendering integration.
        """
        items = [MenuItem(label="Item 1", action="a1")]
        menu = DropdownMenu(items=items, width=30)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        output = menu.render()

        assert output
        assert "Item 1" in output
        assert "\n" in output

    def test_menu_renders_highlighted_item_when_focused(self):
        """Test menu renders highlighted item correctly when focused.

        Verifies focus -> rendering integration.
        """
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2"),
        ]
        menu = DropdownMenu(items=items, width=30)
        menu.bounds = Bounds(x=0, y=0, width=32, height=4)
        menu.on_focus()
        menu.highlighted_index = 0

        output = menu.render()

        # Should have REVERSE styling for highlighted item
        from wijjit.terminal.ansi import ANSIStyle

        assert ANSIStyle.REVERSE in output

    def test_menu_renders_disabled_items_dimmed(self):
        """Test menu renders disabled items with DIM style.

        Verifies disabled item -> rendering integration.
        """
        items = [MenuItem(label="Disabled", action="action", disabled=True)]
        menu = DropdownMenu(items=items, width=30)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        output = menu.render()

        from wijjit.terminal.ansi import ANSIStyle

        assert ANSIStyle.DIM in output

    def test_menu_renders_keyboard_shortcuts(self):
        """Test menu renders keyboard shortcuts correctly.

        Verifies shortcut -> rendering integration.
        """
        items = [MenuItem(label="Copy", action="copy", key="Ctrl+C")]
        menu = DropdownMenu(items=items, width=30)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        output = menu.render()

        assert "Copy" in output
        assert "Ctrl+C" in output


class TestMenuComplexScenarios:
    """Test complex menu integration scenarios."""

    def test_nested_menu_state_updates(self):
        """Test complex state updates through menu interactions.

        Verifies complex menu -> state integration.
        """
        app = Wijjit()
        app.state.file_menu_open = False
        app.state.recent_files = []

        @app.on_action("new_file")
        def handle_new(event):
            app.state.recent_files.append("Untitled.txt")
            app.state.file_menu_open = False

        items = [MenuItem(label="New", action="new_file")]
        menu = DropdownMenu(items=items)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)

        def on_select(action_id, item):
            app._dispatch_action(action_id, {})

        menu.on_item_select = on_select

        # Initial state
        assert len(app.state.recent_files) == 0

        # Select new file
        menu.handle_key(Keys.ENTER)

        # State should be updated
        assert len(app.state.recent_files) == 1
        assert app.state.recent_files[0] == "Untitled.txt"

    @pytest.mark.skip(
        reason="Conditional menu items from if statements not yet fully supported"
    )
    def test_menu_with_conditional_items_from_state(self):
        """Test menu with items conditionally rendered based on state.

        Verifies conditional menu content from state.
        """
        app = Wijjit()
        app.state.show_menu = True
        app.state.is_admin = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Actions" visible="show_menu" %}
                {% menuitem action="view" %}View{% endmenuitem %}
                {% if is_admin %}
                    {% menuitem action="edit" %}Edit{% endmenuitem %}
                    {% menuitem action="delete" %}Delete{% endmenuitem %}
                {% endif %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element

        # Should have 3 items (view, edit, delete)
        assert len(dropdown.items) == 3

        # Change state
        app.state.is_admin = False
        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element

        # Should only have 1 item (view)
        assert len(dropdown.items) == 1

    def test_menu_escape_key_integration(self):
        """Test ESC key closes menu and updates state.

        Verifies ESC -> close -> state integration.
        """
        closed = []

        items = [MenuItem(label="Item", action="action")]
        menu = DropdownMenu(items=items)

        def on_close():
            closed.append(True)

        menu.close_callback = on_close

        # Press ESC
        menu.handle_key(Keys.ESCAPE)

        # Close callback should have been called
        assert len(closed) == 1
