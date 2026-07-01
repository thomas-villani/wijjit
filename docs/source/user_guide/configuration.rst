Configuration
=============

Wijjit uses a Flask-inspired configuration system for managing application settings. All configuration is handled through the ``app.config`` object, which provides a flexible and intuitive API for loading and managing settings.

Overview
--------

The configuration system provides:

* **Multiple loading methods**: Direct assignment, files, objects, environment variables
* **Type-safe defaults**: All options have sensible defaults defined in ``DefaultConfig``
* **Auto-loading**: ``WIJJIT_*`` environment variables are automatically loaded
* **Validation**: Invalid values are logged with warnings
* **Documentation**: All options are documented with inline comments

Quick Start
-----------

Basic configuration is simple and intuitive:

.. code-block:: python

   from wijjit import Wijjit

   app = Wijjit()

   # Direct assignment
   app.config['ENABLE_MOUSE'] = False
   app.config['QUIT_KEY'] = 'q'
   app.config['DEBUG'] = True

   # Bulk update
   app.config.update(
       LOG_LEVEL='INFO',
       NOTIFICATION_DURATION=5.0,
       SHOW_FPS=True
   )

Configuration Loading Methods
-----------------------------

The ``Config`` class provides six methods for loading configuration:

1. Direct Assignment
~~~~~~~~~~~~~~~~~~~~

The simplest method - just set values directly:

.. code-block:: python

   app.config['DEBUG'] = True
   app.config['ENABLE_MOUSE'] = False
   app.config['THEME_FILE'] = 'my_theme.css'

2. Bulk Update
~~~~~~~~~~~~~~

Update multiple values at once using ``update()``:

.. code-block:: python

   app.config.update(
       DEBUG=True,
       LOG_LEVEL='DEBUG',
       SHOW_FPS=True,
       NOTIFICATION_MAX_STACK=10
   )

3. From Python File
~~~~~~~~~~~~~~~~~~~

Load configuration from a Python file with uppercase variables:

.. code-block:: python

   # config.py
   DEBUG = True
   ENABLE_MOUSE = False
   LOG_LEVEL = 'INFO'
   NOTIFICATION_DURATION = 5.0
   QUIT_KEY = 'q'
   THEME_FILE = 'themes/custom.css'

.. code-block:: python

   # app.py
   app.config.from_pyfile('config.py')

4. From Python Object
~~~~~~~~~~~~~~~~~~~~~

Load configuration from a class or module:

.. code-block:: python

   class DevelopmentConfig:
       DEBUG = True
       LOG_LEVEL = 'DEBUG'
       SHOW_FPS = True
       WARN_SLOW_RENDER_MS = 50

   class ProductionConfig:
       DEBUG = False
       LOG_LEVEL = 'WARNING'
       RUN_SYNC_IN_EXECUTOR = True
       EXECUTOR_MAX_WORKERS = 4

   # Load based on environment
   import os
   if os.getenv('ENV') == 'production':
       app.config.from_object(ProductionConfig)
   else:
       app.config.from_object(DevelopmentConfig)

``from_object`` also accepts a dotted **string** path, resolved Flask-style, so
the config target can be selected entirely from configuration/environment without
importing it yourself:

.. code-block:: python

   app.config.from_object('myproject.settings')             # a module
   app.config.from_object('myproject.settings.ProdConfig')  # module attribute
   app.config.from_object('myproject.settings:ProdConfig')  # explicit module:attr form

5. From Environment Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Load configuration from a file path stored in an environment variable:

.. code-block:: bash

   export WIJJIT_SETTINGS=/path/to/config.py

.. code-block:: python

   app.config.from_envvar('WIJJIT_SETTINGS')

6. From Prefixed Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Environment variables with the ``WIJJIT_`` prefix are automatically loaded:

.. code-block:: bash

   export WIJJIT_DEBUG=1
   export WIJJIT_ENABLE_MOUSE=0
   export WIJJIT_LOG_LEVEL=DEBUG
   export WIJJIT_QUIT_KEY=q
   export WIJJIT_THEME_FILE=/path/to/theme.css

.. code-block:: python

   # These are automatically loaded in Wijjit.__init__()
   app = Wijjit()
   # app.config['DEBUG'] is now True
   # app.config['ENABLE_MOUSE'] is now False

Configuration Options Reference
-------------------------------

Input & Interaction (4 options)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ENABLE_MOUSE
^^^^^^^^^^^^

:Type: ``bool``
:Default: ``True``
:Description: Enable mouse event tracking (clicks, hovers, scrolling)

.. code-block:: python

   app.config['ENABLE_MOUSE'] = False  # Keyboard-only mode

MOUSE_TRACKING_MODE
^^^^^^^^^^^^^^^^^^^

:Type: ``str``
:Default: ``'button_event'``
:Values: ``'button_event'``, ``'all_events'``, ``'drag'``
:Description: Controls which mouse events are tracked

.. code-block:: python

   app.config['MOUSE_TRACKING_MODE'] = 'all_events'  # Track all movement

ENABLE_FOCUS_NAVIGATION
^^^^^^^^^^^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``True``
:Description: Enable Tab/Shift+Tab navigation between focusable elements

.. code-block:: python

   app.config['ENABLE_FOCUS_NAVIGATION'] = False  # Disable tab navigation

QUIT_KEY
^^^^^^^^

:Type: ``str``
:Default: ``'ctrl+q'``
:Description: Key binding to quit the application

.. code-block:: python

   app.config['QUIT_KEY'] = 'q'        # Just 'q'
   app.config['QUIT_KEY'] = 'ctrl+c'   # Ctrl+C
   app.config['QUIT_KEY'] = 'escape'   # ESC key

Display & Terminal (3 options)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

USE_ALTERNATE_SCREEN
^^^^^^^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``True``
:Description: Use alternate screen buffer (recommended for full-screen TUIs)

.. code-block:: python

   app.config['USE_ALTERNATE_SCREEN'] = False  # Use normal screen

HIDE_CURSOR
^^^^^^^^^^^

:Type: ``bool``
:Default: ``True``
:Description: Hide terminal cursor during application runtime

.. code-block:: python

   app.config['HIDE_CURSOR'] = False  # Keep cursor visible

APP_TITLE
^^^^^^^^^

:Type: ``str`` or ``None``
:Default: ``None``
:Description: Terminal window/tab title (OSC 0 text). When set, Wijjit emits the title on startup so the terminal tab or window shows it. Most shells reset the title from their prompt hook when the app exits, so no explicit restore is performed. ``None`` leaves the terminal title untouched.

.. code-block:: python

   app.config['APP_TITLE'] = 'My Wijjit App'  # Set the terminal title

Process Control (1 option)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

ENABLE_SUSPEND
^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``True``
:Description: Enable Ctrl+Z suspend/background support on Unix-like systems (Linux, macOS, BSD). When enabled, pressing Ctrl+Z will properly suspend the application to the background, and ``fg`` will resume it. On Windows, this option is ignored.

.. code-block:: python

   app.config['ENABLE_SUSPEND'] = False  # Disable Ctrl+Z suspend

.. tip::
   When suspended with Ctrl+Z, Wijjit automatically:

   1. Saves terminal state (alternate screen, cursor, mouse tracking)
   2. Restores normal terminal so you can use the shell
   3. On resume (``fg``), restores TUI state and triggers a re-render

.. note::
   This feature only works on Unix-like systems. On Windows, job control signals are not available.

Colors & Theming (6 options)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FOCUS_COLOR
^^^^^^^^^^^

:Type: ``tuple`` of 3 ``int`` or ``None``
:Default: ``None``
:Description: Global focus color override (R, G, B). When set, all focused elements use this foreground color instead of theme defaults.

.. code-block:: python

   app.config['FOCUS_COLOR'] = (0, 255, 255)    # Cyan focus (default theme color)
   app.config['FOCUS_COLOR'] = (255, 128, 0)    # Orange focus
   app.config['FOCUS_COLOR'] = (0, 255, 0)      # Green focus
   app.config['FOCUS_COLOR'] = None             # Use theme defaults

This is useful for:

* Ensuring consistent focus indication across all themes
* Accessibility (high-visibility focus colors)
* Branding (matching focus color to app accent color)

NO_COLOR
^^^^^^^^

:Type: ``bool``
:Default: Auto-detected from ``NO_COLOR`` env var
:Description: Disable all ANSI colors (respects `NO_COLOR standard <https://no-color.org/>`_)

.. code-block:: python

   app.config['NO_COLOR'] = True  # Disable colors

.. code-block:: bash

   export NO_COLOR=1  # Automatically disables colors

DEFAULT_THEME
^^^^^^^^^^^^^

:Type: ``str``
:Default: ``'default'``
:Values: ``'default'``, ``'dark'``, ``'light'``, ``'high_contrast'``, or custom theme name
:Description: Built-in theme to use

.. code-block:: python

   app.config['DEFAULT_THEME'] = 'dark'  # Use dark theme

THEME_FILE
^^^^^^^^^^

:Type: ``str`` or ``None``
:Default: ``None``
:Description: Path to custom theme file (CSS or JSON format)

.. code-block:: python

   app.config['THEME_FILE'] = 'themes/custom.css'  # Auto-loaded at startup

STYLE_FILE
^^^^^^^^^^

:Type: ``str`` or ``None``
:Default: ``None``
:Description: Path to additional CSS stylesheet (adds to current theme)

.. code-block:: python

   app.config['STYLE_FILE'] = 'styles/extra.css'  # Additional styles

UNICODE_SUPPORT
^^^^^^^^^^^^^^^

:Type: ``str``
:Default: ``'auto'``
:Values: ``'auto'`` (detect), ``'force'`` (always), ``'disable'`` (never)
:Description: Controls Unicode character support

.. code-block:: python

   app.config['UNICODE_SUPPORT'] = 'force'    # Always use Unicode
   app.config['UNICODE_SUPPORT'] = 'disable'  # ASCII only
   app.config['UNICODE_SUPPORT'] = 'auto'     # Auto-detect (default)

Performance & Threading (5 options)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

REFRESH_INTERVAL
^^^^^^^^^^^^^^^^

:Type: ``float`` or ``None``
:Default: ``None``
:Description: Auto-refresh interval in seconds for animations (None = disabled)

.. code-block:: python

   app.config['REFRESH_INTERVAL'] = 0.1  # 100ms refresh for smooth animations

DEFAULT_ANIMATION_FPS
^^^^^^^^^^^^^^^^^^^^^

:Type: ``int``
:Default: ``5``
:Description: Default frames per second for animations (spinners, progress bars)

.. code-block:: python

   app.config['DEFAULT_ANIMATION_FPS'] = 10  # Smoother animations

MAX_FPS
^^^^^^^

:Type: ``int`` or ``None``
:Default: ``None``
:Description: Maximum frame rate cap (None = unlimited). Limits FPS by sleeping between frames to prevent excessive CPU usage.

.. code-block:: python

   app.config['MAX_FPS'] = 30  # Cap at 30 FPS
   app.config['MAX_FPS'] = 60  # Cap at 60 FPS
   app.config['MAX_FPS'] = None  # Unlimited (default)

.. tip::
   Use ``MAX_FPS`` to reduce CPU usage in resource-constrained environments or when high frame rates aren't needed.

RUN_SYNC_IN_EXECUTOR
^^^^^^^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Run synchronous event handlers in thread pool executor

.. code-block:: python

   app.config['RUN_SYNC_IN_EXECUTOR'] = True  # Prevent UI blocking

EXECUTOR_MAX_WORKERS
^^^^^^^^^^^^^^^^^^^^

:Type: ``int`` or ``None``
:Default: ``None``
:Description: Thread pool size for executor (None = auto-detect)

.. code-block:: python

   app.config['EXECUTOR_MAX_WORKERS'] = 4  # 4 worker threads

Rendering (1 option)
~~~~~~~~~~~~~~~~~~~~~

RENDER_THROTTLE_MS
^^^^^^^^^^^^^^^^^^

:Type: ``int``
:Default: ``0``
:Description: Minimum time between renders in milliseconds (throttling). Prevents renders faster than the specified interval to reduce overhead.

.. code-block:: python

   app.config['RENDER_THROTTLE_MS'] = 16  # Max ~60 FPS
   app.config['RENDER_THROTTLE_MS'] = 33  # Max ~30 FPS
   app.config['RENDER_THROTTLE_MS'] = 0  # No throttling (default)

.. tip::
   Use ``RENDER_THROTTLE_MS`` to limit render frequency and reduce CPU usage from rapid state changes.

Notifications (5 options)
~~~~~~~~~~~~~~~~~~~~~~~~~~

NOTIFICATION_DURATION
^^^^^^^^^^^^^^^^^^^^^

:Type: ``float``
:Default: ``3.0``
:Description: Default notification duration in seconds

.. code-block:: python

   app.config['NOTIFICATION_DURATION'] = 5.0  # 5 second notifications

NOTIFICATION_POSITION
^^^^^^^^^^^^^^^^^^^^^

:Type: ``str``
:Default: ``'top_right'``
:Values: ``'top_right'``, ``'top_left'``, ``'bottom_right'``, ``'bottom_left'``
:Description: Notification stack position

.. code-block:: python

   app.config['NOTIFICATION_POSITION'] = 'bottom_right'

NOTIFICATION_SPACING
^^^^^^^^^^^^^^^^^^^^

:Type: ``int``
:Default: ``1``
:Description: Vertical spacing between stacked notifications (in lines)

.. code-block:: python

   app.config['NOTIFICATION_SPACING'] = 2  # More spacing

NOTIFICATION_MARGIN
^^^^^^^^^^^^^^^^^^^

:Type: ``int``
:Default: ``2``
:Description: Margin from screen edges (in characters)

.. code-block:: python

   app.config['NOTIFICATION_MARGIN'] = 4  # Larger margin

NOTIFICATION_MAX_STACK
^^^^^^^^^^^^^^^^^^^^^^

:Type: ``int`` or ``None``
:Default: ``5``
:Description: Maximum concurrent notifications (oldest dismissed when limit reached)

.. code-block:: python

   app.config['NOTIFICATION_MAX_STACK'] = 10  # Allow 10 notifications
   app.config['NOTIFICATION_MAX_STACK'] = None  # Unlimited

Logging (5 options)
~~~~~~~~~~~~~~~~~~~

LOG_LEVEL
^^^^^^^^^

:Type: ``str``
:Default: ``'WARNING'``
:Values: ``'DEBUG'``, ``'INFO'``, ``'WARNING'``, ``'ERROR'``, ``'CRITICAL'``
:Description: Logging level

.. code-block:: python

   app.config['LOG_LEVEL'] = 'DEBUG'  # Show all logs

LOG_FILE
^^^^^^^^

:Type: ``str`` or ``None``
:Default: ``None``
:Description: Log file path (None = no file logging)

.. code-block:: python

   app.config['LOG_FILE'] = 'app.log'  # Log to file

LOG_TO_CONSOLE
^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Log to console (stderr)

.. code-block:: python

   app.config['LOG_TO_CONSOLE'] = True  # Enable console logging

LOG_FORMAT
^^^^^^^^^^

:Type: ``str``
:Default: ``'%(asctime)s - %(name)s - %(levelname)s - %(message)s'``
:Description: Python logging format string

.. code-block:: python

   app.config['LOG_FORMAT'] = '%(levelname)s: %(message)s'  # Simple format

SUPPRESS_INTERNAL_LOGGING_CONFIG
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: When ``True``, Wijjit will not configure its own loggers, giving the host application full control over logging. Set this if you have pre-configured logging handlers for the ``wijjit`` namespace and don't want Wijjit to override them.

.. code-block:: python

   app.config['SUPPRESS_INTERNAL_LOGGING_CONFIG'] = True  # Host owns logging config

Debug & Development (6 options)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DEBUG
^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Master debug flag (enables various debug features)

.. code-block:: python

   app.config['DEBUG'] = True  # Enable debug mode

SHOW_FPS
^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Display FPS counter in top-right corner

.. code-block:: python

   app.config['SHOW_FPS'] = True  # Show FPS counter

SHOW_BOUNDS
^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Visualize element bounds by drawing colored rectangles around elements. Different colors indicate element types (cyan=input, yellow=display, magenta=container, green=other).

.. code-block:: python

   app.config['SHOW_BOUNDS'] = True  # Show element bounds for debugging

.. tip::
   Use ``SHOW_BOUNDS`` to debug layout issues and understand element positioning.

DEBUG_INPUT_KEYBOARD
^^^^^^^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Log all keyboard events to debug log

.. code-block:: python

   app.config['DEBUG_INPUT_KEYBOARD'] = True  # Log keyboard events

DEBUG_INPUT_MOUSE
^^^^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Log all mouse events to debug log

.. code-block:: python

   app.config['DEBUG_INPUT_MOUSE'] = True  # Log mouse events

WARN_SLOW_RENDER_MS
^^^^^^^^^^^^^^^^^^^

:Type: ``int`` or ``None``
:Default: ``None``
:Description: Warn if render time exceeds threshold (milliseconds, None = disabled)

.. code-block:: python

   app.config['WARN_SLOW_RENDER_MS'] = 100  # Warn if render > 100ms

Templates (2 options)
~~~~~~~~~~~~~~~~~~~~~

TEMPLATE_DIR
^^^^^^^^^^^^

:Type: ``str`` or ``None``
:Default: ``None``
:Description: Directory of file templates loaded with :func:`wijjit.render_template`.
   When left as ``None``, Wijjit auto-discovers a ``templates/`` directory next to
   the module that constructs the app (Flask's convention). Set this to point
   elsewhere, which also disables auto-discovery.

.. code-block:: python

   app.config['TEMPLATE_DIR'] = 'templates/'
   # or, equivalently, at construction time:
   app = Wijjit(template_dir='templates/')

TEMPLATE_AUTO_RELOAD
^^^^^^^^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Automatically reload file templates when they change on disk (for
   development). Wired into the Jinja2 environment's ``auto_reload``.

.. code-block:: python

   app.config['TEMPLATE_AUTO_RELOAD'] = True  # Hot reload templates

HTML Content (1 option)
~~~~~~~~~~~~~~~~~~~~~~~~

HTML_CONTENT
^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Global toggle for HTML content parsing. When ``True``, elements that support HTML will parse HTML tags in their content. Individual elements can still override this with their own ``html=True``/``html=False`` parameter.

.. code-block:: python

   app.config['HTML_CONTENT'] = True  # Parse HTML in content-bearing elements

Accessibility (2 options)
~~~~~~~~~~~~~~~~~~~~~~~~~~

REDUCE_MOTION
^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Reduce or disable animations (for motion sensitivity). When enabled, spinners and other animations freeze at their first frame, providing a static indicator instead.

.. code-block:: python

   app.config['REDUCE_MOTION'] = True  # Disable animations

.. tip::
   Enable ``REDUCE_MOTION`` for users with motion sensitivity or vestibular disorders. Animations can cause discomfort or nausea for some users.

HIGH_CONTRAST
^^^^^^^^^^^^^

:Type: ``bool``
:Default: ``False``
:Description: Use high contrast theme with pure black/white and bright, saturated colors. Automatically switches to the ``high_contrast`` theme for maximum visibility.

.. code-block:: python

   app.config['HIGH_CONTRAST'] = True  # High contrast theme for accessibility

Features of the high contrast theme:

- Pure white (255, 255, 255) text on pure black (0, 0, 0) backgrounds
- Bright, fully saturated accent colors (bright yellow, green, red, cyan)
- Bold text throughout for improved readability
- Strong borders and focus indicators
- No subtle grays or muted effects

.. tip::
   Enable ``HIGH_CONTRAST`` for users with vision impairments or those requiring enhanced visibility. This theme follows WCAG high contrast guidelines.

Common Use Cases
----------------

Development Environment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # config/development.py
   DEBUG = True
   LOG_LEVEL = 'DEBUG'
   SHOW_FPS = True
   WARN_SLOW_RENDER_MS = 50
   DEBUG_INPUT_KEYBOARD = True
   TEMPLATE_AUTO_RELOAD = True

.. code-block:: python

   # app.py
   app.config.from_pyfile('config/development.py')

Production Environment
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # config/production.py
   DEBUG = False
   LOG_LEVEL = 'WARNING'
   LOG_FILE = '/var/log/myapp.log'
   RUN_SYNC_IN_EXECUTOR = True
   EXECUTOR_MAX_WORKERS = 4

.. code-block:: python

   # app.py
   app.config.from_pyfile('config/production.py')

Keyboard-Only Mode
~~~~~~~~~~~~~~~~~~

Perfect for accessibility or when mouse is not available:

.. code-block:: python

   app.config.update(
       ENABLE_MOUSE=False,
       ENABLE_FOCUS_NAVIGATION=True,
       QUIT_KEY='q'  # Simple quit key
   )

Custom Theme with Styles
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   app.config.update(
       THEME_FILE='themes/my_theme.css',  # Base theme
       STYLE_FILE='styles/overrides.css'  # Additional styles
   )

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   app.config.update(
       SHOW_FPS=True,               # Display FPS counter
       WARN_SLOW_RENDER_MS=100,     # Warn on slow renders
       LOG_LEVEL='INFO',            # Log performance info
       LOG_FILE='performance.log'   # Log to file
   )

CI/CD Testing
~~~~~~~~~~~~~

In CI you typically want colorless, deterministic output. Wijjit honors the
``NO_COLOR`` standard, and any ``WIJJIT_*`` variable maps to a real config key:

.. code-block:: bash

   export NO_COLOR=1            # Disable ANSI colors (no-color.org standard)
   export WIJJIT_LOG_LEVEL=DEBUG

.. code-block:: python

   # NO_COLOR and WIJJIT_* vars are picked up in Wijjit.__init__()
   app = Wijjit()  # Colors disabled, debug logging enabled

For driving an app without a real TTY in tests, use the headless harness
(``wijjit.testing.WijjitHarness``) rather than a config flag.

Best Practices
--------------

1. Use Configuration Files for Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of hardcoding settings, use separate config files:

.. code-block:: text

   config/
     ├── development.py
     ├── production.py
     └── testing.py

2. Environment Variables for Secrets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Never commit sensitive data. Use environment variables:

.. code-block:: bash

   export WIJJIT_LOG_FILE=/secure/path/app.log

3. Validate Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Check critical config values at startup:

.. code-block:: python

   app = Wijjit()

   if app.config['THEME_FILE']:
       import os
       if not os.path.exists(app.config['THEME_FILE']):
           raise FileNotFoundError(f"Theme file not found: {app.config['THEME_FILE']}")

4. Use Config Namespaces
~~~~~~~~~~~~~~~~~~~~~~~~~

Group related settings using ``get_namespace()``:

.. code-block:: python

   # Get all notification settings
   notif_config = app.config.get_namespace('NOTIFICATION_')
   print(notif_config)
   # {'duration': 3.0, 'position': 'top_right', ...}

5. Document Custom Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add comments to your config files:

.. code-block:: python

   # config.py

   # Performance settings
   RUN_SYNC_IN_EXECUTOR = True  # Prevent UI blocking
   EXECUTOR_MAX_WORKERS = 4      # Balanced for this server

   # Development helpers
   SHOW_FPS = True              # Monitor performance
   WARN_SLOW_RENDER_MS = 50     # Alert on slow renders

Troubleshooting
---------------

Configuration Not Applied
~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Changed config value but app doesn't reflect it

**Solution**: Ensure config is set before ``app.run()`` or before component initialization:

.. code-block:: python

   app = Wijjit()
   app.config['ENABLE_MOUSE'] = False  # Set BEFORE run()
   app.run()

Environment Variables Not Loaded
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: ``WIJJIT_*`` environment variables not working

**Solution**: Check variable names are uppercase and have ``WIJJIT_`` prefix:

.. code-block:: bash

   # Wrong
   export wijjit_debug=1

   # Correct
   export WIJJIT_DEBUG=1

Boolean parsing also accepts multiple formats:

.. code-block:: bash

   export WIJJIT_DEBUG=true   # or 1, yes, on
   export WIJJIT_DEBUG=false  # or 0, no, off

Theme File Not Loading
~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Theme file specified but not applied

**Solution**: Check file path and format:

.. code-block:: python

   import os

   theme_path = 'themes/custom.css'
   if os.path.exists(theme_path):
       app.config['THEME_FILE'] = theme_path
   else:
       print(f"Theme file not found: {theme_path}")

Also check application logs for theme loading errors:

.. code-block:: python

   app.config['LOG_LEVEL'] = 'DEBUG'  # See theme loading messages

Invalid Config Values
~~~~~~~~~~~~~~~~~~~~~

**Problem**: Invalid config value causes unexpected behavior

**Solution**: Check logs for warnings. Wijjit validates config values and logs warnings:

.. code-block:: python

   app.config['LOG_LEVEL'] = 'DEBUG'  # Enable debug logging

   # Invalid value - will log warning and use default
   app.config['MOUSE_TRACKING_MODE'] = 'invalid'

Examples
--------

See the following example files for complete demonstrations:

* ``examples/basic/config_demo.py`` - Basic configuration methods
* ``examples/basic/theme_config_demo.py`` - Theme loading examples

API Reference
-------------

Config Class
~~~~~~~~~~~~

.. code-block:: python

   from wijjit import Config

   config = Config()

   # Loading methods
   config.from_object(obj)                    # From class/module
   config.from_pyfile(filename, silent=False) # From Python file
   config.from_envvar(var_name, silent=False) # From env var (file path)
   config.from_mapping(dict, **kwargs)        # From dict
   config.from_prefixed_env(prefix='WIJJIT_') # From prefixed env vars

   # Utility methods
   config.get_namespace(prefix, lowercase=True, trim_namespace=True)

DefaultConfig Class
~~~~~~~~~~~~~~~~~~~

All default values are defined in:

.. code-block:: python

   from wijjit import DefaultConfig

   # View defaults
   print(DefaultConfig.ENABLE_MOUSE)  # True
   print(DefaultConfig.QUIT_KEY)      # 'ctrl+q'

See Also
--------

* :doc:`../getting_started/quickstart` - Getting started with Wijjit
* :doc:`styling` - Theming and styling guide
* :doc:`state_management` - State management guide
* ``src/wijjit/config.py`` - Configuration source code
* ``claude-config-next-steps.md`` - Roadmap for future config features
