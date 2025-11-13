"""Markdown Demo - Demonstrates markdown rendering with MarkdownView.

This example shows the MarkdownView element with:
- Markdown content rendering with Rich
- Syntax highlighting in code blocks
- Scrolling for large documents
- Border styles and titles
- Keyboard navigation
- Mouse wheel scrolling

Run with: python examples/markdown_demo.py

Controls:
- Arrow keys: Scroll up/down
- Page Up/Down: Scroll by page
- Home/End: Jump to top/bottom
- Mouse wheel: Scroll content
- Tab: Switch between markdown panels
- q: Quit
"""

import shutil

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.elements.display.markdown import MarkdownView

# Sample markdown content
SAMPLE_MARKDOWN = """# Welcome to Wijjit MarkdownView

This component renders **markdown** content using the *Rich* library, providing beautiful text in your terminal UI.

## Features

1. **Headers** at all levels
2. **Bold** and *italic* text
3. `Inline code` formatting
4. Lists (ordered and unordered)
5. Block quotes
6. Code blocks with syntax highlighting
7. Tables
8. Links (displayed but not clickable in terminal)

## Code Examples

Here's some Python code:

```python
def hello_world():
    message = "Hello from Wijjit!"
    print(message)
    return True
```

And here's some JavaScript:

```javascript
function greet(name) {
    console.log(`Hello, ${name}!`);
    return true;
}
```

## Lists

### Unordered List

- First item
- Second item
  - Nested item
  - Another nested item
- Third item

### Ordered List

1. First step
2. Second step
3. Third step

## Blockquotes

> This is a blockquote.
> It can span multiple lines.
>
> And even multiple paragraphs.

## Tables

| Feature         | Status      | Notes                  |
|-----------------|-------------|------------------------|
| Headers         | Supported   | All levels (H1-H6)     |
| Lists           | Supported   | Ordered and unordered  |
| Code Blocks     | Supported   | With syntax highlight  |
| Inline Code     | Supported   | Monospace formatting   |
| Tables          | Supported   | Full table support     |
| Links           | Partial     | Displayed, not clickable|
| Images          | Not Yet     | Terminal limitation    |

## Emphasis

You can use **bold**, *italic*, or ***both*** for emphasis.

## Horizontal Rules

---

## More Content

This markdown viewer supports scrolling, so you can view documents of any length. Try scrolling with the arrow keys, Page Up/Down, or your mouse wheel!

### Tips

- Press **Tab** to switch between markdown panels
- Press **Arrow keys** or **Page Up/Down** to scroll
- Press **Home** or **End** to jump to top or bottom
- Use your **mouse wheel** to scroll smoothly
- Press **q** to quit

### Why Wijjit?

Wijjit makes building terminal UIs as easy as building web UIs. With familiar patterns like:

- **Declarative templates** using Jinja2
- **State management** similar to React
- **Event handling** like Flask
- **Component library** for common UI elements

You can focus on your application logic instead of wrestling with terminal control sequences!

## Conclusion

This MarkdownView component is perfect for displaying documentation, help text, release notes, or any formatted content in your terminal applications.

Happy coding with Wijjit!
"""  # noqa: E501

SHORT_MARKDOWN = """# Quick Start

This is a shorter markdown document.

## Installation

```bash
pip install wijjit
```

## Usage

```python
from wijjit import Wijjit

app = Wijjit()

@app.view("main", default=True)
def main_view():
    return {"template": "Hello, World!"}

app.run()
```

That's it!
"""


def create_app():
    """Create and configure the markdown demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Get terminal size
    term_size = shutil.get_terminal_size()
    panel_width = min(70, (term_size.columns - 6) // 2)
    panel_height = min(30, term_size.lines - 8)

    # Initialize app with state
    app = Wijjit(
        initial_state={
            "doc1": SAMPLE_MARKDOWN,
            "doc2": SHORT_MARKDOWN,
            "active_panel": "left",
        }
    )

    # Create MarkdownView elements
    markdown1 = MarkdownView(
        id="markdown1",
        content=SAMPLE_MARKDOWN,
        width=panel_width,
        height=panel_height,
        border_style="double",
        title="Full Documentation",
    )

    markdown2 = MarkdownView(
        id="markdown2",
        content=SHORT_MARKDOWN,
        width=panel_width,
        height=panel_height,
        border_style="rounded",
        title="Quick Start",
    )

    # Register elements with focus manager
    app.focus_manager.set_elements([markdown1, markdown2])
    markdown1.on_focus()  # Focus first panel by default

    @app.view("main", default=True)
    def main_view():
        """Main view with dual markdown panels."""

        def render_data():
            # Render markdown panels side by side
            lines1 = markdown1.render().split("\n")
            lines2 = markdown2.render().split("\n")

            # Ensure both have same height
            max_height = max(len(lines1), len(lines2))
            while len(lines1) < max_height:
                lines1.append(" " * panel_width)
            while len(lines2) < max_height:
                lines2.append(" " * panel_width)

            # Combine side by side
            combined_lines = []
            for l1, l2 in zip(lines1, lines2, strict=True):
                combined_lines.append(f"{l1}  {l2}")

            content_text = "\n".join(
                [
                    "=" * term_size.columns,
                    "  MARKDOWN DEMO - Dual Panel Viewer".center(term_size.columns),
                    "=" * term_size.columns,
                    "",
                    *combined_lines,
                    "",
                    "=" * term_size.columns,
                    "  [Tab] Switch Panel  [Arrows/PgUp/PgDn] Scroll  [Home/End] Jump  [q] Quit",
                    "=" * term_size.columns,
                ]
            )

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
        app.on(
            EventType.KEY,
            on_key,
            scope=HandlerScope.VIEW,
            view_name="main",
            priority=100,
        )

    return app


def main():
    """Run the markdown demo application."""
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
