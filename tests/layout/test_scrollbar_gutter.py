"""Scrollbar-gutter reservation across scroll on/off transitions (review 2.4).

The O(2^depth) layout fix (``FrameNode.assign_bounds``) predicts the
vertical-scrollbar gutter from the frame's persisted ``_needs_scroll`` and lays
the subtree out once, re-laying-out only on the frame where scrolling toggles.
This test pins the correctness the optimization must preserve: a ``width="fill"``
child loses exactly one column to the gutter when the frame overflows and
reclaims it when content fits again - across content that grows and shrinks
between renders, which is precisely the on->off / off->on correction path.
"""

from wijjit.testing import WijjitHarness, app_from_template

# Outer frame is fixed width; a width="fill" inner frame fills the interior. It
# gets the full interior width when content fits and one column less when the
# frame overflows and reserves the scrollbar gutter. Interior height is 4 rows
# (height 6 minus two borders); the inner frame is 2 rows, so rows=1 fits (3<=4)
# and rows=20 overflows.
TPL = """
{% frame id="outer" width=40 height=6 scrollable=true %}
  {% vstack spacing=0 %}
    {% frame id="inner" width="fill" height=2 %}x{% endframe %}
    {% for i in range(state.rows) %}{% text %}row {{ i }}{% endtext %}{% endfor %}
  {% endvstack %}
{% endframe %}
"""


def _inner_width(app):
    return app.get_element_by_id("inner").bounds.width


def test_fill_child_reclaims_and_reserves_gutter_across_transitions():
    app = app_from_template(TPL, state={"rows": 1})
    with WijjitHarness(app, size=(60, 20)) as h:
        full = _inner_width(app)
        assert full > 1

        # Grow past the viewport -> scrollbar gutter reserved (off->on).
        app.state["rows"] = 20
        h.tick()
        assert _inner_width(app) == full - 1

        # Shrink back to fitting -> gutter reclaimed (on->off correction).
        app.state["rows"] = 1
        h.tick()
        assert _inner_width(app) == full

        # Grow again -> reserved once more (off->on correction).
        app.state["rows"] = 20
        h.tick()
        assert _inner_width(app) == full - 1
