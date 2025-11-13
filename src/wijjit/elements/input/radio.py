# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from wijjit.elements.base import Element, ElementType
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.terminal.ansi import (
    ANSIColor,
    ANSIStyle,
    clip_to_width,
    supports_unicode,
    visible_length,
)
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class Radio(Element):
    """Radio button element for mutually exclusive selections.

    A radio button is part of a group (defined by the 'name' attribute) where
    only one radio can be selected at a time. It renders with unicode circle
    characters when supported, falling back to ASCII.

    Parameters
    ----------
    id : str, optional
        Element identifier
    name : str
        Group name for mutual exclusion (required)
    label : str, optional
        Label text displayed next to radio button (default: "")
    checked : bool, optional
        Initial checked state (default: False)
    value : str, optional
        Value to associate with this radio button (default: "")

    Attributes
    ----------
    name : str
        Group name
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
    Radio buttons with the same 'name' form a group where only one
    can be selected at a time. The app manages this mutual exclusion.

    Keyboard controls:
    - Space: Select this radio
    - Enter: Trigger action
    - Arrow keys: Navigate within radio group (handled by app)

    Mouse controls:
    - Click: Select this radio
    """

    def __init__(
        self,
        name: str,
        id: str | None = None,
        label: str = "",
        checked: bool = False,
        value: str = "",
    ):
        super().__init__(id)
        self.element_type = ElementType.BUTTON  # Treat as interactive button-like
        self.focusable = True
        self.name = name  # Group identifier
        self.label = label
        self.checked = checked
        self.value = value

        # Callbacks
        self.on_change: Callable[[bool, bool], None] | None = None
        self.on_action: Callable[[], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # Group navigation
        self.radio_group: list[Radio] | None = None  # Set by app

    def select(self) -> None:
        """Select this radio button and emit change event."""
        if not self.checked:
            old_value = self.checked
            self.checked = True
            self._emit_change(old_value, self.checked)

    def deselect(self) -> None:
        """Deselect this radio button (called by group management)."""
        if self.checked:
            old_value = self.checked
            self.checked = False
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
            self.on_change(old_value, new_value)

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
        # Space - select this radio
        if key == Keys.SPACE:
            self.select()
            return True

        # Enter - trigger action
        elif key == Keys.ENTER:
            if self.on_action:
                self.on_action()
            return True

        # Arrow keys for navigation within group
        elif key == Keys.UP or key == Keys.DOWN:
            if self.radio_group:
                try:
                    current_index = self.radio_group.index(self)
                    if key == Keys.UP:
                        next_index = (current_index - 1) % len(self.radio_group)
                    else:  # DOWN
                        next_index = (current_index + 1) % len(self.radio_group)

                    # Select the next radio
                    next_radio = self.radio_group[next_index]
                    next_radio.select()
                    return True
                except ValueError:
                    pass

        return False

    def handle_mouse(self, event: MouseEvent) -> bool:
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
        # Select on click or double-click
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            self.select()
            return True

        return False

    def render(self) -> str:
        """Render the radio button (LEGACY ANSI rendering).

        Returns
        -------
        str
            Rendered radio button with label

        Notes
        -----
        This is the legacy ANSI string-based rendering method.
        New code should use render_to() for cell-based rendering.
        Kept for backward compatibility.
        """
        # Determine radio characters based on unicode support
        if supports_unicode():
            unchecked = "\u25cb"  # Empty circle
            checked_mark = "\u25c9"  # Filled circle
        else:
            unchecked = "( )"
            checked_mark = "(*)"

        # Select the appropriate circle
        circle = checked_mark if self.checked else unchecked

        # Build the full output
        if self.label:
            output = f"{circle} {self.label}"
        else:
            output = circle

        # Style based on focus
        if self.focused:
            # Focused: bold and highlighted
            styles = (
                f"{ANSIStyle.RESET}{ANSIStyle.BOLD}{ANSIColor.BG_BLUE}{ANSIColor.WHITE}"
            )
            return f"{styles}{output}{ANSIStyle.RESET}"
        else:
            # Not focused: plain style
            return f"{ANSIStyle.RESET}{output}{ANSIStyle.RESET}"

    def render_to(self, ctx: "PaintContext") -> None:
        """Render radio button using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the new cell-based rendering method. The legacy render()
        method is kept for backward compatibility.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'radio': Base style
        - 'radio:focus': When element has focus
        - 'radio:selected': When radio is selected
        """

        # Determine radio characters based on unicode support
        if supports_unicode():
            unchecked = "\u25cb"  # Empty circle
            checked_mark = "\u25c9"  # Filled circle
        else:
            unchecked = "( )"
            checked_mark = "(*)"

        # Select the appropriate circle
        circle = checked_mark if self.checked else unchecked

        # Build the full output
        if self.label:
            text = f"{circle} {self.label}"
        else:
            text = circle

        # Resolve style based on state
        if self.focused:
            resolved_style = ctx.style_resolver.resolve_style(self, "radio:focus")
        elif self.checked:
            resolved_style = ctx.style_resolver.resolve_style(self, "radio:selected")
        else:
            resolved_style = ctx.style_resolver.resolve_style(self, "radio")

        # Render text to buffer
        ctx.write_text(0, 0, text, resolved_style)


class RadioGroup(Element):
    """Group of radio buttons for single selection.

    A convenience container that manages multiple radio buttons as a single unit,
    with optional borders and titles. Only one option can be selected at a time.

    Parameters
    ----------
    id : str, optional
        Element identifier
    name : str
        Group name for radio buttons (required)
    options : list, optional
        List of options (strings or dicts with 'value' and 'label' keys)
    selected_value : str, optional
        Initially selected value
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
    name : str
        Group name
    options : list
        Available options
    selected_value : str or None
        Currently selected value
    selected_index : int
        Index of selected option (-1 if none)
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
    - Simple strings: ["Small", "Medium", "Large"]
    - Value/label dicts: [{"value": "s", "label": "Small"}, ...]

    Navigation:
    - Up/Down (vertical) or Left/Right (horizontal): Navigate and auto-select
    - Space: Select highlighted option
    - Enter: Trigger action
    """

    def __init__(
        self,
        name: str,
        id: str | None = None,
        options: list | None = None,
        selected_value: str | None = None,
        width: int = 20,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        border_style: (
            BorderStyle | Literal["single", "double", "rounded"] | None
        ) = None,
        title: str | None = None,
    ):
        super().__init__(id)
        self.element_type = ElementType.SELECTABLE
        self.focusable = True
        self.name = name  # Group identifier

        # Normalize options
        self._raw_options = options or []
        self.options = self._normalize_options(self._raw_options)

        # Selection state
        self.selected_value = selected_value
        self.selected_index = self._find_option_index(selected_value)
        self.highlighted_index = max(0, self.selected_index) if self.options else 0

        # Display properties
        self.width = width
        self.orientation = orientation

        # Border style
        self.border_style = self._normalize_border_style(border_style)
        self.title = title

        # Callbacks
        self.on_change: Callable[[str | None, str | None], None] | None = None
        self.on_action: Callable[[], None] | None = None
        self.on_highlight_change: Callable[[int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True
        self.highlight_state_key: str | None = None

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

    def _normalize_options(self, options: list) -> list[dict]:
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

    def _find_option_index(self, value: str | None) -> int:
        """Find index of option with given value."""
        if value is None:
            return -1
        for i, opt in enumerate(self.options):
            if opt["value"] == value:
                return i
        return -1

    def select_option(self, index: int) -> None:
        """Select option at index.

        Parameters
        ----------
        index : int
            Index of option to select
        """
        if 0 <= index < len(self.options):
            old_value = self.selected_value
            self.selected_value = self.options[index]["value"]
            self.selected_index = index
            self._emit_change(old_value, self.selected_value)

    def _emit_change(self, old_value: str | None, new_value: str | None) -> None:
        """Emit change event."""
        if self.on_change and old_value != new_value:
            self.on_change(old_value, new_value)

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input."""
        if not self.options:
            return False

        # Space - select highlighted option
        if key == Keys.SPACE:
            self.select_option(self.highlighted_index)
            return True

        # Enter - trigger action
        elif key == Keys.ENTER:
            if self.on_action:
                self.on_action()
            return True

        # Navigation with auto-selection
        elif self.orientation == "vertical":
            if key == Keys.UP:
                if self.highlighted_index > 0:
                    self.highlighted_index -= 1
                    self._emit_highlight_change(self.highlighted_index)
                    self.select_option(self.highlighted_index)
                return True
            elif key == Keys.DOWN:
                if self.highlighted_index < len(self.options) - 1:
                    self.highlighted_index += 1
                    self._emit_highlight_change(self.highlighted_index)
                    self.select_option(self.highlighted_index)
                return True
        else:  # horizontal
            if key == Keys.LEFT:
                if self.highlighted_index > 0:
                    self.highlighted_index -= 1
                    self._emit_highlight_change(self.highlighted_index)
                    self.select_option(self.highlighted_index)
                return True
            elif key == Keys.RIGHT:
                if self.highlighted_index < len(self.options) - 1:
                    self.highlighted_index += 1
                    self._emit_highlight_change(self.highlighted_index)
                    self.select_option(self.highlighted_index)
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
            self.on_highlight_change(new_index)

    def handle_mouse(self, event: MouseEvent) -> bool:
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
                    self.select_option(relative_y)
                    return True
            else:  # horizontal
                # Calculate based on radio width
                radio_width = 5  # Approximate width per radio
                clicked_index = relative_x // radio_width
                if 0 <= clicked_index < len(self.options):
                    self.highlighted_index = clicked_index
                    self.select_option(clicked_index)
                    return True

        return False

    def render(self) -> str:
        """Render the radio group (LEGACY ANSI rendering).

        Returns
        -------
        str
            Rendered radio group with optional borders

        Notes
        -----
        This is the legacy ANSI string-based rendering method.
        New code should use render_to() for cell-based rendering.
        Kept for backward compatibility.
        """
        chars = BORDER_CHARS[self.border_style] if self.border_style else None

        lines = []

        # Render radio buttons
        for i, opt in enumerate(self.options):
            is_selected = i == self.selected_index
            is_highlighted = i == self.highlighted_index

            # Determine radio characters
            if supports_unicode():
                circle = "\u25c9" if is_selected else "\u25cb"
            else:
                circle = "(*)" if is_selected else "( )"

            # Build radio line
            radio_text = f"{circle} {opt['label']}"

            # Apply highlighting
            if is_highlighted and self.focused:
                radio_text = (
                    f"{ANSIStyle.RESET}{ANSIStyle.REVERSE}{radio_text}{ANSIStyle.RESET}"
                )
            else:
                radio_text = f"{ANSIStyle.RESET}{radio_text}{ANSIStyle.RESET}"

            # Pad to width
            radio_len = visible_length(radio_text)
            if radio_len < self.width:
                radio_text += " " * (self.width - radio_len)
            elif radio_len > self.width:
                radio_text = clip_to_width(radio_text, self.width, ellipsis="...")

            if self.orientation == "vertical":
                lines.append(radio_text)
            else:  # horizontal - join with space
                if not lines:
                    lines.append(radio_text)
                else:
                    lines[0] += " " + radio_text

        # Apply borders if enabled
        if self.border_style is not None and chars is not None:
            # Choose border color based on focus
            if self.focused:
                border_color = f"{ANSIStyle.BOLD}{ANSIColor.CYAN}"
                reset = ANSIStyle.RESET
            else:
                border_color = ""
                reset = ""

            # Calculate content width
            if self.orientation == "horizontal":
                content_width = visible_length(lines[0]) if lines else self.width
            else:
                content_width = self.width

            # Top border with optional title
            if self.title:
                title_text = f" {self.title} "
                title_len = visible_length(title_text)
                remaining = content_width - title_len

                if remaining >= 0:
                    left_len = 1
                    right_len = remaining - left_len
                    top_border = (
                        f"{border_color}{chars['tl']}{chars['h'] * left_len}"
                        f"{reset}{title_text}{border_color}"
                        f"{chars['h'] * right_len}{chars['tr']}{reset}"
                    )
                else:
                    title_text = clip_to_width(
                        title_text, content_width, ellipsis="..."
                    )
                    top_border = f"{border_color}{chars['tl']}{reset}{title_text}{border_color}{chars['tr']}{reset}"
            else:
                top_border = f"{border_color}{chars['tl']}{chars['h'] * content_width}{chars['tr']}{reset}"

            # Wrap content lines with borders
            bordered_lines = []
            for line in lines:
                bordered_lines.append(
                    f"{border_color}{chars['v']}{reset}{line}{border_color}{chars['v']}{reset}"
                )

            # Bottom border
            bottom_border = f"{border_color}{chars['bl']}{chars['h'] * content_width}{chars['br']}{reset}"

            return f"{top_border}\n" + "\n".join(bordered_lines) + f"\n{bottom_border}"
        else:
            # No borders
            return "\n".join(lines)

    def render_to(self, ctx: "PaintContext") -> None:
        """Render radio group using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the new cell-based rendering method. The legacy render()
        method is kept for backward compatibility.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'radio': For individual radio button items
        - 'radio:selected': For selected radio button
        - 'frame.border': For the border (when border_style is not None)
        - 'text.title': For the title text in border
        """
        from wijjit.styling.style import Style

        # Determine if we have borders
        has_border = self.border_style is not None
        chars = BORDER_CHARS[self.border_style] if has_border else None

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

        # Render radio buttons
        if self.orientation == "vertical":
            # Each radio button on its own line
            for i, opt in enumerate(self.options):
                is_selected = i == self.selected_index
                is_highlighted = i == self.highlighted_index

                # Determine radio character
                if supports_unicode():
                    circle = "\u25c9" if is_selected else "\u25cb"
                else:
                    circle = "(*)" if is_selected else "( )"

                radio_text = f"{circle} {opt['label']}"

                # Resolve style
                if is_highlighted and self.focused:
                    # Highlighted: use reverse video
                    base_style = ctx.style_resolver.resolve_style(self, "radio")
                    radio_style = Style(
                        fg_color=base_style.bg_color or (0, 0, 0),
                        bg_color=base_style.fg_color or (255, 255, 255),
                        reverse=True,
                    )
                elif is_selected:
                    radio_style = ctx.style_resolver.resolve_style(
                        self, "radio:selected"
                    )
                else:
                    radio_style = ctx.style_resolver.resolve_style(self, "radio")

                # Clip or pad to width
                if len(radio_text) > self.width:
                    radio_text = radio_text[: self.width]
                else:
                    radio_text = radio_text.ljust(self.width)

                # Draw left border if present
                x_offset = 0
                if has_border and chars:
                    ctx.write_text(0, y_pos, chars["v"], border_style)
                    x_offset = 1

                # Draw radio text
                ctx.write_text(x_offset, y_pos, radio_text, radio_style)

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

            # Render each radio button side by side
            for i, opt in enumerate(self.options):
                is_selected = i == self.selected_index
                is_highlighted = i == self.highlighted_index

                # Determine radio character
                if supports_unicode():
                    circle = "\u25c9" if is_selected else "\u25cb"
                else:
                    circle = "(*)" if is_selected else "( )"

                radio_text = f"{circle} {opt['label']}"

                # Resolve style
                if is_highlighted and self.focused:
                    base_style = ctx.style_resolver.resolve_style(self, "radio")
                    radio_style = Style(
                        fg_color=base_style.bg_color or (0, 0, 0),
                        bg_color=base_style.fg_color or (255, 255, 255),
                        reverse=True,
                    )
                elif is_selected:
                    radio_style = ctx.style_resolver.resolve_style(
                        self, "radio:selected"
                    )
                else:
                    radio_style = ctx.style_resolver.resolve_style(self, "radio")

                # Render radio button
                ctx.write_text(x_offset, y_pos, radio_text, radio_style)
                x_offset += len(radio_text) + 1  # +1 for space

            # Pad remaining space and draw right border
            if has_border and chars:
                remaining = self.width - (x_offset - 1)
                if remaining > 0:
                    default_style = ctx.style_resolver.resolve_style(self, "radio")
                    ctx.write_text(x_offset, y_pos, " " * remaining, default_style)
                    x_offset += remaining
                ctx.write_text(x_offset, y_pos, chars["v"], border_style)

            y_pos += 1

        # Draw bottom border
        if has_border and chars:
            bottom_border = chars["bl"] + chars["h"] * self.width + chars["br"]
            ctx.write_text(0, y_pos, bottom_border, border_style)
