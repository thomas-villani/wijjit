"""Regression tests for list reconciliation identity in ``{% for %}`` loops.

Element tags auto-generate their reconciliation key from a per-render positional
counter, so by default the Nth element of a given type is keyed purely by its
position. Inserting or reordering rows therefore reuses the element (and the
transient state it carries) that previously sat at each slot, silently migrating
a user's typed value to the wrong logical row. This is the classic index-as-key
bug, and it is worse here than in React because the positional id doubles as the
state-binding key.

These tests pin down both halves of the fix:

* the ``key=`` attribute keeps each row's state with its logical row across a
  head-insert or reorder, for both bound and unbound inputs, and
* the default (unkeyed) behavior is exercised so a future change to it is a
  deliberate, visible decision rather than a silent one.

See ``etc``/``RELEASE_PLAN`` issue 1.1 and
:func:`wijjit.tags.layout.auto_element_id`.
"""

from __future__ import annotations

import re

import pytest

from wijjit import Wijjit, render_template_string
from wijjit.testing import WijjitHarness

pytestmark = pytest.mark.integration

_INPUT_RE = re.compile(r"\[([^\]]*)\]")


def _input_rows(harness: WijjitHarness) -> list[str]:
    """Return the trimmed contents of each rendered text input, top to bottom."""
    rows: list[str] = []
    for line in harness.screen().splitlines():
        match = _INPUT_RE.search(line)
        if match:
            rows.append(match.group(1).strip())
    return rows


def _build(template: str, rows: list[str]) -> Wijjit:
    app = Wijjit()
    app.state["rows"] = list(rows)

    @app.view("main", default=True)
    def main() -> object:
        return render_template_string(template, rows=app.state["rows"])

    return app


# Focus the second input (row "B"), type "hello", then insert a new row at the
# head so every positional slot shifts down by one.
def _type_into_second_then_head_insert(app: Wijjit, harness: WijjitHarness) -> None:
    harness.press("tab")
    harness.press("tab")
    harness.type("hello")
    app.state["rows"] = ["X", "A", "B"]
    harness.tick(frames=2)


UNKEYED = (
    "{% vstack %}{% for it in rows %}"
    "{% textinput placeholder=it %}{% endtextinput %}"
    "{% endfor %}{% endvstack %}"
)
KEYED = (
    "{% vstack %}{% for it in rows %}"
    "{% textinput key=it placeholder=it %}{% endtextinput %}"
    "{% endfor %}{% endvstack %}"
)
KEYED_UNBOUND = (
    "{% vstack %}{% for it in rows %}"
    "{% textinput key=it placeholder=it bind=false %}{% endtextinput %}"
    "{% endfor %}{% endvstack %}"
)


class TestUnkeyedLoopReconciliation:
    """The default (positional-key) behavior: state migrates on structural change."""

    def test_head_insert_migrates_typed_value_to_wrong_row(self):
        """Without a key, typing into row B and inserting a head row moves the
        typed value onto row A - the data-loss footgun this issue documents."""
        app = _build(UNKEYED, ["A", "B"])
        with WijjitHarness(app, size=(44, 8)) as harness:
            _type_into_second_then_head_insert(app, harness)
            rows = _input_rows(harness)

        # Three inputs after the insert: X, then the migrated value on A's row,
        # then B's row left empty (its placeholder).
        assert rows == ["X", "hello", "B"]


class TestKeyedLoopReconciliation:
    """An explicit ``key=`` pins each row's identity across structural change."""

    def test_key_keeps_bound_value_with_row_on_head_insert(self):
        """With key=it, the typed value stays with row B after a head insert."""
        app = _build(KEYED, ["A", "B"])
        with WijjitHarness(app, size=(44, 8)) as harness:
            _type_into_second_then_head_insert(app, harness)
            rows = _input_rows(harness)

        # X inserted at head; A's row stays empty; B keeps "hello".
        assert rows == ["X", "A", "hello"]

    def test_key_keeps_unbound_value_with_row_on_head_insert(self):
        """The same holds for an unbound input (value lives only on the element,
        so this isolates reconciliation identity from state binding)."""
        app = _build(KEYED_UNBOUND, ["A", "B"])
        with WijjitHarness(app, size=(44, 8)) as harness:
            _type_into_second_then_head_insert(app, harness)
            rows = _input_rows(harness)

        assert rows == ["X", "A", "hello"]

    def test_key_derives_a_stable_state_id_per_row(self):
        """A keyed bound input binds to a stable, key-derived state id, so the
        value survives a reorder in ``state`` (not merely on screen)."""
        app = _build(KEYED, ["A", "B"])
        with WijjitHarness(app, size=(44, 8)) as harness:
            _type_into_second_then_head_insert(app, harness)
            # id is derived as f"{type}_{key}" -> "textinput_B" for row B.
            assert app.state["textinput_B"] == "hello"
            assert app.state.get("textinput_A", "") == ""

    def test_key_reorder_preserves_values(self):
        """Reordering keyed rows carries each row's value with it."""
        app = _build(KEYED, ["A", "B", "C"])
        harness = WijjitHarness(app, size=(44, 10))
        with harness:
            harness.press("tab")
            harness.type("first")  # into row A
            harness.press("tab")
            harness.type("second")  # into row B
            app.state["rows"] = ["C", "B", "A"]  # reverse-ish reorder
            harness.tick(frames=2)
            rows = _input_rows(harness)

        # C empty, B keeps "second", A keeps "first".
        assert rows == ["C", "second", "first"]
