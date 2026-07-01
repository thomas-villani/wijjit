Examples
========

Wijjit ships with 69 runnable scripts under ``examples/``. Use them as living documentation—copy snippets, tweak state, or run them as smoke tests while building your own app. Each directory mirrors a difficulty tier:

* ``examples/basic`` (15) – first steps, focus, events, async, alignment.
* ``examples/widgets`` (30) – component spotlights (tables, trees, dialogs, etc.).
* ``examples/advanced`` (21) – multi-view apps, complex layouts, and performance patterns.
* ``examples/styling`` (2) – CSS theming and style-class demos.
* ``examples/apps`` (3) – complete sample applications.

Running an example
------------------

.. code-block:: bash

    cd <repo-root>
    uv run python examples/basic/hello_world.py

Any Python interpreter works; ``uv run`` keeps dependencies isolated. See :file:`examples/README.md` for a catalog with screenshots and controls.

Basics & essentials
-------------------

* ``examples/basic/hello_world.py`` – smallest possible Wijjit app; illustrates ``@app.view`` + inline template.
* ``examples/basic/simple_input_test.py`` – demonstrates text inputs, change events, and live validation.
* ``examples/basic/mouse_demo.py`` – hover, click, and scroll routing.
* ``examples/basic/async_demo.py`` – async view/event handlers with progress updates.
* ``examples/basic/alignment_demo.py`` – compare horizontal/vertical alignment settings.

Inline rendering
----------------

These examples demonstrate inline rendering—outputting styled UI to terminal scrollback without using alternate screen mode:

* ``examples/basic/inline_demo.py`` – one-shot rendering with frames, tables, and nested layouts.
* ``examples/basic/inline_progress_demo.py`` – interactive progress bars with ``InlineApp`` and reactive state.
* ``examples/basic/inline_input_demo.py`` – keyboard-enabled inline forms with focus navigation.

See :doc:`../user_guide/inline_rendering` for detailed documentation.

Widgets & components
--------------------

* ``examples/widgets/checkbox_demo.py`` / ``radio_demo.py`` / ``select_demo.py`` – widget-specific explorations for form controls.
* ``examples/widgets/dropdown_demo.py`` – buttons that spawn dropdown menus with nested actions + shortcuts.
* ``examples/widgets/dialog_showcase.py`` / ``alert_dialog_demo.py`` / ``confirm_dialog_demo.py`` – overlay interactions.
* ``examples/widgets/table_demo.py`` – sortable table with zebra striping and scroll support.
* ``examples/widgets/tree_demo.py`` – hierarchical navigation with expand/collapse and multi-select.
* ``examples/widgets/listview_demo.py`` / ``logview_demo.py`` – scrolling lists and streaming logs.
* ``examples/widgets/contentview_demo.py`` / ``code_editor_demo.py`` – render markdown/ANSI/HTML content and edit syntax-highlighted code.
* ``examples/widgets/progress_demo.py`` / ``spinner_demo.py`` – progress indicators and loading states.
* ``examples/widgets/notification_demo.py`` / ``statusbar_demo.py`` – real-time feedback and persistent hints.
* ``examples/widgets/textarea_demo.py`` – full-featured text editor with clipboard + mouse support.
* ``examples/widgets/charts_demo.py`` – data visualization with sparklines, bar/column/line charts, gauges, and heatmaps.

Advanced workflows
------------------

* ``examples/advanced/login_form.py`` / ``form_demo.py`` / ``data_entry_demo.py`` – multi-field forms with validation and status banners.
* ``examples/advanced/preferences_demo.py`` – multi-column settings editor with grouped frames.
* ``examples/advanced/navigation_demo.py`` – multi-view navigation with lifecycle hooks and scoped handlers.
* ``examples/advanced/dashboard_demo.py`` – monitoring layout built from stacks, frames, and tables.
* ``examples/advanced/filesystem_browser.py`` – list + tree composition that mirrors a file explorer.
* ``examples/apps/todo_app.py`` – CRUD todo list with filters, persistence hooks, and overlays.
* ``examples/apps/chatbot.py`` – conversational TUI with a scrollable history and a rule-based responder (:doc:`tutorial <../getting_started/tutorial_chatbot>`).
* ``examples/apps/spreadsheet.py`` – editable ``DataGrid`` with a live chart and ``.xlsx``/CSV persistence (:doc:`tutorial <../getting_started/tutorial_spreadsheet>`).
* ``examples/advanced/state_management_demo.py`` / ``event_patterns_demo.py`` – reactors, watchers, and custom event scopes.
* ``examples/advanced/scroll_demo.py`` / ``scrollable_children_demo.py`` / ``frame_overflow_demo.py`` – focus-preserving scrolling patterns.
* ``examples/advanced/executor_demo.py`` / ``download_simulator.py`` – background workers and progress coordination.
* ``examples/advanced/error_handling_demo.py`` – graceful fallback paths when handlers fail.

Where to next
-------------

* Pair each example with the relevant user-guide chapter (layout, events, modals) for deeper explanations.
* Add new examples under ``examples/`` and reference them here; follow the naming conventions above.
* For higher-level recipes, see :doc:`cookbook`.
