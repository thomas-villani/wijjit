"""Tests for the public ``register_element`` / ``element`` registration API."""

from __future__ import annotations

import pytest

import wijjit.plugins as plugins
from wijjit import Element, element, register_element
from wijjit.exceptions import PluginRegistrationError


class _Widget(Element):
    def __init__(self, id=None, value=0):
        super().__init__(id=id)
        self.value = value

    def render_to(self, ctx):  # pragma: no cover - not painted in these tests
        pass


def test_register_records_plugin_and_extension(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls, tag="sparkgauge")

    names = [p.type_name for p in plugins.registered_plugins()]
    assert "SparkGauge" in names

    plugin = next(
        p for p in plugins.registered_plugins() if p.type_name == "SparkGauge"
    )
    assert plugin.element_cls is spark_gauge_cls
    assert plugin.tag_name == "sparkgauge"
    assert plugin.extension is not None
    assert "sparkgauge" in plugin.extension.tags
    assert plugin.extension in plugins.plugin_extensions()


def test_register_without_tag_is_class_only(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls)
    plugin = plugins.registered_plugins()[0]
    assert plugin.extension is None
    assert plugin.tag_name is None
    assert plugins.plugin_extensions() == []


def test_aliases_resolve_to_same_class(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls, aliases=("Gauge2", "SG"))
    plugin = plugins.registered_plugins()[0]
    assert plugin.names() == ("SparkGauge", "Gauge2", "SG")


def test_non_element_class_is_rejected():
    with pytest.raises(PluginRegistrationError):
        register_element("NotAnElement", dict)  # type: ignore[arg-type]


def test_builtin_type_collision_raises(spark_gauge_cls):
    with pytest.raises(PluginRegistrationError, match="built-in element"):
        register_element("Button", spark_gauge_cls, tag="mybtn")


def test_builtin_tag_collision_raises(spark_gauge_cls):
    with pytest.raises(PluginRegistrationError, match="built-in tag"):
        register_element("SparkGaugeX", spark_gauge_cls, tag="button")


def test_second_plugin_same_type_name_raises(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls)
    with pytest.raises(PluginRegistrationError, match="another plugin"):
        register_element("SparkGauge", _Widget)


def test_idempotent_double_registration_is_noop(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls, tag="sparkgauge")
    register_element("SparkGauge", spark_gauge_cls, tag="sparkgauge")
    assert len(plugins.registered_plugins()) == 1
    assert len(plugins.plugin_extensions()) == 1


def _make_same_source_class():
    # Two calls produce distinct class objects sharing __module__/__qualname__,
    # exactly like a module re-executed (reloaded) by a test harness.
    class Reloadable(Element):
        def render_to(self, ctx):  # pragma: no cover
            pass

    return Reloadable


def test_same_source_reregistration_refreshes_without_collision():
    first = _make_same_source_class()
    second = _make_same_source_class()
    assert first is not second
    assert first.__qualname__ == second.__qualname__

    register_element("Reloadable", first, tag="reloadable")
    # A reload of the same-named class from the same source must not raise.
    register_element("Reloadable", second, tag="reloadable")

    plugins_now = plugins.registered_plugins()
    assert len(plugins_now) == 1
    assert plugins_now[0].element_cls is second
    assert len(plugins.plugin_extensions()) == 1


def test_override_replaces_existing(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls)
    register_element("SparkGauge", _Widget, override=True)
    plugin = next(
        p for p in plugins.registered_plugins() if p.type_name == "SparkGauge"
    )
    assert plugin.element_cls is _Widget
    assert len(plugins.registered_plugins()) == 1


def test_override_allows_builtin_shadow(spark_gauge_cls):
    # Should not raise with override=True.
    register_element("Button", spark_gauge_cls, tag="mybtn", override=True)
    plugin = plugins.registered_plugins()[0]
    assert plugin.override_builtin is True


def test_decorator_registers_with_class_name():
    @element(tag="gizmo")
    class Gizmo(Element):
        def render_to(self, ctx):  # pragma: no cover
            pass

    plugin = plugins.registered_plugins()[0]
    assert plugin.type_name == "Gizmo"
    assert plugin.tag_name == "gizmo"


def test_decorator_returns_class_unchanged():
    @element("Gizmo", tag="gizmo")
    class Gizmo(Element):
        def render_to(self, ctx):  # pragma: no cover
            pass

    assert Gizmo.__name__ == "Gizmo"
    assert issubclass(Gizmo, Element)


def test_clear_plugins_resets_state(spark_gauge_cls):
    register_element("SparkGauge", spark_gauge_cls, tag="sparkgauge")
    assert plugins.registered_plugins()
    plugins.clear_plugins()
    assert plugins.registered_plugins() == []
    assert plugins.plugin_extensions() == []
