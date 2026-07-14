"""Tests for `bind` as a state key name (review item 3.3).

`bind=True` fuses an element's id with its state key: `id="name"` colonizes
`state["name"]`, so an id collision is a state collision and two widgets cannot
share one key. `bind="somekey"` decouples the two - the id stays an identity,
and the key is named explicitly.

Both halves of the binding must agree on the key: the tags read `state[key]` at
render time, the wiring writes it back on change. They share one resolver
(`resolve_bind_key`), and these tests drive real key events through the harness
so a divergence between the two halves would show up as a value that renders but
never persists (which is exactly how the Slider bug survived).
"""

import pytest

from wijjit import Wijjit, render_template_string
from wijjit.tags.layout import resolve_bind_key
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


class TestResolveBindKey:
    """The shared resolver both halves of the binding call."""

    def test_true_binds_to_id(self):
        assert resolve_bind_key(True, "volume") == "volume"

    def test_string_names_the_key(self):
        assert resolve_bind_key("settings_volume", "volume") == "settings_volume"

    @pytest.mark.parametrize("bind", [False, None, ""])
    def test_falsy_does_not_bind(self, bind):
        """An empty string is falsy, so bind="" means "no binding", not key ""."""
        assert resolve_bind_key(bind, "volume") is None

    def test_default_key_overrides_id(self):
        """Radio/RadioGroup pass their group name as the default key."""
        assert resolve_bind_key(True, "r1", default_key="color") == "color"

    def test_explicit_key_beats_default_key(self):
        assert resolve_bind_key("other", "r1", default_key="color") == "other"

    def test_true_is_never_read_as_a_key(self):
        """isinstance(True, str) is False, so a bool cannot become a key name."""
        assert resolve_bind_key(True, None, default_key=None) is None


class TestBindDefaults:
    """bind=True / bind=False keep their existing meaning exactly."""

    def test_bind_true_reads_and_writes_the_id_key(self):
        app = make_app(
            '{% vstack %}{% textinput id="name" %}{% endtextinput %}{% endvstack %}',
            name="seed",
        )
        with WijjitHarness(app, size=(40, 6)) as h:
            h.assert_text("seed")  # read: state -> element
            h.press("tab")
            h.type("X")
            h.tick()
            assert app.state["name"] == "seedX"  # write: element -> state

    def test_bind_false_neither_reads_nor_writes(self):
        app = make_app(
            '{% vstack %}{% textinput id="name" bind=False %}{% endtextinput %}'
            "{% endvstack %}",
            name="seed",
        )
        with WijjitHarness(app, size=(40, 6)) as h:
            assert "seed" not in h.screen()  # no read
            h.press("tab")
            h.type("X")
            h.tick()
            assert app.state["name"] == "seed"  # no write

    def test_empty_bind_string_is_not_a_binding(self):
        app = make_app(
            '{% vstack %}{% textinput id="name" bind="" %}{% endtextinput %}'
            "{% endvstack %}",
            name="seed",
        )
        with WijjitHarness(app, size=(40, 6)) as h:
            assert "seed" not in h.screen()
            h.press("tab")
            h.type("X")
            h.tick()
            assert app.state["name"] == "seed"


class TestBindKeyDecouplesIdFromState:
    """bind="key" frees the id to be a pure identity."""

    def test_named_key_is_read_and_written_and_id_stays_clean(self):
        app = make_app(
            '{% vstack %}{% textinput id="name_field" bind="username" %}'
            "{% endtextinput %}{% endvstack %}",
            username="ada",
        )
        with WijjitHarness(app, size=(40, 6)) as h:
            h.assert_text("ada")
            h.press("tab")
            h.type("!")
            h.tick()

            assert app.state["username"] == "ada!"
            # Giving the element an id no longer colonizes that state key.
            assert "name_field" not in app.state

    def test_two_widgets_can_share_one_key(self):
        """The thing bind=True makes impossible: one key, two widgets."""
        app = make_app(
            "{% vstack %}"
            '{% textinput id="editor_a" bind="shared" %}{% endtextinput %}'
            '{% textinput id="editor_b" bind="shared" %}{% endtextinput %}'
            "{% endvstack %}",
            shared="hi",
        )
        with WijjitHarness(app, size=(40, 8)) as h:
            # Both read the one key.
            assert h.screen().count("hi") == 2

            h.press("tab")
            h.type("!")
            h.tick(frames=2)

            # Typing in the first writes the key, and the second re-reads it.
            assert app.state["shared"] == "hi!"
            assert h.screen().count("hi!") == 2

    def test_checkbox_and_toggle_bind_keys(self):
        app = make_app(
            "{% vstack %}"
            '{% checkbox id="cb" bind="enabled" %}{% endcheckbox %}'
            "{% endvstack %}",
            enabled=False,
        )
        with WijjitHarness(app, size=(40, 6)) as h:
            h.press("tab")
            h.press("space")
            h.tick()

            assert app.state["enabled"] is True
            assert "cb" not in app.state


class TestRadioBindsToGroupName:
    """Radio/RadioGroup key off the group name - now explicit, and overridable."""

    def test_radiogroup_default_key_is_its_name(self):
        app = make_app(
            "{% vstack %}"
            '{% radiogroup id="rg" name="color" options=["red", "blue"] %}'
            "{% endradiogroup %}"
            "{% endvstack %}",
            color="blue",
        )
        with WijjitHarness(app, size=(40, 8)) as h:
            h.press("tab")
            h.press("up")  # move to "red"
            h.tick()

            # The group's name is the state key, not its id.
            assert app.state["color"] == "red"
            assert "rg" not in app.state

    def test_radiogroup_bind_key_overrides_the_name(self):
        app = make_app(
            "{% vstack %}"
            '{% radiogroup id="rg" name="color" bind="theme" '
            'options=["red", "blue"] %}{% endradiogroup %}'
            "{% endvstack %}",
            theme="blue",
        )
        with WijjitHarness(app, size=(40, 8)) as h:
            h.press("tab")
            h.press("up")
            h.tick()

            assert app.state["theme"] == "red"
            assert "color" not in app.state
