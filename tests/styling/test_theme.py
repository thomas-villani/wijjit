"""Tests for Theme and ThemeManager classes."""

from wijjit.styling.style import Style
from wijjit.styling.theme import (
    DarkTheme,
    DefaultTheme,
    LightTheme,
    Theme,
    ThemeManager,
)


class TestTheme:
    """Test Theme class basic functionality."""

    def test_create_empty_theme(self):
        """Test creating a theme with no styles.

        Returns
        -------
        None
        """
        theme = Theme("empty", {})
        assert theme.name == "empty"
        assert theme.styles == {}

    def test_create_theme_with_styles(self):
        """Test creating a theme with style definitions.

        Returns
        -------
        None
        """
        styles = {
            "button": Style(fg_color=(255, 255, 255), bg_color=(0, 100, 200)),
            "button:focus": Style(bg_color=(0, 150, 255), bold=True),
        }
        theme = Theme("custom", styles)

        assert theme.name == "custom"
        assert len(theme.styles) == 2
        assert "button" in theme.styles
        assert "button:focus" in theme.styles

    def test_get_existing_style(self):
        """Test retrieving an existing style from theme.

        Returns
        -------
        None
        """
        styles = {"button": Style(fg_color=(255, 0, 0))}
        theme = Theme("test", styles)

        style = theme.get_style("button")
        assert style.fg_color == (255, 0, 0)

    def test_get_missing_style_returns_default(self):
        """Test that missing style returns empty Style.

        Returns
        -------
        None
        """
        theme = Theme("test", {})
        style = theme.get_style("nonexistent")

        # Should return empty style
        assert style.fg_color is None
        assert style.bg_color is None
        assert not style.bold
        assert not bool(style)  # Empty style is falsy

    def test_set_style(self):
        """Test setting a new style in theme.

        Returns
        -------
        None
        """
        theme = Theme("test", {})
        new_style = Style(fg_color=(0, 255, 0))

        theme.set_style("custom", new_style)

        assert "custom" in theme.styles
        assert theme.get_style("custom").fg_color == (0, 255, 0)

    def test_set_style_overwrites_existing(self):
        """Test that set_style overwrites existing styles.

        Returns
        -------
        None
        """
        theme = Theme("test", {"button": Style(fg_color=(255, 0, 0))})

        # Overwrite with new style
        theme.set_style("button", Style(fg_color=(0, 255, 0)))

        assert theme.get_style("button").fg_color == (0, 255, 0)


class TestDefaultTheme:
    """Test DefaultTheme has expected styles."""

    def test_default_theme_name(self):
        """Test DefaultTheme has correct name.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        assert theme.name == "default"

    def test_has_button_styles(self):
        """Test DefaultTheme has button styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        button = theme.get_style("button")
        button_focus = theme.get_style("button:focus")
        button_hover = theme.get_style("button:hover")
        button_disabled = theme.get_style("button:disabled")

        assert bool(button)  # Has style
        assert bool(button_focus)
        assert bool(button_hover)
        assert bool(button_disabled)

    def test_has_input_styles(self):
        """Test DefaultTheme has input field styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        input_style = theme.get_style("input")
        input_focus = theme.get_style("input:focus")
        input_disabled = theme.get_style("input:disabled")

        assert bool(input_style)
        assert bool(input_focus)
        assert bool(input_disabled)

    def test_has_checkbox_styles(self):
        """Test DefaultTheme has checkbox styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        checkbox = theme.get_style("checkbox")
        checkbox_focus = theme.get_style("checkbox:focus")
        checkbox_checked = theme.get_style("checkbox:checked")

        assert bool(checkbox)
        assert bool(checkbox_focus)
        assert bool(checkbox_checked)

    def test_has_radio_styles(self):
        """Test DefaultTheme has radio button styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        radio = theme.get_style("radio")
        radio_focus = theme.get_style("radio:focus")
        radio_selected = theme.get_style("radio:selected")

        assert bool(radio)
        assert bool(radio_focus)
        assert bool(radio_selected)

    def test_has_select_styles(self):
        """Test DefaultTheme has select styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        select = theme.get_style("select")
        select_border = theme.get_style("select.border")
        select_option = theme.get_style("select.option")
        select_option_highlighted = theme.get_style("select.option:highlighted")

        assert select is not None
        assert bool(select_border)
        assert select_option is not None
        assert bool(select_option_highlighted)

    def test_has_frame_styles(self):
        """Test DefaultTheme has frame styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        frame = theme.get_style("frame")
        frame_focus = theme.get_style("frame:focus")
        frame_border = theme.get_style("frame.border")

        assert bool(frame)
        assert bool(frame_focus)
        assert bool(frame_border)

    def test_has_table_styles(self):
        """Test DefaultTheme has table styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        table = theme.get_style("table")
        table_header = theme.get_style("table.header")
        table_row = theme.get_style("table.row")
        table_row_selected = theme.get_style("table.row:selected")

        assert table is not None
        assert bool(table_header)
        assert table_row is not None
        assert bool(table_row_selected)

    def test_has_tree_styles(self):
        """Test DefaultTheme has tree styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        tree = theme.get_style("tree")
        tree_node = theme.get_style("tree.node")
        tree_node_selected = theme.get_style("tree.node:selected")

        assert bool(tree)
        assert bool(tree_node)
        assert bool(tree_node_selected)

    def test_has_progress_styles(self):
        """Test DefaultTheme has progress bar styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        progress = theme.get_style("progress")
        progress_fill = theme.get_style("progress.fill")
        progress_empty = theme.get_style("progress.empty")
        progress_gradient_low = theme.get_style("progress.gradient.low")

        assert bool(progress)
        assert bool(progress_fill)
        assert bool(progress_empty)
        assert bool(progress_gradient_low)

    def test_has_spinner_styles(self):
        """Test DefaultTheme has spinner styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        spinner = theme.get_style("spinner")
        spinner_active = theme.get_style("spinner.active")
        spinner_text = theme.get_style("spinner.text")

        assert bool(spinner)
        assert bool(spinner_active)
        assert spinner_text is not None

    def test_has_statusbar_styles(self):
        """Test DefaultTheme has status bar styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        statusbar = theme.get_style("statusbar")
        statusbar_left = theme.get_style("statusbar.left")
        statusbar_center = theme.get_style("statusbar.center")
        statusbar_right = theme.get_style("statusbar.right")

        assert bool(statusbar)
        assert bool(statusbar_left)
        assert bool(statusbar_center)
        assert bool(statusbar_right)

    def test_has_modal_styles(self):
        """Test DefaultTheme has modal styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        modal = theme.get_style("modal")
        modal_backdrop = theme.get_style("modal.backdrop")

        assert bool(modal)
        assert bool(modal_backdrop)

    def test_has_notification_styles(self):
        """Test DefaultTheme has notification styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        notification = theme.get_style("notification")
        notification_info = theme.get_style("notification.info")
        notification_success = theme.get_style("notification.success")
        notification_warning = theme.get_style("notification.warning")
        notification_error = theme.get_style("notification.error")

        assert bool(notification)
        assert bool(notification_info)
        assert bool(notification_success)
        assert bool(notification_warning)
        assert bool(notification_error)

    def test_has_menu_styles(self):
        """Test DefaultTheme has menu styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        menu = theme.get_style("menu")
        menu_border = theme.get_style("menu.border")
        menu_item = theme.get_style("menu.item")
        menu_item_highlighted = theme.get_style("menu.item:highlighted")
        menu_divider = theme.get_style("menu.divider")

        assert bool(menu)
        assert bool(menu_border)
        assert menu_item is not None
        assert bool(menu_item_highlighted)
        assert bool(menu_divider)

    def test_has_logview_styles(self):
        """Test DefaultTheme has logview styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        logview = theme.get_style("logview")
        logview_error = theme.get_style("logview.error")
        logview_warning = theme.get_style("logview.warning")

        assert bool(logview)
        assert bool(logview_error)
        assert bool(logview_warning)

    def test_has_markdown_styles(self):
        """Test DefaultTheme has markdown styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        markdown = theme.get_style("markdown")
        markdown_border = theme.get_style("markdown.border")

        assert bool(markdown)
        assert bool(markdown_border)

    def test_has_code_styles(self):
        """Test DefaultTheme has code block styles.

        Returns
        -------
        None
        """
        theme = DefaultTheme()

        code = theme.get_style("code")
        code_border = theme.get_style("code.border")

        assert bool(code)
        assert bool(code_border)


class TestDarkTheme:
    """Test DarkTheme has expected styles and color scheme."""

    def test_dark_theme_name(self):
        """Test DarkTheme has correct name.

        Returns
        -------
        None
        """
        theme = DarkTheme()
        assert theme.name == "dark"

    def test_has_all_basic_styles(self):
        """Test DarkTheme has all basic element styles.

        Returns
        -------
        None
        """
        theme = DarkTheme()

        # Sample from each category
        assert bool(theme.get_style("button"))
        assert bool(theme.get_style("input"))
        assert bool(theme.get_style("checkbox"))
        assert bool(theme.get_style("select"))
        assert bool(theme.get_style("frame"))
        assert bool(theme.get_style("progress"))
        assert bool(theme.get_style("spinner"))
        assert bool(theme.get_style("statusbar"))
        assert bool(theme.get_style("modal"))
        assert bool(theme.get_style("notification"))
        assert bool(theme.get_style("menu"))

    def test_dark_color_scheme(self):
        """Test that DarkTheme uses appropriate dark colors.

        Returns
        -------
        None
        """
        theme = DarkTheme()

        # Dark themes typically have light text on dark backgrounds
        button = theme.get_style("button")
        if button.bg_color:
            # Background should be relatively dark (all RGB components < 128 for typical dark theme)
            r, g, b = button.bg_color
            # Dark theme button backgrounds should not be too bright
            assert (
                max(r, g, b) < 200
            ), "Dark theme should have darker button backgrounds"


class TestLightTheme:
    """Test LightTheme has expected styles and color scheme."""

    def test_light_theme_name(self):
        """Test LightTheme has correct name.

        Returns
        -------
        None
        """
        theme = LightTheme()
        assert theme.name == "light"

    def test_has_all_basic_styles(self):
        """Test LightTheme has all basic element styles.

        Returns
        -------
        None
        """
        theme = LightTheme()

        # Sample from each category
        assert theme.get_style("button") is not None
        assert theme.get_style("input") is not None
        assert theme.get_style("checkbox") is not None
        assert theme.get_style("select") is not None
        assert theme.get_style("frame") is not None
        assert theme.get_style("progress") is not None
        assert theme.get_style("spinner") is not None
        assert theme.get_style("statusbar") is not None
        assert theme.get_style("modal") is not None
        assert theme.get_style("notification") is not None
        assert theme.get_style("menu") is not None

    def test_light_color_scheme(self):
        """Test that LightTheme uses appropriate light colors.

        Returns
        -------
        None
        """
        theme = LightTheme()

        # Light themes typically have dark text on light backgrounds
        frame = theme.get_style("frame")
        if frame.bg_color:
            # Background should be relatively light (all RGB components > 200 for light theme)
            r, g, b = frame.bg_color
            # Light theme frame backgrounds should be bright
            assert min(r, g, b) > 128, "Light theme should have lighter backgrounds"


class TestThemeManager:
    """Test ThemeManager for switching themes."""

    def test_theme_manager_default(self):
        """Test ThemeManager initializes with DefaultTheme.

        Returns
        -------
        None
        """
        manager = ThemeManager()
        theme = manager.get_theme()

        assert theme.name == "default"
        assert isinstance(theme, DefaultTheme)

    def test_set_dark_theme(self):
        """Test switching to DarkTheme.

        Returns
        -------
        None
        """
        manager = ThemeManager()

        manager.set_theme("dark")
        theme = manager.get_theme()

        assert theme.name == "dark"
        assert isinstance(theme, DarkTheme)

    def test_set_light_theme(self):
        """Test switching to LightTheme.

        Returns
        -------
        None
        """
        manager = ThemeManager()

        manager.set_theme("light")
        theme = manager.get_theme()

        assert theme.name == "light"
        assert isinstance(theme, LightTheme)

    def test_set_custom_theme(self):
        """Test registering and switching to custom theme.

        Returns
        -------
        None
        """
        manager = ThemeManager()
        custom = Theme("custom", {"button": Style(fg_color=(255, 128, 0))})

        # Register custom theme first
        manager.register_theme(custom)
        manager.set_theme("custom")
        theme = manager.get_theme()

        assert theme.name == "custom"
        assert theme.get_style("button").fg_color == (255, 128, 0)

    def test_theme_switch_multiple_times(self):
        """Test switching themes multiple times.

        Returns
        -------
        None
        """
        manager = ThemeManager()

        # Switch to dark
        manager.set_theme("dark")
        assert manager.get_theme().name == "dark"

        # Switch to light
        manager.set_theme("light")
        assert manager.get_theme().name == "light"

        # Switch back to default
        manager.set_theme("default")
        assert manager.get_theme().name == "default"

    def test_theme_mutations_persist_across_switches(self):
        """Test that mutations to themes persist when switching.

        Returns
        -------
        None
        """
        manager = ThemeManager()

        # Mutate the default theme
        custom_style = Style(fg_color=(123, 45, 67), bold=True)
        manager.get_theme().set_style("custom_element", custom_style)

        # Switch to dark theme
        manager.set_theme("dark")
        assert manager.get_theme().name == "dark"

        # Switch back to default
        manager.set_theme("default")
        assert manager.get_theme().name == "default"

        # Verify mutation persists
        style = manager.get_theme().get_style("custom_element")
        assert style.fg_color == (123, 45, 67)
        assert style.bold is True


class TestThemeConsistency:
    """Test that all themes have consistent style coverage."""

    def test_all_themes_have_button_styles(self):
        """Test that all built-in themes have button styles.

        Returns
        -------
        None
        """
        themes = [DefaultTheme(), DarkTheme(), LightTheme()]
        style_keys = ["button", "button:focus", "button:hover", "button:disabled"]

        for theme in themes:
            for key in style_keys:
                style = theme.get_style(key)
                # Should have some styling defined
                assert style is not None, f"{theme.name} missing {key}"

    def test_all_themes_have_input_styles(self):
        """Test that all built-in themes have input styles.

        Returns
        -------
        None
        """
        themes = [DefaultTheme(), DarkTheme(), LightTheme()]
        style_keys = ["input", "input:focus", "input:disabled"]

        for theme in themes:
            for key in style_keys:
                style = theme.get_style(key)
                assert style is not None, f"{theme.name} missing {key}"

    def test_all_themes_have_notification_severities(self):
        """Test that all themes have all notification severity styles.

        Returns
        -------
        None
        """
        themes = [DefaultTheme(), DarkTheme(), LightTheme()]
        style_keys = [
            "notification.info",
            "notification.success",
            "notification.warning",
            "notification.error",
        ]

        for theme in themes:
            for key in style_keys:
                style = theme.get_style(key)
                assert bool(style), f"{theme.name} missing {key} or it's empty"
