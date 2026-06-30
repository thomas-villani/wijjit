"""Build a :class:`~wijjit.core.app.Wijjit` app from a bare template string.

Most tests (and the devtools CLI) only need a single view rendered from a
template plus a few action/key handlers - not a full example ``.py`` module.
:func:`app_from_template` wires those into a ready-to-drive app so they can be
handed straight to :class:`~wijjit.testing.harness.WijjitHarness`::

    app = app_from_template(
        "{% frame %}{% button id='go' label='Go' action='go' %}{% endframe %}",
        state={"clicked": False},
        actions={"go": lambda **_: app.state.update(clicked=True)},
    )
    with WijjitHarness(app) as h:
        h.press("enter")
        assert h.state["clicked"]
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wijjit.core.app import Wijjit
from wijjit.core.templating import RenderedView, render_template_string


def app_from_template(
    template: str,
    *,
    state: dict[str, Any] | None = None,
    actions: dict[str, Callable[..., Any]] | None = None,
    on_key: dict[str, Callable[..., Any]] | None = None,
    views: dict[str, str | RenderedView | Callable[[], Any]] | None = None,
    context: dict[str, Any] | None = None,
    view_name: str = "main",
    **config_overrides: Any,
) -> Wijjit:
    """Build a Wijjit app from a template string and optional handlers.

    Parameters
    ----------
    template : str
        Inline Wijjit/Jinja2 template source for the default view.
    state : dict, optional
        Initial reactive state (``app.state``).
    actions : dict, optional
        Mapping of action id -> handler, registered via ``@app.on_action``.
    on_key : dict, optional
        Mapping of key name -> handler, registered via ``@app.on_key``.
    views : dict, optional
        Extra named views. Each value may be a template string, a
        :class:`~wijjit.core.templating.RenderedView`, or a zero-arg view
        function returning what to render.
    context : dict, optional
        Context passed to the default view's template. Captured once (use
        ``state`` for values that change between renders).
    view_name : str, optional
        Name of the default view (default: ``"main"``).
    **config_overrides
        Forwarded to :class:`~wijjit.core.app.Wijjit` (e.g. ``debug=True``).

    Returns
    -------
    Wijjit
        An un-run app with the default view (and any extras) registered.
    """
    app = Wijjit(initial_state=state or {}, **config_overrides)
    captured_context = dict(context or {})

    @app.view(view_name, default=True)
    def _default_view() -> RenderedView:
        return render_template_string(template, **captured_context)

    for action_id, handler in (actions or {}).items():
        app.on_action(action_id)(handler)

    for key, handler in (on_key or {}).items():
        app.on_key(key)(handler)

    for name, spec in (views or {}).items():
        if isinstance(spec, str):
            app.view(name)(lambda source=spec: render_template_string(source))
        elif isinstance(spec, RenderedView):
            app.view(name)(lambda rendered=spec: rendered)
        else:
            app.view(name)(spec)

    return app
