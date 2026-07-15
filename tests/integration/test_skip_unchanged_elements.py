"""Skip-unchanged-elements fast path (review 2.5, option c).

On the incremental paint path the renderer skips re-painting any element whose
:meth:`~wijjit.elements.base.Element.render_signature` and on-screen geometry
match the previous frame - its cells are already correct in the copied-in
baseline, so ``render_to`` is not called and the element's previous painted
region is re-recorded as coverage (so vacated-cell blanking spares it).

These tests pin the three things that make it safe to ship on by default:

1. **Equivalence** - the visible screen and the emitted ANSI are byte-for-byte
   identical whether the fast path is on or off, across typing, focus moves,
   content that shrinks, and rows added/removed.
2. **Signature completeness** - with ``verify_skips`` on, the renderer paints
   would-be-skipped elements anyway and asserts the paint reproduces the
   baseline exactly; driving that over interactions surfaces any missing
   render input as an error.
3. **Engagement** - unchanged elements really are skipped: a localized edit
   does not call ``render_to`` on the static siblings.
"""

from wijjit import Wijjit, render_template_string
from wijjit.elements.base import TextElement
from wijjit.testing import WijjitHarness

_TEMPLATE = (
    "{% vstack %}"
    '{% textinput id="name" %}{% endtextinput %}'
    '{% textinput id="email" %}{% endtextinput %}'
    "{% for it in items %}{% hstack %}"
    "{% text %}Row {{ it }} label{% endtext %}"
    '{% button label="Go" %}{% endbutton %}{% endhstack %}{% endfor %}'
    "{% endvstack %}"
)


def _make_app():
    app = Wijjit()
    app.state["items"] = [1, 2, 3, 4, 5]

    @app.view("main", default=True)
    def main():
        return render_template_string(_TEMPLATE, items=app.state["items"])

    return app


def _drive(skip_unchanged, verify=False):
    """Run a fixed script; return (screens, cumulative emitted ANSI)."""
    app = _make_app()
    screens = []
    with WijjitHarness(app, size=(60, 20)) as h:
        app.renderer.skip_unchanged_elements = skip_unchanged
        app.renderer._verify_skips = verify
        h.press("tab")
        h.type("Alice")
        screens.append(h.screen())
        h.press("tab")  # focus moves name -> email (both must repaint)
        h.type("a@b.co")
        screens.append(h.screen())
        for _ in range(3):  # shrink email -> vacated cells
            h.press("backspace")
        screens.append(h.screen())
        app.state["items"] = [1, 2]  # remove rows -> vacated rows below
        h.tick(frames=2)
        screens.append(h.screen())
        app.state["items"] = [1, 2, 3, 4, 5, 6]  # grow past original
        h.tick(frames=2)
        screens.append(h.screen())
        h.assert_no_errors()
        return screens, h.emitted_ansi()


def test_skip_screen_equals_full_paint():
    """Every frame is identical with the skip fast path on vs off."""
    on, _ = _drive(True)
    off, _ = _drive(False)
    assert len(on) == len(off)
    for i, (a, b) in enumerate(zip(on, off, strict=True)):
        assert a == b, f"frame {i} differs between skip-on and skip-off"


def test_skip_emitted_ansi_equals_full_paint():
    """The emitted byte stream is identical - the skip changes CPU, not output."""
    _, on = _drive(True)
    _, off = _drive(False)
    assert on == off


def test_verify_mode_finds_no_incomplete_signatures():
    """With verify on, every would-be skip reproduces the baseline exactly."""
    screens, _ = _drive(True, verify=True)
    # verify mode raises (routed to h.errors, checked via assert_no_errors in
    # _drive) if any element's signature is incomplete; reaching here is a pass.
    assert all(s.strip() for s in screens)


def test_unchanged_siblings_are_not_repainted():
    """A localized edit skips render_to on the static labels around it."""
    app = _make_app()
    calls = {"n": 0}
    original = TextElement.render_to

    def counting_render_to(self, ctx):
        calls["n"] += 1
        return original(self, ctx)

    with WijjitHarness(app, size=(60, 20)) as h:
        app.renderer.skip_unchanged_elements = True
        h.press("tab")
        h.type("x")  # warm the incremental + memo path
        h.tick()  # reach steady state (both frames captured a memo)

        TextElement.render_to = counting_render_to
        try:
            calls["n"] = 0
            h.type("y")  # only the focused input changes
        finally:
            TextElement.render_to = original

    # None of the 5 "Row N label" text elements should have repainted.
    assert (
        calls["n"] == 0
    ), f"static labels repainted {calls['n']} times on a localized edit"


def test_engagement_requires_the_flag():
    """With the flag off, the same edit does repaint the static labels."""
    app = _make_app()
    calls = {"n": 0}
    original = TextElement.render_to

    def counting_render_to(self, ctx):
        calls["n"] += 1
        return original(self, ctx)

    with WijjitHarness(app, size=(60, 20)) as h:
        app.renderer.skip_unchanged_elements = False
        h.press("tab")
        h.type("x")
        h.tick()

        TextElement.render_to = counting_render_to
        try:
            calls["n"] = 0
            h.type("y")
        finally:
            TextElement.render_to = original

    # All 5 labels repaint every frame when the fast path is disabled.
    assert calls["n"] >= 5, f"expected all labels to repaint, got {calls['n']}"


# --------------------------------------------------------------------------
# Interactive-widget signatures (checkbox/toggle/slider/radiogroup/...).
# Each widget added a render_signature(); drive real interactions with verify
# mode on so any missing render input surfaces as an error, and pin on/off
# equivalence across the same script.
# --------------------------------------------------------------------------

_WIDGET_TEMPLATE = (
    "{% vstack %}"
    '{% textinput id="name" %}{% endtextinput %}'
    '{% checkbox id="agree" %}I agree{% endcheckbox %}'
    '{% toggle id="dark" %}Dark mode{% endtoggle %}'
    '{% slider id="vol" min=0 max=100 %}{% endslider %}'
    '{% radiogroup id="plan" options=plans %}{% endradiogroup %}'
    '{% checkboxgroup id="feats" options=feats %}{% endcheckboxgroup %}'
    "{% endvstack %}"
)

_PLANS = [
    {"value": "basic", "label": "Basic"},
    {"value": "pro", "label": "Pro"},
]
_FEATS = [
    {"value": "a", "label": "Alpha"},
    {"value": "b", "label": "Beta"},
]


def _make_widget_app():
    app = Wijjit()

    @app.view("main", default=True)
    def main():
        return render_template_string(_WIDGET_TEMPLATE, plans=_PLANS, feats=_FEATS)

    return app


def _drive_widgets(skip_unchanged, verify=False):
    """Tab through the widgets and mutate each; return per-frame screens."""
    app = _make_widget_app()
    screens = []
    with WijjitHarness(app, size=(50, 18)) as h:
        app.renderer.skip_unchanged_elements = skip_unchanged
        app.renderer._verify_skips = verify
        h.press("tab")  # -> name
        h.type("Al")
        screens.append(h.screen())
        h.press("tab")  # -> checkbox
        h.press("space")  # toggle checked
        screens.append(h.screen())
        h.press("tab")  # -> toggle
        h.press("space")  # flip toggle
        screens.append(h.screen())
        h.press("tab")  # -> slider
        h.press("right")  # move handle
        h.press("right")
        screens.append(h.screen())
        h.press("tab")  # -> radiogroup
        h.press("down")  # change selection/highlight
        screens.append(h.screen())
        h.press("tab")  # -> checkboxgroup
        h.press("space")  # toggle a member
        screens.append(h.screen())
        h.assert_no_errors()
        return screens


def test_widget_signatures_screen_equals_full_paint():
    """Widget interactions render identically with the skip fast path on/off."""
    on = _drive_widgets(True)
    off = _drive_widgets(False)
    assert len(on) == len(off)
    for i, (a, b) in enumerate(zip(on, off, strict=True)):
        assert a == b, f"widget frame {i} differs between skip-on and skip-off"


def test_widget_signatures_pass_verify_mode():
    """Verify mode finds no incomplete widget signature across interactions."""
    screens = _drive_widgets(True, verify=True)
    assert all(s.strip() for s in screens)
