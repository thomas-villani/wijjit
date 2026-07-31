# Wijjit Release Plan -> PyPI 0.1.0

This is the single consolidated release document for `0.1.0`. It merges the
former `RELEASE_PLAN.md`, `CODE_REVIEW_0.1.0.md`, `API_AUDIT_0.1.0.md`, and the
root `issues.md`. Everything already completed has been collapsed into the
**Completed** summary at the bottom; the body tracks only what remains.

**Goal:** Ship a polished, correct `0.1.0` to PyPI.

**Current state:**
- Version: **`0.1.0`** (single source: `wijjit.__version__`, hatchling dynamic).
- Tests green (~3700 pass, excl. benchmarks); `ruff check src/` clean;
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
      `2026-07-23`, the pre-tag audit date); keep an empty `[Unreleased]` stub.

### 1b - Docs hosting (GitHub Pages)
- [x] Enable Pages in repo settings (Source: GitHub Actions). **[user action]**
- [x] Verify the published site builds and loads before the URL ships in PyPI
      metadata.
      (The `.github/workflows/docs.yml` build->upload->deploy workflow is in
      place and the `Documentation` project URL already points at the Pages site.)

### 1c - Release pipeline hardening
- [ ] (Optional) Add required-reviewer protection to the `pypi` GitHub
      environment so a tag push can't auto-publish without a human gate.
      (The `release.yml` build job already install-smoke-tests the wheel in a
      clean venv before any publish.)

### 1d - Community health & polish
- [x] Document the `pyperclip` Linux behavior (system clipboard needs xclip/xsel;
      otherwise falls back to an internal clipboard) in README/docs.

### 1e - Trusted Publishing external setup (one-time) **[user actions]**
- [x] PyPI: register a pending Trusted Publisher - repo `thomas-villani/wijjit`,
      workflow `release.yml`, environment `pypi`.
- [ ] TestPyPI: same, environment `testpypi`.
- [x] Create GitHub Actions environments named `pypi` and `testpypi`.

### 1f - Build & TestPyPI dry-run
- [x] Local: `uv build` + `uvx twine check dist/*`.
- [ ] Trigger `release.yml` via `workflow_dispatch` (`target=testpypi`); then in a
      clean venv install from TestPyPI and smoke-test (import + a headless
      example). Note: a TestPyPI version cannot be re-uploaded - bump a local
      `.devN` if a retry is needed.

### 1g - Repo hygiene (before tagging)
- [x] Delete the scratch file `todo-release.md` (0.1.1 example ideas) before
      tagging.

### 1h - Cut the release
- [ ] Commit the version bump on `main`, `git tag v0.1.0`, `git push origin
      v0.1.0`. The tag triggers `release.yml` -> build (+ install-smoke) ->
      publish to PyPI via OIDC -> GitHub Release from the CHANGELOG section.
      Note: `wijjit.__version__` is *already* `0.1.0`, so this first release is
      tagged by hand. `bump-my-version` (configured in `pyproject.toml`) owns
      subsequent bumps - `uv run bump-my-version bump patch` rewrites
      `__init__.py`, commits, and creates the `vX.Y.Z` tag in one step.
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

The detailed 0.1.1 backlog now lives in **`roadmap.md`**, which was made the
single post-0.1.0 backlog on 2026-07-15. The framework correctness/architecture,
internal-dedup, MEDIUM/LOW-correctness, and demo-polish items that used to be
enumerated here (Parts 2a-2d) were migrated there, deduplicated against the
existing roadmap buckets and the still-open framework-review findings. See in
`roadmap.md`:

- **0.1.1 -> Rendering / layout architecture** - dual frame-render path,
  horizontal child-frame scroll (Group C), frame-overflow clip clamping
  (Group D), per-keystroke full re-render (review 2.5), CodeEditor soft-wrap.
- **0.1.1 -> Ephemeral-state preservation contract** - Tree expand-all (Group E),
  keyless-element ephemeral loss + positional frame IDs, declarative ephemeral
  props (review 2.6).
- **0.1.1 -> Input & terminal handling** - Esc/Alt timeout + Alt-digit
  reachability, SIGWINCH resize, ANSI-adapter pattern, DCS, mixed `%`+`fill`,
  legacy mouse mode (review 2.12 tail).
- **0.1.1 -> Framework correctness / cleanup** - internal dedup and the
  MEDIUM/LOW correctness list (former Parts 2b/2c).
- **0.1.1 -> Cosmetic / theming, Viewport / scrolling UX, Platform-specific** -
  the demo-level polish (former Part 2d).
- **0.1.x / 0.2+** - wide-char direct-paint sweep, plugin seam (review 3.5),
  tagline repositioning (review 3.6), and the larger new-scope work.

This document is now the release *runbook* (Part 1); `roadmap.md` owns the
backlog.

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

**Input: idle CPU burn + silent key drops** (`terminal/input.py`) - two coupled
bugs the test suite could not see, because both need a *timing* observation
rather than a return-value assertion. (1) `prompt_toolkit`'s `read_keys()` never
blocks, so the reader thread polled it flat out: measured **98.6% of one core and
~61k calls/second on a completely idle app**. It now waits on the shutdown event
between empty polls (`IDLE_POLL_INTERVAL`), which also keeps `close()` instant.
(2) A `read_keys()` batch can carry several presses, and only `keys[0]` was ever
used - the rest were dropped in four separate places (the main take, the Alt+key
branch, the Escape lookahead, and both mouse-continuation loops). Leftovers are
now held in a `pending` buffer and replayed, in both `read_input` and
`read_input_async`; the old special-cased "Alt+key in the same read" branch is
gone, subsumed by the lookahead. **The two bugs masked each other:** polling that
fast made multi-key batches rare, so throttling the poll *without* the requeue
would have converted a CPU problem into visible input loss. Regression-tested in
`tests/terminal/test_input.py` (`TestInputBatchRequeue`, `TestInputIdlePolling`);
6 of the 8 new tests fail against the pre-fix code, and the suite for that file
went from 73s to 2.3s once the spin stopped starving the GIL.

**Menu template skips un-skipped** - the two `pytest.mark.skip`s in
`tests/integration/test_menu_integration.py` claimed dynamic (`{% for %}`) and
conditional (`{% if %}`) menu items were unsupported. They were supported; the
tests referenced bare `actions` / `is_admin` while the helper passes context as
`{"state": app.state}`, so both were Jinja `Undefined` - which iterates as empty
and tests as falsey, silently. Templates corrected to `state.actions` /
`state.is_admin` and both tests re-enabled. Motivates the `StrictUndefined` item
in Part 2a.

**Mouse-callback chaining + left-button discipline** - every element that
overrode `handle_mouse` consumed clicks without delegating to
`Element.handle_mouse`, so `on_double_click` / `on_context_menu` were silently
dead. Fixed across all inputs (Button, Checkbox/Group, Radio/Group, Select,
Slider, Toggle, TextInput/TextArea, DataGrid) and all display elements (Tree,
ListView, LogView, ContentView, BarChart, Link, Pager, TabbedPanel). `Table`
already delegated, but only on a fallback path its row-hit branch made
unreachable. Related left-button fixes: a right-click used to activate a
`Button`, and a right-click on a `Table` header fired `on_header_click` **and
sorted the column**; row-hit handling also swallowed right-clicks so context
menus never opened on a table row. `DataGrid.get_data_as_dataframe()` no longer
raises on ragged rows (short rows pad, overlong rows truncate **and log a
warning** rather than silently dropping cells). Note: the template-declared
`{% contextmenu %}` path is routed by `mouse_router` before element dispatch and
was never affected. Regression-tested in `tests/elements/test_mouse_callbacks.py`.

**Demo bug sweep (0.1.0)** - fixed crashes/hangs (executor_demo constructor args,
state_management_demo re-entrant `on_change`, form/error_handling reconciler key
collision, charts_demo Gauge auto-height, radio_demo directional-padding crash);
the cross-cutting scrolled-frame mouse hit-test offset; Windows mouse input
(prompt_toolkit `Win32Input` `;`-delimited events); focused-input swallowing
global key shortcuts; frame focus-border on all four sides; autocomplete
mouse-click select; frozen view-`data` snapshot log panels (dialog_showcase,
event_patterns); DataGrid selection-overlay right-border erase; spinner wide-char
label offset; LogView auto-scroll-to-bottom across re-renders (the reconciler
captured the pre-append scroll position and `restore_ephemeral_state` clobbered
`set_lines`' auto-scroll; it now re-asserts the bottom when auto-scroll is on and
the user hasn't scrolled up); plus per-demo layout/overflow fixes.

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
