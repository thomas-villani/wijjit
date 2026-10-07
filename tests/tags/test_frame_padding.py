"""The frame tag's ``padding`` attribute reaches the rendered frame.

The tag stores padding in the VNode layout spec, but the renderer used to
build the ``FrameStyle`` from props, so every frame rendered with the default
``(0, 1, 0, 1)`` whatever the template asked for.
"""

import pytest

from wijjit.tags.layout import DEFAULT_FRAME_PADDING, parse_frame_padding
from wijjit.testing import WijjitHarness, app_from_template


def _hi_position(padding_attr: str) -> tuple[int, int]:
    """Return the (row, column) of "hi" inside a 20x7 frame."""
    template = (
        "{% frame width=20 height=7 " + padding_attr + " %}"
        "{% text %}hi{% endtext %}{% endframe %}"
    )
    with WijjitHarness(app_from_template(template), size=(30, 8)) as h:
        lines = h.screen().splitlines()
    for row, line in enumerate(lines):
        col = line.find("hi")
        if col >= 0:
            return row, col
    raise AssertionError("text not rendered:\n" + "\n".join(lines))


@pytest.mark.parametrize(
    ("attr", "expected"),
    [
        ("", (1, 2)),  # default (0, 1, 0, 1)
        ("padding=0", (1, 1)),
        ("padding=3", (4, 4)),
        ('padding="2"', (3, 3)),
        ("padding=(1, 2, 0, 4)", (2, 5)),
        ('padding="(1, 2, 0, 4)"', (2, 5)),
        ("padding=[1, 3]", (2, 4)),  # CSS shorthand: (vertical, horizontal)
        ('padding="junk"', (1, 2)),  # unreadable -> default
    ],
)
def test_frame_padding_moves_content(attr, expected):
    assert _hi_position(attr) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, DEFAULT_FRAME_PADDING),
        (2, (2, 2, 2, 2)),
        (-1, (0, 0, 0, 0)),
        ("1", (1, 1, 1, 1)),
        ((1, 2, 3, 4), (1, 2, 3, 4)),
        ([5], (5, 5, 5, 5)),
        ((1, 2), (1, 2, 1, 2)),
        ("(0, 2, 0, 2)", (0, 2, 0, 2)),
        ((1, 2, 3), DEFAULT_FRAME_PADDING),
        (("a", 1, 1, 1), DEFAULT_FRAME_PADDING),
        (True, DEFAULT_FRAME_PADDING),
        ("nope", DEFAULT_FRAME_PADDING),
    ],
)
def test_parse_frame_padding(value, expected):
    assert parse_frame_padding(value) == expected


def test_reused_frame_follows_padding_change():
    """A keyed frame reused across renders picks up a new padding value."""
    template = (
        "{% frame id='box' width=20 height=5 padding=state.pad %}"
        "{% text %}hi{% endtext %}{% endframe %}"
    )
    app = app_from_template(template, state={"pad": 0})
    with WijjitHarness(app, size=(30, 6)) as h:
        assert "│hi" in h.screen()
        app.state["pad"] = 2
        h.tick(frames=1)
        assert "│  hi" in h.screen()
