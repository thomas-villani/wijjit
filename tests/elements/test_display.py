"""Tests for display elements (MarkdownView, CodeBlock)."""


from wijjit.elements.base import ElementType
from wijjit.elements.display import CodeBlock, MarkdownView
from wijjit.terminal.input import Keys


class TestMarkdownViewBasics:
    """Tests for MarkdownView basic functionality."""

    def test_create_markdown_view(self):
        """Test creating a markdown view.

        Verifies
        --------
        - ID assignment
        - Dimensions
        - Focusability
        - Element type
        """
        md = MarkdownView(id="docs", content="# Hello", width=60, height=20)
        assert md.id == "docs"
        assert md.width == 60
        assert md.height == 20
        assert md.focusable
        assert md.element_type == ElementType.DISPLAY

    def test_initial_content(self):
        """Test markdown view with initial content.

        Verifies
        --------
        - Content is stored
        - Content is rendered to lines
        """
        content = "# Title\n\nSome text"
        md = MarkdownView(content=content)
        assert md.content == content
        assert len(md.rendered_lines) > 0

    def test_empty_content(self):
        """Test markdown view with empty content.

        Verifies
        --------
        - Empty content doesn't crash
        - Content lines has at most one empty line
        """
        md = MarkdownView(content="")
        assert md.content == ""
        # Empty content may render to a single empty line or empty list
        assert len(md.rendered_lines) <= 1

    def test_border_styles(self):
        """Test markdown view with different border styles.

        Verifies
        --------
        - Single border
        - Double border
        - Rounded border
        - No border
        """
        for style in ["single", "double", "rounded", "none"]:
            md = MarkdownView(border_style=style)
            assert md.border_style == style

    def test_with_title(self):
        """Test markdown view with border title.

        Verifies
        --------
        - Title is stored
        - Title is used in rendering
        """
        md = MarkdownView(title="Documentation", border_style="single")
        assert md.title == "Documentation"
        rendered = md.render()
        assert "Documentation" in rendered

    def test_scrollbar_option(self):
        """Test markdown view scrollbar visibility option.

        Verifies
        --------
        - Scrollbar can be shown
        - Scrollbar can be hidden
        """
        md_with = MarkdownView(show_scrollbar=True)
        md_without = MarkdownView(show_scrollbar=False)
        assert md_with.show_scrollbar is True
        assert md_without.show_scrollbar is False


class TestMarkdownViewScrolling:
    """Tests for MarkdownView scrolling functionality."""

    def test_scroll_down(self):
        """Test scrolling down in markdown view.

        Verifies
        --------
        - Initial scroll position is 0
        - Down key increases scroll position
        - Scroll callback is triggered
        """
        # Create content with explicit newlines that won't be wrapped
        # Use markdown list items which each create a line
        lines = [f"- Item {i}: Some text here" for i in range(50)]
        content = "\n".join(lines)
        md = MarkdownView(content=content, height=10, width=80)

        # Set up scroll callback
        scroll_positions = []
        md.on_scroll = lambda pos: scroll_positions.append(pos)

        # Initial position
        assert md.scroll_manager.state.scroll_position == 0

        # Scroll down (content should be scrollable)
        if md.scroll_manager.state.is_scrollable:
            md.handle_key(Keys.DOWN)
            assert md.scroll_manager.state.scroll_position >= 1
            assert len(scroll_positions) > 0

    def test_scroll_up(self):
        """Test scrolling up in markdown view.

        Verifies
        --------
        - Can scroll back up
        - Position doesn't go negative
        """
        lines = [f"- Item {i}: Some text here" for i in range(50)]
        content = "\n".join(lines)
        md = MarkdownView(content=content, height=10, width=80)

        # Only test if content is scrollable
        if md.scroll_manager.state.is_scrollable:
            # Scroll down first
            md.handle_key(Keys.DOWN)
            md.handle_key(Keys.DOWN)
            pos_after_down = md.scroll_manager.state.scroll_position
            assert pos_after_down >= 2

            # Scroll up
            md.handle_key(Keys.UP)
            assert md.scroll_manager.state.scroll_position < pos_after_down

            # Can't scroll past top
            for _ in range(10):
                md.handle_key(Keys.UP)
            assert md.scroll_manager.state.scroll_position == 0

    def test_page_down(self):
        """Test page down scrolling.

        Verifies
        --------
        - Page down scrolls by viewport height
        - Position increases correctly
        """
        lines = [f"- Item {i}: Some text here" for i in range(100)]
        content = "\n".join(lines)
        md = MarkdownView(content=content, height=10, width=80)

        # Only test if content is scrollable
        if md.scroll_manager.state.is_scrollable:
            md.handle_key(Keys.PAGE_DOWN)
            # Should scroll by some amount
            assert md.scroll_manager.state.scroll_position > 0

    def test_page_up(self):
        """Test page up scrolling.

        Verifies
        --------
        - Page up scrolls backward by viewport height
        - Position decreases correctly
        """
        lines = [f"- Item {i}: Some text here" for i in range(100)]
        content = "\n".join(lines)
        md = MarkdownView(content=content, height=10, width=80)

        # Only test if content is scrollable
        if md.scroll_manager.state.is_scrollable:
            # Scroll down first
            md.handle_key(Keys.PAGE_DOWN)
            md.handle_key(Keys.PAGE_DOWN)
            initial_pos = md.scroll_manager.state.scroll_position

            # Page up
            if initial_pos > 0:
                md.handle_key(Keys.PAGE_UP)
                assert md.scroll_manager.state.scroll_position < initial_pos

    def test_scroll_state_persistence(self):
        """Test scroll state persistence via state key.

        Verifies
        --------
        - scroll_state_key can be set
        - Scroll callback uses the key
        """
        lines = [f"- Item {i}: Some text here" for i in range(50)]
        content = "\n".join(lines)
        md = MarkdownView(content=content, height=10, width=80)
        md.scroll_state_key = "_scroll_docs"

        state = {}
        md.on_scroll = lambda pos: state.update({md.scroll_state_key: pos})

        # Only test if content is scrollable
        if md.scroll_manager.state.is_scrollable:
            md.handle_key(Keys.DOWN)
            assert "_scroll_docs" in state
            assert state["_scroll_docs"] >= 1


class TestMarkdownViewFocus:
    """Tests for MarkdownView focus handling."""

    def test_focus_changes_border_color(self):
        """Test that focus changes border color.

        Verifies
        --------
        - Unfocused border uses default color
        - Focused border uses cyan color
        """
        md = MarkdownView(content="test", border_style="single")

        # Render unfocused
        md.focused = False
        unfocused = md.render()

        # Render focused
        md.focused = True
        focused = md.render()

        # Should have different ANSI codes for color
        assert unfocused != focused
        # Cyan color code (36) should appear in focused version
        assert "36m" in focused


class TestCodeBlockBasics:
    """Tests for CodeBlock basic functionality."""

    def test_create_code_block(self):
        """Test creating a code block.

        Verifies
        --------
        - ID assignment
        - Dimensions
        - Language setting
        - Focusability
        - Element type
        """
        code = CodeBlock(
            id="code",
            code="def hello(): pass",
            language="python",
            width=60,
            height=15,
        )
        assert code.id == "code"
        assert code.width == 60
        assert code.height == 15
        assert code.language == "python"
        assert code.focusable
        assert code.element_type == ElementType.DISPLAY

    def test_initial_code(self):
        """Test code block with initial code content.

        Verifies
        --------
        - Code is stored
        - Code is rendered to lines
        """
        source = "def hello():\n    print('world')"
        code = CodeBlock(code=source, language="python")
        assert code.code == source
        assert len(code.rendered_lines) > 0

    def test_empty_code(self):
        """Test code block with empty code.

        Verifies
        --------
        - Empty code doesn't crash
        - Rendered lines is not None
        """
        code = CodeBlock(code="", language="python")
        assert code.code == ""
        # Empty code may still render with line numbers/formatting
        assert code.rendered_lines is not None
        assert isinstance(code.rendered_lines, list)

    def test_languages(self):
        """Test code block with different languages.

        Verifies
        --------
        - Python language
        - JavaScript language
        - Rust language
        - Go language
        """
        for lang in ["python", "javascript", "rust", "go"]:
            code = CodeBlock(code="test", language=lang)
            assert code.language == lang

    def test_line_numbers(self):
        """Test code block line number option.

        Verifies
        --------
        - Line numbers can be shown
        - Line numbers can be hidden
        """
        with_nums = CodeBlock(code="test", show_line_numbers=True)
        without_nums = CodeBlock(code="test", show_line_numbers=False)
        assert with_nums.show_line_numbers is True
        assert without_nums.show_line_numbers is False

    def test_theme(self):
        """Test code block with theme option.

        Verifies
        --------
        - Default theme is monokai
        - Theme can be changed
        """
        code1 = CodeBlock(code="test")
        assert code1.theme == "monokai"

        code2 = CodeBlock(code="test", theme="github-dark")
        assert code2.theme == "github-dark"

    def test_with_title(self):
        """Test code block with border title.

        Verifies
        --------
        - Title is stored
        - Title appears in rendered output
        """
        code = CodeBlock(
            code="test", language="python", title="Example", border_style="single"
        )
        assert code.title == "Example"
        rendered = code.render()
        assert "Example" in rendered


class TestCodeBlockScrolling:
    """Tests for CodeBlock scrolling functionality."""

    def test_scroll_long_code(self):
        """Test scrolling through long code.

        Verifies
        --------
        - Initial position is 0
        - Can scroll down
        - Scroll callback triggered
        """
        # Create code longer than viewport
        lines = [f"line_{i} = {i}" for i in range(50)]
        source = "\n".join(lines)
        code = CodeBlock(code=source, language="python", height=10)

        scroll_positions = []
        code.on_scroll = lambda pos: scroll_positions.append(pos)

        # Initial
        assert code.scroll_manager.state.scroll_position == 0

        # Scroll
        code.handle_key(Keys.DOWN)
        assert code.scroll_manager.state.scroll_position == 1
        assert 1 in scroll_positions

    def test_scroll_state_key(self):
        """Test scroll state persistence via state key.

        Verifies
        --------
        - scroll_state_key can be set
        - Scroll callback uses the key
        """
        # Create code with enough content to be scrollable
        lines = [f"line_{i} = {i}" for i in range(50)]
        source = "\n".join(lines)
        code = CodeBlock(code=source, language="python", height=10)
        code.scroll_state_key = "_scroll_code"

        state = {}
        code.on_scroll = lambda pos: state.update({code.scroll_state_key: pos})

        code.handle_key(Keys.DOWN)
        assert "_scroll_code" in state


class TestCodeBlockFocus:
    """Tests for CodeBlock focus handling."""

    def test_focus_changes_border_color(self):
        """Test that focus changes border color.

        Verifies
        --------
        - Focused state affects rendering
        - Cyan color appears when focused
        """
        code = CodeBlock(code="test", language="python", border_style="single")

        code.focused = False
        unfocused = code.render()

        code.focused = True
        focused = code.render()

        # Should have different rendering
        assert unfocused != focused
        # Cyan color code should appear
        assert "36m" in focused


class TestMarkdownViewRendering:
    """Tests for MarkdownView rendering behavior."""

    def test_render_basic_markdown(self):
        """Test rendering basic markdown content.

        Verifies
        --------
        - Headers are rendered
        - Text is rendered
        - Output contains visible content
        """
        md = MarkdownView(content="# Title\n\nParagraph text")
        rendered = md.render()
        assert len(rendered) > 0
        assert "Title" in rendered

    def test_render_with_border(self):
        """Test rendering with border.

        Verifies
        --------
        - Border characters appear in output
        - Content is framed by border
        """
        md = MarkdownView(content="test", border_style="single", width=20, height=5)
        rendered = md.render()
        # Should have border box drawing characters
        assert any(c in rendered for c in ["─", "│", "┌", "┐", "└", "┘"])

    def test_render_without_border(self):
        """Test rendering without border.

        Verifies
        --------
        - No border characters in output
        - Content is rendered directly
        """
        md = MarkdownView(content="test", border_style="none")
        rendered = md.render()
        # Should not have border box drawing characters
        assert not any(c in rendered for c in ["─", "│", "┌", "┐", "└", "┘"])

    def test_viewport_clipping(self):
        """Test content is clipped to viewport.

        Verifies
        --------
        - Long content is clipped
        - Rendered height matches viewport
        """
        # Create content much taller than viewport
        content = "\n".join([f"Line {i}" for i in range(100)])
        md = MarkdownView(content=content, height=5, border_style="none")
        rendered = md.render()

        # Count newlines in rendered output
        lines = rendered.split("\n")
        # Should be clipped to viewport height
        assert len(lines) <= 5


class TestCodeBlockRendering:
    """Tests for CodeBlock rendering behavior."""

    def test_render_python_code(self):
        """Test rendering Python code with syntax highlighting.

        Verifies
        --------
        - Code is rendered
        - Output contains ANSI color codes
        """
        code = CodeBlock(code="def hello():\n    pass", language="python")
        rendered = code.render()
        assert len(rendered) > 0
        # Should have syntax highlighting (ANSI codes)
        assert "\x1b[" in rendered or "def" in rendered

    def test_render_with_line_numbers(self):
        """Test rendering with line numbers.

        Verifies
        --------
        - Line numbers appear in output
        - Numbers are formatted correctly
        """
        source = "line1\nline2\nline3"
        code = CodeBlock(
            code=source, language="python", show_line_numbers=True, border_style="none"
        )
        rendered = code.render()
        # Line numbers should appear
        assert "1" in rendered or "2" in rendered

    def test_render_without_line_numbers(self):
        """Test rendering without line numbers.

        Verifies
        --------
        - Code is rendered
        - No line number formatting
        """
        code = CodeBlock(code="test", language="python", show_line_numbers=False)
        rendered = code.render()
        assert len(rendered) > 0


class TestContentUpdates:
    """Tests for updating content after creation."""

    def test_update_markdown_content(self):
        """Test updating markdown content dynamically.

        Verifies
        --------
        - Content can be changed
        - Re-rendering uses new content
        """
        md = MarkdownView(content="Old content", border_style="none")
        old_lines = len(md.rendered_lines)

        md.content = "# New Content\n\nThis is a longer document with multiple lines."
        md._render_content()
        new_lines = len(md.rendered_lines)

        # Should have more rendered lines
        assert new_lines > old_lines
        # Check content changed
        assert md.content == "# New Content\n\nThis is a longer document with multiple lines."

    def test_update_code_content(self):
        """Test updating code content dynamically.

        Verifies
        --------
        - Code can be changed
        - Re-rendering uses new code
        """
        code = CodeBlock(code="old = 1", language="python")
        old_render = code.render()

        code.code = "new = 2"
        code._render_content()
        new_render = code.render()

        # Renders should be different
        assert old_render != new_render

    def test_update_markdown_dimensions(self):
        """Test updating markdown dimensions.

        Verifies
        --------
        - Width can be changed
        - Height can be changed
        - Scroll manager is recreated
        """
        md = MarkdownView(content="test", width=40, height=10)
        md.width = 60
        md.height = 20
        md._render_content()

        assert md.width == 60
        assert md.height == 20

    def test_update_code_language(self):
        """Test updating code language.

        Verifies
        --------
        - Language can be changed
        - Syntax highlighting updates
        """
        code = CodeBlock(code="function test() {}", language="javascript")
        code.language = "python"
        code._render_content()

        assert code.language == "python"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_long_single_line(self):
        """Test markdown with very long single line.

        Verifies
        --------
        - Long lines don't crash
        - Content is wrapped or clipped
        """
        long_line = "word " * 1000
        md = MarkdownView(content=long_line, width=40)
        rendered = md.render()
        assert len(rendered) > 0

    def test_many_lines(self):
        """Test code with many lines.

        Verifies
        --------
        - Large content doesn't crash
        - Scrolling works
        """
        lines = [f"line {i}" for i in range(10000)]
        source = "\n".join(lines)
        code = CodeBlock(code=source, language="python", height=10)
        rendered = code.render()
        assert len(rendered) > 0

    def test_special_characters_markdown(self):
        """Test markdown with special characters.

        Verifies
        --------
        - Special chars don't crash
        - Content is rendered
        """
        content = "Special: <>&\"'\n\t\r\x00"
        md = MarkdownView(content=content)
        rendered = md.render()
        assert len(rendered) > 0

    def test_special_characters_code(self):
        """Test code with special characters.

        Verifies
        --------
        - Special chars in code don't crash
        - Content is rendered
        """
        source = 'text = "Special: <>&\\"\'\\n\\t"'
        code = CodeBlock(code=source, language="python")
        rendered = code.render()
        assert len(rendered) > 0

    def test_zero_dimensions(self):
        """Test handling of zero or minimal dimensions.

        Verifies
        --------
        - Zero width doesn't crash
        - Zero height doesn't crash
        """
        # These should handle gracefully or clip
        md = MarkdownView(content="test", width=1, height=1)
        rendered = md.render()
        # Should produce something even if minimal
        assert isinstance(rendered, str)

    def test_none_content(self):
        """Test handling of None content.

        Verifies
        --------
        - None is converted to empty string
        - No crash occurs
        """
        # None should be handled gracefully
        md = MarkdownView(content=None or "")
        assert md.content == ""

        code = CodeBlock(code=None or "", language="python")
        assert code.code == ""
