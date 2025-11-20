Templates & Tags
================

Wijjit’s templating story is “Jinja everywhere.” Views return inline templates (``"template": """…"""``) or point to files in ``template_dir``. During rendering, Wijjit injects:

* ``state`` – the reactive :class:`wijjit.core.state.State` object.
* ``params`` – any parameters supplied to ``app.navigate(..., params=...)``.
* ``app`` – the running :class:`wijjit.core.app.Wijjit` instance (use sparingly).
* ``data`` – the dict returned by your view’s ``data`` callable or literal.

The Jinja environment preloads extensions from :mod:`wijjit.tags` so you can describe layouts declaratively.

Layout primitives
-----------------

``{% vstack %}`` and ``{% hstack %}``
    Flexbox-like containers from :mod:`wijjit.tags.layout` that stack children vertically or horizontally. Accept ``width``, ``height``, ``spacing``, ``padding``, ``margin``, ``align_h``, ``align_v``, and ``background`` attributes. Nested stacks are the backbone of most layouts.

``{% frame %}``
    Renders a bordered container (:class:`wijjit.layout.frames.Frame`). Key attributes: ``title``, ``border`` (``single``, ``double``, ``rounded``), ``width``, ``height``, ``padding``, ``scrollable``/``overflow_y``/``overflow_x``, and ``style`` presets. Frames can wrap stacks, inputs, or any other nodes.

``{% spacer %}`` (coming from helper macros in examples)
    Use an empty ``{% hstack height=1 %}{% endhstack %}`` or ``padding`` to introduce whitespace between sections.

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

``{% button %}…{% endbutton %}``
    Action buttons. Use ``action="save"`` to emit :class:`wijjit.core.events.ActionEvent`. Optional ``variant`` (``primary``, ``danger``) and ``icon`` attributes help styling.

``{% checkbox %}``, ``{% radiogroup %}``, ``{% select %}``
    High-level inputs for boolean/multi-choice fields. Provide ``options`` as a list of dicts (``{"label": "Admin", "value": "admin"}``) or iterate inside the tag. Checkbox/radio groups expose ``layout`` (“vertical”/“horizontal”), ``legend``, and ``help_text`` attributes.

``{% checkboxgroup %}`` / ``{% radiogroup %}``
    Wrap multiple checkboxes/radios, bind to lists or single values in ``state``.

``{% select %}``
    Dropdown input with optional search/filtering. Provide ``options`` and ``empty_option`` text for placeholder entries.

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
    Visual indicators for background tasks; progress bars accept ``value`` (0–1 or 0–100) and ``label``.

``{% markdown %}`` / ``{% code %}``
    Rich text renderers using the Markdown and Pygments stacks shipped with Wijjit. Provide ``text`` or inline body content.

``{% statusbar %}``
    Fixed-height footer bar for application state, mode indicators, or help text.

Notifications & dialogs
-----------------------

``{% notification %}`` (via display tags) gives you inline banners for success/error/info states. For modal workflows:

* ``{% confirmdialog %}``, ``{% alertdialog %}``, ``{% inputdialog %}`` from :mod:`wijjit.tags.dialogs`.
* ``{% dropdown %}`` / ``{% contextmenu %}`` from :mod:`wijjit.tags.menu` to wire menu overlays to target elements.

Dialogs typically emit actions (``confirm``, ``cancel``) that you handle with ``@app.on_action``. They also integrate with :class:`wijjit.core.overlay.OverlayManager` so focus is trapped and background dimming happens automatically.

Binding data into templates
---------------------------

Inside any template you can reference:

* ``state`` – backing store for bound inputs, lists, toggles, etc.
* ``params`` – navigation parameters (e.g., ``{{ params.tab | default("overview") }}``).
* ``data`` – view-specific context, great for derived values or expensive lookups.
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
