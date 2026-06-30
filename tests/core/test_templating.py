"""Tests for the Flask-style templating API.

Covers :func:`render_template_string` / :func:`render_template`, the
``RenderedView`` return shape, per-render re-invocation (live context),
``on_enter``/``on_exit`` on the decorator, and backward compatibility with the
legacy ``{"template": ..., "data": {...}}`` dict return.
"""

from __future__ import annotations

import pytest

from wijjit import (
    RenderedView,
    Wijjit,
    render_template,
    render_template_string,
)
from wijjit.testing import WijjitHarness


class TestRenderHelpers:
    """The render_template_string / render_template builders."""

    def test_render_template_string_packs_template_and_context(self):
        rv = render_template_string("{{ x }}", x=1, y="two")
        assert isinstance(rv, RenderedView)
        assert rv.template == "{{ x }}"
        assert rv.template_file == ""
        assert rv.context == {"x": 1, "y": "two"}

    def test_render_template_packs_filename_and_context(self):
        rv = render_template("dash.tui", stats=[1, 2])
        assert isinstance(rv, RenderedView)
        assert rv.template == ""
        assert rv.template_file == "dash.tui"
        assert rv.context == {"stats": [1, 2]}

    def test_source_is_positional_only(self):
        # ``source``/``name`` are positional-only so a context kwarg may be
        # named "source" without colliding.
        rv = render_template_string("{{ source }}", source="ok")
        assert rv.context == {"source": "ok"}

    def test_context_is_copied_not_aliased(self):
        ctx = {"a": 1}
        rv = render_template_string("t", **ctx)
        ctx["a"] = 2
        assert rv.context == {"a": 1}


class TestNormalization:
    """ViewRouter accepts RenderedView, legacy dict, and bare-string returns."""

    def _init(self, app, name):
        view = app.views[name]
        app._initialize_view(view)
        return view

    def test_rendered_view_return(self):
        app = Wijjit()

        @app.view("v")
        def v():
            return render_template_string("Hi {{ name }}", name="Al")

        view = self._init(app, "v")
        rv = app.view_router.evaluate_render(view)
        assert rv.template == "Hi {{ name }}"
        assert rv.context == {"name": "Al"}

    def test_legacy_static_dict_return(self):
        app = Wijjit()

        @app.view("v")
        def v():
            return {"template": "Hi {{ name }}", "data": {"name": "Bo"}}

        view = self._init(app, "v")
        rv = app.view_router.evaluate_render(view)
        assert rv.template == "Hi {{ name }}"
        assert rv.context == {"name": "Bo"}

    def test_legacy_callable_data_return(self):
        app = Wijjit()
        app.state.n = 3

        @app.view("v")
        def v():
            return {"template": "{{ n }}", "data": lambda: {"n": app.state.n}}

        view = self._init(app, "v")
        assert app.view_router.evaluate_render(view).context == {"n": 3}

    def test_bare_string_return(self):
        app = Wijjit()

        @app.view("v")
        def v():
            return "just text {{ state.x }}"

        view = self._init(app, "v")
        rv = app.view_router.evaluate_render(view)
        assert rv.template == "just text {{ state.x }}"
        assert rv.context == {}

    def test_template_file_return(self):
        app = Wijjit()

        @app.view("v")
        def v():
            return render_template("page.tui", title="T")

        view = self._init(app, "v")
        rv = app.view_router.evaluate_render(view)
        assert rv.template_file == "page.tui"
        assert rv.context == {"title": "T"}

    def test_invalid_return_type_raises(self):
        app = Wijjit()

        @app.view("v")
        def v():
            return 42  # not a RenderedView / dict / str

        with pytest.raises(TypeError):
            self._init(app, "v")


class TestLiveReinvocation:
    """Synchronous views re-run each render, so derived context stays live."""

    def _app(self):
        app = Wijjit(initial_state={"n": 0})

        @app.view("main", default=True)
        def main_view():
            return render_template_string(
                """
{% frame title="T" border="single" width=30 height=4 %}
val {{ doubled }} n {{ state.n }}
{% endframe %}
""",
                doubled=app.state.n * 2,
            )

        @app.on_key("a")
        def bump(event):
            app.state.n += 1

        return app

    def test_derived_context_updates_across_renders(self):
        app = self._app()
        with WijjitHarness(app, size=(34, 6)) as h:
            h.tick()
            assert "val 0 n 0" in h.screen()
            h.press("a")
            h.tick(frames=2)
            screen = h.screen()
            # ``doubled`` recomputed from the new state on re-render.
            assert "val 2 n 1" in screen

    def test_legacy_static_dict_is_live_under_reinvocation(self):
        # The classic "frozen data" footgun: a derived value placed in a static
        # ``data`` dict. Because the view re-runs, it now refreshes.
        app = Wijjit(initial_state={"n": 0})

        @app.view("main", default=True)
        def main_view():
            return {
                "template": ("{% frame width=30 height=4 %}d {{ d }}{% endframe %}"),
                "data": {"d": app.state.n * 5},
            }

        @app.on_key("a")
        def bump(event):
            app.state.n += 1

        with WijjitHarness(app, size=(34, 6)) as h:
            h.tick()
            assert "d 0" in h.screen()
            h.press("a")
            h.tick(frames=2)
            assert "d 5" in h.screen()


class TestDecoratorHooks:
    """on_enter / on_exit declared on the @app.view decorator."""

    def test_on_enter_from_decorator_fires(self):
        calls = []

        app = Wijjit()

        def enter():
            calls.append("enter")

        @app.view("main", default=True, on_enter=enter)
        def main_view():
            return render_template_string(
                "{% frame width=20 height=3 %}hi{% endframe %}"
            )

        with WijjitHarness(app, size=(24, 5)) as h:
            h.tick()

        assert calls == ["enter"]

    def test_decorator_hook_takes_precedence_over_dict(self):
        app = Wijjit()
        chosen = []

        def decorator_enter():
            chosen.append("decorator")

        def dict_enter():
            chosen.append("dict")

        @app.view("main", on_enter=decorator_enter)
        def main_view():
            return {"template": "x", "on_enter": dict_enter}

        app._initialize_view(app.views["main"])
        assert app.views["main"].on_enter is decorator_enter

    def test_dict_hook_used_when_decorator_omits_it(self):
        app = Wijjit()

        def dict_enter():
            pass

        @app.view("main")
        def main_view():
            return {"template": "x", "on_enter": dict_enter}

        app._initialize_view(app.views["main"])
        assert app.views["main"].on_enter is dict_enter


class TestStateInjection:
    """state is auto-injected; an explicit state in context wins."""

    def test_state_available_without_passing(self):
        app = Wijjit(initial_state={"msg": "hello"})

        @app.view("main", default=True)
        def main_view():
            return render_template_string(
                "{% frame width=24 height=3 %}{{ state.msg }}{% endframe %}"
            )

        with WijjitHarness(app, size=(28, 5)) as h:
            h.tick()
            assert "hello" in h.screen()
