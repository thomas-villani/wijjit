Components
==========

Wijjit ships with a wide range of input and display components. They are implemented under :mod:`wijjit.elements` and exposed to templates through :mod:`wijjit.tags`. This section summarizes what’s available and when to reach for each widget.

Form inputs
-----------

TextInput / TextArea
    Single-line and multi-line editors (:mod:`wijjit.elements.input.text`). Support placeholder text, max length, width/height control, Enter actions, selection, copy/paste (via ``pyperclip``), and spell-friendly cursor movement. Both emit ``ChangeEvent`` on edits and update ``state[id]`` automatically.

Button
    Clickable action trigger (:mod:`wijjit.elements.input.button`). Attributes: ``variant`` (``primary``, ``secondary``, ``danger``), ``icon``, ``disabled``. Useful for both primary actions and inline icon buttons.

Checkbox / CheckboxGroup
    Toggle booleans or sets of values. Groups accept ``options`` and maintain a list in state (``state.selected_tags``). Support tri-state rendering, keyboard navigation, and spacing options.

Radio / RadioGroup
    Mutually exclusive selection. Layout horizontally or vertically, optionally wrap inside a ``frame`` with ``legend="…"``.

Select
    Drop-down picker with search/filter ability. Accepts dictionaries or tuples, can render icons next to labels, and integrates with dropdown overlays for large option sets.

Special behaviors:

* ``bind=False`` lets you manage the value manually (useful for derived or formatted inputs).
* ``action`` on inputs triggers when Enter is pressed.
* ``id`` is mandatory for binding; Wijjit auto-generates ids but naming them yourself keeps focus/state debugging easier.

Display widgets
---------------

Markdown / Code
    Render formatted documentation or syntax-highlighted snippets. Markdown supports headings, lists, checkboxes, and tables. Code blocks use Pygments themes tailored for dark/light terminals.

Table
    Feature-rich table control with column sizing, alignment, zebra striping, and optional selection/highlighting. Works well for log viewers, data dashboards, and admin lists. Consider pairing with scrollable frames for large datasets.

Tree
    Hierarchical explorer for file systems, menus, or org charts. Nodes can be expanded/collapsed via keyboard or mouse.

ListView
    Scrollable vertical list that highlights the selected row. Great for menus, chat transcripts, or search results.

LogView
    Tail-like streaming buffer with manual/auto-scroll toggles. Supports severity coloring and timestamp columns.

ProgressBar / Spinner
    Progress indicators for background tasks. ``progressbar`` accepts numeric ``value`` and optional ``label``; ``spinner`` animates automatically if you set ``app.refresh_interval``.

StatusBar
    Sticky footer for breadcrumbs, key hints, or status indicators. Combine with ``{% hstack %}`` sections to align sections left/center/right.

Notifications
    Inline banners styled by ``tone`` (``info``, ``success``, ``warning``, ``error``). Available as template tags and as programmatic overlays via :class:`wijjit.core.notification_manager.NotificationManager`.

Menus & overlays
----------------

DropdownMenu / ContextMenu
    Provided by :mod:`wijjit.elements.menu` and :mod:`wijjit.tags.menu`. Bind to a trigger element (button, list item) and specify menu items with actions. Context menus open on right-click; dropdowns open on left-click or keyboard shortcuts.

Modal
    Base container for custom dialogs (:mod:`wijjit.elements.modal`). Combine with :doc:`modal_dialogs` for confirm/alert/input flows. Supports focus trapping, dimmed background, and layering via :class:`wijjit.core.overlay.OverlayManager`.

NotificationElement
    For toast-style notifications. Usually managed through :class:`wijjit.core.notification_manager.NotificationManager`.

Custom components
-----------------

When the built-in set isn’t enough, implement a subclass of :class:`wijjit.elements.base.Element`:

1. Override ``render_to`` to paint into the :class:`wijjit.rendering.paint_context.PaintContext`.
2. Implement ``get_intrinsic_size`` if you need better sizing hints.
3. Set ``focusable`` and implement ``handle_key`` / ``handle_mouse`` when appropriate.
4. Expose the component via a Jinja extension (see ``wijjit/tags``) or instantiate it inside a view and insert it into the layout tree manually.

Tips
----

* Wrap inputs inside frames or stacks to control spacing and provide labels.
* Use ``state`` to drive visual states (e.g., ``{% button variant="danger" disabled=state.in_progress %}``).
* For high-frequency components (logs, tables), prefer incremental updates to state rather than rebuilding entire datasets every tick.
* Read the example gallery – most widgets have a dedicated ``examples/<widget>_demo.py`` script illustrating recommended usage.

Next: learn how to orchestrate modals and overlays in :doc:`modal_dialogs`, then deep dive into interaction layers with :doc:`focus_navigation` and :doc:`mouse_support`.
