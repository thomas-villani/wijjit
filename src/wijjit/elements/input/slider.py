"""Slider input element for numeric value selection.

This module provides the Slider element for creating a visual bar with
a draggable handle for selecting numeric values. Supports both integer
and float modes, keyboard navigation, and mouse drag interaction.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from wijjit.elements.base import Element, ElementType
from wijjit.terminal.ansi import supports_unicode
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class Slider(Element):
    """Slider input element for numeric value selection.

    A slider provides a visual bar with a draggable handle for selecting
    values within a range. Supports keyboard navigation (arrows, home/end)
    and mouse interaction (click to set, drag to adjust).

    Parameters
    ----------
    id : str, optional
        Element identifier for state binding
    min_val : float, optional
        Minimum value (default: 0)
    max_val : float, optional
        Maximum value (default: 100)
    value : float, optional
        Initial value (defaults to min_val)
    step : float, optional
        Step increment for keyboard navigation (default: 1)
    width : int, optional
        Visual width of slider track in characters (default: 20)
    float_mode : bool, optional
        If True, value property returns float; if False, returns int (default: False)
    label : str, optional
        Optional label displayed before slider
    show_value : bool, optional
        Display current value after slider (default: True)

    Attributes
    ----------
    min_val : float
        Minimum value
    max_val : float
        Maximum value
    step : float
        Step increment
    width : int
        Track width
    float_mode : bool
        Float mode flag
    label : str or None
        Label text
    show_value : bool
        Show value flag
    on_change : callable or None
        Callback (old_value, new_value) when value changes
    on_slide_start : callable or None
        Callback when drag operation begins
    on_slide_end : callable or None
        Callback when drag operation ends
    action : str or None
        Action ID to dispatch (set by template extension)
    bind : bool
        Whether to auto-bind to state[id] (default: True)

    Notes
    -----
    Keyboard controls:
    - Left/Right: Decrement/increment by step
    - Home/End: Jump to min/max value

    Mouse controls:
    - Click on track: Set value at clicked position
    - Drag handle: Smooth value adjustment
    """

    # Track characters for Unicode
    TRACK_CHAR = "\u2500"  # Horizontal line
    HANDLE_CHAR = "\u2588"  # Full block
    LEFT_CAP = "\u251c"  # Left T-junction
    RIGHT_CAP = "\u2524"  # Right T-junction

    # Track characters for ASCII fallback
    TRACK_CHAR_ASCII = "-"
    HANDLE_CHAR_ASCII = "#"
    LEFT_CAP_ASCII = "["
    RIGHT_CAP_ASCII = "]"

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        min_val: float = 0,
        max_val: float = 100,
        value: float | None = None,
        step: float = 1,
        width: int = 20,
        float_mode: bool = False,
        label: str | None = None,
        show_value: bool = True,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.INPUT
        self.focusable = True

        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self._value = float(value) if value is not None else self.min_val
        self.step = float(step)
        self.width = width
        self.float_mode = float_mode
        self.label = label
        self.show_value = show_value

        # Drag state
        self._dragging = False
        self._drag_start_x: int | None = None
        self._drag_start_value: float | None = None

        # Track position state (set during render for mouse hit testing)
        self._track_start_x: int = 0
        self._track_width: int = width

        # Callbacks
        self.on_change: Callable[[Any, Any], None] | None = None
        self.on_slide_start: Callable[[], None] | None = None
        self.on_slide_end: Callable[[], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    @property
    def value(self) -> float | int:
        """Get current value, cast to int if not float_mode.

        Returns
        -------
        float or int
            Current slider value
        """
        if self.float_mode:
            return self._value
        return int(round(self._value))

    @value.setter
    def value(self, new_value: float) -> None:
        """Set value, clamping to valid range.

        Parameters
        ----------
        new_value : float
            New value to set
        """
        clamped = max(self.min_val, min(self.max_val, float(new_value)))
        old_value = self.value
        self._value = clamped

        # Emit change if value actually changed
        new_val = self.value  # Get through property for type conversion
        if old_value != new_val and self.on_change:
            self.on_change(old_value, new_val)

    def _value_to_position(self, track_width: int) -> int:
        """Convert value to handle position on track.

        Parameters
        ----------
        track_width : int
            Width of the track in characters

        Returns
        -------
        int
            Position of handle (0 to track_width-1)
        """
        if self.max_val == self.min_val:
            return 0
        ratio = (self._value - self.min_val) / (self.max_val - self.min_val)
        return int(round(ratio * (track_width - 1)))

    def _position_to_value(self, pos: int, track_width: int) -> float:
        """Convert handle position to value.

        Parameters
        ----------
        pos : int
            Position on track
        track_width : int
            Width of the track

        Returns
        -------
        float
            Value corresponding to position
        """
        if track_width <= 1:
            return self.min_val
        # Clamp position to valid range
        pos = max(0, min(track_width - 1, pos))
        ratio = pos / (track_width - 1)
        return self.min_val + ratio * (self.max_val - self.min_val)

    def render_to(self, ctx: "PaintContext") -> None:
        """Render slider to paint context.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'slider': Base slider track style
        - 'slider:focus': Track style when focused
        - 'slider.handle': Handle style
        - 'slider.handle:focus': Handle style when focused
        - 'slider.label': Label text style
        - 'slider.value': Value text style
        """
        # Determine characters based on unicode support
        use_unicode = supports_unicode()
        track_char = self.TRACK_CHAR if use_unicode else self.TRACK_CHAR_ASCII
        handle_char = self.HANDLE_CHAR if use_unicode else self.HANDLE_CHAR_ASCII
        left_cap = self.LEFT_CAP if use_unicode else self.LEFT_CAP_ASCII
        right_cap = self.RIGHT_CAP if use_unicode else self.RIGHT_CAP_ASCII

        # Resolve styles
        from wijjit.styling.style import Style

        track_style = ctx.style_resolver.resolve_style(self, "slider")
        if self.focused:
            # Use explicit cyan color for handle when focused
            handle_style = Style(fg_color=(0, 255, 255), bold=True)  # Cyan
        else:
            handle_style = ctx.style_resolver.resolve_style(self, "slider.handle")

        label_style = ctx.style_resolver.resolve_style(self, "slider.label")
        value_style = ctx.style_resolver.resolve_style(self, "slider.value")

        x_offset = 0

        # Render label if present
        if self.label:
            label_text = f"{self.label} "
            ctx.write_text(x_offset, 0, label_text, label_style)
            x_offset += len(label_text)

        # Store track bounds for mouse hit testing
        self._track_start_x = x_offset + 1  # +1 for left cap
        self._track_width = self.width

        # Calculate handle position
        handle_pos = self._value_to_position(self.width)

        # Render left cap
        ctx.write_text(x_offset, 0, left_cap, track_style)
        x_offset += 1

        # Render track with handle
        for i in range(self.width):
            if i == handle_pos:
                ctx.write_text(x_offset + i, 0, handle_char, handle_style)
            else:
                ctx.write_text(x_offset + i, 0, track_char, track_style)

        x_offset += self.width

        # Render right cap
        ctx.write_text(x_offset, 0, right_cap, track_style)
        x_offset += 1

        # Render value if enabled
        if self.show_value:
            if self.float_mode:
                value_str = f" {self.value:.1f}"
            else:
                value_str = f" {self.value}"
            ctx.write_text(x_offset, 0, value_str, value_style)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the slider.

        Returns
        -------
        tuple[int, int]
            (width, height) based on track width, label, and value display
        """
        width = self.width + 2  # track + caps

        if self.label:
            width += len(self.label) + 1  # label + space

        if self.show_value:
            # Estimate value display width
            if self.float_mode:
                # Format: " 100.0" (space + up to 5 digits + decimal + 1 digit)
                width += 1 + len(f"{self.max_val:.1f}")
            else:
                # Format: " 100" (space + digits)
                width += 1 + len(str(int(self.max_val)))

        return (width, 1)

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        if key == Keys.LEFT:
            self.value = self._value - self.step
            return True
        elif key == Keys.RIGHT:
            self.value = self._value + self.step
            return True
        elif key == Keys.HOME:
            self.value = self.min_val
            return True
        elif key == Keys.END:
            self.value = self.max_val
            return True

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input for click and drag.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        if not self.bounds:
            return False

        # Calculate x position relative to track
        rel_x = event.x - self.bounds.x
        track_x = rel_x - self._track_start_x

        # Handle click - set value directly
        if event.type == MouseEventType.CLICK and event.button == MouseButton.LEFT:
            if 0 <= track_x < self._track_width:
                new_value = self._position_to_value(track_x, self._track_width)
                self.value = new_value
                return True

        # Handle press - start drag
        elif event.type == MouseEventType.PRESS and event.button == MouseButton.LEFT:
            if 0 <= track_x < self._track_width:
                self._dragging = True
                self._drag_start_x = event.x
                self._drag_start_value = self._value
                if self.on_slide_start:
                    self.on_slide_start()
                return True

        # Handle drag - update value
        elif event.type == MouseEventType.DRAG and self._dragging:
            if track_x < 0:
                self.value = self.min_val
            elif track_x >= self._track_width:
                self.value = self.max_val
            else:
                new_value = self._position_to_value(track_x, self._track_width)
                self.value = new_value
            return True

        # Handle move during drag
        elif event.type == MouseEventType.MOVE and self._dragging:
            if track_x < 0:
                self.value = self.min_val
            elif track_x >= self._track_width:
                self.value = self.max_val
            else:
                new_value = self._position_to_value(track_x, self._track_width)
                self.value = new_value
            return True

        # Handle release - end drag
        elif event.type == MouseEventType.RELEASE and event.button == MouseButton.LEFT:
            if self._dragging:
                self._dragging = False
                self._drag_start_x = None
                self._drag_start_value = None
                if self.on_slide_end:
                    self.on_slide_end()
                return True

        return False

    def get_ephemeral_state(self) -> dict[str, Any]:
        """Get ephemeral state for reconciliation.

        Returns
        -------
        dict
            State that should survive re-renders
        """
        return {
            "dragging": self._dragging,
        }

    def restore_ephemeral_state(self, state: dict[str, Any]) -> None:
        """Restore ephemeral state after reconciliation.

        Parameters
        ----------
        state : dict
            State from get_ephemeral_state()
        """
        if "dragging" in state:
            self._dragging = state["dragging"]
