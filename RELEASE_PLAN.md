# Wijjit Release Plan -> PyPI 0.1.0

**Goal:** Ship a polished, correct `0.1.0` to PyPI. Strategy chosen:
**full polish** - clear the outstanding demo bugs, get the type-check gate
green, ship docs, then publish.

**Current state (2026-05-26):**
- Tests: ~2480 passing, 15 skipped. Ruff: clean. Build: works (`uv build`).
- Version: `0.1.0a1` (single source: `wijjit.__version__`, hatchling dynamic).
- CI exists (3 OS x Py 3.11-3.13 + lint + coverage) but the **lint job fails**
  on `mypy --strict` (~480 errors).
- Packaging metadata fixed (URLs, version, README, CHANGELOG, public API).

Versioning toward release: `0.1.0a1` (now) -> `0.1.0b1` (after Phase 2) ->
`0.1.0rc1` (after Phases 3-4) -> `0.1.0` (Phase 5).

---

## Phase 1 - Test/inspection harness (do first; unblocks everything)

The biggest dev-velocity gap is the inability to drive a running app and
"see" the output. This blocks fixing the visual demo bugs efficiently.

- [x] Headless driver: `ScriptedInputHandler` feeds queued `Key`/`MouseEvent`
      through the real `EventLoop._process_frame_async()` dispatch; fixed
      terminal size via patched `shutil.get_terminal_size`.
- [x] Buffer-to-text/ANSI snapshot: `WijjitHarness.screen()` (plain text) and
      `.screen_ansi()` (styled), read from the renderer's displayed buffer.
- [x] Public test API: `wijjit.testing.WijjitHarness(app, size=(80,24))` with
      `.press`/`.type`/`.key`/`.click`/`.scroll`/`.tick`/`.screen`/
      `.assert_text`/`.find_text` (+ `tests/testing/test_harness.py`).
- [x] Example loader: `wijjit.testing.load_example_app(path)` execs a demo with
      `__name__ == "__main__"` (and neutralized `sys.argv`) while patching
      `Wijjit.run` to capture the instance instead of blocking. Handles both
      module-level and `main()`-local apps. `discover_examples()` enumerates them.
- [x] Pytest coverage for every example: `tests/examples/test_examples_render.py`
      loads + renders all 62 driveable demos (non-blank smoke assert) plus a
      curated set of initial-screen text goldens (regenerate with
      `pytest --golden-update`). 8 non-harness demos skipped with reasons; known
      bugs marked `xfail`.
- [x] Headless CLI: `python -m wijjit.testing <example.py> [--size WxH]
      [--keys "tab,type:admin,enter,click:10,6,tick:3"] [--ansi]` loads, drives,
      and prints the screen for quick agent-driven iteration.

**Acceptance:** an agent can script keys/clicks against any example and assert
on a text snapshot of the screen, with no real TTY. **Met.**

> The sweep surfaced two issues not previously listed, both now resolved:
> `charts_demo` rendered a blank initial screen (fixed - see Phase 2 crashers),
> and a suspected 1-column title-border width discrepancy that turned out **not**
> to be a bug - the borders align at every width in both render paths; the
> apparent mismatch was trailing-whitespace differences in piped output. Locked
> in with `tests/layout/test_frames.py::TestFrameBorderAlignment`.

## Phase 2 - Fix outstanding demo bugs (-> 0.1.0b1)

Grouped by likely root cause (from `etc/issues.md` / `etc/issues-sorted.md`).
Use the Phase 1 harness to reproduce and regression-test each.

- [x] **Functional crashes/hangs (highest priority):**
  - [x] `executor_demo` crashes: called non-existent `app.configure(...)` with
        wrong key names. Fixed the demo to pass `run_sync_in_executor` /
        `executor_max_workers` via the constructor (the executor is built in
        `__init__`).
  - [x] `state_management_demo` hung on increment: a global `on_change` callback
        wrote `change_log` back into state, re-triggering itself unbounded.
        Fixed the demo (ignore its own `change_log` writes) and hardened `State`
        with a re-entrant-notification depth guard so this footgun logs an error
        instead of crashing.
  - [x] `form_demo` / `error_handling_demo` "[Missing element: TextElement]":
        root cause was a reconciler key collision. Text nodes use positional
        `text_N` keys; when conditional content appears, a key created in one
        subtree was deleted by a stale old-vnode in the next subtree during the
        same pass. Fixed by tracking keys created in the current pass and
        refusing to evict them on delete.
  - [x] `charts_demo` blank render (found via the harness sweep): `Gauge`
        auto-height returned the string `"auto"`, so VStack constraint
        summation hit `int += str`. `Gauge` now auto-calculates an integer
        height for any non-int spec.
- [ ] **Scrolling / clip / overflow:** nested hstack/vstack/frame scroll
      glitches; parent-frame false scrollbars when content fits; scrollbar
      overlap; `frame_overflow_demo` modes look identical.
- [ ] **Modal / focus / key routing:** modals should block app hotkeys
      (except quit); avoid double-key-to-focus; swallow keys that opened a
      dialog. (Many already fixed - re-verify with the harness.)
- [ ] **Render order / dirty marking:** progress bars stop spinners;
      spinner stop leaves `k...` artifacts (dirty-mark on shrink);
      view-switch latency (`statusbar_demo`, `event_patterns_demo`).
- [ ] **Display:** table header-click sort; `table_demo` button placement;
      scrollbar focus color; `Pager` page-5 checkboxes show no text.
- [ ] **Layout polish:** `complex_layout_demo`, `error_handling_demo` cleanup.
  - [x] Suspected frame title-border 1-column discrepancy: investigated, not a
        bug (borders align at every width; regression test added).

**Acceptance:** all `examples/` run without crashes; `etc/issues.md` open items
closed or explicitly deferred with rationale; harness regression tests added.

## Phase 3 - Type-check gate green (-> contributes to 0.1.0rc1)

- [ ] Triage the ~480 `mypy --strict` errors by module.
- [ ] Decide policy: fully fix, or relax strictness pragmatically (e.g. start
      strict on `core/` + public API, looser elsewhere via per-module
      `[[tool.mypy.overrides]]`), then tighten over time.
- [ ] Make CI `lint` job pass (ruff already clean + mypy green).

**Acceptance:** `mypy src/` passes under the agreed config; CI is green.

## Phase 4 - Documentation (-> 0.1.0rc1)

- [ ] Build Sphinx docs per `docs/DOCUMENTATION_PLAN.md` (deps already in the
      `dev` extra: sphinx, myst-parser, copybutton, rtd-theme, tabs).
- [ ] Fix the large volume of Sphinx warnings (`docs/sphinx-warnings.txt`).
- [ ] Phase-1 priority pages: install, quickstart, tutorial, core concepts,
      components, plus autodoc API reference (NumPy docstrings already present).
- [ ] Decide on Read the Docs hosting (the project URL already points there).
- [ ] Per-component example pages (template tag + programmatic) per `etc/todo.md`.

**Acceptance:** `make html` builds with no errors and minimal warnings; the
getting-started path lets a new user build an app in <15 min.

## Phase 5 - Packaging & publish (-> 0.1.0)

- [ ] Verify/confirm author email in `pyproject.toml`
      (`thomas.villani@gmail.com` vs the account `tomrhobus@gmail.com`).
- [ ] Add `.gitattributes` to normalize line endings (repo currently warns
      LF->CRLF on every touched file on Windows).
- [ ] Pin a minimal supported dependency set; smoke-test a clean install in a
      fresh venv on Linux/macOS/Windows (CI matrix already covers test).
- [ ] Note `pyperclip`'s Linux clipboard requirement (xclip/xsel) in docs, or
      degrade gracefully when unavailable.
- [ ] Add release tooling: `twine` (not currently installed) OR use
      `uv publish`. Prefer **PyPI Trusted Publishing** (OIDC from GitHub
      Actions) to avoid storing tokens.
- [ ] `uv build` + `twine check dist/*` (metadata + long-description render).
- [ ] Publish to **TestPyPI**; install from TestPyPI in a clean venv and run a
      smoke test (import + run a headless example).
- [ ] Bump `__version__` to `0.1.0`; finalize `CHANGELOG.md` (move Unreleased
      -> `[0.1.0]` with date); tag `v0.1.0`.
- [ ] Publish to PyPI (ideally via a tag-triggered GitHub Actions release job).
- [ ] Post-release: create a GitHub Release with notes; verify
      `pip install wijjit` works.

**Acceptance:** `pip install wijjit` installs `0.1.0` and a hello-world app runs
on a clean machine across the supported Python/OS matrix.

---

## Cross-cutting / housekeeping

- [ ] Repo hygiene: stray debug `*.log` files at root are gitignored - leave
      or delete. Untracked logo PNGs and scratch `.md` plans: decide what to
      commit vs move under `etc/`/`plan/` (already gitignored).
- [ ] Confirm `@AGENTS.md` import in `CLAUDE.md` loads as expected next session.
- [ ] Consider a `py.typed` marker (the package advertises `Typing :: Typed`).
- [ ] Keep `AGENTS.md` as the single source of project guidance.

## Definition of Done for 0.1.0

1. All examples run without crashes; open `etc/issues.md` bugs closed/deferred.
2. CI fully green (tests + ruff + mypy) on all matrix combos.
3. Docs build cleanly and cover the getting-started path + API reference.
4. `pip install wijjit==0.1.0` works on Linux/macOS/Windows, Py 3.11-3.13.
5. Tagged `v0.1.0`, CHANGELOG finalized, GitHub Release published.
