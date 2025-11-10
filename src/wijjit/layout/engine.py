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

from ..elements.base import Element
from .bounds import Bounds, Size, parse_margin, parse_size
from .frames import Frame


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
        width: int | str | Size = "auto",
        height: int | str | Size = "auto",
        id: str | None = None,
    ):
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
        # For fill elements, check if the element has a _dynamic_sizing flag
        # If so, skip rendering and use minimal constraints
        has_dynamic_sizing = (
            hasattr(self.element, "_dynamic_sizing") and self.element._dynamic_sizing
        )

        # Apply width/height specs if fixed
        if self.width_spec.is_fixed:
            min_width = self.width_spec.value
            preferred_width = self.width_spec.value
        elif has_dynamic_sizing and self.width_spec.is_fill:
            # Dynamic sizing elements report minimal constraints to avoid inflating parent
            # They will expand to fill when space is available via assign_bounds
            min_width = 10  # Reasonable minimum for visibility
            preferred_width = 10  # Keep preferred same as min to avoid inflating parent
        else:
            # Auto or other - measure content
            rendered = self.element.render()
            lines = rendered.split("\n")
            from ..terminal.ansi import visible_length

            content_width = max((visible_length(line) for line in lines), default=1)
            min_width = content_width
            preferred_width = content_width

        if self.height_spec.is_fixed:
            min_height = self.height_spec.value
            preferred_height = self.height_spec.value
        elif has_dynamic_sizing and self.height_spec.is_fill:
            # Dynamic sizing elements report minimal constraints to avoid inflating parent
            # They will expand to fill when space is available via assign_bounds
            min_height = 5  # Reasonable minimum for visibility (includes borders)
            preferred_height = 5  # Keep preferred same as min to avoid inflating parent
        else:
            # Auto or other - measure content
            if not hasattr(self, "_rendered_for_constraints"):
                rendered = self.element.render()
                lines = rendered.split("\n")
                self._rendered_for_constraints = True
            else:
                lines = self.element.render().split("\n")
            content_height = len(lines)
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
        children: list[LayoutNode] | None = None,
        width: int | str | Size = "auto",
        height: int | str | Size = "auto",
        spacing: int = 0,
        padding: int = 0,
        margin: int | tuple[int, int, int, int] = 0,
        align_h: HAlign = "stretch",
        align_v: VAlign = "stretch",
        id: str | None = None,
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
    ):
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
            if (
                self.align_h == "stretch"
                or child.width_spec.is_fill
                or child.width_spec.is_percentage
            ):
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
    ):
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
            if (
                self.align_v == "stretch"
                or child.height_spec.is_fill
                or child.height_spec.is_percentage
            ):
                child_height = content_height
                child_y = current_y
            elif child.height_spec.is_fixed:
                # Use fixed height - don't clamp to content_height
                child_height = child.height_spec.value
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
    ):

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
            child_constraints = self.content_container.calculate_constraints()
            child_min_w = child_constraints.min_width
            child_min_h = child_constraints.min_height
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
        from ..layout.bounds import Bounds

        # Apply margin
        margin_top, margin_right, margin_bottom, margin_left = self.margin
        content_x = x + margin_left
        content_y = y + margin_top
        content_width = width - margin_left - margin_right
        content_height = height - margin_top - margin_bottom

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

    def collect_elements(self) -> list[Element]:
        """Collect frame and all child elements.

        Returns
        -------
        list of Element
            Frame element plus all child elements

        Notes
        -----
        If the frame has child elements, only include the frame if it has
        content set. Otherwise, frame borders are rendered via the legacy
        _render_frames() path to avoid double-rendering conflicts.
        """
        elements = []

        # Only include Frame object if it has actual content to render
        # If frame has children, borders will be drawn by _render_frames()
        if self.frame.content:
            elements.append(self.frame)

        # Add children elements
        for child in self.content_container.children:
            elements.extend(child.collect_elements())

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

    def __init__(self, root: LayoutNode, width: int, height: int):
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
