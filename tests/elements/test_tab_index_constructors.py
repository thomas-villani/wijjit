"""Constructor-level acceptance of ``tab_index`` and ``set[str]`` ``classes``.

Before the 0.1.0 API-consistency batch, ``Element.__init__`` advertised a
``tab_index`` parameter but no concrete focusable element accepted it -- e.g.
``TextInput(id="x", tab_index=2)`` raised ``TypeError`` and tab order only
worked because the tag layer poked the attribute post-construction. Likewise
the subclasses narrowed the ``classes`` annotation to drop ``set[str]`` even
though the base normalizes a set. These tests pin both down at the Python API.
"""

import pytest

from wijjit.elements.display.link import Link
from wijjit.elements.display.pager import Pager
from wijjit.elements.display.tabbed_panel import TabbedPanel
from wijjit.elements.input.button import Button
from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup
from wijjit.elements.input.code_editor import CodeEditor
from wijjit.elements.input.datagrid import DataGrid
from wijjit.elements.input.radio import Radio, RadioGroup
from wijjit.elements.input.select import Select
from wijjit.elements.input.slider import Slider
from wijjit.elements.input.text import TextArea, TextInput
from wijjit.elements.input.toggle import Toggle

# (factory, required positional/keyword args) for every focusable element.
FOCUSABLE_FACTORIES = [
    (TextInput, {}),
    (TextArea, {}),
    (CodeEditor, {}),
    (Button, {"label": "x"}),
    (Checkbox, {}),
    (CheckboxGroup, {}),
    (Radio, {"name": "g"}),
    (RadioGroup, {"name": "g"}),
    (Toggle, {}),
    (Slider, {}),
    (Select, {}),
    (DataGrid, {}),
    (Link, {"text": "x"}),
    (Pager, {}),
    (TabbedPanel, {}),
]


@pytest.mark.parametrize(
    "factory,kwargs", FOCUSABLE_FACTORIES, ids=lambda v: getattr(v, "__name__", "")
)
def test_constructor_accepts_tab_index(factory, kwargs):
    element = factory(tab_index=7, **kwargs)
    assert element.tab_index == 7


@pytest.mark.parametrize(
    "factory,kwargs", FOCUSABLE_FACTORIES, ids=lambda v: getattr(v, "__name__", "")
)
def test_constructor_accepts_set_classes(factory, kwargs):
    element = factory(classes={"a", "b"}, **kwargs)
    assert element.classes == {"a", "b"}


def test_tabbed_panel_tab_index_distinct_from_active_tab_index():
    panel = TabbedPanel(tab_index=3, active_tab_index=1)
    assert panel.tab_index == 3
    assert panel.active_tab_index == 1
