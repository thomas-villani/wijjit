"""Shared utilities for chart elements.

This module provides common utilities for data visualization elements including:
- Braille character rendering for high-resolution plots
- Axis calculation and scaling
- Color gradient helpers
- Data normalization functions
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass


# Braille character base and dot positions
# Braille patterns use Unicode range U+2800 to U+28FF
# Each braille cell has 8 dots arranged in a 2x4 grid:
#   1 4
#   2 5
#   3 6
#   7 8
# Dot values: 1=0x01, 2=0x02, 3=0x04, 4=0x08, 5=0x10, 6=0x20, 7=0x40, 8=0x80
BRAILLE_BASE = 0x2800

# Dot bit positions for braille (row, col) -> bit value
# Row 0-3 (top to bottom), Col 0-1 (left to right)
BRAILLE_DOTS = {
    (0, 0): 0x01,  # Dot 1
    (1, 0): 0x02,  # Dot 2
    (2, 0): 0x04,  # Dot 3
    (3, 0): 0x40,  # Dot 7
    (0, 1): 0x08,  # Dot 4
    (1, 1): 0x10,  # Dot 5
    (2, 1): 0x20,  # Dot 6
    (3, 1): 0x80,  # Dot 8
}

# Block characters for bar charts (eighths)
BLOCK_CHARS_HORIZONTAL = [
    " ",  # 0/8
    "\u258f",  # 1/8 left
    "\u258e",  # 2/8
    "\u258d",  # 3/8
    "\u258c",  # 4/8 (half)
    "\u258b",  # 5/8
    "\u258a",  # 6/8
    "\u2589",  # 7/8
    "\u2588",  # 8/8 (full)
]

BLOCK_CHARS_VERTICAL = [
    " ",  # 0/8
    "\u2581",  # 1/8 bottom
    "\u2582",  # 2/8
    "\u2583",  # 3/8
    "\u2584",  # 4/8 (half)
    "\u2585",  # 5/8
    "\u2586",  # 6/8
    "\u2587",  # 7/8
    "\u2588",  # 8/8 (full)
]

# ASCII fallbacks
ASCII_BLOCK_HORIZONTAL = [" ", ".", ":", "|", "#"]
ASCII_BLOCK_VERTICAL = [" ", ".", ":", "=", "#"]


class BrailleCanvas:
    """A canvas for drawing using braille characters.

    Each character cell represents a 2x4 grid of dots, providing
    higher resolution plotting within terminal constraints.

    Parameters
    ----------
    width : int
        Width in terminal characters
    height : int
        Height in terminal characters

    Attributes
    ----------
    width : int
        Canvas width in characters
    height : int
        Canvas height in characters
    pixel_width : int
        Canvas width in braille dots (width * 2)
    pixel_height : int
        Canvas height in braille dots (height * 4)

    Examples
    --------
    Create a canvas and plot points:

    >>> canvas = BrailleCanvas(20, 5)
    >>> canvas.set_pixel(0, 0)  # Top-left dot
    >>> canvas.set_pixel(39, 19)  # Bottom-right dot
    >>> lines = canvas.to_lines()
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.pixel_width = width * 2
        self.pixel_height = height * 4

        # Initialize grid of braille patterns (0 = empty)
        self._grid: list[list[int]] = [[0 for _ in range(width)] for _ in range(height)]

    def clear(self) -> None:
        """Clear the canvas."""
        for row in self._grid:
            for i in range(len(row)):
                row[i] = 0

    def set_pixel(self, x: int, y: int) -> None:
        """Set a pixel (dot) at the given coordinates.

        Parameters
        ----------
        x : int
            X coordinate in pixels (0 to pixel_width-1)
        y : int
            Y coordinate in pixels (0 to pixel_height-1)

        Notes
        -----
        Coordinates outside the canvas bounds are silently ignored.
        """
        if x < 0 or x >= self.pixel_width or y < 0 or y >= self.pixel_height:
            return

        # Convert pixel coordinates to character cell and dot position
        char_x = x // 2
        char_y = y // 4
        dot_x = x % 2
        dot_y = y % 4

        # Get the bit value for this dot position
        dot_bit = BRAILLE_DOTS.get((dot_y, dot_x), 0)

        # Set the bit in the grid
        self._grid[char_y][char_x] |= dot_bit

    def unset_pixel(self, x: int, y: int) -> None:
        """Unset a pixel (dot) at the given coordinates.

        Parameters
        ----------
        x : int
            X coordinate in pixels
        y : int
            Y coordinate in pixels
        """
        if x < 0 or x >= self.pixel_width or y < 0 or y >= self.pixel_height:
            return

        char_x = x // 2
        char_y = y // 4
        dot_x = x % 2
        dot_y = y % 4

        dot_bit = BRAILLE_DOTS.get((dot_y, dot_x), 0)
        self._grid[char_y][char_x] &= ~dot_bit

    def get_pixel(self, x: int, y: int) -> bool:
        """Check if a pixel is set.

        Parameters
        ----------
        x : int
            X coordinate in pixels
        y : int
            Y coordinate in pixels

        Returns
        -------
        bool
            True if pixel is set, False otherwise
        """
        if x < 0 or x >= self.pixel_width or y < 0 or y >= self.pixel_height:
            return False

        char_x = x // 2
        char_y = y // 4
        dot_x = x % 2
        dot_y = y % 4

        dot_bit = BRAILLE_DOTS.get((dot_y, dot_x), 0)
        return bool(self._grid[char_y][char_x] & dot_bit)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Draw a line between two points using Bresenham's algorithm.

        Parameters
        ----------
        x0, y0 : int
            Starting point coordinates
        x1, y1 : int
            Ending point coordinates
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.set_pixel(x0, y0)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def fill_below(self, x: int, y: int) -> None:
        """Fill all pixels below the given point to the bottom.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate to start filling from
        """
        for fill_y in range(y, self.pixel_height):
            self.set_pixel(x, fill_y)

    def to_lines(self) -> list[str]:
        """Convert the canvas to a list of braille character strings.

        Returns
        -------
        list of str
            Lines of braille characters representing the canvas
        """
        lines = []
        for row in self._grid:
            line = "".join(chr(BRAILLE_BASE + pattern) for pattern in row)
            lines.append(line)
        return lines

    def render(self) -> list[str]:
        """Convert the canvas to a list of braille character strings (DEPRECATED).

        .. deprecated::
            Use ``to_lines()`` instead. This method is kept for
            backwards compatibility.

        Returns
        -------
        list of str
            Lines of braille characters representing the canvas
        """
        return self.to_lines()

    def render_to_string(self) -> str:
        """Convert the canvas to a single string with newlines.

        Returns
        -------
        str
            Complete canvas as a string
        """
        return "\n".join(self.to_lines())


def normalize_data(
    data: list[float | int],
    min_val: float | None = None,
    max_val: float | None = None,
) -> tuple[list[float], float, float]:
    """Normalize data to 0-1 range.

    Parameters
    ----------
    data : list of float or int
        Raw data values
    min_val : float, optional
        Minimum value for scaling (default: auto from data)
    max_val : float, optional
        Maximum value for scaling (default: auto from data)

    Returns
    -------
    tuple
        (normalized_data, actual_min, actual_max)

    Examples
    --------
    >>> data = [10, 20, 30, 40, 50]
    >>> normalized, min_v, max_v = normalize_data(data)
    >>> normalized
    [0.0, 0.25, 0.5, 0.75, 1.0]
    """
    if not data:
        return [], 0.0, 0.0

    actual_min = min_val if min_val is not None else min(data)
    actual_max = max_val if max_val is not None else max(data)

    # Avoid division by zero
    range_val = actual_max - actual_min
    if range_val == 0:
        return [0.5] * len(data), actual_min, actual_max

    normalized = [(v - actual_min) / range_val for v in data]
    return normalized, actual_min, actual_max


def scale_value(
    value: float,
    min_val: float,
    max_val: float,
    target_min: int,
    target_max: int,
) -> int:
    """Scale a value from one range to another.

    Parameters
    ----------
    value : float
        Value to scale
    min_val : float
        Source range minimum
    max_val : float
        Source range maximum
    target_min : int
        Target range minimum
    target_max : int
        Target range maximum

    Returns
    -------
    int
        Scaled value (clamped to target range)
    """
    if max_val == min_val:
        return (target_min + target_max) // 2

    normalized = (value - min_val) / (max_val - min_val)
    scaled = target_min + normalized * (target_max - target_min)
    return int(max(target_min, min(target_max, scaled)))


def get_block_char(
    fraction: float,
    direction: Literal["horizontal", "vertical"] = "horizontal",
    use_unicode: bool = True,
) -> str:
    """Get a block character representing a fractional fill.

    Parameters
    ----------
    fraction : float
        Fill fraction (0.0 to 1.0)
    direction : str
        "horizontal" for left-to-right fill, "vertical" for bottom-to-top
    use_unicode : bool
        Whether to use Unicode block characters (default: True)

    Returns
    -------
    str
        Block character representing the fraction
    """
    fraction = max(0.0, min(1.0, fraction))
    index = int(fraction * 8)
    index = min(index, 8)  # Clamp to valid range

    if use_unicode:
        chars = (
            BLOCK_CHARS_HORIZONTAL
            if direction == "horizontal"
            else BLOCK_CHARS_VERTICAL
        )
    else:
        chars = (
            ASCII_BLOCK_HORIZONTAL
            if direction == "horizontal"
            else ASCII_BLOCK_VERTICAL
        )
        # Map 0-8 to 0-4 for ASCII
        index = index * len(chars) // 9

    return chars[min(index, len(chars) - 1)]


def calculate_axis_ticks(
    min_val: float, max_val: float, max_ticks: int = 5
) -> list[float]:
    """Calculate nice tick values for an axis.

    Parameters
    ----------
    min_val : float
        Minimum axis value
    max_val : float
        Maximum axis value
    max_ticks : int
        Maximum number of ticks (default: 5)

    Returns
    -------
    list of float
        Tick values

    Examples
    --------
    >>> calculate_axis_ticks(0, 100, 5)
    [0, 25, 50, 75, 100]
    """
    if min_val == max_val:
        return [min_val]

    range_val = max_val - min_val

    # Find a nice step size
    raw_step = range_val / (max_ticks - 1)

    # Round to a nice number
    magnitude = 10 ** int(f"{raw_step:.0e}".split("e")[1])
    normalized_step = raw_step / magnitude

    if normalized_step <= 1:
        nice_step = magnitude
    elif normalized_step <= 2:
        nice_step = 2 * magnitude
    elif normalized_step <= 5:
        nice_step = 5 * magnitude
    else:
        nice_step = 10 * magnitude

    # Generate ticks
    ticks = []
    tick = (min_val // nice_step) * nice_step
    while tick <= max_val + nice_step / 2:
        if tick >= min_val - nice_step / 2:
            ticks.append(tick)
        tick += nice_step

    return ticks


def format_axis_value(value: float, max_val: float) -> str:
    """Format an axis value for display.

    Parameters
    ----------
    value : float
        Value to format
    max_val : float
        Maximum value on axis (for determining format)

    Returns
    -------
    str
        Formatted value string
    """
    if max_val >= 1000000:
        return f"{value/1000000:.1f}M"
    elif max_val >= 1000:
        return f"{value/1000:.1f}K"
    elif max_val >= 100:
        return f"{value:.0f}"
    elif max_val >= 1:
        return f"{value:.1f}"
    else:
        return f"{value:.2f}"


def get_gradient_color(
    value: float,
    min_val: float = 0.0,
    max_val: float = 1.0,
    color_scale: Literal["green", "red", "blue", "heat", "cool"] = "green",
) -> tuple[int, int, int]:
    """Get an RGB color from a gradient based on value.

    Parameters
    ----------
    value : float
        Value to map to color
    min_val : float
        Minimum value (maps to start color)
    max_val : float
        Maximum value (maps to end color)
    color_scale : str
        Color scale name: "green", "red", "blue", "heat", "cool"

    Returns
    -------
    tuple of int
        (R, G, B) color values (0-255)
    """
    # Normalize value to 0-1
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0.0, min(1.0, normalized))

    # Define color gradients (start_color, end_color)
    gradients = {
        "green": ((40, 40, 40), (0, 200, 0)),
        "red": ((40, 40, 40), (200, 0, 0)),
        "blue": ((40, 40, 40), (0, 100, 200)),
        "heat": ((0, 0, 128), (255, 100, 0)),  # Blue to orange
        "cool": ((0, 100, 200), (100, 200, 255)),  # Dark to light blue
    }

    start, end = gradients.get(color_scale, gradients["green"])

    # Interpolate
    r = int(start[0] + normalized * (end[0] - start[0]))
    g = int(start[1] + normalized * (end[1] - start[1]))
    b = int(start[2] + normalized * (end[2] - start[2]))

    return (r, g, b)


def get_threshold_color(
    value: float,
    thresholds: list[tuple[float, tuple[int, int, int]]] | None = None,
) -> tuple[int, int, int]:
    """Get a color based on threshold values.

    Parameters
    ----------
    value : float
        Value to check (typically 0-1 normalized)
    thresholds : list of tuples, optional
        List of (threshold, color) pairs, sorted ascending.
        Default: [(0.33, red), (0.66, yellow), (1.0, green)]

    Returns
    -------
    tuple of int
        (R, G, B) color values
    """
    if thresholds is None:
        thresholds = [
            (0.33, (200, 50, 50)),  # Red
            (0.66, (200, 200, 50)),  # Yellow
            (1.0, (50, 200, 50)),  # Green
        ]

    for threshold, color in thresholds:
        if value <= threshold:
            return color

    # Return last color if value exceeds all thresholds
    return thresholds[-1][1] if thresholds else (128, 128, 128)


def extract_values(
    data: list[dict[str, Any] | tuple[Any, ...] | float | int],
    value_key: str = "value",
) -> tuple[list[float], list[str]]:
    """Extract values and labels from various data formats.

    Parameters
    ----------
    data : list
        Data in various formats:
        - List of numbers: [10, 20, 30]
        - List of tuples: [("A", 10), ("B", 20)]
        - List of dicts: [{"label": "A", "value": 10}, ...]
    value_key : str
        Key to use for values in dict format (default: "value")

    Returns
    -------
    tuple
        (values, labels) where values is list of floats and labels is list of strings
    """
    values: list[float] = []
    labels: list[str] = []

    for i, item in enumerate(data):
        if isinstance(item, dict):
            values.append(float(item.get(value_key, 0)))
            labels.append(str(item.get("label", f"{i}")))
        elif isinstance(item, tuple) and len(item) >= 2:
            labels.append(str(item[0]))
            values.append(float(item[1]))
        else:
            assert isinstance(item, (int, float))
            values.append(float(item))
            labels.append(str(i))

    return values, labels
