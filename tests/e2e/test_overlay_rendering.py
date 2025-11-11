"""End-to-end tests for overlay rendering.

Tests verify the complete overlay rendering flow from template declaration
through rendering to final output, ensuring overlays appear correctly.
"""

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.overlay import LayerType
from wijjit.terminal.input import Keys

from .helpers import (
    dispatch_action,
    get_element_by_id,
    render_view,
    simulate_button_click,
    simulate_typing,
)


class TestModalOverlayRendering:
    """Test modal overlay rendering end-to-end."""

    def test_modal_appears_in_output(self):
        """Test that modal declared in template appears in output.

        Verifies the complete flow: template modal tag creates overlay_info,
        renderer processes it, overlay_manager receives it, and modal appears
        in the final rendered output.
        """
        app = Wijjit()
        app.state.show_modal = True

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% modal id="test_modal" visible="show_modal" %}
                <text>Modal content</text>
            {% endmodal %}
        {% endframe %}
        """

        app.view("/")(lambda: template)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify modal was pushed to overlay_manager
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].element.id == "test_modal"

        # Verify base content is in output
        assert "Base content" in output

        # Verify modal content is in output
        # (Modal should be rendered on top of base content)
        assert "Modal content" in output

    def test_modal_not_shown_when_invisible(self):
        """Test that modal is not shown when visible state is False.

        Verifies that visibility control works correctly.
        """
        app = Wijjit()
        app.state.show_modal = False

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% modal id="test_modal" visible="show_modal" %}
                <text>Modal content</text>
            {% endmodal %}
        {% endframe %}
        """

        app.view("/")(lambda: template)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify no overlays
        assert len(app.overlay_manager.overlays) == 0

        # Verify base content is in output
        assert "Base content" in output

        # Modal content should NOT be in output
        assert "Modal content" not in output

    def test_modal_toggling(self):
        """Test toggling modal visibility updates rendering.

        Verifies that changing the visible state correctly shows/hides modal.
        """
        app = Wijjit()
        app.state.show_modal = False

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% modal id="test_modal" visible="show_modal" %}
                <text>Modal content</text>
            {% endmodal %}
        {% endframe %}
        """

        app.view("/")(lambda: template)

        # First render - modal hidden
        output, elements = render_view(app, "/", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 0
        assert "Modal content" not in output

        # Show modal
        app.state.show_modal = True
        output, elements = render_view(app, "/", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 1
        assert "Modal content" in output

        # Hide modal again
        app.state.show_modal = False
        output, elements = render_view(app, "/", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 0
        assert "Modal content" not in output


class TestConfirmDialogRendering:
    """Test confirm dialog rendering end-to-end."""

    def test_confirmdialog_appears_in_output(self):
        """Test that confirm dialog appears correctly in output.

        Verifies that confirmdialog tag creates a modal overlay with
        proper structure (title, message, buttons).
        """
        app = Wijjit()
        app.state.show_confirm = True

        confirm_clicked = False
        cancel_clicked = False

        def handle_confirm():
            nonlocal confirm_clicked
            confirm_clicked = True

        def handle_cancel():
            nonlocal cancel_clicked
            cancel_clicked = True

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% confirmdialog
                id="confirm_dialog"
                title="Confirm Action"
                message="Are you sure you want to proceed?"
                visible="show_confirm"
                confirm_action="handle_confirm"
                cancel_action="handle_cancel"
            %}{% endconfirmdialog %}
        {% endframe %}
        """

        app.view("/")(lambda: template)
        app.action("handle_confirm")(handle_confirm)
        app.action("handle_cancel")(handle_cancel)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify confirm dialog was pushed to overlay_manager
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL
        assert overlay.trap_focus is True

        # Verify dialog content appears in output
        assert "Confirm Action" in output
        assert "Are you sure you want to proceed?" in output

    def test_alertdialog_appears_in_output(self):
        """Test that alert dialog appears correctly in output.

        Verifies that alertdialog tag creates a proper modal overlay.
        """
        app = Wijjit()
        app.state.show_alert = True

        ok_clicked = False

        def handle_ok():
            nonlocal ok_clicked
            ok_clicked = True

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% alertdialog
                id="alert_dialog"
                title="Notice"
                message="This is an important message."
                visible="show_alert"
                ok_action="handle_ok"
            %}{% endalertdialog %}
        {% endframe %}
        """

        app.view("/")(lambda: template)
        app.action("handle_ok")(handle_ok)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify alert dialog was pushed to overlay_manager
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL

        # Verify dialog content appears in output
        assert "Notice" in output
        assert "This is an important message." in output


class TestInputDialogRendering:
    """Test input dialog rendering end-to-end."""

    def test_inputdialog_appears_in_output(self):
        """Test that input dialog appears correctly with text input.

        Verifies that inputdialog tag creates a modal with an input field.
        """
        app = Wijjit()
        app.state.show_input = True

        input_value = None

        def handle_input(value):
            nonlocal input_value
            input_value = value

        def handle_cancel():
            pass

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% inputdialog
                id="input_dialog"
                title="Enter Value"
                prompt="Please enter your name:"
                visible="show_input"
                ok_action="handle_input"
                cancel_action="handle_cancel"
            %}{% endinputdialog %}
        {% endframe %}
        """

        app.view("/")(lambda: template)
        app.action("handle_input")(handle_input)
        app.action("handle_cancel")(handle_cancel)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify input dialog was pushed to overlay_manager
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL

        # Verify dialog content appears in output
        assert "Enter Value" in output
        assert "Please enter your name:" in output


class TestMultipleOverlays:
    """Test multiple overlays rendering together."""

    def test_multiple_modals_stack_correctly(self):
        """Test that multiple modals can be shown and stack properly.

        Verifies that multiple overlays maintain proper z-order.
        """
        app = Wijjit()
        app.state.show_modal1 = True
        app.state.show_modal2 = True

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% modal id="modal1" visible="show_modal1" %}
                <text>First modal</text>
            {% endmodal %}
            {% modal id="modal2" visible="show_modal2" %}
                <text>Second modal</text>
            {% endmodal %}
        {% endframe %}
        """

        app.view("/")(lambda: template)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify both modals were pushed
        assert len(app.overlay_manager.overlays) == 2

        # Verify both have different z-indexes
        z_indexes = [overlay.z_index for overlay in app.overlay_manager.overlays]
        assert len(set(z_indexes)) == 2  # All unique

        # Both modal contents should be in output
        assert "First modal" in output
        assert "Second modal" in output

    def test_overlay_clear_and_rebuild(self):
        """Test that overlays are cleared and rebuilt on each render.

        Verifies the clear-and-rebuild strategy works correctly.
        """
        app = Wijjit()
        app.state.show_modal1 = True
        app.state.show_modal2 = True

        template = """
        {% frame width="80" height="24" %}
            {% modal id="modal1" visible="show_modal1" %}
                <text>Modal 1</text>
            {% endmodal %}
            {% modal id="modal2" visible="show_modal2" %}
                <text>Modal 2</text>
            {% endmodal %}
        {% endframe %}
        """

        app.view("/")(lambda: template)

        # First render - both visible
        output, elements = render_view(app, "/", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 2

        # Second render - hide one
        app.state.show_modal1 = False
        output, elements = render_view(app, "/", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].element.id == "modal2"
        assert "Modal 2" in output
        assert "Modal 1" not in output

        # Third render - show both again
        app.state.show_modal1 = True
        output, elements = render_view(app, "/", width=80, height=24)
        assert len(app.overlay_manager.overlays) == 2
        assert "Modal 1" in output
        assert "Modal 2" in output


class TestOverlayWithDifferentLayers:
    """Test overlays with different layer types."""

    def test_dropdown_layer_overlay(self):
        """Test overlay with dropdown layer type.

        Verifies that layer_type is properly set for dropdown overlays.
        """
        app = Wijjit()
        app.state.show_dropdown = True

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% overlay id="dropdown" layer="dropdown" visible="show_dropdown" %}
                <text>Dropdown content</text>
            {% endoverlay %}
        {% endframe %}
        """

        app.view("/")(lambda: template)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify overlay has correct layer type
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.DROPDOWN

        # Verify content in output
        assert "Dropdown content" in output

    def test_tooltip_layer_overlay(self):
        """Test overlay with tooltip layer type.

        Verifies that layer_type is properly set for tooltip overlays.
        """
        app = Wijjit()
        app.state.show_tooltip = True

        template = """
        {% frame width="80" height="24" %}
            <text>Base content</text>
            {% overlay id="tooltip" layer="tooltip" visible="show_tooltip" %}
                <text>Tooltip content</text>
            {% endoverlay %}
        {% endframe %}
        """

        app.view("/")(lambda: template)

        # Render the view
        output, elements = render_view(app, "/", width=80, height=24)

        # Verify overlay has correct layer type
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.TOOLTIP

        # Verify content in output
        assert "Tooltip content" in output
