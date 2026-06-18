"""Download simulator demo - realistic use case.

This example demonstrates a realistic download scenario with:
- Progress bar showing download percentage
- Spinner indicating active download
- File size and speed information
- Background thread for download simulation
"""

import random
import threading
import time

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "progress": 0,
        "downloading": False,
        "filename": "large_file.zip",
        "total_size_mb": 250,
        "downloaded_mb": 0,
        "speed_mbps": 0,
        "status": "Ready to download",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view - download interface."""
    return {
        "template": """
{% frame title="File Download Manager" border="rounded" width=80 height=25 %}
  {% vstack spacing=1 padding=2 %}
    {% vstack spacing=0 %}
      File: {{ state.filename }}
      Size: {{ state.total_size_mb }} MB
    {% endvstack %}

    {% vstack spacing=1 %}
      Status: {{ state.status }}
    {% endvstack %}

    {% vstack spacing=1 %}
      {% if state.downloading %}
        {% spinner id="downloading" active=True style="dots"
                   label="Downloading..." color="cyan" %}
        {% endspinner %}
      {% endif %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Progress:
      {% progressbar id="progress" value=state.progress max=100
                     width=65 style="gradient" show_percentage=True %}
      {% endprogressbar %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Downloaded: {{ "%.1f" | format(state.downloaded_mb) }} MB / {{ state.total_size_mb }} MB
      {% if state.downloading %}
      Speed: {{ "%.2f" | format(state.speed_mbps) }} MB/s
      {% endif %}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% if not state.downloading %}
        {% button id="start_btn" action="start_download" %}Start Download{% endbutton %}
      {% else %}
        {% button id="cancel_btn" action="cancel_download" %}Cancel{% endbutton %}
      {% endif %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


# Control flag for canceling download
download_active = {"value": False}


def download_simulation():
    """Simulate file download with variable speed."""
    app.state["progress"] = 0
    app.state["downloaded_mb"] = 0
    app.state["downloading"] = True
    app.state["status"] = "Connecting to server..."
    app.refresh_interval = 0.2  # Enable spinner animation (200ms)
    app.refresh()

    time.sleep(1)  # Simulate connection time

    app.state["status"] = "Downloading..."

    total_size = app.state["total_size_mb"]
    chunk_size = 10  # MB per iteration (larger chunks = fewer updates)
    downloaded = 0
    update_counter = 0

    while downloaded < total_size and download_active["value"]:
        # Simulate variable download speed
        time.sleep(0.3)  # Slower simulation for smoother updates
        speed = random.uniform(8, 15)  # Random speed 8-15 MB/s
        actual_chunk = min(chunk_size, total_size - downloaded)
        downloaded += actual_chunk

        # Update state
        app.state["downloaded_mb"] = downloaded
        app.state["progress"] = (downloaded / total_size) * 100
        app.state["speed_mbps"] = speed

        # Only refresh every 2nd update to reduce flickering
        update_counter += 1
        if update_counter % 2 == 0 or downloaded >= total_size:
            app.refresh()

    # Download complete or canceled
    if download_active["value"]:
        app.state["status"] = "Download complete!"
        app.state["progress"] = 100
    else:
        app.state["status"] = "Download canceled"

    app.state["downloading"] = False
    app.state["speed_mbps"] = 0
    app.refresh_interval = None  # Disable spinner animation
    download_active["value"] = False
    app.refresh()


@app.on_action("start_download")
def handle_start_download(event):
    """Start download in background thread."""
    if not download_active["value"]:
        download_active["value"] = True
        thread = threading.Thread(target=download_simulation, daemon=True)
        thread.start()


@app.on_action("cancel_download")
def handle_cancel_download(event):
    """Cancel active download."""
    download_active["value"] = False
    app.state["status"] = "Canceling download..."


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    download_active["value"] = False  # Stop any active download
    app.quit()


if __name__ == "__main__":
    app.run()
