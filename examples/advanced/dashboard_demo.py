"""Dashboard Demo - Multi-Panel Dashboard Layout.

This example demonstrates building a comprehensive dashboard with:
- Multiple panels showing different metrics
- Real-time data updates
- Status indicators
- Tables, progress bars, and statistics
- Responsive layout

Run with: python examples/advanced/dashboard_demo.py

Controls:
- r: Refresh data
- q: Quit
"""

import random
from datetime import datetime

from wijjit import Wijjit

# Create app with dashboard state
app = Wijjit(
    initial_state={
        # System metrics
        "cpu_usage": 45,
        "memory_usage": 62,
        "disk_usage": 73,
        "network_in": 1024,
        "network_out": 512,
        # Application metrics
        "active_users": 127,
        "requests_per_sec": 43,
        "error_rate": 0.5,
        "avg_response_time": 125,
        # Status
        "system_status": "Healthy",
        "last_update": datetime.now().strftime("%H:%M:%S"),
        # Recent activity
        "recent_activity": [
            "User login: alice@example.com",
            "Database backup completed",
            "Cache cleared successfully",
        ],
        # Alert list
        "alerts": [
            {"level": "warning", "message": "High disk usage"},
        ],
    }
)


def simulate_data_update():
    """Simulate updating dashboard metrics with random data."""
    # Update system metrics
    app.state["cpu_usage"] = min(100, max(0, app.state["cpu_usage"] + random.randint(-10, 10)))
    app.state["memory_usage"] = min(
        100, max(0, app.state["memory_usage"] + random.randint(-5, 5))
    )
    app.state["disk_usage"] = min(
        100, max(70, app.state["disk_usage"] + random.randint(-2, 2))
    )
    app.state["network_in"] = max(0, app.state["network_in"] + random.randint(-200, 300))
    app.state["network_out"] = max(
        0, app.state["network_out"] + random.randint(-100, 200)
    )

    # Update application metrics
    app.state["active_users"] = max(
        0, app.state["active_users"] + random.randint(-10, 15)
    )
    app.state["requests_per_sec"] = max(
        0, app.state["requests_per_sec"] + random.randint(-10, 15)
    )
    app.state["error_rate"] = max(0, min(5, app.state["error_rate"] + random.uniform(-0.2, 0.2)))
    app.state["avg_response_time"] = max(
        50, app.state["avg_response_time"] + random.randint(-30, 30)
    )

    # Update status
    app.state["last_update"] = datetime.now().strftime("%H:%M:%S")

    # Update system status based on metrics
    if app.state["error_rate"] > 2.0 or app.state["cpu_usage"] > 90:
        app.state["system_status"] = "Critical"
    elif app.state["disk_usage"] > 85 or app.state["cpu_usage"] > 70:
        app.state["system_status"] = "Warning"
    else:
        app.state["system_status"] = "Healthy"


@app.view("main", default=True)
def main_view():
    """Main dashboard view.

    Returns
    -------
    dict
        View configuration with template and data
    """
    # Format metrics for display
    recent_activity_text = "\n".join(app.state.get("recent_activity", [])[-5:])

    return {
        "template": """
{% frame title="System Dashboard" border="double" width=120 height=40 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Status: {{ state.system_status }} | Last Update: {{ state.last_update }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=38 %}
        {% frame title="System Resources" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% vstack spacing=0 %}
              CPU Usage:
            {% endvstack %}
            {% progressbar value=state.cpu_usage max=100 width=32 style="bar" %}{% endprogressbar %}
            {% vstack spacing=0 %}
              {{ state.cpu_usage }}%
            {% endvstack %}

            {% vstack spacing=0 %}
              Memory Usage:
            {% endvstack %}
            {% progressbar value=state.memory_usage max=100 width=32 style="bar" %}{% endprogressbar %}
            {% vstack spacing=0 %}
              {{ state.memory_usage }}%
            {% endvstack %}

            {% vstack spacing=0 %}
              Disk Usage:
            {% endvstack %}
            {% progressbar value=state.disk_usage max=100 width=32 style="bar" %}{% endprogressbar %}
            {% vstack spacing=0 %}
              {{ state.disk_usage }}%
            {% endvstack %}
          {% endvstack %}
        {% endframe %}

        {% frame title="Network" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Network In:  {{ state.network_in }} KB/s
            Network Out: {{ state.network_out }} KB/s
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=38 %}
        {% frame title="Application Metrics" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Active Users: {{ state.active_users }}
            Requests/sec: {{ state.requests_per_sec }}
            Error Rate:   {{ "%.2f"|format(state.error_rate) }}%
            Avg Response: {{ state.avg_response_time }}ms
          {% endvstack %}
        {% endframe %}

        {% frame title="Recent Activity" border="single" width="fill" height=14 %}
          {% vstack padding=1 %}
{{ recent_activity_text }}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=38 %}
        {% frame title="Alerts" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            {% if state.alerts %}
              {% for alert in state.alerts %}
                [{{ alert.level|upper }}] {{ alert.message }}
              {% endfor %}
            {% else %}
              No active alerts
            {% endif %}
          {% endvstack %}
        {% endframe %}

        {% frame title="Quick Stats" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Uptime: 7d 14h 23m
            Total Requests: 1.2M
            Cache Hit Rate: 94.3%
            DB Connections: 45/100
          {% endvstack %}
        {% endframe %}

        {% frame title="System Info" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Version: 2.1.0
            Environment: Production
            Region: us-east-1
            Cluster: prod-cluster-01
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="refresh" %}Refresh Data{% endbutton %}
      {% button action="clear_alerts" %}Clear Alerts{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Dashboard features: Multi-panel layout | Real-time metrics | Status monitoring
      [r] Refresh | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "recent_activity_text": recent_activity_text,
        },
    }


@app.on_action("refresh")
def handle_refresh(event):
    """Refresh dashboard data.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    simulate_data_update()

    # Add to recent activity
    activity = app.state.get("recent_activity", [])
    activity.append(f"Manual refresh at {app.state['last_update']}")
    app.state["recent_activity"] = activity[-5:]


@app.on_action("clear_alerts")
def handle_clear_alerts(event):
    """Clear all alerts.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["alerts"] = []

    # Add to recent activity
    activity = app.state.get("recent_activity", [])
    activity.append("Alerts cleared")
    app.state["recent_activity"] = activity[-5:]


@app.on_action("quit")
def handle_quit(event):
    """Quit the application.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.quit()


@app.on_key("r")
def on_refresh(event):
    """Refresh data via 'r' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    simulate_data_update()


@app.on_key("q")
def on_quit(event):
    """Handle 'q' key to quit.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.quit()


if __name__ == "__main__":
    print("Dashboard Demo")
    print("=" * 50)
    print()
    print("This demo shows a multi-panel dashboard layout with:")
    print()
    print("Features:")
    print("  • System resource monitoring (CPU, Memory, Disk)")
    print("  • Network metrics (in/out traffic)")
    print("  • Application metrics (users, requests, errors)")
    print("  • Real-time data updates")
    print("  • Alert system")
    print("  • Recent activity log")
    print("  • Status indicators")
    print()
    print("Layout Patterns:")
    print("  • Multi-column responsive layout")
    print("  • Mixed element types (progress bars, tables, text)")
    print("  • Hierarchical information organization")
    print("  • Status-based styling")
    print()
    print("Try:")
    print("  • Press 'r' to refresh data")
    print("  • Watch metrics update")
    print("  • Monitor system status changes")
    print()
    print("Starting app...")
    print()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
