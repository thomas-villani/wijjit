"""Configuration system for Wijjit applications.

This module provides a Flask-like configuration interface for managing
application settings. Configuration can be loaded from Python objects,
files, environment variables, or set directly.

Examples
--------
>>> app = Wijjit()
>>> app.config['DEBUG'] = True
>>> app.config.update(ENABLE_MOUSE=False, LOG_LEVEL='DEBUG')
>>> app.config.from_pyfile('config.py')
>>> app.config.from_envvar('WIJJIT_SETTINGS')
"""

import os
from typing import Any


class Config(dict):
    """Configuration dictionary with Flask-like interface.

    Works like a regular dict but provides additional methods for loading
    configuration from different sources.

    Parameters
    ----------
    defaults : dict, optional
        Initial default values

    Examples
    --------
    >>> config = Config()
    >>> config['DEBUG'] = True
    >>> config.update(ENABLE_MOUSE=False)
    >>> config.from_object(MyConfigClass)
    """

    def __init__(self, defaults: dict | None = None) -> None:
        """Initialize configuration.

        Parameters
        ----------
        defaults : dict, optional
            Initial default values
        """
        super().__init__(defaults or {})

    def from_object(self, obj: Any) -> None:
        """Load config from an object.

        Loads all uppercase attributes from the given object.

        Parameters
        ----------
        obj : Any
            Object with uppercase attributes (module, class, or instance)

        Examples
        --------
        >>> import config
        >>> app.config.from_object(config)

        >>> class Config:
        ...     DEBUG = True
        ...     ENABLE_MOUSE = False
        >>> app.config.from_object(Config)
        """
        if isinstance(obj, str):
            obj = __import__(obj)

        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def from_pyfile(self, filename: str, silent: bool = False) -> bool:
        """Load config from a Python file.

        Parameters
        ----------
        filename : str
            Path to Python file
        silent : bool
            If True, silently ignore missing files

        Returns
        -------
        bool
            True if file was loaded, False otherwise

        Examples
        --------
        >>> app.config.from_pyfile('config.py')
        >>> app.config.from_pyfile('/etc/myapp/config.py')
        """
        filename = os.path.abspath(filename)

        try:
            with open(filename, "rb") as f:
                namespace = {}
                exec(compile(f.read(), filename, "exec"), namespace)
                # Only import uppercase variables
                for key, value in namespace.items():
                    if key.isupper():
                        self[key] = value
            return True
        except FileNotFoundError:
            if silent:
                return False
            raise

    def from_envvar(self, variable_name: str, silent: bool = False) -> bool:
        """Load config from file path in environment variable.

        Parameters
        ----------
        variable_name : str
            Name of environment variable containing config file path
        silent : bool
            If True, silently ignore missing variable/file

        Returns
        -------
        bool
            True if file was loaded, False otherwise

        Examples
        --------
        >>> # export WIJJIT_SETTINGS=/path/to/config.py
        >>> app.config.from_envvar('WIJJIT_SETTINGS')
        """
        rv = os.environ.get(variable_name)
        if not rv:
            if silent:
                return False
            raise RuntimeError(
                f"The environment variable {variable_name!r} is not set. "
                f"Set it to a config file path."
            )
        return self.from_pyfile(rv, silent=silent)

    def from_mapping(self, mapping: dict | None = None, **kwargs) -> None:
        """Load config from a dict or kwargs.

        Parameters
        ----------
        mapping : dict, optional
            Dictionary of config values
        **kwargs
            Additional config values

        Examples
        --------
        >>> app.config.from_mapping({'DEBUG': True, 'ENABLE_MOUSE': False})
        >>> app.config.from_mapping(DEBUG=True, ENABLE_MOUSE=False)
        """
        if mapping is not None:
            self.update(mapping)
        self.update(kwargs)

    def from_prefixed_env(self, prefix: str = "WIJJIT_") -> None:
        """Load config from environment variables with prefix.

        Environment variable names are converted to config keys by removing
        the prefix. Values are automatically parsed as bool/int/float when
        possible.

        Parameters
        ----------
        prefix : str
            Prefix for environment variables (default: 'WIJJIT_')

        Examples
        --------
        >>> # export WIJJIT_DEBUG=1
        >>> # export WIJJIT_ENABLE_MOUSE=0
        >>> # export WIJJIT_LOG_LEVEL=DEBUG
        >>> app.config.from_prefixed_env('WIJJIT_')
        """
        prefix_len = len(prefix)
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[prefix_len:]

                # Try to parse as bool/int/float
                if value.lower() in ("true", "1", "yes", "on"):
                    value = True
                elif value.lower() in ("false", "0", "no", "off"):
                    value = False
                elif value.replace(".", "", 1).replace("-", "", 1).isdigit():
                    value = float(value) if "." in value else int(value)

                self[config_key] = value

    def get_namespace(
        self, namespace: str, lowercase: bool = True, trim_namespace: bool = True
    ) -> dict:
        """Get all config values for a namespace.

        Parameters
        ----------
        namespace : str
            Namespace prefix (e.g., 'NOTIFICATION_')
        lowercase : bool
            Convert keys to lowercase
        trim_namespace : bool
            Remove namespace prefix from keys

        Returns
        -------
        dict
            Dictionary of matching config values

        Examples
        --------
        >>> # Get all notification settings
        >>> notif_config = app.config.get_namespace('NOTIFICATION_')
        >>> # Returns: {'duration': 3.0, 'position': 'top_right', ...}
        """
        rv = {}
        for k, v in self.items():
            if not k.startswith(namespace):
                continue
            if trim_namespace:
                key = k[len(namespace) :]
            else:
                key = k
            if lowercase:
                key = key.lower()
            rv[key] = v
        return rv


class DefaultConfig:
    """Default configuration values for Wijjit.

    These are the framework defaults. Override them by setting
    app.config values or loading from a config file.

    All configuration keys should be UPPERCASE by convention.
    """

    # ============================================================
    # INPUT & INTERACTION
    # ============================================================

    #: Enable mouse event tracking
    ENABLE_MOUSE = True

    #: Mouse tracking mode: 'button_event', 'all_events', or 'drag'
    MOUSE_TRACKING_MODE = "button_event"

    #: Enable Tab/Shift+Tab navigation between focusable elements
    ENABLE_FOCUS_NAVIGATION = True

    #: Key binding to quit application (e.g., 'ctrl+q', 'ctrl+c', 'q')
    QUIT_KEY = "ctrl+q"

    # ============================================================
    # DISPLAY & TERMINAL
    # ============================================================

    #: Use alternate screen buffer (recommended for full-screen TUIs)
    USE_ALTERNATE_SCREEN = True

    #: Hide cursor during application runtime
    HIDE_CURSOR = True

    # ============================================================
    # COLORS & THEMING
    # ============================================================

    #: Disable all ANSI colors (respects NO_COLOR env var standard)
    #: https://no-color.org/
    NO_COLOR = os.environ.get("NO_COLOR") is not None

    #: Force color output even if terminal doesn't appear to support it
    FORCE_COLOR = False

    #: Default theme to use: 'default', 'dark', 'light', or custom theme name
    DEFAULT_THEME = "default"

    #: Path to custom theme file (JSON or CSS format), overrides DEFAULT_THEME
    THEME_FILE = None

    #: Path to custom CSS stylesheet file for additional styles
    STYLE_FILE = None

    #: Unicode support: 'auto' (detect), 'force' (always use), 'disable' (ASCII only)
    UNICODE_SUPPORT = "auto"

    # ============================================================
    # PERFORMANCE & THREADING
    # ============================================================

    #: Auto-refresh interval in seconds (None = disabled, used for animations)
    REFRESH_INTERVAL = None

    #: Default frames per second for animations (spinners, progress bars)
    DEFAULT_ANIMATION_FPS = 5

    #: Maximum frames per second (None = unlimited, int = cap FPS)
    MAX_FPS = None

    #: Run synchronous event handlers in thread pool executor
    RUN_SYNC_IN_EXECUTOR = False

    #: Maximum worker threads for executor (None = auto-detect)
    EXECUTOR_MAX_WORKERS = None

    # ============================================================
    # RENDERING
    # ============================================================

    #: Use diff-based rendering (only update changed cells)
    USE_DIFF_RENDERING = True

    #: Minimum time between renders in milliseconds (throttling)
    RENDER_THROTTLE_MS = 0

    # ============================================================
    # NOTIFICATIONS
    # ============================================================

    #: Default notification duration in seconds
    NOTIFICATION_DURATION = 3.0

    #: Notification position: 'top_right', 'top_left', 'bottom_right', 'bottom_left'
    NOTIFICATION_POSITION = "top_right"

    #: Spacing between stacked notifications (in lines)
    NOTIFICATION_SPACING = 1

    #: Margin from screen edge (in characters)
    NOTIFICATION_MARGIN = 2

    #: Maximum concurrent notifications (older ones are dismissed)
    NOTIFICATION_MAX_STACK = 5

    # ============================================================
    # LOGGING
    # ============================================================

    #: Logging level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    LOG_LEVEL = os.environ.get("WIJJIT_LOG_LEVEL", "WARNING")

    #: Log file path (None = no file logging)
    LOG_FILE = os.environ.get("WIJJIT_LOG_FILE")

    #: Log to console (stderr)
    LOG_TO_CONSOLE = False

    #: Log format string (Python logging format)
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ============================================================
    # DEVELOPMENT & DEBUGGING
    # ============================================================

    #: Master debug flag (enables various debug features)
    DEBUG = False

    #: Display FPS counter on screen
    SHOW_FPS = False

    #: Visualize element bounds (draw rectangles around elements)
    SHOW_BOUNDS = False

    #: Log all keyboard events to debug log
    DEBUG_INPUT_KEYBOARD = False

    #: Log all mouse events to debug log
    DEBUG_INPUT_MOUSE = False

    #: Warn when render time exceeds threshold (milliseconds, None = disabled)
    WARN_SLOW_RENDER_MS = None

    # ============================================================
    # TEMPLATES
    # ============================================================

    #: Template directory path
    TEMPLATE_DIR = None

    #: Automatically reload templates when files change (for development)
    TEMPLATE_AUTO_RELOAD = False

    # ============================================================
    # ACCESSIBILITY
    # ============================================================

    #: Reduce or disable animations (for motion sensitivity)
    REDUCE_MOTION = False

    #: Use high contrast colors
    HIGH_CONTRAST = False

    # ============================================================
    # TESTING & CI
    # ============================================================

    #: Testing mode (may affect behavior for test stability)
    TESTING = False

    #: CI/CD mode (implies NO_COLOR, disables animations, etc.)
    CI = os.environ.get("CI") is not None

    #: Headless mode for automated testing (no terminal required)
    HEADLESS = False
