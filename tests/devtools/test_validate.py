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


def test_unknown_attribute_on_button_is_warning():
    # Every tag now forwards leftover kwargs onto the VNode (not just textinput),
    # so a typo like ``wdith`` on a button reaches the VNode and is flagged
    # instead of vanishing silently.
    src = "{% frame width=30 height=5 %}{% button wdith=20 %}Go{% endbutton %}{% endframe %}"
    report = validate_template(src)
    assert report.ok  # warning only
    unknown = [f for f in report.findings if f.code == "unknown-attribute"]
    assert len(unknown) == 1
    assert "wdith" in unknown[0].message


def test_unknown_attribute_on_display_tag_is_warning():
    # The forwarding choke point works broadly, not only for input tags: a typo
    # on a display tag (text) is surfaced too.
    src = "{% frame width=30 height=5 %}{% text wdith=5 %}Hi{% endtext %}{% endframe %}"
    report = validate_template(src)
    assert report.ok
    assert "unknown-attribute" in _codes(report)


def test_undefined_variable_at_render_dedupes_static_finding():
    # The static check reports {{ typo }} once; the strict render fails on the
    # same name but is deduped, so exactly one undefined-variable finding remains.
    src = "{% frame width=30 height=5 %}{{ typo }}{% endframe %}"
    report = validate_template(src, render=True)
    undefined = [f for f in report.findings if f.code == "undefined-variable"]
    assert len(undefined) == 1


def test_undefined_attribute_on_state_is_error():
    # Attribute access on an undefined value keeps the undefined-attribute code
    # (the message is "... has no attribute ...", not "'x' is undefined").
    src = "{% frame width=30 height=5 %}{{ state.missing }}{% endframe %}"
    report = validate_template(src, render=True, context={"state": {}})
    assert not report.ok
    assert "undefined-attribute" in _codes(report)
    assert "undefined-variable" not in _codes(report)


def test_undefined_variable_and_unknown_attribute_both_reported():
    # The strict render raises on {{ typo }}; the lenient re-render preserves the
    # tree checks so the button's unknown attribute is still surfaced.
    src = (
        "{% frame width=30 height=5 %}{{ typo }}"
        "{% button wdith=1 %}Go{% endbutton %}{% endframe %}"
    )
    report = validate_template(src)
    codes = _codes(report)
    assert "undefined-variable" in codes
    assert "unknown-attribute" in codes


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


def _loop(inner: str) -> str:
    return "{% vstack %}{% for it in rows %}" + inner + "{% endfor %}{% endvstack %}"


def test_unkeyed_stateful_element_in_loop_is_warning():
    src = _loop("{% textinput placeholder=it %}{% endtextinput %}")
    report = validate_template(src, context={"rows": []})
    assert report.ok  # warning only, not an error
    unkeyed = [f for f in report.findings if f.code == "unkeyed-loop-element"]
    assert len(unkeyed) == 1
    assert unkeyed[0].line == 1
    assert "textinput" in unkeyed[0].message


def test_keyed_element_in_loop_is_clean():
    src = _loop("{% textinput key=it placeholder=it %}{% endtextinput %}")
    report = validate_template(src, context={"rows": []})
    assert "unkeyed-loop-element" not in _codes(report)


def test_id_element_in_loop_is_clean():
    # An explicit id is also a stable identity, so it should not be flagged.
    src = _loop('{% textinput id="r_" ~ it %}{% endtextinput %}')
    report = validate_template(src, context={"rows": []})
    assert "unkeyed-loop-element" not in _codes(report)


def test_stateless_element_in_loop_is_not_flagged():
    # Text is repainted from props each render; positional reuse is invisible.
    src = _loop("{% text %}{{ it }}{% endtext %}")
    report = validate_template(src, context={"rows": []})
    assert "unkeyed-loop-element" not in _codes(report)


def test_unkeyed_element_outside_loop_is_not_flagged():
    src = "{% vstack %}{% textinput placeholder='x' %}{% endtextinput %}{% endvstack %}"
    report = validate_template(src)
    assert "unkeyed-loop-element" not in _codes(report)


def test_nested_loop_unkeyed_element_flagged_once():
    src = (
        "{% for g in groups %}{% for it in g %}"
        "{% select %}{% endselect %}"
        "{% endfor %}{% endfor %}"
    )
    report = validate_template(src, context={"groups": []})
    unkeyed = [f for f in report.findings if f.code == "unkeyed-loop-element"]
    assert len(unkeyed) == 1
