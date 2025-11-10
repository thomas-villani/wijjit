"""Rich Content Template Demo - Using Jinja2 Template Tags.

This example demonstrates using the {% markdown %} and {% code %} template tags
for declarative UI definition, rather than creating elements programmatically.

Features:
- Declarative markdown and code display using Jinja2 templates
- State-driven content updates
- Automatic scroll position persistence
- Focus management with Tab key
- Template-based layout

Run with: python examples/rich_content_template_demo.py

Controls:
- Tab: Switch focus between documentation and code
- Arrow keys: Scroll focused panel
- Page Up/Down: Scroll by page
- 1-3: Switch between different code examples
- q: Quit
"""

from wijjit import EventType, HandlerScope, Wijjit

# Sample documentation
API_DOCS = """# Wijjit Template Tags

## Markdown Tag

The `{% markdown %}` tag renders markdown content with Rich formatting:

```jinja2
{% markdown content=state.docs width=60 height=20
            border="double" title="Documentation" %}
{% endmarkdown %}
```

**Features:**
- Full markdown syntax support
- Code blocks with syntax highlighting
- Tables, lists, and emphasis
- Automatic scrolling for long content
- State binding for dynamic updates

## Code Tag

The `{% code %}` tag displays syntax-highlighted code:

```jinja2
{% code language="python" width=60 height=15
        line_numbers=true border="single" %}
{{ state.source_code }}
{% endcode %}
```

**Parameters:**
- `language`: Programming language (python, javascript, rust, go, etc.)
- `line_numbers`: Show/hide line numbers (default: true)
- `theme`: Syntax highlighting theme (default: monokai)
- `width`/`height`: Dimensions
- `border`: Border style (single, double, rounded, none)
- `title`: Optional border title

## TextArea Tag

The `{% textarea %}` tag provides a multi-line text editor:

```jinja2
{% textarea id="editor" value=state.content
            width=60 height=15 wrap_mode="soft" %}
{% endtextarea %}
```

**Features:**
- Multi-line text editing
- Soft/hard line wrapping
- Scrolling for long content
- Two-way state binding
- Mouse and keyboard support

## State Binding

All rich content elements support automatic state binding:

- Set `id="myid"` and `bind=true` (default)
- Content automatically updates when `state.myid` changes
- Scroll positions persist across renders
- Focus state is maintained

Try pressing 1-3 to switch code examples and see state binding in action!
"""

# Code examples
EXAMPLES = {
    "basic": {
        "name": "Basic Example",
        "language": "python",
        "code": '''"""Basic Wijjit app with template tags."""

from wijjit import Wijjit

app = Wijjit(initial_state={
    "message": "Hello, Wijjit!"
})

@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame title="Hello World" border="double" width=60 height=10 %}
  {% vstack padding=2 %}
    {% markdown %}
# Welcome
{{ state.message }}
    {% endmarkdown %}
  {% endvstack %}
{% endframe %}
        """
    }

app.run()
''',
    },
    "interactive": {
        "name": "Interactive Code Viewer",
        "language": "python",
        "code": '''"""Code viewer with language switching."""

from wijjit import Wijjit, EventType, HandlerScope

app = Wijjit(initial_state={
    "code": "def hello():\\n    print('world')",
    "language": "python",
})

@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame title="Code Viewer" border="double" %}
  {% vstack spacing=1 padding=1 %}
    {% code language=state.language width=70 height=20
            line_numbers=true title="Source Code" %}
{{ state.code }}
    {% endcode %}

    {% hstack spacing=2 %}
      {% button action="python" %}Python{% endbutton %}
      {% button action="javascript" %}JavaScript{% endbutton %}
      {% button action="rust" %}Rust{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """
    }

@app.on_action("python")
def show_python(event):
    app.state["language"] = "python"
    app.state["code"] = "def hello():\\n    print('world')"

@app.on_action("javascript")
def show_js(event):
    app.state["language"] = "javascript"
    app.state["code"] = "function hello() {\\n    console.log('world');\\n}"

@app.on_action("rust")
def show_rust(event):
    app.state["language"] = "rust"
    app.state["code"] = "fn main() {\\n    println!(\\"world\\");\\n}"

app.run()
''',
    },
    "combined": {
        "name": "Documentation + Code",
        "language": "python",
        "code": '''"""Documentation viewer with markdown and code."""

from wijjit import Wijjit

docs = """
# API Reference

## Installation

```bash
pip install wijjit
```

## Quick Start

See code panel for implementation example.
"""

code = """
from wijjit import Wijjit

app = Wijjit(initial_state={"count": 0})

@app.view("main", default=True)
def main():
    return {
        "template": \"\"\"
{% frame title="Counter" %}
  Count: {{ state.count }}
  {% button action="increment" %}+1{% endbutton %}
{% endframe %}
        \"\"\"
    }

@app.on_action("increment")
def increment(e):
    app.state["count"] += 1

app.run()
"""

app = Wijjit(initial_state={"docs": docs, "code": code})

@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% hstack spacing=2 %}
  {% markdown id="docs" width=40 height=25
              border="double" title="Docs" %}
  {% endmarkdown %}

  {% code language="python" width=50 height=25
          id="code" border="double" title="Code" %}
  {% endcode %}
{% endhstack %}
        """
    }

app.run()
''',
    },
}


TEMPLATE = """
{% frame title="Rich Content Template Demo" border="double" %}
  Instructions: [Tab] Switch Focus | [Arrows/PgUp/PgDn] Scroll | [1-3] Switch Example | [q] Quit
  {% vstack spacing=1 padding=1 %}
    {% hstack spacing=2 height=20 %}
      {% markdown id="docs" content=state.docs height=18
                  border_style="rounded" title="Documentation" %}
      {% endmarkdown %}

      {% code id="code" code=state.examples[state.current_example].code
              language=state.examples[state.current_example].language
               show_line_numbers=true
              border_style="rounded" title=state.examples[state.current_example].name %}
      {% endcode %}
    {% endhstack %}

    {% hstack spacing=2 height=3 %}
      {% button action="example_basic" %}[1] Basic{% endbutton %}
      {% button action="example_interactive" %}[2] Interactive{% endbutton %}
      {% button action="example_combined" %}[3] Combined{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

  {% endvstack %}
{% endframe %}
"""

def create_app():
    """Create the template demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    app = Wijjit(
        initial_state={
            "docs": API_DOCS,
            "current_example": "basic",
            "examples": EXAMPLES,
        }
    )

    @app.view("main", default=True)
    def main_view():
        """Main view using template tags."""
        return {
            "template": TEMPLATE,
        }

    # Example switchers
    @app.on_action("example_basic")
    def show_basic(event):
        app.state["current_example"] = "basic"

    @app.on_action("example_interactive")
    def show_interactive(event):
        app.state["current_example"] = "interactive"

    @app.on_action("example_combined")
    def show_combined(event):
        app.state["current_example"] = "combined"

    @app.on_action("quit")
    def handle_quit(event):
        app.quit()

    # Keyboard shortcuts
    def handle_key(event):
        if event.key == "q":
            app.quit()
            event.cancel()
        elif event.key == "1":
            app.state["current_example"] = "basic"
            app.refresh()
            event.cancel()
        elif event.key == "2":
            app.state["current_example"] = "interactive"
            app.refresh()
            event.cancel()
        elif event.key == "3":
            app.state["current_example"] = "combined"
            app.refresh()
            event.cancel()

    app.on(EventType.KEY, handle_key, scope=HandlerScope.GLOBAL)

    return app


def main():
    """Run the template demo."""
    app = create_app()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
