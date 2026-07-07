# Release Audit 0.1.0 — Pre-Tag Fix Tracker

Working doc for the final pre-release pass on branch `release-audit-0.1.0`.
Findings from the API/semver, README/docs, and packaging audits. Everything here
is agreed for 0.1.0 unless marked **[0.1.1]**.

Rationale for urgency: PyPI metadata is immutable and public-API shape can't be
renamed/removed after tag without a major/minor bump. Tier 1 items are the ones
that become permanent at tag time; Tier 2 are patch-able but embarrass on day one;
Tier 3 is adoption polish.

## Progress (updated as work lands)

**Done + verified (full suite 3022 pass, ruff/black/mypy --strict all clean):**
- T1.1 dependency floors lowered (rich 13.7.1, pyperclip 1.8.2, tinycss2 1.2.1,
  wcwidth 0.2.5, prompt-toolkit 3.0.36; jinja2 kept at 3.1.6) + pygments declared;
  README dep list updated. Verified: full suite green against the old floors.
- T1.2 `NOTIFICATION_DURATION` wired (sentinel preserves explicit `duration=None`);
  `DEFAULT_ANIMATION_FPS`/`LOG_TO_CONSOLE`/`HTML_CONTENT` dropped from config + docs
  + tests. (`LOG_FORMAT` was already wired — RELEASE_PLAN was stale on that.)
- T1.3 `_RESERVED_NAMES` completed (`data` + all State public methods); raises now
  `StateKeyError`; `state.data = {...}` guarded post-init.
- T1.4 CLI: `run` now launches a `.py` app; new `test` is the pytest passthrough.
- T1.5 fixtures renamed to `wijjit_harness`/`wijjit_make_app` (short aliases kept
  in the repo's own `tests/conftest.py` only, so the shipped surface is clean).
- T1.6 all six charts use `border_style` (attr + kwarg); tag keeps `border` alias.
- T1.8 `render_inline(context=...)` escape hatch added.
- T1.9 `wijjit/exceptions.py` added (`WijjitError` + `StateKeyError`/`ConfigError`/
  `KeyBindingError`/`TemplateError`, back-compat via builtin multi-inherit); wired
  into State/Config/on_key; `render_inline` wraps jinja2 errors as `TemplateError`;
  exported from top-level.
- T1.10 `__all__` trimmed (`HandlerRegistry`/`Handler`/`InputHandler`/`ScreenManager`/
  `ElementType` dropped; still importable from submodules).
- T1.11 pytest plugin defers heavy imports into fixture bodies.
- T1.12 password masking on TextInput (`password=`/`mask_char=`); README + login demo
  updated; regression tests added.
- Tier 2 doc fixes: README AlertDialog `on_close`→`on_ok`; README + examples/README
  phantom demos removed and missing demos added (all refs now resolve); example count
  unified to 72 across README + docs; `components.rst` phantom ref fixed.

**T1.7 dead constructor params — resolved:**
- `Select.item_renderer` — removed (truly dead, un-templatable, test removed).
- `NotificationElement(action_label=, max_width=)` — kept (audit was wrong; both read).
- `Checkbox.value` — removed from element + `checkbox` tag + test (per decision).
- `Spinner/LineChart/Sparkline.color` — WIRED (per decision): `color` now tints the
  glyph/line on top of the theme style, via `parse_color` + `Style.merge`. Accepts
  named/hex/rgb(). Regression tests added; the spinner demo now renders in color.

**Tier 3 polish — done:**
- Screenshot pipeline committed as `scripts/make_screenshots.py` (headless, in-process,
  deterministic); four SVGs written to `docs/assets/screenshots/` and re-rendered
  after the color/masking fixes (login now shows a masked password).
- README reworked for flow: hero screenshot, "Why Wijjit?" section (Rich/Textual
  positioning), tightened features, a screenshot gallery, and the big attribute
  tables (HStack/SplitPanel/Pager/Sizing) + exhaustive component/example lists
  replaced with concise prose + links to the Sphinx docs. ~975 -> 821 lines.
- GitHub Pages: enabled by the user.

**Caveat flagged:** README images use absolute `raw.githubusercontent.com` SVG URLs.
These render on GitHub. If the PyPI project page doesn't render an SVG `<img>`,
rasterize to PNG (no rasterizer is installed here — cairosvg/playwright absent).

**Tag-time only:** CHANGELOG `[0.1.0]` date bump (owner will handle).

---

## Tier 1 — must land before the immutable tag

### T1.1 Lower dependency floors  ✅ decided
Current floors are dev-time resolver artifacts, not real requirements.
**Verified:** full suite (3009 passed, 31 skipped) is green against the old set
below on Windows. Lower `pyproject.toml` `[project].dependencies` to:
- [ ] `rich>=13.7.1`  (was `>=14.2.0` — the critical one; 14.x floor blocks co-install with rich 13.x pins)
- [ ] `pyperclip>=1.8.2`  (was `>=1.11.0`)
- [ ] `tinycss2>=1.2.1`  (was `>=1.5.0`)
- [ ] `wcwidth>=0.2.5`  (was `>=0.2.14`)
- [x] `jinja2>=3.1.6`  — **keep** (security-patch floor; negligible adoption cost). No change.
- [ ] `prompt-toolkit>=3.0.36`  (was `>=3.0.52`)
- [ ] **Add `pygments` as a declared dependency** — imported unguarded in
      `src/wijjit/elements/input/code_editor.py:20`, currently only transitive via rich.
- [ ] Update the README dependency list (README.md:894-909) to match.
- [ ] (nice-to-have) add a "lowest deps" CI job pinning the floors so this can't regress.

### T1.2 Dead config keys  ✅ decided
- [ ] **Wire** `NOTIFICATION_DURATION` — `notify()` should default `duration=None`
      and fall back to the config value (`core/app.py:1880`, key at `config.py:399`).
- [ ] **Drop** `DEFAULT_ANIMATION_FPS` (`config.py:376`), `LOG_TO_CONSOLE` (`config.py:424`),
      `HTML_CONTENT` (`config.py:479`) from `DefaultConfig` — debug/deprecated leftovers.
- [ ] Remove their doc entries (`docs/source/user_guide/configuration.rst`).

### T1.3 Complete `State._RESERVED_NAMES`  ✅ decided
- [ ] Add `data` + all of State's public method names (`watch`, `unwatch`, `on_change`,
      `off_change`, `reset`, `batch_update`, `async_batch_update`, `set_async`,
      `flush_pending_async`) to `_RESERVED_NAMES` (`core/state.py:59-71`).
      **Verified gap:** `state['data']=5` accepted but `state.data` returns the dict;
      `state['watch']='hi'` accepted but `state.watch` returns the bound method.
- [ ] Make the `name == "data"` branch of `__setattr__` internal-only (or document it).

### T1.4 CLI verbs  ✅ decided
- [ ] `wijjit run` → **run a wijjit app** (align with validate/tree/render taking app files).
- [ ] Add `wijjit test` as the pytest passthrough (current `run` behavior).
- [ ] Update CLAUDE.md + README CLI section + docs to match. (`src/wijjit/cli.py:169-197`)

### T1.5 pytest fixture names  ✅ decided
- [ ] Rename `harness` → `wijjit_harness` (avoid shadowing common user fixture).
- [ ] Rename `make_app` → `wijjit_make_app` (avoid collision with the `wijjit_app` marker).
- [ ] Update all in-repo tests, README testing section, docs. (`testing/pytest_plugin.py:47-105`)

### T1.6 Chart `border` → `border_style`  ✅ decided
Charts were missed in the earlier border-unification pass.
- [ ] Rename the constructor param `border` → `border_style` on all six chart classes:
      `barchart.py:125`, `columnchart.py:116`, `gauge.py:124`, `heatmap.py:110`,
      `linechart.py:108`, `sparkline.py:96`. Keep the tag-layer alias so templates are unaffected.
- [ ] Normalize the `"none"` string vs `None` sentinel while here.

### T1.7 Remove dead constructor params  — partially done; rest NEEDS DECISION
- [x] `Select.item_renderer` — REMOVED. Confirmed dead (both render branches were
      identical; never actually invoked), not template-expressible, test removed.
- [x] `NotificationElement(action_label=, max_width=)` — **KEPT.** Audit was wrong:
      both are read (they build the action button and size the toast). Not dead.
- [ ] `Checkbox(value=)` — DECISION NEEDED. Write-only in the element, BUT the
      `checkbox` tag forwards it (`tags/input.py:728 set_prop("value", ...)`), so it's
      a template-facing incomplete feature (HTML-checkbox-analogous), not internal
      dead code. Standalone checkboxes bind by id to booleans; `value` only matters
      for grouping (which CheckboxGroup handles separately). Options: (a) remove from
      element + tag, (b) leave as documented-reserved, (c) wire it.
- [ ] `Spinner(color=)` / `LineChart(color=)` / `Sparkline(color=)` — DECISION NEEDED.
      Write-only, but forwarded by the tags (`color="cyan"`) and used across demos
      (spinner_demo labels four colored spinners). Removing silently makes those demos
      render uncolored. Options: (a) wire color (best product outcome, small feature),
      (b) remove the whole color chain incl. tags + demo usages, (c) leave reserved.

### T1.8 `render_inline` kwarg-collision escape hatch  ✅ decided
- [ ] Add optional `context: dict` param to `render_inline` (`inline/render.py:20-29`);
      when present it supplies template vars so `width`/`height`/`file`/`print_output`/
      `template_dir` names stop being stolen from `**context`. Document the reserved names.

### T1.9 Add `wijjit/exceptions.py`  ✅ decided
- [ ] `WijjitError(Exception)` base; `StateKeyError(WijjitError, ValueError)`,
      `TemplateError(WijjitError)`, `ConfigError(WijjitError, RuntimeError)`.
      Multi-inherit the builtin currently raised so existing `except ValueError` still catches.
- [ ] Wrap leaked `jinja2.TemplateSyntaxError`/`UndefinedError` at the render boundary
      (`render_inline`, view rendering) in `TemplateError`.
- [ ] Route existing raises: `State.__setitem__` (state.py:156), `app.on_key` (app.py:867),
      `Config.from_envvar` (config.py:192), harness startup (harness.py:680).
- [ ] Export the exception types from top-level `wijjit`.

### T1.10 Trim `__all__` internal leaks  ✅ decided
- [ ] Drop `HandlerRegistry`, `Handler`, `InputHandler`, `ScreenManager`, `ElementType`
      from top-level `__all__` (`__init__.py:143-260`). Still importable from submodules.
      Keep `Renderer`/`FocusManager` (documented `app.*` attrs).

### T1.11 pytest plugin import weight  ✅ decided
- [ ] Defer `wijjit.core.app` / `harness` / `app_builder` imports into the fixture
      bodies (`testing/pytest_plugin.py`); module level imports only `pytest`.
      Use `TYPE_CHECKING` + string annotations for hints. (~3s off every unrelated pytest run.)

---

### T1.12 Password masking  ✅ decided (new feature for 0.1.0)
The flagship login example echoes cleartext; no masking exists anywhere.
- [ ] Add a `password` (bool) prop to `TextInput`: state/value stays real, but the
      rendered display substitutes a mask glyph. Cursor/editing operate on the real value.
- [ ] Thread the prop through the `textinput` tag (already forwards `**kwargs`) and
      the reconciler prop-sync (it's a display prop, not ephemeral).
- [ ] Update the README login example to use `password=True` on the password field.
- [ ] Tests: harness assert that the screen shows the mask, not the typed value.

---

## Tier 2 — public-doc correctness (patch-able, but wrong on day one)

- [ ] **README AlertDialog snippet crashes** — `on_close` → `on_ok` (README.md:465-470).
      **Verified:** `AlertDialog(on_close=...)` raises TypeError; real params are
      `message, on_ok, title, ...`. (`on_close` belongs to `app.show_modal(el, on_close=)`.)
- [ ] README phantom examples: `rich_content_demo.py` (README.md:668),
      `rich_content_template_demo.py` (README.md:670) — don't exist; replace with real ones.
- [ ] `examples/README.md`: remove 6 phantom entries (`tree_indicator_styles_demo.py`,
      `markdown_demo.py`, `code_demo.py`, `test_markdown_tag.py`, `rich_content_demo.py`,
      `rich_content_template_demo.py`); add ~15 missing real demos (charts, contentview,
      imageview, tabbedpanel, code_editor, autocomplete, config, grid, hstack_flexbox,
      theme_config, suspend, inline_*, horizontal_scroll).
- [ ] Unify example count to **72** everywhere (basic 15 / widgets 30 / advanced 22
      incl. nested `templates_dir_demo` / styling 2 / apps 3). Fix docs saying 69/71:
      `docs/source/index.rst:13`, `getting_started/quickstart.rst:312`, `examples/index.rst:4`.
- [ ] `docs/source/user_guide/components.rst:261` references nonexistent
      `tree_indicator_styles_demo.py` — fix.
- [ ] CHANGELOG `[0.1.0]` date `2026-06-28` → actual tag date (at tag time).

---

## Tier 3 — adoption polish

- [ ] **Screenshots.** Headless→SVG pipeline built and validated; commit it as
      `scripts/make_screenshots.py`. Embed 2-3 in README via absolute
      `raw.githubusercontent.com` URLs (render on PyPI too). Best shots: charts_demo, todo_app.
      (dashboard_demo excluded — frame-overflow paints past the border at wide widths.)
- [ ] **"Why not Textual?" positioning section** in README — port the "why wijjit" list
      from `docs/source/index.rst`. Rich = output-only; Textual = OO widgets + CSS;
      wijjit = Jinja templates + Flask decorators.
- [ ] Trim the README top: tagline → screenshot → 6 features → install → hello-world →
      login → links in the first ~150 lines; push attribute tables into Sphinx.
- [ ] Surface the CLI (`validate`/`tree`/`render`) + pytest `harness` in the Features list.
- [ ] **[user action]** Enable GitHub Pages + verify the site before publish, or the
      Documentation badge/URL 404s on day one.

---

## Noted / deferred to 0.1.1 (not tag-blocking)

- **Password masking does not exist** anywhere in the framework — the README's flagship
  login example echoes cleartext. Additive (`password=True` on TextInput), so not a
  semver trap, but a visible gap. Decide: add minimal masking for 0.1.0, or de-emphasize
  the password in the example. *(pending your call)*
- Scripted typing doesn't reach the chatbot demo's input under the headless harness
  (focus/autofocus quirk) — investigate.
- Everything already in RELEASE_PLAN.md Part 2 (wide-char buffer, reconciler ephemeral
  state, frame-overflow clip, etc.) stays deferred.

---

## Lower-priority semver notes (fix opportunistically, else document)

From the API audit "ACCEPTABLE" tier — free to fix pre-tag, awkward after:
- Make params after the first keyword-only on `Wijjit.__init__` and `WijjitHarness.__init__`.
- Unify state-init kwarg name (`initial_state` vs `app_from_template(state=)` vs `State(data=)`).
- `Wijjit(**config_overrides)` silently uppercases typo'd kwargs into config keys.
- Two classes named `MouseEvent` (core wrapper vs terminal); the core one isn't exported
  though it's what MOUSE handlers receive.
- `vstack` only supports `spacing` while `hstack` calls `spacing` "legacy" — align docs.
- `harness.py:624` sets `UNICODE_SUPPORT = True` (invalid for the `auto/force/disable`
  contract, and set post-`__init__` so it no-ops) — patch-fixable bug, not semver.
