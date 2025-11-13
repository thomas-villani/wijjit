"""Tests for Cell class."""


from wijjit.terminal.cell import Cell


class TestCell:
    """Tests for the Cell class."""

    def test_create_simple_cell(self):
        """Test creating a cell with just a character.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies basic cell creation with default styling.
        """
        cell = Cell("A")
        assert cell.char == "A"
        assert cell.fg_color is None
        assert cell.bg_color is None
        assert cell.bold is False
        assert cell.italic is False
        assert cell.underline is False
        assert cell.reverse is False
        assert cell.dim is False

    def test_create_styled_cell(self):
        """Test creating a cell with styling.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies cell creation with colors and text attributes.
        """
        cell = Cell(
            "X",
            fg_color=(255, 0, 0),
            bg_color=(0, 0, 255),
            bold=True,
            italic=True,
        )
        assert cell.char == "X"
        assert cell.fg_color == (255, 0, 0)
        assert cell.bg_color == (0, 0, 255)
        assert cell.bold is True
        assert cell.italic is True

    def test_cell_equality(self):
        """Test cell equality comparison.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies that cells with identical properties are equal.
        """
        cell1 = Cell("A", fg_color=(255, 0, 0), bold=True)
        cell2 = Cell("A", fg_color=(255, 0, 0), bold=True)
        cell3 = Cell("A", fg_color=(0, 255, 0), bold=True)  # Different color

        assert cell1 == cell2
        assert cell1 != cell3

    def test_cell_inequality_different_char(self):
        """Test cell inequality with different characters.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies that cells with different characters are not equal.
        """
        cell1 = Cell("A")
        cell2 = Cell("B")
        assert cell1 != cell2

    def test_cell_inequality_different_type(self):
        """Test cell inequality with different type.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies that cells are not equal to non-Cell objects.
        """
        cell = Cell("A")
        assert cell != "A"
        assert cell is not None
        assert cell != 42

    def test_to_ansi_no_styling(self):
        """Test ANSI conversion for unstyled cell.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies that unstyled cells convert to plain character.
        """
        cell = Cell("A")
        assert cell.to_ansi() == "A"

    def test_to_ansi_with_bold(self):
        """Test ANSI conversion with bold attribute.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies ANSI escape sequences for bold text.
        """
        cell = Cell("A", bold=True)
        ansi = cell.to_ansi()
        assert "\x1b[" in ansi
        assert "1" in ansi  # Bold code
        assert "A" in ansi
        assert "\x1b[0m" in ansi  # Reset

    def test_to_ansi_with_color(self):
        """Test ANSI conversion with RGB color.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies ANSI escape sequences for true color RGB.
        """
        cell = Cell("X", fg_color=(255, 0, 0))
        ansi = cell.to_ansi()
        assert "\x1b[" in ansi
        assert "38;2;255;0;0" in ansi  # True color foreground
        assert "X" in ansi
        assert "\x1b[0m" in ansi

    def test_to_ansi_with_bg_color(self):
        """Test ANSI conversion with background color.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies ANSI escape sequences for background colors.
        """
        cell = Cell("Y", bg_color=(0, 255, 0))
        ansi = cell.to_ansi()
        assert "48;2;0;255;0" in ansi  # True color background
        assert "Y" in ansi

    def test_to_ansi_with_multiple_attributes(self):
        """Test ANSI conversion with multiple attributes.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies ANSI escape sequences combine correctly.
        """
        cell = Cell(
            "Z",
            fg_color=(255, 255, 0),
            bg_color=(0, 0, 255),
            bold=True,
            italic=True,
            underline=True,
        )
        ansi = cell.to_ansi()
        assert "1" in ansi  # Bold
        assert "3" in ansi  # Italic
        assert "4" in ansi  # Underline
        assert "38;2;255;255;0" in ansi  # FG color
        assert "48;2;0;0;255" in ansi  # BG color
        assert "Z" in ansi

    def test_clone(self):
        """Test cell cloning.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies that cloned cells are equal but separate objects.
        """
        cell1 = Cell("A", fg_color=(255, 0, 0), bold=True)
        cell2 = cell1.clone()

        assert cell1 == cell2
        assert cell1 is not cell2  # Different objects

        # Modify clone shouldn't affect original
        cell2.char = "B"
        assert cell1.char == "A"
        assert cell2.char == "B"

    def test_empty_character(self):
        """Test cell with empty character string.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies that empty character cells work correctly.
        """
        cell = Cell("")
        assert cell.char == ""
        assert cell.to_ansi() == ""

    def test_reverse_attribute(self):
        """Test ANSI conversion with reverse video.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies reverse video attribute in ANSI output.
        """
        cell = Cell("R", reverse=True)
        ansi = cell.to_ansi()
        assert "7" in ansi  # Reverse video code

    def test_dim_attribute(self):
        """Test ANSI conversion with dim attribute.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Verifies dim attribute in ANSI output.
        """
        cell = Cell("D", dim=True)
        ansi = cell.to_ansi()
        assert "2" in ansi  # Dim code
