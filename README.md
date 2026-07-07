# Wijjit

**Flask for the Console: A declarative TUI framework for Python**

*Wijjit is Just Jinja in Terminal*

[![PyPI version](https://img.shields.io/pypi/v/wijjit.svg)](https://pypi.org/project/wijjit/)
[![Python versions](https://img.shields.io/pypi/pyversions/wijjit.svg)](https://pypi.org/project/wijjit/)
[![CI](https://github.com/thomas-villani/wijjit/actions/workflows/ci.yml/badge.svg)](https://github.com/thomas-villani/wijjit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/thomas-villani/wijjit/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://thomas-villani.github.io/wijjit/)

---

Wijjit is a Python framework for building Terminal User Interfaces (TUIs) using familiar web development patterns.
If you know Flask and Jinja2, you can build rich, interactive console applications with Wijjit.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/charts.svg"
       alt="Wijjit charts demo: sparklines, gauges, bar/column/line charts and a heatmap rendered in the terminal"
       width="850">
</p>

Wijjit was obviously inspired by the wonderful Flask library, and makes heavy use of the patterns innate to Flask
applications. We built this library to bring the syntactic elegance of Flask's decorator patterns to building TUIs.

## Why Wijjit?

The terminal-UI space in Python already has great tools, and Wijjit is deliberately a different point on the spectrum:

- **[Rich](https://github.com/Textualize/rich)** is for *output* — beautiful styled text, tables, and progress bars printed to the terminal. Wijjit uses Rich internally for exactly that, then adds a full interactive application layer on top (focus, events, overlays, re-rendering).
- **[Textual](https://github.com/Textualize/textual)** is a full app framework built around object-oriented widgets composed in Python and styled with a CSS-like language. It's powerful and deep.
- **Wijjit** takes the *web* mental model instead of the widget-tree one: you write **Jinja2 templates** for layout and **Flask-style decorators** (`@app.view`, `@app.on_action`, `@app.on_key`) for behavior, backed by reactive `State`. If you've built a Flask app, the structure is immediately familiar — views return templates, state changes trigger re-renders, and a virtual-DOM reconciler makes those re-renders cheap.

If you think in templates and request handlers rather than widget classes, Wijjit will feel like home.

## Features

- **Declarative UI**: Define layouts using Jinja2 templates, not procedural positioning code
- **Flask-like API**: View decorators, routing, and state management that feels like web development
- **Rich Component Library**: 30+ elements — forms, tables, trees, charts, editors, dialogs, and more
- **Reactive State Management**: State changes automatically trigger re-renders
- **Automatic Focus Navigation**: Tab/Shift+Tab navigation between interactive elements
- **Modal Dialogs**: Built-in confirm, alert, and input dialogs
- **Layout System**: Flexible frames with stacks (vertical/horizontal), split panels, scrolling, and flexbox-style sizing
- **Mouse Support**: Click buttons, scroll content, and interact with elements
- **Inline Rendering**: Output styled UI to terminal scrollback without alternate screen
- **Developer Tooling**: A `wijjit` CLI (`validate`/`tree`/`render`) and a pytest harness for driving apps headlessly — an LLM-friendly path to inspect and test TUIs
- **ANSI-Aware**: Proper handling of colors and styling throughout

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
# Add to your project using uv (recommended)
uv add wijjit

# Optional extra for ImageView / ASCII image rendering (Pillow)
uv add "wijjit[images]"

# Or with pip from PyPI
pip install wijjit

# Optional extras
pip install "wijjit[images]"   # ImageView / ASCII image rendering (Pillow)
```

> **Clipboard note (Linux):** copy/paste uses the system clipboard via
> `pyperclip`, which needs `xclip` or `xsel` installed. Without them, Wijjit
> falls back to an internal in-process clipboard (copy/paste still works inside
> the app, just not across other programs).

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
from wijjit import Wijjit, render_template_string

app = Wijjit()

@app.view("main", default=True)
def main_view():
    return render_template_string("""
{% frame %}
Hello, World! Press 'q' to quit.
{% endframe %}
""")

@app.on_key("q")
def on_quit(event):
    app.quit()

if __name__ == "__main__":
    app.run()
```

### Login Form

A complete login form with validation, showing the power of templates:

```python
from wijjit import Wijjit, render_template_string

app = Wijjit(initial_state={
    'username': '',
    'password': '',
    'status': 'Please enter your credentials',
})

@app.view("login", default=True)
def login_view():
    return render_template_string("""
{% frame title="Login" border="single" width=50 height=15 %}
  {% vstack spacing=1 padding=1 %}
    {{ state.status }}

    {% vstack spacing=0 %}
      Username:
      {% textinput id="username" placeholder="Enter username" width=30 %}{% endtextinput %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Password:
      {% textinput id="password" placeholder="Enter password" width=30 password=True action="login" %}{% endtextinput %}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button action="login" %}Login{% endbutton %}
      {% button action="clear" %}Clear{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """)

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

That login form renders like this (the password field masks input with `password=True`):

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/login.svg"
       alt="Wijjit login form with a masked password field" width="480">
</p>

## Screenshots

<table>
  <tr>
    <td width="50%">
      <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/todo.svg"
           alt="Todo app: input, filter buttons, checkbox list, and status bar" width="100%"><br>
      <sub><code>examples/apps/todo_app.py</code> — a complete app: add/toggle/filter with a status bar.</sub>
    </td>
    <td width="50%">
      <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/code_editor.svg"
           alt="Syntax-highlighted code editor with language and theme switchers" width="100%"><br>
      <sub><code>examples/widgets/code_editor_demo.py</code> — syntax highlighting with language/theme switching.</sub>
    </td>
  </tr>
</table>

All screenshots are generated headlessly and reproducibly by
[`scripts/make_screenshots.py`](scripts/make_screenshots.py). Run any of the
72 bundled examples yourself with `python examples/<dir>/<name>.py`.

## Core Concepts

### Views and Routing

Like Flask, Wijjit uses decorators to define views. A view returns
`render_template_string(...)` for an inline template or `render_template(...)`
for a file in your `templates/` directory; lifecycle hooks go on the decorator:

```python
from wijjit import render_template_string, render_template

@app.view("main", default=True, on_enter=fn, on_exit=fn)
def main_view():
    # Inline template + context (state is auto-injected):
    return render_template_string("...", title="Home", items=items)

@app.view("dashboard")
def dashboard_view():
    # Or load templates/dashboard.tui:
    return render_template("dashboard.tui", stats=get_stats())

# Navigate to a different view
app.navigate("other_view", param=value)
```

File templates live in a `templates/` directory next to your app module
(auto-discovered, Flask-style) or wherever `Wijjit(template_dir=...)` points.

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

def setup_handlers():
    def on_key(event):
        if event.key == "q":
            app.quit()

    app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main")

@app.view("main", default=True, on_enter=setup_handlers)
def main_view():
    return render_template_string("...")
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

Wijjit composes UIs from a handful of layout containers. Sizes accept a fixed
integer (`width=50`), `"fill"` (take remaining space), `"auto"` (size to
content), or a percentage (`"50%"`).

```jinja2
{# Frame: a bordered, optionally-scrollable box #}
{% frame title="Settings" border="single" width=60 height=20 scrollable=True %}
  {% vstack spacing=1 align_h="center" %}   {# vertical stack #}
    Top
    Bottom
  {% endvstack %}
{% endframe %}

{# HStack: horizontal stack with flexbox-style justify + wrap #}
{% hstack justify="space-between" wrap=True gap=1 width="fill" %}
  {% for tag in tags %}
    {% button %}{{ tag }}{% endbutton %}
  {% endfor %}
{% endhstack %}

{# SplitPanel: draggable, resizable, collapsible divider #}
{% splitpanel orientation="horizontal" ratio="30:70" id="main_split" %}
  {% frame title="Sidebar" %}Navigation{% endframe %}
  {% frame title="Main" %}Content{% endframe %}
{% endsplitpanel %}

{# Pager: wizard-style pagination #}
{% pager id="wizard" nav_position="bottom" show_indicator=True %}
  {% page title="Welcome" %}Step one{% endpage %}
  {% page title="Done" %}All set!{% endpage %}
{% endpager %}
```

Each container has a fuller set of attributes (`justify`/`wrap`/`gap` on HStack,
`collapsible`/`divider_style` on SplitPanel, `loop`/`nav_position` on Pager, …).
See the [Layout guide](https://thomas-villani.github.io/wijjit/) for the complete
reference.

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
    on_ok=lambda: app.navigate("main")
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

Wijjit ships 30+ elements. Each has a template tag and a Python class; see the
[component reference](https://thomas-villani.github.io/wijjit/) for every
attribute.

- **Input**: TextInput (with `password` masking), TextArea, CodeEditor
  (syntax-highlighted, 500+ languages), DataGrid (spreadsheet-style), Button,
  Checkbox, Radio, Select (single/multi), Slider, Toggle, Link.
- **Display**: ContentView (plain/ANSI/HTML/Markdown/Rich/code), Table
  (sortable, Rich-powered), Tree (single/multi-select), ListView, LogView,
  ProgressBar, Spinner, StatusIndicator, Notification.
- **Charts**: BarChart, ColumnChart, LineChart (braille), Gauge, HeatMap,
  Sparkline — all support a `color` override.
- **Layout**: Frame, VStack, HStack, SplitPanel, TabbedPanel, Pager.
- **Dialogs & menus**: ConfirmDialog, AlertDialog, TextInputDialog, DropdownMenu,
  ContextMenu.

## Examples

The `examples/` directory contains **72 working examples** in five categories —
`basic/` (15), `widgets/` (30), `advanced/` (22), `styling/` (2), and `apps/`
(3) — all using template-based UI and decorator event handlers.

```bash
python examples/basic/hello_world.py     # smallest possible app
python examples/widgets/table_demo.py    # a single widget in focus
python examples/apps/todo_app.py         # a complete application
```

Highlights: `apps/todo_app.py` (full todo app), `apps/chatbot.py` (streaming
chat), `apps/spreadsheet.py` (editable DataGrid + live chart), `widgets/charts_demo.py`
(all six charts), `advanced/dashboard_demo.py` (monitoring dashboard), and
`advanced/filesystem_browser.py` (tree-based file browser). See
[`examples/README.md`](examples/README.md) for the full categorized catalog.

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

## Developer Tooling & Testing

Wijjit ships a `wijjit` command-line tool for inspecting, validating, and
driving apps - useful both for humans and for LLM agents diagnosing layout or
template issues. `validate` and `tree` accept **either** a raw template file
(`.wij` / `.html` / `.txt`) **or** a full example `.py` app (auto-detected by
the `.py` suffix).

```bash
# Lint a template (or app): reports syntax errors, unknown tags, undefined
# variables, unknown element types/attributes. Add --render for a snapshot.
wijjit validate myform.wij --render
wijjit validate examples/advanced/login_form.py
wijjit validate myform.wij --json          # machine-readable findings

# Dump the VNode "DOM" tree a template produces (text or JSON)
wijjit tree myform.wij
wijjit tree myform.wij --json
wijjit tree myform.wij --context ctx.json --size 100x30

# Render an app headlessly with scripted input (ports python -m wijjit.testing)
wijjit render examples/widgets/spinner_demo.py --tick 5
wijjit render examples/advanced/login_form.py \
    --size 100x30 --keys "tab,type:admin,tab,type:secret,enter" --ansi

# Launch a .py app interactively in this terminal
wijjit run examples/advanced/login_form.py

# Run your test suite (passthrough to pytest)
wijjit test -k login tests/
```

`python -m wijjit <command>` works as well, and the older
`python -m wijjit.testing <example>` still drives the headless renderer.

### Testing your own apps

Installing Wijjit registers a **pytest plugin** that provides `wijjit_harness`
and `wijjit_make_app` fixtures (opt out with `-p no:wijjit`). The fixture names
are `wijjit_`-prefixed so they never shadow your own fixtures. The
`wijjit_harness` fixture builds and starts a `WijjitHarness` from a `Wijjit` app
**or** a bare template string, and closes it automatically at teardown:

```python
TEMPLATE = """
{% frame title="Login" width=40 height=8 %}
  {% textinput id="user" width=20 %}{% endtextinput %}
  {% button id="ok" action="login" %}Log in{% endbutton %}
{% endframe %}
"""

def test_login_flow(wijjit_harness):
    h = wijjit_harness(TEMPLATE, state={"user": ""})
    h.press("tab"); h.type("admin"); h.press("tab"); h.press("enter")
    h.assert_text("admin")
    h.assert_tree_contains(type="Button", key="ok")
    h.assert_no_errors()
```

Build an app from a template without a fixture (e.g. for non-pytest scripts)
with `app_from_template`:

```python
from wijjit import app_from_template
from wijjit.testing import WijjitHarness

app = app_from_template(TEMPLATE, state={"user": ""},
                        actions={"login": my_login_handler})
with WijjitHarness(app) as h:
    ...
```

New `WijjitHarness` assertions: `assert_no_errors()` (no render/handler errors),
`assert_tree_contains(type=, key=, props=)`, and `assert_screen(snapshot)` (for
a syrupy snapshot). The `wijjit_app` / `wijjit_snapshot` markers are registered
by the plugin.

## Project Status

Wijjit `0.1.0` is the first public release. The core framework is
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
- ✅ 72 working examples
- ✅ Comprehensive test suite (3,000+ tests)

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
- `prompt-toolkit>=3.0.36` - Terminal I/O
- `rich>=13.7.1` - ANSI rendering and tables
- `pygments>=2.15.0` - Syntax highlighting (CodeEditor)
- `pyperclip>=1.8.2` - Clipboard access (copy/paste)
- `tinycss2>=1.2.1` - CSS parsing for theming
- `wcwidth>=0.2.5` - Wide/East-Asian character width

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
- **examples/** - 72 working examples
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
