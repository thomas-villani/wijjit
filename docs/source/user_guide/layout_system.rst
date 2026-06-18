Layout System
=============

Wijjit’s layout engine borrows ideas from flexbox and native GUI toolkits. Instead of placing characters manually, you declare stacks, frames, and elements; the engine computes bounds, applies padding, and takes care of scrolling. This chapter covers the primitives available through :mod:`wijjit.layout`.

Mental model
------------

1. **Template tags** (``{% vstack %}``, ``{% frame %}``, etc.) emit layout nodes backed by objects in :mod:`wijjit.layout.engine`.
2. Nodes form a tree rooted at either a stack or frame. Each node specifies width/height behaviour (fixed pixels, percentages, ``fill``, ``auto``) plus alignment hints.
3. On render the engine performs:

   * **Constraint pass** – bottom-up traversal calling ``calculate_constraints`` on each node to derive minimal and preferred sizes.
   * **Assignment pass** – top-down traversal calling ``assign_bounds`` to give every node absolute ``(x, y, width, height)`` coordinates inside the terminal.

4. Elements store their ``Bounds`` and use them during painting. Scroll managers and focus navigation also use these bounds for hit testing.

Sizing options
--------------

Any width/height attribute accepts:

* **Integers** – fixed character/row counts (``width=40``).
* **Percentages** – strings like ``"50%"`` relative to the parent dimension.
* **"fill"** – consume remaining space after fixed/percent siblings have been laid out.
* **"auto"** – use the element’s intrinsic size (``Element.get_intrinsic_size``). Most text-based widgets default to auto height and fill width.

Margins, padding, spacing
-------------------------

* ``margin`` adds space outside a container. Accepts single ints or tuples ``(top, right, bottom, left)``.
* ``padding`` adds inner space between the container border and its children.
* ``spacing`` controls the gap between stacked children.

These attributes are present on both ``{% vstack %}`` and ``{% hstack %}``, so you can fine-tune spacing without sprinkling blank labels.

Stacks
------

``{% vstack %}``
    Arranges children vertically (default ``width="fill"``, ``height="auto"``). ``align_h`` determines how children are aligned horizontally (``left``, ``center``, ``right``, ``stretch``). ``align_v`` controls how the group sits inside the stack’s allotted height (``"stretch"`` by default).

``{% hstack %}``
    Arranges children horizontally. ``{% hstack %}`` accepts a ``justify`` attribute (``flex-start`` – the default – plus ``flex-end``, ``center``, ``space-between``, ``space-around``, ``space-evenly``) to distribute children along the main axis, as well as ``wrap``, ``gap``, ``row_gap``, and ``column_gap``. You can also push items to the edges by inserting a spacer made from an empty ``{% hstack width="fill" %}{% endhstack %}`` between tool groups.

Stacks can contain other stacks, frames, inputs, or display elements. They map to :class:`wijjit.layout.engine.VStack` / :class:`wijjit.layout.engine.HStack`.

Frames
------

``{% frame %}`` wraps content in a bordered box. The ``border`` attribute selects the border (``single``, ``double``, ``rounded``, or ``none``). Beyond visual polish, frames:

* Support scrolling – ``scrollable=true`` enables vertical scrollbars automatically when content exceeds height.
* Manage titlebars – ``title="System Status"`` reserves a line for labels/icons.
* Provide padding defaults – interior padding is ``(0, 1, 0, 1)`` so text does not touch borders.

Internally frames rely on :class:`wijjit.layout.frames.Frame` with :class:`wijjit.layout.frames.FrameStyle` controlling margins, titles, and scrollbar visibility.

Scroll management
-----------------

Any ``ScrollableElement`` (frames, text areas, log views) integrates with :mod:`wijjit.layout.scroll.ScrollManager`. When ``scrollable=True``:

* Wheel events and ``PgUp/PgDn`` keys update the scroll offset.
* Scrollbars render on the right edge if ``show_scrollbar=True``.
* Scroll position is preserved across re-renders because scroll offset is an ephemeral element-state prop that survives reconciliation.

Use scrollable frames to wrap long markdown blocks, tables, or nested layouts.

Horizontal scrolling
~~~~~~~~~~~~~~~~~~~~

Frames also support horizontal scrolling when content exceeds the frame width. Enable it with these attributes:

* ``overflow_x`` - Control horizontal overflow behaviour:

  * ``"auto"`` - Show horizontal scrollbar only when content exceeds width
  * ``"scroll"`` - Always show horizontal scrollbar
  * ``"hidden"`` - Clip content without scrollbar (default)

* ``show_scrollbar_x`` - Explicitly control horizontal scrollbar visibility (default: ``False``)

.. code-block:: jinja

   {% frame width=60 height=15 scrollable=true
            overflow_x="auto" show_scrollbar_x=true %}
       Content that may exceed the frame width...
   {% endframe %}

Keyboard controls for horizontal scrolling:

* **Left/Right arrows** - Scroll horizontally (when frame has focus)
* **Shift+Left/Right** - Page scroll horizontally
* **Shift+Mouse wheel** - Horizontal scroll via mouse

Horizontal scroll offset is preserved across re-renders alongside the vertical scroll offset, since both are ephemeral element-state props that survive reconciliation.

See ``examples/advanced/horizontal_scroll_demo.py`` for a demonstration of combined vertical and horizontal scrolling.

Alignment & distribution
------------------------

``align_h`` and ``align_v`` exist on both stacks and frames:

* ``stretch`` – child fills available dimension (default in many cases).
* ``left``, ``center``, ``right`` – typical alignments.
* ``top``, ``middle``, ``bottom`` – vertical equivalents.

For fine-grained control, mix fixed-width children with ``width="fill"`` siblings to push items to edges (toolbar patterns).

Responsive techniques
---------------------

* **Percentages** – combine ``width="30%"`` and ``width="70%"`` columns in an ``hstack`` to mimic CSS grid behaviour.
* **Breakpoints** – inspect the terminal size with ``shutil.get_terminal_size()`` (e.g. ``shutil.get_terminal_size().columns``) inside your view and switch templates/layouts when the terminal is narrow.
* **Conditional stacks** – use Jinja ``{% if %}`` to swap between vertical and horizontal arrangements when space is limited.

Debugging layouts
-----------------

* A ``WIJJIT_DEBUG_LAYOUT`` environment variable to print layout trees is planned but not yet implemented.
* Temporarily set ``border="double"`` and ``title`` attributes to visualize container boundaries.
* Log bounds: each element exposes ``element.bounds`` after a render; printing them inside handlers can reveal unexpected sizes.

Checklist
---------

1. Start with a ``frame`` or root ``vstack`` that fills the screen.
2. Use nested stacks to represent rows/columns.
3. Assign ``width``/``height`` only where you need explicit sizing; let other nodes auto-measure.
4. Turn on scrolling whenever content is unbounded.
5. When performance matters, minimize deeply nested frames—stacks are lighter.

With the layout system under control, you can focus on the widgets themselves. Continue to :doc:`components` for a catalogue of available elements.
