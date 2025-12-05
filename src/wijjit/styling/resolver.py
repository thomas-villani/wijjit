"""Style resolution system for applying themes to elements.

This module provides the StyleResolver class which handles CSS-like cascade
and pseudo-class resolution for element styling.
"""

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from wijjit.styling.style import Style
from wijjit.styling.theme import Theme

if TYPE_CHECKING:
    from wijjit.elements.base import Element


def _get_element_classes(element: "Element") -> list[str]:
    """Safely extract CSS classes from an element.

    Parameters
    ----------
    element : Element
        Element to extract classes from

    Returns
    -------
    list of str
        List of class names, empty list if classes is None or invalid
    """
    if not hasattr(element, "classes") or element.classes is None:
        return []

    classes = element.classes

    # Handle string (split by whitespace)
    if isinstance(classes, str):
        return classes.split()

    # Handle iterable (but not string since we handled that above)
    if isinstance(classes, Iterable):
        try:
            return [str(c) for c in classes]
        except (TypeError, ValueError):
            return []

    return []


class StyleResolver:
    """Resolves element styles using theme and element state.

    This class implements CSS-like style resolution with support for:
    - Base element styles from theme
    - Pseudo-class styles (:focus, :hover, :disabled, etc.)
    - Inline style overrides
    - Style cascade and merging
    - Style caching for performance optimization

    Parameters
    ----------
    theme : Theme
        Theme to use for style resolution

    Attributes
    ----------
    theme : Theme
        Current theme
    _style_cache : dict
        Cache of resolved styles keyed by (base_class, css_classes_key, state_key)

    Notes
    -----
    Style resolution is cached based on element type, CSS classes, and state.
    The cache is automatically cleared when the theme is changed.
    Inline overrides bypass the cache since they are unique per call.

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
        # Cache for resolved styles: (base_class, css_classes_key, state_key) -> Style
        self._style_cache: dict[tuple, Style] = {}

    def resolve_style(
        self,
        element: "Element",
        base_class: str | None = None,
        inline_overrides: dict[str, Any] | None = None,
    ) -> Style:
        """Resolve final style for an element with CSS class support.

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
        Resolution order (lowest to highest specificity):
        1. Base element type style (inferred from element type)
        2. User CSS classes (from element.classes, e.g., .btn-primary)
        3. Base element pseudo-classes (e.g., button:focus)
        4. CSS class pseudo-classes (e.g., .btn-primary:focus)
        5. Inline overrides

        Each layer is merged on top of the previous using Style.merge().

        Examples
        --------
        Basic resolution:

        >>> from wijjit.elements.input.button import Button
        >>> from wijjit.styling.theme import DefaultTheme
        >>> resolver = StyleResolver(DefaultTheme())
        >>> button = Button('Click me')
        >>> style = resolver.resolve_style(button)

        With CSS classes:

        >>> button = Button('Click me', classes="btn-primary")
        >>> style = resolver.resolve_style(button)
        >>> # Applies both 'button' and '.btn-primary' styles

        With focus:

        >>> button.focused = True
        >>> style = resolver.resolve_style(button)
        >>> # Applies button:focus and .btn-primary:focus

        With override:

        >>> style = resolver.resolve_style(
        ...     button,
        ...     inline_overrides={'fg_color': (255, 255, 0)}
        ... )
        >>> style.fg_color
        (255, 255, 0)
        """
        # Get base element type (for structural styling)
        if base_class is not None:
            # Explicit base_class provided (backward compatibility)
            base_element_type = base_class
        else:
            # Infer from element type
            base_element_type = self._infer_class_from_element(element)

        # Build cache key from element type, CSS classes, and state
        # Skip caching if inline_overrides provided (too dynamic)
        cache_key = None
        element_classes = _get_element_classes(element)
        if not inline_overrides:
            # Build CSS classes key
            css_classes_key: frozenset[str] | None = None
            if element_classes:
                css_classes_key = frozenset(element_classes)

            # Build state key from element pseudo-class state
            state_key = (
                getattr(element, "focused", False),
                getattr(element, "hovered", False),
                getattr(element, "disabled", False),
                getattr(element, "checked", False),
                getattr(element, "selected", False),
            )

            cache_key = (base_element_type, css_classes_key, state_key)

            # Check cache first
            if cache_key in self._style_cache:
                return self._style_cache[cache_key]

        # Cache miss or inline overrides - compute style
        # Start with base element type style
        style = Style()
        base_style = self.theme.get_style(base_element_type)
        if base_style:
            style = style.merge(base_style)

        # Apply user CSS classes (higher specificity than base type)
        if element_classes:
            for class_name in sorted(element_classes):  # Sort for consistency
                # Add dot prefix for CSS utility classes
                css_style = self.theme.get_style(f".{class_name}")
                if css_style:
                    style = style.merge(css_style)

        # Apply pseudo-classes to base element type
        style = self._apply_pseudo_classes(style, element, base_element_type)

        # Apply pseudo-classes to CSS classes
        if element_classes:
            for class_name in sorted(element_classes):
                style = self._apply_pseudo_classes(style, element, f".{class_name}")

        # Cache the computed style (without inline overrides)
        if cache_key is not None:
            self._style_cache[cache_key] = style

        # Apply inline overrides (highest specificity, not cached)
        if inline_overrides:
            override_style = Style(**inline_overrides)
            style = style.merge(override_style)

        return style

    def _apply_pseudo_classes(
        self, style: Style, element: "Element", selector: str
    ) -> Style:
        """Apply pseudo-class styles for a selector.

        Parameters
        ----------
        style : Style
            Current style to merge pseudo-class styles into
        element : Element
            Element to check state from
        selector : str
            Base selector (e.g., 'button', '.btn-primary')

        Returns
        -------
        Style
            Style with pseudo-class styles merged

        Notes
        -----
        Checks element state and applies corresponding pseudo-class styles:
        - :focus if element.focused is True
        - :hover if element.hovered is True
        - :disabled if element.disabled is True
        - :checked if element.checked is True
        - :selected if element.selected is True
        """
        # Focus state
        if hasattr(element, "focused") and element.focused:
            focus_style = self.theme.get_style(f"{selector}:focus")
            if focus_style:
                style = style.merge(focus_style)

        # Hover state
        if hasattr(element, "hovered") and element.hovered:
            hover_style = self.theme.get_style(f"{selector}:hover")
            if hover_style:
                style = style.merge(hover_style)

        # Disabled state
        if hasattr(element, "disabled") and element.disabled:
            disabled_style = self.theme.get_style(f"{selector}:disabled")
            if disabled_style:
                style = style.merge(disabled_style)

        # Checked state (checkboxes, radio buttons)
        if hasattr(element, "checked") and element.checked:
            checked_style = self.theme.get_style(f"{selector}:checked")
            if checked_style:
                style = style.merge(checked_style)

        # Selected state (list items, table rows)
        if hasattr(element, "selected") and element.selected:
            selected_style = self.theme.get_style(f"{selector}:selected")
            if selected_style:
                style = style.merge(selected_style)

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
        The style cache is automatically cleared when the theme changes.

        Examples
        --------
        >>> from wijjit.styling.theme import DefaultTheme, DarkTheme
        >>> resolver = StyleResolver(DefaultTheme())
        >>> resolver.set_theme(DarkTheme())
        >>> resolver.theme.name
        'dark'
        """
        self.theme = theme
        # Clear style cache since theme changed
        self._style_cache.clear()

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

    def clear_cache(self) -> None:
        """Clear the style resolution cache.

        Notes
        -----
        This method clears all cached style resolutions. Useful for testing
        or when element states have changed significantly and you want to
        ensure fresh style computation.

        The cache is also automatically cleared when set_theme() is called.
        """
        self._style_cache.clear()
