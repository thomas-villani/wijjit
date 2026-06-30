"""Tests for the top-level ``wijjit`` CLI dispatcher."""

import json

from wijjit.cli import main

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
