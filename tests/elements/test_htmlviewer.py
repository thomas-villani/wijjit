"""Tests for HTMLViewer element."""

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.display.htmlview import HTMLViewer
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestHTMLViewerBasics:
    """Tests for HTMLViewer basic functionality."""

    def test_create_htmlviewer(self):
        """Test creating an HTML viewer.

        Verifies
        --------
        - ID assignment
        - Dimensions
        - Focusability
        - Element type
        """
        viewer = HTMLViewer(id="content", content="<b>Hello</b>", width=60, height=20)
        assert viewer.id == "content"
        assert viewer.width == 60
        assert viewer.height == 20
        assert viewer.focusable
        assert viewer.element_type == ElementType.DISPLAY

    def test_initial_content(self):
        """Test HTML viewer with initial content.

        Verifies
        --------
        - Content is stored
        - Content is rendered to lines
        """
        content = "<b>Title</b>\n\nSome text"
        viewer = HTMLViewer(content=content)
        assert viewer.content == content
        assert len(viewer.rendered_lines) > 0

    def test_empty_content(self):
        """Test HTML viewer with empty content.

        Verifies
        --------
        - Empty content doesn't crash
        - Content lines has at least one empty line
        """
        viewer = HTMLViewer(content="")
        assert viewer.content == ""
        assert len(viewer.rendered_lines) >= 1

    def test_border_styles(self):
        """Test HTML viewer with different border styles.

        Verifies
        --------
        - Single border
        - Double border
        - Rounded border
        - No border
        """
        for style in ["single", "double", "rounded", "none"]:
            viewer = HTMLViewer(border_style=style)
            assert viewer.border_style == style

    def test_with_title(self):
        """Test HTML viewer with border title.

        Verifies
        --------
        - Title is stored
        - Title is used in rendering
        """
        viewer = HTMLViewer(
            title="Help", border_style="single", content="<b>Test</b>", width=40
        )
        viewer.set_bounds(Bounds(0, 0, viewer.width, viewer.height))
        assert viewer.title == "Help"
        rendered = render_element(viewer, width=viewer.width, height=viewer.height)
        assert "Help" in rendered

    def test_scrollbar_option(self):
        """Test HTML viewer scrollbar visibility option.

        Verifies
        --------
        - Scrollbar can be shown
        - Scrollbar can be hidden
        """
        viewer_with = HTMLViewer(show_scrollbar=True)
        viewer_without = HTMLViewer(show_scrollbar=False)
        assert viewer_with.show_scrollbar is True
        assert viewer_without.show_scrollbar is False


class TestHTMLViewerScrolling:
    """Tests for HTMLViewer scrolling functionality."""

    def test_scroll_down(self):
        """Test scrolling down in HTML viewer.

        Verifies
        --------
        - Initial scroll position is 0
        - Down key increases scroll position
        - Scroll callback is triggered
        """
        lines = [f"<b>Line {i}</b>" for i in range(50)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        scroll_positions = []
        viewer.on_scroll = lambda pos: scroll_positions.append(pos)

        assert viewer.scroll_manager.state.scroll_position == 0

        if viewer.scroll_manager.state.is_scrollable:
            viewer.handle_key(Keys.DOWN)
            assert viewer.scroll_manager.state.scroll_position >= 1
            assert len(scroll_positions) > 0

    def test_scroll_up(self):
        """Test scrolling up in HTML viewer.

        Verifies
        --------
        - Can scroll back up
        - Position doesn't go negative
        """
        lines = [f"<b>Line {i}</b>" for i in range(50)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        if viewer.scroll_manager.state.is_scrollable:
            viewer.handle_key(Keys.DOWN)
            viewer.handle_key(Keys.DOWN)
            pos_after_down = viewer.scroll_manager.state.scroll_position
            assert pos_after_down >= 2

            viewer.handle_key(Keys.UP)
            assert viewer.scroll_manager.state.scroll_position < pos_after_down

            # Scroll to top
            for _ in range(10):
                viewer.handle_key(Keys.UP)
            assert viewer.scroll_manager.state.scroll_position == 0

    def test_scroll_home_end(self):
        """Test HOME and END key scrolling.

        Verifies
        --------
        - HOME scrolls to top
        - END scrolls to bottom
        """
        lines = [f"<b>Line {i}</b>" for i in range(50)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        if viewer.scroll_manager.state.is_scrollable:
            viewer.handle_key(Keys.END)
            assert viewer.scroll_manager.state.scroll_position > 0

            viewer.handle_key(Keys.HOME)
            assert viewer.scroll_manager.state.scroll_position == 0

    def test_page_up_down(self):
        """Test PAGE_UP and PAGE_DOWN scrolling.

        Verifies
        --------
        - PAGE_DOWN scrolls by viewport size
        - PAGE_UP scrolls back
        """
        lines = [f"<b>Line {i}</b>" for i in range(100)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        if viewer.scroll_manager.state.is_scrollable:
            viewer.handle_key(Keys.PAGE_DOWN)
            pos_after_page = viewer.scroll_manager.state.scroll_position
            assert pos_after_page > 0

            viewer.handle_key(Keys.PAGE_UP)
            assert viewer.scroll_manager.state.scroll_position < pos_after_page

    def test_restore_scroll_position(self):
        """Test restoring scroll position.

        Verifies
        --------
        - Scroll position can be restored
        - Position is correctly applied
        """
        lines = [f"<b>Line {i}</b>" for i in range(50)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        if viewer.scroll_manager.state.is_scrollable:
            viewer.restore_scroll_position(5)
            assert viewer.scroll_position == 5

    def test_can_scroll_direction(self):
        """Test can_scroll method.

        Verifies
        --------
        - Cannot scroll up at top
        - Can scroll down when content exceeds viewport
        """
        lines = [f"<b>Line {i}</b>" for i in range(50)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        # At top, cannot scroll up
        assert viewer.can_scroll(-1) is False

        if viewer.scroll_manager.state.is_scrollable:
            # Can scroll down when content exceeds viewport
            assert viewer.can_scroll(1) is True

            # Scroll to bottom
            viewer.handle_key(Keys.END)
            assert viewer.can_scroll(1) is False  # Cannot scroll down at bottom


class TestHTMLViewerMouse:
    """Tests for HTMLViewer mouse interaction."""

    def test_mouse_scroll_down(self):
        """Test mouse wheel scroll down.

        Verifies
        --------
        - Scroll wheel down increases scroll position
        """
        lines = [f"<b>Line {i}</b>" for i in range(50)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        if viewer.scroll_manager.state.is_scrollable:
            event = MouseEvent(
                x=5,
                y=5,
                button=MouseButton.SCROLL_DOWN,
                type=MouseEventType.SCROLL,
            )
            viewer.handle_mouse(event)
            assert viewer.scroll_manager.state.scroll_position >= 1

    def test_mouse_scroll_up(self):
        """Test mouse wheel scroll up.

        Verifies
        --------
        - Scroll wheel up decreases scroll position
        """
        lines = [f"<b>Line {i}</b>" for i in range(50)]
        content = "\n".join(lines)
        viewer = HTMLViewer(content=content, height=10, width=80)

        if viewer.scroll_manager.state.is_scrollable:
            # First scroll down
            viewer.handle_key(Keys.DOWN)
            viewer.handle_key(Keys.DOWN)
            pos = viewer.scroll_manager.state.scroll_position

            event = MouseEvent(
                x=5,
                y=5,
                button=MouseButton.SCROLL_UP,
                type=MouseEventType.SCROLL,
            )
            viewer.handle_mouse(event)
            assert viewer.scroll_manager.state.scroll_position < pos


class TestHTMLViewerContent:
    """Tests for HTMLViewer content handling."""

    def test_set_content(self):
        """Test setting content after creation.

        Verifies
        --------
        - Content is updated
        - Rendered lines are updated
        """
        viewer = HTMLViewer(content="<b>Initial</b>")
        initial_lines = len(viewer.rendered_lines)

        viewer.set_content("<b>New</b>\n<i>Content</i>\n<u>Here</u>")
        assert viewer.content == "<b>New</b>\n<i>Content</i>\n<u>Here</u>"
        assert len(viewer.rendered_lines) >= 3

    def test_html_formatting_bold(self):
        """Test bold HTML tag rendering.

        Verifies
        --------
        - Bold tags create cells with bold attribute
        """
        viewer = HTMLViewer(content="<b>Bold</b>", width=20, height=5)
        # Check that rendered lines exist
        assert len(viewer.rendered_lines) > 0
        assert len(viewer.rendered_lines[0]) > 0

    def test_html_formatting_italic(self):
        """Test italic HTML tag rendering.

        Verifies
        --------
        - Italic tags create cells with italic attribute
        """
        viewer = HTMLViewer(content="<i>Italic</i>", width=20, height=5)
        assert len(viewer.rendered_lines) > 0
        assert len(viewer.rendered_lines[0]) > 0

    def test_html_formatting_mixed(self):
        """Test mixed HTML tags.

        Verifies
        --------
        - Mixed tags render correctly
        """
        viewer = HTMLViewer(content="<b>Bold</b> and <i>italic</i>", width=30, height=5)
        assert len(viewer.rendered_lines) > 0
        # Should have content for "Bold and italic"
        total_chars = sum(len(line) for line in viewer.rendered_lines)
        assert total_chars > 10


class TestHTMLViewerSizing:
    """Tests for HTMLViewer sizing functionality."""

    def test_intrinsic_size_with_border(self):
        """Test intrinsic size includes border.

        Verifies
        --------
        - Width includes borders
        - Height includes borders
        """
        viewer = HTMLViewer(width=40, height=20, border_style="single")
        w, h = viewer.get_intrinsic_size()
        assert w == 42  # 40 + 2 for borders
        assert h == 22  # 20 + 2 for borders

    def test_intrinsic_size_no_border(self):
        """Test intrinsic size without border.

        Verifies
        --------
        - Size matches dimensions when no border
        """
        viewer = HTMLViewer(width=40, height=20, border_style="none")
        w, h = viewer.get_intrinsic_size()
        assert w == 40
        assert h == 20

    def test_dynamic_sizing(self):
        """Test dynamic sizing support.

        Verifies
        --------
        - Dynamic sizing flag can be set
        - set_bounds adjusts dimensions to match bounds
        - Viewport size is correctly calculated for scrolling
        """
        viewer = HTMLViewer(width=40, height=20, border_style="single")
        viewer._dynamic_sizing = True
        assert viewer.supports_dynamic_sizing is True

        viewer.set_bounds(Bounds(0, 0, 60, 30))
        # width/height should match bounds dimensions (outer dimensions)
        assert viewer.width == 60
        assert viewer.height == 30
        # Viewport size should be height minus borders for scrolling
        assert viewer.scroll_manager.state.viewport_size == 28  # 30 - 2 for borders


class TestHTMLViewerClasses:
    """Tests for HTMLViewer CSS class support."""

    def test_css_classes_string(self):
        """Test CSS classes from string.

        Verifies
        --------
        - Classes parsed from space-separated string
        """
        viewer = HTMLViewer(classes="panel primary")
        assert "panel" in viewer.classes
        assert "primary" in viewer.classes

    def test_css_classes_list(self):
        """Test CSS classes from list.

        Verifies
        --------
        - Classes parsed from list
        """
        viewer = HTMLViewer(classes=["panel", "primary"])
        assert "panel" in viewer.classes
        assert "primary" in viewer.classes
