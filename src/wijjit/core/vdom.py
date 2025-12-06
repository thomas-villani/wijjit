"""Virtual DOM implementation for Wijjit.

This module provides the VNode data structures used by the reconciliation system
to diff and patch UI element trees efficiently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Ephemeral props that should NOT be synced from template during reconciliation.
# These represent transient UI state that should persist across re-renders.
EPHEMERAL_PROPS = frozenset(
    {
        # Cursor state
        "cursor_pos",
        "cursor_row",
        "cursor_col",
        # Selection state
        "selection_anchor",
        "selection_start",
        "selection_end",
        # Scroll state
        "scroll_position",
        "scroll_x_position",
        # UI interaction state
        "highlighted_index",
        "focused",
        "hovered",
    }
)


@dataclass(frozen=True)
class VNode:
    """Immutable description of a UI element.

    VNodes are lightweight, immutable descriptions of what the UI should look
    like. They are compared by the Reconciler to determine what changes need
    to be made to the actual Element tree.

    Parameters
    ----------
    type : str
        Element type name (e.g., "TextInput", "Button", "VStack")
    key : str or None
        Stable identity for list reconciliation. Elements with matching keys
        are considered the "same" element and will be updated rather than
        replaced.
    props : tuple of (str, Any) pairs
        Immutable properties as a tuple of key-value pairs. Stored as tuple
        for hashability.
    children : tuple of VNode
        Child VNodes for container elements.
    layout_spec : tuple of (str, Any) pairs
        Layout specification (width, height, margin, padding, etc.) as immutable
        tuple of key-value pairs. Used to rebuild LayoutNode tree from reconciled
        elements.

    Attributes
    ----------
    type : str
        Element type name
    key : str or None
        Reconciliation key
    props : tuple
        Immutable props
    children : tuple
        Child VNodes
    layout_spec : tuple
        Immutable layout specification

    Notes
    -----
    VNodes are frozen dataclasses, making them immutable and hashable. This
    ensures reliable comparison during diffing.

    Examples
    --------
    Create a simple VNode:

    >>> vnode = VNode.create("Button", key="submit", props={"label": "Submit"})
    >>> vnode.type
    'Button'
    >>> dict(vnode.props)
    {'label': 'Submit'}

    Create a container with children:

    >>> child1 = VNode.create("TextInput", key="name")
    >>> child2 = VNode.create("Button", key="submit")
    >>> container = VNode.create("VStack", children=[child1, child2])
    >>> len(container.children)
    2
    """

    type: str
    key: str | None = None
    props: tuple[tuple[str, Any], ...] = ()
    children: tuple[VNode, ...] = ()
    layout_spec: tuple[tuple[str, Any], ...] = ()

    @staticmethod
    def create(
        type: str,
        key: str | None = None,
        props: dict[str, Any] | None = None,
        children: list[VNode] | None = None,
        layout_spec: dict[str, Any] | None = None,
    ) -> VNode:
        """Factory method for creating VNodes with dict/list convenience.

        Parameters
        ----------
        type : str
            Element type name
        key : str, optional
            Reconciliation key
        props : dict, optional
            Properties as a dictionary (will be converted to sorted tuple)
        children : list, optional
            Child VNodes as a list (will be converted to tuple)
        layout_spec : dict, optional
            Layout specification (will be converted to sorted tuple)

        Returns
        -------
        VNode
            New immutable VNode instance

        Examples
        --------
        >>> vnode = VNode.create(
        ...     "TextInput",
        ...     key="username",
        ...     props={"placeholder": "Enter username", "width": 30}
        ... )
        """
        return VNode(
            type=type,
            key=key,
            props=tuple(sorted((props or {}).items())),
            children=tuple(children or []),
            layout_spec=tuple(sorted((layout_spec or {}).items())),
        )

    def get_prop(self, name: str, default: Any = None) -> Any:
        """Get a property value by name.

        Parameters
        ----------
        name : str
            Property name to look up
        default : Any, optional
            Value to return if property not found

        Returns
        -------
        Any
            Property value or default

        Examples
        --------
        >>> vnode = VNode.create("Button", props={"label": "Click"})
        >>> vnode.get_prop("label")
        'Click'
        >>> vnode.get_prop("disabled", False)
        False
        """
        for key, value in self.props:
            if key == name:
                return value
        return default

    def props_dict(self) -> dict[str, Any]:
        """Convert props tuple to dictionary.

        Returns
        -------
        dict
            Props as a mutable dictionary

        Examples
        --------
        >>> vnode = VNode.create("Button", props={"label": "OK", "width": 10})
        >>> vnode.props_dict()
        {'label': 'OK', 'width': 10}
        """
        return dict(self.props)

    def layout_spec_dict(self) -> dict[str, Any]:
        """Convert layout_spec tuple to dictionary.

        Returns
        -------
        dict
            Layout spec as a mutable dictionary

        Examples
        --------
        >>> vnode = VNode.create("Button", layout_spec={"width": "fill", "height": 1})
        >>> vnode.layout_spec_dict()
        {'width': 'fill', 'height': 1}
        """
        return dict(self.layout_spec)


class VNodeBuilder:
    """Mutable builder for constructing VNode trees during template execution.

    Since VNodes are immutable, we use this mutable builder during template
    rendering when children are added incrementally. After template execution
    completes, call `freeze()` to convert to an immutable VNode tree.

    Parameters
    ----------
    type : str
        Element type name
    key : str, optional
        Reconciliation key (typically the element id)

    Attributes
    ----------
    type : str
        Element type name
    key : str or None
        Reconciliation key
    props : dict
        Mutable properties dictionary
    children : list
        Mutable list of child VNodeBuilders
    layout_spec : dict
        Layout specification (width, height, etc.) for this node

    Examples
    --------
    Build a tree incrementally:

    >>> root = VNodeBuilder("VStack", key="main")
    >>> root.props["spacing"] = 1
    >>> child = VNodeBuilder("TextInput", key="name")
    >>> child.props["placeholder"] = "Name"
    >>> root.add_child(child)
    >>> vnode = root.freeze()
    >>> len(vnode.children)
    1
    """

    def __init__(self, type: str, key: str | None = None) -> None:
        self.type = type
        self.key = key
        self.props: dict[str, Any] = {}
        self.children: list[VNodeBuilder] = []
        self.layout_spec: dict[str, Any] = {}

    def add_child(self, child: VNodeBuilder) -> None:
        """Add a child VNodeBuilder.

        Parameters
        ----------
        child : VNodeBuilder
            Child node to add
        """
        self.children.append(child)

    def set_prop(self, name: str, value: Any) -> None:
        """Set a property value.

        Parameters
        ----------
        name : str
            Property name
        value : Any
            Property value
        """
        self.props[name] = value

    def set_layout(self, **kwargs: Any) -> None:
        """Set layout specification.

        Width and height are also copied to props (if not already set) so
        elements receive them as constructor parameters. This ensures elements
        like ImageView that need sizing information get it automatically.

        For elements that need different values for layout vs element (e.g.,
        LogView with borders where layout includes border space), call
        set_prop("width", ...) BEFORE set_layout() to set the element's
        internal dimensions separately from the layout dimensions.

        Parameters
        ----------
        **kwargs
            Layout parameters (width, height, margin, etc.)
        """
        self.layout_spec.update(kwargs)
        # Auto-sync sizing to props for elements that need them as constructor params
        # Only sync if prop isn't already set (allows explicit override)
        if "width" in kwargs and "width" not in self.props:
            self.props["width"] = kwargs["width"]
        if "height" in kwargs and "height" not in self.props:
            self.props["height"] = kwargs["height"]

    def freeze(self) -> VNode:
        """Convert to immutable VNode tree.

        Recursively freezes all children and preserves layout specification.

        Returns
        -------
        VNode
            Immutable VNode tree with layout_spec preserved

        Examples
        --------
        >>> builder = VNodeBuilder("Button", key="ok")
        >>> builder.props["label"] = "OK"
        >>> builder.set_layout(width="fill", height=1)
        >>> vnode = builder.freeze()
        >>> isinstance(vnode, VNode)
        True
        >>> vnode.get_prop("label")
        'OK'
        >>> vnode.layout_spec_dict()
        {'width': 'fill', 'height': 1}
        """
        return VNode(
            type=self.type,
            key=self.key,
            props=tuple(sorted(self.props.items())),
            children=tuple(child.freeze() for child in self.children),
            layout_spec=tuple(sorted(self.layout_spec.items())),
        )

    def __repr__(self) -> str:
        return f"VNodeBuilder({self.type!r}, key={self.key!r}, children={len(self.children)})"


def is_ephemeral_prop(prop_name: str) -> bool:
    """Check if a property name is ephemeral (should not be synced from template).

    Parameters
    ----------
    prop_name : str
        Property name to check

    Returns
    -------
    bool
        True if the property is ephemeral

    Examples
    --------
    >>> is_ephemeral_prop("cursor_pos")
    True
    >>> is_ephemeral_prop("placeholder")
    False
    """
    return prop_name in EPHEMERAL_PROPS


@dataclass
class LayoutSpec:
    """Layout specification for a VNode.

    Stores layout-related properties that will be used when creating
    LayoutNodes (ElementNode, FrameNode, VStack, HStack).

    Parameters
    ----------
    width : int, str, or None
        Width specification ("fill", "auto", percentage, or fixed)
    height : int, str, or None
        Height specification
    margin : int or tuple, optional
        Margin around the element
    align_h : str, optional
        Horizontal alignment
    align_v : str, optional
        Vertical alignment
    """

    width: int | str | None = None
    height: int | str | None = None
    margin: int | tuple[int, int, int, int] | None = None
    padding: int | tuple[int, int, int, int] | None = None
    spacing: int | None = None
    align_h: str | None = None
    align_v: str | None = None
    content_align_h: str | None = None
    content_align_v: str | None = None

    # Container-specific
    is_container: bool = False
    container_type: str | None = None  # "vstack", "hstack", "frame"

    # Frame-specific
    border_style: str | None = None
    title: str | None = None
    scrollable: bool = False
    show_scrollbar: bool = True
    overflow_x: str | None = None
    overflow_y: str | None = None
