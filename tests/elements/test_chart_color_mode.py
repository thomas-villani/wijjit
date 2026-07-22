"""``color_mode`` is the only spelling for the chart colouring enum.

BarChart/ColumnChart/Gauge colour themselves by *mode*
("default"/"gradient"/"threshold"). That parameter was once also spelled
``color``, which collided with ``color`` as a literal colour string on
LineChart/Sparkline -- passing ``color="#ff0000"`` to a BarChart silently did
nothing, because the value was read as a mode and fell through to the default.
The alias was removed before 1.0 so the name means one thing across every chart.
"""

import pytest

from wijjit.elements.display.barchart import BarChart
from wijjit.elements.display.columnchart import ColumnChart
from wijjit.elements.display.gauge import Gauge
from wijjit.elements.display.linechart import LineChart
from wijjit.elements.display.sparkline import Sparkline

# (factory, default mode)
MODE_CHARTS = [
    (BarChart, "default"),
    (ColumnChart, "default"),
    (Gauge, "threshold"),
]

# Charts where ``color`` means a literal colour string.
COLOR_CHARTS = [LineChart, Sparkline]


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_default_mode(factory, default):
    assert factory().color_mode == default


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_color_mode_constructor(factory, default):
    assert factory(color_mode="gradient").color_mode == "gradient"


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_color_mode_assignment(factory, default):
    element = factory()
    element.color_mode = "threshold"
    assert element.color_mode == "threshold"


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_color_alias_is_gone(factory, default):
    # The alias must not linger as a constructor parameter...
    with pytest.raises(TypeError):
        factory(color="gradient")
    # ...nor as a property shadowing the mode.
    assert not hasattr(factory(), "color")


@pytest.mark.parametrize("factory", COLOR_CHARTS)
def test_color_still_means_a_colour_elsewhere(factory):
    # The whole point of dropping the alias: on these charts ``color`` is a
    # literal colour and always was.
    element = factory(color="#ff0000")
    assert element.color == "#ff0000"
