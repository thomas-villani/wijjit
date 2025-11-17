"""Tests for Menu elements."""

from unittest.mock import Mock

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.menu import ContextMenu, DropdownMenu, MenuElement, MenuItem
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import BorderStyle
from wijjit.terminal.ansi import visible_length
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestMenuItem:
    """Tests for MenuItem dataclass."""

    def test_create_menu_item(self):
        """Test creating a basic menu item."""
        item = MenuItem(label="New File")
        assert item.label == "New File"
        assert item.action is None
        assert item.key is None
        assert item.divider is False
        assert item.disabled is False

    def test_create_item_with_action(self):
        """Test creating menu item with action."""
        item = MenuItem(label="Save", action="save_file")
        assert item.label == "Save"
        assert item.action == "save_file"

    def test_create_item_with_shortcut(self):
        """Test creating menu item with keyboard shortcut."""
        item = MenuItem(label="Copy", action="copy", key="Ctrl+C")
        assert item.label == "Copy"
        assert item.key == "Ctrl+C"

    def test_create_divider(self):
        """Test creating a divider menu item."""
        item = MenuItem(label="", divider=True)
        assert item.divider is True

    def test_create_disabled_item(self):
        """Test creating a disabled menu item."""
        item = MenuItem(label="Undo", action="undo", disabled=True)
        assert item.disabled is True

    def test_item_with_all_parameters(self):
        """Test creating menu item with all parameters."""
        item = MenuItem(
            label="Paste", action="paste", key="Ctrl+V", divider=False, disabled=False
        )
        assert item.label == "Paste"
        assert item.action == "paste"
        assert item.key == "Ctrl+V"
        assert item.divider is False
        assert item.disabled is False


class TestMenuElement:
    """Tests for MenuElement base class."""

    def test_create_menu(self):
        """Test creating a menu element."""
        items = [MenuItem(label="Item 1", action="action1")]
        menu = MenuElement(id="test_menu", items=items, width=30)
        assert menu.id == "test_menu"
        assert len(menu.items) == 1
        assert menu.width == 30
        assert menu.focusable is True
        assert menu.element_type == ElementType.SELECTABLE

    def test_create_empty_menu(self):
        """Test creating menu with no items."""
        menu = MenuElement(items=[])
        assert len(menu.items) == 0
        assert menu.highlighted_index == -1

    def test_border_style_single(self):
        """Test menu with single border style."""
        menu = MenuElement(items=[], border_style=BorderStyle.SINGLE)
        assert menu.border_style == BorderStyle.SINGLE

    def test_border_style_string(self):
        """Test menu with border style as string."""
        menu = MenuElement(items=[], border_style="double")
        assert menu.border_style == BorderStyle.DOUBLE

    def test_border_style_rounded(self):
        """Test menu with rounded border style."""
        menu = MenuElement(items=[], border_style="rounded")
        assert menu.border_style == BorderStyle.ROUNDED

    def test_initial_highlighted_index(self):
        """Test initial highlight is on first enabled item."""
        items = [
            MenuItem(label="Item 1", action="a1", disabled=True),
            MenuItem(label="Item 2", action="a2"),
            MenuItem(label="Item 3", action="a3"),
        ]
        menu = MenuElement(items=items)
        assert menu.highlighted_index == 1

    def test_initial_highlight_skips_divider(self):
        """Test initial highlight skips divider items."""
        items = [
            MenuItem(label="", divider=True),
            MenuItem(label="Item 1", action="a1"),
        ]
        menu = MenuElement(items=items)
        assert menu.highlighted_index == 1

    def test_all_items_disabled(self):
        """Test menu where all items are disabled."""
        items = [
            MenuItem(label="Item 1", disabled=True),
            MenuItem(label="Item 2", disabled=True),
        ]
        menu = MenuElement(items=items)
        assert menu.highlighted_index == -1

    def test_down_arrow_navigation(self):
        """Test down arrow moves highlight."""
        items = [MenuItem(label=f"Item {i}", action=f"a{i}") for i in range(3)]
        menu = MenuElement(items=items)
        assert menu.highlighted_index == 0

        result = menu.handle_key(Keys.DOWN)
        assert result is True
        assert menu.highlighted_index == 1

        result = menu.handle_key(Keys.DOWN)
        assert result is True
        assert menu.highlighted_index == 2

    def test_up_arrow_navigation(self):
        """Test up arrow moves highlight up."""
        items = [MenuItem(label=f"Item {i}", action=f"a{i}") for i in range(3)]
        menu = MenuElement(items=items)
        menu.highlighted_index = 2

        result = menu.handle_key(Keys.UP)
        assert result is True
        assert menu.highlighted_index == 1

        result = menu.handle_key(Keys.UP)
        assert result is True
        assert menu.highlighted_index == 0

    def test_navigation_boundaries(self):
        """Test navigation respects boundaries."""
        items = [MenuItem(label=f"Item {i}", action=f"a{i}") for i in range(3)]
        menu = MenuElement(items=items)
        menu.highlighted_index = 0

        # Going up from first stays at first (no wrap)
        result = menu.handle_key(Keys.UP)
        assert result is True
        assert menu.highlighted_index == 0

        # Going down from last stays at last (no wrap)
        menu.highlighted_index = 2
        result = menu.handle_key(Keys.DOWN)
        assert result is True
        assert menu.highlighted_index == 2

    def test_navigation_skips_disabled_items(self):
        """Test navigation skips disabled items."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2", disabled=True),
            MenuItem(label="Item 3", action="a3"),
        ]
        menu = MenuElement(items=items)
        menu.highlighted_index = 0

        result = menu.handle_key(Keys.DOWN)
        assert result is True
        assert menu.highlighted_index == 2

    def test_navigation_skips_dividers(self):
        """Test navigation skips divider items."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="", divider=True),
            MenuItem(label="Item 2", action="a2"),
        ]
        menu = MenuElement(items=items)
        menu.highlighted_index = 0

        result = menu.handle_key(Keys.DOWN)
        assert result is True
        assert menu.highlighted_index == 2

    def test_home_key_jumps_to_first(self):
        """Test HOME key jumps to first enabled item."""
        items = [MenuItem(label=f"Item {i}", action=f"a{i}") for i in range(5)]
        menu = MenuElement(items=items)
        menu.highlighted_index = 3

        result = menu.handle_key(Keys.HOME)
        assert result is True
        assert menu.highlighted_index == 0

    def test_end_key_jumps_to_last(self):
        """Test END key jumps to last enabled item."""
        items = [MenuItem(label=f"Item {i}", action=f"a{i}") for i in range(5)]
        menu = MenuElement(items=items)
        menu.highlighted_index = 0

        result = menu.handle_key(Keys.END)
        assert result is True
        assert menu.highlighted_index == 4

    def test_end_key_skips_disabled(self):
        """Test END key skips disabled items at end."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2"),
            MenuItem(label="Item 3", action="a3", disabled=True),
        ]
        menu = MenuElement(items=items)
        menu.highlighted_index = 0

        result = menu.handle_key(Keys.END)
        assert result is True
        assert menu.highlighted_index == 1

    def test_enter_selects_item(self):
        """Test ENTER key selects highlighted item."""
        item = MenuItem(label="Test", action="test_action")
        menu = MenuElement(items=[item])
        callback = Mock()
        menu.on_item_select = callback

        result = menu.handle_key(Keys.ENTER)
        assert result is True
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "test_action"
        assert args[1] == item

    def test_enter_on_disabled_item_no_select(self):
        """Test ENTER on disabled item does not select."""
        item = MenuItem(label="Test", action="test_action", disabled=True)
        menu = MenuElement(items=[item])
        callback = Mock()
        menu.on_item_select = callback

        result = menu.handle_key(Keys.ENTER)
        assert result is True
        callback.assert_not_called()

    def test_enter_on_divider_no_select(self):
        """Test ENTER on divider does not select."""
        items = [
            MenuItem(label="", divider=True),
            MenuItem(label="Item", action="action"),
        ]
        menu = MenuElement(items=items)
        menu.highlighted_index = 0
        callback = Mock()
        menu.on_item_select = callback

        result = menu.handle_key(Keys.ENTER)
        assert result is True
        callback.assert_not_called()

    def test_selection_triggers_close_callback(self):
        """Test selection triggers close callback."""
        item = MenuItem(label="Test", action="test_action")
        menu = MenuElement(items=[item])
        close_callback = Mock()
        menu.close_callback = close_callback

        menu.handle_key(Keys.ENTER)
        close_callback.assert_called_once()

    def test_escape_closes_menu(self):
        """Test ESC key closes menu."""
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items)
        close_callback = Mock()
        menu.close_callback = close_callback

        result = menu.handle_key(Keys.ESCAPE)
        assert result is True
        close_callback.assert_called_once()

    def test_empty_menu_keyboard_not_handled(self):
        """Test keyboard input on empty menu returns False."""
        menu = MenuElement(items=[])
        result = menu.handle_key(Keys.DOWN)
        assert result is False

    def test_mouse_hover_highlights(self):
        """Test mouse hover updates highlighted_index."""
        items = [MenuItem(label=f"Item {i}", action=f"a{i}") for i in range(3)]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=10, y=5, width=22, height=5)

        # Hover over second item (y=7: border at 5, item 0 at 6, item 1 at 7)
        event = MouseEvent(type=MouseEventType.MOVE, button=MouseButton.NONE, x=15, y=7)
        result = menu.handle_mouse(event)
        assert result is True
        assert menu.highlighted_index == 1

    def test_mouse_click_selects_item(self):
        """Test mouse click selects item."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2"),
        ]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=10, y=5, width=22, height=4)
        callback = Mock()
        menu.on_item_select = callback

        # Click on first item (border at y=5, first item at y=6)
        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.LEFT, x=15, y=6
        )
        result = menu.handle_mouse(event)
        assert result is True
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "a1"

    def test_mouse_double_click_selects_item(self):
        """Test mouse double-click selects item."""
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=3)
        callback = Mock()
        menu.on_item_select = callback

        event = MouseEvent(
            type=MouseEventType.DOUBLE_CLICK, button=MouseButton.LEFT, x=5, y=1
        )
        result = menu.handle_mouse(event)
        assert result is True
        callback.assert_called_once()

    def test_mouse_on_disabled_item_no_highlight(self):
        """Test mouse hover on disabled item does not highlight."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2", disabled=True),
        ]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=4)
        menu.highlighted_index = 0

        # Hover over disabled item
        event = MouseEvent(type=MouseEventType.MOVE, button=MouseButton.NONE, x=5, y=2)
        result = menu.handle_mouse(event)
        assert result is True
        # Highlighted index should not change
        assert menu.highlighted_index == 0

    def test_mouse_on_divider_no_highlight(self):
        """Test mouse hover on divider does not highlight."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="", divider=True),
        ]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=4)
        menu.highlighted_index = 0

        # Hover over divider
        event = MouseEvent(type=MouseEventType.MOVE, button=MouseButton.NONE, x=5, y=2)
        result = menu.handle_mouse(event)
        assert result is True
        assert menu.highlighted_index == 0

    def test_mouse_click_on_disabled_no_select(self):
        """Test mouse click on disabled item does not select."""
        items = [MenuItem(label="Item", action="action", disabled=True)]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=3)
        callback = Mock()
        menu.on_item_select = callback

        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=1)
        result = menu.handle_mouse(event)
        assert result is True
        callback.assert_not_called()

    def test_mouse_outside_bounds_not_handled(self):
        """Test mouse event outside menu bounds is not handled."""
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=10, y=5, width=22, height=3)

        # Click outside bounds
        event = MouseEvent(
            type=MouseEventType.CLICK, button=MouseButton.LEFT, x=50, y=50
        )
        result = menu.handle_mouse(event)
        assert result is False

    def test_mouse_no_bounds_returns_false(self):
        """Test mouse event when menu has no bounds returns False."""
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items)
        # Don't set bounds
        event = MouseEvent(type=MouseEventType.CLICK, button=MouseButton.LEFT, x=5, y=5)
        result = menu.handle_mouse(event)
        assert result is False

    def test_render_basic_menu(self):
        """Test rendering basic menu."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2"),
        ]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=4)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        assert "Item 1" in output
        assert "Item 2" in output
        assert "\n" in output
        # Cell-based rendering stores styling in Cell objects, not ANSI codes

    def test_render_with_shortcut(self):
        """Test rendering menu item with keyboard shortcut."""
        items = [MenuItem(label="Copy", action="copy", key="Ctrl+C")]
        menu = MenuElement(items=items, width=30)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        assert "Copy" in output
        assert "Ctrl+C" in output

    def test_render_highlighted_item(self):
        """Test rendering highlighted menu item."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="Item 2", action="a2"),
        ]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=4)
        menu.on_focus()
        menu.highlighted_index = 0

        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )
        # Cell-based rendering stores styling in Cell objects, not ANSI codes
        # Verify the item content is present
        assert "Item 1" in output

    def test_render_disabled_item(self):
        """Test rendering disabled menu item."""
        items = [MenuItem(label="Undo", action="undo", disabled=True)]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=3)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        assert "Undo" in output
        # Cell-based rendering stores styling in Cell objects, not ANSI codes

    def test_render_divider(self):
        """Test rendering divider item."""
        items = [
            MenuItem(label="Item 1", action="a1"),
            MenuItem(label="", divider=True),
            MenuItem(label="Item 2", action="a2"),
        ]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=5)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        # Should contain horizontal line characters
        from wijjit.layout.frames import BORDER_CHARS

        chars = BORDER_CHARS[BorderStyle.SINGLE]
        assert chars["h"] in output

    def test_render_focused_border(self):
        """Test rendering menu with focused border."""
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items, width=20)
        menu.bounds = Bounds(x=0, y=0, width=22, height=3)
        menu.on_focus()
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        # Cell-based rendering stores styling in Cell objects, not ANSI codes
        # Verify the item content is present
        assert "Item" in output

    def test_render_no_bounds_returns_empty(self):
        """Test rendering menu without bounds set initially.

        Note: render_element helper provides bounds, so menu will render.
        This test verifies the menu initializes without bounds but can render when provided.
        """
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items)
        # Menu has no bounds set initially
        assert menu.bounds is None
        # But render_element provides infrastructure to render
        output = render_element(menu, width=30, height=5)
        # Menu should render successfully with provided dimensions
        assert "Item" in output

    def test_render_width_clipping(self):
        """Test rendering clips long labels to fit width."""
        items = [MenuItem(label="This is a very long menu item label", action="a1")]
        menu = MenuElement(items=items, width=15)
        menu.bounds = Bounds(x=0, y=0, width=17, height=3)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        # Label should be clipped
        assert "..." in output

    def test_render_width_padding(self):
        """Test rendering pads short labels to width."""
        items = [MenuItem(label="Short", action="a1")]
        menu = MenuElement(items=items, width=30)
        menu.bounds = Bounds(x=0, y=0, width=32, height=3)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        lines = output.split("\n")
        # Check that item line has correct visible width
        # (width + 2 for borders)
        item_line = lines[1]
        assert visible_length(item_line) == 32

    def test_render_double_border(self):
        """Test rendering with double border style."""
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items, width=20, border_style=BorderStyle.DOUBLE)
        menu.bounds = Bounds(x=0, y=0, width=22, height=3)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        from wijjit.layout.frames import BORDER_CHARS

        chars = BORDER_CHARS[BorderStyle.DOUBLE]
        # Should contain double border characters
        assert chars["tl"] in output or chars["h"] in output

    def test_render_rounded_border(self):
        """Test rendering with rounded border style."""
        items = [MenuItem(label="Item", action="action")]
        menu = MenuElement(items=items, width=20, border_style="rounded")
        menu.bounds = Bounds(x=0, y=0, width=22, height=3)
        output = render_element(
            menu, width=menu.bounds.width, height=menu.bounds.height
        )

        from wijjit.layout.frames import BORDER_CHARS

        chars = BORDER_CHARS[BorderStyle.ROUNDED]
        # Should contain rounded border characters
        assert chars["tl"] in output or chars["h"] in output

    def test_item_select_without_action(self):
        """Test selecting item without action does not call callback."""
        item = MenuItem(label="Label Only")
        menu = MenuElement(items=[item])
        callback = Mock()
        menu.on_item_select = callback

        menu.handle_key(Keys.ENTER)
        # Should not call callback if item has no action
        callback.assert_not_called()

    def test_close_callback_on_selection(self):
        """Test close callback is called after item selection."""
        item = MenuItem(label="Item", action="action")
        menu = MenuElement(items=[item])
        close_callback = Mock()
        menu.close_callback = close_callback

        menu._select_item(item)
        close_callback.assert_called_once()


class TestDropdownMenu:
    """Tests for DropdownMenu element."""

    def test_create_dropdown(self):
        """Test creating a dropdown menu."""
        items = [MenuItem(label="New", action="new")]
        dropdown = DropdownMenu(id="file_menu", items=items, trigger_text="File")
        assert dropdown.id == "file_menu"
        assert dropdown.trigger_text == "File"
        assert len(dropdown.items) == 1

    def test_default_trigger_text(self):
        """Test dropdown with default trigger text."""
        dropdown = DropdownMenu(items=[])
        assert dropdown.trigger_text == "Menu"

    def test_trigger_key(self):
        """Test dropdown with trigger keyboard shortcut."""
        dropdown = DropdownMenu(items=[], trigger_key="Alt+F")
        assert dropdown.trigger_key == "Alt+F"

    def test_trigger_bounds_attribute(self):
        """Test dropdown has trigger_bounds attribute."""
        dropdown = DropdownMenu(items=[])
        assert hasattr(dropdown, "trigger_bounds")
        assert dropdown.trigger_bounds is None

    def test_trigger_bounds_assignment(self):
        """Test setting trigger bounds."""
        dropdown = DropdownMenu(items=[])
        bounds = Bounds(x=5, y=10, width=10, height=1)
        dropdown.trigger_bounds = bounds
        assert dropdown.trigger_bounds == bounds

    def test_dropdown_inherits_menu_behavior(self):
        """Test dropdown inherits menu element behavior."""
        items = [MenuItem(label="Item", action="action")]
        dropdown = DropdownMenu(items=items)
        dropdown.bounds = Bounds(x=0, y=0, width=32, height=3)

        # Should be able to navigate
        result = dropdown.handle_key(Keys.DOWN)
        assert result is True

        # Should be able to render
        output = render_element(
            dropdown, width=dropdown.bounds.width, height=dropdown.bounds.height
        )
        assert "Item" in output

    def test_dropdown_not_centered(self):
        """Test dropdown menu is not centered by default."""
        dropdown = DropdownMenu(items=[])
        # centered should be False for dropdowns
        assert dropdown.centered is False

    def test_dropdown_custom_width(self):
        """Test dropdown with custom width."""
        dropdown = DropdownMenu(items=[], width=40)
        assert dropdown.width == 40


class TestContextMenu:
    """Tests for ContextMenu element."""

    def test_create_context_menu(self):
        """Test creating a context menu."""
        items = [MenuItem(label="Open", action="open")]
        context = ContextMenu(id="ctx_menu", items=items)
        assert context.id == "ctx_menu"
        assert len(context.items) == 1

    def test_target_element_id(self):
        """Test context menu with target element ID."""
        context = ContextMenu(items=[], target_element_id="file_list")
        assert context.target_element_id == "file_list"

    def test_mouse_position_attribute(self):
        """Test context menu has mouse_position attribute."""
        context = ContextMenu(items=[])
        assert hasattr(context, "mouse_position")
        assert context.mouse_position is None

    def test_mouse_position_assignment(self):
        """Test setting mouse position."""
        context = ContextMenu(items=[])
        context.mouse_position = (15, 20)
        assert context.mouse_position == (15, 20)

    def test_context_inherits_menu_behavior(self):
        """Test context menu inherits menu element behavior."""
        items = [MenuItem(label="Delete", action="delete")]
        context = ContextMenu(items=items)
        context.bounds = Bounds(x=0, y=0, width=32, height=3)

        # Should be able to select
        callback = Mock()
        context.on_item_select = callback
        result = context.handle_key(Keys.ENTER)
        assert result is True
        callback.assert_called_once()

        # Should be able to render
        output = render_element(
            context, width=context.bounds.width, height=context.bounds.height
        )
        assert "Delete" in output

    def test_context_not_centered(self):
        """Test context menu is not centered by default."""
        context = ContextMenu(items=[])
        # centered should be False for context menus
        assert context.centered is False

    def test_context_custom_border_style(self):
        """Test context menu with custom border style."""
        context = ContextMenu(items=[], border_style="double")
        assert context.border_style == BorderStyle.DOUBLE
