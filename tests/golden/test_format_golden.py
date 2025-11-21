"""Golden tests for ANSI formatting and layout rendering."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from wijjit.core.renderer import Renderer
from wijjit.rendering.ansi_adapter import ansi_string_to_cells

GOLDEN_ROOT = Path(__file__).parent
ELEMENTS_DIR = GOLDEN_ROOT / "elements"
LAYOUTS_DIR = GOLDEN_ROOT / "layouts"


def _normalize_cells(cells):
    return [
        {
            "char": cell.char,
            "fg_color": list(cell.fg_color) if cell.fg_color else None,
            "bg_color": list(cell.bg_color) if cell.bg_color else None,
            "bold": cell.bold,
            "italic": cell.italic,
            "underline": cell.underline,
        }
        for cell in cells
    ]


def _compare_or_update_json(path: Path, data: dict, update: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if update:
        path.write_text(json.dumps(data, indent=2) + "\n")
    if not path.exists():
        raise AssertionError(f"Missing golden file: {path}")
    expected = json.loads(path.read_text())
    assert expected == data


def _compare_or_update_text(path: Path, text: str, update: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.rstrip("\n") + "\n"
    if update:
        path.write_text(normalized, encoding="utf-8")
    if not path.exists():
        raise AssertionError(f"Missing golden file: {path}")
    expected = path.read_text(encoding="utf-8")
    assert expected.splitlines() == normalized.splitlines()


@dataclass(frozen=True)
class AnsiCase:
    name: str
    sample: str


ANSI_CASES = [
    AnsiCase(
        "ansi_palette",
        "\x1b[1;38;2;255;200;0mWARN\x1b[0m text "
        "\x1b[3;4;48;2;20;40;60;38;2;180;220;255mNOTE\x1b[0m",
    ),
    AnsiCase(
        "severity_banner",
        "\x1b[2mINFO\x1b[0m | "
        "\x1b[33mWARN\x1b[0m | "
        "\x1b[97;41mALERT\x1b[0m | "
        "\x1b[7mINVERT\x1b[0m",
    ),
]


@pytest.mark.parametrize("case", ANSI_CASES, ids=lambda c: c.name)
def test_ansi_goldens(case: AnsiCase, golden_update: bool) -> None:
    """Ensure ANSI strings map to stored cell representations."""
    parsed_cells = ansi_string_to_cells(case.sample)
    normalized = _normalize_cells(parsed_cells)
    payload = {"sample": case.sample, "cells": normalized}

    golden_path = ELEMENTS_DIR / f"{case.name}.json"
    _compare_or_update_json(golden_path, payload, golden_update)


@dataclass(frozen=True)
class LayoutCase:
    name: str
    template: str
    width: int
    height: int


STATUS_TEMPLATE = """
{% hstack width=60 height=14 spacing=1 %}
    {% frame width=28 height=14 title="Environment" %}
        {% vstack spacing=1 %}
            ENV: Production
            Version: 1.2.3
            Region: us-east-1
            Status: Healthy
        {% endvstack %}
    {% endframe %}
    {% frame width=31 height=14 title="Metrics" %}
        {% vstack spacing=1 %}
            Requests: 1024/s
            Errors: 0.4%
            Latency: 120ms p95
            Active Nodes: 12
        {% endvstack %}
    {% endframe %}
{% endhstack %}
""".strip()


ACTIVITY_TEMPLATE = """
{% frame title="Deployments" width=62 height=15 %}
    {% vstack spacing=1 %}
        Latest activity
        {% frame width=58 height=4 title="prod-cluster" %}
            Version: 2024.10.12
            Status: Success
        {% endframe %}
        {% frame width=58 height=4 title="staging" %}
            Version: 2024.10.13
            Status: In progress
        {% endframe %}
    {% endvstack %}
{% endframe %}
""".strip()


WIZARD_TEMPLATE = """
{% frame title="Setup Wizard" width=60 height=12 %}
    {% vstack spacing=1 %}
        Step 2 of 3: Configure team
        {% progressbar id="progress" value=66 max=100 width=40 %}{% endprogressbar %}
        {% hstack spacing=2 %}
            {% frame width=28 height=5 title="Team" %}
                Members: 12
                Roles: 3
            {% endframe %}
            {% frame width=28 height=5 title="Approvals" %}
                Pending: 2
                Completed: 4
            {% endframe %}
        {% endhstack %}
    {% endvstack %}
{% endframe %}
""".strip()


LAYOUT_CASES = [
    LayoutCase("status_dashboard", STATUS_TEMPLATE, 60, 14),
    LayoutCase("deployments_panel", ACTIVITY_TEMPLATE, 62, 15),
    LayoutCase("wizard_progress", WIZARD_TEMPLATE, 60, 12),
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c.name)
def test_layout_goldens(case: LayoutCase, golden_update: bool) -> None:
    """Rendered layouts should match stored text representations."""
    renderer = Renderer()
    renderer.render_with_layout(case.template, width=case.width, height=case.height)
    rendered_text = renderer.get_buffer_as_text()

    golden_path = LAYOUTS_DIR / f"{case.name}.txt"
    _compare_or_update_text(golden_path, rendered_text, golden_update)
