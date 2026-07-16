"""The devtools validator must recognize plugin element types and their tags."""

from __future__ import annotations

from wijjit.devtools.validate import validate_template


def test_validator_accepts_plugin_tag(registered_spark_gauge):
    template = (
        "{% vstack %}"
        '{% sparkgauge id="g" value=5 %}{% endsparkgauge %}'
        "{% endvstack %}"
    )
    report = validate_template(template)
    codes = [f.code for f in report.findings]
    assert not any("unknown-element-type" == c for c in codes), report.findings
    assert not any("unknown" in (c or "") for c in codes), report.findings


def test_validator_still_flags_unknown_tag(registered_spark_gauge):
    # A genuinely unknown tag must still be reported (the plugin didn't register it).
    template = (
        "{% vstack %}"
        "{% definitelynotarealtag %}{% enddefinitelynotarealtag %}"
        "{% endvstack %}"
    )
    report = validate_template(template)
    assert report.findings  # some error is reported for the bogus tag
