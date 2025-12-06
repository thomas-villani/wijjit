"""Split panel element for resizable two-pane layouts.

This module provides the SplitPanel element which divides space between
two child elements with a draggable divider.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import Container, Element
from wijjit.terminal.ansi import supports_unicode
from wijjit.terminal.cell import get_pooled_cell
from wijjit.terminal.input import Key
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit
    from wijjit.rendering.paint_context import PaintContext


class DividerStyle(Enum):
    """Style for split panel divider."""

    SINGLE = "single"  # Single line (default)
    DOUBLE = "double"  # Double line
    DASHED = "dashed"  # Dashed line
    THICK = "thick"  # Thick/bold line


# Divider characters for each style and orientation
# Format: {style: {orientation: char}}
DIVIDER_CHARS_UNICODE = {
    DividerStyle.SINGLE: {
        "horizontal": "|",  # Vertical line for horizontal split (side-by-side)
        "vertical": "-",  # Horizontal line for vertical split (stacked)
    },
    DividerStyle.DOUBLE: {
        "horizontal": "||",  # Double vertical line
        "vertical": "=",  # Double horizontal line
    },
    DividerStyle.DASHED: {
        "horizontal": ":",  # Dashed vertical
        "vertical": "-",  # Dashed horizontal (rendered with gaps)
    },
    DividerStyle.THICK: {
        "horizontal": "|",  # Thick vertical (styled via attributes)
        "vertical": "-",  # Thick horizontal (styled via attributes)
    },
}

DIVIDER_CHARS_ASCII = {
    DividerStyle.SINGLE: {
        "horizontal": "|",
        "vertical": "-",
    },
    DividerStyle.DOUBLE: {
        "horizontal": "|",
        "vertical": "=",
    },
    DividerStyle.DASHED: {
        "horizontal": ":",
        "vertical": "-",
    },
    DividerStyle.THICK: {
        "horizontal": "|",
        "vertical": "-",
    },
}


def get_divider_char(
    orientation: str, style: DividerStyle = DividerStyle.SINGLE
) -> str:
    """Get divider character for orientation and style.

    Parameters
    ----------
    orientation : str
        "horizontal" or "vertical"
    style : DividerStyle
        Divider style (default: SINGLE)

    Returns
    -------
    str
        Divider character
    """
    if supports_unicode():
        return DIVIDER_CHARS_UNICODE[style][orientation]
    return DIVIDER_CHARS_ASCII[style][orientation]


class SplitPanel(Container):
    """Resizable split panel container.

    A container that divides space between two child elements with a
    draggable divider. Supports horizontal (side-by-side) and vertical
    (stacked) orientations.

    Parameters
    ----------
    orientation : str, optional
        "horizontal" (side-by-side) or "vertical" (stacked).
        Default: "horizontal"
    ratio : str, optional
        Initial size ratio like "50:50" or "30:70". Default: "50:50"
    resizable : bool, optional
        Allow drag-to-resize. Default: True
    min_first : int, optional
        Minimum size for first panel (chars for horizontal, lines for vertical).
        Default: 5
    min_second : int, optional
        Minimum size for second panel. Default: 5
    collapsible : str, optional
        Which panels can collapse: "none", "first", "second", "both".
        Default: "none"
    divider_style : str or DividerStyle, optional
        Style of the divider: "single", "double", "dashed", "thick".
        Default: "single"
    id : str, optional
        Element ID for state binding (ratio persisted to app.state)

    Attributes
    ----------
    orientation : str
        Split direction
    current_ratio : tuple[float, float]
        Current split ratio (first, second), values sum to 1.0
    resizable : bool
        Whether resize is allowed
    min_first : int
        Minimum size for first panel
    min_second : int
        Minimum size for second panel
    collapsible : str
        Collapse mode
    first_collapsed : bool
        Whether first panel is collapsed
    second_collapsed : bool
        Whether second panel is collapsed
    dragging : bool
        Whether divider is being dragged
    divider_hovered : bool
        Whether divider is hovered
    divider_focused : bool
        Whether divider has focus

    Examples
    --------
    Create a horizontal split panel:

    >>> panel = SplitPanel(orientation="horizontal", ratio="30:70")
    >>> panel.set_children(left_frame, right_frame)

    Create a vertical split panel:

    >>> panel = SplitPanel(orientation="vertical", ratio="50:50")
    >>> panel.set_children(top_frame, bottom_frame)
    """

    def __init__(
        self,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        ratio: str = "50:50",
        resizable: bool = True,
        min_first: int = 5,
        min_second: int = 5,
        collapsible: Literal["none", "first", "second", "both"] = "none",
        divider_style: str | DividerStyle = "single",
        id: str | None = None,
    ) -> None:
        super().__init__(id)
        self.orientation = orientation
        self.resizable = resizable
        self.min_first = min_first
        self.min_second = min_second

        # Parse divider style
        if isinstance(divider_style, str):
            style_map = {
                "single": DividerStyle.SINGLE,
                "double": DividerStyle.DOUBLE,
                "dashed": DividerStyle.DASHED,
                "thick": DividerStyle.THICK,
            }
            self.divider_style = style_map.get(divider_style, DividerStyle.SINGLE)
        else:
            self.divider_style = divider_style
        self.collapsible = collapsible

        # Parse initial ratio
        self.default_ratio = self._parse_ratio(ratio)
        self.current_ratio = self.default_ratio

        # Collapse state
        self.first_collapsed = False
        self.second_collapsed = False

        # Drag state
        self.dragging = False
        self.drag_start_pos: int = 0
        self.drag_start_ratio: tuple[float, float] = self.current_ratio

        # Hover and focus state
        self.divider_hovered = False
        self.divider_focused = False

        # Child elements
        self.first_child: Element | None = None
        self.second_child: Element | None = None

        # Calculated layout info (set during layout)
        self._first_size: int = 0
        self._second_size: int = 0
        self._divider_pos: int = 0

        # App reference for state binding
        self._app: Wijjit | None = None

        # Make focusable if resizable (for keyboard navigation)
        self.focusable = resizable

    def _parse_ratio(self, ratio_str: str) -> tuple[float, float]:
        """Parse ratio string to normalized tuple.

        Parameters
        ----------
        ratio_str : str
            Ratio string like "50:50", "30:70", "1:2"

        Returns
        -------
        tuple[float, float]
            Normalized ratio (values sum to 1.0)

        Raises
        ------
        ValueError
            If ratio string is invalid
        """

        parts = ratio_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid ratio format: {ratio_str}")
        first = float(parts[0])
        second = float(parts[1])
        total = first + second
        if total <= 0:
            raise ValueError(f"Invalid ratio values: {ratio_str}")
        return first / total, second / total


    def set_children(self, first: Element, second: Element) -> None:
        """Set the two child elements.

        Parameters
        ----------
        first : Element
            First (left or top) child element
        second : Element
            Second (right or bottom) child element
        """
        self.first_child = first
        self.second_child = second
        self.children = [first, second]

        # Set parent reference on children
        first._parent = self
        second._parent = self

    def set_app(self, app: Wijjit) -> None:
        """Set app reference for state binding.

        Parameters
        ----------
        app : Wijjit
            The application instance
        """
        self._app = app
        self._load_state()

    def _calculate_sizes(self, available: int) -> tuple[int, int, int]:
        """Calculate sizes for each panel and divider position.

        Parameters
        ----------
        available : int
            Available space (width for horizontal, height for vertical)

        Returns
        -------
        tuple[int, int, int]
            (first_size, second_size, divider_pos)
        """
        # Divider takes 1 character
        usable = available - 1

        if self.first_collapsed:
            return (0, usable, 0)
        if self.second_collapsed:
            return (usable, 0, usable)

        # Calculate sizes based on ratio
        first_size = int(usable * self.current_ratio[0])
        second_size = usable - first_size

        # Enforce minimums
        if first_size < self.min_first and not self.first_collapsed:
            first_size = min(self.min_first, usable - self.min_second)
            second_size = usable - first_size
        if second_size < self.min_second and not self.second_collapsed:
            second_size = min(self.min_second, usable - self.min_first)
            first_size = usable - second_size

        divider_pos = first_size

        return (first_size, second_size, divider_pos)

    def _is_on_divider(self, x: int, y: int) -> bool:
        """Check if coordinates are on the divider.

        Parameters
        ----------
        x : int
            X coordinate relative to element bounds
        y : int
            Y coordinate relative to element bounds

        Returns
        -------
        bool
            True if point is on divider
        """
        if not self.bounds:
            return False

        if self.orientation == "horizontal":
            # Divider is a vertical line at divider_pos
            return x == self._divider_pos
        else:
            # Divider is a horizontal line at divider_pos
            return y == self._divider_pos

    def _update_ratio_from_drag(self, event: MouseEvent) -> None:
        """Update ratio based on mouse drag position.

        Parameters
        ----------
        event : MouseEvent
            Mouse event with current position
        """
        if not self.bounds:
            return

        # Get mouse position relative to element
        if self.orientation == "horizontal":
            pos = event.x - self.bounds.x
            available = self.bounds.width - 1  # Subtract divider
        else:
            pos = event.y - self.bounds.y
            available = self.bounds.height - 1

        if available <= 0:
            return

        # Calculate new ratio
        new_first = max(0, min(available, pos))
        new_ratio = (new_first / available, (available - new_first) / available)

        # Check collapse thresholds
        if self.collapsible in ("first", "both"):
            if new_first < self.min_first:
                self.collapse_panel("first")
                return

        if self.collapsible in ("second", "both"):
            if (available - new_first) < self.min_second:
                self.collapse_panel("second")
                return

        # Apply ratio with minimum constraints
        self.current_ratio = self._clamp_ratio(new_ratio, available)

    def _clamp_ratio(
        self, ratio: tuple[float, float], available: int
    ) -> tuple[float, float]:
        """Clamp ratio to respect minimum size constraints.

        Parameters
        ----------
        ratio : tuple[float, float]
            Proposed ratio
        available : int
            Available space

        Returns
        -------
        tuple[float, float]
            Clamped ratio
        """
        if available <= 0:
            return ratio

        first_size = int(available * ratio[0])
        second_size = available - first_size

        # Clamp to minimums
        if first_size < self.min_first:
            first_size = self.min_first
        if second_size < self.min_second:
            first_size = available - self.min_second

        # Ensure we don't go negative
        first_size = max(0, min(available, first_size))
        second_size = available - first_size

        return (first_size / available, second_size / available)

    def _adjust_ratio(self, delta: float) -> None:
        """Adjust ratio by delta (for keyboard resize).

        Parameters
        ----------
        delta : float
            Amount to adjust first panel ratio by (-0.05 to +0.05 typical)
        """
        new_first = max(0.0, min(1.0, self.current_ratio[0] + delta))
        new_second = 1.0 - new_first

        # Calculate available space
        if not self.bounds:
            return

        if self.orientation == "horizontal":
            available = self.bounds.width - 1
        else:
            available = self.bounds.height - 1

        self.current_ratio = self._clamp_ratio((new_first, new_second), available)
        self._sync_state()

    def collapse_panel(self, which: Literal["first", "second"]) -> None:
        """Collapse a panel.

        Parameters
        ----------
        which : str
            "first" or "second" - which panel to collapse
        """
        if which == "first":
            self.first_collapsed = True
            self.current_ratio = (0.0, 1.0)
        else:
            self.second_collapsed = True
            self.current_ratio = (1.0, 0.0)
        self._sync_state()

    def restore_panel(self, which: Literal["first", "second"]) -> None:
        """Restore a collapsed panel.

        Parameters
        ----------
        which : str
            "first" or "second" - which panel to restore
        """
        if which == "first":
            self.first_collapsed = False
        else:
            self.second_collapsed = False
        self.current_ratio = self.default_ratio
        self._sync_state()

    def _sync_state(self) -> None:
        """Persist ratio to app.state if id is set."""
        if self.id and self._app:
            self._app.state[f"{self.id}_ratio"] = self.current_ratio
            self._app.state[f"{self.id}_collapsed"] = (
                self.first_collapsed,
                self.second_collapsed,
            )

    def _load_state(self) -> None:
        """Load ratio from app.state on init."""
        if self.id and self._app:
            if f"{self.id}_ratio" in self._app.state:
                self.current_ratio = self._app.state[f"{self.id}_ratio"]
            if f"{self.id}_collapsed" in self._app.state:
                self.first_collapsed, self.second_collapsed = self._app.state[
                    f"{self.id}_collapsed"
                ]

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get intrinsic size based on children.

        Returns
        -------
        tuple[int, int]
            (width, height) intrinsic size
        """
        first_size = (0, 0)
        second_size = (0, 0)

        if self.first_child:
            first_size = self.first_child.get_intrinsic_size()
        if self.second_child:
            second_size = self.second_child.get_intrinsic_size()

        if self.orientation == "horizontal":
            # Side by side: widths add, heights take max
            width = first_size[0] + second_size[0] + 1  # +1 for divider
            height = max(first_size[1], second_size[1])
        else:
            # Stacked: widths take max, heights add
            width = max(first_size[0], second_size[0])
            height = first_size[1] + second_size[1] + 1  # +1 for divider

        return (width, height)

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for resizing.

        Parameters
        ----------
        key : Key
            The key that was pressed

        Returns
        -------
        bool
            True if key was handled, False otherwise

        Notes
        -----
        Handles the following keys:
        - Ctrl+Left/Right (horizontal): Resize split
        - Ctrl+Up/Down (vertical): Resize split
        - When divider focused: Arrow keys resize without Ctrl
        """
        if not self.resizable:
            return False

        key_name = key.name.lower() if hasattr(key, "name") else str(key).lower()

        # Check for ctrl modifier
        has_ctrl = "ctrl" in key_name or "c-" in key_name

        # Ctrl+Arrow resize
        if has_ctrl:
            if self.orientation == "horizontal":
                if "left" in key_name:
                    self._adjust_ratio(-0.05)
                    return True
                elif "right" in key_name:
                    self._adjust_ratio(0.05)
                    return True
            else:  # vertical
                if "up" in key_name:
                    self._adjust_ratio(-0.05)
                    return True
                elif "down" in key_name:
                    self._adjust_ratio(0.05)
                    return True

        # When divider is focused, plain arrows resize
        if self.divider_focused:
            if self.orientation == "horizontal":
                if key_name == "left":
                    self._adjust_ratio(-0.05)
                    return True
                elif key_name == "right":
                    self._adjust_ratio(0.05)
                    return True
            else:
                if key_name == "up":
                    self._adjust_ratio(-0.05)
                    return True
                elif key_name == "down":
                    self._adjust_ratio(0.05)
                    return True

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse events for divider interaction.

        Parameters
        ----------
        event : MouseEvent
            Mouse event

        Returns
        -------
        bool
            True if event was handled, False otherwise
        """
        if not self.resizable or not self.bounds:
            return False

        # Calculate relative position
        rel_x = event.x - self.bounds.x
        rel_y = event.y - self.bounds.y

        # Handle mouse press on divider (start drag)
        if event.type == MouseEventType.PRESS and event.button == MouseButton.LEFT:
            if self._is_on_divider(rel_x, rel_y):
                self.dragging = True
                if self.orientation == "horizontal":
                    self.drag_start_pos = event.x
                else:
                    self.drag_start_pos = event.y
                self.drag_start_ratio = self.current_ratio
                return True

        # Handle mouse drag (movement with button pressed)
        elif event.type == MouseEventType.DRAG:
            if self.dragging:
                self._update_ratio_from_drag(event)
                return True

        # Handle mouse move (update hover state)
        elif event.type == MouseEventType.MOVE:
            if self.dragging:
                self._update_ratio_from_drag(event)
                return True
            else:
                # Update hover state
                self.divider_hovered = self._is_on_divider(rel_x, rel_y)

        # Handle mouse release (end drag)
        elif event.type == MouseEventType.RELEASE and event.button == MouseButton.LEFT:
            if self.dragging:
                self.dragging = False
                self._sync_state()
                return True

        # Handle double-click to restore default ratio
        elif event.type == MouseEventType.DOUBLE_CLICK:
            if self._is_on_divider(rel_x, rel_y):
                if self.first_collapsed:
                    self.restore_panel("first")
                elif self.second_collapsed:
                    self.restore_panel("second")
                else:
                    self.current_ratio = self.default_ratio
                    self._sync_state()
                return True

        return False

    def on_focus(self) -> None:
        """Called when split panel gains focus."""
        self.focused = True
        self.divider_focused = True

    def on_blur(self) -> None:
        """Called when split panel loses focus."""
        self.focused = False
        self.divider_focused = False

    def on_hover_enter(self) -> None:
        """Called when mouse enters split panel."""
        self.hovered = True

    def on_hover_exit(self) -> None:
        """Called when mouse exits split panel."""
        self.hovered = False
        self.divider_hovered = False

    def render_to(self, ctx: PaintContext) -> None:
        """Render split panel to cell buffer.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Renders:
        1. First child panel
        2. Divider line
        3. Second child panel

        Theme Styles
        ------------
        This element uses the following theme style classes:
        - 'splitpanel.divider': Divider line style
        - 'splitpanel.divider:hover': Divider when hovered
        - 'splitpanel.divider:focus': Divider when focused
        """
        if not self.bounds:
            return

        # Calculate sizes
        if self.orientation == "horizontal":
            available = self.bounds.width
        else:
            available = self.bounds.height

        self._first_size, self._second_size, self._divider_pos = self._calculate_sizes(
            available
        )

        # Resolve divider style from theme
        if self.divider_focused:
            resolved_style = ctx.style_resolver.resolve_style(
                self, "splitpanel.divider:focus"
            )
        elif self.divider_hovered:
            resolved_style = ctx.style_resolver.resolve_style(
                self, "splitpanel.divider:hover"
            )
        else:
            resolved_style = ctx.style_resolver.resolve_style(
                self, "splitpanel.divider"
            )

        divider_attrs = resolved_style.to_cell_attrs()

        # Apply focus color when focused (cyan/bright for visibility)
        if self.divider_focused:
            divider_attrs["fg_color"] = (0, 255, 255)  # Cyan
            divider_attrs["bold"] = True

        divider_char = get_divider_char(self.orientation, self.divider_style)

        # Render divider based on style
        if self.orientation == "horizontal":
            # Vertical divider line
            for y in range(self.bounds.height):
                # For dashed style, alternate between char and space
                if self.divider_style == DividerStyle.DASHED:
                    char = divider_char if y % 2 == 0 else " "
                else:
                    char = divider_char
                ctx.write_cell(
                    self._divider_pos,
                    y,
                    get_pooled_cell(char=char, **divider_attrs),
                )
        else:
            # Horizontal divider line
            for x in range(self.bounds.width):
                # For dashed style, alternate between char and space
                if self.divider_style == DividerStyle.DASHED:
                    char = divider_char if x % 2 == 0 else " "
                else:
                    char = divider_char
                ctx.write_cell(
                    x,
                    self._divider_pos,
                    get_pooled_cell(char=char, **divider_attrs),
                )

        # Note: Child panels are rendered by the layout engine, not here.
        # The layout engine will call render_to on each child with appropriate bounds.

    def get_child_bounds(self) -> list[tuple[Element, int, int, int, int]]:
        """Get bounds for child elements.

        Returns
        -------
        list[tuple[Element, int, int, int, int]]
            List of (element, x, y, width, height) for each child
        """
        if not self.bounds:
            return []

        result = []

        if self.orientation == "horizontal":
            # Side by side
            if self.first_child and not self.first_collapsed:
                result.append(
                    (
                        self.first_child,
                        0,
                        0,
                        self._first_size,
                        self.bounds.height,
                    )
                )
            if self.second_child and not self.second_collapsed:
                result.append(
                    (
                        self.second_child,
                        self._divider_pos + 1,
                        0,
                        self._second_size,
                        self.bounds.height,
                    )
                )
        else:
            # Stacked
            if self.first_child and not self.first_collapsed:
                result.append(
                    (
                        self.first_child,
                        0,
                        0,
                        self.bounds.width,
                        self._first_size,
                    )
                )
            if self.second_child and not self.second_collapsed:
                result.append(
                    (
                        self.second_child,
                        0,
                        self._divider_pos + 1,
                        self.bounds.width,
                        self._second_size,
                    )
                )

        return result

    def get_ephemeral_state(self) -> dict[str, Any]:
        """Get ephemeral state for reconciliation.

        Returns
        -------
        dict
            State that should survive re-renders
        """
        return {
            "_ratio": self.current_ratio,
            "_first_collapsed": self.first_collapsed,
            "_second_collapsed": self.second_collapsed,
        }

    def restore_ephemeral_state(self, state: dict[str, Any]) -> None:
        """Restore ephemeral state after reconciliation.

        Parameters
        ----------
        state : dict
            State from get_ephemeral_state()
        """
        if "_ratio" in state:
            self.current_ratio = state["_ratio"]
        if "_first_collapsed" in state:
            self.first_collapsed = state["_first_collapsed"]
        if "_second_collapsed" in state:
            self.second_collapsed = state["_second_collapsed"]
