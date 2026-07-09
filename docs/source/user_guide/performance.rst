Performance
===========

Wijjit renders through a virtual DOM and a cell-based screen buffer, then writes
only the cells that actually changed. The practical consequence is that a Wijjit
app is cheap to *update*, even when it is expensive to *draw*.

The headline number
-------------------

On a 200x60 terminal, a full repaint of a dashboard (a table, two charts, and a
button row) writes **15,949 bytes**. Advancing the sparkline by one tick writes
**39 bytes**. An idle frame -- one where nothing changed -- writes **nothing at
all**.

That is a ~400x reduction in terminal traffic for a typical update, and it is why
a Wijjit app does not flicker and stays responsive over SSH or a slow serial
link.

What the diff renderer does and does not buy you
------------------------------------------------

It is worth being precise, because the usual intuition is wrong.

The diff renderer is **not** cheaper in CPU than a blind full repaint. It has to
compare every cell in the buffer against the previously displayed one, so a
steady-state frame costs slightly *more* CPU than simply redrawing everything.

What it buys is **I/O and stability**: an unchanged screen produces no output,
and a small change produces a small write. Terminal writes are the expensive,
latency-bound part of a TUI, and they are what causes visible flicker. Trading a
little CPU for a large reduction in bytes is the right trade for a terminal
application, and it is the trade Wijjit makes.

Separately, the virtual-DOM reconciler exists to preserve *state* -- cursor
position, scroll offset, selection -- across re-renders, and to avoid rebuilding
element objects on every frame. That is a correctness and ergonomics win rather
than a throughput one.

Measured results
----------------

Run ``uv run python scripts/bench_perf.py`` to reproduce these on your own
machine. Timings depend on your CPU and system load; treat them as indicative.
The byte counts are deterministic and are regression-tested in
``tests/core/test_diff_render_bytes.py``.

Terminal I/O per frame
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 12 16 12 14 12

   * - Scenario
     - Size
     - Full repaint
     - Idle frame
     - One change
     - Reduction
   * - hello world
     - 80x24
     - 3,364 B
     - 0 B
     - 7 B
     - 481x
   * - hello world
     - 200x60
     - 15,640 B
     - 0 B
     - 7 B
     - 2234x
   * - login form
     - 80x24
     - 3,568 B
     - 0 B
     - 35 B
     - 102x
   * - login form
     - 200x60
     - 15,844 B
     - 0 B
     - 35 B
     - 453x
   * - dashboard (table + charts)
     - 80x24
     - 3,696 B
     - 0 B
     - 39 B
     - 95x
   * - dashboard (table + charts)
     - 200x60
     - 15,949 B
     - 0 B
     - 39 B
     - 409x

Render latency
~~~~~~~~~~~~~~

"Steady state" is the median time to produce one frame in which one small thing
changed -- the cost of an animation tick or a keystroke echo.

Unlike the byte counts, these vary by tens of percent between runs on the same
machine, so they are rounded. Do not read precision into them.

.. list-table::
   :header-rows: 1
   :widths: 30 12 18 18 22

   * - Scenario
     - Size
     - Full repaint
     - Steady state
     - Implied frame rate
   * - hello world
     - 80x24
     - ~2 ms
     - ~2.5 ms
     - ~400 fps
   * - hello world
     - 200x60
     - ~13 ms
     - ~15 ms
     - ~70 fps
   * - login form
     - 80x24
     - ~3 ms
     - ~3.5 ms
     - ~300 fps
   * - dashboard (table + charts)
     - 80x24
     - ~7 ms
     - ~8 ms
     - ~130 fps
   * - dashboard (table + charts)
     - 120x40
     - ~10 ms
     - ~14 ms
     - ~75 fps
   * - dashboard (table + charts)
     - 200x60
     - ~20 ms
     - ~25 ms
     - ~40 fps

Measured on Windows 11, Python 3.13, wijjit 0.1.0.

For context: terminal applications are typically driven by human input, and the
practical ceiling on useful frame rate is the terminal emulator's own refresh
rate. A dashboard that re-renders in under 20 ms at 200x60 will feel immediate.

Startup cost
------------

``import wijjit`` takes roughly **700 ms** in a cold process. Most of that is
``prompt_toolkit`` (~350 ms), which Wijjit imports eagerly for cross-platform
terminal input.

If you are writing a CLI where startup latency matters and the TUI is only one
subcommand, import Wijjit lazily inside that subcommand rather than at module
scope.

What is slow, and what to avoid
-------------------------------

**Screen area dominates.** Render cost scales with ``width x height``, not with
the number of widgets. Going from 80x24 to 200x60 is a 6.25x area increase and
costs roughly 6x the time. A full-screen app on a large monitor is the worst
case.

**There is no virtual scrolling.** Every row of a ``Table``, ``ListView``, or
``Tree`` is laid out on every render, whether or not it is visible. A few
thousand rows is fine; a hundred thousand is not. If you have a very large
dataset, page or filter it before handing it to the element.

**Charts and tables are the expensive widgets.** ``Table`` renders through Rich,
and the charts rasterize to braille or block glyphs. If a frame is slow, those
are the first things to look at.

**Interpolating state into template *source* defeats the compiled-template
cache.** Pass changing values as context variables:

.. code-block:: python

   # Good: the template compiles once and is cached.
   return render_template_string(TEMPLATE, count=app.state.n)

   # Bad: a new template source string on every render, recompiled every time.
   return render_template_string(f"Count: {app.state.n}")

Profiling your own app
----------------------

The headless harness runs the real event loop without a TTY, which makes a
Wijjit app straightforward to profile:

.. code-block:: python

   import cProfile
   import pstats

   from wijjit.testing import WijjitHarness

   with WijjitHarness(app, size=(200, 60)) as h:
       h.tick()  # warm up: first paint, template compile
       profiler = cProfile.Profile()
       profiler.enable()
       h.tick(frames=100)
       profiler.disable()

   pstats.Stats(profiler).sort_stats("tottime").print_stats(20)

Most render time is spent in ``ScreenBuffer`` and ``Cell`` operations. If your
own code shows up above those, that is where to optimize first.
