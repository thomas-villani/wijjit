"""Tests for the Flask-style templating API.

Covers :func:`render_template_string` / :func:`render_template`, the
``RenderedView`` return shape, per-render re-invocation (live context),
``on_enter``/``on_exit`` on the decorator, and backward compatibility with the
legacy ``{"template": ..., "data": {...}}`` dict return.
"""

from __future__ import annotations

import textwrap

import pytest
from jinja2 import TemplateNotFound

from wijjit import (
    RenderedView,
    Wijjit,
    render_template,
    render_template_string,
)
from wijjit.core.renderer import Renderer
from wijjit.testing import WijjitHarness, load_example_app


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


def _write_app_module(tmp_path, *, with_templates: bool) -> str:
    """Write a tiny example app module under ``tmp_path`` and return its path.

    The module builds a module-level ``app = Wijjit()`` (no explicit
    ``template_dir``) so :func:`load_example_app` can exec it from ``tmp_path``
    and exercise Flask-style ``templates/`` auto-discovery relative to that
    file. When ``with_templates`` is True a sibling ``templates/home.tui`` is
    created too.
    """
    if with_templates:
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "home.tui").write_text(
            '{% frame title="Home" width=24 height=3 %}'
            "from file {{ who }}"
            "{% endframe %}",
            encoding="utf-8",
        )
    module = tmp_path / "demo_app.py"
    module.write_text(
        textwrap.dedent(
            """
            from wijjit import Wijjit, render_template

            app = Wijjit()

            @app.view("home", default=True)
            def home():
                return render_template("home.tui", who="World")
            """
        ),
        encoding="utf-8",
    )
    return str(module)


class TestTemplateDirDiscovery:
    """Flask-style auto-discovery of a ``templates/`` directory."""

    def test_auto_discovers_templates_dir_beside_module(self, tmp_path):
        module = _write_app_module(tmp_path, with_templates=True)
        app = load_example_app(module)
        assert app.config["TEMPLATE_DIR"] == str(tmp_path / "templates")
        assert app.renderer.using_file_loader is True

    def test_no_discovery_when_templates_dir_absent(self, tmp_path):
        module = _write_app_module(tmp_path, with_templates=False)
        app = load_example_app(module)
        assert app.config["TEMPLATE_DIR"] is None
        assert app.renderer.using_file_loader is False

    def test_explicit_template_dir_overrides_discovery(self, tmp_path):
        # A real templates/ dir exists beside this test file's tmp module, but
        # an explicit template_dir must win and discovery must not run.
        (tmp_path / "templates").mkdir()
        other = tmp_path / "elsewhere"
        other.mkdir()
        app = Wijjit(template_dir=str(other))
        assert app.config["TEMPLATE_DIR"] == str(other)

    def test_discovered_templates_render_end_to_end(self, tmp_path):
        module = _write_app_module(tmp_path, with_templates=True)
        app = load_example_app(module)
        with WijjitHarness(app, size=(30, 5)) as h:
            h.tick()
            screen = h.screen()
            assert "from file World" in screen
            assert "Home" in screen


class TestFileTemplateErrors:
    """render_template() against a missing dir / file gives actionable errors."""

    def test_render_template_without_dir_raises_runtime_error(self):
        renderer = Renderer()  # DictLoader, no template directory
        with pytest.raises(RuntimeError, match="render_template_string"):
            renderer.render_with_layout(template_name="home.tui")

    def test_render_file_without_dir_raises_runtime_error(self):
        renderer = Renderer()
        with pytest.raises(RuntimeError, match="template directory"):
            renderer.render_file("home.tui")

    def test_missing_file_reports_searched_directory(self, tmp_path):
        renderer = Renderer(template_dir=str(tmp_path))
        with pytest.raises(TemplateNotFound) as excinfo:
            renderer.render_file("nope.tui")
        # The wrapped error names the directory that was searched.
        assert str(tmp_path) in str(excinfo.value)
