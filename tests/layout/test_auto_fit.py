"""Tests for auto-fit layout shrinking.

Auto-fit is the rule that a container whose children ask for more space than the
container has shrinks those children to fit rather than letting them overflow
and clip. It exists because templates hard-code sizes (``width=120``) that are
wrong on any terminal smaller than the author's.

Covers:
- The :func:`shrink_to_fit` primitive in isolation
- HStack width shrinking (packed, justified, and with fill siblings)
- VStack height shrinking and cross-axis width clamping
- The ``AUTO_FIT_LAYOUT`` opt-out
"""

import pytest

from tests.layout.test_engine import MockElement
from wijjit.layout.engine import (
    ElementNode,
    FrameNode,
    HStack,
    VStack,
    auto_fit_enabled,
    set_auto_fit,
    shrink_to_fit,
)
from wijjit.layout.frames import Frame, FrameStyle


@pytest.fixture(autouse=True)
def restore_auto_fit():
    """Restore the process-wide auto-fit flag after each test."""
    previous = auto_fit_enabled()
    yield
    set_auto_fit(previous)


class TestShrinkToFit:
    """Tests for the shrink_to_fit primitive."""

    def test_no_overflow_returns_input_unchanged(self):
        assert shrink_to_fit([10, 20], [1, 1], 40) == [10, 20]

    def test_exact_fit_returns_input_unchanged(self):
        assert shrink_to_fit([10, 20], [1, 1], 30) == [10, 20]

    def test_shrinks_proportionally_to_slack(self):
        # Slack is 9 and 19; the 10 units of overflow are split in that ratio.
        result = shrink_to_fit([10, 20], [1, 1], 20)
        assert sum(result) == 20
        assert result == [7, 13]

    def test_result_sums_exactly_to_available(self):
        # Integer division leaves a remainder that must be handed out, not lost.
        for available in range(10, 60):
            result = shrink_to_fit([30, 25, 17], [5, 5, 5], available)
            assert sum(result) == min(72, max(available, 15))

    def test_floors_at_minimums(self):
        result = shrink_to_fit([20, 20], [18, 2], 10)
        assert result[0] >= 18
        assert result[1] >= 2

    def test_minimums_that_cannot_fit_still_overflow(self):
        # The layout is genuinely too small; clipping is all that is left.
        assert shrink_to_fit([50], [40], 10) == [40]

    def test_zero_slack_is_left_alone(self):
        assert shrink_to_fit([10, 10], [10, 10], 5) == [10, 10]

    def test_empty_input(self):
        assert shrink_to_fit([], [], 10) == []

    def test_disabled_returns_input_unchanged(self):
        set_auto_fit(False)
        assert shrink_to_fit([10, 20], [1, 1], 20) == [10, 20]


class TestHStackAutoFit:
    """Tests for HStack shrinking along its main axis."""

    def _two_fixed(self, w1: int, w2: int, spacing: int = 0) -> HStack:
        return HStack(
            children=[
                ElementNode(MockElement(width=w1, height=1), width=w1, height=1),
                ElementNode(MockElement(width=w2, height=1), width=w2, height=1),
            ],
            spacing=spacing,
        )

    def test_overcommitted_children_shrink_to_fit(self):
        stack = self._two_fixed(60, 60)
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 80, 5)

        right = max(c.bounds.right for c in stack.children)
        assert right <= 80

    def test_gaps_are_accounted_for(self):
        stack = self._two_fixed(60, 60, spacing=4)
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 80, 5)

        assert max(c.bounds.right for c in stack.children) <= 80
        # The gap survives the shrink rather than being eaten by a child.
        assert stack.children[1].bounds.x - stack.children[0].bounds.right == 4

    def test_fitting_children_are_untouched(self):
        stack = self._two_fixed(20, 30)
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 80, 5)

        assert stack.children[0].bounds.width == 20
        assert stack.children[1].bounds.width == 30

    def test_fill_sibling_does_not_starve_fixed_children(self):
        # Regression: reserving room for the fill child up front shrank the
        # fixed child even in rows that already fit.
        stack = HStack(
            children=[
                ElementNode(MockElement(width=46, height=1), width=46, height=1),
                ElementNode(MockElement(width=80, height=1), width="fill", height=1),
            ],
            spacing=2,
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 96, 5)

        assert stack.children[0].bounds.width == 46
        assert stack.children[1].bounds.width == 48

    def test_justified_positions_match_shrunk_widths(self):
        stack = HStack(
            children=[
                ElementNode(MockElement(width=60, height=1), width=60, height=1),
                ElementNode(MockElement(width=60, height=1), width=60, height=1),
            ],
            justify="space-between",
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 80, 5)

        first, second = stack.children
        # Positions are derived from the same widths that get assigned, so the
        # children must not overlap.
        assert first.bounds.right <= second.bounds.x
        assert second.bounds.right <= 80

    def test_cross_axis_height_is_clamped(self):
        stack = HStack(
            children=[ElementNode(MockElement(width=5, height=40), width=5, height=40)]
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 80, 10)

        assert stack.children[0].bounds.height <= 10

    def test_disabled_leaves_overflow_alone(self):
        set_auto_fit(False)
        stack = self._two_fixed(60, 60)
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 80, 5)

        assert stack.children[0].bounds.width == 60
        assert stack.children[1].bounds.width == 60


class TestVStackAutoFit:
    """Tests for VStack shrinking and cross-axis clamping."""

    def test_overcommitted_heights_shrink_to_fit(self):
        stack = VStack(
            children=[
                ElementNode(MockElement(width=10, height=20), width=10, height=20),
                ElementNode(MockElement(width=10, height=20), width=10, height=20),
            ]
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 40, 24)

        assert max(c.bounds.bottom for c in stack.children) <= 24

    def test_fixed_width_child_is_clamped_to_column(self):
        # A pinned width wider than the parent used to run off the right edge.
        stack = VStack(
            children=[ElementNode(MockElement(width=90, height=1), width=90, height=1)]
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 40, 10)

        assert stack.children[0].bounds.width == 40

    def test_fitting_children_are_untouched(self):
        stack = VStack(
            children=[
                ElementNode(MockElement(width=10, height=3), width=10, height=3),
                ElementNode(MockElement(width=10, height=4), width=10, height=4),
            ]
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 40, 24)

        assert stack.children[0].bounds.height == 3
        assert stack.children[1].bounds.height == 4

    def test_disabled_leaves_overflow_alone(self):
        set_auto_fit(False)
        stack = VStack(
            children=[ElementNode(MockElement(width=90, height=1), width=90, height=1)]
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 40, 10)

        assert stack.children[0].bounds.width == 90


class TestFrameAutoFit:
    """Tests for frames shrinking inside an over-committed row."""

    def test_side_by_side_frames_keep_their_borders(self):
        # The wizard_progress regression: two 30-wide frames in a 58-wide row
        # used to clip the second frame's right border away.
        def make_frame(title: str) -> FrameNode:
            return FrameNode(
                frame=Frame(width=30, height=6, style=FrameStyle(title=title)),
                children=[
                    ElementNode(MockElement(width=10, height=2), width=10, height=2)
                ],
                width=30,
                height=6,
            )

        stack = HStack(
            children=[make_frame("Team"), make_frame("Approvals")], spacing=2
        )
        stack.calculate_constraints()
        stack.assign_bounds(0, 0, 58, 8)

        assert max(c.bounds.right for c in stack.children) <= 58
        # Both frames stay wide enough to draw two borders plus content.
        for child in stack.children:
            assert child.bounds.width >= 4

    def test_scrollable_frame_does_not_shrink_its_content(self):
        # A viewport exists to hold content taller than itself. Shrinking the
        # content to fit would leave nothing to scroll.
        container = VStack(
            children=[
                ElementNode(MockElement(width=10, height=20), width=10, height=20)
            ]
        )
        container.no_shrink_height = True
        container.calculate_constraints()
        container.assign_bounds(0, 0, 40, 6)

        assert container.children[0].bounds.height == 20


class TestAutoFitEndToEnd:
    """Auto-fit driven through the real render pipeline."""

    TEMPLATE = """
{% frame title="Outer" border="double" width=120 height=30 %}
  {% hstack spacing=2 %}
    {% frame title="Left" border="single" width=54 height=10 %}
      left
    {% endframe %}
    {% frame title="Right" border="single" width=42 height=10 %}
      right
    {% endframe %}
  {% endhstack %}
{% endframe %}
"""

    def _screen(self, width: int, height: int) -> list[str]:
        from wijjit.testing import WijjitHarness, app_from_template

        app = app_from_template(self.TEMPLATE)
        with WijjitHarness(app, size=(width, height)) as harness:
            harness.tick()
            return harness.screen().splitlines()

    def test_hard_coded_widths_fit_a_narrow_terminal(self):
        # 54 + 2 + 42 needs 98 columns; the terminal has 80.
        lines = self._screen(80, 24)
        row = next(line for line in lines if "Left" in line)

        # Every box on the row closes: no border is clipped away.
        assert row.count("┌") == 2
        assert row.count("┐") == 2
        assert all(len(line.rstrip()) <= 80 for line in lines)

    def test_wide_terminal_keeps_the_declared_widths(self):
        lines = self._screen(120, 30)
        row = next(line for line in lines if "Left" in line)

        # Nothing to reclaim, so the author's sizes are honored exactly.
        left = row[row.index("┌") : row.index("┐") + 1]
        assert len(left) == 54
