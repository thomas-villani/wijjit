# Wijjit 0.1.0 — API-Consistency & Clarity Audit

Pre-release audit of `src/wijjit/` (~67k LOC) by 6 parallel reviewers, one per
layer. **Focus is narrow and deliberate:** *consistency of API patterns* and
*clarity of code* — NOT correctness. Correctness was covered separately in
`CODE_REVIEW_0.1.0.md` (5 fix batches already landed); this audit explicitly
avoids re-reporting those, and any genuinely new correctness smells are parked
at the bottom of each section as "out of scope."

Every finding is grounded in `file:line` refs the reviewer opened and verified.

## Why this matters now (read first)

The single most important framing for a 0.1.0: **API-shape inconsistencies
calcify into backward-compat obligations the moment we publish.** A user who
learns `{% barchart color="gradient" %}` and then writes `{% linechart
color="gradient" %}` (getting a literal color named "gradient") has learned a
broken mental model we can no longer fix without a breaking change. Renaming a
constructor param, unifying `class` vs `classes`, or picking one `border` vs
`border_style` spelling is *free* today and *expensive* after release.

Clarity/dedup findings (dead code, copy-paste, magic numbers, docstring fixes)
carry no compat risk and can land anytime — but the cheap pre-1.0 dead-code
removals are worth doing now so we don't ship deprecated-on-arrival surface.

So findings below are tiered by **release urgency**, not raw severity:

- **P1 — decide before tagging 0.1.0** (public API shape that calcifies)
- **P2 — should-fix** (internal consistency, dedup, DX; low risk)
- **P3 — cleanup** (clarity nits, internal naming; anytime)

---

## Decisions log (locked with maintainer)

Surface-shape choices agreed for the 0.1.0 fix batch. Renames keep undocumented
aliases so the ~69 examples/goldens don't all churn at once.

- **D1 (CC-1) — `class`/`classes`:** Two layers by design — `class` is the
  documented *template* spelling; `classes` is the *Python* param (`class` is a
  reserved keyword). Keep both. Document `class` only; leave `classes` working as
  a silent template passthrough. **Real fix:** one shared `class`→`classes`
  normalization used by *every* tag, including the layout containers
  (`frame`/`vstack`/`hstack`/`grid`) which drop it today.
- **D2 (CC-2) — Border:** `border` stays the canonical name (template + intent);
  `border_style` becomes the documented alias (it's the Python attribute name).
  Apply uniformly to every bordered widget. **Single uniform default =
  `"single"`** across all widgets (charts + `Tree` currently default to no
  border and will gain one → regenerate their goldens). One `has_border(value)`
  helper treats `None`/`"none"`/`""` as no border. **Replace BarChart's
  `show_border: bool` with `border: str`** (gains style choice).
- **D3 (CC-3) — Chart `color`:** Rename the *mode* param to `color_mode`
  (`"default"/"gradient"/"threshold"`) on bar/column/gauge; reserve `color` for
  literal colors everywhere; document `color_scale` uniformly as "palette name."
- **D4 (CC-4) — Layout gap:** Canonical scalar is **`spacing`** (least churn,
  already dominant). Standardize per-axis overrides as `row_gap`/`column_gap`
  (full words) everywhere; kill the `col_gap` spelling. `gutter` rejected.
- **D5 (CC-5) — `tab_index`:** Add `tab_index: int | None = None` to every
  focusable element constructor (all inputs + `Link`/`Pager`/`TabbedPanel`) and
  forward to `super().__init__`. Makes custom tab flow reachable from Python.
- **D6 (CC-6) — value/data access:** `value` property on TextArea/CodeEditor;
  `data` property on Table; `lines` property on LogView; ProgressBar
  `max`→`max_value` (keep `max` alias). All delegate to existing setters so
  reactive assignment is uniform.

---

## Implementation plan (next session — fix batch off `main`)

Branch off `main` (mirrors the prior `fix/0.1.0-code-review-batchN` convention).
Renames keep undocumented back-compat aliases so the ~69 examples/goldens don't
all churn. Land as one tested batch; gate on full suite + `ruff check src/` +
`mypy --strict src/` all clean before finishing.

**Step 1 — Shared helpers (no behavior change):**
- [LANDED — commit 0fd6852] One tag normalization path (`class`→`classes`,
  `tabindex`→`tab_index`) used by *every* tag incl. layout containers; delete
  `apply_tabindex` and the per-family `kwargs.get("class")` copies (D1, CC-1 /
  RENDER-X1, RENDER-X2). NOTE: layout containers now forward the prop; only
  `Frame` (a styled Element) is themed by it — `vstack`/`hstack`/`grid` are pure
  layout nodes with no styling surface, so the prop is carried but inert there.
- [LANDED — commit 2462604] Add `has_border(value) -> bool` (None/"none"/"" = no
  border); route the *tag-level* border-overhead checks through it (D2, CC-2 /
  RENDER-X3). Also fixes the latent "none"-string overhead bug at the tag layer.
- [LANDED — commit 0fd6852] Use `safe_int` for every numeric tag attr (RENDER-X6).
- [PARTIAL] Added the `BORDER_THICKNESS` constant (commit 2462604). The
  `inner_dimensions()` helper + migration of the ~10 `2`/`-2` geometry sites
  (LAYTERM-X3) is pure internal geometry dedup with golden risk and no API-shape
  impact — **deferred to fold into Step 3** (which already touches border
  geometry) or a later dedup batch.

**Step 2 — Constructor params (additive, low risk):** [LANDED — commits 14de967, b4ed603]
- [LANDED] `tab_index: int | None = None` on every focusable element + forward to
  `super().__init__` (D5, CC-5 / INPUT-X1, DISPLAY-X5). Non-focusable charts
  intentionally excluded (inert). Link/Pager/TabbedPanel tab_index kept distinct
  from TabbedPanel.active_tab_index.
- [LANDED] `value` property on TextArea/CodeEditor (no-op-write guarded so the
  reconciled prop doesn't reset the cursor); `data` on Table (syncs _raw_data +
  sort + scroll); `lines` on LogView (delegates to set_lines); ProgressBar
  `max`→`max_value` (alias `max`) (D6, CC-6 / INPUT-2, DISPLAY-1/3).
- [LANDED] Widen `classes` annotations to `str | list[str] | set[str] | None`
  across input + display + menu/modal elements (CC-9).

**Step 3 — Renames with aliases:**
- Border: `border` canonical, `border_style` alias, uniform default `"single"`,
  replace BarChart `show_border` with `border` (D2 / RENDER-X4, DISPLAY-X4).
- Chart mode param `color`→`color_mode` on bar/column/gauge; reserve `color` for
  literals (D3, CC-3 / DISPLAY-X1).
- Gap: canonical `spacing` + `row_gap`/`column_gap` everywhere; drop `col_gap`
  (D4, CC-4 / LAYTERM-X1).

**Step 4 — Verify:** regenerate charts + `Tree` border goldens; run full suite
(`--ignore=tests/benchmarks`) + ruff + mypy. Tick items in this doc as landed.

> Deferred to follow-up batches (not in the D1–D6 surface set): the dedup/
> dead-code cleanups (CC-10, CC-11), logging/loop-convention sweeps (CC-12), the
> public-docstring corrections (CC-13), and the internal manager naming (CC-14).
> Two "out of scope" notes are arguably real bugs worth their own look: the
> uncapped `read_input_async` paste loop (LAYTERM B.4) and
> `Config.from_object` dotted-path import (API B.6).

---

## Part A — Cross-cutting themes (synthesized across reviewers)

These recur across multiple layers; fixing each centrally is higher-leverage
than the per-area entries. Finding IDs in brackets point into Part B.

### CC-1 (P1) — Template attribute naming/normalization is not uniform
The author-facing template attribute surface — the *real* public API for most
users — handles the same attributes four different ways.
- `class` → `classes` is normalized via `normalize_element_kwargs` on input
  tags, hand-rolled as `kwargs.get("class")` on chart/display/dialog/menu tags,
  and **silently dropped entirely** on layout containers (`{% frame
  class="card" %}` produces no `classes` prop). [RENDER-X1, **HIGH**]
- `tabindex` → `tab_index` reaches input + most display tags but only
  `barchart` among the six chart tags. [RENDER-X2]
- Two overlapping helpers (`normalize_element_kwargs` vs `apply_tabindex`) do
  the same job with divergent coverage — that's *why* the gaps exist. [RENDER-X2]
- `int()` vs `safe_int()` for numeric attrs is mixed even within one module, so
  `width="40px"` raises an uncaught `ValueError` on some tags and degrades
  gracefully on others. [RENDER-X6]

**Action:** route *every* tag (incl. layout containers) through one shared
normalize-and-forward path; delete `apply_tabindex`; use `safe_int` for all
numeric coercion.

### CC-2 (P1) — Border API is inconsistent in three dimensions
Spanning tags, display, and input elements:
- **Attribute name:** `border` (frame/table/list/logview/dropdown) vs
  `border_style` (select/checkboxgroup/radiogroup) vs boolean `show_border`
  (BarChart only). [RENDER-X4, DISPLAY-X4]
- **Disabling a border:** `border_style="none"`, vs `border=None`, vs
  `show_border=False`, vs `border_style is not None` checks that treat the
  string `"none"` as a real border (the known overhead bug). [RENDER-X3]
- **`"none"` normalization** is duplicated in 4 input elements and only
  TextArea's copy maps `"none"`/`""` → no border. [INPUT-X4]
- **Defaults differ:** Tree defaults `border="none"`, everything else
  `"single"`. [RENDER-X4]

**Action:** pick `border` as the one public name (keep `border_style` as a
documented alias), one `has_border(value)` helper treating
`None`/`"none"`/`""` as no border, one default, and document any exception.

### CC-3 (P1) — `color` means two incompatible things on charts
`color` is a *mode enum* (`"default"/"gradient"/"threshold"`) on BarChart,
ColumnChart, Gauge — but a *literal color string* on LineChart, Sparkline,
Spinner; HeatMap has no `color` at all and overloads `color_scale`. [DISPLAY-X1,
**HIGH**]

**Action:** rename the mode param to `color_mode` (or `coloring`) on
bar/column/gauge; reserve `color` for literal colors everywhere; document
`color_scale` uniformly as "palette name." This is a headline-feature public
prop — fix before release.

### CC-4 (P1) — "Gap between children" has three names in the layout engine
`spacing` (Container/VStack) vs `column_gap`/`row_gap` (HStack) vs
`col_gap`/`row_gap` (Grid) — and HStack spells the full word `column_gap` while
Grid abbreviates `col_gap` for the *same axis*. VStack has no `*_gap` at all.
[LAYTERM-X1, **HIGH**]

**Action:** standardize one pair (`row_gap`/`column_gap`) across
VStack/HStack/Grid; keep `spacing` as a documented alias.

### CC-5 (P1) — `tab_index` is unreachable through element constructors
`Element.__init__` accepts and documents `tab_index`, but **no input element
and several focusable display elements** (`Link`, `Pager`, `TabbedPanel`) accept
it — they call `super().__init__(id=id, classes=classes)`, hardcoding
`tab_index=None`. `TextInput(id="x", tab_index=2)` is a `TypeError`; tab order
only works because the tag layer pokes the attribute post-construction. The
contract the base advertises is unreachable via the Python API that CLAUDE.md
tells examples/tests to use. [INPUT-X1, DISPLAY-X5]

**Action:** add `tab_index: int | None = None` to every focusable element
`__init__` and forward it to `super().__init__`.

### CC-6 (P1) — Value/data access surface is inconsistent across siblings
- **Inputs:** `.value` is a plain attr (TextInput) / property (Slider, Select),
  but TextArea & CodeEditor have *no* `.value` — only `get_value()`/`set_value()`.
  Generic `element.value` raises `AttributeError` on TextArea. [INPUT-2]
- **Display:** `data` is a reactive property (charts, Tree) on some widgets and
  a raw working field on Table (assigning `table.data` desyncs `_raw_data` +
  scroll); LogView has only `set_lines()`, no `lines` property. [DISPLAY-1]
- **Collection param name** is `data` / `items` / `lines` across Table-Tree /
  ListView / LogView. [DISPLAY-2]
- **Scale ceiling:** ProgressBar uses `max` (shadows builtin, no `min`); Gauge
  uses `min_value`/`max_value`. [DISPLAY-3]

**Action:** give TextArea/CodeEditor a `value` property, Table a `data`
property and LogView a `lines` property (delegating to the setters), and rename
ProgressBar `max`→`max_value` (alias `max`). These are read/write API shape —
decide pre-release.

### CC-7 (P1) — Activation/callback vocabulary is not standardized
The "user activated this control" callback is `on_action` (Checkbox/Radio/
TextInput), `on_toggle` (Toggle — no `on_action`), and `on_click`/`on_activate`
(Button). `on_change` is universal except on Button. `checked` fires `on_change`
on direct assignment for Toggle but is a silent bare attr on Checkbox/Radio, so
a reconciler-driven `checked` change fires a callback on one and not the other.
[INPUT-3, INPUT-1]

**Action:** document a callback vocabulary (`on_change` = value changed,
`on_action` = activation) and align names; add `on_action` to Toggle; make
`checked` behave identically across the three boolean inputs.

### CC-8 (P2) — Callbacks bypass `invoke_callback` (Theme-B residue)
The correctness review routed Slider/Toggle/etc. through `invoke_callback`
(async-aware + exception-logging), but these display/overlay sites still call
the callback directly: `on_dismiss`, `action_callback` (Notification),
`on_page_change` (Pager), `on_tab_change` (TabbedPanel), `on_item_select` /
`close_callback` (Menu). An `async def on_tab_change` is created and never
awaited. [DISPLAY-X3] Also: overridden `handle_mouse` in every input element
never calls `super().handle_mouse`, so the base's documented `on_double_click`/
`on_context_menu` never fire for inputs. [INPUT-X5]

**Action:** route the six display/overlay callbacks through `invoke_callback`;
chain to `super().handle_mouse` (or drop those base callbacks).

### CC-9 (P2) — `classes` type annotation drops `set[str]` in most subclasses
The base accepts and normalizes a `set[str]`, but most input and display
subclasses annotate `str | list[str] | None`, so `classes={"a","b"}` type-errors
under mypy despite working at runtime. [INPUT-4, DISPLAY-4]

**Action:** use `str | list[str] | set[str] | None` (or a shared type alias)
everywhere.

### CC-10 (P2) — Pervasive copy-paste of logic that has already drifted
The highest drift hazards (each already diverged between copies):
- `read_input` vs `read_input_async`: ~250 lines near-duplicated; the async
  paste loop **lost the `MAX_PASTE_SIZE` cap** the sync path has. [LAYTERM-1]
- Scroll key/wheel + `on_scroll` block re-inlined ~50× across the six
  scrollables; Tree/LogView auto-scroll has already diverged from ListView.
  [DISPLAY-X2]
- View lifecycle-hook dispatch triplicated; `_navigate_sync_impl` vs
  `_navigate_async_impl` ~80 lines near-identical. [CORE-X3]
- Border-size `2`/`-2` magic number re-derived in ~10 geometry sites with no
  `BORDER_THICKNESS` constant. [LAYTERM-X3]
- Size-spec resolution copy-pasted across VStack/HStack/Grid. [LAYTERM-X4]
- `_normalize_border_style` ×4 [INPUT-X4]; highlight-state-key property ×3
  [INPUT-X3]; chart `_get_*_color` wrappers ×3 [DISPLAY-X6]; chart `parse()`
  loop ×6 [RENDER-X5]; State reserved-key error message ×5 [CORE-10]; State
  batch-coalesce block ×2 [CORE-13]; `has_suggestions`/`suggestion_count` ×2
  [API-10]; `DirtyRegion` re-implements `Bounds` geometry [LAYTERM-8].

**Action:** extract shared helpers. None are API-visible, so they're low-risk,
but they're where future bugs will be applied inconsistently.

### CC-11 (P2) — Dead / deprecated code to drop before 1.0
Shipping deprecated-on-arrival surface invites users to depend on it:
- `Style.to_ansi` documented-DEPRECATED on the public Style dataclass. [RENDER-6]
- `BraileCanvas.to_lines`/`render` marked `.. deprecated:: 0.1.0`. [DISPLAY out-of-scope]
- `Direction` enum unused. [LAYTERM-2] `BORDER_CHARS` legacy alias unused.
  [LAYTERM-12] `layout/__init__.py` entirely commented out. [LAYTERM-3]
- `is_ephemeral_prop` exported but never called (check inlined everywhere).
  [CORE-7] `ViewRouter.register_view` unused, docstring contradicts code.
  [CORE-9]
- 3 unused word-helpers in `autocomplete/utils.py` [API-4]; 3 unused cursor
  helpers in `inline/cursor.py` (and `InlineApp` hardcodes an escape one of them
  provides) [API-5]; commented-out `_grid` refs in HeatMap referencing a
  never-defined attr [DISPLAY-7]; large dead `CSSParser` compat class
  (also in CODE_REVIEW).

**Action:** remove (after confirming no example/test imports each).

### CC-12 (P2) — Logging-convention and deprecated-loop deviations
- CLAUDE.md mandates `get_logger(__name__)`; `autocomplete/resolver.py` and
  `rendering/html_adapter.py` use `logging.getLogger` directly. [API-2, RENDER-1]
- `state.py`/`app.py` were migrated to `get_running_loop()`, but 4 core sites
  still call deprecated `asyncio.get_event_loop()` inside coroutines (emits
  DeprecationWarning on 3.12+). [CORE-X1]

**Action:** mechanical sweep to the mandated helpers.

### CC-13 (P2) — Public docstrings reference names/behavior that don't exist
Copy-paste examples on public methods that fail immediately:
- `app.show_modal/show_dropdown/show_tooltip` docstrings import a nonexistent
  module (`wijjit.elements.overlay`), a nonexistent `Tooltip` class, and call a
  nonexistent `app.get_element()`. [CORE-1]
- `logging_config` module docstring names `configure_from_environment` (actual:
  `configure_logging_from_environment`). [API-1]
- `focus_next`/`focus_previous` docstrings claim a boundary `False` return but
  the code wraps around. [CORE-2]
- `ScreenBuffer.get_merged_dirty_regions` docstring claims rectangle merging it
  doesn't do. [LAYTERM-5] Horizontal-scrollbar docstring names U+2500/U+2501 but
  emits ASCII `-`/`=`. [LAYTERM-6]
- `load_filesystem_tree` documents an `mtime` key it never produces. [API-3]

**Action:** correct each; these are user-facing and trivially wrong.

### CC-14 (P3) — Manager/method naming & return-shape divergence (internal)
- Sibling "clear a collection" methods return 4 different shapes
  (`list`/`int`/`None`/`bool`). [CORE-X2] Overlay lifecycle uses `push`/`pop`,
  Notification uses `add`/`remove`/`dismiss_*`. [CORE-X2, CORE-3]
- `async_batch_update` is the lone `async_`-prefix among `_async`-suffix
  siblings. [CORE-X4]
- `on()` is a non-decorator while `on_key`/`on_action` are decorators. [CORE-5]
- `State.on_change` has no `off_change` though `watch` has `unwatch`. [CORE-6]
- `clear_cache` means different caches on Renderer vs Reconciler. [CORE-8]
- Hover `get_hovered_element` getter vs `set_hovered` setter; Focus
  `focus_element` vs Hover `set_hovered`. [CORE-12]
- Three manager DI styles (app-passing / explicit params / attribute-injection).
  [CORE-11]
- `show_modal`/`show_dropdown` swap `close_on_*` param order; `show_tooltip`
  drops `on_close`. [CORE-4]
- Notification dismissal (id + `dismiss_notification`) vs overlay dismissal
  (object + reach into manager). [CORE-3]

**Action:** align where cheap; several (`on` decorator form, `off_change`,
`close_overlay`) are small additive API improvements worth doing pre-release;
the rest are internal cleanups.

---

## Part B — Full per-area findings

The complete reviewer output follows, unedited, for traceability. Cross-cutting
items above reference these IDs.

### B.1 — Core layer (prefix: CORE)

#### Cross-cutting patterns
- **[CORE-X1] Deprecated `asyncio.get_event_loop()` survives in 4 sites after `state.py` migrated to `get_running_loop()`** — `events.py:518`, `event_loop.py:156`, `view_router.py:596`, `view_router.py:625` vs `state.py:539`, `app.py:1586`. API-CONSISTENCY | MED. Half-migrated; the 4 calls are inside running coroutines, so `get_running_loop()` is safe and correct. Fix: replace all four.
- **[CORE-X2] Sibling "clear a collection" ops return four different shapes** — `overlay.py:337` (`list`), `notification_manager.py:443` (`int`), `focus.py:297` (`None`), `hover.py:83` (`bool`). API-CONSISTENCY | MED. Also create/remove verbs diverge (Overlay push/pop vs Notification add/remove/dismiss_*). Fix: one convention; document differences.
- **[CORE-X3] View lifecycle-hook invocation triplicated** — `view_router.py:590-601`, `:619-628`, `event_loop.py:145-160`. CLARITY | MED. Same try/except + sync-hook-in-executor block ×3; `_navigate_sync_impl` vs `_navigate_async_impl` ~80 lines near-identical. Fix: extract `_run_hook(hook,label)` + factor navigate body.
- **[CORE-X4] Async-variant naming mixes suffix and prefix** — `state.py:438` (`async_batch_update`) vs `set_async`/`flush_pending_async`/`_trigger_change_async`/`check_expired_async`/`run_async`. API-CONSISTENCY | LOW. Fix: rename `async_batch_update`→`batch_update_async` (alias+deprecate).

#### Individual findings
- **[CORE-1] `show_modal`/`show_dropdown`/`show_tooltip` docstrings import a nonexistent module, class, and method** — `app.py:1673,1735-1737,1806`. CLARITY | MED. `from wijjit.elements.overlay import ConfirmDialog/DropdownMenu/Tooltip` (module doesn't exist; correct: `.modal`/`.menu`; no `Tooltip` at all), `app.get_element(...)` (actual: `get_element_by_id`). All fail immediately. Fix: correct paths/method, drop Tooltip example.
- **[CORE-2] `focus_next`/`focus_previous` docstrings contradict wraparound behavior** — `focus.py:158-175,177-194`. CLARITY | MED. Docs say returns False at last/first; code uses modulo wrap, returns False only when list empty. Fix: document cyclic behavior.
- **[CORE-3] Two incompatible handle paradigms for transient UI** — `app.py:1828,1937` (notify→str id, dismiss_notification) vs `app.py:1637,1696,1768` (show_*→Overlay obj, pop via manager; no app-level dismiss). API-CONSISTENCY | MED. Fix: add `app.close_overlay(overlay)` or unify handle type.
- **[CORE-4] `show_modal`/`show_dropdown` swap `close_on_*` param order; `show_tooltip` drops `on_close`** — `app.py:1637-1643,1696-1703,1768-1774`. API-CONSISTENCY | MED. Fix: standardize `(on_close, close_on_escape, close_on_click_outside, ...)`; add on_close to show_tooltip.
- **[CORE-5] `on` is a non-decorator while `on_key`/`on_action` are decorators** — `app.py:743,778,975`. API-CONSISTENCY | LOW. `@app.on(EventType.KEY)` → TypeError. Fix: return a decorator when callback omitted, or document divergence.
- **[CORE-6] `State.on_change` has no removal counterpart though `watch` has `unwatch`** — `state.py:214,240,272`. API-CONSISTENCY | LOW. Fix: add `off_change(callback)`.
- **[CORE-7] Dead public helper `is_ephemeral_prop`, check inlined at every call site** — `vdom.py:339`; consumers `reconciler.py:243,252`, `elements/base.py:785`, `devtools/validate.py:73`. CLARITY | LOW. Fix: remove or route inline checks through it.
- **[CORE-8] `clear_cache` means different caches on Renderer vs Reconciler** — `renderer.py:1971` (template), `reconciler.py:610` (element), `renderer.py:1975` (`clear_element_cache`). CLARITY | LOW. Fix: rename Renderer.clear_cache→clear_template_cache.
- **[CORE-9] `ViewRouter.register_view` unused; docstring contradicts code** — `view_router.py:648`. CLARITY | LOW. Decorator builds its own ViewConfig and never calls it. Fix: remove or make decorator delegate.
- **[CORE-10] Reserved-key validation error message duplicated 5× in State** — `state.py:100-105,156-160,706-711,768-773,796-803`. CLARITY | LOW. Fix: extract `_reserved_key_error(keys)`/`_validate_keys`.
- **[CORE-11] Inconsistent manager dependency-injection styles** — app-passing (`overlay`/`mouse_router`/`event_loop`/`suspend`/`view_router`/`wiring`), explicit params (`notification_manager.py:147`), no-arg+attribute-injection (`focus.py:69`/`hover.py:28`, `dirty_manager` set in `app.py:308,312`). API-CONSISTENCY | LOW. Fix: constructor injection.
- **[CORE-12] Parallel manager getter/setter naming diverges** — `hover.py:33` get_hovered_element / `:43` set_hovered / `:83` clear_hovered vs `focus.py:134` get_focused_element / `:196` focus_element. API-CONSISTENCY | LOW. Fix: align verb/noun.
- **[CORE-13] Batch-context dedup loop duplicated sync/async** — `state.py:332-348` vs `:416-433`. CLARITY | LOW. Fix: `_coalesce_batch_changes()`.
- **[CORE-14] `RenderContext` docstring omits `item_stack` field** — `render_context.py:85-95` vs field `:92`. CLARITY | LOW. Fix: add to Attributes block.

#### Correctness noticed (out of scope)
- `app._configure_logging` docstring (app.py:412) claims it applies LOG_TO_CONSOLE/LOG_FORMAT but never reads LOG_TO_CONSOLE (matches Part 4 "not wired" note).
- `_dispatch_action` (app.py:1546-1557) sets `needs_render=True` synchronously even for async handlers that have only scheduled; usually self-corrects.

---

### B.2 — Input elements + base (prefix: INPUT)

#### Cross-cutting patterns
- **[INPUT-X1] `tab_index` ctor param dropped by every concrete input element** — `base.py:241-246`, vs `text.py:106-120,683-703`, `button.py:77-86`, `checkbox.py:66-74,280-293`, `radio.py:76-85,321-335`, `toggle.py:99-109`, `slider.py:98-111`, `select.py:104-123`, `code_editor.py:467-492`, `datagrid.py:197-210`. API-CONSISTENCY | MED. All call `super().__init__(id=id, classes=classes)`; `TextInput(id="x", tab_index=2)` is TypeError. Fix: add+forward `tab_index`.
- **[INPUT-X2] `action`/`bind` template-metadata wired inconsistently** — `text.py:118-119,131-132`, `slider.py:139-140`, `checkbox.py:86-87`, `radio.py:98-99`, `toggle.py:124-125`, `checkbox.py:319-320`, `radio.py:363-364`, `button.py:97`. API-CONSISTENCY | MED. TextInput/TextArea take them as params; others hardcode `action=None;bind=True`; Button has `action` only. Fix: one convention.
- **[INPUT-X3] Two parallel highlight-state-key mechanisms; group property copy-pasted 3×** — `base.py:279-281`, `app.py:1368-1374`+`menu.py:140,188-189` vs `checkbox.py:322-343`, `radio.py:366-387`, `select.py:203-242`. API-CONSISTENCY | MED. Fix: hoist single `highlight_state_key` property (cf. `ScrollableElement.scroll_state_key`), delete 3 dupes, migrate Menu.
- **[INPUT-X4] `_normalize_border_style` duplicated 4× with divergent `"none"` handling** — `text.py:841-874` (handles none/""), `checkbox.py:345-358`, `radio.py:389-402`, `select.py` (don't). API-CONSISTENCY | MED. Fix: one shared `normalize_border_style()` incl. none/"".
- **[INPUT-X5] Overridden `handle_mouse` never chains to base, dropping `on_double_click`/`on_context_menu`** — `base.py:585-623` vs `text.py:336`, `button.py:119`, `checkbox.py:130`, `radio.py:186`, `toggle.py:316`, `slider.py:343`, `checkbox.py:449`, `radio.py:504`. API-CONSISTENCY | MED. Fix: `await super().handle_mouse(event)` in each fall-through, or drop base callbacks.
- **[INPUT-X6] Hardcoded focus/highlight colors instead of theme resolution, duplicated** — `slider.py:243-244`, `checkbox.py:513-514`, `radio.py:567-569` (inline cyan), `checkbox.py:580-584`, `radio.py:635-639`, `toggle.py:95-97,211,217`, `text.py:477-478`. CLARITY | MED. Fix: resolve single `*:focus`/highlight theme style; named constants; drop inline literal.

#### Individual findings
- **[INPUT-1] `checked` silent plain attr on Checkbox/Radio but callback-firing property on Toggle** — `checkbox.py:78`/`radio.py:90` vs `toggle.py:113,127-152`. API-CONSISTENCY | MED. Reconciler setattr fires on_change on Toggle only. Fix: standardize.
- **[INPUT-2] "Current value" access diverges: `.value` attr vs `get_value()`/`set_value()`** — `text.py:123` vs `text.py:949-1001` (TextArea, no `.value`); `slider.py:142-171`; `select.py:138,150`. API-CONSISTENCY | MED. Fix: give TextArea a `value` property.
- **[INPUT-3] Activation callback name varies; Button lacks `on_change`** — `checkbox.py:83`/`radio.py:95`/`text.py:145` (on_action) vs `toggle.py:121` (on_toggle) vs `button.py:91,94` (on_click/on_activate). API-CONSISTENCY | MED. Fix: add on_action to Toggle; document vocabulary.
- **[INPUT-4] `classes` annotation narrows in every subclass (drops `set[str]`)** — `base.py:244` vs `text.py:109` etc. CLARITY | LOW. Fix: align to `str|list[str]|set[str]|None`.
- **[INPUT-5] `Select.options` is private-backed property while groups use public `self.options`** — `select.py:129,244-269` vs `checkbox.py:299`, `radio.py:342`. API-CONSISTENCY | LOW. Fix: give groups the same property (or shared base).
- **[INPUT-6] `TextArea.rewrap_content` uses `cursor_row = -1` sentinel** — `text.py:1062-1070`. CLARITY | LOW. Fix: `adjust_cursor: bool=True` param on `_apply_hard_wrap_to_line`.

#### Correctness noticed (out of scope)
- Slider.handle_mouse DRAG and MOVE-while-dragging byte-identical (`slider.py:381-400`); one branch likely dead.
- Slider/Checkbox/Radio/Select nav handlers `return True` at boundary when nothing moved (`slider.py:328-330`, `checkbox.py:414-418`) — key consumed not bubbled; inconsistent w/ TextInput/TextArea arrows.

---

### B.3 — Display elements + overlays (prefix: DISPLAY)

#### Cross-cutting patterns
- **[DISPLAY-X1] `color` ctor param means two incompatible things across charts** — `barchart.py:114`, `columnchart.py:108`, `gauge.py:112` (mode enum) vs `linechart.py:101`, `sparkline.py:94`, `spinner.py:109` (literal string); HeatMap overloads `color_scale`. API-CONSISTENCY | HIGH. Fix: rename mode→`color_mode`; reserve `color` for literals; document `color_scale` uniformly.
- **[DISPLAY-X2] Scroll key/mouse + `on_scroll` block copy-pasted ~50 sites across 6 scrollables** — `list.py:472-579`, `table.py:415-509`, `tree.py:904-1094`, `logview.py:608-729`, `contentview.py:534-628`, `barchart.py:266-356`. API-CONSISTENCY | MED. Already drifted (Tree/LogView vs ListView). Fix: hoist `ScrollableElement._notify_scroll()` + default `handle_scroll_key`.
- **[DISPLAY-X3] Several display/overlay callbacks bypass `invoke_callback`** — `notification.py:174,178,345`, `pager.py:293`, `tabbed_panel.py:209`, `menu.py:321,324`. API-CONSISTENCY | MED. async handlers silently never awaited. Fix: route all six through invoke_callback.
- **[DISPLAY-X4] Border API diverges between charts and others** — `barchart.py:117` (`show_border: bool`) vs `list.py:122`/`logview.py:151`/`contentview.py:134`/`table.py:114`/`tree.py:153`/`pager.py:123`/`tabbed_panel.py:112`/`modal.py:61` (`border_style: str`). API-CONSISTENCY | MED. Fix: standardize `border_style: str = "none"`.
- **[DISPLAY-X5] Focusable widgets inconsistently expose `tab_index`** — `link.py:68-75`, `pager.py:117-129`, `tabbed_panel.py:105-114` (omit) vs `barchart.py:118`/`contentview.py:136`/`list.py:126`/`logview.py:153`/`table.py:115`/`tree.py:156` (accept). API-CONSISTENCY | MED. Fix: add+forward `tab_index` on every focusable=True widget.

#### Individual findings
- **[DISPLAY-1] `data` attribute inconsistent: reactive property vs raw working field** — `table.py:124,334` vs charts/Tree `data` property setters (`barchart.py:163-183`, `tree.py:416-428`, ...). API-CONSISTENCY | MED. `table.data=[...]` desyncs `_raw_data`/scroll; LogView has only set_lines. Fix: Table `data` property, LogView `lines` property.
- **[DISPLAY-2] Collection-input param naming inconsistent (`data`/`items`/`lines`)** — `list.py:116` (items), `logview.py:142` (lines), `table.py:107`/`tree.py:144`/charts (data). API-CONSISTENCY | LOW. Fix: document rationale; consider `data` alias.
- **[DISPLAY-3] `ProgressBar` uses `max` (shadows builtin) while `Gauge` uses `min_value`/`max_value`** — `progress.py:101` vs `gauge.py:104-105`. CLARITY | LOW. Fix: rename ProgressBar param→`max_value` (alias `max`).
- **[DISPLAY-4] `classes` annotation drops `set[str]` on most widgets** — `barchart.py:105`/`table.py:106`/`tree.py:143`/`list.py:115`/`gauge.py:102`/`heatmap.py:93` vs base + `link.py:73`/`pager.py:120`/`tabbed_panel.py:108`. API-CONSISTENCY | LOW. Fix: use base annotation everywhere.
- **[DISPLAY-5] `Table` lacks `title` param its sibling bordered scrollables accept** — `table.py:103-115` vs `list.py:123`/`logview.py:152`/`contentview.py:135`/`tree.py:154`. API-CONSISTENCY | LOW. Fix: add `title`.
- **[DISPLAY-6] Residual identical `_get_*_color` wrapper methods across charts** — `barchart.py:363-386`, `columnchart.py:178-201`, `gauge.py:197-211`. API-CONSISTENCY | LOW. Fix: one `chart_utils.resolve_chart_color(...)`.
- **[DISPLAY-7] Dead commented-out code referencing non-existent `self._grid` in HeatMap** — `heatmap.py:264-265,335`. CLARITY | LOW. Fix: delete.

#### Correctness noticed (out of scope)
- `barchart.py:142` `label_width` uses `len(label)` not `visible_length()` (Theme A family).
- `BraileCanvas.to_lines`/`render` marked `.. deprecated:: 0.1.0` (`chart_utils.py:254`) — should be removed before release, not shipped deprecated.

---

### B.4 — Layout + Terminal (prefix: LAYTERM)

#### Cross-cutting patterns
- **[LAYTERM-X1] Three names for "gap between children"** — `engine.py:359` (spacing), `:700-701,725-726` (column_gap/row_gap; spacing silent fallback `:725`), `:1494-1495,1509-1510` (col_gap/row_gap). API-CONSISTENCY | HIGH. HStack `column_gap` vs Grid `col_gap` same axis; VStack none. Fix: one pair across all; spacing as alias.
- **[LAYTERM-X2] Three notions of "ANSI escape sequence" in ansi.py** — `:37-40` (ECMA-48), `:46-86` (`"\x1b["`+scan-until-letter, CSI only), `:458/467/1125/1165` (SGR-only). API-CONSISTENCY | MED. clip_to_width/wrap_text can miscount the framework's own `\x1b[?25h`/OSC. Fix: one shared tokenizer.
- **[LAYTERM-X3] Border-size `2`/`-2` magic number duplicated** — `engine.py:1994-1995,2090-2093`, `frames.py:325-327,758,842,1478-1480`. CLARITY | MED. Fix: `BORDER_THICKNESS` constant + `inner_dimensions()` helper.
- **[LAYTERM-X4] Size-spec resolution copy-pasted; parallel containers factor differently** — `engine.py:240-266,589-626,770-809,1818-1831`. API-CONSISTENCY | MED. HStack extracts helpers, VStack inlines w/ subtly different fallbacks. Fix: shared `resolve_child_size(...)`.
- **[LAYTERM-X5] Axis/direction modeled three ways** — `engine.py:30-34` (Direction enum, dead), `splitpanel.py:165` (orientation str literal), `frames.py:519,1213` (direction int). API-CONSISTENCY | LOW. Fix: one enum; document scroll int sign or replace.

#### Individual findings
- **[LAYTERM-1] `read_input`/`read_input_async` ~250 lines near-duplicated, already drifted** — `input.py:437-691,693-950` (`:580-687` byte-identical to `:839-946`). CLARITY | HIGH. Sync paste capped (`:510`), async `while True:` uncapped (`:770`). Fix: extract `_process_keys(keys, get_more)`.
- **[LAYTERM-2] `Direction` enum is dead code** — `engine.py:30-34`. CLARITY | MED. Fix: delete or use to unify stacks.
- **[LAYTERM-3] `layout/__init__.py` entirely commented out** — `:1-45`. CLARITY | MED. Fix: delete dead block + one-line docstring, or restore curated `__all__`.
- **[LAYTERM-4] Two parallel dirty-region subsystems with different merge semantics/return contracts** — `dirty.py:161-383` (true merge, (x,y,w,h)) vs `screen_buffer.py:268-303` (per-row strips). API-CONSISTENCY | MED. Both live. Fix: delegate or rename one (`get_dirty_rows`).
- **[LAYTERM-5] `ScreenBuffer.get_merged_dirty_regions` docstring contradicts impl** — `:278-303`. CLARITY | MED. Claims rectangle merge; returns per-row strips. Fix: rewrite docstring or implement merge.
- **[LAYTERM-6] Scrollbars inconsistent glyphs, ignore Unicode config, horizontal docstring wrong** — `scroll.py:368-370` (Unicode), `:411-420` (ASCII; docstring names U+2500/U+2501 but emits `-`/`=`). API-CONSISTENCY | MED. Fix: Unicode-aware lookup like get_border_chars; correct docstring.
- **[LAYTERM-7] Scrollbar thumb detected by hardcoded glyph comparison coupling frames→scroll** — `frames.py:1523` (`== "█"`). CLARITY | MED. Fix: renderer returns structured runs / THUMB_CHAR/TRACK_CHAR constants.
- **[LAYTERM-8] `DirtyRegion` re-implements `Bounds` geometry** — `dirty.py:13-158` vs `bounds.py:52-142`. CLARITY | LOW. Fix: subclass/compose Bounds + merge helpers.
- **[LAYTERM-9] input.py hand-writes mouse escapes with octal `\033` to stdout** — `input.py:1035-1037,1051-1053`. API-CONSISTENCY | LOW. Only octal use; bypasses ANSIScreen/ScreenManager. Fix: add `ANSIScreen.mouse_tracking_on/off`.
- **[LAYTERM-10] `colorize` uses different color model + param name than rest of terminal layer** — `ansi.py:748-754` (`color=` escape-string vs `fg_color` RGB elsewhere). API-CONSISTENCY | LOW. Fix: rename `color`→`fg_color`, document string-ANSI path.
- **[LAYTERM-11] `CellPool` unstyled fast-path only for spaces** — `cell.py:346-347` vs `:368-417`. CLARITY | LOW. `get_pooled_cell(' ')` misses fast path. Fix: give get_char same path or delegate spaces.
- **[LAYTERM-12] Deprecated `BORDER_CHARS` alias retained, no users** — `frames.py:120`. CLARITY | LOW. Fix: remove.

#### Correctness noticed (out of scope)
- `read_input_async` paste loop lacks MAX_PASTE_SIZE cap + truncation warning the sync path has (`input.py:770` vs `:510`) — unbounded aggregation on the primary runtime path.
- `ElementNode` dynamic-sizing min_width=10/min_height=5 unexplained magic (`engine.py:246-247,260-261`).
- `get_merged_dirty_regions` full-width row strips → diff renderer re-scans every column of any touched row (perf).

---

### B.5 — Tags + Styling + Rendering (prefix: RENDER)

#### Cross-cutting patterns
- **[RENDER-X1] Three mechanisms for `class`→`classes`; layout containers drop it entirely** — `layout.py:113`/`input.py:119`/`charts.py:73`/`display.py:137`/`dialogs.py:132`/`menu.py:99`; `_render_frame` `layout.py:888-1098`. API-CONSISTENCY | HIGH. `{% frame class="card" %}` produces no classes prop. Fix: one shared normalize+forward path incl. layout; delete per-family copies + apply_tabindex.
- **[RENDER-X2] Two overlapping normalization helpers with divergent coverage** — `layout.py:113` (normalize_element_kwargs) vs `:146` (apply_tabindex); only barchart among charts (`charts.py:191`). API-CONSISTENCY | MED. Fix: collapse to one; drop apply_tabindex.
- **[RENDER-X3] "Is there a border?" computed three incompatible ways** — `layout.py:997-1003` (border_map), `input.py:503,506` (`is not None` — "none" wrongly adds overhead), `display.py:927,983` (`!= "none"`). API-CONSISTENCY | MED. Fix: one `has_border(value)` helper.
- **[RENDER-X4] Inconsistent canonical border attr: `border` vs `border_style`** — `layout.py:894`, `display.py:260` (tree default "none", no alias), `input.py:519` (border_style only), `dialogs.py:94` (border only). API-CONSISTENCY | MED. Fix: `border` public + `border_style` alias everywhere; one default.
- **[RENDER-X5] Six chart tags hand-roll identical parse loop, silently drop valueless attrs** — `charts.py:37-47,130-140,234-244,334-344,432-442,542-552`. API-CONSISTENCY | MED. Don't call `parse_tag_attributes` (which now warns). Fix: replace all six bodies.
- **[RENDER-X6] `int()` vs `safe_int()` inconsistent** — `charts.py:104,194,208`, `layout.py:1196-1199`, `display.py:327,616,1133` (mixes within module), `menu.py:252`, `dialogs.py:161`. API-CONSISTENCY | MED. `width="40px"` raises uncaught ValueError on bare-int tags. Fix: safe_int everywhere.

#### Individual findings
- **[RENDER-1] `html_adapter` uses stdlib `logging` not `get_logger`** — `html_adapter.py:12,21`. CLARITY | MED. Lone deviation; bypasses centralized config. Fix: get_logger.
- **[RENDER-2] `content_renderers` mixes `*_to_cells`/`*_to_lines` shapes + inconsistent empty sentinels** — `content_renderers.py:23,53,82,104,142,178,214`. API-CONSISTENCY | MED. Empty: to_lines `[""]` (:50), ansi_to_cells `[[]]` (:71), html_to_cells `[[Cell(" ")]]` (:128,139). Fix: document cells-vs-lines split; one empty-row representation.
- **[RENDER-3] Multiple divergent named-color→RGB maps** — `style.py:398` (web), `html_adapter.py:43` (ANSI, documented), `ansi_adapter.py:216,228`. CLARITY | MED. Fix: centralize ANSI_PALETTE/CSS_PALETTE.
- **[RENDER-4] `resolve_style_by_class` returns inconsistently, can leak theme's stored Style** — `resolver.py:370-383` vs `:222-225`. API-CONSISTENCY | LOW. Returns aliased theme Style (non-frozen) when no pseudo/overrides → mutation corrupts theme dict. Fix: start from `Style().merge(...)` or copy.
- **[RENDER-5] `_parse_extended_color` dead redundant bounds check + misleading membership idiom** — `ansi_adapter.py:370` (:353 already guards), `:113` (`not in "["`). CLARITY | LOW. Fix: delete check; use `!= "["` + comment.
- **[RENDER-6] `Style.to_ansi` documented-DEPRECATED on public Style class** — `style.py:206-268`. CLARITY | LOW. Fix: remove pre-release or annotate unsupported.
- **[RENDER-7] `splitpanel` silently discards interleaved text children, unlike colspan/rowspan (warn+keep)** — `layout.py:1556-1561` vs `:1321-1328,:1414-1421`. CLARITY | LOW. Fix: consistent handling across the three exactly-N-children tags.

#### Correctness noticed (out of scope)
- css_parser only sets attrs True; `font-weight:normal`/`text-decoration:none` can't turn OFF (`css_parser.py:140-169`) — in CODE_REVIEW MEDIUM.
- Large dead CSSParser compat class (`css_parser.py:316-513`); Theme.set_style not invalidating resolver cache (`theme.py:84`) — in CODE_REVIEW. Comma-selector split + per-property cascade appear already fixed.
- select `is not None` overhead (`input.py:503,506`) + `_infer_class_from_element` stale `radiobutton` (`resolver.py:419`) — in CODE_REVIEW.

---

### B.6 — Public API + periphery (prefix: API)

#### Cross-cutting patterns
- **[API-X1] Top-level testing surface asymmetric — `app_from_template` exported, `WijjitHarness` not** — `__init__.py:132-133`, `testing/__init__.py:28-35`. API-CONSISTENCY | MED. Fix: keep testing under `wijjit.testing` and drop the top-level helper, or also export WijjitHarness.
- **[API-X2] `--context`/`context=` silently ignored in app (.py) mode for validate AND tree** — `cli.py:43-46`, `devtools/validate.py:385-386`, `cli.py:62-67`, `devtools/tree.py:141-142`. API-CONSISTENCY | MED. `_validate_app()`/`render_app_file()` take no context. Fix: thread it through, or warn when supplied with `.py`.

#### Individual findings
- **[API-1] `logging_config` module docstring references nonexistent `configure_from_environment`** — `logging_config.py:39`. CLARITY | MED. Actual `configure_logging_from_environment`. Fix: correct.
- **[API-2] `autocomplete/resolver.py` uses `logging.getLogger` not `get_logger`** — `resolver.py:14,22`. API-CONSISTENCY | LOW. Fix: get_logger.
- **[API-3] `load_filesystem_tree` documents `mtime` key it never produces; commented dead code** — `helpers.py:53,130-131`. CLARITY | LOW. Fix: populate or remove from docstring + commented block.
- **[API-4] Three unused word-helpers in `autocomplete/utils.py`** — `:144,171,307`. CLARITY | LOW. Fix: delete or export+test.
- **[API-5] Dead cursor helpers in `inline/cursor.py`; `InlineApp` hardcodes an escape one provides** — `cursor.py:46,62,100`; `app.py:250`. CLARITY | LOW. Fix: use move_cursor_down(); remove unused.
- **[API-6] CLI `run` subparser defined but never dispatched, lacks `func` default** — `cli.py:169-174,196-201`. API-CONSISTENCY | LOW. Fix: set_defaults(func=...) or comment help-only role.
- **[API-7] Config time-unit naming inconsistent** — `config.py:323,349` (sec, no unit) vs `:342,406` (_MS). API-CONSISTENCY | LOW. Fix: suffix seconds keys or keep uniform.
- **[API-8] `DefaultConfig` exported but omitted from CLAUDE.md public-API list** — `__init__.py:10,148`. API-CONSISTENCY | LOW. Fix: add to doc enum or demote.
- **[API-9] `WijjitHarness` overloads builtin `type` in public assertion API** — `harness.py:291,506-512`. CLARITY | LOW. Fix: acceptable; optional `node_type=` alias.
- **[API-10] `has_suggestions`/`suggestion_count` duplicated between AutocompleteState and AutocompletePopup** — `state.py:135,146`; `popup.py:418,429`. CLARITY | LOW. Fix: delegate to self.state.

#### Correctness noticed (out of scope)
- `Config.from_object("a.b.c")` calls `__import__("a.b.c")` → returns top-level `a`, not submodule (Flask uses import_string). `config.py:69-70`.
- `get_logger` gates on `startswith("wijjit")` (no trailing dot) → "wijjitx" in-namespace. Harmless. `logging_config.py:181`.
- `Config.from_pyfile` docstring says silent ignores "missing files" but impl suppresses all OSError. `config.py:83-84,105-108`.
