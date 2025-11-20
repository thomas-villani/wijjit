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
- **ANSI-Aware**: Proper handling of colors and styling throughout

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/wijjit.git
cd wijjit

# Install in development mode with uv (recommended)
uv sync --all-extras

# Or with pip
pip install -e .
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
        "template": "Hello, World! Press 'q' to quit.",
    }

@app.on_key("q")
def on_quit():
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

{# Display elements #}
{% table data=state.users columns=["name", "email"] %}{% endtable %}
{% tree data=state.files %}{% endtree %}
{% progress value=state.progress max=100 %}{% endprogress %}
{% markdown content=state.readme %}{% endmarkdown %}
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

### Layout System

Wijjit provides flexible layout containers:

**Frames**: Boxes with borders, titles, and scrolling
```jinja2
{% frame title="Settings" border="single" width=60 height=20 overflow_y="scroll" %}
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

**HStack**: Horizontal stack
```jinja2
{% hstack spacing=2 align_v="middle" %}
  {% button %}Left{% endbutton %}
  {% button %}Right{% endbutton %}
{% endhstack %}
```

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

## Component Library

### Input Components

- **TextInput**: Single-line text input with cursor editing
- **TextArea**: Multi-line text input with scrolling
- **Button**: Clickable button (mouse or keyboard)
- **Checkbox**: Single checkbox or checkbox groups
- **Radio**: Radio button groups
- **Select**: Dropdown select menu

### Display Components

- **Table**: Sortable, scrollable tables (powered by Rich)
- **Tree**: Hierarchical tree view with expand/collapse
- **ListView**: Scrollable list with selection
- **LogView**: Auto-scrolling log viewer
- **ProgressBar**: Progress indicators (bar, dots, spinner styles)
- **Spinner**: Animated loading indicators
- **Markdown**: Markdown rendering with syntax highlighting
- **CodeBlock**: Syntax-highlighted code display

### Layout Components

- **Frame**: Container with borders, titles, padding, and scrolling
- **VStack**: Vertical stack layout
- **HStack**: Horizontal stack layout

## Examples

The `examples/` directory contains **50+ working examples** organized into three categories. All examples use modern patterns with template-based UI and decorator event handlers.

### Basic Examples (`examples/basic/`)

Introductory examples demonstrating core concepts:
- `hello_world.py` - Minimal "Hello World" app
- `simple_input_test.py` - Basic text input with quit handler
- `async_demo.py` - Async/await event handlers
- `mouse_demo.py` - Mouse interaction (clicks, hovers, scrolling)
- `debug_keys.py` - Key event debugging tool
- `alignment_demo.py` - Content alignment in layouts

### Widget Examples (`examples/widgets/`)

Individual UI component demonstrations (20+ widgets):

**Input Elements:**
- `checkbox_demo.py` - Individual checkboxes and checkbox groups
- `radio_demo.py` - Radio button groups with multiple examples
- `select_demo.py`, `dropdown_demo.py` - Dropdown selection menus
- `textarea_demo.py` - Multi-line text input with selection

**Display Elements:**
- `table_demo.py` - Sortable data tables with Rich integration
- `tree_demo.py`, `tree_indicator_styles_demo.py` - Hierarchical tree views
- `listview_demo.py` - Scrollable lists with selection
- `logview_demo.py` - Auto-scrolling log viewer
- `progress_demo.py` - Progress bars and indicators
- `spinner_demo.py` - Loading spinners with animations
- `markdown_demo.py`, `test_markdown_tag.py` - Markdown rendering
- `code_demo.py` - Syntax-highlighted code display
- `statusbar_demo.py` - Status bar component
- `notification_demo.py` - Toast notifications

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
- `todo_app.py` - Full-featured todo list with filtering
- `form_demo.py` - Registration form with comprehensive validation
- `data_entry_demo.py` - Business order entry form
- `preferences_demo.py` - Settings/preferences editor
- `dashboard_demo.py` - Multi-panel monitoring dashboard
- `filesystem_browser.py` - File browser with tree view

**Layout & Design:**
- `complex_layout_demo.py` - Nested layouts and sizing
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
python examples/advanced/todo_app.py
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

Wijjit is **production-ready for many use cases**, with the core framework fully implemented and stable. The project is approximately 70-75% complete compared to the original ambitious roadmap.

### Working Features ✓

- ✅ Core App API with view decorator
- ✅ State management with change detection and watchers
- ✅ Async/await support for event handlers and callbacks
- ✅ Template rendering with Jinja2
- ✅ Layout engine (VStack, HStack, Frame)
- ✅ All input elements (TextInput, TextArea, Button, Checkbox, Radio, Select)
- ✅ All display elements (Table, Tree, ListView, LogView, Progress, Spinner, Markdown, Code)
- ✅ Focus management with Tab navigation
- ✅ Mouse support (click, scroll, hover)
- ✅ Scrolling system with scrollbars
- ✅ Modal/overlay system with dialogs
- ✅ Event handling and dispatch
- ✅ ThreadPoolExecutor for non-blocking I/O
- ✅ ANSI-aware text rendering
- ✅ 50+ working examples
- ✅ Comprehensive test suite (85%+ coverage)

### Known Limitations

- **Performance**: Not optimized for large datasets (no virtual scrolling)
- **Windows**: Some Unicode characters may not display correctly
- **Documentation**: Limited to code comments, examples, and this README
- **Plugin System**: Framework is monolithic (no plugin architecture)

### Planned Features (Future)

- Hot reload for templates
- Visual debugger/inspector
- Animation/transition support
- Drag-and-drop
- Chart/graph components
- Virtual scrolling for large datasets
- Plugin system

## Use Cases

Wijjit is ideal for:

- ✅ CLI tools with forms (login, data entry, configuration)
- ✅ System monitoring dashboards
- ✅ File browsers and managers
- ✅ Log viewers and analyzers
- ✅ Data tables with sorting/filtering
- ✅ Interactive configuration editors
- ✅ Terminal-based admin interfaces

Not recommended for:

- ❌ High-performance real-time applications
- ❌ Applications requiring complex animations
- ❌ Large-scale applications needing code splitting
- ❌ Applications requiring extensive plugin systems

## Dependencies

**Core:**
- `jinja2>=3.1.0` - Template engine
- `prompt-toolkit>=3.0` - Terminal I/O
- `rich>=13.0` - ANSI rendering and tables

**Optional:**
- `pygments>=2.0` - Syntax highlighting for code blocks

**Development:**
- `pytest>=7.0` - Testing
- `pytest-cov>=4.0` - Coverage
- `black>=23.0` - Code formatting
- `mypy>=1.0` - Type checking
- `ruff` - Linting

## Documentation

- **README.md** (this file) - Overview and quick start
- **CLAUDE.md** - Development guide and architecture
- **examples/** - 40+ working examples
- **tests/** - Comprehensive test suite showing usage patterns

Full documentation (Sphinx-based) is in development.

## Contributing

Wijjit is currently in active development. Contributions are welcome!

Areas where contributions would be particularly helpful:
- Performance optimization (virtual scrolling, render caching)
- Windows terminal compatibility improvements
- Additional examples and tutorials
- Documentation (Sphinx docs)
- Bug fixes and edge case handling

## License

[Add your license here]

## Credits

Wijjit is built on the shoulders of giants:
- **Jinja2** for templating
- **prompt-toolkit** for cross-platform terminal I/O
- **Rich** for ANSI rendering and tables

---

**Why "Wijjit"?**

**W**ijjit **I**s **J**ust **J**inja **I**n **T**erminal
