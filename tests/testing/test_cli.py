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
