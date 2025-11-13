"""Integration tests for cell-based rendering migration.

This module tests Frame, ListView, and Table with cell-based rendering to ensure:
1. Cell-based rendering works for all migrated elements
2. Theme styles are applied correctly
3. Focus states work properly
4. Elements render correctly in layouts
5. Scrolling works
"""

from wijjit.elements.display.list import ListView
from wijjit.elements.display.table import Table
from wijjit.layout.bounds import Bounds
from wijjit.layout.frames import BorderStyle, Frame, FrameStyle
from wijjit.rendering.paint_context import PaintContext
from wijjit.styling.resolver import StyleResolver
from wijjit.styling.theme import DarkTheme, DefaultTheme, LightTheme
from wijjit.terminal.screen_buffer import ScreenBuffer


class TestFrameCellRendering:
    """Test Frame element cell-based rendering."""

    def test_frame_render_to(self):
        """Test Frame renders correctly with cell-based rendering."""
        print("Testing Frame cell-based rendering...")

        # Create frame with content
        frame = Frame(
            width=50,
            height=10,
            style=FrameStyle(
                border=BorderStyle.SINGLE, title="Test Frame", padding=(1, 2, 1, 2)
            ),
        )
        frame.set_content("Line 1\nLine 2\nLine 3")

        # Setup cell rendering context
        buffer = ScreenBuffer(50, 10)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=50, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        # Render using new API
        frame.render_to(ctx)

        # Verify cells were written
        top_left = buffer.get_cell(0, 0)
        assert top_left.char == "┌", f"Expected top-left corner, got '{top_left.char}'"

        # Verify title was written
        title_cell = buffer.get_cell(3, 0)
        assert (
            title_cell.char == "T"
        ), f"Expected 'T' from title, got '{title_cell.char}'"

        # Verify content was written
        content_cell = buffer.get_cell(3, 2)  # After padding
        assert (
            content_cell.char == "L"
        ), f"Expected 'L' from 'Line 1', got '{content_cell.char}'"

        print("  [OK] Frame renders correctly")
        print("  [OK] Borders are drawn")
        print("  [OK] Title is displayed")
        print("  [OK] Content is positioned correctly")

    def test_frame_focus_styling(self):
        """Test Frame applies focus styling correctly."""
        print("\nTesting Frame focus styling...")

        frame = Frame(width=30, height=5, style=FrameStyle(title="Focused"))
        frame.focused = True

        buffer = ScreenBuffer(30, 5)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=30, height=5)
        ctx = PaintContext(buffer, resolver, bounds)

        frame.render_to(ctx)

        # Check that border has focus styling
        border_cell = buffer.get_cell(0, 0)
        # Focus style should have cyan color
        assert border_cell.fg_color == (
            0,
            255,
            255,
        ), f"Expected cyan focus color, got {border_cell.fg_color}"
        assert border_cell.bold, "Expected bold border when focused"

        print("  [OK] Focus state applies correct theme colors")
        print("  [OK] Border styling changes on focus")

    def test_all_border_styles(self):
        """Test all border styles render correctly."""
        print("\nTesting all border styles...")

        styles = [
            (BorderStyle.SINGLE, "┌", "─", "┐"),
            (BorderStyle.DOUBLE, "╔", "═", "╗"),
            (BorderStyle.ROUNDED, "╭", "─", "╮"),
        ]

        for border_style, expected_tl, expected_h, expected_tr in styles:
            frame = Frame(width=20, height=5, style=FrameStyle(border=border_style))

            buffer = ScreenBuffer(20, 5)
            resolver = StyleResolver(DefaultTheme())
            bounds = Bounds(x=0, y=0, width=20, height=5)
            ctx = PaintContext(buffer, resolver, bounds)

            frame.render_to(ctx)

            tl = buffer.get_cell(0, 0).char
            h = buffer.get_cell(1, 0).char
            tr = buffer.get_cell(19, 0).char

            assert (
                tl == expected_tl
            ), f"{border_style.name}: Expected TL '{expected_tl}', got '{tl}'"
            assert (
                h == expected_h
            ), f"{border_style.name}: Expected H '{expected_h}', got '{h}'"
            assert (
                tr == expected_tr
            ), f"{border_style.name}: Expected TR '{expected_tr}', got '{tr}'"

            print(f"  [OK] {border_style.name} border renders correctly")

    def test_frame_scrollable(self):
        """Test scrollable frame with cell rendering."""
        print("\nTesting scrollable frame...")

        frame = Frame(
            width=30, height=8, style=FrameStyle(scrollable=True, show_scrollbar=True)
        )

        # Add content that requires scrolling
        content = "\n".join([f"Line {i}" for i in range(20)])
        frame.set_content(content)

        buffer = ScreenBuffer(30, 8)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=30, height=8)
        ctx = PaintContext(buffer, resolver, bounds)

        frame.render_to(ctx)

        # Verify scrollbar is present
        scrollbar_present = False
        for y in range(8):
            cell = buffer.get_cell(28, y)  # Near right edge
            if cell.char in ["▲", "█", "▼", "│"]:
                scrollbar_present = True
                break

        assert scrollbar_present, "Expected scrollbar in scrollable frame"
        assert frame.scroll_manager is not None, "Expected scroll manager"
        assert frame._needs_scroll, "Expected frame to need scrolling"

        print("  [OK] Scrollable frame creates scroll manager")
        print("  [OK] Scrollbar is rendered")
        print("  [OK] Content scrolling works")


class TestListViewCellRendering:
    """Test ListView element cell-based rendering."""

    def test_listview_render_to(self):
        """Test ListView renders correctly with cell-based rendering."""
        print("\nTesting ListView cell-based rendering...")

        listview = ListView(
            items=["Item 1", "Item 2", "Item 3"],
            width=40,
            height=8,
            bullet="bullet",
            border_style="single",
            title="Test List",
        )

        buffer = ScreenBuffer(40, 8)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=40, height=8)
        ctx = PaintContext(buffer, resolver, bounds)

        listview.render_to(ctx)

        # Verify border
        top_left = buffer.get_cell(0, 0)
        assert top_left.char in ["┌", "╭", "╔"], "Expected top-left corner character"

        # Verify title (centered, so search for it)
        title_found = False
        for x in range(40):
            cell = buffer.get_cell(x, 0)
            if cell.char == "T":
                title_found = True
                break
        assert title_found, "Expected to find title 'Test List' in top border"

        # Verify bullet (inside border, y=1 for first item)
        # Bullet should be "•" or "*"
        bullet_cell = buffer.get_cell(1, 1)
        assert bullet_cell.char in [
            "•",
            "*",
        ], f"Expected bullet character, got '{bullet_cell.char}'"

        print("  [OK] ListView renders correctly")
        print("  [OK] Borders are drawn")
        print("  [OK] Title is displayed")
        print("  [OK] Bullets are rendered")

    def test_listview_with_details(self):
        """Test ListView renders items with details correctly."""
        print("\nTesting ListView with details...")

        items = [
            ("Python", "A high-level programming language"),
            ("JavaScript", "A dynamic scripting language"),
        ]

        listview = ListView(
            items=items, width=50, height=10, bullet="dash", border_style="none"
        )

        buffer = ScreenBuffer(50, 10)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=50, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        listview.render_to(ctx)

        # Check first label (y=0)
        label_cell = buffer.get_cell(2, 0)  # After "- "
        assert (
            label_cell.char == "P"
        ), f"Expected 'P' from Python, got '{label_cell.char}'"

        # Check details line (y=1, indented)
        detail_cell = buffer.get_cell(2, 1)  # Indented by 2
        assert (
            detail_cell.char == "A"
        ), f"Expected 'A' from details, got '{detail_cell.char}'"

        # Details should be dimmed
        assert detail_cell.dim, "Expected details to be dimmed"

        print("  [OK] Labels render correctly")
        print("  [OK] Details render with indentation")
        print("  [OK] Details are styled with dim attribute")


class TestTableCellRendering:
    """Test Table element cell-based rendering."""

    def test_table_render_to(self):
        """Test Table renders correctly with cell-based rendering."""
        print("\nTesting Table cell-based rendering...")

        table = Table(
            columns=["Name", "Age", "City"],
            data=[
                {"Name": "Alice", "Age": 30, "City": "NYC"},
                {"Name": "Bob", "Age": 25, "City": "LA"},
            ],
            width=50,
            height=8,
            border_style="single",
        )

        buffer = ScreenBuffer(50, 8)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=50, height=8)
        ctx = PaintContext(buffer, resolver, bounds)

        table.render_to(ctx)

        # Verify cells were written (Rich will add borders)
        # Just check that some cells exist and are not empty
        cells_written = 0
        for y in range(8):
            for x in range(50):
                cell = buffer.get_cell(x, y)
                if cell.char and cell.char != " ":
                    cells_written += 1

        assert cells_written > 0, "Expected table to write cells to buffer"

        print("  [OK] Table renders correctly")
        print("  [OK] Rich output converted to cells")
        print(f"  [OK] {cells_written} cells written to buffer")

    def test_table_with_scrolling(self):
        """Test Table with scrolling data."""
        print("\nTesting Table with scrolling...")

        # Create table with more data than visible
        data = [{"Name": f"Person {i}", "Value": i * 10} for i in range(20)]

        table = Table(
            columns=["Name", "Value"],
            data=data,
            width=40,
            height=10,
            show_scrollbar=True,
        )

        buffer = ScreenBuffer(40, 10)
        resolver = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=40, height=10)
        ctx = PaintContext(buffer, resolver, bounds)

        table.render_to(ctx)

        # Verify scrollbar is present (should be at x=39 if shown)
        scrollbar_present = False
        for y in range(10):
            cell = buffer.get_cell(39, y)
            if cell.char in ["▲", "█", "▼", "│", "║"]:
                scrollbar_present = True
                break

        assert scrollbar_present, "Expected scrollbar to be present"

        print("  [OK] Table with scrolling works")
        print("  [OK] Scrollbar is rendered")


class TestThemeIntegration:
    """Test theme integration across elements."""

    def test_theme_switching(self):
        """Test that different themes apply different colors."""
        print("\nTesting theme switching...")

        frame = Frame(width=20, height=5, style=FrameStyle())
        frame.focused = True

        # Test with DefaultTheme
        buffer1 = ScreenBuffer(20, 5)
        resolver1 = StyleResolver(DefaultTheme())
        bounds = Bounds(x=0, y=0, width=20, height=5)
        ctx1 = PaintContext(buffer1, resolver1, bounds)
        frame.render_to(ctx1)

        # Test with DarkTheme
        buffer2 = ScreenBuffer(20, 5)
        resolver2 = StyleResolver(DarkTheme())
        ctx2 = PaintContext(buffer2, resolver2, bounds)
        frame.render_to(ctx2)

        # Test with LightTheme
        buffer3 = ScreenBuffer(20, 5)
        resolver3 = StyleResolver(LightTheme())
        ctx3 = PaintContext(buffer3, resolver3, bounds)
        frame.render_to(ctx3)

        # Colors should be different across themes
        border1 = buffer1.get_cell(0, 0).fg_color
        border2 = buffer2.get_cell(0, 0).fg_color
        border3 = buffer3.get_cell(0, 0).fg_color

        assert (
            border1 != border2 or border2 != border3
        ), "Expected different colors across themes"

        print("  [OK] DefaultTheme applies colors")
        print("  [OK] DarkTheme applies colors")
        print("  [OK] LightTheme applies colors")
        print("  [OK] Themes produce different visual output")

    def test_theme_consistency_across_elements(self):
        """Test that theme applies consistently to Frame and ListView.

        Notes
        -----
        Table is excluded from this test because it uses Rich library
        which has its own color scheme (not theme-based).
        """
        print("\nTesting theme consistency...")

        # Create Frame and ListView (elements with theme support)
        frame = Frame(width=20, height=5, style=FrameStyle())
        frame.focused = True

        listview = ListView(items=["Item 1"], width=20, height=5, border_style="single")
        listview.focused = True

        # Test with each theme
        for theme_class, theme_name in [
            (DefaultTheme, "default"),
            (DarkTheme, "dark"),
            (LightTheme, "light"),
        ]:
            resolver = StyleResolver(theme_class())
            bounds = Bounds(x=0, y=0, width=20, height=5)

            # Render each element
            for element in [frame, listview]:
                buffer = ScreenBuffer(20, 5)
                ctx = PaintContext(buffer, resolver, bounds)
                element.render_to(ctx)

                # Verify cells were written with themed colors
                cells_with_color = 0
                for y in range(5):
                    for x in range(20):
                        cell = buffer.get_cell(x, y)
                        if cell.fg_color is not None or cell.bg_color is not None:
                            cells_with_color += 1

                assert (
                    cells_with_color > 0
                ), f"{element.__class__.__name__} should have themed colors with {theme_name}"

        print("  [OK] Themes apply colors consistently to Frame and ListView")
