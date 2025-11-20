Examples
========

Wijjit ships with 40+ runnable scripts under ``examples/``. Use them as living documentation—copy snippets, tweak state, or run them as smoke tests while building your own app.

Running an example
------------------

.. code-block:: bash

    cd <repo-root>
    uv run python examples/hello_world.py

Any Python interpreter works; ``uv run`` keeps dependencies isolated.

Basics & essentials
-------------------

* ``hello_world.py`` – smallest possible Wijjit app; illustrates ``@app.view`` + inline template.
* ``simple_input_test.py`` – demonstrates text inputs, change events, and live validation.
* ``form_demo.py`` – multi-field form with buttons and status messages.

Forms & workflows
-----------------

* ``login_form.py`` – login screen with validation, focus hints, and error notifications.
* ``filesystem_browser.py`` – explores list navigation, buttons, and status feedback.
* ``centered_dialog.py`` – wizard-style layout with buttons driving modal overlays.

Data display
------------

* ``table_demo.py`` – sortable table with zebra striping and scroll support.
* ``tree_demo.py`` / ``tree_indicator_styles_demo.py`` – hierarchical navigation with custom indicators.
* ``logview_demo.py`` – streaming log viewer with severity-based styling.
* ``markdown_demo.py`` / ``code_demo.py`` – render markdown and syntax-highlighted panes.

Layout patterns
---------------

* ``alignment_demo.py`` – shows how ``align_h``/``align_v`` impact stacks.
* ``complex_layout_demo.py`` – dashboard composed of nested frames and stacks.
* ``scroll_demo.py`` / ``scrollable_children_demo.py`` – deep dive into scroll containers and focus retention.
* ``frame_sizing_demo.py`` / ``frame_overflow_demo.py`` – compare width/height modes, padding, and overflow handling.

Interaction & advanced UI
-------------------------

* ``checkbox_demo.py``, ``radio_demo.py``, ``select_demo.py`` – widget-specific explorations.
* ``modal_with_button_demo.py`` / ``confirm_dialog_demo.py`` / ``alert_dialog_demo.py`` – overlay interactions.
* ``dropdown_demo.py`` – buttons that spawn dropdown menus with nested actions.
* ``mouse_demo.py`` – showcases hover, clicks, and scroll routing.
* ``notification_demo.py`` – toast notifications with auto-dismiss logic.

Performance & utilities
-----------------------

* ``async_demo.py`` / ``download_simulator.py`` – background tasks updating state.
* ``debug_keys.py`` – raw key event logger, ideal for customizing shortcuts.
* ``statusbar_demo.py`` – persistent footer with modal triggers.

Where to next
-------------

* Pair each example with the relevant user-guide chapter (layout, events, modals) for deeper explanations.
* Add new examples under ``examples/`` and reference them here; follow the naming conventions above.
* For higher-level recipes, see :doc:`cookbook`.
