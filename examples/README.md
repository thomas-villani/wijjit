# Wijjit Examples

This directory contains comprehensive examples demonstrating all aspects of the Wijjit TUI framework.

> **Want to see them first?** [GALLERY.md](GALLERY.md) has screenshots of 20 of
> these demos, each with the command that reproduces it.

## Organization

Examples are organized into five categories:

### 📚 [basic/](basic/) - Introductory Examples

Simple examples demonstrating fundamental concepts and patterns.

- **hello_world.py** - Minimal "Hello World" application
- **simple_input_test.py** - Basic text input with state binding
- **mouse_demo.py** - Mouse interaction with buttons
- **debug_keys.py** - Key event debugging utility
- **async_demo.py** - Async/await patterns (view functions, event handlers, state callbacks)
- **alignment_demo.py** - Content alignment options
- **autocomplete_demo.py** - Autocomplete suggestions for text inputs
- **config_demo.py** - Configuring `app.config` options
- **theme_config_demo.py** - Selecting and configuring themes
- **grid_demo.py** - Grid layout basics
- **hstack_flexbox_demo.py** - HStack flexbox justify/wrap features
- **suspend_demo.py** - Ctrl+Z suspend/resume (Linux/macOS)
- **inline_demo.py** - One-shot inline rendering to scrollback
- **inline_progress_demo.py** - Interactive progress with `InlineApp`
- **inline_input_demo.py** - Interactive inline forms with keyboard input

**Start here if you're new to Wijjit!**

### 🧩 [widgets/](widgets/) - UI Element Demonstrations

Individual examples showcasing specific UI elements and components.

**Input Elements:**
- **checkbox_demo.py** - Individual checkboxes and checkbox groups with form submission
- **radio_demo.py** - Radio button groups (size, color, shipping options)
- **select_demo.py** - Select dropdowns with various options
- **dropdown_demo.py** - Dropdown menus with keyboard shortcuts
- **textarea_demo.py** - Multi-line text editor with selection & clipboard
- **slider_demo.py** - Numeric sliders (integer and float modes, keyboard and mouse)
- **toggle_demo.py** - Toggle switches (single and dual label modes)
- **status_indicator_demo.py** - Status indicators with color presets and custom statuses
- **datagrid_demo.py** - Spreadsheet-like data entry with VisiCalc/Lotus 1-2-3 style editing

- **code_editor_demo.py** - Syntax-highlighted code editor (languages + themes)

**Data Display:**
- **table_demo.py** - Sortable tables with scrolling
- **tree_demo.py** - Hierarchical tree view with expand/collapse
- **listview_demo.py** - Scrollable lists with multiple styles
- **logview_demo.py** - Auto-scrolling log viewer with level detection
- **contentview_demo.py** - Unified content viewer (plain/ANSI/HTML/Markdown/Rich/code)
- **imageview_demo.py** - ASCII/ANSI image rendering (needs the `images` extra)
- **tabbedpanel_demo.py** - Tabbed container with keyboard/mouse navigation
- **statusbar_demo.py** - Status bar component with view-scoped content

**Charts:**
- **charts_demo.py** - Bar/column/line charts, gauges, heatmap, sparklines

**Progress & Loading:**
- **progress_demo.py** - Progress bars with multiple styles
- **spinner_demo.py** - Animated loading spinners
- **notification_demo.py** - Notification system

**Dialogs & Modals:**
- **dialog_showcase.py** - All dialog types (alert, confirm, input) in one example
- **modal_with_button_demo.py** - Advanced modal with interactive button
- **confirm_dialog_demo.py** - Confirmation prompts
- **alert_dialog_demo.py** - Alert messages
- **input_dialog_demo.py** - Input dialogs
- **centered_dialog.py** - Dialog positioning

**Layout:**
- **splitpanel_demo.py** - Resizable split panel with sidebar and form
- **pager_demo.py** - Linear pagination with prev/next navigation (wizard-style)

### 🚀 [advanced/](advanced/) - Complex Applications & Patterns

Complete mini-applications and advanced usage patterns.

**Complete Applications** (under [apps/](apps/)):
- **apps/todo_app.py** - Todo list with a RadioGroup filter, checkboxes, edit/delete dialogs, and GFM persistence
- **apps/gcommit.py** - Interactive git commit builder in *inline* mode: stage files as checkboxes, type a message, preview or run the commit (stays in scrollback)
- **apps/chatbot.py** - Conversational TUI: scrollable history + rule-based bot (has a tutorial)
- **apps/spreadsheet.py** - Editable DataGrid with a live chart and .xlsx/CSV save (has a tutorial)
- **apps/system_monitor.py** - Live CPU/memory gauges and history line charts (needs psutil)
- **form_demo.py** - Registration form with comprehensive validation (email, age, required fields)
- **data_entry_demo.py** - Business order entry form with multiple sections
- **preferences_demo.py** - Settings/preferences editor with multiple categories
- **dashboard_demo.py** - Multi-panel monitoring dashboard with live metrics
- **login_form.py** - Login form with validation
- **filesystem_browser.py** - Interactive file system browser with tree view

**Advanced Patterns:**
- **navigation_demo.py** - Multi-view navigation with lifecycle hooks and view-scoped handlers
- **state_management_demo.py** - State watchers, async callbacks, derived state, change logging
- **event_patterns_demo.py** - Event scopes (global/view/element), priorities, propagation
- **error_handling_demo.py** - Error handling patterns and graceful degradation
- **executor_demo.py** - ThreadPoolExecutor configuration for non-blocking I/O
- **context_menu_demo.py** - Right-click context menus (experimental)

**Layout & Scrolling:**
- **scroll_demo.py** - Comprehensive scrolling features
- **scrollable_children_demo.py** - Scrollable nested content
- **scrollable_minimal.py** - Minimal scrolling example
- **horizontal_scroll_demo.py** - Horizontal scrolling patterns
- **frame_overflow_demo.py** - Frame sizing and overflow modes
- **complex_layout_demo.py** - Complex nested layouts
- **splitpanel_nested_demo.py** - Nested split panels (IDE-like three-pane layout)

**Template Patterns:**
- **templates_dir_demo/** - Flask-style file templates: views load `templates/*.wij.j2`
  from an auto-discovered `templates/` directory and share a header via `{% include %}`
- **template_demo.py** - Template features and patterns
- **download_simulator.py** - Progress tracking simulation

### 🎨 [styling/](styling/) - Theming & CSS

CSS-based styling and theming.

- **css_classes_demo.py** - Styling elements with CSS classes
- **css_theme_demo.py** - Loading a custom theme from a CSS file (`custom_theme.css`)

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
    return render_template_string("...", data=data)

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
