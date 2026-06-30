"""Tabbed panel element for displaying multiple frames with tab interface.

This module provides a tabbed panel element that allows switching between
multiple child frames using tabs positioned on any side.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Union

from wijjit.elements.base import Container, ElementType, delegate_frame_scroll
from wijjit.layout.frames import BORDER_CHARS, BorderStyle, Frame
from wijjit.logging_config import get_logger
from wijjit.terminal.ansi import clip_to_width, visible_length
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.layout.engine import FrameNode
    from wijjit.rendering.paint_context import PaintContext


logger = get_logger(__name__)
# Type alias for tab content - can be Frame or FrameNode
TabContent = Union["Frame", "FrameNode"]


class TabPosition(Enum):
    """Position of tabs relative to content area.

    Attributes
    ----------
    TOP : auto
        Tabs displayed above content (horizontal layout)
    BOTTOM : auto
        Tabs displayed below content (horizontal layout)
    LEFT : auto
        Tabs displayed to left of content (vertical layout)
    RIGHT : auto
        Tabs displayed to right of content (vertical layout)
    """

    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()


class TabbedPanel(Container):
    """Tabbed panel element for displaying multiple frames with tab switching.

    This element provides a tab interface for switching between multiple child
    frames. Tabs can be positioned on any side of the content area and support
    both keyboard and mouse navigation.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str or set of str, optional
        CSS class names for styling
    tab_position : TabPosition, optional
        Position of tabs (default: TabPosition.TOP)
    width : int, optional
        Total panel width (default: 60)
    height : int, optional
        Total panel height (default: 20)
    border_style : str, optional
        Border style: "single", "double", "rounded" (default: "single")
    active_tab_index : int, optional
        Initially active tab index (default: 0)

    Attributes
    ----------
    tabs : list of tuple
        List of (label, frame) tuples representing tabs
    active_tab_index : int
        Index of currently active tab
    tab_position : TabPosition
        Position of tabs
    width : int
        Total panel width
    height : int
        Total panel height
    border_style : BorderStyle
        Border style for panel
    on_tab_change : Callable or None
        Callback when active tab changes: on_tab_change(index, label)

    Notes
    -----
    Navigation:
    - Horizontal tabs (TOP/BOTTOM): Left/Right arrows switch tabs
    - Vertical tabs (LEFT/RIGHT): Up/Down arrows switch tabs
    - Mouse click on tab: Switch to that tab
    - Enter/Space: Activate highlighted tab

    State Persistence:
    - Active tab index is saved to state[id] or state[active_tab_key]
    - Tab state is restored on render
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        tab_index: int | None = None,
        tab_position: TabPosition = TabPosition.TOP,
        width: int = 60,
        height: int = 20,
        border_style: str = "single",
        active_tab_index: int = 0,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.element_type = ElementType.DISPLAY
        self.focusable = True

        # Tab configuration - stores (label, content) where content can be Frame or FrameNode
        self.tabs: list[tuple[str, TabContent]] = []
        self.active_tab_index = active_tab_index
        self.tab_position = tab_position

        # Display properties
        self.width = width
        self.height = height

        # Parse border style
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
        }
        self.border_style = border_map.get(border_style, BorderStyle.SINGLE)

        # Callbacks
        self.on_tab_change: Callable[[int, str], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence - auto-generated from id
        self._active_tab_state_key_override: str | None = None
        self._state_dict: dict[str, Any] | None = None

    @property
    def active_tab_state_key(self) -> str | None:
        """Get the state key for active tab index.

        Returns the explicitly set key if provided, otherwise auto-generates
        from the element id using the convention "{id}:active_tab".

        Returns
        -------
        str or None
            State key for active tab, or None if no id
        """
        if self._active_tab_state_key_override is not None:
            return self._active_tab_state_key_override
        return self._state_key("active_tab")

    @active_tab_state_key.setter
    def active_tab_state_key(self, value: str | None) -> None:
        """Set an explicit active tab state key."""
        self._active_tab_state_key_override = value

    def add_tab(self, label: str, content: TabContent) -> None:
        """Add a tab to the panel.

        Parameters
        ----------
        label : str
            Tab label text
        content : Frame or FrameNode
            Content for the tab - can be a Frame object or FrameNode with children
        """
        self.tabs.append((label, content))

    def switch_to_tab(self, index: int) -> None:
        """Switch to a specific tab by index.

        Parameters
        ----------
        index : int
            Tab index to switch to

        Notes
        -----
        If index is out of range, it will be clamped to valid range.
        Emits on_tab_change callback if tab actually changed.
        Saves state if state persistence is enabled.
        """
        if not self.tabs:
            return

        # Clamp index to valid range
        old_index = self.active_tab_index
        self.active_tab_index = max(0, min(index, len(self.tabs) - 1))

        # Only trigger callbacks if tab actually changed
        if old_index != self.active_tab_index:
            # Save to state
            self._save_active_tab_state()

            # Emit callback
            if self.on_tab_change:
                label = self.tabs[self.active_tab_index][0]
                self.on_tab_change(self.active_tab_index, label)

    def _save_active_tab_state(self) -> None:
        """Save active tab index to app state if available."""
        if self._state_dict is not None and self.active_tab_state_key:
            self._state_dict[self.active_tab_state_key] = self.active_tab_index

    def _wire_frame_scroll_state(self, frame: Any) -> None:
        """Wire up scroll state persistence for a frame.

        This method sets up the on_scroll callback to save scroll position
        to state, and restores the scroll position from state if available.

        Parameters
        ----------
        frame : Frame
            The frame to wire up scroll state for
        """
        from wijjit.layout.frames import Frame

        if not isinstance(frame, Frame):
            return

        scroll_key = getattr(frame, "scroll_state_key", None)
        if not scroll_key or self._state_dict is None:
            return

        # Set up on_scroll callback to save position to state
        def on_scroll_handler(position: int, skey: str = scroll_key) -> None:
            if self._state_dict is not None:
                self._state_dict[skey] = position

        frame.on_scroll = on_scroll_handler

        # Restore scroll position from state if available
        if scroll_key in self._state_dict:
            saved_position = self._state_dict[scroll_key]
            if (
                isinstance(saved_position, int)
                and saved_position > 0
                and hasattr(frame, "restore_scroll_position")
            ):
                frame.restore_scroll_position(saved_position)
                logger.debug(
                    f"Restored scroll position {saved_position} for {scroll_key}"
                )

    def get_focusable_children(self) -> list[Any]:
        """Get focusable children from the active tab's content.

        Returns
        -------
        list
            List of focusable elements in the active tab
        """
        if not self.tabs or not (0 <= self.active_tab_index < len(self.tabs)):
            return []

        _, active_content = self.tabs[self.active_tab_index]

        # Check if content is a FrameNode with children
        from wijjit.layout.engine import FrameNode

        if isinstance(active_content, FrameNode):
            # Collect focusable elements from FrameNode children
            focusable: list[Any] = []
            self._collect_focusable(active_content.children, focusable)
            return focusable

        # Check if frame has a FrameNode reference (backwards compatibility)
        if hasattr(active_content, "_frame_node"):
            frame_node = active_content._frame_node
            if (
                hasattr(frame_node, "content_container")
                and frame_node.content_container
            ):
                # Collect focusable elements from content_container
                focusable = []
                self._collect_focusable(
                    frame_node.content_container.children, focusable
                )
                return focusable
        return []

    def _collect_focusable(self, nodes: list[Any], result: list[Any]) -> None:
        """Recursively collect focusable elements from layout nodes.

        Parameters
        ----------
        nodes : list
            List of layout nodes to search
        result : list
            List to append focusable elements to
        """
        for node in nodes:
            # Check if it's an ElementNode with a focusable element
            if hasattr(node, "element") and hasattr(node.element, "focusable"):
                if node.element.focusable:
                    result.append(node.element)
            # Recurse into children
            if hasattr(node, "children"):
                self._collect_focusable(node.children, result)
            if hasattr(node, "content_container") and hasattr(
                node.content_container, "children"
            ):
                self._collect_focusable(node.content_container.children, result)

    def collect_child_elements(self) -> list[Any]:
        """Collect all child elements from the active tab for event routing.

        Returns
        -------
        list
            List of all elements in the active tab's content

        Notes
        -----
        This method is called by ElementNode.collect_elements() to include
        nested elements in the positioned_elements list for focus and mouse
        event routing.
        """
        if not self.tabs or not (0 <= self.active_tab_index < len(self.tabs)):
            return []

        _, active_content = self.tabs[self.active_tab_index]

        from wijjit.layout.engine import FrameNode

        elements: list[Any] = []

        if isinstance(active_content, FrameNode):
            # Collect all elements from FrameNode children
            self._collect_all_elements(
                active_content.content_container.children, elements
            )
        elif hasattr(active_content, "_frame_node"):
            frame_node = active_content._frame_node
            if (
                hasattr(frame_node, "content_container")
                and frame_node.content_container
            ):
                self._collect_all_elements(
                    frame_node.content_container.children, elements
                )

        return elements

    def _collect_all_elements(self, nodes: list[Any], result: list[Any]) -> None:
        """Recursively collect all elements from layout nodes.

        Parameters
        ----------
        nodes : list
            List of layout nodes to search
        result : list
            List to append elements to
        """
        from wijjit.elements.base import TextElement

        for node in nodes:
            if hasattr(node, "element"):
                # Skip TextElements - they're not interactive
                if not isinstance(node.element, TextElement):
                    result.append(node.element)
            # Recurse into children
            if hasattr(node, "children"):
                self._collect_all_elements(node.children, result)
            if hasattr(node, "content_container") and hasattr(
                node.content_container, "children"
            ):
                self._collect_all_elements(node.content_container.children, result)

    def _is_horizontal(self) -> bool:
        """Check if tabs are laid out horizontally.

        Returns
        -------
        bool
            True if tabs are horizontal (TOP or BOTTOM position)
        """
        return self.tab_position in (TabPosition.TOP, TabPosition.BOTTOM)

    def _calculate_children_height(self, children: list[Any]) -> int:
        """Calculate total height of children for scrolling.

        Parameters
        ----------
        children : list
            List of layout nodes

        Returns
        -------
        int
            Total height of all children
        """
        from wijjit.elements.base import TextElement
        from wijjit.layout.engine import ElementNode

        total = 0
        for child in children:
            if isinstance(child, ElementNode):
                element = child.element
                if isinstance(element, TextElement):
                    # Count lines in text
                    text = element.text if hasattr(element, "text") else ""
                    total += len(text.split("\n")) if text else 0
                elif hasattr(element, "get_intrinsic_size"):
                    _, h = element.get_intrinsic_size()
                    total += h
                else:
                    total += 1
            elif hasattr(child, "children"):
                total += self._calculate_children_height(child.children)
            else:
                total += 1
        return total

    def _render_tab_content(
        self,
        ctx: PaintContext,
        content: TabContent,
        content_x: int,
        content_y: int,
        content_width: int,
        content_height: int,
    ) -> None:
        """Render the content of a tab (Frame or FrameNode with children).

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        content : TabContent
            The tab content - either Frame or FrameNode
        content_x : int
            X position for content area
        content_y : int
            Y position for content area
        content_width : int
            Width of content area
        content_height : int
            Height of content area
        """
        from wijjit.layout.bounds import Bounds
        from wijjit.layout.engine import FrameNode

        # Check if content is a FrameNode (has children)
        if isinstance(content, FrameNode):
            frame = content.frame
            frame.width = content_width
            frame.height = content_height
            frame.bounds = Bounds(
                x=content_x,
                y=content_y,
                width=content_width,
                height=content_height,
            )

            # Update scroll manager viewport after dimension change
            # This ensures scrollability is calculated based on actual render size
            if hasattr(frame, "update_viewport_for_current_size"):
                frame.update_viewport_for_current_size()

            # Wire up scroll state persistence for this frame
            self._wire_frame_scroll_state(frame)

            # Create sub-context for content area
            rel_x = content_x - ctx.bounds.x
            rel_y = content_y - ctx.bounds.y
            content_ctx = ctx.sub_context(rel_x, rel_y, content_width, content_height)

            # For tabs with children (not text content), we need to set up scrolling
            # by telling the frame the total content height
            if not frame.content and content.content_container.children:
                # Calculate total height of children
                total_child_height = self._calculate_children_height(
                    content.content_container.children
                )
                frame.set_child_content_height(total_child_height)

            # Render the frame (border and scrollbar, and content if set)
            frame.render_to(content_ctx)

            # Only render children if Frame doesn't have its own content
            # (to avoid double-rendering text that was extracted to frame.content)
            if not frame.content:
                self._render_children(
                    ctx,
                    content.content_container.children,
                    content_x + 1,  # +1 for frame border
                    content_y + 1,  # +1 for frame border
                    content_width - 2,  # -2 for borders
                    content_height - 2,  # -2 for borders
                    (
                        frame.get_scroll_offset()
                        if hasattr(frame, "get_scroll_offset")
                        else 0
                    ),
                )
        else:
            # It's a plain Frame - just render it
            frame = content
            frame.width = content_width
            frame.height = content_height
            frame.bounds = Bounds(
                x=content_x,
                y=content_y,
                width=content_width,
                height=content_height,
            )

            # Update scroll manager viewport after dimension change
            if hasattr(frame, "update_viewport_for_current_size"):
                frame.update_viewport_for_current_size()

            # Wire up scroll state persistence for this frame
            self._wire_frame_scroll_state(frame)

            # Create sub-context for content area
            rel_x = content_x - ctx.bounds.x
            rel_y = content_y - ctx.bounds.y
            content_ctx = ctx.sub_context(rel_x, rel_y, content_width, content_height)

            # Render the frame
            frame.render_to(content_ctx)

    def _render_children(
        self,
        ctx: PaintContext,
        children: list[Any],
        start_x: int,
        start_y: int,
        available_width: int,
        available_height: int,
        scroll_offset: int = 0,
    ) -> None:
        """Recursively render layout node children.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        children : list
            List of layout nodes to render
        start_x : int
            Starting X position
        start_y : int
            Starting Y position
        available_width : int
            Available width for content
        available_height : int
            Available height for content
        scroll_offset : int
            Vertical scroll offset
        """
        from wijjit.elements.base import TextElement
        from wijjit.layout.bounds import Bounds
        from wijjit.layout.engine import ElementNode

        current_y = start_y - scroll_offset

        for child in children:
            # Skip if completely scrolled out of view
            if current_y >= start_y + available_height:
                break

            if isinstance(child, ElementNode):
                element = child.element

                # Check if it's a TextElement (text content)
                if isinstance(element, TextElement):
                    # Render text element
                    if current_y >= start_y - 1:  # Show if in or near visible area
                        text = element.text if hasattr(element, "text") else ""
                        lines = text.split("\n") if text else []
                        for line in lines:
                            if start_y <= current_y < start_y + available_height:
                                text_style = ctx.style_resolver.resolve_style_by_class(
                                    "text"
                                )
                                clipped_line = clip_to_width(line, available_width)
                                # Convert to relative coordinates for ctx.write_text
                                rel_x = start_x - ctx.bounds.x
                                rel_y = current_y - ctx.bounds.y
                                ctx.write_text(rel_x, rel_y, clipped_line, text_style)
                            current_y += 1
                else:
                    # Render other elements (buttons, inputs, etc.)
                    # Get height from element's intrinsic size or use default
                    if hasattr(element, "get_intrinsic_size"):
                        _, element_height = element.get_intrinsic_size()
                    else:
                        element_height = 1

                    # Set bounds on element
                    element.bounds = Bounds(
                        x=start_x,
                        y=current_y,
                        width=available_width,
                        height=element_height,
                    )

                    # Only render if visible
                    if (
                        current_y + element_height > start_y
                        and current_y < start_y + available_height
                    ):
                        # Create sub-context for element
                        rel_x = start_x - ctx.bounds.x
                        rel_y = current_y - ctx.bounds.y
                        elem_ctx = ctx.sub_context(
                            rel_x, rel_y, available_width, element_height
                        )
                        element.render_to(elem_ctx)

                    current_y += element_height

            elif hasattr(child, "children"):
                # Container node - recurse
                # Calculate height used by this container's children
                container_height = getattr(child, "height", available_height)
                if isinstance(container_height, str):
                    container_height = available_height

                self._render_children(
                    ctx,
                    child.children,
                    start_x,
                    current_y,
                    available_width,
                    min(container_height, available_height),
                    0,  # Don't apply scroll offset again
                )
                current_y += container_height

    def _calculate_tab_dimensions(self) -> tuple[int, int, int, int]:
        """Calculate tab area and content area dimensions.

        Returns
        -------
        tuple of int
            (tab_area_width, tab_area_height, content_width, content_height)

        Notes
        -----
        For horizontal tabs (TOP/BOTTOM):
        - Tab area: full width, 3 lines height (border + content + border)
        - Content area: full width, remaining height

        For vertical tabs (LEFT/RIGHT):
        - Tab area: max label width + 4 chars, full content height
        - Content area: remaining width, full height
        """
        if self._is_horizontal():
            # Horizontal tabs (TOP/BOTTOM)
            tab_area_height = 3  # top border + tab labels + bottom border
            content_height = self.height - tab_area_height

            return self.width, tab_area_height, self.width, content_height
        else:
            # Vertical tabs (LEFT/RIGHT)
            # Calculate max label width (with some padding)
            max_label_width = max(
                (visible_length(label) for label, _ in self.tabs), default=0
            )
            tab_area_width = max_label_width + 4  # borders + padding

            content_width = self.width - tab_area_width
            content_height = self.height

            return tab_area_width, content_height, content_width, content_height

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for tab navigation and content scrolling.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled

        Notes
        -----
        Tab switching:
        - Horizontal (TOP/BOTTOM): Left/Right to switch tabs
        - Vertical (LEFT/RIGHT): Up/Down to switch tabs

        All other keys are delegated to the active frame's content,
        allowing natural scrolling (Up/Down/PageUp/PageDown/Home/End)
        and any other key handling the frame supports.
        """
        if not self.tabs:
            return False

        # Note: Tab/Shift+Tab are intercepted by the app for focus navigation,
        # so we use Left/Right (or Up/Down for vertical) for tab switching.

        # Handle tab-switching keys ONLY
        if self._is_horizontal():
            # Horizontal tabs: use Left/Right to switch tabs
            if key == Keys.LEFT:
                self.switch_to_tab(self.active_tab_index - 1)
                return True
            elif key == Keys.RIGHT:
                self.switch_to_tab(self.active_tab_index + 1)
                return True
        else:
            # Vertical tabs: use Up/Down to switch tabs
            if key == Keys.UP:
                self.switch_to_tab(self.active_tab_index - 1)
                return True
            elif key == Keys.DOWN:
                self.switch_to_tab(self.active_tab_index + 1)
                return True

        # Delegate ALL other keys to the active frame
        # This allows the frame to handle scrolling (Up/Down/PageUp/PageDown/Home/End)
        # and any other keys it supports
        if 0 <= self.active_tab_index < len(self.tabs):
            _, active_content = self.tabs[self.active_tab_index]

            # Get the Frame object (may be wrapped in FrameNode)
            from wijjit.layout.engine import FrameNode

            if isinstance(active_content, FrameNode):
                frame = active_content.frame
            else:
                frame = active_content

            if hasattr(frame, "handle_key"):
                return frame.handle_key(key)

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input for tab clicking and content scrolling.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled

        Notes
        -----
        Handles:
        - Left clicks on tab labels to switch tabs
        - Scroll wheel events delegated to active frame for scrolling
        """
        if not self.bounds or not self.tabs:
            return False

        # Handle scroll wheel events - delegate to active frame
        if event.type == MouseEventType.SCROLL:
            if 0 <= self.active_tab_index < len(self.tabs):
                _, active_content = self.tabs[self.active_tab_index]

                # Get the Frame object (may be wrapped in FrameNode)
                from wijjit.layout.engine import FrameNode

                if isinstance(active_content, FrameNode):
                    frame = active_content.frame
                else:
                    frame = active_content

                # Convert scroll direction: SCROLL_UP = -1, SCROLL_DOWN = 1
                direction = 1 if event.button == MouseButton.SCROLL_DOWN else -1
                return delegate_frame_scroll(frame, direction)
            return False

        # Handle left clicks (or press) for tab switching
        # Accept both CLICK (synthesized) and PRESS (raw) for compatibility
        if event.button != MouseButton.LEFT:
            return False
        if event.type not in (MouseEventType.CLICK, MouseEventType.PRESS):
            return False

        # Convert to relative coordinates
        relative_x = event.x - self.bounds.x
        relative_y = event.y - self.bounds.y

        # Determine if click is in tab area
        if self._is_horizontal():
            # Horizontal tabs
            if self.tab_position == TabPosition.TOP:
                # Tab area is at top (line 0 - tabs are on the top border)
                if relative_y != 0:
                    return False
            else:  # TabPosition.BOTTOM
                # Tab area is at bottom (last line)
                if relative_y != self.height - 1:
                    return False

            # Calculate which tab was clicked based on X position
            # Tab format: [Label] for active (len+2), " Label " for inactive (len+2)
            # All tabs have label_width + 2 characters, plus separator between
            current_x = 1  # Start after left border corner
            for i, (label, _) in enumerate(self.tabs):
                label_width = visible_length(label)
                tab_width = label_width + 2  # brackets or spaces around label
                if current_x <= relative_x < current_x + tab_width:
                    self.switch_to_tab(i)
                    return True
                current_x += tab_width + 1  # Move to next tab (with separator)

        else:
            # Vertical tabs
            if self.tab_position == TabPosition.LEFT:
                # Tab area is on left side
                tab_area_width, _, _, _ = self._calculate_tab_dimensions()
                if relative_x >= tab_area_width:
                    return False
            else:  # TabPosition.RIGHT
                # Tab area is on right side
                tab_area_width, _, content_width, _ = self._calculate_tab_dimensions()
                if relative_x < content_width:
                    return False

            # Calculate which tab was clicked based on Y position
            # Each tab occupies one line (starting from line 1, after top border)
            tab_index = relative_y - 1
            if 0 <= tab_index < len(self.tabs):
                self.switch_to_tab(tab_index)
                return True

        return False

    def get_ephemeral_state(self) -> dict:
        """Get ephemeral state for reconciliation.

        Returns
        -------
        dict
            Active tab index that should survive re-renders.
        """
        return {
            "active_tab_index": self.active_tab_index,
        }

    def restore_ephemeral_state(self, state: dict) -> None:
        """Restore ephemeral state after reconciliation.

        Parameters
        ----------
        state : dict
            State dict from get_ephemeral_state()
        """
        if "active_tab_index" in state:
            # Use switch_to_tab to properly handle bounds and callbacks
            self.switch_to_tab(state["active_tab_index"])

    def render_to(self, ctx: PaintContext) -> None:
        """Render tabbed panel using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Renders the tab interface and active tab's content:
        1. Render tab area with labels
        2. Highlight active tab
        3. Render borders around panel
        4. Render active tab's frame content in content area

        Theme styles:

        This element uses the following theme style classes:
        - ``tabbedpanel``: Base panel style
        - ``tabbedpanel:focus``: When panel has focus
        - ``tabbedpanel.tab``: Tab label style
        - ``tabbedpanel.tab:active``: Active tab style
        - ``tabbedpanel.border``: Border style
        """

        # Capture bounds for mouse hit testing
        self.bounds = ctx.bounds

        if not self.tabs:
            # No tabs - render empty panel with message
            empty_style = ctx.style_resolver.resolve_style(self, "tabbedpanel")
            ctx.write_text(0, 0, "No tabs defined", empty_style)
            return

        # Resolve styles
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(
                self, "tabbedpanel.border:focus"
            )
            tab_style = ctx.style_resolver.resolve_style(self, "tabbedpanel.tab:focus")
        else:
            border_style = ctx.style_resolver.resolve_style(self, "tabbedpanel.border")
            tab_style = ctx.style_resolver.resolve_style(self, "tabbedpanel.tab")

        active_tab_style = ctx.style_resolver.resolve_style(
            self, "tabbedpanel.tab:active"
        )

        # Get border characters
        chars = BORDER_CHARS[self.border_style]
        border_attrs = border_style.to_cell_attrs()
        tab_attrs = tab_style.to_cell_attrs()
        active_tab_attrs = active_tab_style.to_cell_attrs()

        # When panel is focused, make border bold/bright
        if self.focused:
            border_attrs["bold"] = True
            tab_attrs["bold"] = True

        # Calculate dimensions
        (
            tab_area_width,
            tab_area_height,
            content_width,
            content_height,
        ) = self._calculate_tab_dimensions()

        # Render based on tab position
        if self.tab_position == TabPosition.TOP:
            self._render_top_tabs(
                ctx,
                chars,
                border_attrs,
                tab_attrs,
                active_tab_attrs,
                tab_area_height,
                content_width,
                content_height,
            )
        elif self.tab_position == TabPosition.BOTTOM:
            self._render_bottom_tabs(
                ctx,
                chars,
                border_attrs,
                tab_attrs,
                active_tab_attrs,
                tab_area_height,
                content_width,
                content_height,
            )
        elif self.tab_position == TabPosition.LEFT:
            self._render_left_tabs(
                ctx,
                chars,
                border_attrs,
                tab_attrs,
                active_tab_attrs,
                tab_area_width,
                content_width,
                content_height,
            )
        else:  # TabPosition.RIGHT
            self._render_right_tabs(
                ctx,
                chars,
                border_attrs,
                tab_attrs,
                active_tab_attrs,
                tab_area_width,
                content_width,
                content_height,
            )

    def _render_top_tabs(
        self,
        ctx: PaintContext,
        chars: dict,
        border_attrs: dict,
        tab_attrs: dict,
        active_tab_attrs: dict,
        tab_area_height: int,
        content_width: int,
        content_height: int,
    ) -> None:
        """Render tabs at top position.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        tab_attrs : dict
            Tab cell attributes
        active_tab_attrs : dict
            Active tab cell attributes
        tab_area_height : int
            Height of tab area
        content_width : int
            Width of content area
        content_height : int
            Height of content area
        """
        from wijjit.terminal.cell import Cell

        # Line 0: Top border with tab labels
        current_x = 0

        # Top-left corner
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
        )
        current_x += 1

        # Render each tab label on the top border line
        for i, (label, _) in enumerate(self.tabs):
            is_active = i == self.active_tab_index
            label_attrs = active_tab_attrs if is_active else tab_attrs

            # Tab format: [Label] for active, " Label " for inactive
            if is_active:
                tab_text = f"[{label}]"
            else:
                tab_text = f" {label} "

            for char in tab_text:
                if current_x < self.width - 1:
                    ctx.buffer.set_cell(
                        ctx.bounds.x + current_x,
                        ctx.bounds.y,
                        Cell(char=char, **label_attrs),
                    )
                    current_x += 1

            # Separator between tabs (if not last tab)
            if i < len(self.tabs) - 1 and current_x < self.width - 1:
                ctx.buffer.set_cell(
                    ctx.bounds.x + current_x,
                    ctx.bounds.y,
                    Cell(char=chars["h"], **border_attrs),
                )
                current_x += 1

        # Fill remaining top border
        while current_x < self.width - 1:
            ctx.buffer.set_cell(
                ctx.bounds.x + current_x,
                ctx.bounds.y,
                Cell(char=chars["h"], **border_attrs),
            )
            current_x += 1

        # Top-right corner
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y,
            Cell(char=chars["tr"], **border_attrs),
        )

        # Line 1: Separator line between tabs and content
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y + 1, Cell(char=chars["v"], **border_attrs)
        )
        for x in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + 1,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + 1,
            Cell(char=chars["v"], **border_attrs),
        )

        # Line 2 onwards: Content area
        # Render active tab's content (Frame or FrameNode with children)
        if 0 <= self.active_tab_index < len(self.tabs):
            _, active_content = self.tabs[self.active_tab_index]

            # Use helper to render content (handles both Frame and FrameNode)
            self._render_tab_content(
                ctx,
                active_content,
                ctx.bounds.x + 1,
                ctx.bounds.y + 2,
                content_width - 2,
                content_height - 1,
            )

        # Render left and right borders for content area
        for y in range(2, self.height - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["v"], **border_attrs)
            )
            ctx.buffer.set_cell(
                ctx.bounds.x + self.width - 1,
                ctx.bounds.y + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Bottom border
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + self.height - 1,
            Cell(char=chars["bl"], **border_attrs),
        )
        for x in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + self.height - 1,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + self.height - 1,
            Cell(char=chars["br"], **border_attrs),
        )

    def _render_bottom_tabs(
        self,
        ctx: PaintContext,
        chars: dict,
        border_attrs: dict,
        tab_attrs: dict,
        active_tab_attrs: dict,
        tab_area_height: int,
        content_width: int,
        content_height: int,
    ) -> None:
        """Render tabs at bottom position.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        tab_attrs : dict
            Tab cell attributes
        active_tab_attrs : dict
            Active tab cell attributes
        tab_area_height : int
            Height of tab area
        content_width : int
            Width of content area
        content_height : int
            Height of content area
        """
        from wijjit.terminal.cell import Cell

        # Top border
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
        )
        for x in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x, ctx.bounds.y, Cell(char=chars["h"], **border_attrs)
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y,
            Cell(char=chars["tr"], **border_attrs),
        )

        # Content area borders
        for y in range(1, content_height):
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["v"], **border_attrs)
            )
            ctx.buffer.set_cell(
                ctx.bounds.x + self.width - 1,
                ctx.bounds.y + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Render active tab's content using helper (handles FrameNode and state)
        if 0 <= self.active_tab_index < len(self.tabs):
            _, active_content = self.tabs[self.active_tab_index]

            self._render_tab_content(
                ctx,
                active_content,
                ctx.bounds.x + 1,
                ctx.bounds.y + 1,
                content_width - 2,
                content_height - 1,
            )

        # Separator line between content and tabs
        separator_y = content_height
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + separator_y,
            Cell(char=chars["v"], **border_attrs),
        )
        for x in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + separator_y,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + separator_y,
            Cell(char=chars["v"], **border_attrs),
        )

        # Bottom border with tab labels
        tab_y = content_height + 1
        current_x = 0

        # Bottom-left corner
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + tab_y,
            Cell(char=chars["bl"], **border_attrs),
        )
        current_x += 1

        # Render each tab label
        for i, (label, _) in enumerate(self.tabs):
            is_active = i == self.active_tab_index
            label_attrs = active_tab_attrs if is_active else tab_attrs

            # Tab format: [Label] for active, " Label " for inactive
            if is_active:
                tab_text = f"[{label}]"
            else:
                tab_text = f" {label} "

            for char in tab_text:
                if current_x < self.width - 1:
                    ctx.buffer.set_cell(
                        ctx.bounds.x + current_x,
                        ctx.bounds.y + tab_y,
                        Cell(char=char, **label_attrs),
                    )
                    current_x += 1

            # Separator between tabs
            if i < len(self.tabs) - 1 and current_x < self.width - 1:
                ctx.buffer.set_cell(
                    ctx.bounds.x + current_x,
                    ctx.bounds.y + tab_y,
                    Cell(char=chars["h"], **border_attrs),
                )
                current_x += 1

        # Fill remaining bottom border
        while current_x < self.width - 1:
            ctx.buffer.set_cell(
                ctx.bounds.x + current_x,
                ctx.bounds.y + tab_y,
                Cell(char=chars["h"], **border_attrs),
            )
            current_x += 1

        # Bottom-right corner
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + tab_y,
            Cell(char=chars["br"], **border_attrs),
        )

    def _render_left_tabs(
        self,
        ctx: PaintContext,
        chars: dict,
        border_attrs: dict,
        tab_attrs: dict,
        active_tab_attrs: dict,
        tab_area_width: int,
        content_width: int,
        content_height: int,
    ) -> None:
        """Render tabs at left position.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        tab_attrs : dict
            Tab cell attributes
        active_tab_attrs : dict
            Active tab cell attributes
        tab_area_width : int
            Width of tab area
        content_width : int
            Width of content area
        content_height : int
            Height of content area
        """
        from wijjit.terminal.cell import Cell

        # Render tab area on the left
        # Top-left corner
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
        )

        # Top border of tab area
        for x in range(1, tab_area_width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x, ctx.bounds.y, Cell(char=chars["h"], **border_attrs)
            )

        # Tab area separator
        ctx.buffer.set_cell(
            ctx.bounds.x + tab_area_width - 1,
            ctx.bounds.y,
            Cell(char=chars["h"], **border_attrs),
        )

        # Top border of content area
        for x in range(tab_area_width, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x, ctx.bounds.y, Cell(char=chars["h"], **border_attrs)
            )

        # Top-right corner
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y,
            Cell(char=chars["tr"], **border_attrs),
        )

        # Render tab labels vertically
        for i, (label, _) in enumerate(self.tabs):
            if i + 1 >= self.height - 1:
                break  # No more space

            y = i + 1
            is_active = i == self.active_tab_index
            label_attrs = active_tab_attrs if is_active else tab_attrs

            # Left border
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["v"], **border_attrs)
            )

            # Tab label with visual indicator: [Label] for active, " Label " for inactive
            if is_active:
                tab_text = f"[{label}]"
            else:
                tab_text = f" {label} "
            tab_text = tab_text[: tab_area_width - 2]  # Clip if too long
            tab_text = tab_text.ljust(tab_area_width - 2)

            for j, char in enumerate(tab_text):
                ctx.buffer.set_cell(
                    ctx.bounds.x + 1 + j,
                    ctx.bounds.y + y,
                    Cell(char=char, **label_attrs),
                )

            # Vertical separator
            ctx.buffer.set_cell(
                ctx.bounds.x + tab_area_width - 1,
                ctx.bounds.y + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Fill remaining tab area with empty lines
        for y in range(len(self.tabs) + 1, self.height - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["v"], **border_attrs)
            )
            for x in range(1, tab_area_width - 1):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x, ctx.bounds.y + y, Cell(char=" ", **border_attrs)
                )
            ctx.buffer.set_cell(
                ctx.bounds.x + tab_area_width - 1,
                ctx.bounds.y + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Render content area borders
        for y in range(1, self.height - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + self.width - 1,
                ctx.bounds.y + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Render active tab's content using helper (handles FrameNode and state)
        if 0 <= self.active_tab_index < len(self.tabs):
            _, active_content = self.tabs[self.active_tab_index]

            self._render_tab_content(
                ctx,
                active_content,
                ctx.bounds.x + tab_area_width,
                ctx.bounds.y + 1,
                content_width - 1,
                content_height - 2,
            )

        # Bottom border
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + self.height - 1,
            Cell(char=chars["bl"], **border_attrs),
        )
        for x in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + self.height - 1,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + self.height - 1,
            Cell(char=chars["br"], **border_attrs),
        )

    def _render_right_tabs(
        self,
        ctx: PaintContext,
        chars: dict,
        border_attrs: dict,
        tab_attrs: dict,
        active_tab_attrs: dict,
        tab_area_width: int,
        content_width: int,
        content_height: int,
    ) -> None:
        """Render tabs at right position.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        chars : dict
            Border characters
        border_attrs : dict
            Border cell attributes
        tab_attrs : dict
            Tab cell attributes
        active_tab_attrs : dict
            Active tab cell attributes
        tab_area_width : int
            Width of tab area
        content_width : int
            Width of content area
        content_height : int
            Height of content area
        """
        from wijjit.terminal.cell import Cell

        # Top border
        ctx.buffer.set_cell(
            ctx.bounds.x, ctx.bounds.y, Cell(char=chars["tl"], **border_attrs)
        )
        for x in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x, ctx.bounds.y, Cell(char=chars["h"], **border_attrs)
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y,
            Cell(char=chars["tr"], **border_attrs),
        )

        # Render content area border and tab area separator
        for y in range(1, self.height - 1):
            # Left border
            ctx.buffer.set_cell(
                ctx.bounds.x, ctx.bounds.y + y, Cell(char=chars["v"], **border_attrs)
            )

            # Separator between content and tabs
            ctx.buffer.set_cell(
                ctx.bounds.x + content_width,
                ctx.bounds.y + y,
                Cell(char=chars["v"], **border_attrs),
            )

            # Right border
            ctx.buffer.set_cell(
                ctx.bounds.x + self.width - 1,
                ctx.bounds.y + y,
                Cell(char=chars["v"], **border_attrs),
            )

        # Render active tab's content using helper (handles FrameNode and state)
        if 0 <= self.active_tab_index < len(self.tabs):
            _, active_content = self.tabs[self.active_tab_index]

            self._render_tab_content(
                ctx,
                active_content,
                ctx.bounds.x + 1,
                ctx.bounds.y + 1,
                content_width - 1,
                content_height - 2,
            )

        # Render tab labels vertically on the right
        for i, (label, _) in enumerate(self.tabs):
            if i + 1 >= self.height - 1:
                break  # No more space

            y = i + 1
            is_active = i == self.active_tab_index
            label_attrs = active_tab_attrs if is_active else tab_attrs

            # Tab label with visual indicator: [Label] for active, " Label " for inactive
            if is_active:
                tab_text = f"[{label}]"
            else:
                tab_text = f" {label} "
            tab_text = tab_text[: tab_area_width - 1]  # Clip if too long
            tab_text = tab_text.ljust(tab_area_width - 1)

            for j, char in enumerate(tab_text):
                ctx.buffer.set_cell(
                    ctx.bounds.x + content_width + 1 + j,
                    ctx.bounds.y + y,
                    Cell(char=char, **label_attrs),
                )

        # Fill remaining tab area with empty lines
        for y in range(len(self.tabs) + 1, self.height - 1):
            for x in range(content_width + 1, self.width - 1):
                ctx.buffer.set_cell(
                    ctx.bounds.x + x, ctx.bounds.y + y, Cell(char=" ", **border_attrs)
                )

        # Bottom border
        ctx.buffer.set_cell(
            ctx.bounds.x,
            ctx.bounds.y + self.height - 1,
            Cell(char=chars["bl"], **border_attrs),
        )
        for x in range(1, self.width - 1):
            ctx.buffer.set_cell(
                ctx.bounds.x + x,
                ctx.bounds.y + self.height - 1,
                Cell(char=chars["h"], **border_attrs),
            )
        ctx.buffer.set_cell(
            ctx.bounds.x + self.width - 1,
            ctx.bounds.y + self.height - 1,
            Cell(char=chars["br"], **border_attrs),
        )

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the tabbed panel.

        Returns
        -------
        tuple of int
            (width, height) in characters/lines

        Notes
        -----
        Returns the configured width and height of the panel.
        """
        return (self.width, self.height)
