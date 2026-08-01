# Roadmap

Scoping decisions for upcoming Wijjit releases. This is a living document —
update as items move between buckets.

## Sources & status (consolidated 2026-07-15)

This is now the **single backlog** for all post-0.1.0 work. It absorbed the
per-item backlogs that used to live in the other release trackers:

- **`RELEASE_PLAN.md`** — trimmed to the release *runbook* only (Part 1: the
  external publish steps). Its former "Part 2 — deferred to 0.1.1" backlog was
  merged into this file (see "Framework correctness / cleanup" and the 0.1.1
  sections below).
- The pre-tag audit tracker's Tier 1–3 items all landed and were verified against
  the tree; the only pre-tag item left is the CHANGELOG date, owned by
  `RELEASE_PLAN.md` §1a.
- The remaining framework-correctness items below carry short `(review N.N)`
  labels — internal shorthand from the 0.1.0 code-review pass, kept only so the
  original analysis is easy to correlate.

**0.1.0 itself is code-complete** — everything below is post-tag work. The
release is gated only on the external publish steps in `RELEASE_PLAN.md` Part 1.

## 0.1.0 (current release target)

The framework is feature-complete for a credible first release: ~3700 tests
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
- [x] **Wide-character (CJK / emoji) correctness — standard text path**
  (landed 2026-07-13). The width-aware buffer arrived as a glyph head cell +
  sentinel continuation cell (no ``Cell`` field change): ``write_text`` spends
  its budget in columns, NFD combining marks fold onto the base glyph, and the
  diff/full-render emitters advance by true glyph width — border overflow,
  diff-cursor desync, and the click offset are gone for template/frame text.
- [ ] Wide-character correctness — remaining non-template paths
    - finalize char-vs-column cursor/scroll/edit behavior in TextArea / DataGrid / related input paths
    - make ansi_string_to_cells() emit continuation cells for width-2 glyphs
    - audit remaining width math based on raw char slicing rather than display column
- [x] **Reposition the tagline** (review 3.6). Landed 2026-07-16. The tagline is
  now the recursive acronym "Wijjit Is Just Jinja In Terminal", and the pitch
  leads with what the template architecture buys — a UI that is a static artifact
  tooling can read, hence *lintable* / *headlessly driveable* / *byte-diffed*,
  and easy for LLMs to write and test. "Flask for the Console" is retained only
  as a web-dev on-ramp describing ergonomics, and was dropped from the metadata
  surfaces (``pyproject`` description, ``__init__`` docstring, Sphinx texinfo,
  demo UI strings). The pass also corrected the claims it audited: the "no plugin
  system" limitation (false since review 3.5), example counts (72 → 74, ``apps/``
  3 → 5), test count (~3,000 → ~3,600), and render timings that were ~2x
  pessimistic. ``docs/user_guide/performance.rst`` still carried the pre-2.5
  "the diff renderer is not cheaper in CPU" claim and an FPS column, both now
  gone. The README's headline byte figures are pinned by
  ``test_readme_headline_bytes``.

## 0.1.1 — deferred from the 0.1.0 example pass

Items surfaced by the manual ``examples/`` walkthrough (06-29) and the earlier
demo-bug triage (groups A-H). The cross-cutting / crash items were fixed in
0.1.0; everything below is cosmetic, demo-level, platform-specific, or an
architecture-level refactor not worth the risk days before tagging. Root causes
are in ``RELEASE_PLAN.md`` (Part 2). Pull individual items forward as use cases demand.

**Resolved 2026-07-24 in the pre-tag example sweep** (`tv-notes.md`):
terminal-aware auto-fit sizing (over-committed layouts shrink instead of
clipping); `Tree` adopting its assigned bounds; the Windows click/wheel row
offset (Win32 reports *buffer* coordinates - this also explains "clicking the
scrollable frames and the mouse wheel don't work" and the `wijjit run` vs
`python` discrepancy, both of which verify correct headlessly); `wijjit run`
hanging on inline apps and swallowing script output; `AlertDialog` severity
colours; wrapped text overpainting the widget beneath it; single-character
hotkeys firing while typing. Investigated and *not* framework bugs:
`system_monitor` (psutil simply was not installed; it now fails with an install
hint), `preferences_demo`'s stray cursor (Wijjit emits no show-cursor for any
non-text element - a Windows Terminal artifact). `executor_demo` "always
blocking" turned out to be accurate and deeper than a demo bug: every control in
it is a button, and `RUN_SYNC_IN_EXECUTOR` does not apply to `@app.on_action`
handlers at all, so the demo exercised a setting it could never show. It was
removed for 0.1.0; see the two executor entries below.

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
  Re-confirmed 2026-07-24: the horizontal scrollbar in ``horizontal_scroll_demo``
  is not drawn at all, because ``_needs_scroll_x`` is only ever set in
  ``Frame.set_content``, which a child-content frame never calls. The vertical
  path avoids this via the dedicated ``set_child_content_height`` hook; the fix
  is the horizontal analogue plus the x-offset plumbing above.
- [ ] **Group D — frame overflow / clip clamping.** ``content_view_demo``:
  scrolling the outer frame lets children escape the frame *top* (clip not
  clamped to the border row). ``frame_overflow_demo``: 3x50%-in-one-row HStack
  width distribution. Needs a focused layout-engine repro.
- [~] **Per-keystroke full re-render is linear in view size** (review 2.5).
  Profiling reframed this: the template re-exec / VNode diff / re-wire trio the
  review named is **not** where the time goes — on a 40-row bound-input view,
  Jinja render was ~11%, layout ~10%, and reconcile + wiring did not even reach
  the top 25. **~64% was the paint stage** in ``_compose_output_cells``: newing
  up a full-screen ``ScreenBuffer`` of ``Cell`` objects every frame (~1.28M
  ``Cell.__post_init__`` calls over 200 renders) plus a full-buffer diff (every
  state write marks the whole screen dirty, so the diff scans all rows).
  **Landed (three steps):** (1) empty buffer positions share one blank ``Cell``
  instead of allocating one per position (``_BLANK_CELL``); (2) ``Cell.__eq__``
  identity short-circuit; (3) **incremental (damage-tracked) base rendering** —
  the paint buffer starts as a copy of the previous frame (pooled, reused across
  frames), the write paths change-detect so dirty regions reflect only real
  changes, cells painted last frame but not this one are blanked (vacated
  content), and the diff scans just the damage. Gated to the safe case (no
  overlays this/last frame, stable size, diff rendering on) with a full-repaint
  fallback and an ``incremental_render`` off-switch. Measured **~32% less
  per-render CPU on a localized edit** in a 40-row view, screen output
  byte-identical to the full-repaint path (pinned by an equivalence test +
  emitted-bytes replay). **(4) printable-ASCII width fast path** — with the
  allocation and diff costs gone, re-profiling showed the top remaining cost was
  ``wcwidth``/``wcswidth`` (per-character Unicode-table bisection for every glyph
  painted and every cell measured). ``ansi.display_width`` now fast-paths the
  all-printable-ASCII case (provably one column each -> ``len``) and defers to
  ``wcswidth`` otherwise; measured **~2x faster per render** (~8.6->~4.6 ms) and
  it helps the full-repaint path too. **(5) interned cells on the paint path** —
  ``write_text``/``fill_rect`` newed up a ``Cell`` per glyph per frame; a bounded
  ``cell.intern_cell`` now shares one immutable cell per ``(char, style)`` (keyed
  positionally), cutting allocation churn and feeding the diff's identity
  short-circuit (unchanged glyph -> same object frame-over-frame). Measured
  **~15% less per-render CPU** on top of (4). **(6) cheaper damage bookkeeping** —
  the per-frame coverage set now stores a packed ``y * width + x`` int per cell
  instead of an ``(x, y)`` tuple (no tuple alloc per glyph; ~21% faster on the
  isolated coverage add), and ``is_continuation`` tests ``not cell.char`` instead
  of a string compare; both screen-identical. **(c) skip re-painting unchanged
  elements** — the paint itself was the next-biggest lever (``render_to`` ran for
  every element every frame). On the incremental path the buffer already starts
  as a copy of the previous frame, so an unchanged element's cells are already
  correct; each element now exposes a ``render_signature()`` and, when it plus
  on-screen geometry match the previous frame, ``render_to`` is skipped and the
  element's prior painted region is re-recorded as coverage. Guarded: ``None``
  signature = always repaint; elements overlapping the always-repainted
  frame-border pass or under an ``overflow_x="visible"`` frame are never skipped;
  a ``verify_skips`` mode paints anyway and asserts byte-identity (run across
  every example). Signatures first shipped for ``TextElement``/``TextInput``/
  ``Button``; measured **~14% less per-render CPU** on a static-heavy 40-row
  view, screen output byte-identical (on-vs-off screen + emitted-ANSI
  equivalence tests). **Follow-up landed:** signatures now also ship for
  ``Checkbox``/``CheckboxGroup``/``Radio``/``RadioGroup``/``Toggle``/``Slider``/
  ``ProgressBar``/``StatusIndicator``/``StatusBar``/``Link``/``Sparkline``/
  ``Gauge``/``ColumnChart`` (sensitivity-unit-tested + verify-swept), measured
  **~1.36x (~27% less CPU)** on a static form where one field changes per
  keystroke; ``Select``/``BarChart``/``Table`` stay on the ``None`` default
  (paint couples to internal scroll state). The benchmark
  (``scripts/bench_perf.py``) was also fixed to measure the incremental path
  (``allow_incremental=True``) the app actually uses, not a full repaint.
  **Still open — dropped as measured near-zero:** static frame-border skip
  (~3% of render) and a per-interned-cell width cache (the diff-emit width path
  is ~3 calls/frame on the incremental path; the hot ``display_width`` calls are
  in ``write_text`` measurement, which the ASCII fast path already covers).
  **Still open — the real remaining lever, deferred:** *incremental multi-line
  text repaint*. A run of consecutive plain-text lines collapses into a **single**
  ``TextElement`` whose ``text`` is the newline-joined block, so a change to any
  one line changes that element's signature and repaints the **whole** block
  (write_text per line). In a text-heavy framed view that dominates per-keystroke
  cost (~55-60% of render), though realistic forms/dashboards mostly avoid it
  (the changing widget is a separate, skippable element, so the static text block
  already skips). The fix is a line-level version of option (c) inside
  ``TextElement`` — repaint only changed lines and re-record the unchanged lines'
  coverage — but it touches the hottest paint path and needs the same flag +
  verify-mode + byte-identity rigor, so it is its own carefully-guarded change.
  Distant last: template/reconcile/wiring memoization (tiny by measured cost).
- [ ] **CodeEditor soft-wrap scroll desync** — the editor renders *actual* lines
  while its scroll content size counts *wrapped* lines, so long lines clip
  (``code_editor.py:478,839``).

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
- [ ] **Keyless elements lose ephemeral state on update; positional frame IDs
  break under conditional layouts.** (1) Because VNodes key on ``id`` and unkeyed
  elements get per-render positional ids, a keyless element loses its ephemeral
  state (cursor/scroll/selection) on update — needs a positional/path cache
  (``reconciler.py``). (2) Positional frame-ID generation breaks scroll/collapse
  preservation under conditional (``{% if %}``) layouts (``render_context.py``).
  Part (3) of this family — positional ids doubling as *state keys*, silent data
  loss — was fixed in 0.1.0 via first-class ``key=`` (see review 1.1 / CHANGELOG);
  (1) and (2) remain.
- [x] **Declarative control of ephemeral props** (review 2.6). **Landed** as the
  "bound prop lets state win, else preserve" rule. A new
  ``CONTROLLABLE_EPHEMERAL_PROPS`` (``EPHEMERAL_PROPS`` minus ``focused``/
  ``hovered``) plus ``Reconciler._diff_controlled_ephemeral`` reports a
  controllable ephemeral prop **only when its bound value changed** between
  renders; ``_update_element`` applies it over the preserved
  ``get_ephemeral_state`` snapshot, so it flows through each element's existing
  ``restore_ephemeral_state`` (reusing its clamping / scroll-manager mapping).
  Now ``{% textinput cursor_pos=cur %}`` / ``{% listview scroll_position=sp %}``
  / ``highlighted_index=`` work; a live cursor/scroll move survives a re-render
  whose binding did not change (no controlled-input caret snap-back). Also
  normalized the underscore scroll keys (``_scroll_position`` →
  ``scroll_position``) across TextArea/Tree/Select/DataGrid/Frame so every
  element speaks the ``EPHEMERAL_PROPS`` vocabulary. **Deliberately out of
  scope:** ``focused`` (needs ``FocusManager`` coordination — use
  ``focus_element_by_id`` / ``bind_focus_key``) and Group E (Tree expand-all,
  which additionally needs the tree tag to call ``set_prop("id")`` and the
  ``expanded=`` binding plumbing — a self-contained follow-up that can build on
  this). LogView's auto-tail still overrides a stale controlled ``scroll_position``
  by design (a tailing log should not be yanked by a stale binding).

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
- [x] **complex_layout** log is editable (should be read-only) — already
  resolved: the demo now renders the log through a read-only ``ContentView``
  (verified headless: typed input does not alter the pane).
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
- [~] **code_editor_demo** — buttons don't fit and the editor escapes the frame.
  The Tab half of this item shipped in 0.1.0: ``captures_tab`` gives a focused
  element first refusal on Tab, ``CodeEditor`` defaults to capturing it and
  ``TextArea`` opts in with ``capture_tab=True``. The ``Ctrl+Tab`` escape hatch
  originally proposed here is impossible — terminals encode Ctrl+I as Tab — so
  Shift+Tab (which wraps) is the way out. Remaining: the demo's own layout.
- [ ] **``DataGrid`` Tab cell navigation is parked.** ``datagrid.py:1095`` and
  ``:1217`` implement Excel-style Tab/Shift+Tab between cells, and until the
  0.1.0 ``captures_tab`` work it could never run (the global Tab handler
  cancelled the event first). It is still off, deliberately: both branches
  return ``True`` unconditionally, including at the last cell, so opting the
  grid in as-is would make Tab *and* Shift+Tab dead keys inside it. Fix the
  edge returns (return ``False`` at the last/first cell so focus moves on),
  then set ``captures_tab``.
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
- [~] **``autocomplete_demo`` — typing is reported as broken once the suggestion
  popup opens.** Reported 2026-07-24. Half of this is now answered. The
  "popup never opens under the harness" mystery was mundane: ``CompleterConfig``
  defaults to ``trigger="manual"``, so typing is *supposed* to do nothing until
  ``Ctrl+/``. A completer built with ``trigger="auto"`` opens the popup under
  the harness fine, which makes the whole path testable —
  ``tests/core/test_tab_capture.py::TestAutocompleteSelectOnTab`` drives it
  end to end. That test also fixed one real defect the report may have been
  describing: ``select_on_tab`` was unreachable code, because the global Tab
  handler cancelled the event before the input saw it, so Tab moved focus out
  of the field mid-completion instead of accepting the suggestion. Still open:
  whether anything *else* misroutes keys while the popup is open on a real
  console, and whether the demo should default to ``trigger="auto"`` so it
  demonstrates what its name promises.

### Input & terminal handling (from the 0.1.0 code review, 2.12 tail)

Small, mostly self-contained fixes deferred from the review's 2.12 batch (the
CONFIRMED cheap wins there already shipped: fill-remainder distribution, grouped
diff SGR, once-per-frame size sampling, SplitPanel clamp+weakref).

- [ ] **Esc/Alt second 50ms timeout; only letters reach ``alt+``.** On ``escape``
  Wijjit blocks up to 50ms for a follow-up (``input.py:552-578`` sync,
  ``815-841`` async), *on top of* prompt_toolkit's own vt100 disambiguation — so
  every standalone ESC carries a 50ms latency floor. Only ``isalpha()`` follow-ups
  become ``alt+<x>`` (``input.py:562``), so **Alt+digit, Alt+punctuation, and
  Alt+arrow are unreachable** on every platform. Overlaps Group G (Win32 alt-keys).
- [ ] **SIGWINCH-driven resize.** No ``SIGWINCH`` handler; resize is polled via
  ``get_terminal_size()`` once per frame (``event_loop.py``), so an idle app can
  take up to the 0.5s input timeout to reflect a resize. (The mid-frame *tearing*
  half — sampling the size 3x per ``_render`` — was fixed in 2.12.)
- [x] **``_OTHER_ANSI_PATTERN`` weaker than ``ansi.py``**. CONFIRMED and fixed
  2026-08-01. ``ansi_adapter.py`` used ``\x1b\[[0-9;?]*[A-Za-z]``, omitting
  intermediate bytes and restricting the final byte to letters, so ``\x1b[3~``
  matched nothing and the fallthrough planted a **literal ``\x1b`` Cell** into
  the buffer. Both paths now use the full ECMA-48 CSI grammar; SGR still wins
  by being tried first.
- [x] **DCS sequences pass through ``strip_ansi``**. CONFIRMED and fixed
  2026-08-01. ``\x1bP…\x1b\\`` (Sixel) matched neither branch of
  ``ANSI_ESCAPE_PATTERN``, so a whole image counted as visible text. DCS/SOS/PM/
  APC added as their own alternative.
- [ ] **Legacy "normal" mouse mode + per-byte multi-byte input** (``mouse.py``,
  ``input.py``). SGR is the default and works; the legacy path needs bypassing
  prompt_toolkit's UTF-8 decode. Architectural, low value — migrated from
  ``RELEASE_PLAN`` Part 2a.
- [ ] **Mixed ``%`` + ``fill`` siblings mis-account space** (SUSPECTED — could not
  reproduce; **write a test first**). ``VStack.assign_bounds`` reserves a
  percentage child's *intrinsic* height alongside fixed children but the per-child
  loop assigns ``int(content_height * pct)`` and advances by that larger value
  (``engine.py:540-549, 586-587, 632``). Likely needs a taller element to surface.

- [ ] **``RUN_SYNC_IN_EXECUTOR`` silently does not apply to action handlers.**
  ``HandlerRegistry.dispatch_async`` honours the executor, so a blocking
  ``@app.on_key`` / mouse / change handler runs on a worker thread and the loop
  keeps servicing timers, background tasks and state callbacks. ``@app.on_action``
  handlers never reach the registry: ``Wijjit._dispatch_action`` (``app.py``)
  calls ``result = handler(action_event)`` inline, so the config has *no effect*
  on them. Measured 2026-07-24: with a 0.4 s blocking handler, the key path lets
  ~20 background ticks through with the executor on and 0 with it off, while the
  action path is 0 either way. Since buttons are the obvious place a user reaches
  for this, the setting looks broken. Fix is to route ``_dispatch_action``
  through the same executor path — deferred because it changes when every action
  handler runs relative to state callbacks and re-render, which needs its own
  test pass. Pinned by ``tests/core/test_executor_dispatch.py``; those
  expectations flip when it lands.
- [ ] **Even on the executor, a long handler delays the next frame.** The
  executor frees the event-loop *thread*, but ``_process_frame_async`` still
  ``await``\ s the dispatch and the loop body is one sequential coroutine, so
  nothing repaints until the handler returns. Async handlers are awaited inline
  too and block the frame just the same unless they spawn a task. Making "the UI
  stays responsive during a long action" true needs opt-in fire-and-forget
  dispatch, which changes handler ordering guarantees.
- [ ] **Restore an executor demo once the two items above land.**
  ``examples/advanced/executor_demo.py`` was removed before 0.1.0 (2026-07-24):
  every control in it was a button, so it demonstrated a setting it never
  exercised — its screen was byte-identical with the executor on and off, and it
  advertised responsiveness the framework does not provide. A replacement should
  show the observable difference (background work progressing during a blocking
  handler) rather than asserting it in prose.

### Framework correctness / cleanup (from the 0.1.0 code review)

Migrated from the former ``RELEASE_PLAN.md`` Part 2b/2c. None are API-visible;
they are where future bugs get applied inconsistently. Lower-severity, not
release-blocking — pull forward opportunistically.

**Internal dedup / consolidation (no API-shape risk):**
- [ ] ``read_input`` vs ``read_input_async`` (~250 lines near-duplicated); the
  scroll key/wheel + ``on_scroll`` block re-inlined ~50x across the six
  scrollables; view lifecycle-hook dispatch + ``_navigate_sync/async_impl``
  near-duplicated; border ``2``/``-2`` geometry (add an ``inner_dimensions()``
  helper — ``BORDER_THICKNESS`` already landed); size-spec resolution across
  VStack/HStack/Grid; chart ``_get_*_color`` wrappers; the State reserved-key
  message x5; ``DirtyRegion`` re-implements ``Bounds`` geometry.
- [ ] Dead legacy string-render methods (``progress.py``, ``statusbar.py``,
  ``tree.py``, ``select.py``, ``reconciler._collect_elements``,
  ``mouse_router._route_to_element``); the large dead ``CSSParser`` compat class;
  divergent named-color→RGB maps (centralize ``ANSI_PALETTE`` / ``CSS_PALETTE``).
- [ ] Manager-naming nits: ``clear_cache`` means different caches on Renderer vs
  Reconciler; hover/focus getter-setter verb parity; three manager DI styles.

**MEDIUM/LOW correctness (condensed):**
- [ ] **Core:** ``on_key`` registry overwrites handlers sharing a key; ``State``
  has no locking around callback lists despite documented multi-thread access;
  ``batch_update`` drops all notifications on exception after applying writes;
  ``dispatch_async`` lacks per-handler exception isolation; non-interactive
  overlays (tooltips/notifications at TOOLTIP z-index) can swallow clicks to
  base UI. (``set_focus_filter(None)`` being a no-op that contradicted its
  docstring was fixed 2026-08-01 — it now rebuilds the cycle from
  ``all_focusable``.)
- [~] **A template with two top-level sibling elements silently drops all but
  the first.** ``{% textinput id="a" %}{% textinput id="b" %}`` at the root of a
  template renders only ``a`` — ``RenderContext.add_vnode`` has nowhere to put
  the second once ``vnode_root`` is set, so it is dropped with no warning.
  Found 2026-07-31 while writing the Tab tests. **``wijjit validate`` flags it
  as of 2026-08-01** (``multiple-root-elements``, statically — by render time
  the extras are not in the tree to notice; ``{% if %}`` branches count as
  alternatives, and a top-level ``{% for %}`` counts as the same defect).
  Still open: whether the renderer should *implicitly wrap* multiple roots in a
  ``{% vstack %}`` rather than only warn. Deferred because it changes render
  output for any template relying on the drop, so it needs a golden sweep.
- [ ] **Layout:** frame inner dims can go negative (missing ``max(0,…)``);
  ``space-around`` mis-distributes remainder + double-counts ``column_gap``;
  split-panel ``_clamp_ratio`` vs ``_calculate_sizes`` disagreement (resize
  jitter) + unvalidated persisted state; ``Size`` fill/percentage classification
  ambiguous for ``"100%"``.
- [ ] **Display:** Table sort not stable + string-coerces mixed types; ContentView
  re-renders content every frame; Pager ``remove_page`` leaves scroll-state keys
  pointing at the wrong page. (LogView ``set_lines`` re-tail and the
  reconcile/prop-sync path already fixed — see CHANGELOG.)
- [ ] **Charts/status/overlays:** BarChart drops last partial multi-row bar; Gauge
  ticks/min-max not reserved in auto-height; HeatMap legend ``bar_width`` can go
  negative; ImageView broad ``except`` + brittle duck-typing.
- [ ] **Styling:** ``font-weight:normal`` / ``text-decoration:none`` never turn
  attributes OFF; ``theme.set_style`` doesn't invalidate the resolver cache (stale
  styles); no JSON theme loader despite CLAUDE.md mentioning JSON.
  (``_infer_class_from_element`` stale keys fixed 2026-08-01. Auditing the whole
  table against the default theme found the problem was wider than the two
  recorded here: ``ListView``→``list``, plus ``CodeEditor``, ``MenuElement``,
  ``ModalElement``, ``NotificationElement`` and ``ProgressBar`` all inferred a
  key no theme defines, so they got *no* base styling at all. ``radiobutton``
  named a class that does not exist. The regression test asserts the property —
  no element may infer away from a key the theme defines under its own name —
  rather than the table.)
- [x] **Config/API:** invalid ``WIJJIT_LOG_LEVEL`` silently → INFO; CLI
  ``--context`` / ``context=`` silently ignored in ``.py`` app mode for
  ``validate`` / ``tree``. Both fixed 2026-08-01. The log-level lookup went
  through ``getattr(logging, name)``, which also accepted any uppercase module
  attribute (``BASIC_FORMAT`` set the level to a format string); it now resolves
  through an explicit table and reports an unknown name through the logger, so
  the warning lands in the log file rather than on the terminal a TUI is about
  to paint.
- [x] **Devtools / linter polish** (found while verifying the claims in review
  3.6; these are now the tooling the README *leads* with, so the bar is higher
  than the severity suggests). **All three landed 2026-08-01**, together with
  the two false-positive classes in issue #59 and a ratchet test requiring every
  bundled example to validate clean. That ratchet immediately found a third
  instance of the Group E ``expanded=`` gap (``tree_demo`` as well as
  ``filesystem_browser``); both are recorded in ``KNOWN_FINDINGS`` with a
  companion test that fails if the finding ever stops reproducing, so the
  exemption cannot outlive the bug.

  - [x] **Duplicate findings inside loops.** One bad attribute in a ``{% for %}``
    over N items reported N times — the check runs per unrolled VNode, and the
    findings were never deduped. Findings are now deduped before the report is
    rendered.
  - [x] **No line numbers on VNode-derived findings.** ``unknown-attribute`` and
    ``unknown-element-type`` come from the VNode tree, which has lost source
    positions, so they printed as ``file: WARNING[...]`` while AST-derived
    findings (e.g. ``unkeyed-loop-element``) correctly printed
    ``file:4: WARNING[...]``. The line is now recovered from the template AST
    (where the attribute is still a literal keyword) and matched back by
    (element type, attribute). Tags that build more than one node kind
    (``frame``, ``radiogroup``) stay unmapped rather than guess, and keep the
    old no-line behavior.
  - [x] **``--context`` with inline JSON raises a raw traceback.** Actually
    caught, but reported as ``OSError: [Errno 22] Invalid argument`` — which
    names neither the flag nor the fact that it wanted a filename. Inline JSON,
    a missing file, and malformed JSON now each get their own message.
- [ ] **Lower-priority semver/API notes** (from the 0.1.0 release audit — "fix
  opportunistically, else document"): make params after the first keyword-only on
  ``Wijjit.__init__`` / ``WijjitHarness.__init__``; unify the state-init kwarg name
  (``initial_state`` vs ``app_from_template(state=)`` vs ``State(data=)``);
  ``Wijjit(**config_overrides)`` silently uppercases typo'd kwargs into config
  keys; two classes named ``MouseEvent`` (core wrapper vs terminal, the core one
  unexported though MOUSE handlers receive it); ``vstack`` supports only
  ``spacing`` while ``hstack`` calls ``spacing`` "legacy" (align docs).
  (``harness.py`` setting ``UNICODE_SUPPORT = True`` — invalid for the
  ``auto/force/disable`` contract, and post-``__init__`` so it no-opped — fixed
  2026-08-01: set to ``"force"`` and actually pushed to ``terminal.ansi``, with
  ``close()`` restoring the previous mode since it is process-global. Harness
  snapshots had been depending on terminal detection all along.)

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
- [ ] **Reactive collection wrappers for `State`** (`ReactiveList` /
  `ReactiveDict` / `ReactiveSet`). `State.mutate(key)` (landed 2026-07-31)
  gives a *correct* in-place idiom for any value, but it is opt-in: a naive
  `state["todos"].append(x)` is still silent, which is why
  `examples/widgets/input_dialog_demo.py` and `confirm_dialog_demo.py` carry a
  `state["_refresh"] = True` sentinel. Wrappers make the wrong idiom
  impossible rather than merely providing a right one. Design notes from the
  2026-07-31 discussion:
  - **Subclass the builtins, not `UserList`/`UserDict`.** `isinstance(x, list)`
    is load-bearing (`State._is_aliased_mutable`, `json.dumps`, pandas in
    `DataGrid`, Rich). The mutator set is finite and known - for `list`:
    `append, extend, insert, remove, pop, clear, sort, reverse, __setitem__,
    __delitem__, __iadd__, __imul__`. Explicit overrides, no metaclass: a
    metaclass that generates methods produces attributes `mypy --strict`
    cannot see, and Phase 3 is about shrinking the override list.
  - **Identity is the real cost.** CPython refuses `obj.__class__ =
    ReactiveList` for builtin instances, so `state["k"] = my_list` must store
    a *copy*: `state["k"] is my_list` becomes False and outside references
    silently detach. This trades a uniform rule ("mutation never fires") for a
    conditional one. Vue 2 shipped exactly this; go in knowing the price.
    `mutate()` has no such cost, which is why it stays the documented fallback.
  - **Wrap recursively at assignment, not lazily on read.** List-of-dicts is
    the dominant TUI shape (table rows, todo items); lazy-on-read would return
    a fresh wrapper per `state["rows"][0]` access. Recursive-on-assign is O(n)
    once, which the current copy-first idiom already costs.
  - Reuse the `forced=True` notification path added for `mutate()`; gate on a
    `REACTIVE_COLLECTIONS` key in `DefaultConfig`, default on.
- [x] **Public element-registration API / plugin seam** (review 3.5). **Landed
  2026-07-16.** A process-global plugin registry (``src/wijjit/plugins.py``) is
  drained at construction by every ``ElementRegistry`` and ``Renderer`` (so the
  app renderer *and* the devtools validator see plugins for free), sidestepping
  the fact that both registries are built privately per-Renderer. Public surface:
  top-level ``wijjit.register_element(type_name, cls, *, tag=, aliases=,
  extension=, override=)``, a ``@wijjit.element(...)`` decorator, and a
  ``Wijjit.register_element(...)`` instance method that live-patches an
  already-built app (via Jinja's public ``env.add_extension``). The DX win is
  ``wijjit.tags.plugin_ext.make_element_extension``, which generates the leaf
  ``{% tag %}`` from the existing ``layout.py`` helpers so an author writes only
  an ``Element`` subclass + one ``register_element`` call. Auto-discovery via a
  ``wijjit.plugins`` entry-point group (``pytest11`` precedent; a broken plugin is
  logged, never fatal). ``PluginRegistrationError`` on non-``Element`` / builtin /
  cross-plugin collisions (``override=True`` to shadow); a module reload refreshes
  rather than colliding. Built-in extensions hoisted to a ``BUILTIN_EXTENSIONS``
  constant feeding a new ``builtin_tag_names()``; ``builtin_type_names()`` gives
  the built-in collision set without recursion. **Scope:** leaf elements only;
  custom *containers* (layout-tree-builder + validator ``CONTAINER_TYPES``
  integration) are the deferred follow-up. Tests in ``tests/plugins/``; demo
  ``examples/advanced/plugin_element.py``; ``docs/NEW-ELEMENTS.md`` "Shipping an
  element as a plugin".
- [ ] **Converge InlineApp and full-app input handling.** ``InlineApp``
  (``inline/app.py``) reimplements a thin slice of the event loop's keyboard
  path and diverges from ``EventLoop`` (``core/event_loop.py``) in ways that
  make interactive inline apps (e.g. ``examples/apps/gcommit.py``) feel
  second-class. Ultimately these two input paths should share a common core
  rather than duplicate; the seam is worth a design pass. The known gaps, in
  rough order of leverage:
  - [x] **Arrow-key focus navigation between elements** — **already landed**;
    this entry was stale (noticed 2026-08-01 while scoping 0.1.1).
    ``InlineApp._arrow_focus_move`` / ``_arrow_focus_when_unfocused``
    (``inline/app.py``) implement both the event loop's "element didn't consume
    the arrow -> ``focus_previous``/``focus_next`` on Up-Left / Down-Right"
    fallback and the "no focus yet, an arrow enters the ring" case. The rest of
    the convergence items below are still open.
  - **No action / handler dispatch.** ``InlineApp`` has no ``HandlerRegistry``,
    so ``@app.on_action`` / ``@app.on_key`` / Enter-to-submit don't exist and a
    RadioGroup's ``action`` is dropped. This is by design today (the inline
    model is "fill a form, read ``state`` after Ctrl+Q") but is the main thing
    separating an inline app from a real Wijjit app. Adding it changes the
    constructor API and pulls in the event machinery.
  - **Shallow, callback-bypassing state sync.** ``_sync_element_state`` guesses
    among ``.value``/``.text``/``.checked`` and writes straight to
    ``_state.data``, skipping ``on_change``/``watch`` callbacks; the full app
    uses ``ElementWiringManager`` for real bidirectional binding.
  - **No mouse** (``enable_mouse=False``; mouse events dropped), **no overlays /
    Escape / dialogs / notifications**, and **no element identity across
    renders** (the full app reconciles to preserve ephemeral focus/cursor
    state; ``InlineApp`` rebuilds elements every frame and re-derives focus by
    order via ``FocusManager.set_elements``).
- [ ] **``wijjit form`` — pipe-composable TUI forms.** Wrap a bash script or CLI
  command in a throwaway TUI that collects input and composes in a pipeline:
  ``git diff | wijjit form commit.wij.j2 | git commit -F -``. The form renders on
  the controlling terminal; the *data* goes to stdout (JSON by default, or a
  Jinja ``--output`` string over the same bound-state dict). Piped stdin is
  exposed as a template context variable, so forms compose in both directions —
  the canonical shape being ``producer_json | wijjit form t.wij.j2 --stdin-json
  | consumer_json`` (with ``jq`` reshaping between stages). ``--stdin-json``
  *merges* rather than replaces, so each stage enriches the object and upstream
  keys flow through. Unlocks setup/config wizards in bash scripts, long-form
  input/review, review-and-approve and dry-run -> review -> submit gates, and
  multi-select + options. The review gate gets its own verb — ``terraform plan
  -json | wijjit approve && terraform apply`` — since it is the one case with no
  fields at all (the whole output is the exit code); it echoes stdin on approve
  (only when stdout is not a TTY) and emits nothing + exits 1 on deny, renders
  arbitrary stdin via the existing ``content_type`` machinery (``--as
  diff|json|markdown``, through ``Pager``/``ContentView``, which also sidesteps
  the ``CodeEditor`` soft-wrap bug), and is implemented as a **built-in
  template** so ``--print-template`` graduates it like any other — the shorthand
  verbs must not become a second form model. Note ``producer | wijjit approve |
  consumer`` does *not* gate (consumer runs on empty stdin); ``&&`` is the safe
  idiom.
  **Headline use case — agents.** A console agent writes the form spec, wijjit
  renders it, the user fills it in, and the JSON goes straight to the consuming
  command — all from bash, needing no harness support beyond "can run a shell
  command". It is the artifact-first pitch's conclusion (the form is a file the
  *model* writes) and the agent can lint its own UI first:
  ``wijjit validate /tmp/f.wij.j2 && wijjit form /tmp/f.wij.j2 | consumer``.
  This also lets a **secret bypass the model's context window** — but that is a
  property of the *plumbing*, not the form, and needs a real mechanism:
  ``password=true`` (which exists) only masks the display, and ``wijjit form``
  cannot tell ``| curl`` (safe) from a bare agent-captured invocation (leaks) —
  both are just a pipe at the fd level. So a ``secret=true`` field must be
  *routed* away from stdout entirely, to ``--secret-fd N`` / ``--secret-file``,
  with stdout's JSON carrying ``null`` and an exit-2 refusal when no sink is
  given. Do not make the out-of-context claim before that mechanism ships; the
  failure mode is a silently leaked credential.
  **The wedge:** ``gum``/``fzf`` do one widget per invocation and let the shell
  compose them — they structurally cannot do one form with several fields you Tab
  between. Wijjit can, because the form is a template, which also makes it
  lintable (``wijjit validate``), headlessly driveable (``wijjit render --keys``),
  and harness-testable. Flags (``--input NAME``, ``--textarea NAME``, ...) are a
  ten-second on-ramp defined as **sugar that desugars into a template**, with
  ``--print-template`` to graduate flags → file; they stay shallow on purpose, so
  there is exactly one form model. **Enabler already exists:** the
  ``TerminalBackend`` seam (``terminal/backend.py``) — a ``TtyBackend`` writing to
  ``/dev/tty`` / ``CONOUT$`` is required because stdout belongs to the pipe (and
  stdin often does too, so ``get_size`` must use the tty fd, not stdout). The one
  unknown needing a spike first is ``create_input_handler`` over ``/dev/tty``
  (prompt_toolkit's ``Vt100Input`` takes a file object; the Windows console path
  is less clear). Defaults to the full app + alternate screen (the form is
  transient *input*, not output; ``InlineApp``'s gaps above — no action dispatch,
  no arrow focus nav, no reconcile — are exactly what a form trips); ``--inline``
  rides on the convergence item above. Known sharp edge: pipes don't propagate
  cancellation, so ``| git commit -F -`` runs even on Esc — cancel emits nothing
  and exits 1 (for ``pipefail``), and command substitution is the documented
  idiom. Exits 3 with no controlling tty; ``--non-interactive`` makes the same
  script work in CI. Field validation is deliberately **out of scope** — it should
  be a framework-wide element feature (``required=``/``pattern=``) this consumes,
  not a CLI-only dialect. Acceptance test: rewrite ``examples/apps/gcommit.py``
  (already this exact app, hand-written on ``InlineApp``) as a template plus a
  two-line shell function. MVP = the TtyBackend spike + ``wijjit form TEMPLATE``
  → JSON + ``--output``/stdin context.
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
