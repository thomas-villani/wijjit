"""Tests for bounds and size utilities."""

import pytest

from wijjit.layout.bounds import Bounds, Size, parse_size


class TestBounds:
    """Tests for Bounds class."""

    def test_create_bounds(self):
        """Test creating bounds."""
        bounds = Bounds(x=10, y=20, width=30, height=40)
        assert bounds.x == 10
        assert bounds.y == 20
        assert bounds.width == 30
        assert bounds.height == 40

    def test_right_property(self):
        """Test right edge calculation."""
        bounds = Bounds(x=10, y=20, width=30, height=40)
        assert bounds.right == 40  # 10 + 30

    def test_bottom_property(self):
        """Test bottom edge calculation."""
        bounds = Bounds(x=10, y=20, width=30, height=40)
        assert bounds.bottom == 60  # 20 + 40

    def test_area_property(self):
        """Test area calculation."""
        bounds = Bounds(x=0, y=0, width=10, height=20)
        assert bounds.area == 200  # 10 * 20

    def test_contains_point_inside(self):
        """Test point containment check - inside."""
        bounds = Bounds(x=10, y=20, width=30, height=40)
        assert bounds.contains(15, 25)
        assert bounds.contains(10, 20)  # Top-left corner

    def test_contains_point_outside(self):
        """Test point containment check - outside."""
        bounds = Bounds(x=10, y=20, width=30, height=40)
        assert not bounds.contains(5, 25)
        assert not bounds.contains(50, 25)
        assert not bounds.contains(15, 15)
        assert not bounds.contains(15, 70)

    def test_contains_point_edge(self):
        """Test point containment on edges."""
        bounds = Bounds(x=10, y=20, width=30, height=40)
        # Right and bottom edges are exclusive
        assert not bounds.contains(40, 30)  # Right edge
        assert not bounds.contains(15, 60)  # Bottom edge

    def test_overlaps_true(self):
        """Test overlapping bounds."""
        bounds1 = Bounds(x=10, y=10, width=20, height=20)
        bounds2 = Bounds(x=20, y=20, width=20, height=20)
        assert bounds1.overlaps(bounds2)
        assert bounds2.overlaps(bounds1)

    def test_overlaps_false(self):
        """Test non-overlapping bounds."""
        bounds1 = Bounds(x=10, y=10, width=10, height=10)
        bounds2 = Bounds(x=30, y=30, width=10, height=10)
        assert not bounds1.overlaps(bounds2)
        assert not bounds2.overlaps(bounds1)

    def test_overlaps_touching(self):
        """Test bounds that touch but don't overlap."""
        bounds1 = Bounds(x=10, y=10, width=10, height=10)
        bounds2 = Bounds(x=20, y=10, width=10, height=10)  # Touching right edge
        assert not bounds1.overlaps(bounds2)


class TestSize:
    """Tests for Size class."""

    def test_fixed_size(self):
        """Test fixed size."""
        size = Size(50)
        assert size.is_fixed
        assert not size.is_fill
        assert not size.is_percentage

    def test_fill_size(self):
        """Test fill size."""
        size = Size("fill")
        assert not size.is_fixed
        assert size.is_fill
        assert not size.is_percentage

    def test_percentage_size(self):
        """Test percentage size."""
        size = Size("50%")
        assert not size.is_fixed
        assert not size.is_fill
        assert size.is_percentage

    def test_100_percent_is_fill(self):
        """Test that 100% is treated as fill."""
        size = Size("100%")
        assert size.is_fill
        assert size.is_percentage

    def test_get_percentage(self):
        """Test getting percentage value."""
        size = Size("75%")
        assert size.get_percentage() == 0.75

    def test_get_percentage_error(self):
        """Test getting percentage from non-percentage raises error."""
        size = Size(50)
        with pytest.raises(ValueError):
            size.get_percentage()

    def test_calculate_fixed(self):
        """Test calculating fixed size."""
        size = Size(50)
        assert size.calculate(100) == 50
        assert size.calculate(30) == 30  # Clamped to available

    def test_calculate_percentage(self):
        """Test calculating percentage size."""
        size = Size("50%")
        assert size.calculate(100) == 50

        size2 = Size("75%")
        assert size2.calculate(200) == 150

    def test_calculate_fill(self):
        """Test calculating fill size."""
        size = Size("fill")
        assert size.calculate(100) == 100
        assert size.calculate(500) == 500


class TestParseSize:
    """Tests for parse_size function."""

    def test_parse_int(self):
        """Test parsing integer."""
        size = parse_size(50)
        assert isinstance(size, Size)
        assert size.value == 50

    def test_parse_string(self):
        """Test parsing string."""
        size = parse_size("fill")
        assert isinstance(size, Size)
        assert size.value == "fill"

    def test_parse_size_object(self):
        """Test parsing Size object."""
        original = Size(100)
        size = parse_size(original)
        assert size is original
