"""OSC 8 hyperlinks survive ANSI content and reach the terminal.

ANSI content used to lose its links: the adapter stripped every OSC sequence,
so text that is clickable printed straight to the terminal (Rich output with
``Style(link=...)``, a Markdown link, the all2md renderer) was dead inside a
Wijjit app. Links are now parsed onto the cells they cover and re-emitted
around those cells, and opening one stays the terminal's job.

Because a link target is written to the terminal verbatim, it is also an
injection channel: a target holding ESC could smuggle any escape sequence into
the output. Such targets are dropped, and the text kept unlinked.
"""

import pytest

from wijjit import Wijjit
from wijjit.rendering.ansi_adapter import ansi_string_to_cells
from wijjit.terminal import ansi
from wijjit.terminal.cell import (
    HYPERLINK_CLOSE,
    MAX_HYPERLINK_LENGTH,
    Cell,
    Hyperlink,
    intern_cell,
    make_hyperlink,
)
from wijjit.terminal.screen_buffer import DiffRenderer, ScreenBuffer
from wijjit.testing import WijjitHarness, app_from_template

ST = "\x1b\\"
URL = "https://example.com/docs"


def osc8(text: str, url: str = URL, link_id: str | None = None) -> str:
    """``text`` wrapped in an OSC 8 link, as Rich writes it."""
    params = f"id={link_id}" if link_id else ""
    return f"\x1b]8;{params};{url}{ST}{text}\x1b]8;;{ST}"


def open_seq(url: str = URL, link_id: str | None = None) -> str:
    params = f"id={link_id}" if link_id else ""
    return f"\x1b]8;{params};{url}{ST}"


@pytest.fixture(autouse=True)
def _reset_schemes():
    """The scheme allowlist is module state; leave it as we found it."""
    yield
    ansi.set_hyperlink_schemes(None)


def links(cells: list[Cell]) -> list[Hyperlink | None]:
    return [c.link for c in cells]


# --------------------------------------------------------------- parsing


def test_link_attaches_to_exactly_the_cells_it_covers():
    cells = ansi_string_to_cells("see " + osc8("docs", link_id="d1") + " now")

    assert "".join(c.char for c in cells) == "see docs now"
    link = Hyperlink(URL, "d1")
    assert links(cells) == [None] * 4 + [link] * 4 + [None] * 4


def test_link_and_style_are_independent():
    cells = ansi_string_to_cells(
        open_seq() + "\x1b[1mab\x1b[0mc" + HYPERLINK_CLOSE + "d"
    )

    assert [(c.char, c.bold, c.link is not None) for c in cells] == [
        ("a", True, True),
        ("b", True, True),
        ("c", False, True),
        ("d", False, False),
    ]


def test_bel_terminator_is_accepted():
    cells = ansi_string_to_cells(f"\x1b]8;;{URL}\x07x\x1b]8;;\x07y")

    assert links(cells) == [Hyperlink(URL), None]


def test_other_osc_sequences_are_still_stripped():
    cells = ansi_string_to_cells(f"\x1b]0;window title{ST}ok")

    assert "".join(c.char for c in cells) == "ok"
    assert links(cells) == [None, None]


def test_unknown_params_are_ignored_and_id_kept():
    cells = ansi_string_to_cells(f"\x1b]8;foo=bar:id=k1;{URL}{ST}x")

    assert cells[0].link == Hyperlink(URL, "k1")


# --------------------------------------------------------------- safety


@pytest.mark.parametrize(
    "target",
    [
        "https://evil.example/\x1b[2J",  # ESC: would inject a CSI sequence
        "https://evil.example/\x07",  # BEL: would end the OSC early
        "https://evil.example/\x9b2J",  # C1 CSI
        "https://evil.example/\x7f",  # DEL
        "https://evil.example/\n",  # newline
        "https://example.com/" + "a" * MAX_HYPERLINK_LENGTH,  # over-long
    ],
)
def test_unsafe_target_is_dropped_and_text_kept(target):
    assert make_hyperlink(target) is None

    # Through the adapter (newline and BEL cannot sit inside an OSC payload,
    # so check the rest end to end).
    if "\n" not in target and "\x07" not in target:
        cells = ansi_string_to_cells(f"\x1b]8;;{target}{ST}text\x1b]8;;{ST}")
        assert "".join(c.char for c in cells) == "text"
        assert links(cells) == [None] * 4


def test_non_ascii_target_is_percent_encoded_not_refused():
    link = make_hyperlink("https://example.com/café menu")

    assert link == Hyperlink("https://example.com/caf%C3%A9%20menu")


def test_invalid_id_is_dropped_but_link_kept():
    assert make_hyperlink(URL, "bad;id") == Hyperlink(URL)
    assert make_hyperlink(URL, "x" * 300) == Hyperlink(URL)


@pytest.mark.parametrize(
    ("url", "link_id"),
    [
        ("https://x/\x1b", None),
        ("", None),
        ("https://x/é", None),
        (URL, "has:colon"),
        (URL, ""),
    ],
)
def test_hyperlink_refuses_to_hold_anything_but_a_link(url, link_id):
    """A Hyperlink built directly is validated too, so no emitter can be fed
    an escape sequence through one."""
    with pytest.raises(ValueError):
        Hyperlink(url, link_id)


def test_scheme_allowlist_drops_other_schemes():
    ansi.set_hyperlink_schemes(["HTTPS", "mailto"])

    assert make_hyperlink(URL) == Hyperlink(URL)
    assert make_hyperlink("mailto:me@example.com") is not None
    assert make_hyperlink("file:///etc/passwd") is None
    assert make_hyperlink("javascript:alert(1)") is None
    assert make_hyperlink("relative/path") is None


def test_scheme_allowlist_from_comma_separated_string():
    """``WIJJIT_HYPERLINK_SCHEMES=http,https`` arrives as one string."""
    ansi.set_hyperlink_schemes("http, https")

    assert ansi.get_hyperlink_schemes() == frozenset({"http", "https"})


def test_app_config_sets_the_allowlist():
    Wijjit(HYPERLINK_SCHEMES=("https",))
    assert ansi.get_hyperlink_schemes() == frozenset({"https"})

    Wijjit()
    assert ansi.get_hyperlink_schemes() is None


# --------------------------------------------------------------- cells


def test_link_takes_part_in_cell_equality():
    """The diff must repaint a cell whose link changed under the same text."""
    assert Cell("a", link=Hyperlink(URL)) != Cell("a")
    assert Cell("a", link=Hyperlink(URL)) != Cell("a", link=Hyperlink(URL, "x"))
    assert Cell("a", link=Hyperlink(URL)) == Cell("a", link=Hyperlink(URL))
    assert Cell("a", link=Hyperlink(URL)).clone().link == Hyperlink(URL)


def test_intern_cell_keys_on_link():
    plain = intern_cell("a")
    linked = intern_cell("a", link=Hyperlink(URL))

    assert linked is not plain
    assert linked is intern_cell("a", link=Hyperlink(URL))


# --------------------------------------------------------------- emitters


def _row_buffer(text: str, width: int = 16) -> ScreenBuffer:
    buf = ScreenBuffer(width, 1)
    buf.set_cells_horizontal(0, 0, ansi_string_to_cells(text))
    return buf


def test_full_render_wraps_the_run_once():
    out = DiffRenderer().render_diff(
        None, _row_buffer("a " + osc8("link", link_id="k") + " b")
    )

    assert out.count(open_seq(link_id="k")) == 1
    assert f"{open_seq(link_id='k')}link{HYPERLINK_CLOSE} b" in out


def test_full_render_closes_a_link_running_to_the_row_end():
    out = DiffRenderer().render_diff(None, _row_buffer(open_seq() + "x" * 16))

    assert out.endswith(HYPERLINK_CLOSE)


def test_partial_repaint_reopens_the_link_around_the_changed_cells():
    """A dirty region that cuts a link run still emits a well-formed link."""
    old = _row_buffer("a " + osc8("link", link_id="k"))
    new = _row_buffer("a " + osc8("lINk", link_id="k"))

    out = DiffRenderer().render_diff(old, new)

    assert f"{open_seq(link_id='k')}IN{HYPERLINK_CLOSE}" in out


def test_link_change_alone_is_repainted():
    old = _row_buffer(osc8("same", "https://a.example"))
    new = _row_buffer(osc8("same", "https://b.example"))

    out = DiffRenderer().render_diff(old, new)

    assert f"{open_seq('https://b.example')}same{HYPERLINK_CLOSE}" in out


def test_removed_link_is_closed():
    old = _row_buffer(osc8("same"))
    new = _row_buffer("same")

    out = DiffRenderer().render_diff(old, new)

    assert "same" in out
    assert open_seq() not in out


def test_cell_to_ansi_wraps_a_linked_cell():
    cell = Cell("x", bold=True, link=Hyperlink(URL))

    assert cell.to_ansi() == f"{open_seq()}\x1b[1mx\x1b[0m{HYPERLINK_CLOSE}"


# --------------------------------------------------------------- end to end

TEMPLATE = (
    '{% vstack width="fill" height="fill" %}'
    '{% contentview id="body" content=state.doc content_type=state.kind '
    'width="fill" height="fill" border="none" %}'
    "{% endcontentview %}"
    "{% endvstack %}"
)


def _drive(doc: str, kind: str = "ansi", size: tuple[int, int] = (40, 6)):
    return WijjitHarness(
        app_from_template(TEMPLATE, state={"doc": doc, "kind": kind}), size=size
    )


def _screen_links(h: WijjitHarness) -> list[list[Hyperlink | None]]:
    buffer = h.app.renderer._last_displayed_buffer
    return [[cell.link for cell in row] for row in buffer.cells]


def test_contentview_keeps_the_link_and_emits_it():
    doc = "Read the " + osc8("manual", link_id="m1") + " first."
    with _drive(doc) as h:
        h.assert_text("Read the manual first.")
        lines = h.screen().splitlines()
        y = next(i for i, line in enumerate(lines) if "manual" in line)
        x = lines[y].index("manual")
        row = _screen_links(h)[y]
        link = Hyperlink(URL, "m1")
        assert row[x : x + 6] == [link] * 6
        assert row[x - 1] is None and row[x + 6] is None

        assert f"{open_seq(link_id='m1')}manual{HYPERLINK_CLOSE}" in h.emitted_ansi()
        assert f"{open_seq(link_id='m1')}manual" in h.screen_ansi()


def test_link_wrapped_across_lines_keeps_one_id():
    doc = osc8("first half", link_id="w") + "\n" + osc8("second half", link_id="w")
    with _drive(doc) as h:
        linked_rows = [row for row in _screen_links(h) if any(row)]
        assert len(linked_rows) == 2
        assert {link for row in linked_rows for link in row if link} == {
            Hyperlink(URL, "w")
        }
        assert h.emitted_ansi().count(open_seq(link_id="w")) == 2


def test_markdown_links_reach_the_screen():
    """Rich renders a Markdown link as OSC 8; it is no longer stripped."""
    with _drive("See [the guide](https://example.com/guide).", kind="markdown") as h:
        h.assert_text("See the guide.")
        found = {link.url for row in _screen_links(h) for link in row if link}
        assert found == {"https://example.com/guide"}


def test_unsafe_link_in_content_is_never_emitted():
    doc = f"\x1b]8;;https://evil.example/\x1b[2J{ST}click\x1b]8;;{ST}"
    with _drive(doc) as h:
        h.assert_text("click")
        assert "evil.example" not in h.emitted_ansi()
        assert all(link is None for row in _screen_links(h) for link in row)


def test_idle_frame_does_not_re_emit_links():
    """Unchanged linked cells compare equal, so the diff leaves them alone."""
    with _drive("x " + osc8("link")) as h:
        before = len(h.emitted_frames)
        h.tick(frames=2)
        assert "\x1b]8;" not in "".join(h.emitted_frames[before:])
