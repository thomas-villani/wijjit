"""Executor Demo - ThreadPoolExecutor Configuration.

This example demonstrates configuring the ThreadPoolExecutor for
running synchronous handlers without blocking the UI:
- app.configure() method
- Running sync handlers in executor
- Preventing UI blocking with long operations
- Thread pool configuration

Run with: python examples/advanced/executor_demo.py

Controls:
- Click buttons to test different execution modes
- q: Quit
"""

import time

from wijjit import Wijjit

# Create app
app = Wijjit(
    initial_state={
        "status": "Ready",
        "execution_mode": "Direct (blocking)",
        "operation_log": [],
        "operation_count": 0,
    }
)

# Configure app to use ThreadPoolExecutor for sync handlers
# This prevents blocking the UI during I/O operations
app.configure(
    run_sync_handlers_in_executor=True,
    executor_max_workers=4,  # 4 worker threads
)


def log_operation(operation, duration):
    """Log an operation to the history.

    Parameters
    ----------
    operation : str
        Description of the operation
    duration : float
        Duration in seconds
    """
    log = app.state.get("operation_log", [])
    log.append(f"{operation}: {duration:.2f}s")

    # Keep last 10 operations
    app.state["operation_log"] = log[-10:]
    app.state["operation_count"] = len(log)


@app.view("main", default=True)
def main_view():
    """Main executor demo view.

    Returns
    -------
    dict
        View configuration with template and data
    """
    operation_log_text = "\n".join(app.state.get("operation_log", [])[-8:])
    if not operation_log_text:
        operation_log_text = "No operations yet..."

    return {
        "template": """
{% frame title="ThreadPoolExecutor Demo" border="double" width=100 height=36 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Status: {{ state.status }}
      Execution Mode: {{ state.execution_mode }}
      Operations: {{ state.operation_count }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=48 %}
        {% frame title="Simulated Operations" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% vstack spacing=0 %}
              1. Short Operations (< 1s):
            {% endvstack %}
            {% hstack spacing=2 %}
              {% button action="quick_task" %}Quick Task{% endbutton %}
              {% button action="multi_quick" %}5 Quick Tasks{% endbutton %}
            {% endhstack %}

            {% vstack spacing=0 %}
              2. Medium Operations (1-2s):
            {% endvstack %}
            {% hstack spacing=2 %}
              {% button action="medium_task" %}Medium Task{% endbutton %}
              {% button action="multi_medium" %}3 Medium Tasks{% endbutton %}
            {% endhstack %}

            {% vstack spacing=0 %}
              3. Long Operations (2-3s):
            {% endvstack %}
            {% hstack spacing=2 %}
              {% button action="long_task" %}Long Task{% endbutton %}
              {% button action="multi_long" %}2 Long Tasks{% endbutton %}
            {% endhstack %}

            {% vstack spacing=0 %}
              4. Simulated I/O:
            {% endvstack %}
            {% hstack spacing=2 %}
              {% button action="file_io" %}File I/O{% endbutton %}
              {% button action="network_io" %}Network I/O{% endbutton %}
              {% button action="database_io" %}Database I/O{% endbutton %}
            {% endhstack %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=48 %}
        {% frame title="Operation Log" border="single" width="fill" height=20 %}
          {% vstack padding=1 %}
{{ operation_log_text }}
          {% endvstack %}
        {% endframe %}

        {% frame title="Executor Info" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Configuration:
            • run_sync_handlers_in_executor: True
            • executor_max_workers: 4 threads
            • Mode: Non-blocking execution

            Benefits:
            • UI remains responsive during I/O
            • Multiple operations run concurrently
            • Prevents event loop blocking
            • Better performance for I/O-bound tasks

            Note: Async handlers don't need executor
                  (they're already non-blocking)
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="clear_log" %}Clear Log{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Try clicking multiple buttons rapidly - UI stays responsive!
      Operations run in background thread pool.
      [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "operation_log_text": operation_log_text,
        },
    }


# Quick Tasks
@app.on_action("quick_task")
def handle_quick_task(event):
    """Quick task (< 1s) - runs in executor.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Running quick task..."
    start = time.time()

    # Simulate quick operation
    time.sleep(0.5)

    duration = time.time() - start
    log_operation("Quick Task", duration)
    app.state["status"] = "Quick task complete"


@app.on_action("multi_quick")
def handle_multi_quick(event):
    """Multiple quick tasks.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Running 5 quick tasks..."

    for i in range(5):
        start = time.time()
        time.sleep(0.3)
        duration = time.time() - start
        log_operation(f"Quick Task {i+1}/5", duration)

    app.state["status"] = "All quick tasks complete"


# Medium Tasks
@app.on_action("medium_task")
def handle_medium_task(event):
    """Medium task (1-2s) - runs in executor.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Running medium task..."
    start = time.time()

    # Simulate medium operation
    time.sleep(1.5)

    duration = time.time() - start
    log_operation("Medium Task", duration)
    app.state["status"] = "Medium task complete"


@app.on_action("multi_medium")
def handle_multi_medium(event):
    """Multiple medium tasks.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Running 3 medium tasks..."

    for i in range(3):
        start = time.time()
        time.sleep(1.2)
        duration = time.time() - start
        log_operation(f"Medium Task {i+1}/3", duration)

    app.state["status"] = "All medium tasks complete"


# Long Tasks
@app.on_action("long_task")
def handle_long_task(event):
    """Long task (2-3s) - runs in executor.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Running long task..."
    start = time.time()

    # Simulate long operation
    time.sleep(2.5)

    duration = time.time() - start
    log_operation("Long Task", duration)
    app.state["status"] = "Long task complete"


@app.on_action("multi_long")
def handle_multi_long(event):
    """Multiple long tasks.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Running 2 long tasks..."

    for i in range(2):
        start = time.time()
        time.sleep(2.0)
        duration = time.time() - start
        log_operation(f"Long Task {i+1}/2", duration)

    app.state["status"] = "All long tasks complete"


# Simulated I/O Operations
@app.on_action("file_io")
def handle_file_io(event):
    """Simulate file I/O operation.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Simulating file I/O..."
    start = time.time()

    # Simulate file reading/writing
    time.sleep(1.0)

    duration = time.time() - start
    log_operation("File I/O Operation", duration)
    app.state["status"] = "File I/O complete"


@app.on_action("network_io")
def handle_network_io(event):
    """Simulate network I/O operation.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Simulating network request..."
    start = time.time()

    # Simulate network request
    time.sleep(1.5)

    duration = time.time() - start
    log_operation("Network I/O Operation", duration)
    app.state["status"] = "Network request complete"


@app.on_action("database_io")
def handle_database_io(event):
    """Simulate database I/O operation.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["status"] = "Simulating database query..."
    start = time.time()

    # Simulate database query
    time.sleep(1.2)

    duration = time.time() - start
    log_operation("Database I/O Operation", duration)
    app.state["status"] = "Database query complete"


@app.on_action("clear_log")
def handle_clear_log(event):
    """Clear operation log.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["operation_log"] = []
    app.state["operation_count"] = 0
    app.state["status"] = "Log cleared"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.quit()


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
    print("ThreadPoolExecutor Demo")
    print("=" * 50)
    print()
    print("This demo shows how to configure ThreadPoolExecutor")
    print("to prevent UI blocking during synchronous operations.")
    print()
    print("Configuration:")
    print("  app.configure(")
    print("      run_sync_handlers_in_executor=True,")
    print("      executor_max_workers=4")
    print("  )")
    print()
    print("Benefits:")
    print("  • UI stays responsive during I/O operations")
    print("  • Multiple operations run concurrently")
    print("  • Prevents event loop blocking")
    print("  • Better performance for I/O-bound tasks")
    print()
    print("Try:")
    print("  • Click multiple buttons rapidly")
    print("  • Notice UI remains responsive")
    print("  • Operations run in background threads")
    print("  • Watch operation log update in real-time")
    print()
    print("Note: For truly async operations, use async/await instead.")
    print("      The executor is for synchronous code that does I/O.")
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
