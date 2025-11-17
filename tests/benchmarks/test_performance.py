"""Performance benchmarks for Wijjit framework.

These tests measure performance of critical operations:
- Layout calculations
- Template rendering
- Element rendering
- Large dataset handling
- State updates

Run benchmarks with:
    pytest tests/benchmarks/ --benchmark-only

Generate comparison:
    pytest tests/benchmarks/ --benchmark-compare
"""

import os

import pytest

# Disable diff rendering for benchmarks - benchmarks repeatedly render identical
# content, which triggers the diff renderer to skip output since nothing changed.
# Benchmarks should measure full render performance, not diff performance.
os.environ["WIJJIT_DIFF_RENDERING"] = "false"

from tests.helpers import render_element
from wijjit.core.app import Wijjit
from wijjit.core.renderer import Renderer
from wijjit.core.state import State
from wijjit.elements.display.tree import Tree
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import Frame, FrameStyle

pytestmark = pytest.mark.benchmark


class TestLayoutPerformance:
    """Benchmark layout calculation performance."""

    def test_simple_vstack_layout(self, benchmark):
        """Benchmark simple vertical stack layout calculation.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% vstack width=60 height=20 %}
    {% frame height=5 %}Frame 1{% endframe %}
    {% frame height=5 %}Frame 2{% endframe %}
    {% frame height=5 %}Frame 3{% endframe %}
    {% frame height=5 %}Frame 4{% endframe %}
{% endvstack %}
        """

        result = benchmark(renderer.render_with_layout, template, width=60, height=20)
        assert result[0]  # Should produce output

    def test_complex_nested_layout(self, benchmark):
        """Benchmark complex nested layout calculation.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% vstack width=80 height=24 %}
    {% hstack height=8 %}
        {% vstack width=40 %}
            {% frame height=4 %}A{% endframe %}
            {% frame height=4 %}B{% endframe %}
        {% endvstack %}
        {% vstack width=40 %}
            {% frame height=4 %}C{% endframe %}
            {% frame height=4 %}D{% endframe %}
        {% endvstack %}
    {% endhstack %}
    {% hstack height=8 %}
        {% frame width=20 %}E{% endframe %}
        {% frame width=20 %}F{% endframe %}
        {% frame width=20 %}G{% endframe %}
        {% frame width=20 %}H{% endframe %}
    {% endhstack %}
    {% frame height=8 %}I{% endframe %}
{% endvstack %}
        """

        result = benchmark(renderer.render_with_layout, template, width=80, height=24)
        assert result[0]

    def test_percentage_based_layout(self, benchmark):
        """Benchmark percentage-based sizing calculations.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% hstack width=100 height=20 %}
    {% frame width="25%" %}25%{% endframe %}
    {% frame width="50%" %}50%{% endframe %}
    {% frame width="25%" %}25%{% endframe %}
{% endhstack %}
        """

        result = benchmark(renderer.render_with_layout, template, width=100, height=20)
        assert result[0]

    def test_fill_sizing_calculation(self, benchmark):
        """Benchmark fill sizing calculations.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% vstack width=60 height=30 %}
    {% frame height=10 %}Fixed{% endframe %}
    {% frame height="fill" %}Fill 1{% endframe %}
    {% frame height="fill" %}Fill 2{% endframe %}
    {% frame height=5 %}Fixed{% endframe %}
{% endvstack %}
        """

        result = benchmark(renderer.render_with_layout, template, width=60, height=30)
        assert result[0]


class TestRenderingPerformance:
    """Benchmark rendering performance."""

    def test_frame_rendering(self, benchmark):
        """Benchmark frame rendering with borders.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        style = FrameStyle(title="Test Frame")
        frame = Frame(width=40, height=15, style=style)
        frame.set_content("Test content" * 10)

        result = benchmark(frame.render)
        assert result

    def test_template_rendering(self, benchmark):
        """Benchmark template string rendering.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = "Hello {{ name }}, you have {{ count }} messages"
        context = {"name": "Alice", "count": 42}

        result = benchmark(renderer.render_string, template, context)
        assert result

    def test_complex_template_rendering(self, benchmark):
        """Benchmark complex template with loops and conditionals.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% for item in data_items %}
    {% if item.active %}
        {{ item.name }}: {{ item.value }}
    {% endif %}
{% endfor %}
        """
        context = {
            "data_items": [
                {"name": f"Item {i}", "value": i * 10, "active": i % 2 == 0}
                for i in range(50)
            ]
        }

        result = benchmark(renderer.render_string, template, context)
        assert result


class TestStatePerformance:
    """Benchmark state management performance."""

    def test_state_creation(self, benchmark):
        """Benchmark state object creation.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        initial_data = {f"key_{i}": i for i in range(100)}
        result = benchmark(State, initial_data)
        assert result

    def test_state_updates(self, benchmark):
        """Benchmark state update operations.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        state = State({f"key_{i}": i for i in range(100)})

        def update_state():
            for i in range(10):
                state[f"key_{i}"] = i * 2

        benchmark(update_state)

    def test_state_with_callbacks(self, benchmark):
        """Benchmark state updates with change callbacks.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        state = State({"count": 0})
        callback_count = [0]

        def on_change(key, old, new):
            callback_count[0] += 1

        state.on_change(on_change)

        def update_with_callbacks():
            for i in range(20):
                state["count"] = i

        benchmark(update_with_callbacks)
        assert callback_count[0] > 0


class TestLargeDatasetPerformance:
    """Benchmark performance with large datasets."""

    def test_large_tree_rendering(self, benchmark):
        """Benchmark rendering tree with many nodes.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        # Create tree with 100 items
        items = [
            {"label": f"Item {i}", "value": str(i), "type": "file"} for i in range(100)
        ]

        tree = Tree(data=items, height=20)
        tree.bounds = Bounds(0, 0, 80, 20)

        def render_tree():
            return render_element(tree, width=80, height=20)

        result = benchmark(render_tree)
        assert result

    def test_deeply_nested_tree(self, benchmark):
        """Benchmark rendering deeply nested tree structure.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """

        # Create nested tree structure
        def create_nested_tree(depth, breadth):
            if depth == 0:
                return {"label": "Leaf", "value": "leaf", "type": "file"}
            return {
                "label": f"Level {depth}",
                "value": f"level_{depth}",
                "type": "folder",
                "children": [
                    create_nested_tree(depth - 1, breadth) for _ in range(breadth)
                ],
            }

        items = [create_nested_tree(4, 3)]  # Depth 4, 3 children per level
        tree = Tree(data=items, height=20)
        tree.bounds = Bounds(0, 0, 80, 20)

        def render_tree():
            return render_element(tree, width=80, height=20)

        result = benchmark(render_tree)
        assert result

    def test_large_list_template(self, benchmark):
        """Benchmark template rendering with large list iteration.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% for item in entries %}
{{ item }}
{% endfor %}
        """
        context = {"entries": [f"Item {i}" for i in range(500)]}

        result = benchmark(renderer.render_string, template, context)
        assert result


class TestAppPerformance:
    """Benchmark full app operations."""

    def test_app_initialization(self, benchmark):
        """Benchmark app initialization time.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        result = benchmark(Wijjit)
        assert result

    def test_view_registration(self, benchmark):
        """Benchmark view registration performance.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """

        def register_views():
            app = Wijjit()

            @app.view("view1")
            def view1():
                return {"template": "View 1"}

            @app.view("view2")
            def view2():
                return {"template": "View 2"}

            @app.view("view3")
            def view3():
                return {"template": "View 3"}

            return app

        result = benchmark(register_views)
        assert result

    def test_view_navigation(self, benchmark):
        """Benchmark view navigation performance.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        app = Wijjit()

        @app.view("view1", default=True)
        def view1():
            return {"template": "View 1"}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        def navigate_between_views():
            app.navigate("view2")
            app.navigate("view1")

        benchmark(navigate_between_views)

    def test_complete_render_cycle(self, benchmark):
        """Benchmark complete state change -> re-render cycle.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        app = Wijjit(initial_state={"count": 0})

        @app.view("main", default=True)
        def main():
            return {"template": "Count: {{ count }}"}

        app._initialize_view(app.views["main"])

        def render_cycle():
            # Update state
            app.state["count"] += 1

            # Render view
            data = {**dict(app.state), **app.views["main"].data()}
            output = app.renderer.render_string(app.views["main"].template, data)
            return output

        result = benchmark(render_cycle)
        assert result


class TestStressTests:
    """Stress tests with extreme parameters."""

    def test_very_wide_layout(self, benchmark):
        """Benchmark layout with very wide dimensions.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% frame width=200 height=10 %}
    Very wide frame content
{% endframe %}
        """

        result = benchmark(renderer.render_with_layout, template, width=200, height=10)
        assert result[0]

    def test_very_tall_layout(self, benchmark):
        """Benchmark layout with very tall dimensions.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()
        template = """
{% frame width=40 height=100 %}
    Very tall frame content
{% endframe %}
        """

        result = benchmark(renderer.render_with_layout, template, width=40, height=100)
        assert result[0]

    def test_many_siblings(self, benchmark):
        """Benchmark layout with many sibling elements.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        renderer = Renderer()

        # Generate template with 50 frame siblings
        frames = "\n".join(
            [f"{{% frame height=2 %}}Frame {i}{{% endframe %}}" for i in range(50)]
        )
        template = f"""
{{% vstack width=60 height=100 %}}
    {frames}
{{% endvstack %}}
        """

        result = benchmark(renderer.render_with_layout, template, width=60, height=100)
        assert result[0]

    def test_rapid_state_updates(self, benchmark):
        """Benchmark rapid sequential state updates.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        state = State({"counter": 0})

        def rapid_updates():
            for i in range(100):
                state["counter"] = i

        benchmark(rapid_updates)


class TestANSIPerformance:
    """Benchmark ANSI code handling performance."""

    def test_ansi_strip_performance(self, benchmark):
        """Benchmark ANSI code stripping.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.terminal.ansi import ANSIColor, strip_ansi

        text = (
            f"{ANSIColor.RED}Red {ANSIColor.GREEN}Green {ANSIColor.BLUE}Blue{ANSIColor.RESET}"
            * 100
        )

        result = benchmark(strip_ansi, text)
        assert result

    def test_visible_length_calculation(self, benchmark):
        """Benchmark visible length calculation with ANSI codes.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.terminal.ansi import ANSIColor, visible_length

        text = (
            f"{ANSIColor.RED}Colored {ANSIColor.GREEN}text {ANSIColor.BLUE}here{ANSIColor.RESET}"
            * 50
        )

        result = benchmark(visible_length, text)
        assert isinstance(result, int)

    def test_clip_with_ansi_preservation(self, benchmark):
        """Benchmark text clipping with ANSI code preservation.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.terminal.ansi import ANSIColor, clip_to_width

        text = (
            f"{ANSIColor.RED}This is a very long line with colors{ANSIColor.RESET}" * 10
        )

        result = benchmark(clip_to_width, text, 50)
        assert result


class TestDirtyRegionPerformance:
    """Benchmark dirty region tracking and merging performance."""

    def test_dirty_region_single_add(self, benchmark):
        """Benchmark adding a single dirty region.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.layout.dirty import DirtyRegionManager

        manager = DirtyRegionManager()

        def add_region():
            manager.mark_dirty(10, 10, 20, 5)
            manager.clear()

        benchmark(add_region)

    def test_dirty_region_non_overlapping_regions(self, benchmark):
        """Benchmark adding multiple non-overlapping regions.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.layout.dirty import DirtyRegionManager

        manager = DirtyRegionManager()

        def add_regions():
            # Add 50 non-overlapping 5x5 regions across a 200x100 screen
            for i in range(50):
                x = (i * 10) % 190
                y = ((i * 10) // 190) * 10
                manager.mark_dirty(x, y, 5, 5)
            manager.clear()

        benchmark(add_regions)

    def test_dirty_region_overlapping_regions(self, benchmark):
        """Benchmark adding many overlapping regions that require merging.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.layout.dirty import DirtyRegionManager

        manager = DirtyRegionManager()

        def add_overlapping():
            # Add 100 overlapping regions in the same area (worst case for merging)
            for i in range(100):
                manager.mark_dirty(10 + i % 10, 10 + i % 5, 20, 5)
            manager.clear()

        benchmark(add_overlapping)

    def test_dirty_region_adjacent_regions(self, benchmark):
        """Benchmark merging adjacent regions.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.layout.dirty import DirtyRegionManager

        manager = DirtyRegionManager()

        def add_adjacent():
            # Add 20 horizontally adjacent regions (should merge into 1)
            for i in range(20):
                manager.mark_dirty(i * 4, 10, 4, 5)
            manager.clear()

        benchmark(add_adjacent)

    def test_dirty_region_realistic_ui_updates(self, benchmark):
        """Benchmark realistic UI update pattern with mixed regions.

        Parameters
        ----------
        benchmark
            Pytest-benchmark fixture
        """
        from wijjit.layout.dirty import DirtyRegionManager

        manager = DirtyRegionManager()

        def realistic_update():
            # Simulate typical UI update pattern:
            # - Focus change (2 regions)
            # - Button update (1 region)
            # - Status bar update (1 region)
            # - Notification (1 region)
            manager.mark_dirty(10, 5, 30, 3)  # Old focus
            manager.mark_dirty(10, 10, 30, 3)  # New focus
            manager.mark_dirty(45, 15, 15, 3)  # Button
            manager.mark_dirty(0, 23, 80, 1)  # Status bar
            manager.mark_dirty(60, 2, 18, 5)  # Notification
            manager.clear()

        benchmark(realistic_update)
