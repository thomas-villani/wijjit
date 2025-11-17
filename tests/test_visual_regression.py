"""Visual regression tests using snapshot testing.

These tests capture rendered output and compare against saved snapshots
to detect unintended visual changes.

To update snapshots when changes are intentional:
    pytest tests/test_visual_regression.py --snapshot-update

Snapshots are stored in tests/__snapshots__/ directory.
"""

import pytest

from tests.helpers import render_element
from wijjit.core.renderer import Renderer
from wijjit.elements.input.button import Button
from wijjit.elements.input.text import TextInput
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import BorderStyle, Frame, FrameStyle

pytestmark = pytest.mark.visual


class TestFrameSnapshots:
    """Snapshot tests for frame rendering with various configurations."""

    def test_frame_single_border(self, snapshot):
        """Test frame with single-line border style.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.SINGLE)
        frame = Frame(width=30, height=8, style=style)
        frame.set_content("Test content with single border")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot

    def test_frame_double_border(self, snapshot):
        """Test frame with double-line border style.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.DOUBLE)
        frame = Frame(width=30, height=8, style=style)
        frame.set_content("Test content with double border")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot

    def test_frame_rounded_border(self, snapshot):
        """Test frame with rounded corner border style.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.ROUNDED)
        frame = Frame(width=30, height=8, style=style)
        frame.set_content("Test content with rounded border")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot

    def test_frame_with_padding(self, snapshot):
        """Test frame with padding on all sides.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(
            border=BorderStyle.SINGLE, padding=(1, 2, 1, 2)  # top, right, bottom, left
        )
        frame = Frame(width=35, height=10, style=style)
        frame.set_content("Padded content")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot

    def test_frame_multiline_content(self, snapshot):
        """Test frame with multi-line content.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.SINGLE)
        frame = Frame(width=40, height=12, style=style)
        frame.set_content("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot


class TestLayoutSnapshots:
    """Snapshot tests for layout combinations."""

    def test_simple_vstack_layout(self, snapshot):
        """Test simple vertical stack layout.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        renderer = Renderer()
        template = """
{% vstack width=50 height=15 %}
    {% frame height=5 title="Top" %}
        Top content
    {% endframe %}
    {% frame height=5 title="Middle" %}
        Middle content
    {% endframe %}
    {% frame height=5 title="Bottom" %}
        Bottom content
    {% endframe %}
{% endvstack %}
        """.strip()

        output, _, _ = renderer.render_with_layout(template, width=50, height=15)
        assert output == snapshot

    def test_simple_hstack_layout(self, snapshot):
        """Test simple horizontal stack layout.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        renderer = Renderer()
        template = """
{% hstack width=60 height=10 %}
    {% frame width=20 title="Left" %}
        Left
    {% endframe %}
    {% frame width=20 title="Center" %}
        Center
    {% endframe %}
    {% frame width=20 title="Right" %}
        Right
    {% endframe %}
{% endhstack %}
        """.strip()

        output, _, _ = renderer.render_with_layout(template, width=60, height=10)
        assert output == snapshot

    def test_nested_layout(self, snapshot):
        """Test nested VStack and HStack layout.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        renderer = Renderer()
        template = """
{% vstack width=70 height=20 %}
    {% hstack height=10 %}
        {% frame width=35 title="Top Left" %}
            TL Content
        {% endframe %}
        {% frame width=35 title="Top Right" %}
            TR Content
        {% endframe %}
    {% endhstack %}
    {% frame height=10 title="Bottom" %}
        Bottom content spanning full width
    {% endframe %}
{% endvstack %}
        """.strip()

        output, _, _ = renderer.render_with_layout(template, width=70, height=20)
        assert output == snapshot

    def test_percentage_width_layout(self, snapshot):
        """Test layout with percentage-based widths.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        renderer = Renderer()
        template = """
{% hstack width=60 height=10 %}
    {% frame width="30%" title="30%" %}
        Narrow
    {% endframe %}
    {% frame width="70%" title="70%" %}
        Wide
    {% endframe %}
{% endhstack %}
        """.strip()

        output, _, _ = renderer.render_with_layout(template, width=60, height=10)
        assert output == snapshot


class TestOverflowSnapshots:
    """Snapshot tests for text overflow handling."""

    def test_overflow_clip(self, snapshot):
        """Test text clipping overflow mode.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.SINGLE, overflow_x="clip")
        frame = Frame(width=25, height=5, style=style)
        frame.set_content("This is a very long line that will be clipped at the edge")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot

    def test_overflow_wrap(self, snapshot):
        """Test text wrapping overflow mode.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.SINGLE, overflow_x="wrap")
        frame = Frame(width=25, height=8, style=style)
        frame.set_content("This is a very long line that will wrap to multiple lines")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot


class TestElementSnapshots:
    """Snapshot tests for element rendering."""

    def test_button_rendering(self, snapshot):
        """Test button element rendering.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """

        button = Button(label="Click Me!", id="test_btn")
        if not button.bounds:

            button.bounds = Bounds(0, 0, 15, 1)

        output = render_element(
            button, width=button.bounds.width, height=button.bounds.height
        )

        assert output == snapshot

    def test_textinput_rendering(self, snapshot):
        """Test text input element rendering.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """

        text_input = TextInput(id="test_input", placeholder="Enter text...")
        if not text_input.bounds:

            text_input.bounds = Bounds(0, 0, 30, 1)

        output = render_element(
            text_input, width=text_input.bounds.width, height=text_input.bounds.height
        )

        assert output == snapshot

    def test_textinput_with_value(self, snapshot):
        """Test text input with value set.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """

        text_input = TextInput(id="test_input")
        text_input.value = "Current Value"
        if not text_input.bounds:

            text_input.bounds = Bounds(0, 0, 30, 1)

        output = render_element(
            text_input, width=text_input.bounds.width, height=text_input.bounds.height
        )

        assert output == snapshot


class TestComplexTemplateSnapshots:
    """Snapshot tests for complex real-world templates."""

    def test_dashboard_layout(self, snapshot):
        """Test dashboard with multiple sections.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        renderer = Renderer()
        template = """
{% vstack width=80 height=24 %}
    {% frame height=3 title="Dashboard" %}
        Welcome, User!
    {% endframe %}

    {% hstack height=15 %}
        {% frame width=40 title="Statistics" %}
            Messages: 5
            Tasks: 12
            Alerts: 2
        {% endframe %}

        {% frame width=40 title="Quick Actions" %}
            {% vstack %}
                {% button id="compose" %}Compose Message{% endbutton %}
                {% button id="tasks" %}View Tasks{% endbutton %}
                {% button id="settings" %}Settings{% endbutton %}
            {% endvstack %}
        {% endframe %}
    {% endhstack %}

    {% frame height=6 title="Recent Activity" %}
        - Task completed: Review PR #123
        - New message from Alice
        - Meeting in 30 minutes
    {% endframe %}
{% endvstack %}
        """.strip()

        output, _, _ = renderer.render_with_layout(template, width=80, height=24)
        assert output == snapshot


class TestAlignmentSnapshots:
    """Snapshot tests for content alignment."""

    def test_horizontal_align_left(self, snapshot):
        """Test left-aligned content.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.SINGLE, content_align_h="left")
        frame = Frame(width=40, height=8, style=style)
        frame.set_content("Left aligned")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot

    def test_horizontal_align_center(self, snapshot):
        """Test center-aligned content.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.SINGLE, content_align_h="center")
        frame = Frame(width=40, height=8, style=style)
        frame.set_content("Centered")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot

    def test_horizontal_align_right(self, snapshot):
        """Test right-aligned content.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border=BorderStyle.SINGLE, content_align_h="right")
        frame = Frame(width=40, height=8, style=style)
        frame.set_content("Right aligned")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot
