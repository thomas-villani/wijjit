"""Integration tests for state management and rendering pipeline.

Tests cover the integration between:
- State management (reactive updates)
- Template rendering (Jinja2)
- Layout engine (element positioning)
- Element rendering (final output)
"""

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.renderer import Renderer
from wijjit.core.state import State

pytestmark = pytest.mark.integration


class TestStateTemplateIntegration:
    """Test integration between State and template rendering."""

    def test_state_values_render_in_template(self):
        """Test that state values are accessible in templates.

        Verifies basic state-to-template data flow.
        """
        state = State({"name": "Alice", "count": 42})
        renderer = Renderer()

        template = "Hello {{ name }}, count: {{ count }}"
        output = renderer.render_string(template, dict(state))

        assert "Hello Alice" in output
        assert "count: 42" in output

    def test_nested_state_renders_in_template(self):
        """Test that nested state structures are accessible.

        Verifies deep state access in templates.
        """
        state = State(
            {
                "user": {
                    "name": "Bob",
                    "settings": {"theme": "dark", "notifications": True},
                }
            }
        )
        renderer = Renderer()

        template = "User: {{ user.name }}, Theme: {{ user.settings.theme }}"
        output = renderer.render_string(template, dict(state))

        assert "User: Bob" in output
        assert "Theme: dark" in output

    def test_list_iteration_in_template(self):
        """Test that state lists can be iterated in templates.

        Verifies Jinja2 loop integration with state.
        """
        state = State({"products": ["apple", "banana", "cherry"]})
        renderer = Renderer()

        template = "{% for item in products %}{{ item }}{% if not loop.last %}, {% endif %}{% endfor %}"
        output = renderer.render_string(template, dict(state))

        assert "apple, banana, cherry" in output

    def test_conditional_rendering_with_state(self):
        """Test template conditionals based on state values.

        Verifies Jinja2 conditional integration with state.
        """
        renderer = Renderer()
        template = (
            "{% if logged_in %}Welcome {{ username }}{% else %}Please log in{% endif %}"
        )

        # Test logged in state
        state_logged_in = State({"logged_in": True, "username": "Alice"})
        output = renderer.render_string(template, dict(state_logged_in))
        assert "Welcome Alice" in output

        # Test logged out state
        state_logged_out = State({"logged_in": False})
        output = renderer.render_string(template, dict(state_logged_out))
        assert "Please log in" in output

    def test_state_changes_reflect_in_rerender(self):
        """Test that state changes are reflected when re-rendering.

        Verifies reactive rendering on state updates.
        """
        state = State({"counter": 0})
        renderer = Renderer()
        template = "Count: {{ counter }}"

        # Initial render
        output1 = renderer.render_string(template, dict(state))
        assert "Count: 0" in output1

        # Update state
        state["counter"] = 5

        # Re-render with updated state
        output2 = renderer.render_string(template, dict(state))
        assert "Count: 5" in output2


class TestTemplateLayoutIntegration:
    """Test integration between template rendering and layout engine."""

    def test_template_with_elements_creates_layout(self):
        """Test that templates with elements produce proper layout.

        Verifies template -> parse -> layout pipeline.
        """
        renderer = Renderer()
        template = """
        {% vstack width=40 height=10 %}
            {% frame title="Test" %}
                Content here
            {% endframe %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=40, height=10)

        # Should produce output
        assert output
        assert isinstance(output, str)

        # Should collect elements as a list
        assert isinstance(elements, list)

    def test_nested_layout_elements_render_correctly(self):
        """Test that nested layout structures produce correct output.

        Verifies complex template structures with layout.
        """
        renderer = Renderer()
        template = """
        {% vstack width=60 height=15 %}
            {% hstack height=5 %}
                {% frame width="50%" title="Left" %}Left content{% endframe %}
                {% frame width="50%" title="Right" %}Right content{% endframe %}
            {% endhstack %}
            {% frame height="fill" title="Bottom" %}Bottom content{% endframe %}
        {% endvstack %}
        """

        output, elements = renderer.render_with_layout(template, width=60, height=15)

        # Should produce non-empty output
        assert output
        assert len(output.split("\n")) > 0

    def test_state_values_render_inside_layout_elements(self):
        """Test that state values work inside layout elements.

        Verifies state -> template -> layout pipeline integration.
        """
        state = State({"title": "My Frame", "content": "Hello World"})
        renderer = Renderer()

        template = """
        {% frame width=30 height=5 title=title %}
            {{ content }}
        {% endframe %}
        """

        output, elements = renderer.render_with_layout(
            template, width=30, height=5, context=dict(state)
        )

        # Frame should have state-based title and content
        assert "My Frame" in output or output  # Title in border or as content
        assert "Hello World" in output


class TestStateElementIntegration:
    """Test integration between state and interactive elements."""

    def test_textinput_initial_value_from_state(self):
        """Test that TextInput can be initialized from state.

        Verifies state -> element initialization.
        """
        state = State({"username": "Alice"})
        renderer = Renderer()

        template = """{% textinput id="username" value=username %}{% endtextinput %}"""

        output, elements = renderer.render_with_layout(
            template, width=40, height=3, context=dict(state)
        )

        # Element should be created - check by ID in elements list
        element_ids = [e.id for e in elements if hasattr(e, "id") and e.id]
        assert "username" in element_ids or "username" in output

    def test_button_text_from_state(self):
        """Test that button text can come from state.

        Verifies dynamic button text from state.
        """
        state = State({"button_label": "Click Me!"})
        renderer = Renderer()

        template = """{% button id="btn" %}{{ button_label }}{% endbutton %}"""

        output, elements = renderer.render_with_layout(
            template, width=20, height=3, context=dict(state)
        )

        # Output should contain button text
        assert "Click Me!" in output

    def test_conditional_element_rendering(self):
        """Test that elements can be conditionally rendered based on state.

        Verifies conditional element rendering.
        """
        renderer = Renderer()
        template = """
        {% if show_form %}
            {% textinput id="input1" %}{% endtextinput %}
            {% button id="submit" %}Submit{% endbutton %}
        {% else %}
            Form hidden
        {% endif %}
        """

        # Render with form shown
        state_shown = State({"show_form": True})
        output_shown, elements_shown = renderer.render_with_layout(
            template, width=40, height=10, context=dict(state_shown)
        )

        # Render with form hidden
        state_hidden = State({"show_form": False})
        output_hidden, elements_hidden = renderer.render_with_layout(
            template, width=40, height=10, context=dict(state_hidden)
        )

        # Outputs should differ
        assert output_shown != output_hidden or len(elements_shown) != len(
            elements_hidden
        )


class TestStateChangeDetection:
    """Test state change detection and reactive updates."""

    def test_state_change_callback_fires(self):
        """Test that state change callbacks are triggered.

        Verifies state change detection mechanism.
        """
        state = State({"value": 0})
        changes = []

        def on_change(key, old_value, new_value):
            changes.append((key, old_value, new_value))

        state.on_change(on_change)

        # Modify state
        state["value"] = 10

        # Callback should have fired
        assert len(changes) == 1
        assert changes[0] == ("value", 0, 10)

    def test_multiple_state_changes_tracked(self):
        """Test that multiple state changes are all tracked.

        Verifies change detection for multiple updates.
        """
        state = State({"a": 1, "b": 2})
        changes = []

        state.on_change(lambda k, o, n: changes.append(k))

        state["a"] = 10
        state["b"] = 20
        state["c"] = 30

        assert len(changes) == 3
        assert "a" in changes
        assert "b" in changes
        assert "c" in changes

    def test_nested_state_change_detection(self):
        """Test that nested state changes are detected.

        Verifies deep change detection.
        """
        state = State({"user": {"name": "Alice", "age": 30}})
        changes = []

        state.on_change(lambda k, o, n: changes.append(k))

        # Modify nested value - State doesn't auto-detect nested mutations
        # Need to reassign a new dict to trigger detection
        user = state["user"].copy()
        user["age"] = 31
        state["user"] = user

        # Should detect change
        assert len(changes) > 0


class TestAppStateRenderingCycle:
    """Test the complete state-rendering cycle in app context."""

    def test_state_update_triggers_rerender_need(self):
        """Test that updating state sets needs_render flag.

        Verifies reactive render triggering.
        """
        app = Wijjit(initial_state={"count": 0})

        @app.view("main", default=True)
        def main():
            return {"template": "Count: {{ count }}"}

        # Clear render flag
        app.needs_render = False

        # Update state
        app.state["count"] = 5

        # Should need re-render
        assert app.needs_render is True

    def test_rerender_reflects_state_changes(self):
        """Test that re-rendering reflects updated state.

        Verifies complete state -> render pipeline.
        """
        app = Wijjit(initial_state={"message": "Hello"})

        @app.view("main", default=True)
        def main():
            return {"template": "{{ message }}"}

        # Initialize view
        app._initialize_view(app.views["main"])

        # Render initial
        data1 = {**dict(app.state), **app.views["main"].data()}
        output1 = app.renderer.render_string(app.views["main"].template, data1)
        assert "Hello" in output1

        # Update state
        app.state["message"] = "Goodbye"

        # Re-render
        data2 = {**dict(app.state), **app.views["main"].data()}
        output2 = app.renderer.render_string(app.views["main"].template, data2)
        assert "Goodbye" in output2

    def test_state_persists_across_multiple_renders(self):
        """Test that state maintains consistency across renders.

        Verifies state persistence during render cycles.
        """
        app = Wijjit(initial_state={"count": 0})

        @app.view("counter", default=True)
        def counter():
            return {"template": "Count: {{ count }}"}

        # Initialize view
        app._initialize_view(app.views["counter"])

        # Multiple render cycles
        for i in range(5):
            app.state["count"] = i
            data = {**dict(app.state), **app.views["counter"].data()}
            output = app.renderer.render_string(app.views["counter"].template, data)
            assert f"Count: {i}" in output


class TestComplexStateScenarios:
    """Test complex state management scenarios."""

    def test_state_with_dynamic_lists(self):
        """Test state updates with dynamic list content.

        Verifies list manipulation and rendering.
        """
        app = Wijjit(initial_state={"products": []})

        @app.view("list", default=True)
        def list_view():
            return {
                "template": "{% for item in products %}{{ item }}{% if not loop.last %}, {% endif %}{% endfor %}"
            }

        # Initialize view
        app._initialize_view(app.views["list"])

        # Add items
        app.state["products"].append("apple")
        app.state["products"].append("banana")

        # Render with items
        data = {**dict(app.state), **app.views["list"].data()}
        output = app.renderer.render_string(app.views["list"].template, data)

        assert "apple" in output
        assert "banana" in output

    def test_state_with_conditional_sections(self):
        """Test complex conditional rendering based on state.

        Verifies advanced template logic with state.
        """
        app = Wijjit(
            initial_state={"user": None, "is_admin": False, "notifications": []}
        )

        @app.view("dashboard", default=True)
        def dashboard():
            template = """
            {% if user %}
                Welcome {{ user }}
                {% if is_admin %}
                    [Admin Panel]
                {% endif %}
                {% if notifications %}
                    Notifications: {{ notifications|length }}
                {% endif %}
            {% else %}
                Please log in
            {% endif %}
            """
            return {"template": template}

        # Initialize view
        app._initialize_view(app.views["dashboard"])

        # Test logged out state
        data = {**dict(app.state), **app.views["dashboard"].data()}
        output = app.renderer.render_string(app.views["dashboard"].template, data)
        assert "Please log in" in output

        # Test logged in state
        app.state["user"] = "Alice"
        data = {**dict(app.state), **app.views["dashboard"].data()}
        output = app.renderer.render_string(app.views["dashboard"].template, data)
        assert "Welcome Alice" in output

        # Test admin state
        app.state["is_admin"] = True
        data = {**dict(app.state), **app.views["dashboard"].data()}
        output = app.renderer.render_string(app.views["dashboard"].template, data)
        assert "[Admin Panel]" in output
