"""Tests for Reconciler implementation."""


from wijjit.core.reconciler import DiffResult, DiffType, Reconciler
from wijjit.core.vdom import VNode


class MockRegistry:
    """Mock element registry for testing."""

    def __init__(self):
        self.created_elements = []
        # Mock supports all types by default
        self._known_types = {"Button", "TextInput", "Container", "VStack"}

    def has_type(self, type_name: str) -> bool:
        """Check if type is registered."""
        return type_name in self._known_types

    def create_element(self, vnode: VNode):
        """Create a mock element."""
        element = MockElement(vnode.type, vnode.key, vnode.props_dict())
        self.created_elements.append(element)
        return element


class MockElement:
    """Mock element for testing reconciliation."""

    def __init__(self, type_name: str, key: str | None, props: dict):
        self.type_name = type_name
        self.id = key
        self.children = []

        # Copy props as attributes
        for k, v in props.items():
            setattr(self, k, v)

        # Track lifecycle calls
        self.mount_called = False
        self.unmount_called = False
        self.update_calls = []

        # Ephemeral state for testing
        self.cursor_pos = 0

    def on_mount(self):
        self.mount_called = True

    def on_unmount(self):
        self.unmount_called = True

    def on_update(self, changed_props):
        self.update_calls.append(changed_props)

    def get_ephemeral_state(self):
        return {"cursor_pos": self.cursor_pos}

    def restore_ephemeral_state(self, state):
        if "cursor_pos" in state:
            self.cursor_pos = state["cursor_pos"]


class TestReconcilerDiff:
    """Tests for diff algorithm."""

    def test_diff_none_to_none(self):
        """Diffing None to None should return NONE."""
        reconciler = Reconciler(MockRegistry())
        diff = reconciler._diff(None, None)

        assert diff.diff_type == DiffType.NONE

    def test_diff_create(self):
        """Diffing None to VNode should return CREATE."""
        reconciler = Reconciler(MockRegistry())
        vnode = VNode.create("Button", key="btn", props={"label": "OK"})

        diff = reconciler._diff(None, vnode)

        assert diff.diff_type == DiffType.CREATE
        assert diff.new_vnode == vnode

    def test_diff_delete(self):
        """Diffing VNode to None should return DELETE."""
        reconciler = Reconciler(MockRegistry())
        vnode = VNode.create("Button", key="btn", props={"label": "OK"})

        diff = reconciler._diff(vnode, None)

        assert diff.diff_type == DiffType.DELETE
        assert diff.old_vnode == vnode

    def test_diff_replace_different_types(self):
        """Diffing VNodes with different types should return REPLACE."""
        reconciler = Reconciler(MockRegistry())
        old = VNode.create("Button", key="elem", props={"label": "OK"})
        new = VNode.create("TextInput", key="elem", props={"placeholder": "Type"})

        diff = reconciler._diff(old, new)

        assert diff.diff_type == DiffType.REPLACE
        assert diff.old_vnode == old
        assert diff.new_vnode == new

    def test_diff_update_props_changed(self):
        """Diffing VNodes with changed props should return UPDATE."""
        reconciler = Reconciler(MockRegistry())
        old = VNode.create("Button", key="btn", props={"label": "OK"})
        new = VNode.create("Button", key="btn", props={"label": "Cancel"})

        diff = reconciler._diff(old, new)

        assert diff.diff_type == DiffType.UPDATE
        assert "label" in diff.prop_changes
        assert diff.prop_changes["label"] == ("OK", "Cancel")

    def test_diff_no_change(self):
        """Diffing identical VNodes should return NONE."""
        reconciler = Reconciler(MockRegistry())
        old = VNode.create("Button", key="btn", props={"label": "OK"})
        new = VNode.create("Button", key="btn", props={"label": "OK"})

        diff = reconciler._diff(old, new)

        assert diff.diff_type == DiffType.NONE

    def test_diff_skips_ephemeral_props(self):
        """Diff should skip ephemeral props like cursor_pos."""
        reconciler = Reconciler(MockRegistry())
        old = VNode.create(
            "TextInput", key="inp", props={"value": "hello", "cursor_pos": 0}
        )
        new = VNode.create(
            "TextInput", key="inp", props={"value": "hello", "cursor_pos": 5}
        )

        diff = reconciler._diff(old, new)

        # cursor_pos change should be ignored (ephemeral)
        assert diff.diff_type == DiffType.NONE
        assert "cursor_pos" not in diff.prop_changes


class TestReconcilerDiffChildren:
    """Tests for children diffing."""

    def test_diff_children_by_key(self):
        """Children should be matched by key."""
        reconciler = Reconciler(MockRegistry())

        old_children = (
            VNode.create("Button", key="a", props={"label": "A"}),
            VNode.create("Button", key="b", props={"label": "B"}),
        )
        new_children = (
            VNode.create("Button", key="b", props={"label": "B Modified"}),
            VNode.create("Button", key="a", props={"label": "A"}),
        )

        diffs = reconciler._diff_children(old_children, new_children)

        # Should find matches by key, not position
        # b is first in new but exists in old - should be UPDATE
        # a is second in new but exists in old - should be NONE
        assert len(diffs) == 2

    def test_diff_children_create_new(self):
        """New keyed children should be marked CREATE."""
        reconciler = Reconciler(MockRegistry())

        old_children = (VNode.create("Button", key="a", props={"label": "A"}),)
        new_children = (
            VNode.create("Button", key="a", props={"label": "A"}),
            VNode.create("Button", key="b", props={"label": "B"}),
        )

        diffs = reconciler._diff_children(old_children, new_children)

        create_diffs = [d for d in diffs if d.diff_type == DiffType.CREATE]
        assert len(create_diffs) == 1
        assert create_diffs[0].new_vnode.key == "b"

    def test_diff_children_delete_old(self):
        """Removed keyed children should be marked DELETE."""
        reconciler = Reconciler(MockRegistry())

        old_children = (
            VNode.create("Button", key="a", props={"label": "A"}),
            VNode.create("Button", key="b", props={"label": "B"}),
        )
        new_children = (VNode.create("Button", key="a", props={"label": "A"}),)

        diffs = reconciler._diff_children(old_children, new_children)

        delete_diffs = [d for d in diffs if d.diff_type == DiffType.DELETE]
        assert len(delete_diffs) == 1
        assert delete_diffs[0].old_vnode.key == "b"


class TestReconcilerPatch:
    """Tests for patching (applying diffs)."""

    def test_patch_create_calls_on_mount(self):
        """CREATE should call on_mount() on new element."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)
        vnode = VNode.create("Button", key="btn", props={"label": "OK"})

        diff = DiffResult(DiffType.CREATE, None, vnode)
        element = reconciler._patch(diff)

        assert element is not None
        assert element.mount_called

    def test_patch_create_caches_by_key(self):
        """CREATE should cache element by key."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)
        vnode = VNode.create("Button", key="btn", props={"label": "OK"})

        diff = DiffResult(DiffType.CREATE, None, vnode)
        reconciler._patch(diff)

        assert "btn" in reconciler._element_cache

    def test_patch_delete_calls_on_unmount(self):
        """DELETE should call on_unmount() on removed element."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)

        # First create an element
        vnode = VNode.create("Button", key="btn", props={"label": "OK"})
        create_diff = DiffResult(DiffType.CREATE, None, vnode)
        element = reconciler._patch(create_diff)

        # Then delete it
        delete_diff = DiffResult(DiffType.DELETE, vnode, None)
        reconciler._patch(delete_diff)

        assert element.unmount_called
        assert "btn" not in reconciler._element_cache

    def test_patch_update_preserves_ephemeral_state(self):
        """UPDATE should preserve ephemeral state."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)

        # Create initial element
        old_vnode = VNode.create("TextInput", key="inp", props={"value": "hello"})
        create_diff = DiffResult(DiffType.CREATE, None, old_vnode)
        element = reconciler._patch(create_diff)

        # Set some ephemeral state
        element.cursor_pos = 3

        # Update with new value
        new_vnode = VNode.create("TextInput", key="inp", props={"value": "world"})
        update_diff = DiffResult(
            DiffType.UPDATE,
            old_vnode,
            new_vnode,
            prop_changes={"value": ("hello", "world")},
        )
        updated_element = reconciler._patch(update_diff)

        # Ephemeral state should be preserved
        assert updated_element.cursor_pos == 3
        # Value should be updated
        assert updated_element.value == "world"


class TestReconcilerIntegration:
    """Integration tests for full reconciliation."""

    def test_reconcile_first_render(self):
        """First render (old=None) should create all elements."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)

        tree = VNode.create(
            "VStack",
            key="root",
            children=[
                VNode.create("TextInput", key="name"),
                VNode.create("Button", key="submit"),
            ],
        )

        root, elements = reconciler.reconcile(None, tree)

        assert root is not None
        assert len(elements) == 3  # root + 2 children

    def test_reconcile_update_preserves_elements(self):
        """Reconciling with same keys should reuse elements."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)

        old_tree = VNode.create("Button", key="btn", props={"label": "Old"})
        new_tree = VNode.create("Button", key="btn", props={"label": "New"})

        # First render
        root1, _ = reconciler.reconcile(None, old_tree)
        original_element = root1

        # Update
        root2, _ = reconciler.reconcile(old_tree, new_tree)

        # Should be the same object (reused)
        assert root2 is original_element
        assert root2.label == "New"

    def test_reconcile_clear_removes_all(self):
        """Reconciling to None should remove all elements."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)

        tree = VNode.create("Button", key="btn", props={"label": "OK"})

        # First render
        root, _ = reconciler.reconcile(None, tree)

        # Clear
        root2, elements = reconciler.reconcile(tree, None)

        assert root2 is None
        assert elements == []
        assert root.unmount_called

    def test_clear_cache(self):
        """clear_cache() should unmount all cached elements."""
        registry = MockRegistry()
        reconciler = Reconciler(registry)

        tree = VNode.create("Button", key="btn", props={"label": "OK"})
        root, _ = reconciler.reconcile(None, tree)

        reconciler.clear_cache()

        assert root.unmount_called
        assert len(reconciler._element_cache) == 0
