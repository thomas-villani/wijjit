"""Error Handling Demo - Error Management Patterns.

This example demonstrates error handling and graceful degradation:
- Try/except in event handlers
- Error state management and display
- User-friendly error messages
- Recovery from errors
- Validation and error prevention

Run with: python examples/advanced/error_handling_demo.py

Controls:
- Click buttons to trigger various error scenarios
- q: Quit
"""

import asyncio
from datetime import datetime

from wijjit import Wijjit

# Create app with error tracking state
app = Wijjit(
    initial_state={
        "last_action": "None",
        "error_message": "",
        "error_count": 0,
        "error_history": [],
        "divide_a": "10",
        "divide_b": "2",
        "divide_result": "",
        "json_input": '{"name": "Alice"}',
        "json_result": "",
        "file_path": "",
        "file_content": "",
    }
)


def log_error(action, error_msg):
    """Log an error to history.

    Parameters
    ----------
    action : str
        The action that caused the error
    error_msg : str
        The error message
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {action}: {error_msg}"

    history = app.state.get("error_history", [])
    history.append(entry)

    # Keep last 10 errors
    app.state["error_history"] = history[-10:]
    app.state["error_count"] = len(history)


@app.view("main", default=True)
def main_view():
    """Main error handling demo view.

    Returns
    -------
    dict
        View configuration with template and data
    """
    error_history_text = "\n".join(app.state.get("error_history", [])[-5:])
    if not error_history_text:
        error_history_text = "No errors yet"

    return {
        "template": """
{% frame title="Error Handling Demo" border="double" width=100 height=40 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Last Action: {{ state.last_action }}
      Total Errors: {{ state.error_count }}
    {% endvstack %}

    {% if state.error_message %}
      {% frame border="single" %}
        {% vstack spacing=0 padding=1 %}
          ERROR: {{ state.error_message }}
        {% endvstack %}
      {% endframe %}
    {% endif %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack spacing=1 width=48 %}
        {% frame title="Error Scenarios" border="single" width="fill" %}
          {% vstack spacing=1 padding=1 %}
            {% vstack spacing=0 %}
              1. Division by Zero:
            {% endvstack %}
            {% hstack spacing=2 %}
              {% textinput id="divide_a" width=10 placeholder="10" %}{% endtextinput %}
              ÷
              {% textinput id="divide_b" width=10 placeholder="2" %}{% endtextinput %}
              {% button action="divide" %}Calculate{% endbutton %}
            {% endhstack %}
            {% vstack spacing=0 %}
              Result: {{ state.divide_result }}
            {% endvstack %}

            {% vstack spacing=0 %}
              2. JSON Parsing:
            {% endvstack %}
            {% textinput id="json_input" width=40 placeholder='{"key": "value"}' %}{% endtextinput %}
            {% button action="parse_json" %}Parse JSON{% endbutton %}
            {% vstack spacing=0 %}
              Result: {{ state.json_result }}
            {% endvstack %}

            {% vstack spacing=0 %}
              3. File Operations:
            {% endvstack %}
            {% textinput id="file_path" width=40 placeholder="/path/to/file.txt" %}{% endtextinput %}
            {% button action="read_file" %}Read File{% endbutton %}
            {% vstack spacing=0 %}
              {{ state.file_content | truncate(50) }}
            {% endvstack %}

            {% vstack spacing=0 %}
              4. Simulated Errors:
            {% endvstack %}
            {% hstack spacing=2 %}
              {% button action="null_error" %}Null Reference{% endbutton %}
              {% button action="type_error" %}Type Error{% endbutton %}
              {% button action="async_error" %}Async Error{% endbutton %}
            {% endhstack %}
          {% endvstack %}
        {% endframe %}
      {% endvstack %}

      {% vstack spacing=1 width=48 %}
        {% frame title="Error History (Last 5)" border="single" width="fill" height=22 %}
          {% vstack padding=1 %}
{{ error_history_text }}
          {% endvstack %}
        {% endframe %}

        {% frame title="Error Handling Patterns" border="single" width="fill" %}
          {% vstack spacing=0 padding=1 %}
            Demonstrated Patterns:
            • Try/except in action handlers
            • User-friendly error messages
            • Error state management
            • Error history/logging
            • Input validation
            • Graceful degradation
            • Recovery mechanisms
          {% endvstack %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="clear_errors" %}Clear Errors{% endbutton %}
      {% button action="clear_history" %}Clear History{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Try the error scenarios above to see error handling in action!
      [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "error_history_text": error_history_text,
        },
    }


@app.on_action("divide")
def handle_divide(event):
    """Handle division with error handling.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_action"] = "Division"

    try:
        a = float(app.state.get("divide_a", "0"))
        b = float(app.state.get("divide_b", "0"))

        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")

        result = a / b
        app.state["divide_result"] = f"{a} ÷ {b} = {result}"
        app.state["error_message"] = ""

    except ValueError as e:
        error_msg = "Invalid number format"
        app.state["error_message"] = error_msg
        app.state["divide_result"] = "Error"
        log_error("Division", error_msg)

    except ZeroDivisionError as e:
        error_msg = str(e)
        app.state["error_message"] = error_msg
        app.state["divide_result"] = "Error"
        log_error("Division", error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}"
        app.state["error_message"] = error_msg
        app.state["divide_result"] = "Error"
        log_error("Division", error_msg)


@app.on_action("parse_json")
def handle_parse_json(event):
    """Handle JSON parsing with error handling.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    import json

    app.state["last_action"] = "JSON Parsing"

    try:
        json_str = app.state.get("json_input", "")
        if not json_str.strip():
            raise ValueError("JSON input is empty")

        data = json.loads(json_str)
        app.state["json_result"] = f"Parsed: {type(data).__name__} with {len(data)} keys"
        app.state["error_message"] = ""

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON: {e.msg} at position {e.pos}"
        app.state["error_message"] = error_msg
        app.state["json_result"] = "Error"
        log_error("JSON Parsing", error_msg)

    except ValueError as e:
        error_msg = str(e)
        app.state["error_message"] = error_msg
        app.state["json_result"] = "Error"
        log_error("JSON Parsing", error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}"
        app.state["error_message"] = error_msg
        app.state["json_result"] = "Error"
        log_error("JSON Parsing", error_msg)


@app.on_action("read_file")
def handle_read_file(event):
    """Handle file reading with error handling.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_action"] = "File Reading"

    try:
        file_path = app.state.get("file_path", "")
        if not file_path.strip():
            raise ValueError("File path is empty")

        # Attempt to read file
        with open(file_path, "r") as f:
            content = f.read(100)  # Read first 100 chars

        app.state["file_content"] = f"Read {len(content)} characters"
        app.state["error_message"] = ""

    except FileNotFoundError as e:
        error_msg = f"File not found: {file_path}"
        app.state["error_message"] = error_msg
        app.state["file_content"] = ""
        log_error("File Reading", error_msg)

    except PermissionError as e:
        error_msg = f"Permission denied: {file_path}"
        app.state["error_message"] = error_msg
        app.state["file_content"] = ""
        log_error("File Reading", error_msg)

    except ValueError as e:
        error_msg = str(e)
        app.state["error_message"] = error_msg
        app.state["file_content"] = ""
        log_error("File Reading", error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
        app.state["error_message"] = error_msg
        app.state["file_content"] = ""
        log_error("File Reading", error_msg)


@app.on_action("null_error")
def handle_null_error(event):
    """Simulate null reference error.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_action"] = "Null Reference"

    try:
        data = None
        # This will raise AttributeError
        result = data.some_method()

    except AttributeError as e:
        error_msg = "Attempted to access attribute on None object"
        app.state["error_message"] = error_msg
        log_error("Null Reference", error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}"
        app.state["error_message"] = error_msg
        log_error("Null Reference", error_msg)


@app.on_action("type_error")
def handle_type_error(event):
    """Simulate type error.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_action"] = "Type Error"

    try:
        # This will raise TypeError
        result = "string" + 123

    except TypeError as e:
        error_msg = "Cannot concatenate string and integer"
        app.state["error_message"] = error_msg
        log_error("Type Error", error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}"
        app.state["error_message"] = error_msg
        log_error("Type Error", error_msg)


@app.on_action("async_error")
async def handle_async_error(event):
    """Simulate async error.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["last_action"] = "Async Error"

    try:
        # Simulate async operation
        await asyncio.sleep(0.1)

        # This will raise an error
        raise RuntimeError("Simulated async operation failed")

    except RuntimeError as e:
        error_msg = str(e)
        app.state["error_message"] = error_msg
        log_error("Async Error", error_msg)

    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}"
        app.state["error_message"] = error_msg
        log_error("Async Error", error_msg)


@app.on_action("clear_errors")
def handle_clear_errors(event):
    """Clear current error message.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["error_message"] = ""
    app.state["last_action"] = "Cleared errors"


@app.on_action("clear_history")
def handle_clear_history(event):
    """Clear error history.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["error_history"] = []
    app.state["error_count"] = 0
    app.state["last_action"] = "Cleared history"


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
    print("Error Handling Demo")
    print("=" * 50)
    print()
    print("This demo shows error handling best practices:")
    print()
    print("Patterns Demonstrated:")
    print("  • Try/except blocks in event handlers")
    print("  • Specific exception handling (ValueError, TypeError, etc.)")
    print("  • User-friendly error messages")
    print("  • Error state management and display")
    print("  • Error history/logging")
    print("  • Input validation and prevention")
    print("  • Graceful degradation")
    print()
    print("Try the error scenarios:")
    print("  1. Enter 0 for division denominator")
    print("  2. Enter invalid JSON (missing quotes, etc.)")
    print("  3. Enter non-existent file path")
    print("  4. Click simulated error buttons")
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
