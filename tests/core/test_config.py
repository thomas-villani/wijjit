"""Tests for the configuration system.

This module tests the Config class and its various loading methods,
as well as integration with the Wijjit application class.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from wijjit import Config, DefaultConfig, Wijjit


class TestConfigClass:
    """Tests for the Config class itself."""

    def test_config_is_dict(self):
        """Config should behave like a dict.

        Returns
        -------
        None
        """
        config = Config()
        config["TEST"] = "value"
        assert config["TEST"] == "value"
        assert "TEST" in config
        assert len(config) == 1

    def test_config_init_with_defaults(self):
        """Config can be initialized with default values.

        Returns
        -------
        None
        """
        defaults = {"KEY1": "value1", "KEY2": "value2"}
        config = Config(defaults)
        assert config["KEY1"] == "value1"
        assert config["KEY2"] == "value2"

    def test_from_object_with_class(self):
        """Config can load from a class object.

        Returns
        -------
        None
        """

        class TestConfig:
            DEBUG = True
            ENABLE_MOUSE = False
            LOG_LEVEL = "DEBUG"
            lowercase_ignored = "ignored"

        config = Config()
        config.from_object(TestConfig)

        assert config["DEBUG"] is True
        assert config["ENABLE_MOUSE"] is False
        assert config["LOG_LEVEL"] == "DEBUG"
        assert "lowercase_ignored" not in config

    def test_from_object_with_instance(self):
        """Config can load from an object instance.

        Returns
        -------
        None
        """

        class TestConfig:
            DEBUG = True
            VALUE = 42

        instance = TestConfig()
        config = Config()
        config.from_object(instance)

        assert config["DEBUG"] is True
        assert config["VALUE"] == 42

    def test_from_pyfile(self):
        """Config can load from a Python file.

        Returns
        -------
        None
        """
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("DEBUG = True\n")
            f.write("ENABLE_MOUSE = False\n")
            f.write('LOG_LEVEL = "INFO"\n')
            f.write('lowercase = "ignored"\n')
            temp_path = f.name

        try:
            config = Config()
            result = config.from_pyfile(temp_path)

            assert result is True
            assert config["DEBUG"] is True
            assert config["ENABLE_MOUSE"] is False
            assert config["LOG_LEVEL"] == "INFO"
            assert "lowercase" not in config
        finally:
            os.unlink(temp_path)

    def test_from_pyfile_missing_silent(self):
        """Config.from_pyfile with silent=True returns False for missing files.

        Returns
        -------
        None
        """
        config = Config()
        result = config.from_pyfile("/nonexistent/config.py", silent=True)
        assert result is False

    def test_from_pyfile_missing_not_silent(self):
        """Config.from_pyfile raises FileNotFoundError for missing files.

        Returns
        -------
        None
        """
        config = Config()
        with pytest.raises(FileNotFoundError):
            config.from_pyfile("/nonexistent/config.py", silent=False)

    def test_from_envvar(self):
        """Config can load from environment variable pointing to file.

        Returns
        -------
        None
        """
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("DEBUG = True\n")
            temp_path = f.name

        try:
            with patch.dict(os.environ, {"TEST_CONFIG": temp_path}):
                config = Config()
                result = config.from_envvar("TEST_CONFIG")

                assert result is True
                assert config["DEBUG"] is True
        finally:
            os.unlink(temp_path)

    def test_from_envvar_missing_silent(self):
        """Config.from_envvar with silent=True returns False for missing var.

        Returns
        -------
        None
        """
        config = Config()
        result = config.from_envvar("NONEXISTENT_VAR", silent=True)
        assert result is False

    def test_from_envvar_missing_not_silent(self):
        """Config.from_envvar raises RuntimeError for missing var.

        Returns
        -------
        None
        """
        config = Config()
        with pytest.raises(RuntimeError, match="environment variable"):
            config.from_envvar("NONEXISTENT_VAR", silent=False)

    def test_from_mapping(self):
        """Config can load from dict or kwargs.

        Returns
        -------
        None
        """
        config = Config()

        # From dict
        config.from_mapping({"DEBUG": True, "VALUE": 42})
        assert config["DEBUG"] is True
        assert config["VALUE"] == 42

        # From kwargs
        config.from_mapping(ENABLE_MOUSE=False, LOG_LEVEL="INFO")
        assert config["ENABLE_MOUSE"] is False
        assert config["LOG_LEVEL"] == "INFO"

        # Combined
        config.from_mapping({"KEY1": "val1"}, KEY2="val2")
        assert config["KEY1"] == "val1"
        assert config["KEY2"] == "val2"

    def test_from_prefixed_env(self):
        """Config can load from prefixed environment variables.

        Returns
        -------
        None
        """
        env_vars = {
            "WIJJIT_DEBUG": "1",
            "WIJJIT_ENABLE_MOUSE": "0",
            "WIJJIT_LOG_LEVEL": "DEBUG",
            "WIJJIT_REFRESH_INTERVAL": "0.1",
            "WIJJIT_MAX_WORKERS": "4",
            "OTHER_VAR": "ignored",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            config.from_prefixed_env("WIJJIT_")

            # Boolean parsing
            assert config["DEBUG"] is True
            assert config["ENABLE_MOUSE"] is False

            # String values
            assert config["LOG_LEVEL"] == "DEBUG"

            # Numeric parsing
            assert config["REFRESH_INTERVAL"] == 0.1
            assert config["MAX_WORKERS"] == 4

            # Non-prefixed var ignored
            assert "OTHER_VAR" not in config

    def test_from_prefixed_env_bool_variations(self):
        """Config parses various boolean representations.

        Returns
        -------
        None
        """
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]

        for value, expected in test_cases:
            with patch.dict(os.environ, {"TEST_VAL": value}, clear=True):
                config = Config()
                config.from_prefixed_env("TEST_")
                assert config["VAL"] is expected, f"Failed for '{value}'"

    def test_get_namespace(self):
        """Config.get_namespace returns subset of config.

        Returns
        -------
        None
        """
        config = Config(
            {
                "NOTIFICATION_DURATION": 3.0,
                "NOTIFICATION_POSITION": "top_right",
                "NOTIFICATION_MAX_STACK": 5,
                "DEBUG": True,
            }
        )

        # Get namespace with defaults
        notif_config = config.get_namespace("NOTIFICATION_")
        assert notif_config == {
            "duration": 3.0,
            "position": "top_right",
            "max_stack": 5,
        }

        # Without lowercasing
        notif_config = config.get_namespace("NOTIFICATION_", lowercase=False)
        assert notif_config == {
            "DURATION": 3.0,
            "POSITION": "top_right",
            "MAX_STACK": 5,
        }

        # Without trimming
        notif_config = config.get_namespace("NOTIFICATION_", trim_namespace=False)
        assert notif_config == {
            "notification_duration": 3.0,
            "notification_position": "top_right",
            "notification_max_stack": 5,
        }


class TestDefaultConfig:
    """Tests for DefaultConfig class."""

    def test_default_config_has_required_keys(self):
        """DefaultConfig defines all required configuration keys.

        Returns
        -------
        None
        """
        required_keys = [
            # Input & Interaction
            "ENABLE_MOUSE",
            "MOUSE_TRACKING_MODE",
            "ENABLE_FOCUS_NAVIGATION",
            "QUIT_KEY",
            # Display & Terminal
            "USE_ALTERNATE_SCREEN",
            "HIDE_CURSOR",
            # Colors & Theming
            "NO_COLOR",
            "FORCE_COLOR",
            "DEFAULT_THEME",
            "THEME_FILE",
            "STYLE_FILE",
            "UNICODE_SUPPORT",
            # Performance
            "REFRESH_INTERVAL",
            "DEFAULT_ANIMATION_FPS",
            "MAX_FPS",
            "RUN_SYNC_IN_EXECUTOR",
            "EXECUTOR_MAX_WORKERS",
            "USE_DIFF_RENDERING",
            "RENDER_THROTTLE_MS",
            # Notifications
            "NOTIFICATION_DURATION",
            "NOTIFICATION_POSITION",
            "NOTIFICATION_SPACING",
            "NOTIFICATION_MARGIN",
            "NOTIFICATION_MAX_STACK",
            # Logging
            "LOG_LEVEL",
            "LOG_FILE",
            "LOG_TO_CONSOLE",
            "LOG_FORMAT",
            # Debug
            "DEBUG",
            "SHOW_FPS",
            "SHOW_BOUNDS",
            "DEBUG_INPUT_KEYBOARD",
            "DEBUG_INPUT_MOUSE",
            "WARN_SLOW_RENDER_MS",
            # Templates
            "TEMPLATE_DIR",
            "TEMPLATE_AUTO_RELOAD",
            # Accessibility
            "REDUCE_MOTION",
            "HIGH_CONTRAST",
            # Testing
            "TESTING",
            "CI",
            "HEADLESS",
        ]

        for key in required_keys:
            assert hasattr(DefaultConfig, key), f"Missing config key: {key}"

    def test_default_config_values(self):
        """DefaultConfig has sensible default values.

        Returns
        -------
        None
        """
        assert DefaultConfig.ENABLE_MOUSE is True
        assert DefaultConfig.MOUSE_TRACKING_MODE == "button_event"
        assert DefaultConfig.ENABLE_FOCUS_NAVIGATION is True
        assert DefaultConfig.QUIT_KEY == "ctrl+q"

        assert DefaultConfig.USE_ALTERNATE_SCREEN is True
        assert DefaultConfig.HIDE_CURSOR is True

        assert DefaultConfig.DEFAULT_THEME == "default"
        assert DefaultConfig.THEME_FILE is None
        assert DefaultConfig.STYLE_FILE is None
        assert DefaultConfig.UNICODE_SUPPORT == "auto"

        assert DefaultConfig.REFRESH_INTERVAL is None
        assert DefaultConfig.DEFAULT_ANIMATION_FPS == 5
        assert DefaultConfig.MAX_FPS is None
        assert DefaultConfig.RUN_SYNC_IN_EXECUTOR is False
        assert DefaultConfig.USE_DIFF_RENDERING is True

        assert DefaultConfig.NOTIFICATION_DURATION == 3.0
        assert DefaultConfig.NOTIFICATION_POSITION == "top_right"
        assert DefaultConfig.NOTIFICATION_MAX_STACK == 5

        assert DefaultConfig.DEBUG is False
        assert DefaultConfig.SHOW_FPS is False


class TestWijjitIntegration:
    """Tests for Config integration with Wijjit application."""

    def test_wijjit_initializes_config(self):
        """Wijjit app initializes config with defaults.

        Returns
        -------
        None
        """
        app = Wijjit()
        assert isinstance(app.config, Config)
        assert len(app.config) > 0

    def test_wijjit_loads_defaults(self):
        """Wijjit app loads DefaultConfig values.

        Returns
        -------
        None
        """
        app = Wijjit()
        assert app.config["ENABLE_MOUSE"] == DefaultConfig.ENABLE_MOUSE
        assert app.config["QUIT_KEY"] == DefaultConfig.QUIT_KEY
        assert app.config["DEBUG"] == DefaultConfig.DEBUG

    def test_wijjit_loads_env_vars(self):
        """Wijjit app auto-loads WIJJIT_* environment variables.

        Returns
        -------
        None
        """
        env_vars = {
            "WIJJIT_DEBUG": "1",
            "WIJJIT_ENABLE_MOUSE": "0",
        }

        with patch.dict(os.environ, env_vars):
            app = Wijjit()
            assert app.config["DEBUG"] is True
            assert app.config["ENABLE_MOUSE"] is False

    def test_wijjit_applies_config_to_components(self):
        """Wijjit app applies config to its components.

        Returns
        -------
        None
        """
        app = Wijjit()

        # Input handler respects ENABLE_MOUSE
        app.config["ENABLE_MOUSE"] = False
        # Note: InputHandler is already created, but config is available

        # Focus navigation respects config
        assert app.focus_navigation_enabled == app.config["ENABLE_FOCUS_NAVIGATION"]

        # Refresh interval respects config
        assert app.refresh_interval == app.config["REFRESH_INTERVAL"]

    def test_wijjit_config_can_be_modified(self):
        """Wijjit config can be modified after initialization.

        Returns
        -------
        None
        """
        app = Wijjit()

        # Modify config
        app.config["DEBUG"] = True
        app.config["QUIT_KEY"] = "q"
        app.config["NOTIFICATION_MAX_STACK"] = 10

        # Verify changes
        assert app.config["DEBUG"] is True
        assert app.config["QUIT_KEY"] == "q"
        assert app.config["NOTIFICATION_MAX_STACK"] == 10

    def test_wijjit_config_from_file(self):
        """Wijjit can load config from a file.

        Returns
        -------
        None
        """
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("DEBUG = True\n")
            f.write("ENABLE_MOUSE = False\n")
            f.write('QUIT_KEY = "q"\n')
            temp_path = f.name

        try:
            app = Wijjit()
            app.config.from_pyfile(temp_path)

            assert app.config["DEBUG"] is True
            assert app.config["ENABLE_MOUSE"] is False
            assert app.config["QUIT_KEY"] == "q"
        finally:
            os.unlink(temp_path)


class TestConfigEdgeCases:
    """Tests for edge cases and error handling."""

    def test_config_update_preserves_existing(self):
        """Config.update preserves existing values not in update.

        Returns
        -------
        None
        """
        config = Config({"KEY1": "value1", "KEY2": "value2"})
        config.update({"KEY2": "new_value2", "KEY3": "value3"})

        assert config["KEY1"] == "value1"  # Preserved
        assert config["KEY2"] == "new_value2"  # Updated
        assert config["KEY3"] == "value3"  # Added

    def test_config_handles_none_values(self):
        """Config correctly handles None values.

        Returns
        -------
        None
        """
        config = Config()
        config["THEME_FILE"] = None
        config["MAX_FPS"] = None

        assert config["THEME_FILE"] is None
        assert config["MAX_FPS"] is None

    def test_config_handles_numeric_values(self):
        """Config correctly handles numeric values.

        Returns
        -------
        None
        """
        config = Config()
        config["NOTIFICATION_DURATION"] = 3.0
        config["MAX_WORKERS"] = 4
        config["REFRESH_INTERVAL"] = 0.1

        assert isinstance(config["NOTIFICATION_DURATION"], float)
        assert isinstance(config["MAX_WORKERS"], int)
        assert isinstance(config["REFRESH_INTERVAL"], float)


class TestPhase3Features:
    """Tests for Phase 3 advanced configuration features."""

    def test_max_fps_config_defaults_to_none(self):
        """MAX_FPS should default to None (unlimited).

        Returns
        -------
        None
        """
        config = Config()
        config.from_object(DefaultConfig)
        assert config["MAX_FPS"] is None

    def test_max_fps_config_accepts_integer(self):
        """MAX_FPS should accept integer values.

        Returns
        -------
        None
        """
        config = Config()
        config["MAX_FPS"] = 60
        assert config["MAX_FPS"] == 60
        assert isinstance(config["MAX_FPS"], int)

    def test_show_bounds_config_defaults_to_false(self):
        """SHOW_BOUNDS should default to False.

        Returns
        -------
        None
        """
        config = Config()
        config.from_object(DefaultConfig)
        assert config["SHOW_BOUNDS"] is False

    def test_show_bounds_config_accepts_boolean(self):
        """SHOW_BOUNDS should accept boolean values.

        Returns
        -------
        None
        """
        config = Config()
        config["SHOW_BOUNDS"] = True
        assert config["SHOW_BOUNDS"] is True

    def test_reduce_motion_config_defaults_to_false(self):
        """REDUCE_MOTION should default to False.

        Returns
        -------
        None
        """
        config = Config()
        config.from_object(DefaultConfig)
        assert config["REDUCE_MOTION"] is False

    def test_reduce_motion_config_accepts_boolean(self):
        """REDUCE_MOTION should accept boolean values.

        Returns
        -------
        None
        """
        config = Config()
        config["REDUCE_MOTION"] = True
        assert config["REDUCE_MOTION"] is True

    def test_render_throttle_ms_config_defaults_to_zero(self):
        """RENDER_THROTTLE_MS should default to 0 (no throttling).

        Returns
        -------
        None
        """
        config = Config()
        config.from_object(DefaultConfig)
        assert config["RENDER_THROTTLE_MS"] == 0

    def test_render_throttle_ms_config_accepts_integer(self):
        """RENDER_THROTTLE_MS should accept integer values.

        Returns
        -------
        None
        """
        config = Config()
        config["RENDER_THROTTLE_MS"] = 16
        assert config["RENDER_THROTTLE_MS"] == 16

    def test_high_contrast_config_defaults_to_false(self):
        """HIGH_CONTRAST should default to False.

        Returns
        -------
        None
        """
        config = Config()
        config.from_object(DefaultConfig)
        assert config["HIGH_CONTRAST"] is False

    def test_high_contrast_config_accepts_boolean(self):
        """HIGH_CONTRAST should accept boolean values.

        Returns
        -------
        None
        """
        config = Config()
        config["HIGH_CONTRAST"] = True
        assert config["HIGH_CONTRAST"] is True

    def test_phase3_configs_load_from_env(self):
        """Phase 3 config options should load from environment variables.

        Returns
        -------
        None
        """
        env_vars = {
            "WIJJIT_MAX_FPS": "30",
            "WIJJIT_SHOW_BOUNDS": "true",
            "WIJJIT_REDUCE_MOTION": "1",
            "WIJJIT_RENDER_THROTTLE_MS": "16",
            "WIJJIT_HIGH_CONTRAST": "yes",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = Config()
            config.from_prefixed_env("WIJJIT_")

            assert config["MAX_FPS"] == 30
            assert config["SHOW_BOUNDS"] is True
            assert config["REDUCE_MOTION"] is True
            assert config["RENDER_THROTTLE_MS"] == 16
            assert config["HIGH_CONTRAST"] is True

    def test_high_contrast_theme_registered(self):
        """High contrast theme should be registered in ThemeManager.

        Returns
        -------
        None
        """
        from wijjit.styling.theme import ThemeManager

        manager = ThemeManager()
        assert "high_contrast" in manager.themes

    def test_high_contrast_theme_has_required_styles(self):
        """High contrast theme should define required element styles.

        Returns
        -------
        None
        """
        from wijjit.styling.theme import HighContrastTheme

        theme = HighContrastTheme()

        # Check that key styles are defined
        required_styles = [
            "button",
            "button:focus",
            "input",
            "input:focus",
            "checkbox",
            "checkbox:focus",
            "frame",
            "frame.border",
            "notification.success",
            "notification.error",
        ]

        for style_name in required_styles:
            assert style_name in theme.styles, f"Missing style: {style_name}"

    def test_high_contrast_theme_uses_bold(self):
        """High contrast theme should use bold text for visibility.

        Returns
        -------
        None
        """
        from wijjit.styling.theme import HighContrastTheme

        theme = HighContrastTheme()

        # Most styles should be bold for better visibility
        button_style = theme.get_style("button")
        assert button_style.bold is True

        input_style = theme.get_style("input")
        assert input_style.bold is True

        text_style = theme.get_style("text")
        assert text_style.bold is True
