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

Each assignment normally fires its own change callbacks immediately. To coalesce a group of related changes into a single notification, use ``State.batch_update()`` (sync) or ``State.async_batch_update()`` (async). Inside the context manager intermediate callbacks are suppressed, and on exit each key that actually changed (comparing original old vs. final new value) triggers callbacks once:

.. code-block:: python

    def update_profile(name: str, email: str) -> None:
        state = app.state
        with state.batch_update():
            state["status"] = "Saving…"
            state["profile"] = {**state["profile"], "name": name, "email": email}

In async code, prefer ``async with state.async_batch_update():`` so async callbacks are awaited before the context exits.

Multi-key and whole-state updates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To set several keys from a dict in one call, use ``update()`` (each changed key
fires its callbacks, and reserved names are validated):

.. code-block:: python

    app.state.update({"name": name, "email": email}, verified=True)

To replace the entire state (or clear it), use ``reset()``. It fires change
callbacks for every key that was removed or modified:

.. code-block:: python

    app.state.reset({"count": 0, "items": []})   # replace all keys
    app.state.reset()                             # clear everything

Watching specific keys
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    def log_change(key, old, new):
        logger.info("State %s changed from %r to %r", key, old, new)

    app.state.watch("username", log_change)

If you need to react to multiple keys, register multiple watchers or use ``on_change`` and branch on ``key``. Watchers run synchronously unless they are ``async`` coroutines, in which case Wijjit schedules them on the running loop.

To stop listening, use the removal counterparts. ``unwatch(key, callback)`` drops
one watcher (or every watcher for the key if ``callback`` is omitted), and
``off_change(callback)`` unregisters a global ``on_change`` callback:

.. code-block:: python

    app.state.unwatch("username", log_change)   # or unwatch("username") for all
    app.state.off_change(log_change)

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

``State`` ensures watchers run on the loop thread; avoid mutating state from raw background threads. If you must, schedule back onto the loop using ``asyncio.run_coroutine_threadsafe`` or ``loop.call_soon_threadsafe``. To run heavy synchronous handlers off the main loop, set the config keys ``RUN_SYNC_IN_EXECUTOR = True`` (and optionally ``EXECUTOR_MAX_WORKERS``); they can then update state safely afterward.

A plain assignment fires async watchers but does not wait for them (they run as
background tasks). When you need the callbacks to finish before continuing, use
``await state.set_async(key, value)``, which sets the value and awaits every
triggered callback. To drain any still-pending async callbacks (e.g. before
shutdown or in a test), ``await state.flush_pending_async()``.

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
      {{ state.form_errors.username }}
    {% endif %}

Remember to clear or overwrite errors after successful submission. ``State`` decides whether to fire watchers by comparing the new value to the old with ``!=``, so assigning a fresh ``form_errors`` dict whose contents differ from the previous one ensures watchers run.

Refreshing manually
-------------------

Most state mutations trigger renders automatically. Rare cases (timers, animations) may update off-loop; call ``app.refresh()`` or set ``app.refresh_interval`` to request periodic repaints (useful for spinners and clocks).

Testing tips
------------

* Instantiate ``State`` directly in unit tests to verify watchers and validation logic without booting a full Wijjit app.
* Use ``pytest.mark.asyncio`` for async watchers and ``await state.flush_pending_async()`` to deterministically drain pending async callbacks (preferred over ``asyncio.sleep(0)``).
* Snapshot rendered templates (see ``syrupy`` integration) after mutating state to ensure UI changes match expectations.

Next steps: dive into :doc:`templates` to see how state binds to UI elements, then :doc:`event_handling` to wire user input back into your data model.
