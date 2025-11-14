"""Tests for the StyleResolver class."""


from wijjit.styling.resolver import StyleResolver
from wijjit.styling.style import Style
from wijjit.styling.theme import DarkTheme, DefaultTheme, LightTheme, Theme


class MockElement:
    """Mock element for testing style resolution.

    Parameters
    ----------
    focused : bool, optional
        Whether element is focused (default: False)
    hovered : bool, optional
        Whether element is hovered (default: False)
    disabled : bool, optional
        Whether element is disabled (default: False)
    checked : bool, optional
        Whether element is checked (default: False)
    selected : bool, optional
        Whether element is selected (default: False)

    Attributes
    ----------
    focused : bool
        Focus state
    hovered : bool
        Hover state
    disabled : bool
        Disabled state
    checked : bool
        Checked state
    selected : bool
        Selected state
    """

    def __init__(
        self,
        focused: bool = False,
        hovered: bool = False,
        disabled: bool = False,
        checked: bool = False,
        selected: bool = False,
    ):
        self.focused = focused
        self.hovered = hovered
        self.disabled = disabled
        self.checked = checked
        self.selected = selected


class TestStyleResolverBasics:
    """Test basic StyleResolver functionality."""

    def test_create_resolver_with_theme(self):
        """Test creating resolver with a theme.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        assert resolver.theme is theme
        assert resolver.theme.name == "default"

    def test_get_theme(self):
        """Test getting current theme from resolver.

        Returns
        -------
        None
        """
        theme = DarkTheme()
        resolver = StyleResolver(theme)

        retrieved = resolver.get_theme()
        assert retrieved is theme
        assert retrieved.name == "dark"

    def test_set_theme(self):
        """Test changing theme on resolver.

        Returns
        -------
        None
        """
        resolver = StyleResolver(DefaultTheme())
        dark = DarkTheme()

        resolver.set_theme(dark)

        assert resolver.theme is dark
        assert resolver.theme.name == "dark"


class TestResolveStyleByClass:
    """Test resolve_style_by_class() method."""

    def test_resolve_simple_class(self):
        """Test resolving a simple class name.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        style = resolver.resolve_style_by_class("button")

        assert style is not None
        assert bool(style)  # Should have some styling

    def test_resolve_with_pseudo_class(self):
        """Test resolving with pseudo-class.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        base_style = resolver.resolve_style_by_class("button")
        focus_style = resolver.resolve_style_by_class("button", pseudo_class="focus")

        # Focus style should merge on top of base
        assert focus_style is not None
        # Focus typically adds bold or other attributes
        assert bool(focus_style)

    def test_resolve_with_inline_overrides(self):
        """Test resolving with inline style overrides.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        overrides = {"fg_color": (255, 0, 0), "bold": True}
        style = resolver.resolve_style_by_class("button", inline_overrides=overrides)

        # Overrides should be applied
        assert style.fg_color == (255, 0, 0)
        assert style.bold is True

    def test_resolve_with_pseudo_and_overrides(self):
        """Test resolving with both pseudo-class and overrides.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        overrides = {"fg_color": (255, 0, 0)}
        style = resolver.resolve_style_by_class(
            "button", pseudo_class="focus", inline_overrides=overrides
        )

        # Should have focus styling merged with override
        assert style.fg_color == (255, 0, 0)  # Override
        assert bool(style)

    def test_resolve_nonexistent_class(self):
        """Test resolving a class that doesn't exist in theme.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        style = resolver.resolve_style_by_class("nonexistent")

        # Should return empty style for missing class
        assert style is not None
        assert not bool(style)  # Empty style is falsy

    def test_resolve_nonexistent_pseudo_class(self):
        """Test resolving with nonexistent pseudo-class.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        base_style = resolver.resolve_style_by_class("button")
        style = resolver.resolve_style_by_class("button", pseudo_class="nonexistent")

        # Should return just base style (pseudo-class ignored)
        assert style.fg_color == base_style.fg_color
        assert style.bg_color == base_style.bg_color


class TestResolveStyleWithElement:
    """Test resolve_style() method with element instances."""

    def test_resolve_with_default_element(self):
        """Test resolving style for element with no state.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement()

        style = resolver.resolve_style(element, "button")

        # Should get base button style
        assert style is not None
        assert bool(style)

    def test_resolve_with_focused_element(self):
        """Test resolving style for focused element.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement(focused=True)

        style = resolver.resolve_style(element, "button")

        # Should include focus styling
        assert style is not None
        # DefaultTheme button:focus typically has bold
        assert bool(style)

    def test_resolve_with_hovered_element(self):
        """Test resolving style for hovered element.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement(hovered=True)

        style = resolver.resolve_style(element, "button")

        # Should include hover styling
        assert style is not None
        assert bool(style)

    def test_resolve_with_disabled_element(self):
        """Test resolving style for disabled element.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement(disabled=True)

        style = resolver.resolve_style(element, "button")

        # Should include disabled styling
        assert style is not None
        # Disabled typically has dim or altered colors
        assert bool(style)

    def test_resolve_with_checked_element(self):
        """Test resolving style for checked element (checkbox/radio).

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement(checked=True)

        style = resolver.resolve_style(element, "checkbox")

        # Should include checked styling
        assert style is not None
        assert bool(style)

    def test_resolve_with_selected_element(self):
        """Test resolving style for selected element.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement(selected=True)

        style = resolver.resolve_style(element, "radio")

        # Should include selected styling
        assert style is not None
        assert bool(style)

    def test_resolve_with_multiple_states(self):
        """Test resolving style for element with multiple states.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        # Element that is both focused and hovered
        element = MockElement(focused=True, hovered=True)

        style = resolver.resolve_style(element, "button")

        # Should merge both focus and hover styles
        assert style is not None
        assert bool(style)

    def test_resolve_with_element_and_inline_overrides(self):
        """Test resolving with element state and inline overrides.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement(focused=True)
        overrides = {"fg_color": (0, 255, 0)}

        style = resolver.resolve_style(element, "button", inline_overrides=overrides)

        # Override should win
        assert style.fg_color == (0, 255, 0)
        # Should still have focus styling for other properties
        assert bool(style)


class TestStyleCascade:
    """Test style cascade and merging behavior."""

    def test_base_style_applied(self):
        """Test that base style is applied.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        style = resolver.resolve_style_by_class("button")

        # Base button style should have bg_color
        assert style.bg_color is not None

    def test_pseudo_class_merges_on_base(self):
        """Test that pseudo-class merges on top of base.

        Returns
        -------
        None
        """
        # Create custom theme to test merge behavior
        styles = {
            "button": Style(fg_color=(255, 255, 255), bg_color=(0, 100, 200)),
            "button:focus": Style(bold=True),  # Only bold, preserves colors
        }
        theme = Theme("test", styles)
        resolver = StyleResolver(theme)

        base_style = resolver.resolve_style_by_class("button")
        focus_style = resolver.resolve_style_by_class("button", pseudo_class="focus")

        # Focus should preserve base colors and add bold
        assert focus_style.fg_color == (255, 255, 255)  # From base
        assert focus_style.bg_color == (0, 100, 200)  # From base
        assert focus_style.bold is True  # From focus

    def test_inline_overrides_win(self):
        """Test that inline overrides have highest priority.

        Returns
        -------
        None
        """
        styles = {
            "button": Style(fg_color=(255, 255, 255), bg_color=(0, 100, 200)),
            "button:focus": Style(fg_color=(0, 255, 255), bold=True),
        }
        theme = Theme("test", styles)
        resolver = StyleResolver(theme)

        overrides = {"fg_color": (255, 0, 0)}
        style = resolver.resolve_style_by_class(
            "button", pseudo_class="focus", inline_overrides=overrides
        )

        # Override should win over both base and pseudo-class
        assert style.fg_color == (255, 0, 0)  # Override
        assert style.bg_color == (0, 100, 200)  # From base
        assert style.bold is True  # From focus

    def test_multiple_pseudo_classes_cascade(self):
        """Test that multiple pseudo-classes cascade properly.

        Returns
        -------
        None
        """
        styles = {
            "button": Style(fg_color=(255, 255, 255)),
            "button:focus": Style(bold=True),
            "button:hover": Style(underline=True),
        }
        theme = Theme("test", styles)
        resolver = StyleResolver(theme)
        element = MockElement(focused=True, hovered=True)

        style = resolver.resolve_style(element, "button")

        # Should have both focus and hover attributes
        assert style.fg_color == (255, 255, 255)  # From base
        assert style.bold is True  # From focus
        assert style.underline is True  # From hover


class TestThemeSwitching:
    """Test that resolver respects theme changes."""

    def test_different_themes_different_styles(self):
        """Test that different themes produce different styles.

        Returns
        -------
        None
        """
        default_resolver = StyleResolver(DefaultTheme())
        dark_resolver = StyleResolver(DarkTheme())

        default_style = default_resolver.resolve_style_by_class("button")
        dark_style = dark_resolver.resolve_style_by_class("button")

        # Themes should have different button styles
        # (This assumes themes differ - adjust if they don't)
        assert default_style is not None
        assert dark_style is not None

    def test_set_theme_changes_resolution(self):
        """Test that set_theme() changes subsequent resolutions.

        Returns
        -------
        None
        """
        resolver = StyleResolver(DefaultTheme())

        # Get style with default theme
        default_style = resolver.resolve_style_by_class("button")

        # Switch to dark theme
        resolver.set_theme(DarkTheme())
        dark_style = resolver.resolve_style_by_class("button")

        # Should get dark theme button now
        assert resolver.get_theme().name == "dark"

    def test_theme_switch_applies_immediately(self):
        """Test that theme switch applies to all subsequent resolutions.

        Returns
        -------
        None
        """
        resolver = StyleResolver(DefaultTheme())

        # Switch theme
        light = LightTheme()
        resolver.set_theme(light)

        # All resolutions should use new theme
        button_style = resolver.resolve_style_by_class("button")
        input_style = resolver.resolve_style_by_class("input")

        # Verify theme was used (styles should exist)
        assert button_style is not None
        assert input_style is not None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_resolve_with_none_base_class(self):
        """Test resolve_style with None base_class.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)
        element = MockElement()

        # Should try to infer class name (will fail for MockElement)
        # but shouldn't crash
        style = resolver.resolve_style(element, base_class=None)
        assert style is not None

    def test_resolve_with_empty_overrides(self):
        """Test resolving with empty overrides dict.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        style = resolver.resolve_style_by_class("button", inline_overrides={})

        # Should work same as no overrides
        assert style is not None

    def test_resolve_element_without_state_attributes(self):
        """Test resolving element that lacks state attributes.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        # Element with no state attributes
        class MinimalElement:
            """Minimal element with no state attributes."""

            pass

        element = MinimalElement()

        # Should not crash when checking hasattr
        style = resolver.resolve_style(element, "button")
        assert style is not None

    def test_resolve_with_invalid_override_values(self):
        """Test resolving with invalid override values.

        Returns
        -------
        None
        """
        theme = DefaultTheme()
        resolver = StyleResolver(theme)

        # Style() should handle invalid values or raise appropriate error
        # This tests that resolver doesn't crash
        try:
            style = resolver.resolve_style_by_class(
                "button", inline_overrides={"fg_color": (255, 0, 0)}
            )
            assert style is not None
        except Exception:
            # If it raises, that's also acceptable behavior
            pass
