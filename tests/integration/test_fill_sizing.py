"""Fill-width sizing through the real template -> layout -> paint path.

Regression tests for two 0.1.0 fixes: elements that paint their own box from
``self.width`` (LogView, TextInput) used to ignore the width the layout
engine assigned under ``width="fill"``, drawing short of (or past) their
slot. The tests drive the public harness so the whole reconcile -> layout ->
set_bounds -> paint chain is exercised, which element-level tests (where
``bounds.width`` always equals ``self.width``) cannot catch.
"""

from pathlib import Path

import pytest

from wijjit.elements.display.image import PIL_AVAILABLE
from wijjit.testing import WijjitHarness, app_from_template


def _element(app, type_name):
    return next(e for e in app.positioned_elements if type(e).__name__ == type_name)


class TestLogViewFill:
    def test_fill_logview_draws_its_assigned_width(self):
        app = app_from_template(
            '{% frame border="single" width=40 height=8 %}{% vstack %}'
            '{% logview id="log" lines=lines width="fill" height=4'
            ' border="single" %}{% endlogview %}'
            "{% endvstack %}{% endframe %}",
            state={"lines": ["hello"]},
        )
        with WijjitHarness(app, size=(40, 8)) as h:
            h.tick()
            logview = _element(app, "LogView")
            box_top = h.screen().splitlines()[1]
            drawn = box_top.rindex("┐") - box_top.index("┌") + 1
            assert drawn == logview.bounds.width

    def test_fixed_logview_geometry_unchanged(self):
        app = app_from_template(
            '{% frame border="single" width=40 height=8 %}{% vstack %}'
            '{% logview id="log" lines=lines width=30 height=4'
            ' border="single" %}{% endlogview %}'
            "{% endvstack %}{% endframe %}",
            state={"lines": ["hello"]},
        )
        with WijjitHarness(app, size=(40, 8)) as h:
            h.tick()
            logview = _element(app, "LogView")
            box_top = h.screen().splitlines()[1]
            drawn = box_top.rindex("┐") - box_top.index("┌") + 1
            assert drawn == 32  # 30 content + border, exactly as declared
            assert logview.bounds.width == 32


class TestTextInputFill:
    def test_fill_textinput_expands_and_row_does_not_overflow(self):
        app = app_from_template(
            '{% frame border="single" width=50 height=5 %}'
            '{% hstack width="fill" spacing=1 %}'
            '{% textinput id="inp" width="fill" %}{% endtextinput %}'
            '{% button action="a" %}Send{% endbutton %}'
            "{% endhstack %}{% endframe %}"
        )
        with WijjitHarness(app, size=(50, 5)) as h:
            h.tick()
            inp = _element(app, "TextInput")
            btn = _element(app, "Button")
            # The tag used to coerce "fill" to a fixed 30, pinning the input
            # at 32 columns and shoving the button past the frame edge.
            assert inp.bounds.width > 32
            assert inp.width == inp.bounds.width - 2  # bracket glyphs
            assert btn.bounds.x + btn.bounds.width <= 50

    def test_fixed_textinput_unchanged(self):
        app = app_from_template(
            '{% frame border="single" width=50 height=5 %}'
            '{% textinput id="inp" width=20 %}{% endtextinput %}{% endframe %}'
        )
        with WijjitHarness(app, size=(50, 5)) as h:
            h.tick()
            inp = _element(app, "TextInput")
            assert inp.width == 20
            assert inp.bounds.width == 22


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestSiblingImageViews:
    def test_sibling_imageviews_render_distinctly(self):
        """Guard against a shared cache or reconciler reuse blanking siblings."""
        img = str(
            (Path(__file__).parents[2] / "examples/assets/test-image.png").resolve()
        )
        app = app_from_template(
            "{% hstack %}"
            '{% imageview id="a" src=img height=8 mode="braille" threshold=60 %}'
            "{% endimageview %}"
            '{% imageview id="b" src=img height=8 mode="braille" threshold=160 %}'
            "{% endimageview %}"
            '{% imageview id="c" src=img height=8 mode="braille" invert=True %}'
            "{% endimageview %}"
            "{% endhstack %}",
            context={"img": img},
        )
        with WijjitHarness(app, size=(60, 12)) as h:
            h.tick()
            h.tick()
            views = [
                e for e in app.positioned_elements if type(e).__name__ == "ImageView"
            ]
            assert len(views) == 3
            grids = [
                tuple(tuple(cell[0] for cell in row) for row in v._cached_render)
                for v in views
            ]
            assert len(set(grids)) == 3  # all distinct
            for grid in grids:
                assert any(c != "⠀" for row in grid for c in row)  # none blank
