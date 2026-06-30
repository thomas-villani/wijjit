# CLAUDE.md

Guidance for AI agents (Claude Code and others) working in this repository.
This is the canonical, version-controlled project guide; Claude Code loads it
automatically.

## Project Overview

**Wijjit** is a declarative TUI (Terminal User Interface) framework for Python
that brings web development patterns to terminal applications. The tagline is
"Flask for the Console" - it uses Jinja2 templates for UI definition and
provides a Flask-like API with view decorators and reactive state management.

**Target Use Case**: Build rich, interactive CLI tools using familiar web
patterns instead of procedural positioning code.

**Status**: Pre-release (current version `0.1.0a1`), working toward a `0.1.0`
PyPI release. Core framework is complete and stable; ~2480 tests pass. See
`RELEASE_PLAN.md` for the remaining path to release.

## Environment & Tooling

- Package management uses **`uv`** (per user's global instruction).
- Primary dev platform is **Windows**; the virtualenv is at `.venv/`
  (`./.venv/Scripts/python.exe`). A WSL venv (`.venv-wsl/`) may also exist.
- CI runs on Linux/macOS/Windows x Python 3.11/3.12/3.13 (`.github/workflows/ci.yml`).

### Testing

```bash
# All tests (Windows venv)
.venv/Scripts/python.exe -m pytest

# Verbose / single file / short tracebacks
.venv/Scripts/python.exe -m pytest tests/ -v
.venv/Scripts/python.exe -m pytest tests/core/test_state.py -v
.venv/Scripts/python.exe -m pytest tests/ -v --tb=short -q

# Skip the benchmark suite for a faster run
.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/benchmarks -q
```

Tests live under `tests/{layer}/test_{module}.py`. There are also
`tests/e2e/`, `tests/integration/`, `tests/golden/`, `tests/benchmarks/`, and
snapshot tests (syrupy). Use `@pytest.mark.asyncio` (or rely on
`asyncio_mode = "auto"`) for async tests.

**Headless harness:** `wijjit.testing.WijjitHarness` drives a real app without
a TTY - it feeds scripted keys/mouse through the actual event-loop dispatch and
exposes the rendered screen as text/ANSI. Use it to reproduce and regression-
test visual/interaction bugs:

```python
from wijjit.testing import WijjitHarness
with WijjitHarness(app, size=(80, 24)) as h:
    h.press("tab"); h.type("admin"); h.press("enter")
    h.click(10, 6)            # routed through mouse_router
    h.tick(frames=3)          # advance spinner/animation frames
    print(h.screen())         # plain text;  h.screen_ansi() for styling
    h.assert_text("Welcome")
```

**Driving the examples headlessly:** `wijjit.testing.load_example_app(path)`
execs any demo and returns its (un-run) `Wijjit` app, so you can drive it through
the harness. The CLI prints a demo's screen without a TTY - ideal for inspecting
a visual bug:

```bash
.venv/Scripts/python.exe -m wijjit.testing examples/advanced/login_form.py \
    --size 100x30 --keys "tab,type:admin,tab,type:secret,enter" --ansi
```

`tests/examples/test_examples_render.py` exercises every driveable example
(non-blank smoke assert) plus curated initial-screen text goldens (regenerate
with `pytest --golden-update`). Four inline-subsystem / raw-terminal demos and a
couple of `Renderer`-only diagnostics are not harness-driveable and are skipped
there with reasons.

### Code Quality (CI gates)

```bash
.venv/Scripts/python.exe -m black src/ tests/     # format
.venv/Scripts/python.exe -m ruff check src/ tests/ # lint (CI: ruff check src/)
.venv/Scripts/python.exe -m mypy src/              # types (CI: strict)
```

> NOTE: both `ruff check src/` and `mypy --strict src/` are clean, so the CI
> `lint` job is green. A pragmatic set of targeted `[[tool.mypy.overrides]]`
> blocks in `pyproject.toml` relaxes a few structural-gap modules (layout/engine,
> core/renderer, core/wiring, ...); everything else is fully strict. See
> `RELEASE_PLAN.md` Phase 3.

### Building

```bash
uv build   # produces dist/wijjit-<version>-py3-none-any.whl and .tar.gz
```

Version is sourced from `wijjit.__version__` (single source of truth) via
hatchling dynamic versioning. Do **not** add a literal `version =` to the
`[project]` table.

## Architecture Overview

Wijjit follows a layered architecture similar to web frameworks. The rendering
pipeline is built around a **virtual DOM + reconciler** (React-like):

```
Template (Jinja2 + custom tags)
        |  render
        v
VNode tree  (immutable descriptions, src/wijjit/core/vdom.py)
        |  reconcile (diff old vs new)
        v
Element tree  (stateful objects; reused across renders where possible)
        |  layout (engine.py -> Bounds)
        v
PaintContext -> ScreenBuffer (cells)
        |  diff render
        v
ANSI output -> terminal
```

Key idea: templates produce **VNodes**, not elements directly. The `Reconciler`
diffs the new VNode tree against the previous one and creates/updates/replaces/
deletes the corresponding stateful `Element` objects, reusing existing elements
(and their transient UI state) where possible. This makes re-renders cheap and
preserves cursor/scroll/selection state across renders.

### Core Layer (`src/wijjit/core/`)

- **app.py** - Main `Wijjit` application class. Flask-like API: view
  decorators, `on_action`/`on_key` handlers, state, navigation, config.
- **vdom.py** - `VNode` (immutable element description) and `EPHEMERAL_PROPS`
  (transient props like cursor/scroll/selection/focus that are NOT synced from
  the template during reconciliation, so they survive re-renders).
- **reconciler.py** - The diffing/patching algorithm (`DiffType`,
  `DiffResult`, `Reconciler`). Compares VNode trees and patches the element tree.
- **element_registry.py** - `ElementRegistry` maps VNode type names to element
  factories (e.g. `"TextInput" -> TextInput`). Supports aliases
  (`"Progress"->ProgressBar`, `"Tree"->TreeView`, `"Image"->ImageView`, etc.).
- **render_context.py** - Thread-safe, contextvar-based render state
  (`render_context_scope`, `get_render_context`). Replaced the old
  `environment.globals` pattern; holds `layout_context`, template context,
  focused id, radiogroup/menu stacks, frame counter.
- **renderer.py** - Jinja2 environment + registration of all template tags;
  drives the template -> VNode -> reconcile -> layout -> paint pipeline.
- **state.py** - Reactive `State` (UserDict). `on_change()` callbacks,
  per-key `watch()`, dict and attribute access, sync + async callbacks.
- **events.py** - Event system: `EventType` (KEY, ACTION, CHANGE, FOCUS, BLUR,
  MOUSE), `HandlerScope` (GLOBAL, VIEW, ELEMENT), `HandlerRegistry`, sync/async
  handlers, cancellation/propagation.
- **event_loop.py** - Async event loop (`run_async`). Non-blocking input,
  async dispatch, animation/spinner frame advance, notification expiry,
  pending-task cancellation on shutdown.
- **focus.py** / **hover.py** - Keyboard focus navigation (Tab/Shift+Tab,
  tab-index) and mouse hover lifecycle.
- **mouse_router.py** - Hit testing, overlay-first routing by z-index, context
  menu (right-click), hover updates, async element mouse dispatch.
- **overlay.py** - Layered overlays (`LayerType`: `BASE`, `MODAL`, `DROPDOWN`, `TOOLTIP`),
  z-index, click-outside, auto-positioning, focus trapping.
- **notification_manager.py** - Notification lifecycle/positioning/expiry.
- **view_router.py** - View registration/navigation, `ViewConfig`, async views
  and lifecycle hooks (on_enter/on_exit). **Synchronous view functions are
  re-invoked on every render** (`evaluate_render`), so any context they compute
  stays live; async views are resolved once (their body can't be awaited from
  the sync render path) and rely on `state` / a `data` callable for liveness.
- **templating.py** - Flask-style view API: `render_template_string(src, **ctx)`
  / `render_template(name, **ctx)` returning a `RenderedView`. This is the
  preferred view return shape; `on_enter`/`on_exit` go on the `@app.view(...)`
  decorator. The legacy `{"template": ..., "data": {...}}` dict return is still
  supported (and is now live thanks to per-render re-invocation). Note: pass
  changing values via **context kwargs** (live), not by interpolating state into
  the template *source* string (defeats the compiled-template cache).
- **wiring.py** - `ElementWiringManager`: binds element ids to state keys.
- **suspend.py** - Ctrl+Z (SIGTSTP/SIGCONT) suspend/resume on Unix (no-op on
  Windows).
- **logging_config.py** (top level: `src/wijjit/logging_config.py`) -
  `get_logger()` and logging setup. Use `get_logger(__name__)` for logging;
  do not leave `[DEBUG]`-style print logging in committed code.

### Terminal Layer (`src/wijjit/terminal/`)

- **ansi.py** - ANSI utilities: `strip_ansi`, `visible_length`, `clip_to_width`,
  `colorize`, `wrap_text` (ANSI-aware). Uses `wcwidth` for wide chars.
- **screen.py** - Alternate screen buffer context manager.
- **screen_buffer.py** - Cell-based screen buffer + diff rendering + dirty
  region tracking.
- **cell.py** - Cell primitives.
- **input.py** - Cross-platform keyboard input via prompt_toolkit
  (`read_input_async`), special keys, escape sequences.
- **mouse.py** - `MouseEvent`, `MouseButton`, `MouseEventType`.

### Layout Layer (`src/wijjit/layout/`)

- **bounds.py** - Sizing: fixed (`50`), `"fill"`, `"auto"`, `"50%"`.
- **frames.py** - Frame rendering, border styles (single/double/rounded/heavy/
  ascii), titles, padding, scrollbars, `BORDER_CHARS`.
- **engine.py** - Layout tree: `VStack`, `HStack`, `FrameNode`, `ElementNode`,
  `SplitPanelNode`. HStack flexbox: `justify`, `wrap`, `gap`/`row_gap`/`column_gap`.
- **splitpanel.py** - Resizable split panels (drag/keyboard resize, collapse,
  nesting, persistence).
- **scroll.py** - `ScrollManager` (use `update_content_size()` to resize content
  and re-clamp scroll; do not assign `content_size` directly).
- **dirty.py** - Dirty region tracking.

### Elements Layer (`src/wijjit/elements/`)

Base classes (`base.py`): `Element`, `ScrollableElement` (ABC), `Container`,
`OverlayElement`, `TextElement`.

**Input** (`elements/input/`): `TextInput`, `TextArea`, `Button`, `Checkbox`,
`CheckboxGroup`, `Radio`, `RadioGroup`, `Select` (single + `multiple=True`),
`Slider`, `Toggle`, `CodeEditor` (syntax highlighting + autocomplete),
`DataGrid` (spreadsheet-style entry; optional pandas).

**Display** (`elements/display/`): `Table` (Rich-powered, sortable/scrollable),
`Tree` (single + multi-select), `ListView`, `LogView`, `ProgressBar`, `Spinner`,
`StatusBar`, `StatusIndicator`, `Notification`, `Modal`, `Pager`, `TabbedPanel`,
`ContentView`, `Link` (hyperlinks), `ImageView` (ASCII/ANSI image; needs the
`images` extra / Pillow), and charts: `BarChart`, `LineChart`, `ColumnChart`,
`Sparkline`, `HeatMap`, `Gauge`.

**Overlays/menus**: `MenuElement`, `DropdownMenu`, `ContextMenu`; dialogs
(`ConfirmDialog`, `AlertDialog`, `TextInputDialog`).

Element type names (and aliases) are registered in
`core/element_registry.py`. To add an element, see `docs/NEW-ELEMENTS.md`
(element class -> template tag -> registry -> exports).

### Tags Layer (`src/wijjit/tags/`)

Jinja2 extensions: `layout.py` (vstack/hstack/frame/pager/page),
`input.py`, `display.py`, `charts.py`, `menu.py`, `dialogs.py`.

### Styling Layer (`src/wijjit/styling/`)

`style.py`, `theme.py`, `resolver.py`, and `css_parser.py` (CSS theming via
`tinycss2`). Themes load from CSS/JSON files or built-ins. Config keys:
`DEFAULT_THEME` ('default'/'dark'/'light'/'high_contrast'), `THEME_FILE`,
`STYLE_FILE`, `FOCUS_COLOR`, `NO_COLOR`, `UNICODE_SUPPORT`.

### Rendering Layer (`src/wijjit/rendering/`)

`paint_context.py` (`PaintContext` cell API, clip regions), `ansi_adapter.py`,
`html_adapter.py`, `content_renderers.py`. The latter powers the `content_type`
attribute that lets text-containing display elements render raw text, ANSI,
HTML, Markdown, or Rich markup.

### Other top-level modules

- **inline/** - Non-alternate-screen output. `render_inline()` (one-shot to
  scrollback) and `InlineApp` (interactive in-place updates, optional input).
- **autocomplete/** - Suggestion dropdown for text inputs/CodeEditor:
  `completer.py`, `state.py`, `popup.py`, `mixin.py`, `resolver.py`, `utils.py`.
- **config.py** - Flask-style `Config`/`DefaultConfig` (see below).
- **helpers.py** - e.g. `load_filesystem_tree`.

## Public API

The top-level `wijjit` package re-exports the supported public API (see
`src/wijjit/__init__.py`): `Wijjit`, `Config`, `State`, `Renderer`,
`FocusManager`, `ViewConfig`, `RenderedView`, `render_template_string`,
`render_template`, `render_inline`, `InlineApp`, event types, core elements,
layout (`Frame`, `Bounds`, ...), and terminal/ANSI helpers. Prefer importing
from `wijjit` directly in examples and docs.

The idiomatic view returns `render_template_string` / `render_template` with
live context:

```python
@app.view("main", default=True, on_enter=setup)
def main_view():
    return render_template_string(TEMPLATE, count=app.state.n * 10)
```

## Configuration System (`app.config`)

Flask-inspired. Set via `app.config['KEY'] = v`, `app.config.update(...)`,
`from_pyfile`, `from_object`, `from_envvar`, or `WIJJIT_*` env vars
(auto-loaded in `Wijjit.__init__`). Categories: Input/Interaction, Display/
Terminal, Process Control (Ctrl+Z), Colors/Theming, Performance/Threading,
Notifications, Logging, Debug, Templates, Accessibility, Testing/CI. See
`src/wijjit/config.py` (`DefaultConfig`) for the authoritative list and
defaults; `tests/core/test_config.py` covers it.

## Key Design Patterns & Conventions

- **ANSI-aware text**: never use `len()` on terminal text - use
  `visible_length()`, `clip_to_width()`, `strip_ansi()`, `wrap_text()`.
- **Cell-based rendering**: elements implement `render_to(ctx: PaintContext)`
  and `get_intrinsic_size()`.
- **Reconciliation**: template re-renders are diffed; transient state listed in
  `EPHEMERAL_PROPS` (cursor/scroll/selection/focus/hover/highlight) is preserved
  and must not be synced from props.
- **Async by default**: the loop is async internally; `app.run()` calls
  `asyncio.run(app.run_async())`. Both sync and async handlers/views are supported.
- **No Unicode/emoji in implementation code** (fine in tests/docs/test data).
- **NumPy-style docstrings** for all modules/classes/methods/functions.
- **Keep dependencies minimal**: jinja2, prompt-toolkit, rich, tinycss2,
  pyperclip, wcwidth (Pillow only under the `images` extra).

## Examples

`examples/` has ~69 runnable demos, organized into `basic/` (15), `widgets/`
(30), `advanced/` (21), `styling/` (2), `apps/` (1). Run with
`python examples/<dir>/<name>.py`. Note: a few demos still have known visual/
behavioral bugs deferred to 0.1.1, tracked with root causes in `issues.md` (repo
root) - see `RELEASE_PLAN.md`.

## Known Limitations / In-Progress

- `mypy --strict src/` is clean via targeted per-module overrides (see Phase 3
  of `RELEASE_PLAN.md`); a full strict pass on the overridden modules is future
  work.
- A handful of demo bugs are deferred to 0.1.1 (horizontal child-frame scroll,
  tree expand-all, autocomplete select, some layout/clip + Windows alt-keys);
  tracked with root causes in `issues.md`.
- Headless test harness exists (`wijjit.testing.WijjitHarness`); per-example
  snapshot fixtures and a headless example CLI are still TODO.
- Sphinx docs scaffold exists but the build emits many warnings.
- No virtual scrolling for very large datasets.
- Some Unicode may render imperfectly on Windows.

## Adding Things (quick references)

- New element: `docs/NEW-ELEMENTS.md`.
- Docs structure: `docs/DOCUMENTATION_PLAN.md`.
- Outstanding bugs/backlog: `etc/issues.md`, `etc/issues-sorted.md`, `etc/todo.md`.
