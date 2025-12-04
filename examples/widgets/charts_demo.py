#!/usr/bin/env python3
"""Demo application showcasing all chart elements in Wijjit.

This demo displays examples of:
- Sparkline: Compact inline trend visualization
- BarChart: Horizontal bar chart
- ColumnChart: Vertical column chart
- LineChart: Line/area chart with braille rendering
- Gauge: Value indicator gauges
- HeatMap: 2D grid color intensity visualization

Press 'r' to refresh data, 'q' to quit.
"""

import random

from wijjit import Wijjit

app = Wijjit()

# Initialize state with sample data
app.state.update(
    {
        # Sparkline data - CPU history
        "cpu_history": [random.randint(20, 80) for _ in range(30)],
        # Bar chart data - Sales by category
        "sales_data": [
            {"label": "Electronics", "value": 4500},
            {"label": "Clothing", "value": 3200},
            {"label": "Food", "value": 2800},
            {"label": "Books", "value": 1500},
            {"label": "Sports", "value": 2100},
        ],
        # Column chart data - Monthly revenue
        "monthly_data": [
            ("Jan", 120),
            ("Feb", 150),
            ("Mar", 180),
            ("Apr", 160),
            ("May", 200),
            ("Jun", 220),
            ("Jul", 190),
            ("Aug", 210),
        ],
        # Line chart data - Trends
        "trend_data": [random.randint(50, 150) + i * 5 for i in range(20)],
        # Gauge values
        "cpu_usage": 65,
        "memory_usage": 78,
        "disk_usage": 45,
        # Heatmap data - Activity grid (7 days x 24 hours)
        "activity_grid": [
            [random.randint(0, 100) for _ in range(12)] for _ in range(5)
        ],
    }
)


@app.view("main", default=True)
def main_view():
    """Main view displaying all chart types."""
    return {
        "template": """
{% frame title="Wijjit Charts Demo" border="rounded" width="fill" height="fill" %}
  {% vstack spacing=1 %}

    {# Row 1: Sparklines and Gauges #}
    {% hstack spacing=2 %}
      {% frame title="Sparklines" border="single" width=38 height=10 %}
          CPU: {% sparkline id="cpu_spark" data=state.cpu_history width=20 style="line" show_current=true %}{% endsparkline %}
          Mem: {% sparkline id="mem_spark" data=state.cpu_history width=20 style="bar" %}{% endsparkline %}
          Net: {% sparkline id="net_spark" data=state.cpu_history width=20 style="dot" %}{% endsparkline %}
      {% endframe %}

      {% frame title="Gauges" border="single" width=38 height=10 %}
        {% vstack spacing=0 %}
          {% gauge id="cpu_gauge" value=state.cpu_usage max_value=100 width=35 label="CPU" unit="%" color="threshold" %}{% endgauge %}
          {% gauge id="mem_gauge" value=state.memory_usage max_value=100 width=35 label="Memory" unit="%" color="gradient" color_scale="heat" %}{% endgauge %}
          {% gauge id="disk_gauge" value=state.disk_usage max_value=100 width=35 label="Disk" unit="%" %}{% endgauge %}
        {% endvstack %}
      {% endframe %}
    {% endhstack %}

    {# Row 2: Bar Chart and Column Chart #}
    {% hstack spacing=2 %}
      {% frame title="Sales by Category (Bar)" border="single" width=38 height=10 %}
        {% barchart id="sales_bar" data=state.sales_data width=34 height=6
           show_labels=true show_values=true color="gradient" color_scale="green" %}
        {% endbarchart %}
      {% endframe %}

      {% frame title="Monthly Revenue (Column)" border="single" width=38 height=10 %}
        {% columnchart id="monthly_col" data=state.monthly_data width=34 height=6
           column_width=2 spacing=1 show_axis=true color="threshold" %}
        {% endcolumnchart %}
      {% endframe %}
    {% endhstack %}

    {# Row 3: Line Chart and HeatMap #}
    {% hstack spacing=2 %}
      {% frame title="Trend (Line Chart)" border="single" width=38 height=10 %}
        {% linechart id="trend_line" data=state.trend_data width=34 height=6
           style="line" show_axis=true show_labels=false %}
        {% endlinechart %}
      {% endframe %}

      {% frame title="Activity HeatMap" border="single" width=38 height=10 %}
        {% heatmap id="activity_heat" data=state.activity_grid width=34 height=6
           cell_width=2 color_scale="heat" show_legend=true %}
        {% endheatmap %}
      {% endframe %}
    {% endhstack %}

    {# Status line #}
    Press 'r' to refresh data, 'q' to quit

  {% endvstack %}
{% endframe %}
""",
        "data": {"state": app.state},
    }


@app.on_key("r")
def refresh_data(event):
    """Refresh all chart data with new random values."""
    app.state["cpu_history"] = [random.randint(20, 80) for _ in range(30)]
    app.state["trend_data"] = [random.randint(50, 150) + i * 5 for i in range(20)]
    app.state["cpu_usage"] = random.randint(30, 95)
    app.state["memory_usage"] = random.randint(40, 90)
    app.state["disk_usage"] = random.randint(20, 70)
    app.state["activity_grid"] = [
        [random.randint(0, 100) for _ in range(12)] for _ in range(5)
    ]

    # Update sales data - create new list to trigger change detection
    app.state["sales_data"] = [
        {"label": item["label"], "value": int(item["value"] * random.uniform(0.9, 1.1))}
        for item in app.state["sales_data"]
    ]

    # Update monthly data with new random values
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    app.state["monthly_data"] = [(month, random.randint(100, 250)) for month in months]


@app.on_key("q")
def quit_app(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    app.run()
