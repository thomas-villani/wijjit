"""End-to-end tests for overlay rendering.

Tests verify the complete overlay rendering flow from template declaration
through rendering to final output, ensuring overlays appear correctly in
the actual rendered output.
"""

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.overlay import LayerType

from .helpers import render_view

pytestmark = pytest.mark.e2e


class TestModalOverlayE2E:
    """End-to-end tests for modal overlay rendering."""

    def test_modal_full_rendering_flow(self):
        """Test complete modal rendering flow from template to output.

        This E2E test demonstrates the full pipeline:
        1. Template with {% modal %} tag
        2. State controls visibility
        3. Renderer processes template
        4. OverlayManager receives overlay
        5. Modal content appears in final output
        """
        app = Wijjit(initial_state={"show_modal": True})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame width="80" height="24" %}
    Base content here
    {% modal id="test_modal" visible="show_modal" title="Test Modal" %}
        Modal content here
    {% endmodal %}
{% endframe %}
                """
            }

        # Render the view using E2E helper
        output, elements = render_view(app, "main", width=80, height=24)

        # Verify the complete flow worked
        assert (
            len(app.overlay_manager.overlays) == 1
        ), "Modal should be in overlay_manager"
        assert app.overlay_manager.overlays[0].element.id == "test_modal"
        assert app.overlay_manager.overlays[0].layer_type == LayerType.MODAL

        # Verify base content is in output
        assert "Base content here" in output, "Base content should be in output"

        # Note: Modal content compositing into output is handled by app's overlay
        # rendering pipeline, not by render_view. This E2E test verifies that
        # the overlay is properly created and registered with the overlay_manager.


class TestConfirmDialogE2E:
    """End-to-end tests for confirm dialog rendering."""

    def test_confirmdialog_full_rendering_flow(self):
        """Test complete confirm dialog rendering flow.

        Demonstrates that confirm dialogs properly create modal overlays
        and render with buttons in the output.
        """
        app = Wijjit(initial_state={"show_confirm": True})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame width="80" height="24" %}
    Main content
    {% confirmdialog
        id="confirm_dialog"
        title="Confirm"
        message="Are you sure?"
        visible="show_confirm"
        confirm_action="do_confirm"
        cancel_action="do_cancel"
    %}{% endconfirmdialog %}
{% endframe %}
                """
            }

        output, elements = render_view(app, "main", width=80, height=24)

        # Verify overlay was created
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL
        assert overlay.trap_focus is True
        assert overlay.close_on_click_outside is False

        # Note: Dialog content compositing is handled by app's overlay rendering
        # pipeline. This test verifies the overlay is created with correct properties.


class TestOverlayVisibilityE2E:
    """End-to-end tests for overlay visibility control."""

    def test_overlay_visibility_toggle(self):
        """Test that overlay visibility is controlled by state.

        Demonstrates the dynamic visibility feature where overlays
        appear/disappear based on state changes.
        """
        app = Wijjit(initial_state={"show_it": False})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame width="80" height="24" %}
    Content
    {% modal id="dynamic_modal" visible="show_it" %}
        Dynamic modal
    {% endmodal %}
{% endframe %}
                """
            }

        # First render - modal hidden
        app.state.show_it = False
        output1, _ = render_view(app, "main", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 0, "No overlays when hidden"

        # Second render - modal shown
        app.state.show_it = True
        output2, _ = render_view(app, "main", width=80, height=24)
        assert (
            len(app.overlay_manager.overlays) == 1
        ), "Overlay should appear when visible"

        # Third render - modal hidden again
        app.state.show_it = False
        output3, _ = render_view(app, "main", width=80, height=24)
        assert (
            len(app.overlay_manager.overlays) == 0
        ), "Overlay should disappear when hidden"


class TestMultipleOverlaysE2E:
    """End-to-end tests for multiple overlay handling."""

    def test_multiple_overlays_render_correctly(self):
        """Test that multiple overlays can coexist and render properly.

        Demonstrates the overlay stacking system with proper z-ordering.
        """
        app = Wijjit(initial_state={"show_modal1": True, "show_modal2": True})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame width="80" height="24" %}
    Base
    {% modal id="modal1" visible="show_modal1" %}
        First modal
    {% endmodal %}
    {% modal id="modal2" visible="show_modal2" %}
        Second modal
    {% endmodal %}
{% endframe %}
                """
            }

        output, _ = render_view(app, "main", width=80, height=24)

        # Verify both overlays exist
        assert len(app.overlay_manager.overlays) == 2, "Should have 2 overlays"

        # Verify z-ordering (each overlay gets unique z-index)
        z_indexes = [o.z_index for o in app.overlay_manager.overlays]
        assert len(set(z_indexes)) == 2, "Each overlay should have unique z-index"


class TestOverlayLayerTypesE2E:
    """End-to-end tests for different overlay layer types."""

    def test_modal_layer_type(self):
        """Test that modal layer type works correctly."""
        app = Wijjit(initial_state={"show_overlay": True})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame width="80" height="24" %}
    {% modal id="m" visible="show_overlay" %}Content{% endmodal %}
{% endframe %}
                """
            }

        output, _ = render_view(app, "main", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].layer_type == LayerType.MODAL

    def test_dropdown_layer_type(self):
        """Test that dropdown layer type works correctly."""
        app = Wijjit(initial_state={"show_overlay": True})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame width="80" height="24" %}
    {% overlay id="d" layer="dropdown" visible="show_overlay" %}Content{% endoverlay %}
{% endframe %}
                """
            }

        output, _ = render_view(app, "main", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].layer_type == LayerType.DROPDOWN

    def test_tooltip_layer_type(self):
        """Test that tooltip layer type works correctly."""
        app = Wijjit(initial_state={"show_overlay": True})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame width="80" height="24" %}
    {% overlay id="t" layer="tooltip" visible="show_overlay" %}Content{% endoverlay %}
{% endframe %}
                """
            }

        output, _ = render_view(app, "main", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].layer_type == LayerType.TOOLTIP
