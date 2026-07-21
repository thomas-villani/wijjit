"""Tests for ImageView element.

This module tests the ImageView element including:
- Initialization with various parameters
- PIL availability handling
- Image loading from different sources
- Color mode rendering (half-block characters)
- Braille mode rendering
- Sizing calculations (width-only, height-only, both, fill, %)
- Error handling (missing file, corrupted image)
"""

from io import BytesIO
from unittest.mock import patch

import pytest

from tests.helpers import render_element
from wijjit.elements.display.image import PIL_AVAILABLE, ImageView
from wijjit.layout.bounds import Bounds


class TestImageViewInitialization:
    """Test ImageView initialization."""

    def test_default_initialization(self):
        """Test ImageView with default parameters."""
        iv = ImageView()
        assert iv.src is None
        assert iv.mode == "color"
        assert iv.threshold == "auto"
        assert iv.background == (0, 0, 0)
        assert iv.focusable is False
        assert iv.width_spec is None
        assert iv.height_spec is None

    def test_custom_initialization(self):
        """Test ImageView with custom parameters."""
        iv = ImageView(
            id="test",
            src="test.png",
            width=40,
            height=20,
            mode="braille",
            threshold=90,
            background=(255, 255, 255),
        )
        assert iv.id == "test"
        assert iv.src == "test.png"
        assert iv.width_spec == 40
        assert iv.height_spec == 20
        assert iv.mode == "braille"
        assert iv.threshold == 90
        assert iv.background == (255, 255, 255)

    def test_string_sizing_specs(self):
        """Test ImageView with string sizing specs."""
        iv = ImageView(width="fill", height="auto")
        assert iv.width_spec == "fill"
        assert iv.height_spec == "auto"

    def test_percentage_sizing_specs(self):
        """Test ImageView with percentage sizing specs."""
        iv = ImageView(width="50%", height="75%")
        assert iv.width_spec == "50%"
        assert iv.height_spec == "75%"


class TestImageViewSizeSpec:
    """Test size specification parsing."""

    def test_parse_size_spec_none(self):
        """Test parsing None size spec."""
        iv = ImageView()
        result = iv._parse_size_spec(None, 100)
        assert result is None

    def test_parse_size_spec_auto(self):
        """Test parsing 'auto' size spec."""
        iv = ImageView()
        result = iv._parse_size_spec("auto", 100)
        assert result is None

    def test_parse_size_spec_fill(self):
        """Test parsing 'fill' size spec."""
        iv = ImageView()
        result = iv._parse_size_spec("fill", 100)
        assert result == 100

    def test_parse_size_spec_int(self):
        """Test parsing integer size spec."""
        iv = ImageView()
        result = iv._parse_size_spec(50, 100)
        assert result == 50

    def test_parse_size_spec_percentage(self):
        """Test parsing percentage size spec."""
        iv = ImageView()
        result = iv._parse_size_spec("50%", 100)
        assert result == 50

        result = iv._parse_size_spec("25%", 80)
        assert result == 20


class TestImageViewIntrinsicSize:
    """Test intrinsic size calculations."""

    def test_intrinsic_size_no_image(self):
        """Test intrinsic size when no image is loaded."""
        iv = ImageView()
        size = iv.get_intrinsic_size()
        # Default placeholder size
        assert size == (10, 5)

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
    def test_intrinsic_size_with_image_and_width_spec(self):
        """Test intrinsic size with image and width specified."""
        from PIL import Image

        # Create test image
        img = Image.new("RGB", (100, 50), (255, 255, 255))
        iv = ImageView(src=img, width=30)
        size = iv.get_intrinsic_size()
        # When width is specified as int, intrinsic size respects it
        assert size[0] == 30


class TestImageViewCaching:
    """Test caching functionality."""

    def test_set_src_invalidates_cache(self):
        """Test that changing src invalidates cache."""
        iv = ImageView(src="original.png")
        iv._cached_image = "cached"
        iv._cached_render = "cached_render"
        iv._last_render_size = (10, 10, False)

        iv.set_src("new.png")

        assert iv.src == "new.png"
        assert iv._cached_image is None
        assert iv._cached_render is None
        assert iv._last_render_size is None

    def test_invalidate_cache(self):
        """Test explicit cache invalidation."""
        iv = ImageView()
        iv._cached_image = "cached"
        iv._cached_render = "cached_render"
        iv._last_render_size = (10, 10, False)

        iv.invalidate_cache()

        assert iv._cached_image is None
        assert iv._cached_render is None
        assert iv._last_render_size is None


class TestImageViewPlaceholder:
    """Test placeholder rendering."""

    def test_render_placeholder_no_pil(self):
        """Test rendering placeholder when PIL not available."""
        with patch("wijjit.elements.display.image.PIL_AVAILABLE", False):
            iv = ImageView(src="test.png")
            iv.set_bounds(Bounds(0, 0, 20, 5))
            output = render_element(iv, width=20, height=5)
            # Should contain placeholder message
            assert len(output) > 0

    def test_render_placeholder_no_source(self):
        """Test rendering placeholder when no source provided."""
        iv = ImageView()
        iv.set_bounds(Bounds(0, 0, 20, 5))
        output = render_element(iv, width=20, height=5)
        # Should contain placeholder
        assert len(output) > 0


class TestImageViewBrailleMode:
    """Test braille mode functionality."""

    def test_mode_selection(self):
        """Test selecting each render mode."""
        assert ImageView(mode="color").mode == "color"
        assert ImageView(mode="quadrant").mode == "quadrant"
        assert ImageView(mode="braille").mode == "braille"

    def test_braille_dots_constant(self):
        """Test braille dots mapping constant."""
        # Verify the braille dot mapping is correct
        # 8 dots in a 2x4 grid
        assert len(ImageView.BRAILLE_DOTS) == 8

        # Each entry should be (dx, dy, bit_index)
        for dot in ImageView.BRAILLE_DOTS:
            assert len(dot) == 3
            dx, dy, bit = dot
            assert 0 <= dx <= 1
            assert 0 <= dy <= 3
            assert 0 <= bit <= 7

    def test_braille_base_constant(self):
        """Test braille base Unicode constant."""
        assert ImageView.BRAILLE_BASE == 0x2800


class TestImageViewColorMode:
    """Test color mode functionality."""

    def test_half_block_constant(self):
        """Test half-block character constant."""
        assert ImageView.HALF_BLOCK == "\u2580"


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestImageViewWithPIL:
    """Tests that require PIL to be installed."""

    def test_load_image_from_bytes(self):
        """Test loading image from bytes."""
        from PIL import Image

        # Create a simple 10x10 red image
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        iv = ImageView(src=img_bytes)
        loaded = iv._load_image()

        assert loaded is not None
        assert loaded.size == (10, 10)

    def test_load_image_from_pil_image(self):
        """Test loading image from PIL Image object."""
        from PIL import Image

        # Create a simple 10x10 green image
        img = Image.new("RGB", (10, 10), (0, 255, 0))

        iv = ImageView(src=img)
        loaded = iv._load_image()

        assert loaded is not None
        assert loaded.size == (10, 10)

    def test_load_image_caching(self):
        """Test that loaded image is cached."""
        from PIL import Image

        img = Image.new("RGB", (10, 10), (0, 0, 255))

        iv = ImageView(src=img)
        loaded1 = iv._load_image()
        loaded2 = iv._load_image()

        # Should return cached image
        assert loaded1 is loaded2

    def test_calculate_dimensions_width_only(self):
        """Test dimension calculation with width only."""
        from PIL import Image

        # Create 100x50 image (2:1 aspect ratio)
        img = Image.new("RGB", (100, 50), (255, 255, 255))

        iv = ImageView(src=img, width=20)
        width, height = iv._calculate_dimensions(80, 40)

        # Width should be 20, height calculated from aspect
        assert width == 20
        # Height depends on aspect ratio calculation

    def test_calculate_dimensions_height_only(self):
        """Test dimension calculation with height only."""
        from PIL import Image

        img = Image.new("RGB", (100, 50), (255, 255, 255))

        iv = ImageView(src=img, height=10)
        width, height = iv._calculate_dimensions(80, 40)

        # Height should be 10, width calculated from aspect
        assert height == 10

    def test_otsu_threshold(self):
        """Test Otsu's threshold calculation."""
        from PIL import Image

        # Create bimodal image with values around 50 and 200
        # This creates a more realistic test case for Otsu's method
        img = Image.new("L", (100, 100))
        for x in range(100):
            for y in range(100):
                if x < 50:
                    img.putpixel((x, y), 50)  # Dark gray
                else:
                    img.putpixel((x, y), 200)  # Light gray

        iv = ImageView()
        threshold = iv._otsu_threshold(img)

        # Threshold should be between the two modes (50 and 200)
        assert 50 <= threshold <= 200

    def test_render_color_mode_simple(self):
        """Test color mode rendering produces output."""
        from PIL import Image

        # Create simple test image
        img = Image.new("RGB", (10, 20), (128, 128, 128))

        iv = ImageView(src=img, width=5)
        iv.set_bounds(Bounds(0, 0, 10, 10))
        output = render_element(iv, width=10, height=10)

        # Should produce non-empty output
        assert len(output) > 0

    def test_render_braille_mode_simple(self):
        """Test braille mode rendering produces output."""
        from PIL import Image

        # Create simple test image
        img = Image.new("RGB", (20, 40), (255, 255, 255))

        iv = ImageView(src=img, width=5, mode="braille")
        iv.set_bounds(Bounds(0, 0, 10, 10))
        output = render_element(iv, width=10, height=10)

        # Should produce non-empty output with braille characters
        assert len(output) > 0


class TestImageViewErrorHandling:
    """Test error handling."""

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file returns None."""
        iv = ImageView(src="/nonexistent/path/to/image.png")
        loaded = iv._load_image()
        assert loaded is None

    def test_load_unsupported_source_type(self):
        """Test loading unsupported source type."""
        iv = ImageView(src=12345)  # Invalid source type
        loaded = iv._load_image()
        assert loaded is None

    def test_load_none_source(self):
        """Test loading None source."""
        iv = ImageView(src=None)
        loaded = iv._load_image()
        assert loaded is None


class TestImageViewModeValidation:
    """Test validation of the mode and threshold props."""

    def test_invalid_mode_raises(self):
        """Test an unknown mode is rejected at construction."""
        with pytest.raises(ValueError, match="Invalid ImageView mode"):
            ImageView(mode="sextant")

    def test_all_declared_modes_are_constructible(self):
        """Test every mode in MODES can actually be constructed."""
        for mode in ImageView.MODES:
            assert ImageView(mode=mode).mode == mode

    def test_threshold_auto_default(self):
        """Test threshold defaults to automatic Otsu."""
        assert ImageView().threshold == "auto"

    def test_threshold_is_clamped(self):
        """Test out-of-range thresholds clamp to 0-255."""
        assert ImageView(threshold=-20).threshold == 0
        assert ImageView(threshold=900).threshold == 255

    def test_invalid_threshold_raises(self):
        """Test a non-numeric, non-auto threshold is rejected."""
        with pytest.raises(ValueError, match="Invalid ImageView threshold"):
            ImageView(threshold="otsu")


class TestImageViewQuadrantMode:
    """Test quadrant mode rendering."""

    def test_quadrant_chars_table(self):
        """Test the quadrant table covers all 16 subpixel patterns uniquely."""
        assert len(ImageView.QUADRANT_CHARS) == 16
        assert len(set(ImageView.QUADRANT_CHARS)) == 16
        # Row-major bitmask: bit0=TL, bit1=TR, bit2=BL, bit3=BR.
        assert ImageView.QUADRANT_CHARS[0] == " "
        assert ImageView.QUADRANT_CHARS[0b0011] == "▀"  # top row -> upper half
        assert ImageView.QUADRANT_CHARS[0b1100] == "▄"  # bottom row -> lower half
        assert ImageView.QUADRANT_CHARS[0b0101] == "▌"  # left col -> left half
        assert ImageView.QUADRANT_CHARS[0b1010] == "▐"  # right col -> right half
        assert ImageView.QUADRANT_CHARS[0b1111] == "█"  # all -> full block

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")
    def test_quadrant_render_is_full_coverage_and_colored(self):
        """Test quadrant cells keep color, unlike monochrome braille."""
        from PIL import Image

        # Left half red, right half blue - a vertical edge inside every cell.
        img = Image.new("RGB", (8, 8), (255, 0, 0))
        for y in range(8):
            for x in range(4, 8):
                img.putpixel((x, y), (0, 0, 255))

        iv = ImageView(src=img, mode="quadrant")
        cells = iv._render_quadrant_mode(4, 4)

        assert len(cells) == 4
        assert all(len(row) == 4 for row in cells)
        # Every cell carries both a foreground and a background color.
        for row in cells:
            for char, fg, bg in row:
                assert char in ImageView.QUADRANT_CHARS
                assert bg is not None
                assert fg is not None
        # The red/blue split must survive somewhere in the output.
        colors = {c for row in cells for _, fg, bg in row for c in (fg, bg)}
        assert any(c[0] > c[2] for c in colors), "expected a red-dominant color"
        assert any(c[2] > c[0] for c in colors), "expected a blue-dominant color"

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")
    def test_flat_image_renders_solid(self):
        """Test a flat cell paints solid rather than emitting a split pattern."""
        from PIL import Image

        img = Image.new("RGB", (8, 8), (120, 120, 120))
        cells = ImageView(src=img, mode="quadrant")._render_quadrant_mode(4, 4)

        for row in cells:
            for char, _fg, bg in row:
                assert char == " "
                assert bg == (120, 120, 120)


class TestImageViewThresholdBehavior:
    """Test that an explicit braille threshold actually changes the output."""

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")
    def test_threshold_changes_dot_count(self):
        """Test a high threshold yields fewer dots than a low one."""
        from PIL import Image

        # Vertical luminance ramp so the cutoff position matters.
        img = Image.new("RGB", (16, 32))
        for y in range(32):
            v = int(y * 255 / 31)
            for x in range(16):
                img.putpixel((x, y), (v, v, v))

        def dot_count(threshold):
            iv = ImageView(src=img, mode="braille", threshold=threshold)
            cells = iv._render_braille_mode(8, 8)
            return sum(
                bin(ord(char) - ImageView.BRAILLE_BASE).count("1")
                for row in cells
                for char, _fg, _bg in row
            )

        assert dot_count(40) > dot_count(200)

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")
    def test_auto_threshold_matches_otsu(self):
        """Test "auto" resolves to the Otsu threshold."""
        from PIL import Image

        img = Image.new("RGB", (16, 16), (10, 10, 10))
        for y in range(8):
            for x in range(16):
                img.putpixel((x, y), (240, 240, 240))

        iv = ImageView(src=img, mode="braille")
        gray = img.convert("L")
        assert iv._resolve_threshold(gray) == iv._otsu_threshold(gray)


class TestImageViewModeGeometry:
    """Test each mode reports the subpixel grid its aspect math depends on."""

    def test_subpixel_grids(self):
        """Test the subpixel grid per mode."""
        assert ImageView(mode="color")._subpixel_grid() == (1, 2)
        assert ImageView(mode="quadrant")._subpixel_grid() == (2, 2)
        assert ImageView(mode="braille")._subpixel_grid() == (2, 4)

    def test_aspect_ratio_is_mode_independent(self):
        """Test aspect ratio does not depend on the subpixel grid.

        Each mode resamples the whole source onto its own grid, so the subpixel
        count cancels out and only the 2:1 character cell shape matters. Making
        this grid-dependent stretched quadrant images to double height.
        """
        for mode in ImageView.MODES:
            iv = ImageView(mode=mode)
            assert iv._aspect_ratio(100, 100) == 2.0
            assert iv._aspect_ratio(200, 100) == 4.0
            assert iv._aspect_ratio(100, 200) == 1.0

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")
    def test_natural_size_preserves_aspect_across_modes(self):
        """Test unconstrained sizing gives the same shape in every mode."""
        from PIL import Image

        img = Image.new("RGB", (128, 128))
        shapes = {}
        for mode in ImageView.MODES:
            width, height = ImageView(src=img, mode=mode).get_intrinsic_size()
            shapes[mode] = width / height

        assert set(shapes.values()) == {2.0}, shapes

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")
    def test_width_constrained_height_matches_across_modes(self):
        """Test a fixed width yields the same height in every mode."""
        from PIL import Image

        img = Image.new("RGB", (100, 100))
        heights = {
            mode: ImageView(src=img, mode=mode, width=40)._calculate_dimensions(80, 80)[
                1
            ]
            for mode in ImageView.MODES
        }
        assert len(set(heights.values())) == 1, heights
        assert heights["quadrant"] == 20
