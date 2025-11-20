Wijjit Documentation
====================

Wijjit helps you build rich terminal user interfaces using the same mindset as Flask + Jinja. Views are declared with decorators, layouts use expressive template tags, and the runtime takes care of state, focus, mouse, and rendering.

Why Wijjit
----------

* **Web-style ergonomics** – register routes with ``@app.view`` and bind to state just like Flask or FastAPI.
* **Jinja-first layout system** – compose frames, stacks, inputs, and display widgets with template tags instead of manual cursor math.
* **Reactive state** – ``State`` tracks mutations, schedules renders, and keeps elements in sync automatically.
* **Full interaction model** – keyboard, mouse, focus traversal, overlays, dialogs, and notifications are provided out of the box.
* **Production features** – 40+ examples, comprehensive tests, and a renderer that understands ANSI styling and terminal constraints.

Quick Example
-------------

.. code-block:: python

    from wijjit import Wijjit

    app = Wijjit(initial_state={
        "username": "",
        "password": "",
        "status": "Please enter your credentials",
    })

    @app.view("login", default=True)
    def login_view():
        return {
            "template": """
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
            """
        }

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
   user_guide/focus_navigation
   user_guide/mouse_support
   user_guide/styling

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api_reference/core
   api_reference/state
   api_reference/events
   api_reference/layout
   api_reference/elements
   api_reference/tags

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

Wijjit is **production-ready for many console applications**. The core framework is stable and already powers advanced layouts, async workflows, and complex widgets. See :doc:`examples/index` for inspiration and :doc:`developer_guide/architecture` for a deeper dive into the runtime pipeline.

Links
-----

* **GitHub**: https://github.com/yourusername/wijjit
* **Examples**: `examples/ <https://github.com/yourusername/wijjit/tree/main/examples>`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
