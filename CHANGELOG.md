# Changelog

All notable changes to Wijjit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-28

First public release.

### Added
- **`key=` reconciliation attribute** for element tags, separate from `id=`.
  Elements inside a `{% for %}` loop are keyed by position by default, so
  inserting or reordering rows silently migrates a row's state - a text input's
  typed value and cursor, a tree's scroll and selection - to whatever row now
  sits at the old slot (a bound input's value migrates too, since the positional
  id is also its state key). An explicit `key` gives a row a stable identity:
  `{% textinput key=row.id %}` keeps each row's state with its logical row across
  inserts and reorders. For an input with no explicit `id`, the `key` also
  derives a stable per-row state id (`textinput_<key>`), so the author does not
  have to hand-manage an id to keep the bound value. See the "Keying elements
  inside `{% for %}` loops" section of the architecture guide.
- **`wijjit validate` unkeyed-loop-element check**: a stateful element inside a
  loop with neither `key` nor `id` is now flagged as a warning, catching the
  data-loss footgun above at author time. Stateless elements (charts, text,
  spinners, progress bars) are not flagged.
- **`wijjit --version`**: the CLI now reports the installed version.
- **Performance benchmarks**: `scripts/bench_perf.py` measures render latency,
  terminal I/O per frame, and import cost, emitting a text, Markdown, or JSON
  report. The byte counts are regression-tested in
  `tests/core/test_diff_render_bytes.py`, and a new `user_guide/performance`
  documentation page covers the results and how to profile your own app.
- `wijjit.config.no_color_from_env()` and
  `wijjit.terminal.ansi.refresh_no_color_from_env()` for resolving `NO_COLOR`
  from the environment.
- **Flask-style view rendering**: `render_template_string(src, **context)` and
  `render_template(name, **context)` return a `RenderedView`, replacing the
  `{"template": ..., "data": {...}}` dict as the idiomatic view return. Lifecycle
  hooks move onto the decorator (`@app.view(name, on_enter=..., on_exit=...)`).
  Synchronous view functions are now re-invoked on every render, so context
  derived from state stays live (the old static `data` dict was frozen at first
  render). The legacy dict return still works and is also live now.
- **Flask-style template directory**: when `template_dir` is not set, Wijjit
  auto-discovers a `templates/` directory next to the module that constructs the
  app, so `render_template("home.wij.j2", ...)` works zero-config. `render_template`
  against a missing directory/file now raises an actionable error, and
  `TEMPLATE_AUTO_RELOAD` is wired into Jinja2 for hot-reloading file templates
  during development.
- Right-aligned (and centered) **table columns** via a per-column `align` key
  (`{"key": "amount", "align": "right"}`).
- Horizontal **text alignment** for the `{% text %}` tag (`align="left"`,
  `"center"`, `"right"`), plus `width`/`height` attributes so alignment has
  room to take effect.
- **Autosizing `TextArea`**: `autosize=True` grows the height to fit the
  content up to an optional `max_height` (rows), then scrolls.
- **Bind keys to focus**: `app.bind_focus_key(key, element_id)` plus
  `app.get_element_by_id()` / `app.focus_element_by_id()` for jumping focus to
  a named element from a keyboard shortcut.
- **Nested item tags** for list-like elements: `{% selectitem %}` (inside
  `{% select %}`) and `{% treeitem %}` (inside `{% tree %}`, supports nesting),
  mirroring the existing `{% menuitem %}` pattern.
- Public API surface re-exported from the top-level `wijjit` package
  (`State`, event types, `Frame`, ANSI helpers, terminal/input utilities, etc.).
- Inline rendering: `render_inline()` and `InlineApp` for non-alternate-screen output.
- Autocomplete / suggestion dropdown support for text inputs and `CodeEditor`.
- Data display elements: bar/line/column charts, sparkline, heatmap, gauge.
- New elements: `Slider`, `Toggle`, `CodeEditor`, `TabbedPanel`, `ContentView`,
  `StatusIndicator`, `Link`, `ImageView`, `DataGrid`, `Pager`.
- `SplitPanel` resizable split layout and HStack flexbox (justify/wrap/gap).
- Multi-select for `Select` and `Tree`.
- VNode + reconciler rendering pipeline (`vdom`, `reconciler`, `element_registry`).
- CSS-based theming (`tinycss2`) and `content_type` rendering
  (text / ansi / html / markdown / rich) in display elements.
- Ctrl+Z suspend/resume (SIGTSTP) on Unix.
- Flask-style configuration system (`app.config`).

### Fixed
- **Any `print()` or traceback during a run corrupted the alternate screen
  until a full redraw - including the framework's own error path.** Output is a
  diff model: the renderer keeps the last displayed buffer and repaints only the
  cells that changed, so a byte written to the terminal out-of-band is invisible
  to the differ and persists. `_handle_error` printed the **full traceback to
  stderr** on every non-fatal error, dumping a multi-line trace *into* the TUI
  where it stayed. Non-fatal error tracebacks are now buffered while the
  alternate screen is active and flushed to stderr only after the terminal is
  restored on exit; fatal errors propagate and print once on the normal screen.
  A new `app.request_full_repaint()` forces the next frame to repaint the whole
  screen (a screen clear plus every cell), and an opt-in `FULL_REPAINT_INTERVAL`
  config drives that on a heartbeat so foreign `stdout` self-heals. The
  heartbeat is disabled by default so the diff renderer's bytes-saved behavior
  is unchanged unless you ask for it.
- **A killed app left the terminal wedged.** Terminal teardown lived only in the
  event loop's `finally` (thorough, but bypassed by `SIGTERM`/`SIGHUP`, which
  Python terminates on without unwinding the stack or running `atexit`) and a
  `ScreenManager` `atexit` backstop that restored the cursor and alt buffer but
  **never disabled mouse tracking**. So `kill <pid>`, a `timeout`, a process
  manager, or CI teardown left the user in the alternate buffer, cursor hidden,
  raw mode on, and `\x1b[?1002h`/`\x1b[?1006h` mouse tracking still active - the
  terminal then spewed escape codes on every mouse move and needed `reset`. A
  new `TerminalCleanup` coordinator (`wijjit.terminal.cleanup`) wires the full
  restore - cursor, alt buffer, raw mode, **and** mouse tracking - into both a
  single `atexit` handler and `SIGTERM`/`SIGHUP` handlers that run it and then
  chain to the previous disposition so the process still exits with the
  conventional status. Signals are installed only from the main thread (skipped
  silently when embedded off-thread); `SIGHUP` is Unix-only.
- **An idle app burned a full CPU core.** `prompt_toolkit`'s `read_keys()` is
  non-blocking and returns immediately when no input is pending, so the reader
  thread polled it in an unthrottled loop (~60k calls/second, 98% of one core
  with no user input at all). It now waits on the shutdown event between empty
  polls, which keeps `close()` immediately responsive.
- **Keys were silently dropped when several arrived in one read.** A single
  `read_keys()` call can return several key presses - a fast typist, an escape
  sequence split across presses, or a keystroke landing right behind a mouse
  event. Only the first was used and the rest were discarded, in four places:
  the main `keys[0]` take, the Alt+key branch, the Escape lookahead (which
  requeued exactly one press and dropped any others), and both mouse-sequence
  continuation loops. Unconsumed presses are now held and replayed on the next
  read, in both `read_input` and `read_input_async`. These two bugs masked each
  other: the busy-spin polled fast enough that batches of more than one key were
  rare, so throttling the poll without fixing the requeue would have turned a
  CPU problem into visible input loss.
- **`on_double_click` and `on_context_menu` never fired.** Every element that
  overrode `handle_mouse` consumed click events without delegating to
  `Element.handle_mouse`, so both callbacks were silently dead. Fixed across all
  inputs (Button, Checkbox, CheckboxGroup, Radio, RadioGroup, Select, Slider,
  Toggle, TextInput, TextArea, DataGrid) and all display elements (Tree,
  ListView, LogView, ContentView, BarChart, Link, Pager, TabbedPanel). `Table`
  delegated only on a fallback path that its row-hit branch made unreachable.
- **A right-click activated a `Button`.** `Button.handle_mouse` acted on any
  mouse button. It now requires `MouseButton.LEFT`, so a right-click falls
  through and the mouse router can open a context menu.
- **A right-click on a `Table` header fired `on_header_click` and sorted the
  column**, and a right-click on a data row was swallowed by the row-click
  handler, so `on_context_menu` never fired on a table row. Row, cell, and
  header interactions now require the left button. A double-click on a row with
  no `on_row_double_click` set falls back to the element-level
  `on_double_click` instead of being discarded.
- **`DataGrid.get_data_as_dataframe()` raised on ragged rows.** Short rows are
  padded and overlong rows truncated so pandas never sees a length mismatch.
  Truncation discards data, so it now logs a warning instead of dropping cells
  silently.
- **`NO_COLOR` had no effect on rendered output.** The setting was only honored
  by the legacy `colorize()` string helper; the cell-based renderer that draws
  every real app emitted color regardless. `Cell.to_ansi()` and
  `Cell.get_style_codes()` now suppress foreground/background colors when
  `NO_COLOR` is in effect, while preserving text attributes (bold, reverse) so
  focus and selection stay visible without color.
- **`NO_COLOR=""` incorrectly disabled color.** Both `DefaultConfig.NO_COLOR`
  and `ansi.is_no_color()` treated mere *presence* of the variable as enabling
  it. Per [no-color.org](https://no-color.org/) it must be present *and
  non-empty*.
- **`NO_COLOR` was snapshotted at import time.** `DefaultConfig.NO_COLOR` is a
  class attribute evaluated when `wijjit.config` is first imported, so setting
  the variable after `import wijjit` had no effect. `Wijjit.__init__` now
  re-reads the environment, before the `WIJJIT_*` and keyword overrides that
  still take precedence over it.
- `ansi.is_no_color()` took a lock and re-read `os.environ` on every call. It
  runs once per rendered cell, where that cost more than the rest of the cell's
  ANSI generation combined; it is now a cached, lock-free read.
- **Autocomplete mouse selection**: clicking a suggestion in the popup now
  commits it to the input (previously only the keyboard Enter/Tab path applied
  the selection; a click just moved the highlight).
- Mouse hit-testing on scrolled frames: clicks now register against the painted
  (scroll-adjusted) position of an element instead of its pre-scroll bounds.
- `Select` now re-clamps scroll position when its option list changes.
- Pending async tasks spawned from state callbacks are cancelled on shutdown,
  preventing task leaks and exit hangs.
- Global `@app.on_key` handlers (e.g. a quit hotkey) now fire while a
  `TextInput`/`TextArea` is focused; only view-scoped key handlers are
  suppressed so typing a character no longer triggers a view hotkey.
- Windows console mouse input is parsed correctly (`WindowsMouseEvent`), so
  clicks reach buttons and other elements on Windows terminals.
- The source distribution now builds deterministically via an explicit file
  list, so a stray local virtualenv (e.g. `.venv-wsl/`) no longer breaks
  `uv build` / packaging.

### Changed
- **Setting `on_double_click` on a `Button` now suppresses activation on
  double-click.** The base handler runs first and claims the event, so the
  callback fires instead of the button activating. Without the callback, a
  double-click still activates as before.
- **Template files are conventionally named `*.wij.j2`** (was `*.tui`), so
  editors syntax-highlight them as Jinja. The extension is not enforced:
  `validate` and `tree` detect apps by the `.py` suffix and treat anything else
  as a template.
- Expanded the PyPI `keywords` list for discoverability.
- README trimmed and corrected: dropped a duplicated feature list, the inline
  dependency version pins, and the self-contradictory "not optimized / not
  recommended for high-performance applications" language that the measured
  benchmarks contradict. Added performance and accessibility sections.
- **Inner-text discipline**: `{% textinput %}` now uses its tag body as the
  initial value when no `value=` is given, and `{% button %}` / `{% menuitem %}`
  accept a `label=` attribute as an alternative to the body (the attribute wins
  when both are present). Consistent with the existing checkbox/radio/textarea
  behavior.
- Hoisted a number of standard-library imports from function bodies up to
  module level (code hygiene; no behavior change).
- Version is now sourced from `wijjit.__version__` (single source of truth).

[Unreleased]: https://github.com/thomas-villani/wijjit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thomas-villani/wijjit/releases/tag/v0.1.0
