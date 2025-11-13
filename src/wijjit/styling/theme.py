"""Theme system for managing consistent UI styling across components.

This module provides the Theme and ThemeManager classes for defining and
switching between visual themes (light, dark, custom, etc.).
"""


from wijjit.styling.style import Style


class Theme:
    """A named collection of style definitions for UI elements.

    Themes provide consistent styling across all UI elements by defining
    styles for element classes and pseudo-classes (focus, hover, disabled).

    Parameters
    ----------
    name : str
        Theme name
    styles : dict of str to Style
        Style definitions keyed by element class and pseudo-class

    Attributes
    ----------
    name : str
        Theme name
    styles : dict
        Style definitions

    Examples
    --------
    Create a simple theme:

    >>> theme = Theme('custom', {
    ...     'button': Style(bg_color=(0, 100, 200)),
    ...     'button:focus': Style(bg_color=(0, 120, 255), bold=True)
    ... })
    >>> theme.get_style('button').bg_color
    (0, 100, 200)

    Get focused button style:

    >>> focus_style = theme.get_style('button:focus')
    >>> focus_style.bold
    True
    """

    def __init__(self, name: str, styles: dict[str, Style]):
        self.name = name
        self.styles = styles

    def get_style(self, class_name: str) -> Style:
        """Get style for an element class.

        Parameters
        ----------
        class_name : str
            Element class name (e.g., 'button', 'button:focus')

        Returns
        -------
        Style
            Style for the class, or default empty style if not defined

        Notes
        -----
        Returns an empty Style if the class is not defined in the theme,
        ensuring graceful fallback behavior.

        Examples
        --------
        >>> theme = Theme('test', {'button': Style(bold=True)})
        >>> style = theme.get_style('button')
        >>> style.bold
        True
        >>> unknown = theme.get_style('unknown')
        >>> bool(unknown)
        False
        """
        return self.styles.get(class_name, Style())

    def set_style(self, class_name: str, style: Style) -> None:
        """Set style for an element class.

        Parameters
        ----------
        class_name : str
            Element class name
        style : Style
            Style to set

        Notes
        -----
        Allows runtime modification of themes for customization.

        Examples
        --------
        >>> theme = Theme('custom', {})
        >>> theme.set_style('button', Style(bold=True))
        >>> theme.get_style('button').bold
        True
        """
        self.styles[class_name] = style


class DefaultTheme(Theme):
    """Default theme with sensible defaults for all elements.

    This theme provides a clean, neutral color scheme suitable for most
    terminal environments.
    """

    def __init__(self):
        styles = {
            # Button styles
            "button": Style(
                fg_color=(255, 255, 255),
                bg_color=(0, 100, 200),
            ),
            "button:focus": Style(
                fg_color=(255, 255, 255),
                bg_color=(0, 120, 255),
                bold=True,
            ),
            "button:hover": Style(
                fg_color=(255, 255, 255),
                bg_color=(0, 110, 220),
            ),
            "button:disabled": Style(
                fg_color=(128, 128, 128),
                bg_color=(64, 64, 64),
                dim=True,
            ),
            # Input field styles
            "input": Style(
                fg_color=(0, 255, 255),
                bold=True,
            ),
            "input:focus": Style(
                fg_color=(0, 255, 255),
                bg_color=(30, 30, 30),
                bold=True,
                underline=True,
            ),
            "input:disabled": Style(
                fg_color=(128, 128, 128),
                dim=True,
            ),
            # Checkbox styles
            "checkbox": Style(
                fg_color=(0, 255, 0),
            ),
            "checkbox:focus": Style(
                fg_color=(0, 255, 0),
                bold=True,
            ),
            "checkbox:checked": Style(
                fg_color=(0, 255, 0),
                bold=True,
            ),
            # Radio button styles
            "radio": Style(
                fg_color=(0, 255, 0),
            ),
            "radio:focus": Style(
                fg_color=(0, 255, 0),
                bold=True,
            ),
            "radio:selected": Style(
                fg_color=(0, 255, 0),
                bold=True,
            ),
            # Frame styles
            "frame": Style(
                fg_color=(200, 200, 200),
            ),
            "frame:focus": Style(
                fg_color=(255, 255, 255),
                bold=True,
            ),
            "frame.border": Style(
                fg_color=(100, 100, 100),
            ),
            # Text styles
            "text": Style(),
            "text.title": Style(bold=True),
            "text.subtitle": Style(italic=True),
            "text.muted": Style(dim=True),
            # Table styles
            "table": Style(),
            "table.header": Style(bold=True),
            "table.row": Style(),
            "table.row:selected": Style(reverse=True),
            "table.row:hover": Style(bg_color=(30, 30, 30)),
            # Tree styles
            "tree": Style(),
            "tree.node": Style(),
            "tree.node:selected": Style(reverse=True),
            "tree.node:hover": Style(bg_color=(30, 30, 30)),
            # Status bar styles
            "statusbar": Style(
                fg_color=(255, 255, 255),
                bg_color=(0, 100, 200),
            ),
            # Modal styles
            "modal": Style(
                fg_color=(255, 255, 255),
                bg_color=(40, 40, 40),
            ),
            "modal.backdrop": Style(dim=True),
            # Notification styles
            "notification": Style(
                fg_color=(255, 255, 255),
                bg_color=(100, 100, 100),
            ),
            "notification.info": Style(
                fg_color=(255, 255, 255),
                bg_color=(0, 100, 200),
            ),
            "notification.success": Style(
                fg_color=(255, 255, 255),
                bg_color=(0, 200, 0),
            ),
            "notification.warning": Style(
                fg_color=(0, 0, 0),
                bg_color=(255, 200, 0),
            ),
            "notification.error": Style(
                fg_color=(255, 255, 255),
                bg_color=(200, 0, 0),
            )
        }
        super().__init__("default", styles)


class DarkTheme(Theme):
    """Dark theme with high contrast for reduced eye strain.

    This theme uses darker colors with bright highlights, optimized for
    prolonged terminal use in low-light conditions.
    """

    def __init__(self):
        styles = {
            # Button styles
            "button": Style(
                fg_color=(255, 255, 255),
                bg_color=(60, 60, 120),
            ),
            "button:focus": Style(
                fg_color=(255, 255, 255),
                bg_color=(80, 80, 180),
                bold=True,
            ),
            "button:hover": Style(
                fg_color=(255, 255, 255),
                bg_color=(70, 70, 150),
            ),
            # Input field styles
            "input": Style(
                fg_color=(100, 200, 255),
                bg_color=(20, 20, 40),
            ),
            "input:focus": Style(
                fg_color=(150, 220, 255),
                bg_color=(30, 30, 50),
                bold=True,
            ),
            # Checkbox styles
            "checkbox": Style(
                fg_color=(100, 255, 100),
            ),
            "checkbox:focus": Style(
                fg_color=(150, 255, 150),
                bold=True,
            ),
            "checkbox:checked": Style(
                fg_color=(100, 255, 100),
                bold=True,
            ),
            # Radio button styles
            "radio": Style(
                fg_color=(100, 255, 100),
            ),
            "radio:focus": Style(
                fg_color=(150, 255, 150),
                bold=True,
            ),
            "radio:selected": Style(
                fg_color=(100, 255, 100),
                bold=True,
            ),
            # Frame styles
            "frame": Style(
                fg_color=(180, 180, 200),
                bg_color=(20, 20, 30),
            ),
            "frame:focus": Style(
                fg_color=(220, 220, 255),
                bg_color=(30, 30, 50),
            ),
            "frame.border": Style(
                fg_color=(80, 80, 100),
            ),
            # Text styles
            "text": Style(fg_color=(200, 200, 220)),
            "text.title": Style(fg_color=(255, 255, 255), bold=True),
            "text.subtitle": Style(fg_color=(180, 180, 200), italic=True),
            "text.muted": Style(fg_color=(120, 120, 140)),
            # Table styles
            "table": Style(fg_color=(200, 200, 220)),
            "table.header": Style(fg_color=(255, 255, 255), bold=True),
            "table.row": Style(),
            "table.row:selected": Style(bg_color=(60, 60, 100)),
            "table.row:hover": Style(bg_color=(40, 40, 60)),
            # Tree styles
            "tree": Style(fg_color=(200, 200, 220)),
            "tree.node": Style(),
            "tree.node:selected": Style(bg_color=(60, 60, 100)),
            "tree.node:hover": Style(bg_color=(40, 40, 60)),
            # Status bar styles
            "statusbar": Style(
                fg_color=(255, 255, 255),
                bg_color=(60, 60, 120),
            ),
            # Modal styles
            "modal": Style(
                fg_color=(220, 220, 240),
                bg_color=(30, 30, 50),
            ),
            "modal.backdrop": Style(dim=True),
            # Notification styles
            "notification": Style(
                fg_color=(255, 255, 255),
                bg_color=(80, 80, 100),
            ),
            "notification.info": Style(
                fg_color=(255, 255, 255),
                bg_color=(60, 100, 180),
            ),
            "notification.success": Style(
                fg_color=(255, 255, 255),
                bg_color=(40, 180, 40),
            ),
            "notification.warning": Style(
                fg_color=(0, 0, 0),
                bg_color=(255, 180, 0),
            ),
            "notification.error": Style(
                fg_color=(255, 255, 255),
                bg_color=(200, 40, 40),
            ),
        }
        super().__init__("dark", styles)


class LightTheme(Theme):
    """Light theme for well-lit environments.

    This theme uses lighter backgrounds with dark text, suitable for use
    in bright conditions or for users who prefer light color schemes.
    """

    def __init__(self):
        styles = {
            # Button styles
            "button": Style(
                fg_color=(0, 0, 0),
                bg_color=(180, 200, 255),
            ),
            "button:focus": Style(
                fg_color=(0, 0, 0),
                bg_color=(150, 180, 255),
                bold=True,
            ),
            "button:hover": Style(
                fg_color=(0, 0, 0),
                bg_color=(165, 190, 255),
            ),
            # Input field styles
            "input": Style(
                fg_color=(0, 0, 200),
                bg_color=(240, 240, 250),
            ),
            "input:focus": Style(
                fg_color=(0, 0, 255),
                bg_color=(230, 230, 255),
                underline=True,
            ),
            # Checkbox styles
            "checkbox": Style(
                fg_color=(0, 150, 0),
            ),
            "checkbox:focus": Style(
                fg_color=(0, 200, 0),
                bold=True,
            ),
            "checkbox:checked": Style(
                fg_color=(0, 150, 0),
                bold=True,
            ),
            # Radio button styles
            "radio": Style(
                fg_color=(0, 150, 0),
            ),
            "radio:focus": Style(
                fg_color=(0, 200, 0),
                bold=True,
            ),
            "radio:selected": Style(
                fg_color=(0, 150, 0),
                bold=True,
            ),
            # Frame styles
            "frame": Style(
                fg_color=(50, 50, 50),
                bg_color=(250, 250, 250),
            ),
            "frame:focus": Style(
                fg_color=(0, 0, 0),
                bg_color=(240, 240, 240),
            ),
            "frame.border": Style(
                fg_color=(180, 180, 180),
            ),
            # Text styles
            "text": Style(fg_color=(0, 0, 0)),
            "text.title": Style(fg_color=(0, 0, 0), bold=True),
            "text.subtitle": Style(fg_color=(80, 80, 80), italic=True),
            "text.muted": Style(fg_color=(120, 120, 120)),
            # Table styles
            "table": Style(fg_color=(0, 0, 0)),
            "table.header": Style(fg_color=(0, 0, 0), bold=True, underline=True),
            "table.row": Style(),
            "table.row:selected": Style(bg_color=(200, 220, 255)),
            "table.row:hover": Style(bg_color=(230, 240, 255)),
            # Tree styles
            "tree": Style(fg_color=(0, 0, 0)),
            "tree.node": Style(),
            "tree.node:selected": Style(bg_color=(200, 220, 255)),
            "tree.node:hover": Style(bg_color=(230, 240, 255)),
            # Status bar styles
            "statusbar": Style(
                fg_color=(0, 0, 0),
                bg_color=(180, 200, 255),
            ),
            # Modal styles
            "modal": Style(
                fg_color=(0, 0, 0),
                bg_color=(245, 245, 250),
            ),
            "modal.backdrop": Style(dim=True),
            # Notification styles
            "notification": Style(
                fg_color=(0, 0, 0),
                bg_color=(220, 220, 220),
            ),
            "notification.info": Style(
                fg_color=(0, 0, 0),
                bg_color=(180, 200, 255),
            ),
            "notification.success": Style(
                fg_color=(0, 0, 0),
                bg_color=(150, 255, 150),
            ),
            "notification.warning": Style(
                fg_color=(0, 0, 0),
                bg_color=(255, 220, 100),
            ),
            "notification.error": Style(
                fg_color=(255, 255, 255),
                bg_color=(255, 100, 100),
            ),
        }
        super().__init__("light", styles)


class ThemeManager:
    """Manages theme registration and switching.

    Provides a global registry of themes and handles theme switching at runtime.
    Applications typically use a single ThemeManager instance.

    Attributes
    ----------
    themes : dict of str to Theme
        Registered themes by name
    current_theme : Theme
        Currently active theme

    Examples
    --------
    Create manager with built-in themes:

    >>> manager = ThemeManager()
    >>> manager.get_theme().name
    'default'

    Switch themes:

    >>> manager.set_theme('dark')
    >>> manager.get_theme().name
    'dark'

    Register custom theme:

    >>> custom = Theme('custom', {'button': Style(bold=True)})
    >>> manager.register_theme(custom)
    >>> manager.set_theme('custom')
    """

    def __init__(self):
        self.themes: dict[str, Theme] = {}
        self.current_theme: Theme = DefaultTheme()

        # Register built-in themes
        self.register_theme(DefaultTheme())
        self.register_theme(DarkTheme())
        self.register_theme(LightTheme())

    def register_theme(self, theme: Theme) -> None:
        """Register a theme.

        Parameters
        ----------
        theme : Theme
            Theme to register

        Notes
        -----
        Overwrites any existing theme with the same name.

        Examples
        --------
        >>> manager = ThemeManager()
        >>> custom = Theme('custom', {})
        >>> manager.register_theme(custom)
        >>> 'custom' in manager.themes
        True
        """
        self.themes[theme.name] = theme

    def set_theme(self, theme_name: str) -> None:
        """Set the active theme by name.

        Parameters
        ----------
        theme_name : str
            Name of theme to activate

        Raises
        ------
        KeyError
            If theme name is not registered

        Examples
        --------
        >>> manager = ThemeManager()
        >>> manager.set_theme('dark')
        >>> manager.get_theme().name
        'dark'
        """
        if theme_name not in self.themes:
            raise KeyError(f"Theme '{theme_name}' not found")
        self.current_theme = self.themes[theme_name]

    def get_theme(self) -> Theme:
        """Get the currently active theme.

        Returns
        -------
        Theme
            Current theme

        Examples
        --------
        >>> manager = ThemeManager()
        >>> theme = manager.get_theme()
        >>> theme.name
        'default'
        """
        return self.current_theme

    def list_themes(self) -> list[str]:
        """List all registered theme names.

        Returns
        -------
        list of str
            Names of all registered themes

        Examples
        --------
        >>> manager = ThemeManager()
        >>> themes = manager.list_themes()
        >>> 'default' in themes
        True
        >>> 'dark' in themes
        True
        """
        return list(self.themes.keys())
