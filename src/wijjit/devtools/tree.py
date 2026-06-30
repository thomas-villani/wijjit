"""Dump the VNode "DOM" tree a Wijjit template produces.

Wijjit templates compile to a tree of immutable :class:`~wijjit.core.vdom.VNode`
descriptions before they are reconciled into live elements. Seeing that tree is
the fastest way to understand what a template actually builds - which is exactly
what a developer (or an LLM agent) needs when a layout doesn't look right.

This module renders a template (or example app) once and serializes the
resulting VNode tree as either an indented text outline (:func:`render_tree_text`)
or a JSON-friendly nested dict (:func:`vnode_to_dict`).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wijjit.devtools._render import render_app_file, render_template_source

if TYPE_CHECKING:
    from wijjit.core.vdom import VNode


def walk_vnodes(root: VNode | None) -> Iterator[VNode]:
    """Yield every VNode in ``root`` in pre-order (depth-first).

    Parameters
    ----------
    root : VNode or None
        Tree root. ``None`` yields nothing.

    Yields
    ------
    VNode
        Each node, parents before children.
    """
    if root is None:
        return
    yield root
    for child in root.children:
        yield from walk_vnodes(child)


def _render_node(node: VNode, depth: int, lines: list[str]) -> None:
    indent = "  " * depth
    head = f"{indent}{node.type}"
    if node.key is not None:
        head += f" key={node.key!r}"
    props = node.props_dict()
    layout = node.layout_spec_dict()
    parts = [head]
    if props:
        parts.append(f"props={props!r}")
    if layout:
        parts.append(f"layout={layout!r}")
    lines.append(" ".join(parts))
    for child in node.children:
        _render_node(child, depth + 1, lines)


def render_tree_text(root: VNode | None) -> str:
    """Render a VNode tree as an indented text outline.

    Parameters
    ----------
    root : VNode or None
        Tree root.

    Returns
    -------
    str
        One line per node, two spaces of indentation per depth level. Returns
        ``"<no layout tree>"`` when ``root`` is ``None``.
    """
    if root is None:
        return "<no layout tree>"
    lines: list[str] = []
    _render_node(root, 0, lines)
    return "\n".join(lines)


def vnode_to_dict(node: VNode | None) -> dict[str, Any] | None:
    """Convert a VNode tree to a nested JSON-friendly dict.

    Parameters
    ----------
    node : VNode or None
        Tree root.

    Returns
    -------
    dict or None
        ``{"type", "key", "props", "layout_spec", "children"}`` recursively, or
        ``None`` when ``node`` is ``None``. Non-serializable prop values should
        be handled by the JSON encoder (e.g. ``json.dumps(..., default=str)``).
    """
    if node is None:
        return None
    return {
        "type": node.type,
        "key": node.key,
        "props": node.props_dict(),
        "layout_spec": node.layout_spec_dict(),
        "children": [vnode_to_dict(child) for child in node.children],
    }


def build_vnode_tree(
    file: str | Path,
    *,
    context: dict[str, Any] | None = None,
    width: int = 80,
    height: int = 24,
) -> tuple[VNode | None, str]:
    """Render a template file or example app and return its VNode tree.

    Parameters
    ----------
    file : str or Path
        A template file (``.wij`` / ``.html`` / ``.txt`` ...) or an example
        ``.py`` app (auto-detected by the ``.py`` suffix).
    context : dict, optional
        Template variables (template files only).
    width, height : int
        Render size.

    Returns
    -------
    tuple of (VNode or None, str)
        The VNode tree root (``None`` for plain-text templates) and the painted
        screen text.

    Raises
    ------
    BaseException
        Re-raises any error encountered while rendering, so callers can report
        it (the CLI turns it into a readable message).
    """
    path = Path(file)
    if path.suffix == ".py":
        outcome = render_app_file(path, width=width, height=height)
    else:
        source = path.read_text(encoding="utf-8")
        outcome = render_template_source(
            source, context=context, width=width, height=height
        )
    if outcome.render_error is not None:
        raise outcome.render_error
    return outcome.root, outcome.rendered
