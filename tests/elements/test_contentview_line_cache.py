"""``ContentView`` parses each rendered ANSI line once, not every frame.

The rendered content was cached, but painting turned every visible line back
into cells (``ansi_string_to_cells``) on every frame: a few milliseconds a
frame for a full-screen document, and again for every click or hover lookup.
The parsed cells are now cached by line.
"""

import pytest

from wijjit.rendering import ansi_adapter
from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = (
    '{% vstack width="fill" height="fill" %}'
    '{% contentview id="doc" content=state.doc content_type="ansi" '
    'width="fill" height="fill" %}{% endcontentview %}'
    "{% endvstack %}"
)

DOC = "\n".join(f"\x1b[1mline {n:03d}\x1b[0m body text" for n in range(200))


@pytest.fixture
def parses(monkeypatch):
    """Count the lines handed to the ANSI parser."""
    seen: list[str] = []
    real = ansi_adapter.ansi_string_to_cells

    def counting(line):
        seen.append(line)
        return real(line)

    monkeypatch.setattr(ansi_adapter, "ansi_string_to_cells", counting)
    return seen


def _drive(doc=DOC):
    return WijjitHarness(app_from_template(TEMPLATE, state={"doc": doc}), size=(60, 20))


def test_idle_frames_parse_nothing(parses):
    with _drive() as h:
        h.assert_text("line 000")
        first = len(parses)
        assert first > 0
        h.tick(frames=5)
        h.press("tab")  # focus change: repaints the border, not the content
        assert len(parses) == first


def test_scrolling_parses_only_the_newly_shown_lines(parses):
    with _drive() as h:
        view = h.app.get_element_by_id("doc")
        visible = view._get_content_height()
        before = len(parses)
        h.scroll(5, 5, "down", amount=3)
        h.assert_text("line 003")

        assert len(parses) - before == 3
        assert len(set(parses)) == len(parses)  # no line parsed twice
        assert visible > 3


def test_changed_content_is_never_served_stale():
    with _drive() as h:
        h.assert_text("line 000")
        h.app.state["doc"] = DOC.replace("body text", "new words")
        h.tick()
        h.assert_text("line 000 new words")
        assert "body text" not in h.screen()


def test_cache_is_bounded_for_content_that_keeps_changing():
    with _drive("start") as h:
        view = h.app.get_element_by_id("doc")
        for n in range(400):
            h.app.state["doc"] = f"frame {n}"
            h.tick()
        h.assert_text("frame 399")
        assert len(view._line_cell_cache) <= 257


def test_position_lookup_reuses_the_cache(parses):
    with _drive() as h:
        view = h.app.get_element_by_id("doc")
        before = len(parses)
        x, y = view.bounds.x + 2, view.bounds.y + 2
        for _ in range(10):
            assert view.content_position_at(x, y) == (1, 1)
        assert len(parses) == before
