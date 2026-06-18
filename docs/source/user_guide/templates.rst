Templates & Tags
================

Wijjit’s templating story is “Jinja everywhere.” Views return inline templates (``"template": """…"""``) or point to files in ``template_dir``. During rendering, Wijjit injects:

* ``state`` – the reactive :class:`wijjit.core.state.State` object, available as the named ``state`` variable.
* The keys of your view’s ``data`` dict, flattened into top-level template variables. A ``data`` value of ``{"title": "Home"}`` is referenced as ``{{ title }}`` (not ``{{ data.title }}``).

Those are the only injected names – ``params``, ``app``, and a wrapping ``data`` object are **not** placed in the template context.

The Jinja environment preloads extensions from :mod:`wijjit.tags` so you can describe layouts declaratively.

Layout primitives
-----------------

``{% vstack %}`` and ``{% hstack %}``
    Flexbox-like containers from :mod:`wijjit.tags.layout` that stack children vertically or horizontally. Both accept ``width``, ``height``, ``spacing``, ``padding``, ``margin``, ``align_h``, and ``align_v``. ``{% hstack %}`` additionally accepts ``justify``, ``wrap``, ``gap``, ``row_gap``, and ``column_gap``. Nested stacks are the backbone of most layouts.

``{% frame %}``
    Renders a bordered container (:class:`wijjit.layout.frames.Frame`). Key attributes: ``title``, ``border`` (``single``, ``double``, ``rounded``, or ``none``), ``width``, ``height``, ``padding``, ``scrollable``, ``overflow_x``, ``show_scrollbar``, and ``show_scrollbar_x``. Frames can wrap stacks, inputs, or any other nodes.

To introduce whitespace between sections, use an empty ``{% vstack height=1 %}{% endvstack %}`` or the ``padding``/``spacing`` attributes; there is no dedicated spacer tag.

``{% modal %}``
    Defined in :mod:`wijjit.tags.display`, this tag renders modal shells that can be reused inside overlays; see :doc:`modal_dialogs`.

Every layout tag contributes nodes to the ``LayoutContext`` so the layout engine can compute bounds before painting.

Form & input tags
-----------------

All input tags live in :mod:`wijjit.tags.input` and automatically bind to ``state`` by ``id`` when ``bind=True`` (default).

``{% textinput %}…{% endtextinput %}``
    Single-line input (:class:`wijjit.elements.input.text.TextInput`). Attributes: ``id``, ``placeholder``, ``width``, ``max_length``, ``action`` (triggered on Enter), ``bind``. Example: ``{% textinput id="username" placeholder="handle" width=24 %}{% endtextinput %}``.

``{% textarea %}…{% endtextarea %}``
    Multi-line editor (supports scrolling, custom borders). Attributes: ``id``, ``height``, ``width``, ``placeholder``, ``bind``.

``{% codeeditor %}…{% endcodeeditor %}``
    Syntax-highlighted code editor (:class:`wijjit.elements.input.code_editor.CodeEditor`). Extends ``textarea`` with Pygments-powered highlighting. Attributes: ``id``, ``language`` (programming language or ``"auto"``), ``theme`` (``monokai``, ``dracula``, ``nord``, ``github-light``), ``show_line_numbers``, ``filename_hint``, ``width``, ``height``, ``bind``.

``{% button %}…{% endbutton %}``
    Action buttons. Use ``action="save"`` to emit :class:`wijjit.core.events.ActionEvent`. Optional ``variant`` (``primary``, ``danger``) and ``icon`` attributes help styling.

``{% checkbox %}``, ``{% radiogroup %}``, ``{% select %}``
    High-level inputs for boolean/multi-choice fields. Provide ``options`` as a list of dicts (``{"label": "Admin", "value": "admin"}``) or iterate inside the tag. Checkbox/radio groups expose an ``orientation`` attribute (``"vertical"`` – the default – or ``"horizontal"``).

``{% checkboxgroup %}`` / ``{% radiogroup %}``
    Wrap multiple checkboxes/radios, bind to lists or single values in ``state``.

``{% select %}``
    Dropdown input with optional search/filtering. Provide ``options`` and ``empty_option`` text for placeholder entries.

``{% slider %}…{% endslider %}``
    Numeric input with draggable handle (:class:`wijjit.elements.input.slider.Slider`). Supports keyboard (Left/Right/Home/End) and mouse drag. Attributes: ``id``, ``min``, ``max``, ``value``, ``step``, ``width``, ``float_mode`` (returns float if True), ``label``, ``show_value``, ``bind``.

``{% toggle %}…{% endtoggle %}``
    Boolean switch with visual indicator (:class:`wijjit.elements.input.toggle.Toggle`). Clearer on/off feedback than checkbox. Attributes: ``id``, ``checked``, ``label``, ``label_mode`` (``single`` or ``dual``), ``on_label``, ``off_label``, ``bind``. Colors themeable via ``toggle.on``, ``toggle.off``, ``toggle:focus`` CSS.

Each input element stores its ``id`` on the underlying element so focus, state binding, and change events work automatically. To opt out of binding (for read-only inputs), set ``bind=False`` and manage the value manually via wiring helpers.

Display & data tags
-------------------

``{% table %}``
    Renders :class:`wijjit.elements.display.table.TableElement`. Supports column definitions (``columns=[{"key": "name", "label": "Name", "width": 20}]``), row selection, zebra striping, and custom cell renderers. Use ``data=state.rows`` or pass a literal list.

``{% tree %}``
    Hierarchical data viewer with expand/collapse support. Provide ``nodes`` with ``children`` arrays.

``{% listview %}``
    Scrollable list with optional selection markers.

``{% logview %}``
    Tail-like component for streaming logs (pairs nicely with ``state.watch`` or async generators).

``{% progressbar %}`` and ``{% spinner %}``
    Visual indicators for background tasks. Progress bars accept ``value``, ``max``, ``style`` (display style: ``filled``, ``percentage``, ``gradient``, ``custom``), and ``bar_style`` (visual preset: ``block``, ``thin``, ``thick``, ``equals``, ``arrow``, ``dots``, ``ascii``, ``hash``, ``pipe``, ``square``).

``{% status %}…{% endstatus %}``
    Colored status indicator (:class:`wijjit.elements.display.status_indicator.StatusIndicator`). Non-interactive display for dashboards. Built-in statuses: ``error``, ``warning``, ``success``, ``info``, ``pending``, ``active``, ``inactive``, ``disabled``. Attributes: ``status``, ``label``, ``indicator_style`` (``filled``, ``hollow``, ``square``, ``ascii``), ``custom_statuses`` (dict to add/override colors).

``{% contentview %}…{% endcontentview %}``
    Renders rich body content according to its ``content_type`` attribute – ``"markdown"``, ``"rich"``, ``"code"`` (with ``language=``), ANSI, or ``"plain"`` (the default). There are no standalone ``{% markdown %}`` or ``{% code %}`` tags; the same ``content_type`` attribute is also available on other content-bearing display elements.

``{% statusbar %}``
    Fixed-height footer bar for application state, mode indicators, or help text.

Notifications & dialogs
-----------------------

Notifications are created through the app/overlay API (the notification manager), not a template tag – there is no ``{% notification %}`` tag. For modal workflows:

* ``{% confirmdialog %}``, ``{% alertdialog %}``, ``{% inputdialog %}`` from :mod:`wijjit.tags.dialogs`.
* ``{% dropdown %}`` / ``{% contextmenu %}`` from :mod:`wijjit.tags.menu` to wire menu overlays to target elements.

Dialogs typically emit actions (``confirm``, ``cancel``) that you handle with ``@app.on_action``. They also integrate with :class:`wijjit.core.overlay.OverlayManager` so focus is trapped and background dimming happens automatically.

Binding data into templates
---------------------------

Inside any template you can reference:

* ``state`` – backing store for bound inputs, lists, toggles, etc.
* Top-level variables flattened from the view’s ``data`` dict – great for derived values or expensive lookups computed in your ``data`` callable (e.g., ``{{ title | default("overview") }}``).
* Utility filters – everything from standard Jinja filters to custom helpers you register via ``app.renderer.env.filters``.

Use ``{% set total = state.items | length %}`` for quick calculations, or compute in Python if it cleanly lives in your domain logic.

Best practices
--------------

* **Keep templates declarative** – move heavy data manipulation into Python ``data`` callables so templates stay focused on layout.
* **Name every interactive element** – predictable ``id`` values make debugging focus/state wiring easier.
* **Prefer stacks over manual padding** – ``{% vstack padding=1 spacing=1 %}`` usually beats sprinkling blank lines.
* **Extract macros** – Jinja macros (``{% macro toolbar(title) %}…{% endmacro %}``) help reuse repeated component combinations.
* **Co-locate with views** – for larger apps, store templates under ``templates/<view>.tui`` and load them with ``"template_file": "dashboard.tui"``.

With these building blocks you can mix-and-match UI primitives without writing a single cursor-math statement. Continue with :doc:`event_handling` to make those templates interactive.
