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
        style = FrameStyle(border_style=BorderStyle.SINGLE)
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
        style = FrameStyle(border_style=BorderStyle.DOUBLE)
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
        style = FrameStyle(border_style=BorderStyle.ROUNDED)
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
            border_style=BorderStyle.SINGLE,
            padding=(1, 2, 1, 2),  # top, right, bottom, left
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
        style = FrameStyle(border_style=BorderStyle.SINGLE)
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
        style = FrameStyle(border_style=BorderStyle.SINGLE, overflow_x="clip")
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
        style = FrameStyle(border_style=BorderStyle.SINGLE, overflow_x="wrap")
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


class TestEmittedAnsiGoldens:
    """Goldens over the RAW emitted ANSI stream, escape codes included.

    Every other golden/snapshot in the suite strips ANSI (plain-text buffer
    serializations), so SGR regressions, missing resets, and style bleed were
    previously invisible (review Part 4). These snapshot the exact byte
    stream the app writes to its backend, via the harness's recording tee.
    """

    TEMPLATE = """
{% vstack width=80 height=24 %}
    {% frame height=3 title="Emitted ANSI Golden" border="double" %}
        Styled multi-element screen
    {% endframe %}
    {% hstack height=12 %}
        {% frame width=40 title="Form" %}
            {% vstack %}
                {% textinput id="name" placeholder="Your name" %}{% endtextinput %}
                {% button id="ok" %}Submit{% endbutton %}
            {% endvstack %}
        {% endframe %}
        {% frame width=40 title="Chart" %}
            {% barchart id="chart" data=chart_data width=34 height=8 %}{% endbarchart %}
        {% endframe %}
    {% endhstack %}
{% endvstack %}
    """.strip()

    def _harness(self):
        from wijjit.testing import WijjitHarness, app_from_template

        app = app_from_template(
            self.TEMPLATE,
            context={"chart_data": [("Mon", 10), ("Tue", 25), ("Wed", 18)]},
        )
        app.config["DEFAULT_THEME"] = "dark"
        return WijjitHarness(app, size=(80, 24))

    def test_first_paint_emitted_ansi(self, snapshot):
        """The initial full paint's raw ANSI stream is stable."""
        with self._harness() as h:
            assert h.emitted_frames, "no frame was emitted"
            assert h.emitted_frames[0] == snapshot

    def test_focus_diff_emitted_ansi(self, snapshot):
        """Focusing the input emits a stable, small styled diff frame."""
        with self._harness() as h:
            h.press("tab")
            assert h.last_frame == snapshot

    def test_keystroke_diff_is_wellformed(self):
        """A one-char edit emits an absolute-positioned, reset-terminated diff.

        Not a golden: asserts structural SGR hygiene so it stays robust to
        theme changes while still catching missing resets, full-screen
        repaints on tiny edits, and relative-positioning regressions.
        """
        import re

        with self._harness() as h:
            h.press("tab")
            h.type("x")
            frame = h.last_frame

            assert frame, "keystroke emitted no frame"
            # Diff runs are anchored with absolute cursor positioning.
            assert re.search(r"\x1b\[\d+;\d+H", frame), frame
            # No full-screen clear for a one-character edit.
            assert "\x1b[2J" not in frame
            # Styles are closed out by the end of the frame.
            assert frame.rstrip().endswith("\x1b[0m")
            # Every styled run is eventually reset: after the final SGR that
            # sets attributes there must be a reset before the frame ends.
            last_set = max(
                (m.start() for m in re.finditer(r"\x1b\[[0-9;]*m", frame)),
                default=-1,
            )
            assert "\x1b[0m" in frame[last_set:] or frame[last_set:].startswith(
                "\x1b[0m"
            )


class TestAlignmentSnapshots:
    """Snapshot tests for content alignment."""

    def test_horizontal_align_left(self, snapshot):
        """Test left-aligned content.

        Parameters
        ----------
        snapshot
            Syrupy snapshot fixture
        """
        style = FrameStyle(border_style=BorderStyle.SINGLE, content_align_h="left")
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
        style = FrameStyle(border_style=BorderStyle.SINGLE, content_align_h="center")
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
        style = FrameStyle(border_style=BorderStyle.SINGLE, content_align_h="right")
        frame = Frame(width=40, height=8, style=style)
        frame.set_content("Right aligned")

        if not frame.bounds:

            frame.bounds = Bounds(0, 0, frame.width, frame.height)

        output = render_element(
            frame, width=frame.bounds.width, height=frame.bounds.height
        )
        assert output == snapshot
