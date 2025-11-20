Core Concepts
=============

This chapter introduces the moving pieces that make Wijjit feel like “Flask for the console”. Once you understand how the application lifecycle, views, state, rendering, and events cooperate, the rest of the docs become much easier to navigate.

Application lifecycle
---------------------

The :class:`wijjit.core.app.Wijjit` class orchestrates everything (see ``src/wijjit/core/app.py``):

1. **Construction** – provide ``template_dir`` (if you keep templates on disk) and optional ``initial_state``. Internally this wires up the renderer, layout engine, focus/hover managers, overlay system, terminal devices, handler registry, and mouse router.
2. **Configuration** – register views via ``@app.view``, hook actions/keys/mouse handlers, and set global options (refresh interval, custom themes, etc.). Nothing is rendered yet.
3. **Run** – ``app.run()`` hands execution to :class:`wijjit.core.event_loop.EventLoop`, which enters the alternate terminal buffer, enables mouse tracking, and renders the default view. ``run_async()`` is also available when you already have an asyncio loop.
4. **Main loop** – every tick collects input, dispatches events, applies state changes, and triggers renders when ``app.needs_render`` is true. Focus, hover, overlays, and notifications are updated along the way.
5. **Shutdown** – ``app.quit()`` or ``Ctrl+C`` causes the event loop to unwind, restore the cursor/buffer, close the ``InputHandler``, and stop any background executors. ``on_exit`` view hooks and overlay ``on_close`` callbacks are guaranteed to run.

If any handler raises, ``Wijjit._handle_error`` logs the stack trace via ``wijjit.logging_config`` before attempting a clean shutdown.

Views and routing
-----------------

Views describe what should be rendered for a given route. ``@app.view("name", default=True)`` registers the function with :class:`wijjit.core.view_router.ViewRouter`. Each view returns a configuration dictionary with the following keys:

* ``template`` **or** ``template_file`` – inline Jinja template or a filename inside ``template_dir``.
* ``data`` – optional dict or callable that builds a context dictionary for the template.
* ``on_enter`` / ``on_exit`` – lifecycle hooks executed whenever the view is entered or left.

``ViewRouter`` lazily evaluates the function the first time the view is used. Static ``data`` dicts are deep-copied so a render cannot mutate the next run. Navigation is performed with ``app.navigate("settings", params={"tab": "profile"})`` (sync) or ``await app.navigate_async(...)``. During navigation Wijjit:

1. Initializes the target view if necessary.
2. Executes the previous view’s ``on_exit`` hook and clears view-scoped handlers.
3. Switches ``handler_registry.current_view`` and stores ``current_view_params``.
4. Runs the new view’s ``on_enter`` hook.
5. Flags ``needs_render`` so the event loop paints the new layout.

You can keep arbitrary navigation state (breadcrumb stacks, modal routes, etc.) inside the ``State`` object or your own controller classes. The ``examples/navigation_demo.py`` script showcases multiple named views and hotkeys for moving between them.

State & reactivity
------------------

Wijjit ships with :class:`wijjit.core.state.State`, a dict-like container with change detection. Every mutation eventually calls ``State._trigger_change``, which notifies global ``on_change`` callbacks and per-key watchers registered through ``state.watch("key", callback)``. The application constructor registers ``self._on_state_change`` so **any** change marks ``needs_render = True`` when the app is running.

Key behaviors:

* Reserved keys – names that collide with dict methods (``items``, ``keys``, …) are disallowed to keep template attribute access predictable.
* Attribute access – ``state.greeting`` works in Python and templates, but ``state["greeting"]`` remains available for non-identifier keys.
* Async callbacks – watchers can be ``async def``; Wijjit tracks pending tasks and awaits them safely.
* Immutability optional – the class does not enforce immutability; you can mutate nested lists/dicts, but prefer assigning new objects to keep renders predictable.

See :doc:`state_management` for in-depth recipes, including validation, derived data, and background workers.

Rendering pipeline
------------------

Rendering is a multi-step process:

1. **Template rendering** – Wijjit configures a Jinja environment with custom extensions from ``wijjit.tags`` (``{% frame %}``, ``{% vstack %}``, ``{% button %}``, etc.). Your view’s ``template`` is rendered using ``state`` and the optional ``data`` dict.
2. **Layout tree** – tags such as ``{% vstack %}`` emit layout nodes (:class:`wijjit.layout.engine.VStack`, :class:`wijjit.layout.engine.HStack`, :class:`wijjit.layout.engine.FrameNode`) that describe sizing, spacing, and alignment.
3. **Layout pass** – :mod:`wijjit.layout.engine` performs a bottom-up intrinsic size calculation followed by a top-down assignment of absolute bounds (:class:`wijjit.layout.bounds.Bounds`). Scroll containers report overflow to :mod:`wijjit.layout.scroll`.
4. **Element painting** – Each :class:`wijjit.elements.base.Element` paints itself into a :class:`wijjit.rendering.paint_context.PaintContext`, which tracks ANSI styling and dirty regions. Elements only redraw when their bounds intersect the dirty set.
5. **Terminal flush** – The :class:`wijjit.terminal.screen.ScreenManager` writes the diffed buffer to the alternate screen, preserving performance even when complex components are present.

Because layouts are recomputed every render, you can safely change widths/heights in response to state. The ``renderer`` also wires up the ``ElementWiringManager`` so bound inputs (``{% textinput id="name" %}``) stay synced with state keys.

Event flow
----------

Events originate from :class:`wijjit.terminal.input.InputHandler` and :class:`wijjit.terminal.mouse.MouseEvent`. The loop wraps them in classes from :mod:`wijjit.core.events` (``KeyEvent``, ``ActionEvent``, ``ChangeEvent``, ``MouseEvent``) and dispatches them through :class:`wijjit.core.events.HandlerRegistry`. Handlers can be scoped to:

* ``GLOBAL`` – always run (use sparingly).
* ``VIEW`` – automatically registered/unregistered when the active view changes.
* ``ELEMENT`` – tied to a specific element via wiring (e.g., a button’s action).

Handlers may be synchronous or ``async``. By default they run on the main loop, but you can configure ``app.configure(executor=ThreadPoolExecutor())`` to offload blocking work. The registry also supports priorities so critical behavior (e.g., Tab navigation) runs before user code.

Mouse events are routed via :class:`wijjit.core.mouse_router.MouseEventRouter`, which performs hit testing against overlay layers first, then base elements. Hover state is managed by :class:`wijjit.core.hover.HoverManager`.

Working asynchronously
----------------------

Wijjit runs happily inside existing asyncio applications. Call ``await app.run_async()`` or interact directly with ``EventLoop`` if you’re embedding Wijjit into another service. Long-running operations should:

* Spawn a ``asyncio.create_task`` or schedule work on ``ThreadPoolExecutor``.
* Update ``app.state`` when results arrive (loop-safe thanks to ``State`` callbacks).
* Use :func:`app.refresh` to request a render if you mutate data outside the normal event pipeline.

Putting it together
-------------------

Here is a simplified pseudo-loop inspired by ``EventLoop._process_frame_async``:

.. code-block:: python

    while app.running:
        input_event = await input_handler.read()
        handler_registry.dispatch(input_event)
        mouse_router.route_mouse_event(input_event)
        notification_manager.prune()
        if app.needs_render or app.renderer.dirty_manager.has_regions():
            app._render()

Understanding where your feature plugs into this loop (state mutation, handler, layout node, overlay, etc.) will help you design predictable TUIs. Continue to :doc:`state_management`, :doc:`templates`, and :doc:`event_handling` for deeper dives into each subsystem.
