"""``wijjit new`` must not generate anything broken.

A scaffold is copied, not read critically -- whatever it emits becomes the
starting shape of someone's app, and any mistake in it is inherited by every
user who runs the command. So the generated apps are held to the same bar the
documentation tells users to apply: both layouts are linted with ``wijjit
validate`` and then actually driven through the harness.

That bar earned its keep immediately. The first draft of the single-file layout
had no ``@app.view`` at all -- it validated as "No views registered" -- and the
first draft of the generated test suite was order-dependent, because ``app`` is
a module-level singleton whose state *and focus* survive between tests.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from wijjit.cli import main
from wijjit.devtools.scaffold import (
    LAYOUTS,
    ScaffoldError,
    create,
    to_module_name,
    to_title,
)
from wijjit.testing import WijjitHarness, load_example_app


def app_path(root, layout):
    """Return the generated app entry point for a layout."""
    return root / "tasks.py" if layout == "single" else root / "tasks" / "app.py"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("tasks", "tasks"),
        ("task-list", "task_list"),
        ("My Tasks!", "my_tasks"),
        ("  spaced  out  ", "spaced_out"),
        ("weird---name", "weird_name"),
        ("2048", "app_2048"),  # cannot start with a digit
        ("class", "class_app"),  # cannot shadow a keyword
    ],
)
def test_module_names_are_valid_identifiers(raw, expected):
    assert to_module_name(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("tasks", "Tasks"), ("task-list", "Task List"), ("my_notes", "My Notes")],
)
def test_titles_are_human_readable(raw, expected):
    assert to_title(raw) == expected


@pytest.mark.parametrize("raw", ["", "---", "!!!"])
def test_unusable_names_are_rejected(raw):
    with pytest.raises(ScaffoldError, match="Cannot derive a module name"):
        to_module_name(raw)


def test_unknown_layout_is_rejected(tmp_path):
    with pytest.raises(ScaffoldError, match="Unknown layout"):
        create("tasks", directory=tmp_path, layout="nope")


@pytest.mark.parametrize("layout", LAYOUTS)
def test_generated_app_passes_wijjit_validate(tmp_path, layout):
    """The scaffold must pass the linter it tells the reader to run."""
    create("tasks", directory=tmp_path, layout=layout)
    result = subprocess.run(
        [sys.executable, "-m", "wijjit", "validate", str(app_path(tmp_path, layout))],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("layout", LAYOUTS)
def test_generated_app_runs_and_adds_a_task(tmp_path, layout):
    """Drive the generated app the way its own docstring says to."""
    create("tasks", directory=tmp_path, layout=layout)
    app = load_example_app(str(app_path(tmp_path, layout)))

    with WijjitHarness(app, size=(60, 22)) as harness:
        assert app.focus_element_by_id("entry")
        harness.type("buy milk")
        harness.press("enter")

        harness.assert_text("buy milk")
        harness.assert_text("1 task(s)")
        harness.assert_no_errors()


@pytest.mark.parametrize("layout", LAYOUTS)
def test_generated_frame_is_not_accidentally_scrollable(tmp_path, layout):
    """The starter frame must be tall enough for its own content.

    An undersized frame overflows, becomes scrollable, and -- because
    scrollable containers are focusable -- takes the first Tab stop ahead of
    the input. The generated app would then appear to ignore typing until the
    user pressed Tab twice, which is a miserable first five minutes.
    """
    create("tasks", directory=tmp_path, layout=layout)
    app = load_example_app(str(app_path(tmp_path, layout)))

    with WijjitHarness(app, size=(60, 22)) as harness:
        # A scrollbar is the visible symptom of the overflow.
        assert "█" not in harness.screen()
        # And the input, not the frame, is the first thing Tab reaches.
        harness.press("tab")
        focused = app.focus_manager.get_focused_element()
        assert getattr(focused, "id", None) == "entry"


def test_project_layout_writes_the_expected_files(tmp_path):
    written = create("tasks", directory=tmp_path, layout="project")
    names = {p.relative_to(tmp_path).as_posix() for p in written}
    assert names == {
        "tasks/app.py",
        "tasks/templates/main.wij.j2",
        "tasks/tests/test_app.py",
        "tasks/pyproject.toml",
        "tasks/README.md",
        "tasks/.gitignore",
    }


def test_project_template_is_loaded_from_the_templates_dir(tmp_path):
    """The project layout must exercise render_template, not an inline string."""
    create("tasks", directory=tmp_path, layout="project")
    source = (tmp_path / "tasks" / "app.py").read_text(encoding="utf-8")
    assert "render_template(" in source
    assert "render_template_string" not in source


def test_existing_files_are_not_clobbered(tmp_path):
    create("tasks", directory=tmp_path)
    (tmp_path / "tasks.py").write_text("# my work\n", encoding="utf-8")

    with pytest.raises(ScaffoldError, match="Refusing to overwrite"):
        create("tasks", directory=tmp_path)
    assert (tmp_path / "tasks.py").read_text(encoding="utf-8") == "# my work\n"

    create("tasks", directory=tmp_path, force=True)
    assert "Wijjit" in (tmp_path / "tasks.py").read_text(encoding="utf-8")


def test_partial_collision_writes_nothing(tmp_path):
    """A clash on one file must not leave a half-generated project behind."""
    create("tasks", directory=tmp_path, layout="project")
    (tmp_path / "tasks" / "README.md").unlink()

    with pytest.raises(ScaffoldError, match="Refusing to overwrite"):
        create("tasks", directory=tmp_path, layout="project")
    assert not (tmp_path / "tasks" / "README.md").exists()


def test_generated_test_suite_passes_and_is_order_independent(tmp_path):
    """Run the generated project's own tests, forwards and backwards.

    The scaffolded test file is an artifact users inherit and extend, so it has
    to be exemplary rather than merely present. Reverse order is not paranoia:
    the first draft passed in file order and failed in every other, because
    ``app`` is a module-level singleton whose focus survives between tests and
    the assertions counted Tab presses from an assumed starting point.
    """
    create("tasks", directory=tmp_path, layout="project")
    project = tmp_path / "tasks"
    tests = "tests/test_app.py"
    reverse = [
        f"{tests}::test_c_clears_the_list",
        f"{tests}::test_blank_input_is_rejected",
        f"{tests}::test_adding_a_task_shows_it_in_the_list",
    ]

    for args in ([tests], reverse):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
            cwd=project,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_cli_reports_created_files_and_next_steps(tmp_path, capsys):
    assert main(["new", "tasks", "--directory", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "created tasks.py" in out
    assert "wijjit run tasks.py" in out


def test_cli_reports_a_collision_without_a_traceback(tmp_path, capsys):
    main(["new", "tasks", "--directory", str(tmp_path)])
    assert main(["new", "tasks", "--directory", str(tmp_path)]) == 1
    assert "Refusing to overwrite" in capsys.readouterr().err
