"""Tests for hover state management."""

from wijjit.core.hover import HoverManager
from wijjit.elements.base import TextElement


class TestHoverManager:
    """Tests for HoverManager class."""

    def test_init(self):
        """Test HoverManager initialization.

        Verifies that the HoverManager initializes with no hovered element.
        """
        manager = HoverManager()
        assert manager.current_element is None
        assert manager.get_hovered_element() is None

    def test_set_hovered_element(self):
        """Test setting a hovered element.

        Verifies that set_hovered correctly updates the current element
        and returns True when the hover state changes.
        """
        manager = HoverManager()
        elem = TextElement("Test")

        # Set hovered should return True (state changed)
        result = manager.set_hovered(elem)
        assert result is True
        assert manager.get_hovered_element() is elem
        assert elem.hovered is True

    def test_set_hovered_same_element(self):
        """Test setting the same element as hovered.

        Verifies that set_hovered returns False when the element
        is already hovered (no state change).
        """
        manager = HoverManager()
        elem = TextElement("Test")

        # First set
        manager.set_hovered(elem)

        # Set same element again should return False (no change)
        result = manager.set_hovered(elem)
        assert result is False
        assert manager.get_hovered_element() is elem

    def test_hover_transition(self):
        """Test transitioning hover between elements.

        Verifies that lifecycle methods are called correctly when
        hover moves from one element to another.
        """
        manager = HoverManager()
        elem1 = TextElement("First")
        elem2 = TextElement("Second")

        # Hover first element
        manager.set_hovered(elem1)
        assert elem1.hovered is True
        assert elem2.hovered is False

        # Hover second element
        result = manager.set_hovered(elem2)
        assert result is True
        assert elem1.hovered is False  # on_hover_exit called
        assert elem2.hovered is True  # on_hover_enter called
        assert manager.get_hovered_element() is elem2

    def test_clear_hovered(self):
        """Test clearing the hovered element.

        Verifies that clear_hovered removes the current hover
        and calls on_hover_exit.
        """
        manager = HoverManager()
        elem = TextElement("Test")

        # Set hovered
        manager.set_hovered(elem)
        assert elem.hovered is True

        # Clear hovered
        result = manager.clear_hovered()
        assert result is True
        assert elem.hovered is False
        assert manager.get_hovered_element() is None

    def test_clear_when_nothing_hovered(self):
        """Test clearing when nothing is hovered.

        Verifies that clear_hovered returns False when there's
        nothing to clear.
        """
        manager = HoverManager()

        result = manager.clear_hovered()
        assert result is False
        assert manager.get_hovered_element() is None

    def test_set_none_clears_hover(self):
        """Test that set_hovered(None) clears the hover.

        Verifies that passing None to set_hovered clears the
        current hover state.
        """
        manager = HoverManager()
        elem = TextElement("Test")

        # Set hovered
        manager.set_hovered(elem)
        assert elem.hovered is True

        # Set to None
        result = manager.set_hovered(None)
        assert result is True
        assert elem.hovered is False
        assert manager.get_hovered_element() is None

    def test_lifecycle_methods_called(self):
        """Test that lifecycle methods are called correctly.

        Verifies that on_hover_enter and on_hover_exit are called
        at the right times during hover transitions.
        """
        manager = HoverManager()

        # Create test elements that track lifecycle calls
        class TrackingElement(TextElement):
            def __init__(self, text):
                super().__init__(text)
                self.enter_called = False
                self.exit_called = False

            def on_hover_enter(self):
                super().on_hover_enter()
                self.enter_called = True

            def on_hover_exit(self):
                super().on_hover_exit()
                self.exit_called = True

        elem1 = TrackingElement("First")
        elem2 = TrackingElement("Second")

        # Hover first element
        manager.set_hovered(elem1)
        assert elem1.enter_called is True
        assert elem1.exit_called is False

        # Hover second element
        manager.set_hovered(elem2)
        assert elem1.exit_called is True  # First element exit called
        assert elem2.enter_called is True  # Second element enter called
        assert elem2.exit_called is False

        # Clear hover
        manager.clear_hovered()
        assert elem2.exit_called is True  # Second element exit called
