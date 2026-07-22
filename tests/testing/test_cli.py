"""Tests for the top-level ``wijjit`` CLI dispatcher."""

import json

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
