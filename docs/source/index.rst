Wijjit Documentation
====================

Wijjit helps you build rich terminal user interfaces using the same mindset as Flask + Jinja. Views are declared with decorators, layouts use expressive template tags, and the runtime takes care of state, focus, mouse, and rendering.

.. image:: https://raw.githubusercontent.com/thomas-villani/wijjit/main/docs/assets/screenshots/charts.svg
   :alt: Wijjit charts demo: sparklines, gauges, bar/column/line charts and a heatmap rendered in the terminal
   :width: 850
   :align: center

How Wijjit compares
-------------------

The Python terminal-UI space already has excellent tools. Wijjit is deliberately a different point on the spectrum:

* `Rich <https://github.com/Textualize/rich>`_ is for *output* — beautiful styled text, tables, and progress bars printed to the terminal. Wijjit uses Rich internally for exactly that, then adds a full interactive application layer on top (focus, events, overlays, re-rendering).
* `Textual <https://github.com/Textualize/textual>`_ is a full app framework built around object-oriented widgets composed in Python and styled with a CSS-like language. It is powerful and deep.
* **Wijjit** takes the *web* mental model instead of the widget-tree one: you write **Jinja2 templates** for layout and **Flask-style decorators** (``@app.view``, ``@app.on_action``, ``@app.on_key``) for behavior, backed by reactive ``State``.

If you think in templates and request handlers rather than widget classes, Wijjit will feel like home.

Why Wijjit
----------

* **Web-style ergonomics** – register routes with ``@app.view`` and bind to state just like Flask or FastAPI.
* **Jinja-first layout system** – compose frames, stacks, inputs, and display widgets with template tags instead of manual cursor math.
* **Reactive state** – ``State`` tracks mutations, schedules renders, and keeps elements in sync automatically.
* **Full interaction model** – keyboard, mouse, focus traversal, overlays, dialogs, and notifications are provided out of the box.
* **Cheap updates** – a virtual-DOM reconciler diffs re-renders into a cell buffer, so a changed widget writes a few dozen bytes instead of repainting the screen. See :doc:`user_guide/performance`.
* **Built to be tested** – a headless harness drives real apps without a TTY, plus a ``wijjit`` CLI to validate templates and dump the render tree.
* **Production features** – 72 runnable examples and roughly 3,000 tests across Linux, macOS, and Windows on Python 3.11–3.13.

Quick Example
-------------

.. code-block:: python

    from wijjit import Wijjit, render_template_string

    app = Wijjit(initial_state={
        "username": "",
        "password": "",
        "status": "Please enter your credentials",
    })

    @app.view("login", default=True)
    def login_view():
        return render_template_string("""
    {% frame title="Login" border="single" width=50 %}
      {% vstack spacing=1 padding=1 %}
        {{ state.status }}

        Username:
        {% textinput id="username" placeholder="Enter username" width=30 %}{% endtextinput %}

        Password:
        {% textinput id="password" placeholder="Enter password" width=30 action="login" %}{% endtextinput %}

        {% hstack spacing=2 %}
          {% button action="login" %}Login{% endbutton %}
          {% button action="quit"  %}Quit{% endbutton %}
        {% endhstack %}
      {% endvstack %}
    {% endframe %}
            """)

    @app.on_action("login")
    def handle_login(event):
        if app.state["username"] == "admin" and app.state["password"] == "password":
            app.state["status"] = "Welcome!"
        else:
            app.state["status"] = "Try admin/password"
            app.state["password"] = ""

    @app.on_action("quit")
    def handle_quit(event):
        app.quit()

    if __name__ == "__main__":
        app.run()

Next steps:

* :doc:`getting_started/quickstart` – walkthrough of views, state, and actions.
* :doc:`user_guide/core_concepts` – architecture, data flow, and lifecycle.
* :doc:`examples/index` – gallery of runnable demos.

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/tutorial
   getting_started/tutorial_chatbot
   getting_started/tutorial_spreadsheet

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/core_concepts
   user_guide/state_management
   user_guide/templates
   user_guide/event_handling
   user_guide/layout_system
   user_guide/components
   user_guide/modal_dialogs
   user_guide/inline_rendering
   user_guide/focus_navigation
   user_guide/mouse_support
   user_guide/styling
   user_guide/configuration
   user_guide/testing_apps
   user_guide/performance

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api_reference/core
   api_reference/config
   api_reference/state
   api_reference/events
   api_reference/layout
   api_reference/elements
   api_reference/tags
   api_reference/terminal
   api_reference/rendering
   api_reference/styling
   api_reference/helpers

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/index
   examples/cookbook

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   developer_guide/architecture
   developer_guide/contributing
   developer_guide/testing

Project Status
--------------

Wijjit is at its **first public release (0.1.0)** and is stable and feature-complete for that milestone. The core framework already powers advanced layouts, async workflows, and complex widgets, with a set of documented known limitations tracked for follow-up releases. See :doc:`examples/index` for inspiration and :doc:`developer_guide/architecture` for a deeper dive into the runtime pipeline.

Known limitations for 0.1.0:

* **No virtual scrolling** — every row of a ``Table``, ``ListView``, or ``Tree`` is laid out on each render. Page or filter very large datasets before rendering them.
* **Wide characters render at single width** — the screen buffer models one cell per column, so CJK text and emoji can misalign.
* **No plugin system and no hot template reload** — both are on the roadmap.

Links
-----

* **GitHub**: https://github.com/thomas-villani/wijjit
* **PyPI**: https://pypi.org/project/wijjit/
* **Changelog**: `CHANGELOG.md <https://github.com/thomas-villani/wijjit/blob/main/CHANGELOG.md>`_
* **Examples**: `examples/ <https://github.com/thomas-villani/wijjit/tree/main/examples>`_
* **Issues**: https://github.com/thomas-villani/wijjit/issues

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
