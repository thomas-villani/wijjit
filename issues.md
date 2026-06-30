# Demo bug tracker


## 06-29-26 Review

Disposition (mid-review pass, 06-29): FIXED for 0.1.0 are the cross-cutting
mouse-scroll hit-test bug and the two crashes/hangs, the inline_progress
double-percentage, the frame focus-border, and (06-29 dig) the autocomplete
mouse-select wiring plus the dialog_showcase / event_patterns log panels and
the select_demo Submit (was the scroll offset). See [x] items below. Remaining
items are cosmetic, platform-specific, or architectural and are DEFERRED to
0.1.1; items with an explicit "(DEFERRED 0.1.1 ...)" tag carry a root-cause
note. The 06-29 dig reclassified the so-called "repaint-timing family": repaints
DO fire - the genuine architecture item is the reconciler ephemeral-state
preservation contract (tree expand-all), and the log-panel bugs were a separate
"frozen view-`data` snapshot" DX trap (both tracked in roadmap.md).

- [x] examples/basic/alignment_demo.py - Visual: Leftmost border and rightmost border are not colored on focus like the top and bottom (and corners)
      FIXED (framework): a child-bearing frame draws its top/bottom borders in
      `Frame.render_to` (focus-aware) but skips the body, so the vertical side
      borders are painted only by the renderer's frame-border pass
      (`_render_frames_to_buffer`), which ignored focus. That pass is now
      focus-aware (resolves `<prefix>.border:focus` when `frame.focused`), so all
      four sides + corners share the focus color. This was a regression from the
      cell-render refactor that split frame bodies out to child elements.
      Regression tests: `tests/integration/test_frame_focus_border.py`. (The full
      dual-path unification - collapsing pass-1 into `Frame.render_to` - remains
      a 0.1.1 roadmap item; this fixes the user-visible symptom cleanly.)

- [ ] autocomplete.py - Visual: when toggling the language, original caret is not erased, overlaps the last typed char
      (DEFERRED 0.1.1 - caret-erase on re-render; cosmetic.)

- [ ] grid - rowspan/colspan cells have no border? (DEFERRED 0.1.1 - DataGrid span rendering.)

- [x] inline_progress_demo.py - the "Multi-task progress demo" displays the percentages twice:
         `Task 1:█████████████ 100.0%100%`
      FIXED (demo): the progressbar already renders its own percentage label;
      the multi-task template additionally appended `{{ state.taskN }}%`. Removed
      the redundant suffix to match demo_progress_bar.

- [x] mouse_demo.py - mouse works fine before scroll, after scroll, mouse clicks are offset, must click 2 rows below button to trigger it.
      FIXED (framework, cross-cutting): the renderer painted children at
      `bounds.y - scroll_offset` but hit-testing used the unscrolled logical
      `bounds`. The renderer now records the actually-painted, clip-intersected
      on-screen rect (`Element._screen_bounds`) in both render passes, and
      `mouse_router._hit_bounds` hit-tests against it. Regression tests in
      `tests/integration/test_scroll_hit_testing.py`. Affects every scrollable
      frame (mouse_demo, content_view, ...).

- [x] theme_config_demo.py - seems to crash and hang, had to close the terminal.
      FIXED (demo): the default sub-demo (DEFAULT_THEME) instructs "Press 'q' to
      quit" but never bound `q` (global QUIT_KEY default is ctrl+q), so the app
      could not be exited and looked hung. Added an `@app.on_key("q")` quit
      handler. (No framework crash - the app renders fine.)

- [ ] alert_dialog_demo.py - should color the error / success / info alert modals
      (DEFERRED 0.1.1 - severity-based modal theming; cosmetic enhancement.)
- [ ] centered_dialog.py - is not vertically centered as claimed (DEFERRED 0.1.1 - overlay v-centering.)
- [ ] code_editor_demo.py - the buttons don't fit, and the editor goes off the frame.
     - hitting tab switches to the next element, should probably disable or allow to disable
     (DEFERRED 0.1.1 - demo layout + CodeEditor tab-capture option.)

- [ ] content_view_demo.py - scrolling main frame causes elements to escape top of parent frame
      (DEFERRED 0.1.1 - group D clip-region not clamping to frame borders on scroll.)

- [ ] datagrid_demo.py - EXCELLENT. Selection indicator causes right border to erase sometimes, minor
      (DEFERRED 0.1.1 - minor; selection indicator overdraws the right border.)
- [x] dialog_showcase.py - "Action Log" never populates.
      FIXED (demo): the log text was precomputed at the top of the view function
      and passed via `data`. A view function runs once and its `data` dict is
      deep-copied/frozen, so the value stuck at the first-render "No actions
      yet...". State (`action_log`) updated fine and the OK button worked (mouse
      + keyboard) - only the panel was stale. Moved the rendered text into
      `state.action_log_text` (refreshed in `log_action`) so it stays live.
      Root cause (frozen view-`data` snapshot) tracked in roadmap.md.
      (Modal severity coloring is separate, still DEFERRED 0.1.1.)

- [ ] listview_demo.py - rightmost list extends outside of frame.
     - "Add Fruit" and "Add Task" doesn't seem to actually add to the lists, just says "Added New Fruit .. to the fruits list"
     (PARTIAL: the add DOES work - verified headlessly the item is appended and
     rendered; it just lands below the visible viewport in a full list (no
     auto-scroll to the new row). Rightmost-list-overflow + scroll-to-new-row
     DEFERRED 0.1.1.)

- [ ] logview_demo.py - streaming log should probably scroll to bottom (or at least have option)
    - buttons go off edge of panel to right
    (DEFERRED 0.1.1 - LogView auto-scroll option + demo button layout.)

- [x] radio_demo.py - CRASH ON SUBMIT - see radio_error.log
      FIXED (framework): submit reveals an `{% if state.submitted %}` block with a
      `{% vstack padding_left=2 %}`. Directional padding reached the VStack/HStack/
      Grid layout nodes as a 4-tuple, but their geometry assumed a scalar
      (`2 * self.padding`) and crashed with
      `unsupported operand type(s) for +: 'int' and 'tuple'`. Padding is now
      normalized to a 4-tuple (like margin) and applied per-side. Regression
      tests in `tests/layout/test_engine.py` and
      `tests/examples/test_example_interactions.py`.
- [ ] radio_demo.py - "Shipping method" intersects right frame border, strange drawing overlap where parent frame drawn into the "shipping method" box.
      (DEFERRED 0.1.1 - radiogroup/frame border overlap; cosmetic, separate from the crash.)

- [x] select_demo.py - "Submit" doesn't do anything.
      FIXED (no demo change): the handler was always correct - verified headlessly
      that clicking Submit sets `state.status` to the selected values. The "inert"
      symptom was the scrolled-frame mouse hit-test offset (this frame is
      height=38 and scrolls), resolved by the 0.1.0 mouse hit-testing fix.

- [ ] spinner_demo.py - it looks like the last `.` in the ellipses sometimes doesn't get erased on scroll, leading to ghost dots in the same column that scroll
    - turning off clock shows "Working with clock..k" --- probably emoji related?

- [ ] status_indicator_demo.py - would be good to blink after a change, and to allow a blinking state

- [ ] tabbed_panel_demo.py - the welcome pane seems to overlap its border on the left and right? Only the welcome pane, all others are fine

- [ ] textarea_demo.py - we need to be able to show the end of long lines

- [ ] tree_demo.py - the right panel shrinks to the content, intentional?
    - add test node button didn't work
    - the color behind the `>` selector is wrong, making that whole column not respect the proper BG color
    - expand all and collapse all didn't do anything


- [ ] complex_layout_demo.py - why can I edit the log?
      (DEFERRED 0.1.1 - demo/element config: make the LogView/TextArea read-only.)
- [~] context_menu_demo.py - copy and rename don't do anything - intentional?
      PARTIAL: the buttons work (verified - Rename sets `state.status` to
      "Renaming ..."). "Copy" is only reachable via the right-click context menu;
      Rename/Open/Delete also have buttons. The right-click context-menu path is
      the experimental/real-terminal-mouse concern the demo itself flags.
      Context-menu right-click DEFERRED 0.1.1 (needs a real-console repro).
- [x] event_patterns_demo.py - no buttons appear to do anything, nor the keys.
      KEYS FIXED / clarified: keys work (verified - 'h' global, 'v' view-scoped,
      1/2/3 navigation all fire and update state). The Event Log panel was the
      same frozen view-`data` snapshot bug as dialog_showcase - now rendered from
      `state.event_log_text`. The action-button row is laid out below the fixed
      `height=36` frame (~row 50), so it sits off-screen; that off-screen/overflow
      layout item is DEFERRED 0.1.1 (tracked in roadmap.md Viewport section).

- [ ] executor_demo.py -- appears to block, operation log never changes, not working properly.

---

Status of the manually-reported demo bugs, grouped by root cause. Each group is
tagged Fixed / Deferred with a confidence note. The 13 reported items collapse
into 8 root-cause groups (A-H).

## Reported items (original list)

- [x] mouse interaction demo - left/right frame borders not focus-colored
      (group H, deferred)
- [x] autocomplete demo - selecting a suggestion doesn't update the input
      immediately (group F - FIXED 0.1.0: mouse-click select now commits via the
      popup's `on_select` callback; Enter/Tab always worked)
- [x] tree demo - expand-all didn't work; post-expand mouse click failed
      (post-expand click FIXED batch 1 / Windows mouse; expand-all -> group E,
      deferred)
- [ ] layout demo - "features" panel overflows the frame top on scroll; the
      [R][S][H][Q] alt/ctrl hint keys don't work (groups D + G, deferred)
- [x] context menu demo - mouse focus on context menu (FIXED batch 1); "fake
      list element?" + "buttons do wrong thing" (group H, deferred)
- [x] dashboard demo - clicking buttons not working (FIXED batch 1 / Windows mouse)
- [x] data entry demo - buttons not working on mouse click (FIXED batch 1)
- [x] event patterns demo - mouse on buttons (FIXED batch 1); in view2, v/h do
      nothing (group B, FIXED batch 2)
- [x] threadpool executor demo - operations log never updates / appears blocking
      (FIXED earlier - demo passed wrong constructor args)
- [x] form demo - mouse clicks on buttons not working (FIXED batch 1 / Windows
      mouse; the "list swallows click" theory was wrong - the input layer was
      dropping all clicks)
- [ ] frame_overflow_demo - middle frame doesn't extend, rightmost cut off, no
      scroll (groups C + D, deferred)
- [x] horizontal scroll demo - "q" doesn't quit (group B, FIXED batch 2);
      horizontal scrolling only works in the textarea (group C, deferred)
- [x] preferences_demo - can't click buttons with mouse (FIXED batch 1 / Windows
      mouse)

## Root-cause groups

### A. Windows mouse input dropped entirely - FIXED (batch 1, PR #8)

`src/wijjit/terminal/input.py`. On Windows, prompt_toolkit's `Win32Input` emits
`KeyPress(Keys.WindowsMouseEvent, "LEFT;MOUSE_DOWN;x;y")` - a `;`-delimited
string, not a vt100 escape sequence. The handler only recognized vt100 SGR
(`\x1b[<`) and normal (`\x1b[M`) sequences, so every Windows mouse event fell
through to the regular-character branch and was injected as junk. Added
`MouseEventParser.parse_windows()` + `WindowsMouseEvent` handling in both
`InputHandler` read paths, plus a click-synthesis fix for button-less releases.
Verified on a real Windows console. Closed: dashboard, data_entry, form,
preferences (full); the mouse-click portions of event_patterns, context_menu,
tree, mouse-demo. (The headless harness cannot catch this - it injects synthetic
CLICK events and bypasses the input layer.)

### B. Focused text field swallowed global key shortcuts - FIXED (batch 2)

`src/wijjit/core/event_loop.py`. When a `TextInput`/`TextArea` was focused and a
plain char was pressed, `skip_view_handlers_for_input` was set and the dispatch
branch did `pass`, skipping the single `dispatch_async` call that fires *both*
global and view-scoped handlers - so a global `@app.on_key("q")` quit never
fired while a field was focused (horizontal_scroll's "q doesn't quit",
event_patterns view2 "v/h do nothing"). Fix: added an `exclude_scope` parameter
to `HandlerRegistry.dispatch_async` / `_find_matching_handlers` and pass
`HandlerScope.VIEW` when a text input is focused. Global and element handlers
still fire; only view-scoped handlers are suppressed (so typing a char does not
trigger a view hotkey). Regression tests:
`tests/integration/test_modal_key_routing.py::TestFocusedInputKeyScope`.

### C. Horizontal scroll for child-content frames - DEFERRED to 0.1.1

`src/wijjit/layout/frames.py`, `src/wijjit/layout/engine.py`,
`src/wijjit/core/renderer.py`. Deeper than first estimated. A frame's
interpolated body text becomes child `TextElement`s (the child-content path,
`set_child_content_height`), which only ever computes vertical scroll
(`_needs_scroll`); `_content_width` / `_needs_scroll_x` are never set. The
children are also laid out clamped to the frame's inner width
(`content_container.assign_bounds(... inner_width ...)` + the VStack
`min(child_width, content_width)` clamp), so nothing extends horizontally to
scroll over, and the renderer only threads a *vertical* `scroll_offset` through
its recursive child paint (`renderer.py` `y = bounds.y - scroll_offset`; no
horizontal analog). A real fix is a multi-file layout+render feature: lay child
content out at intrinsic width under `overflow_x=scroll/auto`, compute the
horizontal extent, add a child-content horizontal scroll manager, and thread an
`scroll_offset_x` + x-clip through the renderer. Too large/risky for 0.1.0.
Horizontal scroll still works for TextArea (self-scrolling) and for frame *text*
content (`set_content`, which already handles `overflow_x`).

### D. Frame overflow / clip-region - DEFERRED to 0.1.1 (low confidence)

"features panel overflows the frame top on scroll" points at the clip region not
clamping to frame borders (renderer); frame_overflow's "middle doesn't extend /
rightmost cut off" points at HStack width distribution (the demo requests 3x50%
in one row). Needs a focused layout-engine repro before fixing.

### E. Tree "expand all" - DEFERRED to 0.1.1

`src/wijjit/tags/display.py`, `src/wijjit/elements/display/tree.py`,
`src/wijjit/core/wiring.py`. Investigated in depth. Three compounding causes:
(1) the tree tag builds its VNode with `key=id` but never `set_prop("id", id)`,
so the `Tree` element gets `id=None` and therefore no `expand_state_key` -
several other display tags (Table, ProgressBar, Spinner, Modal, Link, ImageView)
have the same `set_prop("id")` omission and should be swept together;
(2) the documented `expanded="<state_key>"` two-way binding is never wired - the
`expanded` prop is dropped at element creation and `_wire_tree` only wires
`on_select`; (3) `expanded_nodes` is ephemeral (preserved across re-renders by
`get/restore_ephemeral_state`), and wiring runs *after* the frame's paint, so an
external "expand all" state write does not reach the painted tree without extra
repaint/dirty plumbing. A spike fixed (1) and the initial-expansion binding but
hit a repaint-ordering problem on live updates; reverted to avoid shipping a
laggy half-fix. Proper fix routes expansion through the reconcile/dirty path (or
marks the tree dirty from wiring) so external writes repaint deterministically.

### F. Autocomplete "doesn't update on select" - FIXED 0.1.0

NOT the same family as group E. Classified with a headless repro: keyboard
Enter/Tab selection always worked (value + state update, popup closes). The
broken path was **mouse-click selection**: `AutocompletePopup.handle_mouse`
moved the highlight and returned `True` "to signal selection should occur", but
nothing consumed that signal - `_apply_selected_suggestion` was only ever
called from `_handle_autocomplete_key` (Enter/Tab). So clicking a suggestion
highlighted it but never committed it to the input. Fixed by giving the popup an
`on_select` callback, wired by the mixin to `self._apply_selected_suggestion`,
invoked from the click branch after setting the highlight. Regression tests:
`tests/autocomplete/test_popup.py::...invokes_on_select` and
`tests/autocomplete/test_integration.py::...mouse_click_applies_suggestion`.
(The caret-not-erased-on-language-toggle visual is a separate paint bug, still
open - see line 27.)

### G. layout demo `[R][S][H][Q]` alt/ctrl keys - DEFERRED to 0.1.1 (Windows)

The demo shows the hints and registers `alt+`/`ctrl+` handlers, but the Windows
alt-key path (`src/wijjit/terminal/input.py`, ESC-timeout lookahead) likely does
not synthesize `alt+` combos on Win32 at all. Real-terminal / platform issue the
harness cannot drive; investigate against a real console, and if it is a
prompt_toolkit/Win32 limitation, document it as a known limitation.

### H. Minor / cosmetic - DEFERRED to 0.1.1

mouse-demo left/right frame border not focus-colored (frame focus-border
rendering); context-menu "buttons do wrong thing" (unresolved). Low priority.

## 0.1.0 disposition

Shipping 0.1.0 with groups A (mouse) and B (global-key) fixed. Groups C-H are
deferred to 0.1.1 with the root causes above; they are demo-level, platform-
specific (Windows input), or architecture-level (layout/render, repaint timing)
issues not suitable for a rushed pre-release fix. See `RELEASE_PLAN.md`.
