# Wijjit Release Plan -> PyPI 0.1.0

**Goal:** Ship a polished, correct `0.1.0` to PyPI. Strategy chosen:
**full polish** - clear the outstanding demo bugs, get the type-check gate
green, ship docs, then publish.

**Current state (2026-06-30):**
- Tests: green (full suite + `mypy --strict` confirmed by maintainer this
  session). Ruff: clean. `uv build` produces both sdist and wheel cleanly.
  CI lint job is **green**.
- CI: 3 OS x Py 3.11-3.13 + lint + coverage, all green.
- Version: **`0.1.0`** (single source: `wijjit.__version__`, hatchling dynamic).
  Bumped from `0.1.0a1`.
- Sphinx docs build clean (0 warnings); docs **hosting: GitHub Pages**
  (not Read the Docs); the `Documentation` project URL points at the Pages site.
- **Phases 1-4 complete.** Phase 5 is **substantially done** (PR #10 merged;
  metadata, community files, docs workflow, release-pipeline hardening, and the
  Flask-style `render_template_string`/`render_template` API all landed). The
  remaining work is the external, user-gated publish steps (Trusted Publishing
  setup, enable Pages, TestPyPI dry-run, tag) plus the final CHANGELOG date.

> RESOLVED: PR #10 is **merged** (commit `6116a35`); the global-key-routing fix,
> `release.yml`, and the deterministic-sdist `include` list are on `main`. The
> stray `.venv-wsl/` that broke `uv build --sdist` is gone, and the explicit
> sdist `include` list means the build no longer walks stray local directories.
> `uv build` succeeds on `main`.

Versioning toward release: `0.1.0a1` -> **`0.1.0`** (done). Earlier intermediate
`b1`/`rc1` tags were skipped; the alpha went straight to `0.1.0`.

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
      patched blind. (CLAUDE.md already lists Unicode-on-Windows as a known
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

- [x] Sphinx build is clean: `sphinx-build -b html docs/source docs/build/html`
      emits 0 warnings and 0 errors (down from ~1500 lines at session start).
- [x] Fixed the large volume of Sphinx warnings. Triaged by root cause:
  - **Duplicate object descriptions (~1000 of the original ~1500)** – came
        from `[[tool.mypy.overrides]]`-style structural mismatches between two
        sources: the autosummary-generated stub pages under `docs/source/api/`
        and the `Module documentation` `automodule` blocks at the bottom of
        every `docs/source/api_reference/*.rst` file. The blocks inherited
        `:members: True` from `autodoc_default_options` despite their
        `:noindex:` annotation, which Sphinx 8 does not propagate to members.
        Resolved by deleting all bottom `automodule` blocks (autosummary stubs
        are now the sole canonical entry per class).
  - **Per-member duplicate descriptions** – the Napoleon `Attributes` NumPy
        section was rendering as separate `.. attribute::` directives that
        collided with `@property` declarations on the same class. Switched
        `napoleon_use_ivar = True` so `Attributes` render as inline `:ivar:`
        fields instead of separate object descriptions.
  - **`__init__` duplicates (~30)** – `napoleon_include_init_with_doc = True`
        folded `__init__` Parameters into the class doc, and the autosummary
        stub template additionally emitted `.. automethod:: __init__`. Two
        descriptions for the same FQN. Removed `:special-members: __init__`
        from `autodoc_default_options` and set
        `napoleon_include_init_with_doc = False`; the stub template's
        explicit `automethod` is now the sole `__init__` source.
  - **Docstring RST formatting (~133 warnings)** – `Examples:` /
        `Syntax:` introducing indented code without `::` made docutils
        interpret the next block as a definition list or unmatched block
        quote. Mechanical sweep converted `<intro>:\n    code` to
        `<intro>::\n\n    code` in all docstrings (script + per-file
        cleanup); ~60 sites fixed.
  - **`Theme Styles` nested NumPy sections (~30 sites)** – the per-element
        `render_to` docstrings had `Theme Styles\n------------` inside the
        Notes section, which docutils flagged as a CRITICAL `Unexpected
        section title`. Converted to plain `Theme styles:` intro text.
  - **`'name:variant'` style-class names** – single-quoted CSS-like names
        with colons (`'checkbox:checked'`) confused docutils as malformed
        string literals. Mechanical sweep wrapped them in double-backticks
        (`` `checkbox:checked` ``) across 32 files.
  - **Wrong autosummary paths** – `wijjit.elements.modal.Modal`,
        `wijjit.tags.dialogs.InputDialogExtension`,
        `wijjit.tags.display.MarkdownExtension`/`CodeBlockExtension`,
        `wijjit.rendering.ansi_adapter.ANSIAdapter` did not exist in the
        current code. Fixed to actual exported names
        (`ModalElement`/`AlertDialog`/`ConfirmDialog`/`TextInputDialog`;
        `TextInputDialogExtension`; `ContentViewExtension` + the
        previously-missing display widgets; `ansi_string_to_cells` +
        `cells_to_ansi`).
  - **`literalinclude` path errors (7)** – `components.rst` used `../../`
        but with the source dir at `docs/source/` the relative resolution
        starts there, not at the document; corrected to `../../../`.
  - **Remaining one-offs (~10)** – `.. deprecated::` directive missing
        version arg (chart_utils, frames), `**attrs` parsed as inline
        strong (style.py), `*.pyc` parsed as emphasis (helpers.py),
        `Threading model:` definition-list/bullet collision (events.py),
        `WIJJIT_` trailing-underscore parsed as a ref target (app.py),
        unindented literal block body in `ListViewExtension` (tags),
        broken `:ref:` to a section that doesn't exist (modal_dialogs).
- [x] Phase-1 priority pages exist and build cleanly: `getting_started/`
      (installation, quickstart, tutorial), `user_guide/` (12 pages incl.
      core_concepts, components, layout_system, modal_dialogs, etc.),
      `api_reference/` (10 modules via autosummary + per-class stubs),
      `examples/` (gallery + cookbook), `developer_guide/` (architecture,
      contributing, testing).
- [x] Docs hosting decided: **GitHub Pages** (not Read the Docs). The Sphinx
      site will be built and deployed by a `docs.yml` Actions workflow; the
      `Documentation` project URL moves to the Pages URL. See Phase 5c.
- [ ] Per-component example pages (template tag + programmatic) per `etc/todo.md`
      (deferred to 0.1.1; not a release blocker).

**Acceptance:** `sphinx-build -b html docs/source docs/build/html` succeeds
with 0 errors and 0 warnings; the getting-started path lets a new user build
an app in <15 min. **Met for the build-quality gate.**

> Side effect during the sweep: the Sphinx config (`docs/source/conf.py`) was
> tuned: `napoleon_use_ivar = True`, `napoleon_include_init_with_doc = False`,
> `:special-members: __init__` removed from `autodoc_default_options`. These
> are the load-bearing changes that eliminate the structural duplicate-object
> warnings without losing API documentation coverage.

## Phase 5 - Packaging, docs hosting & publish (-> 0.1.0)

Done items already verified this session (no action needed): author email is
correct (`thomas.villani@gmail.com` = publishing identity); `.gitattributes`,
`src/wijjit/py.typed`, and the `Typing :: Typed` classifier are in place; the
wheel ships `py.typed`, leaks no tests, and `twine check` passes; dependency
lower bounds are pinned; `pyperclip` already degrades gracefully to an internal
clipboard when no system clipboard backend is present.

### 5a - Merge the staged work (PREREQUISITE - do first)

- [x] Merge **PR #10** (commit `6116a35`). `uv build` succeeds on `main`.

### 5b - Finalize metadata & version (on `main`, post-merge)

- [x] Bump `src/wijjit/__init__.py` `__version__` `0.1.0a1` -> `0.1.0`.
- [ ] `CHANGELOG.md`: set the `[0.1.0]` date to the actual release date (it is
      currently `2026-06-28`); keep an empty `[Unreleased]` stub. **Finalize at
      tag time.**
- [x] `README.md`: removed the "currently in pre-release / `pip install --pre`"
      note and other pre-release language.
- [x] Modernized license metadata: `license = "MIT"` (SPDX) +
      `license-files = ["LICENSE"]`.
- [x] Committed `docs/NEW-ELEMENTS.md`.

### 5c - Docs hosting: GitHub Pages (replaces Read the Docs)

- [x] Pointed the `pyproject.toml` `Documentation` URL at GitHub Pages
      (`https://thomas-villani.github.io/wijjit/`); README links updated.
- [x] Added `.github/workflows/docs.yml`: Sphinx build of `docs/source` ->
      `actions/upload-pages-artifact` -> `actions/deploy-pages`; trigger on push
      to `main` (paths: `docs/**`, `src/wijjit/**`) + `workflow_dispatch`;
      `permissions: pages: write, id-token: write`.
- [ ] Enable Pages in repo settings (Source: GitHub Actions). **[user action]**
- [ ] Verify the published site builds and loads before the URL ships in PyPI
      metadata.

### 5d - Release pipeline hardening

- [x] Added an install-smoke step to `release.yml`'s `build` job: in a clean
      venv, `pip install dist/*.whl` then `import wijjit; print(__version__)`
      so a broken artifact fails the build before any publish.
- [ ] (Optional) Add required-reviewer protection to the `pypi` GitHub
      environment so a tag push can't auto-publish without a human gate.

### 5e - Community health & polish (all in scope per release decision)

- [x] README badges: PyPI version, supported Python versions, CI status,
      license, docs.
- [x] Added `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- [ ] Document the `pyperclip` Linux behavior (system clipboard needs
      xclip/xsel; otherwise falls back to an internal clipboard) in README/docs.

### 5f - Trusted Publishing external setup (one-time) **[user actions]**

- [ ] PyPI: register a pending Trusted Publisher - repo `thomas-villani/wijjit`,
      workflow `release.yml`, environment `pypi`.
- [ ] TestPyPI: same, environment `testpypi`.
- [ ] Create GitHub Actions environments named `pypi` and `testpypi`.

### 5g - Build & TestPyPI dry-run

- [ ] Local: `uv build` + `uvx twine check dist/*`.
- [ ] Trigger `release.yml` via `workflow_dispatch` (`target=testpypi`); then in
      a clean venv install from TestPyPI and smoke-test (import + a headless
      example). Note: a TestPyPI version cannot be re-uploaded - bump a local
      `.devN` if a retry is needed.

### 5h - Cut the release

- [ ] Commit the version bump on `main`, `git tag v0.1.0`, `git push origin
      v0.1.0`. The tag triggers `release.yml` -> build (+ install-smoke) ->
      publish to PyPI via OIDC -> GitHub Release from the CHANGELOG section.
- [ ] Post-release: clean-venv `pip install wijjit` -> import + headless
      hello-world; confirm the PyPI page renders the README and all project
      URLs (incl. the new Pages docs URL) resolve.

### 5i - Repo hygiene (before tagging)

- [x] Triaged untracked root WIP: scratch `.md` plans removed; `test-image.png`
      downscaled to 256x256 (~79 KB) and committed under `examples/assets/` with
      the `imageview_demo` wired to it via `__file__`-relative path (commit
      `6dea06a`). `docs/NEW-ELEMENTS.md` kept (committed in 5b).
- [ ] Delete the last scratch file `todo-release.md` (0.1.1 example ideas)
      before tagging. **[user will remove]**

**Acceptance:** `pip install wijjit` installs `0.1.0` and a hello-world app runs
on a clean machine across the supported Python/OS matrix; the PyPI page renders
the README and every project URL (including the GitHub Pages docs) resolves.

---

## Definition of Done for 0.1.0

1. PR #10 merged; all examples run without crashes; open `etc/issues.md` bugs
   closed or explicitly deferred to 0.1.1.
2. CI fully green (tests + ruff + mypy) on all matrix combos.
3. Docs build cleanly, deploy to **GitHub Pages**, and cover the
   getting-started path + API reference; the `Documentation` URL resolves.
4. `pip install wijjit==0.1.0` works on Linux/macOS/Windows, Py 3.11-3.13.
5. Tagged `v0.1.0`, CHANGELOG finalized, GitHub Release published; community
   health files + README badges in place.
