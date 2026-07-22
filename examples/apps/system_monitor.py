#!/usr/bin/env python3
"""CPU + memory monitor for Wijjit.

Shows:
- live CPU and memory gauges
- history graphs since the app started

Run:
  pip install psutil
  python examples/apps/system_monitor.py
"""

from __future__ import annotations

from datetime import datetime
from threading import Event, Thread

import psutil

from wijjit import Wijjit, render_template_string

SAMPLE_INTERVAL = 1.0
stop_event = Event()


def format_uptime(started_at: datetime) -> str:
    elapsed = int((datetime.now() - started_at).total_seconds())
    mins, secs = divmod(elapsed, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs}h {mins}m {secs}s" if hrs else f"{mins}m {secs}s"


def main() -> None:
    # Prime CPU sampling and capture an initial reading.
    initial_cpu = float(psutil.cpu_percent(interval=0.2))
    initial_memory = float(psutil.virtual_memory().percent)
    started_at = datetime.now()

    app = Wijjit(
        initial_state={
            "cpu_usage": initial_cpu,
            "memory_usage": initial_memory,
            "cpu_history": [initial_cpu],
            "memory_history": [initial_memory],
            "sample_count": 1,
            "last_update": datetime.now().strftime("%H:%M:%S"),
        }
    )

    def monitor_loop() -> None:
        # Gate the worker on the Event, not on app.running: this thread
        # starts before app.run(), when the loop is not running yet.
        while not stop_event.is_set():
            cpu = float(psutil.cpu_percent(interval=None))
            memory = float(psutil.virtual_memory().percent)

            app.state["cpu_usage"] = cpu
            app.state["memory_usage"] = memory
            app.state["cpu_history"] = app.state["cpu_history"] + [cpu]
            app.state["memory_history"] = app.state["memory_history"] + [memory]
            app.state["sample_count"] = app.state["sample_count"] + 1
            app.state["last_update"] = datetime.now().strftime("%H:%M:%S")

            # Ask Wijjit to redraw even if nothing else happens.
            app.refresh()
            stop_event.wait(SAMPLE_INTERVAL)

    @app.view("main", default=True)
    def main_view():
        chart_data = {
            "CPU": list(app.state.cpu_history),
            "Memory": list(app.state.memory_history),
        }

        return render_template_string(
            """
{% frame title="CPU + Memory Monitor" border="double" width="fill" height="fill" %}
  {% vstack spacing=1 padding=1 %}
    Current system usage since app start
    Started: {{ started_at }} | Uptime: {{ uptime }}
    Last sample: {{ state.last_update }} | Samples: {{ state.sample_count }}

    {% hstack spacing=2 %}
      {% frame title="CPU" border="single" width=38 height=9 %}
        {% vstack spacing=0 padding=1 %}
          {% gauge id="cpu_gauge"
                   value=state.cpu_usage
                   max_value=100
                   width=34
                   label="CPU Usage"
                   unit="%"
                   color_mode="threshold" %}{% endgauge %}
          Current: {{ "%.1f"|format(state.cpu_usage) }}%
        {% endvstack %}
      {% endframe %}

      {% frame title="Memory" border="single" width=38 height=9 %}
        {% vstack spacing=0 padding=1 %}
          {% gauge id="mem_gauge"
                   value=state.memory_usage
                   max_value=100
                   width=34
                   label="Memory Usage"
                   unit="%"
                   color_mode="gradient"
                   color_scale="heat" %}{% endgauge %}
          Current: {{ "%.1f"|format(state.memory_usage) }}%
        {% endvstack %}
      {% endframe %}
    {% endhstack %}

    {% frame title="History since app start" border="single" width="fill" height=14 %}
      {% linechart id="usage_history"
                   data=chart_data
                   width=76
                   height=10
                   style="line"
                   show_axis=true
                   show_labels=false
                   show_legend=true %}
      {% endlinechart %}
    {% endframe %}

    Press 'r' to force a refresh, 'q' to quit
  {% endvstack %}
{% endframe %}
            """,
            state=app.state,
            chart_data=chart_data,
            started_at=started_at.strftime("%H:%M:%S"),
            uptime=format_uptime(started_at),
        )

    @app.on_key("r")
    def refresh_now(event):
        app.refresh()

    @app.on_key("q")
    def quit_app(event):
        stop_event.set()
        app.quit()

    worker = Thread(target=monitor_loop, daemon=True)
    worker.start()

    try:
        app.run()
    finally:
        stop_event.set()


if __name__ == "__main__":
    main()
