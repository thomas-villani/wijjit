"""Flask-style template rendering helpers for view functions.

This module provides :class:`RenderedView` and the :func:`render_template_string`
/ :func:`render_template` helpers that a view function returns to describe what
to render. They replace the older ``{"template": ..., "data": {...}}`` dict
shape with an explicit, Flask-like call::

    @app.view("main", default=True, on_enter=setup)
    def main_view():
        return render_template_string(
            TEMPLATE,
            greeting=f"Hello, {app.state.name}",
        )

Because a view function is re-invoked on every render (for synchronous views),
the keyword context passed here is recomputed each frame and therefore stays
live - unlike a value baked into a static ``data`` dict, which is frozen at the
first render. See :mod:`wijjit.core.view_router` for the evaluation path and the
legacy-dict compatibility shim.

Classes
-------
RenderedView
    Immutable description of a template (inline string or file) plus its
    rendering context.

Functions
---------
render_template_string
    Build a :class:`RenderedView` from an inline template string.
render_template
    Build a :class:`RenderedView` from a template filename.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RenderedView:
    """Immutable result of a view function describing what to render.

    A view function returns one of these (via :func:`render_template_string` or
    :func:`render_template`) instead of the legacy
    ``{"template": ..., "data": {...}}`` dict. Exactly one of ``template`` or
    ``template_file`` is set.

    Parameters
    ----------
    template : str, optional
        Inline template source. Mutually exclusive with ``template_file``.
    template_file : str, optional
        Template filename to load from the configured template directory.
        Mutually exclusive with ``template``.
    context : dict, optional
        Mapping of names made available to the template. ``state`` is injected
        automatically by the renderer if not present, so templates can always
        use ``{{ state.x }}``.

    Notes
    -----
    Lifecycle hooks (``on_enter`` / ``on_exit``) are not carried here - they are
    declared on the ``@app.view(...)`` decorator, which keeps per-render output
    separate from view lifecycle configuration.
    """

    template: str = ""
    template_file: str = ""
    context: dict[str, Any] = field(default_factory=dict)


def render_template_string(source: str, /, **context: Any) -> RenderedView:
    """Render an inline template string with the given context.

    Parameters
    ----------
    source : str
        The inline Jinja2/Wijjit template source.
    **context
        Names made available to the template (e.g. ``title="Home"``).

    Returns
    -------
    RenderedView
        A description the framework renders. ``state`` is injected
        automatically, so it need not be passed explicitly.

    Examples
    --------
    >>> @app.view("main", default=True)
    ... def main_view():
    ...     return render_template_string(
    ...         "{{ greeting }}",
    ...         greeting=f"Hello, {app.state.name}",
    ...     )
    """
    return RenderedView(template=source, context=dict(context))


def render_template(name: str, /, **context: Any) -> RenderedView:
    """Render a template file with the given context.

    Parameters
    ----------
    name : str
        Template filename to load from the configured template directory
        (``TEMPLATE_DIR`` / the renderer's ``FileSystemLoader``).
    **context
        Names made available to the template.

    Returns
    -------
    RenderedView
        A description the framework renders. ``state`` is injected
        automatically, so it need not be passed explicitly.

    Examples
    --------
    >>> @app.view("dashboard")
    ... def dashboard_view():
    ...     return render_template("dashboard.tui", stats=get_stats())
    """
    return RenderedView(template_file=name, context=dict(context))
