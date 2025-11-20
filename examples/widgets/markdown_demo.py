"""Markdown Demo - Demonstrates markdown rendering with MarkdownView.

This example shows the MarkdownView element with cell-based rendering,
featuring Rich markdown formatting, syntax highlighting, and scrolling.

Run with: python examples/markdown_demo_new.py

Controls:
- Arrow keys: Scroll up/down
- Page Up/Down: Scroll by page
- Home/End: Jump to top/bottom
- Mouse wheel: Scroll content
- q: Quit
"""

from wijjit import Wijjit

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

## Cell-Based Rendering

This demo uses the new **cell-based rendering** system with:
- Theme support for colors and styling
- Efficient diff-based updates
- Proper focus state handling
- Smooth scrolling

## Conclusion

This MarkdownView component is perfect for displaying documentation, help text, release notes, or any formatted content in your terminal applications.

Happy coding with Wijjit!
"""  # noqa: E501


def main():
    """Run the markdown demo application."""
    print("Starting markdown demo...")
    print("Debug log will be written to: markdown_demo_debug.log")

    # Create app with initial state
    app = Wijjit(initial_state={"markdown_text": SAMPLE_MARKDOWN})
    print(f"App created with state keys: {list(app.state.keys())}")

    @app.view("main", default=True)
    def main_view():
        """Main view with markdown viewer."""
        # IMPORTANT: Markdown must be wrapped in a layout container (frame/vstack/hstack)
        # to get bounds assigned and render properly
        template = """
{% frame width="100%" height="100%" %}
  {% markdown id="markdown"
              width="fill"
              height="fill"
              border_style="double"
              title="Markdown Viewer" %}
{{ state.markdown_text }}
  {% endmarkdown %}
{% endframe %}
        """.strip()

        print(f"Rendering view with template length: {len(template)}")
        print(f"State has markdown_text: {'markdown_text' in app.state}")

        return {
            "template": template,
            "data": {},
        }

    @app.on_key("q")
    def on_quit(event):
        """Handle 'q' key to quit."""
        app.quit()

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
