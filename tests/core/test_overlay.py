"""Tests for overlay management system."""

import pytest

from wijjit.core.overlay import LayerType, Overlay, OverlayManager
from wijjit.layout.bounds import Bounds


class MockElement:
    """Mock element for testing."""

    def __init__(self, id=None, x=0, y=0, width=10, height=5):
        self.id = id
        self.focusable = False
        self.bounds = Bounds(x=x, y=y, width=width, height=height)

    def render(self):
        return "MockElement"


class MockApp:
    """Mock app for testing OverlayManager."""

    def __init__(self):
        self.needs_render = False
        self.focus_manager = MockFocusManager()


class MockFocusManager:
    """Mock focus manager for testing."""

    def __init__(self):
        self.focused_element = None
        self.elements = []

    def get_focused_element(self):
        return self.focused_element

    def focus_element(self, element):
        self.focused_element = element
        return True

    def set_elements(self, elements):
        self.elements = elements

    def focus_first(self):
        if self.elements:
            self.focused_element = self.elements[0]

    def save_state(self):
        return (list(self.elements), 0 if self.focused_element else None)

    def restore_state(self, state):
        elements, index = state
        self.elements = elements
        if index is not None and index < len(elements):
            self.focused_element = elements[index]


class TestLayerType:
    """Tests for LayerType enum."""

    def test_layer_base_values(self):
        """Test that layer types have correct base z-index values."""
        assert LayerType.BASE == 0
        assert LayerType.MODAL == 100
        assert LayerType.DROPDOWN == 200
        assert LayerType.TOOLTIP == 300

    def test_layer_ordering(self):
        """Test that layers are ordered correctly."""
        assert LayerType.BASE < LayerType.MODAL
        assert LayerType.MODAL < LayerType.DROPDOWN
        assert LayerType.DROPDOWN < LayerType.TOOLTIP


class TestOverlayManager:
    """Tests for OverlayManager."""

    @pytest.fixture
    def app(self):
        """Create a mock app."""
        return MockApp()

    @pytest.fixture
    def manager(self, app):
        """Create an OverlayManager."""
        return OverlayManager(app)

    def test_init(self, manager, app):
        """Test OverlayManager initialization."""
        assert manager.app is app
        assert manager.overlays == []
        assert LayerType.MODAL in manager._next_z_index
        assert LayerType.DROPDOWN in manager._next_z_index
        assert LayerType.TOOLTIP in manager._next_z_index

    def test_push_modal(self, manager):
        """Test pushing a modal overlay."""
        element = MockElement(id="modal1")

        overlay = manager.push(element, LayerType.MODAL)

        assert overlay.element is element
        assert overlay.layer_type == LayerType.MODAL
        assert overlay.z_index == 100  # First modal
        assert overlay in manager.overlays
        assert manager.app.needs_render is True

    def test_push_multiple_modals(self, manager):
        """Test pushing multiple modals increments z-index."""
        modal1 = manager.push(MockElement(id="m1"), LayerType.MODAL)
        modal2 = manager.push(MockElement(id="m2"), LayerType.MODAL)
        modal3 = manager.push(MockElement(id="m3"), LayerType.MODAL)

        assert modal1.z_index == 100
        assert modal2.z_index == 101
        assert modal3.z_index == 102
        assert len(manager.overlays) == 3

    def test_overlays_sorted_by_z_index(self, manager):
        """Test that overlays are kept sorted by z-index."""
        modal = manager.push(MockElement(id="modal"), LayerType.MODAL)
        tooltip = manager.push(MockElement(id="tooltip"), LayerType.TOOLTIP)
        dropdown = manager.push(MockElement(id="dropdown"), LayerType.DROPDOWN)

        # Should be sorted: modal(100), dropdown(200), tooltip(300)
        assert manager.overlays[0].z_index == 100
        assert manager.overlays[1].z_index == 200
        assert manager.overlays[2].z_index == 300

    def test_pop_topmost(self, manager):
        """Test popping the topmost overlay."""
        modal1 = manager.push(MockElement(), LayerType.MODAL)
        modal2 = manager.push(MockElement(), LayerType.MODAL)

        popped = manager.pop()

        assert popped is modal2
        assert len(manager.overlays) == 1
        assert manager.overlays[0] is modal1

    def test_pop_specific_overlay(self, manager):
        """Test popping a specific overlay."""
        modal1 = manager.push(MockElement(id="m1"), LayerType.MODAL)
        modal2 = manager.push(MockElement(id="m2"), LayerType.MODAL)
        modal3 = manager.push(MockElement(id="m3"), LayerType.MODAL)

        popped = manager.pop(modal2)

        assert popped is modal2
        assert len(manager.overlays) == 2
        assert modal1 in manager.overlays
        assert modal3 in manager.overlays
        assert modal2 not in manager.overlays

    def test_pop_empty_returns_none(self, manager):
        """Test that popping from empty manager returns None."""
        result = manager.pop()
        assert result is None

    def test_pop_nonexistent_returns_none(self, manager):
        """Test that popping non-existent overlay returns None."""
        overlay1 = manager.push(MockElement(), LayerType.MODAL)
        fake_overlay = Overlay(
            element=MockElement(),
            layer_type=LayerType.MODAL,
            z_index=999,
        )

        result = manager.pop(fake_overlay)

        assert result is None
        assert len(manager.overlays) == 1

    def test_pop_layer(self, manager):
        """Test removing all overlays in a specific layer."""
        modal1 = manager.push(MockElement(), LayerType.MODAL)
        modal2 = manager.push(MockElement(), LayerType.MODAL)
        dropdown1 = manager.push(MockElement(), LayerType.DROPDOWN)
        tooltip1 = manager.push(MockElement(), LayerType.TOOLTIP)

        removed = manager.pop_layer(LayerType.MODAL)

        assert len(removed) == 2
        assert modal1 in removed
        assert modal2 in removed
        assert len(manager.overlays) == 2  # Only dropdown and tooltip remain
        assert dropdown1 in manager.overlays
        assert tooltip1 in manager.overlays

    def test_clear(self, manager):
        """Test clearing all overlays."""
        manager.push(MockElement(), LayerType.MODAL)
        manager.push(MockElement(), LayerType.DROPDOWN)
        manager.push(MockElement(), LayerType.TOOLTIP)

        removed = manager.clear()

        assert len(removed) == 3
        assert len(manager.overlays) == 0

    def test_get_at_position(self, manager):
        """Test getting overlay at a position."""
        # Modal at (10, 10) size 10x5
        modal_elem = MockElement(id="modal", x=10, y=10, width=10, height=5)
        modal = manager.push(modal_elem, LayerType.MODAL)

        # Dropdown at (20, 20) size 10x5
        dropdown_elem = MockElement(id="dropdown", x=20, y=20, width=10, height=5)
        dropdown = manager.push(dropdown_elem, LayerType.DROPDOWN)

        # Click on modal
        overlay = manager.get_at_position(12, 12)
        assert overlay is modal

        # Click on dropdown (higher z-index)
        overlay = manager.get_at_position(22, 22)
        assert overlay is dropdown

        # Click outside all overlays
        overlay = manager.get_at_position(0, 0)
        assert overlay is None

    def test_get_at_position_returns_highest_z(self, manager):
        """Test that get_at_position returns highest z-index overlay."""
        # Two overlapping overlays at same position
        modal_elem = MockElement(id="modal", x=10, y=10, width=10, height=5)
        modal = manager.push(modal_elem, LayerType.MODAL)

        tooltip_elem = MockElement(id="tooltip", x=10, y=10, width=10, height=5)
        tooltip = manager.push(tooltip_elem, LayerType.TOOLTIP)

        # Should return tooltip (higher z-index)
        overlay = manager.get_at_position(12, 12)
        assert overlay is tooltip

    def test_get_top_overlay(self, manager):
        """Test getting the topmost overlay."""
        assert manager.get_top_overlay() is None

        modal = manager.push(MockElement(), LayerType.MODAL)
        assert manager.get_top_overlay() is modal

        dropdown = manager.push(MockElement(), LayerType.DROPDOWN)
        assert manager.get_top_overlay() is dropdown

        tooltip = manager.push(MockElement(), LayerType.TOOLTIP)
        assert manager.get_top_overlay() is tooltip

    def test_handle_click_outside(self, manager):
        """Test handling clicks outside overlays."""
        # Create modal that closes on click outside
        modal_elem = MockElement(x=10, y=10, width=10, height=5)
        manager.push(modal_elem, LayerType.MODAL, close_on_click_outside=True)

        # Click outside
        closed = manager.handle_click_outside(0, 0)

        assert closed is True
        assert len(manager.overlays) == 0

    def test_handle_click_outside_no_close(self, manager):
        """Test that overlays with close_on_click_outside=False don't close."""
        modal_elem = MockElement(x=10, y=10, width=10, height=5)
        manager.push(modal_elem, LayerType.MODAL, close_on_click_outside=False)

        # Click outside
        closed = manager.handle_click_outside(0, 0)

        assert closed is False
        assert len(manager.overlays) == 1

    def test_handle_click_outside_stops_at_overlay(self, manager):
        """Test that click inside overlay doesn't close it."""
        modal_elem = MockElement(x=10, y=10, width=10, height=5)
        manager.push(modal_elem, LayerType.MODAL, close_on_click_outside=True)

        # Click inside modal
        closed = manager.handle_click_outside(12, 12)

        assert closed is False
        assert len(manager.overlays) == 1

    def test_handle_escape(self, manager):
        """Test handling ESC key."""
        manager.push(MockElement(), LayerType.MODAL, close_on_escape=True)

        closed = manager.handle_escape()

        assert closed is True
        assert len(manager.overlays) == 0

    def test_handle_escape_no_close(self, manager):
        """Test that overlays with close_on_escape=False don't close on ESC."""
        manager.push(MockElement(), LayerType.MODAL, close_on_escape=False)

        closed = manager.handle_escape()

        assert closed is False
        assert len(manager.overlays) == 1

    def test_handle_escape_closes_topmost(self, manager):
        """Test that ESC closes only the topmost closeable overlay."""
        modal1 = manager.push(MockElement(), LayerType.MODAL, close_on_escape=True)
        modal2 = manager.push(MockElement(), LayerType.MODAL, close_on_escape=True)

        closed = manager.handle_escape()

        assert closed is True
        assert len(manager.overlays) == 1
        assert manager.overlays[0] is modal1

    def test_should_trap_focus(self, manager):
        """Test checking if focus should be trapped."""
        assert manager.should_trap_focus() is False

        manager.push(MockElement(), LayerType.MODAL, trap_focus=False)
        assert manager.should_trap_focus() is False

        manager.push(MockElement(), LayerType.MODAL, trap_focus=True)
        assert manager.should_trap_focus() is True

    def test_on_close_callback(self, manager):
        """Test that on_close callback is invoked."""
        called = []

        def on_close():
            called.append(True)

        overlay = manager.push(MockElement(), LayerType.MODAL, on_close=on_close)

        manager.pop(overlay)

        assert len(called) == 1

    def test_dimmed_background(self, manager):
        """Test has_dimmed_overlay method."""
        assert manager.has_dimmed_overlay() is False

        manager.push(MockElement(), LayerType.MODAL, dimmed_background=False)
        assert manager.has_dimmed_overlay() is False

        manager.push(MockElement(), LayerType.MODAL, dimmed_background=True)
        assert manager.has_dimmed_overlay() is True

    def test_get_overlay_elements(self, manager):
        """Test getting overlay elements in z-order."""
        modal_elem = MockElement(id="modal")
        tooltip_elem = MockElement(id="tooltip")
        dropdown_elem = MockElement(id="dropdown")

        manager.push(modal_elem, LayerType.MODAL)
        manager.push(tooltip_elem, LayerType.TOOLTIP)
        manager.push(dropdown_elem, LayerType.DROPDOWN)

        elements = manager.get_overlay_elements()

        assert len(elements) == 3
        assert elements[0] is modal_elem  # z=100
        assert elements[1] is dropdown_elem  # z=200
        assert elements[2] is tooltip_elem  # z=300
