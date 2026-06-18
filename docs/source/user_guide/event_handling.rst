Event Handling
==============

Wijjit applications are event driven. Keyboard input, mouse activity, and widget actions are converted into strongly-typed events defined in :mod:`wijjit.core.events` and dispatched through :class:`wijjit.core.events.HandlerRegistry`. This chapter explains how to hook those events, manage scope, and keep handlers responsive.

Event types
-----------

``EventType.KEY``
    Low-level key presses. Wrapped by :class:`wijjit.core.events.KeyEvent` (``event.key``, ``event.modifiers``, ``event.key_obj``).

``EventType.ACTION``
    Emitted by widgets such as buttons, menus, dialogs, and inputs configured with ``action="…"``. Delivered as :class:`wijjit.core.events.ActionEvent` containing ``action_id``, ``source_element_id``, and optional ``data``.

``EventType.CHANGE``
    Triggered when a bound input modifies its value. :class:`wijjit.core.events.ChangeEvent` surfaces ``element_id``, ``old_value``, and ``new_value``.

``EventType.FOCUS`` / ``EventType.BLUR``
    Sent whenever focus moves between elements. Helpful for validation and inline help.

``EventType.MOUSE``
    Raised for clicks, drags, scrolls, and hover updates. Wraps :class:`wijjit.terminal.mouse.MouseEvent` with coordinates and modifiers.

Registering handlers
--------------------

Wijjit exposes decorator helpers on the app instance:

``@app.on_key("ctrl+s")``
    Decorator that registers a KEY handler with hotkey parsing (``ctrl``, ``alt``, ``shift``). The key is matched exactly (case-insensitively) against ``event.key``; there is no ``"*"`` wildcard.

``@app.on_action("save")``
    Decorator that subscribes to a specific action id. Handy for buttons and dialogs.

``app.on(EventType.CHANGE, handler, scope=HandlerScope.VIEW)``
    Lowest-level API. **Note:** ``Wijjit.on`` is *not* a decorator – ``callback`` is a required positional argument. Define the handler function, then pass it to ``app.on(...)``.

Handlers receive one argument (the event object). They can be synchronous or ``async``; Wijjit detects coroutines automatically. Example:

.. code-block:: python

    from wijjit.core.events import EventType, HandlerScope

    async def handle_keys(event):
        if event.key == "escape":
            app.quit()

    app.on(
        EventType.KEY,
        handle_keys,
        scope=HandlerScope.VIEW,
        view_name="home",
        priority=10,
    )

Handler scopes & lifetimes
--------------------------

``HandlerScope.GLOBAL``
    Always active. Use for cross-view shortcuts (``Ctrl+C`` to quit). Keep global handlers minimal to avoid unexpected interactions.

``HandlerScope.VIEW``
    Active only while the named view is visible. When navigation occurs, Wijjit automatically unregisters view-scoped handlers and re-registers those belonging to the new view. To get this scope, pass ``scope=HandlerScope.VIEW`` (and a ``view_name``) to ``app.on(...)``. Note that ``@app.on_key`` always registers at ``HandlerScope.GLOBAL``, and ``@app.on_action`` does not use ``HandlerScope`` at all – its handlers are stored in a separate action-handler map.

``HandlerScope.ELEMENT``
    Used internally by the element wiring manager. Custom elements may register element-scoped handlers to capture focus, mouse, or change events belonging to a specific widget id.

Priorities default to ``0``; higher values run earlier. For example, Wijjit registers Tab/Shift+Tab navigation with priority ``100`` so it executes before user code can intercept the key.

Actions & change events
-----------------------

Any widget can emit an action:

* Buttons – ``{% button action="save" %}``
* Text inputs – ``{% textinput action="login" %}`` (fires on Enter)
* Dialogs – ``{% confirmdialog action_ok="confirm_delete" %}``
* Menus – menu items specify ``action`` on each entry.

Handle them using ``@app.on_action("save")`` or ``app.on(EventType.ACTION, handler)`` if you need a catch-all logger. ``ActionEvent.data`` carries widget-specific payloads (e.g., selected option).

``ChangeEvent`` is emitted by bound inputs (text, textarea, checkbox, select). It is useful for real-time validation:

.. code-block:: python

    def validate(event):
        if event.element_id == "password" and len(event.new_value) < 8:
            app.state.password_error = "Too short"

    app.on(EventType.CHANGE, validate, scope=HandlerScope.VIEW, view_name="signup")

Keyboard shortcuts
------------------

`prompt-toolkit` normalizes keys to strings (``"ctrl+c"``, ``"f5"``, ``"enter"``). ``@app.on_key`` registers one key per decorator; apply it multiple times (or call it directly) to bind several keys:

.. code-block:: python

    @app.on_key("ctrl+s")
    def save_handler(event):
        save()

    @app.on_key("ctrl+w")
    def close_handler(event):
        close_tab()

To stop further handlers from running, call ``event.cancel()``.

Mouse handling
--------------

Mouse events surface through :class:`wijjit.core.events.MouseEvent`, which wraps the terminal-layer mouse event in ``event.mouse_event`` and exposes convenience properties directly on the event: ``event.x``, ``event.y``, ``event.button``, ``event.mouse_type``, ``event.shift``/``event.alt``/``event.ctrl``, and ``event.click_count``. Scroll direction is read from ``event.button`` (there is no ``scroll_amount``):

.. code-block:: python

    from wijjit.terminal.mouse import MouseButton

    def on_mouse(event):
        if event.button == MouseButton.SCROLL_UP and event.ctrl:
            zoom_in()
        elif event.button == MouseButton.SCROLL_DOWN and event.ctrl:
            zoom_out()

    app.on(EventType.MOUSE, on_mouse, scope=HandlerScope.VIEW, view_name="canvas")

For widget-level interactions (click a specific element), implement ``handle_mouse`` on the element or rely on built-in widgets (buttons, menus, scroll containers) which already handle mouse input.

Element event callbacks
-----------------------

In addition to app-level handlers, elements expose callback attributes for direct event handling:

**Base Element Callbacks** (all elements):

* ``on_double_click(event: MouseEvent)`` – Called on double-click
* ``on_context_menu(event: MouseEvent) -> list | None`` – Called on right-click, return menu items

**Drag-and-Drop** (all elements, set ``draggable=True`` or ``drop_target=True`` to enable):

* ``on_drag_start(event) -> data | None`` – Start drag, return data or None to cancel
* ``on_drag(event, data)`` – Called during drag
* ``on_drag_end(event, data, dropped)`` – Called when drag ends
* ``on_drag_over(event, data) -> bool`` – Check if drop allowed
* ``on_drop(event, data, source_element) -> bool`` – Handle drop

**Table Callbacks**:

* ``on_row_click(row_index, row_data)`` – Row clicked
* ``on_row_double_click(row_index, row_data)`` – Row double-clicked
* ``on_cell_click(row_index, column_key, value)`` – Cell clicked
* ``on_header_click(column_key)`` – Column header clicked
* ``on_sort(column_key, direction)`` – Sort changed

**TextInput/TextArea Callbacks**:

* ``on_change(old_value, new_value)`` – Value changed
* ``on_submit(value)`` – Enter pressed (TextInput) or Ctrl+Enter (TextArea)
* ``on_paste(text) -> str | None`` – Modify pasted text, return None to use original
* ``on_file_path_paste(paths) -> bool`` – File paths detected in paste, return True to prevent

Example:

.. code-block:: python

    from wijjit.elements.input.text import TextInput
    from wijjit.elements.display.table import Table

    # TextInput with submit handling
    search = TextInput(id="search")
    search.on_submit = lambda value: print(f"Search: {value}")

    # Table with row selection
    table = Table(data=data, columns=columns)
    table.on_row_click = lambda idx, row: print(f"Selected: {row}")

Asynchronous handlers
---------------------

Mark a handler ``async def`` to perform network calls or I/O. Wijjit awaits the coroutine. If you need to run CPU-intensive synchronous handlers off the main loop, set the config keys ``RUN_SYNC_IN_EXECUTOR = True`` (and optionally ``EXECUTOR_MAX_WORKERS``); synchronous handlers then execute on a thread pool and the event loop remains responsive.

Error handling & debugging
--------------------------

* Exceptions inside handlers bubble to ``Wijjit._handle_error`` where they are logged with stack traces and the app keeps running unless the error is fatal.
* Use ``logger = get_logger(__name__)`` and log inside handlers to confirm they fire in the expected order.
* ``HandlerRegistry.list_handlers()`` (inspect the source) can aid debugging by listing registered callbacks and scopes.

Best practices
--------------

* Keep handlers small. Delegate business logic to separate functions/services.
* Prefer specific scopes. Global handlers are powerful but can cause conflicts as your app grows.
* Use actions for semantic events (“save”, “submit”) and key handlers for physical keystrokes. That way you can trigger the same action from buttons, menus, or keyboard shortcuts without duplicating code.
* Cancel events when you consume them to prevent downstream handlers from running unnecessarily.
* Remove long-lived handlers you register manually (using ``handler_registry.unregister``) when they’re no longer needed to avoid memory leaks.

Next, read :doc:`layout_system` and :doc:`components` to see how these events translate into UI building blocks.
