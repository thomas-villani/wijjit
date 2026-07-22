# Wijjit Gallery

A visual tour of what Wijjit apps look like. Every screenshot below is a real
bundled example, captured **headlessly** — no terminal, no window manager, no
screen-recording. The whole page is regenerated with one command:

```bash
uv run python scripts/make_screenshots.py --gallery
```

That is the point of the architecture, not a trick: because the UI is a Jinja2
template rendered to a virtual DOM, `wijjit render` can drive an app with a
scripted key sequence and print the exact screen it would have shown. The demos
that generate sample data seed `random` at import and each render runs in a
throwaway working directory, so the captures are byte-reproducible —
regenerating only changes an image when the example or the framework actually
changed. (The two exceptions are System Monitor and Dashboard, which display a
live clock and real machine metrics.)

The animation below is built the same way — frames captured through
`WijjitHarness` and rasterized with Pillow, no screen-recorder anywhere:

```bash
uv run python scripts/make_demo_gif.py
```

See [README.md](README.md) for the full annotated index of all 74 examples, and
[docs/NEW-ELEMENTS.md](../docs/NEW-ELEMENTS.md) to add your own element.

> **Reproduce any of these yourself.** Each entry lists the exact command. Drop
> `--ansi` for plain text, change `--size`, or add `--keys` to script input.

---

## In motion

Adding a task, tabbing through the list, and checking it off — recorded
headlessly, one captured frame per keystroke.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/todo.gif"
       alt="Animated demo of the todo app: typing a new task, adding it, navigating with Tab, and checking it off" width="700">
</p>

```bash
uv run python scripts/make_demo_gif.py todo
```

---

## Applications

### System Monitor

Live-updating gauges, sparklines and tables — an `htop`-style dashboard built
from templates rather than positioning code.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/system_monitor.svg"
       alt="System monitor demo: CPU and memory gauges, per-core sparklines, and a process table" width="860">
</p>

```bash
wijjit run examples/apps/system_monitor.py
wijjit render examples/apps/system_monitor.py --size 94x30 --tick 2 --ansi
```

### Todo App

Text input, a radio-group filter, a scrollable checklist and a live counter —
state lives in `app.state` and the reconciler preserves cursor and scroll across
re-renders.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/todo.svg"
       alt="Todo app demo: an input row, All/Active/Done filter, and a checkbox list" width="700">
</p>

```bash
wijjit run examples/apps/todo_app.py
wijjit render examples/apps/todo_app.py --size 74x28 --ansi
```

### Spreadsheet

A `DataGrid` with VisiCalc-style cell entry, formulas and keyboard navigation.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/spreadsheet.svg"
       alt="Spreadsheet app demo: a grid of labelled cells with a formula entry row" width="860">
</p>

```bash
wijjit run examples/apps/spreadsheet.py
wijjit render examples/apps/spreadsheet.py --size 92x28 --ansi
```

### Chatbot

A streaming chat log, an input row, and a background task typing the reply in.
Captured with `settle:400`, which pumps event-loop frames until the async reply
finishes -- the headless equivalent of "wait for it".

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/chatbot.svg"
       alt="Chatbot demo: a conversation log with a streamed bot reply, an input row, and Send/Clear buttons" width="820">
</p>

```bash
wijjit run examples/apps/chatbot.py
wijjit render examples/apps/chatbot.py --size 84x30 --keys "tab,tab,type:help,enter,settle:400" --ansi
```

---

## Charts

All six chart elements — sparklines, bar, column and line charts, gauges and a
heatmap — rendered with braille and block glyphs. Multi-series line charts take
their colors from a categorical palette validated for colour-vision deficiency
against both light and dark terminals; override per series with `series_colors`.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/charts.svg"
       alt="Charts demo: sparklines, gauges, bar, column and line charts, and a heatmap" width="900">
</p>

```bash
wijjit run examples/widgets/charts_demo.py
wijjit render examples/widgets/charts_demo.py --size 100x40 --tick 2 --ansi
```

### Dashboard

Charts, gauges and status indicators composed into a single refreshing layout.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/dashboard.svg"
       alt="Dashboard demo: metric tiles, gauges and charts in a multi-column layout" width="880">
</p>

```bash
wijjit run examples/advanced/dashboard_demo.py
wijjit render examples/advanced/dashboard_demo.py --size 98x32 --tick 2 --ansi
```

---

## Layout

### Nested Split Panels

Draggable, collapsible, nestable split panels with keyboard resize.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/splitpanel_nested.svg"
       alt="Nested split panel demo: a vertical split containing two horizontal splits" width="860">
</p>

```bash
wijjit run examples/advanced/splitpanel_nested_demo.py
wijjit render examples/advanced/splitpanel_nested_demo.py --size 92x28 --ansi
```

### HStack Flexbox

`justify`, `wrap`, `gap` / `row_gap` / `column_gap` — CSS flexbox semantics on
a terminal grid.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/hstack_flexbox.svg"
       alt="HStack flexbox demo: rows of boxes showing justify and wrap behaviour" width="820">
</p>

```bash
wijjit run examples/basic/hstack_flexbox_demo.py
wijjit render examples/basic/hstack_flexbox_demo.py --size 86x26 --ansi
```

### Grid

Grid layout basics — the starting point for most multi-pane apps.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/grid.svg"
       alt="Grid layout demo: labelled cells arranged in a fixed grid" width="720">
</p>

```bash
wijjit run examples/basic/grid_demo.py
wijjit render examples/basic/grid_demo.py --size 76x24 --ansi
```

---

## Data Display

### Table

Rich-powered, sortable, scrollable tables.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/table.svg"
       alt="Table demo: a bordered table with sortable column headers" width="840">
</p>

```bash
wijjit run examples/widgets/table_demo.py
wijjit render examples/widgets/table_demo.py --size 88x28 --ansi
```

### Tree

Hierarchical tree with expand/collapse and single or multi-select.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/tree.svg"
       alt="Tree view demo: a nested, expandable tree of nodes" width="700">
</p>

```bash
wijjit run examples/widgets/tree_demo.py
wijjit render examples/widgets/tree_demo.py --size 74x26 --ansi
```

### DataGrid

Spreadsheet-style data entry, with optional pandas interop.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/datagrid.svg"
       alt="DataGrid demo: an editable grid of rows and typed columns" width="860">
</p>

```bash
wijjit run examples/widgets/datagrid_demo.py
wijjit render examples/widgets/datagrid_demo.py --size 92x26 --ansi
```

### LogView

Streaming log viewer with level colouring and ANSI passthrough.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/logview.svg"
       alt="LogView demo: colour-coded log lines streaming in a scrollable pane" width="860">
</p>

```bash
wijjit run examples/widgets/logview_demo.py
wijjit render examples/widgets/logview_demo.py --size 92x28 --ansi
```

### ImageView

Real images in the terminal, in three rendering modes — half-block colour,
2x2 quadrant colour, and monochrome braille. Needs the `images` extra:
`pip install "wijjit[images]"`.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/imageview.svg"
       alt="ImageView demo: the same image rendered in colour, quadrant and braille modes" width="880">
</p>

```bash
wijjit run examples/widgets/imageview_demo.py
wijjit render examples/widgets/imageview_demo.py --size 96x30 --ansi
```

---

## Input & Overlays

### Form

Text inputs, selects, checkboxes and validation wired to `@app.on_action`.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/form.svg"
       alt="Form demo: a labelled form with text inputs, a select and checkboxes" width="760">
</p>

```bash
wijjit run examples/advanced/form_demo.py
wijjit render examples/advanced/form_demo.py --size 80x30 --ansi
```

### Login Form

The smallest interesting interactive app — captured mid-typing by a scripted
key run, which is exactly how its regression test drives it.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/login.svg"
       alt="Login form demo with username and masked password filled in" width="620">
</p>

```bash
wijjit run examples/advanced/login_form.py
wijjit render examples/advanced/login_form.py --size 60x18 --keys "tab,type:admin,tab,type:hunter2" --ansi
```

### Dialogs

Modal overlays with focus trapping and click-outside handling. Captured with
`--keys d` to pop the confirmation open.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/dialogs.svg"
       alt="Confirm dialog demo: a modal delete confirmation over a file list" width="760">
</p>

```bash
wijjit run examples/widgets/confirm_dialog_demo.py
wijjit render examples/widgets/confirm_dialog_demo.py --size 80x26 --keys "d" --ansi
```

### Tabbed Panel

Tabbed navigation with per-tab content.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/tabbedpanel.svg"
       alt="Tabbed panel demo: a tab strip above the selected tab's content" width="780">
</p>

```bash
wijjit run examples/widgets/tabbedpanel_demo.py
wijjit render examples/widgets/tabbedpanel_demo.py --size 82x26 --ansi
```

### Autocomplete

A suggestion dropdown over a text input, captured after typing `py`.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/autocomplete.svg"
       alt="Autocomplete demo: a suggestion dropdown open beneath a text input" width="720">
</p>

```bash
wijjit run examples/basic/autocomplete_demo.py
wijjit render examples/basic/autocomplete_demo.py --size 76x24 --keys "type:py" --ansi
```

---

## Editing & Theming

### Code Editor

Syntax highlighting via Pygments, plus autocomplete.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/code_editor.svg"
       alt="Code editor demo: syntax-highlighted Python with line numbers" width="860">
</p>

```bash
wijjit run examples/widgets/code_editor_demo.py
wijjit render examples/widgets/code_editor_demo.py --size 92x30 --ansi
```

### CSS Theming

Themes loaded from a real CSS file via `tinycss2`.

<p align="center">
  <img src="https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/gallery/css_theme.svg"
       alt="CSS theme demo: widgets restyled by a custom CSS theme file" width="820">
</p>

```bash
wijjit run examples/styling/css_theme_demo.py
wijjit render examples/styling/css_theme_demo.py --size 84x28 --ansi
```

---

## Adding a screenshot

Add an entry to `GALLERY` in [`scripts/make_screenshots.py`](../scripts/make_screenshots.py):

```python
(
    "my_demo",                          # output slug -> gallery/my_demo.svg
    "examples/widgets/my_demo.py",      # example to drive
    (84, 26),                           # (cols, rows)
    "tab,type:hello,enter",             # scripted keys ("" for the initial screen)
    0,                                  # animation frames to tick first
    "wijjit - my_demo.py",              # SVG window title
),
```

Then regenerate and add a section here. If the demo generates sample data from
`random`, seed it at module import first — otherwise every regeneration rewrites
the SVG with different data.
