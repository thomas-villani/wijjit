"""Measure and report Wijjit rendering performance.

Drives the real ``Renderer.render_with_layout`` pipeline (template parse ->
VNode -> reconcile -> layout -> paint -> ANSI) across a few representative
scenarios and terminal sizes, and reports three things:

1. **Render latency** - wall-clock per frame. Reported for context only; lead
   with the byte counts, which are deterministic.
2. **Terminal I/O** - bytes emitted for a full repaint, for an idle frame, and
   for a frame in which one small thing changed. This is the number that
   matters most: it is what makes a Wijjit app feel instant over SSH and why it
   does not flicker.
3. **Import cost** - ``import wijjit`` in a cold subprocess.

The biggest win is I/O: an idle frame writes nothing at all, and a frame with
one changed widget writes a few dozen bytes instead of the whole screen. The
steady-state render is now also CPU-cheaper than a full repaint - on the
incremental path (the one a running app uses) the paint buffer starts as a copy
of the previous frame, unchanged elements are skipped, and only real changes are
diffed, so a localized edit does work proportional to *what changed*, not to the
size of the view. The ``full`` column below is the worst case (first paint or a
resize), which still paints and diffs the whole screen.

Timings are machine- and load-dependent, so treat them as indicative. The byte
counts are deterministic and are regression-tested in
``tests/core/test_diff_render_bytes.py``.

Usage
-----
From the repo root::

    uv run python scripts/bench_perf.py              # human-readable table
    uv run python scripts/bench_perf.py --markdown   # paste into docs
    uv run python scripts/bench_perf.py --json       # machine-readable
    uv run python scripts/bench_perf.py --quick      # fewer iterations
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wijjit.core.renderer import Renderer  # noqa: E402

# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------

HELLO = """
{% frame title="Hello" border="single" %}
  {% vstack spacing=1 %}
    Hello, world.
    Frame {{ tick }}
    {% button action="go" %}Go{% endbutton %}
  {% endvstack %}
{% endframe %}
"""

FORM = """
{% frame title="Login" border="single" %}
  {% vstack spacing=1 padding=1 %}
    {{ status }}
    Username:
    {% textinput id="username" width=30 %}{% endtextinput %}
    Password:
    {% textinput id="password" width=30 password=True %}{% endtextinput %}
    {% hstack spacing=2 %}
      {% button action="login" %}Login{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
"""

# Each scenario exposes one naturally-changing value so the "one small change"
# frame is meaningful: a frame counter, a status message, a sparkline tick.
_STATUSES = [
    "Enter your credentials",
    "Checking credentials...",
    "Invalid username or password",
]

DASHBOARD = """
{% vstack %}
  {% hstack height=10 %}
    {% frame title="Stats" width="50%" %}
      {% vstack %}
        {% for i in rows %}
        Row {{ i }}: value {{ i * 7 }}
        {% endfor %}
      {% endvstack %}
    {% endframe %}
    {% frame title="Chart" width="50%" %}
      {% sparkline data=series %}{% endsparkline %}
      {% gauge value=42 max_value=100 %}{% endgauge %}
    {% endframe %}
  {% endhstack %}
  {% frame title="Table" height="fill" %}
    {% table data=users columns=["name", "email", "role"] %}{% endtable %}
  {% endframe %}
  {% hstack height=3 %}
    {% button action="a" %}Alpha{% endbutton %}
    {% button action="b" %}Beta{% endbutton %}
    {% button action="c" %}Gamma{% endbutton %}
  {% endhstack %}
{% endvstack %}
"""


def _dashboard_context(tick: int = 0) -> dict[str, Any]:
    """Build the dashboard context; ``tick`` animates the sparkline."""
    return {
        "rows": list(range(8)),
        "series": [(tick + i) % 10 for i in range(12)],
        "users": [
            {
                "name": f"User {i}",
                "email": f"u{i}@example.com",
                "role": "admin" if i % 3 else "user",
            }
            for i in range(40)
        ],
    }


# (label, template, context factory taking a tick counter)
SCENARIOS: list[tuple[str, str, Callable[[int], dict[str, Any]]]] = [
    ("hello world", HELLO, lambda tick: {"tick": tick}),
    ("login form", FORM, lambda tick: {"status": _STATUSES[tick % len(_STATUSES)]}),
    ("dashboard (table + charts)", DASHBOARD, _dashboard_context),
]

SIZES: list[tuple[int, int]] = [(80, 24), (120, 40), (200, 60)]


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


@dataclass
class Timing:
    """Latency for one scenario at one terminal size."""

    scenario: str
    width: int
    height: int
    full_ms: float
    diff_idle_ms: float
    diff_change_ms: float
    diff_change_p95_ms: float


@dataclass
class ByteCount:
    """Bytes written to the terminal for one scenario at one size."""

    scenario: str
    width: int
    height: int
    full_bytes: int
    idle_bytes: int
    change_bytes: int

    @property
    def ratio(self) -> float | None:
        """How many times smaller a one-change frame is than a full repaint.

        ``None`` when the changed frame emitted nothing, which would make the
        ratio meaningless rather than merely large.
        """
        if self.change_bytes <= 0:
            return None
        return self.full_bytes / self.change_bytes


def _time_it(
    fn: Callable[[], Any], iterations: int, warmup: int
) -> tuple[float, float]:
    """Return (median, p95) seconds for ``fn`` over ``iterations`` samples."""
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    samples.sort()
    return statistics.median(samples), samples[int(len(samples) * 0.95)]


def measure_timing(
    scenario: str,
    template: str,
    context_for: Callable[[int], dict[str, Any]],
    width: int,
    height: int,
    iterations: int,
    warmup: int,
) -> Timing:
    """Measure full-render and steady-state diff-render latency."""
    # Full render: clear the displayed buffer so no diffing can occur. This is
    # the worst case, e.g. the first paint or a terminal resize.
    full_renderer = Renderer()

    def full() -> Any:
        full_renderer._last_displayed_buffer = None
        return full_renderer.render_with_layout(
            template, context=context_for(0), width=width, height=height
        )

    full_median, _ = _time_it(full, iterations, warmup)

    # Steady state, nothing changed: the diff finds no work but still compares.
    # These steady-state renderers pass ``allow_incremental=True`` so they
    # exercise the SAME path a running app uses (``app._render`` enables it
    # whenever no overlay is up): the paint buffer starts as a copy of the
    # previous frame, unchanged elements are skipped, and only real changes are
    # diffed. The full-repaint measurement above deliberately does not - it is
    # the worst case (first paint / resize), where every cell is painted fresh.
    idle_renderer = Renderer()
    idle_renderer.render_with_layout(
        template, context=context_for(0), width=width, height=height
    )

    def diff_idle() -> Any:
        return idle_renderer.render_with_layout(
            template,
            context=context_for(0),
            width=width,
            height=height,
            allow_incremental=True,
        )

    idle_median, _ = _time_it(diff_idle, iterations, warmup)

    # Steady state with a small change each frame: the realistic animation case.
    change_renderer = Renderer()
    change_renderer.render_with_layout(
        template, context=context_for(0), width=width, height=height
    )
    tick = iter(range(1, 10**9))

    def diff_change() -> Any:
        return change_renderer.render_with_layout(
            template,
            context=context_for(next(tick)),
            width=width,
            height=height,
            allow_incremental=True,
        )

    change_median, change_p95 = _time_it(diff_change, iterations, warmup)

    return Timing(
        scenario=scenario,
        width=width,
        height=height,
        full_ms=full_median * 1000,
        diff_idle_ms=idle_median * 1000,
        diff_change_ms=change_median * 1000,
        diff_change_p95_ms=change_p95 * 1000,
    )


def measure_bytes(
    scenario: str,
    template: str,
    context_for: Callable[[int], dict[str, Any]],
    width: int,
    height: int,
) -> ByteCount:
    """Measure ANSI bytes for a full repaint, an idle frame, and a changed frame."""
    renderer = Renderer()

    # Prime, then force a full repaint and measure it.
    renderer.render_with_layout(
        template, context=context_for(0), width=width, height=height
    )
    renderer._last_displayed_buffer = None
    full_out, _, _ = renderer.render_with_layout(
        template, context=context_for(0), width=width, height=height
    )

    # Idle frame: re-render identical content. A correct diff emits nothing.
    idle_out, _, _ = renderer.render_with_layout(
        template, context=context_for(0), width=width, height=height
    )

    # Steady-state frame with a single small change.
    change_out, _, _ = renderer.render_with_layout(
        template, context=context_for(1), width=width, height=height
    )

    return ByteCount(
        scenario=scenario,
        width=width,
        height=height,
        full_bytes=len(full_out),
        idle_bytes=len(idle_out),
        change_bytes=len(change_out),
    )


def measure_import_ms(runs: int = 5) -> float:
    """Median wall-clock milliseconds for ``import wijjit`` in a fresh process."""
    snippet = (
        "import time; start = time.perf_counter(); "
        "import wijjit; "
        "print(time.perf_counter() - start)"
    )
    samples = []
    for _ in range(runs):
        proc = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )
        samples.append(float(proc.stdout.strip()) * 1000)
    return statistics.median(samples)


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _machine() -> dict[str, str]:
    return {
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "python": platform.python_version(),
        "wijjit": __import__("wijjit").__version__,
    }


def report_text(
    timings: list[Timing], counts: list[ByteCount], import_ms: float
) -> str:
    lines: list[str] = []
    info = _machine()
    lines.append(
        f"wijjit {info['wijjit']} | python {info['python']} | {info['platform']}"
    )
    lines.append("")

    lines.append("Render latency (median per frame)")
    lines.append(
        f"  {'scenario':<28} {'size':>8} {'full':>10} {'idle':>10} {'change':>10} {'p95':>10}"
    )
    for t in timings:
        size = f"{t.width}x{t.height}"
        lines.append(
            f"  {t.scenario:<28} {size:>8} {t.full_ms:>9.2f}m {t.diff_idle_ms:>9.2f}m "
            f"{t.diff_change_ms:>9.2f}m {t.diff_change_p95_ms:>9.2f}m"
        )
    lines.append("")

    lines.append("Terminal I/O per frame")
    lines.append(
        f"  {'scenario':<28} {'size':>8} {'full repaint':>14} {'idle':>8} {'1 change':>10} {'saving':>9}"
    )
    for c in counts:
        size = f"{c.width}x{c.height}"
        saving = f"{c.ratio:.0f}x" if c.ratio is not None else "-"
        lines.append(
            f"  {c.scenario:<28} {size:>8} {c.full_bytes:>13,}B {c.idle_bytes:>7,}B "
            f"{c.change_bytes:>9,}B {saving:>9}"
        )
    lines.append("")
    lines.append(f"import wijjit: {import_ms:.0f} ms (cold subprocess, median)")
    return "\n".join(lines)


def report_markdown(
    timings: list[Timing], counts: list[ByteCount], import_ms: float
) -> str:
    info = _machine()
    lines: list[str] = []
    lines.append("### Render latency")
    lines.append("")
    lines.append("| Scenario | Size | Full repaint | Steady state | p95 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for t in timings:
        lines.append(
            f"| {t.scenario} | {t.width}x{t.height} | {t.full_ms:.1f} ms | "
            f"{t.diff_change_ms:.1f} ms | {t.diff_change_p95_ms:.1f} ms |"
        )
    lines.append("")
    lines.append("### Terminal I/O per frame")
    lines.append("")
    lines.append(
        "| Scenario | Size | Full repaint | Idle frame | One change | Reduction |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for c in counts:
        saving = f"{c.ratio:.0f}x" if c.ratio is not None else "n/a"
        lines.append(
            f"| {c.scenario} | {c.width}x{c.height} | {c.full_bytes:,} B | "
            f"{c.idle_bytes:,} B | {c.change_bytes:,} B | {saving} |"
        )
    lines.append("")
    lines.append(f"`import wijjit`: **{import_ms:.0f} ms** (cold subprocess, median)")
    lines.append("")
    lines.append(
        f"<sub>Measured on {info['platform']}, Python {info['python']}, "
        f"wijjit {info['wijjit']}.</sub>"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Wijjit rendering.")
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    parser.add_argument(
        "--markdown", action="store_true", help="Emit a Markdown table."
    )
    parser.add_argument("--quick", action="store_true", help="Fewer iterations.")
    args = parser.parse_args(argv)

    iterations = 40 if args.quick else 200
    warmup = 5 if args.quick else 20

    timings: list[Timing] = []
    counts: list[ByteCount] = []
    for scenario, template, context_for in SCENARIOS:
        for width, height in SIZES:
            timings.append(
                measure_timing(
                    scenario, template, context_for, width, height, iterations, warmup
                )
            )
            counts.append(measure_bytes(scenario, template, context_for, width, height))

    import_ms = measure_import_ms(runs=3 if args.quick else 5)

    if args.json:
        print(
            json.dumps(
                {
                    "machine": _machine(),
                    "timings": [asdict(t) for t in timings],
                    "bytes": [
                        asdict(c)
                        | {"ratio": round(c.ratio, 1) if c.ratio is not None else None}
                        for c in counts
                    ],
                    "import_ms": round(import_ms, 1),
                },
                indent=2,
            )
        )
    elif args.markdown:
        print(report_markdown(timings, counts, import_ms))
    else:
        print(report_text(timings, counts, import_ms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
