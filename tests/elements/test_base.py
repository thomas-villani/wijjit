"""Tests for base element classes."""

import pytest
from wijjit.elements.base import Element, Container, ElementType
from wijjit.layout.bounds import Bounds


# Concrete test implementation of Element
class TestElement(Element):
    """Test element implementation."""

    def __init__(self, content="test", id=None):
        super().__init__(id)
        self.content = content

    def render(self):
        return self.content


class TestElementBase:
    """Tests for Element base class."""

    def test_create_element(self):
        """Test creating an element."""
        elem = TestElement(id="test1")
        assert elem.id == "test1"
        assert not elem.focused
        assert not elem.focusable
        assert elem.bounds is None

    def test_element_without_id(self):
        """Test creating element without ID."""
        elem = TestElement()
        assert elem.id is None

    def test_on_focus(self):
        """Test focusing an element."""
        elem = TestElement()
        elem.on_focus()
        assert elem.focused

    def test_on_blur(self):
        """Test blurring an element."""
        elem = TestElement()
        elem.on_focus()
        assert elem.focused

        elem.on_blur()
        assert not elem.focused

    def test_set_bounds(self):
        """Test setting element bounds."""
        elem = TestElement()
        bounds = Bounds(x=10, y=20, width=30, height=40)

        elem.set_bounds(bounds)
        assert elem.bounds == bounds

    def test_render(self):
        """Test rendering element."""
        elem = TestElement(content="Hello")
        assert elem.render() == "Hello"

    def test_handle_key_default(self):
        """Test default key handling."""
        from wijjit.terminal.input import Keys

        elem = TestElement()
        # Default implementation returns False
        assert not elem.handle_key(Keys.ENTER)


class TestContainer:
    """Tests for Container class."""

    def test_create_container(self):
        """Test creating a container."""
        container = Container(id="container1")
        assert container.id == "container1"
        assert len(container.children) == 0

    def test_add_child(self):
        """Test adding a child element."""
        container = Container()
        elem = TestElement()

        container.add_child(elem)
        assert len(container.children) == 1
        assert elem in container.children

    def test_add_multiple_children(self):
        """Test adding multiple children."""
        container = Container()
        elem1 = TestElement()
        elem2 = TestElement()

        container.add_child(elem1)
        container.add_child(elem2)

        assert len(container.children) == 2
        assert elem1 in container.children
        assert elem2 in container.children

    def test_remove_child(self):
        """Test removing a child element."""
        container = Container()
        elem = TestElement()

        container.add_child(elem)
        assert len(container.children) == 1

        container.remove_child(elem)
        assert len(container.children) == 0
        assert elem not in container.children

    def test_remove_nonexistent_child(self):
        """Test removing a child that isn't in the container."""
        container = Container()
        elem = TestElement()

        # Should not raise an error
        container.remove_child(elem)

    def test_get_focusable_children_none(self):
        """Test getting focusable children when none exist."""
        container = Container()
        container.add_child(TestElement())
        container.add_child(TestElement())

        focusable = container.get_focusable_children()
        assert len(focusable) == 0

    def test_get_focusable_children_some(self):
        """Test getting focusable children."""
        container = Container()

        elem1 = TestElement()
        elem2 = TestElement()
        elem2.focusable = True
        elem3 = TestElement()
        elem3.focusable = True

        container.add_child(elem1)
        container.add_child(elem2)
        container.add_child(elem3)

        focusable = container.get_focusable_children()
        assert len(focusable) == 2
        assert elem2 in focusable
        assert elem3 in focusable
        assert elem1 not in focusable

    def test_get_focusable_children_nested(self):
        """Test getting focusable children from nested containers."""
        outer = Container()
        inner = Container()

        elem1 = TestElement()
        elem1.focusable = True

        elem2 = TestElement()
        elem2.focusable = True

        inner.add_child(elem1)
        outer.add_child(inner)
        outer.add_child(elem2)

        focusable = outer.get_focusable_children()
        assert len(focusable) == 2
        assert elem1 in focusable
        assert elem2 in focusable

    def test_render_empty_container(self):
        """Test rendering an empty container."""
        container = Container()
        result = container.render()
        assert result == ""

    def test_render_with_children(self):
        """Test rendering container with children."""
        container = Container()
        container.add_child(TestElement(content="Line 1"))
        container.add_child(TestElement(content="Line 2"))

        result = container.render()
        assert "Line 1" in result
        assert "Line 2" in result
