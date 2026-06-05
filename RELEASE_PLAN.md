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
- [x] **Scrolling / clip / overflow:** nested hstack/vstack/frame scroll
      glitches; parent-frame false scrollbars when content fits; scrollbar
      overlap.
  - [x] `frame_overflow_demo` modes looked identical: a text-only frame body
        wrapped regardless of `overflow_x`. The frame tag's `overflow_x` now
        defaults to None (body text wraps by default) but honors an explicit
        clip/visible/scroll/auto (keeps logical lines). CLIP and WRAP now
        render differently; unspecified frames are unchanged. Regression tests
        added. (VISIBLE still mirrors CLIP visually - deferred.)
  - [x] Scrolled-out children escaped the parent viewport: the renderer clipped
        each element to only its innermost frame, and the parent_frame chain
        broke at intermediate non-element frames. Now clips to the intersection
        of the innermost frame plus any *scrolling* ancestor, and links nested
        frames into the chain structurally. Regression tests added.
  - [x] Scrollbar-overlaps-child-borders: a width="fill" child of a scrollable
        parent was laid out at the full inner width, so its right border landed
        in the column the parent reserves for its scrollbar; the renderer's clip
        then cut the border off and the scrollbar overdrew it. The layout engine
        (`FrameNode.assign_bounds`) now reserves the scrollbar column - re-laying
        children one column narrower - once the frame actually needs to scroll
        (`_needs_scroll`), matching the clip and the frame's own scrollbar
        drawing. Non-scrolling frames are unchanged. grid_demo's golden was
        regenerated (its inner frame borders now render closed). Regression test:
        `tests/layout/test_frames.py::TestScrollbarChildBorderClearance`.
- [x] **Modal / focus / key routing:** harness-verified end-to-end via
      `tests/integration/test_modal_key_routing.py`. Confirmed invariants:
      (1) a trap-focus modal blocks app-level `on_key` handlers; (2) `Ctrl+Q`
      always quits, even with a TextInput focused or a modal open; (3) the
      key that opened a modal does NOT leak into the new modal's input; (4)
      Tab/Shift+Tab cycle focus between dialog buttons; (5) a freshly-opened
      dialog auto-focuses its first button so Enter activates it immediately.
      Found and fixed one real regression while writing (5): `_render` was
      bounds-filtering overlay focusables before the composite step assigned
      bounds to them, wiping the focus that `overlay.push()` had just set.
      Removed the over-strict filter (overlay focusables come from a
      structural walk of the modal hierarchy; they're real focusables
      regardless of this-frame bounds).
- [~] **Render order / dirty marking (deferred - architectural / not headless-
      testable):** progress bars "stop" spinners; spinner stop leaves `k...`
      artifacts; view-switch latency (`statusbar_demo`, `event_patterns_demo`).
      Root-caused (see `etc/issues.md`): the spinner `k...` residue is the cell
      buffer + diff renderer lacking double-width (wide-char) support - the clock
      uses emoji frames (1 codepoint, 2 display columns), so the real terminal's
      cursor drifts by one for everything after it on the row and the tail is
      left uncleared. The buffer itself is correct, so the harness (which reads
      the buffer, not the live terminal) cannot reproduce or regression-test it;
      a proper fix needs continuation cells + width-aware diff positioning across
      `paint_context`/`screen_buffer`/the diff renderer. The progress/spinner and
      view-switch items are wall-clock animation timing, which `harness.tick`
      bypasses (it advances frames directly). All three are real-terminal/timing
      issues the headless harness fundamentally can't drive; deferred rather than
      patched blind. (AGENTS.md already lists Unicode-on-Windows as a known
      limitation.)
- [x] **Display:** done.
  - [x] table scrollbar focus color: the table resolved non-existent
        `table.scrollbar` style classes, so the scrollbar was always unstyled
        and never changed on focus. Now resolves the shared `scrollbar.thumb`/
        `scrollbar.track` (+ `:focus`) classes frames use, so a focused table's
        scrollbar picks up the focus accent. Regression tests added.
  - [x] `table_demo` button placement: demo-config tightening - sized the table
        to its data (height 19) and the frame to its content (height 29) so the
        buttons sit directly below the table with no wasted space. Golden
        regenerated.
  - [x] table header-click sort: hit-testing assumed equal-width columns, but
        Rich sizes columns to content, so clicks mapped to the wrong column.
        Now captures the real column boundaries from the rendered top border
        each frame (`Table._get_column_at_x`); regression tests added.
  - [x] `Pager` page-5 "checkboxes show no text": symptom did not reproduce;
        the real defect was mixed text + block-element overlap on that page.
        The pager assigned child bounds without first running the constraint
        pass, so children defaulted to height 1 and collapsed. Fixed by calling
        `calculate_constraints()` before `assign_bounds()`; regression test
        added. (Residual: `_render_children` dual-coordinate flow noted in
        `etc/issues.md` for a future cleanup; no current failing case.)
- [x] **Layout polish:** all demos clean.
  - [x] `error_handling_demo` cleanup: outer frame was width=100 height=40
        with two width=48 inner columns + spacing=2, which overflowed the
        usable inner area; the resulting vertical scrollbar clipped the right
        column's right borders, the three simulated-error buttons overflowed
        their column ("Async Error" truncated), and the bottom action row +
        footer hint were hidden below the viewport. Restructured: outer
        106x40; left column 54 + right column 46 (fits within padding +
        spacing); shortened "Null Reference" to "Null Ref" + tightened button
        spacing; replaced the conditional 5-line bordered error frame with a
        single-line "[ERROR] ..." row so the layout stays stable when an
        error is shown; dropped the redundant
        `{% vstack spacing=0 %}<single line>{% endvstack %}` wrappers
        throughout; reduced "Error History" frame from height=22 to height=14.
        Regression tests: `tests/examples/test_error_handling_demo_layout.py`
        (5 assertions: no overflow scrollbar, all three sim-error buttons
        visible, bottom action row + footer visible, child-frame right
        borders intact, layout stable with an error message set).
  - [x] `complex_layout_demo` ("all fucked"): was a Renderer-only diagnostic
        using a non-existent `{% markdown %}` tag (it crashed on load). Rewrote
        it as a proper Wijjit app (valid `{% contentview content_type=
        "markdown" %}`, quit handling) and fixed two real layout-engine bugs it
        surfaced: (1) a `width=fill` TextArea never flagged dynamic sizing, so
        ElementNode used its large fixed intrinsic size as its preferred size,
        collapsing the parent frame and overflowing the layout - the tag now
        passes a `dynamic_sizing` flag (mirrors ContentView); (2)
        `border_style="none"` fell through to SINGLE in TextArea, drawing a
        border its layout box never reserved. Demo now renders cleanly and is
        harness-covered (removed from the example-render skip list). Regression
        tests: `tests/elements/test_textarea.py::TestTextAreaDynamicSizing` and
        `::TestTextAreaBorderNormalization`. (Note: `{% hstack %}` defaults to
        `width="auto"`; rows that should fill need explicit `width=fill` - this
        is intended framework behavior, applied in the demo.)
  - [x] Suspected frame title-border 1-column discrepancy: investigated, not a
        bug (borders align at every width; regression test added).

**Acceptance:** all `examples/` run without crashes; `etc/issues.md` open items
closed or explicitly deferred with rationale; harness regression tests added.

## Phase 3 - Type-check gate green (-> contributes to 0.1.0rc1)

- [x] Triaged: 496 errors across 50 files; top rules type-arg (162),
      no-untyped-def (60), arg-type (56), assignment (50), attr-defined (40);
      top files engine.py (103), renderer.py (50), wiring.py (37), frames.py
      (25). Categories cluster on structural Element-base attr access and
      Literal-string flow through template tags.
- [x] Policy chosen: pragmatic split. Public API surface (`wijjit.__init__`),
      `core/` (except renderer/wiring/app), `terminal/`, `tags/`, `styling/`
      (except css_parser), `inline/`, `autocomplete/`, `rendering/`, and the
      smaller elements/layout files are fully strict. The structural-gap files
      keep targeted `[[tool.mypy.overrides]]` blocks in `pyproject.toml` with
      inline comments and `RELEASE_PLAN`-tracked deferred work: layout/engine
      (Literal-through-tag-stack), core/renderer (Element-base attr access),
      core/wiring (lambda-in-closure factories), layout/frames (BorderStyle |
      None indexing), elements/input/datagrid (property setters + pandas),
      core/app (handler-signature variance), elements/display/tabbed_panel,
      elements/input/code_editor (pygments untyped + lots of property setters),
      elements/display/tree, elements/display/image (Pillow None checks),
      testing/harness (test-fixture-shaped runtime), elements/display/table,
      elements/display/pager, styling/css_parser (tinycss2 untyped), and
      elements/menu. Each block disables only the categories that would need
      structural refactoring; everything else stays strict.
- [x] Made CI `lint` job pass: ruff clean + mypy --strict clean.

**Acceptance:** `mypy --strict src/` passes; CI lint job green. **Met.**

> Side effect during the sweep: `Notification.handle_mouse` was awaiting the
> coroutine returned by the action-button's `handle_mouse` incorrectly (the
> coroutine was returned without `await`, so clicks on a notification's
> action button silently fell through to the dismiss path). Fixed inline.

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
