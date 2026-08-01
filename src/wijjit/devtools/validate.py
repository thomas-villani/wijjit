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

import ast
import inspect
import re
import textwrap
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import jinja2
from jinja2 import meta as jinja_meta
from jinja2 import nodes

from wijjit.core.element_registry import ElementRegistry
from wijjit.core.reconciler import KNOWN_CONTAINER_TYPES
from wijjit.core.renderer import Renderer
from wijjit.core.vdom import (
    EPHEMERAL_PROPS,
    FRAMEWORK_ONLY_PROPS,
    IMPLICIT_TEXT_ROOT_KEY,
    LAYOUT_META,
)
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
# ``action`` is routed through the event system: input tags always emit it
# (``None`` when unset) and the reconciler applies it by setattr, so it is a
# valid attribute even on elements whose ``__init__`` does not list it.
FRAMEWORK_PROPS = EPHEMERAL_PROPS | FRAMEWORK_ONLY_PROPS | {"tab_index", "action"}

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


@cache
def _instance_attrs(factory: type) -> frozenset[str]:
    """Return the instance attribute names an element class assigns itself.

    A constructor signature is only half of what an element accepts. The
    registry filters *creation* props to the ``__init__`` signature, but the
    reconciler applies *updates* with
    ``if hasattr(element, name): setattr(element, name, value)``
    (:meth:`Reconciler._apply_prop_changes`), so any attribute the element
    carries is a live prop target even when it is not a constructor parameter.
    ``DataGrid`` is the worked example: the tag emits ``width_spec`` /
    ``height_spec``, which the constructor spells ``width`` / ``height`` but
    stores under the ``_spec`` names - so the props really are applied, and
    flagging them as typos was wrong.

    The scan is static (an AST walk of every ``__init__`` in the MRO looking for
    ``self.NAME = ...``), never instantiating the element - constructing one
    here could import an optional dependency or do real work.

    Parameters
    ----------
    factory : type
        Element class to inspect.

    Returns
    -------
    frozenset of str
        Attribute names reachable by ``setattr`` on an instance: everything on
        the class (methods, properties, class attributes) plus every
        ``self.NAME`` assigned in an ``__init__`` along the MRO.
    """
    names: set[str] = set(dir(factory))
    for klass in factory.__mro__:
        init = klass.__dict__.get("__init__")
        if init is None:
            continue
        try:
            source = textwrap.dedent(inspect.getsource(init))
            tree = ast.parse(source)
        except (OSError, TypeError, SyntaxError, IndentationError):
            continue
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    names.add(target.attr)
    return frozenset(names)


def _dropped_props(factory: type, prop_names: set[str]) -> set[str]:
    """Return props the element would neither accept nor carry.

    Mirrors :meth:`ElementRegistry._filter_props_for_factory`: a ``**kwargs``
    parameter accepts everything, otherwise props outside the signature are
    dropped at construction. Props that name an attribute the element carries
    are still applied on update by the reconciler, so they are not reported -
    see :func:`_instance_attrs`.
    """
    try:
        sig = inspect.signature(factory.__init__)  # type: ignore[misc]
    except (ValueError, TypeError):
        return set()
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return set()
    valid = (set(sig.parameters.keys()) - {"self"}) | _instance_attrs(factory)
    return prop_names - valid


@cache
def _tag_vnode_types() -> dict[str, frozenset[str]]:
    """Map each template tag to the VNode types its render method builds.

    Recovered statically: every VNode-building tag's ``_render_<tag>`` contains
    a literal ``VNodeBuilder("<Type>", ...)`` call, so the mapping can be read
    out of the AST without rendering anything. Tags that build no VNode at all
    (the dialog and menu tags, which populate ``overlay_info`` instead) map to
    an empty set.

    Returns
    -------
    dict
        Tag name -> frozenset of VNode type names it can build.
    """
    from wijjit.core.renderer import Renderer

    env = Renderer().env
    mapping: dict[str, frozenset[str]] = {}
    for extension in env.extensions.values():
        for tag in getattr(extension, "tags", set()):
            handler = getattr(extension, f"_render_{tag}", None)
            if handler is None:
                continue
            try:
                tree = ast.parse(textwrap.dedent(inspect.getsource(handler)))
            except (OSError, TypeError, SyntaxError, IndentationError):
                continue
            built: set[str] = set()
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "VNodeBuilder"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    built.add(str(node.args[0].value))
            mapping[str(tag)] = frozenset(built)
    return mapping


@cache
def _tag_element_types() -> dict[str, str]:
    """Map each template tag to the single element type it builds.

    Only *unambiguous* tags are included. Container tags build more than one
    kind of node (``{% frame %}`` yields a ``Frame`` plus a ``TextElement`` for
    its body text, ``{% radiogroup %}`` yields three), and there is no sound way
    to decide which one an attribute belongs to, so they are left out and their
    findings simply carry no line number - the status quo.

    Returns
    -------
    dict
        Tag name -> element type name, for tags that build exactly one
        registered element type.
    """
    registry = ElementRegistry()
    mapping: dict[str, str] = {}
    for tag, built in _tag_vnode_types().items():
        registered = {t for t in built if registry.has_type(t)}
        if len(registered) == 1:
            mapping[tag] = registered.pop()
    return mapping


def _root_element_linenos(node: nodes.Node) -> list[int]:
    """Return the source lines of the element tags at a template's top level.

    A template has room for exactly one root: the renderer wraps the first
    top-level element in an implicit root frame, and
    :meth:`RenderContext.add_vnode` drops any later one on the floor - with no
    warning, because at that point there is no container to add it to. So
    ``{% textinput id="a" %}{% textinput id="b" %}`` renders only ``a``.

    Branches of an ``{% if %}`` are alternatives rather than siblings, so the
    larger branch is taken rather than their sum. A ``{% for %}`` at the top
    level *is* a defect whenever its body yields an element, since every
    iteration after the first is dropped - it is reported as two roots so the
    caller's "more than one" test catches it.

    Parameters
    ----------
    node : jinja2.nodes.Node
        Node to inspect; call with the template root.

    Returns
    -------
    list of int
        One line number per top-level root, in source order.
    """
    vnode_tags = _tag_vnode_types()

    if isinstance(node, nodes.CallBlock):
        method = getattr(getattr(node.call, "node", None), "name", None)
        if isinstance(method, str) and method.startswith("_render_"):
            # A tag that builds no VNode (dialogs, menu items) never becomes a
            # root; anything else takes the single root slot, and its own body
            # is nested rather than top-level, so do not descend.
            if vnode_tags.get(method[len("_render_") :]):
                return [node.lineno]
            return []

    if isinstance(node, nodes.If):
        taken: list[int] = []
        for branch in (node.body, node.elif_, node.else_):
            lines: list[int] = []
            for child in branch:
                lines.extend(_root_element_linenos(child))
            if len(lines) > len(taken):
                taken = lines
        return taken

    if isinstance(node, nodes.For):
        lines = []
        for child in node.body:
            lines.extend(_root_element_linenos(child))
        # One element per iteration: all but the first are dropped.
        return lines * 2 if lines else []

    lines = []
    for child in node.iter_child_nodes():
        lines.extend(_root_element_linenos(child))
    return lines


def _attribute_linenos(template_ast: nodes.Template) -> dict[tuple[str, str], int]:
    """Locate each element attribute's source line in the template AST.

    The VNode tree has no source positions - by render time a ``{% for %}`` has
    been unrolled and the templates' line structure is gone - which is why
    ``unknown-attribute`` findings historically printed without a line. The
    attributes are still literal keyword arguments in the AST, so their lines
    can be recovered there and matched back to the findings by
    (element type, attribute name).

    Parameters
    ----------
    template_ast : jinja2.nodes.Template
        Parsed template AST.

    Returns
    -------
    dict
        ``(element_type, attribute_name)`` -> 1-based line. First occurrence
        wins, so a repeated typo points at the one the author should fix first.
    """
    tag_types = _tag_element_types()
    linenos: dict[tuple[str, str], int] = {}
    for node in template_ast.find_all(nodes.CallBlock):
        method = getattr(getattr(node.call, "node", None), "name", None)
        if not isinstance(method, str) or not method.startswith("_render_"):
            continue
        element_type = tag_types.get(method[len("_render_") :])
        if element_type is None:
            continue
        for keyword in node.call.kwargs:
            linenos.setdefault((element_type, keyword.key), keyword.lineno)
    return linenos


def _check_tree(
    root: Any,
    registry: ElementRegistry,
    linenos: dict[tuple[str, str], int] | None = None,
) -> list[Finding]:
    """Walk the VNode tree, checking element types and attributes.

    Parameters
    ----------
    root : VNode
        Root of the rendered VNode tree.
    registry : ElementRegistry
        Registry used to resolve element types to factories.
    linenos : dict, optional
        ``(element_type, attribute)`` -> source line, from
        :func:`_attribute_linenos`. Absent in app mode, where there is no single
        template source to point into.
    """
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
                    (linenos or {}).get((node.type, name)),
                )
            )
    return findings


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Collapse identical findings, preserving first-seen order.

    The tree checks run per VNode, and a ``{% for %}`` is fully unrolled by the
    time they see it - so one bad attribute on a tag inside a loop over N items
    used to be reported N times. The loop is a template-authoring detail; the
    defect is one edit in one place, so it should be one finding.

    Parameters
    ----------
    findings : list of Finding
        Findings in detection order.

    Returns
    -------
    list of Finding
        The same list with exact duplicates removed.
    """
    seen: set[tuple[str, str, str, int | None, int | None]] = set()
    unique: list[Finding] = []
    for finding in findings:
        identity = (
            finding.severity,
            finding.code,
            finding.message,
            finding.line,
            finding.col,
        )
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(finding)
    return unique


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

    # 2c. Multiple top-level roots. Only the first survives; the rest are
    # dropped silently, so this must be caught statically - by render time the
    # extras simply are not in the tree to notice.
    root_lines = _root_element_linenos(ast)
    if len(root_lines) > 1:
        report.findings.append(
            Finding(
                "warning",
                "multiple-root-elements",
                f"Template has {len(root_lines)} top-level elements; only the "
                f"first is rendered and the rest are dropped silently. Wrap "
                f"them in a {{% vstack %}} or {{% frame %}}.",
                root_lines[1],
            )
        )

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
                report.findings = _dedupe(report.findings)
                return report
        else:
            if render:
                report.rendered = outcome.rendered
            report.findings = _dedupe(report.findings)
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
        report.findings = _dedupe(report.findings)
        return report

    report.findings.extend(
        _check_tree(
            outcome.root,
            renderer._reconciler.registry,
            _attribute_linenos(ast),
        )
    )
    report.findings = _dedupe(report.findings)
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
    report.findings = _dedupe(report.findings)
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
