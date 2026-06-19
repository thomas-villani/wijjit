# Wijjit 0.1.0 — Pre-Release Code Review

Comprehensive multi-agent review of `src/wijjit/` (67k LOC, 10 reviewers, one per layer).
Findings are verified against source with `file:line` references. Severities:
**CRITICAL** (correctness/data-loss, fix before release), **HIGH** (real user-facing
bug), **MEDIUM** (degraded behavior / fragility), **LOW** (smell / DX / cleanup).

---

## Part 0 — Remediation status

**Batch 1** — branch `fix/0.1.0-code-review-batch1`, PR
[#3](https://github.com/thomas-villani/wijjit/pull/3). All changes test-backed;
full suite **2767 passed**, `ruff` / `black` / `mypy --strict` clean. (Note:
`mypy --strict src/` is now fully clean — the ~480-error blocker referenced in
CLAUDE.md is already resolved.)

### Fixed in batch 1

- **CRITICAL #1** `_dispatch_action` unsafe task — *done* (Theme B).
- **CRITICAL #4** TextInput cursor clamp on shrinking bound value — *done*
  (`restore_ephemeral_state` override).
- **CRITICAL #6** `Tree.set_data` double-normalize — *done*.
- **CRITICAL #7** `ColumnChart.render_to` mutation — *done*.
- **Theme B (async dispatch), in full** — `invoke_callback` task retention +
  exception logging; app `_schedule_coroutine`/`_on_background_task_done`;
  `navigate()` synchronous validation; `State` `get_running_loop` +
  `run_coroutine_threadsafe`; autocomplete cancel-prior-fetch; slider / toggle
  / button / datagrid / list / logview / contentview / barchart / link routed
  through `invoke_callback`.
- **CSS HIGHs** — grouped (comma) selectors split per-selector; same-selector
  rules cascade per-property.
- **Terminal restore safety net** — `ScreenManager` `atexit` net (idempotent,
  closed-stream-safe); shutdown cancels only Wijjit-owned tasks
  (embedding-safe), not `asyncio.all_tasks()`.
- **Theme E hit-testing** — horizontal checkbox/radio click ranges derived from
  real per-option widths; menu border columns excluded; menu per-event debug
  logging removed.
- **chart_utils.extract_values** — `assert isinstance` -> explicit `TypeError`
  (was stripped under `python -O`).
- **Config** — `from_pyfile` silent now suppresses `OSError` broadly but lets
  malformed configs raise; `from_prefixed_env` numeric coercion no longer
  mis-parses `"1-2"`.
- **select tag** — disabled dict option without `value` falls back to `label`
  (no more `KeyError` mid-render).
- **completer** — `trigger_key` docstring/comment corrected to actual `"ctrl+/"`.
- **Theme C (partial)** — `Size.calculate` warns once per unknown size string;
  `element_registry` logs dropped props at debug.
- **Theme A** — *documented only* (maintainer decision): `ScreenBuffer`
  docstring states the single-width limitation; wide-char support added to
  `roadmap.md` (near-term).

### Fixed in batch 2

Branch `fix/0.1.0-code-review-batch2` (stacked on batch 1). 17 new tests;
full suite **2784 passed**, `ruff` / `black` / `mypy --strict` clean.

- **Standalone `Radio` sibling deselect (HIGH)** — `Radio.select()` deselects
  same-`name` siblings; `ElementWiringManager.wire_elements()` groups radios by
  name and populates `radio_group`, so mutual exclusion and Up/Down navigation
  work for unbound radios (previously only state-bound radios round-tripped).
- **Select down-arrow scroll overshoot (HIGH)** — arrow handlers now share the
  adaptive `_scroll_margin` (`min(2, visible_rows // 4)`) used by `__init__`;
  small selects no longer scroll prematurely / pin the highlight to the edge.
- **DataGrid Tab/Enter nav (HIGH)** — removed the dead non-editing-ENTER commit
  branch; Tab/Shift+Tab row-wrap uses a single `_move_cursor` delta so the
  column change drives `on_cell_select`; removed redundant `_commit_edit()`
  calls in edit mode (`_move_cursor` already commits) → no more double-commit.
- **Tags `tabindex` normalization (HIGH)** — `apply_tabindex` helper; Table,
  Tree, ListView, LogView, ContentView, BarChart constructors accept
  `tab_index` and the tags forward `tabindex`/`tab_index`.

### Fixed in batch 3

Branch `fix/0.1.0-code-review-batch3` (stacked on batch 2). 16 new tests;
full suite **2798 passed** (excl. benchmarks), `ruff` / `black` / `mypy
--strict` clean.

- **Tree multi-select dropped on `multiple` toggle (HIGH)** — `selected_node_ids`
  was only saved/restored when `self.multiple` was True. Since the reconciler
  captures ephemeral state before applying prop changes and restores it after,
  toggling `multiple` across a re-render discarded the selection. Now always
  saved and restored, so the selection survives the round-trip.
- **Tree bordered auto-scroll viewport (HIGH)** — Down/Right auto-scroll used the
  raw `self.height` (including border rows), scrolling the highlight off-screen
  on a bordered tree; the viewport was never re-synced on resize (unlike
  ListView). Added border-aware `_get_content_height()`, re-sync the viewport in
  `render_to`, and drive auto-scroll math from the viewport size.
- **Pager / TabbedPanel wheel vs keyboard API (HIGH)** — wheel delegated to
  `frame.handle_scroll` while keyboard delegated to `frame.handle_key`; a frame
  with only the keyboard API silently no-opped on the wheel. New shared
  `delegate_frame_scroll` helper (`elements/base.py`) prefers `handle_scroll`
  and falls back to synthesized Up/Down keys; both containers route through it.

### Checked and rejected (not bugs as described)

- "Removed/None props never cleared" (`reconciler._diff_props`) — the diff
  already emits `(old, None)` for removed props and `_apply_prop_changes`
  applies it. No change made.
- "Keyless elements lose ephemeral state" — real only for elements with **no
  id** (VNodes key on `id`); an id-less interactive element can't bind state
  anyway. A proper fix needs a positional/path cache (see deferred).

### Deferred to a follow-up batch (need design, not quick edits)

Highest-value first:

1. **CRITICALs #2, #3, #5 / Theme A buffer rewrite** — width-aware screen
   buffer (continuation cells) + sweep of remaining `len()` width math.
   Documented for 0.1.0; near-term per roadmap.
2. **Reconciler state correctness (HIGH)** — keyless-element ephemeral
   preservation via a positional/path cache; conditional frame-id stability
   (`render_context.py:117`).
3. ~~Standalone `Radio` sibling deselect~~ — **done in batch 2.**
4. **Input HIGHs (partial)** — ~~Select down-arrow scroll margin overshoot~~ and
   ~~DataGrid Tab/Enter dead-commit + double-commit~~ **done in batch 2**;
   *remaining:* CodeEditor soft-wrap scroll desync (`code_editor.py:478,839`).
5. ~~**Display HIGHs** — Tree multi-select ephemeral dropped on `multiple`
   toggle + bordered auto-scroll viewport (`tree.py`); Pager wheel-vs-keyboard
   Frame API (`pager.py:489`, `tabbed_panel.py:782`).~~ — **done in batch 3.**
6. **Tags HIGHs (partial)** — ~~`tabindex`->`tab_index` normalization on
   focusable display/chart tags~~ **done in batch 2** (Table, Tree, ListView,
   LogView, ContentView, BarChart); *remaining:* menu/dialog tag `tabindex`
   (lower value — those elements are rarely tab-ordered) and unknown-attribute
   forwarding.
7. **Theme C remainder** — warnings at the other silent-drop sites (unknown tag
   type, tag attribute parsing, CSS malformed declarations/colors).
8. **Terminal MEDIUMs** — multi-byte input split; legacy mouse coords/clicks;
   `strip_ansi` regex too narrow; `_full_render` style reset.
9. **Theme F** — dead-code removal + chart/dialog/border dedup.
10. Remaining **MEDIUM/LOW** items in Parts 3-4 and the **Public API**
    re-export gaps.

---

## Part 1 — Cross-cutting systemic themes

These recur across many files. Fixing them centrally is higher leverage than the
individual findings below.

### Theme A — `len()` used on terminal text instead of `visible_length()` (wide-char breakage)
CLAUDE.md mandates ANSI-aware width math, but `len()` / raw string slicing is used
pervasively for column arithmetic, cursor positioning, clipping, and padding. Any
CJK / emoji / combining-char content misaligns, overflows borders, and desyncs
cursor/click mapping. Independently flagged by **7 of 10** reviewers:
- `terminal/screen_buffer.py` — buffer model is 1 cell == 1 column; no continuation cell for width-2 glyphs (**CRITICAL**, corrupts diff cursor positioning).
- `terminal/ansi.py` — `clip_to_width` / `wrap_text` count characters, not columns.
- `layout/frames.py:1887-1928, 1711-1741` — cell content render strips ANSI and `len()`-indexes; title truncation ignores wide chars (**CRITICAL**).
- `elements/input/text.py` (TextInput + TextArea), `checkbox.py`, `radio.py`, `code_editor.py`, `datagrid.py` — cursor/scroll/column/padding math (**CRITICAL**).
- `elements/base.py:1299-1302` — HTML render path uses `len(line_cells)`.
- `elements/display/spinner.py` — emoji clock frames sized with `len()`.
- `rendering/content_renderers.py:77,137` — `cells[:width]` slices by cell count.
- `tags/input.py:290` and others — `button_width = len(label) + 4`.

**Action:** sweep for `len(` on rendered text; route all width math through
`visible_length()` / `clip_to_width()`. Make the screen buffer width-aware
(glyph cell + sentinel continuation cell) or document the single-width limitation
prominently for 0.1.0.

### Theme B — Fire-and-forget async dispatch (lost tasks, lost exceptions, sync/async inconsistency)
`asyncio.create_task(...)` is called without retaining a reference (GC can kill the
task) and without routing exceptions, and several elements call user callbacks
directly instead of through the async-aware `invoke_callback`. Flagged by 5 reviewers:
- `core/app.py:1442-1445` — `_dispatch_action` create_task: uncaught `RuntimeError` if no running loop, no strong ref (**CRITICAL**).
- `core/view_router.py:353` — `navigate()` swallows exceptions; `navigate("typo")` silently does nothing (**HIGH**).
- `core/state.py:531,559` — deprecated `get_event_loop()` + non-thread-safe `create_task` from executor threads (**HIGH**).
- `autocomplete/mixin.py:272-277` — per-keystroke create_task, no cancel of prior, races (**MEDIUM**).
- `elements/input/slider.py`, `toggle.py`, `button.py` (keyboard path) — call `on_change`/`on_click` directly; async handlers become un-awaited coroutines (**HIGH/LOW**).
- `elements/display/{list,logview,contentview}.py` — `on_scroll` called directly while `table`/`tree` use `invoke_callback` (**LOW**).
- `elements/base.py:80-91` — `invoke_callback` falls back to `asyncio.run()` (spins a throwaway loop) when no running loop (**MEDIUM**).

**Action:** add a single app-owned task set (`add`, `add_done_callback` → route to
`_handle_error`), use it for all create_task sites; route **every** element callback
through `invoke_callback`; capture the running loop once and use
`call_soon_threadsafe` / `run_coroutine_threadsafe` for cross-thread scheduling.

### Theme C — Silent failure on user/author error (poor DX)
Mistakes produce no diagnostic — the hardest class of bug to debug:
- `core/element_registry.py:268-281` — typo'd template props silently dropped.
- `core/reconciler.py:356-362` — unknown/typo'd tag type silently vanishes.
- `tags/*` — most display/chart tags silently discard unknown attributes; `parse_tag_attributes` silently `break`s on the first valueless attribute (`tags/layout.py:87-97`).
- `styling/css_parser.py` — comma selectors, malformed declarations, unknown properties, bad colors all silently dropped; malformed CSS file → empty theme, no warning.
- `layout/bounds.py:200-223` — unknown size string (`"50px"`, typo) silently → size 0.

**Action:** add `logger.warning` (gated where hot) at each silent-drop site naming
the offending attribute/tag/selector. Consider a shared attribute-extraction helper
for the tags layer.

### Theme D — `render_to` must be a pure read of state
- `elements/display/columnchart.py:262-265` — permanently mutates `self.column_width` during render; columns shrink irreversibly across re-renders (**CRITICAL**).
- `elements/modal.py:299-331` — `AlertDialog.render_to` monkey-patches the shared `style_resolver.resolve_style` without `try/finally`; an exception leaves global styling corrupted (**MEDIUM**).

### Theme E — Click hit-testing math diverges from render math
Several elements compute clickable regions with magic constants instead of the real
rendered widths/offsets:
- `elements/input/checkbox.py:472-474`, `radio.py:511-514` — horizontal groups use `width=5` magic constant; clicks select the wrong option (**HIGH**).
- `elements/menu.py:296-298` — uses full width, ignores border; border clicks fire items (**HIGH**).
- `elements/input/datagrid.py:1314-1322` — entry-line cursor off by ~2 columns vs render.
- `elements/display/table.py:526` — `header_offset` hardcoded; borderless tables mis-map rows.
- `elements/display/tree.py:1108-1109` — `expand_end = expand_start + 3` hardcoded; wrong for 1-char indicator styles.

**Action:** derive hit-test regions from the same width/offset helpers used in render.

### Theme F — Code duplication / dead legacy code
Bug-fix drift hazard; flagged across charts, dialogs, elements, tags:
- Chart `_get_*_color` duplicated 3× (`barchart`/`columnchart`/`gauge`); two divergent color-name→RGB maps; dialog auto-height math duplicated; chart `parse()` loop copy-pasted 6× instead of using `parse_tag_attributes`.
- Dead legacy string-render methods: `progress.py:201-356`, `statusbar.py` `_get_*_color_code`, `tree.py:1604-1651` `_render_node_line`, `select.py:905-956` `_render_option`, `reconciler.py:553-575` `_collect_elements`, `mouse_router.py:377-392` `_route_to_element`.
- Border-drawing block duplicated ~70 lines each across `tree`/`list`/`logview`/`contentview`.
- Identical `to_text`/`to_string` in `screen_buffer.py`; duplicated style-code builder in `cell.py`.
- `_detect_file_paths` copy-pasted in TextInput and TextArea.

---

## Part 2 — CRITICAL findings (must-fix for release)

1. **`_dispatch_action` async task is unsafe** — `core/app.py:1442-1445`. Uncaught `RuntimeError` outside a running loop; task can be GC'd. (Theme B)
2. **Screen buffer corrupts on wide characters** — `terminal/screen_buffer.py:55-122`. Cursor/diff column model desyncs from the terminal for any CJK/emoji. (Theme A)
3. **Frame cell renderer strips ANSI and `len()`-indexes content** — `layout/frames.py:1887-1928`. Frame text loses all color/attributes; wide chars overflow. (Theme A)
4. **TextInput cursor not clamped when bound `value` shrinks** — `text.py` (no `on_update`; cf. TextArea `text.py:3414-3427`). Programmatic value change leaves cursor out of range → wrong insert/delete.
5. **Wide-char math throughout input elements** — `text.py`, `checkbox.py`, `radio.py`, `code_editor.py`, `datagrid.py`. (Theme A)
6. **`Tree.set_data` double-normalizes** — `tree.py:494-504` + setter at `404-422`. Regenerates child ids, silently breaking expansion/selection state.
7. **`ColumnChart.render_to` mutates `self.column_width`** — `columnchart.py:262-265`. Irreversible shrink across renders. (Theme D)

---

## Part 3 — HIGH findings (by layer)

### Core pipeline (`core/`)
- Removed/`None`-valued props never cleared on element — `reconciler.py:230-233, 504-522`. Stale values persist across renders (e.g. `disabled` sticks).
- Keyless elements lose ephemeral state on update — `reconciler.py:462-493`. Cache key `None` → recreate instead of update; loses cursor/scroll/selection. Most elements are keyless.
- Positional frame-ID generation breaks state preservation under conditional layouts — `render_context.py:117`. Conditional frames lose scroll/collapse state.
- Unknown tag types silently vanish — `reconciler.py:356-362`. (Theme C)

### Core runtime (`core/`)
- `navigate()` fire-and-forget swallows exceptions — `view_router.py:353`. (Theme B)
- State async callbacks use deprecated `get_event_loop()` + non-threadsafe `create_task` — `state.py:531,559`. (Theme B)
- Shutdown cancels **all** loop tasks, including the host app's — `event_loop.py:245-255`. Hostile to embedding.
- Non-interactive overlays (tooltips/notifications) swallow clicks to base UI — `mouse_router.py:132-148`. Notifications pushed at TOOLTIP z-index block buttons beneath them.

### Terminal (`terminal/`)
- Multi-byte input split per-byte; legacy "normal" mouse coords wrong past ~95 cols — `input.py:583-630`, `mouse.py:227-256`.
- Normal mouse mode never synthesizes clicks (released button lost → NONE) — `mouse.py`. Legacy mode effectively non-functional (SGR default is fine).
- `strip_ansi` regex too narrow — `ansi.py:22`. Leaves OSC / private-mode CSI (`\x1b[?25h`, the framework's own sequences) in text → `visible_length` overcounts.
- `parse_ansi_text` fragile bounds drop trailing 256/truecolor params — `ansi.py:491-522`.
- `_full_render` doesn't reset style before first row — `screen_buffer.py:483-499`. Attribute bleed on first styled cell after full repaint.

### Layout (`layout/`)
- `Size` fill/percentage classification ambiguous for `"100%"` — `bounds.py:159-223` vs engine consumers. `is_fill` and `is_percentage` overlap; engine and `Size.calculate` disagree on branch order.
- Split-panel `_clamp_ratio` violates stated minimums and disagrees with `_calculate_sizes` — `splitpanel.py:405-418` vs `309-314`. Visual jitter/snapping on resize.
- `_load_state` trusts persisted ratio/collapsed shape unvalidated — `splitpanel.py:483-491`. Corrupt state → wrong sizes or `TypeError` mid-layout.

### Input elements (`elements/input/`)
- Horizontal checkbox/radio group click selects wrong option — `checkbox.py:472`, `radio.py:511`. (Theme E)
- Standalone `Radio` selection never deselects siblings — `radio.py:104-167`. Multiple radios appear checked.
- `Select` Down-arrow scroll margin overshoots on small selects — `select.py:540-548`; margin computed inconsistently vs `__init__`.
- `Slider`/`Toggle` callbacks bypass `invoke_callback` — async handlers never run. (Theme B)
- `DataGrid` Tab/Enter nav: dead commit branch + double-commit + suppressed `on_cell_select` — `datagrid.py:1039-1061, 1155-1168`.
- `CodeEditor` soft-wrap renders actual lines while scroll content size counts wrapped lines — `code_editor.py:478, 839-983`. Scroll desync + clipped long lines.

### Display elements (`elements/display/`)
- Tree multi-select ephemeral state dropped when `multiple` toggles across renders — `tree.py:1137-1164`.
- Tree down/right auto-scroll uses `self.height` not border-adjusted viewport — `tree.py:895-952`. Bordered tree scrolls highlight off-screen; viewport never re-synced in `render_to` (unlike ListView).
- Pager wheel vs keyboard use different Frame APIs; wheel silently no-ops if `handle_scroll` absent — `pager.py:489-494`; same assumption in `tabbed_panel.py:782`.
- Menu border-click fires items + per-event debug logging left in — `menu.py:272-330`. (Themes E + debug-logging)
- `chart_utils.extract_values` uses `assert isinstance(...)` — `chart_utils.py:599`. Breaks under `python -O` (silently drops bad values → label/value length mismatch); cryptic `AssertionError` otherwise. Affects every chart.

### Tags (`tags/`)
- `class`→`classes` and `tabindex`→`tab_index` only normalized on input/layout tags — display/chart/menu/dialog tags use `kwargs.get("class")`; `tab_index` silently ignored on focusable tables/trees. (Theme C)
- Most display/chart tags silently discard unknown attributes — no `**kwargs` forwarding. (Theme C)
- `select` tag: crashes on disabled dict option without `value` (`opt["value"]`), and silently keeps malformed JSON option lines as literal labels — `input.py:463-466, 552-558`.

### Styling (`styling/`)
- Comma-separated selectors stored as one unsplittable key, never match — `css_parser.py:207`. Grouped selectors (very common) silently produce zero styles.
- Same-selector rules overwrite instead of cascade — `css_parser.py:214-216`. Split-property stylesheets lose data.

### Rendering / inline / autocomplete / config
- `CompleterConfig.trigger_key` default `"ctrl+/"` contradicts its docstring (`"ctrl+space"`) and the dead Ctrl+Space handling in `mixin.py:191-199` — `completer.py:48,64`.
- `_position_popup` clamps popup x to element width using a text index + magic `+2`, ignoring input scroll — `mixin.py:368-370`. Popup detaches from the word.
- `from_pyfile(silent=True)` only catches `FileNotFoundError` — `config.py:98-110`. Malformed config crashes startup despite `silent`.
- `from_prefixed_env` numeric coercion mis-parses `"1-2"` etc. → `ValueError` at startup, or silently coerces `"007"`→7 — `config.py:192-193`.

---

## Part 4 — MEDIUM / LOW (condensed)

**Core:** `on_key` registry overwrites handlers sharing a key (`app.py:760`); `shutil.get_terminal_size()` called many times per render, risking mid-resize geometry mismatch; `State` has no locking around callback lists despite documented multi-thread access (`state.py:464+`); `dispatch_async` lacks per-handler exception isolation (`events.py:494`); `set_focus_filter(None)` is a no-op contradicting its docstring (`focus.py:308`); `batch_update` drops all notifications on exception after applying writes (`state.py:315-348`); dropdown trigger bound by label-text equality (`wiring.py:625`); SIGTSTP handler does I/O + sets `suspended` after teardown (`suspend.py:180-231`).

**Terminal:** `resize()` shares Cell references (`screen_buffer.py:361`); `get_merged_dirty_regions` discards x/width (dead optimization) (`screen_buffer.py:266`); async paste loop missing `MAX_PASTE_SIZE` cap the sync path has (`input.py:758`); **no atexit/signal last-resort terminal restore** — hard crash leaves raw mode/alt-screen/mouse on (`input.py:928`, `screen.py:141`); mouse tracking writes to `sys.stdout` bypassing managed output (`input.py:1011`); duplicated `to_text`/`to_string` and style-code builders.

**Layout:** Frame inner dims can go negative (missing `max(0,…)`) (`frames.py:325` etc.); unknown size string → 0 and unguarded `float()` in `get_percentage` (`bounds.py:198`); `space-around` mis-distributes remainder + double-counts `column_gap` (`engine.py:962-989`); dirty-region merge over-merges to bounding box (`dirty.py:98-148`); negative/>100% percentages unclamped; split-panel ctrl detection via substring match (`splitpanel.py:543`).

**Input:** broad `except Exception` around pyperclip with no logging (`text.py:323` etc.); `DataGrid` ragged rows can crash `get_data_as_dataframe` (`datagrid.py:757`); `Select.item_renderer` stored but never invoked (dead documented feature); `Button` keyboard path sync vs mouse async; `Slider` `_drag_start_*` captured but unused.

**Display:** Table sort not stable + string-coerces mixed types (`table.py:383`); ListView detail/divider classification by string-sniffing rendered lines (`list.py:938`); LogView width recompute vs stale `rendered_lines` if `lines` set directly (`logview.py:262`); ContentView re-renders content every frame (`contentview.py:642`); LogView auto-scroll suppressed when content shrinks/equal — breaks tailing of rotated logs (`logview.py:424`); Pager `remove_page` leaves scroll-state keys pointing at wrong page (`pager.py:225`); inconsistent `on_scroll` async handling across scrollables.

**Charts/status/overlays:** BarChart drops last partial multi-row bar (`barchart.py:436`); `calculate_axis_ticks` magnitude via string-parsing scientific notation (`chart_utils.py:430`); Gauge ticks/min-max not reserved in auto-height + uneven tick spacing (`gauge.py:286`); HeatMap legend `bar_width` can go negative (`heatmap.py:344`); StatusBar inline colors limited to 8 + dead `_get_*_color_code`; duplicated color maps & chart color helpers; `BraileCanvas.render()` deprecated in 0.1.0 (just remove); ImageView broad `except` + brittle duck-typing (`image.py:163-181`); dialog auto-height magic numbers duplicated, `TextInputDialog` inconsistent fixed height.

**Tags:** `border="none"` adds border overhead on select/checkboxgroup/radiogroup (`is not None` vs `!= "none"`) (`input.py:498` etc.); bare `int()` vs `safe_int` inconsistency (charts, grid, modal); `radiogroup` mixing `options=` with nested `{% radio %}` duplicates radios silently; `frame` border map masks typos & omits heavy/ascii; `{% tab %}`/`{% page %}` lack out-of-context warnings present for menuitem/treeitem/selectitem.

**Styling:** bad/missing theme file crashes some entry points, silently ignored on others (`css_parser.py:240`, `theme.py:142`); parse errors/unknown props/bad colors silently dropped (`css_parser.py:103-161`); `font-weight:normal`/`text-decoration:none` never turn attributes OFF (`css_parser.py:130-159`); `theme.set_style` doesn't invalidate resolver cache → stale styles (`theme.py:84`, `resolver.py:115`); `_infer_class_from_element` has stale keys (`radiobutton`, `listview→list`) so ListView base styling silently not applied (`resolver.py:414`); malformed hex falls through by luck (`style.py:363`); large dead `CSSParser` compat class pre-1.0. **Doc/feature mismatch:** CLAUDE.md says themes load from JSON but no JSON loader exists.

**Rendering/inline/autocomplete/config:** autocomplete state mutated directly in mixin instead of via `AutocompleteState` (duplicate move/update logic); inline in-place update relies on fragile `\x1b[s`/`\x1b[u` save/restore — drifts when content scrolls (`inline/app.py:248-341`); `ansi_string_to_cells` ESC-skip heuristic `not in "["` + emits trailing lone ESC as a cell (`ansi_adapter.py:110`); `html_adapter.strip_html_tags` broad `except`; `_apply_selected_suggestion` indexes without bounds check (`mixin.py:399`); `from_object(str)` uses `__import__` (returns top package, not submodule) (`config.py:69`); inline frame detection by `__name__ == "Frame"` string match; invalid `WIJJIT_LOG_LEVEL` silently → INFO; `LOG_TO_CONSOLE`/`LOG_FORMAT` config keys not wired.

**Public API:** completer classes (`WordCompleter`, `CallbackCompleter`, `AsyncCompleter`, `StateCompleter`, `CompleterConfig`) not re-exported from top-level `wijjit` despite autocomplete being a headline feature; `Modal`/`Notification` documented under those names but exported as `ModalElement`/`NotificationElement`.

---

## Part 5 — Suggested release sequencing

1. **Theme A (wide chars)** + the two rendering CRITICALs (#2, #3) — systemic correctness, touches the most surface.
2. **Theme B (async dispatch)** with a shared task set + `invoke_callback` everywhere — fixes CRITICAL #1 and several HIGHs at once.
3. **Reconciler state correctness** — removed-prop clearing, keyless-element update, frame-id stability (HIGHs).
4. **CRITICALs #4, #6, #7** (TextInput cursor, Tree.set_data, ColumnChart mutation) — isolated, high-impact, low-risk fixes.
5. **CSS HIGHs** (comma selectors, cascade) — silently break user themes.
6. **Theme C (silent failures)** — add warnings; biggest DX win for early adopters.
7. **Terminal restore safety net** (atexit/signal) — protects users from a wrecked terminal on crash.
8. Sweep **Theme E** (hit-testing) and **Theme F** (dedup/dead code) as cleanup.

**Notable strengths confirmed:** clean VDOM→reconcile→layout→paint separation;
careful overlay clip composition; `Cell` equality optimization; SGR mouse + double-click
synthesis (default path); thread-safe notification manager (a good model for `State`);
graceful theme/style fallbacks; no mutable-default-arg bugs found; no leftover `print()`
debugging. Bare `except:` is essentially absent (broad-but-logged `except Exception` is
the dominant pattern, acceptable for a crash-averse TUI with the noted exceptions).
