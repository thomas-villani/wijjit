"""Headless render coverage for the bundled example apps.

Every example under ``examples/`` that is a standard :class:`~wijjit.Wijjit`
application is loaded with :func:`~wijjit.testing.load_example_app` and driven
through :class:`~wijjit.testing.WijjitHarness`. Two layers of checking:

1. ``test_example_loads_and_renders`` - a smoke test asserting each example
   loads and produces a non-blank initial screen. This is the always-green
   regression net that catches import crashes and blank renders.
2. ``test_example_initial_screen_golden`` - a text snapshot of the initial
   screen for a curated, deterministic subset, stored under ``__snapshots__/``
   and regenerated with ``pytest --golden-update``.

Some demos are excluded because they are not driveable by the standard
event-loop harness (the inline subsystem, raw-terminal demos, ``Renderer``
diagnostics, and interactive ``input()`` launchers). Known-broken demos are
marked ``xfail`` and tracked in ``etc/issues.md``; remove the marker once fixed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wijjit.testing import discover_examples, load_example_app
from wijjit.testing.harness import WijjitHarness

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"
SNAPSHOT_DIR = Path(__file__).parent / "__snapshots__"
HARNESS_SIZE = (100, 30)

# Examples that are not driveable by the standard Wijjit event-loop harness.
# Mapped to the reason they are skipped.
EXCLUDED: dict[str, str] = {
    "advanced/scroll_demo.py": "raw ScreenManager demo with a blocking input loop",
    "advanced/template_demo.py": "Renderer diagnostic, builds no Wijjit app",
    "basic/debug_keys.py": "raw blocking keyboard-input loop",
    "basic/inline_demo.py": "inline subsystem (render_inline), builds no app",
    "basic/inline_input_demo.py": "InlineApp interactive demo, blocks on input",
    "basic/inline_progress_demo.py": "InlineApp animation loop, blocks",
    "basic/theme_config_demo.py": "interactive input() launcher, EOFErrors headless",
}

# Known-broken demos (tracked in etc/issues.md). Remove the entry once fixed.
XFAIL: dict[str, str] = {}

# Deterministic, content-stable demos that get a full initial-screen golden.
# (Excludes anything that reads the live filesystem, writes logs, or animates.)
GOLDEN_EXAMPLES: tuple[str, ...] = (
    "basic/hello_world.py",
    "basic/grid_demo.py",
    "advanced/login_form.py",
    "advanced/form_demo.py",
    "widgets/checkbox_demo.py",
    "widgets/radio_demo.py",
    "widgets/select_demo.py",
    "widgets/table_demo.py",
    "widgets/tree_demo.py",
)


def _all_example_ids() -> list[str]:
    """Return every discovered example as a repo-relative POSIX path."""
    return [
        path.relative_to(EXAMPLES_DIR).as_posix()
        for path in discover_examples(EXAMPLES_DIR)
    ]


def _render_initial_screen(rel_path: str, size: tuple[int, int] = HARNESS_SIZE) -> str:
    """Load an example and return its initial rendered screen as plain text."""
    app = load_example_app(EXAMPLES_DIR / rel_path)
    with WijjitHarness(app, size=size) as harness:
        return harness.screen()


def _compare_or_update_text(path: Path, text: str, update: bool) -> None:
    """Compare ``text`` against a golden file, or rewrite it when updating."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.rstrip("\n") + "\n"
    if update:
        # Force LF so snapshots match .gitattributes and stay stable on Windows.
        path.write_text(normalized, encoding="utf-8", newline="\n")
    if not path.exists():
        raise AssertionError(f"Missing golden file: {path} (run --golden-update)")
    expected = path.read_text(encoding="utf-8")
    assert expected.splitlines() == normalized.splitlines()


@pytest.mark.parametrize("rel_path", _all_example_ids())
def test_example_loads_and_renders(rel_path: str) -> None:
    """Every harness-driveable example loads and renders a non-blank screen."""
    if rel_path in EXCLUDED:
        pytest.skip(EXCLUDED[rel_path])
    if rel_path in XFAIL:
        pytest.xfail(XFAIL[rel_path])

    screen = _render_initial_screen(rel_path)
    non_blank = [line for line in screen.splitlines() if line.strip()]
    assert non_blank, f"{rel_path} rendered a blank screen"


@pytest.mark.parametrize("rel_path", GOLDEN_EXAMPLES)
def test_example_initial_screen_golden(rel_path: str, golden_update: bool) -> None:
    """The initial screen of curated demos matches its stored text snapshot."""
    screen = _render_initial_screen(rel_path)
    golden_name = rel_path.replace("/", "__").removesuffix(".py") + ".txt"
    _compare_or_update_text(SNAPSHOT_DIR / golden_name, screen, golden_update)
