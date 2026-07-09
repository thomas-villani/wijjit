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

## Why Wijjit?

The terminal-UI space in Python already has great tools, and Wijjit is deliberately a different point on the spectrum:

- **[Rich](https://github.com/Textualize/rich)** is for *output* — beautiful styled text, tables, and progress bars printed to the terminal. Wijjit uses Rich internally for exactly that, then adds a full interactive application layer on top (focus, events, overlays, re-rendering).
- **[Textual](https://github.com/Textualize/textual)** is a full app framework built around object-oriented widgets composed in Python and styled with a CSS-like language. It's powerful and deep.
- **Wijjit** takes the *web* mental model instead of the widget-tree one: you write **Jinja2 templates** for layout and **Flask-style decorators** (`@app.view`, `@app.on_action`, `@app.on_key`) for behavior, backed by reactive `State`. A virtual-DOM reconciler diffs re-renders so cursor, scroll, and selection state survive them.

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
- **Job Control**: Ctrl+Z suspend/resume support on Unix systems (Linux, macOS)
- **ANSI-Aware**: Proper handling of colors and styling throughout

## Installation

```bash
# Add to your project using uv (recommended)
uv add wijjit

# Or with pip from PyPI
pip install wijjit

# Optional extra for ImageView / ASCII image rendering (Pillow)
uv add "wijjit[images]"
pip install "wijjit[images]"
```

Wijjit requires Python 3.11+ and is tested on Linux, macOS, and Windows.

> **Clipboard note (Linux):** copy/paste uses the system clipboard via
> `pyperclip`, which needs `xclip` or `xsel` installed. Without them, Wijjit
> falls back to an internal in-process clipboard (copy/paste still works inside
> the app, just not across other programs).

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
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """)

@app.on_action("login")
def handle_login(event):
    if app.state['username'] == 'admin' and app.state['password'] == 'password':
        app.state['status'] = 'Success! Welcome, admin!'
    else:
        app.state['status'] = 'Error: Invalid credentials'

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
    # Or load templates/dashboard.wij.j2:
    return render_template("dashboard.wij.j2", stats=get_stats())

# Navigate to a different view
app.navigate("other_view", param=value)
```

File templates live in a `templates/` directory next to your app module
(auto-discovered, Flask-style) or wherever `Wijjit(template_dir=...)` points.
They are conventionally named `*.wij.j2` so editors syntax-highlight them as
Jinja, but the extension is not enforced.

Pass changing values as **context kwargs** rather than interpolating them into
the template *source* string — the source is compiled once and cached.

### State Management

Wijjit provides reactive state that automatically triggers re-renders when changed:

```python
# Initialize with state
app = Wijjit(initial_state={'count': 0})

# Access state (dict-style or attribute-style)
app.state['count'] = 1
app.state.count = 2

# State changes automatically re-render the UI.
# Elements with matching IDs automatically bind to state.
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

{# Multi-select elements - state holds lists #}
{% select id="toppings" multiple=True %}
  {"value": "cheese", "label": "Cheese"}
  {"value": "pepperoni", "label": "Pepperoni"}
{% endselect %}

{# Display elements #}
{% table data=state.users columns=["name", "email"] %}{% endtable %}
{% tree data=state.files %}{% endtree %}
{% progressbar value=state.progress max_value=100 %}{% endprogressbar %}
{% contentview content_type="markdown" content=state.readme %}{% endcontentview %}
```

### Event Handling

Handle user interactions with decorators:

```python
# Action handlers (from buttons, inputs with an `action` attribute)
@app.on_action("submit")
def handle_submit(event):
    ...

# Key handlers
@app.on_key("ctrl+s")
def save(event):
    ...
```

Elements also expose callback attributes for direct event handling —
`on_double_click`, `on_context_menu`, `Table.on_row_click`,
`TextInput.on_submit`, and low-level drag-and-drop hooks. See the
[event handling guide](https://thomas-villani.github.io/wijjit/user_guide/event_handling.html)
for the complete reference.

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

See the [Layout guide](https://thomas-villani.github.io/wijjit/user_guide/layout_system.html)
for the complete reference.

### Modal Dialogs

```python
from wijjit import ConfirmDialog, AlertDialog, TextInputDialog

dialog = ConfirmDialog(
    title="Confirm",
    message="Are you sure?",
    on_confirm=lambda: print("Confirmed!"),
    on_cancel=lambda: print("Cancelled"),
)
app.show_modal(dialog)
```

`AlertDialog` and `TextInputDialog` follow the same shape.

### Inline Rendering

For CLI tools that don't need full-screen mode, Wijjit renders styled content
directly to terminal scrollback:

```python
from wijjit import render_inline

render_inline('''
{% frame title="Results" border="rounded" %}
  {% vstack %}
    Status: {{ status }}
    Count: {{ count }}
  {% endvstack %}
{% endframe %}
''', status="Complete", count=42)
```

`InlineApp` extends this to interactive, in-place-updating output (progress
bars, live status, even keyboard input) without taking over the screen:

```python
import asyncio
from wijjit import InlineApp

async def main():
    template = '{% progressbar value=state.progress max_value=100 %}{% endprogressbar %}'
    async with InlineApp(template, initial_state={"progress": 0}) as app:
        for i in range(101):
            app.state.progress = i
            await asyncio.sleep(0.05)

asyncio.run(main())
```

## Component Library

Wijjit ships 30+ elements. Each has a template tag and a Python class; see the
[component reference](https://thomas-villani.github.io/wijjit/user_guide/components.html)
for every attribute.

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

## Performance

Wijjit renders through a virtual DOM into a cell-based screen buffer, then
writes only the cells that actually changed.

On a 200x60 terminal, a full repaint of a dashboard (a table, two charts, and a
button row) writes **15,949 bytes**. Advancing the sparkline by one tick writes
**39 bytes**. A frame in which nothing changed writes **nothing at all**. That
is what keeps a Wijjit app flicker-free and responsive over SSH.

| Dashboard frame | 80x24 | 200x60 |
| --- | --- | --- |
| Bytes written, full repaint | 3,696 B | 15,949 B |
| Bytes written, one change | 39 B | 39 B |
| Bytes written, idle frame | 0 B | 0 B |
| Render time, full repaint | ~7 ms | ~20 ms |
| Render time, one change | ~8 ms | ~25 ms |

Reproduce with `uv run python scripts/bench_perf.py`. The byte counts are
deterministic and regression-tested; the timings come from one Windows machine,
vary by tens of percent with system load, and are rounded accordingly.

Note that the diff renderer costs slightly *more* CPU than a blind repaint — it
compares every cell — and buys a large reduction in terminal I/O in exchange.
The [performance guide](https://thomas-villani.github.io/wijjit/user_guide/performance.html)
has the full picture, including how to profile your own app.

## Accessibility

Wijjit honors the [`NO_COLOR`](https://no-color.org/) environment variable and
can fall back to ASCII box-drawing, so apps stay usable on limited terminals:

```bash
NO_COLOR=1 python myapp.py                       # no ANSI color
WIJJIT_UNICODE_SUPPORT=disable python myapp.py   # ASCII borders, not box-drawing
```

Under `NO_COLOR`, text attributes such as bold and reverse video are preserved,
so focus and selection remain visible without relying on color.

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

## Developer Tooling & Testing

Wijjit ships a `wijjit` command-line tool for inspecting, validating, and
driving apps — useful both for humans and for LLM agents diagnosing layout or
template issues. `validate` and `tree` accept **either** a raw template file
**or** a full `.py` app (auto-detected by the `.py` suffix).

```bash
# Lint a template (or app): reports syntax errors, unknown tags, undefined
# variables, unknown element types/attributes. Add --render for a snapshot.
wijjit validate myform.wij.j2 --render
wijjit validate examples/advanced/login_form.py
wijjit validate myform.wij.j2 --json       # machine-readable findings

# Dump the VNode "DOM" tree a template produces (text or JSON)
wijjit tree myform.wij.j2 --json
wijjit tree myform.wij.j2 --context ctx.json --size 100x30

# Render an app headlessly with scripted input
wijjit render examples/widgets/spinner_demo.py --tick 5
wijjit render examples/advanced/login_form.py \
    --size 100x30 --keys "tab,type:admin,tab,type:secret,enter" --ansi

# Launch a .py app interactively, or run your tests
wijjit run examples/advanced/login_form.py
wijjit test -k login tests/
wijjit --version
```

`python -m wijjit <command>` works as well.

### Testing your own apps

Installing Wijjit registers a **pytest plugin** providing `wijjit_harness` and
`wijjit_make_app` fixtures (opt out with `-p no:wijjit`). The harness drives a
real app without a TTY, feeding scripted keys and mouse events through the
actual event-loop dispatch:

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

Outside pytest, `app_from_template(...)` builds a drivable app from a bare
template. See the
[testing guide](https://thomas-villani.github.io/wijjit/user_guide/testing_apps.html).

## Project Status

Wijjit `0.1.0` is the first public release. The core framework is stable and
feature-complete for this milestone: the element, layout, event, and rendering
pipelines are all implemented and covered by roughly 3,000 tests running on
Linux, macOS, and Windows across Python 3.11–3.13.

See the [CHANGELOG](CHANGELOG.md) for what shipped and
[`roadmap.md`](roadmap.md) for what's next.

### Known limitations

- **No virtual scrolling.** Every row of a `Table`, `ListView`, or `Tree` is
  laid out on each render. A few thousand rows is comfortable; a hundred
  thousand is not — page or filter large datasets before rendering them.
- **Wide characters render at single width.** The screen buffer models one cell
  per column, so CJK text and emoji can misalign. Tracked for 0.1.1.
- **No plugin system and no hot template reload.** Both are on the roadmap.
- **Some Windows alt-key combinations** are not delivered by the underlying
  terminal input layer.

## Documentation

- **[Full documentation](https://thomas-villani.github.io/wijjit/)** — guides and API reference
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — development setup, tests, and the CI gates
- **[CLAUDE.md](CLAUDE.md)** — architecture guide for AI agents working in this repo
- **`examples/`** — 72 working examples
- **`tests/`** — a large test suite that doubles as usage documentation

Build the docs locally with `cd docs && make html`.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup and
the CI gates (`black`, `ruff`, `mypy --strict`, `pytest`).

Areas where help would be particularly valuable:

- Performance optimization (virtual scrolling, render caching)
- Wide-character / East-Asian text support in the screen buffer
- Windows terminal compatibility
- Additional examples and tutorials

## License

MIT License. See [LICENSE](LICENSE).

## Credits

Wijjit is built on the shoulders of giants: **Jinja2** for templating,
**prompt-toolkit** for cross-platform terminal I/O, and **Rich** for ANSI
rendering and tables.

---

**Why "Wijjit"?**

**W**ijjit **I**s **J**ust **J**inja **I**n **T**erminal
