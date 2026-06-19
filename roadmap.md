# Roadmap

Scoping decisions for upcoming Wijjit releases. This is a living document —
update as items move between buckets.

## 0.1.0 (current release target)

The framework is feature-complete for a credible first release: ~2702 tests
passing, ruff clean, `mypy --strict` clean, Sphinx docs build with zero
warnings. The remaining 0.1.0 work is a tight set of quality-of-life fixes
that would otherwise embarrass the first public release.

### Polish items

- [x] **Better template error handling** — initial render now propagates
  errors out of ``app.run()`` instead of being swallowed; the event loop's
  cleanup block restores the terminal before the traceback surfaces.
- [x] **Template without outer frame** — frameless templates (e.g. a bare
  ``{% textinput %}``) now route through ``render_with_layout`` and pick
  up the implicit-root-frame wrapping that already existed in the renderer.
- [x] **Scroll-follows-focus** — ``FocusManager`` walks the
  ``parent_frame`` chain on every focus change and asks scrollable
  ancestors to scroll the newly-focused element into view.
- [x] **ContentView width=fill** — verified during investigation as
  already implemented (``set_bounds`` + ``is_fill``).
- [x] **App title bar setting** — ``APP_TITLE`` config emits OSC 0 on
  startup; shells reset the title from their prompt hook on exit.
- [x] **Docs review + organize exports** — top-level ``wijjit`` now
  re-exports the full element surface (86 names); the elements submodule
  no longer has commented-out exports; the API reference covers the
  previously-missing Slider/Toggle/DataGrid/ImageView/Pager/StatusIndicator.

### Quality-of-life features folded in from the 0.1.x bucket

These started as 0.1.x items but were small and well-isolated enough to ship
in 0.1.0 (all test-backed via the headless harness):

- [x] **Right-align text and table columns** — per-column ``align`` key on
  ``Table``; ``align`` (+ ``width``/``height``) on the ``{% text %}`` tag.
- [x] **Autosizing TextArea** — ``autosize=True`` + optional ``max_height``;
  the element reports a content-driven intrinsic height and scrolls past it.
- [x] **Bind keys to focus** — ``app.bind_focus_key(key, element_id)`` plus
  ``get_element_by_id`` / ``focus_element_by_id``.
- [x] **Inner-text discipline** — ``{% textinput %}`` body becomes its initial
  value; ``{% button %}`` / ``{% menuitem %}`` accept a ``label=`` attribute.
- [x] **Define select / tree items via tags** — new ``{% selectitem %}`` and
  ``{% treeitem %}`` (nesting-aware) tags; menu items already supported this.
- [x] **Move local imports** (phase 1) — hoisted safe stdlib imports out of
  function bodies. Optional-dependency and circular-guard imports stay local.

### Phase 5 (after the items above)

Bump to ``0.1.0``, set up Trusted Publishing via GitHub Actions, ``uv build``,
``twine check``, publish to TestPyPI, then PyPI. See ``RELEASE_PLAN.md``.

## 0.1.x point releases

Real features, but not blockers — ship as additive minor versions after 0.1.0.

- [x] **Right-align text and table columns.** Shipped in 0.1.0.
- [x] **Autosizing TextArea** — shipped in 0.1.0 (``autosize`` + ``max_height``).
- [x] **Bind keys to focus** — shipped in 0.1.0 (``bind_focus_key``).
- [x] **Inner-text discipline** — shipped in 0.1.0 for the high-traffic tags
  (textinput/button/menuitem); a broader Frame/Markdown/Code audit can follow.
- [x] **Define select / tree items via tags** — shipped in 0.1.0
  (``selectitem``/``treeitem``). The ``{% for %}``/``{% if %}`` loop-over-items
  case (the two skipped menu-integration tests) still needs Jinja2 AST work.
- [~] **Move local imports** — phase 1 (stdlib hoist) done in 0.1.0. The
  remaining function-local ``wijjit`` imports are circular-import guards;
  untangling them is deferred.
- [ ] **Inline span element** for styling fragments of text. Deferred: the
  layout engine is block-based, so a true inline-flow ``{% span %}`` is a large
  change. For now, fragment styling is available via inline HTML inside a
  ``{% text html=true %}`` (e.g. ``<span class="text-danger">...</span>``).
- [ ] **Dynamic API for collection updates** — uniform programmatic way to
  add/remove/update items in ``ListView``, ``Menu``, ``Tree``, ``Select``.
  Deferred: the four elements diverge enough that a clean unified API needs
  its own design pass (property setters work today).
- [ ] **Full-screen a panel/element** — temporarily expand any container to
  fill the screen. Deferred: a naive bounds override breaks on stateful /
  scrolled / clipped elements; the correct version is overlay-based.
- [ ] **Selectable text** — enable text selection / copy in display elements.
  Deferred: display elements render through Rich (pre-baked ANSI, no per-char
  model); a real implementation is a substantial feature.
- [ ] **Wide-character (CJK / emoji) correctness** — near-term. The screen
  buffer is currently one cell per column with no continuation cell for
  width-2 glyphs, and several width calculations still use ``len()`` / raw
  string slicing instead of ``visible_length`` / ``clip_to_width``. The result
  is misaligned columns, border overflow, and cursor/click desync for CJK and
  emoji content. 0.1.0 documents this as a known single-width limitation (see
  ``ScreenBuffer`` docstring); the fix is a width-aware buffer (glyph cell +
  sentinel continuation cell) plus a sweep of the remaining ``len()`` width
  math. Tracked from the 0.1.0 code review (Theme A, CRITICALs #2/#3/#5).

## 0.2+ (new scope, post-0.1)

Clearly new functionality or substantial subsystems. Worth doing, not now.

### New components
- [ ] Navigation bar (tabs-for-views)
- [ ] Command palette (auto-populated from keybindings)
- [ ] BigText (ASCII-art for large letters)
- [ ] Shiny text (left-to-right per-letter color change)
- [ ] TagEditor (textarea that converts to tags)
- [ ] Tooltip / popover on hover or focus
- [ ] Prompt element (command-input bar)
- [ ] Shell-pipe passthrough for subshell / other apps

### Subsystems
- [ ] **Vim mode** for ``TextArea`` and ``CodeEditor``.
- [ ] **Spreadsheet formulas** in ``DataGrid`` (Excel-style ``=A1+B1``).
- [ ] **CSV / Excel / JSON data sources** for ``Table`` / ``DataGrid``.
- [ ] **Blueprints** — Flask-style modular view registration.
- [ ] **LLM-friendly mode** — a switch that exposes paths/macros to make TUIs
  driveable by an LLM more easily.
- [ ] **Virtual scrolling** for very large datasets.
- [ ] **Mocks and test runner for app developers** — public testing API
  layered on ``WijjitHarness``.

### Examples
- [ ] Per-component examples showing template tag *and* programmatic
  approaches.
- [ ] Integrated demo apps: text editor, file browser, todo list,
  configuration form, multi-view app.
