"""Bounds and positioning utilities for layout calculation.

This module provides dataclasses and utilities for tracking the position
and size of UI elements in the terminal.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Bounds:
    """Represents the position and size of a UI element.

    Parameters
    ----------
    x : int
        Horizontal position (column), 0-indexed
    y : int
        Vertical position (row), 0-indexed
    width : int
        Width in characters
    height : int
        Height in lines

    Attributes
    ----------
    x : int
        Horizontal position
    y : int
        Vertical position
    width : int
        Width in characters
    height : int
        Height in lines
    """

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Get the right edge position (x + width).

        Returns
        -------
        int
            Right edge column
        """
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Get the bottom edge position (y + height).

        Returns
        -------
        int
            Bottom edge row
        """
        return self.y + self.height

    @property
    def area(self) -> int:
        """Get the total area (width * height).

        Returns
        -------
        int
            Total area in characters
        """
        return self.width * self.height

    def contains(self, x: int, y: int) -> bool:
        """Check if a point is within these bounds.

        Parameters
        ----------
        x : int
            X coordinate to check
        y : int
            Y coordinate to check

        Returns
        -------
        bool
            True if the point is within bounds
        """
        return self.x <= x < self.right and self.y <= y < self.bottom

    def overlaps(self, other: Bounds) -> bool:
        """Check if these bounds overlap with another bounds.

        Parameters
        ----------
        other : Bounds
            The other bounds to check

        Returns
        -------
        bool
            True if bounds overlap
        """
        return not (
            self.right <= other.x
            or self.x >= other.right
            or self.bottom <= other.y
            or self.y >= other.bottom
        )

    def __repr__(self) -> str:
        """String representation of bounds.

        Returns
        -------
        str
            String representation
        """
        return (
            f"Bounds(x={self.x}, y={self.y}, width={self.width}, height={self.height})"
        )


@dataclass
class Size:
    """Represents a size specification for layout calculation.

    This can represent fixed sizes, percentages, or fill behavior.

    Parameters
    ----------
    value : int or str
        Size value (integer for fixed, "fill" for remaining space,
        or percentage string like "50%")

    Attributes
    ----------
    value : int or str
        The size specification
    """

    value: int | str

    @property
    def is_fixed(self) -> bool:
        """Check if this is a fixed size.

        Returns
        -------
        bool
            True if fixed size
        """
        return isinstance(self.value, int)

    @property
    def is_fill(self) -> bool:
        """Check if this should fill available space.

        Returns
        -------
        bool
            True if fill mode
        """
        return self.value == "fill" or self.value == "100%"

    @property
    def is_percentage(self) -> bool:
        """Check if this is a percentage size.

        Returns
        -------
        bool
            True if percentage
        """
        return isinstance(self.value, str) and self.value.endswith("%")

    def get_percentage(self) -> float:
        """Get the percentage value (0.0 to 1.0).

        Returns
        -------
        float
            Percentage as decimal

        Raises
        ------
        ValueError
            If not a percentage size
        """
        if not self.is_percentage:
            raise ValueError("Size is not a percentage")

        return float(self.value.rstrip("%")) / 100.0

    def calculate(self, available: int) -> int:
        """Calculate the actual size given available space.

        Parameters
        ----------
        available : int
            Available space

        Returns
        -------
        int
            Calculated size
        """
        if self.is_fixed:
            return min(self.value, available)
        elif self.is_percentage:
            return int(available * self.get_percentage())
        elif self.is_fill:
            return available
        else:
            # Auto or unknown - use minimum
            return 0

    def __repr__(self) -> str:
        """String representation of size.

        Returns
        -------
        str
            String representation
        """
        return f"Size({self.value})"


def parse_size(value: int | str | Size) -> Size:
    """Parse a size value into a Size object.

    Parameters
    ----------
    value : int, str, or Size
        Size specification

    Returns
    -------
    Size
        Parsed Size object
    """
    if isinstance(value, Size):
        return value
    return Size(value)


def parse_margin(value: int | tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Parse a margin value into a normalized 4-tuple.

    Parameters
    ----------
    value : int or tuple of int
        Margin specification. If int, applies uniformly to all sides.
        If tuple, specifies (top, right, bottom, left) margins.

    Returns
    -------
    tuple of int
        Normalized 4-tuple (top, right, bottom, left)

    Examples
    --------
    >>> parse_margin(2)
    (2, 2, 2, 2)
    >>> parse_margin((1, 2, 3, 4))
    (1, 2, 3, 4)
    """
    if isinstance(value, int):
        return (value, value, value, value)
    elif isinstance(value, tuple) and len(value) == 4:
        return value
    else:
        raise ValueError(f"Margin must be int or 4-tuple, got {type(value)}")
