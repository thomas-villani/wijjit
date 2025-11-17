# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable
from typing import Literal

from wijjit.elements.base import Element, ElementType, ScrollableMixin
from wijjit.layout.frames import BORDER_CHARS, BorderStyle
from wijjit.layout.scroll import ScrollManager
from wijjit.terminal.ansi import ANSIStyle, clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class Select(ScrollableMixin, Element):
    """Select list element for choosing from a scrollable list of options.

    This is a fixed-height scrollable list selector suitable for TUI applications.
    Unlike web dropdowns, this is always visible and uses vertical space efficiently.

    Parameters
    ----------
    id : str, optional
        Element identifier
    options : list, optional
        List of options (strings or dicts with 'value' and 'label' keys)
    value : str, optional
        Currently selected value
    width : int, optional
        Display width for content area (default: 20).
        Note: Borders add 2 additional columns to total width when enabled.
    visible_rows : int, optional
        Number of visible rows in the list (default: 5)
    disabled_values : list, optional
        List of values that are disabled (cannot be selected)
    placeholder : str, optional
        Text to display when options list is empty (default: "No options")
    item_renderer : callable, optional
        Custom renderer function: (option, selected, highlighted, disabled) -> str
    border_style : BorderStyle or {"single", "double", "rounded"} or None, optional
        Border style for the select list (default: None).
        - "single": Single-line box-drawing characters
        - "double": Double-line box-drawing characters
        - "rounded": Rounded corner box-drawing characters
        - None: No borders (backward compatible)
        Can also accept BorderStyle enum values.
    title : str, optional
        Title to display in the top border (only shown when border_style is not None)

    Attributes
    ----------
    options : list
        Available options
    value : str or None
        Currently selected value
    selected_index : int
        Index of selected option (-1 if none)
    highlighted_index : int
        Index of highlighted option for keyboard navigation
    width : int
        Display width (content area, excluding borders)
    visible_rows : int
        Number of visible rows
    disabled_values : set
        Set of disabled values
    placeholder : str
        Text to display when options list is empty
    item_renderer : callable or None
        Custom renderer function
    scroll_manager : ScrollManager
        Manages scrolling of options list
    border_style : BorderStyle or None
        Border style for rendering
    title : str or None
        Title displayed in top border (when borders are enabled)

    Notes
    -----
    Options can be specified as:
    - Simple strings: ["Red", "Green", "Blue"]
    - Value/label dicts: [{"value": "r", "label": "Red"}, ...]
    - Mixed: ["Simple", {"value": "v", "label": "Complex"}]

    Navigation:
    - Up/Down: Navigate options
    - Enter/Space: Select highlighted option
    - Home/End: Jump to first/last option
    - PageUp/PageDown: Scroll by page
    """

    def __init__(
        self,
        id: str | None = None,
        options: list | None = None,
        value: str | None = None,
        width: int = 20,
        visible_rows: int = 5,
        disabled_values: list | None = None,
        placeholder: str = "No options",
        item_renderer: Callable | None = None,
        on_change: Callable[[str | None, str | None], None] | None = None,
        border_style: (
            BorderStyle | Literal["single", "double", "rounded"] | None
        ) = None,
        title: str | None = None,
    ):
        ScrollableMixin.__init__(self)
        Element.__init__(self, id)
        self.element_type = ElementType.SELECTABLE
        self.focusable = True

        # Normalize options to internal format
        self._raw_options = options or []
        self.options = self._normalize_options(self._raw_options)

        # Selection state
        self.value = value
        self.selected_index = self._find_option_index(value)
        self.highlighted_index = max(0, self.selected_index) if self.options else 0

        # Display properties
        self.width = width
        self.visible_rows = visible_rows

        # Disabled options
        self.disabled_values = set(disabled_values) if disabled_values else set()

        # Placeholder text for empty state
        self.placeholder = placeholder

        # Custom renderer
        self.item_renderer = item_renderer

        # Border style (normalize string to enum)
        self.border_style = self._normalize_border_style(border_style)

        # Title for border display
        self.title = title

        # Scroll management for long lists
        self.scroll_manager = ScrollManager(
            content_size=len(self.options), viewport_size=visible_rows
        )

        # Ensure highlighted option is visible with margin
        if self.highlighted_index >= 0:
            # Calculate scroll position to center the highlighted item, or keep it with margin
            margin = min(
                2, visible_rows // 4
            )  # Use 2-line margin, or 1/4 of viewport if smaller

            # Try to position with margin from top
            target_scroll = max(0, self.highlighted_index - margin)

            # But also ensure we don't scroll past the end
            max_scroll = max(0, len(self.options) - visible_rows)
            target_scroll = min(target_scroll, max_scroll)

            self.scroll_manager.scroll_to(target_scroll)

        # Callbacks
        self.on_change: Callable[[str | None, str | None], None] | None = on_change
        self.on_action: Callable[[], None] | None = None
        self.on_highlight_change: Callable[[int], None] | None = None
        # on_scroll provided by ScrollableMixin

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True
        self.highlight_state_key: str | None = None
        # scroll_state_key provided by ScrollableMixin

        # Backward compatibility
        self.max_visible = visible_rows  # Alias for tests

    def _normalize_border_style(
        self, style: BorderStyle | Literal["single", "double", "rounded"] | None
    ) -> BorderStyle | None:
        """Normalize border style from string or enum to BorderStyle enum.

        Parameters
        ----------
        style : BorderStyle or str or None
            Border style as enum, string, or None

        Returns
        -------
        BorderStyle or None
            Normalized border style as enum, or None
        """
        if style is None:
            return None
        if isinstance(style, BorderStyle):
            return style
        # Convert string to enum
        style_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        return style_map.get(style.lower(), BorderStyle.SINGLE)

    def _normalize_options(self, options: list) -> list[dict]:
        """Normalize options to internal format with value and label.

        Parameters
        ----------
        options : list
            Raw options (strings or dicts)

        Returns
        -------
        list of dict
            Normalized options with 'value' and 'label' keys
        """
        normalized = []
        for opt in options:
            if isinstance(opt, dict):
                # Already in dict format
                normalized.append(
                    {
                        "value": opt.get("value", ""),
                        "label": opt.get("label", opt.get("value", "")),
                    }
                )
            else:
                # String format - use same value for both
                normalized.append({"value": str(opt), "label": str(opt)})
        return normalized

    def _find_option_index(self, value: str | None) -> int:
        """Find index of option with given value.

        Parameters
        ----------
        value : str or None
            Value to search for

        Returns
        -------
        int
            Index of option, or -1 if not found
        """
        if value is None:
            return -1

        for i, opt in enumerate(self.options):
            if opt["value"] == value:
                return i
        return -1

    def _skip_disabled_options(self, start_index: int, direction: int) -> int:
        """Find next enabled option in given direction.

        Parameters
        ----------
        start_index : int
            Starting index in options list
        direction : int
            Direction to search (1 for down, -1 for up, 0 for current check)

        Returns
        -------
        int
            Index of next enabled option, or start_index if none found
        """
        if not self.options:
            return -1

        options_count = len(self.options)

        # First check if start_index itself is valid and enabled
        if 0 <= start_index < options_count:
            opt_value = self.options[start_index]["value"]
            if opt_value not in self.disabled_values:
                return start_index

        # Start_index is disabled or invalid, search for next enabled option
        current = start_index
        for _ in range(options_count):
            current = (current + direction) % options_count
            opt_value = self.options[current]["value"]
            if opt_value not in self.disabled_values:
                return current

        # All options disabled
        return start_index

    def on_focus(self) -> None:
        """Called when element gains focus.

        Note: highlighted_index is preserved across renders via state persistence,
        so we don't reset it here. It's initialized correctly during __init__
        (either from state restoration or defaults to selected_index).
        """
        super().on_focus()

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
        if not self.options:
            return False

        old_value = self.value

        # Enter or Space - select current highlighted option
        if key == Keys.ENTER or key == Keys.SPACE:
            if 0 <= self.highlighted_index < len(self.options):
                opt = self.options[self.highlighted_index]
                # Check if disabled
                if opt["value"] not in self.disabled_values:
                    self.value = opt["value"]
                    self.selected_index = self.highlighted_index
                    self._emit_change(old_value, self.value)
                    return True
            return True

        # Up arrow - move highlight up (selection happens on Enter/Space)
        elif key == Keys.UP:
            if self.highlighted_index > 0:
                new_index = self.highlighted_index - 1
                # Skip disabled options if any exist
                if self.disabled_values:
                    new_index = self._skip_disabled_options(new_index, -1)
                if new_index != self.highlighted_index:
                    self.highlighted_index = new_index
                    self._emit_highlight_change(self.highlighted_index)
                    # Ensure visible with margin (keep 2 lines visible above when possible)
                    visible_start, _ = self.scroll_manager.get_visible_range()
                    margin = 2
                    if self.highlighted_index < visible_start + margin:
                        # Scroll up to keep margin, but don't go below 0
                        target = max(0, self.highlighted_index - margin)
                        self.scroll_manager.scroll_to(target)
                        self._emit_scroll_change()
            return True

        # Down arrow - move highlight down (selection happens on Enter/Space)
        elif key == Keys.DOWN:
            if self.highlighted_index < len(self.options) - 1:
                new_index = self.highlighted_index + 1
                # Skip disabled options if any exist
                if self.disabled_values:
                    new_index = self._skip_disabled_options(new_index, 1)
                if new_index != self.highlighted_index:
                    self.highlighted_index = new_index
                    self._emit_highlight_change(self.highlighted_index)
                    # Ensure visible with margin (keep 2 lines visible below when possible)
                    _, visible_end = self.scroll_manager.get_visible_range()
                    margin = 2
                    # Calculate how many lines are below the highlighted index
                    lines_below = (visible_end - 1) - self.highlighted_index
                    if lines_below < margin:
                        # Scroll down to keep margin
                        target = self.highlighted_index - self.visible_rows + margin + 1
                        self.scroll_manager.scroll_to(max(0, target))
                        self._emit_scroll_change()
            return True

        # Home - jump to first option (selection happens on Enter/Space)
        elif key == Keys.HOME:
            new_index = 0
            # Skip disabled options if any exist
            if self.disabled_values:
                new_index = self._skip_disabled_options(0, 1)
            self.highlighted_index = new_index
            self._emit_highlight_change(self.highlighted_index)
            self.scroll_manager.scroll_to(0)
            self._emit_scroll_change()
            return True

        # End - jump to last option (selection happens on Enter/Space)
        elif key == Keys.END:
            last = len(self.options) - 1
            new_index = last
            # Skip disabled options if any exist
            if self.disabled_values:
                new_index = self._skip_disabled_options(last, -1)
            self.highlighted_index = new_index
            self._emit_highlight_change(self.highlighted_index)
            target = max(0, self.highlighted_index - self.visible_rows + 1)
            self.scroll_manager.scroll_to(target)
            self._emit_scroll_change()
            return True

        # Page Up (selection happens on Enter/Space)
        elif key == Keys.PAGE_UP:
            self.scroll_manager.page_up()
            self._emit_scroll_change()
            # Move highlighted to top of visible range
            visible_start, _ = self.scroll_manager.get_visible_range()
            if self.disabled_values:
                self.highlighted_index = self._skip_disabled_options(visible_start, 1)
            else:
                self.highlighted_index = visible_start
            self._emit_highlight_change(self.highlighted_index)
            return True

        # Page Down (selection happens on Enter/Space)
        elif key == Keys.PAGE_DOWN:
            self.scroll_manager.page_down()
            self._emit_scroll_change()
            # Move highlighted to bottom of visible range
            _, visible_end = self.scroll_manager.get_visible_range()
            bottom_index = visible_end - 1
            if self.disabled_values:
                self.highlighted_index = self._skip_disabled_options(bottom_index, -1)
            else:
                self.highlighted_index = bottom_index
            self._emit_highlight_change(self.highlighted_index)
            return True

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
        # Scroll wheel - scroll options list
        if event.button == MouseButton.SCROLL_UP:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(-1)
            new_pos = self.scroll_manager.state.scroll_position
            if old_pos != new_pos:
                self._emit_scroll_change()
                return True
            return False

        elif event.button == MouseButton.SCROLL_DOWN:
            old_pos = self.scroll_manager.state.scroll_position
            self.scroll_manager.scroll_by(1)
            new_pos = self.scroll_manager.state.scroll_position
            if old_pos != new_pos:
                self._emit_scroll_change()
                return True
            return False

        # Click events
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

            # Click on an option
            if 0 <= relative_y < self.visible_rows and 0 <= relative_x < self.width:
                visible_start, _ = self.scroll_manager.get_visible_range()
                clicked_index = visible_start + relative_y

                if clicked_index < len(self.options):
                    opt = self.options[clicked_index]
                    # Check if disabled
                    if opt["value"] not in self.disabled_values:
                        old_value = self.value
                        self.value = opt["value"]
                        self.selected_index = clicked_index
                        self.highlighted_index = clicked_index
                        self._emit_change(old_value, self.value)
                        return True
                return True

        return False

    def _emit_change(self, old_value: str | None, new_value: str | None) -> None:
        """Emit change event.

        Parameters
        ----------
        old_value : str or None
            Previous value
        new_value : str or None
            New value
        """
        if self.on_change and old_value != new_value:
            self.on_change(old_value, new_value)

    def _emit_highlight_change(self, new_index: int) -> None:
        """Emit highlight change event.

        Parameters
        ----------
        new_index : int
            New highlighted index
        """
        if self.on_highlight_change:
            self.on_highlight_change(new_index)

    def _emit_scroll_change(self) -> None:
        """Emit scroll position change event."""
        if self.on_scroll:
            self.on_scroll(self.scroll_manager.state.scroll_position)

    def render_to(self, ctx) -> None:
        """Render the select element using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the new cell-based rendering method that uses theme styles
        instead of hardcoded ANSI colors. It renders a scrollable list of options
        with optional borders and title.

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'select': Base select style
        - 'select:focus': Focused select style
        - 'select.border': Border style
        - 'select.border:focus': Focused border style
        - 'select.option': Option item style
        - 'select.option:selected': Selected option style (marked with *)
        - 'select.option:highlighted': Highlighted option style (keyboard focus)
        - 'select.option:disabled': Disabled option style
        - 'select.placeholder': Placeholder text style (empty state)
        """

        # Get visible range from scroll manager
        visible_start, visible_end = self.scroll_manager.get_visible_range()
        visible_options = self.options[visible_start:visible_end]

        # Determine border offset (0 if no borders, 1 if borders)
        border_offset = 1 if self.border_style else 0
        top_row = border_offset  # First content row

        # Render borders if enabled
        if self.border_style:
            border_style = ctx.style_resolver.resolve_style(
                self, "select.border:focus" if self.focused else "select.border"
            )

            # Get border characters for the style
            border_chars = BORDER_CHARS[self.border_style]

            # Draw border around the entire select element
            ctx.draw_border(
                0, 0, ctx.bounds.width, ctx.bounds.height, border_style, border_chars
            )

            # Render title if provided
            if self.title:
                title_style = ctx.style_resolver.resolve_style(self, "select.title")
                title_text = f" {self.title} "
                ctx.write_text(2, 0, title_text, title_style)

        # Render options or placeholder
        if not visible_options:
            # No options - show placeholder
            placeholder_style = ctx.style_resolver.resolve_style(
                self, "select.placeholder"
            )
            empty_text = self.placeholder if not self.options else "No options"

            # Clip to inner width (accounting for borders and padding)
            inner_width = self.width - 2 if self.width > 2 else self.width
            empty_len = visible_length(empty_text)

            if empty_len < inner_width:
                empty_text = empty_text + " " * (inner_width - empty_len)
            else:
                empty_text = clip_to_width(empty_text, inner_width, ellipsis="...")

            # Center the placeholder in the first content row
            x_offset = border_offset + 1  # Account for border and padding
            ctx.write_text(x_offset, top_row, empty_text, placeholder_style)
        else:
            # Render visible options
            for i, opt in enumerate(visible_options):
                option_index = visible_start + i
                row = top_row + i

                is_selected = option_index == self.selected_index
                is_highlighted = option_index == self.highlighted_index
                is_disabled = opt["value"] in self.disabled_values

                # Use custom renderer if provided
                if self.item_renderer:
                    # Custom renderer returns ANSI string - we need to convert it
                    # For now, use default rendering with theme styles
                    self._render_option_to_ctx(
                        ctx,
                        opt,
                        is_selected,
                        is_highlighted,
                        is_disabled,
                        row,
                        border_offset,
                    )
                else:
                    self._render_option_to_ctx(
                        ctx,
                        opt,
                        is_selected,
                        is_highlighted,
                        is_disabled,
                        row,
                        border_offset,
                    )

        # Fill remaining rows with empty space (padding to visible_rows)
        content_height = ctx.bounds.height - (2 * border_offset)
        for row_idx in range(len(visible_options), content_height):
            row = top_row + row_idx
            if row < ctx.bounds.height - border_offset:
                # Fill empty row with base select style
                base_style = ctx.style_resolver.resolve_style(self, "select")
                empty_line = " " * self.width
                x_offset = border_offset
                ctx.write_text(x_offset, row, empty_line, base_style)

    def _render_option_to_ctx(
        self,
        ctx,
        option: dict,
        is_selected: bool,
        is_highlighted: bool,
        is_disabled: bool,
        row: int,
        border_offset: int,
    ) -> None:
        """Render a single option to the context at the specified row.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        option : dict
            Option with 'value' and 'label' keys
        is_selected : bool
            Whether this option is currently selected
        is_highlighted : bool
            Whether this option is highlighted (keyboard focus)
        is_disabled : bool
            Whether this option is disabled
        row : int
            Row index to render at
        border_offset : int
            Offset due to borders (0 or 1)
        """
        label = option["label"]

        # Selection indicator
        indicator = "*" if is_selected else " "

        # Calculate available width for label (1 for indicator, 1 for space, 1 for padding)
        label_width = self.width - 3

        # Clip or pad label
        label_len = visible_length(label)
        if label_len > label_width:
            label = clip_to_width(label, label_width, ellipsis="...")
        else:
            label = label + " " * (label_width - label_len)

        # Determine style based on state
        if is_disabled:
            style = ctx.style_resolver.resolve_style(self, "select.option:disabled")
        elif is_highlighted and self.focused:
            style = ctx.style_resolver.resolve_style(self, "select.option:highlighted")
        elif is_selected:
            # Combine selected style with base option style
            style = ctx.style_resolver.resolve_style(self, "select.option:selected")
        else:
            style = ctx.style_resolver.resolve_style(self, "select.option")

        # Render the option line: " {indicator}{label} "
        x_offset = border_offset
        text = f" {indicator}{label} "
        ctx.write_text(x_offset, row, text, style)

    def _render_option(
        self, option: dict, is_selected: bool, is_highlighted: bool, is_disabled: bool
    ) -> str:
        """Render a single option line.

        Parameters
        ----------
        option : dict
            Option with 'value' and 'label' keys
        is_selected : bool
            Whether this option is currently selected
        is_highlighted : bool
            Whether this option is highlighted (keyboard focus)
        is_disabled : bool
            Whether this option is disabled

        Returns
        -------
        str
            Rendered option line with styling
        """
        label = option["label"]

        # Selection indicator
        indicator = "*" if is_selected else " "

        # Calculate available width for label (1 for indicator, 1 for space, 1 for padding)
        label_width = self.width - 3

        # Clip or pad label
        label_len = visible_length(label)
        if label_len > label_width:
            label = clip_to_width(label, label_width, ellipsis="...")
        else:
            label = label + " " * (label_width - label_len)

        # Apply styling
        if is_disabled:
            # Disabled: dim
            styles = f"{ANSIStyle.RESET}{ANSIStyle.DIM}"
            return f"{styles} {indicator}{label} {ANSIStyle.RESET}"
        elif is_highlighted and self.focused:
            # Highlighted and element is focused: reverse video
            styles = f"{ANSIStyle.RESET}{ANSIStyle.REVERSE}"
            return f"{styles} {indicator}{label} {ANSIStyle.RESET}"
        else:
            # Normal
            return f"{ANSIStyle.RESET} {indicator}{label} {ANSIStyle.RESET}"
