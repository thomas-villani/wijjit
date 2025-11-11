"""Tests for automatic bounds calculation in overlay manager."""

import shutil

from wijjit.core.app import Wijjit
from wijjit.core.overlay import LayerType
from wijjit.elements.modal import ConfirmDialog


class TestOverlayAutoBounds:
    """Tests for automatic bounds calculation for centered overlays."""

    def test_auto_bounds_centered_overlay(self):
        """Test that centered overlays automatically get bounds calculated.

        When an overlay element has centered=True but no bounds,
        the overlay manager should auto-calculate centered bounds.
        """
        app = Wijjit()

        # Create a centered overlay element without bounds
        dialog = ConfirmDialog(
            title="Test Dialog",
            message="Test message",
            on_confirm=lambda: None,
            on_cancel=lambda: None,
            width=50,
            height=12,
        )

        # Verify element is marked as centered and has no bounds
        assert dialog.centered is True
        assert dialog.bounds is None

        # Push to overlay manager
        overlay = app.overlay_manager.push(
            dialog,
            layer_type=LayerType.MODAL,
            trap_focus=False,
            dimmed_background=True,
        )

        # Verify bounds were auto-calculated
        assert dialog.bounds is not None
        assert overlay.element.bounds is not None

        # Verify bounds are centered
        term_size = shutil.get_terminal_size()
        expected_x = (term_size.columns - dialog.width) // 2
        expected_y = (term_size.lines - dialog.height) // 2

        assert dialog.bounds.x == expected_x
        assert dialog.bounds.y == expected_y
        assert dialog.bounds.width == dialog.width
        assert dialog.bounds.height == dialog.height

    def test_auto_bounds_not_applied_when_bounds_exist(self):
        """Test that auto-bounds are not applied when element already has bounds.

        If an element already has bounds set, the overlay manager should
        not override them.
        """
        from wijjit.layout.bounds import Bounds

        app = Wijjit()

        # Create a centered overlay element WITH bounds
        dialog = ConfirmDialog(
            title="Test Dialog",
            message="Test message",
            on_confirm=lambda: None,
            on_cancel=lambda: None,
            width=50,
            height=12,
        )

        # Set custom bounds
        custom_bounds = Bounds(x=10, y=5, width=50, height=12)
        dialog.bounds = custom_bounds

        # Push to overlay manager
        overlay = app.overlay_manager.push(
            dialog,
            layer_type=LayerType.MODAL,
            trap_focus=False,
            dimmed_background=True,
        )

        # Verify bounds were NOT changed
        assert dialog.bounds.x == 10
        assert dialog.bounds.y == 5
        assert dialog.bounds.width == 50
        assert dialog.bounds.height == 12

    def test_auto_bounds_not_applied_when_not_centered(self):
        """Test that auto-bounds are not applied to non-centered overlays.

        If an element is not marked as centered, the overlay manager should
        not calculate bounds automatically.
        """
        from wijjit.elements.base import Element

        app = Wijjit()

        # Create a non-centered overlay element
        class CustomElement(Element):
            def __init__(self):
                super().__init__()
                self.width = 50
                self.height = 12
                self.centered = False  # Not centered

            def render(self):
                return "Custom Element"

        element = CustomElement()

        # Verify element is not centered and has no bounds
        assert element.centered is False
        assert element.bounds is None

        # Push to overlay manager
        overlay = app.overlay_manager.push(
            element,
            layer_type=LayerType.MODAL,
            trap_focus=False,
            dimmed_background=False,
        )

        # Verify bounds were NOT calculated
        assert element.bounds is None

    def test_recalculate_centered_overlays_on_resize(self):
        """Test that centered overlays are repositioned on terminal resize.

        When the terminal size changes, centered overlays should be
        recalculated to remain centered.
        """
        app = Wijjit()

        # Create a centered overlay element
        dialog = ConfirmDialog(
            title="Test Dialog",
            message="Test message",
            on_confirm=lambda: None,
            on_cancel=lambda: None,
            width=50,
            height=12,
        )

        # Push to overlay manager (this will auto-calculate initial bounds)
        overlay = app.overlay_manager.push(
            dialog,
            layer_type=LayerType.MODAL,
            trap_focus=False,
            dimmed_background=True,
        )

        # Get initial bounds
        initial_bounds = dialog.bounds

        # Simulate terminal resize to a different size
        new_width = 120
        new_height = 40

        # Recalculate overlay positions
        app.overlay_manager.recalculate_centered_overlays(new_width, new_height)

        # Verify bounds were recalculated
        expected_x = (new_width - dialog.width) // 2
        expected_y = (new_height - dialog.height) // 2

        assert dialog.bounds.x == expected_x
        assert dialog.bounds.y == expected_y
        assert dialog.bounds.width == dialog.width
        assert dialog.bounds.height == dialog.height

        # Verify bounds changed from initial
        assert (
            dialog.bounds.x != initial_bounds.x or dialog.bounds.y != initial_bounds.y
        )
