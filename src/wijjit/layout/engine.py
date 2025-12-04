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
from enum import Enum
from typing import Literal

from wijjit.elements.base import Element
from wijjit.layout.bounds import Bounds, Size, parse_margin, parse_size
from wijjit.layout.frames import Frame


class Direction(Enum):
    """Layout direction for stacking containers."""

    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


# Type aliases for alignment options
HAlign = Literal["left", "center", "right", "stretch"]
VAlign = Literal["top", "middle", "bottom", "stretch"]


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
    """

    min_width: int
    min_height: int
    preferred_width: int | None = None
    preferred_height: int | None = None

    def __post_init__(self) -> None:
        """Set preferred sizes to min sizes if not specified."""
        if self.preferred_width is None:
            self.preferred_width = self.min_width
        if self.preferred_height is None:
            self.preferred_height = self.min_height


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
            min_width = 10  # Reasonable minimum for visibility
            preferred_width = 10  # Keep preferred same as min to avoid inflating parent
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
            min_height = 5  # Reasonable minimum for visibility (includes borders)
            preferred_height = 5  # Keep preferred same as min to avoid inflating parent
        else:
            # Auto or other - get intrinsic size from element
            _, content_height = self.element.get_intrinsic_size()
            min_height = content_height
            preferred_height = content_height

        self.constraints = SizeConstraints(
            min_width=min_width,
            min_height=min_height,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
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
        padding: int = 0,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: str | None = None,
    ) -> None:
        super().__init__(width, height, id)
        self.children = children or []
        self.spacing = spacing
        self.padding = padding
        self.margin = parse_margin(margin)
        self.align_h = align_h
        self.align_v = align_v

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
        padding: int = 0,
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

        if not self.children:
            # Empty container
            min_size = 2 * self.padding
            self.constraints = SizeConstraints(
                min_width=min_size + margin_left + margin_right,
                min_height=min_size + margin_top + margin_bottom,
                preferred_width=min_size + margin_left + margin_right,
                preferred_height=min_size + margin_top + margin_bottom,
            )
            return self.constraints

        # Calculate children constraints first
        child_constraints = [child.calculate_constraints() for child in self.children]

        # Width: max of children
        max_child_width = max(c.preferred_width for c in child_constraints)

        # Height: sum of children plus spacing
        # For children with height=fill, use min_height instead of preferred_height
        # to avoid inflating the parent
        total_height = 0
        for i, child in enumerate(self.children):
            constraint = child_constraints[i]
            if child.height_spec.is_fill:
                # Fill children contribute only their minimum
                total_height += constraint.min_height
            else:
                # Fixed/auto children contribute their preferred size
                total_height += constraint.preferred_height
        total_height += self.spacing * (len(self.children) - 1)

        # Add padding and margins
        min_width = max_child_width + 2 * self.padding + margin_left + margin_right
        min_height = total_height + 2 * self.padding + margin_top + margin_bottom

        # Apply width/height specs if fixed
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

        # Calculate available space for children (after margins and padding)
        content_width = width - 2 * self.padding - margin_left - margin_right
        content_height = height - 2 * self.padding - margin_top - margin_bottom

        # Save original content_height for alignment calculation
        original_content_height = content_height
        content_height -= self.spacing * (len(self.children) - 1)

        # Count fill children
        fill_children = [c for c in self.children if c.height_spec.is_fill]
        fixed_children = [c for c in self.children if not c.height_spec.is_fill]

        # Calculate fixed heights
        fixed_height = sum(
            c.constraints.preferred_height if c.constraints else 0
            for c in fixed_children
        )

        # Distribute remaining height to fill children
        remaining_height = max(0, content_height - fixed_height)
        fill_height_each = (
            remaining_height // len(fill_children) if fill_children else 0
        )

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
        current_y = y + margin_top + self.padding + vertical_offset
        current_x = x + margin_left + self.padding

        for child in self.children:
            if child.height_spec.is_fill:
                child_height = fill_height_each
            elif child.height_spec.is_fixed:
                child_height = child.height_spec.value
            elif child.height_spec.is_percentage:
                child_height = int(content_height * child.height_spec.get_percentage())
            else:
                child_height = (
                    child.constraints.preferred_height if child.constraints else 1
                )

            # Width handling based on alignment
            # Note: Fixed-width children should NOT be stretched even when align_h is "stretch"
            # This ensures elements with explicit widths are respected
            if child.width_spec.is_fixed:
                # Respect the child's explicit fixed width
                child_width = child.width_spec.value
            elif (
                self.align_h == "stretch"
                or child.width_spec.is_fill
                or child.width_spec.is_percentage
            ):
                child_width = content_width
                child_x = current_x
            else:
                child_width = (
                    child.constraints.preferred_width
                    if child.constraints
                    else content_width
                )

            # Ensure width doesn't exceed content width
            child_width = min(child_width, content_width)

            # Apply horizontal alignment if child is narrower than available space
            if self.align_h != "stretch" and child_width < content_width:
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

    Arranges children horizontally with optional spacing.

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
        width: int | str | Size = "auto",
        height: int | str | Size = "auto",
        spacing: int = 0,
        padding: int = 0,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: str | None = None,
    ) -> None:
        super().__init__(
            children, width, height, spacing, padding, margin, align_h, align_v, id
        )

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate constraints for horizontal stack.

        Width is the sum of children widths plus spacing.
        Height is the maximum of children heights.

        Returns
        -------
        SizeConstraints
            Calculated constraints
        """
        margin_top, margin_right, margin_bottom, margin_left = self.margin

        if not self.children:
            # Empty container
            min_size = 2 * self.padding
            self.constraints = SizeConstraints(
                min_width=min_size + margin_left + margin_right,
                min_height=min_size + margin_top + margin_bottom,
                preferred_width=min_size + margin_left + margin_right,
                preferred_height=min_size + margin_top + margin_bottom,
            )
            return self.constraints

        # Calculate children constraints first
        child_constraints = [child.calculate_constraints() for child in self.children]

        # Width: sum of children plus spacing
        # For children with width=fill, use min_width instead of preferred_width
        # to avoid inflating the parent
        total_width = 0
        for i, child in enumerate(self.children):
            constraint = child_constraints[i]
            if child.width_spec.is_fill:
                # Fill children contribute only their minimum
                total_width += constraint.min_width
            else:
                # Fixed/auto children contribute their preferred size
                total_width += constraint.preferred_width
        total_width += self.spacing * (len(self.children) - 1)

        # Height: max of children
        # For children with height=fill, use min_height instead of preferred_height
        max_child_height = 0
        for i, child in enumerate(self.children):
            constraint = child_constraints[i]
            if child.height_spec.is_fill:
                # Fill children contribute only their minimum
                height = constraint.min_height
            else:
                # Fixed/auto children contribute their preferred size
                height = constraint.preferred_height
            max_child_height = max(max_child_height, height)

        # Add padding and margins
        min_width = total_width + 2 * self.padding + margin_left + margin_right
        min_height = max_child_height + 2 * self.padding + margin_top + margin_bottom

        # Apply width/height specs if fixed
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
        """Assign bounds to container and position children horizontally.

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

        # Calculate available space for children (after margins and padding)
        content_width = width - 2 * self.padding - margin_left - margin_right
        content_height = height - 2 * self.padding - margin_top - margin_bottom
        content_width -= self.spacing * (len(self.children) - 1)

        # Count fill children
        fill_children = [c for c in self.children if c.width_spec.is_fill]
        fixed_children = [c for c in self.children if not c.width_spec.is_fill]

        # Calculate fixed widths
        fixed_width = sum(
            c.constraints.preferred_width if c.constraints else 0
            for c in fixed_children
        )

        # Distribute remaining width to fill children
        remaining_width = max(0, content_width - fixed_width)
        fill_width_each = remaining_width // len(fill_children) if fill_children else 0

        # Calculate horizontal alignment offset
        # If align_h is not "stretch", we need to position the group of children
        if self.align_h != "stretch" and not fill_children:
            # Calculate total width of all children
            total_children_width = fixed_width
            total_with_spacing = total_children_width + self.spacing * (
                len(self.children) - 1
            )

            # Calculate empty space and offset
            if total_with_spacing < content_width + self.spacing * (
                len(self.children) - 1
            ):
                actual_content_width = content_width + self.spacing * (
                    len(self.children) - 1
                )
                empty_space = actual_content_width - total_with_spacing
                if self.align_h == "center":
                    horizontal_offset = empty_space // 2
                elif self.align_h == "right":
                    horizontal_offset = empty_space
                else:  # "left"
                    horizontal_offset = 0
            else:
                horizontal_offset = 0
        else:
            horizontal_offset = 0

        # Position children (offset by margins and horizontal alignment)
        current_x = x + margin_left + self.padding + horizontal_offset
        current_y = y + margin_top + self.padding

        for child in self.children:
            if child.width_spec.is_fill:
                child_width = fill_width_each
            elif child.width_spec.is_fixed:
                child_width = child.width_spec.value
            elif child.width_spec.is_percentage:
                child_width = int(content_width * child.width_spec.get_percentage())
            else:
                child_width = (
                    child.constraints.preferred_width if child.constraints else 1
                )

            # Height handling based on alignment
            # Note: Fixed-height children should NOT be stretched even when align_v is "stretch"
            # This ensures elements with explicit heights are respected
            if child.height_spec.is_fixed:
                # Respect the child's explicit fixed height
                child_height = child.height_spec.value
            elif (
                self.align_v == "stretch"
                or child.height_spec.is_fill
                or child.height_spec.is_percentage
            ):
                child_height = content_height
                child_y = current_y
            else:
                child_height = (
                    child.constraints.preferred_height
                    if child.constraints
                    else content_height
                )
                # Only clamp non-fixed heights to content height
                child_height = min(child_height, content_height)

            # Apply vertical alignment if child is shorter than available space
            if self.align_v != "stretch" and child_height < content_height:
                if self.align_v == "middle":
                    child_y = current_y + (content_height - child_height) // 2
                elif self.align_v == "bottom":
                    child_y = current_y + (content_height - child_height)
                else:  # "top" or default
                    child_y = current_y
            else:
                child_y = current_y

            child.assign_bounds(current_x, child_y, child_width, child_height)
            current_x += child_width + self.spacing


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
    col_gap : int, optional
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
    col_gap : int
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
        col_gap: int = 0,
        width: int | str | Size = "fill",
        height: int | str | Size = "auto",
        padding: int = 0,
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
        self.col_gap = col_gap

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

        for child in self.children:
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
                raise ValueError(
                    f"Grid overflow: Cannot place child. "
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

        if not self.children:
            min_size = 2 * self.padding
            self.constraints = SizeConstraints(
                min_width=min_size + margin_left + margin_right,
                min_height=min_size + margin_top + margin_bottom,
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
                    current_width += self.col_gap * (cell.colspan - 1)

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
        total_width = sum(self._col_widths) + self.col_gap * (self.cols - 1)
        total_height = sum(self._row_heights) + self.row_gap * (self.rows - 1)

        # Add padding and margins
        min_width = total_width + 2 * self.padding + margin_left + margin_right
        min_height = total_height + 2 * self.padding + margin_top + margin_bottom

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

        # Calculate content area
        content_x = x + margin_left + self.padding
        content_y = y + margin_top + self.padding

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
            current_x += self._col_widths[c] + self.col_gap

        # Assign bounds to each child based on its cell position and span
        for child, cell in self._children_placed:
            cell_x = col_x_positions[cell.col]
            cell_y = row_y_positions[cell.row]

            # Calculate spanned width (sum of columns + gaps)
            cell_width = sum(
                self._col_widths[c] for c in range(cell.col, cell.col + cell.colspan)
            )
            cell_width += self.col_gap * (cell.colspan - 1)

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

    def calculate_constraints(self) -> SizeConstraints:
        """Calculate size constraints for the frame and its children.

        Returns
        -------
        SizeConstraints
            Size constraints for the frame
        """
        # Calculate children constraints
        if self.content_container.children:
            # Has layout children (which may include text converted to TextElement)
            child_constraints = self.content_container.calculate_constraints()
            child_min_w = child_constraints.min_width
            child_min_h = child_constraints.min_height

            # If frame ALSO has direct text content (edge case), add it to height
            # This shouldn't normally happen (text becomes TextElement child), but handle it
            if self.frame.content:
                child_min_h += len(self.frame.content)
        else:
            # No layout children, but check if frame has text content
            if self.frame.content:
                # Use number of content lines as minimum height
                child_min_h = len(self.frame.content)
                child_min_w = 0
            else:
                child_min_w = 0
                child_min_h = 0

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

        # Respect fixed width/height specifications
        # If width_spec is fixed, use that instead of calculated width
        if self.width_spec.is_fixed:
            total_min_w = self.width_spec.value + margin_left + margin_right
            preferred_width = self.width_spec.value + margin_left + margin_right
        else:
            preferred_width = total_min_w

        if self.height_spec.is_fixed:
            total_min_h = self.height_spec.value + margin_top + margin_bottom
            preferred_height = self.height_spec.value + margin_top + margin_bottom
        else:
            preferred_height = total_min_h

        self.constraints = SizeConstraints(
            min_width=total_min_w,
            min_height=total_min_h,
            preferred_width=preferred_width,
            preferred_height=preferred_height,
        )
        return self.constraints

    def assign_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Assign absolute position and size.

        Parameters
        ----------
        x : int
            X position
        y : int
            Y position
        width : int
            Available width
        height : int
            Available height
        """
        from wijjit.layout.bounds import Bounds

        # Apply margin
        margin_top, margin_right, margin_bottom, margin_left = self.margin

        # Calculate actual dimensions, respecting fixed size specifications
        # This is important for root frames with explicit dimensions
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
            self.content_container.assign_bounds(
                inner_x, inner_y, inner_width, inner_height
            )

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

            # Find maximum bottom across all descendants
            max_bottom = find_max_bottom(self.content_container, inner_y)

            # Set child content height on frame for scrolling calculations
            # Always call this when there are children, even if calculated height is 0
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

        # Add children elements and set parent_frame reference if frame is scrollable
        for child in self.content_container.children:
            child_elements = child.collect_elements()

            # If this frame is scrollable with children, set parent_frame on child elements
            # Only set if not already set by a more immediate scrollable parent
            if self.frame.style.scrollable and self.frame._has_children:
                for elem in child_elements:
                    if elem.parent_frame is None:
                        elem.parent_frame = self.frame

                    # Ensure scrollable child elements have scroll_state_key for persistence
                    # This allows scroll positions to survive re-renders even for unnamed elements
                    if hasattr(elem, "scroll_state_key") and hasattr(
                        elem, "scroll_position"
                    ):
                        if not elem.scroll_state_key:
                            # Synthesize a stable key based on frame and element IDs
                            frame_id = self.frame.id or "frame"
                            elem_id = elem.id or elem.__class__.__name__
                            elem.scroll_state_key = f"_scroll_{frame_id}_{elem_id}"

            elements.extend(child_elements)

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
