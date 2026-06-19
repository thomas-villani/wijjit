- [ ] On mouse interaction demo - left and right borders of frame are not colored with focus color

- [ ] autocomplete demo - some strange issues when selecting suggestion (doesn't update input immediatley)

- [ ] Tree demo - expand all didn't work, and after expanding, mouse click wasn't working

- [ ] layout demo - "features" panel overflows the frame on top during scroll.
    - shows [R], [S], [H], [Q] but those alt/ctrl-keys don't work.


- [ ] context menu demo - why are we using a fake list element? use real list?
    - focus on mouse context menu not working (but keys do)
    - buttons do wrong thing

- [ ] dashboard demo - clicking buttons not working
- [ ] data entry demo - buttons not working on mouse click

- [ ] event patterns demo - in view2, hitting v or h does nothing
    - clicking buttons does nothing

- [ ] threadpool executor demo - operaitons log never updates. everything appears blocking

- [ ] form demo - mouse click on buttons not working - list select  swallows mouse click?

- [ ] frame_overflow_demo.py - seems ok, but middle frame does not extend, and rightmost frame seems cut off and no scroll

- [ ] horizontal scroll demo - horizontal scrolling only works in "textarea with horizontal scroll". also "q" doesn't quit, need to say "Ctrl+q"

- [ ] preferences_demo.py - can't click buttons with mouse (keys ok)

## Investigation

The 13 reported items collapse into 8 root causes. Confidence is noted per
group; a few still need a second repro pass before fixing.

### Confirmed root causes

**A. Windows mouse input is dropped entirely** - `src/wijjit/terminal/input.py`
On Windows, prompt_toolkit's `Win32Input` emits
`KeyPress(Keys.WindowsMouseEvent, "LEFT;MOUSE_DOWN;x;y")` - a `;`-delimited
string, not a vt100 escape sequence. Our handler only recognizes vt100 SGR
(`\x1b[<`, input.py:838) and normal (`\x1b[M`, input.py:859) sequences, and
`WindowsMouseEvent` is not in `PROMPT_TOOLKIT_KEY_MAP` (input.py:226). So every
mouse event on Windows falls through to the "regular character" branch and is
injected as a junk key - all real mouse clicks silently fail on Windows.
Explains: dashboard, data_entry, form, preferences, event_patterns (buttons),
context-menu mouse focus, tree post-expand click, mouse-demo focus. The headless
harness cannot catch this - it injects synthetic CLICK events, bypassing the
input layer entirely.

**B. A focused text field swallows global key shortcuts** - `event_loop.py:549-552`
When a `TextInput`/`TextArea` is focused and a plain char is pressed,
`skip_view_handlers_for_input` is set and the code does `pass`, skipping all
handler dispatch including *global* `@app.on_key` handlers (not just
view-scoped, despite the comment). Explains horizontal_scroll's "q doesn't quit"
and likely event_patterns view2 "v/h do nothing" (manual run had a focused
input). Design tension: if `q` quits globally you cannot type `q` in a field -
the actual over-reach is skipping *global* scope; view-scope skipping is
intended.

**C. Horizontal scroll never enabled for child-content frames** - `frames.py:452`
`set_child_content_height` sets `self.focusable = self._needs_scroll` (vertical
only) and never computes `_needs_scroll_x`, unlike `set_content` (frames.py:409:
`self._needs_scroll or self._needs_scroll_x`). Only `TextArea` (self-scrolling)
works. Explains horizontal_scroll "only works in textarea" and part of
frame_overflow "no scroll".

### Need a second look before fixing

**D. Frame overflow / clip-region (low confidence).** "features panel overflows
the frame top on scroll" points at the clip region not clamping frame borders
(renderer); frame_overflow's "middle doesn't extend / rightmost cut off" points
at HStack width distribution (the demo may request 3x50% in one row). Needs a
layout-engine repro.

**E. Tree "expand all" (medium).** Likely the `expanded` prop is not wired from
state to the element (`wiring.py` `_wire_tree`), so expand-all updates state but
not the rendered tree. Mechanism needs confirming.

**F. Autocomplete "doesn't update on select" (re-investigate).** The popup does
open (suggestions are visible), so the real suspect is the
accept -> writeback -> re-render path, not trigger-key matching. Needs a focused
repro.

**G. layout demo `[R][S][H][Q]` (medium).** Likely the demo shows the hints but
registers no `alt+`/`ctrl+` handlers, and the Windows alt-key path (ESC-timeout
lookahead, input.py:798) may not produce alt combos on Win32 at all.

**H. Minor / demo-correctness (low).** mouse-demo left/right border not
focus-colored (frame focus-border rendering); context-menu "fake list" (appears
to be a real `ListView`; "buttons do wrong thing" unresolved).

### Fix plan (branch-per-batch)

1. **Batch 1 - Group A (Windows mouse).** Biggest win; unblocks ~7 issues. Add a
   `WindowsMouseEvent` translation in input.py (button/event/x/y -> `MouseEvent`,
   routed through the existing press -> release -> click synthesis). Not
   verifiable in the harness - add a unit test for the translation plus a manual
   Windows-console check script.
2. **Batch 2 - Groups B + C** (both confirmed, single-area fixes).
3. **Batch 3+ - D/E/F/G/H** after the deeper repros above.
