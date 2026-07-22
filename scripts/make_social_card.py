"""Generate the GitHub social preview card.

Produces ``docs/assets/social-card.png`` at 1280x640 -- GitHub's recommended
size for a repository social preview (minimum 640x320, under 1 MB, PNG/JPG/GIF).
Upload it under Settings -> General -> Social preview.

The card is a split: the Jinja template on the left, the screen it actually
renders on the right. That is Wijjit's whole differentiator in one image, and
the right-hand panel is a genuine headless render of the source shown on the
left -- captured through ``WijjitHarness`` and rasterized with the same code
that builds the demo GIF, so the two panels cannot disagree.

Design constraint worth preserving: social cards are consumed *small*. A Slack
unfurl or timeline preview is roughly 400-500px wide, so this 1280px image gets
downscaled 2.5-3x. Everything on it is therefore large and sparse -- a full
100-column app screenshot would render as unreadable grey mush at that scale.
Keep the panels to a handful of lines of big type.

Usage
-----
From the repo root::

    uv run python scripts/make_social_card.py
    uv run python scripts/make_social_card.py --font PATH.ttf
"""

from __future__ import annotations

import sys
from pathlib import Path

from _termshot import FALLBACK_CANDIDATES, FontSet, find_font, parse_screen
from PIL import Image, ImageDraw, ImageFont

from wijjit.testing import WijjitHarness, app_from_template

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "social-card.png"

WIDTH, HEIGHT = 1280, 640
MARGIN = 56

BG = (16, 17, 20)
PANEL_BG = (24, 26, 30)
INK = (232, 232, 228)
MUTED = (138, 140, 148)
RULE = (52, 55, 62)

# From the palette validated for both light and dark surfaces (chart_utils).
ACCENT = (57, 135, 229)  # blue  - tag delimiters
ACCENT_2 = (217, 89, 38)  # orange - attribute names
ACCENT_3 = (25, 158, 112)  # aqua  - string literals

# The exact template rendered on the right. Kept narrow so it can be shown
# verbatim -- the card would be dishonest if the source were a simplified
# stand-in for what actually renders.
TEMPLATE = """{% frame title="Login" border="rounded" %}
  {% vstack spacing=1 padding=1 %}
    {% textinput id="user" %}
    {% endtextinput %}
    {% textinput id="pass" password=True %}
    {% endtextinput %}
    {% button action="signin" %}
      Sign in
    {% endbutton %}
  {% endvstack %}
{% endframe %}"""

# The frame takes its size from the terminal, so this is what makes the
# rendered panel 30 columns wide. Keep it in step with the panel geometry
# below: at 22px the left column fits ~43 characters, which is what caps how
# long a line of TEMPLATE may be.
RENDER_SIZE = (32, 10)
RENDER_STATE = {"user": "admin", "pass": "hunter2"}


def capture_render() -> list[list[tuple[str, object, object, bool]]]:
    """Render TEMPLATE headlessly and return its parsed cell grid."""
    app = app_from_template(TEMPLATE, state=RENDER_STATE)
    with WijjitHarness(app, size=RENDER_SIZE) as harness:
        # Tab past the two inputs so the button carries its focus styling.
        for _ in range(3):
            harness.press("tab")
        return parse_screen(harness.screen_ansi())


def tokenize(line: str) -> list[tuple[str, tuple[int, int, int]]]:
    """Split a template line into coloured runs.

    A deliberately small tokenizer -- enough to make ``{% %}``, attribute names
    and string literals distinguishable at a glance, which is all the card
    needs. It is not a Jinja parser.
    """
    runs: list[tuple[str, tuple[int, int, int]]] = []
    i = 0
    while i < len(line):
        if line.startswith("{%", i) or line.startswith("%}", i):
            runs.append((line[i : i + 2], ACCENT))
            i += 2
        elif line[i] == '"':
            end = line.find('"', i + 1)
            end = len(line) - 1 if end == -1 else end
            runs.append((line[i : end + 1], ACCENT_3))
            i = end + 1
        elif line[i].isalpha() or line[i] == "_":
            j = i
            while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            is_attr = j < len(line) and line[j] == "="
            runs.append((word, ACCENT_2 if is_attr else INK))
            i = j
        else:
            runs.append((line[i], MUTED))
            i += 1
    return runs


def draw_terminal(
    img: Image.Image,
    grid: list[list[tuple[str, object, object, bool]]],
    fonts: FontSet,
    origin: tuple[int, int],
) -> None:
    """Paint a parsed cell grid onto the card, honouring per-cell colours."""
    draw = ImageDraw.Draw(img)
    ox, oy = origin
    cw, ch = fonts.cell_w, fonts.cell_h
    for y, row in enumerate(grid):
        for x, (char, fg, bg, _bold) in enumerate(row):
            px, py = ox + x * cw, oy + y * ch
            if bg != (26, 26, 25) and bg != PANEL_BG:
                draw.rectangle([px, py, px + cw - 1, py + ch - 1], fill=bg)
            if not char or char == " ":
                continue
            font = fonts.font_for(char)
            offset = (cw - font.getlength(char)) / 2
            draw.text(
                (px + offset, py + fonts.ascent),
                char,
                font=font,
                fill=fg,
                anchor="ls",
            )


def build_card(font_path: str | None) -> Image.Image:
    """Compose the full 1280x640 card."""
    mono = find_font(font_path)
    mono_path = mono.primary.path
    body_font = ImageFont.truetype(mono_path, 22)
    fallbacks = [
        ImageFont.truetype(p, 22) for p in FALLBACK_CANDIDATES if Path(p).exists()
    ]
    term_fonts = FontSet(body_font, fallbacks)

    title_font = ImageFont.truetype(mono_path, 46)
    tag_font = ImageFont.truetype(mono_path, 23)
    caption_font = ImageFont.truetype(mono_path, 19)

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # -- header ----------------------------------------------------------
    draw.text((MARGIN, MARGIN), "wijjit", font=title_font, fill=INK)
    draw.text(
        (MARGIN, MARGIN + 62),
        "Wijjit Is Just Jinja In Terminal",
        font=tag_font,
        fill=ACCENT,
    )
    draw.text(
        (MARGIN, MARGIN + 96),
        "A declarative TUI framework for Python",
        font=tag_font,
        fill=MUTED,
    )

    rule_y = MARGIN + 140
    draw.line([(MARGIN, rule_y), (WIDTH - MARGIN, rule_y)], fill=RULE, width=2)

    # -- panels ----------------------------------------------------------
    # Both panels are sized from their content rather than the canvas, so the
    # source can grow a line without spilling out of its background box.
    panel_top = rule_y + 34
    mid = WIDTH // 2
    left_x, right_x = MARGIN, mid + 28

    source_lines = TEMPLATE.splitlines()
    grid = capture_render()
    line_h = term_fonts.cell_h
    source_h = len(source_lines) * line_h

    draw.rectangle(
        [left_x - 18, panel_top - 14, mid - 28, panel_top + source_h + 10],
        fill=PANEL_BG,
    )

    for i, line in enumerate(source_lines):
        x = left_x
        y = panel_top + i * line_h
        for text, colour in tokenize(line):
            draw.text((x, y), text, font=body_font, fill=colour)
            x += body_font.getlength(text)

    # Centre the render against the source block so neither side floats.
    rendered_rows = sum(1 for row in grid if any(c.strip() for c, *_ in row))
    right_y = panel_top + max(0, (len(source_lines) - rendered_rows)) * line_h // 2
    draw_terminal(img, grid, term_fonts, (right_x, right_y))

    # -- captions --------------------------------------------------------
    caption_y = panel_top + source_h + 26
    draw.text(
        (left_x, caption_y), "the template you write", font=caption_font, fill=MUTED
    )
    draw.text((right_x, caption_y), "what it renders", font=caption_font, fill=MUTED)
    draw.text(
        (WIDTH - MARGIN, MARGIN + 8),
        "pip install wijjit",
        font=caption_font,
        fill=MUTED,
        anchor="ra",
    )
    return img


def main() -> int:
    argv = sys.argv[1:]
    font_path = None
    if "--font" in argv:
        idx = argv.index("--font")
        font_path = argv[idx + 1]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    card = build_card(font_path)
    card.save(OUT, optimize=True)
    size_kb = OUT.stat().st_size / 1024
    print(
        f"wrote {OUT.relative_to(ROOT)} ({card.width}x{card.height}, {size_kb:.0f} KB)"
    )
    if size_kb > 1024:
        print("WARNING: over GitHub's 1 MB limit", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
