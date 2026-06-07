"""Tests for focus management."""

from wijjit.core.focus import FocusManager
from wijjit.elements.base import Element
from wijjit.rendering.paint_context import PaintContext


# Test element implementation
class FocusableElement(Element):
    """Test focusable element."""

    def __init__(self, id=None):
        super().__init__(id)
        self.focusable = True

    def render(self):
        return f"Element {self.id}"

    def render_to(self, ctx: PaintContext) -> None:
        """Render element to cell buffer.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds
        """
        # Simple mock implementation for testing
        text = f"Element {self.id}"
        for i, char in enumerate(text):
            ctx.buffer.write_at(i, 0, char)


class TestFocusManager:
    """Tests for FocusManager class."""

    def test_create_focus_manager(self):
        """Test creating a focus manager."""
        manager = FocusManager()
        assert len(manager.elements) == 0
        assert manager.current_index is None

    def test_set_elements(self):
        """Test setting focusable elements."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])

        assert len(manager.elements) == 2
        assert elem1 in manager.elements
        assert elem2 in manager.elements

    def test_set_elements_filters_non_focusable(self):
        """Test that non-focusable elements are filtered out."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem2.focusable = False  # Make it non-focusable

        manager.set_elements([elem1, elem2])

        assert len(manager.elements) == 1
        assert elem1 in manager.elements
        assert elem2 not in manager.elements

    def test_no_focus_on_initial_set(self):
        """Test that no element is focused when elements are first set.

        This allows the first user navigation action (Tab/Shift+Tab) to focus
        the first (or last) element, avoiding the visual issue where focus
        appears to "skip" the first element.
        """
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])

        assert not elem1.focused
        assert not elem2.focused
        assert manager.current_index is None

    def test_get_focused_element(self):
        """Test getting the currently focused element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])

        # Initially no element is focused
        assert manager.get_focused_element() is None

        # Focus first element explicitly
        manager.focus_first()
        focused = manager.get_focused_element()
        assert focused == elem1

    def test_get_focused_element_none(self):
        """Test getting focused element when none exists."""
        manager = FocusManager()
        assert manager.get_focused_element() is None

    def test_focus_next(self):
        """Test moving focus to next element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        manager.set_elements([elem1, elem2, elem3])

        # Initially no element is focused - first focus_next focuses first element
        assert manager.current_index is None
        manager.focus_next()
        assert elem1.focused
        assert manager.current_index == 0

        manager.focus_next()
        assert not elem1.focused
        assert elem2.focused
        assert manager.current_index == 1

        manager.focus_next()
        assert not elem2.focused
        assert elem3.focused
        assert manager.current_index == 2

    def test_focus_next_wraps_around(self):
        """Test that focus wraps from last to first element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])
        manager.focus_first()  # Explicitly focus first element

        manager.focus_next()  # Focus elem2
        assert elem2.focused

        manager.focus_next()  # Should wrap to elem1
        assert elem1.focused
        assert not elem2.focused
        assert manager.current_index == 0

    def test_focus_previous(self):
        """Test moving focus to previous element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        manager.set_elements([elem1, elem2, elem3])
        manager.focus_last()

        assert elem3.focused

        manager.focus_previous()
        assert elem2.focused
        assert manager.current_index == 1

        manager.focus_previous()
        assert elem1.focused
        assert manager.current_index == 0

    def test_focus_previous_wraps_around(self):
        """Test that focus wraps from first to last element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])
        manager.focus_first()  # Explicitly focus first element

        assert elem1.focused

        manager.focus_previous()  # Should wrap to elem2
        assert elem2.focused
        assert not elem1.focused
        assert manager.current_index == 1

    def test_focus_first(self):
        """Test focusing first element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])
        manager.focus_last()  # Focus elem2 first

        manager.focus_first()
        assert elem1.focused
        assert not elem2.focused

    def test_focus_last(self):
        """Test focusing last element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])

        manager.focus_last()
        assert elem2.focused
        assert not elem1.focused

    def test_focus_element_by_reference(self):
        """Test focusing a specific element by reference."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        manager.set_elements([elem1, elem2, elem3])

        result = manager.focus_element(elem3)
        assert result
        assert elem3.focused
        assert not elem1.focused
        assert not elem2.focused

    def test_focus_element_not_in_list(self):
        """Test focusing an element that's not in the list."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        manager.set_elements([elem1, elem2])

        result = manager.focus_element(elem3)
        assert not result

    def test_clear(self):
        """Test clearing focus manager."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])
        manager.focus_first()  # Explicitly focus
        assert elem1.focused

        manager.clear()
        assert not elem1.focused
        assert len(manager.elements) == 0
        assert manager.current_index is None

    def test_focus_next_empty_list(self):
        """Test focus_next with no elements."""
        manager = FocusManager()
        result = manager.focus_next()
        assert not result

    def test_focus_previous_empty_list(self):
        """Test focus_previous with no elements."""
        manager = FocusManager()
        result = manager.focus_previous()
        assert not result

    def test_blur_on_refocus(self):
        """Test that previous element is blurred when focus moves."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])
        manager.focus_first()  # Explicitly focus first

        assert elem1.focused
        assert not elem2.focused

        manager.focus_next()

        assert not elem1.focused
        assert elem2.focused


class TestFocusScrollsAncestor:
    """Focus changes should auto-scroll scrollable ancestor frames."""

    def _setup(self):
        from wijjit.layout.bounds import Bounds
        from wijjit.layout.frames import Frame, FrameStyle

        style = FrameStyle(scrollable=True)
        # Viewport = 10 lines, content = 40 lines.
        frame = Frame(width=20, height=12, style=style)
        frame.bounds = Bounds(x=0, y=0, width=20, height=12)
        frame.set_child_content_height(40)

        # One element inside the visible window, one well below it.
        visible = FocusableElement(id="visible")
        visible.bounds = Bounds(x=1, y=3, width=10, height=1)
        visible.parent_frame = frame

        offscreen = FocusableElement(id="offscreen")
        offscreen.bounds = Bounds(x=1, y=30, width=10, height=1)
        offscreen.parent_frame = frame

        return frame, visible, offscreen

    def test_focus_below_viewport_scrolls_ancestor_down(self):
        """Tabbing onto an element below the viewport scrolls the ancestor down."""
        frame, visible, offscreen = self._setup()
        manager = FocusManager()
        manager.set_elements([visible, offscreen])

        manager.focus_first()
        assert frame.scroll_position == 0

        manager.focus_next()
        # Bottom of offscreen (offset 30) aligns with viewport bottom (10):
        # scroll_position = 30 - 10 = 20.
        assert frame.scroll_position == 20

    def test_focus_above_viewport_scrolls_ancestor_up(self):
        """Tabbing back to an element above the viewport scrolls the ancestor up."""
        frame, visible, offscreen = self._setup()
        manager = FocusManager()
        manager.set_elements([visible, offscreen])

        manager.focus_first()
        manager.focus_next()  # scrolls to 20
        manager.focus_previous()  # back to "visible" at offset 2

        # Visible's top (offset 2) is above the current viewport (20..30),
        # so the frame scrolls up to align it with the viewport top.
        assert frame.scroll_position == 2

    def test_focus_inside_viewport_does_not_scroll(self):
        """Focusing an already-visible element leaves the scroll alone."""
        frame, visible, offscreen = self._setup()
        # Pre-scroll to a position where "visible" still fits.
        frame.scroll_manager.scroll_to(0)
        manager = FocusManager()
        manager.set_elements([visible, offscreen])

        manager.focus_first()
        assert frame.scroll_position == 0


class TestTabIndex:
    """Tests for tab_index focus ordering."""

    def test_elements_sorted_by_tab_index(self):
        """Test that elements are sorted by tab_index."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        # Set tab indices out of order
        elem1.tab_index = 3
        elem2.tab_index = 1
        elem3.tab_index = 2

        manager.set_elements([elem1, elem2, elem3])

        # Should be sorted: elem2 (1), elem3 (2), elem1 (3)
        assert manager.elements[0] == elem2
        assert manager.elements[1] == elem3
        assert manager.elements[2] == elem1

    def test_none_tab_index_after_explicit(self):
        """Test that elements with None tab_index come after explicit indices."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")
        elem4 = FocusableElement("e4")

        elem1.tab_index = None
        elem2.tab_index = 2
        elem3.tab_index = 1
        elem4.tab_index = None

        manager.set_elements([elem1, elem2, elem3, elem4])

        # Expected: elem3 (1), elem2 (2), elem1 (None), elem4 (None)
        # None elements maintain document order relative to each other
        assert manager.elements[0] == elem3
        assert manager.elements[1] == elem2
        assert manager.elements[2] == elem1
        assert manager.elements[3] == elem4

    def test_negative_tab_index_excluded(self):
        """Test that elements with tab_index=-1 are excluded from tab order."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        elem1.tab_index = 1
        elem2.tab_index = -1  # Excluded from tab navigation
        elem3.tab_index = 2

        manager.set_elements([elem1, elem2, elem3])

        # elem2 should be excluded from elements list
        assert len(manager.elements) == 2
        assert elem2 not in manager.elements
        assert elem1 in manager.elements
        assert elem3 in manager.elements

        # But elem2 should still be in all_focusable
        assert elem2 in manager.all_focusable

    def test_zero_tab_index_valid(self):
        """Test that tab_index=0 is valid and comes first."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        elem1.tab_index = 2
        elem2.tab_index = 0  # First in order
        elem3.tab_index = 1

        manager.set_elements([elem1, elem2, elem3])

        # elem2 (0) should be first
        assert manager.elements[0] == elem2
        assert manager.elements[1] == elem3
        assert manager.elements[2] == elem1

    def test_all_focusable_contains_excluded_elements(self):
        """Test that all_focusable includes elements with tab_index=-1."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        elem1.tab_index = 1
        elem2.tab_index = -1

        manager.set_elements([elem1, elem2])

        assert len(manager.elements) == 1
        assert len(manager.all_focusable) == 2
        assert elem2 in manager.all_focusable

    def test_focus_by_id_after_reorder(self):
        """Test focus is preserved by ID after tab_index reordering."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")
        elem3 = FocusableElement("e3")

        elem1.tab_index = 3
        elem2.tab_index = 1
        elem3.tab_index = 2

        manager.set_elements([elem1, elem2, elem3])
        manager.focus_element(elem1)
        assert elem1.focused

        # Re-set elements (simulates re-render) - focus should be preserved
        elem1_new = FocusableElement("e1")
        elem2_new = FocusableElement("e2")
        elem3_new = FocusableElement("e3")
        elem1_new.tab_index = 3
        elem2_new.tab_index = 1
        elem3_new.tab_index = 2

        manager.set_elements([elem1_new, elem2_new, elem3_new])

        # Focus should be on elem1_new (same ID)
        assert elem1_new.focused
        assert not elem2_new.focused
        assert not elem3_new.focused
