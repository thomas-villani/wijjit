"""Tests for SplitPanel element and layout node."""

from __future__ import annotations

import pytest

from wijjit.elements.base import Element, TextElement
from wijjit.layout.bounds import Bounds
from wijjit.layout.engine import ElementNode, SplitPanelNode
from wijjit.layout.splitpanel import SplitPanel


class TestSplitPanelRatio:
    """Tests for ratio parsing and calculation."""

    def test_parse_ratio_equal(self):
        """Test parsing '50:50' ratio."""
        panel = SplitPanel(ratio="50:50")
        assert panel.current_ratio == (0.5, 0.5)

    def test_parse_ratio_unequal(self):
        """Test parsing '30:70' ratio."""
        panel = SplitPanel(ratio="30:70")
        assert panel.current_ratio == (0.3, 0.7)

    def test_parse_ratio_simple(self):
        """Test parsing '1:2' ratio (converts to 33:67)."""
        panel = SplitPanel(ratio="1:2")
        assert abs(panel.current_ratio[0] - 1 / 3) < 0.001
        assert abs(panel.current_ratio[1] - 2 / 3) < 0.001

    def test_parse_ratio_invalid_format(self):
        """Test that invalid ratio format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ratio"):
            SplitPanel(ratio="50")

    def test_parse_ratio_invalid_values(self):
        """Test that invalid ratio values raise ValueError."""
        with pytest.raises(ValueError, match="Invalid ratio"):
            SplitPanel(ratio="0:0")


class TestSplitPanelSizeCalculation:
    """Tests for size calculation based on ratio."""

    def test_calculate_sizes_horizontal_equal(self):
        """Test size calculation for horizontal split with equal ratio."""
        panel = SplitPanel(orientation="horizontal", ratio="50:50")
        # Total width 101 (100 usable + 1 divider)
        first, second, divider_pos = panel._calculate_sizes(101)
        assert first == 50
        assert second == 50
        assert divider_pos == 50

    def test_calculate_sizes_horizontal_unequal(self):
        """Test size calculation for horizontal split with unequal ratio."""
        panel = SplitPanel(orientation="horizontal", ratio="30:70")
        # Total width 101 (100 usable + 1 divider)
        first, second, divider_pos = panel._calculate_sizes(101)
        assert first == 30
        assert second == 70
        assert divider_pos == 30

    def test_calculate_sizes_vertical_equal(self):
        """Test size calculation for vertical split with equal ratio."""
        panel = SplitPanel(orientation="vertical", ratio="50:50")
        # Total height 51 (50 usable + 1 divider)
        first, second, divider_pos = panel._calculate_sizes(51)
        assert first == 25
        assert second == 25
        assert divider_pos == 25

    def test_min_constraints_first(self):
        """Test minimum size enforcement for first panel."""
        panel = SplitPanel(ratio="10:90", min_first=20)
        # Ratio would give 10 to first, but min is 20
        first, second, divider_pos = panel._calculate_sizes(101)
        assert first >= 20

    def test_min_constraints_second(self):
        """Test minimum size enforcement for second panel."""
        panel = SplitPanel(ratio="90:10", min_second=20)
        # Ratio would give 10 to second, but min is 20
        first, second, divider_pos = panel._calculate_sizes(101)
        assert second >= 20


class TestSplitPanelCollapse:
    """Tests for collapse behavior."""

    def test_collapse_first(self):
        """Test collapsing first panel."""
        panel = SplitPanel(ratio="50:50", collapsible="first")
        panel.collapse_panel("first")
        assert panel.first_collapsed is True
        assert panel.current_ratio == (0.0, 1.0)

    def test_collapse_second(self):
        """Test collapsing second panel."""
        panel = SplitPanel(ratio="50:50", collapsible="second")
        panel.collapse_panel("second")
        assert panel.second_collapsed is True
        assert panel.current_ratio == (1.0, 0.0)

    def test_restore_first(self):
        """Test restoring collapsed first panel."""
        panel = SplitPanel(ratio="30:70", collapsible="first")
        panel.collapse_panel("first")
        panel.restore_panel("first")
        assert panel.first_collapsed is False
        assert panel.current_ratio == (0.3, 0.7)

    def test_restore_second(self):
        """Test restoring collapsed second panel."""
        panel = SplitPanel(ratio="30:70", collapsible="second")
        panel.collapse_panel("second")
        panel.restore_panel("second")
        assert panel.second_collapsed is False
        assert panel.current_ratio == (0.3, 0.7)

    def test_collapsed_sizes_first(self):
        """Test that collapsed first panel has zero size."""
        panel = SplitPanel(ratio="50:50", collapsible="first")
        panel.collapse_panel("first")
        first, second, divider_pos = panel._calculate_sizes(101)
        assert first == 0
        assert second == 100
        assert divider_pos == 0

    def test_collapsed_sizes_second(self):
        """Test that collapsed second panel has zero size."""
        panel = SplitPanel(ratio="50:50", collapsible="second")
        panel.collapse_panel("second")
        first, second, divider_pos = panel._calculate_sizes(101)
        assert first == 100
        assert second == 0


class TestSplitPanelDividerHitTest:
    """Tests for divider hit testing."""

    def test_is_on_divider_horizontal(self):
        """Test divider hit test for horizontal split."""
        panel = SplitPanel(orientation="horizontal", ratio="50:50")
        panel.bounds = Bounds(0, 0, 101, 50)
        panel._first_size, panel._second_size, panel._divider_pos = (
            panel._calculate_sizes(101)
        )
        # Divider is at x=50
        assert panel._is_on_divider(50, 0) is True
        assert panel._is_on_divider(50, 25) is True
        assert panel._is_on_divider(49, 0) is False
        assert panel._is_on_divider(51, 0) is False

    def test_is_on_divider_vertical(self):
        """Test divider hit test for vertical split."""
        panel = SplitPanel(orientation="vertical", ratio="50:50")
        panel.bounds = Bounds(0, 0, 80, 51)
        panel._first_size, panel._second_size, panel._divider_pos = (
            panel._calculate_sizes(51)
        )
        # Divider is at y=25
        assert panel._is_on_divider(0, 25) is True
        assert panel._is_on_divider(40, 25) is True
        assert panel._is_on_divider(0, 24) is False
        assert panel._is_on_divider(0, 26) is False


class TestSplitPanelAdjustRatio:
    """Tests for keyboard-based ratio adjustment."""

    def test_adjust_ratio_positive(self):
        """Test adjusting ratio by positive delta."""
        panel = SplitPanel(ratio="50:50")
        panel.bounds = Bounds(0, 0, 101, 50)
        panel._adjust_ratio(0.1)
        assert abs(panel.current_ratio[0] - 0.6) < 0.01

    def test_adjust_ratio_negative(self):
        """Test adjusting ratio by negative delta."""
        panel = SplitPanel(ratio="50:50")
        panel.bounds = Bounds(0, 0, 101, 50)
        panel._adjust_ratio(-0.1)
        assert abs(panel.current_ratio[0] - 0.4) < 0.01

    def test_adjust_ratio_clamp_min(self):
        """Test that ratio adjustment respects minimum constraints."""
        panel = SplitPanel(ratio="50:50", min_first=20)
        panel.bounds = Bounds(0, 0, 101, 50)
        # Try to adjust below minimum
        panel._adjust_ratio(-0.9)
        # Should be clamped to respect min_first
        assert panel.current_ratio[0] >= 0.2


class TestSplitPanelIntrinsicSize:
    """Tests for intrinsic size calculation."""

    def test_intrinsic_size_horizontal(self):
        """Test intrinsic size for horizontal split."""
        panel = SplitPanel(orientation="horizontal")
        # Create mock children with known sizes
        first = TextElement(text="First")
        first.get_intrinsic_size = lambda: (20, 5)
        second = TextElement(text="Second")
        second.get_intrinsic_size = lambda: (30, 8)
        panel.set_children(first, second)

        width, height = panel.get_intrinsic_size()
        # Side by side: widths add + 1 for divider
        assert width == 51
        # Heights take max
        assert height == 8

    def test_intrinsic_size_vertical(self):
        """Test intrinsic size for vertical split."""
        panel = SplitPanel(orientation="vertical")
        # Create mock children with known sizes
        first = TextElement(text="First")
        first.get_intrinsic_size = lambda: (20, 5)
        second = TextElement(text="Second")
        second.get_intrinsic_size = lambda: (30, 8)
        panel.set_children(first, second)

        width, height = panel.get_intrinsic_size()
        # Widths take max
        assert width == 30
        # Stacked: heights add + 1 for divider
        assert height == 14


class TestSplitPanelEphemeralState:
    """Tests for ephemeral state preservation."""

    def test_get_ephemeral_state(self):
        """Test getting ephemeral state."""
        panel = SplitPanel(ratio="30:70")
        panel.collapse_panel("first")
        state = panel.get_ephemeral_state()
        assert "_ratio" in state
        assert "_first_collapsed" in state
        assert "_second_collapsed" in state
        assert state["_ratio"] == (0.0, 1.0)
        assert state["_first_collapsed"] is True

    def test_restore_ephemeral_state(self):
        """Test restoring ephemeral state."""
        panel = SplitPanel(ratio="50:50")
        state = {
            "_ratio": (0.3, 0.7),
            "_first_collapsed": False,
            "_second_collapsed": True,
        }
        panel.restore_ephemeral_state(state)
        assert panel.current_ratio == (0.3, 0.7)
        assert panel.first_collapsed is False
        assert panel.second_collapsed is True


class TestSplitPanelNode:
    """Tests for SplitPanelNode layout integration."""

    def test_add_children(self):
        """Test adding children to SplitPanelNode."""
        panel = SplitPanel()
        node = SplitPanelNode(split_panel=panel)

        first = ElementNode(TextElement(text="First"))
        second = ElementNode(TextElement(text="Second"))

        node.add_child(first)
        node.add_child(second)

        assert node.first_child is first
        assert node.second_child is second

    def test_add_extra_child_warning(self):
        """Test that adding more than 2 children logs warning."""
        panel = SplitPanel()
        node = SplitPanelNode(split_panel=panel)

        first = ElementNode(TextElement(text="First"))
        second = ElementNode(TextElement(text="Second"))
        third = ElementNode(TextElement(text="Third"))

        node.add_child(first)
        node.add_child(second)
        # Third child should be ignored (with warning)
        node.add_child(third)

        assert node.first_child is first
        assert node.second_child is second

    def test_calculate_constraints_horizontal(self):
        """Test constraint calculation for horizontal split."""
        panel = SplitPanel(orientation="horizontal")
        node = SplitPanelNode(split_panel=panel)

        # Create children with known constraints
        first = ElementNode(TextElement(text="First"))
        first.calculate_constraints = lambda: type(
            "C",
            (),
            {
                "min_width": 20,
                "min_height": 5,
                "preferred_width": 20,
                "preferred_height": 5,
            },
        )()
        second = ElementNode(TextElement(text="Second"))
        second.calculate_constraints = lambda: type(
            "C",
            (),
            {
                "min_width": 30,
                "min_height": 8,
                "preferred_width": 30,
                "preferred_height": 8,
            },
        )()

        node.first_child = first
        node.second_child = second

        constraints = node.calculate_constraints()
        # Side by side: widths add + 1 for divider
        assert constraints.min_width == 51
        # Heights take max
        assert constraints.min_height == 8

    def test_calculate_constraints_vertical(self):
        """Test constraint calculation for vertical split."""
        panel = SplitPanel(orientation="vertical")
        node = SplitPanelNode(split_panel=panel)

        # Create children with known constraints
        first = ElementNode(TextElement(text="First"))
        first.calculate_constraints = lambda: type(
            "C",
            (),
            {
                "min_width": 20,
                "min_height": 5,
                "preferred_width": 20,
                "preferred_height": 5,
            },
        )()
        second = ElementNode(TextElement(text="Second"))
        second.calculate_constraints = lambda: type(
            "C",
            (),
            {
                "min_width": 30,
                "min_height": 8,
                "preferred_width": 30,
                "preferred_height": 8,
            },
        )()

        node.first_child = first
        node.second_child = second

        constraints = node.calculate_constraints()
        # Widths take max
        assert constraints.min_width == 30
        # Stacked: heights add + 1 for divider
        assert constraints.min_height == 14

    def test_assign_bounds_horizontal(self):
        """Test bounds assignment for horizontal split."""
        panel = SplitPanel(orientation="horizontal", ratio="50:50")
        node = SplitPanelNode(split_panel=panel)

        first = ElementNode(TextElement(text="First"))
        second = ElementNode(TextElement(text="Second"))
        node.first_child = first
        node.second_child = second

        # Calculate constraints first
        node.calculate_constraints()

        # Assign bounds
        node.assign_bounds(0, 0, 101, 50)

        assert node.bounds.width == 101
        assert node.bounds.height == 50
        assert first.bounds.width == 50
        assert second.bounds.width == 50
        assert second.bounds.x == 51  # After divider

    def test_assign_bounds_vertical(self):
        """Test bounds assignment for vertical split."""
        panel = SplitPanel(orientation="vertical", ratio="50:50")
        node = SplitPanelNode(split_panel=panel)

        first = ElementNode(TextElement(text="First"))
        second = ElementNode(TextElement(text="Second"))
        node.first_child = first
        node.second_child = second

        # Calculate constraints first
        node.calculate_constraints()

        # Assign bounds
        node.assign_bounds(0, 0, 80, 51)

        assert node.bounds.width == 80
        assert node.bounds.height == 51
        assert first.bounds.height == 25
        assert second.bounds.height == 25
        assert second.bounds.y == 26  # After divider

    def test_collect_elements(self):
        """Test element collection from SplitPanelNode."""
        panel = SplitPanel()
        node = SplitPanelNode(split_panel=panel)

        first_elem = TextElement(text="First")
        second_elem = TextElement(text="Second")
        first = ElementNode(first_elem)
        second = ElementNode(second_elem)
        node.first_child = first
        node.second_child = second

        elements = node.collect_elements()

        assert panel in elements
        assert first_elem in elements
        assert second_elem in elements

    def test_collect_elements_collapsed_first(self):
        """Test that collapsed first panel's elements are not collected."""
        panel = SplitPanel(collapsible="first")
        panel.collapse_panel("first")
        node = SplitPanelNode(split_panel=panel)

        first_elem = TextElement(text="First")
        second_elem = TextElement(text="Second")
        first = ElementNode(first_elem)
        second = ElementNode(second_elem)
        node.first_child = first
        node.second_child = second

        elements = node.collect_elements()

        assert panel in elements
        assert first_elem not in elements
        assert second_elem in elements

    def test_collect_elements_collapsed_second(self):
        """Test that collapsed second panel's elements are not collected."""
        panel = SplitPanel(collapsible="second")
        panel.collapse_panel("second")
        node = SplitPanelNode(split_panel=panel)

        first_elem = TextElement(text="First")
        second_elem = TextElement(text="Second")
        first = ElementNode(first_elem)
        second = ElementNode(second_elem)
        node.first_child = first
        node.second_child = second

        elements = node.collect_elements()

        assert panel in elements
        assert first_elem in elements
        assert second_elem not in elements


class TestNestedSplitPanels:
    """Tests for nested split panels."""

    def test_nested_layout(self):
        """Test nested split panel layout calculation."""
        # Outer: horizontal split
        outer_panel = SplitPanel(orientation="horizontal", ratio="30:70")
        outer_node = SplitPanelNode(split_panel=outer_panel)

        # Inner: vertical split (as second child of outer)
        inner_panel = SplitPanel(orientation="vertical", ratio="50:50")
        inner_node = SplitPanelNode(split_panel=inner_panel)

        # Create leaf elements
        left_elem = TextElement(text="Left")
        top_elem = TextElement(text="Top")
        bottom_elem = TextElement(text="Bottom")

        left = ElementNode(left_elem)
        top = ElementNode(top_elem)
        bottom = ElementNode(bottom_elem)

        inner_node.add_child(top)
        inner_node.add_child(bottom)

        outer_node.add_child(left)
        outer_node.add_child(inner_node)

        # Calculate and assign bounds
        outer_node.calculate_constraints()
        outer_node.assign_bounds(0, 0, 101, 51)

        # Verify outer split
        assert left.bounds.width == 30
        assert inner_node.bounds.width == 70

        # Verify inner split
        assert top.bounds.height == 25
        assert bottom.bounds.height == 25
        assert bottom.bounds.y == 26
