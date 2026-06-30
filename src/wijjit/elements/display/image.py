"""Image display element for rendering images in the terminal.

This module provides the ImageView element which converts images to ANSI
colored characters for display in terminal user interfaces.
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import TYPE_CHECKING, Any, Union

from wijjit.elements.base import Element, ElementType
from wijjit.logging_config import get_logger
from wijjit.terminal.cell import Cell

if TYPE_CHECKING:

    from wijjit.rendering.paint_context import PaintContext

logger = get_logger(__name__)

# Check PIL availability
PIL_AVAILABLE = False
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore


# Type alias for image sources
ImageSource = Union[str, bytes, "os.PathLike[str]", "Image.Image", None]


class ImageView(Element):
    """Element for displaying images in the terminal.

    Converts images to ANSI-colored characters for terminal display.
    Supports two rendering modes:

    - Color mode (default): Uses half-block characters (U+2580) with
      foreground (upper pixel) and background (lower pixel) colors,
      achieving 2x vertical resolution.

    - Braille mode: Converts image to black/white using Otsu's threshold,
      then renders using braille characters (U+2800-U+28FF) for 2x4
      pixel resolution per character.

    Parameters
    ----------
    id : str, optional
        Element identifier
    src : str, Path, bytes, or PIL.Image.Image, optional
        Image source - file path, bytes data, or PIL Image object
    width : int or str, optional
        Display width. If "auto" or None, calculate from height and aspect ratio.
        If "fill", expand to available space.
    height : int or str, optional
        Display height. If "auto" or None, calculate from width and aspect ratio.
        If "fill", expand to available space.
    braille : bool, optional
        If True, use braille mode for B&W rendering (default: False)
    invert : bool, optional
        If True, invert the threshold in braille mode so dark pixels become
        dots instead of light pixels (default: False)
    background : tuple of (int, int, int), optional
        Background RGB color for transparency compositing (default: (0, 0, 0))
    classes : str or list of str, optional
        CSS class names for styling

    Attributes
    ----------
    src : ImageSource
        Image source
    width_spec : int or str or None
        Width specification
    height_spec : int or str or None
        Height specification
    braille : bool
        Whether to use braille rendering mode
    invert : bool
        Whether to invert the braille threshold
    background : tuple
        Background color for transparency
    """

    # Half-block character for color mode (upper half filled)
    HALF_BLOCK = "\u2580"

    # Braille base character (empty braille pattern)
    BRAILLE_BASE = 0x2800

    # Braille dot positions: (dx, dy, bit_index)
    # Each braille char represents 2x4 pixels
    BRAILLE_DOTS = [
        (0, 0, 0),
        (0, 1, 1),
        (0, 2, 2),
        (1, 0, 3),
        (1, 1, 4),
        (1, 2, 5),
        (0, 3, 6),
        (1, 3, 7),
    ]

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | set[str] | None = None,
        src: ImageSource = None,
        width: int | str | None = None,
        height: int | str | None = None,
        braille: bool = False,
        invert: bool = False,
        background: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        # Image properties
        self.src = src
        self.width_spec = width
        self.height_spec = height
        self.braille = braille
        self.invert = invert
        self.background = background

        # Template metadata
        self.bind: bool = True

        # Cache
        self._cached_image: Any = None  # PIL.Image.Image
        self._cached_render: list[list[tuple[str, tuple, tuple | None]]] | None = None
        self._last_render_size: tuple[int, int] | None = None

        if not PIL_AVAILABLE and src is not None:
            logger.warning(
                "PIL/Pillow not installed. ImageView will show placeholder. "
                "Install with: pip install Pillow"
            )

    def _load_image(self) -> Any:
        """Load image from source with error handling.

        Returns
        -------
        PIL.Image.Image or None
            Loaded image or None on failure
        """
        if not PIL_AVAILABLE:
            return None

        if self._cached_image is not None:
            return self._cached_image

        if self.src is None:
            return None

        try:
            if hasattr(self.src, "copy") and hasattr(self.src, "convert"):
                # It's a PIL Image
                self._cached_image = self.src.copy()
            elif isinstance(self.src, bytes):
                self._cached_image = Image.open(BytesIO(self.src))
            elif isinstance(self.src, (str, os.PathLike)):
                self._cached_image = Image.open(self.src)
            else:
                logger.warning(f"Unsupported image source type: {type(self.src)}")
                return None

            return self._cached_image

        except FileNotFoundError:
            logger.warning(f"Image file not found: {self.src}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load image: {e}")
            return None

    def _parse_size_spec(self, spec: int | str | None, available: int) -> int | None:
        """Parse a size specification.

        Parameters
        ----------
        spec : int, str, or None
            Size spec: int, "fill", "auto", "50%", or None
        available : int
            Available space

        Returns
        -------
        int or None
            Resolved size or None for "auto"
        """
        if spec is None or spec == "auto":
            return None
        if spec == "fill":
            return available
        if isinstance(spec, str) and spec.endswith("%"):
            pct = int(spec[:-1])
            return max(1, int(available * pct / 100))
        return int(spec)

    def _calculate_dimensions(
        self, available_width: int, available_height: int
    ) -> tuple[int, int]:
        """Calculate final render dimensions from specs and constraints.

        Parameters
        ----------
        available_width : int
            Maximum available width
        available_height : int
            Maximum available height

        Returns
        -------
        tuple of (int, int)
            (width, height) in characters/rows
        """
        img = self._load_image()
        if img is None:
            return (1, 1)

        img_width, img_height = img.size

        # Calculate aspect ratio accounting for terminal character proportions
        # Terminal chars are ~2:1 (twice as tall as wide)
        # Half-block gives 2 pixels vertically per row
        # Braille gives 4 pixels vertically, 2 horizontally per char
        if self.braille:
            # Braille: 2 pixels wide, 4 pixels tall per char
            # Effective aspect = (img_width / 2) / (img_height / 4) = img_width * 2 / img_height
            aspect_ratio = (img_width / 2) / (img_height / 4)
        else:
            # Half-block: 1 pixel wide, 2 pixels tall per char
            # Effective aspect = img_width / (img_height / 2) = img_width * 2 / img_height
            aspect_ratio = img_width / (img_height / 2)

        # Parse width/height specs
        width = self._parse_size_spec(self.width_spec, available_width)
        height = self._parse_size_spec(self.height_spec, available_height)

        # Handle sizing modes
        if width is None and height is None:
            # Both auto: fit within available space
            width = available_width
            height = int(width / aspect_ratio)
            if height > available_height:
                height = available_height
                width = int(height * aspect_ratio)
        elif width is None:
            # Width auto: calculate from height
            width = int(height * aspect_ratio)
            width = min(width, available_width)
        elif height is None:
            # Height auto: calculate from width
            height = int(width / aspect_ratio)
            height = min(height, available_height)

        # Ensure minimum dimensions
        return (max(1, width), max(1, height))

    def _otsu_threshold(self, img: Any) -> int:
        """Calculate Otsu's threshold for binarization.

        Parameters
        ----------
        img : PIL.Image.Image
            Grayscale image

        Returns
        -------
        int
            Optimal threshold value (0-255)
        """
        # Build histogram
        histogram = img.histogram()
        total_pixels = img.width * img.height

        if total_pixels == 0:
            return 128

        # Compute Otsu's threshold
        sum_total = sum(i * histogram[i] for i in range(256))
        sum_background = 0
        weight_background = 0
        max_variance = 0
        threshold = 128

        for i in range(256):
            weight_background += histogram[i]
            if weight_background == 0:
                continue
            weight_foreground = total_pixels - weight_background
            if weight_foreground == 0:
                break

            sum_background += i * histogram[i]
            mean_background = sum_background / weight_background
            mean_foreground = (sum_total - sum_background) / weight_foreground

            variance = (
                weight_background
                * weight_foreground
                * (mean_background - mean_foreground) ** 2
            )

            if variance > max_variance:
                max_variance = variance
                threshold = i

        return threshold

    def _render_color_mode(
        self, cols: int, rows: int
    ) -> list[list[tuple[str, tuple, tuple]]]:
        """Render image using half-block characters with fg/bg colors.

        Parameters
        ----------
        cols : int
            Number of character columns
        rows : int
            Number of terminal rows

        Returns
        -------
        list of list of tuple
            2D grid of (char, fg_color, bg_color) tuples
        """
        img = self._load_image()
        if img is None:
            return []

        # Convert to RGBA for transparency handling
        img = img.convert("RGBA")

        # Composite over background
        bg = Image.new("RGBA", img.size, (*self.background, 255))
        img = Image.alpha_composite(bg, img).convert("RGB")

        # Choose resampling method
        try:
            resample = Image.Resampling.BOX
        except AttributeError:
            resample = Image.BOX  # type: ignore

        # Resize: width = cols, height = rows * 2 (2 pixels per row)
        target_size = (cols, rows * 2)
        down = img.resize(target_size, resample)
        px = down.load()

        cells = []
        for y in range(rows):
            row_cells = []
            for x in range(cols):
                top = px[x, 2 * y]  # Upper pixel -> fg
                bottom = px[x, 2 * y + 1]  # Lower pixel -> bg
                row_cells.append((self.HALF_BLOCK, top, bottom))
            cells.append(row_cells)

        return cells

    def _render_braille_mode(
        self, cols: int, rows: int
    ) -> list[list[tuple[str, tuple, None]]]:
        """Render image using braille characters (2x4 pixels per char).

        Parameters
        ----------
        cols : int
            Number of character columns
        rows : int
            Number of terminal rows

        Returns
        -------
        list of list of tuple
            2D grid of (char, fg_color, None) tuples
        """
        img = self._load_image()
        if img is None:
            return []

        # Convert to grayscale
        gray = img.convert("L")

        # Apply Otsu's threshold
        threshold = self._otsu_threshold(gray)

        # Choose resampling method
        try:
            resample = Image.Resampling.BOX
        except AttributeError:
            resample = Image.BOX  # type: ignore

        # Resize: width = cols * 2, height = rows * 4 (2x4 pixels per char)
        target_size = (cols * 2, rows * 4)
        down = gray.resize(target_size, resample)
        px = down.load()

        cells = []
        for y in range(rows):
            row_cells = []
            for x in range(cols):
                pattern = 0
                for dx, dy, bit in self.BRAILLE_DOTS:
                    px_x = x * 2 + dx
                    px_y = y * 4 + dy
                    # Check if pixel should be a dot
                    # Normal: white pixels (above threshold) become dots
                    # Invert: dark pixels (below threshold) become dots
                    pixel_value = px[px_x, px_y]
                    if self.invert:
                        is_dot = pixel_value <= threshold
                    else:
                        is_dot = pixel_value > threshold
                    if is_dot:
                        pattern |= 1 << bit

                char = chr(self.BRAILLE_BASE + pattern)
                # Use white foreground for braille dots
                row_cells.append((char, (255, 255, 255), None))
            cells.append(row_cells)

        return cells

    def _render_placeholder(self, ctx: PaintContext, message: str) -> None:
        """Render a placeholder when image cannot be displayed.

        Parameters
        ----------
        ctx : PaintContext
            Paint context
        message : str
            Error message to display
        """
        style = ctx.style_resolver.resolve_style(self, "image.placeholder")

        # Draw border
        width = ctx.bounds.width
        height = ctx.bounds.height

        # Top border
        ctx.write_text(0, 0, "+" + "-" * (width - 2) + "+", style)

        # Side borders
        for y in range(1, height - 1):
            ctx.write_text(0, y, "|", style)
            ctx.write_text(width - 1, y, "|", style)

        # Bottom border
        if height > 1:
            ctx.write_text(0, height - 1, "+" + "-" * (width - 2) + "+", style)

        # Center message
        msg = f"[{message}]"
        if len(msg) > width - 4:
            msg = msg[: width - 7] + "...]"

        x = max(1, (width - len(msg)) // 2)
        y = height // 2
        if 0 < y < height - 1:
            ctx.write_text(x, y, msg, style)

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic size based on image dimensions.

        Returns
        -------
        tuple of (int, int)
            (width, height) for auto sizing
        """
        img = self._load_image()
        if img is None:
            return (10, 5)  # Default placeholder size

        img_width, img_height = img.size

        # Calculate aspect ratio for terminal chars
        # Terminal chars are ~2:1 (twice as tall as wide)
        if self.braille:
            # Braille: 2 pixels wide, 4 pixels tall per char
            aspect_ratio = (img_width / 2) / (img_height / 4)
        else:
            # Half-block: 1 pixel wide, 2 pixels tall per char
            aspect_ratio = img_width / (img_height / 2)

        # Check if width or height is specified
        width_specified = self.width_spec is not None and isinstance(
            self.width_spec, int
        )
        height_specified = self.height_spec is not None and isinstance(
            self.height_spec, int
        )

        if width_specified and height_specified:
            # Both specified - use them directly
            width = self.width_spec
            height = self.height_spec
        elif width_specified:
            # Width specified - calculate height from aspect ratio
            width = self.width_spec
            height = max(1, int(width / aspect_ratio))
        elif height_specified:
            # Height specified - calculate width from aspect ratio
            height = self.height_spec
            width = max(1, int(height * aspect_ratio))
        else:
            # Neither specified - use natural size
            if self.braille:
                width = img_width // 2
                height = img_height // 4
            else:
                width = img_width
                height = img_height // 2

        # Limit to reasonable defaults
        width = min(width, 80)
        height = min(height, 40)

        return (max(1, width), max(1, height))

    def render_to(self, ctx: PaintContext) -> None:
        """Render the image to the paint context.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds
        """
        if not PIL_AVAILABLE:
            self._render_placeholder(ctx, "PIL not installed")
            return

        img = self._load_image()
        if img is None:
            self._render_placeholder(ctx, "No image")
            return

        # Calculate dimensions
        width, height = self._calculate_dimensions(ctx.bounds.width, ctx.bounds.height)

        # Clamp to available space
        width = min(width, ctx.bounds.width)
        height = min(height, ctx.bounds.height)

        # Check cache
        render_size = (width, height, self.braille, self.invert)
        if self._cached_render is not None and self._last_render_size == render_size:
            cells = self._cached_render
        else:
            # Render image to cells
            if self.braille:
                cells = self._render_braille_mode(width, height)
            else:
                cells = self._render_color_mode(width, height)
            self._cached_render = cells
            self._last_render_size = render_size

        if not cells:
            self._render_placeholder(ctx, "Render failed")
            return

        # Write cells to paint context
        for y, row in enumerate(cells):
            for x, (char, fg, bg) in enumerate(row):
                if x < ctx.bounds.width and y < ctx.bounds.height:
                    # Write cell with true color
                    cell = Cell(char=char, fg_color=fg, bg_color=bg)
                    ctx.write_cell(x, y, cell)

    def set_src(self, src: ImageSource) -> None:
        """Update image source and invalidate cache.

        Parameters
        ----------
        src : ImageSource
            New image source
        """
        if self.src != src:
            self.src = src
            self._cached_image = None
            self._cached_render = None
            self._last_render_size = None

    def invalidate_cache(self) -> None:
        """Force cache invalidation for next render."""
        self._cached_image = None
        self._cached_render = None
        self._last_render_size = None
