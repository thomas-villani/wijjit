"""Tests for WijjitEnvironment: State keys resolve ahead of State methods.

Jinja's default ``Environment.getattr`` tries ``getattr()`` first, so
``{{ state.items }}`` on a ``UserDict`` finds the bound method and never the
data. That is what used to make ``items``/``keys``/``get``/``data`` illegal as
state keys. ``WijjitEnvironment`` looks the key up first, which frees the names
while leaving the method call available whenever no such key exists.
"""

import pytest
from jinja2 import UndefinedError

from wijjit.core.renderer import Renderer
from wijjit.core.state import State


class TestStateKeyResolution:
    """A present key wins over the same-named State method."""

    @pytest.mark.parametrize(
        "key,value",
        [
            ("items", ["a", "b"]),
            ("keys", "my keys"),
            ("values", 42),
            ("data", "not the backing store"),
            ("update", "updatable"),
            ("copy", "copyable"),
        ],
    )
    def test_method_named_key_renders_its_value(self, key, value):
        """{{ state.<method name> }} renders the stored value, not the method."""
        renderer = Renderer()
        state = State({key: value})

        result = renderer.env.from_string(f"{{{{ state.{key} }}}}").render(state=state)

        assert result == str(value)

    def test_key_wins_for_iteration(self):
        """A list under state['items'] is iterable in a for loop."""
        renderer = Renderer()
        state = State({"items": ["x", "y"]})

        result = renderer.env.from_string(
            "{% for it in state.items %}{{ it }};{% endfor %}"
        ).render(state=state)

        assert result == "x;y;"

    def test_attr_filter_matches_dot_access(self):
        """|attr() routes through the same getattr, so it agrees with dot access."""
        renderer = Renderer()
        state = State({"items": ["a"]})

        result = renderer.env.from_string("{{ state|attr('items') }}").render(
            state=state
        )

        assert result == "['a']"


class TestMethodFallback:
    """With no such key, the Mapping methods are still reachable."""

    def test_items_method_still_iterates(self):
        """{% for k, v in state.items() %} works when there is no 'items' key."""
        renderer = Renderer()
        state = State({"a": 1, "b": 2})

        result = renderer.env.from_string(
            "{% for k, v in state.items() %}{{ k }}={{ v }};{% endfor %}"
        ).render(state=state)

        assert result == "a=1;b=2;"

    def test_get_guard_idiom_still_works(self):
        """{{ state.get('k', default) }} is the documented guard under DEBUG."""
        renderer = Renderer()
        state = State({"present": "yes"})

        result = renderer.env.from_string(
            "{{ state.get('present', 'dflt') }}|{{ state.get('absent', 'dflt') }}"
        ).render(state=state)

        assert result == "yes|dflt"

    def test_plain_dicts_are_unaffected(self):
        """Only State is special-cased; a plain dict keeps Jinja's semantics."""
        renderer = Renderer()

        result = renderer.env.from_string(
            "{% for k, v in d.items() %}{{ k }}={{ v }};{% endfor %}"
        ).render(d={"a": 1})

        assert result == "a=1;"


class TestStrictUndefinedPreserved:
    """A genuinely missing name still falls through to undefined."""

    def test_strict_mode_still_raises_on_missing_key(self):
        """Item 3.2's DEBUG-gated StrictUndefined must survive the override."""
        renderer = Renderer(strict_undefined=True)
        state = State({"present": 1})

        with pytest.raises(UndefinedError):
            renderer.env.from_string("{{ state.missing }}").render(state=state)

    def test_lenient_mode_still_renders_empty(self):
        """Production stays lenient: one bad key cannot crash a running TUI."""
        renderer = Renderer()
        state = State({"present": 1})

        result = renderer.env.from_string("[{{ state.missing }}]").render(state=state)

        assert result == "[]"
