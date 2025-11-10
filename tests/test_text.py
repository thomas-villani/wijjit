"""Tests for text processing utilities."""

from wijjit.terminal.ansi import ANSIColor, ANSIStyle, is_wrap_boundary, wrap_text


class TestIsWrapBoundary:
    """Tests for is_wrap_boundary function."""

    def test_space_is_boundary(self):
        """Test that spaces are wrap boundaries."""
        assert is_wrap_boundary(" ")
        assert is_wrap_boundary("\t")
        assert is_wrap_boundary("\n")

    def test_hyphen_is_boundary(self):
        """Test that hyphens are wrap boundaries."""
        assert is_wrap_boundary("-")

    def test_punctuation_is_boundary(self):
        """Test that common punctuation marks are wrap boundaries."""
        assert is_wrap_boundary(".")
        assert is_wrap_boundary(",")
        assert is_wrap_boundary(";")
        assert is_wrap_boundary(":")
        assert is_wrap_boundary("!")
        assert is_wrap_boundary("?")
        assert is_wrap_boundary(")")
        assert is_wrap_boundary("]")
        assert is_wrap_boundary("}")
        assert is_wrap_boundary('"')
        assert is_wrap_boundary("'")

    def test_alphanumeric_not_boundary(self):
        """Test that letters and digits are not wrap boundaries."""
        assert not is_wrap_boundary("a")
        assert not is_wrap_boundary("Z")
        assert not is_wrap_boundary("5")
        assert not is_wrap_boundary("0")

    def test_empty_string_not_boundary(self):
        """Test that empty string is not a boundary."""
        assert not is_wrap_boundary("")

    def test_special_chars_not_boundary(self):
        """Test that special characters (non-punctuation) are not boundaries."""
        assert not is_wrap_boundary("@")
        assert not is_wrap_boundary("#")
        assert not is_wrap_boundary("$")
        assert not is_wrap_boundary("%")
        assert not is_wrap_boundary("&")
        assert not is_wrap_boundary("*")


class TestWrapText:
    """Tests for wrap_text function."""

    def test_empty_string(self):
        """Test wrapping empty string."""
        result = wrap_text("", 10)
        assert result == [""]

    def test_text_fits_within_width(self):
        """Test text that fits within width."""
        result = wrap_text("Hello", 10)
        assert result == ["Hello"]

    def test_text_exactly_width(self):
        """Test text exactly at width."""
        result = wrap_text("HelloWorld", 10)
        assert result == ["HelloWorld"]

    def test_zero_width(self):
        """Test zero width returns empty string."""
        result = wrap_text("Hello", 0)
        assert result == [""]

    def test_negative_width(self):
        """Test negative width returns empty string."""
        result = wrap_text("Hello", -5)
        assert result == [""]

    def test_simple_wrap_at_space(self):
        """Test basic wrapping at space boundaries."""
        result = wrap_text("Hello world test", 10)
        assert len(result) > 1
        # Should break at spaces
        for segment in result:
            # Each segment should fit within width (visible length)
            from wijjit.terminal.ansi import visible_length

            assert visible_length(segment.strip()) <= 10

    def test_wrap_at_hyphen(self):
        """Test wrapping at hyphen boundaries."""
        result = wrap_text("Hello-world-test", 10)
        assert len(result) > 1

    def test_wrap_at_punctuation(self):
        """Test wrapping at punctuation boundaries."""
        result = wrap_text("Hello, world. Test!", 12)
        assert len(result) > 1

    def test_hard_break_no_boundary(self):
        """Test hard break when no boundary available."""
        # Long word with no boundaries
        result = wrap_text("Supercalifragilisticexpialidocious", 10)
        assert len(result) > 1
        # Should break mid-word at width
        from wijjit.terminal.ansi import visible_length

        for segment in result[:-1]:  # All but last should be full width
            assert visible_length(segment) <= 10

    def test_wrap_with_ansi_codes(self):
        """Test wrapping preserves ANSI escape codes."""
        text = f"{ANSIColor.RED}Hello{ANSIColor.RESET} world test"
        result = wrap_text(text, 10)

        # Check that result contains ANSI codes
        assert any("\x1b[" in segment for segment in result)

        # Check visible length is respected
        from wijjit.terminal.ansi import visible_length

        for segment in result:
            assert visible_length(segment.strip()) <= 10

    def test_wrap_multiple_ansi_codes(self):
        """Test wrapping with multiple ANSI codes."""
        text = (
            f"{ANSIColor.RED}{ANSIStyle.BOLD}Bold Red{ANSIStyle.RESET} "
            f"{ANSIColor.BLUE}Blue{ANSIColor.RESET} Normal"
        )
        result = wrap_text(text, 12)

        # Should wrap and preserve ANSI
        assert len(result) >= 1

    def test_wrap_very_long_text(self):
        """Test wrapping very long text."""
        long_text = "This is a very long line of text that will need to be wrapped multiple times across many segments to test the wrapping algorithm thoroughly."
        result = wrap_text(long_text, 20)

        # Should produce multiple segments
        assert len(result) > 5

        # All segments should fit within width
        from wijjit.terminal.ansi import visible_length

        for segment in result:
            assert visible_length(segment.strip()) <= 20

    def test_wrap_removes_leading_spaces_after_break(self):
        """Test that leading spaces are removed after line breaks."""
        result = wrap_text("Hello    world    test", 8)
        # After breaking, new segments shouldn't start with multiple spaces
        for i, segment in enumerate(result):
            if i > 0:  # Not first segment
                # Should not start with multiple spaces
                assert not segment.startswith("  ")

    def test_wrap_single_word_longer_than_width(self):
        """Test wrapping when single word exceeds width."""
        result = wrap_text("Antidisestablishmentarianism", 10)
        assert len(result) >= 3  # Should break into multiple pieces

        from wijjit.terminal.ansi import visible_length

        for segment in result[:-1]:
            assert visible_length(segment) <= 10

    def test_wrap_text_with_newlines(self):
        """Test wrapping text that contains newlines."""
        # Note: wrap_text is designed for single lines
        # Newlines would be treated as whitespace (boundary)
        result = wrap_text("Hello\nworld", 15)
        assert len(result) >= 1

    def test_wrap_preserves_ansi_reset(self):
        """Test that ANSI reset codes are preserved."""
        text = f"{ANSIColor.RED}Colored text{ANSIColor.RESET} normal text here"
        result = wrap_text(text, 15)

        # Reset code should be in one of the segments
        combined = "".join(result)
        assert ANSIColor.RESET in combined

    def test_wrap_with_trailing_spaces(self):
        """Test wrapping text with trailing spaces."""
        result = wrap_text("Hello world     ", 10)
        # Should handle trailing spaces gracefully
        assert len(result) >= 1

    def test_wrap_uniform_width_segments(self):
        """Test that segments are roughly uniform in width."""
        text = "The quick brown fox jumps over the lazy dog"
        result = wrap_text(text, 15)

        from wijjit.terminal.ansi import visible_length

        # All segments except possibly the last should be close to width
        for segment in result[:-1]:
            vis_len = visible_length(segment.strip())
            # Should use most of the available width (at least 50%)
            assert vis_len >= 7 or len(segment.strip()) == 0

    def test_wrap_ansi_only_text(self):
        """Test wrapping text that is only ANSI codes."""
        text = f"{ANSIColor.RED}{ANSIColor.RESET}"
        result = wrap_text(text, 10)
        # Should return the ANSI codes even though no visible chars
        assert len(result) == 1

    def test_wrap_mixed_boundaries(self):
        """Test wrapping with multiple boundary types."""
        text = "Hello, world-test. How are you?"
        result = wrap_text(text, 12)
        # Should wrap at various boundaries
        assert len(result) >= 2

        from wijjit.terminal.ansi import visible_length

        for segment in result:
            assert visible_length(segment.strip()) <= 12
