"""Reconciler for Virtual DOM diffing and patching.

This module provides the core reconciliation algorithm that compares old and new
VNode trees and efficiently updates the Element tree by reusing existing elements
where possible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from wijjit.core.vdom import EPHEMERAL_PROPS, VNode
from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from wijjit.core.element_registry import ElementRegistry
    from wijjit.elements.base import Element

logger = get_logger(__name__)


class DiffType(Enum):
    """Types of differences detected during reconciliation."""

    NONE = auto()  # No change needed
    CREATE = auto()  # Create new element
    DELETE = auto()  # Remove element
    UPDATE = auto()  # Update existing element props
    REPLACE = auto()  # Replace element (type changed)


@dataclass
class DiffResult:
    """Result of diffing two VNodes.

    Parameters
    ----------
    diff_type : DiffType
        Type of difference detected
    old_vnode : VNode or None
        Previous VNode (None for CREATE)
    new_vnode : VNode or None
        New VNode (None for DELETE)
    prop_changes : dict
        Map of prop_name -> (old_value, new_value) for changed props
    children_diffs : list
        List of DiffResults for children

    Attributes
    ----------
    element : Element or None
        The Element associated with this diff (set during patching)
    """

    diff_type: DiffType
    old_vnode: VNode | None
    new_vnode: VNode | None
    prop_changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    children_diffs: list[DiffResult] = field(default_factory=list)
    element: Element | None = field(default=None, repr=False)


class Reconciler:
    """Reconciles old and new VNode trees, producing a patched Element tree.

    The Reconciler implements a React-style diffing algorithm that:
    1. Compares old and new VNode trees
    2. Identifies what changed (creates, deletes, updates)
    3. Patches existing Elements in place where possible
    4. Creates new Elements only when necessary
    5. Preserves ephemeral state (cursor, scroll, selection)

    Parameters
    ----------
    registry : ElementRegistry
        Registry for creating new Element instances

    Attributes
    ----------
    registry : ElementRegistry
        Element factory registry
    _element_cache : dict
        Cache of key -> Element for reusing elements

    Examples
    --------
    >>> from wijjit.core.vdom import VNode
    >>> from wijjit.core.element_registry import ElementRegistry
    >>> registry = ElementRegistry()
    >>> reconciler = Reconciler(registry)
    >>> old_tree = VNode.create("Button", key="btn", props={"label": "Old"})
    >>> new_tree = VNode.create("Button", key="btn", props={"label": "New"})
    >>> root, elements = reconciler.reconcile(old_tree, new_tree)
    >>> root.label  # Element was updated, not replaced
    'New'
    """

    def __init__(self, registry: ElementRegistry) -> None:
        self.registry = registry
        self._element_cache: dict[str, Element] = {}

    def reconcile(
        self,
        old_tree: VNode | None,
        new_tree: VNode | None,
    ) -> tuple[Element | None, list[Element]]:
        """Reconcile old and new VNode trees.

        Parameters
        ----------
        old_tree : VNode or None
            Previous VNode tree (None on first render)
        new_tree : VNode or None
            New VNode tree (None to unmount everything)

        Returns
        -------
        tuple
            (root_element, flat_element_list)
            - root_element: Root Element of the tree (None if new_tree is None)
            - flat_element_list: Flattened list of all Elements for event handling
        """
        # Phase 1: Diff the trees
        diff = self._diff(old_tree, new_tree)

        # Phase 2: Patch (create/update/delete elements)
        root = self._patch(diff)

        # Phase 3: Collect all elements into flat list
        elements = self._collect_elements(root)

        return root, elements

    def _diff(self, old: VNode | None, new: VNode | None) -> DiffResult:
        """Diff two VNodes recursively.

        Parameters
        ----------
        old : VNode or None
            Old VNode
        new : VNode or None
            New VNode

        Returns
        -------
        DiffResult
            Description of differences
        """
        # Case 1: Both None - nothing to do
        if old is None and new is None:
            return DiffResult(DiffType.NONE, None, None)

        # Case 2: Create new element
        if old is None and new is not None:
            children_diffs = [self._diff(None, child) for child in new.children]
            return DiffResult(DiffType.CREATE, None, new, {}, children_diffs)

        # Case 3: Delete element
        if old is not None and new is None:
            children_diffs = [self._diff(child, None) for child in old.children]
            return DiffResult(DiffType.DELETE, old, None, {}, children_diffs)

        # Case 4: Type changed - replace entirely
        if old.type != new.type:
            # Diff children of new tree for creation
            children_diffs = [self._diff(None, child) for child in new.children]
            return DiffResult(DiffType.REPLACE, old, new, {}, children_diffs)

        # Case 5: Same type - diff props and children
        prop_changes = self._diff_props(old.props, new.props)
        children_diffs = self._diff_children(old.children, new.children)

        if prop_changes or any(d.diff_type != DiffType.NONE for d in children_diffs):
            return DiffResult(DiffType.UPDATE, old, new, prop_changes, children_diffs)

        return DiffResult(DiffType.NONE, old, new, {}, children_diffs)

    def _diff_props(
        self,
        old_props: tuple[tuple[str, Any], ...],
        new_props: tuple[tuple[str, Any], ...],
    ) -> dict[str, tuple[Any, Any]]:
        """Diff property tuples.

        Parameters
        ----------
        old_props : tuple
            Old props as tuple of (key, value) pairs
        new_props : tuple
            New props as tuple of (key, value) pairs

        Returns
        -------
        dict
            Map of changed props: name -> (old_value, new_value)
            Does NOT include ephemeral props.
        """
        old_dict = dict(old_props)
        new_dict = dict(new_props)
        changes: dict[str, tuple[Any, Any]] = {}

        # Find changed and new props
        for key, new_val in new_dict.items():
            # Skip ephemeral props - they should not be synced from template
            if key in EPHEMERAL_PROPS:
                continue

            old_val = old_dict.get(key)
            if old_val != new_val:
                changes[key] = (old_val, new_val)

        # Find removed props (set to None)
        for key in old_dict:
            if key not in new_dict and key not in EPHEMERAL_PROPS:
                changes[key] = (old_dict[key], None)

        return changes

    def _diff_children(
        self,
        old_children: tuple[VNode, ...],
        new_children: tuple[VNode, ...],
    ) -> list[DiffResult]:
        """Diff children using key-based matching.

        Parameters
        ----------
        old_children : tuple
            Old child VNodes
        new_children : tuple
            New child VNodes

        Returns
        -------
        list
            List of DiffResults for children
        """
        # Build map of old children by key
        old_by_key: dict[str, VNode] = {}
        old_keyless: list[VNode] = []

        for child in old_children:
            if child.key:
                old_by_key[child.key] = child
            else:
                old_keyless.append(child)

        results: list[DiffResult] = []
        matched_keys: set[str] = set()
        keyless_index = 0

        for new_child in new_children:
            if new_child.key and new_child.key in old_by_key:
                # Match by key - diff with old element
                matched_keys.add(new_child.key)
                results.append(self._diff(old_by_key[new_child.key], new_child))
            elif new_child.key:
                # New keyed element
                results.append(self._diff(None, new_child))
            else:
                # Keyless element - match by position
                if keyless_index < len(old_keyless):
                    results.append(self._diff(old_keyless[keyless_index], new_child))
                    keyless_index += 1
                else:
                    results.append(self._diff(None, new_child))

        # Delete unmatched old keyed children
        for key, old_child in old_by_key.items():
            if key not in matched_keys:
                results.append(self._diff(old_child, None))

        # Delete remaining unmatched keyless children
        while keyless_index < len(old_keyless):
            results.append(self._diff(old_keyless[keyless_index], None))
            keyless_index += 1

        return results

    def _patch(self, diff: DiffResult) -> Element | None:
        """Apply diff to create/update/delete elements.

        Parameters
        ----------
        diff : DiffResult
            Diff to apply

        Returns
        -------
        Element or None
            The resulting element (None for DELETE)
        """
        if diff.diff_type == DiffType.NONE:
            # No change - return existing element from cache
            if diff.old_vnode and diff.old_vnode.key:
                element = self._element_cache.get(diff.old_vnode.key)
                if element:
                    diff.element = element
                    # Still need to recursively patch children
                    self._patch_children(element, diff.children_diffs)
                    return element
            return None

        if diff.diff_type == DiffType.CREATE:
            return self._create_element(diff)

        if diff.diff_type == DiffType.DELETE:
            return self._delete_element(diff)

        if diff.diff_type == DiffType.REPLACE:
            self._delete_element(diff)
            return self._create_element(diff)

        if diff.diff_type == DiffType.UPDATE:
            return self._update_element(diff)

        return None

    def _create_element(self, diff: DiffResult) -> Element | None:
        """Create a new element from VNode.

        Parameters
        ----------
        diff : DiffResult
            Diff with new_vnode set

        Returns
        -------
        Element or None
            Newly created element, or None for container types
        """
        vnode = diff.new_vnode
        if vnode is None:
            raise ValueError("Cannot create element: new_vnode is None")

        # Skip container types (Frame, VStack, HStack) - they're created by template
        if not self.registry.has_type(vnode.type):
            logger.debug(f"Skipping unknown/container type: {vnode.type}")
            # Still process children for containers
            for child_diff in diff.children_diffs:
                self._patch(child_diff)
            return None

        # Create element via registry
        element = self.registry.create_element(vnode)

        # Cache by key if available
        if vnode.key:
            self._element_cache[vnode.key] = element

        # Call mount lifecycle
        if hasattr(element, "on_mount"):
            element.on_mount()

        # Create children
        if hasattr(element, "children"):
            element.children = []
            for child_diff in diff.children_diffs:
                child_elem = self._patch(child_diff)
                if child_elem:
                    element.children.append(child_elem)

        diff.element = element
        return element

    def _delete_element(self, diff: DiffResult) -> None:
        """Delete an element.

        Parameters
        ----------
        diff : DiffResult
            Diff with old_vnode set
        """
        vnode = diff.old_vnode
        if vnode is None:
            return

        # Remove from cache
        if vnode.key and vnode.key in self._element_cache:
            element = self._element_cache.pop(vnode.key)

            # Call unmount lifecycle
            if hasattr(element, "on_unmount"):
                element.on_unmount()

        # Recursively delete children
        for child_diff in diff.children_diffs:
            self._delete_element(child_diff)

    def _update_element(self, diff: DiffResult) -> Element | None:
        """Update an existing element with prop changes.

        Parameters
        ----------
        diff : DiffResult
            Diff with both old_vnode and new_vnode set

        Returns
        -------
        Element or None
            Updated element
        """
        if diff.old_vnode is None or diff.new_vnode is None:
            return None

        # Skip container types (Frame, VStack, HStack) - they're created by template
        if not self.registry.has_type(diff.new_vnode.type):
            logger.debug(
                f"Skipping unknown/container type update: {diff.new_vnode.type}"
            )
            # Still process children for containers
            for child_diff in diff.children_diffs:
                self._patch(child_diff)
            return None

        # Get existing element from cache
        key = diff.old_vnode.key or diff.new_vnode.key
        element = self._element_cache.get(key) if key else None

        if element is None:
            # Element not in cache - need to create it
            logger.warning(
                f"Element with key {key!r} not found in cache during update, creating new"
            )
            return self._create_element(diff)

        # Save ephemeral state before update
        ephemeral_state: dict[str, Any] = {}
        if hasattr(element, "get_ephemeral_state"):
            ephemeral_state = element.get_ephemeral_state()

        # Apply prop changes
        if diff.prop_changes:
            self._apply_prop_changes(element, diff.prop_changes)

            # Call update lifecycle
            if hasattr(element, "on_update"):
                element.on_update(diff.prop_changes)

        # Restore ephemeral state
        if ephemeral_state and hasattr(element, "restore_ephemeral_state"):
            element.restore_ephemeral_state(ephemeral_state)

        # Update cache key if changed
        if diff.new_vnode.key and diff.new_vnode.key != key:
            if key:
                del self._element_cache[key]
            self._element_cache[diff.new_vnode.key] = element

        # Patch children
        self._patch_children(element, diff.children_diffs)

        diff.element = element
        return element

    def _apply_prop_changes(
        self,
        element: Element,
        changes: dict[str, tuple[Any, Any]],
    ) -> None:
        """Apply property changes to an element.

        Parameters
        ----------
        element : Element
            Element to update
        changes : dict
            Map of prop_name -> (old_value, new_value)
        """
        for prop_name, (_old_val, new_val) in changes.items():
            if hasattr(element, prop_name):
                setattr(element, prop_name, new_val)
            elif hasattr(element, "apply_props"):
                element.apply_props({prop_name: new_val})

    def _patch_children(
        self,
        parent: Element,
        children_diffs: list[DiffResult],
    ) -> None:
        """Patch children of a container element.

        Parameters
        ----------
        parent : Element
            Parent container element
        children_diffs : list
            List of DiffResults for children
        """
        if not hasattr(parent, "children"):
            return

        new_children: list[Element] = []

        for child_diff in children_diffs:
            if child_diff.diff_type == DiffType.DELETE:
                self._patch(child_diff)  # Just delete, don't add to new_children
            else:
                child_elem = self._patch(child_diff)
                if child_elem:
                    new_children.append(child_elem)

        parent.children = new_children

    def _collect_elements(self, root: Element | None) -> list[Element]:
        """Collect all elements into a flat list.

        Parameters
        ----------
        root : Element or None
            Root element

        Returns
        -------
        list
            Flattened list of all elements (for event handling)
        """
        if root is None:
            return []

        result: list[Element] = [root]

        if hasattr(root, "children"):
            for child in root.children:
                result.extend(self._collect_elements(child))

        return result

    def clear_cache(self) -> None:
        """Clear the element cache.

        Call this when switching views or when a full re-render is needed.
        """
        # Call unmount on all cached elements
        for element in self._element_cache.values():
            if hasattr(element, "on_unmount"):
                element.on_unmount()

        self._element_cache.clear()

    def get_cached_element(self, key: str) -> Element | None:
        """Get an element from the cache by key.

        Parameters
        ----------
        key : str
            Element key

        Returns
        -------
        Element or None
            Cached element, or None if not found
        """
        return self._element_cache.get(key)
