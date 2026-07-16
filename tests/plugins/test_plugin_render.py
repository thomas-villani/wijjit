"""End-to-end render of a plugin element through the public seam."""

from __future__ import annotations

import wijjit.plugins as plugins
from wijjit import Element, app_from_template, register_element
from wijjit.testing import WijjitHarness

TEMPLATE = (
    "{% vstack %}"
    '{% sparkgauge id="g" value=state.value %}{% endsparkgauge %}'
    "{% endvstack %}"
)


def test_plugin_element_renders(registered_spark_gauge):
    app = app_from_template(TEMPLATE, state={"value": 70})
    with WijjitHarness(app, size=(30, 5)) as h:
        h.tick(frames=1)
        # value 70 -> 7 filled blocks in a 10-wide bar.
        h.assert_text("[#######")


def test_plugin_element_reacts_to_state(registered_spark_gauge):
    app = app_from_template(TEMPLATE, state={"value": 20})
    with WijjitHarness(app, size=(30, 5)) as h:
        h.tick(frames=1)
        h.assert_text("[##")
        app.state["value"] = 90
        h.tick(frames=1)
        h.assert_text("[#########")


def test_plugin_alias_type_resolves(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls, tag="sparkgauge", aliases=("SG",))
    # The alias is present in the element registry built by a fresh renderer.
    from wijjit.core.element_registry import ElementRegistry

    registry = ElementRegistry()
    assert registry.has_type("SparkGauge")
    assert registry.has_type("SG")


def test_late_registration_via_app_method(spark_gauge_cls):
    # Build an app whose renderer already exists, then register on it.
    app = app_from_template("{% vstack %}{% text %}hi{% endtext %}{% endvstack %}")
    app.register_element("SparkGauge", spark_gauge_cls, tag="sparkgauge")

    assert app.renderer._reconciler.registry.has_type("SparkGauge")
    assert "sparkgauge" in app.renderer.get_extension_tag_names()
