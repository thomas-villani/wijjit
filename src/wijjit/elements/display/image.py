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
    Supports three rendering modes, selected with ``mode``:

    - ``"color"`` (default): Uses half-block characters (U+2580) with
      foreground (upper pixel) and background (lower pixel) colors,
      achieving 2x vertical resolution.

    - ``"quadrant"``: Uses quadrant block characters (U+2596-U+259F) for a
      2x2 subpixel grid per cell. Each cell is split into a bright and a dark
      group at the cell's own mean luminance and drawn with two colors, so it
      keeps full color while doubling horizontal detail over ``"color"``.

    - ``"braille"``: Converts the image to black/white using ``threshold``,
      then renders using braille characters (U+2800-U+28FF) for 2x4
      pixel resolution per character.

    Notes
    -----
    Braille resolves 2x4 subpixels but its dots only cover part of each cell,
    so fine detail is monochrome and visually diluted. ``"quadrant"`` resolves
    fewer subpixels but fills the cell completely and keeps color, which reads
    better for photographs; ``"braille"`` suits line art and high-contrast
    graphics. Denser full-coverage charsets exist (sextants at 2x3, octants at
    2x4) but are absent from common terminal fonts - including Cascadia Mono,
    the Windows Terminal default - so they are deliberately not offered here.

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
    mode : str, optional
        Rendering mode: "color", "quadrant", or "braille" (default: "color")
    threshold : int or str, optional
        Binarization cutoff for braille mode: an integer 0-255, or "auto" to
        compute Otsu's threshold from the image (default: "auto")
    invert : bool, optional
        If True, invert the threshold in braille mode so dark pixels become
        dots instead of light pixels (default: False)
    background : tuple of (int, int, int), optional
        Background RGB color for transparency compositing (default: (0, 0, 0))
    classes : str or list of str, optional
        CSS class names for styling

    Raises
    ------
    ValueError
        If ``mode`` is not one of the supported modes, or ``threshold`` is
        neither "auto" nor an integer.

    Attributes
    ----------
    src : ImageSource
        Image source
    width_spec : int or str or None
        Width specification
    height_spec : int or str or None
        Height specification
    mode : str
        Active rendering mode
    threshold : int or str
        Braille binarization cutoff, or "auto"
    invert : bool
        Whether to invert the braille threshold
    background : tuple
        Background color for transparency
    """

    #: Supported values for ``mode``.
    MODES = ("color", "quadrant", "braille")

    # Half-block character for color mode (upper half filled)
    HALF_BLOCK = "\u2580"

    # Quadrant block characters indexed by a row-major bitmask:
    # bit0=top-left, bit1=top-right, bit2=bottom-left, bit3=bottom-right.
    QUADRANT_CHARS = (
        " ",
        "\u2598",
        "\u259d",
        "\u2580",
        "\u2596",
        "\u258c",
        "\u259e",
        "\u259b",
        "\u2597",
        "\u259a",
        "\u2590",
        "\u259c",
        "\u2584",
        "\u2599",
        "\u259f",
        "\u2588",
    )

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
        mode: str = "color",
        threshold: int | str = "auto",
        invert: bool = False,
        background: tuple[int, int, int] = (0, 0, 0),
        bind: bool | str = True,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY
        self.focusable = False

        if mode not in self.MODES:
            raise ValueError(
                f"Invalid ImageView mode {mode!r}. Expected one of: "
                + ", ".join(repr(m) for m in self.MODES)
            )

        # Image properties
        self.src = src
        self.width_spec = width
        self.height_spec = height
        self.mode = mode
        self.threshold = self._validate_threshold(threshold)
        self.invert = invert
        self.background = background

        # Template metadata
        self.bind: bool | str = bind

        # Cache
        self._cached_image: Any = None  # PIL.Image.Image
        self._cached_render: list[list[tuple[str, tuple, tuple | None]]] | None = None
        self._last_render_size: tuple[Any, ...] | None = None

        if not PIL_AVAILABLE and src is not None:
            logger.warning(
                "PIL/Pillow not installed. ImageView will show placeholder. "
                "Install with: pip install Pillow"
            )

    @staticmethod
    def _validate_threshold(threshold: int | str) -> int | str:
        """Normalize and validate the braille binarization threshold.

        Parameters
        ----------
        threshold : int or str
            An integer 0-255, or "auto" for Otsu's method.

        Returns
        -------
        int or str
            "auto", or the threshold clamped to 0-255.

        Raises
        ------
        ValueError
            If threshold is neither "auto" nor an integer.
        """
        if threshold == "auto":
            return "auto"
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            raise ValueError(
                f"Invalid ImageView threshold {threshold!r}. "
                'Expected an integer 0-255 or "auto".'
            )
        return max(0, min(255, int(threshold)))

    def _resolve_threshold(self, gray: Any) -> int:
        """Resolve the effective braille threshold for a grayscale image.

        Parameters
        ----------
        gray : PIL.Image.Image
            Grayscale ("L" mode) image.

        Returns
        -------
        int
            Threshold value 0-255.
        """
        if self.threshold == "auto":
            return self._otsu_threshold(gray)
        return int(self.threshold)

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

        aspect_ratio = self._aspect_ratio(img_width, img_height)

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

    def _subpixel_grid(self) -> tuple[int, int]:
        """Get the subpixel grid each character cell resolves, for the mode.

        Returns
        -------
        tuple of (int, int)
            (columns, rows) of subpixels sampled per character cell.
        """
        if self.mode == "braille":
            return (2, 4)
        if self.mode == "quadrant":
            return (2, 2)
        return (1, 2)

    def _natural_cell_pixels(self) -> tuple[int, int]:
        """Get the source pixels a cell consumes when sizing at natural scale.

        This is not the same as :meth:`_subpixel_grid`. Quadrant mode samples a
        2x2 subpixel grid, but those subpixels are not square on screen - a cell
        is twice as tall as it is wide - so at natural scale a quadrant cell
        covers a 2x4 pixel region and resamples it down. Using the sampling grid
        here instead would stretch quadrant images to double height.

        Returns
        -------
        tuple of (int, int)
            (columns, rows) of source pixels per character cell.
        """
        if self.mode == "color":
            return (1, 2)
        return (2, 4)

    def _aspect_ratio(self, img_width: int, img_height: int) -> float:
        """Get the undistorted cell aspect ratio for an image.

        This is deliberately independent of the render mode. Every mode
        resamples the whole source onto its own subpixel grid, so the subpixel
        count cancels out; all that remains is the shape of a character cell,
        which is roughly twice as tall as it is wide.

        Parameters
        ----------
        img_width : int
            Source image width in pixels.
        img_height : int
            Source image height in pixels.

        Returns
        -------
        float
            Width-to-height ratio in character cells.
        """
        return 2.0 * img_width / img_height

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
        img = self._prepare_rgb()
        if img is None:
            return []

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

    def _prepare_rgb(self) -> Any:
        """Load the image as RGB, compositing transparency over ``background``.

        Returns
        -------
        PIL.Image.Image or None
            RGB image, or None if the source could not be loaded.
        """
        img = self._load_image()
        if img is None:
            return None
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (*self.background, 255))
        return Image.alpha_composite(bg, img).convert("RGB")

    @staticmethod
    def _luminance(rgb: tuple[int, int, int]) -> float:
        """Get the Rec. 709 relative luminance of an RGB triple.

        Parameters
        ----------
        rgb : tuple of (int, int, int)
            Pixel color.

        Returns
        -------
        float
            Luminance in the range 0-255.
        """
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

    @staticmethod
    def _mean_rgb(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
        """Get the component-wise mean of a list of RGB triples.

        Parameters
        ----------
        pixels : list of tuple
            Pixel colors; must be non-empty.

        Returns
        -------
        tuple of (int, int, int)
            Mean color.
        """
        n = len(pixels)
        return (
            sum(p[0] for p in pixels) // n,
            sum(p[1] for p in pixels) // n,
            sum(p[2] for p in pixels) // n,
        )

    def _render_quadrant_mode(
        self, cols: int, rows: int
    ) -> list[list[tuple[str, tuple, tuple]]]:
        """Render the image using quadrant blocks (2x2 subpixels per cell).

        Each cell samples a 2x2 pixel block and splits it at its own mean
        luminance. The brighter subpixels become the character's set quadrants
        drawn in their mean color; the darker ones become the background. This
        is a two-color block-truncation code, so the cell stays fully covered
        and in color while resolving twice the horizontal detail of half-block
        mode.

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
        img = self._prepare_rgb()
        if img is None:
            return []

        try:
            resample = Image.Resampling.BOX
        except AttributeError:
            resample = Image.BOX  # type: ignore

        down = img.resize((cols * 2, rows * 2), resample)
        px = down.load()

        cells = []
        for y in range(rows):
            row_cells = []
            for x in range(cols):
                # Row-major order matches the QUADRANT_CHARS bitmask.
                quad = [
                    px[x * 2, y * 2],
                    px[x * 2 + 1, y * 2],
                    px[x * 2, y * 2 + 1],
                    px[x * 2 + 1, y * 2 + 1],
                ]
                lums = [self._luminance(p) for p in quad]
                pivot = sum(lums) / 4

                hi = [p for p, lu in zip(quad, lums, strict=True) if lu > pivot]
                lo = [p for p, lu in zip(quad, lums, strict=True) if lu <= pivot]

                if not hi:
                    # Flat cell: nothing above the mean, so paint it solid.
                    row_cells.append((" ", (0, 0, 0), self._mean_rgb(lo)))
                    continue

                mask = 0
                for i, lu in enumerate(lums):
                    if lu > pivot:
                        mask |= 1 << i

                bg = self._mean_rgb(lo) if lo else self._mean_rgb(hi)
                row_cells.append((self.QUADRANT_CHARS[mask], self._mean_rgb(hi), bg))
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

        # Resolve the binarization cutoff (Otsu, or a caller-supplied value)
        threshold = self._resolve_threshold(gray)

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
        aspect_ratio = self._aspect_ratio(img_width, img_height)

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
            cell_w, cell_h = self._natural_cell_pixels()
            width = img_width // cell_w
            height = img_height // cell_h

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
        render_size = (width, height, self.mode, self.threshold, self.invert)
        if self._cached_render is not None and self._last_render_size == render_size:
            cells = self._cached_render
        else:
            # Render image to cells
            if self.mode == "braille":
                cells = self._render_braille_mode(width, height)
            elif self.mode == "quadrant":
                cells = self._render_quadrant_mode(width, height)
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
