Components
==========

Wijjit ships with a wide range of input and display components. They are implemented under :mod:`wijjit.elements` and exposed to templates through :mod:`wijjit.tags`. This section summarizes what’s available and when to reach for each widget.

The examples referenced here are managed under ``examples/``. We pull live snippets with ``literalinclude`` so the docs stay in sync with the runnable demos—open the referenced script if you want to try it yourself.

Form inputs
-----------

TextInput / TextArea
    Single-line and multi-line editors (:mod:`wijjit.elements.input.text`). Support placeholder text, max length, width/height control, Enter actions, selection, copy/paste (via ``pyperclip``), and cursor movement. Both emit ``ChangeEvent`` on edits and update ``state[id]`` automatically. Use ``bind=False`` to manage the value manually (useful for formatted or derived inputs) and attach ``action=...`` to submit on Enter.

    .. literalinclude:: ../../examples/basic/simple_input_test.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/basic/simple_input_test.py`` – binding a ``textinput`` to ``state``

    ``textarea`` adds scrollbars, selection APIs, and clipboard shortcuts. It’s ideal for log editing, notes, or prompt composition. Pair it with derived state to show live counts, as demonstrated below.

    .. literalinclude:: ../../examples/widgets/textarea_demo.py
       :language: jinja
       :caption: Template excerpt from ``examples/widgets/textarea_demo.py``
       :start-after: "template": """
       :end-before: """,

Button
    Clickable action trigger (:mod:`wijjit.elements.input.button`). Attributes: ``variant`` (``primary``, ``secondary``, ``danger``), ``icon``, ``disabled``. Useful for both primary actions and inline icon buttons. Remember that ``action`` ids participate in handler routing—keep them short verbs (``save``, ``cancel``) and reuse them across views to share behavior.

Checkbox / CheckboxGroup
    Toggle booleans or sets of values. Groups accept ``options`` and maintain a list in state (``state.selected_tags``). Support tri-state rendering, keyboard navigation, and spacing options. Use them for preference panes or wizards.

    .. literalinclude:: ../../examples/widgets/checkbox_demo.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/widgets/checkbox_demo.py`` – single inputs + grouped toggles

Radio / RadioGroup
    Mutually exclusive selection. Layout horizontally or vertically, optionally wrap inside a ``frame`` with ``legend="…"``. Combine with ``state.watch`` to react when users pick a new option.

Select
    Drop-down picker with search/filter ability. Accepts dictionaries or tuples, can render icons next to labels, and integrates with dropdown overlays for large option sets.

Special behaviors:

* ``bind=False`` lets you manage the value manually (useful for derived or formatted inputs).
* ``action`` on inputs triggers when Enter is pressed.
* ``id`` is mandatory for binding; Wijjit auto-generates ids but naming them yourself keeps focus/state debugging easier.

Display widgets
---------------

Markdown / Code
    Render formatted documentation or syntax-highlighted snippets. Markdown supports headings, lists, checkboxes, and tables. Code blocks use Pygments themes tailored for dark/light terminals. Try ``examples/widgets/markdown_demo.py`` and ``examples/widgets/code_demo.py`` for end-to-end samples.

Table
    Feature-rich table control with column sizing, alignment, zebra striping, sorting, and optional selection/highlighting. Works well for log viewers, data dashboards, and admin lists. Consider pairing with scrollable frames for large datasets or binding button actions to operate on selected rows.

    .. literalinclude:: ../../examples/widgets/table_demo.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/widgets/table_demo.py`` – sorted table with action bar

Tree
    Hierarchical explorer for file systems, menus, or org charts. Nodes can be expanded/collapsed via keyboard or mouse. See ``examples/widgets/tree_demo.py`` and ``tree_indicator_styles_demo.py`` for layout variations.

ListView
    Scrollable vertical list that highlights the selected row. Great for menus, chat transcripts, or search results. Works nicely with ``app.on_action`` handlers that parse the row id (``row_selected_<id>`` pattern).

LogView
    Tail-like streaming buffer with manual/auto-scroll toggles. Supports severity coloring and timestamp columns. Pair it with background tasks to watch long-running jobs.

ProgressBar / Spinner
    Progress indicators for background tasks. ``progressbar`` accepts numeric ``value`` and optional ``label``; ``spinner`` animates automatically if you set ``app.refresh_interval``.

StatusBar
    Sticky footer for breadcrumbs, key hints, or status indicators. Combine with ``{% hstack %}`` sections to align regions left/center/right. ``examples/widgets/statusbar_demo.py`` shows how to surface view-scoped hints.

Notifications
    Inline banners styled by ``tone`` (``info``, ``success``, ``warning``, ``error``). Available as template tags and as programmatic overlays via :class:`wijjit.core.notification_manager.NotificationManager`. Use them for asynchronous feedback or confirmations.

    .. literalinclude:: ../../examples/widgets/notification_demo.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/widgets/notification_demo.py`` – framing actionable hints

Menus & overlays
----------------

DropdownMenu / ContextMenu
    Provided by :mod:`wijjit.elements.menu` and :mod:`wijjit.tags.menu`. Bind to a trigger element (button, list item) and specify menu items with actions. Context menus open on right-click; dropdowns open on left-click or keyboard shortcuts.

    .. literalinclude:: ../../examples/widgets/dropdown_demo.py
       :language: jinja
       :caption: Menu definition from ``examples/widgets/dropdown_demo.py``
       :start-after: TEMPLATE = """
       :end-before: """

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
* Read the example gallery – most widgets live under ``examples/widgets/*_demo.py`` so you can run the exact code showcased here.

Next: learn how to orchestrate modals and overlays in :doc:`modal_dialogs`, then deep dive into interaction layers with :doc:`focus_navigation` and :doc:`mouse_support`.
