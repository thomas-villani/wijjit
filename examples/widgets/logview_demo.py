"""LogView demo showcasing all features.

This example demonstrates:
- Automatic log level detection and coloring
- Auto-scroll functionality
- Soft-wrap for long lines
- Line numbers display
- Manual scrolling
- Performance with many log lines
- Simulated log streaming
- ANSI passthrough
"""

import random
from datetime import datetime

from wijjit import Wijjit
from wijjit.terminal.ansi import ANSIColor, ANSIStyle

# Sample log messages for different levels
ERROR_MESSAGES = [
    "ERROR: Connection to database failed",
    "FATAL: Unable to allocate memory",
    "CRITICAL: Disk space exhausted",
    "ERROR: Authentication failed for user admin",
    "ERROR: Timeout waiting for response",
]

WARNING_MESSAGES = [
    "WARNING: High memory usage detected (85%)",
    "WARN: Slow query detected (2.3s)",
    "WARNING: Cache miss rate above threshold",
    "WARN: Connection pool nearly exhausted",
    "WARNING: Deprecated API usage detected",
]

INFO_MESSAGES = [
    "INFO: Application started successfully",
    "INFO: Processing batch job 12345",
    "INFO: User logged in: john.doe",
    "INFO: Configuration reloaded",
    "INFO: Health check passed",
]

DEBUG_MESSAGES = [
    "DEBUG: Entering function process_request()",
    "DEBUG: Variable state: {active: true, count: 42}",
    "DEBUG: Cache hit for key: user_profile_123",
    "DEBUG: SQL query executed in 15ms",
    "DEBUG: Response body size: 2.3 KB",
]

TRACE_MESSAGES = [
    "TRACE: Method entry: calculateTotal()",
    "TRACE: Loop iteration 5 of 100",
    "TRACE: Conditional branch taken: if(x > 0)",
    "TRACE: Object created: RequestContext@0x7f8b",
    "TRACE: Method exit: calculateTotal() returned 142.50",
]

# Initial logs with various levels
initial_logs = [
    "INFO: Server starting on port 8080",
    "INFO: Loading configuration from config.yaml",
    "DEBUG: Database connection pool initialized (size: 10)",
    "INFO: Starting HTTP listener",
    "INFO: Application ready to accept connections",
    "",
    "INFO: Received request GET /api/users",
    "DEBUG: Query executed: SELECT * FROM users LIMIT 10",
    "INFO: Request completed in 23ms",
    "",
    "WARNING: Request queue building up (15 pending)",
    "INFO: Scaling up worker pool to 20 threads",
    "INFO: Queue cleared",
    "",
    "ERROR: Connection lost to cache server",
    "WARNING: Falling back to local cache",
    "INFO: Cache server reconnected",
]

# Initial logs with ANSI codes (for passthrough demo)
ansi_logs = [
    f"{ANSIColor.GREEN}Custom colored message{ANSIStyle.RESET}",
    f"{ANSIStyle.BOLD}Bold message{ANSIStyle.RESET}",
    f"{ANSIColor.MAGENTA}Magenta text{ANSIStyle.RESET}",
    "Regular text mixed with custom colors",
]

# Long lines for soft-wrap demo
long_logs = [
    "INFO: This is a very long log line that will demonstrate the soft-wrap feature when enabled. It should wrap to multiple lines instead of being clipped.",
    "ERROR: " + "A" * 150,
    "DEBUG: Long JSON payload: " + "{'key': 'value', " * 20 + "}",
]

# Create app with initial state
app = Wijjit(
    initial_state={
        "main_logs": initial_logs.copy(),
        "stream_logs": ["INFO: Log streaming demo - click 'Add Log' to simulate"],
        "ansi_logs": ansi_logs.copy(),
        "long_logs": long_logs.copy(),
        "line_numbers_enabled": False,
        "soft_wrap_enabled": False,
        "auto_scroll_enabled": True,
        "log_counter": 0,
        "status": "Ready. Click buttons or scroll with arrow keys.",
    }
)


@app.view("main", default=True)
def main_view():
    """Main view showcasing LogView elements."""
    return {
        "template": """
{% frame title="LogView Demo - Log Display with Auto-Coloring" border="double" width=120 height=28 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% vstack spacing=1 %}
        {% logview id="main_logs"
                   lines=state.main_logs
                   auto_scroll=true
                   soft_wrap=false
                   show_line_numbers=false
                   detect_log_levels=true
                   width=55
                   height=8
                   border_style="single"
                   title="Main Logs (Auto-Scroll)"
                   show_scrollbar=true %}
        {% endlogview %}

        {% logview id="stream_logs"
                   lines=state.stream_logs
                   auto_scroll=state.auto_scroll_enabled
                   soft_wrap=state.soft_wrap_enabled
                   show_line_numbers=state.line_numbers_enabled
                   detect_log_levels=true
                   width=55
                   height=8
                   border_style="rounded"
                   title="Streaming Logs"
                   show_scrollbar=true %}
        {% endlogview %}
      {% endvstack %}

      {% vstack spacing=1 %}
        {% logview id="ansi_logs"
                   lines=state.ansi_logs
                   auto_scroll=false
                   detect_log_levels=false
                   width=55
                   height=8
                   border_style="single"
                   title="ANSI Passthrough (No Level Detection)"
                   show_scrollbar=true %}
        {% endlogview %}

        {% logview id="long_logs"
                   lines=state.long_logs
                   auto_scroll=false
                   soft_wrap=true
                   show_line_numbers=false
                   detect_log_levels=true
                   width=55
                   height=8
                   border_style="double"
                   title="Long Lines (Soft-Wrap Enabled)"
                   show_scrollbar=true %}
        {% endlogview %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button id="add_log_btn" action="add_log" %}Add Log{% endbutton %}
      {% button id="add_error_btn" action="add_error" %}Add ERROR{% endbutton %}
      {% button id="add_warning_btn" action="add_warning" %}Add WARNING{% endbutton %}
      {% button id="add_many_btn" action="add_many" %}Add 50 Logs{% endbutton %}
      {% button id="clear_stream_btn" action="clear_stream" %}Clear Stream{% endbutton %}
      {% button id="toggle_wrap_btn" action="toggle_wrap" %}Toggle Wrap{% endbutton %}
      {% button id="toggle_numbers_btn" action="toggle_numbers" %}Toggle Line #{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("add_log")
def handle_add_log(event):
    """Add a random log message."""
    # Pick random log level and message
    level_choice = random.choice(["INFO", "DEBUG", "TRACE"])

    if level_choice == "INFO":
        message = random.choice(INFO_MESSAGES)
    elif level_choice == "DEBUG":
        message = random.choice(DEBUG_MESSAGES)
    else:
        message = random.choice(TRACE_MESSAGES)

    # Add to stream logs
    current_logs = app.state.get("stream_logs", [])
    timestamp = datetime.now().strftime("%H:%M:%S")
    current_logs.append(f"[{timestamp}] {message}")
    app.state["stream_logs"] = current_logs

    # Update counter
    app.state["log_counter"] = app.state.get("log_counter", 0) + 1
    app.state["status"] = f"Added log. Total: {app.state['log_counter']} logs"


@app.on_action("add_error")
def handle_add_error(event):
    """Add an ERROR log message."""
    message = random.choice(ERROR_MESSAGES)

    current_logs = app.state.get("stream_logs", [])
    timestamp = datetime.now().strftime("%H:%M:%S")
    current_logs.append(f"[{timestamp}] {message}")
    app.state["stream_logs"] = current_logs

    app.state["log_counter"] = app.state.get("log_counter", 0) + 1
    app.state["status"] = f"Added ERROR. Total: {app.state['log_counter']} logs"


@app.on_action("add_warning")
def handle_add_warning(event):
    """Add a WARNING log message."""
    message = random.choice(WARNING_MESSAGES)

    current_logs = app.state.get("stream_logs", [])
    timestamp = datetime.now().strftime("%H:%M:%S")
    current_logs.append(f"[{timestamp}] {message}")
    app.state["stream_logs"] = current_logs

    app.state["log_counter"] = app.state.get("log_counter", 0) + 1
    app.state["status"] = f"Added WARNING. Total: {app.state['log_counter']} logs"


@app.on_action("add_many")
def handle_add_many(event):
    """Add many logs at once to test performance."""
    current_logs = app.state.get("stream_logs", [])

    all_messages = (
        ERROR_MESSAGES
        + WARNING_MESSAGES
        + INFO_MESSAGES
        + DEBUG_MESSAGES
        + TRACE_MESSAGES
    )

    for i in range(50):
        message = random.choice(all_messages)
        timestamp = datetime.now().strftime("%H:%M:%S")
        current_logs.append(f"[{timestamp}] {message}")

    app.state["stream_logs"] = current_logs
    app.state["log_counter"] = app.state.get("log_counter", 0) + 50
    app.state["status"] = f"Added 50 logs. Total: {app.state['log_counter']} logs"


@app.on_action("clear_stream")
def handle_clear_stream(event):
    """Clear the streaming logs."""
    app.state["stream_logs"] = ["INFO: Logs cleared"]
    app.state["log_counter"] = 0
    app.state["status"] = "Streaming logs cleared"


@app.on_action("toggle_wrap")
def handle_toggle_wrap(event):
    """Toggle soft-wrap in streaming logs."""
    current = app.state.get("soft_wrap_enabled", False)
    app.state["soft_wrap_enabled"] = not current
    app.state["status"] = f"Soft-wrap: {'ON' if not current else 'OFF'}"


@app.on_action("toggle_numbers")
def handle_toggle_numbers(event):
    """Toggle line numbers in streaming logs."""
    current = app.state.get("line_numbers_enabled", False)
    app.state["line_numbers_enabled"] = not current
    app.state["status"] = f"Line numbers: {'ON' if not current else 'OFF'}"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


@app.on_key("q")
def handle_key_q(event):
    """Handle 'q' key to quit."""
    app.quit()


if __name__ == "__main__":
    print("LogView Demo")
    print("=" * 50)
    print("Features:")
    print("- Automatic log level detection and coloring")
    print("- Auto-scroll (scroll to bottom automatically)")
    print("- Soft-wrap for long lines")
    print("- Line numbers")
    print("- ANSI passthrough (preserves colors)")
    print("- High performance with many logs")
    print()
    print("Controls:")
    print("- Click buttons to add logs and toggle features")
    print("- Use arrow keys, Page Up/Down, Home/End to scroll")
    print("- Use Tab to switch focus between log views")
    print("- Press 'q' or click Quit to exit")
    print()
    print("Log Views:")
    print("- Top Left: Main Logs (auto-scroll enabled)")
    print("- Bottom Left: Streaming Logs (toggleable features)")
    print("- Top Right: ANSI Passthrough (custom colors)")
    print("- Bottom Right: Long Lines (soft-wrap demo)")
    print("=" * 50)
    print()

    # Run the app
    app.run()
