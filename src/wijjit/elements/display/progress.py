"""Progress bar element for displaying operation progress.

This module provides the ProgressBar element for displaying visual progress
indicators in terminal user interfaces. Supports multiple display styles
including filled bars, percentages, and gradients.
"""

from typing import Literal

from wijjit.elements.base import Element, ElementType
from wijjit.rendering.paint_context import PaintContext
from wijjit.terminal.ansi import clip_to_width

# Bar style presets: (unicode_fill, unicode_empty, ascii_fill, ascii_empty)
BAR_STYLES: dict[str, tuple[str, str, str, str]] = {
    # Default block style - solid blocks
    "block": ("\u2588", "\u2591", "#", "-"),
    # Thin horizontal line
    "thin": ("\u2500", "\u2508", "-", "."),
    # Thick/heavy horizontal line
    "thick": ("\u2501", "\u2509", "=", "-"),
    # Classic equals sign style
    "equals": ("=", " ", "=", " "),
    # Arrow/chevron style
    "arrow": (">", " ", ">", " "),
    # Dot style using middle dot
    "dots": ("\u2022", "\u00b7", "*", "."),
    # Pure ASCII style
    "ascii": ("#", "-", "#", "-"),
    # Hash/pound style
    "hash": ("#", " ", "#", " "),
    # Pipe style
    "pipe": ("|", " ", "|", " "),
    # Square brackets style
    "square": ("\u25a0", "\u25a1", "#", "-"),
}


class ProgressBar(Element):
    """Progress bar element for displaying progress of operations.

    This element provides a visual progress indicator with support for:
    - Multiple display styles (filled bar, percentage only, gradient, custom)
    - Multiple bar styles (block, thin, thick, equals, arrow, dots, ascii, etc.)
    - Optional coloring
    - Customizable fill and empty characters
    - Percentage display

    Parameters
    ----------
    id : str, optional
        Element identifier
    value : float, optional
        Current progress value (default: 0)
    max : float, optional
        Maximum progress value (default: 100)
    width : int, optional
        Display width in columns (default: 40)
    style : str, optional
        Display style: "filled", "percentage", "gradient", "custom" (default: "filled")
    bar_style : str, optional
        Visual bar style preset: "block", "thin", "thick", "equals", "arrow",
        "dots", "ascii", "hash", "pipe", "square" (default: "block").
        Sets default fill_char and empty_char values.
    color : str, optional
        Color name for the progress bar (default: None)
    show_percentage : bool, optional
        Whether to show percentage text (default: True for filled/gradient, False for percentage style)
    fill_char : str, optional
        Character for filled portion. Overrides bar_style if specified.
    empty_char : str, optional
        Character for empty portion. Overrides bar_style if specified.

    Attributes
    ----------
    value : float
        Current progress value
    max : float
        Maximum progress value
    width : int
        Display width
    style : str
        Display style
    bar_style : str
        Visual bar style preset
    color : str or None
        Color name
    show_percentage : bool
        Whether to show percentage
    fill_char : str
        Fill character
    empty_char : str
        Empty character
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        value: float = 0,
        max_value: float = 100,
        max: float | None = None,
        width: int = 40,
        style: Literal["filled", "percentage", "gradient", "custom"] = "filled",
        bar_style: Literal[
            "block",
            "thin",
            "thick",
            "equals",
            "arrow",
            "dots",
            "ascii",
            "hash",
            "pipe",
            "square",
        ] = "block",
        color: str | None = None,
        show_percentage: bool | None = None,
        fill_char: str | None = None,
        empty_char: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False  # Progress bars are not interactive

        # Progress properties
        self.value = float(value)
        # ``max`` is a deprecated alias for ``max_value``; honor it when given.
        self._max_value = float(max if max is not None else max_value)
        self.width = width
        self.style = style
        self.bar_style = bar_style
        self.color = color

        # Default show_percentage based on style
        if show_percentage is None:
            self.show_percentage = style in ("filled", "gradient", "custom")
        else:
            self.show_percentage = show_percentage

        # Get bar style preset characters
        from wijjit.terminal.ansi import supports_unicode

        preset = BAR_STYLES.get(bar_style, BAR_STYLES["block"])
        unicode_fill, unicode_empty, ascii_fill, ascii_empty = preset

        # Use bar_style preset, but allow fill_char/empty_char to override
        if supports_unicode():
            self.fill_char = fill_char if fill_char is not None else unicode_fill
            self.empty_char = empty_char if empty_char is not None else unicode_empty
        else:
            self.fill_char = fill_char if fill_char is not None else ascii_fill
            self.empty_char = empty_char if empty_char is not None else ascii_empty

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    @property
    def max_value(self) -> float:
        """Upper bound of the progress range."""
        return self._max_value

    @max_value.setter
    def max_value(self, value: float) -> None:
        self._max_value = float(value)

    @property
    def max(self) -> float:
        """Deprecated alias for :attr:`max_value`."""
        return self._max_value

    @max.setter
    def max(self, value: float) -> None:
        self._max_value = float(value)

    def set_progress(self, value: float) -> None:
        """Update progress value.

        Parameters
        ----------
        value : float
            New progress value
        """
        self.value = float(value)

    def get_percentage(self) -> float:
        """Get current progress as percentage.

        Returns
        -------
        float
            Progress percentage (0-100)
        """
        if self.max_value <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.value / self.max_value) * 100.0))

    def _get_color_for_percentage(self, percentage: float) -> str | None:
        """Get color based on percentage for gradient style.

        Parameters
        ----------
        percentage : float
            Current percentage (0-100)

        Returns
        -------
        str or None
            ANSI color code
        """
        from wijjit.terminal.ansi import ANSIColor

        if percentage < 33:
            return ANSIColor.RED
        elif percentage < 66:
            return ANSIColor.YELLOW
        else:
            return ANSIColor.GREEN

    def _render_filled_bar(self) -> str:
        """Render filled block style progress bar.

        Returns
        -------
        str
            Rendered progress bar
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        percentage = self.get_percentage()

        # Calculate percentage text first to know its exact width
        if self.show_percentage:
            percentage_text = f" {percentage:.1f}%"
            percentage_width = len(percentage_text)
            bar_width = self.width - percentage_width
        else:
            bar_width = self.width

        # Ensure minimum bar width
        bar_width = max(1, bar_width)

        # Calculate filled and empty portions
        filled_width = int((percentage / 100.0) * bar_width)
        empty_width = bar_width - filled_width

        # Build bar
        bar = self.fill_char * filled_width + self.empty_char * empty_width

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                bar = colorize(bar, color=color_code)

        # Add percentage text if enabled
        if self.show_percentage:
            return bar + percentage_text
        else:
            return bar

    def _render_percentage_only(self) -> str:
        """Render percentage-only style.

        Returns
        -------
        str
            Rendered percentage text
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        percentage = self.get_percentage()
        text = f"Progress: {percentage:5.1f}%"

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                text = colorize(text, color=color_code)

        # Pad to width
        if len(text) < self.width:
            text = text.ljust(self.width)
        else:
            text = clip_to_width(text, self.width)

        return text

    def _render_gradient_bar(self) -> str:
        """Render gradient color style progress bar.

        The color changes based on completion percentage:
        - 0-33%: Red
        - 33-66%: Yellow
        - 66-100%: Green

        Returns
        -------
        str
            Rendered progress bar with gradient color
        """
        from wijjit.terminal.ansi import colorize

        percentage = self.get_percentage()

        # Calculate percentage text first to know its exact width
        if self.show_percentage:
            percentage_text = f" {percentage:.1f}%"
            percentage_width = len(percentage_text)
            bar_width = self.width - percentage_width
        else:
            bar_width = self.width

        bar_width = max(1, bar_width)

        # Calculate filled and empty portions
        filled_width = int((percentage / 100.0) * bar_width)
        empty_width = bar_width - filled_width

        # Build bar
        bar = self.fill_char * filled_width + self.empty_char * empty_width

        # Apply gradient color
        gradient_color = self._get_color_for_percentage(percentage)
        if gradient_color:
            bar = colorize(bar, color=gradient_color)

        # Add percentage text
        if self.show_percentage:
            return bar + percentage_text
        else:
            return bar

    def _render_custom_bar(self) -> str:
        """Render custom character style progress bar.

        Uses user-specified fill_char and empty_char.

        Returns
        -------
        str
            Rendered progress bar
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        percentage = self.get_percentage()

        # Calculate percentage text first to know its exact width
        if self.show_percentage:
            percentage_text = f" {percentage:.1f}%"
            percentage_width = len(percentage_text)
            bar_width = self.width - percentage_width
        else:
            bar_width = self.width

        bar_width = max(1, bar_width)

        # Calculate filled and empty portions
        filled_width = int((percentage / 100.0) * bar_width)
        empty_width = bar_width - filled_width

        # Build bar with custom characters
        bar = self.fill_char * filled_width + self.empty_char * empty_width

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                bar = colorize(bar, color=color_code)

        # Add percentage text
        if self.show_percentage:
            return bar + percentage_text
        else:
            return bar

    def render_to(self, ctx: PaintContext) -> None:
        """Render the progress bar using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the new cell-based rendering method that uses theme styles
        instead of hardcoded ANSI colors. It supports all progress bar styles:
        filled, percentage, gradient, and custom.

        Theme styles:

        This element uses the following theme style classes:
        - ``progress``: Base progress bar style
        - ``progress.fill``: Filled portion style
        - ``progress.empty``: Empty portion style
        - ``progress.text``: Progress percentage text style
        - ``progress.gradient.low``: Gradient color for 0-33% (gradient style only)
        - ``progress.gradient.medium``: Gradient color for 33-66% (gradient style only)
        - ``progress.gradient.high``: Gradient color for 66-100% (gradient style only)
        """

        percentage = self.get_percentage()

        # Calculate dimensions
        if self.show_percentage and self.style != "percentage":
            percentage_text = f" {percentage:.1f}%"
            percentage_width = len(percentage_text)
            bar_width = max(1, ctx.bounds.width - percentage_width)
        else:
            bar_width = ctx.bounds.width

        # For percentage-only style
        if self.style == "percentage":
            text_style = ctx.style_resolver.resolve_style(self, "progress.text")
            text = f"Progress: {percentage:5.1f}%"
            # Pad or clip to width
            if len(text) < ctx.bounds.width:
                text = text.ljust(ctx.bounds.width)
            else:
                from wijjit.terminal.ansi import clip_to_width

                text = clip_to_width(text, ctx.bounds.width)
            ctx.write_text(0, 0, text, text_style)
            return

        # Calculate filled and empty portions
        filled_width = int((percentage / 100.0) * bar_width)
        empty_width = bar_width - filled_width

        # Determine styles based on style type
        if self.style == "gradient":
            # Gradient style - color changes with percentage
            if percentage < 33:
                fill_style = ctx.style_resolver.resolve_style(
                    self, "progress.gradient.low"
                )
            elif percentage < 66:
                fill_style = ctx.style_resolver.resolve_style(
                    self, "progress.gradient.medium"
                )
            else:
                fill_style = ctx.style_resolver.resolve_style(
                    self, "progress.gradient.high"
                )
        else:
            # Filled or custom style
            fill_style = ctx.style_resolver.resolve_style(self, "progress.fill")

        empty_style = ctx.style_resolver.resolve_style(self, "progress.empty")
        text_style = ctx.style_resolver.resolve_style(self, "progress.text")

        # Render filled portion
        if filled_width > 0:
            filled_bar = self.fill_char * filled_width
            ctx.write_text(0, 0, filled_bar, fill_style)

        # Render empty portion
        if empty_width > 0:
            empty_bar = self.empty_char * empty_width
            ctx.write_text(filled_width, 0, empty_bar, empty_style)

        # Render percentage text if enabled
        if self.show_percentage:
            ctx.write_text(bar_width, 0, percentage_text, text_style)
