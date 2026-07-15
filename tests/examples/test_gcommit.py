"""Tests for the gcommit example's pure helpers and template.

The interactive InlineApp loop is not driven here (it blocks on real input and
is excluded from the render harness); these tests cover the parsing, command
building, and template rendering that the app is built on.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from wijjit.devtools._render import render_template_source

_GCOMMIT_PATH = Path(__file__).resolve().parents[2] / "examples" / "apps" / "gcommit.py"


@pytest.fixture(scope="module")
def gcommit() -> ModuleType:
    """Import gcommit.py as a module (it defines no top-level app to load)."""
    spec = importlib.util.spec_from_file_location("gcommit_example", _GCOMMIT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so the @dataclass can resolve its own module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SAMPLE_STATUS = (
    " M src/foo.py\n"  # unstaged modification
    "M  src/bar.py\n"  # staged modification
    "A  new file.py\n"  # staged add, path with a space
    "?? untracked.txt\n"  # untracked
    "R  old.py -> src/new.py\n"  # staged rename
)


def test_parse_status_marks_staged_entries(gcommit: ModuleType) -> None:
    """Only entries with a non-space index column count as staged."""
    changes = gcommit.parse_status(SAMPLE_STATUS)
    by_path = {change.path: change for change in changes}

    assert by_path["src/foo.py"].staged is False
    assert by_path["src/bar.py"].staged is True
    assert by_path["new file.py"].staged is True
    assert by_path["untracked.txt"].staged is False
    # Renames resolve to the new path and are staged.
    assert "src/new.py" in by_path
    assert by_path["src/new.py"].staged is True


def test_parse_status_ignores_blank_lines(gcommit: ModuleType) -> None:
    """Empty output yields no changes."""
    assert gcommit.parse_status("") == []


def test_build_commit_commands_limits_pathspec(gcommit: ModuleType) -> None:
    """Both add and commit are limited to the selected paths."""
    paths = ["src/bar.py", "new file.py"]
    add_cmd, commit_cmd = gcommit.build_commit_commands(paths, "fix: stuff")

    assert add_cmd == ["git", "add", "--", *paths]
    assert commit_cmd == ["git", "commit", "-m", "fix: stuff", "--", *paths]


def test_template_renders_without_error(gcommit: ModuleType) -> None:
    """The inline template renders the change list and message box."""
    changes = gcommit.parse_status(SAMPLE_STATUS)
    state: dict[str, object] = {
        "header": "gcommit - main",
        "changes": changes,
        "message": "",
    }
    for index, change in enumerate(changes):
        state[f"file_{index}"] = change.staged

    outcome = render_template_source(
        gcommit.TEMPLATE, context={"state": state}, width=72, height=24
    )

    assert outcome.render_error is None
    assert "src/bar.py" in outcome.rendered
    assert "Commit message:" in outcome.rendered
