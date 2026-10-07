"""``action=`` reaches the element and dispatches, for every dispatching element.

Checkbox, Radio, CheckboxGroup, RadioGroup and Toggle keep ``action`` as a
plain attribute, not a constructor parameter. The registry's signature filter
dropped it on the render that created the element, and the reconciler only
re-applies a prop whose value *changed*, so a constant ``action="go"`` never
reached the element: ``elem.action`` stayed ``None`` and the wiring never set
``on_action``. ``action`` is now a framework-only prop, applied right after
construction.
"""

from __future__ import annotations

import pytest

from wijjit.core.element_registry import ElementRegistry
from wijjit.core.vdom import FRAMEWORK_ONLY_PROPS
from wijjit.elements.base import Element
from wijjit.testing import WijjitHarness, app_from_template


def _drive(template, keys, element_id, **app_kwargs):
    """Render ``template``, Tab to the first element, press ``keys``.

    Returns the list of ActionEvents the ``go`` handler saw, and the element.
    """
    calls = []
    app = app_from_template(
        template, actions={"go": lambda event: calls.append(event)}, **app_kwargs
    )
    with WijjitHarness(app, size=(60, 10)) as h:
        h.press("tab")
        element = app.get_element_by_id(element_id)
        for key in keys:
            h.press(key)
        h.assert_no_errors()
    return calls, element


CASES = {
    "checkbox": (
        '{% vstack %}{% checkbox id="el" action="go" %}Agree{% endcheckbox %}'
        "{% endvstack %}",
        ["enter"],
    ),
    "radio": (
        '{% vstack %}{% radio id="el" name="size" value="s" action="go" %}Small'
        "{% endradio %}{% endvstack %}",
        ["enter"],
    ),
    "checkboxgroup": (
        '{% vstack %}{% checkboxgroup id="el" options=["a", "b"] action="go" %}'
        "{% endcheckboxgroup %}{% endvstack %}",
        ["enter"],
    ),
    "radiogroup": (
        '{% vstack %}{% radiogroup id="el" name="color" options=["red", "blue"] '
        'action="go" %}{% endradiogroup %}{% endvstack %}',
        ["enter"],
    ),
    "toggle": (
        '{% vstack %}{% toggle id="el" action="go" %}Dark{% endtoggle %}'
        "{% endvstack %}",
        ["space"],
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_action_reaches_element_and_dispatches(name):
    template, keys = CASES[name]
    calls, element = _drive(template, keys, "el")

    assert element.action == "go"
    assert element.on_action is not None
    assert len(calls) == 1
    assert calls[0].action_id == "go"
    # These elements carry no payload with their action.
    assert calls[0].data is None


def test_checkbox_space_toggles_without_dispatching():
    # Enter is the "submit" key for a checkbox; Space only toggles it.
    template, _ = CASES["checkbox"]
    calls, element = _drive(template, ["space"], "el")
    assert element.checked is True
    assert calls == []


def test_checkbox_enter_toggles_and_dispatches():
    template, _ = CASES["checkbox"]
    calls, element = _drive(template, ["enter"], "el")
    assert element.checked is True
    assert len(calls) == 1


def test_checkboxgroup_enter_toggles_highlighted_option_and_dispatches():
    template, _ = CASES["checkboxgroup"]
    calls, element = _drive(template, ["enter"], "el")
    assert element.selected_values == {"a"}
    assert len(calls) == 1


def test_radiogroup_space_selects_enter_dispatches():
    template, _ = CASES["radiogroup"]
    calls, element = _drive(template, ["down", "space"], "el")
    assert element.selected_value == "blue"
    assert calls == []

    calls, element = _drive(template, ["down", "space", "enter"], "el")
    assert element.selected_value == "blue"
    assert len(calls) == 1


def test_toggle_dispatches_on_every_flip():
    template, _ = CASES["toggle"]
    calls, element = _drive(template, ["space", "enter"], "el")
    assert element.checked is False  # flipped twice
    assert [c.action_id for c in calls] == ["go", "go"]


def test_per_item_action_names_dispatch_from_a_loop():
    # The idiom the tutorial uses: build each row's action with ``~``.
    seen = []
    app = app_from_template(
        "{% vstack %}{% for item in state.rows %}"
        '{% checkbox id="todo_" ~ item action="toggle_" ~ item %}{{ item }}'
        "{% endcheckbox %}{% endfor %}{% endvstack %}",
        state={"rows": [1, 2]},
        actions={
            "toggle_1": lambda e: seen.append(e.action_id),
            "toggle_2": lambda e: seen.append(e.action_id),
        },
    )
    with WijjitHarness(app, size=(40, 6)) as h:
        h.press("tab")
        h.press("tab")
        h.press("enter")
        h.assert_no_errors()
        assert app.get_element_by_id("todo_1").action == "toggle_1"
    assert seen == ["toggle_2"]


def test_action_change_between_renders_rewires():
    # A state-driven action still updates through the normal changed-prop path.
    calls = []
    app = app_from_template(
        '{% vstack %}{% checkbox id="el" action=state.act %}A{% endcheckbox %}'
        "{% endvstack %}",
        state={"act": "first"},
        actions={
            "first": lambda e: calls.append(e.action_id),
            "second": lambda e: calls.append(e.action_id),
        },
    )
    with WijjitHarness(app, size=(40, 5)) as h:
        h.press("tab")
        h.press("enter")
        app.state["act"] = "second"
        h.tick(frames=1)
        assert app.get_element_by_id("el").action == "second"
        h.press("enter")
        h.assert_no_errors()
    assert calls == ["first", "second"]


def test_button_action_unaffected():
    # Button takes ``action`` in __init__; the extra setattr is harmless.
    calls, element = _drive(
        '{% vstack %}{% button id="el" action="go" %}Go{% endbutton %}'
        "{% endvstack %}",
        ["enter"],
        "el",
    )
    assert element.action == "go"
    assert [c.action_id for c in calls] == ["go"]


def test_action_is_a_framework_only_prop():
    assert "action" in FRAMEWORK_ONLY_PROPS


def test_base_element_does_not_dispatch_action():
    assert Element.dispatches_action is False


def test_dispatching_element_types_are_exactly_the_wired_ones():
    # ``dispatches_action`` drives the validator's ignored-attribute check, so
    # it must name exactly the classes core/wiring.py wires to a dispatch.
    registry = ElementRegistry()
    factories = {registry.get_factory(name) for name in registry.list_types()}
    dispatching = {
        factory.__name__
        for factory in factories
        if factory is not None
        and factory.__module__.startswith("wijjit.")
        and getattr(factory, "dispatches_action", False)
    }
    assert dispatching == {
        "Button",
        "Checkbox",
        "CheckboxGroup",
        "CodeEditor",
        "ContentView",
        "Link",
        "Radio",
        "RadioGroup",
        "TextArea",
        "TextInput",
        "Toggle",
        "Tree",
    }
