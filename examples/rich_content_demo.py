"""Rich Content Demo - Combined Markdown and Code display.

This example demonstrates using both MarkdownView and CodeBlock together
in a single application, simulating a documentation viewer or API reference.

Features:
- Side-by-side markdown documentation and code examples
- Synchronized scrolling (optional)
- Tab to switch focus between panels
- Demonstrates typical use case: docs + implementation

Run with: python examples/rich_content_demo.py

Controls:
- Tab: Switch focus between documentation and code
- Arrow keys: Scroll focused panel
- Page Up/Down: Scroll by page
- Home/End: Jump to top/bottom
- Mouse wheel: Scroll focused panel
- q: Quit
"""

import shutil

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.elements.display.code import CodeBlock
from wijjit.elements.display.markdown import MarkdownView

# API Documentation
API_DOCS = """# Wijjit API Reference

## Quick Start Guide

Wijjit is a declarative TUI framework that brings web development patterns to terminal applications.

## Core Concepts

### 1. The App Class

The `Wijjit` class is the main application controller, similar to Flask's `app` object.

```python
from wijjit import Wijjit

app = Wijjit(initial_state={"counter": 0})
```

### 2. Views and Routing

Define views using the `@app.view()` decorator:

- Each view returns a dictionary with `template` and optionally `data`
- Views are identified by name
- One view must be marked as `default=True`

### 3. State Management

State is reactive and automatically triggers re-renders when changed:

- Access via `app.state[key]`
- Changes propagate to all bound elements
- State is preserved across renders

### 4. Event Handling

Handle events with decorators:

- `@app.on_action(name)` - Handle custom actions
- `@app.on(EventType.KEY, handler)` - Handle keyboard events
- `@app.on(EventType.MOUSE, handler)` - Handle mouse events

## Template Syntax

Wijjit uses Jinja2 templates with custom tags:

### Layout Tags

- `{% frame %}` - Bordered container
- `{% vstack %}` - Vertical stack
- `{% hstack %}` - Horizontal stack

### Input Elements

- `{% textinput %}` - Single-line text input
- `{% textarea %}` - Multi-line text editor
- `{% button %}` - Clickable button
- `{% select %}` - Selection list
- `{% checkbox %}` - Checkbox input
- `{% radio %}` - Radio button

### Display Elements

- `{% table %}` - Data table with sorting
- `{% tree %}` - Tree view for hierarchical data
- `{% progressbar %}` - Progress indicator
- `{% spinner %}` - Loading spinner
- `{% markdown %}` - Markdown content
- `{% code %}` - Syntax-highlighted code

## Examples

See the code panel on the right for detailed examples!

## Best Practices

1. **Keep state minimal** - Only store what's necessary
2. **Use templates** - Declarative UI is easier to maintain
3. **Leverage events** - Don't poll, react to user input
4. **Test incrementally** - Build and test components individually

## Advanced Topics

### Custom Components

You can create custom components by extending `Element`:

```python
from wijjit.elements import Element

class MyElement(Element):
    def render(self):
        return "My custom content"
```

### Layout Engine

The layout engine automatically positions elements based on:

- Container flow (vertical/horizontal stacks)
- Element dimensions (width/height)
- Alignment rules
- Scroll regions

### Performance Tips

- Minimize state updates
- Use `app.refresh()` to batch updates
- Leverage focus management for large element trees
- Cache rendered content when possible

## Getting Help

- GitHub: https://github.com/yourusername/wijjit
- Docs: https://wijjit.readthedocs.io
- Issues: Report bugs and feature requests on GitHub

Happy building!
"""

# Implementation Example
IMPLEMENTATION_CODE = '''"""Example: Building a TODO app with Wijjit."""

from wijjit import Wijjit, EventType, HandlerScope

# Initialize app with state
app = Wijjit(initial_state={
    "todos": [
        {"id": 1, "text": "Learn Wijjit", "done": False},
        {"id": 2, "text": "Build TUI app", "done": False},
    ],
    "next_id": 3,
    "new_todo": "",
})


@app.view("main", default=True)
def main_view():
    """Main view with todo list."""
    return {
        "template": """
{% frame title="TODO App" border="double" width=60 height=25 %}
  {% vstack spacing=1 padding=1 %}
    {% textinput id="new_todo"
                 value=state.new_todo
                 placeholder="Enter new todo..."
                 action="add_todo" %}

    {% vstack spacing=0 %}
      {% for todo in state.todos %}
        {% checkbox id="todo_" + todo.id|string
                   checked=todo.done
                   label=todo.text %}
      {% endfor %}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="clear_completed" %}Clear Completed{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("add_todo")
def handle_add_todo(event):
    """Add a new todo item."""
    text = app.state["new_todo"].strip()

    if text:
        todos = app.state["todos"]
        todos.append({
            "id": app.state["next_id"],
            "text": text,
            "done": False,
        })

        app.state["todos"] = todos
        app.state["next_id"] += 1
        app.state["new_todo"] = ""


@app.on_action("clear_completed")
def handle_clear_completed(event):
    """Remove all completed todos."""
    app.state["todos"] = [
        todo for todo in app.state["todos"]
        if not todo["done"]
    ]


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


# Global keyboard shortcut
def handle_key_q(event):
    """Handle 'q' key to quit."""
    if event.key == "q":
        app.quit()
        event.cancel()


app.on(EventType.KEY, handle_key_q, scope=HandlerScope.GLOBAL)


if __name__ == "__main__":
    app.run()


# ===================================
# More Advanced Example: Data Viewer
# ===================================

class DataViewerApp:
    """A data viewer with filtering and sorting."""

    def __init__(self, data):
        self.app = Wijjit(initial_state={
            "data": render_data,  # Pass the function itself, not the result
            "filtered_data": data,
            "filter_text": "",
            "sort_column": None,
            "sort_desc": False,
        })
        self.setup_views()
        self.setup_handlers()

    def setup_views(self):
        """Set up the application views."""
        @self.app.view("main", default=True)
        def main_view():
            return {
                "template": """
{% frame title="Data Viewer" border="double" %}
  {% vstack spacing=1 padding=1 %}
    {% textinput id="filter"
                 value=state.filter_text
                 placeholder="Filter..."
                 action="filter_data" %}

    {% table id="data_table"
             data=state.filtered_data
             columns=["name", "value", "status"]
             sortable=true
             width=80
             height=20 %}
    {% endtable %}

    {% hstack %}
      {% button action="export" %}Export{% endbutton %}
      {% button action="refresh" %}Refresh{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
                """,
                "data": {},
            }

    def setup_handlers(self):
        """Set up event handlers."""
        @self.app.on_action("filter_data")
        def handle_filter(event):
            filter_text = self.app.state["filter_text"].lower()
            all_data = self.app.state["data"]

            if not filter_text:
                self.app.state["filtered_data"] = all_data
            else:
                self.app.state["filtered_data"] = [
                    row for row in all_data
                    if filter_text in str(row).lower()
                ]

        @self.app.on_action("export")
        def handle_export(event):
            # Export logic here
            pass

        @self.app.on_action("refresh")
        def handle_refresh(event):
            # Refresh data logic here
            pass

    def run(self):
        """Run the application."""
        self.app.run()


# Usage
if __name__ == "__main__":
    sample_data = [
        {"name": "Item 1", "value": 100, "status": "Active"},
        {"name": "Item 2", "value": 200, "status": "Inactive"},
        {"name": "Item 3", "value": 150, "status": "Active"},
    ]

    viewer = DataViewerApp(sample_data)
    viewer.run()
'''


def create_app():
    """Create and configure the rich content demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Get terminal size
    term_size = shutil.get_terminal_size()
    panel_width = (term_size.columns - 6) // 2
    panel_height = term_size.lines - 8

    # Initialize app
    app = Wijjit(initial_state={
        "focused_panel": "docs",
    })

    # Create elements
    markdown = MarkdownView(
        id="docs",
        content=API_DOCS,
        width=panel_width,
        height=panel_height,
        border_style="double",
        title="API Documentation",
    )

    codeblock = CodeBlock(
        id="code",
        code=IMPLEMENTATION_CODE,
        language="python",
        width=panel_width,
        height=panel_height,
        border_style="double",
        title="Implementation Example",
        show_line_numbers=True,
        theme="monokai",
    )

    # Register with focus manager
    app.focus_manager.set_elements([markdown, codeblock])
    markdown.on_focus()

    @app.view("main", default=True)
    def main_view():
        """Main view with side-by-side panels."""
        def render_data():
            # Render both panels
            markdown_lines = markdown.render().split("\n")
            code_lines = codeblock.render().split("\n")

            # Ensure both have same height
            max_height = max(len(markdown_lines), len(code_lines))
            while len(markdown_lines) < max_height:
                markdown_lines.append(" " * panel_width)
            while len(code_lines) < max_height:
                code_lines.append(" " * panel_width)

            # Combine side by side
            combined_lines = []
            for md_line, code_line in zip(markdown_lines, code_lines, strict=True):
                combined_lines.append(f"{md_line}  {code_line}")

            # Build full UI
            content_text = "\n".join([
                "=" * term_size.columns,
                "  RICH CONTENT DEMO - Documentation + Code".center(term_size.columns),
                "=" * term_size.columns,
                "",
                *combined_lines,
                "",
                "=" * term_size.columns,
                "  [Tab] Switch Panel  [Arrows/PgUp/PgDn] Scroll  [Home/End] Jump  [q] Quit",
                "=" * term_size.columns,
            ])

            return {"content": content_text}

        # data = render_data()  # Fixed: pass function directly

        return {
            "template": "{{ content }}",
            "data": render_data,  # Pass the function itself, not the result
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers."""
        def on_key(event):
            """Handle keyboard events."""
            # Quit with 'q'
            if event.key == "q":
                app.quit()
                event.cancel()
                return

        # Register key handler
        app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main", priority=100)

    return app


def main():
    """Run the rich content demo application."""
    app = create_app()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
