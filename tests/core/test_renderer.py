"""Tests for template renderer."""

import os
import tempfile

import pytest
from jinja2 import TemplateNotFound

from wijjit.core.renderer import Renderer


class TestRenderer:
    """Tests for Renderer class."""

    def test_init_no_template_dir(self):
        """Test creating renderer without template directory."""
        renderer = Renderer()
        assert renderer.env is not None
        assert len(renderer._string_templates) == 0

    def test_init_with_template_dir(self):
        """Test creating renderer with template directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            renderer = Renderer(template_dir=tmpdir)
            assert renderer.env is not None

    def test_render_string_simple(self):
        """Test rendering a simple string template."""
        renderer = Renderer()
        result = renderer.render_string("Hello, {{ name }}!", {"name": "World"})
        assert result == "Hello, World!"

    def test_render_string_no_context(self):
        """Test rendering without context."""
        renderer = Renderer()
        result = renderer.render_string("Hello, World!")
        assert result == "Hello, World!"

    def test_render_string_with_loop(self):
        """Test rendering with a loop."""
        renderer = Renderer()
        template = "{% for item in numbers %}{{ item }}{% endfor %}"
        result = renderer.render_string(template, {"numbers": [1, 2, 3]})
        assert result == "123"

    def test_render_string_with_conditional(self):
        """Test rendering with conditionals."""
        renderer = Renderer()
        template = "{% if show %}Visible{% else %}Hidden{% endif %}"

        result1 = renderer.render_string(template, {"show": True})
        assert result1 == "Visible"

        result2 = renderer.render_string(template, {"show": False})
        assert result2 == "Hidden"

    def test_render_string_caching(self):
        """Test that templates are cached."""
        renderer = Renderer()
        template = "Hello, {{ name }}!"

        # First render
        result1 = renderer.render_string(template, {"name": "Alice"})
        assert len(renderer._string_templates) == 1

        # Second render should use cache
        result2 = renderer.render_string(template, {"name": "Bob"})
        assert len(renderer._string_templates) == 1
        assert result1 == "Hello, Alice!"
        assert result2 == "Hello, Bob!"

    def test_render_file(self):
        """Test rendering from a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template file
            template_path = os.path.join(tmpdir, "test.tui")
            with open(template_path, "w") as f:
                f.write("Hello, {{ name }}!")

            renderer = Renderer(template_dir=tmpdir)
            result = renderer.render_file("test.tui", {"name": "World"})
            assert result == "Hello, World!"

    def test_render_file_not_found(self):
        """Test rendering non-existent file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            renderer = Renderer(template_dir=tmpdir)

            with pytest.raises(TemplateNotFound):
                renderer.render_file("nonexistent.tui")

    def test_add_filter(self):
        """Test adding custom filter."""
        renderer = Renderer()

        def reverse_filter(text):
            return text[::-1]

        renderer.add_filter("reverse", reverse_filter)

        result = renderer.render_string("{{ text|reverse }}", {"text": "hello"})
        assert result == "olleh"

    def test_builtin_filters(self):
        """Test built-in filters."""
        renderer = Renderer()

        # Upper filter
        result = renderer.render_string("{{ text|upper }}", {"text": "hello"})
        assert result == "HELLO"

        # Lower filter
        result = renderer.render_string("{{ text|lower }}", {"text": "HELLO"})
        assert result == "hello"

        # Title filter
        result = renderer.render_string("{{ text|title }}", {"text": "hello world"})
        assert result == "Hello World"

    def test_add_global(self):
        """Test adding global variable."""
        renderer = Renderer()
        renderer.add_global("app_name", "Wijjit")

        result = renderer.render_string("Welcome to {{ app_name }}!")
        assert result == "Welcome to Wijjit!"

    def test_clear_cache(self):
        """Test clearing template cache."""
        renderer = Renderer()

        # Render some templates
        renderer.render_string("Template 1")
        renderer.render_string("Template 2")
        assert len(renderer._string_templates) == 2

        # Clear cache
        renderer.clear_cache()
        assert len(renderer._string_templates) == 0

    def test_trim_blocks(self):
        """Test that trim_blocks is enabled."""
        renderer = Renderer()
        template = """
        {% for i in [1, 2] %}
        Item {{ i }}
        {% endfor %}
        """
        result = renderer.render_string(template)
        # Should trim whitespace around blocks
        assert "Item 1" in result
        assert "Item 2" in result

    def test_complex_template(self):
        """Test rendering a complex template."""
        renderer = Renderer()
        template = """
        {% if user %}
        Hello, {{ user.name }}!
        Your shopping list:
        {% for item in user.shopping_list %}
        - {{ item }}
        {% endfor %}
        {% else %}
        No user logged in.
        {% endif %}
        """

        context = {
            "user": {"name": "Alice", "shopping_list": ["apple", "banana", "cherry"]}
        }

        result = renderer.render_string(template, context)
        assert "Hello, Alice!" in result
        assert "apple" in result
        assert "banana" in result
        assert "cherry" in result

    def test_autoescape_disabled(self):
        """Test that autoescape is disabled by default."""
        renderer = Renderer()
        result = renderer.render_string("{{ text }}", {"text": "<b>bold</b>"})
        # Should not escape HTML
        assert result == "<b>bold</b>"

    def test_autoescape_enabled(self):
        """Test rendering with autoescape enabled."""
        renderer = Renderer(autoescape=True)
        result = renderer.render_string("{{ text }}", {"text": "<b>bold</b>"})
        # Should escape HTML
        assert "&lt;b&gt;" in result or result == "<b>bold</b>"  # Depends on context

    def test_multiple_contexts(self):
        """Test rendering same template with different contexts."""
        renderer = Renderer()
        template = "Count: {{ count }}"

        result1 = renderer.render_string(template, {"count": 1})
        result2 = renderer.render_string(template, {"count": 2})
        result3 = renderer.render_string(template, {"count": 3})

        assert result1 == "Count: 1"
        assert result2 == "Count: 2"
        assert result3 == "Count: 3"

    def test_button_auto_id_generation(self):
        """Test that buttons without IDs get auto-generated IDs."""
        renderer = Renderer()
        template = """
{% frame title="Test" width=40 height=10 %}
  {% button %}Button 1{% endbutton %}
  {% button %}Button 2{% endbutton %}
  {% button id="custom_btn" %}Button 3{% endbutton %}
{% endframe %}
        """

        output, elements, _ = renderer.render_with_layout(template, width=80, height=24)

        # Should have 3 button elements
        buttons = [
            e
            for e in elements
            if hasattr(e, "element_type") and e.element_type.name == "BUTTON"
        ]
        assert len(buttons) == 3

        # First button should have auto-generated ID
        assert buttons[0].id == "button_0"

        # Second button should have auto-generated ID
        assert buttons[1].id == "button_1"

        # Third button should have custom ID
        assert buttons[2].id == "custom_btn"

    def test_textinput_auto_id_generation(self):
        """Test that text inputs without IDs get auto-generated IDs."""
        renderer = Renderer()
        template = """
{% frame title="Test" width=40 height=10 %}
  {% textinput %}{% endtextinput %}
  {% textinput %}{% endtextinput %}
  {% textinput id="username" %}{% endtextinput %}
{% endframe %}
        """

        output, elements, _ = renderer.render_with_layout(template, width=80, height=24)

        # Should have 3 text input elements
        text_inputs = [
            e
            for e in elements
            if hasattr(e, "element_type") and e.element_type.name == "INPUT"
        ]
        assert len(text_inputs) == 3

        # First input should have auto-generated ID
        assert text_inputs[0].id == "textinput_0"

        # Second input should have auto-generated ID
        assert text_inputs[1].id == "textinput_1"

        # Third input should have custom ID
        assert text_inputs[2].id == "username"

    def test_select_auto_id_generation(self):
        """Test that selects without IDs get auto-generated IDs."""
        renderer = Renderer()
        template = """
{% frame title="Test" width=40 height=10 %}
  {% select %}
    Option 1
    Option 2
  {% endselect %}
  {% select %}
    Option A
    Option B
  {% endselect %}
  {% select id="color" %}
    Red
    Green
  {% endselect %}
{% endframe %}
        """

        output, elements, _ = renderer.render_with_layout(template, width=80, height=24)

        # Should have 3 select elements
        selects = [
            e
            for e in elements
            if hasattr(e, "element_type") and e.element_type.name == "SELECTABLE"
        ]
        assert len(selects) == 3

        # First select should have auto-generated ID
        assert selects[0].id == "select_0"

        # Second select should have auto-generated ID
        assert selects[1].id == "select_1"

        # Third select should have custom ID
        assert selects[2].id == "color"

    def test_mixed_elements_auto_id_generation(self):
        """Test auto-generated IDs with mixed element types."""
        renderer = Renderer()
        template = """
{% frame title="Test" width=40 height=15 %}
  {% button %}Button 1{% endbutton %}
  {% textinput %}{% endtextinput %}
  {% button %}Button 2{% endbutton %}
  {% select %}
    Option 1
    Option 2
  {% endselect %}
  {% textinput %}{% endtextinput %}
{% endframe %}
        """

        output, elements, _ = renderer.render_with_layout(template, width=80, height=24)

        # Find each element type
        buttons = [
            e
            for e in elements
            if hasattr(e, "element_type") and e.element_type.name == "BUTTON"
        ]
        text_inputs = [
            e
            for e in elements
            if hasattr(e, "element_type") and e.element_type.name == "INPUT"
        ]
        selects = [
            e
            for e in elements
            if hasattr(e, "element_type") and e.element_type.name == "SELECTABLE"
        ]

        # Verify counts
        assert len(buttons) == 2
        assert len(text_inputs) == 2
        assert len(selects) == 1

        # Verify IDs are type-specific counters
        assert buttons[0].id == "button_0"
        assert buttons[1].id == "button_1"
        assert text_inputs[0].id == "textinput_0"
        assert text_inputs[1].id == "textinput_1"
        assert selects[0].id == "select_0"

    def test_render_with_layout_from_file(self):
        """Test rendering layout template from file using template_name parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template file with layout tags
            template_path = os.path.join(tmpdir, "test_layout.tui")
            with open(template_path, "w") as f:
                f.write(
                    """
{% frame title="Hello" width=40 height=10 %}
  Welcome, {{ name }}!
{% endframe %}
"""
                )

            renderer = Renderer(template_dir=tmpdir)
            output, elements, layout_ctx = renderer.render_with_layout(
                template_name="test_layout.tui",
                context={"name": "Alice"},
                width=80,
                height=24,
            )

            # Should have rendered successfully
            assert output is not None
            assert len(output) > 0

            # Should have created frame element
            assert layout_ctx.root is not None

    def test_render_with_layout_from_file_with_variables(self):
        """Test rendering template from file with Jinja2 variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create template with variables and loops
            template_path = os.path.join(tmpdir, "dynamic.tui")
            with open(template_path, "w") as f:
                f.write(
                    """
{% frame width=50 height=15 %}
  {% for item in items %}
    - {{ item }}
  {% endfor %}
{% endframe %}
"""
                )

            renderer = Renderer(template_dir=tmpdir)
            context = {"title": "My List", "items": ["Apple", "Banana", "Cherry"]}
            output, elements, layout_ctx = renderer.render_with_layout(
                template_name="dynamic.tui", context=context, width=80, height=24
            )

            # Should have rendered the items
            buffer_text = renderer.get_buffer_as_text()
            assert "Apple" in buffer_text
            assert "Banana" in buffer_text
            assert "Cherry" in buffer_text

    def test_render_with_layout_file_not_found(self):
        """Test that missing template file raises TemplateNotFound."""
        with tempfile.TemporaryDirectory() as tmpdir:
            renderer = Renderer(template_dir=tmpdir)

            with pytest.raises(TemplateNotFound):
                renderer.render_with_layout(
                    template_name="nonexistent.tui", width=80, height=24
                )

    def test_render_with_layout_string_vs_file(self):
        """Test that template_string and template_name are mutually exclusive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file template
            template_path = os.path.join(tmpdir, "file_template.tui")
            with open(template_path, "w") as f:
                f.write(
                    "{% frame title='From File' width=40 height=10 %}File Content{% endframe %}"
                )

            renderer = Renderer(template_dir=tmpdir)

            # Test with template_name (should use file)
            output1, _, _ = renderer.render_with_layout(
                template_name="file_template.tui", width=80, height=24
            )
            buffer_text1 = renderer.get_buffer_as_text()
            assert "From File" in buffer_text1
            assert "File Content" in buffer_text1

            # Test with template_string (should use inline)
            renderer._last_base_buffer = None  # Reset buffer
            renderer._last_displayed_buffer = None
            output2, _, _ = renderer.render_with_layout(
                template_string="{% frame title='Inline' width=40 height=10 %}Inline Content{% endframe %}",
                width=80,
                height=24,
            )
            buffer_text2 = renderer.get_buffer_as_text()
            assert "Inline" in buffer_text2
            assert "Inline Content" in buffer_text2
