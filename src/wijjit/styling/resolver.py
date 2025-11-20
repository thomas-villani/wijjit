"""Style resolution system for applying themes to elements.

This module provides the StyleResolver class which handles CSS-like cascade
and pseudo-class resolution for element styling.
"""

from typing import TYPE_CHECKING, Any

from wijjit.styling.style import Style
from wijjit.styling.theme import Theme

if TYPE_CHECKING:
    from wijjit.elements.base import Element


class StyleResolver:
    """Resolves element styles using theme and element state.

    This class implements CSS-like style resolution with support for:
    - Base element styles from theme
    - Pseudo-class styles (:focus, :hover, :disabled, etc.)
    - Inline style overrides
    - Style cascade and merging

    Parameters
    ----------
    theme : Theme
        Theme to use for style resolution

    Attributes
    ----------
    theme : Theme
        Current theme

    Examples
    --------
    Basic style resolution:

    >>> from wijjit.styling.theme import DefaultTheme
    >>> resolver = StyleResolver(DefaultTheme())
    >>> style = resolver.resolve_style_by_class('button')
    >>> style.bg_color  # From theme
    (0, 100, 200)

    Resolve with pseudo-class:

    >>> style = resolver.resolve_style_by_class('button', pseudo_class='focus')
    >>> style.bold  # button:focus is bold
    True

    Resolve with inline overrides:

    >>> override = {'fg_color': (255, 255, 0)}
    >>> style = resolver.resolve_style_by_class(
    ...     'button', inline_overrides=override
    ... )
    >>> style.fg_color  # Overridden
    (255, 255, 0)
    """

    def __init__(self, theme: Theme) -> None:
        self.theme = theme

    def resolve_style(
        self,
        element: "Element",
        base_class: str | None = None,
        inline_overrides: dict[str, Any] | None = None,
    ) -> Style:
        """Resolve final style for an element.

        Parameters
        ----------
        element : Element
            Element to resolve style for
        base_class : str, optional
            Base element class (e.g., 'button'). If None, inferred from element type
        inline_overrides : dict, optional
            Dict of style properties to override (e.g., {'fg_color': (255, 0, 0)})

        Returns
        -------
        Style
            Resolved style with all cascades and overrides applied

        Notes
        -----
        Resolution order:
        1. Base class style from theme (e.g., 'button')
        2. Pseudo-class styles if element state matches:
           - :focus if element.focused is True
           - :hover if element.hovered is True
           - :disabled if element has disabled=True attribute
        3. Inline overrides from parameters

        Each layer is merged on top of the previous using Style.merge().

        Examples
        --------
        Basic resolution:

        >>> from wijjit.elements.input.button import Button
        >>> from wijjit.styling.theme import DefaultTheme
        >>> resolver = StyleResolver(DefaultTheme())
        >>> button = Button('Click me')
        >>> style = resolver.resolve_style(button, 'button')

        With focus:

        >>> button.focused = True
        >>> style = resolver.resolve_style(button, 'button')
        >>> style.bold  # button:focus is bold
        True

        With override:

        >>> style = resolver.resolve_style(
        ...     button, 'button',
        ...     inline_overrides={'fg_color': (255, 255, 0)}
        ... )
        >>> style.fg_color
        (255, 255, 0)
        """
        # Get class names to apply
        if base_class is not None:
            # Explicit base_class provided, use it
            class_names = [base_class]
        elif hasattr(element, "get_style_classes"):
            # Element provides its own class names
            class_names = element.get_style_classes()
            if not class_names:
                # Empty list means use automatic inference
                class_names = [self._infer_class_from_element(element)]
        else:
            # Fall back to automatic inference
            class_names = [self._infer_class_from_element(element)]

        # Merge base styles from all classes in order
        style = Style()
        for class_name in class_names:
            class_style = self.theme.get_style(class_name)
            if class_style:
                style = style.merge(class_style)

        # Apply pseudo-class styles based on element state
        # Use the last class name (most specific) for pseudo-classes
        primary_class = class_names[-1] if class_names else ""

        if hasattr(element, "focused") and element.focused:
            focus_style = self.theme.get_style(f"{primary_class}:focus")
            if focus_style:
                style = style.merge(focus_style)

        if hasattr(element, "hovered") and element.hovered:
            hover_style = self.theme.get_style(f"{primary_class}:hover")
            if hover_style:
                style = style.merge(hover_style)

        if hasattr(element, "disabled") and element.disabled:
            disabled_style = self.theme.get_style(f"{primary_class}:disabled")
            if disabled_style:
                style = style.merge(disabled_style)

        # Additional state-specific pseudo-classes
        if hasattr(element, "checked") and element.checked:
            checked_style = self.theme.get_style(f"{primary_class}:checked")
            if checked_style:
                style = style.merge(checked_style)

        if hasattr(element, "selected") and element.selected:
            selected_style = self.theme.get_style(f"{primary_class}:selected")
            if selected_style:
                style = style.merge(selected_style)

        # Apply inline overrides
        if inline_overrides:
            override_style = Style(**inline_overrides)
            style = style.merge(override_style)

        return style

    def resolve_style_by_class(
        self,
        class_name: str,
        pseudo_class: str | None = None,
        inline_overrides: dict[str, Any] | None = None,
    ) -> Style:
        """Resolve style by class name without an element instance.

        Parameters
        ----------
        class_name : str
            Element class name (e.g., 'button', 'input')
        pseudo_class : str, optional
            Pseudo-class to apply (e.g., 'focus', 'hover')
        inline_overrides : dict, optional
            Dict of style properties to override

        Returns
        -------
        Style
            Resolved style

        Notes
        -----
        This is a simpler version of resolve_style() that doesn't require an
        element instance. Useful for manual style resolution or testing.

        Examples
        --------
        Resolve button style:

        >>> from wijjit.styling.theme import DefaultTheme
        >>> resolver = StyleResolver(DefaultTheme())
        >>> style = resolver.resolve_style_by_class('button')
        >>> style.bg_color
        (0, 100, 200)

        With pseudo-class:

        >>> style = resolver.resolve_style_by_class('button', pseudo_class='focus')
        >>> style.bold
        True

        With override:

        >>> style = resolver.resolve_style_by_class(
        ...     'button',
        ...     inline_overrides={'fg_color': (255, 0, 0)}
        ... )
        >>> style.fg_color
        (255, 0, 0)
        """
        # Get base style
        style = self.theme.get_style(class_name)

        # Apply pseudo-class if specified
        if pseudo_class:
            pseudo_style = self.theme.get_style(f"{class_name}:{pseudo_class}")
            if pseudo_style:
                style = style.merge(pseudo_style)

        # Apply inline overrides
        if inline_overrides:
            override_style = Style(**inline_overrides)
            style = style.merge(override_style)

        return style

    def _infer_class_from_element(self, element: "Element") -> str:
        """Infer CSS class name from element type.

        Parameters
        ----------
        element : Element
            Element to infer class from

        Returns
        -------
        str
            Inferred class name

        Notes
        -----
        Maps element types to class names. Defaults to lowercase class name.

        Examples
        --------
        >>> from wijjit.elements.input.button import Button
        >>> resolver = StyleResolver(DefaultTheme())
        >>> button = Button('Test')
        >>> resolver._infer_class_from_element(button)
        'button'
        """
        # Get class name
        class_name = element.__class__.__name__.lower()

        # Map some common element types
        type_map = {
            "textinput": "input",
            "textarea": "input",
            "textelement": "text",
            "checkbox": "checkbox",
            "radiobutton": "radio",
            "button": "button",
            "frame": "frame",
            "table": "table",
            "tree": "tree",
            "listview": "list",
            "statusbar": "statusbar",
            "modal": "modal",
            "notification": "notification",
        }

        return type_map.get(class_name, class_name)

    def set_theme(self, theme: Theme) -> None:
        """Change the theme used for resolution.

        Parameters
        ----------
        theme : Theme
            New theme to use

        Notes
        -----
        This allows runtime theme switching. After calling this method,
        subsequent style resolutions will use the new theme.

        Examples
        --------
        >>> from wijjit.styling.theme import DefaultTheme, DarkTheme
        >>> resolver = StyleResolver(DefaultTheme())
        >>> resolver.set_theme(DarkTheme())
        >>> resolver.theme.name
        'dark'
        """
        self.theme = theme

    def get_theme(self) -> Theme:
        """Get the current theme.

        Returns
        -------
        Theme
            Current theme

        Examples
        --------
        >>> from wijjit.styling.theme import DefaultTheme
        >>> resolver = StyleResolver(DefaultTheme())
        >>> theme = resolver.get_theme()
        >>> theme.name
        'default'
        """
        return self.theme
