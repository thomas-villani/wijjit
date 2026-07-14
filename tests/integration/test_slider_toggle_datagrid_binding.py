"""Slider/Toggle/DataGrid write their value back to state (review item 3.3).

All three advertised `bind=True` and their tags read `state[id]` at render, but
none of them appeared in the wiring dispatch, so nothing ever subscribed to the
`on_change` they were already firing. The result was a binding that only worked
in one direction, silently: `examples/widgets/slider_demo.py` showed the bar at
59 while its own readout, driven from `state["volume"]`, still said 50.

These tags had zero test coverage, which is how the gap survived. The tests
drive real key events through the harness and assert on `app.state`, so a
one-way binding fails here.
"""

from wijjit import Wijjit, render_template_string
from wijjit.elements.input.datagrid import DataGrid
from wijjit.testing import WijjitHarness


def make_app(template, **state):
    """Build a one-view app over `template` with `state` pre-seeded."""
    app = Wijjit()
    for key, value in state.items():
        app.state[key] = value

    @app.view("main", default=True)
    def main():
        return render_template_string(template)

    return app


class TestSliderBinding:
    """The reproduced bug: the bar moved, state did not."""

    def test_slider_writes_back_to_state(self):
        app = make_app(
            '{% vstack %}{% slider id="vol" min=0 max=100 %}{% endslider %}'
            "{% endvstack %}",
            vol=10,
        )
        with WijjitHarness(app, size=(50, 6)) as h:
            h.press("tab")
            for _ in range(5):
                h.press("right")
            h.tick()

            assert app.state["vol"] == 15

    def test_slider_binds_to_a_named_key(self):
        app = make_app(
            '{% vstack %}{% slider id="vol_widget" bind="volume" min=0 max=100 %}'
            "{% endslider %}{% endvstack %}",
            volume=10,
        )
        with WijjitHarness(app, size=(50, 6)) as h:
            h.press("tab")
            h.press("right")
            h.tick()

            assert app.state["volume"] == 11
            assert "vol_widget" not in app.state

    def test_slider_bind_false_does_not_write(self):
        app = make_app(
            '{% vstack %}{% slider id="vol" bind=False min=0 max=100 %}{% endslider %}'
            "{% endvstack %}",
            vol=10,
        )
        with WijjitHarness(app, size=(50, 6)) as h:
            h.press("tab")
            h.press("right")
            h.tick()

            assert app.state["vol"] == 10


class TestToggleBinding:
    """Same gap as Slider: on_change fired with nobody listening."""

    def test_toggle_writes_back_to_state(self):
        app = make_app(
            '{% vstack %}{% toggle id="dark" %}{% endtoggle %}{% endvstack %}',
            dark=False,
        )
        with WijjitHarness(app, size=(50, 6)) as h:
            h.press("tab")
            h.press("space")
            h.tick()

            assert app.state["dark"] is True

            # ...and back again, so this is a live binding, not a one-shot.
            h.press("space")
            h.tick()
            assert app.state["dark"] is False


class TestDataGridBinding:
    """DataGrid must write back a *copy* of its rows."""

    TEMPLATE = (
        '{% vstack %}{% datagrid id="rows" columns=["A", "B"] height=6 %}'
        "{% enddatagrid %}{% endvstack %}"
    )

    def _grid(self, app):
        for elem in app.positioned_elements:
            if isinstance(elem, DataGrid):
                return elem
        raise AssertionError("no DataGrid in the rendered tree")

    def test_two_successive_edits_both_reach_state(self):
        """The copy is load-bearing, and only a *second* edit proves it.

        DataGrid.set_cell mutates self.data in place and then fires
        on_data_change(self.data). If the write-back stored that reference,
        state[key] would *be* the element's live list - so on the next edit
        State.__setitem__ would compare the new value against itself, find them
        equal, and fire no change callback. The grid would update once and then
        go silent. A single-edit test passes either way.
        """
        app = make_app(self.TEMPLATE, rows=[["a", "b"], ["c", "d"]])
        with WijjitHarness(app, size=(60, 12)) as h:
            h.tick()
            grid = self._grid(app)

            grid.set_cell(0, 0, "FIRST")
            h.tick()
            assert app.state["rows"][0][0] == "FIRST"

            grid.set_cell(1, 1, "SECOND")
            h.tick()
            assert app.state["rows"][1][1] == "SECOND"
            # The first edit must survive the second.
            assert app.state["rows"][0][0] == "FIRST"

    def test_every_edit_fires_a_change_callback(self):
        """The failure mode is a *missing callback*, not wrong data.

        If state aliased the grid's rows, __setitem__ would still store the
        value - so the data would look right - but the equality gate would see
        old_value and value as the same mutated object and fire nothing, so the
        screen would never repaint. Assert on the callbacks, not just the data.

        The two edits deliberately run back-to-back with **no render between
        them**: a re-render re-assigns the ``data`` prop through DataGrid's
        normalizing setter, which would copy the alias away and mask the bug.
        This is the case only the write-back's own copy defends.
        """
        app = make_app(self.TEMPLATE, rows=[["a", "b"], ["c", "d"]])
        with WijjitHarness(app, size=(60, 12)) as h:
            h.tick()
            grid = self._grid(app)

            fired = []
            app.state.on_change(lambda key, old, new: fired.append(key))

            grid.set_cell(0, 0, "FIRST")
            grid.set_cell(1, 1, "SECOND")

            assert fired == ["rows", "rows"]
            assert app.state["rows"][0][0] == "FIRST"
            assert app.state["rows"][1][1] == "SECOND"

    def test_state_does_not_alias_the_element_rows(self):
        """state's snapshot must be distinct from the grid's working list."""
        app = make_app(self.TEMPLATE, rows=[["a", "b"]])
        with WijjitHarness(app, size=(60, 12)) as h:
            h.tick()
            grid = self._grid(app)
            grid.set_cell(0, 0, "x")
            h.tick()

            assert app.state["rows"] is not grid.data
            assert app.state["rows"][0] is not grid.data[0]

    def test_datagrid_binds_to_a_named_key(self):
        app = make_app(
            '{% vstack %}{% datagrid id="grid" bind="sheet" columns=["A"] height=6 %}'
            "{% enddatagrid %}{% endvstack %}",
            sheet=[["a"]],
        )
        with WijjitHarness(app, size=(60, 12)) as h:
            h.tick()
            self._grid(app).set_cell(0, 0, "z")
            h.tick()

            assert app.state["sheet"][0][0] == "z"
            assert "grid" not in app.state
