"""Pager element for linear pagination through multiple pages.

This module provides a Pager element that displays one page at a time
with navigation buttons and keyboard bindings for moving between pages.
Similar to a tabbed panel but with linear prev/next navigation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Union

from wijjit.elements.base import (
    Container,
    ElementType,
    delegate_frame_scroll,
    invoke_callback,
)
from wijjit.layout.frames import BORDER_CHARS, BorderStyle, Frame, FrameStyle
from wijjit.logging_config import get_logger
from wijjit.terminal.ansi import clip_to_width
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.layout.engine import FrameNode
    from wijjit.rendering.paint_context import PaintContext


logger = get_logger(__name__)

# Type alias for page content
PageContent = Union["Frame", "FrameNode", str]


@dataclass
class Page:
    """Represents a single page in the Pager.

    Parameters
    ----------
    title : str
        Page title displayed in the indicator
    content : PageContent
        Page content - can be Frame, FrameNode, or string content

    Attributes
    ----------
    title : str
        Page title
    content : PageContent
        Page content
    """

    title: str = ""
    content: PageContent = ""


class Pager(Container):
    """Pager element for linear pagination through multiple pages.

    This element provides prev/next navigation for switching between pages.
    Each page is wrapped in an implicit Frame and can contain any content.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str or set of str, optional
        CSS class names for styling
    width : int, optional
        Total pager width (default: 60)
    height : int, optional
        Total pager height (default: 20)
    border_style : str, optional
        Border style: "single", "double", "rounded", "none" (default: "single")
    nav_position : str, optional
        Navigation position: "top", "bottom", "both" (default: "bottom")
    show_indicator : bool, optional
        Show "Page X of Y" indicator (default: True)
    show_titles : bool, optional
        Show page title in indicator (default: False)
    loop : bool, optional
        Wrap from last to first page (default: False)
    current_page : int, optional
        Initially active page index (default: 0)

    Attributes
    ----------
    pages : list of Page
        List of pages
    current_page : int
        Index of currently displayed page (0-based)
    width : int
        Total pager width
    height : int
        Total pager height
    border_style : BorderStyle
        Border style for pager
    nav_position : str
        Navigation bar position
    show_indicator : bool
        Whether to show page indicator
    show_titles : bool
        Whether to show page title
    loop : bool
        Whether to loop at ends
    on_page_change : Callable or None
        Callback when page changes: on_page_change(old_index, new_index)

    Notes
    -----
    Navigation:
    - Left/PgUp: Previous page
    - Right/PgDown: Next page
    - Home: First page
    - End: Last page
    - Mouse click on Prev/Next buttons
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        tab_index: int | None = None,
        width: int = 60,
        height: int = 20,
        border_style: str = "single",
        nav_position: str = "bottom",
        show_indicator: bool = True,
        show_titles: bool = False,
        loop: bool = False,
        current_page: int = 0,
    ) -> None:
        super().__init__(id=id, classes=classes, tab_index=tab_index)
        self.element_type = ElementType.DISPLAY
        self.focusable = True

        # Page storage
        self.pages: list[Page] = []
        self.current_page = current_page

        # Display properties
        self.width = width
        self.height = height

        # Parse border style
        border_map = {
            "single": BorderStyle.SINGLE,
            "double": BorderStyle.DOUBLE,
            "rounded": BorderStyle.ROUNDED,
            "none": BorderStyle.NONE,
        }
        self.border_style = border_map.get(border_style, BorderStyle.SINGLE)

        # Navigation settings
        self.nav_position = nav_position
        self.show_indicator = show_indicator
        self.show_titles = show_titles
        self.loop = loop

        # Callbacks
        self.on_page_change: Callable[[int, int], None] | None = None

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

        # State persistence
        self._page_state_key_override: str | None = None
        self._state_dict: dict[str, Any] | None = None

        # Internal: track button positions for mouse handling
        self._prev_button_bounds: tuple[int, int, int, int] | None = None
        self._next_button_bounds: tuple[int, int, int, int] | None = None

        # Frame cache for text-only pages (enables scrolling)
        self._frame_cache: dict[int, Frame] = {}

    @property
    def page_state_key(self) -> str | None:
        """Get the state key for current page index.

        Returns the explicitly set key if provided, otherwise auto-generates
        from the element id using the convention "{id}:page".

        Returns
        -------
        str or None
            State key for current page, or None if no id
        """
        if self._page_state_key_override is not None:
            return self._page_state_key_override
        return self._state_key("page")

    @page_state_key.setter
    def page_state_key(self, value: str | None) -> None:
        """Set an explicit page state key."""
        self._page_state_key_override = value

    @property
    def page_count(self) -> int:
        """Get the total number of pages.

        Returns
        -------
        int
            Number of pages
        """
        return len(self.pages)

    def add_page(
        self, page: Page | None = None, title: str = "", content: PageContent = ""
    ) -> None:
        """Add a page to the pager.

        Parameters
        ----------
        page : Page, optional
            Page object to add. If None, creates from title/content.
        title : str, optional
            Page title (used if page is None)
        content : PageContent, optional
            Page content (used if page is None)
        """
        if page is None:
            page = Page(title=title, content=content)
        self.pages.append(page)

    def remove_page(self, index: int) -> Page | None:
        """Remove a page by index.

        Parameters
        ----------
        index : int
            Index of page to remove

        Returns
        -------
        Page or None
            Removed page, or None if index invalid
        """
        if 0 <= index < len(self.pages):
            page = self.pages.pop(index)
            # Clear frame cache for removed page and rebuild indices
            new_cache: dict[int, Frame] = {}
            for cached_idx, cached_frame in self._frame_cache.items():
                if cached_idx < index:
                    new_cache[cached_idx] = cached_frame
                elif cached_idx > index:
                    new_cache[cached_idx - 1] = cached_frame
            self._frame_cache = new_cache
            # Adjust current page if needed
            if self.current_page >= len(self.pages) and self.pages:
                self.current_page = len(self.pages) - 1
            elif not self.pages:
                self.current_page = 0
            return page
        return None

    def clear_pages(self) -> None:
        """Remove all pages."""
        self.pages.clear()
        self._frame_cache.clear()
        self.current_page = 0

    def go_to_page(self, index: int) -> bool:
        """Navigate to a specific page.

        Parameters
        ----------
        index : int
            Page index to navigate to

        Returns
        -------
        bool
            True if page changed, False otherwise
        """
        if not self.pages:
            return False

        old_index = self.current_page

        # Handle looping
        if self.loop:
            index = index % len(self.pages)
        else:
            index = max(0, min(index, len(self.pages) - 1))

        if old_index == index:
            return False

        self.current_page = index
        self._save_page_state()

        if self.on_page_change:
            invoke_callback(self.on_page_change, old_index, index)

        return True

    def next_page(self) -> bool:
        """Navigate to the next page.

        Returns
        -------
        bool
            True if page changed, False otherwise
        """
        return self.go_to_page(self.current_page + 1)

    def prev_page(self) -> bool:
        """Navigate to the previous page.

        Returns
        -------
        bool
            True if page changed, False otherwise
        """
        return self.go_to_page(self.current_page - 1)

    def first_page(self) -> bool:
        """Navigate to the first page.

        Returns
        -------
        bool
            True if page changed, False otherwise
        """
        return self.go_to_page(0)

    def last_page(self) -> bool:
        """Navigate to the last page.

        Returns
        -------
        bool
            True if page changed, False otherwise
        """
        return self.go_to_page(len(self.pages) - 1)

    def _save_page_state(self) -> None:
        """Save current page index to app state if available."""
        if self._state_dict is not None and self.page_state_key:
            self._state_dict[self.page_state_key] = self.current_page

    def _wire_frame_scroll_state(self, frame: Frame) -> None:
        """Wire up scroll state persistence for a frame.

        This method sets up the on_scroll callback to save scroll position
        to state, and restores the scroll position from state if available.

        Parameters
        ----------
        frame : Frame
            The frame to wire up scroll state for
        """
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

    def _get_active_frame(self) -> Frame | None:
        """Get the Frame for the current page's content.

        Returns
        -------
        Frame or None
            The active page's Frame, or None if not available
        """
        if not self.pages or not (0 <= self.current_page < len(self.pages)):
            return None

        page = self.pages[self.current_page]
        content = page.content

        # Check different content types
        if isinstance(content, Frame):
            return content

        # Check if it's a FrameNode
        from wijjit.layout.engine import FrameNode

        if isinstance(content, FrameNode):
            return content.frame

        # Check frame cache for text-only pages
        if isinstance(content, str) and self.current_page in self._frame_cache:
            return self._frame_cache[self.current_page]

        return None

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input for page navigation and content scrolling.

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
        Page navigation keys:
        - Left/Right: Previous/Next page
        - PgUp/PgDown: Previous/Next page
        - Home/End: First/Last page

        Content scrolling keys (delegated to active frame):
        - Up/Down: Scroll content line by line
        """
        logger.debug(f"Pager.handle_key called with key={key}, pages={len(self.pages)}")

        if not self.pages:
            return False

        # Handle page-switching keys
        if key == Keys.LEFT or key == Keys.PAGE_UP:
            return self.prev_page()

        if key == Keys.RIGHT or key == Keys.PAGE_DOWN:
            return self.next_page()

        if key == Keys.HOME:
            return self.first_page()

        if key == Keys.END:
            return self.last_page()

        # Delegate Up/Down to the active frame for line-by-line scrolling
        if key in (Keys.UP, Keys.DOWN):
            if 0 <= self.current_page < len(self.pages):
                frame = self._get_active_frame()
                logger.debug(
                    f"Pager scroll delegation: frame={frame}, "
                    f"cache_keys={list(self._frame_cache.keys())}"
                )
                if frame is not None and hasattr(frame, "handle_key"):
                    result = frame.handle_key(key)
                    logger.debug(f"Frame.handle_key returned: {result}")
                    return result

        return False

    async def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input for button clicks and scroll wheel.

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
        - Left clicks on Prev/Next buttons
        - Scroll wheel events delegated to active frame
        """
        if not self.bounds or not self.pages:
            return False

        # Handle scroll wheel - delegate to active frame
        if event.type == MouseEventType.SCROLL:
            frame = self._get_active_frame()
            direction = 1 if event.button == MouseButton.SCROLL_DOWN else -1
            return delegate_frame_scroll(frame, direction)

        # Only handle CLICK events for buttons (not PRESS to avoid double-fire)
        if event.button != MouseButton.LEFT:
            return False
        if event.type != MouseEventType.CLICK:
            return False

        # Check Prev button
        if self._prev_button_bounds:
            bx, by, bw, bh = self._prev_button_bounds
            if bx <= event.x < bx + bw and by <= event.y < by + bh:
                self.prev_page()
                return True

        # Check Next button
        if self._next_button_bounds:
            bx, by, bw, bh = self._next_button_bounds
            if bx <= event.x < bx + bw and by <= event.y < by + bh:
                self.next_page()
                return True

        return False

    def get_ephemeral_state(self) -> dict:
        """Get ephemeral state for reconciliation.

        Returns
        -------
        dict
            Current page index that should survive re-renders.
        """
        return {"current_page": self.current_page}

    def restore_ephemeral_state(self, state: dict) -> None:
        """Restore ephemeral state after reconciliation.

        Parameters
        ----------
        state : dict
            State dict from get_ephemeral_state()
        """
        if "current_page" in state:
            self.go_to_page(state["current_page"])

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the pager.

        Returns
        -------
        tuple of int
            (width, height) in characters/lines
        """
        return (self.width, self.height)

    def _get_nav_height(self) -> int:
        """Get height of navigation bar(s).

        Returns
        -------
        int
            Total height used by navigation bars
        """
        if self.nav_position == "both":
            return 2
        return 1

    def _get_content_bounds(self) -> tuple[int, int, int, int]:
        """Calculate content area bounds.

        Returns
        -------
        tuple
            (x, y, width, height) for content area
        """
        # Account for border
        has_border = self.border_style != BorderStyle.NONE
        border_offset = 1 if has_border else 0

        content_x = border_offset
        content_width = self.width - (2 * border_offset)

        # Account for navigation bar(s)
        nav_height = self._get_nav_height()

        if self.nav_position == "top":
            content_y = border_offset + nav_height
            content_height = self.height - (2 * border_offset) - nav_height
        elif self.nav_position == "bottom":
            content_y = border_offset
            content_height = self.height - (2 * border_offset) - nav_height
        else:  # both
            content_y = border_offset + 1
            content_height = self.height - (2 * border_offset) - nav_height

        return content_x, content_y, content_width, max(1, content_height)

    def render_to(self, ctx: PaintContext) -> None:
        """Render pager using cell-based rendering.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        Renders the pager with:
        1. Border (if enabled)
        2. Navigation bar(s) with Prev/Next buttons and page indicator
        3. Current page content in a Frame

        Theme styles:

        This element uses the following theme style classes:
        - ``pager``: Base pager style
        - ``pager:focus``: When pager has focus
        - ``pager.border``: Border style
        - ``pager.nav``: Navigation bar style
        - ``pager.button``: Navigation button style
        - ``pager.button:disabled``: Disabled button style
        - ``pager.indicator``: Page indicator style
        """

        # Capture bounds for mouse hit testing
        self.bounds = ctx.bounds

        # Resolve styles - use standard button styles for nav buttons
        if self.focused:
            border_style = ctx.style_resolver.resolve_style(self, "frame.border:focus")
        else:
            border_style = ctx.style_resolver.resolve_style(self, "frame.border")

        nav_style = ctx.style_resolver.resolve_style_by_class("frame")
        # Use standard button styles so nav buttons look like other buttons
        button_style = ctx.style_resolver.resolve_style_by_class("button")
        button_disabled_style = ctx.style_resolver.resolve_style_by_class("text.muted")
        indicator_style = ctx.style_resolver.resolve_style_by_class("text")

        # Get border characters
        if self.border_style != BorderStyle.NONE:
            chars = BORDER_CHARS[self.border_style]
            # note: this unused?
            # border_attrs = border_style.to_cell_attrs()

            # Draw border
            ctx.draw_border(0, 0, self.width, self.height, border_style, chars)

        # Clear button bounds
        self._prev_button_bounds = None
        self._next_button_bounds = None

        # Render navigation bar(s)
        if self.nav_position in ("top", "both"):
            self._render_nav_bar(
                ctx,
                nav_y=1 if self.border_style != BorderStyle.NONE else 0,
                nav_style=nav_style,
                button_style=button_style,
                button_disabled_style=button_disabled_style,
                indicator_style=indicator_style,
            )

        if self.nav_position in ("bottom", "both"):
            nav_y = (
                self.height - 2
                if self.border_style != BorderStyle.NONE
                else self.height - 1
            )
            self._render_nav_bar(
                ctx,
                nav_y=nav_y,
                nav_style=nav_style,
                button_style=button_style,
                button_disabled_style=button_disabled_style,
                indicator_style=indicator_style,
            )

        # Render current page content
        if self.pages and 0 <= self.current_page < len(self.pages):
            cx, cy, cw, ch = self._get_content_bounds()

            # Create sub-context for content
            content_ctx = ctx.sub_context(cx, cy, cw, ch)

            # Get current page
            page = self.pages[self.current_page]
            self._render_page_content(content_ctx, page, cw, ch)

    def _render_nav_bar(
        self,
        ctx: PaintContext,
        nav_y: int,
        nav_style: Any,
        button_style: Any,
        button_disabled_style: Any,
        indicator_style: Any,
    ) -> None:
        """Render the navigation bar.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        nav_y : int
            Y position for navigation bar
        nav_style : Style
            Navigation bar style
        button_style : Style
            Button style
        button_disabled_style : Style
            Disabled button style
        indicator_style : Style
            Page indicator style
        """
        has_border = self.border_style != BorderStyle.NONE
        content_start = 1 if has_border else 0
        content_width = self.width - (2 if has_border else 0)

        # Import Cell here to avoid repeated __import__
        from wijjit.terminal.cell import Cell

        # Fill nav bar background
        nav_attrs = nav_style.to_cell_attrs()
        for x in range(content_width):
            ctx.buffer.set_cell(
                ctx.bounds.x + content_start + x,
                ctx.bounds.y + nav_y,
                Cell(char=" ", **nav_attrs),
            )

        # Determine button states
        can_prev = self.loop or self.current_page > 0
        can_next = self.loop or self.current_page < len(self.pages) - 1

        # Prev button - use bracket style like regular buttons
        prev_text = "< Prev >" if can_prev else "  Prev  "
        prev_style = button_style if can_prev else button_disabled_style
        prev_attrs = prev_style.to_cell_attrs()

        prev_x = content_start + 1
        for i, char in enumerate(prev_text):
            ctx.buffer.set_cell(
                ctx.bounds.x + prev_x + i,
                ctx.bounds.y + nav_y,
                Cell(char=char, **prev_attrs),
            )

        # Store button bounds for mouse handling
        self._prev_button_bounds = (
            ctx.bounds.x + prev_x,
            ctx.bounds.y + nav_y,
            len(prev_text),
            1,
        )

        # Next button - use bracket style like regular buttons
        next_text = "< Next >" if can_next else "  Next  "
        next_style = button_style if can_next else button_disabled_style
        next_attrs = next_style.to_cell_attrs()

        next_x = content_start + content_width - len(next_text) - 1
        for i, char in enumerate(next_text):
            ctx.buffer.set_cell(
                ctx.bounds.x + next_x + i,
                ctx.bounds.y + nav_y,
                Cell(char=char, **next_attrs),
            )

        # Store button bounds
        self._next_button_bounds = (
            ctx.bounds.x + next_x,
            ctx.bounds.y + nav_y,
            len(next_text),
            1,
        )

        # Page indicator (centered)
        if self.show_indicator and self.pages:
            if self.show_titles and self.pages[self.current_page].title:
                indicator_text = (
                    f"{self.pages[self.current_page].title} "
                    f"({self.current_page + 1}/{len(self.pages)})"
                )
            else:
                indicator_text = f"Page {self.current_page + 1} of {len(self.pages)}"

            # Calculate centered position
            indicator_x = content_start + (content_width - len(indicator_text)) // 2
            indicator_attrs = indicator_style.to_cell_attrs()

            for i, char in enumerate(indicator_text):
                if content_start + len(prev_text) + 2 <= indicator_x + i < next_x - 1:
                    ctx.buffer.set_cell(
                        ctx.bounds.x + indicator_x + i,
                        ctx.bounds.y + nav_y,
                        Cell(char=char, **indicator_attrs),
                    )

    def collect_focusable_children(self) -> list:
        """Collect focusable elements from the active page's content.

        Returns
        -------
        list
            List of focusable elements in the active page
        """
        from wijjit.layout.engine import FrameNode

        if not self.pages or not (0 <= self.current_page < len(self.pages)):
            return []

        page = self.pages[self.current_page]
        content = page.content

        if isinstance(content, FrameNode):
            if hasattr(content, "content_container") and content.content_container:
                focusable: list[Any] = []
                self._collect_focusable(content.content_container.children, focusable)
                return focusable

        return []

    def _collect_focusable(self, children: list, result: list) -> None:
        """Recursively collect focusable elements from children.

        Parameters
        ----------
        children : list
            List of layout nodes to search
        result : list
            List to append focusable elements to
        """
        from wijjit.layout.engine import ElementNode

        for node in children:
            if isinstance(node, ElementNode):
                element = node.element
                if hasattr(element, "focusable") and element.focusable:
                    result.append(element)
            if hasattr(node, "children"):
                self._collect_focusable(node.children, result)
            if hasattr(node, "content_container") and hasattr(
                node.content_container, "children"
            ):
                self._collect_focusable(node.content_container.children, result)

    def collect_child_elements(self) -> list:
        """Collect all child elements from the active page's content.

        Returns
        -------
        list
            List of all elements in the active page
        """
        from wijjit.layout.engine import FrameNode

        if not self.pages or not (0 <= self.current_page < len(self.pages)):
            return []

        page = self.pages[self.current_page]
        content = page.content

        elements: list[Any] = []
        if isinstance(content, FrameNode):
            if hasattr(content, "content_container") and content.content_container:
                self._collect_all_elements(content.content_container.children, elements)

        return elements

    def _collect_all_elements(self, children: list, result: list) -> None:
        """Recursively collect all elements from children.

        Parameters
        ----------
        children : list
            List of layout nodes to search
        result : list
            List to append elements to
        """
        from wijjit.layout.engine import ElementNode

        for node in children:
            if isinstance(node, ElementNode):
                result.append(node.element)
            if hasattr(node, "children"):
                self._collect_all_elements(node.children, result)
            if hasattr(node, "content_container") and hasattr(
                node.content_container, "children"
            ):
                self._collect_all_elements(node.content_container.children, result)

    def _calculate_children_height(self, children: list) -> int:
        """Calculate total height of layout children.

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

    def _render_page_content(
        self,
        ctx: PaintContext,
        page: Page,
        width: int,
        height: int,
    ) -> None:
        """Render a page's content.

        Parameters
        ----------
        ctx : PaintContext
            Paint context for content area
        page : Page
            Page to render
        width : int
            Content area width
        height : int
            Content area height
        """
        from wijjit.layout.bounds import Bounds
        from wijjit.layout.engine import FrameNode

        content = page.content

        # Handle different content types
        if isinstance(content, str):
            # String content - get or create cached frame
            if self.current_page not in self._frame_cache:
                # Create frame on first render
                logger.debug(
                    f"Creating frame for page {self.current_page}, "
                    f"content_len={len(content)}, size=({width}x{height})"
                )
                # Set up scroll state key for this page
                scroll_state_key = (
                    f"_scroll_{self.id}_page_{self.current_page}" if self.id else None
                )
                frame = Frame(
                    width=width,
                    height=height,
                    style=FrameStyle(
                        border_style=BorderStyle.SINGLE,
                        title=page.title if page.title else None,
                        padding=(0, 1, 0, 1),
                        scrollable=True,
                        show_scrollbar=True,
                    ),
                )
                frame.scroll_state_key = scroll_state_key
                frame.set_content(content)
                self._frame_cache[self.current_page] = frame
                logger.debug(
                    f"Frame cached for page {self.current_page}, "
                    f"scroll_manager={frame.scroll_manager is not None}, "
                    f"scrollable={frame.style.scrollable}"
                )
            else:
                # Reuse cached frame to preserve scroll state
                frame = self._frame_cache[self.current_page]
                # Update dimensions in case they changed
                frame.width = width
                frame.height = height
                logger.debug(f"Reusing cached frame for page {self.current_page}")

            frame.bounds = Bounds(
                x=ctx.bounds.x, y=ctx.bounds.y, width=width, height=height
            )

            # Update scroll manager viewport for current size
            if hasattr(frame, "update_viewport_for_current_size"):
                frame.update_viewport_for_current_size()

            # Wire up scroll state persistence
            self._wire_frame_scroll_state(frame)

            frame.render_to(ctx)

        elif isinstance(content, FrameNode):
            # FrameNode - render the frame and its children
            frame = content.frame
            frame.width = width
            frame.height = height
            frame.bounds = Bounds(
                x=ctx.bounds.x, y=ctx.bounds.y, width=width, height=height
            )

            # Update scroll manager viewport
            if hasattr(frame, "update_viewport_for_current_size"):
                frame.update_viewport_for_current_size()

            # Wire up scroll state persistence for this frame
            self._wire_frame_scroll_state(frame)

            # Calculate content height for scrolling
            if (
                hasattr(content, "content_container")
                and content.content_container
                and content.content_container.children
                and not frame.content
            ):
                total_height = self._calculate_children_height(
                    content.content_container.children
                )
                frame.set_child_content_height(total_height)

            # Create sub-context for frame
            frame.render_to(ctx)

            # Render children if frame doesn't have text content
            if (
                hasattr(content, "content_container")
                and content.content_container
                and content.content_container.children
                and not frame.content
            ):
                content_x = ctx.bounds.x + 1  # +1 for frame border
                content_y = ctx.bounds.y + 1  # +1 for frame border
                content_width = width - 2  # -2 for borders
                content_height = height - 2  # -2 for borders

                # Compute size constraints bottom-up before assigning bounds.
                # Without this, every child's `.constraints` is None and
                # assign_bounds defaults each to height 1, collapsing multi-line
                # text and nested containers so siblings overlap.
                content.content_container.calculate_constraints()

                # Assign bounds to content_container to compute proper layout
                # This is essential for HStack children to have correct x positions
                content.content_container.assign_bounds(
                    content_x, content_y, content_width, content_height
                )

                scroll_offset = (
                    frame.get_scroll_offset()
                    if hasattr(frame, "get_scroll_offset")
                    else 0
                )

                self._render_children(
                    ctx,
                    content.content_container.children,
                    content_x,
                    content_y,
                    content_width,
                    content_height,
                    scroll_offset,
                )

        elif isinstance(content, Frame):
            # Frame object - render directly
            content.width = width
            content.height = height
            content.bounds = Bounds(
                x=ctx.bounds.x, y=ctx.bounds.y, width=width, height=height
            )
            content.render_to(ctx)

        else:
            # Unknown content type - show placeholder
            text_style = ctx.style_resolver.resolve_style_by_class("text")
            ctx.write_text(0, 0, "[Empty page]", text_style)

    def _render_children(
        self,
        ctx: PaintContext,
        children: list,
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
                    if current_y >= start_y - 1:
                        text = element.text if hasattr(element, "text") else ""
                        lines = text.split("\n") if text else []
                        for line in lines:
                            if start_y <= current_y < start_y + available_height:
                                text_style = ctx.style_resolver.resolve_style_by_class(
                                    "text"
                                )
                                clipped_line = clip_to_width(line, available_width)
                                rel_x = start_x - ctx.bounds.x
                                rel_y = current_y - ctx.bounds.y
                                ctx.write_text(rel_x, rel_y, clipped_line, text_style)
                            current_y += 1
                else:
                    # Render other elements (buttons, inputs, etc.)
                    if hasattr(element, "get_intrinsic_size"):
                        elem_width, element_height = element.get_intrinsic_size()
                    else:
                        elem_width = available_width
                        element_height = 1

                    # Use pre-computed bounds if available (from assign_bounds),
                    # otherwise set bounds based on vertical stacking position.
                    # This is important for HStack children which have horizontal
                    # positions computed by the layout engine.
                    if element.bounds is not None:
                        # Use layout-computed bounds, but adjust y for scroll
                        elem_x = element.bounds.x
                        elem_y = element.bounds.y - scroll_offset
                        elem_width = element.bounds.width
                        element_height = element.bounds.height
                    else:
                        # Fallback: compute bounds for vertical stacking
                        elem_x = start_x
                        elem_y = current_y
                        element.bounds = Bounds(
                            x=elem_x,
                            y=elem_y,
                            width=available_width,
                            height=element_height,
                        )

                    # Only render if visible
                    if (
                        elem_y + element_height > start_y
                        and elem_y < start_y + available_height
                    ):
                        rel_x = elem_x - ctx.bounds.x
                        rel_y = elem_y - ctx.bounds.y
                        elem_ctx = ctx.sub_context(
                            rel_x, rel_y, elem_width, element_height
                        )
                        element.render_to(elem_ctx)

                    current_y += element_height

            elif hasattr(child, "children"):
                # Container node - recurse
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
