"""Tests for layout engine.

This module tests the layout calculation system including:
- Size constraint calculation (bottom-up)
- Position assignment (top-down)
- VStack and HStack containers
- Various sizing modes (fixed, fill, percentage, auto)
"""

from wijjit.layout.engine import (
    ElementNode,
    VStack,
    HStack,
    LayoutEngine,
    SizeConstraints,
)
from wijjit.elements.base import Element
from wijjit.layout.bounds import Bounds


class MockElement(Element):
    """Mock element for testing.

    Parameters
    ----------
    width : int
        Element width
    height : int
        Element height
    id : str, optional
        Element identifier
    """

    def __init__(self, width: int = 10, height: int = 1, id: str = None):
        super().__init__(id)
        self.mock_width = width
        self.mock_height = height

    def render(self) -> str:
        """Render mock element.

        Returns
        -------
        str
            Mock content with specified dimensions
        """
        return "\n".join(["X" * self.mock_width] * self.mock_height)


class TestElementNode:
    """Tests for ElementNode."""

    def test_calculate_constraints_auto(self):
        """Test constraint calculation with auto sizing.

        ElementNode should calculate size from element content.
        """
        element = MockElement(width=20, height=3)
        node = ElementNode(element)

        constraints = node.calculate_constraints()

        assert constraints.min_width == 20
        assert constraints.min_height == 3
        assert constraints.preferred_width == 20
        assert constraints.preferred_height == 3

    def test_calculate_constraints_fixed_width(self):
        """Test constraint calculation with fixed width."""
        element = MockElement(width=20, height=3)
        node = ElementNode(element, width=30)

        constraints = node.calculate_constraints()

        assert constraints.min_width == 30
        assert constraints.preferred_width == 30

    def test_calculate_constraints_fixed_height(self):
        """Test constraint calculation with fixed height."""
        element = MockElement(width=20, height=3)
        node = ElementNode(element, height=5)

        constraints = node.calculate_constraints()

        assert constraints.min_height == 5
        assert constraints.preferred_height == 5

    def test_assign_bounds(self):
        """Test bounds assignment to element."""
        element = MockElement()
        node = ElementNode(element)

        node.assign_bounds(10, 20, 30, 5)

        assert node.bounds == Bounds(x=10, y=20, width=30, height=5)
        assert element.bounds == Bounds(x=10, y=20, width=30, height=5)

    def test_collect_elements(self):
        """Test element collection."""
        element = MockElement(id="test")
        node = ElementNode(element)

        elements = node.collect_elements()

        assert len(elements) == 1
        assert elements[0] is element


class TestVStack:
    """Tests for VStack container."""

    def test_empty_container_constraints(self):
        """Test empty VStack constraints."""
        vstack = VStack()

        constraints = vstack.calculate_constraints()

        # Empty container should have minimal size (just padding)
        assert constraints.min_width == 0
        assert constraints.min_height == 0

    def test_empty_container_with_padding(self):
        """Test empty VStack with padding."""
        vstack = VStack(padding=2)

        constraints = vstack.calculate_constraints()

        # Padding should be included
        assert constraints.min_width == 4  # 2*padding
        assert constraints.min_height == 4

    def test_single_child_constraints(self):
        """Test VStack with single child."""
        child = ElementNode(MockElement(width=20, height=3))
        vstack = VStack(children=[child])

        constraints = vstack.calculate_constraints()

        # Should match child size
        assert constraints.preferred_width == 20
        assert constraints.preferred_height == 3

    def test_multiple_children_width(self):
        """Test VStack width is maximum of children."""
        child1 = ElementNode(MockElement(width=20, height=2))
        child2 = ElementNode(MockElement(width=30, height=2))
        child3 = ElementNode(MockElement(width=15, height=2))
        vstack = VStack(children=[child1, child2, child3])

        constraints = vstack.calculate_constraints()

        # Width should be max of children (30)
        assert constraints.preferred_width == 30

    def test_multiple_children_height_sum(self):
        """Test VStack height is sum of children."""
        child1 = ElementNode(MockElement(width=20, height=2))
        child2 = ElementNode(MockElement(width=20, height=3))
        child3 = ElementNode(MockElement(width=20, height=1))
        vstack = VStack(children=[child1, child2, child3])

        constraints = vstack.calculate_constraints()

        # Height should be sum (2+3+1 = 6)
        assert constraints.preferred_height == 6

    def test_spacing_in_height(self):
        """Test spacing is added to height."""
        child1 = ElementNode(MockElement(width=20, height=2))
        child2 = ElementNode(MockElement(width=20, height=2))
        child3 = ElementNode(MockElement(width=20, height=2))
        vstack = VStack(children=[child1, child2, child3], spacing=1)

        constraints = vstack.calculate_constraints()

        # Height = 2+2+2 + 2*spacing = 8
        assert constraints.preferred_height == 8

    def test_padding_in_size(self):
        """Test padding is added to size."""
        child = ElementNode(MockElement(width=20, height=3))
        vstack = VStack(children=[child], padding=2)

        constraints = vstack.calculate_constraints()

        # Width = 20 + 2*2 = 24, Height = 3 + 2*2 = 7
        assert constraints.preferred_width == 24
        assert constraints.preferred_height == 7

    def test_position_children_vertically(self):
        """Test children are positioned vertically."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        child3 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2, child3])

        # Calculate constraints first
        vstack.calculate_constraints()

        # Assign bounds
        vstack.assign_bounds(0, 0, 20, 10)

        # Check children are stacked vertically
        assert child1.bounds.y == 0
        assert child2.bounds.y == 2
        assert child3.bounds.y == 4

    def test_position_with_spacing(self):
        """Test children positioned with spacing."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2], spacing=3)

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 20, 10)

        # Spacing between children
        assert child1.bounds.y == 0
        assert child2.bounds.y == 5  # 2 + 3

    def test_position_with_padding(self):
        """Test children positioned with padding."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], padding=2)

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 20, 10)

        # Padding offset
        assert child.bounds.x == 2
        assert child.bounds.y == 2

    def test_fill_height_distribution(self):
        """Test fill height distributed among children."""
        child1 = ElementNode(MockElement(width=10, height=2), height="fill")
        child2 = ElementNode(MockElement(width=10, height=2), height="fill")
        vstack = VStack(children=[child1, child2])

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 20, 20)

        # Each child gets half the available height
        assert child1.bounds.height == 10
        assert child2.bounds.height == 10

    def test_mixed_fixed_and_fill(self):
        """Test mix of fixed and fill heights."""
        child1 = ElementNode(MockElement(width=10, height=2), height=5)
        child2 = ElementNode(MockElement(width=10, height=2), height="fill")
        vstack = VStack(children=[child1, child2])

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 20, 20)

        # Child1 gets fixed height, child2 gets remaining
        assert child1.bounds.height == 5
        assert child2.bounds.height == 15


class TestHStack:
    """Tests for HStack container."""

    def test_empty_container_constraints(self):
        """Test empty HStack constraints."""
        hstack = HStack()

        constraints = hstack.calculate_constraints()

        assert constraints.min_width == 0
        assert constraints.min_height == 0

    def test_single_child_constraints(self):
        """Test HStack with single child."""
        child = ElementNode(MockElement(width=20, height=3))
        hstack = HStack(children=[child])

        constraints = hstack.calculate_constraints()

        assert constraints.preferred_width == 20
        assert constraints.preferred_height == 3

    def test_multiple_children_width_sum(self):
        """Test HStack width is sum of children."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=15, height=2))
        child3 = ElementNode(MockElement(width=20, height=2))
        hstack = HStack(children=[child1, child2, child3])

        constraints = hstack.calculate_constraints()

        # Width should be sum (10+15+20 = 45)
        assert constraints.preferred_width == 45

    def test_multiple_children_height_max(self):
        """Test HStack height is maximum of children."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=5))
        child3 = ElementNode(MockElement(width=10, height=3))
        hstack = HStack(children=[child1, child2, child3])

        constraints = hstack.calculate_constraints()

        # Height should be max (5)
        assert constraints.preferred_height == 5

    def test_spacing_in_width(self):
        """Test spacing is added to width."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        child3 = ElementNode(MockElement(width=10, height=2))
        hstack = HStack(children=[child1, child2, child3], spacing=2)

        constraints = hstack.calculate_constraints()

        # Width = 10+10+10 + 2*spacing = 34
        assert constraints.preferred_width == 34

    def test_position_children_horizontally(self):
        """Test children are positioned horizontally."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=15, height=2))
        child3 = ElementNode(MockElement(width=20, height=2))
        hstack = HStack(children=[child1, child2, child3])

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 60, 10)

        # Check children are positioned horizontally
        assert child1.bounds.x == 0
        assert child2.bounds.x == 10
        assert child3.bounds.x == 25  # 10 + 15

    def test_position_with_spacing(self):
        """Test children positioned with spacing."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        hstack = HStack(children=[child1, child2], spacing=5)

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Spacing between children
        assert child1.bounds.x == 0
        assert child2.bounds.x == 15  # 10 + 5

    def test_fill_width_distribution(self):
        """Test fill width distributed among children."""
        child1 = ElementNode(MockElement(width=10, height=2), width="fill")
        child2 = ElementNode(MockElement(width=10, height=2), width="fill")
        hstack = HStack(children=[child1, child2])

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 40, 10)

        # Each child gets half the available width
        assert child1.bounds.width == 20
        assert child2.bounds.width == 20


class TestLayoutEngine:
    """Tests for LayoutEngine."""

    def test_simple_layout(self):
        """Test simple single-element layout."""
        element = MockElement(width=20, height=3, id="test")
        root = ElementNode(element)
        engine = LayoutEngine(root, width=80, height=24)

        elements = engine.layout()

        assert len(elements) == 1
        assert elements[0].bounds == Bounds(x=0, y=0, width=80, height=24)

    def test_vstack_layout(self):
        """Test VStack layout calculation."""
        child1 = ElementNode(MockElement(width=10, height=2, id="c1"))
        child2 = ElementNode(MockElement(width=15, height=3, id="c2"))
        root = VStack(children=[child1, child2], spacing=1)

        engine = LayoutEngine(root, width=80, height=24)
        elements = engine.layout()

        assert len(elements) == 2
        assert elements[0].id == "c1"
        assert elements[1].id == "c2"
        # Verify bounds were assigned
        assert elements[0].bounds is not None
        assert elements[1].bounds is not None

    def test_nested_layout(self):
        """Test nested container layout."""
        # Create nested structure: VStack containing HStack containing elements
        elem1 = ElementNode(MockElement(width=10, height=2, id="e1"))
        elem2 = ElementNode(MockElement(width=10, height=2, id="e2"))
        hstack = HStack(children=[elem1, elem2], spacing=2)

        elem3 = ElementNode(MockElement(width=20, height=3, id="e3"))
        root = VStack(children=[hstack, elem3], spacing=1)

        engine = LayoutEngine(root, width=80, height=24)
        elements = engine.layout()

        # Should collect all leaf elements
        assert len(elements) == 3
        assert all(e.bounds is not None for e in elements)

    def test_percentage_width(self):
        """Test percentage-based width.

        NOTE: Currently VStack treats percentage widths the same as fill.
        TODO: Implement proper percentage width calculation.
        """
        child = ElementNode(MockElement(width=10, height=2), width="50%")
        root = VStack(children=[child])

        engine = LayoutEngine(root, width=80, height=24)
        elements = engine.layout()

        # Currently percentage widths get full width (like fill)
        # TODO: Should be 40 (50% of 80) when properly implemented
        assert elements[0].bounds.width == 80

    def test_fill_width(self):
        """Test fill width behavior."""
        child = ElementNode(MockElement(width=10, height=2), width="fill")
        root = VStack(children=[child])

        engine = LayoutEngine(root, width=80, height=24)
        elements = engine.layout()

        # Child should fill container width
        assert elements[0].bounds.width == 80


class TestSizeConstraints:
    """Tests for SizeConstraints dataclass."""

    def test_default_preferred(self):
        """Test preferred sizes default to min sizes."""
        constraints = SizeConstraints(min_width=10, min_height=5)

        assert constraints.preferred_width == 10
        assert constraints.preferred_height == 5

    def test_explicit_preferred(self):
        """Test explicit preferred sizes."""
        constraints = SizeConstraints(
            min_width=10, min_height=5, preferred_width=20, preferred_height=10
        )

        assert constraints.preferred_width == 20
        assert constraints.preferred_height == 10


class TestMarginSupport:
    """Tests for margin support in containers."""

    def test_uniform_margin_in_constraints(self):
        """Test uniform margins are added to size constraints."""
        child = ElementNode(MockElement(width=20, height=3))
        vstack = VStack(children=[child], margin=2)

        constraints = vstack.calculate_constraints()

        # Width = 20 + 2*2 (margin) = 24
        # Height = 3 + 2*2 (margin) = 7
        assert constraints.preferred_width == 24
        assert constraints.preferred_height == 7

    def test_tuple_margin_in_constraints(self):
        """Test per-side margins are added to size constraints."""
        child = ElementNode(MockElement(width=20, height=3))
        vstack = VStack(children=[child], margin=(1, 2, 3, 4))  # top, right, bottom, left

        constraints = vstack.calculate_constraints()

        # Width = 20 + 4 (left) + 2 (right) = 26
        # Height = 3 + 1 (top) + 3 (bottom) = 7
        assert constraints.preferred_width == 26
        assert constraints.preferred_height == 7

    def test_margin_offset_in_assign_bounds(self):
        """Test margins offset children positioning."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], margin=(1, 2, 3, 4))  # top, right, bottom, left

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 20, 10)

        # Child should be offset by left and top margins
        # x = 0 + 4 (left margin) = 4
        # y = 0 + 1 (top margin) = 1
        assert child.bounds.x == 4
        assert child.bounds.y == 1

    def test_margin_with_padding(self):
        """Test margins work with padding."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], margin=2, padding=1)

        constraints = vstack.calculate_constraints()

        # Width = 10 + 2*1 (padding) + 2*2 (margin) = 16
        # Height = 2 + 2*1 (padding) + 2*2 (margin) = 8
        assert constraints.preferred_width == 16
        assert constraints.preferred_height == 8


class TestFrameLevelAlignment:
    """Tests for frame-level alignment (align_h, align_v) in containers."""

    def test_horizontal_alignment_left(self):
        """Test horizontal left alignment in VStack."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], align_h="left")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 10)

        # Child should be left-aligned
        # x = 0 (left aligned)
        # width = 10 (child's preferred width)
        assert child.bounds.x == 0
        assert child.bounds.width == 10

    def test_horizontal_alignment_center(self):
        """Test horizontal center alignment in VStack."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], align_h="center")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 10)

        # Child should be center-aligned
        # Available width = 30, child width = 10
        # x = 0 + (30 - 10) // 2 = 10
        assert child.bounds.x == 10
        assert child.bounds.width == 10

    def test_horizontal_alignment_right(self):
        """Test horizontal right alignment in VStack."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], align_h="right")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 10)

        # Child should be right-aligned
        # Available width = 30, child width = 10
        # x = 0 + (30 - 10) = 20
        assert child.bounds.x == 20
        assert child.bounds.width == 10

    def test_horizontal_alignment_stretch(self):
        """Test horizontal stretch alignment in VStack (default)."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], align_h="stretch")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 10)

        # Child should stretch to fill width
        # x = 0, width = 30 (full width)
        assert child.bounds.x == 0
        assert child.bounds.width == 30

    def test_vertical_alignment_top(self):
        """Test vertical top alignment in HStack."""
        child = ElementNode(MockElement(width=10, height=2))
        hstack = HStack(children=[child], align_v="top")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Child should be top-aligned
        # y = 0 (top aligned)
        # height = 2 (child's preferred height)
        assert child.bounds.y == 0
        assert child.bounds.height == 2

    def test_vertical_alignment_middle(self):
        """Test vertical middle alignment in HStack."""
        child = ElementNode(MockElement(width=10, height=2))
        hstack = HStack(children=[child], align_v="middle")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Child should be middle-aligned
        # Available height = 10, child height = 2
        # y = 0 + (10 - 2) // 2 = 4
        assert child.bounds.y == 4
        assert child.bounds.height == 2

    def test_vertical_alignment_bottom(self):
        """Test vertical bottom alignment in HStack."""
        child = ElementNode(MockElement(width=10, height=2))
        hstack = HStack(children=[child], align_v="bottom")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Child should be bottom-aligned
        # Available height = 10, child height = 2
        # y = 0 + (10 - 2) = 8
        assert child.bounds.y == 8
        assert child.bounds.height == 2

    def test_vertical_alignment_stretch(self):
        """Test vertical stretch alignment in HStack (default)."""
        child = ElementNode(MockElement(width=10, height=2))
        hstack = HStack(children=[child], align_v="stretch")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Child should stretch to fill height
        # y = 0, height = 10 (full height)
        assert child.bounds.y == 0
        assert child.bounds.height == 10


class TestVStackVerticalAlignment:
    """Tests for vertical alignment in VStack (positioning groups of children)."""

    def test_vstack_vertical_alignment_top(self):
        """Test VStack vertical top alignment with multiple children."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2], align_v="top")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # Children should be positioned at the top (no offset)
        assert child1.bounds.y == 0
        assert child2.bounds.y == 2

    def test_vstack_vertical_alignment_middle(self):
        """Test VStack vertical middle alignment with multiple children."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2], align_v="middle")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # Total children height = 2 + 2 = 4
        # Available height = 20
        # Offset = (20 - 4) // 2 = 8
        assert child1.bounds.y == 8
        assert child2.bounds.y == 10

    def test_vstack_vertical_alignment_bottom(self):
        """Test VStack vertical bottom alignment with multiple children."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2], align_v="bottom")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # Total children height = 2 + 2 = 4
        # Available height = 20
        # Offset = 20 - 4 = 16
        assert child1.bounds.y == 16
        assert child2.bounds.y == 18

    def test_vstack_vertical_alignment_with_spacing(self):
        """Test VStack vertical middle alignment with spacing."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        child3 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2, child3], spacing=1, align_v="middle")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # Total children height = 2 + 2 + 2 = 6
        # Total spacing = 2 * 1 = 2
        # Total height = 6 + 2 = 8
        # Available height = 20
        # Offset = (20 - 8) // 2 = 6
        assert child1.bounds.y == 6
        assert child2.bounds.y == 9  # 6 + 2 + 1 (spacing)
        assert child3.bounds.y == 12  # 9 + 2 + 1 (spacing)

    def test_vstack_vertical_alignment_with_padding(self):
        """Test VStack vertical middle alignment with padding."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2], padding=2, align_v="middle")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # Content area = 20 - 2*2 (padding) = 16
        # Total children height = 2 + 2 = 4
        # Offset within content area = (16 - 4) // 2 = 6
        # Actual y position = 2 (padding) + 6 (offset) = 8
        assert child1.bounds.y == 8
        assert child2.bounds.y == 10

    def test_vstack_vertical_alignment_stretch_default(self):
        """Test VStack vertical stretch alignment (default behavior)."""
        child1 = ElementNode(MockElement(width=10, height=2))
        child2 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2], align_v="stretch")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # With stretch, children should be positioned from the top (no offset)
        assert child1.bounds.y == 0
        assert child2.bounds.y == 2

    def test_vstack_vertical_alignment_with_fill_child(self):
        """Test VStack vertical alignment with fill children (should disable alignment)."""
        child1 = ElementNode(MockElement(width=10, height=2), height="fill")
        child2 = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child1, child2], align_v="middle")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # When there are fill children, vertical alignment should be disabled
        # Children should be positioned from the top
        assert child1.bounds.y == 0


class TestHStackHorizontalAlignment:
    """Tests for horizontal alignment in HStack (positioning groups of children)."""

    def test_hstack_horizontal_alignment_left(self):
        """Test HStack horizontal left alignment with multiple children."""
        child1 = ElementNode(MockElement(width=5, height=2))
        child2 = ElementNode(MockElement(width=5, height=2))
        hstack = HStack(children=[child1, child2], align_h="left")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Children should be positioned at the left (no offset)
        assert child1.bounds.x == 0
        assert child2.bounds.x == 5

    def test_hstack_horizontal_alignment_center(self):
        """Test HStack horizontal center alignment with multiple children."""
        child1 = ElementNode(MockElement(width=5, height=2))
        child2 = ElementNode(MockElement(width=5, height=2))
        hstack = HStack(children=[child1, child2], align_h="center")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Total children width = 5 + 5 = 10
        # Available width = 30
        # Offset = (30 - 10) // 2 = 10
        assert child1.bounds.x == 10
        assert child2.bounds.x == 15

    def test_hstack_horizontal_alignment_right(self):
        """Test HStack horizontal right alignment with multiple children."""
        child1 = ElementNode(MockElement(width=5, height=2))
        child2 = ElementNode(MockElement(width=5, height=2))
        hstack = HStack(children=[child1, child2], align_h="right")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 30, 10)

        # Total children width = 5 + 5 = 10
        # Available width = 30
        # Offset = 30 - 10 = 20
        assert child1.bounds.x == 20
        assert child2.bounds.x == 25

    def test_hstack_horizontal_alignment_with_spacing(self):
        """Test HStack horizontal center alignment with spacing."""
        child1 = ElementNode(MockElement(width=5, height=2))
        child2 = ElementNode(MockElement(width=5, height=2))
        child3 = ElementNode(MockElement(width=5, height=2))
        hstack = HStack(children=[child1, child2, child3], spacing=2, align_h="center")

        hstack.calculate_constraints()
        hstack.assign_bounds(0, 0, 40, 10)

        # Total children width = 5 + 5 + 5 = 15
        # Total spacing = 2 * 2 = 4
        # Total width = 15 + 4 = 19
        # Available width = 40
        # Offset = (40 - 19) // 2 = 10
        assert child1.bounds.x == 10
        assert child2.bounds.x == 17  # 10 + 5 + 2 (spacing)
        assert child3.bounds.x == 24  # 17 + 5 + 2 (spacing)


class TestMarginAndAlignmentIntegration:
    """Integration tests for margin and alignment working together."""

    def test_margin_with_horizontal_alignment(self):
        """Test margin combined with horizontal alignment."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], margin=2, align_h="center")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 10)

        # Content area after margins = 30 - 2*2 (horizontal margins) = 26
        # Child width = 10
        # Horizontal offset = (26 - 10) // 2 = 8
        # Actual x = 0 + 2 (left margin) + 8 (alignment offset) = 10
        assert child.bounds.x == 10
        # Vertical position with top margin
        assert child.bounds.y == 2

    def test_margin_with_vertical_alignment(self):
        """Test margin combined with vertical alignment."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], margin=2, align_v="middle")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # Content area after margins = 20 - 2*2 (vertical margins) = 16
        # Child height = 2
        # Vertical offset = (16 - 2) // 2 = 7
        # Actual y = 0 + 2 (top margin) + 7 (alignment offset) = 9
        assert child.bounds.y == 9

    def test_margin_padding_alignment_combined(self):
        """Test margin, padding, and alignment all combined."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(
            children=[child], margin=2, padding=1, align_h="center", align_v="middle"
        )

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 40, 20)

        # Content area after margins = 40 - 2*2 (horizontal margins) = 36
        # Content area after padding = 36 - 2*1 (horizontal padding) = 34
        # Child width = 10
        # Horizontal offset = (34 - 10) // 2 = 12
        # Actual x = 0 + 2 (left margin) + 1 (left padding) + 12 (alignment) = 15
        assert child.bounds.x == 15

        # Vertical: area after margins = 20 - 2*2 = 16
        # Area after padding = 16 - 2*1 = 14
        # Child height = 2
        # Vertical offset = (14 - 2) // 2 = 6
        # Actual y = 0 + 2 (top margin) + 1 (top padding) + 6 (alignment) = 9
        assert child.bounds.y == 9

    def test_nested_containers_with_alignment(self):
        """Test nested containers with different alignments."""
        # Create nested structure: outer VStack with centered HStack
        # Set HStack height to "auto" so it doesn't fill (default is "fill")
        elem1 = ElementNode(MockElement(width=5, height=2, id="e1"))
        elem2 = ElementNode(MockElement(width=5, height=2, id="e2"))
        inner_hstack = HStack(children=[elem1, elem2], spacing=2, height="auto")

        outer_vstack = VStack(children=[inner_hstack], align_h="center", align_v="middle")

        outer_vstack.calculate_constraints()
        outer_vstack.assign_bounds(0, 0, 40, 20)

        # HStack size = 5 + 5 + 2 (spacing) = 12 width, 2 height
        # Horizontal centering: (40 - 12) // 2 = 14
        # Vertical centering: (20 - 2) // 2 = 9
        assert inner_hstack.bounds.x == 14
        assert inner_hstack.bounds.y == 9
        assert inner_hstack.bounds.height == 2  # Should have auto height, not fill


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_margin(self):
        """Test margin=0 behaves like no margin."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], margin=0)

        constraints = vstack.calculate_constraints()
        assert constraints.preferred_width == 10
        assert constraints.preferred_height == 2

        vstack.assign_bounds(0, 0, 20, 10)
        assert child.bounds.x == 0
        assert child.bounds.y == 0

    def test_margin_tuple_with_zeros(self):
        """Test margin tuple with some zero values."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], margin=(0, 2, 0, 3))

        constraints = vstack.calculate_constraints()
        # Width = 10 + 3 (left) + 2 (right) = 15
        # Height = 2 + 0 (top) + 0 (bottom) = 2
        assert constraints.preferred_width == 15
        assert constraints.preferred_height == 2

    def test_alignment_when_child_fills_space(self):
        """Test alignment has no effect when child fills available space."""
        child = ElementNode(MockElement(width=10, height=2))
        vstack = VStack(children=[child], align_h="center")

        vstack.calculate_constraints()
        # Assign bounds exactly matching child size
        vstack.assign_bounds(0, 0, 10, 2)

        # No extra space, so centering has no effect
        assert child.bounds.x == 0

    def test_multiple_children_mixed_sizes_alignment(self):
        """Test alignment with multiple children of different sizes."""
        child1 = ElementNode(MockElement(width=5, height=2))
        child2 = ElementNode(MockElement(width=15, height=3))
        child3 = ElementNode(MockElement(width=10, height=1))
        vstack = VStack(children=[child1, child2, child3], align_h="center")

        vstack.calculate_constraints()
        vstack.assign_bounds(0, 0, 30, 20)

        # VStack width is determined by widest child (15)
        # Each child should be centered within the 30-width container
        # child1 (width=5): offset = (30 - 5) // 2 = 12
        # child2 (width=15): offset = (30 - 15) // 2 = 7
        # child3 (width=10): offset = (30 - 10) // 2 = 10
        assert child1.bounds.x == 12
        assert child2.bounds.x == 7
        assert child3.bounds.x == 10
