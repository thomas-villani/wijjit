Components
==========

Wijjit ships with a wide range of input and display components. They are implemented under :mod:`wijjit.elements` and exposed to templates through :mod:`wijjit.tags`. This section summarizes what’s available and when to reach for each widget.

The examples referenced here are managed under ``examples/``. We pull live snippets with ``literalinclude`` so the docs stay in sync with the runnable demos—open the referenced script if you want to try it yourself.

Form inputs
-----------

TextInput / TextArea
    Single-line and multi-line editors (:mod:`wijjit.elements.input.text`). Support placeholder text, max length, width/height control, Enter actions, selection, copy/paste (via ``pyperclip``), and cursor movement. Both emit ``ChangeEvent`` on edits and update ``state[id]`` automatically. Use ``bind=False`` to manage the value manually (useful for formatted or derived inputs) and attach ``action=...`` to submit on Enter.

    .. literalinclude:: ../../../examples/basic/simple_input_test.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/basic/simple_input_test.py`` – binding a ``textinput`` to ``state``

    ``textarea`` adds scrollbars, selection APIs, and clipboard shortcuts. It's ideal for log editing, notes, or prompt composition. Pair it with derived state to show live counts, as demonstrated below.

    .. literalinclude:: ../../../examples/widgets/textarea_demo.py
       :language: jinja
       :caption: Template excerpt from ``examples/widgets/textarea_demo.py``
       :dedent:
       :start-after: return render_template_string(
       :end-before: lines=content.count

CodeEditor
    Syntax-highlighted code editor (:mod:`wijjit.elements.input.code_editor`). Extends ``TextArea`` with syntax highlighting powered by Pygments. Supports 500+ programming languages, multiple color themes (monokai, dracula, nord, github-light), line numbers, and automatic language detection.

    Key attributes:

    * ``language`` - Programming language for highlighting (``python``, ``javascript``, ``rust``, etc.) or ``"auto"`` for detection
    * ``theme`` - Color theme (``monokai``, ``dracula``, ``nord``, ``github-light``)
    * ``show_line_numbers`` - Display line numbers in the gutter (default: ``True``)
    * ``filename_hint`` - Helps auto-detection when ``language="auto"``

    Performance is optimized for large files through per-line token caching and debounced re-tokenization during edits. Inherits all ``TextArea`` features including selection, clipboard support, and scrolling.

    .. literalinclude:: ../../../examples/widgets/code_editor_demo.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/widgets/code_editor_demo.py`` - syntax highlighting with theme switching

DataGrid
    Spreadsheet-like data entry element (:mod:`wijjit.elements.input.datagrid`). Implements VisiCalc/Lotus 1-2-3 style editing with an entry line at the top for data input. Supports keyboard navigation (arrow keys, Tab, Enter), mouse interaction (click cells, scroll), and automatic state binding.

    Key attributes:

    * ``data`` - 2D list of cell values (list of rows)
    * ``columns`` - List of column headers (strings or dicts with ``key``, ``label``, ``width``)
    * ``width`` / ``height`` - Grid dimensions in characters
    * ``show_row_numbers`` - Display row numbers on the left (default: ``True``)
    * ``editable`` - Allow cell editing (default: ``True``)
    * ``show_scrollbar`` - Show scrollbars when content exceeds viewport (default: ``True``)

    Navigation:

    * **Arrow keys** - Move between cells
    * **Tab / Shift+Tab** - Move to next/previous cell
    * **Enter** - Confirm edit and move down, or start editing current cell
    * **Escape** - Cancel current edit
    * **Mouse click** - Select cell, double-click to edit
    * **Mouse scroll** - Scroll through large datasets

    Data formats (input and output):

    * **List of lists** - Default format: ``[["A", "B"], ["C", "D"]]``
    * **List of dicts** - Each row as a dict: ``[{"name": "John", "age": 30}, ...]``
    * **pandas DataFrame** - Automatically converts to/from DataFrames (pandas optional)

    .. code-block:: jinja

       {% datagrid id="spreadsheet" width=60 height=15 %}
           columns:
             - {key: "name", label: "Name", width: 20}
             - {key: "price", label: "Price", width: 10}
             - {key: "qty", label: "Quantity", width: 10}
           data:
             - ["Widget", "9.99", "100"]
             - ["Gadget", "19.99", "50"]
       {% enddatagrid %}

    Working with DataGrid state:

    .. code-block:: python

       # Get data as list of lists (default)
       data = app.state["spreadsheet"]

       # Get data as list of dicts
       from wijjit.elements.input.datagrid import DataGrid
       grid = app.get_element_by_id("spreadsheet")
       data_as_dicts = grid.get_data_as_dicts()

       # Get data as pandas DataFrame (if pandas available)
       df = grid.get_data_as_dataframe()

       # Set data from various formats
       grid.set_data([["A", "B"], ["C", "D"]])  # list of lists
       grid.set_data([{"col1": "A", "col2": "B"}])  # list of dicts
       grid.set_data(pandas_df)  # DataFrame

    See ``examples/widgets/datagrid_demo.py`` for a complete inventory management example with add/delete row functionality.

Button
    Clickable action trigger (:mod:`wijjit.elements.input.button`). Attributes: ``variant`` (``primary``, ``secondary``, ``danger``), ``icon``, ``disabled``. Useful for both primary actions and inline icon buttons. Remember that ``action`` ids participate in handler routing—keep them short verbs (``save``, ``cancel``) and reuse them across views to share behavior.

Checkbox / CheckboxGroup
    Toggle booleans or sets of values. Groups accept ``options`` and maintain a list in state (``state.selected_tags``). Support tri-state rendering, keyboard navigation, and spacing options. Use them for preference panes or wizards.

    .. literalinclude:: ../../../examples/widgets/checkbox_demo.py
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

Slider
    Numeric input with draggable handle (:mod:`wijjit.elements.input.slider`). Supports both integer and float modes, keyboard navigation (Left/Right arrows, Home/End), and mouse interaction (click to set, drag to adjust).

    Key attributes:

    * ``min`` - Minimum value (default: 0)
    * ``max`` - Maximum value (default: 100)
    * ``value`` - Initial value (defaults to min)
    * ``step`` - Increment for keyboard navigation (default: 1)
    * ``width`` - Track width in characters (default: 20)
    * ``float_mode`` - Return float instead of int (default: ``False``)
    * ``label`` - Optional label before slider
    * ``show_value`` - Display current value after slider (default: ``True``)

    .. code-block:: jinja

       {# Integer slider #}
       {% slider id="volume" min=0 max=100 value=50 %}{% endslider %}

       {# Float slider with decimal step #}
       {% slider id="opacity" min=0.0 max=1.0 step=0.1 float_mode=True label="Opacity" %}{% endslider %}

    See ``examples/widgets/slider_demo.py`` for integer and float slider examples.

Toggle
    Boolean switch with visual indicator (:mod:`wijjit.elements.input.toggle`). Provides clearer on/off feedback than a checkbox with colored block characters. Supports single label mode (label after switch) and dual label mode (labels on both sides).

    Key attributes:

    * ``checked`` - Initial state (default: ``False``)
    * ``label`` - Label text for single mode
    * ``label_mode`` - ``single`` (default) or ``dual``
    * ``on_label`` - "On" text for dual mode (default: "ON")
    * ``off_label`` - "Off" text for dual mode (default: "OFF")

    Colors are themeable via CSS: ``toggle.on``, ``toggle.off``, ``toggle:focus``.

    .. code-block:: jinja

       {# Single mode: switch + label #}
       {% toggle id="dark_mode" label="Dark Mode" %}{% endtoggle %}

       {# Dual mode: OFF [switch] ON #}
       {% toggle id="theme" label_mode="dual" off_label="Light" on_label="Dark" %}{% endtoggle %}

    See ``examples/widgets/toggle_demo.py`` for single and dual mode examples.

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
    * ``border`` - Border style: ``single``, ``double``, ``rounded``, or ``none``
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

    .. literalinclude:: ../../../examples/widgets/table_demo.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/widgets/table_demo.py`` – sorted table with action bar

Tree
    Hierarchical explorer for file systems, menus, or org charts. Nodes can be expanded/collapsed via keyboard or mouse. See ``examples/widgets/tree_demo.py`` and ``tree_indicator_styles_demo.py`` for layout variations.

ListView
    Scrollable vertical list that highlights the selected row. Great for menus, chat transcripts, or search results. Works nicely with ``app.on_action`` handlers that parse the row id (``row_selected_<id>`` pattern).

LogView
    Tail-like streaming buffer with manual/auto-scroll toggles. Supports severity coloring and timestamp columns. Pair it with background tasks to watch long-running jobs.

StatusIndicator
    Colored status indicator with extensible presets (:mod:`wijjit.elements.display.status_indicator`). Displays a colored circle (or other shape) to indicate status. Non-interactive display element perfect for dashboards and system status displays.

    Built-in statuses: ``error`` (red), ``warning`` (yellow), ``success`` (green), ``info`` (blue), ``pending`` (cyan), ``active`` (bright green), ``inactive`` (dim), ``disabled`` (gray).

    Key attributes:

    * ``status`` - Status name (default: ``info``)
    * ``label`` - Optional label text after indicator
    * ``indicator_style`` - Shape: ``filled`` (default), ``hollow``, ``square``, ``ascii``
    * ``custom_statuses`` - Dict to add/override status colors

    .. code-block:: jinja

       {# Built-in statuses #}
       {% status status="success" label="Connected" %}{% endstatus %}
       {% status status="error" label="Failed" %}{% endstatus %}
       {% status status="warning" label="Degraded" %}{% endstatus %}

       {# Custom status with color #}
       {% status status="processing" custom_statuses={"processing": "magenta"} label="Working..." %}{% endstatus %}

       {# Different indicator styles #}
       {% status status="info" indicator_style="hollow" label="Hollow" %}{% endstatus %}
       {% status status="info" indicator_style="square" label="Square" %}{% endstatus %}

    See ``examples/widgets/status_indicator_demo.py`` for a complete dashboard example.

ProgressBar / Spinner
    Progress indicators for background tasks. ``progressbar`` accepts numeric ``value`` and optional ``label``; ``spinner`` animates automatically if you set ``app.refresh_interval``.

    **ProgressBar** supports multiple display and visual styles:

    * **Display styles** (``style`` attribute): ``filled`` (default), ``percentage``, ``gradient``, ``custom``
    * **Bar styles** (``bar_style`` attribute): Visual presets for the progress bar characters

      - ``block`` (default) - Solid Unicode block characters
      - ``thin`` - Thin horizontal line
      - ``thick`` - Heavy horizontal line
      - ``equals`` - Classic ``====`` style
      - ``arrow`` - Arrow/chevron ``>>>>`` style
      - ``dots`` - Bullet dot characters
      - ``ascii`` - Pure ASCII (``#`` and ``-``)
      - ``hash`` - Hash marks with spaces
      - ``pipe`` - Pipe characters
      - ``square`` - Square box characters

    Example with different bar styles:

    .. code-block:: jinja

        {% progressbar id="download" value=state.progress bar_style="equals" color="green" %}{% endprogressbar %}
        {% progressbar id="upload" value=state.upload bar_style="arrow" style="gradient" %}{% endprogressbar %}
        {% progressbar id="cpu" value=state.cpu bar_style="thin" %}{% endprogressbar %}

    See ``examples/widgets/progress_demo.py`` for a complete demonstration of all bar styles.

StatusBar
    Sticky footer for breadcrumbs, key hints, or status indicators. Combine with ``{% hstack %}`` sections to align regions left/center/right. ``examples/widgets/statusbar_demo.py`` shows how to surface view-scoped hints.

Notifications
    Inline banners styled by ``tone`` (``info``, ``success``, ``warning``, ``error``). Available as template tags and as programmatic overlays via :class:`wijjit.core.notification_manager.NotificationManager`. Use them for asynchronous feedback or confirmations.

    .. literalinclude:: ../../../examples/widgets/notification_demo.py
       :language: python
       :pyobject: main_view
       :caption: ``examples/widgets/notification_demo.py`` – framing actionable hints

ImageView
    Renders raster images as ASCII/ANSI art in the terminal (:mod:`wijjit.elements.display.imageview`). Requires the ``images`` extra (``pip install wijjit[images]``), which pulls in Pillow. Exposed via the ``{% imageview %}`` tag (registered alias: ``Image``). Accepts a file path, raw bytes, or a PIL ``Image`` as ``src`` and auto-binds it to ``state[id]`` unless ``bind=False``.

    Key attributes:

    * ``src`` - Image source: file path, bytes, or PIL ``Image``
    * ``width`` / ``height`` - Size spec: int, ``"auto"``, ``"fill"``, or ``"50%"`` (default: ``"auto"``)
    * ``braille`` - Use braille mode for black-and-white rendering (default: ``False``)
    * ``invert`` - Invert the threshold in braille mode (default: ``False``)
    * ``background`` - Background RGB tuple for transparent pixels (default: ``(0, 0, 0)``)

    .. code-block:: jinja

       {% imageview id="logo" src="assets/logo.png" width=40 %}{% endimageview %}

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

    .. literalinclude:: ../../../examples/widgets/dropdown_demo.py
       :language: jinja
       :caption: Menu definition from ``examples/widgets/dropdown_demo.py``
       :start-after: TEMPLATE = """
       :end-before: """

Modal
    Base container for custom dialogs. The base modal element is :class:`wijjit.elements.display.modal.ModalElement`; the higher-level dialog subclasses (``ConfirmDialog``, ``AlertDialog``, ``TextInputDialog``) live in :mod:`wijjit.elements.modal`. Drive it from a template with ``{% modal id=... visible="state_key" %}...{% endmodal %}`` and combine with :doc:`modal_dialogs` for confirm/alert/input flows. Supports focus trapping, dimmed background, and layering via :class:`wijjit.core.overlay.OverlayManager`.

NotificationElement
    For toast-style notifications. Usually managed through :class:`wijjit.core.notification_manager.NotificationManager`.

Container widgets
-----------------

TabbedPanel
    Tabbed container for organizing content into switchable panels (:mod:`wijjit.elements.display.tabbed_panel`). Each tab displays a separate frame of content, with keyboard and mouse navigation between tabs. Ideal for settings panels, multi-page forms, or dashboards with distinct sections.

    Key attributes:

    * ``tab_position`` - Position of tabs: ``top`` (default), ``bottom``, ``left``, ``right``
    * ``width`` / ``height`` - Panel dimensions
    * ``border`` - Border style: ``single`` (default), ``double``, ``rounded``
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

Pager
    Paged container that shows one ``{% page %}`` at a time with built-in navigation (:mod:`wijjit.elements.display.pager`). Useful for wizards, slideshows, onboarding flows, or any sequential multi-step UI. Each child ``{% page %}`` is a self-contained frame; the pager renders a "Page X of Y" indicator and Prev/Next controls.

    Key attributes:

    * ``nav_position`` - Position of navigation controls: ``top``, ``bottom`` (default), or ``both``
    * ``show_indicator`` - Show the "Page X of Y" indicator (default: ``True``)
    * ``show_titles`` - Show the page title in the indicator (default: ``False``)
    * ``loop`` - Wrap from the last page back to the first (default: ``False``)
    * ``current_page`` - State key name for page binding, or an initial page index (default: ``0``)
    * ``width`` / ``height`` - Pager dimensions (default: 60 x 20)
    * ``border`` - Border style: ``single`` (default), ``double``, ``rounded``, ``none``

    .. code-block:: jinja

       {% pager id="wizard" nav_position="bottom" show_indicator=True %}
           {% page title="Welcome" %}
               Welcome to the setup wizard.
           {% endpage %}
           {% page title="Account" %}
               {% textinput id="username" placeholder="Username" width=30 %}{% endtextinput %}
           {% endpage %}
           {% page title="Done" %}
               All set!
           {% endpage %}
       {% endpager %}

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
