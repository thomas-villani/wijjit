"""Tests for StatusBar template tags."""

from wijjit.core.renderer import Renderer
from wijjit.core.state import State
from wijjit.elements.display.statusbar import StatusBar


class TestStatusBarTag:
    """Test the {% statusbar %} template tag."""

    def test_statusbar_tag_creates_element(self):
        """Test that {% statusbar %} tag creates StatusBar element.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% frame width="80" height="24" %}
    Main content
    {% statusbar left="File: app.py" center="Ready" right="Line 1" %}
    {% endstatusbar %}
{% endframe %}
        """

        # Render template - statusbar is stored in layout_ctx._statusbar
        output, elements, layout_ctx = renderer.render_with_layout(
            template, width=80, height=24
        )

        # Verify statusbar was captured
        assert hasattr(layout_ctx, "_statusbar")
        assert layout_ctx._statusbar is not None
        assert isinstance(layout_ctx._statusbar, StatusBar)

    def test_statusbar_with_sections(self):
        """Test statusbar with left, center, and right sections.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% frame width="80" height="10" %}
    Content
    {% statusbar left="Left section"
                 center="Center section"
                 right="Right section" %}
    {% endstatusbar %}
{% endframe %}
        """

        output, elements, layout_ctx = renderer.render_with_layout(
            template, width=80, height=10
        )

        assert hasattr(layout_ctx, "_statusbar")
        statusbar = layout_ctx._statusbar
        assert isinstance(statusbar, StatusBar)

        # Verify sections are set
        assert statusbar.left == "Left section"
        assert statusbar.center == "Center section"
        assert statusbar.right == "Right section"

    def test_statusbar_with_state_binding(self):
        """Test statusbar with state variable binding.

        Returns
        -------
        None
        """
        renderer = Renderer()
        state = State(
            {
                "filename": "app.py",
                "status_msg": "Ready",
                "line_num": 42,
            }
        )

        template = """
{% frame width="80" height="10" %}
    Content
    {% statusbar left="File: " + state.filename
                 center=state.status_msg
                 right="Line " + state.line_num|string %}
    {% endstatusbar %}
{% endframe %}
        """

        output, elements, layout_ctx = renderer.render_with_layout(
            template, width=80, height=10, context={"state": state}
        )

        assert hasattr(layout_ctx, "_statusbar")
        statusbar = layout_ctx._statusbar

        # Verify bound values
        assert statusbar.left == "File: app.py"
        assert statusbar.center == "Ready"
        assert statusbar.right == "Line 42"

    def test_statusbar_with_colors(self):
        """Test statusbar with custom colors.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% frame width="80" height="10" %}
    Content
    {% statusbar left="Info"
                 bg_color="blue"
                 text_color="white" %}
    {% endstatusbar %}
{% endframe %}
        """

        output, elements, layout_ctx = renderer.render_with_layout(
            template, width=80, height=10
        )

        assert hasattr(layout_ctx, "_statusbar")
        statusbar = layout_ctx._statusbar

        # Verify colors are set directly as attributes
        assert statusbar.bg_color == "blue"
        assert statusbar.text_color == "white"

    def test_statusbar_empty_sections(self):
        """Test statusbar with empty sections.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% frame width="80" height="10" %}
    Content
    {% statusbar %}{% endstatusbar %}
{% endframe %}
        """

        output, elements, layout_ctx = renderer.render_with_layout(
            template, width=80, height=10
        )

        assert hasattr(layout_ctx, "_statusbar")
        statusbar = layout_ctx._statusbar

        # Default to empty strings
        assert statusbar.left == ""
        assert statusbar.center == ""
        assert statusbar.right == ""

    def test_statusbar_with_id(self):
        """Test statusbar with custom id.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% frame width="80" height="10" %}
    Content
    {% statusbar id="main_statusbar" left="Status" %}
    {% endstatusbar %}
{% endframe %}
        """

        output, elements, layout_ctx = renderer.render_with_layout(
            template, width=80, height=10
        )

        assert hasattr(layout_ctx, "_statusbar")
        statusbar = layout_ctx._statusbar
        assert statusbar.id == "main_statusbar"

    def test_statusbar_replaces_previous(self):
        """Test that new statusbar replaces previous one.

        Returns
        -------
        None
        """
        renderer = Renderer()

        # First render with statusbar
        template1 = """
{% frame width="80" height="10" %}
    Content 1
    {% statusbar left="First" %}{% endstatusbar %}
{% endframe %}
        """
        _, _, layout_ctx1 = renderer.render_with_layout(template1, width=80, height=10)

        # Second render with different statusbar
        template2 = """
{% frame width="80" height="10" %}
    Content 2
    {% statusbar left="Second" %}{% endstatusbar %}
{% endframe %}
        """
        _, _, layout_ctx2 = renderer.render_with_layout(template2, width=80, height=10)

        # Verify second statusbar replaced first
        assert hasattr(layout_ctx2, "_statusbar")
        assert layout_ctx2._statusbar.left == "Second"

    def test_statusbar_without_frame(self):
        """Test statusbar can be used without frame tag.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% statusbar left="Standalone" %}{% endstatusbar %}
        """

        _, _, layout_ctx = renderer.render_with_layout(template, width=80, height=24)

        assert hasattr(layout_ctx, "_statusbar")
        assert isinstance(layout_ctx._statusbar, StatusBar)


class TestStatusBarIntegration:
    """Test statusbar integration with rendering pipeline."""

    def test_statusbar_renders_to_screen(self):
        """Test that statusbar appears in rendered output.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% frame width="40" height="5" %}
    Main content
    {% statusbar left="File" center="Status" right="Info" %}
    {% endstatusbar %}
{% endframe %}
        """

        output, _, layout_ctx = renderer.render_with_layout(
            template, width=40, height=5
        )

        # StatusBar is not part of main output - it's handled separately
        # But it should be captured in layout_ctx._statusbar
        assert hasattr(layout_ctx, "_statusbar")
        assert layout_ctx._statusbar is not None

    def test_statusbar_updates_with_state_changes(self):
        """Test that statusbar reflects state changes.

        Returns
        -------
        None
        """
        renderer = Renderer()
        state = State({"counter": 0})

        template = """
{% frame width="40" height="5" %}
    Content
    {% statusbar center="Count: " + state.counter|string %}
    {% endstatusbar %}
{% endframe %}
        """

        # Initial render
        _, _, layout_ctx1 = renderer.render_with_layout(
            template, width=40, height=5, context={"state": state}
        )
        assert layout_ctx1._statusbar.center == "Count: 0"

        # Update state and re-render
        state["counter"] = 5
        _, _, layout_ctx2 = renderer.render_with_layout(
            template, width=40, height=5, context={"state": state}
        )
        assert layout_ctx2._statusbar.center == "Count: 5"

    def test_multiple_sections_alignment(self):
        """Test that all three sections can be used simultaneously.

        Returns
        -------
        None
        """
        renderer = Renderer()
        template = """
{% frame width="80" height="10" %}
    Content
    {% statusbar left="Left text goes here"
                 center="Center text"
                 right="Right text here" %}
    {% endstatusbar %}
{% endframe %}
        """

        _, _, layout_ctx = renderer.render_with_layout(template, width=80, height=10)

        statusbar = layout_ctx._statusbar

        # All sections should be present
        assert statusbar.left != ""
        assert statusbar.center != ""
        assert statusbar.right != ""
        assert "Left text goes here" in statusbar.left
        assert "Center text" in statusbar.center
        assert "Right text here" in statusbar.right
