# Wijjit Release Plan -> PyPI 0.1.0

This is the single consolidated release document for `0.1.0`. It merges the
former `RELEASE_PLAN.md`, `CODE_REVIEW_0.1.0.md`, `API_AUDIT_0.1.0.md`, and the
root `issues.md`. Everything already completed has been collapsed into the
**Completed** summary at the bottom; the body tracks only what remains.

**Goal:** Ship a polished, correct `0.1.0` to PyPI.

**Current state:**
- Version: **`0.1.0`** (single source: `wijjit.__version__`, hatchling dynamic).
- Tests green (~3000 pass, excl. benchmarks); `ruff check src/` clean;
  `mypy --strict src/` clean; `uv build` produces sdist + wheel; `twine check`
  passes. CI (3 OS x Py 3.11-3.13 + lint + coverage) is green.
- Sphinx docs build clean (0 warnings). Hosting: **GitHub Pages**.
- All bundled examples load and render without crashes; remaining demo issues are
  cosmetic/platform/architectural and deferred to 0.1.1 (see Part 2).

The remaining work is almost entirely the **external, user-gated publish steps**
(Trusted Publishing setup, enabling Pages, a TestPyPI dry-run, tagging) plus a
final CHANGELOG date. See Part 1.

---

## Part 1 - Remaining steps to ship 0.1.0

### 1a - Finalize metadata & version (at tag time)
- [ ] `CHANGELOG.md`: set the `[0.1.0]` date to the actual release date (currently
      `2026-06-28`); keep an empty `[Unreleased]` stub.

### 1b - Docs hosting (GitHub Pages)
- [ ] Enable Pages in repo settings (Source: GitHub Actions). **[user action]**
- [ ] Verify the published site builds and loads before the URL ships in PyPI
      metadata.
      (The `.github/workflows/docs.yml` build->upload->deploy workflow is in
      place and the `Documentation` project URL already points at the Pages site.)

### 1c - Release pipeline hardening
- [ ] (Optional) Add required-reviewer protection to the `pypi` GitHub
      environment so a tag push can't auto-publish without a human gate.
      (The `release.yml` build job already install-smoke-tests the wheel in a
      clean venv before any publish.)

### 1d - Community health & polish
- [ ] Document the `pyperclip` Linux behavior (system clipboard needs xclip/xsel;
      otherwise falls back to an internal clipboard) in README/docs.

### 1e - Trusted Publishing external setup (one-time) **[user actions]**
- [ ] PyPI: register a pending Trusted Publisher - repo `thomas-villani/wijjit`,
      workflow `release.yml`, environment `pypi`.
- [ ] TestPyPI: same, environment `testpypi`.
- [ ] Create GitHub Actions environments named `pypi` and `testpypi`.

### 1f - Build & TestPyPI dry-run
- [ ] Local: `uv build` + `uvx twine check dist/*`.
- [ ] Trigger `release.yml` via `workflow_dispatch` (`target=testpypi`); then in a
      clean venv install from TestPyPI and smoke-test (import + a headless
      example). Note: a TestPyPI version cannot be re-uploaded - bump a local
      `.devN` if a retry is needed.

### 1g - Repo hygiene (before tagging)
- [ ] Delete the scratch file `todo-release.md` (0.1.1 example ideas) before
      tagging.

### 1h - Cut the release
- [ ] Commit the version bump on `main`, `git tag v0.1.0`, `git push origin
      v0.1.0`. The tag triggers `release.yml` -> build (+ install-smoke) ->
      publish to PyPI via OIDC -> GitHub Release from the CHANGELOG section.
- [ ] Post-release: clean-venv `pip install wijjit` -> import + headless
      hello-world; confirm the PyPI page renders the README and all project URLs
      (incl. the Pages docs URL) resolve.

### Definition of Done for 0.1.0
1. All examples run without crashes; open bugs closed or explicitly deferred to
   0.1.1 (Part 2).
2. CI fully green (tests + ruff + mypy) on all matrix combos.
3. Docs build cleanly, deploy to GitHub Pages, and cover the getting-started path
   + API reference; the `Documentation` URL resolves.
4. `pip install wijjit==0.1.0` works on Linux/macOS/Windows, Py 3.11-3.13.
5. Tagged `v0.1.0`, CHANGELOG finalized, GitHub Release published; community
   health files + README badges in place.

---

## Part 2 - Deferred to 0.1.1

These are intentionally out of scope for 0.1.0: demo-level, platform-specific
(Windows input), cosmetic, or architecture-level (layout/render/reconcile) work
not suitable for a rushed pre-release fix. Root causes are preserved so the fix
can start from the analysis, not a fresh repro. Cross-referenced in `roadmap.md`.

### 2a - Framework: correctness / architecture

- **Wide-char (Theme A) screen-buffer rewrite.** The buffer model is 1 cell == 1
  column with no continuation cell for width-2 glyphs, so CJK/emoji desync the
  diff renderer's cursor positioning (`terminal/screen_buffer.py`), and `len()`/
  raw slicing is still used for width math in several input elements
  (`text.py`, `checkbox.py`, `radio.py`, `code_editor.py`, `datagrid.py`) and the
  frame cell renderer (`layout/frames.py`). This is also the root of the spinner
  "clock...k" residue and scroll-ghost dots. Documented as a known limitation for
  0.1.0. Fix needs glyph cell + sentinel continuation cell + width-aware diff
  positioning across `paint_context`/`screen_buffer`/the diff renderer.
- **Reconciler ephemeral-state correctness.** (1) Keyless elements lose ephemeral
  state (cursor/scroll/selection) on update because VNodes key on `id` - needs a
  positional/path cache (`reconciler.py`). (2) Positional frame-ID generation
  breaks scroll/collapse preservation under conditional layouts
  (`render_context.py`). This is also the true root of tree "expand all" not
  taking effect on live updates (external state writes don't repaint the tree
  deterministically; wiring runs after paint).
- **CodeEditor soft-wrap scroll desync** - renders actual lines while scroll
  content size counts wrapped lines; long lines clip (`code_editor.py:478,839`).
- **Unknown-attribute forwarding on tags** - deliberately not done: forwarding
  arbitrary tag kwargs to the VNode is unsafe (the registry only filters by
  signature on *create*, so the *update* path would `setattr` typo'd attributes).
  Dropped props are already logged at debug by `element_registry`.
- **Legacy "normal" mouse mode + per-byte multi-byte input** (`mouse.py`,
  `input.py`) - SGR is the default and works; the legacy path needs bypassing
  prompt_toolkit's UTF-8 decode (architectural, low value).
- **Windows alt-/ctrl- key combos** (layout demo `[R][S][H][Q]` hints) - the
  Win32 ESC-timeout lookahead likely never synthesizes `alt+` combos; verify on a
  real console and document as a known limitation if it's a prompt_toolkit/Win32
  limit.
- **Horizontal scroll for child-content frames** - a multi-file layout+render
  feature: lay child content out at intrinsic width under `overflow_x=scroll/auto`,
  compute the horizontal extent, add a child-content horizontal scroll manager,
  and thread `scroll_offset_x` + x-clip through the renderer (`frames.py`,
  `engine.py`, `renderer.py`). Works today for TextArea and frame *text* content.
- **Frame overflow / clip-region on scroll** - "features panel overflows the
  frame top on scroll" (clip region not clamping to frame borders) and
  frame_overflow's HStack width distribution for `3x50%` in one row. Needs a
  focused layout-engine repro.

### 2b - Framework: internal dedup / cleanup (no API-shape risk)

From the code-review Theme F and the API-audit CC-10/CC-14 tails. None are
API-visible; they're where future bugs get applied inconsistently.
- `read_input` vs `read_input_async` (~250 lines near-duplicated); scroll
  key/wheel + `on_scroll` block re-inlined ~50x across the six scrollables;
  view lifecycle-hook dispatch + `_navigate_sync/async_impl` near-duplicated;
  border `2`/`-2` geometry (add `inner_dimensions()` helper - `BORDER_THICKNESS`
  constant already landed); size-spec resolution across VStack/HStack/Grid; chart
  `_get_*_color` wrappers; State reserved-key message x5; `DirtyRegion`
  re-implements `Bounds` geometry.
- Dead legacy string-render methods (`progress.py`, `statusbar.py`, `tree.py`,
  `select.py`, `reconciler._collect_elements`, `mouse_router._route_to_element`);
  large dead `CSSParser` compat class; divergent named-color->RGB maps
  (centralize `ANSI_PALETTE`/`CSS_PALETTE`).
- Manager-naming nits (CC-14 remainder): `clear_cache` means different caches on
  Renderer vs Reconciler; hover/focus getter-setter verb parity; three manager DI
  styles.

### 2c - Remaining MEDIUM/LOW correctness items (condensed)

Lower-severity items surfaced by the code review, not release-blocking:
- **Core:** `on_key` registry overwrites handlers sharing a key; `State` has no
  locking around callback lists despite documented multi-thread access;
  `batch_update` drops all notifications on exception after applying writes;
  `dispatch_async` lacks per-handler exception isolation; `set_focus_filter(None)`
  is a no-op contradicting its docstring; non-interactive overlays
  (tooltips/notifications at TOOLTIP z-index) can swallow clicks to base UI.
- **Layout:** frame inner dims can go negative (missing `max(0,...)`);
  `space-around` mis-distributes remainder + double-counts `column_gap`;
  split-panel `_clamp_ratio` vs `_calculate_sizes` disagreement (resize jitter)
  and unvalidated persisted state; `Size` fill/percentage classification
  ambiguous for `"100%"`.
- **Input:** `Select.item_renderer` stored but never invoked (dead documented
  feature); `DataGrid` ragged rows can crash `get_data_as_dataframe`; overridden
  `handle_mouse` never chains to `super()`, so `on_double_click`/`on_context_menu`
  never fire for inputs.
- **Display:** Table sort not stable + string-coerces mixed types; LogView
  auto-scroll suppressed when content shrinks/equal (breaks tailing rotated logs);
  ContentView re-renders content every frame; Pager `remove_page` leaves
  scroll-state keys pointing at the wrong page.
- **Charts/status/overlays:** BarChart drops last partial multi-row bar; Gauge
  ticks/min-max not reserved in auto-height; HeatMap legend `bar_width` can go
  negative; ImageView broad `except` + brittle duck-typing.
- **Styling:** `font-weight:normal`/`text-decoration:none` never turn attributes
  OFF; `theme.set_style` doesn't invalidate the resolver cache (stale styles);
  `_infer_class_from_element` has stale keys (`radiobutton`, `listview`->`list`)
  so ListView base styling isn't applied; no JSON theme loader despite CLAUDE.md
  mentioning JSON.
- **Config/API:** invalid `WIJJIT_LOG_LEVEL` silently -> INFO;
  `LOG_TO_CONSOLE`/`LOG_FORMAT` config keys not wired; CLI `--context`/`context=`
  silently ignored in `.py` app mode for `validate`/`tree`; `run` subparser
  defined but never dispatched.

### 2d - Demo-level polish (cosmetic / behavioral, 0.1.1)

Open items from the demo sweep; each is demo-scoped unless noted:
- `autocomplete.py` - original caret not erased on language toggle (cosmetic
  caret-erase on re-render).
- `grid` - rowspan/colspan cells have no border (DataGrid span rendering).
- `alert_dialog_demo.py` - color the error/success/info alert modals
  (severity-based modal theming).
- `content_view_demo.py` - scrolling main frame lets elements escape the top of
  the parent frame (clip-region clamp on scroll; see 2a frame overflow).
- `logview_demo.py` - streaming log should scroll to bottom (auto-scroll option);
  buttons run off the right edge.
- `status_indicator_demo.py` - support a blinking state / blink after a change.
- `textarea_demo.py` - need to show the end of long lines.
- `tree_demo.py` - right panel shrinks to content; "add test node" button no-ops;
  the `>` selector's background color is wrong (column ignores BG); expand-all /
  collapse-all don't take effect (see 2a reconciler/tree expand-all).
- `code_editor_demo.py` - Tab moves focus instead of indenting; add an option to
  capture Tab.
- `listview_demo.py` - "Add Fruit"/"Add Task" append correctly but the new row
  lands below the viewport (no auto-scroll to the new row).
- `context_menu_demo.py` - right-click context-menu path (Copy) needs a
  real-console repro (experimental real-terminal mouse).
- `executor_demo.py` - threaded-executor operation log needs a real wall-clock
  thread-completion check (the frame-stepped headless harness can't drive it).

---

## Completed (for reference)

Collapsed summaries of the work already landed. Full per-item detail lived in the
now-removed `CODE_REVIEW_0.1.0.md`, `API_AUDIT_0.1.0.md`, and root `issues.md`;
recover from git history if needed.

**Test/inspection harness** - headless `WijjitHarness` (scripted keys/mouse
through the real event loop; text/ANSI screen capture), `load_example_app`,
`app_from_template`, the `wijjit` devtools CLI (`validate`/`tree`/`render`/`run`),
the `pytest11` plugin (`harness`/`make_app` fixtures + markers), and
`tests/examples/` coverage of every driveable demo.

**Demo bug sweep (0.1.0)** - fixed crashes/hangs (executor_demo constructor args,
state_management_demo re-entrant `on_change`, form/error_handling reconciler key
collision, charts_demo Gauge auto-height, radio_demo directional-padding crash);
the cross-cutting scrolled-frame mouse hit-test offset; Windows mouse input
(prompt_toolkit `Win32Input` `;`-delimited events); focused-input swallowing
global key shortcuts; frame focus-border on all four sides; autocomplete
mouse-click select; frozen view-`data` snapshot log panels (dialog_showcase,
event_patterns); DataGrid selection-overlay right-border erase; spinner wide-char
label offset; plus per-demo layout/overflow fixes.

**Correctness code review (5 batches, merged)** - async dispatch (Theme B):
app-owned task set + `invoke_callback` everywhere, thread-safe State scheduling,
autocomplete cancel-prior-fetch, `navigate()` synchronous validation; CSS grouped
selectors + per-property cascade; terminal restore atexit safety net (embedding-
safe shutdown); hit-testing (Theme E) from real widths; CRITICALs #1/#4/#6/#7
(dispatch task, TextInput cursor clamp, `Tree.set_data` double-normalize,
`ColumnChart` render mutation); standalone Radio sibling deselect; Select scroll
overshoot; DataGrid Tab/Enter nav; Tree multi-select + bordered auto-scroll;
Pager/TabbedPanel wheel-vs-keyboard; silent-failure warnings (Theme C: unknown
tag/attr, CSS); `strip_ansi` widened to OSC/private-mode CSI; `_full_render` style
reset.

**API-consistency audit (3 batches, merged)** - one shared tag normalization
(`class`->`classes`, `tabindex`->`tab_index`) incl. layout containers; `border`
canonical + `border_style` alias + uniform `"single"` default + `has_border()`
helper (all six charts gained real borders); chart mode param `color`->
`color_mode`; grid `col_gap`->`column_gap`; `tab_index` on every focusable
constructor; `value`/`data`/`lines` properties (TextArea/CodeEditor, Table,
LogView) + ProgressBar `max`->`max_value`; boolean-input `on_change` unified
(firing `checked` on Checkbox/Radio, `on_action` on Toggle); six overlay/display
callbacks routed through `invoke_callback`; `MAX_PASTE_SIZE` cap on the async
paste path; `Config.from_object` dotted-path import; `get_running_loop()` sweep;
public-docstring corrections; dead-code removal (`Direction`,
`ViewRouter.register_view`, BrailleCanvas `render()`, etc.); additive symmetry
(`State.off_change`, `app.close_overlay`, decorator-form `app.on`); top-level
re-exports (completers, dialogs, `Modal`/`Notification` aliases).

**Type-check gate** - `mypy --strict src/` clean via targeted
`[[tool.mypy.overrides]]` blocks on the structural-gap modules (layout/engine,
core/renderer, core/wiring, ...); everything else fully strict.

**Documentation** - Sphinx build clean (0 warnings, down from ~1500); getting-
started + user-guide + api-reference + examples + developer-guide pages; hosting
decided as GitHub Pages with a `docs.yml` deploy workflow.

**Packaging** - version `0.1.0` (hatchling dynamic); `py.typed` +
`Typing :: Typed`; deterministic sdist `include`; SPDX license metadata; README
badges; `CONTRIBUTING.md`/`SECURITY.md`/`CODE_OF_CONDUCT.md`; PR #10 merged
(global-key routing, `release.yml`, install-smoke); `imageview_demo` asset
committed.
