"""Tests for the CodeEditor element with syntax highlighting."""

import pytest

from wijjit.elements.input.code_editor import CodeEditor, SyntaxHighlighter
from wijjit.elements.input.highlighting import (
    DEFAULT_THEME,
    THEMES,
    get_available_themes,
    get_style_for_token,
)

# Skip importing pygments.token at module level to allow tests to run
# even if Pygments has issues
try:
    from pygments.token import Keyword, Token

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class TestHighlighting:
    """Tests for the highlighting module."""

    def test_default_theme_exists(self):
        """Default theme should exist in THEMES."""
        assert DEFAULT_THEME in THEMES
        assert DEFAULT_THEME == "monokai"

    def test_all_themes_exist(self):
        """All expected themes should be available."""
        themes = get_available_themes()
        assert "monokai" in themes
        assert "dracula" in themes
        assert "github-light" in themes
        assert "nord" in themes

    @pytest.mark.skipif(not PYGMENTS_AVAILABLE, reason="Pygments not available")
    def test_get_style_for_token_keyword(self):
        """Should return style for keyword tokens."""
        style = get_style_for_token(Keyword, "monokai")
        assert "fg_color" in style
        assert style["fg_color"] is not None

    @pytest.mark.skipif(not PYGMENTS_AVAILABLE, reason="Pygments not available")
    def test_get_style_for_token_hierarchy(self):
        """Should traverse hierarchy for specific token types."""
        # Keyword.Reserved should fall back to Keyword style
        style = get_style_for_token(Keyword.Reserved, "monokai")
        keyword_style = get_style_for_token(Keyword, "monokai")
        # Should get a valid style (might be same as parent)
        assert "fg_color" in style

    @pytest.mark.skipif(not PYGMENTS_AVAILABLE, reason="Pygments not available")
    def test_get_style_for_token_fallback(self):
        """Should fall back to Token style for unknown types."""
        style = get_style_for_token(Token, "monokai")
        assert "fg_color" in style

    def test_get_style_for_unknown_theme(self):
        """Should use default theme for unknown theme name."""
        if not PYGMENTS_AVAILABLE:
            pytest.skip("Pygments not available")
        style = get_style_for_token(Token, "nonexistent_theme")
        # Should not raise, falls back to default
        assert "fg_color" in style


class TestSyntaxHighlighter:
    """Tests for the SyntaxHighlighter class."""

    def test_init_with_language(self):
        """Should initialize lexer for valid language."""
        highlighter = SyntaxHighlighter(language="python")
        assert highlighter.language == "python"
        assert highlighter.lexer is not None

    def test_init_with_invalid_language(self):
        """Should handle invalid language gracefully."""
        highlighter = SyntaxHighlighter(language="nonexistent_lang_xyz")
        assert highlighter.lexer is None

    def test_init_with_auto(self):
        """Auto should not initialize lexer until detect is called."""
        highlighter = SyntaxHighlighter(language="auto")
        assert highlighter.language == "auto"
        assert highlighter.lexer is None

    def test_init_with_none(self):
        """None should disable highlighting."""
        highlighter = SyntaxHighlighter(language=None)
        assert highlighter.language is None
        assert highlighter.lexer is None

    def test_tokenize_document_python(self):
        """Should tokenize Python code into per-line tokens."""
        highlighter = SyntaxHighlighter(language="python")
        lines = ["def hello():", "    return 42"]
        highlighter.tokenize_document(lines)

        assert len(highlighter.line_tokens) == 2
        # First line should have tokens
        assert len(highlighter.line_tokens[0]) > 0
        # Check that we have keyword 'def' token
        first_line_text = "".join(t[1] for t in highlighter.line_tokens[0])
        assert "def" in first_line_text

    def test_tokenize_document_caching(self):
        """Should cache tokenization results."""
        highlighter = SyntaxHighlighter(language="python")
        lines = ["x = 1"]
        highlighter.tokenize_document(lines)
        tokens1 = highlighter.line_tokens.copy()

        # Same content should use cache
        highlighter.tokenize_document(lines)
        assert highlighter.line_tokens == tokens1

    def test_tokenize_document_multiline_string(self):
        """Should correctly handle multi-line strings."""
        highlighter = SyntaxHighlighter(language="python")
        lines = ['"""', "docstring", '"""']
        highlighter.tokenize_document(lines)

        # Should have 3 lines of tokens
        assert len(highlighter.line_tokens) >= 3

    def test_get_line_tokens(self):
        """Should return tokens for specific line."""
        highlighter = SyntaxHighlighter(language="python")
        lines = ["x = 1", "y = 2"]
        highlighter.tokenize_document(lines)

        tokens_0 = highlighter.get_line_tokens(0)
        tokens_1 = highlighter.get_line_tokens(1)

        assert tokens_0 != tokens_1
        assert "x" in "".join(t[1] for t in tokens_0)
        assert "y" in "".join(t[1] for t in tokens_1)

    def test_get_line_tokens_out_of_bounds(self):
        """Should return empty list for out-of-bounds line."""
        highlighter = SyntaxHighlighter(language="python")
        lines = ["x = 1"]
        highlighter.tokenize_document(lines)

        assert highlighter.get_line_tokens(-1) == []
        assert highlighter.get_line_tokens(100) == []

    def test_is_highlighting_enabled(self):
        """Should report whether highlighting is enabled."""
        enabled = SyntaxHighlighter(language="python")
        disabled = SyntaxHighlighter(language=None)

        assert enabled.is_highlighting_enabled() is True
        assert disabled.is_highlighting_enabled() is False

    def test_set_language(self):
        """Should change language and clear cache."""
        highlighter = SyntaxHighlighter(language="python")
        lines = ["x = 1"]
        highlighter.tokenize_document(lines)
        assert len(highlighter.line_tokens) > 0

        highlighter.set_language("javascript")
        assert highlighter.language == "javascript"
        assert highlighter.line_tokens == []  # Cache cleared

    def test_set_theme(self):
        """Should change theme."""
        highlighter = SyntaxHighlighter(theme="monokai")
        assert highlighter.theme == "monokai"

        highlighter.set_theme("dracula")
        assert highlighter.theme == "dracula"

    def test_set_theme_invalid(self):
        """Should ignore invalid theme."""
        highlighter = SyntaxHighlighter(theme="monokai")
        highlighter.set_theme("nonexistent_theme")
        assert highlighter.theme == "monokai"  # Unchanged

    def test_detect_language_from_filename(self):
        """Should detect language from filename hint."""
        highlighter = SyntaxHighlighter(language="auto", filename_hint="test.py")
        detected = highlighter.detect_language("x = 1")
        assert detected is not None
        assert "python" in detected.lower()

    def test_invalidate_from_line(self):
        """Should mark lines as dirty."""
        highlighter = SyntaxHighlighter(language="python")
        highlighter.invalidate_from_line(5)
        assert highlighter._dirty_from_line == 5

        # Should keep minimum
        highlighter.invalidate_from_line(3)
        assert highlighter._dirty_from_line == 3


class TestCodeEditor:
    """Tests for the CodeEditor class."""

    def test_init_default(self):
        """Should initialize with default values."""
        editor = CodeEditor()
        assert editor.highlighter is not None
        assert editor.highlighter.language == "python"
        assert editor.highlighter.theme == "monokai"
        assert editor.show_line_numbers is True

    def test_init_with_language(self):
        """Should initialize with specified language."""
        editor = CodeEditor(language="javascript")
        assert editor.highlighter.language == "javascript"

    def test_init_with_value(self):
        """Should initialize with initial value."""
        code = "def hello():\n    pass"
        editor = CodeEditor(value=code)
        assert editor.get_value() == code

    def test_init_with_theme(self):
        """Should initialize with specified theme."""
        editor = CodeEditor(theme="dracula")
        assert editor.highlighter.theme == "dracula"

    def test_init_no_highlighting(self):
        """Should allow disabling highlighting."""
        editor = CodeEditor(language=None)
        assert editor.highlighter.lexer is None
        assert editor.highlighter.is_highlighting_enabled() is False

    def test_set_value_tokenizes(self):
        """Setting value should trigger tokenization."""
        editor = CodeEditor(language="python")
        editor.set_value("x = 1\ny = 2")

        # Should have tokenized the content
        assert len(editor.highlighter.line_tokens) == 2

    def test_set_language(self):
        """Should change language and re-tokenize."""
        editor = CodeEditor(language="python", value="x = 1")
        assert editor.highlighter.language == "python"

        editor.set_language("javascript")
        assert editor.highlighter.language == "javascript"

    def test_set_theme(self):
        """Should change theme."""
        editor = CodeEditor(theme="monokai")
        assert editor.highlighter.theme == "monokai"

        editor.set_theme("nord")
        assert editor.highlighter.theme == "nord"

    def test_inherits_textarea_key_handling(self):
        """Should inherit TextArea keyboard handling."""
        from wijjit.terminal.input import Keys

        editor = CodeEditor(value="hello")
        editor.cursor_col = 0  # Start at beginning
        # Arrow key should move cursor
        editor.handle_key(Keys.RIGHT)
        assert editor.cursor_col == 1  # Should have moved right

    def test_inherits_textarea_selection(self):
        """Should inherit TextArea selection methods."""
        editor = CodeEditor(value="hello world")
        editor._select_all()
        assert editor._has_selection() is True

    def test_inherits_textarea_clipboard(self):
        """Should inherit TextArea clipboard methods."""
        editor = CodeEditor(value="hello")
        editor._select_all()
        result = editor._copy_selection()
        assert result is True

    def test_line_number_width_calculation(self):
        """Should calculate line number width correctly."""
        # Few lines
        editor = CodeEditor(value="a\nb\nc")
        editor._update_line_number_width()
        assert editor.line_number_width >= 3  # "1 " + separator

        # Many lines
        big_content = "\n".join(f"line {i}" for i in range(100))
        editor2 = CodeEditor(value=big_content)
        editor2._update_line_number_width()
        assert editor2.line_number_width >= 5  # "100" + space + separator

    def test_show_line_numbers_false(self):
        """Should allow hiding line numbers."""
        editor = CodeEditor(show_line_numbers=False)
        assert editor.show_line_numbers is False
        editor._update_line_number_width()
        assert editor.line_number_width == 0

    def test_emit_change_triggers_retokenize(self):
        """Content changes should trigger re-tokenization."""
        editor = CodeEditor(language="python", value="x = 1")

        # Change the actual content (simulating an edit)
        editor.lines[0] = "y = 2"

        # Manually emit change (this would normally be called by key handlers)
        editor._emit_change("x = 1", "y = 2")

        # Since no event loop is running, immediate re-tokenization happens
        # Verify that tokens were updated to reflect the new content
        new_tokens = editor.highlighter.get_line_tokens(0)
        token_text = "".join(t[1] for t in new_tokens)
        assert "y" in token_text  # New variable name should be tokenized

    def test_auto_language_detection(self):
        """Should auto-detect language when set to auto."""
        python_code = """
import os
import sys

def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
        editor = CodeEditor(language="auto", filename_hint="script.py")
        editor.set_value(python_code)

        # With filename hint, should detect Python
        assert editor.highlighter.lexer is not None


class TestCodeEditorCopyPickle:
    """Tests for copy/pickle support."""

    def test_syntax_highlighter_deepcopy(self):
        """SyntaxHighlighter should support deepcopy."""
        import copy

        h = SyntaxHighlighter(language="python")
        h.tokenize_document(["x = 1", "y = 2"])

        h2 = copy.deepcopy(h)

        assert h2 is not h
        assert h2.language == "python"
        assert len(h2.line_tokens) == 2
        assert h2.lexer is not None

    def test_syntax_highlighter_pickle(self):
        """SyntaxHighlighter should support pickle."""
        import pickle

        h = SyntaxHighlighter(language="python")
        h.tokenize_document(["x = 1"])

        pickled = pickle.dumps(h)
        h2 = pickle.loads(pickled)

        assert h2.language == "python"
        assert h2.lexer is not None

    def test_code_editor_deepcopy(self):
        """CodeEditor should support deepcopy."""
        import copy

        editor = CodeEditor(language="python", value="x = 1")

        editor2 = copy.deepcopy(editor)

        assert editor2 is not editor
        assert editor2.get_value() == "x = 1"
        assert editor2.highlighter.language == "python"
        assert editor2.highlighter.lexer is not None
        assert editor2._retokenize_task is None

    def test_code_editor_pickle(self):
        """CodeEditor should support pickle."""
        import pickle

        editor = CodeEditor(language="python", value="x = 1")

        pickled = pickle.dumps(editor)
        editor2 = pickle.loads(pickled)

        assert editor2.get_value() == "x = 1"
        assert editor2.highlighter.language == "python"


class TestCodeEditorIntegration:
    """Integration tests for CodeEditor."""

    def test_large_file_tokenization(self):
        """Should handle large files efficiently."""
        # Create 500 lines of Python code
        lines = [f"x{i} = {i}" for i in range(500)]
        large_code = "\n".join(lines)

        editor = CodeEditor(language="python", value=large_code)

        # Should tokenize all lines
        assert len(editor.highlighter.line_tokens) == 500

    def test_multiline_constructs(self):
        """Should correctly highlight multi-line constructs."""
        code = '''def foo():
    """
    Multi-line
    docstring
    """
    return 42'''

        editor = CodeEditor(language="python", value=code)

        # Should have tokens for all lines
        assert len(editor.highlighter.line_tokens) == 6

        # The docstring lines should be part of a string token
        # (not broken into separate constructs)
        # Check that we have tokens on each line
        for i in range(6):
            assert editor.highlighter.get_line_tokens(i) is not None

    def test_theme_switching_preserves_content(self):
        """Switching themes should preserve content."""
        code = "x = 1"
        editor = CodeEditor(language="python", value=code, theme="monokai")

        editor.set_theme("dracula")
        assert editor.get_value() == code
        assert editor.highlighter.theme == "dracula"

    def test_language_switching_preserves_content(self):
        """Switching languages should preserve content."""
        code = "x = 1"
        editor = CodeEditor(language="python", value=code)

        editor.set_language("javascript")
        assert editor.get_value() == code
        assert editor.highlighter.language == "javascript"
