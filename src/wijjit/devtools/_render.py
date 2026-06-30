"""Shared rendering mechanics for the devtools (validate / tree).

Both the validator and the tree dumper need the same thing: take a template
source (or an example ``.py`` app), render it once, and recover the resulting
VNode tree plus the painted screen. This module owns that single code path so
the two tools stay consistent.

Two render modes:

* **Template source** - a fresh :class:`~wijjit.core.renderer.Renderer` is built
  per call so the reconciler's ``_last_vnode_tree`` starts ``None`` and the very
  first render creates every element cleanly (no diffing against stale state).
* **App file** - the example is loaded with
  :func:`~wijjit.testing.examples.load_example_app` and driven once through
  :class:`~wijjit.testing.harness.WijjitHarness`, which renders the default view
  and captures any errors the app reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wijjit.core.renderer import Renderer
from wijjit.core.state import State

if TYPE_CHECKING:
    from wijjit.core.vdom import VNode


@dataclass
class RenderOutcome:
    """Result of rendering a template or app for inspection / validation.

    Attributes
    ----------
    root : VNode or None
        Root of the frozen VNode tree, or ``None`` for a plain-text
        (non-layout) template that produced no element tree.
    rendered : str
        The painted screen as plain text.
    render_error : BaseException or None
        Exception raised during the render pass, if any (template mode).
    app_errors : list of (str, BaseException)
        Errors the app reported via ``_handle_error`` (app mode).
    renderer : Renderer or None
        The renderer used (template mode), exposed so callers can reuse its
        Jinja environment for static analysis.
    """

    root: VNode | None
    rendered: str
    render_error: BaseException | None = None
    app_errors: list[tuple[str, BaseException]] = field(default_factory=list)
    renderer: Renderer | None = None


def make_data(context: dict[str, Any] | None) -> dict[str, Any]:
    """Build a render context with ``state`` injected, mirroring the app.

    Parameters
    ----------
    context : dict or None
        Caller-supplied template variables.

    Returns
    -------
    dict
        A copy of ``context`` with a ``state`` entry (a :class:`State` wrapping
        any provided ``state`` mapping) so templates can use ``{{ state.x }}``.
    """
    data = dict(context or {})
    raw_state = data.get("state", {})
    if not isinstance(raw_state, State):
        data["state"] = State(raw_state if isinstance(raw_state, dict) else {})
    return data


def render_with(
    renderer: Renderer,
    source: str,
    *,
    context: dict[str, Any] | None = None,
    width: int = 80,
    height: int = 24,
) -> RenderOutcome:
    """Render ``source`` through ``renderer``, capturing any failure.

    Parameters
    ----------
    renderer : Renderer
        A (typically fresh) renderer to drive.
    source : str
        Template source.
    context : dict, optional
        Template variables.
    width, height : int
        Render size.

    Returns
    -------
    RenderOutcome
        Outcome with ``root``/``rendered`` set on success or ``render_error``
        set on failure.
    """
    data = make_data(context)
    try:
        rendered, _elements, layout_ctx = renderer.render_with_layout(
            template_string=source,
            context=data,
            width=width,
            height=height,
        )
        return RenderOutcome(
            root=layout_ctx.freeze_vnode_tree(),
            rendered=rendered,
            renderer=renderer,
        )
    except Exception as exc:  # noqa: BLE001 - tool must report, not crash
        return RenderOutcome(
            root=None, rendered="", render_error=exc, renderer=renderer
        )


def render_template_source(
    source: str,
    *,
    context: dict[str, Any] | None = None,
    width: int = 80,
    height: int = 24,
) -> RenderOutcome:
    """Render a template string with a fresh renderer.

    Parameters
    ----------
    source : str
        Template source.
    context : dict, optional
        Template variables.
    width, height : int
        Render size.

    Returns
    -------
    RenderOutcome
        The render outcome.
    """
    return render_with(Renderer(), source, context=context, width=width, height=height)


def render_app_file(
    path: str | Path,
    *,
    width: int = 80,
    height: int = 24,
) -> RenderOutcome:
    """Load and render an example ``.py`` app once through the harness.

    Parameters
    ----------
    path : str or Path
        Path to the example module.
    width, height : int
        Terminal size to render at.

    Returns
    -------
    RenderOutcome
        Outcome with the app's VNode tree, painted screen, and any captured
        app errors.

    Raises
    ------
    wijjit.testing.examples.ExampleLoadError
        If the example cannot be loaded (callers handle this).
    """
    from wijjit.testing.examples import load_example_app
    from wijjit.testing.harness import WijjitHarness

    app = load_example_app(path)
    with WijjitHarness(app, size=(width, height)) as harness:
        return RenderOutcome(
            root=harness.tree(),
            rendered=harness.screen(),
            app_errors=harness.errors,
        )
