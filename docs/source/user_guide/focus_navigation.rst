Focus Navigation
================

Like any desktop UI, Wijjit tracks which element currently has focus so keyboard users can interact without touching the mouse. Focus management lives in :class:`wijjit.core.focus.FocusManager`, which the app updates after every render.

How focus is determined
-----------------------

1. During rendering the layout engine collects all :class:`wijjit.elements.base.Element` instances.
2. ``FocusManager.set_elements`` filters the list to those with ``focusable=True`` (buttons, inputs, menus, etc.).
3. The manager tries to keep focus on the same ``id`` as the previous frame. If an element disappeared, it falls back to the same index.
4. If nothing could be restored, an element marked ``autofocus=True`` takes focus (see :ref:`autofocus-attribute`). Otherwise focus is left **unset** until the first Tab.
5. Focus state is synced with each element via ``element.on_focus()`` / ``element.on_blur()`` (implemented by the base class). These hooks toggle visual cues (highlighted borders, caret visibility).

.. _autofocus-attribute:

Initial focus: the ``autofocus`` attribute
------------------------------------------

A newly started app has **nothing focused**. This is deliberate - focusing the
first element unconditionally makes the first ``Tab`` appear to skip an element -
but it means keystrokes go nowhere until the user presses Tab. For a form, that
is rarely what you want.

Mark the element the app should start in:

.. code-block:: jinja

   {% textinput id="entry" placeholder="New task" width="fill" autofocus=True %}
   {% endtextinput %}

The rule is precise:

* It applies whenever focus would otherwise be unset - on the first render, and
  again if the focused element disappears from the tree.
* It **never** steals focus from an element that already has it, so a re-render
  cannot yank the cursor out from under the user.
* It changes only *where focus starts*, never the Tab order.
* ``tabindex="-1"`` excludes an element from ``autofocus`` exactly as it excludes
  it from Tab.
* Use it once per view. More than one is a template mistake: the first in tab
  order wins, and the framework logs a warning rather than picking silently.

``autofocus`` is accepted by every element, not just inputs, and needs no
support from the element class - it lives on
:class:`wijjit.elements.base.Element`.

Inside a modal it selects *which* element the dialog opens on. A trapping
overlay always takes focus somewhere, so there ``autofocus`` overrides the
default "first focusable element" choice rather than adding focus where there
was none.

The imperative equivalent is ``app.focus_element_by_id("entry")``, but note it
only works **after** the first render has built the elements - which is why it
cannot be called from an ``on_enter`` hook. Prefer ``autofocus`` for initial
focus, and the imperative helpers for focus that moves in response to events.

Built-in navigation
-------------------

Wijjit registers global Tab/Shift+Tab handlers so keyboard traversal works out of the box:

* ``Tab`` → ``FocusManager.focus_next()``
* ``Shift+Tab`` → ``focus_previous()``

When focus moves, the manager marks both the old and new element bounds as dirty so they re-render with appropriate styling.

Override strategies:

* Disable automatic Tab handling by setting ``app.focus_navigation_enabled = False`` and register your own key handlers (useful for custom grids).
* For modal dialogs, focus is automatically trapped if you set ``trap_focus=True`` when pushing the overlay. Closing the modal restores the previous focus state.

.. _tab-capture:

When Tab belongs to the element instead
---------------------------------------

Sometimes Tab is an editing key, not a navigation key: a code editor should
indent, and an open autocomplete popup should accept the highlighted
suggestion. Because the built-in handler above runs early and cancels the
event, a focused element does not see Tab at all unless it asks for it.

An element asks by overriding the ``captures_tab`` property
(:attr:`wijjit.elements.base.Element.captures_tab`). When it returns True the
element gets **first refusal** on plain Tab: its ``handle_key`` is called, and
focus moves on anyway if it returns False.

Two rules keep this from stranding the keyboard user:

* **Shift+Tab is never captured.** It always moves focus backward, so there is
  always a way out - and because backward movement wraps, every element stays
  reachable even though Tab cannot move *forward* past a capturing element.
  (Ctrl+Tab is not an alternative: terminals encode Ctrl+I as Tab.)
* **Declining is normal.** An element that returns True unconditionally turns
  Tab into a dead key; return False whenever there is nothing useful to do.

In templates this is the ``capture_tab`` attribute, with ``tab_width``
controlling how many spaces one Tab inserts:

.. code-block:: jinja

   {# A code editor indents by default - no attribute needed #}
   {% codeeditor id="src" language="python" width="fill" height=20 %}{% endcodeeditor %}

   {# A textarea moves focus by default; opt in where an indent is wanted #}
   {% textarea id="notes" width=40 height=8 capture_tab=True tab_width=2 %}{% endtextarea %}

``TextInput`` claims Tab conditionally: only while its autocomplete popup is
open, so a plain form field keeps Tab-to-next-field.

Focus cycling in modals
-----------------------

When a modal is displayed with ``trap_focus=True``, Tab and Shift+Tab navigation continues to work within the modal's focusable elements. This allows users to navigate between buttons, inputs, and other interactive elements inside the dialog without affecting the underlying view.

The focus manager automatically:

* **Cycles through focusable elements** - Tab moves forward, Shift+Tab moves backward through the modal's interactive elements
* **Wraps at boundaries** - From the last element, Tab wraps to the first element (and vice versa for Shift+Tab)
* **Restores focus on close** - When the modal closes, focus returns to the element that was focused before the modal opened

This behaviour is automatic and requires no configuration. Bind the modal's
visibility to a state key with ``visible=`` (the modal only renders while that
key is truthy) and include focusable elements (buttons, inputs, checkboxes,
etc.) in its body:

.. code-block:: jinja

   {% modal id="confirm_dialog" visible="show_confirm" title="Confirm" %}
       Are you sure you want to delete this item?

       {% hstack spacing=2 %}
           {% button action="confirm" %}Yes, Delete{% endbutton %}
           {% button action="cancel" %}Cancel{% endbutton %}
       {% endhstack %}
   {% endmodal %}

Focus trapping is applied automatically for modal-layer overlays - there is no
``trap_focus`` tag attribute to set. With this template, once you set
``state["show_confirm"] = True`` the modal opens and users can Tab between the
"Yes, Delete" and "Cancel" buttons while it is open. See :doc:`modal_dialogs`
for more details on building dialogs.

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

You can direct focus programmatically. The app offers a one-call helper that
looks the element up by id:

.. code-block:: python

    app.focus_element_by_id("search_box")   # returns True if the element was focused

    # equivalent lower-level form:
    app.focus_manager.focus_element(app.get_element_by_id("search_box"))

To wire a hotkey that jumps focus to a named element, use
``app.bind_focus_key(key, element_id, priority=0)`` (e.g. ``/`` to focus a search
box):

.. code-block:: python

    app.bind_focus_key("/", "search_box")

The ``FocusManager`` also exposes helper methods:

* ``focus_first()`` – highlight the first focusable element.
* ``focus_last()`` – highlight the last element (useful when opening popovers).
* ``get_focused_element()`` – inspect the current element (handy in debugging).

To disable Tab/Shift+Tab navigation entirely (e.g. for a display-only app), call
``app.configure_focus(enabled=False)``.

For multi-pane apps where each pane should maintain its own focus, save the focus state (``focus_manager.save_state()``) before switching panes and restore with ``focus_manager.restore_state(saved)`` later. Overlays already do this automatically.

Troubleshooting tips
--------------------

* **Nothing is focused when the app starts** – that is the default. Mark the field you want the user to start in with ``autofocus=True`` (see :ref:`autofocus-attribute`).
* **Typing does nothing until I press Tab twice** – a container is taking the first Tab stop. A frame whose content does not fit becomes scrollable, and scrollable containers are focusable, so they sort ahead of their own children. Give the frame enough height for its content.
* **Element skipped** – ensure ``focusable=True`` and the element is part of the layout tree (check ``element.bounds`` is not ``None``).
* **Wrong order** – focus order follows the layout tree order. Rearrange template tags or assign an explicit ``tab_index`` attribute to fine-tune. ``tab_index`` is a constructor param on :class:`wijjit.elements.base.Element` and is wired through the element tags, so you can set it directly in templates (e.g. ``{% textinput id="name" tab_index=1 %}``).
* **Focus lost after rerender** – assign stable ``id`` values. Auto-generated ids may change between renders when conditionals add/remove elements.
* **Scroll jumps** – if a focused element is inside a scrollable frame with dynamic height, keep the frame height fixed so scroll offsets remain valid.

When building keyboard-first workflows, pair this guide with :doc:`event_handling` and :doc:`components` to ensure every interaction can be reached without a mouse.
