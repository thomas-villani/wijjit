"""Tests for dirty region tracking."""


from wijjit.layout.bounds import Bounds
from wijjit.layout.dirty import DirtyRegion, DirtyRegionManager


class TestDirtyRegion:
    """Tests for DirtyRegion class."""

    def test_create_region(self):
        """Test creating a dirty region."""
        region = DirtyRegion(x=10, y=20, width=30, height=40)
        assert region.x == 10
        assert region.y == 20
        assert region.width == 30
        assert region.height == 40

    def test_right_property(self):
        """Test right edge calculation."""
        region = DirtyRegion(x=10, y=20, width=30, height=40)
        assert region.right == 40  # 10 + 30

    def test_bottom_property(self):
        """Test bottom edge calculation."""
        region = DirtyRegion(x=10, y=20, width=30, height=40)
        assert region.bottom == 60  # 20 + 40

    def test_area_property(self):
        """Test area calculation."""
        region = DirtyRegion(x=0, y=0, width=10, height=20)
        assert region.area == 200  # 10 * 20

    def test_overlaps_true(self):
        """Test overlapping regions."""
        region1 = DirtyRegion(x=10, y=10, width=20, height=20)
        region2 = DirtyRegion(x=20, y=20, width=20, height=20)
        assert region1.overlaps(region2)
        assert region2.overlaps(region1)

    def test_overlaps_false(self):
        """Test non-overlapping regions."""
        region1 = DirtyRegion(x=10, y=10, width=10, height=10)
        region2 = DirtyRegion(x=30, y=30, width=10, height=10)
        assert not region1.overlaps(region2)
        assert not region2.overlaps(region1)

    def test_overlaps_touching(self):
        """Test regions that touch but don't overlap."""
        region1 = DirtyRegion(x=10, y=10, width=10, height=10)
        region2 = DirtyRegion(x=20, y=10, width=10, height=10)
        assert not region1.overlaps(region2)

    def test_is_adjacent_horizontal(self):
        """Test horizontal adjacency."""
        region1 = DirtyRegion(x=10, y=10, width=10, height=20)
        region2 = DirtyRegion(x=20, y=10, width=10, height=20)
        assert region1.is_adjacent(region2)
        assert region2.is_adjacent(region1)

    def test_is_adjacent_vertical(self):
        """Test vertical adjacency."""
        region1 = DirtyRegion(x=10, y=10, width=20, height=10)
        region2 = DirtyRegion(x=10, y=20, width=20, height=10)
        assert region1.is_adjacent(region2)
        assert region2.is_adjacent(region1)

    def test_is_adjacent_false(self):
        """Test non-adjacent regions."""
        region1 = DirtyRegion(x=10, y=10, width=10, height=10)
        region2 = DirtyRegion(x=30, y=30, width=10, height=10)
        assert not region1.is_adjacent(region2)

    def test_is_adjacent_different_sizes(self):
        """Test adjacency with different row/column ranges."""
        region1 = DirtyRegion(x=10, y=10, width=10, height=10)
        region2 = DirtyRegion(x=20, y=15, width=10, height=20)
        assert not region1.is_adjacent(region2)

    def test_merge_overlapping(self):
        """Test merging overlapping regions."""
        region1 = DirtyRegion(x=10, y=10, width=20, height=20)
        region2 = DirtyRegion(x=20, y=20, width=20, height=20)
        merged = region1.merge(region2)
        assert merged.x == 10
        assert merged.y == 10
        assert merged.width == 30  # Spans from x=10 to x=40
        assert merged.height == 30  # Spans from y=10 to y=40

    def test_merge_adjacent(self):
        """Test merging adjacent regions."""
        region1 = DirtyRegion(x=10, y=10, width=10, height=20)
        region2 = DirtyRegion(x=20, y=10, width=10, height=20)
        merged = region1.merge(region2)
        assert merged.x == 10
        assert merged.y == 10
        assert merged.width == 20
        assert merged.height == 20

    def test_merge_non_overlapping(self):
        """Test merging creates bounding box for non-overlapping regions."""
        region1 = DirtyRegion(x=10, y=10, width=10, height=10)
        region2 = DirtyRegion(x=30, y=30, width=10, height=10)
        merged = region1.merge(region2)
        # Should create bounding box from (10,10) to (40,40)
        assert merged.x == 10
        assert merged.y == 10
        assert merged.width == 30
        assert merged.height == 30


class TestDirtyRegionManager:
    """Tests for DirtyRegionManager class."""

    def test_create_manager(self):
        """Test creating a dirty region manager."""
        manager = DirtyRegionManager()
        assert not manager.is_dirty()
        assert not manager.is_full_screen_dirty()
        assert manager.get_merged_regions() == []

    def test_mark_dirty_single_region(self):
        """Test marking a single region as dirty."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 20, 30, 40)
        assert manager.is_dirty()
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        assert regions[0] == (10, 20, 30, 40)

    def test_mark_dirty_multiple_non_overlapping(self):
        """Test marking multiple non-overlapping regions."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, 10, 10)
        manager.mark_dirty(30, 30, 10, 10)
        assert manager.is_dirty()
        regions = manager.get_merged_regions()
        assert len(regions) == 2

    def test_mark_dirty_overlapping_merges(self):
        """Test that overlapping regions are merged."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, 20, 20)
        manager.mark_dirty(20, 20, 20, 20)
        assert manager.is_dirty()
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        # Should be merged into one region
        x, y, w, h = regions[0]
        assert x == 10
        assert y == 10
        assert w == 30
        assert h == 30

    def test_mark_dirty_adjacent_merges(self):
        """Test that adjacent regions are merged."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, 10, 20)
        manager.mark_dirty(20, 10, 10, 20)
        assert manager.is_dirty()
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        # Should be merged into one region
        x, y, w, h = regions[0]
        assert x == 10
        assert y == 10
        assert w == 20
        assert h == 20

    def test_mark_dirty_cascade_merging(self):
        """Test that multiple regions cascade merge."""
        manager = DirtyRegionManager()
        # Add three adjacent regions
        manager.mark_dirty(0, 0, 10, 10)
        manager.mark_dirty(10, 0, 10, 10)
        manager.mark_dirty(20, 0, 10, 10)
        # All should merge into one
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        x, y, w, h = regions[0]
        assert x == 0
        assert y == 0
        assert w == 30
        assert h == 10

    def test_mark_dirty_bounds(self):
        """Test marking dirty using Bounds object."""
        manager = DirtyRegionManager()
        bounds = Bounds(x=10, y=20, width=30, height=40)
        manager.mark_dirty_bounds(bounds)
        assert manager.is_dirty()
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        assert regions[0] == (10, 20, 30, 40)

    def test_mark_dirty_zero_width(self):
        """Test that zero width regions are ignored."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, 0, 10)
        assert not manager.is_dirty()

    def test_mark_dirty_zero_height(self):
        """Test that zero height regions are ignored."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, 10, 0)
        assert not manager.is_dirty()

    def test_mark_dirty_negative_dimensions(self):
        """Test that negative dimensions are ignored."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, -10, 10)
        assert not manager.is_dirty()
        manager.mark_dirty(10, 10, 10, -10)
        assert not manager.is_dirty()

    def test_mark_full_screen(self):
        """Test marking full screen as dirty."""
        manager = DirtyRegionManager()
        manager.mark_full_screen(80, 24)
        assert manager.is_dirty()
        assert manager.is_full_screen_dirty()
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        assert regions[0] == (0, 0, 80, 24)

    def test_mark_full_screen_clears_regions(self):
        """Test that marking full screen clears individual regions."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, 10, 10)
        manager.mark_dirty(30, 30, 10, 10)
        manager.mark_full_screen(80, 24)
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        assert regions[0] == (0, 0, 80, 24)

    def test_mark_dirty_after_full_screen(self):
        """Test that marking dirty after full screen has no effect."""
        manager = DirtyRegionManager()
        manager.mark_full_screen(80, 24)
        manager.mark_dirty(10, 10, 10, 10)
        # Should still just have full screen
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        assert regions[0] == (0, 0, 80, 24)

    def test_clear(self):
        """Test clearing dirty regions."""
        manager = DirtyRegionManager()
        manager.mark_dirty(10, 10, 10, 10)
        manager.mark_dirty(30, 30, 10, 10)
        assert manager.is_dirty()
        manager.clear()
        assert not manager.is_dirty()
        assert manager.get_merged_regions() == []

    def test_clear_full_screen(self):
        """Test clearing full screen dirty state."""
        manager = DirtyRegionManager()
        manager.mark_full_screen(80, 24)
        assert manager.is_full_screen_dirty()
        manager.clear()
        assert not manager.is_full_screen_dirty()
        assert not manager.is_dirty()

    def test_complex_merging_scenario(self):
        """Test complex scenario with multiple merges."""
        manager = DirtyRegionManager()
        # Create a pattern that requires multiple merge passes
        manager.mark_dirty(0, 0, 10, 10)
        manager.mark_dirty(20, 0, 10, 10)
        manager.mark_dirty(10, 0, 10, 10)  # Bridge between first two
        # All three should merge
        regions = manager.get_merged_regions()
        assert len(regions) == 1
        x, y, w, h = regions[0]
        assert x == 0
        assert y == 0
        assert w == 30
        assert h == 10

    def test_repr(self):
        """Test string representation."""
        manager = DirtyRegionManager()
        assert "DirtyRegionManager" in repr(manager)
        manager.mark_dirty(10, 10, 10, 10)
        assert "1 region" in repr(manager)
        manager.mark_full_screen(80, 24)
        assert "full_screen" in repr(manager)
        assert "80x24" in repr(manager)
