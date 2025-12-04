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

    ``textarea`` adds scrollbars, selection APIs, and clipboard shortcuts. It's ideal for log editing, notes, or prompt composition. Pair it with derived state to show live counts, as demonstrated below.

    .. literalinclude:: ../../examples/widgets/textarea_demo.py
       :language: jinja
       :caption: Template excerpt from ``examples/widgets/textarea_demo.py``
       :start-after: "template": """
       :end-before: """,

CodeEditor
    Syntax-highlighted code editor (:mod:`wijjit.elements.input.code_editor`). Extends ``TextArea`` with syntax highlighting powered by Pygments. Supports 500+ programming languages, multiple color themes (monokai, dracula, nord, github-light), line numbers, and automatic language detection.

    Key attributes:

    * ``language`` - Programming language for highlighting (``python``, ``javascript``, ``rust``, etc.) or ``"auto"`` for detection
    * ``theme`` - Color theme (``monokai``, ``dracula``, ``nord``, ``github-light``)
    * ``show_line_numbers`` - Display line numbers in the gutter (default: ``True``)
    * ``filename_hint`` - Helps auto-detection when ``language="auto"``

    Performance is optimized for large files through per-line token caching and debounced re-tokenization during edits. Inherits all ``TextArea`` features including selection, clipboard support, and scrolling.

    .. literalinclude:: ../../examples/widgets/code_editor_demo.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/widgets/code_editor_demo.py`` - syntax highlighting with theme switching

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

Link
    Inline clickable text element (:mod:`wijjit.elements.display.link`). Renders as styled text that can be focused and activated via keyboard (Enter/Space) or mouse click. Perfect for inline navigation, action triggers, or any clickable text that shouldn't look like a button.

    Key attributes:

    * ``action`` - Action name to trigger when clicked
    * ``class`` - CSS class for styling (e.g., ``text-danger``, ``text-success``)

    .. code-block:: jinja

       {% hstack spacing=3 %}
         {% link action="home" %}Home{% endlink %}
         {% link action="settings" %}Settings{% endlink %}
         {% link action="logout" class="text-danger" %}Logout{% endlink %}
       {% endhstack %}

    See ``examples/widgets/html_demo.py`` for usage examples alongside HTMLViewer.

Special behaviors:

* ``bind=False`` lets you manage the value manually (useful for derived or formatted inputs).
* ``action`` on inputs triggers when Enter is pressed.
* ``id`` is mandatory for binding; Wijjit auto-generates ids but naming them yourself keeps focus/state debugging easier.

Display widgets
---------------

ContentView
    Unified content display element supporting multiple content types (:mod:`wijjit.elements.display.contentview`). Renders content in various formats with scrolling, borders, and keyboard/mouse navigation. This single component replaces the need for separate markdown, code, and HTML viewers.

    Supported content types (``content_type`` attribute):

    * ``"plain"`` / ``"text"`` - Plain text with word wrapping
    * ``"ansi"`` - Text with ANSI escape codes passed through
    * ``"html"`` - HTML-like markup with ``<b>``, ``<i>``, ``<u>``, ``<s>``, and ``<style>`` tags
    * ``"markdown"`` - Markdown with headings, lists, code blocks, and blockquotes
    * ``"rich"`` - Rich markup with ``[bold]``, ``[red]``, etc.
    * ``"code"`` - Syntax-highlighted code (500+ languages via Pygments)

    Key attributes:

    * ``content_type`` - Content format (default: ``"plain"``)
    * ``width`` / ``height`` - Display dimensions
    * ``border_style`` - Border style: ``single``, ``double``, ``rounded``, or ``none``
    * ``title`` - Optional title in top border
    * ``show_scrollbar`` - Show vertical scrollbar (default: ``True``)

    Code-specific attributes:

    * ``language`` - Programming language for syntax highlighting (default: ``"python"``)
    * ``theme`` - Syntax highlighting theme (default: ``"monokai"``)
    * ``show_line_numbers`` - Display line numbers (default: ``False``)
    * ``line_number_start`` - Starting line number (default: ``1``)

    .. code-block:: jinja

       {# Markdown content #}
       {% contentview id="docs" content_type="markdown" title="Documentation" height=15 %}
       # Welcome

       This is **bold** and *italic* text.

       - Bullet points
       - Multiple items
       {% endcontentview %}

       {# Syntax-highlighted code #}
       {% contentview id="code" content_type="code" language="python" show_line_numbers=true title="Example" %}
       def hello(name: str) -> str:
           return f"Hello, {name}!"
       {% endcontentview %}

       {# HTML-style formatting #}
       {% contentview id="html" content_type="html" title="Styled Text" %}
       <b>Bold</b> and <i>italic</i>
       <style fg="red">Red text</style>
       {% endcontentview %}

    Keyboard controls: Up/Down arrows for line-by-line scrolling, PageUp/PageDown for page scrolling, Home/End to jump to start/end.

    See ``examples/widgets/contentview_demo.py`` for a complete demonstration of all content types.

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

Data Visualization
------------------

Wijjit includes a suite of data visualization components for dashboards, monitoring, and analytics. All chart elements support reactive updates - simply update the data and the chart re-renders automatically. These are provided by :mod:`wijjit.elements.display` and exposed via :mod:`wijjit.tags.charts`.

Sparkline
    Compact inline trend visualization (:mod:`wijjit.elements.display.sparkline`). Perfect for embedding trends alongside text or in dense dashboards. Renders in a single row using braille characters for high resolution.

    Key attributes:

    * ``data`` - List of numeric values
    * ``width`` - Display width in characters (default: 20)
    * ``style`` - Rendering style: ``line`` (braille), ``bar``, or ``dot``
    * ``show_current`` - Display the last value as text
    * ``show_minmax`` - Mark min/max points

    .. code-block:: jinja

       {% sparkline data=cpu_history width=30 style="line" show_current=True %}{% endsparkline %}

BarChart
    Horizontal bar chart with labels (:mod:`wijjit.elements.display.barchart`). Supports scrolling for large datasets, gradient or threshold-based coloring, and value display.

    Key attributes:

    * ``data`` - List of values, tuples ``(label, value)``, or dicts ``{"label": ..., "value": ...}``
    * ``width`` / ``height`` - Display dimensions
    * ``show_values`` - Display numeric values on bars
    * ``color`` - Color mode: ``default``, ``gradient``, or ``threshold``
    * ``max_value`` - Override automatic scaling

    .. code-block:: jinja

       {% barchart data=sales_by_region width=40 height=8 show_values=True color="gradient" %}{% endbarchart %}

ColumnChart
    Vertical column chart with Y-axis (:mod:`wijjit.elements.display.columnchart`). Uses block characters for rendering with optional grid lines and axis labels.

    Key attributes:

    * ``data`` - List of values or labeled data
    * ``width`` / ``height`` - Display dimensions
    * ``show_axis`` - Display Y-axis with tick marks
    * ``show_labels`` - Display X-axis labels
    * ``color`` - Color mode for columns

    .. code-block:: jinja

       {% columnchart data=monthly_revenue width=50 height=12 show_axis=True show_labels=True %}{% endcolumnchart %}

LineChart
    High-resolution line chart using braille characters (:mod:`wijjit.elements.display.linechart`). Each character contains a 2x4 dot grid, enabling smooth curves in terminal displays. Supports multiple series, area fills, and axis display.

    Key attributes:

    * ``data`` - List of values or list of series ``[{"values": [...], "label": ...}, ...]``
    * ``width`` / ``height`` - Display dimensions
    * ``style`` - Rendering style: ``line``, ``area``, or ``dots``
    * ``show_axis`` - Display axes with labels
    * ``show_legend`` - Display series legend (for multi-series)

    .. code-block:: jinja

       {% linechart data=temperature_readings width=60 height=15 style="line" show_axis=True %}{% endlinechart %}

Gauge
    Value indicator with linear or arc styles (:mod:`wijjit.elements.display.gauge`). Ideal for showing percentages, metrics, or bounded values with threshold coloring.

    Key attributes:

    * ``value`` - Current value
    * ``min_value`` / ``max_value`` - Value range (default: 0-100)
    * ``style`` - Display style: ``linear`` (horizontal bar) or ``arc`` (semi-circular)
    * ``color`` - Color mode: ``default``, ``gradient``, or ``threshold``
    * ``label`` - Optional label text above gauge
    * ``unit`` - Unit suffix for value display (e.g., ``%``, ``MB``)
    * ``show_value`` - Display current value
    * ``show_minmax`` - Display min/max labels

    .. code-block:: jinja

       {% gauge value=cpu_usage style="arc" label="CPU" unit="%" color="threshold" %}{% endgauge %}

HeatMap
    2D grid visualization with color intensity (:mod:`wijjit.elements.display.heatmap`). Uses block characters with RGB coloring to represent values. Great for correlation matrices, activity grids, or geographic data.

    Key attributes:

    * ``data`` - 2D list of values ``[[row1...], [row2...], ...]``
    * ``width`` / ``height`` - Display dimensions
    * ``color_scale`` - Color palette: ``viridis``, ``plasma``, ``inferno``, ``cool``, ``hot``, ``greens``, ``blues``, ``reds``
    * ``show_values`` - Display values in cells (space permitting)
    * ``row_labels`` / ``col_labels`` - Optional axis labels

    .. code-block:: jinja

       {% heatmap data=correlation_matrix width=40 height=20 color_scale="viridis" %}{% endheatmap %}

All chart elements support reactive updates through state binding:

.. code-block:: python

   @app.on_action("refresh")
   async def refresh_data(event):
       app.state.update({
           "cpu_history": await fetch_cpu_metrics(),
           "memory_usage": await get_memory_percent()
       })
       # Charts automatically re-render with new data

See ``examples/widgets/charts_demo.py`` for a complete interactive demonstration of all chart types.

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

Container widgets
-----------------

TabbedPanel
    Tabbed container for organizing content into switchable panels (:mod:`wijjit.elements.display.tabbed_panel`). Each tab displays a separate frame of content, with keyboard and mouse navigation between tabs. Ideal for settings panels, multi-page forms, or dashboards with distinct sections.

    Key attributes:

    * ``tab_position`` - Position of tabs: ``top`` (default), ``bottom``, ``left``, ``right``
    * ``width`` / ``height`` - Panel dimensions
    * ``border_style`` - Border style: ``single`` (default), ``double``, ``rounded``
    * ``active_tab_index`` - Initially active tab (default: 0)

    Navigation:

    * **Horizontal tabs** (top/bottom): Left/Right arrows switch tabs
    * **Vertical tabs** (left/right): Up/Down arrows switch tabs
    * **Mouse**: Click on tab labels to switch
    * **Content scrolling**: Up/Down/PageUp/PageDown scroll the active tab's content

    State persistence: The active tab index is automatically saved to ``state[id]`` (where ``id`` is the element's id attribute), preserving the user's tab selection across re-renders.

    .. code-block:: jinja

       {% tabbedpanel id="settings" tab_position="top" width=60 height=20 %}
           {% tab label="General" %}
               General settings content here...
               {% checkbox id="dark_mode" label="Dark Mode" %}{% endcheckbox %}
               {% checkbox id="notifications" label="Enable Notifications" %}{% endcheckbox %}
           {% endtab %}
           {% tab label="Advanced" %}
               Advanced settings content here...
               {% textinput id="api_key" placeholder="API Key" width=40 %}{% endtextinput %}
           {% endtab %}
           {% tab label="About" %}
               Application version 1.0.0
               Built with Wijjit
           {% endtab %}
       {% endtabbedpanel %}

    See ``examples/widgets/tabbedpanel_demo.py`` for a complete interactive demonstration with all tab positions.

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
