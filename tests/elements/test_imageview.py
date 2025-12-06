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
        assert iv.braille is False
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
            braille=True,
            background=(255, 255, 255),
        )
        assert iv.id == "test"
        assert iv.src == "test.png"
        assert iv.width_spec == 40
        assert iv.height_spec == 20
        assert iv.braille is True
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

    def test_braille_mode_flag(self):
        """Test braille mode flag."""
        iv_color = ImageView(braille=False)
        iv_braille = ImageView(braille=True)

        assert iv_color.braille is False
        assert iv_braille.braille is True

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

        iv = ImageView(src=img, width=5, braille=True)
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
