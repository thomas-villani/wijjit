"""Status indicator element for displaying status with colored indicator.

This module provides the StatusIndicator element for displaying a colored
circle/dot indicator with an optional label. Supports preset statuses
(error, warning, success, etc.) and custom user-defined statuses.
"""

from typing import TYPE_CHECKING

from wijjit.elements.base import Element, ElementType
from wijjit.terminal.ansi import supports_unicode

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


# Default status presets: status_name -> (color_name, indicator_char_override)
# If indicator_char_override is None, use the indicator_style setting
DEFAULT_STATUSES: dict[str, tuple[str, str | None]] = {
    "error": ("red", None),
    "warning": ("yellow", None),
    "success": ("green", None),
    "disabled": ("gray", None),
    "info": ("blue", None),
    "pending": ("cyan", None),
    "active": ("bright_green", None),
    "inactive": ("dim", None),
}

# Unicode indicator characters
INDICATOR_FILLED = "\u25cf"  # Black circle (filled)
INDICATOR_HOLLOW = "\u25cb"  # White circle (hollow)
INDICATOR_SQUARE = "\u25a0"  # Black square
INDICATOR_ASCII = "*"  # ASCII fallback


class StatusIndicator(Element):
    """Status indicator element displaying colored dot with label.

    A status indicator shows a colored circle/dot with an optional label
    to represent various states like success, error, warning, etc.
    Supports preset statuses and custom user-defined statuses.

    Parameters
    ----------
    id : str, optional
        Element identifier
    status : str, optional
        Status name matching preset or custom status (default: "info")
    label : str, optional
        Optional label displayed after indicator
    custom_statuses : dict, optional
        Custom status definitions mapping name to color string
        or (color, indicator_char) tuple
    indicator_style : {"filled", "hollow", "square", "ascii"}, optional
        Indicator character style (default: "filled")

    Attributes
    ----------
    status : str
        Current status name
    label : str or None
        Label text
    indicator_style : str
        Indicator visual style

    Notes
    -----
    This is a display-only element and is not focusable.

    Default statuses:
    - error: red
    - warning: yellow
    - success: green
    - disabled: gray
    - info: blue
    - pending: cyan
    - active: bright_green
    - inactive: dim

    Custom statuses can be registered via:
    - Constructor: custom_statuses={"custom": "magenta"}
    - Runtime: indicator.register_status("custom", "magenta")
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        status: str = "info",
        label: str | None = None,
        custom_statuses: dict[str, str | tuple[str, str]] | None = None,
        indicator_style: str = "filled",
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False  # Display-only element

        self._status = status
        self.label = label
        self.indicator_style = indicator_style

        # Build status registry from defaults + custom
        self._statuses: dict[str, tuple[str, str | None]] = dict(DEFAULT_STATUSES)
        if custom_statuses:
            for name, value in custom_statuses.items():
                if isinstance(value, str):
                    # Just color, use default indicator
                    self._statuses[name] = (value, None)
                else:
                    # (color, indicator) tuple
                    self._statuses[name] = value

    @property
    def status(self) -> str:
        """Get current status.

        Returns
        -------
        str
            Current status name
        """
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        """Set status.

        Parameters
        ----------
        value : str
            Status name to set
        """
        self._status = value

    def register_status(
        self, name: str, color: str, indicator: str | None = None
    ) -> None:
        """Register a custom status at runtime.

        Parameters
        ----------
        name : str
            Status name to register
        color : str
            Color for the indicator (e.g., "red", "bright_blue", "magenta")
        indicator : str, optional
            Custom indicator character (defaults to indicator_style setting)
        """
        self._statuses[name] = (color, indicator)

    def _get_indicator_char(self, use_unicode: bool) -> str:
        """Get indicator character based on style and unicode support.

        Parameters
        ----------
        use_unicode : bool
            Whether unicode is supported

        Returns
        -------
        str
            Indicator character
        """
        if not use_unicode or self.indicator_style == "ascii":
            return INDICATOR_ASCII

        if self.indicator_style == "hollow":
            return INDICATOR_HOLLOW
        elif self.indicator_style == "square":
            return INDICATOR_SQUARE
        else:  # "filled" or default
            return INDICATOR_FILLED

    def render_to(self, ctx: "PaintContext") -> None:
        """Render status indicator to paint context.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'status_indicator': Base indicator style
        - 'status_indicator.{status}': Status-specific style (e.g., status_indicator.error)
        - 'status_indicator.label': Label text style
        """
        # Look up status definition
        status_def = self._statuses.get(self._status)
        if status_def:
            color, custom_char = status_def
        else:
            # Unknown status - use gray as fallback
            color = "gray"
            custom_char = None

        # Determine indicator character
        use_unicode = supports_unicode()
        if custom_char:
            # Custom character specified in status def
            indicator = custom_char
        else:
            indicator = self._get_indicator_char(use_unicode)

        # Resolve styles
        # Try status-specific style first, fall back to base
        indicator_style = ctx.style_resolver.resolve_style(
            self, f"status_indicator.{self._status}"
        )
        # If no specific style, use base with color override
        if not indicator_style.fg_color:
            indicator_style = ctx.style_resolver.resolve_style(self, "status_indicator")

        label_style = ctx.style_resolver.resolve_style(self, "status_indicator.label")

        x_offset = 0

        # Render indicator with color
        # Apply color from status definition
        from wijjit.styling.style import Style

        colored_style = Style(
            fg_color=self._color_name_to_rgb(color),
            bold=indicator_style.bold,
        )
        ctx.write_text(x_offset, 0, indicator, colored_style)
        x_offset += 1

        # Render label if present
        if self.label:
            ctx.write_text(x_offset, 0, f" {self.label}", label_style)

    def _color_name_to_rgb(self, color_name: str) -> tuple[int, int, int] | None:
        """Convert color name to RGB tuple.

        Parameters
        ----------
        color_name : str
            Color name like "red", "green", "bright_blue"

        Returns
        -------
        tuple[int, int, int] or None
            RGB color tuple or None if unknown
        """
        # Basic color map
        colors = {
            "black": (0, 0, 0),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "yellow": (255, 255, 0),
            "blue": (0, 0, 255),
            "magenta": (255, 0, 255),
            "cyan": (0, 255, 255),
            "white": (255, 255, 255),
            "gray": (128, 128, 128),
            "grey": (128, 128, 128),
            "dim": (96, 96, 96),
            # Bright variants
            "bright_red": (255, 100, 100),
            "bright_green": (100, 255, 100),
            "bright_yellow": (255, 255, 100),
            "bright_blue": (100, 100, 255),
            "bright_magenta": (255, 100, 255),
            "bright_cyan": (100, 255, 255),
            "bright_white": (255, 255, 255),
            # Semantic colors
            "orange": (255, 165, 0),
            "purple": (128, 0, 128),
            "pink": (255, 192, 203),
            "brown": (139, 69, 19),
        }

        return colors.get(color_name.lower())

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the status indicator.

        Returns
        -------
        tuple[int, int]
            (width, height) based on indicator and label
        """
        width = 1  # indicator
        if self.label:
            width += 1 + len(self.label)  # space + label

        return (width, 1)
