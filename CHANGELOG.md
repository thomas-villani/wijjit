# Changelog

All notable changes to Wijjit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`WijjitHarness.resize(width, height)`** for driving a terminal resize
  through the running loop in tests. It changes the size the app's backend
  reports and pumps a frame, so the event loop's resize-detection path runs
  exactly as on a live resize: the view re-lays-out, scroll offsets re-clamp to
  the new viewport, centered overlays re-centre, and the buffer repaints at the
  new dimensions. `screen()` / `screen_ansi()` reflect the new size afterward.
  The harness was previously fixed-size, so none of this was testable (review
  Part 4 #4).
- **Undo/redo in `TextArea` and `CodeEditor`** (`Ctrl+Z` / `Ctrl+Y`). Editing
  was previously unrecoverable: `_delete_selection`, cut, and
  select-all-then-type discarded content with no history at all. Snapshots are
  taken at the key boundary rather than inside the mutating primitives, so a
  keypress that runs several of them is **one** undo unit - typing over a
  selection (delete + insert) and an insert that triggers a hard-wrap reflow
  each undo as a single action. A run of character insertions coalesces, so
  typing a word is one undo, not one per letter; the run breaks on any other
  edit, a cursor move, or a selection change. History is bounded at 200 entries
  and is cheap (each snapshot shares the line strings it did not change).
  `CodeEditor` inherits this and re-highlights on undo. New `ctrl+y` key
  (redo is not `Ctrl+Shift+Z`: terminals do not reliably distinguish shift on a
  control chord).
- **`bind` now accepts a state key name**, not just a bool. `bind=True`
  (unchanged default) binds to the element's default key - its `id`, or the
  group `name` for `radio`/`radiogroup`. `bind="some_key"` binds to
  `state["some_key"]` whatever the id is, which unfuses element identity from
  state storage: two widgets can now share one key
  (`{% textinput id="a" bind="draft" %}` + `{% textinput id="b" bind="draft" %}`),
  and giving an element an id no longer colonizes that state key. Both halves
  of the binding - the tags' render-time read and the wiring's write-back -
  now resolve the key through one shared `resolve_bind_key`, so an element
  cannot read one key and write another. Works on display and chart tags too,
  where binding stays one-way (read-only).
- **Hardware cursor parking** (`HARDWARE_CURSOR` config, default on). The
  caret used to be only a painted reverse-video cell while the terminal's
  real cursor stayed hidden for the whole session, so terminals could not
  blink it and screen readers had nothing to track. When the focused element
  reports a caret cell (TextInput, TextArea, CodeEditor), each frame now ends
  with a cursor-move + show-cursor escape parking the real cursor on the
  caret - column-correct for wide CJK/emoji input - and hides it again when
  no caret is visible (unfocused, or scrolled out of a frame's interior).
  Idle frames add no bytes, so the diff renderer's emit-nothing-when-idle
  property is unchanged. Custom elements can opt in by overriding
  `Element.get_hardware_cursor_position()` / setting the anchor via
  `PaintContext.cursor_anchor()`.
- **Raw emitted-ANSI capture in the test harness.** `WijjitHarness`
  previously discarded everything the app wrote; it now records each
  `write_frame` payload: `h.emitted_frames` (list of raw frames),
  `h.last_frame`, and `h.emitted_ansi()`. Tests can assert on the exact byte
  stream a terminal receives - diff shape, SGR hygiene, cursor escapes - and
  the suite now carries lossless emitted-ANSI goldens for a themed
  multi-element screen.
- **Deterministic performance budgets**
  (`tests/benchmarks/test_perf_budgets.py`): asserted ceilings on bytes
  emitted (idle frame, one-value change, scroll, end-to-end keystroke) and
  on layout passes per frame, so a silent perf regression fails CI without
  flaky wall-clock thresholds.
- New demo app: `examples/apps/system_monitor.py`, a live system resource
  monitor (CPU/memory line chart, per-core gauges; requires `psutil`)
  driven by a background worker thread updating reactive state.
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

### Removed
- **~126 lines of dead code in `TextArea`.** `_render_cursor_in_line` and
  `_apply_selection_to_line_ansi` were a pre-cell-buffer path that built ANSI
  strings by hand (one hardcoding a theme color). Rendering has gone through
  `PaintContext` since the clip migration; both had zero call sites.

### Fixed
- **A template `{% modal %}` / dialog vanished on the next re-render.** A
  centered overlay declared in a template is rebuilt fresh (with `bounds=None`)
  every render; the initial render centred it, but the per-render *update* path
  only re-derived bounds for menus, so a modal or dialog lost its bounds and
  silently stopped compositing on the first re-render - and almost any keystroke
  or state change triggers one. The update path now re-centres a centered
  overlay via a shared `OverlayManager.center_element`, so it stays put across
  renders and re-centres on resize (review item 2.13).
- **`{% confirmdialog %}` / `{% alertdialog %}` / `{% textinputdialog %}` leaked
  one overlay per render.** The dialog classes never accepted or forwarded an
  `id`, so the element's id was always `None` and the overlay de-dup (which
  matches on id) failed - every render pushed a *new* duplicate overlay, growing
  the stack unboundedly. The dialog constructors now take `id` and pass it
  through, and the tags forward the (explicit or auto-generated) id, so a dialog
  reconciles to a single stable overlay.
- **Text style could bleed into the shell prompt after the app exited.**
  Teardown showed the cursor and left the alternate buffer but never reset SGR
  attributes, so an active colour/bold/reverse from the last frame - or, worse,
  from a frame whose render raised before it could emit its own trailing reset -
  persisted on the normal screen. Every teardown path (the event loop's normal
  `finally`, the signal/`atexit` emergency restore, and `ScreenManager.cleanup`)
  now emits `\x1b[0m` before showing the cursor and leaving the alternate buffer
  (review Part 4 #5a).
- **Nested scrollable frames re-ran layout ~O(2^depth) every frame.** A
  scrollable frame that needs a scrollbar re-lays-out its whole subtree one
  column narrower to reserve the gutter; because that second pass recursed into
  nested frames that also doubled, a depth-3 chain cost 7 layout passes per
  render and each extra level doubled again. `FrameNode.assign_bounds` now
  predicts the gutter from the frame's persisted `_needs_scroll` and lays the
  subtree out once, re-laying-out only on the frame where scrolling actually
  turns on or off. Steady-state layout is now one pass per frame - linear in
  depth (depth-3: 7 -> 3 passes); the cold first render settled 7 -> 6. The
  reserved-gutter behavior is unchanged (review item 2.4).
- **`SplitPanel` could compute negative panel sizes and held the app strongly.**
  When `min_first + min_second` exceeded the usable space, `_calculate_sizes`
  drove a pane negative (e.g. `(-2, 5)`); sizes now clamp into `[0, usable]` and
  always sum to `usable`, and space too small for even the divider yields
  `(0, 0, 0)`. The app reference used for state persistence is now a `weakref`
  (matching `parent_frame`), so a panel no longer keeps the whole application
  alive (review item 2.12).
- **A render sampled the terminal size more than once, so a mid-frame resize
  could tear the frame.** Layout and overlay compositing each called
  `get_terminal_size()` independently (and the FPS counter a third time), so a
  resize landing between them laid the base out at one size and composited
  overlays at another. `_render` now samples once at the top and reuses that for
  layout, overlay compositing, and the FPS overlay, keeping every frame
  internally consistent (review item 2.12).
- **`fill` children under-filled their container by up to N-1 cells.** `VStack`
  and `HStack` gave every fill child `remaining // count` and discarded the
  integer remainder, so three fill children in a height of 20 took 6+6+6=18 and
  left two rows dead at the bottom (same for columns). The remainder now spreads
  onto the leading fill children (7+7+6=20) - the same distribution
  `HStack._distribute_space` already used for justify gaps, now shared through
  one `_distribute_fill` helper (review item 2.12).
- **Diff renderer emitted a redundant SGR prefix and reset per changed cell.**
  `_render_row_diff` wrote `cell.to_ansi()` (style codes + char + `\x1b[0m`) for
  every changed cell, so a contiguous run of same-styled cells shipped the whole
  style prefix and a reset once *per cell* - a 10-cell run of red text was ~230
  bytes. It now groups runs the way the full-render path already did: one prefix
  per run, and the style even carries across a cursor jump to the next run (a
  cursor move does not touch SGR state), with a single trailing reset. The same
  10-cell run is now 37 bytes. Output is byte-for-byte equivalent in effect;
  only redundant escapes are removed. Serves the project's bytes-saved
  performance story (review item 2.12).
- **Sync state callbacks ran on whatever thread performed the write**, racing
  the renderer and - worse - reading the wrong terminal size. `State` now runs
  every callback on the event-loop thread regardless of which thread wrote,
  marshalling with `call_soon_threadsafe` when a worker thread performs the
  assignment (the async half of this landed earlier; this is the sync half).
  `set_async()` and `async_batch_update()` used to `run_in_executor` their sync
  callbacks, which was the framework's *own* path off the loop thread - no user
  threads required. That mattered because `get_terminal_size()` reads a
  `ContextVar` and context is not propagated into executor threads, so
  `app._on_state_change` silently fell back to the *process* terminal size and
  marked, say, an 80x24 region dirty on a 200x60 session - leaving everything
  beyond that unrepainted. A `State` with no running loop still invokes
  callbacks inline, so bare/sync use is unchanged.
- **Reassigning a mutable value after mutating it in place fired nothing.**
  `state["rows"] = state["rows"]` (after `rows.append(x)`) compared the mutated
  list against itself, hit the equality gate, and silently did not re-render -
  and so did the other idiom the docs recommended, `state["rows"] =
  list(state["rows"])`, because a value-equal copy of an already-mutated list is
  indistinguishable from a no-op write. `State` now detects the same-object
  write, fires the change (it cannot prove the container is unchanged, and a
  spurious repaint beats a missed one), and warns pointing at the immutable
  idiom. The value-equal-copy case is unfixable and is now documented as such:
  **build the new container first, then assign** (`state[k] = [*state[k], x]`).
  Order is what matters - copy-then-mutate works, mutate-then-copy is silent.
  The equality gate is unchanged for scalars and immutable containers.
- **`Slider`, `Toggle`, and `DataGrid` never wrote their value back to
  state.** All three advertised `bind=True` and read `state[id]` at render,
  but none was wired, so nothing subscribed to the `on_change` they were
  already firing: the binding ran one way, silently. `examples/widgets/slider_demo.py`
  showed this in the shipped demo - drag the slider to 59 and its own readout,
  driven from `state["volume"]`, still said 50. All three are now wired, so
  `bind` means the same thing on every input. **Behavior change:** apps using
  these three with a bound id now see `state[id]` update on interaction.
  DataGrid normalizes every cell to `str`, so the rows it writes back are
  strings.
- **`bind=False` was ignored by every element except `TextInput`/`TextArea`.**
  The other element classes hardcoded `self.bind = True` and did not accept
  `bind` in `__init__`, and the element registry filters props against the
  constructor signature - so the prop never reached them. All 25 element
  constructors now take `bind`.
- **`State` no longer reserves 21 key names.** Because `State` subclasses
  `UserDict`, every one of its methods claimed a key name: `state["items"]`,
  `state["keys"]`, `state["get"]`, `state["data"]` and 17 others raised
  `StateKeyError`. Banning `items` in a framework built to render lists is a
  landmine, and Wijjit's own documentation stepped on it twice. The collision
  was only ever in Jinja's attribute lookup, so it is fixed there: the
  template environment now resolves a present state key before falling back
  to the attribute, so `{{ state.items }}` renders your list while
  `{% for k, v in state.items() %}` and `{{ state.get('k', d) }}` still work
  in apps that define no such keys. All key names are now legal via subscript.
  Python-side attribute *reads* of a method-shadowing name still find the
  method (inverting that would break `dict(state)`, which calls `keys()`), so
  attribute *writes* of those names raise a `StateKeyError` pointing at
  `state["items"] = ...` rather than storing a value the same syntax cannot
  read back.
- **`State.copy()` raised `StateKeyError` on every call.** `UserDict.copy()`
  reassigns `self.data`, which `State.__setattr__` rejects to stop callers
  silently replacing the whole store. `State` now overrides `copy()`.
- **Elements could paint over the borders and content around a scrolled
  frame.** `PaintContext` enforces a clip region, but roughly half the
  element library bypassed it by writing buffer cells directly, so an
  element taller than a scrollable frame's interior overwrote the frame's
  border and whatever sat above/below it once scrolled. All element
  rendering now goes through clipped, wide-char-aware `PaintContext` write
  APIs (`write_cell` emits head + continuation cells for wide glyphs and
  returns the columns consumed; new bulk `write_cells` /
  `write_cells_vertical` cover row/column runs), a ratchet test keeps
  direct buffer writes out of `src/wijjit/elements/`, and a clip-regression
  suite drives ten element types through both overflow directions. The
  migration also fixed three latent bugs: chart borders *replaced* the
  inherited clip instead of intersecting it, TextArea/CodeEditor painted one
  column wider than their assigned bounds when a scrollbar appeared, and
  ContentView bled padding rows outside its bounds.
- **Wide characters landed on the wrong cells in element-painted content.**
  TextArea/CodeEditor content, the reverse-video cursor, and selection
  highlights were placed by character index at one-cell pitch, so CJK/emoji
  shifted the row and the cursor/selection highlighted the wrong cells;
  TextInput's caret had the same off-by-width bug. Element content loops are
  now per-cluster with separate character (semantics) and column (placement)
  counters. Pre-rendered ANSI content (`content_type="ansi"`) still maps one
  code point per cell; see the `ScreenBuffer` docstring for scope.
- **`app.running` was always `False`.** The `Wijjit.running` attribute was
  set in `__init__` and never updated, so a worker thread polling it to know
  when to stop (as examples suggest) exited immediately. It is now a
  property delegating to the event loop's running flag.
- **Wide characters (CJK, emoji, decomposed accents) misaligned everything to
  their right.** Layout measured text in terminal columns (`wcwidth`) but the
  writer stored one buffer cell per Python character and the diff renderer
  assumed every cell advanced the cursor one column, so a width-2 glyph pushed
  the frame's right border out of place, desynced the diff cursor
  run-length-dependently, and offset mouse clicks for the rest of the row. The
  standard text path is now column-correct: a wide glyph occupies a head cell
  plus a continuation cell, zero-width combining marks fold onto their base
  glyph (NFD filenames like macOS's `Résumé.txt` render correctly), and the
  diff/full-render emitters advance by true glyph width. Raw ANSI escapes
  embedded in *plain* text bodies are now stripped cleanly rather than
  accidentally round-tripped (use `content_type="ansi"` for pre-styled
  content). Elements that paint cells directly (TextArea and friends) are not
  yet cluster-aware; see the `ScreenBuffer` docstring for the exact scope.
- **Template typos failed silently - undefined variables rendered as empty and
  misspelled attributes vanished.** `{{ mispeled }}` rendered as `""` and
  `{% for x in mispeled %}` iterated zero times with no diagnostic (this once
  kept a fully working feature marked "unsupported" for eight months). With
  `DEBUG` enabled (`Wijjit(debug=True)` or `WIJJIT_DEBUG=1`), templates now use
  Jinja's `StrictUndefined` and raise on undefined names; production stays
  lenient so one bad key cannot crash a running TUI. `wijjit validate` is
  always strict and reports a bare undefined name as `undefined-variable`.
  Separately, only the `textinput` tag used to forward unrecognized attributes
  onto its element description, so the validator could catch attribute typos
  on exactly one tag; every VNode-building tag now forwards extras, so
  `{% button wdith=20 %}` is flagged as `unknown-attribute` instead of
  disappearing. `Button` accepts `style` as a string (`style="box"`) as part
  of this, falling back to brackets with a warning for unknown names.
- **Exceptions in async state callbacks vanished; worker-thread callbacks
  outlived shutdown.** An `async` `on_change`/`watch` callback that raised was
  never surfaced - the task's exception was never retrieved, so the error
  appeared (if at all) as a cryptic "Task exception was never retrieved" at
  garbage collection. And a state write from a worker thread scheduled its
  callback via a fire-and-forget future invisible to `flush_pending_async`
  and shutdown, so it could still be running after the terminal was restored.
  Callback task failures now flow through the app's error handling like any
  other handler error, and worker-thread writes create their tasks on the
  event-loop thread where flush and the shutdown sweep already track them.
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
- **More elements opt in to the skip-unchanged fast path.** The skip-unchanged
  paint optimization only helps elements that publish a `render_signature()`;
  it previously shipped for `TextElement`, `TextInput`, and `Button`, so an
  otherwise-static form still repainted its checkboxes, toggles, and sliders on
  every keystroke. Signatures now ship for `Checkbox`, `CheckboxGroup`, `Radio`,
  `RadioGroup`, `Toggle`, `Slider`, `ProgressBar`, `StatusIndicator`,
  `StatusBar`, `Link`, `Sparkline`, `Gauge`, and `ColumnChart` - so an unchanged
  widget is skipped while the one field being edited repaints. Each signature
  captures exactly the instance state its `render_to` reads (content plus the
  variant/layout inputs; focus/hover/checked/selected and CSS classes come from
  the shared `_style_signature`), and unit tests assert every signature is
  sensitive to each of those inputs. `Select`, `BarChart`, and `Table` stay on
  the safe default (`None` -> always repaint): their paint couples to internal
  scroll state that a signature cannot yet capture completely. Measured **~1.36x
  (about 27% less per-render CPU)** on a static form where one field changes per
  keystroke; screen output stays byte-for-byte identical (review 2.5).
- **Skip re-painting unchanged elements.** With the per-frame allocation and
  full-screen diff costs already gone, the largest remaining per-keystroke cost
  was the paint itself: `render_to` (and its per-glyph `write_text` loop) ran for
  *every* element every frame, even the ones that did not change. On the
  incremental path the paint buffer already starts as a copy of the previous
  frame, so an unchanged element's cells are already correct - there is nothing
  to repaint. Each element now exposes a `render_signature()` (value, cursor,
  style-affecting state, ...); when it and the element's on-screen geometry match
  the previous frame, the renderer skips `render_to` entirely and just re-records
  the element's previous painted region as coverage (so vacated-cell blanking
  still spares it). Correctness is guarded three ways: elements return `None`
  (always repaint) unless they opt in with a complete signature; an element whose
  region overlaps the always-repainted frame-border pass, or that sits under an
  `overflow_x="visible"` frame, is never skipped; and a `verify_skips` render
  mode paints would-be-skipped elements anyway and asserts the result is
  byte-identical to the baseline (exercised across every bundled example). Gated
  on the incremental path with a stable theme, behind a
  `renderer.skip_unchanged_elements` off-switch, screen output byte-for-byte
  identical to a full paint (pinned by on-vs-off screen + emitted-ANSI
  equivalence tests). Signatures ship for `TextElement`, `TextInput`, and
  `Button`; measured **~14% less per-render CPU** on a static-heavy 40-row view
  where one input changes per keystroke (review 2.5).
- **Cheaper damage-tracking bookkeeping on the paint path.** The per-frame
  coverage set (which records every painted cell so the incremental path can
  blank vacated content) now stores a packed `y * width + x` int per cell
  instead of an `(x, y)` tuple, removing a tuple allocation on every glyph write
  (~1268 painted cells/frame on the profiled 40-row view); the renderer unpacks
  it in the vacated-cell loop. The wide-glyph continuation test
  (`is_continuation`, ~768k calls over 400 renders) drops its string compare for
  `not cell.char` — exactly equivalent, since the continuation sentinel is the
  only empty `char` in the pipeline. Both are byte-for-byte identical on screen
  (review 2.5 follow-up).
- **Interned cells on the paint hot path.** `PaintContext.write_text` /
  `fill_rect` allocated a fresh `Cell` for every glyph on every frame (~407k
  `Cell.__post_init__` calls over 400 renders on a 40-row view). A bounded
  (LRU) `wijjit.terminal.cell.intern_cell` now shares one immutable `Cell` per
  `(char, style)`, so re-painting the same text is a cache lookup instead of an
  allocation - safe for exactly the reason the shared blank cell is (cells are
  never mutated in place). It also speeds the diff: an unchanged glyph resolves
  to the *same* object frame-over-frame, so `Cell.__eq__`'s identity
  short-circuit settles it without comparing fields (the biggest gain on the
  full-repaint path). The cache is keyed positionally (roughly an order of
  magnitude cheaper than a keyword key). Measured ~15% less per-render CPU on
  top of the width fast path below (review 2.5).
- **Faster text-width measurement: printable-ASCII fast path (`display_width`).**
  With the per-frame allocation and full-screen diff costs removed by the two
  changes below, profiling a 40-row Latin-text view showed the single largest
  remaining per-render cost was `wcwidth`/`wcswidth` — the per-character Unicode
  table bisection run for every glyph painted, every cell measured by the diff,
  and every `visible_length` call. A new `wijjit.terminal.ansi.display_width`
  fast-paths the overwhelmingly common all-printable-ASCII case (where each code
  point is provably one column, so the width is just `len`) and otherwise defers
  to `wcswidth` unchanged; the cell/width/wrap call sites route through it (and
  their per-call `from wcwidth import ...` imports were hoisted). CJK/emoji/NFD
  width handling is unaffected. Measured ~2x faster per render (~8.6 ms -> ~4.6 ms
  on the profiled view); benefits the full-repaint path too, not just the
  incremental one (review 2.5).
- **Incremental (damage-tracked) rendering.** The base render used to repaint
  the whole view into a fresh buffer and diff the entire screen every frame, so
  a one-character edit cost the same as a full redraw (the bulk of per-keystroke
  CPU). The paint buffer now starts as a copy of the previous frame and the
  buffer write paths change-detect, so the dirty set — and therefore the diff —
  covers only the cells that actually changed; cells painted last frame but not
  this one are blanked (vacated content). This is gated to the safe case (no
  overlays this or last frame, unchanged size, diff rendering on) with a
  full-repaint fallback and an `renderer.incremental_render` off-switch, and is
  byte-for-byte identical on screen to the full-repaint path. Measured ~32% less
  per-render CPU on a localized edit in a 40-row view (review 2.5).
- **Faster per-frame paint: empty screen-buffer cells share one blank `Cell`.**
  `ScreenBuffer` used to allocate a distinct `Cell(" ")` for every position on
  every render (a fresh buffer is composed each frame), which profiling showed
  was the single largest per-keystroke cost — far more than the template
  re-execution or VNode diff. Empty positions now reference one shared blank
  cell, which is safe because the pipeline replaces cell slots and never mutates
  a cell in place. Measured ~17% less CPU per render on a 40-row bound-input
  view, with byte-for-byte identical output (review 2.5, partial; further wins —
  buffer reuse and locality-limited diffing — tracked in `roadmap.md`).
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
