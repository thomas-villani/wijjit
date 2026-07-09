"""Tests for Cell class."""

import pytest

from wijjit.terminal import ansi
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


class TestCellNoColor:
    """Cells must honor the NO_COLOR standard (https://no-color.org/).

    The cell renderer is the only place the production pipeline emits SGR color
    parameters, so suppressing them here suppresses them everywhere. Text
    attributes are deliberately preserved: NO_COLOR suppresses color, not
    styling, and bold/reverse are how focus stays visible without color.
    """

    @pytest.fixture(autouse=True)
    def _restore_no_color(self):
        """Reset the module-level no-color override and env snapshot."""
        yield
        ansi._no_color = None
        ansi.refresh_no_color_from_env()

    def test_colors_suppressed_when_no_color_enabled(self):
        ansi.set_no_color(True)
        cell = Cell("A", fg_color=(255, 0, 0), bg_color=(0, 0, 255))

        assert "38;2" not in cell.to_ansi()
        assert "48;2" not in cell.to_ansi()
        assert "38;2" not in cell.get_style_codes()
        assert "48;2" not in cell.get_style_codes()

    def test_character_still_rendered_when_no_color_enabled(self):
        ansi.set_no_color(True)
        cell = Cell("A", fg_color=(255, 0, 0))

        assert cell.to_ansi().endswith("A") or "A" in cell.to_ansi()

    def test_text_attributes_survive_no_color(self):
        """Bold and reverse are the color-free focus cues; they must remain."""
        ansi.set_no_color(True)
        cell = Cell("A", fg_color=(255, 0, 0), bold=True, reverse=True)

        codes = cell.get_style_codes()
        assert "1" in codes  # bold
        assert "7" in codes  # reverse

    def test_unstyled_cell_emits_bare_char_under_no_color(self):
        ansi.set_no_color(True)
        assert Cell("A", fg_color=(255, 0, 0)).to_ansi() == "A"

    def test_colors_present_when_no_color_disabled(self):
        ansi.set_no_color(False)
        cell = Cell("A", fg_color=(255, 0, 0))

        assert "38;2;255;0;0" in cell.to_ansi()

    @pytest.mark.parametrize(
        ("env_value", "expect_disabled"),
        [
            (None, False),  # unset
            ("", False),  # present but empty: the standard says color stays ON
            ("1", True),
            ("0", True),  # any non-empty value disables color
            ("false", True),
        ],
    )
    def test_env_var_follows_no_color_standard(
        self, monkeypatch, env_value, expect_disabled
    ):
        """https://no-color.org/ - set *and non-empty* disables color."""
        if env_value is None:
            monkeypatch.delenv("NO_COLOR", raising=False)
        else:
            monkeypatch.setenv("NO_COLOR", env_value)
        ansi._no_color = None  # no explicit override; fall back to the env
        ansi.refresh_no_color_from_env()

        assert ansi.is_no_color() is expect_disabled

        has_color = "38;2;255;0;0" in Cell("A", fg_color=(255, 0, 0)).to_ansi()
        assert has_color is not expect_disabled

    def test_explicit_override_beats_env_var(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        ansi.refresh_no_color_from_env()
        ansi.set_no_color(False)

        assert ansi.is_no_color() is False
        assert "38;2;255;0;0" in Cell("A", fg_color=(255, 0, 0)).to_ansi()
