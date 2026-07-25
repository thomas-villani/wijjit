"""Layout engine for calculating positions and sizes of UI elements.

This module provides a two-pass layout system:
1. Bottom-up: Calculate minimum/preferred sizes from children
2. Top-down: Assign absolute positions based on available space

The layout system supports:
- Fixed sizes (width=20)
- Percentage sizes (width="50%")
- Fill behavior (width="fill")
- Auto sizing (based on content)
- Stacking (vertical and horizontal)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from wijjit.elements.base import Element
from wijjit.layout.bounds import Bounds, Size, parse_margin, parse_size
from wijjit.layout.frames import Frame
from wijjit.layout.splitpanel import SplitPanel
from wijjit.logging_config import get_logger

# Module logger
logger = get_logger(__name__)


# Type aliases for alignment options
HAlign = Literal["left", "center", "right", "stretch"]
VAlign = Literal["top", "middle", "bottom", "stretch"]

# Type alias for justify-content options (flexbox-style)
JustifyContent = Literal[
    "flex-start",
    "flex-end",
    "center",
    "space-between",
    "space-around",
    "space-evenly",
    "left",
    "right",  # Aliases for flex-start/flex-end
]


# How far auto-fit may compress a leaf element. Elements clip or scroll their
# own content, so an over-committed row is better served by squeezing two
# widgets than by letting the second run off the screen entirely. These match
# the "reasonable minimum for visibility" figures ElementNode already uses for
# dynamically sized elements.
ELEMENT_MIN_VISIBLE_WIDTH = 10
ELEMENT_MIN_VISIBLE_HEIGHT = 5

# Whether over-committed fixed sizes are shrunk to fit their parent. Set from
# the ``AUTO_FIT_LAYOUT`` config key at app construction, mirroring how
# ``UNICODE_SUPPORT`` reaches ``wijjit.terminal.ansi.set_unicode_mode``. Layout
# is a leaf layer with no handle on the app, so the value is pushed in.
_auto_fit_enabled: bool = True


def set_auto_fit(enabled: bool) -> None:
    """Enable or disable auto-fit shrinking for over-committed layouts.

    Parameters
    ----------
    enabled : bool
        When True (the default), a container whose children ask for more space
        than the container was given shrinks those children to fit rather than
        letting them overflow and clip. See :func:`shrink_to_fit`.
    """
    global _auto_fit_enabled
    _auto_fit_enabled = enabled


def auto_fit_enabled() -> bool:
    """Return whether auto-fit shrinking is currently enabled.

    Returns
    -------
    bool
        True if over-committed layouts shrink to fit.
    """
    return _auto_fit_enabled


def shrink_to_fit(
    requested: list[int], minimums: list[int], available: int
) -> list[int]:
    """Scale over-committed sizes down proportionally, floored at minimums.

    This is the CSS flexbox ``flex-shrink`` rule reduced to what Wijjit needs:
    when the children of a stack collectively ask for more room than the stack
    has, every child that has slack gives space back in proportion to how much
    slack it has, so a rigid child is not squeezed while a roomy sibling keeps
    its surplus.

    Parameters
    ----------
    requested : list of int
        The size each child asked for, in child order.
    minimums : list of int
        The floor for each child - the size below which it must not be shrunk
        (typically ``constraints.content_min_width`` / ``content_min_height``).
    available : int
        Total space the children must fit into, gaps already deducted.

    Returns
    -------
    list of int
        Sizes summing to at most ``available``, or ``requested`` unchanged when
        it already fits, when auto-fit is disabled, or when no child has slack.

    Notes
    -----
    If the minimums alone exceed ``available`` the result still overflows: the
    layout is genuinely too small and clipping is the only remaining option.
    """
    if not requested:
        return []
    total = sum(requested)
    overflow = total - available
    if overflow <= 0 or not _auto_fit_enabled:
        return list(requested)

    # Slack is what each child can give up before hitting its content floor.
    slack = [max(0, r - m) for r, m in zip(requested, minimums, strict=True)]
    total_slack = sum(slack)
    if total_slack <= 0:
        return list(requested)

    # Never claw back more than the children can actually give.
    to_reclaim = min(overflow, total_slack)
    cuts = [(to_reclaim * s) // total_slack for s in slack]

    # Integer division leaves a remainder; hand it to the children that still
    # have slack left, largest slack first, so the result sums exactly.
    leftover = to_reclaim - sum(cuts)
    if leftover:
        order = sorted(
            range(len(slack)), key=lambda i: slack[i] - cuts[i], reverse=True
        )
        for i in order:
            if leftover <= 0:
                break
            room = slack[i] - cuts[i]
            if room <= 0:
                continue
            take = min(room, leftover)
            cuts[i] += take
            leftover -= take

    return [r - c for r, c in zip(requested, cuts, strict=True)]


def _content_min_width(node: "LayoutNode") -> int:
    """Return a node's auto-fit width floor.

    Parameters
    ----------
    node : LayoutNode
        The node to inspect.

    Returns
    -------
    int
        ``constraints.content_min_width`` when constraints have been calculated,
        otherwise 0 (an uncalculated node imposes no floor).
    """
    if node.constraints is None:
        return 0
    return node.constraints.content_min_width or 0


def _content_min_height(node: "LayoutNode") -> int:
    """Return a node's auto-fit height floor.

    Parameters
    ----------
    node : LayoutNode
        The node to inspect.

    Returns
    -------
    int
        ``constraints.content_min_height`` when constraints have been
        calculated, otherwise 0.
    """
    if node.constraints is None:
        return 0
    return node.constraints.content_min_height or 0


def _distribute_fill(total: int, count: int) -> list[int]:
    """Split ``total`` into ``count`` near-equal parts, remainder to the front.

    ``fill`` distribution used to be ``total // count`` for every child, which
    discards the remainder, so ``count`` fill children under-filled their
    container by up to ``count - 1`` cells. Spread the leftover onto the leading
    children so every available cell is consumed - the same thing
    ``HStack._distribute_space`` already does for justify gaps.

    Parameters
    ----------
    total : int
        Total space to distribute.
    count : int
        Number of fill children.

    Returns
    -------
    list of int
        Per-child sizes summing to ``total`` (empty when ``count <= 0``).
    """
    if count <= 0:
        return []
    base, remainder = divmod(total, count)
    return [base + (1 if i < remainder else 0) for i in range(count)]


@dataclass
class SizeConstraints:
    """Size constraints for layout calculation.

    Parameters
    ----------
    min_width : int
        Minimum width required
    min_height : int
        Minimum height required
    preferred_width : int, optional
        Preferred width (default: min_width)
    preferred_height : int, optional
        Preferred height (default: min_height)
    content_min_width : int, optional
        Width below which the node's *content* cannot be shown, ignoring any
        explicit fixed ``width`` spec (default: ``min_width``).
    content_min_height : int, optional
        Height below which the node's *content* cannot be shown, ignoring any
        explicit fixed ``height`` spec (default: ``min_height``).

    Attributes
    ----------
    min_width : int
        Minimum width required
    min_height : int
        Minimum height required
    preferred_width : int
        Preferred width
    preferred_height : int
        Preferred height
    content_min_width : int
        Natural content minimum width (the auto-fit shrink floor)
    content_min_height : int
        Natural content minimum height (the auto-fit shrink floor)

    Notes
    -----
    A node with a fixed ``width``/``height`` spec reports that value as both
    ``min_*`` and ``preferred_*``, which makes it look incompressible. The
    ``content_min_*`` pair records what the node would need if the author had
    not pinned a size, and is what auto-fit (see :func:`shrink_to_fit`) uses as
    the floor when it has to claw back over-committed space.
    """

    min_width: int
    min_height: int
    preferred_width: int | None = None
    preferred_height: int | None = None
    content_min_width: int | None = None
    content_min_height: int | None = None

    def __post_init__(self) -> None:
        """Set preferred and content-minimum sizes to min sizes if not given."""
        if self.preferred_width is None:
            self.preferred_width = self.min_width
        if self.preferred_height is None:
            self.preferred_height = self.min_height
        if self.content_min_width is None:
            self.content_min_width = self.min_width
        if self.content_min_height is None:
            self.content_min_height = self.min_height


@dataclass
class LayoutRow:
    """Represents a single row in a wrapped HStack layout.

    Used internally by HStack when wrap=True to track which children
    are in each row and their collective dimensions.

    Attributes
    ----------
    children : list of LayoutNode
        Child nodes in this row
    total_width : int
        Sum of children widths in this row (excluding gaps)
    max_height : int
        Maximum height among children in this row
    """

    children: list["LayoutNode"]
    total_width: int
    max_height: int


class LayoutNode(ABC):
    """Base class for layout tree nodes.

    A layout node can be either a container (with children) or a leaf
    (wrapping an Element).

    Parameters
    ----------
    width : int, str, or Size, optional
        Width specification (default: "auto")
    height : int, str, or Size, optional
        Height specification (default: "auto")
    id : str, optional
        Node identifier

    Attributes
    ----------
    width_spec : Size
        Width specification
    height_spec : Size
        Height specification
    id : str or None
        Node identifier
    constraints : SizeConstraints or None
        Calculated size constraints
    bounds : Bounds or None
        Assigned position and size
    """

    def __init__(
        self,
        width: int | str | Size = "auto",
        height: int | str | Size = "auto",
        id: str | None = None,
    ) -> None:
        self.width_spec = parse_size(width)
        self.height_spec = parse_size(height)
        self.id = id
        self.constraints: SizeConstraints | None = None
        self.bounds: Bounds | None = None

    @abstractmethod
    def calculate_constraints(self) -> SizeConstraints:
        """Calculate size constraints (bottom-up pass).

        Returns
        -------
        SizeConstraints
            Calculated constraints
        """
        pass

    @abstractmethod
    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign absolute position and size (top-down pass).

        Parameters
        ----------
        x : int
            X position
        y : int
            Y position
        width : int
            Assigned width
        height : int
            Assigned height
        """
        pass

    def get_height_for_width(self, width: int) -> int:
        """Return the height this node needs when laid out at ``width``.

        The bottom-up constraint pass has to guess a height before any width is
        known, which is wrong for anything whose height depends on its width.
        Wrapped text is the case that bites: a long line measures as one row,
        is allocated one row, and paints its continuation lines over whichever
        sibling was laid out beneath it. Containers call this on the way down,
        once a child's width is settled, to correct the guess.

        Parameters
        ----------
        width : int
            The width this node will be laid out at.

        Returns
        -------
        int
            Required height. The default reports the constraint-pass value,
            which is correct for every node whose height is width-independent.
        """
        if self.height_spec.is_fixed:
            return int(self.height_spec.value)
        return self.constraints.preferred_height if self.constraints else 1

    @abstractmethod
    def collect_elements(self) -> list[Element]:
        """Collect all Element objects in this subtree.

        Returns
        -------
        list of Element
            All elements in the subtree
        """
        pass


class ElementNode(LayoutNode):
    """Layout node wrapping a single Element.

    Parameters
    ----------
    element : Element
        The element to wrap
    width : int, str, or Size, optional
        Width specification (default: "auto")
    height : int, str, or Size, optional
        Height specification (default: "auto")

    Attributes
    ----------
    element : Element
        The wrapped element
    """

    def __init__(
        self,
        element: Element,
        width: int | str | Size = "auto",
        height: int | str | Size = "auto",
    ) -> None:
        super().__init__(width, height, id=element.id)
        self.element = element

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate size constraints based on element content.

        For now, uses simple heuristics. Elements can override this
        by providing their own size hints.

        Returns
        -------
        SizeConstraints
            Calculated constraints
        """
        # Check if element supports dynamic sizing
        # Dynamic sizing elements use minimal constraints to avoid inflating parent
        supports_dynamic_sizing = self.element.supports_dynamic_sizing

        # Apply width/height specs if fixed
        if self.width_spec.is_fixed:
            min_width = self.width_spec.value
            preferred_width = self.width_spec.value
        elif supports_dynamic_sizing and self.width_spec.is_fill:
            # Dynamic sizing elements report minimal constraints to avoid inflating parent
            # They will expand to fill when space is available via assign_bounds
            min_width = ELEMENT_MIN_VISIBLE_WIDTH
            # Keep preferred same as min to avoid inflating parent
            preferred_width = ELEMENT_MIN_VISIBLE_WIDTH
        else:
            # Auto or other - get intrinsic size from element
            content_width, _ = self.element.get_intrinsic_size()
            min_width = content_width
            preferred_width = content_width

        if self.height_spec.is_fixed:
            min_height = self.height_spec.value
            preferred_height = self.height_spec.value
        elif supports_dynamic_sizing and self.height_spec.is_fill:
            # Dynamic sizing elements report minimal constraints to avoid inflating parent
            # They will expand to fill when space is available via assign_bounds
            min_height = ELEMENT_MIN_VISIBLE_HEIGHT
            # Keep preferred same as min to avoid inflating parent
            preferred_height = ELEMENT_MIN_VISIBLE_HEIGHT
        else:
            # Auto or other - get intrinsic size from element
            _, content_height = self.element.get_intrinsic_size()
            min_height = content_height
            preferred_height = content_height

        # An element's requested size is not a hard floor for auto-fit: elements
        # clip or scroll their own content, so under space pressure a squeezed
        # widget still shows something, whereas an unshrunk one is pushed off the
        # screen entirely. Never raise the floor above what was asked for.
        content_min_width = min(min_width, ELEMENT_MIN_VISIBLE_WIDTH)
        content_min_height = min(min_height, ELEMENT_MIN_VISIBLE_HEIGHT)

        self.constraints = SizeConstraints(
            min_width=min_width,
            min_height=min_height,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            content_min_width=content_min_width,
            content_min_height=content_min_height,
        )
        return self.constraints

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign bounds to this node and its element.

        Parameters
        ----------
        x : int
            X position
        y : int
            Y position
        width : int
            Assigned width
        height : int
            Assigned height
        """
        self.bounds = Bounds(x=x, y=y, width=width, height=height)
        self.element.set_bounds(self.bounds)

    def get_height_for_width(self, width: int) -> int:
        """Re-measure the wrapped element against its settled width.

        Parameters
        ----------
        width : int
            The width this node will be laid out at.

        Returns
        -------
        int
            Rows the element needs at ``width``.
        """
        if self.height_spec.is_fixed:
            return int(self.height_spec.value)
        if width <= 0:
            return super().get_height_for_width(width)
        return max(1, self.element.get_height_for_width(width))

    def collect_elements(self) -> list[Element]:
        """Return the wrapped element and any nested children.

        Returns
        -------
        list of Element
            List containing the element and any nested children it contains

        Notes
        -----
        If the element has a `collect_child_elements()` method (e.g., TabbedPanel),
        those nested elements are also included for focus/mouse event routing.
        """
        elements = [self.element]
        # Check if element has nested children (e.g., TabbedPanel with tab content)
        if hasattr(self.element, "collect_child_elements"):
            elements.extend(self.element.collect_child_elements())
        return elements


class Container(LayoutNode):
    """Base container class for layout nodes with children.

    Parameters
    ----------
    children : list of LayoutNode, optional
        Child nodes
    width : int, str, or Size, optional
        Width specification (default: "auto")
    height : int, str, or Size, optional
        Height specification (default: "auto")
    spacing : int, optional
        Spacing between children (default: 0)
    padding : int, optional
        Padding around children (default: 0)
    margin : int or tuple of int, optional
        Margin around container. If int, applies uniformly to all sides.
        If tuple, specifies (top, right, bottom, left) margins. (default: 0)
    align_h : {"left", "center", "right", "stretch"}, optional
        Horizontal alignment of children (default: "stretch")
    align_v : {"top", "middle", "bottom", "stretch"}, optional
        Vertical alignment of children (default: "stretch")
    id : str, optional
        Node identifier

    Attributes
    ----------
    children : list of LayoutNode
        Child nodes
    spacing : int
        Spacing between children
    padding : int
        Padding around children
    margin : tuple of int
        Margin (top, right, bottom, left)
    align_h : str
        Horizontal alignment
    align_v : str
        Vertical alignment
    """

    def __init__(
        self,
        children: list[LayoutNode] | None = None,
        width: int | str | Size = "auto",
        height: int | str | Size = "auto",
        spacing: int = 0,
        padding: int | tuple[int, int, int, int] = 0,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: str | None = None,
    ) -> None:
        super().__init__(width, height, id)
        self.children = children or []
        self.spacing = spacing
        # Normalize padding to a 4-tuple (top, right, bottom, left) so directional
        # padding (e.g. ``padding_left=2`` from a tag) is honored per-side instead
        # of being mis-applied as a uniform scalar (or crashing the geometry math).
        self.padding = parse_margin(padding)
        self.margin = parse_margin(margin)
        self.align_h = align_h
        self.align_v = align_v
        # Axes on which auto-fit must not shrink children. A scrollable frame
        # sets these on its content container: overflow on the scrolling axis is
        # the entire point of a viewport, so squeezing the content to fit would
        # leave nothing to scroll.
        self.no_shrink_width = False
        self.no_shrink_height = False

    def add_child(self, child: LayoutNode) -> None:
        """Add a child node.

        Parameters
        ----------
        child : LayoutNode
            Child node to add
        """
        self.children.append(child)

    def collect_elements(self) -> list[Element]:
        """Collect all elements from children.

        Returns
        -------
        list of Element
            All elements in the subtree
        """
        elements = []
        for child in self.children:
            elements.extend(child.collect_elements())
        return elements


class VStack(Container):
    """Vertical stacking container.

    Arranges children vertically with optional spacing.

    Parameters
    ----------
    children : list of LayoutNode, optional
        Child nodes
    width : int, str, or Size, optional
        Width specification (default: "fill")
    height : int, str, or Size, optional
        Height specification (default: "fill")
    spacing : int, optional
        Spacing between children (default: 0)
    padding : int, optional
        Padding around children (default: 0)
    margin : int or tuple of int, optional
        Margin around container (default: 0)
    align_h : {"left", "center", "right", "stretch"}, optional
        Horizontal alignment of children (default: "stretch")
    align_v : {"top", "middle", "bottom", "stretch"}, optional
        Vertical alignment of children (default: "stretch")
    id : str, optional
        Node identifier
    """

    def __init__(
        self,
        children: list[LayoutNode] | None = None,
        width: int | str | Size = "fill",
        height: int | str | Size = "fill",
        spacing: int = 0,
        padding: int | tuple[int, int, int, int] = 0,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: str | None = None,
    ) -> None:
        super().__init__(
            children, width, height, spacing, padding, margin, align_h, align_v, id
        )

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate constraints for vertical stack.

        Width is the maximum of children widths.
        Height is the sum of children heights plus spacing.

        Returns
        -------
        SizeConstraints
            Calculated constraints
        """
        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.padding
        pad_w = pad_left + pad_right
        pad_h = pad_top + pad_bottom

        if not self.children:
            # Empty container
            self.constraints = SizeConstraints(
                min_width=pad_w + margin_left + margin_right,
                min_height=pad_h + margin_top + margin_bottom,
                preferred_width=pad_w + margin_left + margin_right,
                preferred_height=pad_h + margin_top + margin_bottom,
            )
            return self.constraints

        # Calculate children constraints first
        child_constraints = [child.calculate_constraints() for child in self.children]

        # Width: max of children
        max_child_width = max(c.preferred_width for c in child_constraints)
        # The auto-fit floor must be built from the children's own floors, not
        # their preferred sizes - otherwise one nested fixed-width widget makes
        # the whole column look incompressible.
        max_child_content_min = max(c.content_min_width or 0 for c in child_constraints)

        # Height: sum of children plus spacing
        # For children with height=fill, use min_height instead of preferred_height
        # to avoid inflating the parent
        total_height = 0
        total_content_min_height = 0
        for i, child in enumerate(self.children):
            constraint = child_constraints[i]
            if child.height_spec.is_fill:
                # Fill children contribute only their minimum
                total_height += constraint.min_height
            else:
                # Fixed/auto children contribute their preferred size
                total_height += constraint.preferred_height
            total_content_min_height += constraint.content_min_height or 0
        total_height += self.spacing * (len(self.children) - 1)
        total_content_min_height += self.spacing * (len(self.children) - 1)

        # Add padding and margins
        min_width = max_child_width + pad_w + margin_left + margin_right
        min_height = total_height + pad_h + margin_top + margin_bottom

        # What the stack needs before any explicit size spec is applied. Auto-fit
        # shrinks toward these, not toward a pinned width/height.
        content_min_width = max_child_content_min + pad_w + margin_left + margin_right
        content_min_height = (
            total_content_min_height + pad_h + margin_top + margin_bottom
        )

        # Apply width/height specs if fixed
        if self.width_spec.is_fixed:
            min_width = self.width_spec.value
            preferred_width = self.width_spec.value
            content_min_width = min(content_min_width, min_width)
        else:
            preferred_width = min_width

        if self.height_spec.is_fixed:
            min_height = self.height_spec.value
            preferred_height = self.height_spec.value
            content_min_height = min(content_min_height, min_height)
        else:
            preferred_height = min_height

        self.constraints = SizeConstraints(
            min_width=min_width,
            min_height=min_height,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            content_min_width=content_min_width,
            content_min_height=content_min_height,
        )
        return self.constraints

    def _resolve_child_width(self, child: LayoutNode, content_width: int) -> int:
        """Resolve one child's width within this column.

        Parameters
        ----------
        child : LayoutNode
            The child to size.
        content_width : int
            Width available inside this stack's padding and margins.

        Returns
        -------
        int
            The child's width.

        Notes
        -----
        ``align_h="stretch"`` affects the *positioning* of a narrower child, not
        whether an auto-width child is stretched. Only ``fill`` children stretch.
        """
        if child.width_spec.is_fixed:
            # Respect the child's explicit fixed width, but never let it exceed
            # the column: a pinned width wider than the terminal would otherwise
            # overflow and clip. Size.calculate() applies the same min() for
            # fixed sizes; auto-fit extends it to the stacks.
            child_width = child.width_spec.value
            if auto_fit_enabled() and not self.no_shrink_width:
                child_width = max(min(child_width, content_width), 0)
            return child_width
        if child.width_spec.is_fill:
            return content_width
        if child.width_spec.is_percentage:
            return int(content_width * child.width_spec.get_percentage())
        # Auto - intrinsic size from constraints, clamped to what is available.
        child_width = (
            child.constraints.preferred_width if child.constraints else content_width
        )
        return min(child_width, content_width)

    def _requested_height(
        self, child: LayoutNode, child_width: int, content_height: int
    ) -> int:
        """Resolve the height one non-fill child asks for at ``child_width``.

        Parameters
        ----------
        child : LayoutNode
            The child to measure.
        child_width : int
            The width the child has already been assigned.
        content_height : int
            Height available for children, spacing already deducted.

        Returns
        -------
        int
            Rows the child wants.

        Notes
        -----
        An auto-height leaf is re-measured against its resolved width. The
        bottom-up constraint pass could not do this - it runs before any width
        is known - so a wrapping line was measured as a single row, allocated a
        single row, and then painted its continuation lines over the sibling
        laid out beneath it.
        """
        if child.height_spec.is_fixed:
            return int(child.height_spec.value)
        if child.height_spec.is_percentage:
            return int(content_height * child.height_spec.get_percentage())
        return child.get_height_for_width(child_width)

    def get_height_for_width(self, width: int) -> int:
        """Sum the children's heights at the widths this column would give them.

        Parameters
        ----------
        width : int
            The width this stack will be laid out at.

        Returns
        -------
        int
            Rows the column needs, including spacing, padding and margins.
        """
        if self.height_spec.is_fixed:
            return int(self.height_spec.value)
        if not self.children or width <= 0:
            return super().get_height_for_width(width)

        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.padding
        content_width = width - pad_left - pad_right - margin_left - margin_right

        total = 0
        for child in self.children:
            if child.height_spec.is_fill or child.height_spec.is_percentage:
                # Neither can be resolved without knowing the height on offer,
                # which is what this call is trying to establish. Fall back to
                # the constraint-pass figure.
                total += child.constraints.min_height if child.constraints else 0
                continue
            total += child.get_height_for_width(
                self._resolve_child_width(child, content_width)
            )

        total += self.spacing * (len(self.children) - 1)
        return total + pad_top + pad_bottom + margin_top + margin_bottom

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign bounds to container and position children vertically.

        Parameters
        ----------
        x : int
            X position
        y : int
            Y position
        width : int
            Assigned width
        height : int
            Assigned height
        """
        self.bounds = Bounds(x=x, y=y, width=width, height=height)

        if not self.children:
            return

        # Apply margins
        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.padding

        # Calculate available space for children (after margins and padding)
        content_width = width - (pad_left + pad_right) - margin_left - margin_right
        content_height = height - (pad_top + pad_bottom) - margin_top - margin_bottom

        # Save original content_height for alignment calculation
        original_content_height = content_height
        content_height -= self.spacing * (len(self.children) - 1)

        # Resolve every child's width up front. Heights are measured against
        # them (wrapped text needs its width before it knows its row count), and
        # the loop below reuses them so the two passes cannot disagree.
        child_widths = {
            id(c): self._resolve_child_width(c, content_width) for c in self.children
        }

        # Count fill children
        fill_children = [c for c in self.children if c.height_spec.is_fill]
        fixed_children = [c for c in self.children if not c.height_spec.is_fill]

        # Auto-fit: when the non-fill children ask for more rows than the stack
        # has, claw the surplus back from those with slack so the column fits the
        # terminal instead of running off the bottom. Fill children then take
        # what is left, like a CSS flex item with ``flex-basis: 0``.
        requested_heights = [
            self._requested_height(c, child_widths[id(c)], content_height)
            for c in fixed_children
        ]
        fixed_heights = (
            requested_heights
            if self.no_shrink_height
            else shrink_to_fit(
                requested_heights,
                [_content_min_height(c) for c in fixed_children],
                content_height,
            )
        )
        shrunk_height = {
            id(c): h for c, h in zip(fixed_children, fixed_heights, strict=True)
        }
        fixed_height = sum(fixed_heights)

        # Distribute remaining height to fill children, spreading the integer
        # remainder onto the leading fill children so they consume every cell.
        remaining_height = max(0, content_height - fixed_height)
        fill_heights = iter(_distribute_fill(remaining_height, len(fill_children)))

        # Calculate vertical alignment offset
        # If align_v is not "stretch", we need to position the group of children
        if self.align_v != "stretch" and not fill_children:
            # Calculate total height of all children
            total_children_height = fixed_height
            total_with_spacing = total_children_height + self.spacing * (
                len(self.children) - 1
            )

            # Calculate empty space and offset (use original_content_height, not reduced one)
            if total_with_spacing < original_content_height:
                empty_space = original_content_height - total_with_spacing
                if self.align_v == "middle":
                    vertical_offset = empty_space // 2
                elif self.align_v == "bottom":
                    vertical_offset = empty_space
                else:  # "top"
                    vertical_offset = 0
            else:
                vertical_offset = 0
        else:
            vertical_offset = 0

        # Position children (offset by margins and vertical alignment)
        current_y = y + margin_top + pad_top + vertical_offset
        current_x = x + margin_left + pad_left

        for child in self.children:
            child_width = child_widths[id(child)]

            if child.height_spec.is_fill:
                child_height = next(fill_heights)
            else:
                child_height = self._requested_height(
                    child, child_width, content_height
                )
                # Cap at the auto-fit allowance. Equal to the request when the
                # column fits, smaller when this child had to give space back.
                allowance = shrunk_height.get(id(child))
                if allowance is not None:
                    child_height = min(child_height, allowance)

            # Apply horizontal alignment if child is narrower than available space
            if child_width < content_width:
                if self.align_h == "center":
                    child_x = current_x + (content_width - child_width) // 2
                elif self.align_h == "right":
                    child_x = current_x + (content_width - child_width)
                else:  # "left" or default
                    child_x = current_x
            else:
                child_x = current_x

            child.assign_bounds(child_x, current_y, child_width, child_height)
            current_y += child_height + self.spacing


class HStack(Container):
    """Horizontal stacking container.

    Arranges children horizontally with optional spacing. Supports flexbox-style
    features including content justification and wrapping.

    Parameters
    ----------
    children : list of LayoutNode, optional
        Child nodes
    width : int, str, or Size, optional
        Width specification (default: "auto")
    height : int, str, or Size, optional
        Height specification (default: "auto")
    spacing : int, optional
        Spacing between children (default: 0). Acts as column_gap fallback.
    padding : int, optional
        Padding around children (default: 0)
    margin : int or tuple of int, optional
        Margin around container (default: 0)
    align_h : {"left", "center", "right", "stretch"}, optional
        Horizontal alignment of children (default: "stretch")
    align_v : {"top", "middle", "bottom", "stretch"}, optional
        Vertical alignment of children (default: "stretch")
    justify : str, optional
        Main axis distribution mode (default: "flex-start").
        Options: "flex-start", "flex-end", "center", "space-between",
        "space-around", "space-evenly", "left", "right"
    wrap : bool, optional
        If True, children wrap to next row when exceeding width (default: False)
    row_gap : int, optional
        Space between rows when wrapping (default: 0)
    column_gap : int, optional
        Space between columns. Overrides spacing if provided.
    id : str, optional
        Node identifier

    Notes
    -----
    When any child has width="fill", the justify setting is ignored and
    fill children expand to consume remaining space instead.

    When wrap=True with fill children, fill is treated as auto-sized.
    """

    def __init__(
        self,
        children: list[LayoutNode] | None = None,
        width: int | str | Size = "auto",
        height: int | str | Size = "auto",
        spacing: int = 0,
        padding: int | tuple[int, int, int, int] = 0,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        justify: JustifyContent = "flex-start",
        wrap: bool = False,
        row_gap: int | None = None,
        column_gap: int | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(
            children, width, height, spacing, padding, margin, align_h, align_v, id
        )
        # Normalize justify aliases
        if justify == "left":
            justify = "flex-start"
        elif justify == "right":
            justify = "flex-end"

        # Backward compatibility: map align_h to justify when justify not explicitly set
        # This allows existing code using align_h="center" or align_h="right" to work
        if justify == "flex-start" and align_h in ("center", "right", "left"):
            if align_h == "center":
                justify = "center"
            elif align_h == "right":
                justify = "flex-end"
            # "left" stays as "flex-start"

        self.justify: JustifyContent = justify
        self.wrap = wrap
        # column_gap takes precedence over spacing
        self.column_gap = column_gap if column_gap is not None else spacing
        self.row_gap = row_gap if row_gap is not None else 0

    def _distribute_space(self, total_space: int, num_gaps: int) -> list[int]:
        """Distribute space into gaps, handling integer remainders.

        Remainders are distributed to earlier gaps to avoid visible unevenness.

        Parameters
        ----------
        total_space : int
            Total space to distribute
        num_gaps : int
            Number of gaps to distribute into

        Returns
        -------
        list of int
            List of gap sizes
        """
        return _distribute_fill(total_space, num_gaps)

    def _get_child_width(
        self, child: LayoutNode, content_width: int, fill_width_each: int = 0
    ) -> int:
        """Get width for a child based on its width_spec.

        Parameters
        ----------
        child : LayoutNode
            Child node
        content_width : int
            Available content width
        fill_width_each : int
            Width to assign to each fill child (0 if not computed)

        Returns
        -------
        int
            Child width
        """
        if child.width_spec.is_fill:
            # In wrap mode, treat fill as auto
            if self.wrap:
                return child.constraints.preferred_width if child.constraints else 1
            return fill_width_each
        elif child.width_spec.is_fixed:
            return child.width_spec.value
        elif child.width_spec.is_percentage:
            return int(content_width * child.width_spec.get_percentage())
        else:
            return child.constraints.preferred_width if child.constraints else 1

    def _get_child_height(
        self, child: LayoutNode, row_height: int, content_height: int
    ) -> int:
        """Get height for a child based on its height_spec.

        Parameters
        ----------
        child : LayoutNode
            Child node
        row_height : int
            Height of the current row (max of children in row)
        content_height : int
            Total available content height

        Returns
        -------
        int
            Child height
        """
        if child.height_spec.is_fixed:
            # Cross axis: a pinned height taller than the row would overflow and
            # clip, so clamp it the way Size.calculate() clamps fixed sizes.
            if auto_fit_enabled() and not self.no_shrink_height:
                return max(0, min(child.height_spec.value, content_height))
            return child.height_spec.value
        elif child.height_spec.is_fill:
            return row_height if self.wrap else content_height
        elif child.height_spec.is_percentage:
            return int(content_height * child.height_spec.get_percentage())
        else:
            height = child.constraints.preferred_height if child.constraints else 1
            return min(height, row_height if self.wrap else content_height)

    def _compute_rows(self, content_width: int) -> list[LayoutRow]:
        """Distribute children into rows based on available width.

        Only used when wrap=True.

        Parameters
        ----------
        content_width : int
            Available width for content

        Returns
        -------
        list of LayoutRow
            List of rows with their children and dimensions

        Notes
        -----
        total_width in LayoutRow is the sum of children widths only (no gaps).
        This is what _apply_justify expects.
        """
        rows: list[LayoutRow] = []
        current_row_children: list[LayoutNode] = []
        current_row_width_with_gaps = 0
        current_row_children_width = 0  # Sum of child widths only (no gaps)

        for child in self.children:
            child_width = self._get_child_width(child, content_width, 0)
            gap = self.column_gap if current_row_children else 0

            # Check if child fits in current row (using width with gaps)
            if (
                current_row_children
                and current_row_width_with_gaps + gap + child_width > content_width
            ):
                # Finalize current row
                max_height = max(
                    (c.constraints.preferred_height if c.constraints else 1)
                    for c in current_row_children
                )
                rows.append(
                    LayoutRow(
                        children=current_row_children,
                        total_width=current_row_children_width,  # Children only, no gaps
                        max_height=max_height,
                    )
                )
                # Start new row
                current_row_children = [child]
                current_row_width_with_gaps = child_width
                current_row_children_width = child_width
            else:
                current_row_children.append(child)
                current_row_width_with_gaps += gap + child_width
                current_row_children_width += child_width

        # Add final row
        if current_row_children:
            max_height = max(
                (c.constraints.preferred_height if c.constraints else 1)
                for c in current_row_children
            )
            rows.append(
                LayoutRow(
                    children=current_row_children,
                    total_width=current_row_children_width,  # Children only, no gaps
                    max_height=max_height,
                )
            )

        return rows

    def _apply_justify(
        self,
        children: list[LayoutNode],
        widths: list[int],
        x_start: int,
        available_width: int,
    ) -> list[tuple[int, LayoutNode]]:
        """Calculate x positions for children based on justify mode.

        Parameters
        ----------
        children : list of LayoutNode
            Children to position
        widths : list of int
            Final width of each child, in the same order as ``children``. These
            are resolved up front (fill distribution and auto-fit shrink already
            applied) so positions and assigned widths cannot disagree.
        x_start : int
            Starting x position
        available_width : int
            Available width for positioning

        Returns
        -------
        list of tuple
            List of (x_position, child) tuples
        """
        num_children = len(children)
        if num_children == 0:
            return []

        total_children_width = sum(widths)

        # Calculate total space including gaps
        total_gap_width = self.column_gap * (num_children - 1)
        content_with_gaps = total_children_width + total_gap_width
        free_space = max(0, available_width - content_with_gaps)

        positions: list[tuple[int, LayoutNode]] = []
        current_x = x_start

        if self.justify == "space-between":
            # First at start, last at end, equal space between
            if num_children == 1:
                positions.append((x_start, children[0]))
            else:
                gaps = self._distribute_space(free_space, num_children - 1)
                for i, (child, child_width) in enumerate(
                    zip(children, widths, strict=True)
                ):
                    positions.append((current_x, child))
                    extra_gap = gaps[i] if i < len(gaps) else 0
                    current_x += child_width + self.column_gap + extra_gap

        elif self.justify == "space-around":
            # Equal space around each item (half space at edges)
            # Each item gets equal space around it
            # Total gaps = 2 * num_children (one before and one after each)
            # Edge gaps are half of inter-item gaps
            total_half_gaps = num_children * 2
            half_gap_sizes = self._distribute_space(free_space, total_half_gaps)
            # First edge gap
            current_x = x_start + half_gap_sizes[0] if half_gap_sizes else x_start
            for i, (child, child_width) in enumerate(
                zip(children, widths, strict=True)
            ):
                positions.append((current_x, child))
                # After each child: half_gap[2*i+1] + column_gap + half_gap[2*i+2]
                after_idx = 2 * i + 1
                before_next_idx = 2 * i + 2
                after_gap = (
                    half_gap_sizes[after_idx] if after_idx < len(half_gap_sizes) else 0
                )
                before_next = (
                    half_gap_sizes[before_next_idx]
                    if before_next_idx < len(half_gap_sizes)
                    else 0
                )
                current_x += child_width + self.column_gap + after_gap + before_next

        elif self.justify == "space-evenly":
            # Equal space between all items including edges
            num_gaps = num_children + 1
            gaps = self._distribute_space(free_space, num_gaps)
            current_x = x_start + (gaps[0] if gaps else 0)
            for i, (child, child_width) in enumerate(
                zip(children, widths, strict=True)
            ):
                positions.append((current_x, child))
                extra_gap = gaps[i + 1] if i + 1 < len(gaps) else 0
                current_x += child_width + self.column_gap + extra_gap

        else:
            # Packed layouts ("flex-start", "flex-end", "center", and any
            # unrecognized value, which falls back to flex-start). They differ
            # only in where the group starts; the walk itself is identical.
            if self.justify == "flex-end":
                current_x = x_start + free_space
            elif self.justify == "center":
                current_x = x_start + free_space // 2
            for child, child_width in zip(children, widths, strict=True):
                positions.append((current_x, child))
                current_x += child_width + self.column_gap

        return positions

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate constraints for horizontal stack.

        Width is the sum of children widths plus column_gap.
        Height is the maximum of children heights.

        When wrap=True:
        - min_width is the widest single child (must fit at least one)
        - preferred_width is single-row width (no wrapping needed)

        Returns
        -------
        SizeConstraints
            Calculated constraints
        """
        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.padding
        pad_w = pad_left + pad_right
        pad_h = pad_top + pad_bottom

        if not self.children:
            # Empty container
            self.constraints = SizeConstraints(
                min_width=pad_w + margin_left + margin_right,
                min_height=pad_h + margin_top + margin_bottom,
                preferred_width=pad_w + margin_left + margin_right,
                preferred_height=pad_h + margin_top + margin_bottom,
            )
            return self.constraints

        # Calculate children constraints first
        child_constraints = [child.calculate_constraints() for child in self.children]

        # Width: sum of children plus column_gap
        # For children with width=fill, use min_width instead of preferred_width
        # to avoid inflating the parent (unless wrap mode, where fill=auto)
        total_width = 0
        max_child_width = 0
        # The auto-fit floor is built from the children's own floors, not their
        # preferred sizes, so a nested fixed-width widget does not make the whole
        # row look incompressible.
        total_content_min_width = 0
        max_child_content_min = 0
        for i, child in enumerate(self.children):
            constraint = child_constraints[i]
            if child.width_spec.is_fill and not self.wrap:
                # Fill children contribute only their minimum (non-wrap mode)
                child_width = constraint.min_width
            else:
                # Fixed/auto children (or fill in wrap mode) use preferred size
                child_width = constraint.preferred_width
            total_width += child_width
            max_child_width = max(max_child_width, child_width)
            child_content_min = constraint.content_min_width or 0
            total_content_min_width += child_content_min
            max_child_content_min = max(max_child_content_min, child_content_min)
        total_width += self.column_gap * (len(self.children) - 1)
        total_content_min_width += self.column_gap * (len(self.children) - 1)

        # Height: max of children
        # For children with height=fill, use min_height instead of preferred_height
        max_child_height = 0
        max_child_content_min_height = 0
        for i, child in enumerate(self.children):
            constraint = child_constraints[i]
            if child.height_spec.is_fill:
                # Fill children contribute only their minimum
                height = constraint.min_height
            else:
                # Fixed/auto children contribute their preferred size
                height = constraint.preferred_height
            max_child_height = max(max_child_height, height)
            max_child_content_min_height = max(
                max_child_content_min_height, constraint.content_min_height or 0
            )

        # Add padding and margins
        preferred_content_width = total_width + pad_w + margin_left + margin_right
        min_content_height = max_child_height + pad_h + margin_top + margin_bottom

        # For wrap mode, min_width only needs to fit widest single child
        if self.wrap:
            min_content_width = max_child_width + pad_w + margin_left + margin_right
        else:
            min_content_width = preferred_content_width

        # What the stack needs before any explicit size spec is applied. Auto-fit
        # shrinks toward these, not toward a pinned width/height. In wrap mode the
        # floor is the widest single child's floor - a wrapped row can reflow the
        # rest onto more rows.
        if self.wrap:
            content_min_width = (
                max_child_content_min + pad_w + margin_left + margin_right
            )
        else:
            content_min_width = (
                total_content_min_width + pad_w + margin_left + margin_right
            )
        content_min_height = (
            max_child_content_min_height + pad_h + margin_top + margin_bottom
        )

        # Apply width/height specs if fixed
        if self.width_spec.is_fixed:
            min_width = self.width_spec.value
            preferred_width = self.width_spec.value
            content_min_width = min(content_min_width, min_width)
        else:
            min_width = min_content_width
            preferred_width = preferred_content_width

        if self.height_spec.is_fixed:
            min_height = self.height_spec.value
            preferred_height = self.height_spec.value
            content_min_height = min(content_min_height, min_height)
        else:
            min_height = min_content_height
            preferred_height = min_content_height

        self.constraints = SizeConstraints(
            min_width=min_width,
            min_height=min_height,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            content_min_width=content_min_width,
            content_min_height=content_min_height,
        )
        return self.constraints

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign bounds to container and position children horizontally.

        Supports flexbox-style justify and wrap modes.

        Parameters
        ----------
        x : int
            X position
        y : int
            Y position
        width : int
            Assigned width
        height : int
            Assigned height
        """
        self.bounds = Bounds(x=x, y=y, width=width, height=height)

        if not self.children:
            return

        # Apply margins
        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.padding

        # Calculate available space for children (after margins and padding)
        content_width = width - (pad_left + pad_right) - margin_left - margin_right
        content_height = height - (pad_top + pad_bottom) - margin_top - margin_bottom

        # Content area start position
        content_x = x + margin_left + pad_left
        content_y = y + margin_top + pad_top

        # Check for fill children (disables justify in non-wrap mode)
        fill_children = [c for c in self.children if c.width_spec.is_fill]
        has_fill_children = bool(fill_children) and not self.wrap

        if self.wrap:
            # Multi-row wrapped layout
            self._assign_bounds_wrapped(
                content_x, content_y, content_width, content_height
            )
        elif has_fill_children:
            # Fill children present - use legacy behavior (ignore justify)
            self._assign_bounds_with_fill(
                content_x, content_y, content_width, content_height
            )
        else:
            # Single row with justify
            self._assign_bounds_justified(
                content_x, content_y, content_width, content_height
            )

    def _resolve_child_widths(self, content_width: int) -> list[int]:
        """Resolve the final width of every child, applying auto-fit shrink.

        Fill children absorb whatever is left after their non-fill siblings are
        served. When the non-fill siblings over-commit the row, auto-fit claws
        space back from them (see :func:`shrink_to_fit`) so the row fits the
        terminal instead of running off the right edge.

        Parameters
        ----------
        content_width : int
            Available content width, gaps included.

        Returns
        -------
        list of int
            Final width per child, in child order.
        """
        num = len(self.children)
        available = max(0, content_width - self.column_gap * (num - 1))

        fill_idx = [i for i, c in enumerate(self.children) if c.width_spec.is_fill]
        rigid_idx = [i for i, c in enumerate(self.children) if not c.width_spec.is_fill]

        widths = [0] * num
        for i in rigid_idx:
            widths[i] = self._get_child_width(self.children[i], content_width, 0)

        # Rigid children are shrunk only against the row itself. Fill children
        # get whatever is left over, exactly like a CSS flex item with
        # ``flex-basis: 0``: reserving room for them up front would shrink a
        # fixed-width sibling even in rows that already fit.
        if not self.no_shrink_width:
            shrunk = shrink_to_fit(
                [widths[i] for i in rigid_idx],
                [_content_min_width(self.children[i]) for i in rigid_idx],
                available,
            )
            for i, w in zip(rigid_idx, shrunk, strict=True):
                widths[i] = w

        if fill_idx:
            remaining = max(0, available - sum(widths[i] for i in rigid_idx))
            # Spread the integer remainder onto the leading fill children so
            # they consume every cell.
            for i, w in zip(
                fill_idx, _distribute_fill(remaining, len(fill_idx)), strict=True
            ):
                widths[i] = w

        return widths

    def _assign_bounds_with_fill(
        self, content_x: int, content_y: int, content_width: int, content_height: int
    ) -> None:
        """Assign bounds when fill children are present (legacy behavior).

        Fill children expand to consume remaining width. Justify is ignored.

        Parameters
        ----------
        content_x : int
            Content area X start
        content_y : int
            Content area Y start
        content_width : int
            Available content width
        content_height : int
            Available content height
        """
        widths = self._resolve_child_widths(content_width)

        current_x = content_x

        for child, child_width in zip(self.children, widths, strict=True):
            child_height = self._get_child_height(child, content_height, content_height)

            # Apply vertical alignment
            child_y = self._apply_align_v(content_y, child_height, content_height)

            child.assign_bounds(current_x, child_y, child_width, child_height)
            current_x += child_width + self.column_gap

    def _assign_bounds_justified(
        self, content_x: int, content_y: int, content_width: int, content_height: int
    ) -> None:
        """Assign bounds for single-row layout with justify.

        Parameters
        ----------
        content_x : int
            Content area X start
        content_y : int
            Content area Y start
        content_width : int
            Available content width
        content_height : int
            Available content height
        """
        widths = self._resolve_child_widths(content_width)

        # Get positioned children from justify
        positions = self._apply_justify(
            self.children,
            widths,
            content_x,
            content_width,
        )

        for (child_x, child), child_width in zip(positions, widths, strict=True):
            child_height = self._get_child_height(child, content_height, content_height)

            # Apply vertical alignment
            child_y = self._apply_align_v(content_y, child_height, content_height)

            child.assign_bounds(child_x, child_y, child_width, child_height)

    def _assign_bounds_wrapped(
        self, content_x: int, content_y: int, content_width: int, content_height: int
    ) -> None:
        """Assign bounds for multi-row wrapped layout.

        Parameters
        ----------
        content_x : int
            Content area X start
        content_y : int
            Content area Y start
        content_width : int
            Available content width
        content_height : int
            Available content height
        """
        rows = self._compute_rows(content_width)
        current_y = content_y

        for row in rows:
            # Wrapping already resolves overflow by reflowing, so widths here are
            # taken as requested - only a single child too wide for the whole row
            # is clamped, which shrink_to_fit does for free.
            row_widths = shrink_to_fit(
                [self._get_child_width(c, content_width, 0) for c in row.children],
                [_content_min_width(c) for c in row.children],
                max(0, content_width - self.column_gap * (len(row.children) - 1)),
            )

            # Get positioned children from justify for this row
            positions = self._apply_justify(
                row.children,
                row_widths,
                content_x,
                content_width,
            )

            for (child_x, child), child_width in zip(
                positions, row_widths, strict=True
            ):
                child_height = self._get_child_height(
                    child, row.max_height, content_height
                )

                # Apply vertical alignment within the row
                child_y = self._apply_align_v(current_y, child_height, row.max_height)

                child.assign_bounds(child_x, child_y, child_width, child_height)

            current_y += row.max_height + self.row_gap

    def _apply_align_v(
        self, base_y: int, child_height: int, available_height: int
    ) -> int:
        """Apply vertical alignment to get child Y position.

        Parameters
        ----------
        base_y : int
            Base Y position (top of available space)
        child_height : int
            Height of the child
        available_height : int
            Available height in the row/container

        Returns
        -------
        int
            Y position for the child
        """
        if child_height < available_height:
            if self.align_v == "middle":
                return base_y + (available_height - child_height) // 2
            elif self.align_v == "bottom":
                return base_y + (available_height - child_height)
        return base_y


@dataclass
class GridCell:
    """Represents a cell or span in the grid.

    Parameters
    ----------
    row : int
        Starting row index (0-based)
    col : int
        Starting column index (0-based)
    rowspan : int
        Number of rows this cell spans (default: 1)
    colspan : int
        Number of columns this cell spans (default: 1)
    node : LayoutNode or None
        The layout node occupying this cell

    Attributes
    ----------
    row : int
        Starting row index
    col : int
        Starting column index
    rowspan : int
        Number of rows spanned
    colspan : int
        Number of columns spanned
    node : LayoutNode or None
        The layout node in this cell
    """

    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    node: LayoutNode | None = None


class GridSpanWrapper(LayoutNode):
    """Wrapper node that carries colspan/rowspan information.

    This wrapper is used by {% colspan %} and {% rowspan %} tags to
    communicate span information to the parent Grid container.

    Parameters
    ----------
    child : LayoutNode
        The actual layout node being wrapped
    colspan : int
        Number of columns to span (default: 1)
    rowspan : int
        Number of rows to span (default: 1)

    Attributes
    ----------
    child : LayoutNode
        The wrapped layout node
    colspan : int
        Number of columns to span
    rowspan : int
        Number of rows to span
    """

    def __init__(
        self,
        child: LayoutNode,
        colspan: int = 1,
        rowspan: int = 1,
    ) -> None:
        super().__init__()
        self.child = child
        self.colspan = colspan
        self.rowspan = rowspan

    def calculate_constraints(self) -> SizeConstraints:
        """Delegate to wrapped child.

        Returns
        -------
        SizeConstraints
            Constraints from the wrapped child
        """
        self.constraints = self.child.calculate_constraints()
        return self.constraints

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Delegate to wrapped child.

        Parameters
        ----------
        x : int
            X position
        y : int
            Y position
        width : int
            Assigned width
        height : int
            Assigned height
        """
        self.bounds = Bounds(x=x, y=y, width=width, height=height)
        self.child.assign_bounds(x, y, width, height)

    def collect_elements(self) -> list[Element]:
        """Delegate to wrapped child.

        Returns
        -------
        list of Element
            Elements from the wrapped child
        """
        return self.child.collect_elements()


class Grid(Container):
    """Grid container for 2D layouts.

    Arranges children in a rows x cols grid with optional gaps.
    Supports colspan and rowspan via GridSpanWrapper children.

    Parameters
    ----------
    rows : int
        Number of rows in the grid
    cols : int
        Number of columns in the grid
    children : list of LayoutNode, optional
        Child nodes (may include GridSpanWrapper for spans)
    row_gap : int, optional
        Vertical gap between rows (default: 0)
    column_gap : int, optional
        Horizontal gap between columns (default: 0)
    width : int, str, or Size, optional
        Width specification (default: "fill")
    height : int, str, or Size, optional
        Height specification (default: "auto")
    padding : int, optional
        Padding around the grid (default: 0)
    margin : int or tuple, optional
        Margin around the grid (default: 0)
    align_h : {"left", "center", "right", "stretch"}, optional
        Horizontal alignment of cells (default: "stretch")
    align_v : {"top", "middle", "bottom", "stretch"}, optional
        Vertical alignment of cells (default: "stretch")
    id : str, optional
        Node identifier

    Attributes
    ----------
    rows : int
        Number of grid rows
    cols : int
        Number of grid columns
    row_gap : int
        Gap between rows
    column_gap : int
        Gap between columns

    Raises
    ------
    ValueError
        If child count doesn't match grid capacity after accounting for spans
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        children: list[LayoutNode] | None = None,
        row_gap: int = 0,
        column_gap: int = 0,
        width: int | str | Size = "fill",
        height: int | str | Size = "auto",
        padding: int | tuple[int, int, int, int] = 0,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: str | None = None,
    ) -> None:
        super().__init__(
            children, width, height, 0, padding, margin, align_h, align_v, id
        )
        self.rows = rows
        self.cols = cols
        self.row_gap = row_gap
        self.column_gap = column_gap

        # Internal tracking (initialized in validate_and_place_children)
        self._cell_map: list[list[GridCell | None]] = []
        self._row_heights: list[int] = []
        self._col_widths: list[int] = []
        self._children_placed: list[tuple[LayoutNode, GridCell]] = []

    def _span_fits(self, row: int, col: int, rowspan: int, colspan: int) -> bool:
        """Check if a span fits at the given position.

        Parameters
        ----------
        row : int
            Starting row
        col : int
            Starting column
        rowspan : int
            Number of rows to span
        colspan : int
            Number of columns to span

        Returns
        -------
        bool
            True if span fits, False otherwise
        """
        if row + rowspan > self.rows or col + colspan > self.cols:
            return False

        for r in range(row, row + rowspan):
            for c in range(col, col + colspan):
                if self._cell_map[r][c] is not None:
                    return False
        return True

    def validate_and_place_children(self) -> None:
        """Validate child count and place children in grid cells.

        Places children in left-to-right, top-to-bottom order,
        respecting colspan/rowspan from GridSpanWrapper children.

        Raises
        ------
        ValueError
            If children don't fit exactly in grid capacity
        """
        self._cell_map = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self._children_placed = []

        current_row = 0
        current_col = 0

        for child_index, child in enumerate(self.children):
            # Extract span info if wrapped
            if isinstance(child, GridSpanWrapper):
                colspan = child.colspan
                rowspan = child.rowspan
                actual_child = child.child
            else:
                colspan = 1
                rowspan = 1
                actual_child = child

            # Find next available cell
            found = False
            while current_row < self.rows:
                while current_col < self.cols:
                    if self._cell_map[current_row][current_col] is None:
                        # Check if span fits
                        if self._span_fits(current_row, current_col, rowspan, colspan):
                            found = True
                            break
                    current_col += 1

                if found:
                    break

                current_row += 1
                current_col = 0

            if not found:
                # Build child description for error message
                child_desc = f"child #{child_index}"
                if hasattr(actual_child, "element") and hasattr(
                    actual_child.element, "id"
                ):
                    child_desc = (
                        f"child #{child_index} (id='{actual_child.element.id}')"
                    )
                span_info = ""
                if colspan > 1 or rowspan > 1:
                    span_info = f" with colspan={colspan}, rowspan={rowspan}"
                raise ValueError(
                    f"Grid overflow: Cannot place {child_desc}{span_info}. "
                    f"Grid has {self.rows} rows x {self.cols} cols = "
                    f"{self.rows * self.cols} cells. "
                    f"Check that child count matches grid capacity "
                    f"accounting for colspan/rowspan."
                )

            # Place the child
            cell = GridCell(
                row=current_row,
                col=current_col,
                rowspan=rowspan,
                colspan=colspan,
                node=actual_child,
            )

            # Mark cells as occupied
            for r in range(current_row, current_row + rowspan):
                for c in range(current_col, current_col + colspan):
                    self._cell_map[r][c] = cell

            self._children_placed.append((actual_child, cell))

            # Move to next cell
            current_col += colspan
            if current_col >= self.cols:
                current_col = 0
                current_row += 1

        # Validate: all cells must be filled
        for r in range(self.rows):
            for c in range(self.cols):
                if self._cell_map[r][c] is None:
                    raise ValueError(
                        f"Grid underflow: Cell ({r}, {c}) is empty. "
                        f"Grid has {self.rows} rows x {self.cols} cols = "
                        f"{self.rows * self.cols} cells. "
                        f"Add more children or reduce grid size."
                    )

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate size constraints for the grid.

        Auto-sizes columns to fit largest content in each column,
        and rows to fit tallest content in each row.

        Returns
        -------
        SizeConstraints
            Calculated constraints
        """
        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.padding
        pad_w = pad_left + pad_right
        pad_h = pad_top + pad_bottom

        if not self.children:
            self.constraints = SizeConstraints(
                min_width=pad_w + margin_left + margin_right,
                min_height=pad_h + margin_top + margin_bottom,
            )
            return self.constraints

        # Validate and place children first
        self.validate_and_place_children()

        # Calculate child constraints
        for child, _cell in self._children_placed:
            child.calculate_constraints()

        # Initialize column widths and row heights
        self._col_widths = [0] * self.cols
        self._row_heights = [0] * self.rows

        # First pass: Process non-spanning cells to establish base sizes
        for child, cell in self._children_placed:
            if cell.colspan == 1 and cell.rowspan == 1:
                if child.constraints:
                    self._col_widths[cell.col] = max(
                        self._col_widths[cell.col],
                        child.constraints.preferred_width,
                    )
                    self._row_heights[cell.row] = max(
                        self._row_heights[cell.row],
                        child.constraints.preferred_height,
                    )

        # Second pass: Handle spanning cells
        # Distribute any extra needed size across spanned columns/rows
        for child, cell in self._children_placed:
            if cell.colspan > 1 or cell.rowspan > 1:
                if child.constraints:
                    # Calculate current spanned width
                    spanned_cols = list(range(cell.col, cell.col + cell.colspan))
                    current_width = sum(self._col_widths[c] for c in spanned_cols)
                    current_width += self.column_gap * (cell.colspan - 1)

                    # If child needs more width, distribute evenly
                    if child.constraints.preferred_width > current_width:
                        extra = child.constraints.preferred_width - current_width
                        per_col = extra // cell.colspan
                        remainder = extra % cell.colspan
                        for i, c in enumerate(spanned_cols):
                            self._col_widths[c] += per_col
                            if i < remainder:
                                self._col_widths[c] += 1

                    # Same for height
                    spanned_rows = list(range(cell.row, cell.row + cell.rowspan))
                    current_height = sum(self._row_heights[r] for r in spanned_rows)
                    current_height += self.row_gap * (cell.rowspan - 1)

                    if child.constraints.preferred_height > current_height:
                        extra = child.constraints.preferred_height - current_height
                        per_row = extra // cell.rowspan
                        remainder = extra % cell.rowspan
                        for i, r in enumerate(spanned_rows):
                            self._row_heights[r] += per_row
                            if i < remainder:
                                self._row_heights[r] += 1

        # Calculate total size
        total_width = sum(self._col_widths) + self.column_gap * (self.cols - 1)
        total_height = sum(self._row_heights) + self.row_gap * (self.rows - 1)

        # Add padding and margins
        min_width = total_width + pad_w + margin_left + margin_right
        min_height = total_height + pad_h + margin_top + margin_bottom

        # Apply fixed size specs
        if self.width_spec.is_fixed:
            min_width = self.width_spec.value
            preferred_width = self.width_spec.value
        else:
            preferred_width = min_width

        if self.height_spec.is_fixed:
            min_height = self.height_spec.value
            preferred_height = self.height_spec.value
        else:
            preferred_height = min_height

        self.constraints = SizeConstraints(
            min_width=min_width,
            min_height=min_height,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
        )
        return self.constraints

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign bounds to grid and position children in cells.

        Parameters
        ----------
        x : int
            X position
        y : int
            Y position
        width : int
            Assigned width
        height : int
            Assigned height
        """
        self.bounds = Bounds(x=x, y=y, width=width, height=height)

        if not self.children:
            return

        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.padding

        # Calculate content area
        content_x = x + margin_left + pad_left
        content_y = y + margin_top + pad_top

        # Calculate row Y positions
        row_y_positions = [0] * self.rows
        current_y = content_y
        for r in range(self.rows):
            row_y_positions[r] = current_y
            current_y += self._row_heights[r] + self.row_gap

        # Calculate column X positions
        col_x_positions = [0] * self.cols
        current_x = content_x
        for c in range(self.cols):
            col_x_positions[c] = current_x
            current_x += self._col_widths[c] + self.column_gap

        # Assign bounds to each child based on its cell position and span
        for child, cell in self._children_placed:
            cell_x = col_x_positions[cell.col]
            cell_y = row_y_positions[cell.row]

            # Calculate spanned width (sum of columns + gaps)
            cell_width = sum(
                self._col_widths[c] for c in range(cell.col, cell.col + cell.colspan)
            )
            cell_width += self.column_gap * (cell.colspan - 1)

            # Calculate spanned height (sum of rows + gaps)
            cell_height = sum(
                self._row_heights[r] for r in range(cell.row, cell.row + cell.rowspan)
            )
            cell_height += self.row_gap * (cell.rowspan - 1)

            # Apply alignment within cell
            child_width = cell_width
            child_height = cell_height
            child_x = cell_x
            child_y = cell_y

            # Horizontal alignment
            if self.align_h != "stretch" and child.constraints:
                child_width = min(child.constraints.preferred_width, cell_width)
                if self.align_h == "center":
                    child_x = cell_x + (cell_width - child_width) // 2
                elif self.align_h == "right":
                    child_x = cell_x + (cell_width - child_width)

            # Vertical alignment
            if self.align_v != "stretch" and child.constraints:
                child_height = min(child.constraints.preferred_height, cell_height)
                if self.align_v == "middle":
                    child_y = cell_y + (cell_height - child_height) // 2
                elif self.align_v == "bottom":
                    child_y = cell_y + (cell_height - child_height)

            child.assign_bounds(child_x, child_y, child_width, child_height)

    def collect_elements(self) -> list[Element]:
        """Collect all elements from children.

        Returns
        -------
        list of Element
            All elements in the subtree

        Notes
        -----
        Iterates through the children list (which may contain GridSpanWrapper),
        collecting elements from each.
        """
        elements = []
        for child in self.children:
            elements.extend(child.collect_elements())
        return elements


class FrameNode(Container):
    """Frame container node that wraps Frame objects with children.

    FrameNode combines the visual styling of Frame (borders, padding, overflow)
    with the layout capabilities of Container (children management).

    Parameters
    ----------
    frame : Frame
        The Frame object providing visual styling and rendering
    children : list of LayoutNode, optional
        Child nodes to layout inside the frame
    width : int, str, or Size, optional
        Width specification (default: from frame)
    height : int, str, or Size, optional
        Height specification (default: from frame)
    margin : int or tuple of int, optional
        Margin around frame (default: 0)
    align_h : {"left", "center", "right", "stretch"}, optional
        Horizontal alignment within parent (default: "stretch")
    align_v : {"top", "middle", "bottom", "stretch"}, optional
        Vertical alignment within parent (default: "stretch")
    content_align_h : {"left", "center", "right", "stretch"}, optional
        Horizontal alignment of children within frame (default: "stretch")
    content_align_v : {"top", "middle", "bottom", "stretch"}, optional
        Vertical alignment of children within frame (default: "stretch")
    id : str, optional
        Node identifier

    Attributes
    ----------
    frame : Frame
        The wrapped Frame object
    content_container : VStack
        Internal VStack for managing children inside frame content area
    """

    def __init__(
        self,
        frame: "Frame",
        children: list[LayoutNode] | None = None,
        width: int | str | Size | None = None,
        height: int | str | Size | None = None,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        content_align_h: HAlign = "stretch",
        content_align_v: VAlign = "stretch",
        id: str | None = None,
    ) -> None:

        # Use frame dimensions if not specified
        if width is None:
            width = frame.width
        if height is None:
            height = frame.height

        # Initialize container with frame dimensions
        super().__init__(
            children=[],
            width=width,
            height=height,
            spacing=0,
            padding=0,
            margin=margin,
            align_h=align_h,
            align_v=align_v,
            id=id,
        )

        self.frame = frame

        # Create internal VStack for children inside frame content area
        self.content_container = VStack(
            children=children or [],
            width="fill",
            height="fill",
            spacing=0,
            padding=0,
            margin=0,
            align_h=content_align_h,
            align_v=content_align_v,
        )

    def add_child(self, child: LayoutNode) -> None:
        """Add a child node to the frame's content area.

        Parameters
        ----------
        child : LayoutNode
            Child node to add
        """
        self.content_container.add_child(child)

    def get_height_for_width(self, width: int) -> int:
        """Measure the frame's content at the interior width ``width`` implies.

        Parameters
        ----------
        width : int
            The width this frame will be laid out at, margins included.

        Returns
        -------
        int
            Rows the frame needs, including borders, padding and margins.
        """
        if self.height_spec.is_fixed:
            return int(self.height_spec.value)
        if not self.content_container.children or width <= 0:
            return super().get_height_for_width(width)

        margin_top, margin_right, margin_bottom, margin_left = self.margin
        pad_top, pad_right, pad_bottom, pad_left = self.frame.style.padding
        # Interior width: drop margins, the two border columns, then padding.
        inner_width = width - margin_left - margin_right - 2 - pad_left - pad_right
        if inner_width <= 0:
            return super().get_height_for_width(width)

        inner_height = self.content_container.get_height_for_width(inner_width)
        return (
            inner_height
            + pad_top
            + pad_bottom
            + 2  # top and bottom borders
            + margin_top
            + margin_bottom
        )

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate size constraints for the frame and its children.

        The constraints returned include margin space. This follows the CSS
        box model where:

        - Content: The actual frame content area
        - Padding: Space inside the frame border (handled by frame.style.padding)
        - Border: The frame border (2 chars: 1 left + 1 right, 1 top + 1 bottom)
        - Margin: Space outside the frame border (this class's margin attribute)

        The min_width/min_height values returned include all of these components.
        When assign_bounds() is called, the passed width/height represents the
        total allocated space including margin, and the actual frame is positioned
        inset by the margin amounts.

        Returns
        -------
        SizeConstraints
            Size constraints for the frame, including margin space
        """
        # Calculate children constraints
        if self.content_container.children:
            # Has layout children (which may include text converted to TextElement)
            child_constraints = self.content_container.calculate_constraints()
            child_min_w = child_constraints.min_width
            child_min_h = child_constraints.min_height
            # Auto-fit floors come from the content's own floors, so a nested
            # fixed-size widget does not make this frame incompressible.
            child_content_min_w = child_constraints.content_min_width or 0
            child_content_min_h = child_constraints.content_min_height or 0

            # If frame ALSO has direct text content (edge case), add it to height
            # This shouldn't normally happen (text becomes TextElement child), but handle it
            if self.frame.content:
                child_min_h += len(self.frame.content)
                child_content_min_h += len(self.frame.content)
        else:
            # No layout children, but check if frame has text content
            if self.frame.content:
                # Use number of content lines as minimum height
                child_min_h = len(self.frame.content)
                child_min_w = 0
            else:
                child_min_w = 0
                child_min_h = 0
            child_content_min_w = child_min_w
            child_content_min_h = child_min_h

        # Account for frame borders and padding
        padding_top, padding_right, padding_bottom, padding_left = (
            self.frame.style.padding
        )
        border_width = 2  # Left and right borders
        border_height = 2  # Top and bottom borders

        # Calculate total required size
        frame_min_w = child_min_w + padding_left + padding_right + border_width
        frame_min_h = child_min_h + padding_top + padding_bottom + border_height

        # Apply margin
        margin_top, margin_right, margin_bottom, margin_left = self.margin
        total_min_w = frame_min_w + margin_left + margin_right
        total_min_h = frame_min_h + margin_top + margin_bottom

        # What the frame needs before any explicit size spec is applied - border,
        # padding and the content's own floor. Auto-fit shrinks toward this and
        # never below it, so a squeezed frame keeps its border and a sliver of
        # content rather than collapsing.
        content_min_w = (
            child_content_min_w
            + padding_left
            + padding_right
            + border_width
            + margin_left
            + margin_right
        )
        content_min_h = (
            child_content_min_h
            + padding_top
            + padding_bottom
            + border_height
            + margin_top
            + margin_bottom
        )

        # Respect fixed width/height specifications
        # If width_spec is fixed, use that instead of calculated width
        if self.width_spec.is_fixed:
            total_min_w = self.width_spec.value + margin_left + margin_right
            preferred_width = self.width_spec.value + margin_left + margin_right
            content_min_w = min(content_min_w, total_min_w)
        else:
            preferred_width = total_min_w

        if self.height_spec.is_fixed:
            total_min_h = self.height_spec.value + margin_top + margin_bottom
            preferred_height = self.height_spec.value + margin_top + margin_bottom
            content_min_h = min(content_min_h, total_min_h)
        else:
            preferred_height = total_min_h

        self.constraints = SizeConstraints(
            min_width=total_min_w,
            min_height=total_min_h,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            content_min_width=content_min_w,
            content_min_height=content_min_h,
        )
        return self.constraints

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign absolute position and size to the frame.

        This method handles margin application following the CSS box model.
        The passed x, y, width, height represent the total allocated space
        INCLUDING margin. The actual frame content is positioned inside this
        space, inset by the margin amounts.

        Coordinate flow:
        1. Input (x, y, width, height) = Total space allocated for this element
        2. Frame bounds = (x + margin_left, y + margin_top,
                          width - margins, height - margins)
        3. Inner content = Frame bounds minus border and padding

        Parameters
        ----------
        x : int
            Left edge of allocated space (margin box)
        y : int
            Top edge of allocated space (margin box)
        width : int
            Total allocated width including margins
        height : int
            Total allocated height including margins
        """
        from wijjit.layout.bounds import Bounds

        # Extract margin values (CSS box model: margin is outermost)
        margin_top, margin_right, margin_bottom, margin_left = self.margin

        # Calculate frame dimensions (inside margin, at border box)
        # The passed width/height includes margin space
        available_width = width - margin_left - margin_right
        available_height = height - margin_top - margin_bottom

        # If width_spec is fixed, use that instead of available width
        if self.width_spec.is_fixed:
            content_width = min(self.width_spec.value, available_width)
        else:
            content_width = available_width

        # If height_spec is fixed, use that instead of available height
        if self.height_spec.is_fixed:
            content_height = min(self.height_spec.value, available_height)
        else:
            content_height = available_height

        content_x = x + margin_left
        content_y = y + margin_top

        # Assign bounds to frame node and frame object
        self.bounds = Bounds(content_x, content_y, content_width, content_height)
        self.frame.bounds = Bounds(content_x, content_y, content_width, content_height)
        self.frame.width = content_width
        self.frame.height = content_height

        # Calculate inner content area (inside borders and padding)
        padding_top, padding_right, padding_bottom, padding_left = (
            self.frame.style.padding
        )
        inner_x = content_x + 1 + padding_left  # +1 for left border
        inner_y = content_y + 1 + padding_top  # +1 for top border
        inner_width = content_width - 2 - padding_left - padding_right  # -2 for borders
        inner_height = (
            content_height - 2 - padding_top - padding_bottom
        )  # -2 for borders

        # Lay out children in content area
        if self.content_container.children:

            # Calculate total child content height for scrolling
            # Recursively find the bottom-most element across all descendants
            def find_max_bottom(node: LayoutNode, base_y: int) -> int:
                """Recursively find the maximum bottom position of all descendants.

                Parameters
                ----------
                node : LayoutNode
                    Node to search
                base_y : int
                    Base Y position to calculate relative bottom from

                Returns
                -------
                int
                    Maximum bottom position relative to base_y
                """
                max_bottom = 0

                # Check this node's bounds
                if node.bounds is not None:
                    node_bottom = node.bounds.y + node.bounds.height - base_y
                    max_bottom = max(max_bottom, node_bottom)

                # Recursively check children if this is a container
                if isinstance(node, Container):
                    for child in node.children:
                        child_bottom = find_max_bottom(child, base_y)
                        max_bottom = max(max_bottom, child_bottom)

                return max_bottom

            def scrollbar_reserved() -> bool:
                """Whether the vertical-scrollbar column must be reserved.

                The scrollbar is drawn in the rightmost interior column (the
                renderer's clip and the frame's own ``render_to`` both subtract
                one column for it), so a ``width="fill"`` child laid out at the
                full inner width overhangs into it: its right border falls
                outside the clip and the scrollbar overdraws it, leaving the
                child visually open on the right. When this is true the children
                are laid out one column narrower so their right edge clears the
                gutter.
                """
                return (
                    self.frame.style.scrollable
                    and self.frame._needs_scroll
                    and self.frame.style.show_scrollbar
                    and inner_width > 1
                )

            # Predict the gutter from the frame's *previous* scroll state so the
            # common case lays the whole subtree out exactly once. ``_needs_scroll``
            # persists on the reused Frame element across renders, so a frame that
            # was scrolling last frame is almost certainly scrolling this one; a
            # frame that fit still fits. Laying out at the correct width up front
            # avoids the full re-layout that made review item 2.4 O(2^depth): that
            # second pass recurses into nested frames, each of which doubled again.
            # A viewport exists to hold content bigger than itself, so auto-fit
            # must leave the scrolling axis alone - shrinking the content to the
            # viewport would leave nothing to scroll.
            self.content_container.no_shrink_height = bool(self.frame.style.scrollable)
            self.content_container.no_shrink_width = self.frame.style.overflow_x in (
                "scroll",
                "auto",
            )

            reserve = scrollbar_reserved()
            layout_width = inner_width - 1 if reserve else inner_width
            self.content_container.assign_bounds(
                inner_x, inner_y, layout_width, inner_height
            )
            # Always call this when there are children, even if calculated height
            # is 0 - it (re)creates the scroll manager and recomputes _needs_scroll
            # from the measured content height.
            max_bottom = find_max_bottom(self.content_container, inner_y)
            self.frame.set_child_content_height(max_bottom)

            # Correct a mispredicted gutter with a single re-layout. This runs
            # only on the transition frame where scrolling turns on (content grew
            # past the viewport) or off (content shrank to fit) - not in steady
            # state - so the amortized cost stays at one subtree layout per frame.
            if scrollbar_reserved() != reserve:
                reserve = not reserve
                layout_width = inner_width - 1 if reserve else inner_width
                self.content_container.assign_bounds(
                    inner_x, inner_y, layout_width, inner_height
                )
                max_bottom = find_max_bottom(self.content_container, inner_y)
                self.frame.set_child_content_height(max_bottom)

    def collect_elements(self) -> list[Element]:
        """Collect frame and all child elements.

        Returns
        -------
        list of Element
            Frame element plus all child elements

        Notes
        -----
        Includes the Frame object if:
        - It has text content set, OR
        - It's scrollable and needs scrolling (to receive focus and keyboard input), OR
        - It has an explicit id (for mouse event targeting, e.g., context menus)

        Otherwise, frame borders are rendered via the legacy _render_frames() path.
        """
        elements = []

        # Include Frame object if:
        # - It has text content, OR
        # - It's vertically scrollable (needs to receive mouse/keyboard input for scrolling), OR
        # - It's horizontally scrollable (overflow_x="scroll" or "auto"), OR
        # - It has an explicit id (for mouse event targeting)
        # Note: Scrollable frames must be in elements list even when _needs_scroll is False
        # to receive mouse wheel events
        needs_horizontal_scroll = self.frame.style.overflow_x in ("scroll", "auto")
        if (
            self.frame.content
            or self.frame.style.scrollable
            or needs_horizontal_scroll
            or self.frame.id
        ):
            elements.append(self.frame)

        # Add children elements and set parent_frame reference for clipping
        for child in self.content_container.children:
            child_elements = child.collect_elements()

            # Set parent_frame on all child elements for proper clipping.
            # This ensures content is clipped to frame bounds even for
            # non-scrollable frames.
            #
            # The element-level scroll_state_key synthesis below stays driven by
            # the flat child_elements list; the parent_frame *chain* is built
            # structurally (see _link_child_frames after the loop) so a nested
            # frame that is not itself a collected element still links into the
            # chain.
            if self.frame._has_children:
                for elem in child_elements:
                    if elem.parent_frame is None:
                        elem.parent_frame = self.frame

                    # Ensure scrollable child elements have scroll_state_key for persistence
                    # This allows scroll positions to survive re-renders even for unnamed elements
                    if (
                        self.frame.style.scrollable
                        and hasattr(elem, "scroll_state_key")
                        and hasattr(elem, "scroll_position")
                    ):
                        if not elem.scroll_state_key:
                            # Synthesize a stable key based on frame and element IDs
                            frame_id = self.frame.id or "frame"
                            elem_id = elem.id or elem.__class__.__name__
                            elem.scroll_state_key = f"_scroll_{frame_id}_{elem_id}"

            elements.extend(child_elements)

        # Link nested child FRAMES into the parent_frame chain. A nested frame
        # that is not itself a collected element (no id/content/scroll) is not
        # in child_elements, so the loop above never sets its parent_frame; its
        # descendants would then clip only to it and could paint outside this
        # outer frame when scrolled. Set it structurally from the current layout
        # tree (unconditional, so it is rebuilt cleanly each render rather than
        # walking the possibly-stale parent_frame chain on reused elements).
        if self.frame._has_children:
            self._link_child_frames(self.content_container)

        return elements

    def _link_child_frames(self, node: LayoutNode) -> None:
        """Set parent_frame on nested child frames reachable without crossing
        another frame.

        Recurses through plain containers (vstack/hstack) but stops at each
        nested :class:`FrameNode`, whose own ``collect_elements`` links the
        frames nested inside it. This builds the full frame chain level by
        level for correct multi-frame clipping.

        Parameters
        ----------
        node : LayoutNode
            Subtree to scan (typically this frame's content container).
        """
        for child in getattr(node, "children", []):
            if isinstance(child, FrameNode):
                child.frame.parent_frame = self.frame
                # Do not descend: child's interior links to child.frame.
            elif isinstance(child, Container):
                self._link_child_frames(child)


class SplitPanelNode(Container):
    """Split panel container node that wraps SplitPanel objects with two children.

    SplitPanelNode manages layout for resizable split panels with a divider
    between two child areas.

    Parameters
    ----------
    split_panel : SplitPanel
        The SplitPanel object providing split behavior and rendering
    first_child : LayoutNode, optional
        First (left or top) child node
    second_child : LayoutNode, optional
        Second (right or bottom) child node
    width : int, str, or Size, optional
        Width specification (default: "fill")
    height : int, str, or Size, optional
        Height specification (default: "fill")
    id : str, optional
        Node identifier

    Attributes
    ----------
    split_panel : SplitPanel
        The wrapped SplitPanel object
    first_child : LayoutNode or None
        First child layout node
    second_child : LayoutNode or None
        Second child layout node
    """

    def __init__(
        self,
        split_panel: SplitPanel,
        first_child: LayoutNode | None = None,
        second_child: LayoutNode | None = None,
        width: int | str | Size | None = None,
        height: int | str | Size | None = None,
        id: str | None = None,
    ) -> None:

        # Default to fill if not specified
        if width is None:
            width = "fill"
        if height is None:
            height = "fill"

        # Initialize container
        super().__init__(
            children=[],
            width=width,
            height=height,
            spacing=0,
            padding=0,
            margin=0,
            align_h="stretch",
            align_v="stretch",
            id=id,
        )

        self.split_panel = split_panel
        self.first_child = first_child
        self.second_child = second_child

    def add_child(self, child: LayoutNode) -> None:
        """Add a child node to the split panel.

        Parameters
        ----------
        child : LayoutNode
            Child node to add (first or second)

        Notes
        -----
        First call sets first_child, second call sets second_child.
        Additional calls are ignored with a warning.
        """
        if self.first_child is None:
            self.first_child = child
        elif self.second_child is None:
            self.second_child = child
        else:
            logger.warning(
                "SplitPanelNode already has 2 children, ignoring additional child"
            )

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate size constraints for the split panel and its children.

        Returns
        -------
        SizeConstraints
            Size constraints for the split panel
        """
        # Calculate constraints for both children
        first_constraints = SizeConstraints(min_width=0, min_height=0)
        second_constraints = SizeConstraints(min_width=0, min_height=0)

        if self.first_child:
            first_constraints = self.first_child.calculate_constraints()
        if self.second_child:
            second_constraints = self.second_child.calculate_constraints()

        # Calculate total constraints based on orientation
        if self.split_panel.orientation == "horizontal":
            # Side by side: widths add (plus divider), heights take max
            min_width = (
                first_constraints.min_width
                + second_constraints.min_width
                + 1  # Divider
            )
            min_height = max(
                first_constraints.min_height, second_constraints.min_height
            )
            preferred_width = (
                first_constraints.preferred_width
                + second_constraints.preferred_width
                + 1
            )
            preferred_height = max(
                first_constraints.preferred_height, second_constraints.preferred_height
            )
        else:
            # Stacked: widths take max, heights add (plus divider)
            min_width = max(first_constraints.min_width, second_constraints.min_width)
            min_height = (
                first_constraints.min_height
                + second_constraints.min_height
                + 1  # Divider
            )
            preferred_width = max(
                first_constraints.preferred_width, second_constraints.preferred_width
            )
            preferred_height = (
                first_constraints.preferred_height
                + second_constraints.preferred_height
                + 1
            )

        # Respect fixed width/height specifications
        if self.width_spec.is_fixed:
            min_width = self.width_spec.value
            preferred_width = self.width_spec.value

        if self.height_spec.is_fixed:
            min_height = self.height_spec.value
            preferred_height = self.height_spec.value

        self.constraints = SizeConstraints(
            min_width=min_width,
            min_height=min_height,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
        )
        return self.constraints

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign absolute position and size to the split panel and children.

        Parameters
        ----------
        x : int
            Left edge position
        y : int
            Top edge position
        width : int
            Total width
        height : int
            Total height
        """
        from wijjit.layout.bounds import Bounds

        # Set bounds for this node and the split panel element
        self.bounds = Bounds(x, y, width, height)
        self.split_panel.bounds = Bounds(x, y, width, height)

        # Calculate child sizes using the split panel's ratio
        if self.split_panel.orientation == "horizontal":
            available = width
        else:
            available = height

        first_size, second_size, divider_pos = self.split_panel._calculate_sizes(
            available
        )

        # Store calculated sizes in split panel for rendering
        self.split_panel._first_size = first_size
        self.split_panel._second_size = second_size
        self.split_panel._divider_pos = divider_pos

        # Assign bounds to children based on orientation
        if self.split_panel.orientation == "horizontal":
            # Side by side
            if self.first_child and not self.split_panel.first_collapsed:
                self.first_child.assign_bounds(x, y, first_size, height)
            if self.second_child and not self.split_panel.second_collapsed:
                self.second_child.assign_bounds(
                    x + divider_pos + 1, y, second_size, height
                )
        else:
            # Stacked
            if self.first_child and not self.split_panel.first_collapsed:
                self.first_child.assign_bounds(x, y, width, first_size)
            if self.second_child and not self.split_panel.second_collapsed:
                self.second_child.assign_bounds(
                    x, y + divider_pos + 1, width, second_size
                )

    def collect_elements(self) -> list[Element]:
        """Collect split panel and all child elements.

        Returns
        -------
        list of Element
            SplitPanel element plus all child elements
        """
        elements = [self.split_panel]

        if self.first_child and not self.split_panel.first_collapsed:
            elements.extend(self.first_child.collect_elements())
        if self.second_child and not self.split_panel.second_collapsed:
            elements.extend(self.second_child.collect_elements())

        return elements


class LayoutEngine:
    """Main layout engine that coordinates the layout process.

    The layout engine performs a two-pass layout:
    1. Bottom-up: Calculate size constraints
    2. Top-down: Assign absolute positions and sizes

    Parameters
    ----------
    root : LayoutNode
        Root of the layout tree
    width : int
        Available width
    height : int
        Available height

    Attributes
    ----------
    root : LayoutNode
        Root of the layout tree
    width : int
        Available width
    height : int
        Available height
    """

    def __init__(self, root: LayoutNode, width: int, height: int) -> None:
        self.root = root
        self.width = width
        self.height = height

    def layout(self) -> list[Element]:
        """Perform layout calculation.

        Returns
        -------
        list of Element
            All elements with assigned bounds
        """
        # Pass 1: Calculate constraints (bottom-up)
        self.root.calculate_constraints()

        # Pass 2: Assign bounds (top-down)
        self.root.assign_bounds(0, 0, self.width, self.height)

        # Collect all elements with bounds
        return self.root.collect_elements()
