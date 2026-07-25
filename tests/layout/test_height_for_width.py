"""Tests for width-aware height measurement.

The constraint pass measures bottom-up, before any width is known, so a text
line that will wrap was measured as a single row. It was then allocated a single
row and painted its continuation lines over whatever sibling sat beneath it - so
the wrapped remainder *and* the next widget silently disappeared.
``get_height_for_width`` re-measures on the way down, once a width is settled.
"""

from wijjit.elements.base import TextElement
from wijjit.layout.engine import ElementNode, VStack
from wijjit.testing import WijjitHarness, app_from_template


class TestTextElementHeightForWidth:
    """The element-level measurement."""

    LONG = "This is a fairly long sentence that must wrap across several lines."

    def test_wrapping_text_reports_its_wrapped_row_count(self):
        element = TextElement(text=self.LONG)
        assert element.get_intrinsic_size()[1] == 1
        assert element.get_height_for_width(20) > 1

    def test_narrower_width_needs_more_rows(self):
        element = TextElement(text=self.LONG)
        assert element.get_height_for_width(20) > element.get_height_for_width(40)

    def test_width_that_fits_matches_the_intrinsic_height(self):
        element = TextElement(text="short")
        assert element.get_height_for_width(40) == element.get_intrinsic_size()[1]

    def test_multiple_lines_are_each_wrapped(self):
        element = TextElement(text=f"{self.LONG}\nAFTER")
        # Every wrapped row of the long line, plus one for AFTER.
        assert element.get_height_for_width(30) == (
            TextElement(text=self.LONG).get_height_for_width(30) + 1
        )

    def test_blank_lines_still_occupy_a_row(self):
        assert TextElement(text="a\n\nb").get_height_for_width(40) == 3

    def test_wrapping_disabled_reports_the_intrinsic_height(self):
        element = TextElement(text=self.LONG, wrap=False)
        assert element.get_height_for_width(10) == 1

    def test_zero_width_falls_back_to_the_intrinsic_height(self):
        assert TextElement(text=self.LONG).get_height_for_width(0) == 1


class TestNodeHeightForWidth:
    """The layout-node measurement, which has to recurse."""

    def test_element_node_defers_to_its_element(self):
        text = "word " * 30
        node = ElementNode(TextElement(text=text), width="fill", height="auto")
        node.calculate_constraints()
        assert node.get_height_for_width(20) > 1

    def test_fixed_height_is_not_re_measured(self):
        node = ElementNode(TextElement(text="word " * 30), width="fill", height=3)
        node.calculate_constraints()
        assert node.get_height_for_width(20) == 3

    def test_vstack_sums_its_children_and_adds_padding(self):
        stack = VStack(
            children=[
                ElementNode(TextElement(text="a"), width="fill", height="auto"),
                ElementNode(TextElement(text="b"), width="fill", height="auto"),
            ],
            spacing=1,
            padding=1,
        )
        stack.calculate_constraints()
        # 2 rows of text + 1 spacing + 2 padding.
        assert stack.get_height_for_width(20) == 5

    def test_vstack_grows_when_a_child_wraps(self):
        stack = VStack(
            children=[
                ElementNode(
                    TextElement(text="word " * 20), width="fill", height="auto"
                )
            ],
        )
        stack.calculate_constraints()
        assert stack.get_height_for_width(20) > stack.get_height_for_width(80)


class TestWrappedTextEndToEnd:
    """The bug as a user hits it: a wrapped line eating its sibling."""

    TEMPLATE = """
{% frame title="T" width=40 height=14 %}
  {% vstack spacing=1 padding=1 %}
    This is a fairly long sentence that must wrap across more than one line.
    AFTER
  {% endvstack %}
{% endframe %}
"""

    def _screen(self):
        app = app_from_template(self.TEMPLATE)
        with WijjitHarness(app, size=(60, 20)) as harness:
            harness.tick()
            return harness.screen()

    def test_the_whole_sentence_renders(self):
        screen = self._screen()
        # The final wrapped fragment used to be cut off with the row it needed.
        assert "one line." in screen

    def test_the_following_sibling_survives(self):
        # The wrapped continuation used to be painted over AFTER's row.
        assert "AFTER" in self._screen()
