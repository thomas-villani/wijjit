"""Split panel element for resizable two-pane layouts.

This module provides the SplitPanel element which divides space between
two child elements with a draggable divider.
"""

from __future__ import annotations

import math
import weakref
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from wijjit.elements.base import Container, Element
from wijjit.logging_config import get_logger
from wijjit.terminal.ansi import supports_unicode
from wijjit.terminal.cell import get_pooled_cell
from wijjit.terminal.input import Key
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit
    from wijjit.rendering.paint_context import PaintContext


logger = get_logger(__name__)

#: Slack added before flooring ``usable * ratio`` to a cell count. A ratio
#: stored as ``k / usable`` can multiply back to just under ``k`` in floating
#: point (22 * (15 / 22) == 14.999...), which would lose a cell on every
#: round trip; the epsilon is far below one cell yet far above float error.
_RATIO_EPSILON = 1e-9

#: Fraction of the usable size one keyboard resize step moves the divider.
_KEY_STEP_FRACTION = 0.05


def _ratio_to_cells(usable: int, fraction: float) -> int:
    """Convert a ratio share to a whole number of cells in ``[0, usable]``.

    Parameters
    ----------
    usable : int
        Space to split, excluding the divider.
    fraction : float
        The first pane's share, normally in ``[0, 1]``.

    Returns
    -------
    int
        ``floor(usable * fraction)``, exact for any ratio built as
        ``cells / usable``.
    """
    return max(0, min(usable, math.floor(usable * fraction + _RATIO_EPSILON)))


def _valid_ratio(value: Any) -> tuple[float, float] | None:
    """Validate a persisted split ratio.

    Parameters
    ----------
    value : Any
        The value found in app state.

    Returns
    -------
    tuple of float or None
        ``(first, second)`` when ``value`` is a two-item sequence of real
        numbers, each in ``[0, 1]``, summing to 1 (within float error);
        otherwise None.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    if len(value) != 2:
        return None
    first, second = value
    for part in (first, second):
        if isinstance(part, bool) or not isinstance(part, (int, float)):
            return None
        if not math.isfinite(part) or not 0.0 <= part <= 1.0:
            return None
    if abs(first + second - 1.0) > 1e-6:
        return None
    return (float(first), float(second))


def _valid_collapsed(value: Any) -> tuple[bool, bool] | None:
    """Validate a persisted ``(first_collapsed, second_collapsed)`` pair.

    Parameters
    ----------
    value : Any
        The value found in app state.

    Returns
    -------
    tuple of bool or None
        The pair when ``value`` is a two-item sequence of bools, else None.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    if len(value) != 2 or not all(isinstance(v, bool) for v in value):
        return None
    return (value[0], value[1])


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

        # App reference for state binding. Held weakly (like parent_frame) so a
        # SplitPanel does not keep the whole application alive - the app owns the
        # element tree, so a strong ref back would be a cycle.
        self._app_ref: weakref.ref[Wijjit] | None = None

        # Make focusable if resizable (for keyboard navigation)
        self.focusable = resizable

    @property
    def _app(self) -> Wijjit | None:
        """The bound application, or None if unset or already collected."""
        if self._app_ref is None:
            return None
        return self._app_ref()

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
        first._parent = self  # type: ignore[attr-defined]
        second._parent = self  # type: ignore[attr-defined]

    def set_app(self, app: Wijjit) -> None:
        """Set app reference for state binding.

        Parameters
        ----------
        app : Wijjit
            The application instance
        """
        self._app_ref = weakref.ref(app)
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

        # Too little room for even the divider: nothing to split.
        if usable <= 0:
            return (0, 0, 0)

        if self.first_collapsed:
            return (0, usable, 0)
        if self.second_collapsed:
            return (usable, 0, usable)

        # Calculate sizes based on ratio
        first_size = _ratio_to_cells(usable, self.current_ratio[0])
        second_size = usable - first_size

        # Enforce minimums
        if first_size < self.min_first and not self.first_collapsed:
            first_size = min(self.min_first, usable - self.min_second)
            second_size = usable - first_size
        if second_size < self.min_second and not self.second_collapsed:
            second_size = min(self.min_second, usable - self.min_first)
            first_size = usable - second_size

        # When both minimums cannot fit (min_first + min_second > usable) the
        # steps above can drive a size negative. Clamp into [0, usable] and
        # derive the other pane so the two always sum to usable and neither is
        # negative - a best-effort split when there is simply not enough room.
        first_size = max(0, min(first_size, usable))
        second_size = usable - first_size

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

        # The divider goes where the mouse is: pos cells of first pane
        new_first = max(0, min(available, pos))

        # Check collapse thresholds
        if self.collapsible in ("first", "both"):
            if new_first < self.min_first:
                self.collapse_panel("first")
                return

        if self.collapsible in ("second", "both"):
            if (available - new_first) < self.min_second:
                self.collapse_panel("second")
                return

        # Apply with minimum constraints
        self._set_first_cells(new_first, available)

    def _clamp_first_cells(self, first_size: int, available: int) -> int:
        """Clamp a first-pane size to the minimum size constraints.

        Parameters
        ----------
        first_size : int
            Proposed first-pane size in cells.
        available : int
            Usable space (excluding the divider).

        Returns
        -------
        int
            The clamped size, in ``[0, available]``. When both minimums
            cannot fit, the second pane's minimum wins.
        """
        if first_size < self.min_first:
            first_size = self.min_first
        if available - first_size < self.min_second:
            first_size = available - self.min_second
        return max(0, min(available, first_size))

    def _set_first_cells(self, first_size: int, available: int) -> None:
        """Place the divider after ``first_size`` cells of usable space.

        Parameters
        ----------
        first_size : int
            Desired first-pane size in cells (clamped to the minimums).
        available : int
            Usable space (excluding the divider).

        Notes
        -----
        The ratio is stored as ``cells / available``, which
        ``_calculate_sizes`` converts back to exactly the same cell count.
        """
        if available <= 0:
            return
        first_size = self._clamp_first_cells(first_size, available)
        self.current_ratio = (
            first_size / available,
            (available - first_size) / available,
        )

    def _step_divider(self, direction: int) -> None:
        """Move the divider one keyboard step (for keyboard resize).

        Parameters
        ----------
        direction : int
            ``+1`` grows the first pane, ``-1`` shrinks it.

        Notes
        -----
        A step is a whole number of cells - about 5% of the usable size,
        and never less than one - added to the divider's current on-screen
        position. Stepping one way and then back returns exactly to the
        starting position unless a minimum size clamped the move.
        """
        if not self.bounds:
            return

        if self.orientation == "horizontal":
            total = self.bounds.width
        else:
            total = self.bounds.height
        available = total - 1
        if available <= 0:
            return

        current, _, _ = self._calculate_sizes(total)
        step = max(1, math.floor(available * _KEY_STEP_FRACTION + 0.5))
        self._set_first_cells(current + direction * step, available)
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
        app = self._app
        if self.id and app:
            app.state[f"{self.id}_ratio"] = self.current_ratio
            app.state[f"{self.id}_collapsed"] = (
                self.first_collapsed,
                self.second_collapsed,
            )

    def _load_state(self) -> None:
        """Load ratio and collapse state from app.state on init.

        Values are validated against the shapes ``_sync_state`` writes - a
        ``(first, second)`` pair of numbers in [0, 1] summing to 1, and a
        pair of bools. Anything else (a ``"30:70"`` string, out-of-range
        numbers, None) is ignored with a warning and the current value is
        kept.
        """
        app = self._app
        if self.id and app:
            ratio_key = f"{self.id}_ratio"
            if ratio_key in app.state:
                ratio = _valid_ratio(app.state[ratio_key])
                if ratio is None:
                    logger.warning(
                        "Ignoring invalid split ratio %r in app.state[%r]",
                        app.state[ratio_key],
                        ratio_key,
                    )
                else:
                    self.current_ratio = ratio
            collapsed_key = f"{self.id}_collapsed"
            if collapsed_key in app.state:
                collapsed = _valid_collapsed(app.state[collapsed_key])
                if collapsed is None:
                    logger.warning(
                        "Ignoring invalid collapse state %r in app.state[%r]",
                        app.state[collapsed_key],
                        collapsed_key,
                    )
                else:
                    self.first_collapsed, self.second_collapsed = collapsed

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
                    self._step_divider(-1)
                    return True
                elif "right" in key_name:
                    self._step_divider(1)
                    return True
            else:  # vertical
                if "up" in key_name:
                    self._step_divider(-1)
                    return True
                elif "down" in key_name:
                    self._step_divider(1)
                    return True

        # When divider is focused, plain arrows resize
        if self.divider_focused:
            if self.orientation == "horizontal":
                if key_name == "left":
                    self._step_divider(-1)
                    return True
                elif key_name == "right":
                    self._step_divider(1)
                    return True
            else:
                if key_name == "up":
                    self._step_divider(-1)
                    return True
                elif key_name == "down":
                    self._step_divider(1)
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

        Theme styles:

        This element uses the following theme style classes:
        - ``splitpanel.divider``: Divider line style
        - ``splitpanel.divider:hover``: Divider when hovered
        - ``splitpanel.divider:focus``: Divider when focused
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
