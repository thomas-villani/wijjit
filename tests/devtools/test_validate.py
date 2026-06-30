"""Tests for wijjit.devtools.validate."""

from pathlib import Path

from wijjit.devtools import validate_file, validate_template

GOOD = """
{% frame title="Login" width=40 height=8 %}
  {% vstack spacing=1 %}
    {% textinput id="username" placeholder="User" width=30 action="go" bind=True tab_index=1 %}{% endtextinput %}
    {% button id="ok" action="go" %}Login{% endbutton %}
  {% endvstack %}
{% endframe %}
"""


def _codes(report):
    return [f.code for f in report.findings]


def test_clean_template_is_ok():
    report = validate_template(GOOD)
    assert report.ok
    assert report.errors() == []


def test_clean_realistic_template_has_no_spurious_attribute_warnings():
    # tab_index / bind / action / focused must not be flagged as unknown attrs.
    report = validate_template(GOOD)
    assert "unknown-attribute" not in _codes(report)


def test_missing_end_tag_is_syntax_error_with_line():
    src = "{% frame width=20 height=4 %}\n  hello\n"  # never closed
    report = validate_template(src)
    assert not report.ok
    findings = report.errors()
    assert findings
    assert findings[0].code == "jinja-syntax"
    assert findings[0].line is not None


def test_unknown_tag_is_syntax_error():
    report = validate_template("{% frame %}{% blorp %}{% endframe %}")
    assert not report.ok
    assert "jinja-syntax" in _codes(report)


def test_undefined_variable_is_warning():
    src = "{% frame width=30 height=4 %}{{ missing_var }}{% endframe %}"
    report = validate_template(src)
    assert report.ok  # warning only
    warns = report.warnings()
    assert any(f.code == "undefined-variable" for f in warns)


def test_provided_context_suppresses_undefined_warning():
    src = "{% frame width=30 height=4 %}{{ greeting }}{% endframe %}"
    report = validate_template(src, context={"greeting": "hi"})
    assert "undefined-variable" not in _codes(report)


def test_unknown_attribute_on_passthrough_tag_is_warning():
    # textinput forwards extra kwargs to the element, so a typo reaches the VNode.
    src = '{% frame width=30 height=5 %}{% textinput id="u" colour="red" %}{% endtextinput %}{% endframe %}'
    report = validate_template(src)
    assert report.ok  # warning only
    assert "unknown-attribute" in _codes(report)


def test_no_layout_tags_is_info():
    report = validate_template("just text, no tags")
    assert report.ok
    assert "no-layout-tags" in _codes(report)


def test_render_flag_populates_rendered():
    report = validate_template(GOOD, render=True)
    assert report.rendered is not None
    assert "Login" in report.rendered


def test_to_dict_is_json_friendly():
    report = validate_template(GOOD)
    d = report.to_dict()
    assert d["ok"] is True
    assert isinstance(d["findings"], list)
    assert "path" in d


def test_validate_file_template(tmp_path: Path):
    f = tmp_path / "ok.wij"
    f.write_text(GOOD, encoding="utf-8")
    report = validate_file(f)
    assert report.ok


def test_validate_file_app_loads_cleanly():
    report = validate_file("examples/basic/hello_world.py")
    assert report.ok
