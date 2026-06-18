# Wijjit

**Flask for the Console: A declarative TUI framework for Python**

*Wijjit is Just Jinja in Terminal*

---

Wijjit is a Python framework for building Terminal User Interfaces (TUIs) using familiar web development patterns. 
If you know Flask and Jinja2, you can build rich, interactive console applications with Wijjit.

Wijjit was obviously inspired by the wonderful Flask library, and makes heavy use of the patterns innate to Flask 
applications. We built this library to bring the syntactic elegance of Flask's decorator patterns to building TUIs.

## Features

- **Declarative UI**: Define layouts using Jinja2 templates, not procedural positioning code
- **Flask-like API**: View decorators, routing, and state management that feels like web development
- **Rich Component Library**: Pre-built elements for forms, tables, trees, progress indicators, and more
- **Reactive State Management**: State changes automatically trigger re-renders
- **Automatic Focus Navigation**: Tab/Shift+Tab navigation between interactive elements
- **Modal Dialogs**: Built-in confirm, alert, and input dialogs
- **Layout System**: Flexible frames with stacks (vertical/horizontal), scrolling, and sizing options
- **Mouse Support**: Click buttons, scroll content, and interact with elements
- **Inline Rendering**: Output styled UI to terminal scrollback without alternate screen
- **Job Control**: Ctrl+Z suspend/resume support on Unix systems (Linux, macOS)
- **ANSI-Aware**: Proper handling of colors and styling throughout

## Installation

```bash
# From PyPI
pip install wijjit

# Optional extras
pip install "wijjit[images]"   # ImageView / ASCII image rendering (Pillow)
```

> Wijjit is currently in pre-release. Until 0.1.0 is published, install the
> latest alpha with `pip install --pre wijjit`, or install from source below.

### From source (development)

```bash
git clone https://github.com/thomas-villani/wijjit.git
cd wijjit

# Install in development mode with uv (recommended)
uv sync --all-extras

# Or with pip
pip install -e ".[dev]"
```

## Quick Start

### Hello World

The simplest possible Wijjit app:

```python
from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope

app = Wijjit()

@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame %}
Hello, World! Press 'q' to quit.
{% endframe %}
""",
    }

@app.on_key("q")
def on_quit(event):
    app.quit()

if __name__ == "__main__":
    app.run()
```

### Login Form

A complete login form with validation, showing the power of templates:

```python
from wijjit import Wijjit

app = Wijjit(initial_state={
    'username': '',
    'password': '',
    'status': 'Please enter your credentials',
})

@app.view("login", default=True)
def login_view():
    return {
        "template": """
{% frame title="Login" border="single" width=50 height=15 %}
  {% vstack spacing=1 padding=1 %}
    {{ state.status }}

    {% vstack spacing=0 %}
      Username:
      {% textinput id="username" placeholder="Enter username" width=30 %}{% endtextinput %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Password:
      {% textinput id="password" placeholder="Enter password" width=30 action="login" %}{% endtextinput %}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="login" %}Login{% endbutton %}
      {% button action="clear" %}Clear{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """
    }

@app.on_action("login")
def handle_login(event):
    username = app.state.get('username', '')
    password = app.state.get('password', '')

    if username == 'admin' and password == 'password':
        app.state['status'] = f'Success! Welcome, {username}!'
    else:
        app.state['status'] = 'Error: Invalid credentials'

@app.on_action("clear")
def handle_clear(event):
    app.state['username'] = ''
    app.state['password'] = ''

@app.on_action("quit")
def handle_quit(event):
    app.quit()

if __name__ == '__main__':
    app.run()
```

## Core Concepts

### Views and Routing

Like Flask, Wijjit uses decorators to define views:

```python
@app.view("main", default=True)
def main_view():
    return {
        "template": "...",  # Jinja2 template string
        "data": {...},      # Additional template data
        "on_enter": fn,     # Called when view is entered
        "on_exit": fn,      # Called when view is exited
    }

# Navigate to a different view
app.navigate("other_view", param=value)
```

### State Management

Wijjit provides reactive state that automatically triggers re-renders when changed:

```python
# Initialize with state
app = Wijjit(initial_state={'count': 0})

# Access state (dict-style or attribute-style)
app.state['count'] = 1
app.state.count = 2

# State changes automatically re-render the UI
# Elements with matching IDs automatically bind to state
```

### Templates

Use Jinja2 templates with custom tags for UI elements:

```jinja2
{# Layout containers #}
{% frame title="My App" border="rounded" width=60 %}
  {% vstack spacing=1 %}
    Content here
  {% endvstack %}
{% endframe %}

{# Input elements #}
{% textinput id="name" placeholder="Enter name" %}{% endtextinput %}
{% textarea id="bio" width=40 height=5 %}{% endtextarea %}
{% button action="submit" %}Submit{% endbutton %}
{% checkbox id="agree" label="I agree" %}{% endcheckbox %}
{% select id="theme" options=["dark", "light"] %}{% endselect %}
{% slider id="volume" min=0 max=100 value=50 %}{% endslider %}
{% toggle id="dark_mode" label="Dark Mode" %}{% endtoggle %}
{% status status="success" label="Connected" %}{% endstatus %}

{# Multi-select elements - state holds lists #}
{% select id="toppings" multiple=True %}
  {"value": "cheese", "label": "Cheese"}
  {"value": "pepperoni", "label": "Pepperoni"}
{% endselect %}
{% tree id="files" data=state.file_tree multiple=True %}{% endtree %}

{# Display elements #}
{% table data=state.users columns=["name", "email"] %}{% endtable %}
{% tree data=state.files %}{% endtree %}
{% progressbar value=state.progress max=100 %}{% endprogressbar %}
{% contentview content_type="markdown" content=state.readme %}{% endcontentview %}
```

### Event Handling

Handle user interactions with decorators:

```python
# Action handlers (from buttons, inputs with action attribute)
@app.on_action("submit")
def handle_submit(event):
    # Process form submission
    pass

# Key handlers
@app.on_key("ctrl+s")
def save(event):
    # Save on Ctrl+S
    pass

# Generic event handlers
from wijjit.core.events import EventType, HandlerScope

@app.view("main", default=True)
def main_view():
    return {
        "template": "...",
        "on_enter": setup_handlers,
    }

def setup_handlers():
    def on_key(event):
        if event.key == "q":
            app.quit()

    app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main")
```

### Element Event Callbacks

In addition to app-level handlers, elements expose callback attributes for direct event handling:

**Mouse Callbacks** (all elements):
```python
from wijjit.elements.display.table import Table

# Double-click handling
element.on_double_click = lambda event: print("Double-clicked!")

# Context menu (right-click) - return menu items or None
element.on_context_menu = lambda event: [{"label": "Copy"}, {"label": "Paste"}]
```

**Drag-and-Drop** (set `draggable=True` or `drop_target=True`):

> The low-level drag/drop callbacks below are available on elements today. A
> higher-level drag-and-drop manager is planned but not yet implemented.

```python
element.draggable = True
element.on_drag_start = lambda event: {"item": "data"}  # Return drag data
element.on_drag = lambda event, data: None  # Called during drag
element.on_drag_end = lambda event, data, dropped: None  # Drag finished

element.drop_target = True
element.on_drag_over = lambda event, data: True  # Return True to allow drop
element.on_drop = lambda event, data, source: handle_drop(data)  # Handle drop
```

**Table Callbacks**:
```python
table = Table(data=users, columns=["name", "email"])
table.on_row_click = lambda row_idx, row_data: select_user(row_data)
table.on_row_double_click = lambda row_idx, row_data: edit_user(row_data)
table.on_cell_click = lambda row_idx, col_key, value: print(f"Clicked {col_key}")
table.on_header_click = lambda col_key: sort_by(col_key)
```

**TextInput/TextArea Callbacks**:
```python
from wijjit.elements.input.text import TextInput, TextArea

# Submit on Enter (TextInput) or Ctrl+Enter (TextArea)
text_input.on_submit = lambda value: search(value)

# Intercept paste - return modified text or None
text_input.on_paste = lambda text: text.strip()

# Detect file paths in paste (e.g., drag files to terminal)
text_input.on_file_path_paste = lambda paths: handle_files(paths)
```

### Layout System

Wijjit provides flexible layout containers:

**Frames**: Boxes with borders, titles, and scrolling
```jinja2
{% frame title="Settings" border="single" width=60 height=20 scrollable=True %}
  Content
{% endframe %}
```

**VStack**: Vertical stack
```jinja2
{% vstack spacing=1 align_h="center" %}
  {% button %}Top{% endbutton %}
  {% button %}Bottom{% endbutton %}
{% endvstack %}
```

**HStack**: Horizontal stack with flexbox-style features
```jinja2
{% hstack spacing=2 align_v="middle" %}
  {% button %}Left{% endbutton %}
  {% button %}Right{% endbutton %}
{% endhstack %}

{# Flexbox justify modes - use width="fill" so hstack expands to container #}
{% hstack justify="space-between" width="fill" %}
  {% button %}Start{% endbutton %}
  {% button %}End{% endbutton %}
{% endhstack %}

{# Wrap items to multiple rows #}
{% hstack wrap=True gap=1 justify="center" width="fill" %}
  {% for tag in tags %}
    {% button %}{{ tag }}{% endbutton %}
  {% endfor %}
{% endhstack %}
```

HStack attributes:
- `spacing`: Gap between children (alias for `column_gap`)
- `justify`: Distribution mode: `"flex-start"`, `"flex-end"`, `"center"`, `"space-between"`, `"space-around"`, `"space-evenly"`
- `wrap`: Allow children to wrap to next row when exceeding width (default: `false`)
- `column_gap`: Space between columns
- `row_gap`: Space between rows when wrapping
- `gap`: Shorthand for both `row_gap` and `column_gap`
- `align_v`: Vertical alignment within row: `"top"`, `"middle"`, `"bottom"`, `"stretch"`
- `width`: Set to `"fill"` when using justify modes (required for justify to have space to distribute)

**SplitPanel**: Resizable split panel with draggable divider
```jinja2
{# Horizontal split (side-by-side panels) #}
{% splitpanel orientation="horizontal" ratio="30:70" id="main_split" %}
  {% frame title="Sidebar" %}
    Navigation content
  {% endframe %}
  {% frame title="Main" %}
    Main content
  {% endframe %}
{% endsplitpanel %}

{# Vertical split (stacked panels) #}
{% splitpanel orientation="vertical" ratio="60:40" collapsible="first" %}
  {% frame title="Editor" %}
    Code here
  {% endframe %}
  {% frame title="Terminal" %}
    Output here
  {% endframe %}
{% endsplitpanel %}
```

SplitPanel attributes:
- `orientation`: `"horizontal"` (side-by-side) or `"vertical"` (stacked)
- `ratio`: Initial size ratio like `"50:50"` or `"30:70"`
- `resizable`: Allow drag-to-resize (default: `true`)
- `collapsible`: Which panels can collapse: `"none"`, `"first"`, `"second"`, `"both"`
- `divider_style`: Divider appearance: `"single"`, `"double"`, `"dashed"`, `"thick"`
- `min_first`, `min_second`: Minimum sizes for each panel (default: 5)
- `id`: Element ID for state persistence (ratio survives re-renders)

**Pager**: Linear pagination for wizard-style interfaces
```jinja2
{% pager id="wizard" nav_position="bottom" show_indicator=True show_titles=True %}
  {% page title="Welcome" %}
    Welcome to the setup wizard!
    Press Right arrow or click "Next >" to continue.
  {% endpage %}

  {% page title="Settings" %}
    {% vstack spacing=1 %}
      {% textinput id="name" placeholder="Enter your name" %}{% endtextinput %}
      {% checkbox id="newsletter" %}Subscribe to newsletter{% endcheckbox %}
    {% endvstack %}
  {% endpage %}

  {% page title="Complete" %}
    Setup complete! Press 'q' to exit.
  {% endpage %}
{% endpager %}
```

Pager attributes:
- `nav_position`: Navigation bar position: `"top"`, `"bottom"`, or `"both"`
- `show_indicator`: Show "Page X of Y" indicator (default: `true`)
- `show_titles`: Show page title in indicator (default: `false`)
- `loop`: Wrap from last to first page (default: `false`)
- `border`: Border style: `"single"`, `"double"`, `"rounded"`, `"none"`
- `width`, `height`: Pager dimensions
- `current_page`: Initial page index (0-based)

Pager navigation:
- Left/PgUp: Previous page
- Right/PgDown: Next page
- Home/End: First/Last page
- Mouse click on Prev/Next buttons

**Sizing**: Flexible size specifications
- Fixed: `width=50` or `width="50"`
- Fill available space: `width="fill"`
- Size to content: `width="auto"`
- Percentage: `width="50%"`

### Modal Dialogs

Built-in dialog components:

```python
from wijjit.tags.dialogs import ConfirmDialog, AlertDialog, TextInputDialog

# Confirmation dialog
dialog = ConfirmDialog(
    title="Confirm",
    message="Are you sure?",
    on_confirm=lambda: print("Confirmed!"),
    on_cancel=lambda: print("Cancelled")
)
app.show_modal(dialog)

# Alert dialog
dialog = AlertDialog(
    title="Success",
    message="Operation completed!",
    on_close=lambda: app.navigate("main")
)
app.show_modal(dialog)

# Input dialog
dialog = TextInputDialog(
    title="Enter Name",
    prompt="What's your name?",
    on_submit=lambda value: handle_input(value)
)
app.show_modal(dialog)
```

### Inline Rendering

For CLI tools that don't need full-screen mode, Wijjit provides inline rendering that outputs styled content directly to terminal scrollback:

**One-shot rendering with `render_inline()`:**
```python
from wijjit import render_inline

# Render styled output directly to terminal
render_inline('''
{% frame title="Results" border="rounded" %}
  {% vstack %}
    Status: {{ status }}
    Count: {{ count }}
  {% endvstack %}
{% endframe %}
''', status="Complete", count=42)
```

**Interactive inline apps with `InlineApp`:**
```python
import asyncio
from wijjit import InlineApp

template = '''
{% frame title="Progress" %}
  {% progressbar value=state.progress max=100 %}{% endprogressbar %}
  {{ state.status }}
{% endframe %}
'''

async def main():
    async with InlineApp(template, initial_state={"progress": 0, "status": "Starting"}) as app:
        for i in range(101):
            app.state.progress = i
            app.state.status = f"Processing... {i}%"
            await asyncio.sleep(0.05)
        app.state.status = "Complete!"

asyncio.run(main())
```

**Interactive forms with keyboard input:**
```python
template = '''
{% frame title="Quick Input" %}
  Name: {% textinput id="name" %}{% endtextinput %}
  Press Ctrl+Q when done
{% endframe %}
'''

async with InlineApp(template, enable_input=True, quit_key="ctrl+q") as app:
    await app.wait()  # Wait for quit key

print(f"You entered: {app.state.name}")
```

## Component Library

### Input Components

- **TextInput**: Single-line text input with cursor editing
- **TextArea**: Multi-line text input with scrolling
- **CodeEditor**: Syntax-highlighted code editor (500+ languages, multiple themes)
- **DataGrid**: Spreadsheet-like data entry with VisiCalc/Lotus 1-2-3 style entry line
- **Button**: Clickable button (mouse or keyboard)
- **Checkbox**: Single checkbox or checkbox groups
- **Radio**: Radio button groups
- **Select**: Dropdown select menu (supports multi-select with `multiple=True`)
- **Slider**: Numeric input with draggable handle (supports int/float modes)
- **Toggle**: Boolean switch with visual indicator (single/dual label modes)
- **Link**: Clickable inline text element

### Display Components

- **ContentView**: Unified content viewer (plain, ANSI, HTML, Markdown, Rich markup, code with syntax highlighting)
- **Table**: Sortable, scrollable tables (powered by Rich)
- **Tree**: Hierarchical tree view with expand/collapse (supports multi-select with `multiple=True`)
- **ListView**: Scrollable list with selection
- **LogView**: Auto-scrolling log viewer
- **ProgressBar**: Progress indicators (bar, dots, spinner styles)
- **Spinner**: Animated loading indicators
- **StatusIndicator**: Colored status indicator with extensible presets (error, warning, success, info, etc.)
- **Notification**: Toast-style notifications with auto-dismiss

### Data Visualization Components

- **BarChart**: Horizontal bar charts with labels and gradient coloring
- **ColumnChart**: Vertical column charts with Y-axis
- **LineChart**: High-resolution line charts using braille characters
- **Gauge**: Linear or arc-style value indicators
- **HeatMap**: 2D grid visualization with color intensity
- **Sparkline**: Compact inline trend visualization

### Layout Components

- **Frame**: Container with borders, titles, padding, and scrolling
- **VStack**: Vertical stack layout
- **HStack**: Horizontal stack layout
- **SplitPanel**: Resizable split panel with draggable divider
- **TabbedPanel**: Tabbed container with keyboard/mouse navigation
- **Pager**: Linear pagination through multiple pages with prev/next navigation

## Examples

The `examples/` directory contains **69 working examples** organized into five
categories: `basic/` (15), `widgets/` (30), `advanced/` (21), `styling/` (2),
and `apps/` (1). All examples use modern patterns with template-based UI and
decorator event handlers.

### Basic Examples (`examples/basic/`)

Introductory examples demonstrating core concepts:
- `hello_world.py` - Minimal "Hello World" app
- `simple_input_test.py` - Basic text input with quit handler
- `async_demo.py` - Async/await event handlers
- `mouse_demo.py` - Mouse interaction (clicks, hovers, scrolling)
- `debug_keys.py` - Key event debugging tool
- `alignment_demo.py` - Content alignment in layouts
- `suspend_demo.py` - Ctrl+Z suspend/background (Linux/macOS)
- `inline_demo.py` - One-shot inline rendering to scrollback
- `inline_progress_demo.py` - Interactive progress with `InlineApp`
- `inline_input_demo.py` - Interactive forms with keyboard input

### Widget Examples (`examples/widgets/`)

Individual UI component demonstrations (20+ widgets):

**Input Elements:**
- `checkbox_demo.py` - Individual checkboxes and checkbox groups
- `radio_demo.py` - Radio button groups with multiple examples
- `select_demo.py`, `dropdown_demo.py` - Dropdown selection menus
- `textarea_demo.py` - Multi-line text input with selection
- `slider_demo.py` - Numeric sliders (integer and float modes)
- `toggle_demo.py` - Toggle switches (single and dual label modes)
- `status_indicator_demo.py` - Status indicators with color presets

**Display Elements:**
- `table_demo.py` - Sortable data tables with Rich integration
- `tree_demo.py` - Hierarchical tree views
- `listview_demo.py` - Scrollable lists with selection
- `logview_demo.py` - Auto-scrolling log viewer
- `progress_demo.py` - Progress bars and indicators
- `spinner_demo.py` - Loading spinners with animations
- `contentview_demo.py` - ContentView (plain/ANSI/HTML/Markdown/Rich/code)
- `code_editor_demo.py` - Syntax-highlighted code editor
- `statusbar_demo.py` - Status bar component
- `notification_demo.py` - Toast notifications

**Layout:**
- `splitpanel_demo.py` - Resizable split panel with sidebar layout
- `pager_demo.py` - Linear pagination with prev/next navigation

**Dialogs:**
- `dialog_showcase.py` - All dialog types (alert, confirm, input)
- `alert_dialog_demo.py` - Alert messages
- `confirm_dialog_demo.py` - Confirmation prompts
- `input_dialog_demo.py` - Input dialogs with validation
- `modal_with_button_demo.py` - Advanced modal with interactive elements
- `centered_dialog.py` - Dialog positioning

### Advanced Examples (`examples/advanced/`)

Complete applications and advanced patterns:

**Complete Applications:**
- `../apps/todo_app.py` - Full-featured todo list with filtering
- `form_demo.py` - Registration form with comprehensive validation
- `data_entry_demo.py` - Business order entry form
- `preferences_demo.py` - Settings/preferences editor
- `dashboard_demo.py` - Multi-panel monitoring dashboard
- `filesystem_browser.py` - File browser with tree view

**Layout & Design:**
- `complex_layout_demo.py` - Nested layouts and sizing
- `splitpanel_nested_demo.py` - Nested split panels (IDE-like three-pane layout)
- `scroll_demo.py`, `scrollable_minimal.py`, `scrollable_children_demo.py` - Scrolling patterns
- `frame_overflow_demo.py` - Frame sizing modes and overflow
- `login_form.py` - Login UI with validation

**Advanced Patterns:**
- `navigation_demo.py` - Multi-view navigation with lifecycle hooks
- `state_management_demo.py` - State watchers, async callbacks, derived state
- `event_patterns_demo.py` - Event scopes, priorities, and propagation
- `error_handling_demo.py` - Error handling and graceful degradation
- `executor_demo.py` - ThreadPoolExecutor configuration
- `context_menu_demo.py` - Right-click context menus
- `rich_content_demo.py` - Combined markdown and code display
- `download_simulator.py` - Progress tracking
- `template_demo.py`, `rich_content_template_demo.py` - Template features

Run any example with:
```bash
python examples/basic/hello_world.py
python examples/widgets/table_demo.py
python examples/apps/todo_app.py
```

See `examples/README.md` for a complete categorized list with descriptions.

## Architecture

Wijjit follows a layered architecture:

```
┌─────────────────────────────────────────────────┐
│              User Application                    │
│  (View functions, state management, handlers)   │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│            Wijjit Core API                      │
│  - App class & view decorator                   │
│  - Navigation system                            │
│  - Global state management                      │
└──────────────┬──────────────────────────────────┘
               │
    ┌──────────┼────────┐
    │          │        │
┌───▼───┐   ┌──▼───┐ ┌──▼────────┐
│Template│  │Layout│ │ Terminal  │
│ Engine │  │Engine│ │  I/O      │
└───┬───┘   └──┬───┘ └──┬────────┘
    │          │        │
┌───▼──────────▼────────▼─────────────────────────┐
│         Rendering Pipeline                      │
│  1. Parse template → Element tree               │
│  2. Calculate layout → Coordinates              │
│  3. Render elements → ANSI strings              │
│  4. Composite → Terminal output                 │
└─────────────────────────────────────────────────┘
```

### Module Structure

- **`wijjit/core/`**: App, state, renderer, events, focus, hover, overlay
- **`wijjit/terminal/`**: ANSI utilities, screen management, input handling, mouse support
- **`wijjit/layout/`**: Layout engine, frames, bounds calculation, scrolling
- **`wijjit/elements/`**: Base classes and all interactive/display elements
- **`wijjit/tags/`**: Jinja2 template tags for UI elements

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/terminal/test_ansi.py -v

# Run with coverage
python -m pytest --cov=src/wijjit --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

## Project Status

Wijjit is approaching its first public release (`0.1.0`). The core framework is
**stable and feature-complete for 0.1.0**, with the full element, layout, event,
and rendering pipelines implemented and covered by a large test suite. A handful
of known limitations remain (see below).

### Working Features ✓

- ✅ Core App API with view decorator
- ✅ State management with change detection and watchers
- ✅ Async/await support for event handlers and callbacks
- ✅ Template rendering with Jinja2
- ✅ Layout engine (VStack, HStack, Frame, SplitPanel)
- ✅ All input elements (TextInput, TextArea, CodeEditor, Button, Checkbox, Radio, Select)
- ✅ All display elements (ContentView, Table, Tree, ListView, LogView, Progress, Spinner, Notification)
- ✅ Data visualization (BarChart, LineChart, ColumnChart, Gauge, HeatMap, Sparkline)
- ✅ Focus management with Tab navigation
- ✅ Mouse support (click, scroll, hover)
- ✅ Scrolling system with scrollbars (vertical and horizontal)
- ✅ Modal/overlay system with dialogs
- ✅ Inline rendering (render_inline, InlineApp with keyboard input)
- ✅ Job control with Ctrl+Z suspend/resume (Unix)
- ✅ Event handling and dispatch
- ✅ ThreadPoolExecutor for non-blocking I/O
- ✅ ANSI-aware text rendering
- ✅ 69 working examples
- ✅ Comprehensive test suite (85%+ coverage)

### Known Limitations

- **Performance**: Not optimized for large datasets (no virtual scrolling)
- **Windows**: Some Unicode characters may not display correctly
- **Plugin System**: Framework is monolithic (no plugin architecture)

### Planned Features (Future)

- Hot reload for templates
- Visual debugger/inspector
- Animation/transition support
- Drag-and-drop manager (callbacks defined, manager not yet implemented)
- Virtual scrolling for large datasets
- Plugin system

## Use Cases

Wijjit is ideal for:

- ✅ CLI tools with styled output (using inline rendering)
- ✅ CLI tools with forms (login, data entry, configuration)
- ✅ System monitoring dashboards
- ✅ File browsers and managers
- ✅ Log viewers and analyzers
- ✅ Data tables with sorting/filtering
- ✅ Interactive configuration editors
- ✅ Terminal-based admin interfaces
- ✅ Progress indicators and status displays

Not recommended for:

- ❌ High-performance real-time applications
- ❌ Applications requiring complex animations
- ❌ Large-scale applications needing code splitting
- ❌ Applications requiring extensive plugin systems

## Dependencies

**Core:**
- `jinja2>=3.1.6` - Template engine
- `prompt-toolkit>=3.0.52` - Terminal I/O
- `rich>=14.2.0` - ANSI rendering and tables
- `pyperclip>=1.11.0` - Clipboard access (copy/paste)
- `tinycss2>=1.5.0` - CSS parsing for theming
- `wcwidth>=0.2.14` - Wide/East-Asian character width

**Optional:**
- `pillow>=12.0.0` - `ImageView` / ASCII image rendering (the `images` extra)

**Development:**
- `pytest>=8.4.2` - Testing
- `pytest-cov>=6.0.0` - Coverage
- `black>=25.9.0` - Code formatting
- `mypy>=1.18.2` - Type checking
- `ruff>=0.14.2` - Linting

## Documentation

- **README.md** (this file) - Overview and quick start
- **CLAUDE.md** - Development guide and architecture
- **docs/** - Full Sphinx documentation (build with `cd docs && make html`)
- **examples/** - 69 working examples
- **tests/** - Comprehensive test suite showing usage patterns

Build the documentation locally:
```bash
cd docs
make html
# Open docs/build/html/index.html in your browser
```

## Contributing

Wijjit is currently in active development. Contributions are welcome!

Areas where contributions would be particularly helpful:
- Performance optimization (virtual scrolling, render caching)
- Windows terminal compatibility improvements
- Additional examples and tutorials
- Bug fixes and edge case handling

## License

MIT License

## Credits

Wijjit is built on the shoulders of giants:
- **Jinja2** for templating
- **prompt-toolkit** for cross-platform terminal I/O
- **Rich** for ANSI rendering and tables

---

**Why "Wijjit"?**

**W**ijjit **I**s **J**ust **J**inja **I**n **T**erminal
