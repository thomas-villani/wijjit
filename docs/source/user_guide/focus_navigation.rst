Focus Navigation
================

Like any desktop UI, Wijjit tracks which element currently has focus so keyboard users can interact without touching the mouse. Focus management lives in :class:`wijjit.core.focus.FocusManager`, which the app updates after every render.

How focus is determined
-----------------------

1. During rendering the layout engine collects all :class:`wijjit.elements.base.Element` instances.
2. ``FocusManager.set_elements`` filters the list to those with ``focusable=True`` (buttons, inputs, menus, etc.).
3. The manager tries to keep focus on the same ``id`` as the previous frame. If an element disappeared, it falls back to the same index or the first available element.
4. Focus state is synced with each element via ``element.on_focus()`` / ``element.on_blur()`` (implemented by the base class). These hooks toggle visual cues (highlighted borders, caret visibility).

Built-in navigation
-------------------

Wijjit registers global Tab/Shift+Tab handlers (see ``Wijjit._handle_tab_key`` in ``src/wijjit/core/app.py``):

* ``Tab`` → ``FocusManager.focus_next()``
* ``Shift+Tab`` → ``focus_previous()``

When focus moves, the manager marks both the old and new element bounds as dirty so they re-render with appropriate styling.

Override strategies:

* Disable automatic Tab handling by setting ``app.focus_navigation_enabled = False`` and register your own key handlers (useful for custom grids).
* For modal dialogs, focus is automatically trapped if you set ``trap_focus=True`` when pushing the overlay. Closing the modal restores the previous focus state.

Making elements focusable
-------------------------

When building custom elements:

.. code-block:: python

    class TagPicker(Element):
        def __init__(self, id=None):
            super().__init__(id)
            self.focusable = True

        def on_focus(self):
            self.focused = True

        def on_blur(self):
            self.focused = False

        def handle_key(self, key: Key) -> bool:
            if key == Keys.LEFT:
                self.move_left()
                return True
            return False

If ``handle_key`` returns ``True`` the event stops propagating. Combine this with ``handle_mouse`` to support clicks and focus on pointer interaction.

Working inside scrollable containers
------------------------------------

Scrollable frames keep child bounds relative to the frame viewport. Focused elements inside a scrollable region are automatically scrolled into view by the frame’s ``ScrollManager``. For best results:

* Ensure each input inside a scrollable frame has a unique ``id``.
* Avoid placing focusable children outside the frame’s content area (no negative margins).

Managing focus manually
-----------------------

You can direct focus programmatically:

.. code-block:: python

    app.focus_manager.focus_element(app.renderer.get_element("search_box"))

or use helper methods:

* ``focus_first()`` – highlight the first focusable element.
* ``focus_last()`` – highlight the last element (useful when opening popovers).
* ``get_focused_element()`` – inspect the current element (handy in debugging).

For multi-pane apps where each pane should maintain its own focus, save the focus state (``focus_manager.save_state()``) before switching panes and restore with ``focus_manager.restore_state(saved)`` later. Overlays already do this automatically.

Troubleshooting tips
--------------------

* **Element skipped** – ensure ``focusable=True`` and the element is part of the layout tree (check ``element.bounds`` is not ``None``).
* **Wrong order** – focus order follows the layout tree order. Rearrange template tags or assign explicit ``tab_index`` (feature coming soon) to fine-tune.
* **Focus lost after rerender** – assign stable ``id`` values. Auto-generated ids may change between renders when conditionals add/remove elements.
* **Scroll jumps** – if a focused element is inside a scrollable frame with dynamic height, keep the frame height fixed so scroll offsets remain valid.

When building keyboard-first workflows, pair this guide with :doc:`event_handling` and :doc:`components` to ensure every interaction can be reached without a mouse.
