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
from typing import List, Optional, Union, Tuple, Literal
from enum import Enum

from .bounds import Bounds, Size, parse_size, parse_margin
from ..elements.base import Element


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
    preferred_width: Optional[int] = None
    preferred_height: Optional[int] = None

    def __post_init__(self):
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
        width: Union[int, str, Size] = "auto",
        height: Union[int, str, Size] = "auto",
        id: Optional[str] = None,
    ):
        self.width_spec = parse_size(width)
        self.height_spec = parse_size(height)
        self.id = id
        self.constraints: Optional[SizeConstraints] = None
        self.bounds: Optional[Bounds] = None

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
    def collect_elements(self) -> List[Element]:
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
        width: Union[int, str, Size] = "auto",
        height: Union[int, str, Size] = "auto",
    ):
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
        # Get element's rendered content to measure
        rendered = self.element.render()
        lines = rendered.split("\n")

        # Import visible_length for ANSI-aware measurement
        from ..terminal.ansi import visible_length

        # Calculate actual content size
        content_width = max((visible_length(line) for line in lines), default=1)
        content_height = len(lines)

        # Apply width/height specs if fixed
        if self.width_spec.is_fixed:
            min_width = self.width_spec.value
            preferred_width = self.width_spec.value
        else:
            min_width = content_width
            preferred_width = content_width

        if self.height_spec.is_fixed:
            min_height = self.height_spec.value
            preferred_height = self.height_spec.value
        else:
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

    def collect_elements(self) -> List[Element]:
        """Return the wrapped element.

        Returns
        -------
        list of Element
            List containing the single element
        """
        return [self.element]


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
        children: Optional[List[LayoutNode]] = None,
        width: Union[int, str, Size] = "auto",
        height: Union[int, str, Size] = "auto",
        spacing: int = 0,
        padding: int = 0,
        margin: Union[int, Tuple[int, int, int, int]] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: Optional[str] = None,
    ):
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

    def collect_elements(self) -> List[Element]:
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
        children: Optional[List[LayoutNode]] = None,
        width: Union[int, str, Size] = "fill",
        height: Union[int, str, Size] = "auto",
        spacing: int = 0,
        padding: int = 0,
        margin: Union[int, Tuple[int, int, int, int]] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: Optional[str] = None,
    ):
        super().__init__(children, width, height, spacing, padding, margin, align_h, align_v, id)

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
        total_height = sum(c.preferred_height for c in child_constraints)
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
            total_with_spacing = total_children_height + self.spacing * (len(self.children) - 1)

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
            if self.align_h == "stretch" or child.width_spec.is_fill or child.width_spec.is_percentage:
                child_width = content_width
                child_x = current_x
            elif child.width_spec.is_fixed:
                child_width = child.width_spec.value
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
        children: Optional[List[LayoutNode]] = None,
        width: Union[int, str, Size] = "auto",
        height: Union[int, str, Size] = "fill",
        spacing: int = 0,
        padding: int = 0,
        margin: Union[int, Tuple[int, int, int, int]] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: Optional[str] = None,
    ):
        super().__init__(children, width, height, spacing, padding, margin, align_h, align_v, id)

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
        total_width = sum(c.preferred_width for c in child_constraints)
        total_width += self.spacing * (len(self.children) - 1)

        # Height: max of children
        max_child_height = max(c.preferred_height for c in child_constraints)

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
            total_with_spacing = total_children_width + self.spacing * (len(self.children) - 1)

            # Calculate empty space and offset
            if total_with_spacing < content_width + self.spacing * (len(self.children) - 1):
                actual_content_width = content_width + self.spacing * (len(self.children) - 1)
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
            if self.align_v == "stretch" or child.height_spec.is_fill or child.height_spec.is_percentage:
                child_height = content_height
                child_y = current_y
            elif child.height_spec.is_fixed:
                child_height = child.height_spec.value
            else:
                child_height = (
                    child.constraints.preferred_height
                    if child.constraints
                    else content_height
                )

            # Ensure height doesn't exceed content height
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

    def __init__(self, root: LayoutNode, width: int, height: int):
        self.root = root
        self.width = width
        self.height = height

    def layout(self) -> List[Element]:
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
