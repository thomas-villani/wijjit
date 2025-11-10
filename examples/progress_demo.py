"""Progress indicator demo showcasing all features.

This example demonstrates:
- Progress bars with multiple styles (filled, gradient, percentage, custom)
- Spinners with different animation styles
- State-driven updates
- Auto-refresh for animations
- Background thread simulating long-running tasks
"""

import threading
import time

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "download_progress": 0,
        "upload_progress": 0,
        "cpu_usage": 65,
        "loading": False,
        "processing": False,
        "status": "Ready",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing progress indicators."""
    return {
        "template": """
{% frame title="Progress Indicators Demo" border="double" width=90 height=40 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% vstack spacing=1 %}
      Instructions: Press buttons to start tasks | Press 'q' to quit | Spinners animate automatically
    {% endvstack %}

    {% vstack spacing=1 %}
      Download Progress (Filled Bar - Green):
      {% progressbar id="download_progress" value=state.download_progress max=100
                     width=70 style="filled" color="green" show_percentage=True %}
      {% endprogressbar %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Upload Progress (Gradient - Auto Color):
      {% progressbar id="upload_progress" value=state.upload_progress max=100
                     width=70 style="gradient" show_percentage=True %}
      {% endprogressbar %}
    {% endvstack %}

    {% vstack spacing=1 %}
      CPU Usage (Custom Characters):
      {% progressbar id="cpu_usage" value=state.cpu_usage max=100
                     width=70 style="custom" fill_char="=" empty_char=" "
                     color="cyan" show_percentage=True %}
      {% endprogressbar %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Percentage Only Style:
      {% progressbar id="download_progress" value=state.download_progress max=100
                     width=70 style="percentage" color="yellow" %}
      {% endprogressbar %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Loading Spinners:
    {% endvstack %}

    {% hstack spacing=3 %}
      {% spinner id="loading" active=state.loading style="dots"
                 label="Loading..." color="cyan" %}
      {% endspinner %}

      {% spinner id="processing" active=state.processing style="bouncing"
                 label="Processing" color="yellow" %}
      {% endspinner %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button id="start_download_btn" action="start_download" %}Start Download{% endbutton %}
      {% button id="start_upload_btn" action="start_upload" %}Start Upload{% endbutton %}
      {% button id="start_loading_btn" action="toggle_loading" %}Toggle Loading{% endbutton %}
      {% button id="start_processing_btn" action="toggle_processing" %}Toggle Processing{% endbutton %}
      {% button id="reset_btn" action="reset" %}Reset{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


def download_task():
    """Simulate a download task with progress updates."""
    app.state["download_progress"] = 0
    app.state["status"] = "Downloading..."

    for i in range(101):
        time.sleep(0.08)  # Simulate work (slower updates)
        app.state["download_progress"] = i

        # Only refresh UI every 10% to reduce flickering
        if i % 10 == 0 or i == 100:
            app.refresh()

    app.state["status"] = "Download complete!"
    app.refresh()


def upload_task():
    """Simulate an upload task with progress updates."""
    app.state["upload_progress"] = 0
    app.state["status"] = "Uploading..."

    for i in range(101):
        time.sleep(0.06)  # Simulate work (slower updates)
        app.state["upload_progress"] = i

        # Only refresh UI every 10% to reduce flickering
        if i % 10 == 0 or i == 100:
            app.refresh()

    app.state["status"] = "Upload complete!"
    app.refresh()


@app.on_action("start_download")
def handle_start_download(event):
    """Start download in background thread."""
    app.state["status"] = "Starting download..."
    thread = threading.Thread(target=download_task, daemon=True)
    thread.start()


@app.on_action("start_upload")
def handle_start_upload(event):
    """Start upload in background thread."""
    app.state["status"] = "Starting upload..."
    thread = threading.Thread(target=upload_task, daemon=True)
    thread.start()


@app.on_action("toggle_loading")
def handle_toggle_loading(event):
    """Toggle loading spinner."""
    app.state["loading"] = not app.state["loading"]

    # Enable auto-refresh when any spinner is active
    if app.state["loading"] or app.state["processing"]:
        app.refresh_interval = 0.2  # 200ms refresh - smooth but not too fast
    else:
        app.refresh_interval = None  # Disable auto-refresh

    app.state["status"] = f"Loading spinner: {'ON' if app.state['loading'] else 'OFF'}"


@app.on_action("toggle_processing")
def handle_toggle_processing(event):
    """Toggle processing spinner."""
    app.state["processing"] = not app.state["processing"]

    # Enable auto-refresh when any spinner is active
    if app.state["loading"] or app.state["processing"]:
        app.refresh_interval = 0.2  # 200ms refresh - smooth but not too fast
    else:
        app.refresh_interval = None  # Disable auto-refresh

    app.state["status"] = f"Processing spinner: {'ON' if app.state['processing'] else 'OFF'}"


@app.on_action("reset")
def handle_reset(event):
    """Reset all progress and spinners."""
    app.state["download_progress"] = 0
    app.state["upload_progress"] = 0
    app.state["loading"] = False
    app.state["processing"] = False
    app.refresh_interval = None  # Disable auto-refresh
    app.state["status"] = "Reset complete"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


if __name__ == "__main__":
    app.run()
