"""Tests for the ANSI adapter module."""

from wijjit.rendering.ansi_adapter import ansi_string_to_cells


class TestAnsiStringToCells:
    """Test ansi_string_to_cells function."""

    def test_plain_text(self):
        """Test parsing plain text without ANSI codes.

        Returns
        -------
        None
        """
        cells = ansi_string_to_cells("Hello")

        assert len(cells) == 5
        assert cells[0].char == "H"
        assert cells[1].char == "e"
        assert cells[2].char == "l"
        assert cells[3].char == "l"
        assert cells[4].char == "o"

    def test_simple_color(self):
        """Test parsing text with simple foreground color.

        Returns
        -------
        None
        """
        cells = ansi_string_to_cells("\x1b[31mRed\x1b[0m")

        assert len(cells) == 3
        assert cells[0].char == "R"
        assert cells[1].char == "e"
        assert cells[2].char == "d"
        # All cells should have red color
        assert cells[0].fg_color is not None
        assert cells[1].fg_color is not None
        assert cells[2].fg_color is not None

    def test_bold_text(self):
        """Test parsing bold text.

        Returns
        -------
        None
        """
        cells = ansi_string_to_cells("\x1b[1mBold\x1b[0m")

        assert len(cells) == 4
        assert cells[0].bold is True
        assert cells[1].bold is True
        assert cells[2].bold is True
        assert cells[3].bold is True

    def test_csi_cursor_movement_stripped(self):
        """Test that CSI cursor movement sequences are stripped.

        Returns
        -------
        None
        """
        # ESC[H is cursor home, should be stripped
        cells = ansi_string_to_cells("Hello\x1b[HWorld")

        # Should only get "HelloWorld" - cursor movement stripped
        assert len(cells) == 10
        assert "".join(c.char for c in cells) == "HelloWorld"

    def test_osc_hyperlink_stripped(self):
        """Test that OSC hyperlink sequences are stripped (Issue 22 regression).

        Returns
        -------
        None
        """
        # OSC 8 hyperlink format: ESC]8;;URL ESC\ text ESC]8;; ESC\
        text_with_link = "Click \x1b]8;;http://example.com\x07here\x1b]8;;\x07 now"
        cells = ansi_string_to_cells(text_with_link)

        # Should get "Click here now" - OSC sequences stripped
        result = "".join(c.char for c in cells)
        assert result == "Click here now"
        assert len(cells) == 14  # "Click here now" = 14 chars

    def test_osc_with_st_terminator(self):
        """Test OSC sequences terminated with ST (ESC backslash).

        Returns
        -------
        None
        """
        # OSC can be terminated with ESC\ (ST) instead of BEL
        text_with_osc = "Test \x1b]0;Window Title\x1b\\ text"
        cells = ansi_string_to_cells(text_with_osc)

        # Should get "Test  text" - OSC stripped
        result = "".join(c.char for c in cells)
        assert result == "Test  text"

    def test_osc_color_definition_stripped(self):
        """Test that OSC color definition sequences are stripped.

        Returns
        -------
        None
        """
        # OSC 4 color definition
        text = "Color\x1b]4;1;rgb:ff/00/00\x07 text"
        cells = ansi_string_to_cells(text)

        result = "".join(c.char for c in cells)
        assert result == "Color text"

    def test_mixed_sgr_and_osc(self):
        """Test text with both SGR styling and OSC sequences.

        Returns
        -------
        None
        """
        # Combine color codes with OSC hyperlink
        text = "\x1b[31m\x1b]8;;http://example.com\x07Red link\x1b]8;;\x07\x1b[0m"
        cells = ansi_string_to_cells(text)

        result = "".join(c.char for c in cells)
        assert result == "Red link"
        # First cell should be red
        assert cells[0].fg_color is not None

    def test_empty_string(self):
        """Test parsing empty string.

        Returns
        -------
        None
        """
        cells = ansi_string_to_cells("")

        assert len(cells) == 0

    def test_only_escape_sequences(self):
        """Test string with only escape sequences and no text.

        Returns
        -------
        None
        """
        cells = ansi_string_to_cells("\x1b[31m\x1b]8;;http://example.com\x07\x1b[0m")

        # No actual characters, only escape sequences
        assert len(cells) == 0

    def test_true_color_rgb(self):
        """Test parsing true color RGB sequences.

        Returns
        -------
        None
        """
        # True color format: ESC[38;2;R;G;Bm
        cells = ansi_string_to_cells("\x1b[38;2;255;128;64mRGB\x1b[0m")

        assert len(cells) == 3
        assert cells[0].fg_color == (255, 128, 64)
        assert cells[1].fg_color == (255, 128, 64)
        assert cells[2].fg_color == (255, 128, 64)

    def test_multiple_osc_sequences(self):
        """Test text with multiple OSC sequences.

        Returns
        -------
        None
        """
        text = (
            "\x1b]0;Title\x07"
            "Start "
            "\x1b]8;;http://link1.com\x07link1\x1b]8;;\x07"
            " and "
            "\x1b]8;;http://link2.com\x07link2\x1b]8;;\x07"
            " end"
        )
        cells = ansi_string_to_cells(text)

        result = "".join(c.char for c in cells)
        assert result == "Start link1 and link2 end"
