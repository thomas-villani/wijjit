# Wijjit Examples

This directory contains comprehensive examples demonstrating all aspects of the Wijjit TUI framework.

## Organization

Examples are organized into three categories:

### 📚 [basic/](basic/) - Introductory Examples

Simple examples demonstrating fundamental concepts and patterns.

- **hello_world.py** - Minimal "Hello World" application
- **simple_input_test.py** - Basic text input with state binding
- **mouse_demo.py** - Mouse interaction with buttons
- **debug_keys.py** - Key event debugging utility
- **async_demo.py** - Async/await patterns (view functions, event handlers, state callbacks)
- **alignment_demo.py** - Content alignment options

**Start here if you're new to Wijjit!**

### 🧩 [widgets/](widgets/) - UI Element Demonstrations

Individual examples showcasing specific UI elements and components.

**Data Display:**
- **table_demo.py** - Sortable tables with scrolling
- **tree_demo.py** - Hierarchical tree view with expand/collapse
- **tree_indicator_styles_demo.py** - Different tree indicator styles
- **listview_demo.py** - Scrollable lists with multiple styles
- **logview_demo.py** - Auto-scrolling log viewer with level detection
- **markdown_demo.py** - Markdown rendering with syntax highlighting
- **code_demo.py** - Syntax-highlighted code display
- **statusbar_demo.py** - Status bar component with view-scoped content

**Form Elements:**
- **select_demo.py** - Select dropdowns with various options
- **dropdown_demo.py** - Dropdown menus with keyboard shortcuts
- **textarea_demo.py** - Multi-line text editor with selection & clipboard

**Progress & Loading:**
- **progress_demo.py** - Progress bars with multiple styles
- **spinner_demo.py** - Animated loading spinners
- **notification_demo.py** - Notification system

**Dialogs & Modals:**
- **modal_with_button_demo.py** - Advanced modal with interactive button
- **confirm_dialog_demo.py** - Confirmation prompts
- **alert_dialog_demo.py** - Alert messages
- **input_dialog_demo.py** - Input dialogs
- **centered_dialog.py** - Dialog positioning

**Other:**
- **test_markdown_tag.py** - Markdown tag testing

### 🚀 [advanced/](advanced/) - Complex Applications & Patterns

Complete mini-applications and advanced usage patterns.

**Mini Applications:**
- **login_form.py** - Login form with validation
- **filesystem_browser.py** - Interactive file system browser
- **download_simulator.py** - Progress tracking simulation

**Layout & Scrolling:**
- **scroll_demo.py** - Comprehensive scrolling features
- **scrollable_children_demo.py** - Scrollable nested content
- **scrollable_minimal.py** - Minimal scrolling example
- **frame_overflow_demo.py** - Frame sizing and overflow modes
- **complex_layout_demo.py** - Complex nested layouts

**Template Patterns:**
- **template_demo.py** - Template features and patterns
- **rich_content_template_demo.py** - Rich content in templates

## Running Examples

All examples can be run directly with Python:

```bash
python examples/basic/hello_world.py
python examples/widgets/table_demo.py
python examples/advanced/login_form.py
```

Most examples support keyboard shortcuts:
- **q** - Quit the application
- **Tab / Shift+Tab** - Navigate between elements
- **Arrow keys** - Navigate within elements
- **Enter / Space** - Activate buttons

## Examples to be Rewritten

The `to-replace/` folder contains examples using outdated patterns that need complete rewrites:

- checkbox_demo.py - Needs template-based approach
- radio_demo.py - Needs template-based approach
- form_demo.py - Outdated form patterns
- context_menu_demo.py - Context menu implementation
- navigation_demo.py - Multi-view navigation
- simple_modal_demo.py - Basic modal patterns
- todo_app.py - Complete todo list app
- simple_checkbox_template.py - Template-based checkbox
- rich_content_demo.py - Rich content display
- preferences_template_demo.py - Settings/preferences UI

## Key Patterns Demonstrated

### Event Handling
Modern decorator-based event handling:
```python
@app.on_key("q")
def on_quit(event):
    app.quit()

@app.on_action("submit")
def handle_submit(event):
    # Handle form submission
    pass
```

### State Management
Reactive state with automatic re-rendering:
```python
app = Wijjit(initial_state={"count": 0})

@app.on_action("increment")
def increment(event):
    app.state["count"] += 1  # Triggers re-render
```

### Template-Based UI
Declarative UI definition with Jinja2:
```jinja2
{% frame title="My App" %}
  {% vstack spacing=1 %}
    {% textinput id="username" %}{% endtextinput %}
    {% button action="submit" %}Submit{% endbutton %}
  {% endvstack %}
{% endframe %}
```

### Async/Await
Full async support throughout:
```python
@app.view("main", default=True)
async def main_view():
    data = await load_data()
    return {"template": "..."}

@app.on_action("fetch")
async def fetch_data(event):
    result = await api_call()
    app.state["data"] = result
```

## Contributing

When adding new examples:
1. Place them in the appropriate directory (basic/widgets/advanced)
2. Include a comprehensive docstring describing the example
3. Add keyboard shortcuts documentation
4. Use modern patterns (@app.on_key, @app.on_action decorators)
5. Include error handling with try/except
6. Update this README

## Documentation

For more information:
- **Main README**: ../README.md
- **Development Guide**: ../CLAUDE.md
- **API Documentation**: ../docs/
