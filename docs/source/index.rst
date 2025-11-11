Wijjit Documentation
====================

**Flask for the Console: A declarative TUI framework for Python**

*Wijjit is Just Jinja in Terminal* (a recursive acronym, like GNU)

----

Welcome to Wijjit
-----------------

Wijjit is a Python framework for building Terminal User Interfaces (TUIs) using familiar web development patterns. If you know Flask and Jinja2, you can build rich, interactive console applications with Wijjit.

Key Features
------------

* **Declarative UI**: Define layouts using Jinja2 templates, not procedural positioning code
* **Flask-like API**: View decorators, routing, and state management that feels like web development
* **Rich Component Library**: Pre-built elements for forms, tables, trees, progress indicators, and more
* **Reactive State Management**: State changes automatically trigger re-renders
* **Automatic Focus Navigation**: Tab/Shift+Tab navigation between interactive elements
* **Modal Dialogs**: Built-in confirm, alert, and input dialogs
* **Layout System**: Flexible frames with stacks (vertical/horizontal), scrolling, and sizing options
* **Mouse Support**: Click buttons, scroll content, and interact with elements
* **ANSI-Aware**: Proper handling of colors and styling throughout

Quick Example
-------------

Here's a simple login form in Wijjit:

.. code-block:: python

    from wijjit import Wijjit

    app = Wijjit(initial_state={
        'username': '',
        'password': '',
        'status': 'Please enter your credentials',
    })

    @app.view("login", default=True)
    def login_view():
        return {
            "template": """
    {% frame title="Login" border="single" width=50 height=15 %}
      {% vstack spacing=1 padding=1 %}
        {{ state.status }}

        Username:
        {% textinput id="username" placeholder="Enter username" %}{% endtextinput %}

        Password:
        {% textinput id="password" placeholder="Enter password" %}{% endtextinput %}

        {% button action="login" %}Login{% endbutton %}
      {% endvstack %}
    {% endframe %}
            """
        }

    @app.on_action("login")
    def handle_login(event):
        if app.state['username'] == 'admin':
            app.state['status'] = 'Welcome!'

    if __name__ == '__main__':
        app.run()

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

Wijjit is **production-ready for many use cases**, with the core framework fully implemented and stable. The project is approximately 70-75% complete compared to the original ambitious roadmap.

**Working Features** ✓

* Core App API with view decorator
* State management with change detection
* Template rendering with Jinja2
* Layout engine (VStack, HStack, Frame)
* All input elements (TextInput, TextArea, Button, Checkbox, Radio, Select)
* All display elements (Table, Tree, ListView, LogView, Progress, Spinner, Markdown, Code)
* Focus management with Tab navigation
* Mouse support (click, scroll, hover)
* Scrolling system with scrollbars
* Modal/overlay system with dialogs
* Event handling and dispatch
* ANSI-aware text rendering
* 40+ working examples
* Comprehensive test suite (85%+ coverage)

Links
-----

* **GitHub**: https://github.com/yourusername/wijjit
* **PyPI**: https://pypi.org/project/wijjit/ (coming soon)
* **Examples**: 40+ examples in the `examples/ <https://github.com/yourusername/wijjit/tree/main/examples>`_ directory

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
