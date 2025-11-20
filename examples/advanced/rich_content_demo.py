"""Rich Content Demo - Combined Markdown and Code Display.

This example demonstrates displaying rich content using both Markdown
and CodeBlock elements together in a single application, simulating
a documentation viewer or API reference.

Features:
- Side-by-side markdown documentation and code examples
- Template-based UI with {% markdown %} and {% code %} tags
- Tab navigation between multiple examples
- Demonstrates typical use case: docs + implementation

Run with: python examples/advanced/rich_content_demo.py

Controls:
- 1/2/3: Switch between example pages
- q: Quit
"""

from wijjit import Wijjit

# API Documentation examples
DOCS_PAGE_1 = """# Quick Start Guide

## Installation

```bash
pip install wijjit
```

## Your First App

Creating a Wijjit app is simple:

1. Import the Wijjit class
2. Create an app instance
3. Define a view with `@app.view()`
4. Run the app with `app.run()`

The code example on the right shows
a minimal "Hello World" application."""

CODE_PAGE_1 = '''"""Hello World Example"""

from wijjit import Wijjit

# Create app
app = Wijjit()

@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame title="Hello" border="double" %}
  {% vstack padding=2 %}
    Hello, World!

    {% button action="quit" %}
      Quit
    {% endbutton %}
  {% endvstack %}
{% endframe %}
        """,
    }

@app.on_action("quit")
def handle_quit(event):
    app.quit()

@app.on_key("q")
def on_quit(event):
    app.quit()

if __name__ == "__main__":
    app.run()
'''

DOCS_PAGE_2 = """# State Management

## Reactive State

Wijjit provides reactive state
management that automatically
triggers re-renders when state
changes.

## Usage

Access state via `app.state`:

```python
# Read state
value = app.state["counter"]

# Write state (triggers re-render)
app.state["counter"] = value + 1
```

## Initial State

Set initial state when creating
the app:

```python
app = Wijjit(initial_state={
    "counter": 0,
    "name": "Alice"
})
```"""

CODE_PAGE_2 = '''"""Counter Example with State"""

from wijjit import Wijjit

app = Wijjit(
    initial_state={"counter": 0}
)

@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame title="Counter" border="double" %}
  {% vstack spacing=1 padding=2 %}
    Counter: {{ state.counter }}

    {% hstack spacing=2 %}
      {% button action="increment" %}
        Increment
      {% endbutton %}

      {% button action="decrement" %}
        Decrement
      {% endbutton %}

      {% button action="reset" %}
        Reset
      {% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
    }

@app.on_action("increment")
def handle_increment(event):
    app.state["counter"] += 1

@app.on_action("decrement")
def handle_decrement(event):
    app.state["counter"] -= 1

@app.on_action("reset")
def handle_reset(event):
    app.state["counter"] = 0

if __name__ == "__main__":
    app.run()
'''

DOCS_PAGE_3 = """# Event Handling

## Action Handlers

Use `@app.on_action()` to handle
button clicks and form submissions:

```python
@app.on_action("submit")
def handle_submit(event):
    # Process form data
    pass
```

## Keyboard Handlers

Use `@app.on_key()` for keyboard
shortcuts:

```python
@app.on_key("q")
def on_quit(event):
    app.quit()
```

## Event Types

- **ActionEvent**: Button clicks
- **KeyEvent**: Keyboard input
- **ChangeEvent**: Input changes
- **FocusEvent**: Focus changes
- **MouseEvent**: Mouse interaction"""

CODE_PAGE_3 = '''"""Event Handling Example"""

from wijjit import Wijjit

app = Wijjit(initial_state={
    "message": "",
    "input_text": "",
})

@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame title="Events" border="double" %}
  {% vstack spacing=1 padding=2 %}
    {% vstack spacing=0 %}
      {{ state.message }}
    {% endvstack %}

    {% textinput
        id="input_text"
        placeholder="Type here..."
        width=40
    %}{% endtextinput %}

    {% hstack spacing=2 %}
      {% button action="greet" %}
        Say Hello
      {% endbutton %}

      {% button action="clear" %}
        Clear
      {% endbutton %}
    {% endhstack %}

    Shortcuts: [Ctrl+G] Greet
  {% endvstack %}
{% endframe %}
        """,
    }

@app.on_action("greet")
def handle_greet(event):
    text = app.state.get("input_text", "")
    if text:
        msg = f"Hello, {text}!"
    else:
        msg = "Hello, World!"
    app.state["message"] = msg

@app.on_action("clear")
def handle_clear(event):
    app.state["message"] = ""
    app.state["input_text"] = ""

@app.on_key("ctrl+g")
def on_ctrl_g(event):
    handle_greet(event)

if __name__ == "__main__":
    app.run()
'''

# Create app with page state
app = Wijjit(
    initial_state={
        "current_page": 1,
    }
)


def get_current_content():
    """Get documentation and code for current page.

    Returns
    -------
    tuple
        (docs_text, code_text) for current page
    """
    page = app.state.get("current_page", 1)

    if page == 1:
        return DOCS_PAGE_1, CODE_PAGE_1
    elif page == 2:
        return DOCS_PAGE_2, CODE_PAGE_2
    else:
        return DOCS_PAGE_3, CODE_PAGE_3


@app.view("main", default=True)
def main_view():
    """Main view with side-by-side documentation and code.

    Returns
    -------
    dict
        View configuration with template and data
    """
    docs, code = get_current_content()
    page = app.state.get("current_page", 1)

    return {
        "template": """
{% frame title="Rich Content Demo - Docs + Code" border="double" width=120 height=35 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      Page {{ page }}/3: {{ page_title }}
    {% endvstack %}

    {% hstack spacing=2 align_v="top" %}
      {% vstack width=55 %}
        {% frame title="Documentation" border="single" height=25 scrollable=true %}
          {% markdown content=docs_content %}{% endmarkdown %}
        {% endframe %}
      {% endvstack %}

      {% vstack width=60 %}
        {% frame title="Implementation" border="single" height=25 scrollable=true %}
          {% code language="python" content=code_content show_line_numbers=true %}{% endcode %}
        {% endframe %}
      {% endvstack %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% button action="page_1" %}Page 1: Quick Start{% endbutton %}
      {% button action="page_2" %}Page 2: State{% endbutton %}
      {% button action="page_3" %}Page 3: Events{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Controls: [1/2/3] Switch page | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {
            "page": page,
            "page_title": ["Quick Start", "State Management", "Event Handling"][page - 1],
            "docs_content": docs,
            "code_content": code,
        },
    }


# Action handlers for page navigation
@app.on_action("page_1")
def handle_page_1(event):
    """Navigate to page 1.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["current_page"] = 1


@app.on_action("page_2")
def handle_page_2(event):
    """Navigate to page 2.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["current_page"] = 2


@app.on_action("page_3")
def handle_page_3(event):
    """Navigate to page 3.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.state["current_page"] = 3


@app.on_action("quit")
def handle_quit(event):
    """Handle quit button.

    Parameters
    ----------
    event : ActionEvent
        The action event
    """
    app.quit()


# Keyboard shortcuts for page navigation
@app.on_key("1")
def on_key_1(event):
    """Navigate to page 1 via '1' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.state["current_page"] = 1


@app.on_key("2")
def on_key_2(event):
    """Navigate to page 2 via '2' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.state["current_page"] = 2


@app.on_key("3")
def on_key_3(event):
    """Navigate to page 3 via '3' key.

    Parameters
    ----------
    event : KeyEvent
        The key event
    """
    app.state["current_page"] = 3


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
    print("Rich Content Demo")
    print("=" * 50)
    print()
    print("This demo shows side-by-side documentation and code")
    print("using Markdown and CodeBlock display elements.")
    print()
    print("Features:")
    print("- Multiple pages of content")
    print("- Markdown rendering with syntax highlighting")
    print("- Code display with line numbers")
    print("- Template-based layout")
    print()
    print("Controls:")
    print("  [1/2/3] Switch between pages")
    print("  [q] Quit")
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
