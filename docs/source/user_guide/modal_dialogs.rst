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

Showing a modal from a template
-------------------------------

The simplest way to show a modal is the ``{% modal %}`` tag bound to a state key
via ``visible=``. The modal renders only while that state key is truthy, and you
flip it from action handlers:

.. code-block:: python

    from wijjit import Wijjit, render_template_string

    app = Wijjit()
    app.state["show_confirm"] = False

    @app.view("home", default=True)
    def home():
        return render_template_string("""
            {% vstack %}
              {% button action="open" %}Delete project{% endbutton %}

              {% modal id="confirm" visible="show_confirm" title="Delete project?" width=44 height=9 %}
                This cannot be undone.

                {% hstack spacing=2 %}
                  {% button action="confirm_cancel" %}Cancel{% endbutton %}
                  {% button action="confirm_delete" variant="danger" %}Delete{% endbutton %}
                {% endhstack %}
              {% endmodal %}
            {% endvstack %}
            """)

    @app.on_action("open")
    def open_modal(event):
        app.state["show_confirm"] = True

    @app.on_action("confirm_cancel")
    def cancel(event):
        app.state["show_confirm"] = False

    @app.on_action("confirm_delete")
    def delete(event):
        # ... perform deletion ...
        app.state["show_confirm"] = False

The ``{% modal %}`` tag accepts ``id``, ``visible`` (state key for visibility),
``title``, ``width``, ``height``, and ``border`` (``single``, ``double``,
``rounded``). Focus trapping and a dimmed background are applied automatically
for modal-layer overlays.

Creating overlays programmatically
----------------------------------

For full control you can instantiate a :class:`wijjit.elements.display.modal.ModalElement`
and push it onto the overlay manager yourself:

.. code-block:: python

    from wijjit.core.overlay import LayerType
    from wijjit.elements.display.modal import ModalElement

    def show_confirm():
        modal = ModalElement(
            title="Delete project?",
            width=44,
            height=9,
            border_style="rounded",
        )
        app.overlay_manager.push(
            modal,
            layer_type=LayerType.MODAL,
            trap_focus=True,
            dimmed_background=True,
        )

``ModalElement`` itself is just a bordered container - its constructor params are
``id``, ``title``, ``width``, ``height``, ``border_style``, ``centered``, and
``padding`` (there is no ``body`` or ``buttons`` argument; add child elements via
the layout tree, or prefer the ``{% modal %}`` template approach above for
button-bearing dialogs).

``OverlayManager.push`` returns an ``Overlay`` object you can keep to close manually. Options:

* ``close_on_click_outside`` – close if the user clicks outside the overlay (default ``True``).
* ``close_on_escape`` – respond to Escape (default ``True``).
* ``trap_focus`` – keep focus inside the overlay until closed (set ``True`` for modals).
* ``dimmed_background`` – render a dimmed layer behind the overlay.
* ``on_close`` – callback invoked after the overlay is dismissed.

When ``trap_focus=True``, keyboard navigation (Tab/Shift+Tab) continues to work within the modal, cycling through its focusable elements. Focus is automatically restored to the previously focused element when the modal closes. See :doc:`focus_navigation` for details.

Templated dialogs
-----------------

You rarely need to instantiate modals manually. :mod:`wijjit.tags.dialogs` exposes tags tailored to common flows:

``{% confirmdialog %}``
    Renders a confirm/cancel dialog. Attributes: ``id``, ``visible`` (state key controlling visibility - **required** for the dialog to appear), ``title``, ``message`` (or supply the message as body content), ``confirm_action``, ``cancel_action``, ``confirm_label``, ``cancel_label``, ``width``, ``height``, ``border``.

    .. code-block:: jinja

       {% confirmdialog visible="show_confirm"
                        title="Delete file?"
                        message="This cannot be undone."
                        confirm_action="do_delete"
                        cancel_action="cancel_delete"
                        confirm_label="Delete"
                        cancel_label="Cancel" %}{% endconfirmdialog %}

``{% alertdialog %}``
    Simple "OK" dialog. Attributes: ``id``, ``visible`` (required state key), ``title``, ``message`` (or body content), ``ok_action``, ``ok_label``, ``width``, ``height``, ``border``.

``{% inputdialog %}``
    Collects a short text input. Attributes: ``id``, ``visible`` (required state key), ``title``, ``prompt``, ``initial_value``, ``submit_action``, ``cancel_action``, ``placeholder``, ``submit_label``, ``cancel_label``, ``width``, ``height``, ``border``, ``input_width``.

Each dialog tag is only rendered while its ``visible`` state key is truthy, so set that key to ``True`` from an action handler to show the dialog and back to ``False`` to dismiss it. The renderer turns each tag into the matching dialog overlay element and pushes it automatically. Actions fire like any other button: use ``@app.on_action("do_delete")`` to handle the user's choice.

Dropdowns & context menus
-------------------------

Dropdowns (``{% dropdown for="button_id" %}``) and context menus (``{% contextmenu target="list_item" %}``) are implemented in :mod:`wijjit.tags.menu`. They automatically attach to the specified target element, track click/hover coordinates, and close when the user clicks elsewhere. Right-click detection is handled by :class:`wijjit.core.mouse_router.MouseEventRouter`.

Closing overlays
----------------

Ways an overlay can close:

* User clicks outside (``close_on_click_outside``).
* User presses Escape (``close_on_escape``).
* An action handler calls ``app.overlay_manager.pop(overlay)`` to close one overlay, or ``app.overlay_manager.pop_layer(LayerType.MODAL)`` to close every overlay in a layer.
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

Toast-style notifications also use the overlay system under the hood. The
easiest entry point is the high-level ``app.notify()`` helper, which builds a
notification element and queues it for you:

.. code-block:: python

    app.notify("Saved successfully", severity="success")
    app.notify("Deployment failed", severity="error", duration=None)  # no auto-dismiss

``severity`` is one of ``"info"`` (default), ``"success"``, ``"warning"``, or
``"error"``. Pass ``duration=None`` for a notification that stays until
dismissed, and an optional ``action=(label, callback)`` tuple to add an action
button. ``notify()`` returns a notification id you can pass to
``app.dismiss_notification(id)``.

For lower-level control, :class:`wijjit.core.notification_manager.NotificationManager`
exposes ``add(element, duration=3.0, on_close=None)``, where ``element`` is a
:class:`wijjit.elements.display.notification.NotificationElement`:

.. code-block:: python

    from wijjit.elements.display.notification import NotificationElement

    note = NotificationElement(message="Saved successfully", severity="success")
    app.notification_manager.add(note, duration=3.0)

The manager creates overlay entries at the edge of the viewport and removes them when timers expire or the user dismisses them.

Tips
----

* Prepare dialog templates as macros for reuse (e.g., ``{% macro confirm_delete(name) %}…{% endmacro %}``).
* Centralize overlay actions (``confirm_delete``, ``confirm_cancel``) in a dedicated module so business logic isn’t scattered across views.
* Consider storing overlay visibility in state (``state.show_settings_modal``) if the dialog affects layout or needs to coordinate with other components.

For focus-specific guidance read :doc:`focus_navigation`; for pointer interactions see :doc:`mouse_support`.
