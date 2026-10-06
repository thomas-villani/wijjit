"""Document Reader - a Markdown viewer with live links, an outline, and jumps.

A small document viewer built on one ContentView, showing three things a
reader needs and a plain text view cannot do:

- External links stay real links. The Markdown is laid out by Rich, which
  writes OSC 8 hyperlinks; Wijjit keeps them on the cells they cover, so your
  terminal underlines them and opens one on Ctrl+click (Cmd+click on macOS).
  The app never opens anything itself.
- In-document links jump. The content is a *function of the width*: the app
  lays the document out at the width the view really has and records where
  every link and heading landed. ContentView reports clicks and hovers as
  (line, column), so the app looks the position up in that map.
- Hovering a link shows its target in the status bar before you click.

HYPERLINK_SCHEMES keeps the in-document targets (``#section``) out of what is
sent to the terminal: only http, https and mailto links reach it. Hover needs
MOUSE_TRACKING_MODE="all_events", since terminals report bare pointer motion
only in that mode.

Controls:
- Mouse: click an in-document link to jump; hover a link to see where it goes
- Ctrl+click (terminal): open an external link
- Tab/Shift+Tab: move between the outline and the document
- Outline (focused at start): Up/Down to move, Enter to jump to a section
- Document: arrows / Page Up / Page Down / mouse wheel to scroll
- Ctrl+Q: Quit
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import StringIO

from rich.console import Console
from rich.markdown import Markdown

from wijjit import Wijjit, render_template_string
from wijjit.terminal.ansi import strip_ansi, visible_length

DOCUMENT = """\
# Wijjit Is Just Jinja In Terminal

Wijjit builds terminal apps from [Jinja2](https://jinja.palletsprojects.com/)
templates. This reader is one of them: the outline on the left is a tree, and
this pane is a single content view showing Markdown laid out by
[Rich](https://github.com/Textualize/rich).

Jump ahead to [how links work](#how-links-work), see
[what the app sees](#what-the-app-sees), or skip to the
[limits](#limits).

## How links work

Rich writes each link as an OSC 8 hyperlink. Wijjit keeps the link on the
cells it covers and writes it back around them, so your terminal treats the
text as a link: try Ctrl+click on [the Wijjit repository](https://github.com/thomas-villani/wijjit).

Opening a link is always the terminal's job. A link whose target could carry
escape sequences is dropped, and `HYPERLINK_SCHEMES` limits which kinds of
link reach the terminal at all. Mail links work too:
[write to someone](mailto:someone@example.com).

## What the app sees

The view reports a click as a line and a column. The line counts from the top
of the document, whatever is scrolled into view; the column is a display
column, so wide characters count twice: 日本語 is six columns.

Because the app laid this text out itself, at the width the view really has,
it knows which link sits at which position. Back to the
[top](#wijjit-is-just-jinja-in-terminal).

### Hovering

Move the pointer over any link and the status bar shows its target. Moving
off the text clears it.

## Limits

Only the pointer is reported. The keyboard can still reach every section
through the outline, which is the accessible path; the links are a shortcut.

Read more in the [user guide](https://wijjit.readthedocs.io/).
"""

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
OSC8 = re.compile(r"\x1b\]8;[^;\x07\x1b]*;(.*?)(?:\x07|\x1b\\)")
# Characters of the boxes Rich draws around top-level headings (light and heavy).
BOX_CHARS = " \u2500\u2502\u250c\u2510\u2514\u2518\u2501\u2503\u250f\u2513\u2517\u251b"
DEFAULT_STATUS = "Hover a link to see its target. Click an in-document link to jump."


def slugify(title: str) -> str:
    """Turn a heading into its anchor, the way GitHub does.

    Parameters
    ----------
    title : str
        Heading text.

    Returns
    -------
    str
        Lowercase, punctuation dropped, spaces as hyphens.
    """
    return re.sub(r"[^\w\- ]", "", title.lower()).strip().replace(" ", "-")


def outline_of(markdown: str) -> dict:
    """Build the outline tree (headings nested by level) for the document.

    Parameters
    ----------
    markdown : str
        The document.

    Returns
    -------
    dict
        A tree root whose children are the headings, each with ``label``,
        ``value`` (the anchor) and ``children``.
    """
    root: dict = {"label": "Document", "value": "", "children": []}
    stack: list[tuple[int, dict]] = [(0, root)]
    for hashes, title in HEADING.findall(markdown):
        level = len(hashes)
        node = {"label": title, "value": slugify(title), "children": []}
        while stack[-1][0] >= level:
            stack.pop()
        stack[-1][1]["children"].append(node)
        stack.append((level, node))
    return root


@dataclass
class Layout:
    """The document laid out at one width, and where everything landed.

    Attributes
    ----------
    lines : list of str
        The rendered ANSI lines, as the view shows them.
    links : dict of int to list of (int, int, str)
        Per line, the ``(start, end, target)`` column span of each link.
    headings : dict of str to int
        Anchor of each heading to the line it is drawn on.
    """

    lines: list[str]
    links: dict[int, list[tuple[int, int, str]]] = field(default_factory=dict)
    headings: dict[str, int] = field(default_factory=dict)


def link_spans(line: str) -> list[tuple[int, int, str]]:
    """Find the display-column span of every OSC 8 link on one ANSI line.

    Parameters
    ----------
    line : str
        One rendered line.

    Returns
    -------
    list of (int, int, str)
        ``(start, end, target)`` per link, ``end`` exclusive.
    """
    spans = []
    column, pos = 0, 0
    target, start = "", 0
    for match in OSC8.finditer(line):
        column += visible_length(line[pos : match.start()])
        if target:
            spans.append((start, column, target))
        target, start, pos = match.group(1), column, match.end()
    return spans


class Document:
    """The view's content: a function of the width, with a map per width.

    ContentView calls this with the width it has, and again when that
    changes. Each layout is kept, so the click and hover handlers can look up
    a position in the layout currently on screen.

    Parameters
    ----------
    markdown : str
        The document.
    """

    def __init__(self, markdown: str) -> None:
        self.markdown = markdown
        self.titles = {slugify(t): t for _, t in HEADING.findall(markdown)}
        self._layouts: dict[int, Layout] = {}
        self.width = 0

    def __call__(self, width: int) -> str:
        self.width = width
        return "\n".join(self.layout(width).lines)

    def layout(self, width: int) -> Layout:
        """Lay the document out at ``width`` columns (cached per width)."""
        if width not in self._layouts:
            out = StringIO()
            # legacy_windows=False: on Windows Rich otherwise assumes the old
            # console and leaves the links out.
            Console(
                file=out, width=width, force_terminal=True, legacy_windows=False
            ).print(Markdown(self.markdown))
            layout = Layout(out.getvalue().rstrip("\n").split("\n"))
            by_title = {title: slug for slug, title in self.titles.items()}
            for number, line in enumerate(layout.lines):
                if spans := link_spans(line):
                    layout.links[number] = spans
                text = strip_ansi(line).strip(BOX_CHARS)
                if text in by_title and by_title[text] not in layout.headings:
                    # A boxed heading's top border is the line above it.
                    boxed = strip_ansi(line)[:1] in ("\u2502", "\u2503")
                    top = number - 1 if boxed else number
                    layout.headings[by_title[text]] = top
            self._layouts[width] = layout
        return self._layouts[width]

    def link_at(self, line: int, column: int) -> str | None:
        """Return the target of the link at a position on screen, if any."""
        for start, end, target in self.layout(self.width).links.get(line, []):
            if start <= column < end:
                return target
        return None

    def line_of(self, anchor: str) -> int | None:
        """Return the line a heading is drawn on, or None."""
        return self.layout(self.width).headings.get(anchor)


document = Document(DOCUMENT)

app = Wijjit(
    MOUSE_TRACKING_MODE="all_events",
    HYPERLINK_SCHEMES=("http", "https", "mailto"),
)
app.state["status"] = DEFAULT_STATUS

TEMPLATE = """
{% vstack width="fill" height="fill" %}
  {% hstack width="fill" height="fill" %}
    {% tree id="outline" data=outline width=30 height="fill" show_root=false
            enter_selects=true expanded=open action="goto" autofocus=true
            border="rounded" title="Outline" %}{% endtree %}
    {% contentview id="doc" content=document content_type="ansi"
                   width="fill" height="fill" border="rounded" title="Reader"
                   on_click=on_click on_hover=on_hover %}{% endcontentview %}
  {% endhstack %}
  {% statusbar left=state.status right="Tab: switch pane   Ctrl+Q: quit" %}
  {% endstatusbar %}
{% endvstack %}
"""

OUTLINE = outline_of(DOCUMENT)
OPEN = [slugify(t) for _, t in HEADING.findall(DOCUMENT)]


def jump_to(anchor: str) -> None:
    """Scroll the reader so the heading for ``anchor`` is at the top."""
    line = document.line_of(anchor)
    view = app.get_element_by_id("doc")
    if line is None or view is None:
        return
    view.scroll_manager.scroll_to(line)
    app.state["status"] = f"Jumped to: {document.titles[anchor]}"


def on_click(line: int, column: int, event: object) -> None:
    """A click in the document: jump on an in-document link."""
    target = document.link_at(line, column)
    if target is None:
        app.state["status"] = f"Clicked line {line + 1}, column {column + 1}"
    elif target.startswith("#"):
        jump_to(target[1:])
    else:
        app.state["status"] = f"Ctrl+click opens it in your terminal: {target}"


def on_hover(line: int | None, column: int | None) -> None:
    """The pointer moved: show the target of the link under it."""
    target = None if line is None else document.link_at(line, column or 0)
    if target is None:
        app.state["status"] = DEFAULT_STATUS
    elif target.startswith("#"):
        app.state["status"] = f"Jump to: {document.titles.get(target[1:], target)}"
    else:
        app.state["status"] = f"Link: {target}"


@app.view("main", default=True)
def main_view():
    return render_template_string(
        TEMPLATE,
        document=document,
        outline=OUTLINE,
        open=OPEN,
        on_click=on_click,
        on_hover=on_hover,
    )


@app.on_action("goto")
def goto(event):
    """Enter (or a click) on an outline entry jumps to that section."""
    if event.data and event.data.get("value"):
        jump_to(event.data["value"])


if __name__ == "__main__":
    app.run()
