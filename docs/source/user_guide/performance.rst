Performance
===========

Wijjit renders through a virtual DOM and a cell-based screen buffer, then writes
only the cells that actually changed. The practical consequence is that a Wijjit
app is cheap to *update*, even when it is expensive to *draw*.

The headline number
-------------------

On a 200x60 terminal, a full repaint of a dashboard (a table, two charts, and a
button row) writes **15,980 bytes**. Advancing the sparkline by one tick writes
**37 bytes**. An idle frame -- one where nothing changed -- writes **nothing at
all**.

That is a ~430x reduction in terminal traffic for a typical update, and it is why
a Wijjit app does not flicker and stays responsive over SSH or a slow serial
link.

What the diff renderer buys you
-------------------------------

The primary win is **I/O and stability**: an unchanged screen produces no output,
and a small change produces a small write. Terminal writes are the expensive,
latency-bound part of a TUI, and they are what causes visible flicker. Lead with
the bytes -- they are deterministic and regression-tested, while timings move
with your CPU and system load.

The incremental path is **also cheaper in CPU** than a full repaint. This is
worth stating explicitly because it was not always true, and older advice said
the opposite. The path a running app actually uses starts each frame from a copy
of the previous one, skips elements whose content and position did not change
(via ``render_signature()``), and diffs only what moved -- so a localized edit
does work proportional to *what changed* rather than to the size of the view.
Steady state is roughly 2x cheaper than a full repaint on a form of independent
widgets. The gain is smaller on the dashboard below, whose ``Table`` has no skip
signature yet and so repaints wholesale.

A full repaint -- the worst case, on first paint or a terminal resize -- still
touches every cell.

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
     - 3,676 B
     - 0 B
     - 37 B
     - 99x
   * - dashboard (table + charts)
     - 200x60
     - 15,980 B
     - 0 B
     - 37 B
     - 432x

Render latency
~~~~~~~~~~~~~~

"Steady state" is the median time to produce one frame in which one small thing
changed -- the cost of an animation tick or a keystroke echo.

Unlike the byte counts, these vary by tens of percent between runs on the same
machine, so they are rounded. Do not read precision into them, and prefer the
byte figures above when comparing.

.. list-table::
   :header-rows: 1
   :widths: 34 14 26 26

   * - Scenario
     - Size
     - Full repaint
     - Steady state
   * - hello world
     - 80x24
     - ~2 ms
     - ~1.5 ms
   * - hello world
     - 200x60
     - ~6 ms
     - ~3 ms
   * - login form
     - 80x24
     - ~2.5 ms
     - ~2 ms
   * - login form
     - 200x60
     - ~6 ms
     - ~3.5 ms
   * - dashboard (table + charts)
     - 80x24
     - ~7 ms
     - ~6.5 ms
   * - dashboard (table + charts)
     - 120x40
     - ~7.5 ms
     - ~7 ms
   * - dashboard (table + charts)
     - 200x60
     - ~10 ms
     - ~6.5 ms

Measured on Windows 11, Python 3.13, wijjit 0.1.0.

Steady state beats a full repaint in every row, which is the skip-unchanged path
doing its job. The margin is widest where the changed widget is small relative to
the view (hello world at 200x60) and narrowest on the dashboard, whose ``Table``
still repaints wholesale.

For context: terminal applications are driven by human input, so what matters is
that a frame lands well inside a keystroke's worth of time -- not a frame-rate
number. A dashboard that re-renders in ~10 ms at 200x60 feels immediate, and the
bytes it writes are what determine whether that holds over SSH.

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
