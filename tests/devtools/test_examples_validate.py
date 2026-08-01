"""Ratchet: every bundled example must pass its own linter cleanly.

Wijjit leads with ``wijjit validate``, so the bundled demos failing it is a
credibility problem before it is a correctness one - a user who copies a demo
inherits its warnings, and a user who writes a correct template gets a warning
they can neither silence nor act on.

This is the check that was missing when the ``codeeditor`` / ``datagrid`` false
positives shipped (issue #59): both demos had been warning since the linter
existed, and nothing was watching.

Examples that cannot be loaded headlessly are skipped through the same
``EXCLUDED`` map ``test_examples_render`` uses - importing it rather than
copying it, so a demo can never be exempt here but not there.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tests.examples.test_examples_render import EXCLUDED, OPTIONAL_DEPS
from wijjit.devtools import validate_file

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"

# Demos whose warnings describe a real, tracked framework gap rather than a
# defect in the demo. Each entry names the finding code and the backlog item, so
# the exemption cannot quietly outlive the bug it stands for.
_TREE_EXPANDED = (
    "unknown-attribute",
    "TreeView has no 'expanded' constructor parameter, so the tag's documented "
    "expanded=<state-key> binding is dropped at element creation. Tracked as "
    "roadmap.md Group E (Tree expand/collapse), which needs a reconciler design "
    "pass - the linter is right to flag it.",
)

KNOWN_FINDINGS: dict[str, tuple[str, str]] = {
    "advanced/filesystem_browser.py": _TREE_EXPANDED,
    "widgets/tree_demo.py": _TREE_EXPANDED,
}


def _all_example_ids() -> list[str]:
    """Return every example as a repo-relative POSIX path."""
    return sorted(
        path.relative_to(EXAMPLES_DIR).as_posix()
        for path in EXAMPLES_DIR.rglob("*.py")
        if path.name != "__init__.py"
    )


@pytest.mark.parametrize("rel_path", _all_example_ids())
def test_example_validates_clean(rel_path: str) -> None:
    """Each bundled example lints with no errors and no unexpected warnings."""
    if rel_path in EXCLUDED:
        pytest.skip(EXCLUDED[rel_path])
    dep = OPTIONAL_DEPS.get(rel_path)
    if dep is not None and importlib.util.find_spec(dep) is None:
        pytest.skip(f"optional dependency {dep!r} not installed")

    report = validate_file(EXAMPLES_DIR / rel_path)

    assert (
        report.errors() == []
    ), f"{rel_path} has validation errors:\n{report.format_text()}"

    known = KNOWN_FINDINGS.get(rel_path)
    unexpected = [
        finding
        for finding in report.warnings()
        if known is None or finding.code != known[0]
    ]
    assert (
        not unexpected
    ), f"{rel_path} has unexpected validation warnings:\n{report.format_text()}"


def test_known_findings_still_reproduce() -> None:
    """A tracked exemption that has been fixed must be removed, not left behind.

    Without this, ``KNOWN_FINDINGS`` would silently turn into a permanent
    allowlist - the exact failure mode the ratchet exists to prevent.
    """
    for rel_path, (code, reason) in KNOWN_FINDINGS.items():
        report = validate_file(EXAMPLES_DIR / rel_path)
        codes = {finding.code for finding in report.warnings()}
        assert code in codes, (
            f"{rel_path} no longer reports {code!r} - delete its KNOWN_FINDINGS "
            f"entry. Recorded reason: {reason}"
        )
