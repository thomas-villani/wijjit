"""Tests for the {% radiogroup %} template tag layout."""

from __future__ import annotations

from wijjit.core.vdom import VNode
from wijjit.devtools._render import render_template_source

_OPTIONS = (
    '[{"value":"a","label":"A"},'
    ' {"value":"b","label":"B"},'
    ' {"value":"c","label":"C"}]'
)


def _find(node: VNode | None, type_name: str) -> VNode | None:
    """Depth-first search for the first VNode of ``type_name``."""
    if node is None:
        return None
    if node.type == type_name:
        return node
    for child in node.children:
        found = _find(child, type_name)
        if found is not None:
            return found
    return None


def _radiogroup_height(orientation: str) -> int:
    """Render a 3-option radiogroup and return its reserved layout height."""
    source = (
        f'{{% radiogroup id="g" orientation="{orientation}" '
        f"options={_OPTIONS} %}}{{% endradiogroup %}}"
    )
    outcome = render_template_source(source, width=80, height=24)
    assert outcome.render_error is None
    node = _find(outcome.root, "RadioGroup")
    assert node is not None
    return int(node.layout_spec_dict()["height"])


def test_horizontal_radiogroup_reserves_one_row() -> None:
    """Regression: a horizontal group draws on one line, so it must reserve a
    single row of layout height regardless of the option count (previously it
    reserved ``len(options)`` rows and pushed later content down)."""
    assert _radiogroup_height("horizontal") == 1


def test_vertical_radiogroup_reserves_one_row_per_option() -> None:
    """A vertical group still reserves one row per option."""
    assert _radiogroup_height("vertical") == 3
