"""Tests for the top-level ``wijjit`` CLI dispatcher."""

import json
from pathlib import Path

from wijjit.cli import main
from wijjit.testing.cli import _tokenize_keys


def test_tokenize_keys_keeps_click_coords_together():
    # The documented ``click:X,Y`` step contains its own comma; the naive
    # ``keys.split(",")`` used to sever the coordinates.
    assert _tokenize_keys("tab,type:admin,click:10,6,tick:3,click:22,11") == [
        "tab",
        "type:admin",
        "click:10,6",
        "tick:3",
        "click:22,11",
    ]


def test_tokenize_keys_click_without_coord_not_greedily_joined():
    # A ``type:`` payload that happens to be digits must not be swallowed onto
    # a preceding complete ``click:X,Y``.
    assert _tokenize_keys("click:1,2,type:9") == ["click:1,2", "type:9"]


GOOD = """
{% frame title="CLI" width=30 height=5 %}
  {% button id="ok" action="go" %}Go{% endbutton %}
{% endframe %}
"""


def test_validate_clean_template_exits_zero(tmp_path, capsys):
    f = tmp_path / "ok.wij"
    f.write_text(GOOD, encoding="utf-8")
    code = main(["validate", str(f)])
    out = capsys.readouterr().out
    assert code == 0
    assert "OK" in out


def test_validate_broken_template_exits_nonzero(tmp_path, capsys):
    f = tmp_path / "bad.wij"
    f.write_text("{% frame %}{% blorp %}{% endframe %}", encoding="utf-8")
    code = main(["validate", str(f)])
    out = capsys.readouterr().out
    assert code == 1
    assert "jinja-syntax" in out


def test_validate_json_output(tmp_path, capsys):
    f = tmp_path / "ok.wij"
    f.write_text(GOOD, encoding="utf-8")
    code = main(["validate", str(f), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["path"].endswith("ok.wij")


def test_tree_json_output(tmp_path, capsys):
    f = tmp_path / "t.wij"
    f.write_text(GOOD, encoding="utf-8")
    code = main(["tree", str(f), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["type"] == "Frame"


def test_tree_text_output(tmp_path, capsys):
    f = tmp_path / "t.wij"
    f.write_text(GOOD, encoding="utf-8")
    code = main(["tree", str(f)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("Frame")
    assert "Button" in out


def test_render_example(capsys):
    code = main(["render", "examples/basic/hello_world.py", "--size", "40x6"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Hello" in out


def test_run_launches_app(monkeypatch):
    # ``wijjit run app.py`` loads the app and calls app.run(); stub run() so the
    # test doesn't block on the event loop / a TTY.
    from wijjit.core.app import Wijjit

    launched = []
    monkeypatch.setattr(Wijjit, "run", lambda self: launched.append(self))
    code = main(["run", "examples/basic/hello_world.py"])
    assert code == 0
    assert len(launched) == 1


def test_run_missing_file_exits_nonzero(capsys):
    code = main(["run", "does/not/exist.py"])
    assert code == 1
    assert "Failed to load" in capsys.readouterr().err


def test_run_executes_script_output_visibly(tmp_path, capsys):
    # ``wijjit run`` used to go through load_example_app, which swallows stdout
    # to keep banner prints out of headless inspection. A script that prints and
    # sleeps then looked like a hang, and one that ran its own blocking loop
    # (an InlineApp) really did hang, during loading.
    script = tmp_path / "plain.py"
    script.write_text("print('ran as', __name__)\n", encoding="utf-8")

    assert main(["run", str(script)]) == 0
    assert "ran as __main__" in capsys.readouterr().out


def test_run_launches_module_level_app_that_never_runs_itself(tmp_path, monkeypatch):
    # Convenience path: a file with no ``if __name__ == "__main__"`` block.
    from wijjit.core.app import Wijjit

    launched = []
    monkeypatch.setattr(Wijjit, "run", lambda self: launched.append(self))

    script = tmp_path / "bare.py"
    script.write_text(
        "from wijjit import Wijjit\napp = Wijjit()\n",
        encoding="utf-8",
    )

    assert main(["run", str(script)]) == 0
    assert len(launched) == 1


def test_run_does_not_double_launch(tmp_path, monkeypatch):
    # A module that runs itself must not be run a second time by the fallback.
    from wijjit.core.app import Wijjit

    launched = []
    monkeypatch.setattr(Wijjit, "run", lambda self: launched.append(self))

    script = tmp_path / "selfrun.py"
    script.write_text(
        "from wijjit import Wijjit\n"
        "app = Wijjit()\n"
        "if __name__ == '__main__':\n"
        "    app.run()\n",
        encoding="utf-8",
    )

    assert main(["run", str(script)]) == 0
    assert len(launched) == 1


def test_run_restores_argv_and_syspath(tmp_path):
    import sys

    script = tmp_path / "probe.py"
    script.write_text("import sys\nassert sys.argv[0].endswith('probe.py')\n", "utf-8")

    before_argv, before_path = list(sys.argv), list(sys.path)
    assert main(["run", str(script)]) == 0
    assert sys.argv == before_argv
    assert sys.path == before_path


def test_validate_missing_file_exits_nonzero(capsys):
    code = main(["validate", "does_not_exist.wij.j2"])
    assert code == 1
    err = capsys.readouterr().err
    assert "Failed to validate" in err
    assert "Traceback" not in err


def test_validate_missing_context_file_exits_nonzero(tmp_path, capsys):
    f = tmp_path / "ok.wij"
    f.write_text("{% frame width=30 height=4 %}hi{% endframe %}", encoding="utf-8")
    code = main(["validate", str(f), "--context", str(tmp_path / "nope.json")])
    assert code == 1
    err = capsys.readouterr().err
    assert "Failed to validate" in err
    assert "Traceback" not in err


def test_render_bad_keys_step_exits_nonzero(capsys):
    code = main(["render", "examples/basic/hello_world.py", "--keys", "bogus_key_xyz"])
    assert code == 1
    err = capsys.readouterr().err
    assert "Bad --keys step" in err
    assert "Traceback" not in err


def test_render_bad_click_coords_exits_nonzero(capsys):
    code = main(["render", "examples/basic/hello_world.py", "--keys", "click:abc,5"])
    assert code == 1
    assert "Bad --keys step" in capsys.readouterr().err


def test_validate_with_context_file(tmp_path, capsys):
    f = tmp_path / "ctx.wij"
    f.write_text(
        "{% frame width=30 height=4 %}{{ greeting }}{% endframe %}", encoding="utf-8"
    )
    ctx = tmp_path / "ctx.json"
    ctx.write_text(json.dumps({"greeting": "hi"}), encoding="utf-8")
    code = main(["validate", str(f), "--context", str(ctx)])
    out = capsys.readouterr().out
    assert code == 0
    assert "undefined-variable" not in out


def test_settle_step_lets_background_work_finish(tmp_path, capsys):
    """``settle:N`` pumps event-loop frames so async tasks can complete.

    ``tick`` only advances animation frames, so an app that streams text from a
    background task was captured mid-update. ``settle`` runs full frames, which
    lets awaited work (including ``asyncio.sleep``) progress.
    """
    app_file = tmp_path / "streaming.py"
    app_file.write_text(
        """
import asyncio

from wijjit import Wijjit, render_template_string

app = Wijjit(initial_state={"text": "start"})


@app.view("main", default=True)
def main_view():
    return render_template_string(
        '{% frame width=30 height=5 %}{% text %}{{ state.text }}'
        '{% endtext %}{% endframe %}'
    )


@app.on_key("g")
def go(event):
    async def stream():
        for word in ("one", "two", "done"):
            await asyncio.sleep(0.01)
            app.state["text"] = word

    asyncio.ensure_future(stream())
""",
        encoding="utf-8",
    )

    assert main(["render", str(app_file), "--size", "40x8", "--keys", "g"]) == 0
    assert "done" not in capsys.readouterr().out

    assert (
        main(["render", str(app_file), "--size", "40x8", "--keys", "g,settle:200"]) == 0
    )
    assert "done" in capsys.readouterr().out


# -- --context diagnostics ---------------------------------------------------


def test_load_context_rejects_inline_json_with_a_useful_message(tmp_path):
    """``--context`` takes a path. Passing the JSON itself is an easy mistake,
    and on Windows it surfaced as ``OSError: [Errno 22] Invalid argument`` -
    which says nothing about filenames."""
    import pytest

    from wijjit.cli import _load_context

    with pytest.raises(ValueError, match="not JSON itself"):
        _load_context(Path('{"rows": [1, 2]}'))


def test_load_context_reports_a_missing_file(tmp_path):
    import pytest

    from wijjit.cli import _load_context

    with pytest.raises(ValueError, match="does not exist"):
        _load_context(tmp_path / "nope.json")


def test_load_context_reports_invalid_json(tmp_path):
    import pytest

    from wijjit.cli import _load_context

    bad = tmp_path / "ctx.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        _load_context(bad)


def test_load_context_reads_a_valid_file(tmp_path):
    from wijjit.cli import _load_context

    good = tmp_path / "ctx.json"
    good.write_text('{"rows": [1, 2]}', encoding="utf-8")
    assert _load_context(good) == {"rows": [1, 2]}


def test_context_is_reported_as_ignored_for_a_py_app(tmp_path, capsys):
    """App mode builds its context from the app's own views and state, so a
    context file has nowhere to go. Silently ignoring it looked like it had
    been applied and its values simply had no effect."""
    import argparse

    from wijjit.cli import _warn_unused_context

    ctx = tmp_path / "ctx.json"
    ctx.write_text("{}", encoding="utf-8")
    _warn_unused_context(argparse.Namespace(file="app.py", context=ctx))
    assert "--context is ignored" in capsys.readouterr().err


def test_context_is_not_reported_as_ignored_for_a_template(tmp_path, capsys):
    import argparse

    from wijjit.cli import _warn_unused_context

    ctx = tmp_path / "ctx.json"
    ctx.write_text("{}", encoding="utf-8")
    _warn_unused_context(argparse.Namespace(file="a.wij.j2", context=ctx))
    assert capsys.readouterr().err == ""
