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
