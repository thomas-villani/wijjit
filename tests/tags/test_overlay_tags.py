"""Unit tests for template overlay tags.

Tests verify that overlay template tags properly create overlay_info structures
and integrate with the OverlayManager.
"""

from wijjit.core.app import Wijjit
from wijjit.core.overlay import LayerType
from wijjit.core.renderer import Renderer


# Helper to render template with overlay support
def render_template(app: Wijjit, template: str, width: int = 80, height: int = 24):
    """Render a template with overlay support."""
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


class TestOverlayTags:
    """Test overlay template tags."""

    def test_modal_tag_creates_overlay_info(self):
        """Test that {% modal %} tag creates overlay info.

        Verifies that the modal tag properly creates an overlay_info dict
        with correct element, layer_type, and options.
        """
        app = Wijjit()
        app.state.show_modal = True

        template = """
        {% frame width="80" height="24" %}
            {% modal id="test_modal" visible="show_modal" %}
                Test modal content
            {% endmodal %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Verify overlay was pushed to overlay_manager
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL
        assert overlay.element.id == "test_modal"
        assert overlay.trap_focus is True
        assert overlay.dimmed_background is True

    def test_modal_tag_respects_visibility(self):
        """Test that modal visibility is controlled by state.

        Verifies that when visible state is False, modal is not shown.
        """
        app = Wijjit()
        app.state.show_modal = False

        template = """
        {% frame width="80" height="24" %}
            {% modal id="test_modal" visible="show_modal" %}
                Test modal content
            {% endmodal %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Modal should not be in overlay_manager when visible=False
        assert len(app.overlay_manager.overlays) == 0

    def test_confirmdialog_tag_creates_overlay_info(self):
        """Test that {% confirmdialog %} tag creates overlay info.

        Verifies that confirm dialog tag creates proper overlay_info
        with modal layer type and expected options.
        """
        app = Wijjit()
        app.state.show_confirm = True

        template = """
        {% frame width="80" height="24" %}
            {% confirmdialog
                id="test_confirm"
                title="Confirm Action"
                message="Are you sure?"
                visible="show_confirm"
                confirm_action="handle_confirm"
                cancel_action="handle_cancel"
            %}{% endconfirmdialog %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Verify confirm dialog overlay was pushed
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL
        assert overlay.trap_focus is True
        assert overlay.close_on_click_outside is False

    def test_alertdialog_tag_creates_overlay_info(self):
        """Test that {% alertdialog %} tag creates overlay info.

        Verifies that alert dialog tag creates proper overlay_info.
        """
        app = Wijjit()
        app.state.show_alert = True

        template = """
        {% frame width="80" height="24" %}
            {% alertdialog
                id="test_alert"
                title="Alert"
                message="This is an alert"
                visible="show_alert"
                ok_action="handle_ok"
            %}{% endalertdialog %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Verify alert dialog overlay was pushed
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL
        assert overlay.trap_focus is True

    def test_inputdialog_tag_creates_overlay_info(self):
        """Test that {% inputdialog %} tag creates overlay info.

        Verifies that input dialog tag creates proper overlay_info.
        """
        app = Wijjit()
        app.state.show_input = True

        template = """
        {% frame width="80" height="24" %}
            {% inputdialog
                id="test_input"
                title="Input Required"
                prompt="Enter value:"
                visible="show_input"
                submit_action="handle_input"
                cancel_action="handle_cancel"
            %}{% endinputdialog %}
        {% endframe %}
        """

        output, elements = render_template(app, template)

        # Verify input dialog overlay was pushed
        assert len(app.overlay_manager.overlays) == 1
        overlay = app.overlay_manager.overlays[0]
        assert overlay.layer_type == LayerType.MODAL
        assert overlay.trap_focus is True

    def test_multiple_overlays_cleared_on_render(self):
        """Test that overlays are cleared and rebuilt on each render.

        Verifies the simple clear-and-rebuild strategy where all
        template overlays are cleared before new ones are pushed.
        """
        app = Wijjit()
        app.state.show_modal1 = True
        app.state.show_modal2 = True

        template = """
        {% frame width="80" height="24" %}
            {% modal id="modal1" visible="show_modal1" %}
                Modal 1
            {% endmodal %}
            {% modal id="modal2" visible="show_modal2" %}
                Modal 2
            {% endmodal %}
        {% endframe %}
        """

        # First render - both modals visible
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 2

        # Second render - hide one modal
        app.state.show_modal1 = False
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].element.id == "modal2"

        # Third render - show both again
        app.state.show_modal1 = True
        output, elements = render_template(app, template)
        assert len(app.overlay_manager.overlays) == 2


class TestRendererOverlayIntegration:
    """Test Renderer's integration with OverlayManager."""

    def test_renderer_processes_overlays_with_overlay_manager(self):
        """Test that Renderer.render_with_layout processes overlays.

        Verifies that when overlay_manager is passed to render_with_layout,
        it properly processes layout_ctx._overlays and pushes them.
        """
        app = Wijjit()
        app.state.show_modal = True
        renderer = app.renderer  # Use app's renderer which has proper setup

        template = """
        {% frame width="80" height="24" %}
            {% modal id="test_modal" visible="show_modal" %}
                Test content
            {% endmodal %}
        {% endframe %}
        """

        # Set up context like render_template helper does
        data = {"state": app.state}
        renderer.add_global("_wijjit_current_context", data)

        output, elements, layout_ctx = renderer.render_with_layout(
            template,
            context=data,
            width=80,
            height=24,
            overlay_manager=app.overlay_manager,
        )

        # Process template-declared overlays (this is now done by app, not renderer)
        app._sync_template_overlays(layout_ctx)

        renderer.add_global("_wijjit_current_context", None)

        # Verify overlay was pushed to manager
        assert len(app.overlay_manager.overlays) == 1
        assert app.overlay_manager.overlays[0].element.id == "test_modal"

    def test_renderer_without_overlay_manager_doesnt_crash(self):
        """Test that Renderer works without overlay_manager parameter.

        Verifies backward compatibility - render_with_layout should work
        when overlay_manager is not provided (for non-app usage).
        """
        renderer = Renderer()

        template = """
        {% frame width="80" height="24" %}
            {% modal id="test_modal" %}
                Test content
            {% endmodal %}
        {% endframe %}
        """

        # Should not crash when overlay_manager is None
        output, elements, _ = renderer.render_with_layout(
            template, context={}, width=80, height=24, overlay_manager=None
        )

        # Output should still be valid
        assert output is not None
        assert isinstance(elements, list)
