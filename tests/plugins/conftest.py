"""Shared fixtures for the plugin-seam tests.

The plugin registry is process-global mutable state, so every test must start
and end with a clean slate or registrations leak across tests and the
``_discovered`` flag short-circuits the discovery tests.
"""

from __future__ import annotations

import pytest

import wijjit.plugins as plugins
from wijjit import Element


class SparkGauge(Element):
    """A tiny leaf element used as a plugin fixture across the plugin tests."""

    def __init__(self, id=None, value=0, width="auto", height=1):
        super().__init__(id=id)
        self.value = int(value)
        self.width_spec = width
        self.height_spec = height

    def get_intrinsic_size(self):
        return (12, 1)

    def render_to(self, ctx):
        style = ctx.style_resolver.resolve_style(self, "sparkgauge")
        blocks = "#" * max(0, min(10, self.value // 10))
        ctx.write_text(0, 0, f"[{blocks:<10}]", style)


@pytest.fixture(autouse=True)
def _reset_plugins():
    """Clear the global plugin registry and discovery flag around every test."""
    plugins.clear_plugins()
    yield
    plugins.clear_plugins()


@pytest.fixture
def spark_gauge_cls():
    """Return the fixture element class (unregistered)."""
    return SparkGauge


@pytest.fixture
def registered_spark_gauge(spark_gauge_cls):
    """Register the fixture element with a ``{% sparkgauge %}`` tag and return it."""
    plugins.register_element("SparkGauge", spark_gauge_cls, tag="sparkgauge")
    return spark_gauge_cls
