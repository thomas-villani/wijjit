"""Render-signature completeness for the skip-unchanged fast path.

Each element that opts in to the "skip unchanged elements" optimization
(review 2.5, option c) implements
:meth:`~wijjit.elements.base.Element.render_signature`, returning a comparable
tuple that must capture every instance attribute its ``render_to`` reads. If a
paint-affecting attribute is missing, an unchanged signature would wrongly skip
a repaint and leave stale cells on screen.

These unit tests pin *sensitivity*: mutating any paint-affecting attribute (and
the shared focus/class state folded in by ``_style_signature``) must change the
signature. They complement the integration verify-mode sweeps
(``tests/integration/test_skip_unchanged_elements.py``), which paint would-be
skips and assert byte-identity end to end.
"""

from __future__ import annotations

from typing import Any

import pytest

from wijjit.elements.display.columnchart import ColumnChart
from wijjit.elements.display.gauge import Gauge
from wijjit.elements.display.link import Link
from wijjit.elements.display.progress import ProgressBar
from wijjit.elements.display.sparkline import Sparkline
from wijjit.elements.display.status_indicator import StatusIndicator
from wijjit.elements.display.statusbar import StatusBar
from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup
from wijjit.elements.input.radio import Radio, RadioGroup
from wijjit.elements.input.slider import Slider
from wijjit.elements.input.toggle import Toggle

# Each case: a factory building a fresh element, and a list of
# (attribute, new_value) mutations that each must change render_signature().
# Values need only be *distinct* from the default - the signature is compared,
# never rendered, so arbitrary sentinels are fine.
_OPTIONS = [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}]

_CASES: dict[str, tuple[Any, list[tuple[str, Any]]]] = {
    "Checkbox": (
        lambda: Checkbox(id="c", label="Agree"),
        [("label", "Changed")],
    ),
    "CheckboxGroup": (
        lambda: CheckboxGroup(id="cg", options=list(_OPTIONS)),
        [
            ("options", [{"value": "x", "label": "X"}]),
            ("selected_values", {"a"}),
            ("highlighted_index", 1),
            ("orientation", "horizontal"),
            ("width", 42),
            ("title", "T"),
        ],
    ),
    "Radio": (
        lambda: Radio(name="grp", id="r", label="One"),
        [("label", "Two")],
    ),
    "RadioGroup": (
        lambda: RadioGroup(name="grp", id="rg", options=list(_OPTIONS)),
        [
            ("options", [{"value": "x", "label": "X"}]),
            ("selected_index", 1),
            ("highlighted_index", 1),
            ("orientation", "horizontal"),
            ("width", 42),
            ("title", "T"),
        ],
    ),
    "Toggle": (
        lambda: Toggle(id="t", label="L", on_label="On", off_label="Off"),
        [
            ("label", "Changed"),
            ("on_label", "Yes"),
            ("off_label", "No"),
            ("label_mode", "dual"),
        ],
    ),
    "Slider": (
        lambda: Slider(id="s", value=10, min_val=0, max_val=100, width=20),
        [
            ("_value", 55.0),
            ("min_val", 5.0),
            ("max_val", 50.0),
            ("width", 30),
            ("label", "Vol"),
            ("show_value", False),
            ("float_mode", True),
        ],
    ),
    "ProgressBar": (
        lambda: ProgressBar(id="p", value=30, max_value=100),
        [
            ("value", 60),
            ("max_value", 200),
            ("style", "percentage"),
            ("show_percentage", False),
            ("fill_char", "#"),
            ("empty_char", "."),
        ],
    ),
    "Gauge": (
        lambda: Gauge(id="g", value=40),
        [
            ("value", 70),
            ("min_value", 5),
            ("max_value", 200),
            ("style", "arc"),
            ("width", 40),
            ("height", 8),
            ("show_value", False),
            ("show_minmax", True),
            ("show_ticks", True),
            ("color_mode", "gradient"),
            ("thresholds", [(50, "red")]),
            ("label", "CPU"),
            ("unit", "%"),
            ("border_style", "double"),
        ],
    ),
    "Sparkline": (
        lambda: Sparkline(id="sp", data=[1, 2, 3]),
        [
            ("values", [4, 5, 6]),
            ("style", "bar"),
            ("width", 40),
            ("height", 4),
            ("show_current", True),
            ("show_minmax", True),
            ("color", "red"),
            ("border_style", "single"),
        ],
    ),
    "StatusIndicator": (
        lambda: StatusIndicator(id="si", status="ok", label="Ready"),
        [
            ("_status", "error"),
            ("indicator_style", "circle"),
            ("label", "Down"),
        ],
    ),
    "StatusBar": (
        lambda: StatusBar(id="sb", left="L", center="C", right="R"),
        [
            ("left", "Left2"),
            ("center", "Center2"),
            ("right", "Right2"),
            ("bg_color", "blue"),
            ("text_color", "white"),
        ],
    ),
    "Link": (
        lambda: Link(text="Home", id="ln"),
        [("text", "Away")],
    ),
    "ColumnChart": (
        lambda: ColumnChart(id="cc", data=[1, 2, 3]),
        [
            ("values", [4, 5, 6]),
            ("labels", ["x", "y", "z"]),
            ("width", 40),
            ("height", 8),
            ("column_width", 5),
            ("spacing", 2),
            ("show_labels", False),
            ("show_axis", False),
            ("axis_width", 8),
            ("show_grid", True),
            ("color_mode", "gradient"),
            ("border_style", "double"),
        ],
    ),
}


@pytest.mark.parametrize("name", sorted(_CASES))
def test_signature_is_not_none(name: str) -> None:
    """Every opted-in element returns a concrete (non-None) signature."""
    factory, _ = _CASES[name]
    assert factory().render_signature() is not None


@pytest.mark.parametrize(
    "name,attr,value",
    [(n, a, v) for n, (_, muts) in _CASES.items() for (a, v) in muts],
)
def test_signature_sensitive_to_attr(name: str, attr: str, value: Any) -> None:
    """Mutating a paint-affecting attribute changes the render signature."""
    factory, _ = _CASES[name]
    element = factory()
    before = element.render_signature()
    setattr(element, attr, value)
    after = element.render_signature()
    assert after != before, (
        f"{name}.render_signature() ignored a change to {attr!r}: "
        "the skip-unchanged fast path would leave stale cells on screen"
    )


@pytest.mark.parametrize("name", sorted(_CASES))
def test_signature_sensitive_to_focus(name: str) -> None:
    """Focus state (folded in via _style_signature) changes the signature."""
    factory, _ = _CASES[name]
    element = factory()
    before = element.render_signature()
    element.focused = not element.focused
    assert element.render_signature() != before
