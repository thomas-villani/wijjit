"""Uniform ``on_change`` semantics across boolean inputs (audit D7 / CC-7).

``on_change`` was documented on Checkbox/Radio/Toggle but only fired on
*direct assignment* for Toggle -- Checkbox/Radio stored ``checked`` as a plain
attribute, so a reconciler-driven ``checked`` change fired a callback on Toggle
and silently not on the other two. ``checked`` is now a firing property on all
three (JS ``onChange`` semantics): assigning it fires ``on_change`` on any real
change (user interaction, programmatic assignment, or reconciler prop sync),
with an equality guard so assigning the same value is a no-op.
"""

from unittest.mock import Mock

import pytest

from wijjit.elements.input.checkbox import Checkbox
from wijjit.elements.input.radio import Radio
from wijjit.elements.input.toggle import Toggle


def _make(factory):
    """Construct a boolean input unchecked; Radio needs a group ``name``."""
    if factory is Radio:
        return factory(name="grp", checked=False)
    return factory(checked=False)


BOOLEAN_INPUTS = [Checkbox, Radio, Toggle]


@pytest.mark.parametrize("factory", BOOLEAN_INPUTS)
def test_assigning_checked_fires_on_change(factory):
    """Assigning ``checked`` fires on_change with (old, new) on all three."""
    element = _make(factory)
    callback = Mock()
    element.on_change = callback

    element.checked = True  # this is exactly what the reconciler does (setattr)
    callback.assert_called_once_with(False, True)

    callback.reset_mock()
    element.checked = False
    callback.assert_called_once_with(True, False)


@pytest.mark.parametrize("factory", BOOLEAN_INPUTS)
def test_assigning_same_value_is_noop(factory):
    """Equality guard: assigning the current value fires nothing (no loop)."""
    element = _make(factory)
    callback = Mock()
    element.on_change = callback

    element.checked = False  # already False
    callback.assert_not_called()


@pytest.mark.parametrize("factory", BOOLEAN_INPUTS)
def test_init_does_not_fire_on_change(factory):
    """Constructing with ``checked=True`` must not fire on_change."""
    # A callback attached after construction should not see the initial state.
    if factory is Radio:
        element = factory(name="grp", checked=True)
    else:
        element = factory(checked=True)
    callback = Mock()
    element.on_change = callback
    # No assignment yet -> no callback.
    callback.assert_not_called()
    assert element.checked is True


@pytest.mark.parametrize("factory", BOOLEAN_INPUTS)
def test_checked_roundtrips(factory):
    """The property reads back what was written."""
    element = _make(factory)
    assert element.checked is False
    element.checked = True
    assert element.checked is True


def test_checkbox_toggle_fires_once():
    """Checkbox.toggle() fires on_change exactly once (no double-fire)."""
    cb = Checkbox(checked=False)
    callback = Mock()
    cb.on_change = callback
    cb.toggle()
    callback.assert_called_once_with(False, True)


def test_radio_select_fires_once_and_deselects_sibling():
    """Radio.select() fires its own on_change once; the deselected sibling
    fires its own on_change once."""
    a = Radio(name="grp", value="a", checked=True)
    b = Radio(name="grp", value="b", checked=False)
    a.radio_group = [a, b]
    b.radio_group = [a, b]

    cb_a = Mock()
    cb_b = Mock()
    a.on_change = cb_a
    b.on_change = cb_b

    b.select()

    # b became checked, a was deselected -- one callback each.
    cb_b.assert_called_once_with(False, True)
    cb_a.assert_called_once_with(True, False)
    assert b.checked is True
    assert a.checked is False


def test_toggle_on_action_and_on_toggle_alias_both_fire():
    """Toggle activation fires the canonical on_action and the deprecated
    on_toggle alias."""
    toggle = Toggle(checked=False)
    on_action = Mock()
    on_toggle = Mock()
    toggle.on_action = on_action
    toggle.on_toggle = on_toggle

    toggle.toggle()

    on_action.assert_called_once()
    on_toggle.assert_called_once()
