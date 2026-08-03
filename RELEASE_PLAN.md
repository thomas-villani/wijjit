# Wijjit Release Runbook

This is the publish runbook. It is **per-release and reusable**: Part 1 is the
checklist to run for every version, and the one-time external setup it depends
on (Trusted Publishing, GitHub environments) is recorded as done in Part 3.
`roadmap.md` owns the backlog; this document owns the act of shipping.

**Shipped so far:**
- `0.1.0` - **published to PyPI 2026-07-31**, tagged `v0.1.0`, GitHub Release
  created from the CHANGELOG section.

**In preparation: `0.1.1`.** A correctness and tooling release - no breaking
changes. One additive public API (`State.mutate()` / `async_mutate()`), a
stricter `wijjit validate`, and a batch of styling, config, ANSI, focus and
harness fixes. Kept a *patch* bump rather than a minor: the project is 0.x, and
the docstrings for the new API already carry `.. versionadded:: 0.1.1`.

---

## Part 1 - Per-release checklist

Run this list top to bottom for each version. Status shown is for the release
currently in preparation (`0.1.1`).

### 1a - Gates (all must be green locally and in CI)
- [x] `.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/benchmarks`
      (3861 passed, 40 skipped as of 2026-08-03).
- [x] `ruff check src/ tests/`, `mypy src/`, `black --check src/ tests/`.
- [x] Sphinx builds clean with `-W` (`docs/`; same flag CI and Read the Docs use).
- [x] `uv build` + `uvx twine check dist/*`.
- [x] Every bundled example validates clean and renders headlessly (ratchet test
      in `tests/examples/`).

### 1b - Finalize metadata & version (at tag time)
- [x] `CHANGELOG.md`: rename `[Unreleased]` to `[X.Y.Z]` with the actual release
      date, leave an empty `[Unreleased]` stub above it, and add the two link
      refs at the bottom (`[Unreleased]` compare-from the new tag, `[X.Y.Z]`
      compare between tags). The `github-release` job extracts its notes by
      matching the literal `## [X.Y.Z]` heading, so the format is load-bearing.
- [x] Refresh the version/status claims that are written out in prose:
      `README.md` "Project Status" and `CLAUDE.md` "Status".
- [ ] Bump the version. `bump-my-version` (configured in `pyproject.toml`) owns
      this: `uv run bump-my-version bump patch` rewrites `wijjit.__version__`
      *and* the tool's own `current_version`, commits, and creates the `vX.Y.Z`
      tag in one step. Do not hand-edit either. `allow_dirty = false`, so commit
      the CHANGELOG and prose edits first.

### 1c - Docs hosting (Read the Docs)
- [x] Hosting moved from GitHub Pages to <https://wijjit.readthedocs.io> during
      0.1.1. `.readthedocs.yaml` builds with `fail_on_warning: true`;
      `.github/workflows/docs.yml` still builds the site as a PR check but no
      longer deploys.
- [ ] After tagging, activate the new version in the Read the Docs dashboard.
      **[user action]** Note: `v0.1.0` predates `.readthedocs.yaml` and cannot
      be built - `0.1.1` is the oldest buildable version.

### 1d - Build & TestPyPI dry-run (optional for a patch)
- [ ] Trigger `release.yml` via `workflow_dispatch` (`target=testpypi`), then
      install from TestPyPI into a clean venv and smoke-test (import,
      `wijjit --version`, `wijjit new` -> `validate --render` -> `render`,
      `llm-help`). A TestPyPI version cannot be re-uploaded, so a retry needs a
      local `.devN`.
      (Done for 0.1.0 on 2026-07-31, run `30652654671` - build 19s, publish 15s,
      both artifacts up, all smoke steps OK. The `release.yml` build job also
      install-smoke-tests the wheel in a clean venv before *any* publish, so
      this dry-run is belt-and-braces for a patch release.)

### 1e - Cut the release
- [ ] Push the bump commit to `main` **via a PR** - `main` rejects direct pushes.
- [ ] Push the tag: `git push origin vX.Y.Z`. That triggers `release.yml` ->
      build (+ install-smoke) -> publish to PyPI via OIDC -> GitHub Release from
      the CHANGELOG section.
- [ ] **Approve the deployment.** The `pypi` environment has required-reviewer
      protection, so the publish job waits for a human click. **[user action]**
- [ ] Post-release: clean-venv `pip install wijjit` -> import + headless
      hello-world; confirm the PyPI page renders the README and every project
      URL (including the Read the Docs link) resolves.

### Definition of Done
1. All gates in 1a green, on every CI matrix combo (3 OS x Py 3.11-3.13).
2. CHANGELOG section dated and complete; no work landed since the last tag is
   missing from it.
3. Docs build cleanly and the `Documentation` URL resolves to the new version.
4. `pip install wijjit==X.Y.Z` works on Linux/macOS/Windows, Py 3.11-3.13.
5. Tagged `vX.Y.Z`, GitHub Release published, roadmap reconciled against what
   actually shipped.

---

## Part 2 - Where the backlog lives

The detailed backlog lives in **`roadmap.md`**, which was made the single
post-0.1.0 backlog on 2026-07-15. Its `0.1.1` bucket is a *pool of candidates*,
not a release contract: `0.1.1` ships the 8 items checked off there, and the
rest carry forward. The framework correctness/architecture,
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

## Part 3 - One-time external setup (done; do not repeat)

Recorded here because Part 1 depends on it and it is invisible from the repo.

- [x] **PyPI + TestPyPI Trusted Publishers** - repo `thomas-villani/wijjit`,
      workflow `release.yml`, environments `pypi` / `testpypi`. Both were
      registered as *pending* publishers (neither project existed yet) and
      converted to project-scoped publishers on first successful upload. No API
      tokens are stored in the repository; publishing is OIDC.
- [x] **GitHub Actions environments `pypi` and `testpypi`.**
- [x] **Required-reviewer protection on `pypi`** (reviewer: `thomas-villani`),
      so a tag push cannot auto-publish without a human gate.
- [x] **Deployment branch policies** - `pypi` accepts the `v*` **tag** pattern
      only, so a real publish can only ever run from a release tag; a
      `workflow_dispatch` with `target=pypi` from a branch is refused by the
      environment. `testpypi` additionally allows the `main` **branch**, which
      is what makes the 1d dry-run dispatchable.
- [x] **Branch protection on `main`** - direct pushes are rejected, so the
      version-bump commit goes through a PR like any other change.
- [x] **Read the Docs project** connected to the repo and building from
      `.readthedocs.yaml`.

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
