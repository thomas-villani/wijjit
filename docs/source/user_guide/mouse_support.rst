Mouse Support
=============

Mouse interaction is enabled by default. When ``app.run()`` starts, :class:`wijjit.terminal.input.InputHandler` switches the terminal into raw mode and activates mouse tracking sequences. From there, :class:`wijjit.core.mouse_router.MouseEventRouter` decides where each event goes.

Event pipeline
--------------

1. **Terminal** – prompt-toolkit emits :class:`wijjit.terminal.mouse.MouseEvent` objects containing ``x``, ``y``, ``button``, ``type`` (a :class:`wijjit.terminal.mouse.MouseEventType`: ``PRESS``, ``RELEASE``, ``DRAG``, ``MOVE``, ``SCROLL``, ``CLICK``, ``DOUBLE_CLICK``), modifier flags (``shift``/``alt``/``ctrl``), and ``click_count``.
2. **MouseEventRouter** – checks overlays first, then performs hit testing against the base layout to find the element occupying ``(x, y)``.
3. **HoverManager** – updates hover state when the pointer moves across elements; hover changes mark the UI as dirty so highlights/tooltips refresh.
4. **Element handlers** – if the target element implements ``handle_mouse`` it receives the event. Otherwise built-in logic handles clicks for common widgets (buttons, list items, frames).

Supported gestures
------------------

* **Clicks** – left, right, and middle buttons. Single clicks arrive as ``MouseEventType.CLICK``. Right-click opens context menus if defined.
* **Double clicks** – delivered as a distinct ``MouseEventType.DOUBLE_CLICK`` event (with ``event.click_count == 2``). Great for list selection shortcuts.
* **Scroll** – wheel events map to ``MouseEventType.SCROLL``; the direction is carried by ``event.button`` (``MouseButton.SCROLL_UP`` or ``MouseButton.SCROLL_DOWN``). There is no scroll-amount field - each wheel notch is one event. Wijjit scrolls frames/log views automatically.
* **Drag** – elements can listen for ``PRESS``/``DRAG``/``RELEASE`` sequences to implement sliders or lasso selection.

Writing mouse-aware elements
----------------------------

Implement ``async def handle_mouse(self, event: MouseEvent) -> bool`` on your
element (the base method is a coroutine, so override it as ``async``). Return
``True`` if you consumed the event. Inspect ``event.type`` (a
:class:`wijjit.terminal.mouse.MouseEventType`) to branch, and use
``event.button`` for the scroll direction. Example:

.. code-block:: python

    from wijjit.terminal.mouse import MouseEventType, MouseButton

    async def handle_mouse(self, event):
        if event.type == MouseEventType.CLICK and self.bounds.contains(event.x, event.y):
            self.toggle()
            return True
        if event.type == MouseEventType.SCROLL:
            if event.button == MouseButton.SCROLL_UP:
                self.scroll_manager.scroll(-1)
            else:
                self.scroll_manager.scroll(1)
            return True
        return False

The ``MouseEvent`` dataclass exposes ``type``, ``button``, ``x``, ``y``, the
``shift`` / ``alt`` / ``ctrl`` modifier flags, and ``click_count``.

Hover effects & tooltips
------------------------

``HoverManager`` tracks which element the pointer is over and exposes hooks to elements via ``element.hovered``. Built-in widgets change styling automatically; custom elements can react during ``render_to``:

.. code-block:: python

    if self.hovered:
        style = style.with_background("yellow")

To show a tooltip, call ``app.show_tooltip(element, x, y)`` with a small element
(typically a ``Frame`` with content) positioned near the cursor; it opens on the
``LayerType.TOOLTIP`` overlay without trapping focus. Dismiss it with
``app.close_overlay(overlay)`` using the ``Overlay`` returned by ``show_tooltip``.

Menus & context clicks
----------------------

Context menus use the mouse router’s ``_handle_context_menu`` helper. Register a ``{% contextmenu target="element_id" %}`` and Wijjit automatically opens it on right-click. Dropdown menus behave similarly but attach to explicit triggers (buttons, select inputs).

Platform notes
--------------

* Mouse tracking requires a terminal that supports SGR mouse sequences (most modern emulators). In tmux or screen, ensure mouse mode is enabled (``set -g mouse on``).
* Windows Terminal and modern PowerShell consoles fully support mouse events; the legacy ``cmd.exe`` does not.
* If you notice missing events, verify your SSH client forwards mouse sequences (Enable “Application mouse mode”).

Debugging
---------

* Set ``WIJJIT_DEBUG_MOUSE=1`` (environment variable) to log mouse events (feature landing soon). Meanwhile, add ``logger.debug`` inside custom ``handle_mouse`` implementations.
* Use ``app.mouse_router._find_element_at(x, y)`` in a REPL to confirm hit testing results.
* For hover-related performance issues, limit expensive work in ``render_to`` when ``self.hovered`` toggles.

Remember that keyboard accessibility should remain intact even when mouse interactions are rich. Pair mouse handlers with equivalent key handlers to keep your TUI inclusive.
