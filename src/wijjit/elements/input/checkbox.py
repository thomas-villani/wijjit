"""Checkbox elements for boolean and multi-select inputs.

This module provides Checkbox and CheckboxGroup elements for creating
single checkboxes and grouped checkbox selections in terminal user interfaces.
Supports keyboard and mouse interaction, custom styling, and change callbacks.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import Element, ElementType, invoke_callback
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.terminal.ansi import (
    supports_unicode,
)
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class Checkbox(Element):
    """Checkbox element for boolean selections.

    A checkbox allows users to toggle a boolean value on/off. It renders
    with unicode box characters when supported, falling back to ASCII.

    Parameters
    ----------
    id : str, optional
        Element identifier
    label : str, optional
        Label text displayed next to checkbox (default: "")
    checked : bool, optional
        Initial checked state (default: False)
    value : str, optional
        Value to associate with this checkbox (default: "")

    Attributes
    ----------
    label : str
        Label text
    checked : bool
        Current checked state
    value : str
        Associated value
    on_change : callable or None
        Callback (old_value, new_value) when state changes
    on_action : callable or None
        Callback when Enter is pressed
    action : str or None
        Action ID to dispatch (set by template extension)
    bind : bool
        Whether to auto-bind to state[id] (default: True)

    Notes
    -----
    Keyboard controls:
    - Space/Enter: Toggle checkbox (Enter also triggers action callback)

    Mouse controls:
    - Click: Toggle checkbox
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        label: str = "",
        checked: bool = False,
        value: str = "",
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.BUTTON  # Treat as interactive button-like
        self.focusable = True
        self.label = label
        self.checked = checked
        self.value = value

        # Callbacks
        self.on_change: Callable[[bool, bool], None] | None = None
        self.on_action: Callable[[], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    def toggle(self) -> None:
        """Toggle the checked state and emit change event."""
        old_value = self.checked
        self.checked = not self.checked
        self._emit_change(old_value, self.checked)

    def _emit_change(self, old_value: bool, new_value: bool) -> None:
        """Emit change event.

        Parameters
        ----------
        old_value : bool
            Previous checked state
        new_value : bool
            New checked state
        """
        if self.on_change and old_value != new_value:
            invoke_callback(self.on_change, old_value, new_value)

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
        # Space or Enter - toggle checkbox and trigger action
        if key == Keys.SPACE or key == Keys.ENTER:
            self.toggle()
            if key == Keys.ENTER and self.on_action:
                invoke_callback(self.on_action)
            return True

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        # Toggle on left click or double-click
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            if event.button == MouseButton.LEFT:
                self.toggle()
                return True

        return False

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the checkbox.

        Returns
        -------
        tuple[int, int]
            (width, height) based on checkbox box and label text
        """
        # Checkbox box character width
        if supports_unicode():
            box_width = 1  # Unicode checkbox is 1 character
        else:
            box_width = 3  # ASCII "[X]" is 3 characters

        # Calculate total width: box + space + label
        if self.label:
            width = box_width + 1 + len(self.label)
        else:
            width = box_width

        return (width, 1)

    def render_to(self, ctx: "PaintContext") -> None:
        """Render checkbox using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the new cell-based rendering method. The legacy render()
        method is kept for backward compatibility.

        Theme styles:

        This element uses the following theme style classes:
        - ``checkbox``: Base style
        - ``checkbox:focus``: When element has focus
        - ``checkbox:checked``: When checkbox is checked
        """

        # Determine checkbox characters based on unicode support
        if supports_unicode():
            unchecked = "\u2610"  # Empty checkbox
            checked_mark = "\u2611"  # Checkbox with check mark
        else:
            unchecked = "[ ]"
            checked_mark = "[X]"

        # Select the appropriate box
        box = checked_mark if self.checked else unchecked

        # Build the full output
        if self.label:
            text = f"{box} {self.label}"
        else:
            text = box

        # Resolve style based on state
        if self.focused:
            resolved_style = ctx.style_resolver.resolve_style(self, "checkbox:focus")
        elif self.checked:
            resolved_style = ctx.style_resolver.resolve_style(self, "checkbox:checked")
        else:
            resolved_style = ctx.style_resolver.resolve_style(self, "checkbox")

        # Render text to buffer
        ctx.write_text(0, 0, text, resolved_style)


class CheckboxGroup(Element):
    """Group of checkboxes for multiple selections.

    A convenience container that manages multiple checkboxes as a single unit,
    with optional borders and titles. Selected values are stored as a list.

    Parameters
    ----------
    id : str, optional
        Element identifier
    options : list, optional
        List of options (strings or dicts with 'value' and 'label' keys)
    selected_values : list, optional
        List of initially selected values
    width : int, optional
        Display width for content area (default: 20).
        Note: Borders add 2 additional columns to total width when enabled.
    orientation : {"vertical", "horizontal"}, optional
        Layout orientation (default: "vertical")
    border_style : BorderStyle or {"single", "double", "rounded"} or None, optional
        Border style for the group (default: None).
        - "single": Single-line box-drawing characters
        - "double": Double-line box-drawing characters
        - "rounded": Rounded corner box-drawing characters
        - None: No borders
        Can also accept BorderStyle enum values.
    title : str, optional
        Title to display in the top border (only shown when border_style is not None)

    Attributes
    ----------
    options : list
        Available options
    selected_values : list
        Currently selected values
    highlighted_index : int
        Index of highlighted option for keyboard navigation
    width : int
        Display width (content area, excluding borders)
    orientation : str
        Layout orientation
    border_style : BorderStyle or None
        Border style for rendering
    title : str or None
        Title displayed in top border (when borders are enabled)

    Notes
    -----
    Options can be specified as:
    - Simple strings: ["Option A", "Option B", "Option C"]
    - Value/label dicts: [{"value": "a", "label": "Option A"}, ...]

    Navigation:
    - Up/Down (vertical) or Left/Right (horizontal): Navigate options
    - Space/Enter: Toggle highlighted option (Enter also triggers action)
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        options: list[Any] | None = None,
        selected_values: list[Any] | None = None,
        width: int = 20,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        border_style: (
            BorderStyle | Literal["single", "double", "rounded"] | None
        ) = None,
        title: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.SELECTABLE
        self.focusable = True

        # Normalize options
        self._raw_options = options or []
        self.options = self._normalize_options(self._raw_options)

        # Selection state
        self.selected_values = set(selected_values) if selected_values else set()
        self.highlighted_index = 0

        # Display properties
        self.width = width
        self.orientation = orientation

        # Border style
        self.border_style = self._normalize_border_style(border_style)
        self.title = title

        # Callbacks
        self.on_change: Callable[[list[Any], list[Any]], None] | None = None
        self.on_action: Callable[[], None] | None = None
        self.on_highlight_change: Callable[[int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True
        # highlight_state_key auto-generates to "{id}:highlight"
        self._highlight_state_key_override: str | None = None

    @property
    def highlight_state_key(self) -> str | None:
        """Get the state key for highlighted index.

        Returns the explicitly set key if provided, otherwise auto-generates
        from the element id using the convention "{id}:highlight".

        Returns
        -------
        str or None
            State key for highlight, or None if no id
        """
        if self._highlight_state_key_override is not None:
            return self._highlight_state_key_override
        return self._state_key("highlight")

    @highlight_state_key.setter
    def highlight_state_key(self, value: str | None) -> None:
        """Set an explicit highlight state key."""
        self._highlight_state_key_override = value

    def _normalize_border_style(
        self, style: BorderStyle | Literal["single", "double", "rounded"] | None
    ) -> BorderStyle | None:
        """Normalize border style from string or enum to BorderStyle enum."""
        if style is None:
            return None
        if isinstance(style, BorderStyle):
            return style
        style_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        return style_map.get(style.lower(), BorderStyle.SINGLE)

    def _normalize_options(self, options: list[Any]) -> list[dict[str, Any]]:
        """Normalize options to internal format with value and label."""
        normalized = []
        for opt in options:
            if isinstance(opt, dict):
                normalized.append(
                    {
                        "value": opt.get("value", ""),
                        "label": opt.get("label", opt.get("value", "")),
                    }
                )
            else:
                normalized.append({"value": str(opt), "label": str(opt)})
        return normalized

    def toggle_option(self, index: int) -> None:
        """Toggle selection of option at index.

        Parameters
        ----------
        index : int
            Index of option to toggle
        """
        if 0 <= index < len(self.options):
            old_values = list(self.selected_values)
            value = self.options[index]["value"]

            if value in self.selected_values:
                self.selected_values.remove(value)
            else:
                self.selected_values.add(value)

            new_values = list(self.selected_values)
            self._emit_change(old_values, new_values)

    def _emit_change(self, old_values: list[Any], new_values: list[Any]) -> None:
        """Emit change event."""
        if self.on_change and old_values != new_values:
            invoke_callback(self.on_change, old_values, new_values)

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input."""
        if not self.options:
            return False

        # Space or Enter - toggle highlighted option and trigger action
        if key == Keys.SPACE or key == Keys.ENTER:
            self.toggle_option(self.highlighted_index)
            if key == Keys.ENTER and self.on_action:
                invoke_callback(self.on_action)
            return True

        # Navigation
        elif self.orientation == "vertical":
            if key == Keys.UP:
                if self.highlighted_index > 0:
                    self.highlighted_index -= 1
                    self._emit_highlight_change(self.highlighted_index)
                return True
            elif key == Keys.DOWN:
                if self.highlighted_index < len(self.options) - 1:
                    self.highlighted_index += 1
                    self._emit_highlight_change(self.highlighted_index)
                return True
        else:  # horizontal
            if key == Keys.LEFT:
                if self.highlighted_index > 0:
                    self.highlighted_index -= 1
                    self._emit_highlight_change(self.highlighted_index)
                return True
            elif key == Keys.RIGHT:
                if self.highlighted_index < len(self.options) - 1:
                    self.highlighted_index += 1
                    self._emit_highlight_change(self.highlighted_index)
                return True

        return False

    def _emit_highlight_change(self, new_index: int) -> None:
        """Emit highlight change event.

        Parameters
        ----------
        new_index : int
            New highlighted index
        """
        if self.on_highlight_change:
            invoke_callback(self.on_highlight_change, new_index)

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input."""
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            if not self.bounds:
                return False

            # Convert to relative coordinates
            relative_x = event.x - self.bounds.x
            relative_y = event.y - self.bounds.y

            # Account for borders if present
            if self.border_style is not None:
                relative_y -= 1  # Top border
                relative_x -= 1  # Left border

            # Determine which option was clicked based on orientation
            if self.orientation == "vertical":
                if 0 <= relative_y < len(self.options):
                    self.highlighted_index = relative_y
                    self.toggle_option(relative_y)
                    return True
            else:  # horizontal
                # Calculate based on checkbox width
                checkbox_width = 5  # Approximate width per checkbox
                clicked_index = relative_x // checkbox_width
                if 0 <= clicked_index < len(self.options):
                    self.highlighted_index = clicked_index
                    self.toggle_option(clicked_index)
                    return True

        return False

    def render_to(self, ctx: "PaintContext") -> None:
        """Render checkbox group using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Theme styles:

        This element uses the following theme style classes:
        - ``checkbox``: For individual checkbox items
        - ``checkbox:checked``: For checked checkbox items
        - ``frame.border``: For the border (when border_style is not None)
        - ``text.title``: For the title text in border
        """
        from wijjit.styling.style import Style

        # Determine if we have borders
        has_border = self.border_style is not None
        chars = (
            BORDER_CHARS[self.border_style] if self.border_style is not None else None
        )

        # Resolve border style
        if has_border:
            if self.focused:
                # Cyan bold border when focused
                border_style = Style(fg_color=(0, 255, 255), bold=True)
            else:
                border_style = ctx.style_resolver.resolve_style(self, "frame.border")

        # Track current y position
        y_pos = 0

        # Draw top border with optional title
        if has_border and chars:
            if self.title:
                title_text = f" {self.title} "
                title_len = len(title_text)
                remaining = self.width - title_len

                if remaining >= 0:
                    left_len = 1
                    right_len = remaining - left_len
                    # Draw top-left corner + left horizontal
                    ctx.write_text(
                        0, y_pos, chars["tl"] + chars["h"] * left_len, border_style
                    )
                    # Draw title
                    title_style = ctx.style_resolver.resolve_style(self, "text.title")
                    ctx.write_text(1 + left_len, y_pos, title_text, title_style)
                    # Draw right horizontal + top-right corner
                    ctx.write_text(
                        1 + left_len + title_len,
                        y_pos,
                        chars["h"] * right_len + chars["tr"],
                        border_style,
                    )
                else:
                    # Title too long, clip it
                    title_text = title_text[: self.width]
                    ctx.write_text(0, y_pos, chars["tl"], border_style)
                    title_style = ctx.style_resolver.resolve_style(self, "text.title")
                    ctx.write_text(1, y_pos, title_text, title_style)
                    ctx.write_text(
                        1 + len(title_text), y_pos, chars["tr"], border_style
                    )
            else:
                # No title, simple top border
                top_border = chars["tl"] + chars["h"] * self.width + chars["tr"]
                ctx.write_text(0, y_pos, top_border, border_style)

            y_pos += 1

        # Render checkboxes
        if self.orientation == "vertical":
            # Each checkbox on its own line
            for i, opt in enumerate(self.options):
                is_selected = opt["value"] in self.selected_values
                is_highlighted = i == self.highlighted_index

                # Determine checkbox character
                if supports_unicode():
                    box = "\u2611" if is_selected else "\u2610"
                else:
                    box = "[X]" if is_selected else "[ ]"

                checkbox_text = f"{box} {opt['label']}"

                # Resolve style
                if is_highlighted and self.focused:
                    # Highlighted: use reverse video
                    base_style = ctx.style_resolver.resolve_style(self, "checkbox")
                    checkbox_style = Style(
                        fg_color=base_style.bg_color or (0, 0, 0),
                        bg_color=base_style.fg_color or (255, 255, 255),
                        reverse=True,
                    )
                elif is_selected:
                    checkbox_style = ctx.style_resolver.resolve_style(
                        self, "checkbox:checked"
                    )
                else:
                    checkbox_style = ctx.style_resolver.resolve_style(self, "checkbox")

                # Clip or pad to width
                if len(checkbox_text) > self.width:
                    checkbox_text = checkbox_text[: self.width]
                else:
                    checkbox_text = checkbox_text.ljust(self.width)

                # Draw left border if present
                x_offset = 0
                if has_border and chars:
                    ctx.write_text(0, y_pos, chars["v"], border_style)
                    x_offset = 1

                # Draw checkbox text
                ctx.write_text(x_offset, y_pos, checkbox_text, checkbox_style)

                # Draw right border if present
                if has_border and chars:
                    ctx.write_text(
                        x_offset + self.width, y_pos, chars["v"], border_style
                    )

                y_pos += 1

        else:
            # Horizontal orientation - all on one line
            x_offset = 0

            # Draw left border if present
            if has_border and chars:
                ctx.write_text(0, y_pos, chars["v"], border_style)
                x_offset = 1

            # Render each checkbox side by side
            for i, opt in enumerate(self.options):
                is_selected = opt["value"] in self.selected_values
                is_highlighted = i == self.highlighted_index

                # Determine checkbox character
                if supports_unicode():
                    box = "\u2611" if is_selected else "\u2610"
                else:
                    box = "[X]" if is_selected else "[ ]"

                checkbox_text = f"{box} {opt['label']}"

                # Resolve style
                if is_highlighted and self.focused:
                    base_style = ctx.style_resolver.resolve_style(self, "checkbox")
                    checkbox_style = Style(
                        fg_color=base_style.bg_color or (0, 0, 0),
                        bg_color=base_style.fg_color or (255, 255, 255),
                        reverse=True,
                    )
                elif is_selected:
                    checkbox_style = ctx.style_resolver.resolve_style(
                        self, "checkbox:checked"
                    )
                else:
                    checkbox_style = ctx.style_resolver.resolve_style(self, "checkbox")

                # Render checkbox
                ctx.write_text(x_offset, y_pos, checkbox_text, checkbox_style)
                x_offset += len(checkbox_text) + 1  # +1 for space

            # Pad remaining space and draw right border
            if has_border and chars:
                remaining = self.width - (x_offset - 1)
                if remaining > 0:
                    default_style = ctx.style_resolver.resolve_style(self, "checkbox")
                    ctx.write_text(x_offset, y_pos, " " * remaining, default_style)
                    x_offset += remaining
                ctx.write_text(x_offset, y_pos, chars["v"], border_style)

            y_pos += 1

        # Draw bottom border
        if has_border and chars:
            bottom_border = chars["bl"] + chars["h"] * self.width + chars["br"]
            ctx.write_text(0, y_pos, bottom_border, border_style)

    def get_ephemeral_state(self) -> dict[str, Any]:
        """Get ephemeral state for reconciliation.

        Returns
        -------
        dict
            Highlight state that should survive re-renders
        """
        return {
            "highlighted_index": self.highlighted_index,
        }

    def restore_ephemeral_state(self, state: dict[str, Any]) -> None:
        """Restore ephemeral state after reconciliation.

        Parameters
        ----------
        state : dict
            State from get_ephemeral_state()
        """
        # Restore highlight
        if "highlighted_index" in state:
            max_index = len(self.options) - 1 if self.options else 0
            self.highlighted_index = min(state["highlighted_index"], max_index)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size of the checkbox group.

        Returns
        -------
        tuple[int, int]
            (width, height) based on options and orientation

        Notes
        -----
        For vertical orientation: height = number of options (+ 2 for borders)
        For horizontal orientation: height = 1 (+ 2 for borders)
        Width includes border characters if borders are enabled.
        """
        # Calculate content height
        if self.orientation == "vertical":
            content_height = len(self.options) if self.options else 1
        else:
            content_height = 1

        # Calculate content width
        if self.orientation == "horizontal":
            # Sum of all option widths plus spacing
            total_width = 0
            for opt in self.options:
                # Checkbox (1-3 chars) + space + label
                box_width = 1 if supports_unicode() else 3
                total_width += box_width + 1 + len(opt["label"]) + 1
            content_width = max(total_width, self.width)
        else:
            content_width = self.width

        # Add border space if borders enabled
        if self.border_style is not None:
            return (content_width + 2, content_height + 2)
        else:
            return (content_width, content_height)
