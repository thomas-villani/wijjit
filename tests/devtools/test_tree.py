"""Tests for wijjit.devtools.tree."""

from pathlib import Path

from wijjit.devtools import (
    build_vnode_tree,
    render_tree_text,
    vnode_to_dict,
    walk_vnodes,
)

TEMPLATE = """
{% frame width=40 height=6 %}
  {% vstack %}
    {% button id="ok" action="go" %}Go{% endbutton %}
  {% endvstack %}
{% endframe %}
"""


def test_build_tree_returns_root_and_rendered(tmp_path: Path):
    f = tmp_path / "t.wij"
    f.write_text(TEMPLATE, encoding="utf-8")
    root, rendered = build_vnode_tree(f)
    assert root is not None
    assert root.type == "Frame"
    assert "Go" in rendered


def test_tree_structure_and_walk(tmp_path: Path):
    f = tmp_path / "t.wij"
    f.write_text(TEMPLATE, encoding="utf-8")
    root, _ = build_vnode_tree(f)
    types = [n.type for n in walk_vnodes(root)]
    assert types == ["Frame", "VStack", "Button"]


def test_render_tree_text_is_indented(tmp_path: Path):
    f = tmp_path / "t.wij"
    f.write_text(TEMPLATE, encoding="utf-8")
    root, _ = build_vnode_tree(f)
    text = render_tree_text(root)
    lines = text.split("\n")
    assert lines[0].startswith("Frame")
    assert lines[1].startswith("  VStack")
    assert lines[2].startswith("    Button")
    assert "key='ok'" in lines[2]


def test_vnode_to_dict_round_trips_structure(tmp_path: Path):
    f = tmp_path / "t.wij"
    f.write_text(TEMPLATE, encoding="utf-8")
    root, _ = build_vnode_tree(f)
    d = vnode_to_dict(root)
    assert d is not None
    assert d["type"] == "Frame"
    assert d["children"][0]["type"] == "VStack"
    assert d["children"][0]["children"][0]["type"] == "Button"
    assert d["children"][0]["children"][0]["key"] == "ok"


def test_non_layout_template_has_no_tree(tmp_path: Path):
    f = tmp_path / "plain.wij"
    f.write_text("just text", encoding="utf-8")
    root, rendered = build_vnode_tree(f)
    assert root is None
    assert render_tree_text(root) == "<no layout tree>"
    assert vnode_to_dict(root) is None


def test_build_tree_from_app():
    root, rendered = build_vnode_tree("examples/basic/hello_world.py")
    assert root is not None
    assert root.type == "Frame"
