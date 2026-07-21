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
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
from jinja2 import meta as jinja_meta
from jinja2 import nodes

from wijjit.core.element_registry import ElementRegistry
from wijjit.core.reconciler import KNOWN_CONTAINER_TYPES
from wijjit.core.renderer import Renderer
from wijjit.core.vdom import EPHEMERAL_PROPS, IMPLICIT_TEXT_ROOT_KEY, LAYOUT_META
from wijjit.devtools._render import render_with
from wijjit.devtools.tree import walk_vnodes

# Layout container VNode types that the renderer builds directly (and which are
# intentionally absent from ElementRegistry). Reuse the reconciler's canonical
# set so the two never drift.
CONTAINER_TYPES = KNOWN_CONTAINER_TYPES

# ``LAYOUT_META`` (layout/meta props that VNodeBuilder.set_layout copies onto
# props but element constructors generally don't accept) lives in
# :mod:`wijjit.core.vdom` so the tag layer and this validator share one
# definition. It is excluded from the unknown-attribute check so it doesn't
# read as typos.

# Framework props that tags set on many elements but constructors don't take as
# parameters (handled by focus/reconciliation machinery, not __init__).
FRAMEWORK_PROPS = EPHEMERAL_PROPS | {"tab_index"}

# Props never flagged as unknown attributes.
_IGNORED_PROPS = LAYOUT_META | FRAMEWORK_PROPS

# A ``jinja2.UndefinedError`` for a bare undefined *name* (as opposed to
# attribute/item access on an undefined value) has a message of the form
# ``'foo' is undefined``. Matching it lets the render-time classifier report an
# ``undefined-variable`` (mirroring the static check) rather than an
# ``undefined-attribute``, and lets ``validate_template`` dedupe against the
# names the static check already reported.
_UNDEFINED_VAR_RE = re.compile(r"'(\w+)' is undefined")

# Element tag render-methods whose instances carry state that survives
# reconciliation - a bound value, a cursor/selection, a scroll offset, an
# expanded/active subset. When one of these appears inside a ``{% for %}`` with
# neither ``key`` nor ``id``, its reconciliation identity is purely positional,
# so inserting or reordering rows silently migrates that state to the wrong row
# (see the ``key=`` attribute and :func:`wijjit.tags.layout.auto_element_id`).
# Stateless elements (charts, text, spinner, progressbar, status) are omitted:
# they are fully repainted from props each render, so positional reuse is
# invisible and needs no key.
_STATEFUL_LOOP_METHODS = frozenset(
    {
        "_render_textinput",
        "_render_textarea",
        "_render_codeeditor",
        "_render_select",
        "_render_checkbox",
        "_render_checkboxgroup",
        "_render_radio",
        "_render_radiogroup",
        "_render_slider",
        "_render_toggle",
        "_render_datagrid",
        "_render_table",
        "_render_tree",
        "_render_listview",
        "_render_logview",
        "_render_tabbedpanel",
        "_render_contentview",
        "_render_pager",
    }
)


def _check_unkeyed_loop_elements(ast: nodes.Template) -> list[Finding]:
    """Flag stateful element tags inside a ``{% for %}`` that lack ``key``/``id``.

    This is a *static* check: by render time the loop has been unrolled and the
    VNode tree carries auto-generated positional keys, so the "was this in a
    loop and unkeyed?" signal only exists in the template AST. Each element tag
    compiles to a :class:`jinja2.nodes.CallBlock` whose call targets a
    ``_render_<tag>`` extension method with the tag's attributes as keyword
    arguments; walking the AST lets us see the loop nesting and the literal
    ``key``/``id`` attributes before either is lost.

    Parameters
    ----------
    ast : jinja2.nodes.Template
        Parsed template AST.

    Returns
    -------
    list of Finding
        One ``unkeyed-loop-element`` warning per offending tag.
    """
    findings: list[Finding] = []

    def visit(node: nodes.Node, in_loop: bool) -> None:
        if in_loop and isinstance(node, nodes.CallBlock):
            method = getattr(getattr(node.call, "node", None), "name", None)
            if method in _STATEFUL_LOOP_METHODS:
                attrs = {kw.key for kw in node.call.kwargs}
                if "key" not in attrs and "id" not in attrs:
                    tag = method[len("_render_") :]
                    findings.append(
                        Finding(
                            "warning",
                            "unkeyed-loop-element",
                            f"<{tag}> inside a loop has no 'key' or 'id'. Its "
                            f"identity is positional, so inserting or reordering "
                            f"rows silently migrates its state (typed value, "
                            f"selection, scroll) to the wrong row. Add "
                            f"key=<stable-id> (e.g. key=item.id).",
                            node.lineno,
                        )
                    )
        child_in_loop = in_loop or isinstance(node, nodes.For)
        for child in node.iter_child_nodes():
            visit(child, child_in_loop)

    visit(ast, False)
    return findings


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
    # Strict undefined so a typo'd template name (``{{ nope }}``) is surfaced
    # rather than silently rendered as an empty string.
    renderer = Renderer(strict_undefined=True)

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
    static_undefined_names: set[str] = set()
    for name in sorted(declared - provided):
        static_undefined_names.add(name)
        report.findings.append(
            Finding(
                "warning",
                "undefined-variable",
                f"Variable {name!r} is used but not provided in context.",
            )
        )

    # 2b. Unkeyed stateful elements inside loops (static AST check - the loop
    # structure is gone by render time).
    report.findings.extend(_check_unkeyed_loop_elements(ast))

    # 3. Render pass (reuse the same renderer; parse() did not touch its state).
    outcome = render_with(renderer, source, context=context, width=width, height=height)

    if outcome.render_error is not None:
        finding = _classify_render_error(outcome.render_error)
        # Dedupe: the static find_undeclared_variables check above already
        # reported bare undefined names as warnings. When the strict render fails
        # on the same name, don't add a duplicate render-time finding.
        already_reported = False
        if finding.code == "undefined-variable":
            match = _UNDEFINED_VAR_RE.search(finding.message)
            already_reported = (
                match is not None and match.group(1) in static_undefined_names
            )
        if not already_reported:
            report.findings.append(finding)

        # Preserve tree checks. The strict renderer raises on the first undefined
        # name, which would otherwise strand the unknown-attribute / element-type
        # findings for the rest of the template. Re-render once leniently (fresh
        # Renderer, same source/context) and, if that succeeds, continue with the
        # tree checks on the lenient outcome. If the lenient render also fails,
        # stop here (as before).
        if isinstance(outcome.render_error, jinja2.UndefinedError):
            outcome = render_with(
                Renderer(), source, context=context, width=width, height=height
            )
            if outcome.render_error is not None:
                if render:
                    report.rendered = outcome.rendered
                return report
        else:
            if render:
                report.rendered = outcome.rendered
            return report

    if render:
        report.rendered = outcome.rendered

    # 4. Tree checks (element types + attributes).
    # A template with no Wijjit tags either renders nothing (root is None) or is
    # bare top-level text that the renderer wraps in an implicit Text element.
    # Both mean "no explicit layout tags" - report it as info either way.
    if outcome.root is None or outcome.root.key == IMPLICIT_TEXT_ROOT_KEY:
        report.findings.append(
            Finding(
                "info",
                "no-layout-tags",
                "Template uses no Wijjit layout tags; its bare text renders in "
                "an implicit text element.",
            )
        )
        return report

    report.findings.extend(_check_tree(outcome.root, renderer._reconciler.registry))
    return report


def _classify_render_error(exc: BaseException) -> Finding:
    """Map a render-time exception to a Finding.

    A :class:`jinja2.UndefinedError` is split into two codes: a bare undefined
    *name* (message ``'foo' is undefined``, i.e. a likely typo of a context
    variable) is reported as ``undefined-variable``, mirroring the static check;
    anything else (attribute/item access on an undefined value) keeps the
    ``undefined-attribute`` classification.
    """
    if isinstance(exc, jinja2.UndefinedError):
        message = str(exc)
        if _UNDEFINED_VAR_RE.search(message):
            return Finding("error", "undefined-variable", message)
        return Finding("error", "undefined-attribute", message)
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
