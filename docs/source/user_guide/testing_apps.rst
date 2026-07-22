Testing Your App
================

Wijjit ships a headless **test runner** so you can drive a real application the
way a user would -- pressing keys, typing, clicking, scrolling, advancing
animations -- and then assert on what the app renders, all without a TTY. The
same runner powers quick command-line inspection of a demo and a set of pytest
fixtures for your own suite.

This page covers testing *your* Wijjit app. For contributing to the framework
itself, see :doc:`../developer_guide/testing`.

.. note::

   The runner feeds scripted input through the *same* event-loop dispatch path
   used in production. Focus traversal, modal blocking, overlay compositing, and
   async handler dispatch all run exactly as they do for a real user, so a test
   exercises the real interaction model rather than a mock of it.

The harness
-----------

:class:`wijjit.testing.WijjitHarness` wraps a
:class:`~wijjit.core.app.Wijjit` app, renders it at a fixed terminal size, and
exposes synchronous methods to drive and inspect it. Use it as a context
manager so setup and teardown are automatic:

.. code-block:: python

    from wijjit import Wijjit, render_template_string
    from wijjit.testing import WijjitHarness

    app = Wijjit(initial_state={"name": "", "status": "ready"})

    @app.view("main", default=True)
    def main_view():
        return render_template_string(
            """
            {% frame title="Login" border="single" width=40 %}
              {% vstack spacing=1 padding=1 %}
                {{ state.status }}
                {% textinput id="name" placeholder="name" width=20 %}{% endtextinput %}
                {% button action="greet" %}Greet{% endbutton %}
              {% endvstack %}
            {% endframe %}
            """
        )

    @app.on_action("greet")
    def greet(event=None):
        app.state["status"] = "Hello " + (app.state["name"] or "world")

    def test_greeting():
        with WijjitHarness(app, size=(40, 12)) as h:
            h.press("tab")        # focus the text input
            h.type("Ada")
            h.press("tab")        # focus the Greet button
            h.press("enter")      # activate the "greet" action
            h.assert_text("Hello Ada")

Every input method returns the harness, so calls chain:
``h.press("tab").type("Ada").press("enter")``.

.. note::

   The leading ``press("tab")`` is needed because this template does not mark
   any field ``autofocus=True``, so the app starts with nothing focused. If you
   add ``autofocus`` to the input, drop that Tab - otherwise it moves focus
   *past* the input and the test types into the button.

   Counting Tab presses from an assumed starting point is brittle in general:
   the app object is usually shared across tests, and focus survives between
   them. Prefer ``app.focus_element_by_id("name")`` inside the harness block
   when a test needs a specific element focused.

Driving input
-------------

All input methods are synchronous; the harness pumps the async event loop
internally on a private loop, so your test code stays flat.

* ``press(key)`` -- press one key. Accepts a friendly name (``"enter"``,
  ``"tab"``, ``"shift+tab"``, ``"up"``, ``"esc"``, ``"backspace"``, ...), a
  control chord (``"ctrl+q"``), or a single character.
* ``type(text)`` -- type a string one character at a time into the focused
  element.
* ``key(key_obj)`` -- enqueue a raw :class:`wijjit.terminal.input.Key` when you
  need full control over key type or escape sequence.
* ``click(x, y, button="left", count=1)`` -- click a screen cell (0-based).
  ``count=2`` produces a double-click; ``button`` is ``"left"``, ``"middle"``,
  or ``"right"`` (right-click opens context menus).
* ``scroll(x, y, direction="down", amount=1)`` -- send wheel events at a cell.
* ``tick(frames=1)`` -- advance animation frames (spinners, progress) and
  re-render, without waiting on a wall clock.

.. code-block:: python

    with WijjitHarness(app, size=(80, 24)) as h:
        h.press("tab")
        h.type("admin")
        h.click(10, 6)          # routed through the real mouse router
        h.scroll(40, 12, "down", amount=3)
        h.tick(frames=5)        # advance a spinner five frames

Waiting for asynchronous updates
--------------------------------

When a view resolves asynchronously, a background task updates ``state``, a
notification expires, or an animation needs to reach a target frame, the UI
settles over several frames rather than immediately. Use ``wait_for`` /
``wait_for_text`` instead of guessing a frame count:

.. code-block:: python

    with WijjitHarness(app, size=(80, 24)) as h:
        h.press("enter")                                    # kicks off async work
        h.wait_for(lambda: h.state["status"] == "done")     # pump until settled
        h.wait_for_text("Loaded")                           # or wait for output
        h.assert_text("Loaded")

``wait_for(predicate, *, frames=100, tick=False)`` pumps one frame at a time --
rendering and yielding to any pending asyncio tasks -- and re-checks
``predicate`` after each, returning as soon as it is true. ``wait_for_text`` is
sugar for waiting on rendered output.

The harness has **no wall clock** -- rendering is deterministic and
frame-driven -- so the timeout is a *frame budget*, not seconds. This keeps
waits reproducible across machines and CI. If the condition never holds within
``frames`` frames, both methods raise ``TimeoutError`` with the final screen
included for context. Pass ``tick=True`` to also advance one animation frame per
iteration when the condition depends on spinner/animation progress.

Inspecting the result
----------------------

* ``screen()`` -- the rendered screen as plain text (no ANSI).
* ``screen_ansi()`` -- the screen as an ANSI string, with styling.
* ``lines()`` -- the screen as a list of plain-text rows.
* ``find_text(text)`` -- whether ``text`` appears anywhere on screen.
* ``tree()`` -- the last rendered :class:`~wijjit.core.vdom.VNode` tree (the
  "DOM"), or ``None`` for a plain-text template.
* ``state`` -- the app's reactive :class:`~wijjit.core.state.State`.
* ``focused`` -- the currently focused element, if any. Non-``None`` on the very
  first frame when some element declares ``autofocus``; otherwise ``None`` until
  the first Tab.
* ``running`` -- whether the event loop is still running (``False`` after quit).

Assertions
----------

The harness bundles assertions that fail with useful context (the offending
screen or tree) rather than a bare ``False``:

* ``assert_text(text)`` -- assert ``text`` is visible; the failure message
  includes the full screen.
* ``assert_no_errors()`` -- assert the app reported no render, action, or
  background-task errors while the harness drove it. It catches errors the app
  logged and kept running through, so a template that raises mid-render is caught
  here even if the screen still looks plausible.
* ``assert_tree_contains(type=..., key=..., props=...)`` -- assert a matching
  VNode exists in the tree (match by type, reconciliation key/id, and/or a
  subset of props).
* ``assert_screen(snapshot)`` -- compare the plain-text screen against a
  `syrupy <https://github.com/syrupy-project/syrupy>`_ ``snapshot`` fixture.

.. code-block:: python

    def test_renders_cleanly():
        with WijjitHarness(app, size=(80, 24)) as h:
            h.press("tab")
            h.assert_no_errors()
            h.assert_tree_contains(type="Button", props={"action": "greet"})

Pytest fixtures
---------------

Installing Wijjit registers a ``pytest11`` plugin, so two factory fixtures are
available in any suite with no ``conftest.py`` wiring (opt out per run with
``-p no:wijjit``):

* ``wijjit_make_app`` -- build a :class:`~wijjit.core.app.Wijjit` from a
  template string (via :func:`~wijjit.testing.app_from_template`) or pass an
  existing app through unchanged.
* ``wijjit_harness`` -- build and **start** a
  :class:`~wijjit.testing.WijjitHarness` from an app *or* a template string;
  each harness is closed automatically at teardown.

Pass a template string to build the app on the fly, or a pre-built app when
handlers need to close over it (action/key handlers receive an ``event``, not
the app, so they reach state through the app they were defined against):

.. code-block:: python

    from wijjit.testing import app_from_template

    def test_counter(wijjit_harness):
        app = app_from_template(
            """
            {% frame title="Counter" %}
              Count: {{ state.count }}
              {% button action="inc" %}+1{% endbutton %}
            {% endframe %}
            """,
            state={"count": 0},
        )

        @app.on_action("inc")
        def inc(event=None):
            app.state["count"] += 1

        h = wijjit_harness(app, size=(40, 8))   # started; closed at teardown
        h.press("tab").press("enter")
        h.assert_text("Count: 1")

For a view with no handlers -- just rendering state -- you can hand
``wijjit_harness`` the template string directly:
``wijjit_harness("{% frame %}{{ state.msg }}{% endframe %}", state={"msg": "hi"})``.

The plugin also defines the ``wijjit_app`` and ``wijjit_snapshot`` markers.
Fixture names are ``wijjit_``-prefixed so they never collide with fixtures in
your own suite.

Building an app from a template
-------------------------------

:func:`wijjit.testing.app_from_template` (also exported from the top-level
``wijjit`` package) builds a ready-to-drive app from a bare template string --
no example ``.py`` file needed. Pass ``state``, ``actions``, ``on_key``, and
``views`` to wire it up:

.. code-block:: python

    from wijjit.testing import app_from_template, WijjitHarness

    app = app_from_template(
        "{% frame title='T' %}{{ state.msg }}{% endframe %}",
        state={"msg": "hi"},
    )
    with WijjitHarness(app) as h:
        h.assert_text("hi")

Driving apps from the command line
----------------------------------

For quick, interactive iteration on a visual bug -- or to hand an LLM a way to
"see" a screen -- render any ``.py`` app headlessly and print the result:

.. code-block:: bash

    # via the wijjit CLI
    wijjit render examples/advanced/login_form.py \
        --size 100x30 --keys "type:admin,tab,type:secret,enter" --ansi

    # equivalent module entry point
    python -m wijjit.testing examples/widgets/spinner_demo.py --tick 5

The ``--keys`` script is a comma-separated list of steps, each one of: a named
key (``tab``, ``enter``, ``ctrl+q``, ...) or single character; ``type:TEXT`` to
type a literal string; ``click:X,Y`` to left-click a cell; or ``tick`` /
``tick:N`` to advance animation frames. Add ``--ansi`` to print the styled
screen instead of plain text, and ``--size WIDTHxHEIGHT`` to set the render
size.

To launch an app interactively in your own terminal instead, use
``wijjit run path/to/app.py``. To lint or inspect a template without driving it,
see ``wijjit validate`` and ``wijjit tree``.
