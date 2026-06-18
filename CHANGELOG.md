# Changelog

All notable changes to Wijjit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Targeting the first public release, `0.1.0`. See `RELEASE_PLAN.md` for the
remaining work.

### Added
- Right-aligned (and centered) **table columns** via a per-column `align` key
  (`{"key": "amount", "align": "right"}`).
- Horizontal **text alignment** for the `{% text %}` tag (`align="left"`,
  `"center"`, `"right"`), plus `width`/`height` attributes so alignment has
  room to take effect.
- **Autosizing `TextArea`**: `autosize=True` grows the height to fit the
  content up to an optional `max_height` (rows), then scrolls.
- **Bind keys to focus**: `app.bind_focus_key(key, element_id)` plus
  `app.get_element_by_id()` / `app.focus_element_by_id()` for jumping focus to
  a named element from a keyboard shortcut.
- **Nested item tags** for list-like elements: `{% selectitem %}` (inside
  `{% select %}`) and `{% treeitem %}` (inside `{% tree %}`, supports nesting),
  mirroring the existing `{% menuitem %}` pattern.
- Public API surface re-exported from the top-level `wijjit` package
  (`State`, event types, `Frame`, ANSI helpers, terminal/input utilities, etc.).
- Inline rendering: `render_inline()` and `InlineApp` for non-alternate-screen output.
- Autocomplete / suggestion dropdown support for text inputs and `CodeEditor`.
- Data display elements: bar/line/column charts, sparkline, heatmap, gauge.
- New elements: `Slider`, `Toggle`, `CodeEditor`, `TabbedPanel`, `ContentView`,
  `StatusIndicator`, `Link`, `ImageView`, `DataGrid`, `Pager`.
- `SplitPanel` resizable split layout and HStack flexbox (justify/wrap/gap).
- Multi-select for `Select` and `Tree`.
- VNode + reconciler rendering pipeline (`vdom`, `reconciler`, `element_registry`).
- CSS-based theming (`tinycss2`) and `content_type` rendering
  (text / ansi / html / markdown / rich) in display elements.
- Ctrl+Z suspend/resume (SIGTSTP) on Unix.
- Flask-style configuration system (`app.config`).

### Fixed
- `Select` now re-clamps scroll position when its option list changes.
- Pending async tasks spawned from state callbacks are cancelled on shutdown,
  preventing task leaks and exit hangs.

### Changed
- **Inner-text discipline**: `{% textinput %}` now uses its tag body as the
  initial value when no `value=` is given, and `{% button %}` / `{% menuitem %}`
  accept a `label=` attribute as an alternative to the body (the attribute wins
  when both are present). Consistent with the existing checkbox/radio/textarea
  behavior.
- Hoisted a number of standard-library imports from function bodies up to
  module level (code hygiene; no behavior change).
- Version is now sourced from `wijjit.__version__` (single source of truth).

[Unreleased]: https://github.com/thomas-villani/wijjit/commits/main
