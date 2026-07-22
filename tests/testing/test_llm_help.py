"""``wijjit llm-help`` must not teach anything false.

This document exists to stop an LLM inventing tags and attributes, so it is
worth more than most docs that it stay true. Two things are checked here: the
generated tag reference really reflects the registered tags, and the example app
in the prose actually validates and runs. The first draft of that example bound
``ctrl+q``, which raises ``KeyBindingError`` -- caught by this test's ancestor,
which is why it exists.
"""

import re
import subprocess
import sys

import pytest

from wijjit.cli import main
from wijjit.devtools import build_tag_reference, render_llm_help
from wijjit.testing import WijjitHarness, load_example_app


def python_blocks(doc: str) -> list[str]:
    """Extract fenced python blocks from the briefing."""
    return re.findall(r"```python\n(.*?)```", doc, re.S)


def test_tag_reference_matches_the_registered_tags():
    from wijjit.core.renderer import Renderer

    registered = set()
    for extension in Renderer().env.extensions.values():
        registered.update(str(t) for t in getattr(extension, "tags", set()))

    reference = build_tag_reference()
    listed = set(re.findall(r"`\{% (\w+) %\}`", reference))
    # Every registered tag is documented, and nothing invented is listed.
    assert registered == listed


def test_tag_attributes_are_real_signature_parameters():
    # Spot-check a tag whose attributes changed recently: the mode-based charts
    # use color_mode, and the abbreviated grid gap is gone.
    reference = build_tag_reference()
    barchart = next(
        line for line in reference.splitlines() if line.startswith("- `{% barchart %}`")
    )
    assert "color_mode" in barchart
    assert "color_scale" in barchart

    grid = next(
        line for line in reference.splitlines() if line.startswith("- `{% grid %}`")
    )
    assert "column_gap" in grid
    assert "col_gap," not in grid


def test_briefing_is_self_contained_markdown():
    doc = render_llm_help()
    assert doc.startswith("# Wijjit for LLMs")
    # The version is interpolated, not left as a placeholder.
    assert "__WIJJIT_VERSION__" not in doc
    assert "{version}" not in doc
    for heading in ("## A complete app", "## Common mistakes", "## Tag reference"):
        assert heading in doc


def test_example_app_validates_and_runs(tmp_path):
    """The app in the briefing must pass the linter it tells the reader to run."""
    code = python_blocks(render_llm_help())[0]
    app_file = tmp_path / "guide_app.py"
    app_file.write_text(code, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "wijjit", "validate", str(app_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    app = load_example_app(str(app_file))
    with WijjitHarness(app, size=(60, 12)) as harness:
        harness.press("tab")
        harness.type("alice")
        harness.press("enter")
        harness.assert_text("Hello, alice!")
        harness.assert_no_errors()


@pytest.mark.parametrize("args", [["llm-help"], ["llm-help", "--tags-only"]])
def test_cli_prints_and_exits_zero(args, capsys):
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "{% vstack %}" in out
