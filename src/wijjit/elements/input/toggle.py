"""Toggle switch element for boolean input.

This module provides the Toggle element for creating visual switch controls
distinct from checkboxes. Supports single label mode (label after switch)
and dual label mode (labels on both sides showing On/Off states).
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from wijjit.elements.base import Element, ElementType, invoke_callback
from wijjit.terminal.ansi import supports_unicode
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


LabelMode = Literal["single", "dual"]


class Toggle(Element):
    """Toggle switch element for boolean values.

    A toggle switch provides a clear visual indicator for on/off states,
    distinct from a checkbox. Uses colored block characters to show state.
    Supports two label modes:
    - Single mode: Label displayed after the switch
    - Dual mode: Labels on both sides showing Off/On states

    Parameters
    ----------
    id : str, optional
        Element identifier for state binding
    checked : bool, optional
        Initial checked state (default: False)
    label : str, optional
        Label for single mode, displayed after switch
    on_label : str, optional
        Label shown for "on" state in dual mode (default: "ON")
    off_label : str, optional
        Label shown for "off" state in dual mode (default: "OFF")
    label_mode : {"single", "dual"}, optional
        Label display mode (default: "single")

    Attributes
    ----------
    checked : bool
        Current checked state
    label : str or None
        Label text (single mode)
    on_label : str
        On state label (dual mode)
    off_label : str
        Off state label (dual mode)
    label_mode : str
        Label display mode
    on_change : callable or None
        Callback (old_value, new_value) when state changes
    on_toggle : callable or None
        Callback when toggle is activated
    action : str or None
        Action ID to dispatch (set by template extension)
    bind : bool
        Whether to auto-bind to state[id] (default: True)

    Notes
    -----
    Keyboard controls:
    - Space/Enter: Toggle the switch

    Mouse controls:
    - Click: Toggle the switch

    Visual representation (Unicode):
    - Single mode (off): Gray track with knob on right + Label
    - Single mode (on):  Green track with knob on left + Label
    - Dual mode: OFF/ON labels on sides with colored switch

    Visual representation (ASCII):
    - Off: [  O] or OFF [  O] ON
    - On:  [O  ] or OFF [O  ] ON
    """

    # Unicode block characters
    TRACK_CHAR = "\u2591"  # Light shade block for track
    KNOB_CHAR = "\u2588"  # Full block for knob

    # ASCII fallback
    TRACK_CHAR_ASCII = "-"
    KNOB_CHAR_ASCII = "O"

    # Colors
    ON_COLOR = (0, 200, 0)  # Green when on
    OFF_COLOR = (100, 100, 100)  # Gray when off
    FOCUS_COLOR = (0, 255, 255)  # Cyan when focused

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        checked: bool = False,
        label: str | None = None,
        on_label: str = "ON",
        off_label: str = "OFF",
        label_mode: LabelMode = "single",
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.BUTTON  # Interactive like button
        self.focusable = True

        self._checked = checked
        self.label = label
        self.on_label = on_label
        self.off_label = off_label
        self.label_mode = label_mode

        # Callbacks
        self.on_change: Callable[[bool, bool], None] | None = None
        self.on_toggle: Callable[[], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    @property
    def checked(self) -> bool:
        """Get checked state.

        Returns
        -------
        bool
            Current checked state
        """
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        """Set checked state, triggering callbacks if changed.

        Parameters
        ----------
        value : bool
            New checked state
        """
        old_value = self._checked
        self._checked = value

        if old_value != value:
            if self.on_change:
                invoke_callback(self.on_change, old_value, value)

    def toggle(self) -> None:
        """Toggle the current state.

        Flips the checked state and triggers on_toggle callback.
        """
        self.checked = not self._checked
        if self.on_toggle:
            invoke_callback(self.on_toggle)

    def render_to(self, ctx: "PaintContext") -> None:
        """Render toggle switch to paint context.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Theme styles:

        This element uses the following theme style classes for colors:
        - ``toggle.on``: On state color (default: green)
        - ``toggle.off``: Off state color (default: gray)
        - ``toggle:focus``: Focused state color (default: cyan)
        - ``toggle.label``: Label text style
        - ``toggle.label.active``: Active label style (dual mode)
        - ``toggle.label.inactive``: Inactive label style (dual mode)

        Example CSS to customize colors::

            toggle.on { color: rgb(0, 255, 0); }
            toggle.off { color: rgb(255, 0, 0); }
        """
        from wijjit.styling.style import Style

        # Determine characters based on unicode support
        use_unicode = supports_unicode()
        if use_unicode:
            track_char = self.TRACK_CHAR
            knob_char = self.KNOB_CHAR
        else:
            track_char = self.TRACK_CHAR_ASCII
            knob_char = self.KNOB_CHAR_ASCII

        # Resolve colors from theme, fall back to defaults
        # Theme can define: toggle.on, toggle.off, toggle:focus
        on_style = ctx.style_resolver.resolve_style(self, "toggle.on")
        off_style = ctx.style_resolver.resolve_style(self, "toggle.off")
        focus_style = ctx.style_resolver.resolve_style(self, "toggle:focus")

        # Use theme colors if defined, otherwise use defaults
        on_color = on_style.fg_color if on_style.fg_color else self.ON_COLOR
        off_color = off_style.fg_color if off_style.fg_color else self.OFF_COLOR
        focus_color = focus_style.fg_color if focus_style.fg_color else self.FOCUS_COLOR

        # Determine colors based on state
        if self.focused:
            track_color = focus_color
            knob_color = (255, 255, 255)  # White knob when focused
        elif self._checked:
            track_color = on_color
            knob_color = (255, 255, 255)  # White knob
        else:
            track_color = off_color
            knob_color = (200, 200, 200)  # Light gray knob

        track_style = Style(fg_color=track_color)
        knob_style = Style(fg_color=knob_color, bold=True)

        label_style = ctx.style_resolver.resolve_style(self, "toggle.label")
        active_label_style = ctx.style_resolver.resolve_style(
            self, "toggle.label.active"
        )
        inactive_label_style = ctx.style_resolver.resolve_style(
            self, "toggle.label.inactive"
        )

        x_offset = 0

        if self.label_mode == "dual":
            # Dual mode: OFF [switch] ON
            # Off label
            off_text = f"{self.off_label} "
            if self._checked:
                ctx.write_text(x_offset, 0, off_text, inactive_label_style)
            else:
                ctx.write_text(x_offset, 0, off_text, active_label_style)
            x_offset += len(off_text)

            # Render switch: 4 chars total [knob + track or track + knob]
            if self._checked:
                # On: knob on left [O---]
                ctx.write_text(x_offset, 0, knob_char, knob_style)
                ctx.write_text(x_offset + 1, 0, track_char * 3, track_style)
            else:
                # Off: knob on right [---O]
                ctx.write_text(x_offset, 0, track_char * 3, track_style)
                ctx.write_text(x_offset + 3, 0, knob_char, knob_style)
            x_offset += 4

            # On label
            on_text = f" {self.on_label}"
            if self._checked:
                ctx.write_text(x_offset, 0, on_text, active_label_style)
            else:
                ctx.write_text(x_offset, 0, on_text, inactive_label_style)

        else:
            # Single mode: [switch] label
            # Render switch: 4 chars total
            if self._checked:
                # On: knob on left [O---]
                ctx.write_text(x_offset, 0, knob_char, knob_style)
                ctx.write_text(x_offset + 1, 0, track_char * 3, track_style)
            else:
                # Off: knob on right [---O]
                ctx.write_text(x_offset, 0, track_char * 3, track_style)
                ctx.write_text(x_offset + 3, 0, knob_char, knob_style)
            x_offset += 4

            if self.label:
                ctx.write_text(x_offset, 0, f" {self.label}", label_style)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the toggle.

        Returns
        -------
        tuple[int, int]
            (width, height) based on mode and labels
        """
        switch_width = 4  # 4-character switch (knob + 3 track chars)

        if self.label_mode == "dual":
            # OFF [switch] ON
            width = len(self.off_label) + 1 + switch_width + 1 + len(self.on_label)
        else:
            # [switch] label
            width = switch_width
            if self.label:
                width += 1 + len(self.label)  # space + label

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
        if key == Keys.SPACE or key == Keys.ENTER:
            self.toggle()
            return True

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse click to toggle.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            if event.button == MouseButton.LEFT:
                self.toggle()
                return True

        return False
