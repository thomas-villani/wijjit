State Management
================

Wijjit ships with a purpose-built :class:`wijjit.core.state.State` class that behaves like a dictionary, emits change notifications, and integrates tightly with the rendering pipeline. Mastering the state layer makes it easy to reason about reactivity, derived data, and background work.

State fundamentals
------------------

``State`` subclasses :class:`collections.UserDict` so it exposes familiar dict semantics while adding:

* **Attribute access** – ``state.greeting`` mirrors ``state["greeting"]``; templates can use either form.
* **Validation** – keys that collide with dict methods (``items``, ``keys``, ``pop``…) raise ``ValueError`` so templates never shadow built-in attributes.
* **Change detection** – ``__setitem__`` and ``__setattr__`` compare the new value to the previous one; callbacks fire only when a value actually changed.
* **Watchers** – arbitrary functions can subscribe to all changes (``state.on_change``) or to a specific key (``state.watch("username", callback)``).
* **Async support** – callbacks may be ``async def``; Wijjit tracks ``_pending_tasks`` so the event loop can await them without leaking coroutines.

It is safe to mutate nested structures, but remember that mutating a list in-place will not trigger watchers until you reassign the list (``state.todos = list(state.todos)``) or call ``state["todos"] = state["todos"]`` after editing. Prefer constructing new containers for clarity.

Common mutation patterns
------------------------

Single key updates
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    app.state["status"] = "Saving…"
    app.state.count += 1            # attribute style

Batch updates
^^^^^^^^^^^^^

Group related changes to avoid multiple renders. Wrapping updates in a helper keeps intent clear:

.. code-block:: python

    def update_profile(name: str, email: str) -> None:
        state = app.state
        state["status"] = "Saving…"
        state["profile"] = {**state["profile"], "name": name, "email": email}

State will emit two change events (``status`` then ``profile``); the renderer coalesces them into a single frame.

Watching specific keys
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    def log_change(key, old, new):
        logger.info("State %s changed from %r to %r", key, old, new)

    app.state.watch("username", log_change)

If you need to react to multiple keys, register multiple watchers or use ``on_change`` and branch on ``key``. Watchers run synchronously unless they are ``async`` coroutines, in which case Wijjit schedules them on the running loop.

Async and background work
-------------------------

Long-running operations should not block the event loop. Typical pattern:

.. code-block:: python

    async def refresh_data():
        app.state.loading = True
        try:
            data = await api.fetch()
            app.state.items = data
        finally:
            app.state.loading = False

``State`` ensures watchers run on the loop thread; avoid mutating state from raw background threads. If you must, schedule back onto the loop using ``asyncio.run_coroutine_threadsafe`` or ``loop.call_soon_threadsafe``. The ``EventLoop`` constructor accepts a ``ThreadPoolExecutor`` so heavy synchronous handlers can run off-thread while still updating state safely afterward.

Derived & computed data
-----------------------

Keep frequently-used derived values in either:

* **State** – update the derived key inside a watcher whenever its inputs change.
* **View ``data`` callables** – compute values on demand when the view renders.

Example – maintain ``completed_count`` whenever ``todos`` changes:

.. code-block:: python

    def derive_counts(key, old, new):
        if key == "todos":
            completed = sum(1 for todo in new if todo["done"])
            app.state.completed_count = completed

    app.state.watch("todos", derive_counts)

In templates you can reference ``state.completed_count`` without recomputing. If the derived value depends on multiple keys, register watchers for each or compute it inside the view’s ``data`` function where you have access to the entire ``state`` snapshot.

Validation & error reporting
----------------------------

A common pattern is to store validation errors in state and render them near input elements:

.. code-block:: python

    errors = {}
    if not state.username.strip():
        errors["username"] = "Username required"
    if len(state.password) < 8:
        errors["password"] = "Password must be 8+ chars"
    app.state.form_errors = errors

Template snippet:

.. code-block:: jinja

    {% if state.form_errors.username %}
      {% notification tone="error" %}{{ state.form_errors.username }}{% endnotification %}
    {% endif %}

Remember to clear or overwrite errors after successful submission. Because ``State`` uses deep equality, setting ``form_errors`` to a new dict ensures watchers fire even if the previous dict was empty.

Refreshing manually
-------------------

Most state mutations trigger renders automatically. Rare cases (timers, animations) may update off-loop; call ``app.refresh()`` or set ``app.refresh_interval`` to request periodic repaints (useful for spinners and clocks).

Testing tips
------------

* Instantiate ``State`` directly in unit tests to verify watchers and validation logic without booting a full Wijjit app.
* Use ``pytest.mark.asyncio`` for async watchers and leverage ``asyncio.sleep(0)`` to flush pending tasks.
* Snapshot rendered templates (see ``syrupy`` integration) after mutating state to ensure UI changes match expectations.

Next steps: dive into :doc:`templates` to see how state binds to UI elements, then :doc:`event_handling` to wire user input back into your data model.
