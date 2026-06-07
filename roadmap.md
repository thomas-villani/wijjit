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

### Phase 5 (after the items above)

Bump to ``0.1.0``, set up Trusted Publishing via GitHub Actions, ``uv build``,
``twine check``, publish to TestPyPI, then PyPI. See ``RELEASE_PLAN.md``.

## 0.1.x point releases

Real features, but not blockers — ship as additive minor versions after 0.1.0.

- [ ] **Inline span element** for styling fragments of text.
- [ ] **Right-align text and table columns.**
- [ ] **Dynamic API for collection updates** — uniform programmatic way to
  add/remove/update items in ``ListView``, ``Menu``, ``Tree``, ``Select``.
- [ ] **Autosizing TextArea** — expand to content size up to a configurable
  max.
- [ ] **Bind keys to focus** — keyboard shortcut that jumps focus to a named
  frame or element.
- [ ] **Full-screen a panel/element** — temporarily expand any container to
  fill the screen.
- [ ] **Selectable text** — enable text selection / copy in display elements.
- [ ] **Move local imports** — code hygiene; hoist imports currently inside
  function bodies.
- [ ] **Define menuitems / select items / tree items via tags** — make sure
  every list-like element supports both template tags and dynamic population.
- [ ] **Inner-text discipline** — audit elements that should accept inner
  text in templates (Frame, TextArea, Markdown, Code, Button, etc.) and make
  the behavior consistent.

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
