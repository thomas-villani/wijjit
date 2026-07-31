Core Concepts
=============

This chapter introduces the moving pieces that make Wijjit feel like “Flask for the console”. Once you understand how the application lifecycle, views, state, rendering, and events cooperate, the rest of the docs become much easier to navigate.

Application lifecycle
---------------------

The :class:`wijjit.core.app.Wijjit` class orchestrates everything:

1. **Construction** – provide ``template_dir`` (if you keep templates on disk) and optional ``initial_state``. Creating the app sets up everything it needs to render and respond to input: the rendering pipeline, layout engine, focus and mouse handling, the overlay system, and the terminal connection.
2. **Configuration** – register views via ``@app.view``, hook actions/keys/mouse handlers, and set global options (refresh interval, custom themes, etc.). Nothing is rendered yet.
3. **Run** – ``app.run()`` starts the event loop, which enters the alternate terminal buffer, enables mouse tracking, and renders the default view. Wijjit is async internally, so ``app.run()`` is a thin wrapper around ``asyncio.run(...)``; if you are already inside an event loop, await the loop directly with ``await app.event_loop.run_async()`` instead.
4. **Main loop** – every tick collects input, dispatches events, applies state changes, and re-renders whenever something changed. Focus, hover, overlays, and notifications are updated along the way.
5. **Shutdown** – ``app.quit()`` or ``Ctrl+C`` causes the event loop to unwind, restore the cursor and terminal state, and stop any background work. ``on_exit`` view hooks and overlay ``on_close`` callbacks are guaranteed to run.

If a handler raises, Wijjit logs the traceback and the app keeps running — one bad handler does not take down your UI. Tracebacks are buffered while the alternate screen is active and flushed to stderr after the terminal is restored, so they never corrupt the frame. The exception is the *initial* render: a template that fails on first paint is fatal, so the error surfaces on a clean screen instead of leaving your terminal wedged.

Views and routing
-----------------

Views describe what should be rendered for a given route. ``@app.view("name", default=True)`` registers the function with :class:`wijjit.core.view_router.ViewRouter`. A view returns what to render via the Flask-style helpers:

* :func:`wijjit.render_template_string` – an inline Jinja template plus its context (``return render_template_string(SOURCE, title="Home")``).
* :func:`wijjit.render_template` – a template *file* from the template directory plus its context (``return render_template("dashboard.wij.j2", stats=stats)``).

Lifecycle hooks go on the decorator – ``@app.view("name", default=True, on_enter=setup, on_exit=teardown)`` – not in the return value. Context is passed as keyword arguments and flattened into top-level template variables; ``state`` is auto-injected.

``ViewRouter`` lazily evaluates the function the first time the view is used, then **re-invokes a synchronous view on every render** so any derived context stays live. Navigation is performed with ``app.navigate("settings", tab="profile")``; parameters are passed as keyword arguments (``Wijjit.navigate(view_name, **params)``). ``navigate`` auto-detects async view callables, so the same call works for sync and async views. During navigation Wijjit:

1. Initializes the target view if necessary.
2. Executes the previous view’s ``on_exit`` hook and clears view-scoped handlers.
3. Switches ``handler_registry.current_view`` and stores ``current_view_params``.
4. Runs the new view’s ``on_enter`` hook.
5. Flags ``needs_render`` so the event loop paints the new layout.

You can keep arbitrary navigation state (breadcrumb stacks, modal routes, etc.) inside the ``State`` object or your own controller classes. The ``examples/advanced/navigation_demo.py`` script showcases multiple named views and hotkeys for moving between them.

State & reactivity
------------------

Wijjit ships with :class:`wijjit.core.state.State`, a dict-like container with change detection. Every mutation notifies global ``on_change`` callbacks and per-key watchers registered through ``state.watch("key", callback)``. The app subscribes to state itself, so while it is running **any** change schedules a re-render automatically.

Key behaviors:

* Any key name – including ones that collide with a ``State`` method (``items``, ``keys``, …). Templates resolve ``{{ state.items }}`` to your value; in Python, reach those keys with ``state["items"]``. See :ref:`method-named-keys`.
* Attribute access – ``state.greeting`` works in Python and templates, but ``state["greeting"]`` remains available for non-identifier keys.
* Async callbacks – watchers can be ``async def``; Wijjit tracks pending tasks and awaits them safely.
* Immutability optional – the class does not enforce immutability; you can mutate nested lists/dicts, but prefer assigning new objects to keep renders predictable.

See :doc:`state_management` for in-depth recipes, including validation, derived data, and background workers.

Rendering pipeline
------------------

Rendering is a multi-step process:

1. **Template rendering** – Wijjit configures a Jinja environment with custom extensions from ``wijjit.tags`` (``{% frame %}``, ``{% vstack %}``, ``{% button %}``, etc.). Your view’s template (inline or file) is rendered with ``state`` injected as a named object, plus every context keyword argument flattened into a top-level template variable. Passing ``title="Home"`` is therefore referenced as ``{{ title }}``, not ``{{ data.title }}``.
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

Handlers may be synchronous or ``async``. By default they run on the main loop, but you can offload blocking synchronous handlers to a thread pool by setting the config keys ``RUN_SYNC_IN_EXECUTOR = True`` (and optionally ``EXECUTOR_MAX_WORKERS``); see :doc:`configuration`. The registry also supports priorities so critical behavior (e.g., Tab navigation) runs before user code.

Mouse events are routed via :class:`wijjit.core.mouse_router.MouseEventRouter`, which performs hit testing against overlay layers first, then base elements. Hover state is managed by :class:`wijjit.core.hover.HoverManager`.

Working asynchronously
----------------------

Wijjit is async internally – ``app.run()`` calls ``asyncio.run(...)`` to drive an async event loop, and both sync and async handlers/views are supported. Long-running operations should:

* Spawn a ``asyncio.create_task`` or schedule work on ``ThreadPoolExecutor``.
* Update ``app.state`` when results arrive (loop-safe thanks to ``State`` callbacks).
* Use :func:`app.refresh` to request a render if you mutate data outside the normal event pipeline.

Putting it together
-------------------

Every frame follows the same shape. In pseudocode:

.. code-block:: text

    while the app is running:
        read the next input event (key or mouse)
        dispatch it to the matching handlers
        expire any timed-out notifications
        if anything changed, re-render the view

Understanding where your feature plugs into this loop (state mutation, handler, layout node, overlay, etc.) will help you design predictable TUIs. Continue to :doc:`state_management`, :doc:`templates`, and :doc:`event_handling` for deeper dives into each subsystem.
