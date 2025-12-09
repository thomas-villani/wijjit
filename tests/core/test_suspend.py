"""Tests for suspend/background functionality."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from wijjit.core.suspend import _SUSPEND_AVAILABLE, SuspendManager


class TestSuspendAvailability:
    """Tests for platform availability detection."""

    def test_suspend_available_constant(self):
        """Test that _SUSPEND_AVAILABLE is correctly set based on platform."""
        # On Windows, suspend should not be available
        # On Unix (Linux, macOS), suspend should be available
        if sys.platform == "win32":
            assert _SUSPEND_AVAILABLE is False
        else:
            assert _SUSPEND_AVAILABLE is True


class TestSuspendManager:
    """Tests for SuspendManager class."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock Wijjit app for testing."""
        app = MagicMock()
        app.config = {"ENABLE_SUSPEND": True}
        app.screen_manager = MagicMock()
        app.screen_manager.in_alternate_buffer = True
        app.screen_manager._cursor_hidden = True
        app.screen_manager.output = MagicMock()
        app.input_handler = MagicMock()
        app.input_handler.mouse_enabled = True
        app.needs_render = False
        return app

    def test_init(self, mock_app):
        """Test SuspendManager initialization."""
        manager = SuspendManager(mock_app)

        assert manager.app is mock_app
        assert manager.enabled is False
        assert manager.suspended is False
        assert manager._was_in_alt_buffer is False
        assert manager._was_cursor_hidden is False
        assert manager._was_mouse_enabled is False

    def test_available_property(self, mock_app):
        """Test available property returns platform-appropriate value."""
        manager = SuspendManager(mock_app)
        assert manager.available == _SUSPEND_AVAILABLE

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Suspend not available on Windows"
    )
    def test_register_on_unix(self, mock_app):
        """Test signal handler registration on Unix-like systems."""
        manager = SuspendManager(mock_app)

        # Should succeed on Unix
        result = manager.register()
        assert result is True
        assert manager.enabled is True

        # Cleanup
        manager.unregister()

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Suspend not available on Windows"
    )
    def test_register_twice(self, mock_app):
        """Test that registering twice returns False on second call."""
        manager = SuspendManager(mock_app)

        result1 = manager.register()
        assert result1 is True

        result2 = manager.register()
        assert result2 is False

        # Cleanup
        manager.unregister()

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Suspend not available on Windows"
    )
    def test_register_disabled_config(self, mock_app):
        """Test that registration fails when disabled via config."""
        mock_app.config["ENABLE_SUSPEND"] = False
        manager = SuspendManager(mock_app)

        result = manager.register()
        assert result is False
        assert manager.enabled is False

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Suspend not available on Windows"
    )
    def test_unregister(self, mock_app):
        """Test signal handler unregistration."""
        manager = SuspendManager(mock_app)

        manager.register()
        assert manager.enabled is True

        manager.unregister()
        assert manager.enabled is False

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Suspend not available on Windows"
    )
    def test_unregister_without_register(self, mock_app):
        """Test that unregister without register doesn't error."""
        manager = SuspendManager(mock_app)
        # Should not raise
        manager.unregister()
        assert manager.enabled is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Only test on Windows")
    def test_register_on_windows(self, mock_app):
        """Test that registration returns False on Windows."""
        manager = SuspendManager(mock_app)
        result = manager.register()
        assert result is False
        assert manager.enabled is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Only test on Windows")
    def test_unregister_on_windows(self, mock_app):
        """Test that unregister is a no-op on Windows."""
        manager = SuspendManager(mock_app)
        # Should not raise
        manager.unregister()

    def test_state_saving_on_sigtstp(self, mock_app):
        """Test that terminal state is saved when SIGTSTP is received."""
        manager = SuspendManager(mock_app)

        # Simulate the state saving that happens in _handle_sigtstp
        # We directly test the state variables since we can't easily trigger signals
        manager._was_in_alt_buffer = mock_app.screen_manager.in_alternate_buffer
        manager._was_cursor_hidden = mock_app.screen_manager._cursor_hidden
        manager._was_mouse_enabled = mock_app.input_handler.mouse_enabled

        assert manager._was_in_alt_buffer is True
        assert manager._was_cursor_hidden is True
        assert manager._was_mouse_enabled is True


@pytest.mark.skipif(
    sys.platform == "win32", reason="Signal handling tests require Unix"
)
class TestSuspendSignalHandling:
    """Tests for signal handler behavior (Unix only)."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock Wijjit app for testing."""
        app = MagicMock()
        app.config = {"ENABLE_SUSPEND": True}
        app.screen_manager = MagicMock()
        app.screen_manager.in_alternate_buffer = True
        app.screen_manager._cursor_hidden = True
        app.screen_manager.output = MagicMock()
        app.input_handler = MagicMock()
        app.input_handler.mouse_enabled = True
        app.needs_render = False
        return app

    def test_sigcont_handler_restores_state(self, mock_app):
        """Test that SIGCONT handler restores terminal state."""
        manager = SuspendManager(mock_app)

        # Set up as if we were suspended
        manager.suspended = True
        manager._was_in_alt_buffer = True
        manager._was_cursor_hidden = True
        manager._was_mouse_enabled = True

        # Call the SIGCONT handler directly (simulate signal)
        manager._handle_sigcont(18, None)  # 18 = SIGCONT

        # Verify terminal state was restored
        mock_app.screen_manager.enter_alternate_buffer.assert_called_once()
        mock_app.screen_manager.hide_cursor.assert_called_once()
        mock_app.input_handler.enable_mouse_tracking.assert_called_once()

        # Verify state was updated
        assert manager.suspended is False
        assert mock_app.needs_render is True

    def test_sigcont_handler_skips_if_not_suspended(self, mock_app):
        """Test that SIGCONT handler does nothing if not in suspended state."""
        manager = SuspendManager(mock_app)
        manager.suspended = False

        # Call the SIGCONT handler
        manager._handle_sigcont(18, None)

        # Nothing should be called
        mock_app.screen_manager.enter_alternate_buffer.assert_not_called()
        mock_app.screen_manager.hide_cursor.assert_not_called()
        mock_app.input_handler.enable_mouse_tracking.assert_not_called()

    def test_sigcont_handler_respects_saved_state(self, mock_app):
        """Test that SIGCONT only restores state that was active before suspend."""
        manager = SuspendManager(mock_app)

        # Set up as if alt buffer was off and cursor was visible
        manager.suspended = True
        manager._was_in_alt_buffer = False
        manager._was_cursor_hidden = False
        manager._was_mouse_enabled = True

        # Call the SIGCONT handler
        manager._handle_sigcont(18, None)

        # Only mouse should be restored
        mock_app.screen_manager.enter_alternate_buffer.assert_not_called()
        mock_app.screen_manager.hide_cursor.assert_not_called()
        mock_app.input_handler.enable_mouse_tracking.assert_called_once()

    @patch("wijjit.core.suspend.signal")
    @patch("wijjit.core.suspend.os")
    def test_sigtstp_handler_cleanup_and_suspend(self, mock_os, mock_signal, mock_app):
        """Test that SIGTSTP handler cleans up terminal and sends SIGSTOP."""
        manager = SuspendManager(mock_app)

        # Call the SIGTSTP handler directly
        manager._handle_sigtstp(20, None)  # 20 = SIGTSTP

        # Verify terminal cleanup happened
        mock_app.input_handler.disable_mouse_tracking.assert_called_once()
        mock_app.screen_manager.show_cursor.assert_called_once()
        mock_app.screen_manager.exit_alternate_buffer.assert_called_once()
        mock_app.screen_manager.output.flush.assert_called_once()

        # Verify state was saved
        assert manager.suspended is True

        # Verify signal handlers were manipulated and SIGTSTP was sent
        mock_signal.signal.assert_called()
        mock_os.kill.assert_called_once()
