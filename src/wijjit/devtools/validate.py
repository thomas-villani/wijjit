"""Validate a Wijjit template (or example app) and report structured findings.

Today template errors only surface lazily at render time, and only for example
apps. This module lints a *raw template* (or a full ``.py`` app) up front and
returns a structured :class:`ValidationReport` so developers and LLM agents get
actionable, machine-readable diagnostics.

Checks performed (template mode):

* **jinja-syntax** (error) - syntax errors and unknown ``{% tags %}``, caught by
  parsing the source; carries a line number.
* **undefined-variable** (warning) - names used in the template that are not in
  the provided context, found statically via :func:`jinja2.meta`.
* **undefined-attribute** (error) - attribute access on an undefined value,
  surfaced when the template is rendered.
* **unknown-element-type** (error) - a VNode type that is neither a registered
  element nor a known layout container.
* **unknown-attribute** (warning) - an element attribute that the element's
  constructor does not accept (likely a typo); framework/layout props are
  excluded to avoid noise.
* **optional-dependency** (warning) - an element needs an optional extra (e.g.
  Pillow for ImageView) that is not installed.
* **render-error** (error) - any other failure raised while rendering.
* **no-layout-tags** (info) - the template uses no Wijjit layout tags, so it
  renders as plain text with no element tree.

For an app (``.py``), syntax/undefined static checks are skipped (views are
dynamic); instead the app is loaded and its default view rendered, with any
reported error captured as ``render-error`` / ``app-load``.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
from jinja2 import meta as jinja_meta

from wijjit.core.element_registry import ElementRegistry
from wijjit.core.reconciler import KNOWN_CONTAINER_TYPES
from wijjit.core.renderer import Renderer
from wijjit.core.vdom import EPHEMERAL_PROPS
from wijjit.devtools._render import render_with
from wijjit.devtools.tree import walk_vnodes

# Layout container VNode types that the renderer builds directly (and which are
# intentionally absent from ElementRegistry). Reuse the reconciler's canonical
# set so the two never drift.
CONTAINER_TYPES = KNOWN_CONTAINER_TYPES

# Layout/meta props that VNodeBuilder.set_layout copies onto props but element
# constructors generally don't accept - excluded from the unknown-attribute
# check so they don't read as typos.
LAYOUT_META = frozenset(
    {
        "width",
        "height",
        "margin",
        "padding",
        "spacing",
        "align_h",
        "align_v",
        "content_align_h",
        "content_align_v",
    }
)

# Framework props that tags set on many elements but constructors don't take as
# parameters (handled by focus/reconciliation machinery, not __init__).
FRAMEWORK_PROPS = EPHEMERAL_PROPS | {"tab_index"}

# Props never flagged as unknown attributes.
_IGNORED_PROPS = LAYOUT_META | FRAMEWORK_PROPS


@dataclass(frozen=True)
class Finding:
    """A single validation diagnostic.

    Attributes
    ----------
    severity : str
        ``"error"``, ``"warning"`` or ``"info"``.
    code : str
        Stable machine-readable code (e.g. ``"jinja-syntax"``).
    message : str
        Human-readable description.
    line : int or None
        1-based source line, when known.
    col : int or None
        Column, when known.
    """

    severity: str
    code: str
    message: str
    line: int | None = None
    col: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dict for this finding."""
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "col": self.col,
        }


@dataclass
class ValidationReport:
    """The collected findings for one template/app.

    Attributes
    ----------
    path : str
        Source path (or ``"<string>"``).
    findings : list of Finding
        All diagnostics, in detection order.
    rendered : str or None
        Painted screen text, populated when ``render=True``.
    """

    path: str
    findings: list[Finding] = field(default_factory=list)
    rendered: str | None = None

    @property
    def ok(self) -> bool:
        """True if there are no ``error``-severity findings."""
        return not any(f.severity == "error" for f in self.findings)

    def errors(self) -> list[Finding]:
        """Return only the error-severity findings."""
        return [f for f in self.findings if f.severity == "error"]

    def warnings(self) -> list[Finding]:
        """Return only the warning-severity findings."""
        return [f for f in self.findings if f.severity == "warning"]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dict for the whole report."""
        return {
            "path": self.path,
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
            "rendered": self.rendered,
        }

    def format_text(self) -> str:
        """Render the report as human-readable lines.

        Returns
        -------
        str
            One ``path:line: SEVERITY[code] message`` line per finding, plus a
            summary line. Reports ``"OK"`` when clean.
        """
        lines = []
        for f in self.findings:
            loc = f"{self.path}:{f.line}" if f.line is not None else self.path
            lines.append(f"{loc}: {f.severity.upper()}[{f.code}] {f.message}")
        n_err = len(self.errors())
        n_warn = len(self.warnings())
        if not self.findings:
            lines.append(f"{self.path}: OK")
        else:
            lines.append(f"{self.path}: {n_err} error(s), {n_warn} warning(s)")
        return "\n".join(lines)


def _dropped_props(factory: type, prop_names: set[str]) -> set[str]:
    """Return props the factory's ``__init__`` would not accept.

    Mirrors :meth:`ElementRegistry._filter_props_for_factory`: a ``**kwargs``
    parameter accepts everything, otherwise props outside the signature are
    dropped.
    """
    try:
        sig = inspect.signature(factory.__init__)  # type: ignore[misc]
    except (ValueError, TypeError):
        return set()
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return set()
    valid = set(sig.parameters.keys()) - {"self"}
    return prop_names - valid


def _check_tree(root: Any, registry: ElementRegistry) -> list[Finding]:
    """Walk the VNode tree, checking element types and attributes."""
    findings: list[Finding] = []
    for node in walk_vnodes(root):
        is_container = node.type in CONTAINER_TYPES
        if not is_container and not registry.has_type(node.type):
            findings.append(
                Finding(
                    "error",
                    "unknown-element-type",
                    f"Unknown element type {node.type!r}.",
                )
            )
            continue
        if is_container:
            continue
        factory = registry.get_factory(node.type)
        if factory is None:
            continue
        candidate = set(node.props_dict().keys()) - _IGNORED_PROPS
        dropped = _dropped_props(factory, candidate)
        for name in sorted(dropped):
            findings.append(
                Finding(
                    "warning",
                    "unknown-attribute",
                    f"{node.type} does not accept attribute {name!r} "
                    f"(possible typo).",
                )
            )
    return findings


def validate_template(
    source: str,
    *,
    context: dict[str, Any] | None = None,
    width: int = 80,
    height: int = 24,
    path: str = "<string>",
    render: bool = False,
) -> ValidationReport:
    """Validate a template source string.

    Parameters
    ----------
    source : str
        Template source.
    context : dict, optional
        Template variables (used to suppress undefined-variable findings and to
        render).
    width, height : int
        Render size.
    path : str, optional
        Label used in findings.
    render : bool, optional
        When True, populate ``report.rendered`` with the painted screen.

    Returns
    -------
    ValidationReport
        The findings.
    """
    report = ValidationReport(path=path)
    renderer = Renderer()

    # 1. Syntax / unknown tags (also yields the AST for undefined analysis).
    try:
        ast = renderer.env.parse(source)
    except jinja2.TemplateSyntaxError as exc:
        report.findings.append(
            Finding("error", "jinja-syntax", exc.message or str(exc), exc.lineno)
        )
        return report

    # 2. Undefined variables (static).
    declared = jinja_meta.find_undeclared_variables(ast)
    provided = (
        set((context or {}).keys()) | set(renderer.env.globals.keys()) | {"state"}
    )
    for name in sorted(declared - provided):
        report.findings.append(
            Finding(
                "warning",
                "undefined-variable",
                f"Variable {name!r} is used but not provided in context.",
            )
        )

    # 3. Render pass (reuse the same renderer; parse() did not touch its state).
    outcome = render_with(renderer, source, context=context, width=width, height=height)
    if render:
        report.rendered = outcome.rendered

    if outcome.render_error is not None:
        report.findings.append(_classify_render_error(outcome.render_error))
        return report

    # 4. Tree checks (element types + attributes).
    if outcome.root is None:
        report.findings.append(
            Finding(
                "info",
                "no-layout-tags",
                "Template uses no Wijjit layout tags; renders as plain text.",
            )
        )
        return report

    report.findings.extend(_check_tree(outcome.root, renderer._reconciler.registry))
    return report


def _classify_render_error(exc: BaseException) -> Finding:
    """Map a render-time exception to a Finding."""
    if isinstance(exc, jinja2.UndefinedError):
        return Finding("error", "undefined-attribute", str(exc))
    if isinstance(exc, jinja2.TemplateSyntaxError):
        return Finding("error", "jinja-syntax", exc.message or str(exc), exc.lineno)
    if isinstance(exc, ImportError):
        return Finding(
            "warning",
            "optional-dependency",
            f"Optional dependency missing: {exc}",
        )
    return Finding("error", "render-error", f"{type(exc).__name__}: {exc}")


def _validate_app(
    path: Path,
    *,
    width: int = 80,
    height: int = 24,
    render: bool = False,
) -> ValidationReport:
    """Validate an example ``.py`` app by loading and rendering it once."""
    from wijjit.core.element_registry import ElementRegistry as _Registry
    from wijjit.devtools._render import render_app_file
    from wijjit.testing.examples import ExampleLoadError

    report = ValidationReport(path=str(path))
    try:
        outcome = render_app_file(path, width=width, height=height)
    except ExampleLoadError as exc:
        report.findings.append(Finding("error", "app-load", str(exc)))
        return report
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        report.findings.append(_classify_render_error(exc))
        return report

    if render:
        report.rendered = outcome.rendered

    for message, error in outcome.app_errors:
        finding = _classify_render_error(error)
        report.findings.append(
            Finding(finding.severity, finding.code, f"{message}: {finding.message}")
        )

    if outcome.root is not None:
        report.findings.extend(_check_tree(outcome.root, _Registry()))
    return report


def validate_file(
    file: str | Path,
    *,
    context: dict[str, Any] | None = None,
    width: int = 80,
    height: int = 24,
    render: bool = False,
) -> ValidationReport:
    """Validate a template file or example ``.py`` app (auto-detected).

    Parameters
    ----------
    file : str or Path
        A template file or an example ``.py`` app (``.py`` suffix -> app mode).
    context : dict, optional
        Template variables (template mode).
    width, height : int
        Render size.
    render : bool, optional
        Populate ``report.rendered`` with the painted screen.

    Returns
    -------
    ValidationReport
        The findings.
    """
    path = Path(file)
    if path.suffix == ".py":
        return _validate_app(path, width=width, height=height, render=render)
    source = path.read_text(encoding="utf-8")
    return validate_template(
        source,
        context=context,
        width=width,
        height=height,
        path=str(path),
        render=render,
    )
