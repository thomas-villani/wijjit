# Demo bug tracker

Status of the manually-reported demo bugs, grouped by root cause. Each group is
tagged Fixed / Deferred with a confidence note. The 13 reported items collapse
into 8 root-cause groups (A-H).

## Reported items (original list)

- [x] mouse interaction demo - left/right frame borders not focus-colored
      (group H, deferred)
- [ ] autocomplete demo - selecting a suggestion doesn't update the input
      immediately (group F, deferred)
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

### F. Autocomplete "doesn't update on select" - DEFERRED to 0.1.1

The popup opens (suggestions visible), so the suspect is the accept -> writeback
-> re-render path (same repaint-timing family as group E), not trigger-key
matching. Needs a focused repro in `autocomplete/mixin.py` + `state.py`. Note:
the 7-item autocomplete implementation review is separately resolved; this is the
remaining demo-level symptom.

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
