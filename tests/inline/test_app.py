"""Tests for InlineApp class."""

import asyncio
import io
import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

from wijjit.inline.app import InlineApp
from wijjit.core.state import State


class TestInlineAppInit:
    """Tests for InlineApp initialization."""

    def test_init_default_values(self):
        """Test InlineApp initializes with default values."""
        app = InlineApp("template")

        assert app._template == "template"
        assert app._height_spec == "auto"
        assert app._width is None
        assert app._refresh_interval == 0.1
        assert app._running is False
        assert app._needs_render is True

    def test_init_with_height(self):
        """Test InlineApp with fixed height."""
        app = InlineApp("template", height=10)

        assert app._height_spec == 10

    def test_init_with_width(self):
        """Test InlineApp with fixed width."""
        app = InlineApp("template", width=60)

        assert app._width == 60

    def test_init_with_initial_state(self):
        """Test InlineApp with initial state."""
        app = InlineApp("template", initial_state={"count": 0, "name": "test"})

        assert app.state["count"] == 0
        assert app.state["name"] == "test"

    def test_init_with_refresh_interval(self):
        """Test InlineApp with custom refresh interval."""
        app = InlineApp("template", refresh_interval=0.05)

        assert app._refresh_interval == 0.05


class TestInlineAppState:
    """Tests for InlineApp state management."""

    def test_state_property(self):
        """Test state property returns State object."""
        app = InlineApp("template")

        assert isinstance(app.state, State)

    def test_state_change_triggers_render_flag(self):
        """Test state changes set _needs_render flag."""
        app = InlineApp("template", initial_state={"count": 0})
        app._needs_render = False  # Reset flag

        app.state["count"] = 1

        assert app._needs_render is True

    def test_state_attribute_access(self):
        """Test state values via attribute access."""
        app = InlineApp("template", initial_state={"value": 42})

        assert app.state.value == 42

        app.state.value = 100
        assert app.state["value"] == 100


class TestInlineAppRefresh:
    """Tests for InlineApp refresh method."""

    def test_refresh_sets_needs_render(self):
        """Test refresh() sets _needs_render flag."""
        app = InlineApp("template")
        app._needs_render = False

        with patch.object(app, "_render"):
            app.refresh()

        assert app._needs_render is True

    def test_refresh_calls_render(self):
        """Test refresh() calls _render()."""
        app = InlineApp("template")

        with patch.object(app, "_render") as mock_render:
            app.refresh()

        mock_render.assert_called_once()


class TestInlineAppSpinnerFrames:
    """Tests for InlineApp spinner animation support."""

    def test_advance_spinner_frames_no_spinners(self):
        """Test advancing frames with no spinner elements."""
        app = InlineApp("template")
        app._positioned_elements = []

        result = app._advance_spinner_frames()

        assert result is False

    def test_advance_spinner_frames_with_spinner(self):
        """Test advancing frames with active spinner."""
        from wijjit.elements.display.spinner import Spinner

        app = InlineApp("template")
        spinner = Spinner(active=True)
        app._positioned_elements = [spinner]

        result = app._advance_spinner_frames()

        assert result is True

    def test_advance_spinner_frames_inactive_spinner(self):
        """Test inactive spinner is not advanced."""
        from wijjit.elements.display.spinner import Spinner

        app = InlineApp("template")
        spinner = Spinner(active=False)
        app._positioned_elements = [spinner]

        result = app._advance_spinner_frames()

        assert result is False


class TestInlineAppContextManager:
    """Tests for InlineApp async context manager."""

    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        """Test __aenter__ returns self."""
        app = InlineApp("Test", height=1, width=40)

        # Mock stdout and terminal size
        mock_stdout = io.StringIO()
        with patch("sys.stdout", mock_stdout):
            with patch("shutil.get_terminal_size", return_value=Mock(columns=80, lines=24)):
                try:
                    result = await app.__aenter__()
                    assert result is app
                finally:
                    # Cleanup
                    app._running = False
                    if app._refresh_task:
                        app._refresh_task.cancel()
                        try:
                            await app._refresh_task
                        except asyncio.CancelledError:
                            pass

    @pytest.mark.asyncio
    async def test_aenter_starts_refresh_task(self):
        """Test __aenter__ starts refresh task."""
        app = InlineApp("Test", height=1, width=40)

        mock_stdout = io.StringIO()
        with patch("sys.stdout", mock_stdout):
            with patch("shutil.get_terminal_size", return_value=Mock(columns=80, lines=24)):
                try:
                    await app.__aenter__()
                    assert app._running is True
                    assert app._refresh_task is not None
                finally:
                    app._running = False
                    if app._refresh_task:
                        app._refresh_task.cancel()
                        try:
                            await app._refresh_task
                        except asyncio.CancelledError:
                            pass

    @pytest.mark.asyncio
    async def test_aexit_stops_running(self):
        """Test __aexit__ stops the app."""
        app = InlineApp("Test", height=1, width=40)

        mock_stdout = io.StringIO()
        with patch("sys.stdout", mock_stdout):
            with patch("shutil.get_terminal_size", return_value=Mock(columns=80, lines=24)):
                await app.__aenter__()
                await app.__aexit__(None, None, None)

                assert app._running is False

    @pytest.mark.asyncio
    async def test_aexit_cancels_refresh_task(self):
        """Test __aexit__ cancels refresh task."""
        app = InlineApp("Test", height=1, width=40)

        mock_stdout = io.StringIO()
        with patch("sys.stdout", mock_stdout):
            with patch("shutil.get_terminal_size", return_value=Mock(columns=80, lines=24)):
                await app.__aenter__()
                refresh_task = app._refresh_task
                await app.__aexit__(None, None, None)

                assert refresh_task.cancelled() or refresh_task.done()

    @pytest.mark.asyncio
    async def test_full_context_manager_usage(self):
        """Test complete async with usage."""
        template = "Count: {{ state.count }}"

        mock_stdout = io.StringIO()
        with patch("sys.stdout", mock_stdout):
            with patch("shutil.get_terminal_size", return_value=Mock(columns=80, lines=24)):
                async with InlineApp(template, height=1, width=40, initial_state={"count": 0}) as app:
                    app.state.count = 5
                    # Brief pause to allow render
                    await asyncio.sleep(0.01)

        # App should have cleaned up
        assert app._running is False


class TestInlineAppRender:
    """Tests for InlineApp rendering."""

    def test_render_updates_needs_render_flag(self):
        """Test _render() clears _needs_render flag."""
        template = "{% frame %}Test{% endframe %}"
        app = InlineApp(template, height=3, width=40)
        app._render_width = 40
        app._actual_height = 3
        app._needs_render = True

        mock_stdout = io.StringIO()
        with patch("sys.stdout", mock_stdout):
            app._render()

        assert app._needs_render is False

    def test_render_stores_positioned_elements(self):
        """Test _render() stores elements for animation."""
        template = "{% frame %}Test{% endframe %}"
        app = InlineApp(template, height=3, width=40)
        app._render_width = 40
        app._actual_height = 3

        mock_stdout = io.StringIO()
        with patch("sys.stdout", mock_stdout):
            app._render()

        # Elements should be stored (may be empty for simple text)
        assert hasattr(app, "_positioned_elements")


class TestInlineAppAutoHeight:
    """Tests for InlineApp auto height calculation."""

    def test_calculate_auto_height(self):
        """Test auto height calculation."""
        app = InlineApp("Simple text", width=40)
        app._render_width = 40

        height = app._calculate_auto_height()

        assert height >= 1

    def test_calculate_auto_height_with_frame(self):
        """Test auto height with frame template."""
        template = "{% frame %}Content{% endframe %}"
        app = InlineApp(template, width=40)
        app._render_width = 40

        height = app._calculate_auto_height()

        # Frame needs at least 3 lines (top border, content, bottom border)
        assert height >= 3
