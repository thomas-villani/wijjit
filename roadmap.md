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

## 0.1.1 — deferred from the 0.1.0 example pass

Items surfaced by the manual ``examples/`` walkthrough (06-29) and the earlier
demo-bug triage (groups A-H). The cross-cutting / crash items were fixed in
0.1.0; everything below is cosmetic, demo-level, platform-specific, or an
architecture-level refactor not worth the risk days before tagging. Root causes
are in ``RELEASE_PLAN.md`` (Part 2). Pull individual items forward as use cases demand.

**Already resolved in 0.1.0** (for reference): mouse hit-testing offset on
scrolled frames; radio_demo layout crash (directional padding on
VStack/HStack/Grid); theme_config_demo quit-key hang; inline_progress double
percentage; **focus-border left/right** (frame-border pass made focus-aware);
**autocomplete mouse-select** (clicking a suggestion now commits it - the popup
gained an ``on_select`` callback wired to the input's apply handler; Enter/Tab
already worked); **dialog_showcase / event_patterns log panels** (rewrote the
demos to keep the rendered log text in ``state`` instead of a precomputed view
``data`` value - see the frozen-``data`` note below); **select_demo "Submit"**
(was the scrolled-frame click offset, fixed by the mouse hit-testing work; the
handler was always correct).

### Rendering / layout architecture (highest leverage)

- [ ] **Unify the dual frame-render path.** Frame borders are drawn by two
  paths: the renderer's ``_render_frames_to_buffer`` (pass 1, all frames) and
  ``Frame.render_to`` (pass 2, only frames with content / scroll / id). The
  ``FrameNode.collect_elements`` docstring already calls pass 1 the "legacy"
  path. Collapse to a single ``Element.render_to`` path: (1) always include the
  ``Frame`` in ``collect_elements``; (2) delete ``_render_frames_to_buffer``;
  (3) move its recursive ``scroll_offset``/``clip_region`` border plumbing into
  the pass-2 per-element path; (4) regenerate affected golden/snapshot fixtures.
  Medium-high risk (touches every frame render + the scroll/clip code). The
  0.1.0 focus-border fix made pass 1 focus-aware as a stopgap; unification
  removes the duplication entirely.
- [ ] **Group C — horizontal scroll for child-content frames.** Child
  ``TextElement`` bodies only ever compute vertical scroll; ``_content_width`` /
  ``_needs_scroll_x`` are never set, children are clamped to inner width, and the
  renderer threads only a vertical ``scroll_offset``. Needs intrinsic-width
  layout under ``overflow_x``, a horizontal scroll manager, and an x-clip/offset
  through the renderer. (Works today for TextArea + frame *text* content.)
- [ ] **Group D — frame overflow / clip clamping.** ``content_view_demo``:
  scrolling the outer frame lets children escape the frame *top* (clip not
  clamped to the border row). ``frame_overflow_demo``: 3x50%-in-one-row HStack
  width distribution. Needs a focused layout-engine repro.

### Ephemeral-state preservation contract (reconciler)

Originally filed as a "repaint-timing family," but the 06-29 dig found repaints
*do* fire (``_on_state_change`` marks the screen dirty on every state write).
The real conflict is the reconciler's ephemeral-state preservation contract
(``reconciler.py``): on re-render it saves ``get_ephemeral_state()``, applies
prop changes, then ``restore_ephemeral_state()`` — so transient state in
``EPHEMERAL_PROPS`` (cursor/scroll/selection/expansion) is intentionally *not*
synced from props, which is exactly what fights programmatic/bound writes to
those same fields.

- [ ] **Group E — Tree "expand all / collapse all".** The genuine
  ephemeral-contract item. ``expanded_nodes`` lives in the protected bucket, so
  a programmatic expand-all is overwritten by the restored prior expansion.
  Three compounding causes: the tree tag never calls ``set_prop("id")`` (so no
  ``expand_state_key``; sweep Table/Progress/Spinner/Modal/Link/ImageView for
  the same omission); the ``expanded="<key>"`` two-way binding is dropped at
  element creation; and expansion writes need a "bound prop lets state win, else
  preserve" rule. Needs a reconciler design pass. Also (cosmetic): ``tree_demo``
  color behind the ``>`` selector ignores the BG; right panel shrinks to
  content; add-node button.

### Frozen view-``data`` snapshot (DX trap) — RESOLVED 0.1.0

- [x] **Reactive derived view data.** Previously a view function ran *once* and
  its returned ``data`` dict was deep-copied and frozen, so any value derived
  from state never refreshed — only ``state`` stayed live. This silently bit six
  demos (``dialog_showcase``, ``event_patterns``, ``dashboard``, ``data_entry``,
  ``error_handling``, ``executor`` — the last looked like a hung executor).
  Fixed at the framework level: **synchronous view functions are now re-invoked
  every render** (``ViewRouter.evaluate_render``), so derived context is always
  live. Added a Flask-style API — ``render_template_string(src, **ctx)`` /
  ``render_template(name, **ctx)`` returning a ``RenderedView`` — with
  ``on_enter``/``on_exit`` moved onto the ``@app.view`` decorator. The legacy
  ``{"template": ..., "data": {...}}`` dict return still works (and is now live
  too). Async views keep once-resolution (their body can't be awaited from the
  sync render path) and use ``state`` / a ``data`` callable for liveness. Audit
  confirmed only 3 of 70 demo view bodies had side effects; all three were fixed
  (state-setup hoisted out / artificial ``sleep`` dropped). Compiled templates
  are cached by source, so per-frame re-render stays cheap. Tests:
  ``tests/core/test_templating.py``.

- [ ] **autocomplete language toggle** leaves the old caret un-erased (overlaps
  the last typed char) — caret-erase on re-render. (Separate paint/erase bug,
  not the contract above.)
- [ ] **complex_layout** log is editable (should be read-only) — demo/element
  config (set the LogView/TextArea read-only).
- [ ] **context_menu** right-click menu (Copy is only reachable there) — the
  buttons work; the right-click path is the experimental context-menu /
  real-terminal mouse concern the demo itself flags. Needs a real-console repro.

### Cosmetic / theming

- [ ] **Modal severity coloring** — ``alert_dialog_demo`` / ``dialog_showcase``
  error/success/info modals should be colored by severity.
- [ ] **centered_dialog** is not vertically centered as claimed (overlay
  v-centering).
- [ ] **datagrid** selection indicator overdraws the right border (minor);
  **grid** rowspan/colspan cells render without borders.
- [ ] **tabbed_panel** welcome pane overlaps its left/right border (only that
  pane); **radio_demo** "Shipping method" radiogroup intersects the right frame
  border.
- [ ] **status_indicator** — add a blinking state / blink-after-change option.

### Viewport / scrolling UX

- [ ] **Auto-scroll to new content.** ``listview_demo`` add works but the new row
  lands below the fold; ``logview_demo`` streaming log should scroll to bottom
  (or expose an option). ``textarea_demo`` should reveal the end of long lines.
- [ ] **listview / logview demo layout** — rightmost list / buttons overflow the
  panel to the right.
- [ ] **code_editor_demo** — buttons don't fit and the editor escapes the frame;
  add a CodeEditor option to capture Tab instead of moving focus.
- [ ] **event_patterns_demo button row off-screen** — the fixed ``height=36``
  frame holds two tall side panels plus a 26-row log, pushing the action-button
  row (``Go to View 2`` … ``Quit``) to ~row 50, below the viewport. Keys all
  work; the buttons are simply laid out past the visible area. Needs the frame
  content to fit (or scroll) the viewport — a demo-layout + overflow concern.

### Platform-specific (Windows, real-terminal only)

- [ ] **Group G — ``alt+`` / ``ctrl+`` hint keys on Win32.** The layout demo's
  ``[R][S][H][Q]`` combos likely aren't synthesized by the Windows ESC-timeout
  lookahead in ``terminal/input.py``. Needs a real-console repro; may be a
  prompt_toolkit/Win32 limitation to document rather than patch.
- [ ] **spinner_demo on scroll** — trailing ``.`` of the ellipsis ghosts in its
  column; the emoji clock frame ("Working with clock..k") is sized with
  ``len()``. Ties into the wide-character correctness item above.

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
