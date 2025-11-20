Cookbook
========

Short, repeatable recipes for everyday Wijjit tasks. Each entry links to a working example so you can copy-paste with confidence.

Form validation with inline errors
----------------------------------

Source: ``examples/login_form.py``

1. Bind text inputs to state keys (``id="username"``/``"password"``).
2. Use ``@app.on_action("login")`` to validate fields; populate ``state.form_errors`` with error messages.
3. Render errors next to inputs using template conditionals:

   .. code-block:: jinja

        {% if state.form_errors.username %}
          {% notification tone="error" %}{{ state.form_errors.username }}{% endnotification %}
        {% endif %}

4. Clear errors when the form succeeds or users edit the fields.

Persisting data between sessions
--------------------------------

Source: tutorial todo app (see :doc:`../getting_started/tutorial`)

1. Load data from disk when constructing ``Wijjit``; store a ``next_id`` counter in state.
2. Define helper ``persist()`` that writes ``state["todos"]`` back to JSON.
3. Call ``persist()`` inside ``@app.on_action`` handlers and/or ``state.watch("todos", ...)`` so every change is saved.
4. Keep file paths under ``Path.home()`` or configurable via environment variables.

Multi-view navigation with keyboard shortcuts
---------------------------------------------

Source: ``examples/centered_dialog.py`` (modal navigation) and ``examples/dropdown_demo.py`` (actions)

1. Register multiple views with ``@app.view("home", default=True)`` and ``@app.view("settings")``.
2. Use ``@app.on_action("go_settings")`` to call ``app.navigate("settings")``.
3. Add keyboard shortcuts via ``@app.on_key("ctrl+,")`` to trigger the same action.
4. Store breadcrumbs or parameters in ``app.current_view_params`` if you need to restore filters/search terms when returning.

Background tasks & progress indicators
--------------------------------------

Source: ``examples/async_demo.py`` and ``examples/download_simulator.py``

1. Mark the handler ``async def`` (Wijjit awaits coroutines).
2. Update ``state["progress"]`` inside the coroutine and call ``await asyncio.sleep(...)`` between iterations.
3. Render ``progress`` via ``{% progressbar value=state.progress label=state.status %}``.
4. For CPU-bound work, configure ``app.configure(executor=ThreadPoolExecutor(...))`` and use ``loop.run_in_executor`` to keep the UI responsive.

Modal confirmations before destructive actions
----------------------------------------------

Source: ``examples/modal_with_button_demo.py``

1. Define a template snippet with ``{% confirmdialog action_ok="confirm_delete" action_cancel="cancel_delete" %}``.
2. Show the dialog by updating a boolean in state or by returning overlay metadata from the view.
3. Handle the confirm/cancel actions with ``@app.on_action``; call ``app.overlay_manager.close_all(LayerType.MODAL)`` when done.
4. Use ``trap_focus=True`` and ``dimmed_background=True`` for critical workflows.

Data tables with selection
--------------------------

Source: ``examples/table_demo.py``

1. Prepare rows as list of dicts; include ``selected_row`` in state.
2. Pass ``rows`` and ``columns`` to the table tag; use ``action="select_row_{{ row.id }}"`` on buttons/checkboxes inside cells.
3. Handle selection in a generic ``EventType.ACTION`` handler by parsing the action id (``select_row_`` prefix).
4. Reflect selection elsewhere (details pane, status bar, modal).

Notifications & status feedback
-------------------------------

Source: ``examples/notification_demo.py`` and ``examples/statusbar_demo.py``

1. For transient toasts, call ``app.notification_manager.info("Saved!")``. The manager auto-dismisses based on timeout.
2. For persistent hints, bind a ``state.status`` string to a ``statusbar`` or text block.
3. Combine with success/error tones to give clear guidance after actions.

Theming and styling tweaks
--------------------------

Source: ``examples/spinner_demo.py`` + :doc:`../user_guide/styling`

1. Create a custom ``Theme`` with overrides (button colors, frame borders).
2. Call ``app.renderer.set_theme(custom_theme)`` during startup or in response to user preference toggles.
3. Use ``style={...}`` attributes on template tags for one-off overrides (e.g., danger buttons).
4. Snapshot the UI after theme changes to catch regressions.

Have a recipe to add? Drop a runnable snippet in ``examples/`` and update this page so others can benefit. Refer back to :doc:`../user_guide/core_concepts` for a deeper explanation of how these patterns plug into the runtime.
