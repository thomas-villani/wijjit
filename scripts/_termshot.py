"""Rasterize a captured ANSI terminal screen to an image.

Shared by ``make_demo_gif.py`` (frames of an animation) and
``make_social_card.py`` (a single panel). Wijjit already renders any app to a
styled ANSI screen without a terminal; this turns that text into pixels, so
every image asset in the repo comes from a real headless render rather than a
screen capture.

Requires Pillow and a monospace TTF covering box-drawing and braille. See
:class:`FontSet` for how missing glyphs are detected and filled.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Terminal surface. The dark surface the chart palette was validated against, so
# a recorded chart looks the way the palette was checked to look.
DEFAULT_FG = (204, 204, 204)
DEFAULT_BG = (26, 26, 25)

FONT_SIZE = 18
PADDING = 12

# Monospace faces that carry box-drawing *and* braille, best first.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/CascadiaMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/Library/Fonts/DejaVuSansMono.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/lucon.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]

# No mainstream monospace face covers everything a Wijjit screen can contain --
# Cascadia Mono, for instance, has braille but not the ballot boxes a Checkbox
# draws, which would silently render as tofu. These non-monospace symbol faces
# fill the gaps; a fallback glyph is centred in its cell, so the grid still
# lines up.
FALLBACK_CANDIDATES = [
    "C:/Windows/Fonts/seguisym.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Apple Symbols.ttf",
]

SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")

# The 16 ANSI base colours, for demos that use them instead of truecolor.
BASE_COLORS = [
    (0, 0, 0),
    (205, 49, 49),
    (13, 188, 121),
    (229, 229, 16),
    (36, 114, 200),
    (188, 63, 188),
    (17, 168, 205),
    (229, 229, 229),
    (102, 102, 102),
    (241, 76, 76),
    (35, 209, 139),
    (245, 245, 67),
    (59, 142, 234),
    (214, 112, 214),
    (41, 184, 219),
    (255, 255, 255),
]


class Pen:
    """The active SGR state while scanning one line of ANSI output."""

    def __init__(self) -> None:
        self.fg: tuple[int, int, int] | None = None
        self.bg: tuple[int, int, int] | None = None
        self.bold = False
        self.reverse = False

    def reset(self) -> None:
        self.__init__()

    def apply(self, params: str) -> None:
        """Apply one SGR escape's parameters."""
        codes = [int(p) if p else 0 for p in params.split(";")] or [0]
        i = 0
        while i < len(codes):
            code = codes[i]
            if code == 0:
                self.reset()
            elif code == 1:
                self.bold = True
            elif code == 22:
                self.bold = False
            elif code == 7:
                self.reverse = True
            elif code == 27:
                self.reverse = False
            elif code == 39:
                self.fg = None
            elif code == 49:
                self.bg = None
            elif 30 <= code <= 37:
                self.fg = BASE_COLORS[code - 30]
            elif 90 <= code <= 97:
                self.fg = BASE_COLORS[code - 90 + 8]
            elif 40 <= code <= 47:
                self.bg = BASE_COLORS[code - 40]
            elif 100 <= code <= 107:
                self.bg = BASE_COLORS[code - 100 + 8]
            elif code in (38, 48) and i + 1 < len(codes):
                target = "fg" if code == 38 else "bg"
                mode = codes[i + 1]
                if mode == 2 and i + 4 < len(codes):
                    setattr(self, target, tuple(codes[i + 2 : i + 5]))
                    i += 4
                elif mode == 5 and i + 2 < len(codes):
                    setattr(self, target, xterm256(codes[i + 2]))
                    i += 2
            i += 1

    def colors(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Resolve the pen to concrete (foreground, background) colours."""
        fg = self.fg if self.fg is not None else DEFAULT_FG
        bg = self.bg if self.bg is not None else DEFAULT_BG
        return (bg, fg) if self.reverse else (fg, bg)


def xterm256(index: int) -> tuple[int, int, int]:
    """Convert an xterm-256 colour index to RGB."""
    if index < 16:
        return BASE_COLORS[index]
    if index < 232:
        index -= 16
        levels = [0, 95, 135, 175, 215, 255]
        return (levels[index // 36], levels[(index // 6) % 6], levels[index % 6])
    grey = 8 + (index - 232) * 10
    return (grey, grey, grey)


def parse_screen(ansi: str) -> list[list[tuple[str, Any, Any, bool]]]:
    """Parse a styled ANSI screen into a grid of (char, fg, bg, bold) cells."""
    grid = []
    for line in ansi.splitlines():
        pen = Pen()
        row: list[tuple[str, Any, Any, bool]] = []
        pos = 0
        for match in SGR_RE.finditer(line):
            for char in line[pos : match.start()]:
                fg, bg = pen.colors()
                row.append((char, fg, bg, pen.bold))
            pen.apply(match.group(1))
            pos = match.end()
        for char in line[pos:]:
            fg, bg = pen.colors()
            row.append((char, fg, bg, pen.bold))
        grid.append(row)
    return grid


class FontSet:
    """A monospace font plus symbol fallbacks for the glyphs it lacks.

    A missing glyph does not raise -- FreeType quietly substitutes ``.notdef``
    (the "tofu" box), which is easy to ship by accident. Coverage is therefore
    probed by rendering: a character whose bitmap matches the font's rendering
    of an unassigned private-use codepoint is missing, and is looked up in the
    fallback faces instead.
    """

    PROBE = ""  # unassigned private-use area, i.e. guaranteed .notdef

    def __init__(
        self, primary: ImageFont.FreeTypeFont, fallbacks: list[ImageFont.FreeTypeFont]
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks
        self.ascent, self.descent = primary.getmetrics()
        self.cell_w = int(round(primary.getlength("M")))
        self.cell_h = self.ascent + self.descent
        self._tofu: dict[int, bytes] = {}
        self._cache: dict[str, ImageFont.FreeTypeFont] = {}

    def _render_bits(self, font: ImageFont.FreeTypeFont, char: str) -> bytes:
        img = Image.new("L", (self.cell_w * 3, self.cell_h * 2), 0)
        ImageDraw.Draw(img).text((2, 2), char, font=font, fill=255)
        return img.tobytes()

    def _is_missing(self, font: ImageFont.FreeTypeFont, char: str) -> bool:
        key = id(font)
        if key not in self._tofu:
            self._tofu[key] = self._render_bits(font, self.PROBE)
        return self._render_bits(font, char) == self._tofu[key]

    def font_for(self, char: str) -> ImageFont.FreeTypeFont:
        """Pick the best font that actually has a glyph for ``char``."""
        cached = self._cache.get(char)
        if cached is not None:
            return cached
        chosen = self.primary
        if self._is_missing(self.primary, char):
            for fallback in self.fallbacks:
                if not self._is_missing(fallback, char):
                    chosen = fallback
                    break
        self._cache[char] = chosen
        return chosen


def find_font(explicit: str | None) -> FontSet:
    """Load the primary monospace font and any available symbol fallbacks."""
    candidates = [explicit] if explicit else FONT_CANDIDATES
    primary = None
    for path in candidates:
        if path and Path(path).exists():
            primary = ImageFont.truetype(path, FONT_SIZE)
            break
    if primary is None:
        raise SystemExit(
            "No monospace font found. Pass --font /path/to/Mono.ttf (it must "
            "cover box-drawing and braille glyphs)."
        )

    fallbacks = [
        ImageFont.truetype(path, FONT_SIZE)
        for path in FALLBACK_CANDIDATES
        if Path(path).exists()
    ]
    return FontSet(primary, fallbacks)


def render_frame(
    grid: list[list[tuple[str, Any, Any, bool]]],
    fonts: FontSet,
    cols: int,
    rows: int,
) -> Image.Image:
    """Rasterize one parsed screen to an image."""
    cell_w, cell_h = fonts.cell_w, fonts.cell_h
    img = Image.new(
        "RGB", (cols * cell_w + 2 * PADDING, rows * cell_h + 2 * PADDING), DEFAULT_BG
    )
    draw = ImageDraw.Draw(img)

    for y, row in enumerate(grid[:rows]):
        for x, (char, fg, bg, _bold) in enumerate(row[:cols]):
            px, py = PADDING + x * cell_w, PADDING + y * cell_h
            if bg != DEFAULT_BG:
                draw.rectangle([px, py, px + cell_w - 1, py + cell_h - 1], fill=bg)
            if not char or char == " ":
                continue
            font = fonts.font_for(char)
            # Centre the glyph in its cell and sit every font on the primary
            # font's baseline, so a proportional fallback still lines up.
            offset = (cell_w - font.getlength(char)) / 2
            draw.text(
                (px + offset, py + fonts.ascent), char, font=font, fill=fg, anchor="ls"
            )
    return img
