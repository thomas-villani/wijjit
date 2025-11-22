"""Tests for TabbedPanel display element."""

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.display.tabbed_panel import TabbedPanel, TabPosition
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import Frame, FrameStyle
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestTabbedPanelCreation:
    """Tests for TabbedPanel element creation and initialization."""

    def test_create_empty_panel(self):
        """Test creating a tabbed panel with no tabs."""
        panel = TabbedPanel(id="settings")

        assert panel.id == "settings"
        assert panel.tabs == []
        assert panel.active_tab_index == 0
        assert panel.element_type == ElementType.DISPLAY
        assert panel.focusable

    def test_default_properties(self):
        """Test default tabbed panel properties."""
        panel = TabbedPanel()

        assert panel.width == 60
        assert panel.height == 20
        assert panel.tab_position == TabPosition.TOP
        assert panel.active_tab_index == 0
        assert panel.on_tab_change is None

    def test_custom_dimensions(self):
        """Test creating panel with custom dimensions."""
        panel = TabbedPanel(width=80, height=30)

        assert panel.width == 80
        assert panel.height == 30

    def test_tab_positions(self):
        """Test creating panels with different tab positions."""
        positions = [
            (TabPosition.TOP, "top"),
            (TabPosition.BOTTOM, "bottom"),
            (TabPosition.LEFT, "left"),
            (TabPosition.RIGHT, "right"),
        ]

        for position, name in positions:
            panel = TabbedPanel(tab_position=position)
            assert panel.tab_position == position, f"Failed for {name} position"

    def test_border_styles(self):
        """Test creating panels with different border styles."""
        from wijjit.layout.frames import BorderStyle

        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }

        for style_name, expected_style in border_map.items():
            panel = TabbedPanel(border_style=style_name)
            assert panel.border_style == expected_style

    def test_initial_active_tab(self):
        """Test creating panel with specific initial active tab."""
        panel = TabbedPanel(active_tab_index=2)

        assert panel.active_tab_index == 2

    def test_css_classes(self):
        """Test creating panel with CSS classes."""
        panel = TabbedPanel(classes="my-panel")

        assert "my-panel" in panel.classes


class TestTabbedPanelTabs:
    """Tests for tab management functionality."""

    def test_add_single_tab(self):
        """Test adding a single tab."""
        panel = TabbedPanel()
        frame = Frame(width=50, height=10)

        panel.add_tab("General", frame)

        assert len(panel.tabs) == 1
        assert panel.tabs[0][0] == "General"
        assert panel.tabs[0][1] == frame

    def test_add_multiple_tabs(self):
        """Test adding multiple tabs."""
        panel = TabbedPanel()

        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.add_tab("Tab 3", Frame(width=50, height=10))

        assert len(panel.tabs) == 3
        assert panel.tabs[0][0] == "Tab 1"
        assert panel.tabs[1][0] == "Tab 2"
        assert panel.tabs[2][0] == "Tab 3"

    def test_tab_with_content(self):
        """Test adding tab with frame content."""
        panel = TabbedPanel()
        frame = Frame(width=50, height=10)
        frame.set_content("Hello World")

        panel.add_tab("Content", frame)

        assert panel.tabs[0][1].content == ["Hello World"]


class TestTabbedPanelNavigation:
    """Tests for tab navigation functionality."""

    def test_switch_to_tab(self):
        """Test switching to a specific tab."""
        panel = TabbedPanel()
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.add_tab("Tab 3", Frame(width=50, height=10))

        panel.switch_to_tab(1)

        assert panel.active_tab_index == 1

    def test_switch_to_tab_callback(self):
        """Test callback when switching tabs."""
        panel = TabbedPanel()
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        callback_called = []

        def on_change(index, label):
            callback_called.append((index, label))

        panel.on_tab_change = on_change

        panel.switch_to_tab(1)

        assert callback_called == [(1, "Tab 2")]

    def test_switch_to_same_tab_no_callback(self):
        """Test that switching to same tab doesn't trigger callback."""
        panel = TabbedPanel()
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        callback_called = []

        def on_change(index, label):
            callback_called.append((index, label))

        panel.on_tab_change = on_change

        # Already at tab 0
        panel.switch_to_tab(0)

        assert callback_called == []

    def test_switch_clamps_negative_index(self):
        """Test that negative index is clamped to 0."""
        panel = TabbedPanel()
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        panel.switch_to_tab(-5)

        assert panel.active_tab_index == 0

    def test_switch_clamps_overflow_index(self):
        """Test that overflow index is clamped to last tab."""
        panel = TabbedPanel()
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        panel.switch_to_tab(100)

        assert panel.active_tab_index == 1

    def test_switch_empty_panel_no_error(self):
        """Test that switching on empty panel doesn't raise error."""
        panel = TabbedPanel()

        # Should not raise
        panel.switch_to_tab(0)
        panel.switch_to_tab(5)


class TestTabbedPanelKeyboardNavigation:
    """Tests for keyboard navigation."""

    def test_horizontal_left_key(self):
        """Test left arrow switches to previous tab (horizontal tabs)."""
        panel = TabbedPanel(tab_position=TabPosition.TOP)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.switch_to_tab(1)

        result = panel.handle_key(Keys.LEFT)

        assert result is True
        assert panel.active_tab_index == 0

    def test_horizontal_right_key(self):
        """Test right arrow switches to next tab (horizontal tabs)."""
        panel = TabbedPanel(tab_position=TabPosition.TOP)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        result = panel.handle_key(Keys.RIGHT)

        assert result is True
        assert panel.active_tab_index == 1

    def test_vertical_up_key(self):
        """Test up arrow switches to previous tab (vertical tabs)."""
        panel = TabbedPanel(tab_position=TabPosition.LEFT)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.switch_to_tab(1)

        result = panel.handle_key(Keys.UP)

        assert result is True
        assert panel.active_tab_index == 0

    def test_vertical_down_key(self):
        """Test down arrow switches to next tab (vertical tabs)."""
        panel = TabbedPanel(tab_position=TabPosition.LEFT)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        result = panel.handle_key(Keys.DOWN)

        assert result is True
        assert panel.active_tab_index == 1

    def test_horizontal_ignores_vertical_keys(self):
        """Test horizontal tabs ignore up/down for tab switching."""
        panel = TabbedPanel(tab_position=TabPosition.TOP)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        # Up/Down should not switch tabs in horizontal mode
        # (they delegate to frame for scrolling)
        initial_index = panel.active_tab_index
        panel.handle_key(Keys.UP)
        panel.handle_key(Keys.DOWN)

        assert panel.active_tab_index == initial_index

    def test_empty_panel_handles_keys(self):
        """Test that empty panel handles keys gracefully."""
        panel = TabbedPanel()

        result = panel.handle_key(Keys.LEFT)

        assert result is False


class TestTabbedPanelMouseNavigation:
    """Tests for mouse event handling."""

    def test_click_tab_horizontal(self):
        """Test clicking on a tab in horizontal mode."""
        panel = TabbedPanel(tab_position=TabPosition.TOP, width=60, height=20)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.bounds = Bounds(0, 0, 60, 20)

        # Click on second tab (approximate position)
        # Tab format: "[Tab 1]" = 7 chars, then separator, then " Tab 2 "
        event = MouseEvent(
            x=10,  # After first tab
            y=0,  # Top border line where tabs are
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )

        result = panel.handle_mouse(event)

        assert result is True
        assert panel.active_tab_index == 1

    def test_click_first_tab(self):
        """Test clicking on the first tab."""
        panel = TabbedPanel(tab_position=TabPosition.TOP, width=60, height=20)
        panel.add_tab("A", Frame(width=50, height=10))
        panel.add_tab("B", Frame(width=50, height=10))
        panel.switch_to_tab(1)  # Start on second tab
        panel.bounds = Bounds(0, 0, 60, 20)

        # Click on first tab (position 1-3 for "[A]")
        event = MouseEvent(
            x=2,
            y=0,
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )

        result = panel.handle_mouse(event)

        assert result is True
        assert panel.active_tab_index == 0

    def test_click_vertical_tab(self):
        """Test clicking on a tab in vertical mode."""
        panel = TabbedPanel(tab_position=TabPosition.LEFT, width=60, height=20)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.bounds = Bounds(0, 0, 60, 20)

        # Click on second tab (y=2, which is second row after top border)
        event = MouseEvent(
            x=2,  # In tab area
            y=2,  # Second tab row
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )

        result = panel.handle_mouse(event)

        assert result is True
        assert panel.active_tab_index == 1

    def test_click_outside_tabs_no_switch(self):
        """Test clicking outside tab area doesn't switch tabs."""
        panel = TabbedPanel(tab_position=TabPosition.TOP, width=60, height=20)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.bounds = Bounds(0, 0, 60, 20)

        # Click in content area (not on tabs)
        event = MouseEvent(
            x=30,
            y=10,  # Middle of content area
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )

        result = panel.handle_mouse(event)

        assert result is False
        assert panel.active_tab_index == 0

    def test_scroll_wheel_delegates_to_frame(self):
        """Test scroll wheel events are delegated to active frame."""
        panel = TabbedPanel(tab_position=TabPosition.TOP, width=60, height=20)
        frame = Frame(
            width=50,
            height=10,
            style=FrameStyle(scrollable=True, show_scrollbar=True),
        )
        frame.set_content("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        panel.add_tab("Tab 1", frame)
        panel.bounds = Bounds(0, 0, 60, 20)

        event = MouseEvent(
            x=30,
            y=10,
            button=MouseButton.SCROLL_DOWN,
            type=MouseEventType.SCROLL,
        )

        # Should not raise and should return True if frame handles scroll
        result = panel.handle_mouse(event)
        # Result depends on frame scroll handling

    def test_empty_panel_handles_mouse(self):
        """Test that empty panel handles mouse events gracefully."""
        panel = TabbedPanel()
        panel.bounds = Bounds(0, 0, 60, 20)

        event = MouseEvent(
            x=10,
            y=0,
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )

        result = panel.handle_mouse(event)

        assert result is False

    def test_no_bounds_handles_mouse(self):
        """Test that panel without bounds handles mouse gracefully."""
        panel = TabbedPanel()
        panel.add_tab("Tab 1", Frame(width=50, height=10))

        event = MouseEvent(
            x=10,
            y=0,
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )

        result = panel.handle_mouse(event)

        assert result is False


class TestTabbedPanelDimensions:
    """Tests for dimension calculations."""

    def test_horizontal_tab_dimensions(self):
        """Test dimension calculation for horizontal tabs."""
        panel = TabbedPanel(tab_position=TabPosition.TOP, width=60, height=20)
        panel.add_tab("Tab 1", Frame(width=50, height=10))

        tab_w, tab_h, content_w, content_h = panel._calculate_tab_dimensions()

        assert tab_w == 60  # Full width
        assert tab_h == 3  # Tab area height
        assert content_w == 60  # Full width
        assert content_h == 17  # height - tab_area

    def test_vertical_tab_dimensions(self):
        """Test dimension calculation for vertical tabs."""
        panel = TabbedPanel(tab_position=TabPosition.LEFT, width=60, height=20)
        panel.add_tab("Tab 1", Frame(width=50, height=10))

        tab_w, tab_h, content_w, content_h = panel._calculate_tab_dimensions()

        # Tab area width depends on label length + padding
        assert tab_w > 0
        assert tab_h == 20  # Full height
        assert content_w == 60 - tab_w
        assert content_h == 20

    def test_is_horizontal(self):
        """Test _is_horizontal helper."""
        horizontal_positions = [TabPosition.TOP, TabPosition.BOTTOM]
        vertical_positions = [TabPosition.LEFT, TabPosition.RIGHT]

        for pos in horizontal_positions:
            panel = TabbedPanel(tab_position=pos)
            assert panel._is_horizontal() is True

        for pos in vertical_positions:
            panel = TabbedPanel(tab_position=pos)
            assert panel._is_horizontal() is False

    def test_get_intrinsic_size(self):
        """Test intrinsic size returns configured dimensions."""
        panel = TabbedPanel(width=80, height=25)

        width, height = panel.get_intrinsic_size()

        assert width == 80
        assert height == 25


class TestTabbedPanelRendering:
    """Tests for rendering functionality."""

    def test_render_empty_panel(self):
        """Test rendering an empty panel."""
        panel = TabbedPanel(width=40, height=10)

        output = render_element(panel, width=40, height=10)

        assert "No tabs defined" in output

    def test_render_single_tab(self):
        """Test rendering panel with single tab."""
        panel = TabbedPanel(width=40, height=10)
        frame = Frame(width=36, height=6)
        frame.set_content("Content")
        panel.add_tab("Tab 1", frame)

        output = render_element(panel, width=40, height=10)

        assert "Tab 1" in output

    def test_render_multiple_tabs(self):
        """Test rendering panel with multiple tabs."""
        panel = TabbedPanel(width=50, height=10)
        panel.add_tab("First", Frame(width=46, height=6))
        panel.add_tab("Second", Frame(width=46, height=6))
        panel.add_tab("Third", Frame(width=46, height=6))

        output = render_element(panel, width=50, height=10)

        assert "First" in output
        assert "Second" in output
        assert "Third" in output

    def test_render_focused_state(self):
        """Test rendering in focused state applies styling."""
        panel = TabbedPanel(width=40, height=10)
        panel.add_tab("Tab 1", Frame(width=36, height=6))
        panel.focused = True

        # Should not raise
        output = render_element(panel, width=40, height=10)
        assert output  # Should produce some output


class TestTabbedPanelStatePersistence:
    """Tests for state persistence functionality."""

    def test_state_key_assignment(self):
        """Test active tab state key assignment."""
        panel = TabbedPanel(id="my_panel")
        panel.active_tab_state_key = "current_tab"

        assert panel.active_tab_state_key == "current_tab"

    def test_save_state_on_switch(self):
        """Test that state is saved when switching tabs."""
        panel = TabbedPanel(id="settings")
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))

        state_dict = {}
        panel._state_dict = state_dict
        panel.active_tab_state_key = "active_tab"

        panel.switch_to_tab(1)

        assert state_dict.get("active_tab") == 1

    def test_no_save_without_state_dict(self):
        """Test that no error occurs when state_dict is None."""
        panel = TabbedPanel(id="settings")
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.active_tab_state_key = "active_tab"

        # Should not raise when _state_dict is None
        panel.switch_to_tab(1)


class TestTabbedPanelChildElements:
    """Tests for child element collection functionality."""

    def test_get_focusable_children_empty(self):
        """Test getting focusable children from empty panel."""
        panel = TabbedPanel()

        children = panel.get_focusable_children()

        assert children == []

    def test_collect_child_elements_empty(self):
        """Test collecting child elements from empty panel."""
        panel = TabbedPanel()

        elements = panel.collect_child_elements()

        assert elements == []


class TestTabbedPanelAsyncMouse:
    """Tests for async mouse handling."""

    def test_async_mouse_delegates_to_sync(self):
        """Test async mouse handler delegates to sync version."""
        import asyncio

        panel = TabbedPanel(tab_position=TabPosition.TOP, width=60, height=20)
        panel.add_tab("Tab 1", Frame(width=50, height=10))
        panel.add_tab("Tab 2", Frame(width=50, height=10))
        panel.bounds = Bounds(0, 0, 60, 20)

        event = MouseEvent(
            x=10,
            y=0,
            button=MouseButton.LEFT,
            type=MouseEventType.CLICK,
        )

        async def test():
            return await panel.handle_mouse_async(event)

        # Use asyncio.run() for Python 3.10+ compatibility
        result = asyncio.run(test())

        # Should have switched tabs via sync handler
        assert panel.active_tab_index == 1
