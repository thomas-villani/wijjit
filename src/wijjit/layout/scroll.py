"""Scroll state management and utilities for scrollable content.

This module provides infrastructure for managing scroll state in scrollable
containers like frames, text areas, and lists. It handles:
- Scroll position tracking and bounds checking
- Viewport calculations
- Scrollbar rendering
- Keyboard and mouse wheel scroll operations
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ScrollState:
    """Represents the scroll state of a scrollable container.

    This class tracks the relationship between content size, viewport size,
    and current scroll position. It provides properties for calculating
    scroll bounds and determining whether scrolling is possible.

    Parameters
    ----------
    content_size : int
        Total size of content (height in lines or width in columns)
    viewport_size : int
        Size of visible viewport (height in lines or width in columns)
    scroll_position : int, optional
        Current scroll offset (0-based, default: 0)

    Attributes
    ----------
    content_size : int
        Total content size
    viewport_size : int
        Viewport size
    scroll_position : int
        Current scroll offset
    """

    content_size: int
    viewport_size: int
    scroll_position: int = 0

    @property
    def max_scroll(self) -> int:
        """Maximum valid scroll position.

        Returns
        -------
        int
            Maximum scroll position (content_size - viewport_size), minimum 0
        """
        return max(0, self.content_size - self.viewport_size)

    @property
    def scroll_percentage(self) -> float:
        """Current scroll position as a percentage.

        Returns
        -------
        float
            Scroll percentage (0.0 to 1.0). Returns 0.0 if content fits in viewport.
        """
        if self.max_scroll == 0:
            return 0.0
        return self.scroll_position / self.max_scroll

    @property
    def can_scroll_up(self) -> bool:
        """Check if scrolling up is possible.

        Returns
        -------
        bool
            True if scroll position > 0
        """
        return self.scroll_position > 0

    @property
    def can_scroll_down(self) -> bool:
        """Check if scrolling down is possible.

        Returns
        -------
        bool
            True if scroll position < max_scroll
        """
        return self.scroll_position < self.max_scroll

    @property
    def is_scrollable(self) -> bool:
        """Check if content exceeds viewport (scrolling needed).

        Returns
        -------
        bool
            True if content_size > viewport_size
        """
        return self.content_size > self.viewport_size

    def __post_init__(self) -> None:
        """Validate and clamp scroll position after initialization."""
        self.scroll_position = max(0, min(self.scroll_position, self.max_scroll))


class ScrollManager:
    """Manages scroll state and operations for a scrollable container.

    This class provides methods for scrolling, handles bounds checking,
    and calculates visible content ranges. It maintains the scroll state
    and ensures all scroll operations are valid.

    Parameters
    ----------
    content_size : int
        Total content size (lines or columns)
    viewport_size : int
        Viewport size (visible lines or columns)
    initial_position : int, optional
        Initial scroll position (default: 0)

    Attributes
    ----------
    state : ScrollState
        Current scroll state
    """

    def __init__(
        self, content_size: int, viewport_size: int, initial_position: int = 0
    ) -> None:
        self.state = ScrollState(
            content_size=content_size,
            viewport_size=viewport_size,
            scroll_position=initial_position,
        )

    def scroll_by(self, delta: int) -> int:
        """Scroll by a relative amount.

        Parameters
        ----------
        delta : int
            Amount to scroll (positive = down/right, negative = up/left)

        Returns
        -------
        int
            New scroll position after clamping
        """
        new_position = self.state.scroll_position + delta
        self.state.scroll_position = max(0, min(new_position, self.state.max_scroll))
        return self.state.scroll_position

    def scroll_to(self, position: int) -> int:
        """Scroll to an absolute position.

        Parameters
        ----------
        position : int
            Target scroll position

        Returns
        -------
        int
            Actual scroll position after clamping
        """
        self.state.scroll_position = max(0, min(position, self.state.max_scroll))
        return self.state.scroll_position

    def scroll_to_top(self) -> int:
        """Scroll to the beginning (position 0).

        Returns
        -------
        int
            New scroll position (always 0)
        """
        return self.scroll_to(0)

    def scroll_to_bottom(self) -> int:
        """Scroll to the end (maximum scroll position).

        Returns
        -------
        int
            New scroll position (max_scroll)
        """
        return self.scroll_to(self.state.max_scroll)

    def page_up(self) -> int:
        """Scroll up by one viewport.

        Returns
        -------
        int
            New scroll position
        """
        return self.scroll_by(-self.state.viewport_size)

    def page_down(self) -> int:
        """Scroll down by one viewport.

        Returns
        -------
        int
            New scroll position
        """
        return self.scroll_by(self.state.viewport_size)

    def update_content_size(self, size: int) -> None:
        """Update content size and adjust scroll position if needed.

        Parameters
        ----------
        size : int
            New content size

        Notes
        -----
        If the new content size results in a smaller max_scroll, the scroll
        position will be clamped to the new maximum.
        """
        self.state.content_size = max(0, size)
        # Clamp scroll position to new bounds
        self.state.scroll_position = min(
            self.state.scroll_position, self.state.max_scroll
        )

    def update_viewport_size(self, size: int) -> None:
        """Update viewport size and adjust scroll position if needed.

        Parameters
        ----------
        size : int
            New viewport size

        Notes
        -----
        If the new viewport size results in a smaller max_scroll, the scroll
        position will be clamped to the new maximum.
        """
        self.state.viewport_size = max(0, size)
        # Clamp scroll position to new bounds
        self.state.scroll_position = min(
            self.state.scroll_position, self.state.max_scroll
        )

    def get_visible_range(self) -> tuple[int, int]:
        """Get the range of visible content indices.

        Returns
        -------
        tuple of int
            (start_index, end_index) where end_index is exclusive.
            For example, (5, 10) means indices 5, 6, 7, 8, 9 are visible.

        Examples
        --------
        >>> manager = ScrollManager(content_size=100, viewport_size=10)
        >>> manager.scroll_to(20)
        20
        >>> manager.get_visible_range()
        (20, 30)
        """
        start = self.state.scroll_position
        end = min(start + self.state.viewport_size, self.state.content_size)
        return (start, end)


def calculate_scrollbar_thumb(
    scroll_state: ScrollState, bar_height: int
) -> tuple[int, int]:
    """Calculate scrollbar thumb position and size.

    Parameters
    ----------
    scroll_state : ScrollState
        Current scroll state
    bar_height : int
        Total height of scrollbar in characters

    Returns
    -------
    tuple of int
        (thumb_start, thumb_size) in characters

    Notes
    -----
    The thumb size is proportional to the viewport/content ratio.
    The thumb position is proportional to the scroll percentage.
    Thumb size is always at least 1 character.

    Examples
    --------
    >>> state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
    >>> calculate_scrollbar_thumb(state, 20)
    (0, 2)  # thumb is 2 chars tall, at position 0
    >>> state.scroll_position = 50
    >>> calculate_scrollbar_thumb(state, 20)
    (10, 2)  # thumb is 2 chars tall, at position 10
    """
    # If content fits in viewport, thumb fills entire bar
    if not scroll_state.is_scrollable:
        return (0, bar_height)

    # Calculate thumb size proportional to viewport/content ratio
    # Minimum size is 1 character
    thumb_size = max(
        1, int((scroll_state.viewport_size / scroll_state.content_size) * bar_height)
    )

    # Calculate thumb position based on scroll percentage
    # Available space for thumb movement
    available_space = bar_height - thumb_size

    if available_space <= 0:
        thumb_start = 0
    else:
        thumb_start = int(scroll_state.scroll_percentage * available_space)

    return (thumb_start, thumb_size)


def render_vertical_scrollbar(
    scroll_state: ScrollState, height: int, style: Literal["simple", "fancy"] = "simple"
) -> list[str]:
    """Render a vertical scrollbar as a list of characters.

    Parameters
    ----------
    scroll_state : ScrollState
        Current scroll state
    height : int
        Height of scrollbar in characters
    style : {"simple", "fancy"}, optional
        Scrollbar style (default: "simple")
        - "simple": uses │ (track) and █ (thumb)
        - "fancy": uses │ (track), █ (thumb), ▲ (top), ▼ (bottom)

    Returns
    -------
    list of str
        List of characters for each line of the scrollbar

    Notes
    -----
    For "simple" style:
    - Track character: │ (U+2502 Box Drawings Light Vertical)
    - Thumb character: █ (U+2588 Full Block)

    For "fancy" style (future enhancement):
    - Top arrow: ▲ (U+25B2 Black Up-Pointing Triangle)
    - Bottom arrow: ▼ (U+25BC Black Down-Pointing Triangle)

    Examples
    --------
    >>> state = ScrollState(content_size=100, viewport_size=10, scroll_position=0)
    >>> bar = render_vertical_scrollbar(state, 5, style="simple")
    >>> print('\\n'.join(bar))
    █
    │
    │
    │
    │
    """
    # Simple style characters
    track_char = "│"
    thumb_char = "█"

    # If content fits, show solid track (no scrolling needed)
    if not scroll_state.is_scrollable:
        return [track_char] * height

    # Calculate thumb position and size
    thumb_start, thumb_size = calculate_scrollbar_thumb(scroll_state, height)

    # Build scrollbar
    scrollbar = []
    for i in range(height):
        if thumb_start <= i < thumb_start + thumb_size:
            scrollbar.append(thumb_char)
        else:
            scrollbar.append(track_char)

    return scrollbar


def render_horizontal_scrollbar(
    scroll_state: ScrollState, width: int, style: Literal["simple", "fancy"] = "simple"
) -> str:
    """Render a horizontal scrollbar as a string.

    Parameters
    ----------
    scroll_state : ScrollState
        Current scroll state
    width : int
        Width of scrollbar in characters
    style : {"simple", "fancy"}, optional
        Scrollbar style (default: "simple")

    Returns
    -------
    str
        String representing the horizontal scrollbar

    Notes
    -----
    For "simple" style:
    - Track character: ─ (U+2500 Box Drawings Light Horizontal)
    - Thumb character: █ (U+2588 Full Block)
    """
    # Simple style characters
    track_char = "─"
    thumb_char = "█"

    # If content fits, show solid track (no scrolling needed)
    if not scroll_state.is_scrollable:
        return track_char * width

    # Calculate thumb position and size
    thumb_start, thumb_size = calculate_scrollbar_thumb(scroll_state, width)

    # Build scrollbar
    scrollbar = []
    for i in range(width):
        if thumb_start <= i < thumb_start + thumb_size:
            scrollbar.append(thumb_char)
        else:
            scrollbar.append(track_char)

    return "".join(scrollbar)
