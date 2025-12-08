"""Tests for autocomplete utilities."""


from wijjit.autocomplete.utils import (
    get_word_at_cursor,
    get_word_boundaries,
    is_word_char,
    replace_word_at_cursor,
    split_into_words,
)


class TestGetWordAtCursor:
    """Tests for get_word_at_cursor function."""

    def test_word_at_end(self):
        """Test extracting word when cursor is at end."""
        word, start, end = get_word_at_cursor("hello", 5)
        assert word == "hello"
        assert start == 0
        assert end == 5

    def test_word_in_middle_of_sentence(self):
        """Test extracting word from middle of sentence."""
        word, start, end = get_word_at_cursor("hello world foo", 11)
        assert word == "world"
        assert start == 6
        assert end == 11

    def test_partial_word(self):
        """Test extracting partial word (cursor in middle).

        "hello world" with cursor at position 8:
        h e l l o   w o | r l d
        0 1 2 3 4 5 6 7 8 9 10

        Cursor is before 'r', so word up to cursor is "wo".
        """
        word, start, end = get_word_at_cursor("hello world", 8)
        assert word == "wo"  # Text from start to cursor position
        assert start == 6
        assert end == 8

    def test_cursor_after_space(self):
        """Test cursor after space returns empty."""
        word, start, end = get_word_at_cursor("hello ", 6)
        assert word == ""
        assert start == 6
        assert end == 6

    def test_empty_text(self):
        """Test empty text returns empty."""
        word, start, end = get_word_at_cursor("", 0)
        assert word == ""
        assert start == 0
        assert end == 0

    def test_cursor_at_zero(self):
        """Test cursor at position 0 returns empty."""
        word, start, end = get_word_at_cursor("hello", 0)
        assert word == ""
        assert start == 0
        assert end == 0

    def test_cursor_clamped_to_length(self):
        """Test cursor position clamped to text length."""
        word, start, end = get_word_at_cursor("hi", 100)
        assert word == "hi"
        assert start == 0
        assert end == 2

    def test_underscores_are_word_chars(self):
        """Test that underscores are treated as word characters."""
        word, start, end = get_word_at_cursor("hello_world", 11)
        assert word == "hello_world"
        assert start == 0
        assert end == 11

    def test_numbers_are_word_chars(self):
        """Test that numbers are treated as word characters."""
        word, start, end = get_word_at_cursor("test123", 7)
        assert word == "test123"
        assert start == 0
        assert end == 7

    def test_punctuation_breaks_word(self):
        """Test that punctuation breaks words."""
        word, start, end = get_word_at_cursor("hello,world", 5)
        assert word == "hello"
        assert start == 0
        assert end == 5

    def test_cursor_after_punctuation(self):
        """Test cursor right after punctuation."""
        word, start, end = get_word_at_cursor("hello,", 6)
        assert word == ""
        assert start == 6
        assert end == 6

    def test_multiple_spaces(self):
        """Test multiple spaces between words."""
        word, start, end = get_word_at_cursor("hello   world", 10)
        assert word == "wo"
        assert start == 8
        assert end == 10

    def test_special_characters(self):
        """Test various special characters."""
        # Dash breaks word
        word, start, end = get_word_at_cursor("hello-world", 5)
        assert word == "hello"
        assert start == 0
        assert end == 5

        # At sign breaks word
        word, start, end = get_word_at_cursor("user@domain", 4)
        assert word == "user"
        assert start == 0
        assert end == 4


class TestReplaceWordAtCursor:
    """Tests for replace_word_at_cursor function."""

    def test_replace_complete_word(self):
        """Test replacing a complete word."""
        new_text, new_cursor = replace_word_at_cursor("hel", 3, "hello")
        assert new_text == "hello"
        assert new_cursor == 5

    def test_replace_word_in_sentence(self):
        """Test replacing word in middle of sentence."""
        new_text, new_cursor = replace_word_at_cursor("say hel to me", 7, "hello")
        assert new_text == "say hello to me"
        assert new_cursor == 9

    def test_replace_at_end(self):
        """Test replacing word at end of text."""
        new_text, new_cursor = replace_word_at_cursor("the quick bro", 13, "brown")
        assert new_text == "the quick brown"
        assert new_cursor == 15

    def test_replace_at_start(self):
        """Test replacing word at start of text."""
        new_text, new_cursor = replace_word_at_cursor("app is cool", 3, "application")
        assert new_text == "application is cool"
        assert new_cursor == 11

    def test_replace_empty_word(self):
        """Test replacing at position with no word (after space)."""
        new_text, new_cursor = replace_word_at_cursor("hello ", 6, "world")
        assert new_text == "hello world"
        assert new_cursor == 11

    def test_replace_with_empty_string(self):
        """Test replacing with empty string (deletion)."""
        new_text, new_cursor = replace_word_at_cursor("hello world", 5, "")
        assert new_text == " world"
        assert new_cursor == 0

    def test_cursor_position_after_replace(self):
        """Test cursor is placed at end of replacement."""
        new_text, new_cursor = replace_word_at_cursor("a", 1, "abc")
        assert new_text == "abc"
        assert new_cursor == 3


class TestIsWordChar:
    """Tests for is_word_char function."""

    def test_letters(self):
        """Test letters are word characters."""
        assert is_word_char("a") is True
        assert is_word_char("z") is True
        assert is_word_char("A") is True
        assert is_word_char("Z") is True

    def test_numbers(self):
        """Test numbers are word characters."""
        assert is_word_char("0") is True
        assert is_word_char("9") is True

    def test_underscore(self):
        """Test underscore is a word character."""
        assert is_word_char("_") is True

    def test_non_word_chars(self):
        """Test non-word characters."""
        assert is_word_char(" ") is False
        assert is_word_char("-") is False
        assert is_word_char(".") is False
        assert is_word_char(",") is False
        assert is_word_char("@") is False
        assert is_word_char("!") is False


class TestGetWordBoundaries:
    """Tests for get_word_boundaries function."""

    def test_cursor_in_middle_of_word(self):
        """Test getting boundaries with cursor in middle."""
        start, end = get_word_boundaries("hello world", 2)
        assert start == 0
        assert end == 5

    def test_cursor_at_word_start(self):
        """Test cursor at word start."""
        start, end = get_word_boundaries("hello world", 6)
        assert start == 6
        assert end == 11

    def test_cursor_at_word_end(self):
        """Test cursor at word end."""
        start, end = get_word_boundaries("hello world", 5)
        assert start == 0
        assert end == 5

    def test_cursor_between_words(self):
        """Test cursor on space between words."""
        start, end = get_word_boundaries("hello  world", 6)
        # On a space, boundaries should just be that position
        assert start == 6
        assert end == 6

    def test_empty_text(self):
        """Test empty text."""
        start, end = get_word_boundaries("", 0)
        assert start == 0
        assert end == 0

    def test_cursor_clamped(self):
        """Test cursor position is clamped."""
        start, end = get_word_boundaries("hi", 100)
        assert start == 0
        assert end == 2


class TestSplitIntoWords:
    """Tests for split_into_words function."""

    def test_simple_sentence(self):
        """Test splitting simple sentence."""
        words = split_into_words("hello world")
        assert words == [("hello", 0, 5), ("world", 6, 11)]

    def test_multiple_separators(self):
        """Test multiple separator types."""
        words = split_into_words("one,two;three")
        assert words == [("one", 0, 3), ("two", 4, 7), ("three", 8, 13)]

    def test_multiple_spaces(self):
        """Test multiple spaces between words."""
        words = split_into_words("hello   world")
        assert words == [("hello", 0, 5), ("world", 8, 13)]

    def test_leading_trailing_spaces(self):
        """Test leading and trailing spaces."""
        words = split_into_words("  hello world  ")
        assert words == [("hello", 2, 7), ("world", 8, 13)]

    def test_empty_string(self):
        """Test empty string."""
        words = split_into_words("")
        assert words == []

    def test_only_spaces(self):
        """Test string with only spaces."""
        words = split_into_words("   ")
        assert words == []

    def test_single_word(self):
        """Test single word."""
        words = split_into_words("hello")
        assert words == [("hello", 0, 5)]

    def test_underscores_in_words(self):
        """Test words with underscores."""
        words = split_into_words("hello_world foo_bar")
        assert words == [("hello_world", 0, 11), ("foo_bar", 12, 19)]

    def test_numbers_in_words(self):
        """Test words with numbers."""
        words = split_into_words("test123 456abc")
        assert words == [("test123", 0, 7), ("456abc", 8, 14)]
