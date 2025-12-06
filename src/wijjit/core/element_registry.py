"""Element registry for Virtual DOM reconciliation.

This module provides a registry that maps VNode type names to Element factory
functions, enabling the reconciler to create Element instances from VNodes.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from wijjit.core.vdom import VNode
    from wijjit.elements.base import Element

logger = get_logger(__name__)


class ElementRegistry:
    """Registry mapping VNode types to Element factories.

    The ElementRegistry maintains a mapping from VNode type strings (like
    "TextInput", "Button") to Element class constructors. During reconciliation,
    when a new element needs to be created, the registry provides the appropriate
    factory function.

    Attributes
    ----------
    _factories : dict
        Mapping of type name to Element class/factory

    Examples
    --------
    >>> registry = ElementRegistry()
    >>> from wijjit.core.vdom import VNode
    >>> vnode = VNode.create("Button", props={"label": "OK"})
    >>> element = registry.create_element(vnode)
    >>> element.__class__.__name__
    'Button'
    """

    def __init__(self) -> None:
        self._factories: dict[str, type] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in element types."""
        # Import all element classes
        # Input elements
        # Base elements
        from wijjit.elements.base import Container, TextElement
        from wijjit.elements.display.barchart import BarChart
        from wijjit.elements.display.columnchart import ColumnChart
        from wijjit.elements.display.contentview import ContentView
        from wijjit.elements.display.gauge import Gauge
        from wijjit.elements.display.heatmap import HeatMap
        from wijjit.elements.display.image import ImageView
        from wijjit.elements.display.linechart import LineChart
        from wijjit.elements.display.link import Link
        from wijjit.elements.display.list import ListView
        from wijjit.elements.display.logview import LogView
        from wijjit.elements.display.modal import ModalElement
        from wijjit.elements.display.notification import NotificationElement
        from wijjit.elements.display.progress import ProgressBar

        # Chart elements
        from wijjit.elements.display.sparkline import Sparkline
        from wijjit.elements.display.spinner import Spinner
        from wijjit.elements.display.statusbar import StatusBar

        # Note: TabbedPanel is intentionally NOT imported here.
        # It manages tabs internally via template extension, similar to Frame.
        # Display elements
        from wijjit.elements.display.table import Table
        from wijjit.elements.display.tree import Tree
        from wijjit.elements.input.button import Button
        from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup
        from wijjit.elements.input.code_editor import CodeEditor
        from wijjit.elements.input.radio import Radio, RadioGroup
        from wijjit.elements.input.select import Select
        from wijjit.elements.input.text import TextArea, TextInput

        # Menu elements
        from wijjit.elements.menu import ContextMenu, DropdownMenu, MenuElement

        # Note: Frame, VStack and HStack are NOT registered because they require
        # layout information (width/height) to be instantiated. They are handled
        # specially in the layout tree building logic where layout_spec is available.

        # Register all element types
        self._factories = {
            # Input elements
            "TextInput": TextInput,
            "TextArea": TextArea,
            "Button": Button,
            "Checkbox": Checkbox,
            "CheckboxGroup": CheckboxGroup,
            "Radio": Radio,
            "RadioGroup": RadioGroup,
            "Select": Select,
            "CodeEditor": CodeEditor,
            # Display elements
            "Table": Table,
            "TreeView": Tree,
            "Tree": Tree,
            "ListView": ListView,
            "LogView": LogView,
            "ProgressBar": ProgressBar,
            "Progress": ProgressBar,  # Alias
            "Spinner": Spinner,
            "StatusBar": StatusBar,
            "Notification": NotificationElement,
            "Modal": ModalElement,
            # Note: TabbedPanel is NOT registered because it manages its own
            # tabs internally. The template extension creates and populates it
            # directly, similar to how Frame/VStack/HStack work.
            "Link": Link,
            "ContentView": ContentView,
            # Chart elements
            "Sparkline": Sparkline,
            "BarChart": BarChart,
            "LineChart": LineChart,
            "ColumnChart": ColumnChart,
            "Heatmap": HeatMap,
            "HeatMap": HeatMap,
            "Gauge": Gauge,
            "ImageView": ImageView,
            "Image": ImageView,  # Alias
            # Menu elements
            "MenuElement": MenuElement,
            "Menu": MenuElement,  # Alias
            "DropdownMenu": DropdownMenu,
            "ContextMenu": ContextMenu,
            # Base elements
            "TextElement": TextElement,
            "Text": TextElement,  # Alias
            "Container": Container,
        }

    def register(self, type_name: str, factory: type) -> None:
        """Register a custom element type.

        Parameters
        ----------
        type_name : str
            VNode type name to register
        factory : type
            Element class or factory function

        Examples
        --------
        >>> registry = ElementRegistry()
        >>> class CustomWidget(Element):
        ...     pass
        >>> registry.register("CustomWidget", CustomWidget)
        """
        self._factories[type_name] = factory

    def unregister(self, type_name: str) -> None:
        """Unregister an element type.

        Parameters
        ----------
        type_name : str
            VNode type name to unregister

        Raises
        ------
        KeyError
            If type_name is not registered
        """
        del self._factories[type_name]

    def has_type(self, type_name: str) -> bool:
        """Check if a type is registered.

        Parameters
        ----------
        type_name : str
            VNode type name to check

        Returns
        -------
        bool
            True if type is registered
        """
        return type_name in self._factories

    def create_element(self, vnode: VNode) -> Element:
        """Create an Element instance from a VNode.

        Parameters
        ----------
        vnode : VNode
            Virtual node describing the element

        Returns
        -------
        Element
            New Element instance

        Raises
        ------
        KeyError
            If vnode.type is not registered
        ValueError
            If element creation fails

        Examples
        --------
        >>> from wijjit.core.vdom import VNode
        >>> registry = ElementRegistry()
        >>> vnode = VNode.create("TextInput", props={"id": "name", "placeholder": "Name"})
        >>> element = registry.create_element(vnode)
        >>> element.id
        'name'
        """
        if vnode.type not in self._factories:
            raise KeyError(f"Unknown element type: {vnode.type!r}")

        factory = self._factories[vnode.type]
        props = vnode.props_dict()

        # Merge layout specs (width, height, etc.) with props for elements that need them
        # Some elements like ImageView accept width/height as constructor parameters
        layout_spec = vnode.layout_spec_dict()
        if layout_spec:
            # Only include layout specs that the factory accepts as parameters
            # This allows elements to receive width/height if they expect them
            props = {**props, **layout_spec}

        # Filter props to only those accepted by the factory
        valid_props = self._filter_props_for_factory(factory, props)

        try:
            return factory(**valid_props)
        except TypeError as e:
            logger.error(
                f"Failed to create element {vnode.type} with props {valid_props}: {e}"
            )
            raise ValueError(f"Failed to create element {vnode.type}: {e}") from e

    def _filter_props_for_factory(
        self,
        factory: type,
        props: dict[str, Any],
    ) -> dict[str, Any]:
        """Filter props to only those accepted by the factory's __init__.

        Parameters
        ----------
        factory : type
            Element class
        props : dict
            All props from VNode

        Returns
        -------
        dict
            Props that match factory constructor parameters
        """
        try:
            sig = inspect.signature(factory.__init__)
            valid_params = set(sig.parameters.keys()) - {"self"}

            # Check for **kwargs - if present, accept all props
            for param in sig.parameters.values():
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    return props

            # Filter to only valid parameters
            return {k: v for k, v in props.items() if k in valid_params}
        except (ValueError, TypeError):
            # If we can't inspect, just return all props and let it fail naturally
            return props

    def get_factory(self, type_name: str) -> type | None:
        """Get the factory for a type name.

        Parameters
        ----------
        type_name : str
            VNode type name

        Returns
        -------
        type or None
            Element class/factory, or None if not registered
        """
        return self._factories.get(type_name)

    def list_types(self) -> list[str]:
        """List all registered type names.

        Returns
        -------
        list of str
            Sorted list of registered type names
        """
        return sorted(self._factories.keys())
