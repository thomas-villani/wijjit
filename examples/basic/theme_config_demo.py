"""Theme Configuration Demo.

This example demonstrates how to load themes using the configuration system.
Shows THEME_FILE and DEFAULT_THEME config options.
"""

import os

from wijjit import Wijjit

# ==============================================================================
# METHOD 1: Load theme via THEME_FILE config
# ==============================================================================


def demo_theme_file():
    """Load a custom theme from a CSS file via config."""
    print("\n=== Demo 1: THEME_FILE ===")

    app = Wijjit()

    # Point to an existing CSS theme file
    css_path = os.path.join(os.path.dirname(__file__), "../styling/custom_theme.css")

    if os.path.exists(css_path):
        app.config["THEME_FILE"] = css_path
        # Theme will be auto-loaded when renderer initializes
        # Note: Since renderer is already init, we'd need to reload
        # For demo, we'll show the config approach for new apps

        print(f"THEME_FILE set to: {css_path}")
        print("(In real usage, set config before app runs)")
    else:
        print(f"CSS theme not found at: {css_path}")
        print("Using default theme instead")


# ==============================================================================
# METHOD 2: Use built-in theme via DEFAULT_THEME config
# ==============================================================================


def demo_default_theme():
    """Select a built-in theme via DEFAULT_THEME config."""
    print("\n=== Demo 2: DEFAULT_THEME ===")

    app = Wijjit()

    # Use built-in dark theme
    app.config["DEFAULT_THEME"] = "dark"

    print(f"DEFAULT_THEME set to: {app.config['DEFAULT_THEME']}")

    @app.view("main", default=True)
    def main_view():
        template = """
{% frame border="single" title="Dark Theme Demo" %}
  {% vstack spacing=1 %}
    This uses the built-in 'dark' theme
    configured via DEFAULT_THEME config.

    Available built-in themes:
    - default
    - dark
    - light

    Press 'q' to quit
  {% endvstack %}
{% endframe %}
"""
        return {"template": template}

    print("\nRunning app with dark theme...")
    app.run()


# ==============================================================================
# METHOD 3: Load theme from config file
# ==============================================================================


def demo_config_file():
    """Load theme settings from a config file."""
    print("\n=== Demo 3: Config File ===")

    # Create temp config file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Wijjit Configuration\n")
        f.write("DEFAULT_THEME = 'dark'\n")
        f.write("ENABLE_MOUSE = False\n")
        f.write("QUIT_KEY = 'q'\n")
        config_path = f.name

    try:
        app = Wijjit()
        app.config.from_pyfile(config_path)

        print(f"Loaded config from: {config_path}")
        print(f"  DEFAULT_THEME: {app.config['DEFAULT_THEME']}")
        print(f"  ENABLE_MOUSE: {app.config['ENABLE_MOUSE']}")
        print(f"  QUIT_KEY: {app.config['QUIT_KEY']}")

        @app.view("main", default=True)
        def main_view():
            template = """
{% frame border="single" title="Config File Theme Demo" %}
  {% vstack spacing=1 %}
    Theme loaded from config.py file

    Current settings:
    - Theme: {{ config.DEFAULT_THEME }}
    - Mouse: {{ config.ENABLE_MOUSE }}
    - Quit key: {{ config.QUIT_KEY }}

    Press '{{ config.QUIT_KEY }}' to quit
  {% endvstack %}
{% endframe %}
"""
            return {"template": template, "data": {"config": app.config}}

        print("\nRunning app with config file settings...")
        app.run()

    finally:
        os.unlink(config_path)


# ==============================================================================
# METHOD 4: Environment variable configuration
# ==============================================================================


def demo_env_vars():
    """Load theme via environment variables."""
    print("\n=== Demo 4: Environment Variables ===")
    print("\nYou can set:")
    print("  export WIJJIT_DEFAULT_THEME=dark")
    print("  export WIJJIT_THEME_FILE=/path/to/theme.css")
    print("\nThese are automatically loaded by Wijjit()")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("THEME CONFIGURATION DEMO")
    print("=" * 60)

    if len(sys.argv) > 1:
        demo_choice = sys.argv[1]
    else:
        print("\nAvailable demos:")
        print("  1: THEME_FILE (load from CSS)")
        print("  2: DEFAULT_THEME (built-in themes)")
        print("  3: Config file (load all settings from file)")
        print("  4: Environment variables (WIJJIT_* vars)")
        print("\nRun with: python theme_config_demo.py <number>")
        print("Or press Enter to run demo 2 (DEFAULT_THEME)...")
        demo_choice = input("> ").strip() or "2"

    if demo_choice == "1":
        demo_theme_file()
    elif demo_choice == "2":
        demo_default_theme()
    elif demo_choice == "3":
        demo_config_file()
    elif demo_choice == "4":
        demo_env_vars()
    else:
        print(f"Unknown demo: {demo_choice}")
        sys.exit(1)
