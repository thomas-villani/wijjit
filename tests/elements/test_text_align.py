"""Tests for TextElement horizontal alignment (left/center/right)."""

from tests.helpers import render_element
from wijjit.elements.base import TextElement
from wijjit.layout.bounds import Bounds


def _render(text, align, width=20, height=1, **kwargs):
    """Render a TextElement at a fixed width and return the first line."""
    element = TextElement(text, align=align, **kwargs)
    element.set_bounds(Bounds(0, 0, width, height))
    output = render_element(element, width=width, height=height)
    return output.splitlines()[0] if output.splitlines() else ""


class TestTextAlign:
    """Alignment of plain text within a wider-than-content element."""

    def test_default_is_left(self):
        assert TextElement("hi").align == "left"

    def test_normalizes_unknown_and_case(self):
        assert TextElement("hi", align="RIGHT").align == "right"
        assert TextElement("hi", align="bogus").align == "left"
        assert TextElement("hi", align=None).align == "left"

    def test_left_alignment(self):
        line = _render("abc", "left", width=10)
        assert line.startswith("abc")

    def test_right_alignment(self):
        line = _render("abc", "right", width=10)
        # Text pushed to the right edge of the 10-wide element.
        assert line.rstrip().endswith("abc")
        assert line.startswith(" ")
        assert line.index("abc") == 7

    def test_center_alignment(self):
        line = _render("abc", "center", width=11)
        # (11 - 3) // 2 == 4 leading spaces.
        assert line.index("abc") == 4

    def test_no_offset_when_text_fills_width(self):
        line = _render("abcdefghij", "right", width=10)
        assert line.startswith("abcdefghij")

    def test_per_line_alignment_multiline(self):
        element = TextElement("a\nbb", align="right", wrap=False)
        element.set_bounds(Bounds(0, 0, 6, 2))
        output = render_element(element, width=6, height=2)
        lines = output.splitlines()
        assert lines[0].rstrip().endswith("a")
        assert lines[0].index("a") == 5
        assert lines[1].rstrip().endswith("bb")
        assert lines[1].index("bb") == 4


class TestTextAlignHtml:
    """Alignment also applies to HTML-rendered text."""

    def test_right_align_html(self):
        element = TextElement("<b>hi</b>", align="right", html=True, wrap=False)
        element.set_bounds(Bounds(0, 0, 10, 1))
        output = render_element(element, width=10, height=1)
        line = output.splitlines()[0]
        assert line.rstrip().endswith("hi")
        assert line.index("hi") == 8
