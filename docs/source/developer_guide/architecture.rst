Architecture
============

This chapter explains how Wijjit is organized under the hood so contributors can reason about changes confidently. Each subsection calls out the major modules involved and the responsibilities they own.

Runtime overview
----------------

High-level flow:

:: 

    ┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
    │  Templates (Jinja) │────▶ │ Layout Engine      │────▶ │ Rendering Pipeline │
    └────────┬───────────┘      └────────┬──────────┘      └────────┬──────────┘
             │                            │                           │
             │   state / data context     │   bounds & elements        │  ANSI cells
             ▼                            ▼                           ▼
        ┌──────────┐               ┌──────────┐               ┌────────────────┐
        │  Wijjit  │◀──────────────│ Event    │◀──────────────│ Terminal (PTK) │
        │  core    │  actions/keys │ Loop     │  input events │ Screen/Mouse   │
        └──────────┘               └──────────┘               └────────────────┘

1. **App construction** – :class:`wijjit.core.app.Wijjit` wires together the renderer, layout engine, state, event registry, overlay manager, focus/hover managers, mouse router, notification manager, and terminal adapters. Arguments such as ``template_dir`` and ``initial_state`` are stored on the instance.
2. **View registration** – ``@app.view`` stores lazy :class:`wijjit.core.view_router.ViewConfig` objects inside :class:`wijjit.core.view_router.ViewRouter`. Each view returns ``template``/``template_file`` plus optional ``data`` callbacks and lifecycle hooks.
3. **Event loop** – ``app.run()`` delegates to :class:`wijjit.core.event_loop.EventLoop` which switches to the alternate screen, hides the cursor, enables mouse mode, renders the default view, and enters the main async loop.
4. **Frame processing** – every iteration reads input (keyboard/mouse), dispatches events via :class:`wijjit.core.events.HandlerRegistry`, updates notifications/overlays, and triggers a render if ``app.needs_render`` or the dirty region manager requests it.
5. **Shutdown** – when ``app.quit()`` or ``Ctrl+C`` fires, the loop unwinds: overlays close, handlers are cleared, the cursor is restored, and the screen buffer exits alternate mode.

Module map
----------

The ``src/wijjit`` tree is intentionally segmented:

* ``core/`` – orchestration (app, event loop, events, state, focus, hover, mouse router, overlay manager, notification manager, wiring).
* ``layout/`` – size math and container primitives (bounds, engine, frames, scroll, dirty tracking).
* ``elements/`` – UI widgets. ``base.py`` defines :class:`Element`; subpackages ``input/`` and ``display/`` implement concrete components plus modals/menus.
* ``tags/`` – Jinja extensions mapping template tags to element/layout nodes.
* ``rendering/`` – paint context and ANSI adapters bridging Rich / prompt-toolkit.
* ``terminal/`` – input handling, screen buffer, ANSI utilities.
* ``styling/`` – theme + style resolver.
* ``helpers.py`` – misc utilities shared across modules.

Renderer & layout pipeline
--------------------------

1. **Template render** – :class:`wijjit.core.renderer.Renderer` configures a Jinja environment with the custom tags from ``wijjit.tags``. Views call ``Renderer.render_view`` which passes ``state``, ``data``, and ``params`` to the template.
2. **Layout tree** – tags such as ``{% vstack %}``, ``{% frame %}``, and ``{% button %}`` instantiate layout nodes (``wijjit.layout.engine``) and elements (``wijjit.elements``). A ``LayoutContext`` builds the tree as tags execute.
3. **Constraint pass** – :class:`wijjit.layout.engine.LayoutNode.calculate_constraints`` recursively computes minimum/preferred sizes based on element content and width/height specs. Scrollable frames consult ``wijjit.layout.scroll`` to measure overflow.
4. **Assign bounds** – ``assign_bounds`` walks top-down assigning concrete ``Bounds`` rectangles, respecting padding/margin/spacing rules.
5. **Painting** – each element’s ``render_to`` writes to :class:`wijjit.rendering.paint_context.PaintContext`, which wraps a :class:`wijjit.terminal.screen_buffer.ScreenBuffer`. Styles are resolved via :class:`wijjit.styling.resolver.StyleResolver`.
6. **Terminal flush** – :class:`wijjit.terminal.screen.ScreenManager`` diffs the buffer against the previous frame and writes ANSI commands to the alternate screen for flicker-free updates.

Event system
------------

* **Input layer** – :class:`wijjit.terminal.input.InputHandler` captures keys and mouse events from prompt-toolkit. Mouse events are wrapped in :class:`wijjit.terminal.mouse.MouseEvent`.
* **Event types** – defined in :mod:`wijjit.core.events`: ``KeyEvent``, ``ActionEvent``, ``ChangeEvent``, ``FocusEvent``, ``MouseEvent``. Each has metadata (key, modifiers, element id, etc.).
* **Handler registry** – :class:`HandlerRegistry`` stores ``Handler`` objects tagged with ``HandlerScope`` (GLOBAL / VIEW / ELEMENT), optional view/element ids, and priority. ``dispatch`` looks up matching handlers, runs sync callbacks, and awaits async ones.
* **Convenience decorators** – ``@app.on_action``, ``@app.on_key`` wrap ``HandlerRegistry.register``. Internally they set ``scope=VIEW`` by default so handlers automatically clear during navigation.
* **Mouse routing** – :class:`wijjit.core.mouse_router.MouseEventRouter` performs hit-testing (overlays first, then base layout), updates :class:`wijjit.core.hover.HoverManager`, and forwards events to elements with ``handle_mouse`` methods.
* **Focus management** – :class:`wijjit.core.focus.FocusManager`` tracks focusable elements, handles Tab/Shift+Tab, and marks dirty regions when focus changes. Overlays can trap focus and restore the previous state upon closing.

State & wiring
--------------

* **Reactive state** – :class:`wijjit.core.state.State`` extends ``UserDict`` with change detection, attribute access, global and per-key watchers, and async callback support. ``Wijjit`` registers ``state.on_change`` to set ``app.needs_render`` when any key changes.
* **Element wiring** – :class:`wijjit.core.wiring.ElementWiringManager`` binds template-generated elements (forms, lists) to state keys/actions by id. For example, ``{% textinput id="username" %}`` automatically syncs ``state["username"]`` and emits ``ChangeEvent`` when edits occur.
* **Notifications** – :class:`wijjit.core.notification_manager.NotificationManager`` leverages overlays to display toast-like alerts, auto-expiring them with the help of the event loop’s periodic checks.

Overlays & modals
-----------------

* :class:`wijjit.core.overlay.OverlayManager`` manages stacked overlays grouped by :class:`LayerType`` (BASE / MODAL / DROPDOWN / TOOLTIP). Each overlay stores focus state, z-index, and dismissal behavior.
* Template tags in ``wijjit.tags.dialogs`` and ``wijjit.tags.menu`` emit overlay descriptors (confirm dialogs, alerts, dropdown menus, context menus). During rendering the overlay manager instantiates the appropriate elements and pushes them with ``trap_focus`` or ``dimmed_background`` as needed.
* Mouse clicks and keyboard events route through overlays before reaching the base layout, ensuring modals behave like first-class screens.

Terminal adapters
-----------------

* **ANSI utilities** – ``wijjit.terminal.ansi`` provides color helpers, cursor movement, and width-aware string functions (``visible_length``, ``wrap_text``).
* **Screen management** – ``wijjit.terminal.screen.ScreenManager`` toggles alternate-screen mode, hides/shows the cursor, and flushes buffers.
* **Cells & buffers** – ``wijjit.terminal.cell.Cell`` and ``wijjit.terminal.screen_buffer.ScreenBuffer`` represent styled characters; the paint context writes to these objects instead of printing directly.

Extending Wijjit
----------------

* **New elements** – subclass :class:`wijjit.elements.base.Element`` or ``ScrollableElement``. Implement ``render_to``, ``get_intrinsic_size``, and optional ``handle_key`` / ``handle_mouse``. Expose the element via a new tag in ``wijjit.tags`` for templated usage.
* **Themes** – add entries to :class:`wijjit.styling.theme.Theme`` and expose selectors through ``get_style_classes`` on elements. Users can swap themes at runtime via ``app.renderer.set_theme``.
* **View helpers** – store shared macros or template fragments in ``templates/`` or ``docs/examples`` and load them with ``template_file``.
* **Background tasks** – use ``asyncio.create_task`` or configure ``EventLoop`` with a ``ThreadPoolExecutor`` via ``app.configure`` to keep the UI responsive while running long operations.

Use this architecture map as a starting point before touching multiple subsystems. When in doubt:

1. Locate the subsystem under ``src/wijjit``.
2. Read the relevant docstring/tests (the test suite mirrors the runtime tree).
3. Update the accompanying documentation so future contributors inherit accurate context.
