"""Tests for ``wijjit.plugins`` entry-point auto-discovery."""

from __future__ import annotations

import importlib.metadata

import pytest

import wijjit.plugins as plugins
from wijjit import Element


class _DiscoveredWidget(Element):
    def render_to(self, ctx):  # pragma: no cover - not painted here
        pass


class _FakeEntryPoint:
    """Minimal stand-in for ``importlib.metadata.EntryPoint``."""

    def __init__(self, name, load_fn):
        self.name = name
        self.group = "wijjit.plugins"
        self._load_fn = load_fn

    def load(self):
        return self._load_fn()


def _patch_entry_points(monkeypatch, eps):
    def fake_entry_points(*, group=None):
        assert group == "wijjit.plugins"
        return list(eps)

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)


def test_discovery_loads_declared_plugin(monkeypatch):
    def _register():
        plugins.register_element(
            "DiscoveredWidget", _DiscoveredWidget, tag="discovered"
        )

    _patch_entry_points(monkeypatch, [_FakeEntryPoint("dw", _register)])

    plugins.ensure_plugins_loaded()

    names = [p.type_name for p in plugins.registered_plugins()]
    assert "DiscoveredWidget" in names


def test_discovery_runs_once(monkeypatch):
    calls = {"n": 0}

    def _register():
        calls["n"] += 1
        plugins.register_element("DiscoveredWidget", _DiscoveredWidget)

    _patch_entry_points(monkeypatch, [_FakeEntryPoint("dw", _register)])

    plugins.ensure_plugins_loaded()
    plugins.ensure_plugins_loaded()  # second call is a no-op

    assert calls["n"] == 1


def test_broken_plugin_is_skipped_and_others_still_load(monkeypatch, caplog):
    def _boom():
        raise RuntimeError("plugin exploded on import")

    def _register_good():
        plugins.register_element("GoodWidget", _DiscoveredWidget, tag="goodwidget")

    _patch_entry_points(
        monkeypatch,
        [
            _FakeEntryPoint("broken", _boom),
            _FakeEntryPoint("good", _register_good),
        ],
    )

    plugins.ensure_plugins_loaded()  # must not raise

    names = [p.type_name for p in plugins.registered_plugins()]
    assert "GoodWidget" in names
    assert "GoodWidget" not in (n for n in names if n == "broken")


def test_metadata_backend_error_is_non_fatal(monkeypatch):
    def fake_entry_points(*, group=None):
        raise RuntimeError("metadata backend unavailable")

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)

    # Should swallow the error and simply register nothing.
    plugins.ensure_plugins_loaded()
    assert plugins.registered_plugins() == []
