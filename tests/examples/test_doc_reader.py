"""The document reader demo: links, jumps and hover, driven end to end.

``examples/apps/doc_reader.py`` is the showcase for three ContentView features
(OSC 8 links, click positions, hover), so a regression in any of them should
fail here, not in front of a user.
"""

from pathlib import Path

import pytest

from wijjit.testing import WijjitHarness, load_example_app

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "apps" / "doc_reader.py"


@pytest.fixture
def h():
    with WijjitHarness(load_example_app(EXAMPLE), size=(110, 30)) as harness:
        yield harness


def _find(h, text):
    """Screen cell of the first occurrence of ``text``."""
    for y, line in enumerate(h.screen().splitlines()):
        if text in line:
            return line.index(text), y
    raise AssertionError(f"{text!r} not on screen:\n{h.screen()}")


def _status(h):
    return h.screen().splitlines()[-1]


def _scroll(h):
    return h.app.get_element_by_id("doc").scroll_position


def test_in_document_link_jumps_to_its_section(h):
    x, y = _find(h, "how links work")
    h.click(x + 1, y)

    assert "Jumped to: How links work" in _status(h)
    assert _scroll(h) > 0
    _, top = _find(h, "Reader")
    assert "How links work" in h.screen().splitlines()[top + 1]


def test_back_to_top_reaches_the_title(h):
    h.scroll(60, 10, "down", amount=12)
    x, y = _find(h, "top.")
    h.click(x, y)

    assert _scroll(h) == 0
    assert "Jumped to: Wijjit Is Just Jinja In Terminal" in _status(h)


def test_hover_shows_link_targets_and_clears(h):
    x, y = _find(h, "Wijjit repository")
    h.hover(x + 1, y)
    assert "Link: https://github.com/thomas-villani/wijjit" in _status(h)

    x, y = _find(h, "what the app sees")
    h.hover(x + 1, y)
    assert "Jump to: What the app sees" in _status(h)

    h.hover(1, 1)  # off the document
    assert "Hover a link" in _status(h)


def test_external_links_reach_the_terminal_but_anchors_do_not(h):
    emitted = h.emitted_ansi()

    assert "https://github.com/thomas-villani/wijjit\x1b\\" in emitted
    # In-document targets have no scheme, so HYPERLINK_SCHEMES keeps them out.
    assert ";#how-links-work" not in emitted


def test_external_link_click_is_left_to_the_terminal(h):
    x, y = _find(h, "Wijjit repository")
    h.click(x + 1, y)

    assert "Ctrl+click opens it in your terminal" in _status(h)
    assert _scroll(h) == 0


def test_outline_enter_jumps(h):
    # The outline has autofocus, so the keyboard starts there.
    h.press("down").press("down").press("enter")

    assert "Jumped to: What the app sees" in _status(h)
    assert _scroll(h) > 0
    h.assert_no_errors()
