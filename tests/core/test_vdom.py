"""Tests for Virtual DOM implementation."""

import pytest

from wijjit.core.vdom import (
    EPHEMERAL_PROPS,
    VNode,
    VNodeBuilder,
    is_ephemeral_prop,
)


class TestVNode:
    """Tests for VNode dataclass."""

    def test_create_simple_vnode(self):
        """VNode.create() should create a VNode with basic props."""
        vnode = VNode.create("Button", key="btn1", props={"label": "Click"})

        assert vnode.type == "Button"
        assert vnode.key == "btn1"
        assert vnode.get_prop("label") == "Click"
        assert vnode.children == ()

    def test_create_vnode_with_children(self):
        """VNode.create() should create a VNode with children."""
        child1 = VNode.create("TextInput", key="name")
        child2 = VNode.create("Button", key="submit")
        parent = VNode.create("VStack", children=[child1, child2])

        assert len(parent.children) == 2
        assert parent.children[0].type == "TextInput"
        assert parent.children[1].type == "Button"

    def test_vnode_immutability(self):
        """VNode should be frozen (immutable)."""
        vnode = VNode.create("Button", props={"label": "OK"})

        with pytest.raises(AttributeError):
            vnode.type = "Changed"

    def test_vnode_get_prop_default(self):
        """get_prop() should return default when prop not found."""
        vnode = VNode.create("Button", props={"label": "OK"})

        assert vnode.get_prop("disabled", False) is False
        assert vnode.get_prop("nonexistent") is None

    def test_vnode_props_dict(self):
        """props_dict() should convert props tuple to dict."""
        vnode = VNode.create("Button", props={"label": "OK", "width": 10})
        props = vnode.props_dict()

        assert props == {"label": "OK", "width": 10}

    def test_vnode_equality(self):
        """VNodes with same content should be equal."""
        vnode1 = VNode.create("Button", key="btn", props={"label": "OK"})
        vnode2 = VNode.create("Button", key="btn", props={"label": "OK"})

        assert vnode1 == vnode2

    def test_vnode_inequality_different_type(self):
        """VNodes with different types should not be equal."""
        vnode1 = VNode.create("Button", props={"label": "OK"})
        vnode2 = VNode.create("TextInput", props={"label": "OK"})

        assert vnode1 != vnode2

    def test_vnode_inequality_different_props(self):
        """VNodes with different props should not be equal."""
        vnode1 = VNode.create("Button", props={"label": "OK"})
        vnode2 = VNode.create("Button", props={"label": "Cancel"})

        assert vnode1 != vnode2

    def test_vnode_hashable(self):
        """VNodes should be hashable for use in sets/dicts."""
        vnode = VNode.create("Button", key="btn", props={"label": "OK"})

        # Should not raise
        hash(vnode)
        _test_set = {vnode}  # Use in set


class TestVNodeBuilder:
    """Tests for VNodeBuilder."""

    def test_builder_basic(self):
        """VNodeBuilder should build a simple VNode."""
        builder = VNodeBuilder("Button", key="btn1")
        builder.props["label"] = "Click"

        vnode = builder.freeze()

        assert vnode.type == "Button"
        assert vnode.key == "btn1"
        assert vnode.get_prop("label") == "Click"

    def test_builder_with_children(self):
        """VNodeBuilder should build nested VNode trees."""
        root = VNodeBuilder("VStack", key="root")
        root.props["spacing"] = 1

        child1 = VNodeBuilder("TextInput", key="name")
        child1.props["placeholder"] = "Name"

        child2 = VNodeBuilder("Button", key="submit")
        child2.props["label"] = "Submit"

        root.add_child(child1)
        root.add_child(child2)

        vnode = root.freeze()

        assert vnode.type == "VStack"
        assert len(vnode.children) == 2
        assert vnode.children[0].type == "TextInput"
        assert vnode.children[0].get_prop("placeholder") == "Name"
        assert vnode.children[1].type == "Button"

    def test_builder_set_prop(self):
        """set_prop() should set a property."""
        builder = VNodeBuilder("Button")
        builder.set_prop("label", "OK")
        builder.set_prop("width", 10)

        vnode = builder.freeze()

        assert vnode.get_prop("label") == "OK"
        assert vnode.get_prop("width") == 10

    def test_builder_set_layout(self):
        """set_layout() should set layout specification."""
        builder = VNodeBuilder("Frame")
        builder.set_layout(width="fill", height=10)

        assert builder.layout_spec == {"width": "fill", "height": 10}

    def test_builder_repr(self):
        """__repr__ should show useful info."""
        builder = VNodeBuilder("VStack", key="main")
        builder.add_child(VNodeBuilder("Button"))

        repr_str = repr(builder)

        assert "VStack" in repr_str
        assert "main" in repr_str
        assert "children=1" in repr_str


class TestEphemeralProps:
    """Tests for ephemeral props handling."""

    def test_cursor_props_are_ephemeral(self):
        """Cursor-related props should be ephemeral."""
        assert is_ephemeral_prop("cursor_pos")
        assert is_ephemeral_prop("cursor_row")
        assert is_ephemeral_prop("cursor_col")

    def test_selection_props_are_ephemeral(self):
        """Selection-related props should be ephemeral."""
        assert is_ephemeral_prop("selection_anchor")
        assert is_ephemeral_prop("selection_start")
        assert is_ephemeral_prop("selection_end")

    def test_scroll_props_are_ephemeral(self):
        """Scroll-related props should be ephemeral."""
        assert is_ephemeral_prop("scroll_position")
        assert is_ephemeral_prop("scroll_x_position")

    def test_ui_state_props_are_ephemeral(self):
        """UI state props should be ephemeral."""
        assert is_ephemeral_prop("highlighted_index")
        assert is_ephemeral_prop("focused")
        assert is_ephemeral_prop("hovered")

    def test_regular_props_not_ephemeral(self):
        """Regular props should not be ephemeral."""
        assert not is_ephemeral_prop("value")
        assert not is_ephemeral_prop("placeholder")
        assert not is_ephemeral_prop("label")
        assert not is_ephemeral_prop("width")
        assert not is_ephemeral_prop("options")

    def test_ephemeral_props_is_frozenset(self):
        """EPHEMERAL_PROPS should be a frozenset."""
        assert isinstance(EPHEMERAL_PROPS, frozenset)
