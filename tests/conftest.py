"""Shared pytest fixtures and utilities for Wijjit tests.

This module provides common fixtures used across unit, integration, and e2e tests.
"""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.renderer import Renderer
from wijjit.core.state import State
from wijjit.elements.base import Element
from wijjit.layout.frames import Frame, FrameStyle
from wijjit.terminal.input import Keys


class MockElement(Element):
    """Mock element for testing layout and rendering.

    Parameters
    ----------
    width : int, optional
        Element width, by default 10
    height : int, optional
        Element height, by default 1
    content : str, optional
        Element content, by default "X" repeated
    id : str, optional
        Element identifier
    focusable : bool, optional
        Whether element can receive focus, by default False
    """

    def __init__(
        self,
        width: int = 10,
        height: int = 1,
        content: str = None,
        id: str = None,
        focusable: bool = False,
    ):
        super().__init__(id)
        self.mock_width = width
        self.mock_height = height
        self.mock_content = content or "X"
        self.focusable = focusable
        self.render_count = 0

    def render(self) -> str:
        """Render mock element.

        Returns
        -------
        str
            Mock content with specified dimensions
        """
        self.render_count += 1
        line = self.mock_content * self.mock_width
        return "\n".join([line[: self.mock_width]] * self.mock_height)


class TestElement(Element):
    """Simple test element with configurable content.

    Parameters
    ----------
    content : str, optional
        Element content to render, by default "test"
    id : str, optional
        Element identifier
    focusable : bool, optional
        Whether element can receive focus, by default False
    """

    def __init__(self, content: str = "test", id: str = None, focusable: bool = False):
        super().__init__(id)
        self.content = content
        self.focusable = focusable

    def render(self) -> str:
        """Render test element.

        Returns
        -------
        str
            Element content
        """
        return self.content


@pytest.fixture
def mock_element():
    """Create a MockElement factory.

    Returns
    -------
    Callable
        Factory function that creates MockElement instances
    """

    def _create_mock_element(**kwargs):
        return MockElement(**kwargs)

    return _create_mock_element


@pytest.fixture
def test_element():
    """Create a TestElement factory.

    Returns
    -------
    Callable
        Factory function that creates TestElement instances
    """

    def _create_test_element(**kwargs):
        return TestElement(**kwargs)

    return _create_test_element


@pytest.fixture
def mock_app():
    """Create a mock Wijjit app for testing.

    Returns
    -------
    Mock
        Mock app with common attributes
    """
    app = Mock(spec=Wijjit)
    app.state = State()
    app.running = False
    app.needs_render = True
    app.current_view = None
    return app


@pytest.fixture
def app():
    """Create a real Wijjit app instance for integration tests.

    Returns
    -------
    Wijjit
        Wijjit application instance
    """
    return Wijjit()


@pytest.fixture
def app_with_state():
    """Create a Wijjit app with initial state.

    Returns
    -------
    Wijjit
        Wijjit app with sample state
    """
    return Wijjit(initial_state={"count": 0, "name": "Test", "items": []})


@pytest.fixture
def renderer():
    """Create a Renderer instance for testing.

    Returns
    -------
    Renderer
        Template renderer
    """
    return Renderer()


@pytest.fixture
def state():
    """Create a State instance for testing.

    Returns
    -------
    State
        Reactive state object
    """
    return State()


@pytest.fixture
def state_with_data():
    """Create a State instance with sample data.

    Returns
    -------
    State
        State with test data
    """
    return State({"count": 0, "data_items": ["a", "b", "c"], "enabled": True})


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file-based tests.

    Yields
    ------
    Path
        Path to temporary directory (automatically cleaned up)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for testing.

    Parameters
    ----------
    temp_dir : Path
        Temporary directory fixture

    Returns
    -------
    Callable
        Factory function that creates temporary files
    """

    def _create_temp_file(name: str, content: str = ""):
        file_path = temp_dir / name
        file_path.write_text(content)
        return file_path

    return _create_temp_file


@pytest.fixture
def captured_output():
    """Create a StringIO buffer for capturing output.

    Returns
    -------
    StringIO
        Output buffer
    """
    return StringIO()


@pytest.fixture
def mock_input():
    """Create a mock input handler for testing keyboard input.

    Returns
    -------
    Mock
        Mock input handler with raw_mode context manager
    """
    mock = Mock()
    mock_raw_mode = MagicMock()
    mock_raw_mode.__enter__ = Mock(return_value=None)
    mock_raw_mode.__exit__ = Mock(return_value=None)
    mock.raw_mode.return_value = mock_raw_mode
    return mock


@pytest.fixture
def sample_keys():
    """Provide sample key constants for testing.

    Returns
    -------
    type
        Keys class with constants
    """
    return Keys


@pytest.fixture
def mock_clipboard():
    """Mock pyperclip clipboard for isolated testing.

    This fixture prevents tests from depending on system clipboard state
    by mocking the pyperclip module. Tests can set clipboard content by
    calling mock_clipboard.paste.return_value = "text".

    Returns
    -------
    Mock
        Mock pyperclip module with paste() and copy() methods

    Examples
    --------
    >>> def test_paste(mock_clipboard):
    ...     mock_clipboard.paste.return_value = "Hello World"
    ...     textarea = TextArea()
    ...     textarea._paste()
    ...     assert textarea.get_value() == "Hello World"
    """
    from unittest.mock import MagicMock, patch

    # Mock pyperclip module directly since it's imported dynamically inside methods
    with patch("pyperclip.paste") as mock_paste, patch("pyperclip.copy") as mock_copy:
        mock_paste.return_value = ""
        # Create a simple mock object with paste and copy methods for convenience
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste = mock_paste
        mock_pyperclip.copy = mock_copy
        yield mock_pyperclip


class FrameBuilder:
    """Builder for creating Frame instances with fluent API.

    Examples
    --------
    >>> frame = FrameBuilder().with_size(20, 10).with_title("Test").build()
    >>> frame = FrameBuilder().with_border("double").with_padding(2).build()
    """

    def __init__(self):
        self.width = 20
        self.height = 10
        self.style = FrameStyle()

    def with_size(self, width: int, height: int):
        """Set frame size.

        Parameters
        ----------
        width : int
            Frame width
        height : int
            Frame height

        Returns
        -------
        FrameBuilder
            Self for chaining
        """
        self.width = width
        self.height = height
        return self

    def with_border(self, border_style: str):
        """Set border style.

        Parameters
        ----------
        border_style : str
            Border style (single, double, rounded, heavy, light)

        Returns
        -------
        FrameBuilder
            Self for chaining
        """
        self.style.border = border_style
        return self

    def with_title(self, title: str, position: str = "center"):
        """Set frame title.

        Parameters
        ----------
        title : str
            Frame title
        position : str, optional
            Title position (left, center, right), by default "center"

        Returns
        -------
        FrameBuilder
            Self for chaining
        """
        self.style.title = title
        self.style.title_position = position
        return self

    def with_padding(self, padding: int):
        """Set frame padding.

        Parameters
        ----------
        padding : int
            Padding amount in all directions

        Returns
        -------
        FrameBuilder
            Self for chaining
        """
        self.style.padding_top = padding
        self.style.padding_right = padding
        self.style.padding_bottom = padding
        self.style.padding_left = padding
        return self

    def with_overflow(self, overflow_x: str = None, overflow_y: str = None):
        """Set overflow behavior.

        Parameters
        ----------
        overflow_x : str, optional
            Horizontal overflow (clip, visible, wrap)
        overflow_y : str, optional
            Vertical overflow (clip, visible, scroll)

        Returns
        -------
        FrameBuilder
            Self for chaining
        """
        if overflow_x:
            self.style.overflow_x = overflow_x
        if overflow_y:
            self.style.overflow_y = overflow_y
        return self

    def build(self) -> Frame:
        """Build the Frame instance.

        Returns
        -------
        Frame
            Configured frame
        """
        return Frame(width=self.width, height=self.height, style=self.style)


@pytest.fixture
def frame_builder():
    """Create a FrameBuilder factory.

    Returns
    -------
    Callable
        Factory function that creates FrameBuilder instances
    """

    def _create_builder():
        return FrameBuilder()

    return _create_builder
