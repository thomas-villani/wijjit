"""Developer / LLM-friendly tooling for inspecting and validating templates.

This package provides static-analysis helpers that complement the live
:mod:`wijjit.testing` harness:

* :func:`validate_template` / :func:`validate_file` - lint a template or app and
  return structured :class:`ValidationReport` findings.
* :func:`build_vnode_tree` / :func:`render_tree_text` / :func:`vnode_to_dict` -
  dump the VNode "DOM" a template produces.
* :func:`render_llm_help` - a paste-able Wijjit briefing for LLMs, with the tag
  reference introspected from the live environment.

These power the ``wijjit validate``, ``wijjit tree`` and ``wijjit llm-help``
CLI subcommands.
"""

from __future__ import annotations

from wijjit.devtools.llm_help import build_tag_reference, render_llm_help
from wijjit.devtools.tree import (
    build_vnode_tree,
    render_tree_text,
    vnode_to_dict,
    walk_vnodes,
)
from wijjit.devtools.validate import (
    Finding,
    ValidationReport,
    validate_file,
    validate_template,
)

__all__ = [
    "Finding",
    "ValidationReport",
    "validate_template",
    "validate_file",
    "build_vnode_tree",
    "render_tree_text",
    "vnode_to_dict",
    "walk_vnodes",
    "render_llm_help",
    "build_tag_reference",
]
