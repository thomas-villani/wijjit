"""Tests for focus management."""

from wijjit.core.focus import FocusManager
from wijjit.elements.base import Element


# Test element implementation
class FocusableElement(Element):
    """Test focusable element."""

    def __init__(self, id=None):
        super().__init__(id)
        self.focusable = True

    def render(self):
        return f"Element {self.id}"


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

    def test_focus_first_on_set(self):
        """Test that first element is focused when elements are set."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])

        assert elem1.focused
        assert not elem2.focused
        assert manager.current_index == 0

    def test_get_focused_element(self):
        """Test getting the currently focused element."""
        manager = FocusManager()
        elem1 = FocusableElement("e1")
        elem2 = FocusableElement("e2")

        manager.set_elements([elem1, elem2])

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

        assert elem1.focused

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
        manager.focus_next()  # Focus elem2

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

        assert elem1.focused
        assert not elem2.focused

        manager.focus_next()

        assert not elem1.focused
        assert elem2.focused
