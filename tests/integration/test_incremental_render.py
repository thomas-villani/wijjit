"""Incremental (damage-tracked) rendering equivalence and behavior.

The incremental base-render path (review 2.5) starts each frame's paint buffer
as a copy of the previous frame and lets the write paths change-detect, so the
diff scans only the cells that actually change. These tests pin the two things
that make it safe to ship on by default:

1. **Equivalence** - the visible screen after every step is byte-for-byte the
   same whether ``incremental_render`` is on or off, across the cases that
   stress it: typing, content that shrinks, rows removed and re-added (vacated
   cells), wide characters, and overlays (which force the full-repaint fallback).
2. **Engagement** - a localized change actually takes the incremental path and
   emits far fewer bytes than a full repaint, so the optimization is not
   silently falling back to full repaints.
"""

from wijjit import Wijjit, render_template_string
from wijjit.terminal.ansi import strip_ansi
from wijjit.testing import WijjitHarness

_TEMPLATE = (
    "{% vstack %}"
    '{% textinput id="name" %}{% endtextinput %}'
    "{% for it in items %}{% hstack %}"
    "{% text %}Row {{ it }} label{% endtext %}"
    '{% textinput id="r" ~ it %}{% endtextinput %}{% endhstack %}{% endfor %}'
    "{% endvstack %}"
)


def _make_app():
    app = Wijjit()
    app.state["items"] = [1, 2, 3, 4, 5]

    @app.view("main", default=True)
    def main():
        return render_template_string(_TEMPLATE, items=app.state["items"])

    return app


def _drive(incremental):
    """Run a fixed script and return the screen after each step."""
    app = _make_app()
    screens = []
    with WijjitHarness(app, size=(60, 20)) as h:
        app.renderer.incremental_render = incremental
        h.press("tab")
        h.type("Alexander")
        screens.append(h.screen())
        for _ in range(6):  # shrink the name -> vacated cells on the right
            h.press("backspace")
        screens.append(h.screen())
        h.press("tab")
        h.type("hello")
        screens.append(h.screen())
        app.state["items"] = [1, 2]  # remove rows -> vacated rows below
        h.tick(frames=2)
        screens.append(h.screen())
        app.state["items"] = [1, 2, 3, 4, 5, 6, 7]  # grow past the original
        h.tick(frames=2)
        screens.append(h.screen())
        app.state["name"] = "日本語テスト"  # wide characters via state
        h.tick(frames=2)
        screens.append(h.screen())
        app.state["name"] = ""  # clear -> vacated wide-glyph cells
        h.tick(frames=2)
        screens.append(h.screen())
    return screens


def test_incremental_screen_equals_full_repaint():
    """Every frame is identical with incremental rendering on vs off."""
    on = _drive(True)
    off = _drive(False)
    assert len(on) == len(off)
    for i, (a, b) in enumerate(zip(on, off, strict=True)):
        assert a == b, f"frame {i} differs between incremental and full repaint"


def test_localized_change_takes_incremental_path():
    """A one-character edit emits far fewer bytes than a full repaint.

    Proves the incremental path is actually engaged (not silently falling back):
    typing one character into a focused input should touch only a couple of
    cells, so the emitted frame is a fraction of a whole-screen repaint.
    """
    app = _make_app()
    with WijjitHarness(app, size=(60, 20)) as h:
        app.renderer.incremental_render = True
        h.press("tab")
        h.type("x")  # warm the incremental path
        h.tick()
        h.type("y")  # the measured localized edit
        localized = len(h.last_frame or "")

        # Force a full repaint and measure that.
        app.renderer.invalidate_display()
        h.tick()
        full = len(h.last_frame or "")

    assert localized > 0, "a visible edit should emit something"
    # A localized edit is a small fraction of a full-screen repaint.
    assert localized < full / 5, f"localized={localized} not << full={full}"


def test_incremental_survives_overlay_fallback():
    """Opening/closing an overlay renders correctly with incremental on.

    Overlays force the full-repaint fallback; this checks the base view is
    correct before, during, and after an overlay, and that dismissing it leaves
    no ghost (the modal body is gone from the visible screen).
    """
    template = (
        '{% frame width="fill" height="fill" %}Base content here'
        '{% modal id="m" visible="show" title="Hi" width=30 height=6 %}'
        "Modal body text{% endmodal %}{% endframe %}"
    )
    app = Wijjit()
    app.state["show"] = False

    @app.view("main", default=True)
    def main():
        return render_template_string(template)

    with WijjitHarness(app, size=(60, 20)) as h:
        app.renderer.incremental_render = True
        assert "Base content here" in h.screen()
        assert "Modal body text" not in h.screen()

        app.state["show"] = True
        h.tick(frames=2)
        assert "Modal body text" in h.screen()

        app.state["show"] = False
        h.tick(frames=2)
        assert "Modal body text" not in strip_ansi(h.screen())
        assert "Base content here" in h.screen()
