"""Tests for ContentView element."""

import pytest

from wijjit.elements.base import ElementType
from wijjit.elements.display.contentview import ContentType, ContentView
from wijjit.layout.bounds import Bounds
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestContentViewCreation:
    """Tests for ContentView creation and configuration."""

    def test_create_with_defaults(self):
        """Test creating ContentView with default values.

        Verifies
        --------
        - Default content_type is PLAIN
        - Element is focusable
        - Element type is DISPLAY
        """
        view = ContentView()
        assert view.content_type == ContentType.PLAIN
        assert view.focusable is True
        assert view.element_type == ElementType.DISPLAY
        assert view.content == ""

    def test_create_with_id(self):
        """Test creating ContentView with ID.

        Verifies
        --------
        - ID is assigned correctly
        """
        view = ContentView(id="docs")
        assert view.id == "docs"

    def test_create_with_content_type_string(self):
        """Test creating ContentView with content_type as string.

        Verifies
        --------
        - String content types are resolved to enums
        """
        for type_str in ["plain", "text", "ansi", "html", "markdown", "rich", "code"]:
            view = ContentView(content_type=type_str)
            assert isinstance(view.content_type, ContentType)

    def test_create_with_content_type_enum(self):
        """Test creating ContentView with content_type as enum.

        Verifies
        --------
        - Enum content types work directly
        """
        view = ContentView(content_type=ContentType.MARKDOWN)
        assert view.content_type == ContentType.MARKDOWN

    def test_invalid_content_type_raises(self):
        """Test that invalid content_type raises ValueError.

        Verifies
        --------
        - ValueError raised for unknown content type
        """
        with pytest.raises(ValueError) as exc:
            ContentView(content_type="invalid_type")
        assert "Invalid content_type" in str(exc.value)

    def test_text_alias_for_plain(self):
        """Test that 'text' is an alias for 'plain'.

        Verifies
        --------
        - Both 'text' and 'plain' work for plain text content
        """
        view_text = ContentView(content="Hello", content_type="text")
        view_plain = ContentView(content="Hello", content_type="plain")
        assert view_text.content_type == ContentType.TEXT
        assert view_plain.content_type == ContentType.PLAIN
        # Both should render similarly (TEXT is just an alias)


class TestContentViewPlainText:
    """Tests for ContentView with plain text content."""

    def test_plain_text_rendering(self):
        """Test plain text content rendering.

        Verifies
        --------
        - Plain text is stored
        - Lines are created
        """
        view = ContentView(content="Hello World", content_type="plain")
        assert view.content == "Hello World"
        assert len(view.rendered_lines) >= 1

    def test_multiline_plain_text(self):
        """Test multiline plain text.

        Verifies
        --------
        - Lines are split correctly
        """
        content = "Line 1\nLine 2\nLine 3"
        view = ContentView(content=content, content_type="plain")
        assert len(view.rendered_lines) >= 3

    def test_empty_content(self):
        """Test empty content handling.

        Verifies
        --------
        - Empty content doesn't crash
        - At least one line exists
        """
        view = ContentView(content="", content_type="plain")
        assert len(view.rendered_lines) >= 1


class TestContentViewANSI:
    """Tests for ContentView with ANSI content."""

    def test_ansi_content_type(self):
        """Test ANSI content type is set.

        Verifies
        --------
        - Content type is ANSI
        """
        view = ContentView(content="\x1b[31mRed\x1b[0m", content_type="ansi")
        assert view.content_type == ContentType.ANSI
        assert len(view.rendered_lines) >= 1


class TestContentViewHTML:
    """Tests for ContentView with HTML content."""

    def test_html_content_type(self):
        """Test HTML content type.

        Verifies
        --------
        - HTML content is processed
        - Uses cell-based rendering
        """
        view = ContentView(content="<b>Bold</b>", content_type="html")
        assert view.content_type == ContentType.HTML
        assert view._uses_cells is True
        assert len(view.rendered_cells) >= 1

    def test_html_multiline(self):
        """Test multiline HTML content.

        Verifies
        --------
        - Multiple lines are processed
        """
        content = "<b>Line 1</b>\n<i>Line 2</i>"
        view = ContentView(content=content, content_type="html")
        assert len(view.rendered_cells) >= 2


class TestContentViewMarkdown:
    """Tests for ContentView with Markdown content."""

    def test_markdown_content_type(self):
        """Test Markdown content rendering.

        Verifies
        --------
        - Markdown content is processed via Rich
        """
        view = ContentView(content="# Hello\n**Bold**", content_type="markdown")
        assert view.content_type == ContentType.MARKDOWN
        assert len(view.rendered_lines) >= 1

    def test_markdown_headers(self):
        """Test Markdown headers are rendered.

        Verifies
        --------
        - Header content produces output
        """
        view = ContentView(content="# Title\n## Subtitle", content_type="markdown")
        assert len(view.rendered_lines) >= 1


class TestContentViewRich:
    """Tests for ContentView with Rich markup content."""

    def test_rich_markup_content(self):
        """Test Rich markup content.

        Verifies
        --------
        - Rich markup like [green]text[/green] is processed
        """
        view = ContentView(content="[green]Success[/green]", content_type="rich")
        assert view.content_type == ContentType.RICH
        assert len(view.rendered_lines) >= 1


class TestContentViewCode:
    """Tests for ContentView with code content."""

    def test_code_content_type(self):
        """Test code content with syntax highlighting.

        Verifies
        --------
        - Code content is highlighted
        """
        code = "def hello():\n    print('Hello')"
        view = ContentView(content=code, content_type="code", language="python")
        assert view.content_type == ContentType.CODE
        assert len(view.rendered_lines) >= 2

    def test_code_with_line_numbers(self):
        """Test code with line numbers.

        Verifies
        --------
        - Line numbers option is stored
        """
        code = "x = 1\ny = 2"
        view = ContentView(
            content=code,
            content_type="code",
            show_line_numbers=True,
            line_number_start=10,
        )
        assert view.show_line_numbers is True
        assert view.line_number_start == 10

    def test_code_language_option(self):
        """Test different programming languages.

        Verifies
        --------
        - Language option is stored
        """
        view = ContentView(
            content="console.log('hi');", content_type="code", language="javascript"
        )
        assert view.language == "javascript"

    def test_code_theme_option(self):
        """Test syntax highlighting theme.

        Verifies
        --------
        - Theme option is stored
        """
        view = ContentView(content="x = 1", content_type="code", theme="monokai")
        assert view.theme == "monokai"


class TestContentViewScrolling:
    """Tests for ContentView scrolling functionality."""

    def test_scroll_down(self):
        """Test scrolling down.

        Verifies
        --------
        - Down key increases scroll position
        """
        lines = [f"Line {i}" for i in range(50)]
        content = "\n".join(lines)
        view = ContentView(content=content, content_type="plain", height=10, width=80)

        assert view.scroll_manager.state.scroll_position == 0

        if view.scroll_manager.state.is_scrollable:
            view.handle_key(Keys.DOWN)
            assert view.scroll_manager.state.scroll_position >= 1

    def test_scroll_up(self):
        """Test scrolling up.

        Verifies
        --------
        - Up key decreases scroll position
        """
        lines = [f"Line {i}" for i in range(50)]
        content = "\n".join(lines)
        view = ContentView(content=content, content_type="plain", height=10, width=80)

        if view.scroll_manager.state.is_scrollable:
            view.handle_key(Keys.DOWN)
            view.handle_key(Keys.DOWN)
            pos = view.scroll_manager.state.scroll_position

            view.handle_key(Keys.UP)
            assert view.scroll_manager.state.scroll_position < pos

    def test_home_end_keys(self):
        """Test HOME and END key scrolling.

        Verifies
        --------
        - HOME goes to top
        - END goes to bottom
        """
        lines = [f"Line {i}" for i in range(50)]
        content = "\n".join(lines)
        view = ContentView(content=content, content_type="plain", height=10, width=80)

        if view.scroll_manager.state.is_scrollable:
            view.handle_key(Keys.END)
            assert view.scroll_manager.state.scroll_position > 0

            view.handle_key(Keys.HOME)
            assert view.scroll_manager.state.scroll_position == 0

    def test_page_up_down(self):
        """Test PAGE_UP and PAGE_DOWN scrolling.

        Verifies
        --------
        - Page keys scroll by viewport size
        """
        lines = [f"Line {i}" for i in range(100)]
        content = "\n".join(lines)
        view = ContentView(content=content, content_type="plain", height=10, width=80)

        if view.scroll_manager.state.is_scrollable:
            view.handle_key(Keys.PAGE_DOWN)
            pos = view.scroll_manager.state.scroll_position
            assert pos > 0

            view.handle_key(Keys.PAGE_UP)
            assert view.scroll_manager.state.scroll_position < pos

    def test_can_scroll_direction(self):
        """Test can_scroll method.

        Verifies
        --------
        - Reports scroll capability correctly
        """
        lines = [f"Line {i}" for i in range(50)]
        content = "\n".join(lines)
        view = ContentView(content=content, content_type="plain", height=10, width=80)

        # At top, cannot scroll up
        assert view.can_scroll(-1) is False

        if view.scroll_manager.state.is_scrollable:
            assert view.can_scroll(1) is True


class TestContentViewMouse:
    """Tests for ContentView mouse interaction."""

    @pytest.mark.asyncio
    async def test_mouse_scroll_down(self):
        """Test mouse wheel scroll down.

        Verifies
        --------
        - Scroll wheel down works
        """
        lines = [f"Line {i}" for i in range(50)]
        content = "\n".join(lines)
        view = ContentView(content=content, content_type="plain", height=10, width=80)

        if view.scroll_manager.state.is_scrollable:
            event = MouseEvent(
                x=5,
                y=5,
                button=MouseButton.SCROLL_DOWN,
                type=MouseEventType.SCROLL,
            )
            await view.handle_mouse(event)
            assert view.scroll_manager.state.scroll_position >= 1

    @pytest.mark.asyncio
    async def test_mouse_scroll_up(self):
        """Test mouse wheel scroll up.

        Verifies
        --------
        - Scroll wheel up works
        """
        lines = [f"Line {i}" for i in range(50)]
        content = "\n".join(lines)
        view = ContentView(content=content, content_type="plain", height=10, width=80)

        if view.scroll_manager.state.is_scrollable:
            view.handle_key(Keys.DOWN)
            view.handle_key(Keys.DOWN)
            pos = view.scroll_manager.state.scroll_position

            event = MouseEvent(
                x=5,
                y=5,
                button=MouseButton.SCROLL_UP,
                type=MouseEventType.SCROLL,
            )
            await view.handle_mouse(event)
            assert view.scroll_manager.state.scroll_position < pos


class TestContentViewBorders:
    """Tests for ContentView border functionality."""

    def test_border_styles(self):
        """Test different border styles.

        Verifies
        --------
        - All border styles work
        """
        for style in ["single", "double", "rounded", "none"]:
            view = ContentView(border_style=style)
            assert view.border_style == style

    def test_with_title(self):
        """Test border with title.

        Verifies
        --------
        - Title is stored
        """
        view = ContentView(title="Documentation", border_style="single")
        assert view.title == "Documentation"


class TestContentViewSizing:
    """Tests for ContentView sizing functionality."""

    def test_intrinsic_size_with_border(self):
        """Test intrinsic size includes border.

        Verifies
        --------
        - Size includes borders
        """
        view = ContentView(width=40, height=20, border_style="single")
        w, h = view.get_intrinsic_size()
        assert w == 42  # 40 + 2 for borders
        assert h == 22  # 20 + 2 for borders

    def test_intrinsic_size_no_border(self):
        """Test intrinsic size without border.

        Verifies
        --------
        - Size matches dimensions
        """
        view = ContentView(width=40, height=20, border_style="none")
        w, h = view.get_intrinsic_size()
        assert w == 40
        assert h == 20

    def test_dynamic_sizing(self):
        """Test dynamic sizing support.

        Verifies
        --------
        - Dynamic sizing adjusts dimensions
        - Width/height store inner dimensions (excluding borders)
        """
        view = ContentView(width=40, height=20, border_style="single")
        view._dynamic_sizing = True
        assert view.supports_dynamic_sizing is True

        view.set_bounds(Bounds(0, 0, 60, 30))
        # With borders, inner dimensions are bounds - 2
        assert view.width == 58  # 60 - 2 for borders
        assert view.height == 28  # 30 - 2 for borders


class TestContentViewSetContent:
    """Tests for ContentView set_content method."""

    def test_set_content_same_type(self):
        """Test setting content without changing type.

        Verifies
        --------
        - Content is updated
        """
        view = ContentView(content="Initial", content_type="plain")
        view.set_content("Updated")
        assert view.content == "Updated"

    def test_set_content_with_type_change(self):
        """Test setting content with type change.

        Verifies
        --------
        - Content and type both update
        """
        view = ContentView(content="Hello", content_type="plain")
        view.set_content("# Header", content_type="markdown")
        assert view.content == "# Header"
        assert view.content_type == ContentType.MARKDOWN


class TestContentViewDynamicContent:
    """Tests for ContentView dynamic content updates via property setter."""

    def test_content_property_setter_updates_scroll_manager(self):
        """Test that setting content via property updates scroll manager.

        Verifies
        --------
        - Content is updated
        - Scroll manager content_size is updated
        - Rendered lines are updated
        """
        # Create view with short content
        view = ContentView(content="Line 1", content_type="plain", height=5)
        initial_content_size = view.scroll_manager.state.content_size
        assert initial_content_size == 1

        # Set new content with more lines via property
        view.content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        assert view.content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        assert view.scroll_manager.state.content_size == 5
        assert len(view.rendered_lines) == 5

    def test_content_property_setter_shrink_content(self):
        """Test that setting shorter content updates scroll manager.

        Verifies
        --------
        - Scroll manager content_size is reduced
        - Rendered lines are reduced
        """
        # Create view with long content
        long_content = "\n".join([f"Line {i}" for i in range(20)])
        view = ContentView(content=long_content, content_type="plain", height=5)
        assert view.scroll_manager.state.content_size == 20

        # Set shorter content
        view.content = "Short"
        assert view.scroll_manager.state.content_size == 1
        assert len(view.rendered_lines) == 1

    def test_content_property_setter_same_value_no_update(self):
        """Test that setting same content doesn't trigger re-render.

        Verifies
        --------
        - No unnecessary re-render when content is unchanged
        """
        view = ContentView(content="Same", content_type="plain")
        cache_key_before = view._render_cache_key

        # Set same content
        view.content = "Same"
        # Cache key should not change (no re-render needed)
        assert view._render_cache_key == cache_key_before

    def test_content_property_setter_clears_cache(self):
        """Test that setting new content clears render cache.

        Verifies
        --------
        - Render cache is cleared when content changes
        - New content is rendered
        """
        view = ContentView(content="Original", content_type="plain")
        original_cache_key = view._render_cache_key

        # Set new content
        view.content = "New content"
        # Cache key should be different (re-render occurred)
        assert view._render_cache_key != original_cache_key


class TestContentViewClasses:
    """Tests for ContentView CSS class support."""

    def test_css_classes_string(self):
        """Test CSS classes from string.

        Verifies
        --------
        - Classes parsed correctly
        """
        view = ContentView(classes="panel primary")
        assert "panel" in view.classes
        assert "primary" in view.classes

    def test_css_classes_list(self):
        """Test CSS classes from list.

        Verifies
        --------
        - Classes parsed from list
        """
        view = ContentView(classes=["panel", "primary"])
        assert "panel" in view.classes
        assert "primary" in view.classes
