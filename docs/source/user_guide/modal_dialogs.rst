Modal Dialogs & Overlays
========================

Wijjit’s overlay system lets you layer modals, dropdowns, context menus, and tooltips above the base UI without rewriting your layout. Everything is coordinated by :class:`wijjit.core.overlay.OverlayManager`.

Overlay layers
--------------

Overlays live in one of several :class:`wijjit.core.overlay.LayerType` buckets:

* ``BASE`` – normal UI (no overlay).
* ``MODAL`` – blocking dialogs, confirmation flows.
* ``DROPDOWN`` – dropdowns, context menus.
* ``TOOLTIP`` – transient tooltips/popovers.

Each layer has its own z-index range. Within a layer, newly pushed overlays get a higher z-index so they stack correctly.

Creating overlays programmatically
----------------------------------

.. code-block:: python

    from wijjit.core.overlay import LayerType
    from wijjit.elements.modal import Modal

    def show_confirm():
        modal = Modal(
            title="Delete project?",
            body="This cannot be undone.",
            buttons=[
                {"label": "Cancel", "action": "confirm_cancel"},
                {"label": "Delete", "action": "confirm_delete", "variant": "danger"},
            ],
        )
        app.overlay_manager.push(
            modal,
            layer_type=LayerType.MODAL,
            trap_focus=True,
            dimmed_background=True,
        )

``OverlayManager.push`` returns an ``Overlay`` object you can keep to close manually. Options:

* ``close_on_click_outside`` – close if the user clicks outside the overlay (default ``True``).
* ``close_on_escape`` – respond to Escape (default ``True``).
* ``trap_focus`` – keep focus inside the overlay until closed (set ``True`` for modals).
* ``dimmed_background`` – render a translucent layer behind the overlay.
* ``on_close`` – callback invoked after the overlay is dismissed.

Templated dialogs
-----------------

You rarely need to instantiate modals manually. :mod:`wijjit.tags.dialogs` exposes tags tailored to common flows:

``{% confirmdialog %}``
    Renders a confirm/cancel dialog. Attributes: ``title``, ``message``, ``action_ok``, ``action_cancel``, ``ok_label``, ``cancel_label``, ``danger``.

``{% alertdialog %}``
    Simple “OK” dialog with tone-specific styling.

``{% inputdialog %}``
    Collects a short text input with built-in validation message slots.

Each dialog tag emits an overlay definition that the renderer turns into :class:`Modal` elements and pushes automatically. Actions fire like any other button: use ``@app.on_action("confirm_delete")`` to handle the user’s choice.

Dropdowns & context menus
-------------------------

Dropdowns (``{% dropdown for="button_id" %}``) and context menus (``{% contextmenu target="list_item" %}``) are implemented in :mod:`wijjit.tags.menu`. They automatically attach to the specified target element, track click/hover coordinates, and close when the user clicks elsewhere. Right-click detection is handled by :class:`wijjit.core.mouse_router.MouseEventRouter`.

Closing overlays
----------------

Ways an overlay can close:

* User clicks outside (``close_on_click_outside``).
* User presses Escape (``close_on_escape``).
* An action handler calls ``app.overlay_manager.pop(overlay)`` or ``close_all(layer_type=LayerType.MODAL)``.
* Overlays tied to state (e.g., notifications) update their ``visible_state_key`` to ``False``.

When closing, the overlay manager restores the previous focus state so the user returns to the element they were interacting with before the modal opened.

Stacking & multiple overlays
----------------------------

It’s common to have a dropdown inside a modal or a tooltip above a dropdown. Because each layer has its own z-index, you can safely push overlays in any order. Best practices:

* Keep the overlay stack shallow; nested modals are confusing.
* Always supply ``trap_focus=True`` for modals so keyboard users don’t accidentally interact with the background.
* Use ``dimmed_background`` sparingly (only for blocking dialogs).

Notifications & toasts
----------------------

Toast-style notifications also use the overlay system under the hood. Use :class:`wijjit.core.notification_manager.NotificationManager` to show toasts with auto-dismiss timers:

.. code-block:: python

    app.notification_manager.info("Saved successfully")
    app.notification_manager.error("Deployment failed", persist=True)

The manager creates overlay entries at the edge of the viewport and removes them when timers expire or the user dismisses them.

Tips
----

* Prepare dialog templates as macros for reuse (e.g., ``{% macro confirm_delete(name) %}…{% endmacro %}``).
* Centralize overlay actions (``confirm_delete``, ``confirm_cancel``) in a dedicated module so business logic isn’t scattered across views.
* Consider storing overlay visibility in state (``state.show_settings_modal``) if the dialog affects layout or needs to coordinate with other components.

For focus-specific guidance read :doc:`focus_navigation`; for pointer interactions see :doc:`mouse_support`.
