"""color -> color_mode rename with a back-compat alias (audit D3 / CC-3).

On BarChart/ColumnChart/Gauge, ``color`` was a *mode* enum
("default"/"gradient"/"threshold") -- colliding with ``color`` as a literal
color string on LineChart/Sparkline. ``color_mode`` is now the canonical mode
parameter; ``color`` remains a deprecated alias (constructor param + property)
so existing templates and code keep working.
"""

import pytest

from wijjit.elements.display.barchart import BarChart
from wijjit.elements.display.columnchart import ColumnChart
from wijjit.elements.display.gauge import Gauge

# (factory, default mode)
MODE_CHARTS = [
    (BarChart, "default"),
    (ColumnChart, "default"),
    (Gauge, "threshold"),
]


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_default_mode(factory, default):
    element = factory()
    assert element.color_mode == default
    assert element.color == default  # alias reads through


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_color_mode_canonical(factory, default):
    element = factory(color_mode="gradient")
    assert element.color_mode == "gradient"
    assert element.color == "gradient"


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_color_alias_constructor(factory, default):
    element = factory(color="gradient")
    assert element.color_mode == "gradient"


@pytest.mark.parametrize("factory,default", MODE_CHARTS)
def test_color_alias_assignment(factory, default):
    element = factory()
    element.color = "gradient"
    assert element.color_mode == "gradient"
    element.color_mode = "threshold"
    assert element.color == "threshold"
