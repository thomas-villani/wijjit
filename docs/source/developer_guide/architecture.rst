Architecture
============

This chapter explains how Wijjit is organized under the hood so contributors can reason about changes confidently. Each subsection calls out the major modules involved and the responsibilities they own.

Runtime overview
----------------

High-level flow:

:: 

    ┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
    │  Templates (Jinja) │────▶ │ Layout Engine      │────▶ │ Rendering Pipeline │
    └────────┬───────────┘      └────────┬───────────┘      └────────┬───────────┘
             │                           │                           │
             │   state / data context    │   bounds & elements       │  ANSI cells
             ▼                           ▼                           ▼
        ┌──────────┐               ┌──────────┐               ┌────────────────┐
        │  Wijjit  │◀──────────────│ Event    │◀──────────────│ Terminal (PTK) │
        │  core    │  actions/keys │ Loop     │  input events │ Screen/Mouse   │
        └──────────┘               └──────────┘               └────────────────┘

1. **App construction** – :class:`wijjit.core.app.Wijjit` wires together the renderer, layout engine, state, event registry, overlay manager, focus/hover managers, mouse router, notification manager, and terminal adapters. Arguments such as ``template_dir`` and ``initial_state`` are stored on the instance.
2. **View registration** – ``@app.view`` stores lazy :class:`wijjit.core.view_router.ViewConfig` objects inside :class:`wijjit.core.view_router.ViewRouter`. A view returns a :class:`wijjit.core.templating.RenderedView` (via :func:`wijjit.render_template_string` / :func:`wijjit.render_template`) carrying an inline template or a ``template_file`` plus its context; lifecycle hooks are declared on the decorator. Synchronous views are re-invoked every render so derived context stays live.
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
2. **VNode tree** – tags such as ``{% vstack %}``, ``{% frame %}``, and ``{% button %}`` do **not** build elements directly; they emit immutable :class:`wijjit.core.vdom.VNode` descriptions via a ``VNodeBuilder``. The template render therefore produces a VNode tree, not an element tree.
3. **Reconcile** – :class:`wijjit.core.reconciler.Reconciler` diffs the new VNode tree against the previous one and creates/updates/replaces/deletes the corresponding stateful :class:`wijjit.elements.base.Element` objects, reusing existing elements (and their ephemeral UI state) where possible. The reconciler also wires the resulting elements into the layout tree (``wijjit.layout.engine``).
4. **Constraint pass** – :meth:`wijjit.layout.engine.LayoutNode.calculate_constraints` recursively computes minimum/preferred sizes based on element content and width/height specs. Scrollable frames consult ``wijjit.layout.scroll`` to measure overflow.
5. **Assign bounds** – ``assign_bounds`` walks top-down assigning concrete ``Bounds`` rectangles, respecting padding/margin/spacing rules.
6. **Painting** – each element’s ``render_to`` writes to :class:`wijjit.rendering.paint_context.PaintContext`, which wraps a :class:`wijjit.terminal.screen_buffer.ScreenBuffer`. Styles are resolved via :class:`wijjit.styling.resolver.StyleResolver`.
7. **Terminal flush** – :class:`wijjit.terminal.screen.ScreenManager` diffs the buffer against the previous frame and writes ANSI commands to the alternate screen for flicker-free updates.

Virtual DOM & Reconciliation
----------------------------

Wijjit uses a React-style Virtual DOM for efficient UI updates. This system lives in :mod:`wijjit.core.vdom` and :mod:`wijjit.core.reconciler`.

**VNode** (:class:`wijjit.core.vdom.VNode`)

Immutable description of what the UI should look like:

* ``type`` – Element type name (e.g., "TextInput", "Button", "VStack")
* ``key`` – Stable identity for list reconciliation
* ``props`` – Immutable properties tuple
* ``children`` – Child VNodes
* ``layout_spec`` – Layout configuration (width, height, margin, etc.)

VNodes are frozen dataclasses, ensuring reliable comparison during diffing.

**VNodeBuilder** (:class:`wijjit.core.vdom.VNodeBuilder`)

Mutable builder used during template execution. Template tags call methods like ``add_child()`` and ``set_prop()``. At the end of rendering, call ``freeze()`` to convert to an immutable VNode tree.

**Reconciler** (:class:`wijjit.core.reconciler.Reconciler`)

Compares old and new VNode trees and efficiently updates the Element tree:

1. **Diff phase** – Compares trees, produces :class:`DiffResult` with changes
2. **Patch phase** – Creates/updates/deletes elements based on diff
3. **Ephemeral state preservation** – Cursor, scroll, selection state survives re-renders

Diff types (:class:`wijjit.core.reconciler.DiffType`):

* ``CREATE`` – New element needed
* ``DELETE`` – Element removed
* ``UPDATE`` – Props changed, reuse element
* ``REPLACE`` – Type changed, recreate element

Key-based reconciliation matches elements by ``key`` prop for stable identity in lists. Elements with matching keys are considered the "same" and will be updated rather than replaced.

Thread-safe RenderContext
-------------------------

:class:`wijjit.core.render_context.RenderContext` provides thread-safe, reentrant state management during template processing. It replaces the previous pattern of storing state in Jinja2's ``environment.globals``, which was not thread-safe.

The context holds:

* ``layout_context`` – LayoutContext for building VNode trees
* ``template_context`` – Template variables including 'state'
* ``focused_id`` – Currently focused element ID
* ``radiogroup_stack`` / ``menu_stack`` – For nested component building
* ``frame_counter`` – Auto-increment counter for generating frame IDs
* ``overlays`` – Overlay info for dialogs/menus
* ``statusbar`` – StatusBar element if present

Usage in template extensions::

    from wijjit.core.render_context import get_render_context

    def _render_button(self, ...):
        ctx = get_render_context()
        layout_ctx = ctx.layout_context
        focused_id = ctx.focused_id
        # ...

The renderer uses ``render_context_scope()`` context manager to establish the context:

.. code-block:: python

    with render_context_scope(layout_context, template_context) as ctx:
        output = template.render(**template_context)

The context uses Python's ``contextvars`` module for thread safety and reentrancy.

Ephemeral State Pattern
-----------------------

Elements preserve transient UI state across re-renders using the ephemeral state pattern. This is critical for maintaining cursor position, scroll offset, and selection state when templates re-execute.

**Protected props** (defined in ``wijjit.core.vdom.EPHEMERAL_PROPS``):

* Cursor state: ``cursor_pos``, ``cursor_row``, ``cursor_col``
* Selection state: ``selection_anchor``, ``selection_start``, ``selection_end``
* Scroll state: ``scroll_position``, ``scroll_x_position``
* UI interaction: ``highlighted_index``, ``focused``, ``hovered``

These props are excluded from template-to-element syncing during reconciliation.

**Implementation:**

Elements implement two methods to participate in ephemeral state preservation:

.. code-block:: python

    class MyElement(Element):
        def get_ephemeral_state(self) -> dict:
            """Return state that should survive re-renders."""
            return {
                "cursor_pos": self.cursor_pos,
                "scroll_position": self.scroll_position,
            }

        def restore_ephemeral_state(self, state: dict) -> None:
            """Restore state after reconciliation."""
            if "cursor_pos" in state:
                self.cursor_pos = state["cursor_pos"]
            if "scroll_position" in state:
                self.scroll_position = state["scroll_position"]

Elements that implement these methods include: TextInput, TextArea, Menu, Tree, TabbedPanel, and all scrollable elements.

Clip Region System
------------------

Nested frames require proper clipping to prevent content from rendering outside boundaries. The :class:`wijjit.rendering.paint_context.PaintContext` manages clip regions.

When rendering nested content::

    # Create sub-context with clipped bounds
    inner_ctx = ctx.sub_context(x, y, width, height)
    # All writes to inner_ctx are clipped to the sub-region
    child_element.render_to(inner_ctx)

The ``sub_context()`` method:

1. Creates a new PaintContext with adjusted bounds
2. Inherits the style resolver and screen buffer
3. Applies accumulated scroll offsets from parent frames
4. Clips any writes that fall outside the region

The renderer uses ``clip_region`` during frame rendering to ensure scrollable content doesn't overflow borders. Nested frames accumulate their offsets, so deeply nested scrollable content is correctly clipped to all ancestor frames.

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

* **New elements** – subclass :class:`wijjit.elements.base.Element` or ``ScrollableElement``. Implement ``render_to``, ``get_intrinsic_size``, and optional ``handle_key`` / ``handle_mouse``. Expose the element via a new tag in ``wijjit.tags`` for templated usage.
* **Themes** – add entries to the styles dict of :class:`wijjit.styling.theme.Theme`, keyed by element style class (e.g. ``button``, ``button.label``). Elements resolve their style by calling ``ctx.style_resolver.resolve_style(self, "<base_class>")`` inside ``render_to``. Register a theme at runtime via ``app.renderer.theme_manager.register_theme(theme)`` and activate it with ``app.renderer.theme_manager.set_theme(theme.name)``.
* **View helpers** – store shared macros or template fragments in ``templates/`` or ``docs/examples`` and load them with ``template_file``.
* **Background tasks** – use ``asyncio.create_task`` for async work, or set ``app.config["RUN_SYNC_IN_EXECUTOR"] = True`` (with optional ``app.config["EXECUTOR_MAX_WORKERS"]``) so blocking sync handlers run on a ``ThreadPoolExecutor`` and keep the UI responsive.

Use this architecture map as a starting point before touching multiple subsystems. When in doubt:

1. Locate the subsystem under ``src/wijjit``.
2. Read the relevant docstring/tests (the test suite mirrors the runtime tree).
3. Update the accompanying documentation so future contributors inherit accurate context.
