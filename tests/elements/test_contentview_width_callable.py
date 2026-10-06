"""``ContentView`` takes a function of the width as its content.

An app that lays out its own content (pre-rendered ANSI, say) needs the width
it will be shown at. ANSI content is passed through unwrapped, and the inner
width depends on the border, padding and whether a scrollbar is showing, so an
app guessing it clipped its own text. A callable ``content`` is called with
the real inner width, and again on resize.
"""

from wijjit.elements.display.contentview import ContentView
from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = (
    '{% vstack width="fill" height="fill" %}'
    '{% contentview id="body" content=state.rules content_type="ansi" width="fill" height="fill" %}'
    "{% endcontentview %}"
    "{% endvstack %}"
)


class Rules:
    """Content of ``rows`` lines, each a rule exactly as wide as asked."""

    def __init__(self, rows: int) -> None:
        self.rows = rows
        self.widths: list[int] = []

    def __call__(self, width: int) -> str:
        self.widths.append(width)
        return "\n".join("<" + "-" * (width - 2) + ">" for _ in range(self.rows))


def _rule_lines(screen: str) -> list[str]:
    """The rules on screen, cut from the first ``<`` to the last ``>``."""
    return [
        line[line.index("<") : line.rindex(">") + 1]
        for line in screen.splitlines()
        if "<" in line
    ]


def test_called_with_the_inner_width_and_shown_whole():
    rules = Rules(rows=3)
    with WijjitHarness(
        app_from_template(TEMPLATE, state={"rules": rules}), size=(40, 12)
    ) as h:
        h.tick(frames=1)
        h.assert_no_errors()
        lines = _rule_lines(h.screen())
        assert len(lines) == 3
        width = rules.widths[-1]
        assert all(len(line) == width for line in lines)
        assert 30 <= width <= 38
        assert rules.widths == [width]


def test_leaves_room_for_the_scrollbar_when_the_content_scrolls():
    rules = Rules(rows=40)
    with WijjitHarness(
        app_from_template(TEMPLATE, state={"rules": rules}), size=(40, 12)
    ) as h:
        h.tick(frames=1)
        h.assert_no_errors()
        lines = _rule_lines(h.screen())
        assert lines
        # The rule's right end survives: the scrollbar took a column of its own.
        width = rules.widths[-1]
        assert all(len(line) == width for line in lines)
        assert rules.widths == [width + 1, width]


def test_called_again_on_resize():
    rules = Rules(rows=3)
    with WijjitHarness(
        app_from_template(TEMPLATE, state={"rules": rules}), size=(40, 12)
    ) as h:
        h.tick(frames=1)
        before = rules.widths[-1]
        h.resize(60, 12)
        h.tick(frames=1)
        assert rules.widths[-1] == before + 20
        assert _rule_lines(h.screen())[0].count("-") == before + 18


def test_called_once_per_size():
    rules = Rules(rows=3)
    app = app_from_template(TEMPLATE, state={"rules": rules, "n": 0})
    with WijjitHarness(app, size=(40, 12)) as h:
        h.tick(frames=1)
        calls = len(rules.widths)
        for n in range(5):
            app.state["n"] = n + 1
            h.tick(frames=1)
        assert len(rules.widths) == calls


def test_a_bound_callable_is_not_stringified():
    rules = Rules(rows=2)
    template = '{% contentview id="rules" content_type="ansi" width=30 height=6 %}{% endcontentview %}'
    with WijjitHarness(
        app_from_template(template, state={"rules": rules}), size=(40, 12)
    ) as h:
        h.tick(frames=1)
        h.assert_no_errors()
        assert len(_rule_lines(h.screen())) == 2


def test_the_element_directly():
    view = ContentView(
        content=lambda width: "x" * width, content_type="plain", width=12, height=4
    )
    assert view.rendered_lines == ["x" * 12]
