"""Unit tests for menu template tags.

Tests verify that menu template tags (menuitem, dropdown, contextmenu)
properly create menu elements and overlay_info structures.
"""

from wijjit.core.app import Wijjit
from wijjit.core.overlay import LayerType
from wijjit.elements.menu import ContextMenu, DropdownMenu


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
    # Prepare render context with state
    data = {"state": app.state}

    # Set up global context for template extensions (needed for visibility checks)
    app.renderer.add_global("_wijjit_current_context", data)

    # Render with layout engine and overlay_manager
    output, elements, layout_ctx = app.renderer.render_with_layout(
        template,
        context=data,
        width=width,
        height=height,
        overlay_manager=app.overlay_manager,
    )

    # Process template-declared overlays (mimic app._render behavior)
    app._sync_template_overlays(layout_ctx)

    # Clean up globals
    app.renderer.add_global("_wijjit_current_context", None)

    return output, elements


class TestMenuitemTag:
    """Tests for {% menuitem %} tag."""

    def test_menuitem_with_action(self):
        """Test menuitem tag with action attribute."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new_file" %}New File{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Verify dropdown was created with menuitem
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert isinstance(dropdown, DropdownMenu)
        assert len(dropdown.items) == 1
        assert dropdown.items[0].label == "New File"
        assert dropdown.items[0].action == "new_file"

    def test_menuitem_with_keyboard_shortcut(self):
        """Test menuitem tag with keyboard shortcut."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Edit" visible="show_menu" %}
                {% menuitem action="copy" key="Ctrl+C" %}Copy{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert len(dropdown.items) == 1
        assert dropdown.items[0].label == "Copy"
        assert dropdown.items[0].action == "copy"
        assert dropdown.items[0].key == "Ctrl+C"

    def test_menuitem_divider(self):
        """Test menuitem tag as divider."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Menu" visible="show_menu" %}
                {% menuitem action="item1" %}Item 1{% endmenuitem %}
                {% menuitem divider=true %}{% endmenuitem %}
                {% menuitem action="item2" %}Item 2{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert len(dropdown.items) == 3
        assert dropdown.items[0].label == "Item 1"
        assert dropdown.items[1].divider is True
        assert dropdown.items[1].label == ""
        assert dropdown.items[2].label == "Item 2"

    def test_menuitem_disabled(self):
        """Test menuitem tag with disabled attribute."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Menu" visible="show_menu" %}
                {% menuitem action="undo" disabled=true %}Undo{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert len(dropdown.items) == 1
        assert dropdown.items[0].label == "Undo"
        assert dropdown.items[0].disabled is True

    def test_multiple_menuitems(self):
        """Test multiple menuitem tags in a menu."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new" key="Ctrl+N" %}New{% endmenuitem %}
                {% menuitem action="open" key="Ctrl+O" %}Open{% endmenuitem %}
                {% menuitem action="save" key="Ctrl+S" %}Save{% endmenuitem %}
                {% menuitem divider=true %}{% endmenuitem %}
                {% menuitem action="quit" key="Ctrl+Q" %}Quit{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert len(dropdown.items) == 5
        assert dropdown.items[0].label == "New"
        assert dropdown.items[1].label == "Open"
        assert dropdown.items[2].label == "Save"
        assert dropdown.items[3].divider is True
        assert dropdown.items[4].label == "Quit"


class TestDropdownTag:
    """Tests for {% dropdown %} tag."""

    def test_dropdown_basic(self):
        """Test basic dropdown tag."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Menu" visible="show_menu" %}
                {% menuitem action="action1" %}Item 1{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Verify dropdown overlay was created
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.DROPDOWN
        assert isinstance(overlay.element, DropdownMenu)
        assert overlay.close_on_escape is True
        assert overlay.close_on_click_outside is True
        assert overlay.trap_focus is True
        assert overlay.dimmed_background is False

    def test_dropdown_trigger_text(self):
        """Test dropdown tag with custom trigger text."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert dropdown.trigger_text == "File"

    def test_dropdown_trigger_key(self):
        """Test dropdown tag with trigger keyboard shortcut."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" key="Alt+F" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert dropdown.trigger_key == "Alt+F"

    def test_dropdown_custom_width(self):
        """Test dropdown tag with custom width."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Menu" width=40 visible="show_menu" %}
                {% menuitem action="item" %}Item{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert dropdown.width == 40

    def test_dropdown_border_style(self):
        """Test dropdown tag with custom border style."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Menu" border_style="double" visible="show_menu" %}
                {% menuitem action="item" %}Item{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        from wijjit.layout.frames import BorderStyle

        assert dropdown.border_style == BorderStyle.DOUBLE

    def test_dropdown_respects_visibility(self):
        """Test dropdown visibility is controlled by state."""
        app = Wijjit()
        app.state.show_menu = False

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Dropdown should not be in overlay_manager when visible=False
        assert len(app.overlay_manager.overlays) == 0

    def test_dropdown_visibility_toggle(self):
        """Test dropdown can be toggled via state."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        # First render - visible
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1

        # Second render - hidden
        app.state.show_menu = False
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 0

        # Third render - visible again
        app.state.show_menu = True
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1

    def test_dropdown_auto_id_generation(self):
        """Test dropdown generates ID when not provided."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        # Should have auto-generated ID
        assert dropdown.id is not None
        assert "dropdown" in dropdown.id

    def test_dropdown_custom_id(self):
        """Test dropdown with custom ID."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown id="file_menu" trigger="File" visible="show_menu" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert dropdown.id == "file_menu"

    def test_dropdown_empty_items(self):
        """Test dropdown with no menu items."""
        app = Wijjit()
        app.state.show_menu = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown trigger="Empty" visible="show_menu" %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        dropdown = overlay.element
        assert len(dropdown.items) == 0


class TestContextmenuTag:
    """Tests for {% contextmenu %} tag."""

    def test_contextmenu_basic(self):
        """Test basic context menu tag."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="file_list" visible="show_context" %}
                {% menuitem action="open" %}Open{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Verify context menu overlay was created
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.DROPDOWN
        assert isinstance(overlay.element, ContextMenu)
        assert overlay.close_on_escape is True
        assert overlay.close_on_click_outside is True
        assert overlay.trap_focus is True
        assert overlay.dimmed_background is False

    def test_contextmenu_target_element(self):
        """Test context menu with target element ID."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="my_list" visible="show_context" %}
                {% menuitem action="delete" %}Delete{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        context = overlay.element
        assert context.target_element_id == "my_list"

    def test_contextmenu_custom_width(self):
        """Test context menu with custom width."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="list" width=35 visible="show_context" %}
                {% menuitem action="item" %}Item{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        context = overlay.element
        assert context.width == 35

    def test_contextmenu_border_style(self):
        """Test context menu with custom border style."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="list" border_style="rounded" visible="show_context" %}
                {% menuitem action="item" %}Item{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        context = overlay.element
        from wijjit.layout.frames import BorderStyle

        assert context.border_style == BorderStyle.ROUNDED

    def test_contextmenu_respects_visibility(self):
        """Test context menu visibility is controlled by state."""
        app = Wijjit()
        app.state.show_context = False

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="list" visible="show_context" %}
                {% menuitem action="open" %}Open{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Context menu should not be in overlay_manager when visible=False
        assert len(app.overlay_manager.overlays) == 0

    def test_contextmenu_visibility_toggle(self):
        """Test context menu can be toggled via state."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="list" visible="show_context" %}
                {% menuitem action="open" %}Open{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        # First render - visible
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1

        # Second render - hidden
        app.state.show_context = False
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 0

        # Third render - visible again
        app.state.show_context = True
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1

    def test_contextmenu_auto_id_generation(self):
        """Test context menu generates ID when not provided."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="list" visible="show_context" %}
                {% menuitem action="open" %}Open{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        context = overlay.element
        # Should have auto-generated ID
        assert context.id is not None
        assert "contextmenu" in context.id

    def test_contextmenu_custom_id(self):
        """Test context menu with custom ID."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu id="ctx_menu" target="list" visible="show_context" %}
                {% menuitem action="open" %}Open{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        context = overlay.element
        assert context.id == "ctx_menu"

    def test_contextmenu_with_multiple_items(self):
        """Test context menu with multiple menu items."""
        app = Wijjit()
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% contextmenu target="list" visible="show_context" %}
                {% menuitem action="open" %}Open{% endmenuitem %}
                {% menuitem action="rename" %}Rename{% endmenuitem %}
                {% menuitem divider=true %}{% endmenuitem %}
                {% menuitem action="delete" %}Delete{% endmenuitem %}
                {% menuitem action="properties" %}Properties{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        overlay = app.overlay_manager.overlays[0]
        context = overlay.element
        assert len(context.items) == 5
        assert context.items[0].label == "Open"
        assert context.items[1].label == "Rename"
        assert context.items[2].divider is True
        assert context.items[3].label == "Delete"
        assert context.items[4].label == "Properties"


class TestMultipleMenus:
    """Tests for multiple menus in same template."""

    def test_multiple_dropdowns(self):
        """Test multiple dropdown menus in one template."""
        app = Wijjit()
        app.state.show_file = True
        app.state.show_edit = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown id="file_menu" trigger="File" visible="show_file" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
            {% dropdown id="edit_menu" trigger="Edit" visible="show_edit" %}
                {% menuitem action="copy" %}Copy{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        assert len(app.overlay_manager.overlays) == 2
        assert app.overlay_manager.overlays[0].element.id == "file_menu"
        assert app.overlay_manager.overlays[1].element.id == "edit_menu"

    def test_dropdown_and_contextmenu(self):
        """Test dropdown and context menu in same template."""
        app = Wijjit()
        app.state.show_dropdown = True
        app.state.show_context = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown id="menu" trigger="Menu" visible="show_dropdown" %}
                {% menuitem action="item1" %}Item 1{% endmenuitem %}
            {% enddropdown %}
            {% contextmenu id="ctx" target="list" visible="show_context" %}
                {% menuitem action="item2" %}Item 2{% endmenuitem %}
            {% endcontextmenu %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        assert len(app.overlay_manager.overlays) == 2
        assert isinstance(app.overlay_manager.overlays[0].element, DropdownMenu)
        assert isinstance(app.overlay_manager.overlays[1].element, ContextMenu)

    def test_selective_visibility(self):
        """Test showing only some menus based on state."""
        app = Wijjit()
        app.state.show_file = True
        app.state.show_edit = False
        app.state.show_view = True

        template = """
        {% frame width="80" height="24" %}
            {% dropdown id="file" trigger="File" visible="show_file" %}
                {% menuitem action="new" %}New{% endmenuitem %}
            {% enddropdown %}
            {% dropdown id="edit" trigger="Edit" visible="show_edit" %}
                {% menuitem action="copy" %}Copy{% endmenuitem %}
            {% enddropdown %}
            {% dropdown id="view" trigger="View" visible="show_view" %}
                {% menuitem action="zoom" %}Zoom{% endmenuitem %}
            {% enddropdown %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Only file and view should be visible
        assert len(app.overlay_manager.overlays) == 2
        ids = [overlay.element.id for overlay in app.overlay_manager.overlays]
        assert "file" in ids
        assert "view" in ids
        assert "edit" not in ids
