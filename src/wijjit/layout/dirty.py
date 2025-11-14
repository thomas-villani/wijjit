"""Dirty region tracking for optimized rendering.

This module provides the DirtyRegionManager class which tracks rectangular
regions of the screen that need to be redrawn. It merges overlapping and
adjacent regions to minimize the number of screen updates required.
"""

from dataclasses import dataclass

from wijjit.layout.bounds import Bounds


@dataclass
class DirtyRegion:
    """Represents a rectangular region that needs redrawing.

    Parameters
    ----------
    x : int
        Left edge column position
    y : int
        Top edge row position
    width : int
        Width in columns
    height : int
        Height in rows

    Attributes
    ----------
    x : int
        Left edge column position
    y : int
        Top edge row position
    width : int
        Width in columns
    height : int
        Height in rows
    """

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Right edge column position.

        Returns
        -------
        int
            Right edge position (x + width)
        """
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge row position.

        Returns
        -------
        int
            Bottom edge position (y + height)
        """
        return self.y + self.height

    @property
    def area(self) -> int:
        """Total area of the region.

        Returns
        -------
        int
            Area in cells (width * height)
        """
        return self.width * self.height

    def overlaps(self, other: "DirtyRegion") -> bool:
        """Check if this region overlaps with another.

        Parameters
        ----------
        other : DirtyRegion
            The other region to check

        Returns
        -------
        bool
            True if regions overlap
        """
        return not (
            self.right <= other.x
            or self.x >= other.right
            or self.bottom <= other.y
            or self.y >= other.bottom
        )

    def is_adjacent(self, other: "DirtyRegion") -> bool:
        """Check if this region is adjacent to another (touching edges).

        Adjacent regions can be merged to reduce the number of updates.

        Parameters
        ----------
        other : DirtyRegion
            The other region to check

        Returns
        -------
        bool
            True if regions are adjacent
        """
        # Check horizontal adjacency (same row range, touching columns)
        if self.y == other.y and self.height == other.height:
            if self.right == other.x or other.right == self.x:
                return True

        # Check vertical adjacency (same column range, touching rows)
        if self.x == other.x and self.width == other.width:
            if self.bottom == other.y or other.bottom == self.y:
                return True

        return False

    def merge(self, other: "DirtyRegion") -> "DirtyRegion":
        """Merge this region with another to create a bounding rectangle.

        Parameters
        ----------
        other : DirtyRegion
            The other region to merge with

        Returns
        -------
        DirtyRegion
            A new region that encompasses both regions
        """
        min_x = min(self.x, other.x)
        min_y = min(self.y, other.y)
        max_right = max(self.right, other.right)
        max_bottom = max(self.bottom, other.bottom)

        return DirtyRegion(
            x=min_x,
            y=min_y,
            width=max_right - min_x,
            height=max_bottom - min_y,
        )

    def __repr__(self) -> str:
        """String representation of the dirty region.

        Returns
        -------
        str
            String representation
        """
        return f"DirtyRegion(x={self.x}, y={self.y}, width={self.width}, height={self.height})"


class DirtyRegionManager:
    """Manages dirty regions for optimized screen rendering.

    This class tracks rectangular regions of the screen that need to be
    redrawn and automatically merges overlapping or adjacent regions to
    minimize rendering overhead.

    Attributes
    ----------
    _regions : list[DirtyRegion]
        List of dirty regions
    _full_screen_dirty : bool
        Whether the entire screen is marked as dirty
    _screen_width : int or None
        Screen width (set when marking full screen dirty)
    _screen_height : int or None
        Screen height (set when marking full screen dirty)

    Examples
    --------
    >>> manager = DirtyRegionManager()
    >>> manager.mark_dirty(0, 0, 10, 5)
    >>> manager.mark_dirty(5, 0, 10, 5)  # Overlaps, will be merged
    >>> regions = manager.get_merged_regions()
    >>> len(regions)
    1
    >>> regions[0]
    DirtyRegion(x=0, y=0, width=15, height=5)
    """

    def __init__(self) -> None:
        """Initialize the dirty region manager."""
        self._regions: list[DirtyRegion] = []
        self._full_screen_dirty: bool = False
        self._screen_width: int | None = None
        self._screen_height: int | None = None

    def mark_dirty(self, x: int, y: int, width: int, height: int) -> None:
        """Mark a rectangular region as dirty.

        The region will be merged with any overlapping or adjacent regions
        automatically to optimize rendering.

        Parameters
        ----------
        x : int
            Left edge column position
        y : int
            Top edge row position
        width : int
            Width in columns
        height : int
            Height in rows

        Notes
        -----
        If the full screen is already marked as dirty, this method has no
        effect since the entire screen will be redrawn anyway.
        """
        # If full screen is dirty, no need to track individual regions
        if self._full_screen_dirty:
            return

        # Ignore invalid regions
        if width <= 0 or height <= 0:
            return

        region = DirtyRegion(x=x, y=y, width=width, height=height)
        self._add_and_merge(region)

    def mark_dirty_bounds(self, bounds: Bounds) -> None:
        """Mark a region as dirty using a Bounds object.

        Parameters
        ----------
        bounds : Bounds
            The bounds to mark as dirty
        """
        self.mark_dirty(bounds.x, bounds.y, bounds.width, bounds.height)

    def mark_full_screen(self, width: int, height: int) -> None:
        """Mark the entire screen as dirty.

        This clears all individual dirty regions and marks the whole screen
        for redraw. Use this for major layout changes or when the cost of
        tracking individual regions exceeds the benefit.

        Parameters
        ----------
        width : int
            Screen width in columns
        height : int
            Screen height in rows
        """
        self._regions.clear()
        self._full_screen_dirty = True
        self._screen_width = width
        self._screen_height = height

    def get_merged_regions(self) -> list[tuple[int, int, int, int]]:
        """Get all dirty regions as merged rectangles.

        Returns dirty regions with overlapping/adjacent regions merged to
        minimize the number of screen updates.

        Returns
        -------
        list[tuple[int, int, int, int]]
            List of dirty regions as (x, y, width, height) tuples

        Notes
        -----
        If the full screen is marked as dirty, returns a single region
        covering the entire screen.
        """
        if self._full_screen_dirty:
            if self._screen_width is not None and self._screen_height is not None:
                return [(0, 0, self._screen_width, self._screen_height)]
            return []

        # Return merged regions as tuples
        return [(r.x, r.y, r.width, r.height) for r in self._regions]

    def is_full_screen_dirty(self) -> bool:
        """Check if the full screen is marked as dirty.

        Returns
        -------
        bool
            True if full screen needs redraw
        """
        return self._full_screen_dirty

    def is_dirty(self) -> bool:
        """Check if there are any dirty regions.

        Returns
        -------
        bool
            True if there are dirty regions or full screen is dirty
        """
        return self._full_screen_dirty or len(self._regions) > 0

    def clear(self) -> None:
        """Clear all dirty regions.

        Call this after rendering is complete to reset the dirty state.
        """
        self._regions.clear()
        self._full_screen_dirty = False
        self._screen_width = None
        self._screen_height = None

    def _add_and_merge(self, new_region: DirtyRegion) -> None:
        """Add a region and merge with overlapping/adjacent regions.

        This method implements an iterative merging algorithm:
        1. Check if new region overlaps or is adjacent to any existing region
        2. If yes, merge them and repeat with the merged region
        3. Continue until no more merges are possible
        4. Add the final merged region to the list

        Parameters
        ----------
        new_region : DirtyRegion
            The region to add and merge
        """
        merged = True
        while merged:
            merged = False
            for i, existing in enumerate(self._regions):
                if new_region.overlaps(existing) or new_region.is_adjacent(existing):
                    # Merge the regions
                    new_region = new_region.merge(existing)
                    # Remove the old region
                    self._regions.pop(i)
                    # Mark that we merged and need another pass
                    merged = True
                    break

        # Add the final merged region
        self._regions.append(new_region)

    def __repr__(self) -> str:
        """String representation of the dirty region manager.

        Returns
        -------
        str
            String representation showing dirty state
        """
        if self._full_screen_dirty:
            return f"DirtyRegionManager(full_screen: {self._screen_width}x{self._screen_height})"
        return f"DirtyRegionManager({len(self._regions)} regions)"
