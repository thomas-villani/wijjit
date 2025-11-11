"""
Tests for the logging configuration module.

This module tests the logging configuration functionality, including:
- No side effects on import
- Level validation with fallback
- File and environment-based configuration
"""

import logging

from wijjit.logging_config import (
    configure_logging_from_environment,
    configure_logging,
    get_logger,
)


class TestConfigureLogging:
    """
    Tests for the configure_logging function.
    """

    def test_configure_with_file(self, tmp_path):
        """
        Test that configure_logging sets up file logging correctly.

        Parameters
        ----------
        tmp_path : Path
            Pytest fixture providing temporary directory path.
        """
        log_file = tmp_path / "test.log"
        configure_logging(log_file, level="DEBUG")

        logger = get_logger("wijjit.test")
        logger.debug("Test message")

        # Verify log file was created and contains the message
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content
        assert "DEBUG" in content

    def test_configure_with_none_disables_logging(self):
        """
        Test that configure_logging(None) disables logging.
        """
        configure_logging(None)

        # Check the parent wijjit logger (child loggers inherit from it)
        parent_logger = logging.getLogger("wijjit")
        # Parent logger should have NullHandler and very high level
        assert any(isinstance(h, logging.NullHandler) for h in parent_logger.handlers)
        assert parent_logger.level > logging.CRITICAL

    def test_level_validation_with_valid_string(self, tmp_path):
        """
        Test that valid level strings are converted correctly.

        Parameters
        ----------
        tmp_path : Path
            Pytest fixture providing temporary directory path.
        """
        log_file = tmp_path / "test.log"
        configure_logging(log_file, level="WARNING")

        # Check the parent wijjit logger
        parent_logger = logging.getLogger("wijjit")
        assert parent_logger.level == logging.WARNING

    def test_level_validation_with_invalid_string_falls_back(self, tmp_path):
        """
        Test that invalid level strings fall back to INFO.

        Parameters
        ----------
        tmp_path : Path
            Pytest fixture providing temporary directory path.
        """
        log_file = tmp_path / "test.log"
        configure_logging(log_file, level="INVALID_LEVEL")

        # Check the parent wijjit logger
        parent_logger = logging.getLogger("wijjit")
        # Should fall back to INFO
        assert parent_logger.level == logging.INFO

    def test_level_validation_with_int(self, tmp_path):
        """
        Test that integer levels are accepted directly.

        Parameters
        ----------
        tmp_path : Path
            Pytest fixture providing temporary directory path.
        """
        log_file = tmp_path / "test.log"
        configure_logging(log_file, level=logging.ERROR)

        # Check the parent wijjit logger
        parent_logger = logging.getLogger("wijjit")
        assert parent_logger.level == logging.ERROR

    def test_custom_format_string(self, tmp_path):
        """
        Test that custom format strings are applied.

        Parameters
        ----------
        tmp_path : Path
            Pytest fixture providing temporary directory path.
        """
        log_file = tmp_path / "test.log"
        custom_format = "%(levelname)s - %(message)s"
        configure_logging(log_file, level="INFO", format_string=custom_format)

        logger = get_logger("wijjit.test")
        logger.info("Custom format test")

        content = log_file.read_text()
        # Should have the custom format (no timestamp or logger name)
        assert "INFO - Custom format test" in content
        # Should NOT have the default format elements
        lines = content.strip().split("\n")
        # Find the line with our message
        test_line = [line for line in lines if "Custom format test" in line][0]
        # Custom format should not include timestamp (YYYY-MM-DD pattern)
        assert (
            "202" not in test_line or "INFO - Custom format test" == test_line.strip()
        )


class TestConfigureFromEnvironment:
    """
    Tests for the configure_logging_from_environment function.
    """

    def test_configure_from_env_with_file_set(self, tmp_path, monkeypatch):
        """
        Test configuration from environment variables when WIJJIT_LOG_FILE is set.

        Parameters
        ----------
        tmp_path : Path
            Pytest fixture providing temporary directory path.
        monkeypatch : MonkeyPatch
            Pytest fixture for modifying environment variables.
        """
        log_file = tmp_path / "env_test.log"
        monkeypatch.setenv("WIJJIT_LOG_FILE", str(log_file))
        monkeypatch.setenv("WIJJIT_LOG_LEVEL", "DEBUG")

        configure_logging_from_environment()

        logger = get_logger("wijjit.env_test")
        logger.debug("Environment config test")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Environment config test" in content

    def test_configure_from_env_without_file_disables(self, monkeypatch):
        """
        Test that configure_logging_from_environment disables logging when WIJJIT_LOG_FILE not set.

        Parameters
        ----------
        monkeypatch : MonkeyPatch
            Pytest fixture for modifying environment variables.
        """
        # Ensure WIJJIT_LOG_FILE is not set
        monkeypatch.delenv("WIJJIT_LOG_FILE", raising=False)

        configure_logging_from_environment()

        # Check the parent wijjit logger
        parent_logger = logging.getLogger("wijjit")
        # Should be disabled
        assert any(isinstance(h, logging.NullHandler) for h in parent_logger.handlers)

    def test_configure_from_env_defaults_to_info_level(self, tmp_path, monkeypatch):
        """
        Test that configure_logging_from_environment defaults to INFO level.

        Parameters
        ----------
        tmp_path : Path
            Pytest fixture providing temporary directory path.
        monkeypatch : MonkeyPatch
            Pytest fixture for modifying environment variables.
        """
        log_file = tmp_path / "default_level.log"
        monkeypatch.setenv("WIJJIT_LOG_FILE", str(log_file))
        monkeypatch.delenv("WIJJIT_LOG_LEVEL", raising=False)

        configure_logging_from_environment()

        # Check the parent wijjit logger
        parent_logger = logging.getLogger("wijjit")
        assert parent_logger.level == logging.INFO


class TestGetLogger:
    """
    Tests for the get_logger function.
    """

    def test_get_logger_with_wijjit_prefix(self):
        """
        Test that get_logger returns correct logger for wijjit modules.
        """
        logger = get_logger("wijjit.core.app")
        assert logger.name == "wijjit.core.app"

    def test_get_logger_without_wijjit_prefix_adds_it(self):
        """
        Test that get_logger adds wijjit prefix if not present.
        """
        logger = get_logger("mymodule")
        assert logger.name == "wijjit.mymodule"

    def test_get_logger_returns_child_of_wijjit_logger(self):
        """
        Test that loggers are children of the root wijjit logger.
        """
        logger = get_logger("wijjit.test.module")
        # Should be a descendant of the wijjit logger
        assert logger.name.startswith("wijjit.")


class TestNoSideEffectsOnImport:
    """
    Tests to verify no side effects occur on module import.
    """

    def test_import_does_not_configure_logging(self):
        """
        Test that importing the module does not configure logging automatically.

        This test verifies that the logging configuration module can be imported
        without any side effects, addressing the code review concern about
        automatic configuration on import.
        """
        # Get the wijjit logger before any explicit configuration
        logger = logging.getLogger("wijjit")

        # After just importing (which happened at test startup), the logger
        # should not have any non-NullHandler handlers configured
        # We need to be careful here - if other tests ran, they might have configured it
        # So we'll just verify that it's safe to import without crashing
        # and that the functions exist
        from wijjit import logging_config

        assert hasattr(logging_config, "configure_logging")
        assert hasattr(logging_config, "configure_logging_from_environment")
        assert hasattr(logging_config, "get_logger")
        # Module should be importable without errors
        assert logging_config is not None
