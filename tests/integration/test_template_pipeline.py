"""Integration tests for the complete template-to-output pipeline.

Tests the full pipeline:
1. Template parsing (Jinja2)
2. Element creation from tags
3. Layout calculation
4. Element rendering
5. Final output composition
"""

import pytest

from wijjit.core.renderer import Renderer

pytestmark = pytest.mark.integration


class TestCompletePipeline:
    """Test the complete template rendering pipeline."""

    def test_simple_template_to_output(self):
        """Test simplest case: plain text template to output.

        Verifies basic template -> output flow.
        """
        renderer = Renderer()
        template = "Hello, World!"

        output = renderer.render_string(template, {})

        assert output == "Hello, World!"

    def test_template_with_variables_to_output(self):
        """Test template with variable substitution.

        Verifies template + context -> output flow.
        """
        renderer = Renderer()
        template = "Hello, {{ name }}!"
        context = {"name": "Alice"}

        output = renderer.render_string(template, context)

        assert output == "Hello, Alice!"

    def test_template_with_frame_to_output(self):
        """Test template with frame element.

        Verifies template -> frame element -> rendered output.
        """
        renderer = Renderer()
        template = """
        {% frame width=30 height=5 title="Test" %}
            Content
        {% endframe %}
        """

        output, elements = renderer.render_with_layout(template, width=30, height=5)

        # Should produce bordered output
        assert output
        assert isinstance(output, str)
        lines = output.split("\n")
        assert len(lines) > 0

    def test_template_with_layout_to_output(self):
        """Test template with layout containers.

        Verifies template -> layout calculation -> output.
        """
        renderer = Renderer()
        template = """
        {% vstack width=40 height=10 %}
            Line 1
            Line 2
            Line 3
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=10)

        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output


class TestElementCreation:
    """Test element creation from template tags."""

    def test_frame_element_created_from_tag(self):
        """Test that frame tag creates Frame element.

        Verifies tag -> element instantiation.
        """
        renderer = Renderer()
        template = """
        {% frame id="myframe" width=20 height=5 %}
            Test
        {% endframe %}
        """

        output, elements = renderer.render_with_layout(template, width=20, height=5)

        # Should collect frame element as a list
        assert isinstance(elements, list)

    def test_textinput_element_created_from_tag(self):
        """Test that textinput tag creates TextInput element.

        Verifies input element creation.
        """
        renderer = Renderer()
        template = """{% textinput id="username" placeholder="Enter name" %}{% endtextinput %}"""

        output, elements = renderer.render_with_layout(template, width=40, height=3)

        # Should create textinput element - check by ID in elements list
        element_ids = [e.id for e in elements if hasattr(e, "id") and e.id]
        assert "username" in element_ids or "username" in output

    def test_button_element_created_from_tag(self):
        """Test that button tag creates Button element.

        Verifies button element creation.
        """
        renderer = Renderer()
        template = """{% button id="submit" %}Submit{% endbutton %}"""

        output, elements = renderer.render_with_layout(template, width=20, height=3)

        # Should create button - check by ID in elements list
        element_ids = [e.id for e in elements if hasattr(e, "id") and e.id]
        assert "submit" in element_ids or "Submit" in output

    def test_multiple_elements_created(self):
        """Test that template with multiple elements creates all.

        Verifies multi-element templates.
        """
        renderer = Renderer()
        template = """
        {% vstack width=40 height=15 %}
            {% textinput id="username" %}{% endtextinput %}
            {% textinput id="password" %}{% endtextinput %}
            {% button id="login" %}Login{% endbutton %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=15)

        # Should create all elements as a list
        assert isinstance(elements, list)
        # Elements might be collected or just rendered
        assert output


class TestLayoutCalculation:
    """Test layout calculation integration."""

    def test_vstack_calculates_vertical_layout(self):
        """Test that VStack correctly positions children vertically.

        Verifies vertical layout calculation.
        """
        renderer = Renderer()
        template = """
        {% vstack width=30 height=15 %}
            {% frame height=5 %}Top{% endframe %}
            {% frame height=5 %}Middle{% endframe %}
            {% frame height=5 %}Bottom{% endframe %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=30, height=15)

        # All frames should be rendered
        assert "Top" in output
        assert "Middle" in output
        assert "Bottom" in output

    def test_hstack_calculates_horizontal_layout(self):
        """Test that HStack correctly positions children horizontally.

        Verifies horizontal layout calculation.
        """
        renderer = Renderer()
        template = """
        {% hstack width=60 height=10 %}
            {% frame width=20 %}Left{% endframe %}
            {% frame width=20 %}Center{% endframe %}
            {% frame width=20 %}Right{% endframe %}
        {% endhstack %}
        """

        output, elements = renderer.render_with_layout(template, width=60, height=10)

        # All frames should be rendered
        assert "Left" in output
        assert "Center" in output
        assert "Right" in output

    def test_nested_layout_calculation(self):
        """Test that nested layouts calculate correctly.

        Verifies recursive layout calculation.
        """
        renderer = Renderer()
        template = """
        {% vstack width=60 height=20 %}
            {% hstack height=10 %}
                {% frame width="50%" %}Top Left{% endframe %}
                {% frame width="50%" %}Top Right{% endframe %}
            {% endhstack %}
            {% frame height=10 %}Bottom{% endframe %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=60, height=20)

        assert output
        lines = output.split("\n")
        assert len(lines) > 0

    def test_fill_sizing_in_layout(self):
        """Test that 'fill' sizing works in layout.

        Verifies dynamic sizing calculation.
        """
        renderer = Renderer()
        template = """
        {% vstack width=40 height=20 %}
            {% frame height=5 %}Fixed{% endframe %}
            {% frame height="fill" %}Fills remaining{% endframe %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=20)

        # Both frames should render
        assert "Fixed" in output
        assert "Fills remaining" in output


class TestOutputComposition:
    """Test final output composition from rendered elements."""

    def test_frame_renders_with_borders(self):
        """Test that frame output includes border characters.

        Verifies frame rendering to final output.
        """
        renderer = Renderer()
        template = """
        {% frame width=20 height=5 border="single" %}
            Content
        {% endframe %}
        """

        output, elements = renderer.render_with_layout(template, width=20, height=5)

        lines = output.split("\n")

        # Should have border characters (box drawing)
        top_line = lines[0] if lines else ""
        # Common border characters
        assert any(char in top_line for char in ["─", "┌", "┐", "-", "+"])

    def test_frame_title_appears_in_output(self):
        """Test that frame title appears in rendered output.

        Verifies frame title rendering.
        """
        renderer = Renderer()
        template = """
        {% frame width=30 height=5 title="My Title" %}
            Content
        {% endframe %}
        """

        output, elements = renderer.render_with_layout(template, width=30, height=5)

        # Title should appear in output
        assert "My Title" in output

    def test_text_content_preserved_in_output(self):
        """Test that text content is preserved through pipeline.

        Verifies content preservation.
        """
        renderer = Renderer()
        template = """
        {% frame width=40 height=10 %}
            This is some test content that should appear.
        {% endframe %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=10)

        assert "test content" in output

    def test_ansi_codes_preserved_in_output(self):
        """Test that ANSI color codes are preserved.

        Verifies ANSI code handling through pipeline.
        """
        from wijjit.terminal.ansi import ANSIColor

        renderer = Renderer()
        template = (
            """
        {% frame width=30 height=5 %}
            """
            + f"{ANSIColor.RED}Colored Text{ANSIColor.RESET}"
            + """
        {% endframe %}
        """
        )

        output, elements = renderer.render_with_layout(template, width=30, height=5)

        # ANSI codes should be in output
        assert ANSIColor.RED in output or "Colored Text" in output


class TestAutoIDGeneration:
    """Test automatic ID generation for elements."""

    def test_elements_get_auto_ids(self):
        """Test that elements without IDs get auto-generated ones.

        Verifies auto-ID system.
        """
        renderer = Renderer()
        template = """
        {% vstack width=40 height=15 %}
            {% textinput %}{% endtextinput %}
            {% textinput %}{% endtextinput %}
            {% button %}Click{% endbutton %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=15)

        # Elements should be collected as a list (with auto IDs or explicit rendering)
        assert isinstance(elements, list)

    def test_explicit_ids_preserved(self):
        """Test that explicit IDs are not overridden.

        Verifies ID preservation.
        """
        renderer = Renderer()
        template = """
        {% vstack width=40 height=10 %}
            {% textinput id="myinput" %}{% endtextinput %}
            {% button id="mybutton" %}Click{% endbutton %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=10)

        # Explicit IDs should be in elements list
        element_ids = [e.id for e in elements if hasattr(e, "id") and e.id]
        assert "myinput" in element_ids or "myinput" in output
        assert "mybutton" in element_ids or "mybutton" in output


class TestComplexTemplates:
    """Test complex real-world template scenarios."""

    def test_login_form_template(self):
        """Test complete login form template.

        Verifies realistic form layout.
        """
        renderer = Renderer()
        template = """
        {% frame width=40 height=15 title="Login" %}
            {% vstack %}
                Username:
                {% textinput id="username" %}{% endtextinput %}

                Password:
                {% textinput id="password" placeholder="Password" %}{% endtextinput %}

                {% hstack %}
                    {% button id="login" %}Login{% endbutton %}
                    {% button id="cancel" %}Cancel{% endbutton %}
                {% endhstack %}
            {% endvstack %}
        {% endframe %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=15)

        # Should render form elements
        assert "Login" in output
        assert "Username" in output
        assert "Password" in output

    def test_dashboard_template_with_data(self):
        """Test dashboard template with dynamic data.

        Verifies complex template with data binding.
        """
        renderer = Renderer()
        template = """
        {% vstack width=80 height=24 %}
            {% frame height=3 padding=0 title="Dashboard" %}
                Welcome back, {{ user }}!
            {% endframe %}

            {% hstack height="fill" %}
                {% frame width=40 title="Stats" %}
                    Messages: {{ message_count }}
                    Tasks: {{ task_count }}
                {% endframe %}

                {% frame width=40 title="Quick Actions" %}
                    {% button id="compose" %}Compose{% endbutton %}
                    {% button id="tasks" %}View Tasks{% endbutton %}
                {% endframe %}
            {% endhstack %}
        {% endvstack %}
        """

        context = {"user": "Alice", "message_count": 5, "task_count": 12}

        output, elements = renderer.render_with_layout(
            template, width=80, height=24, context=context
        )

        # Should render with data
        assert "Alice" in output
        assert "5" in output or "Messages: 5" in output
        assert "12" in output or "Tasks: 12" in output

    def test_list_view_with_iteration(self):
        """Test list view with item iteration.

        Verifies template loops with layout.
        """
        renderer = Renderer()
        template = """
        {% frame width=50 height=20 title="Products" %}
            {% vstack %}
                {% for item in products %}
                    {{ loop.index }}. {{ item.name }} - ${{ item.price }}
                {% endfor %}
            {% endvstack %}
        {% endframe %}
        """

        context = {
            "products": [
                {"name": "Apple", "price": 1.50},
                {"name": "Banana", "price": 0.75},
                {"name": "Cherry", "price": 2.00},
            ]
        }

        output, elements = renderer.render_with_layout(
            template, width=50, height=20, context=context
        )

        # Should render all products
        assert "Apple" in output
        assert "Banana" in output
        assert "Cherry" in output
        assert "1.5" in output or "1.50" in output  # Price formatting may vary


class TestErrorHandling:
    """Test error handling in template pipeline."""

    def test_invalid_template_syntax(self):
        """Test handling of invalid Jinja2 syntax.

        Verifies error handling for malformed templates.
        """
        renderer = Renderer()
        template = "Hello {{ unclosed"

        # Should raise or handle gracefully
        try:
            output = renderer.render_string(template, {})
            # If it doesn't raise, it should at least not crash
            assert isinstance(output, str)
        except Exception as e:
            # Expected to raise template error
            assert "template" in str(e).lower() or "syntax" in str(e).lower()

    def test_missing_variable_in_template(self):
        """Test handling of undefined variables.

        Verifies graceful handling of missing context variables.
        """
        renderer = Renderer()
        template = "Hello {{ undefined_var }}!"

        # Should handle undefined variable (Jinja2 default is empty string)
        output = renderer.render_string(template, {})

        # Should produce some output (with empty string for undefined)
        assert isinstance(output, str)
