"""Tests for the example loader and the headless example CLI."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from wijjit import Wijjit
from wijjit.testing import ExampleLoadError, discover_examples, load_example_app
from wijjit.testing.cli import main as cli_main

MODULE_LEVEL_EXAMPLE = """\
from wijjit import Wijjit

app = Wijjit(initial_state={"msg": "module-level"})


@app.view("main", default=True)
def main_view():
    return {"template": "{% frame %}{{ state.msg }}{% endframe %}"}


if __name__ == "__main__":
    app.run()
"""

FUNCTION_LOCAL_EXAMPLE = """\
import sys

from wijjit import Wijjit


def main():
    # Branch on argv the way several real demos do; the loader must make this
    # look like a plain `python example.py` invocation (argv length 1).
    if len(sys.argv) >= 2:
        raise SystemExit("should not see extra argv under the loader")
    app = Wijjit(initial_state={"msg": "function-local"})

    @app.view("main", default=True)
    def main_view():
        return {"template": "{% frame %}{{ state.msg }}{% endframe %}"}

    app.run()


if __name__ == "__main__":
    main()
"""

NO_APP_EXAMPLE = """\
print("I build no Wijjit app")
"""


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


def test_loads_module_level_app(tmp_path: Path) -> None:
    app = load_example_app(_write(tmp_path, "mod.py", MODULE_LEVEL_EXAMPLE))
    assert isinstance(app, Wijjit)
    assert app.state["msg"] == "module-level"


def test_loads_function_local_app_via_run_capture(tmp_path: Path) -> None:
    app = load_example_app(_write(tmp_path, "func.py", FUNCTION_LOCAL_EXAMPLE))
    assert isinstance(app, Wijjit)
    assert app.state["msg"] == "function-local"


def test_loader_does_not_actually_run_the_event_loop(tmp_path: Path) -> None:
    app = load_example_app(_write(tmp_path, "mod.py", MODULE_LEVEL_EXAMPLE))
    # run() was captured, not executed: the loop never started.
    assert app.event_loop.running is False


def test_loader_restores_sys_argv(tmp_path: Path) -> None:
    before = list(sys.argv)
    load_example_app(_write(tmp_path, "func.py", FUNCTION_LOCAL_EXAMPLE))
    assert sys.argv == before


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ExampleLoadError, match="not found"):
        load_example_app(tmp_path / "nope.py")


def test_no_app_raises(tmp_path: Path) -> None:
    with pytest.raises(ExampleLoadError, match="No Wijjit app"):
        load_example_app(_write(tmp_path, "empty.py", NO_APP_EXAMPLE))


def test_discover_examples_skips_dunder_and_helpers(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "_helper.py").write_text("", encoding="utf-8")
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.py").write_text("", encoding="utf-8")
    found = {p.name for p in discover_examples(tmp_path)}
    assert found == {"a.py", "b.py"}


def test_cli_renders_example_to_stdout(tmp_path: Path, capsys) -> None:
    example = _write(tmp_path, "mod.py", MODULE_LEVEL_EXAMPLE)
    exit_code = cli_main([str(example), "--size", "40x6"])
    assert exit_code == 0
    assert "module-level" in capsys.readouterr().out


def test_cli_reports_load_failure(tmp_path: Path, capsys) -> None:
    example = _write(tmp_path, "empty.py", NO_APP_EXAMPLE)
    exit_code = cli_main([str(example)])
    assert exit_code == 1
    assert "Failed to load example" in capsys.readouterr().err
