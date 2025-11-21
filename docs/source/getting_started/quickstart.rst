Quick Start
===========

This guide will get you building your first Wijjit application in just a few minutes.

Hello World
-----------

Let's start with the simplest possible Wijjit app:

.. code-block:: python

    from wijjit import Wijjit
    from wijjit.core.events import EventType, HandlerScope

    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        return {
            "template": "Hello, World! Press 'q' to quit.",
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        def on_quit(event):
            if event.key == "q":
                app.quit()

        app.on(EventType.KEY, on_quit, scope=HandlerScope.VIEW, view_name="main")

    if __name__ == "__main__":
        app.run()

Save this as ``hello.py`` and run it:

.. code-block:: bash

    python hello.py

You should see "Hello, World!" displayed in your terminal. Press ``q`` to quit.

Understanding the Code
~~~~~~~~~~~~~~~~~~~~~~

Let's break down what's happening:

1. **Import Wijjit**: ``from wijjit import Wijjit`` imports the main app class
2. **Create app**: ``app = Wijjit()`` creates a new Wijjit application
3. **Define view**: ``@app.view("main", default=True)`` decorates a function that defines the main view
4. **Return template**: The view function returns a dict with a ``template`` key containing the UI
5. **Setup handlers**: The ``on_enter`` hook sets up keyboard handlers when the view is entered
6. **Run app**: ``app.run()`` starts the event loop

Adding a Frame
--------------

Let's add a border around our text using a frame:

.. code-block:: python

    from wijjit import Wijjit
    from wijjit.core.events import EventType, HandlerScope

    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        return {
            "template": """
    {% frame title="Welcome" border="rounded" width=50 height=10 %}
      Hello, World!

      This is a Wijjit TUI application.

      Press 'q' to quit.
    {% endframe %}
            """,
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        def on_quit(event):
            if event.key == "q":
                app.quit()

        app.on(EventType.KEY, on_quit, scope=HandlerScope.VIEW, view_name="main")

    if __name__ == "__main__":
        app.run()

Now the text is displayed inside a rounded box with a title!

Adding State and Input
----------------------

Let's create an interactive app with a text input and button:

.. code-block:: python

    from wijjit import Wijjit

    app = Wijjit(initial_state={
        'name': '',
        'greeting': 'Please enter your name'
    })

    @app.view("main", default=True)
    def main_view():
        return {
            "template": """
    {% frame title="Greeting App" border="single" width=60 height=12 %}
      {% vstack spacing=1 padding=1 %}
        {{ state.greeting }}

        {% vstack spacing=0 %}
          Your name:
          {% textinput id="name" placeholder="Enter your name" width=30 %}{% endtextinput %}
        {% endvstack %}

        {% hstack spacing=2 %}
          {% button action="greet" %}Greet Me{% endbutton %}
          {% button action="quit" %}Quit{% endbutton %}
        {% endhstack %}
      {% endvstack %}
    {% endframe %}
            """
        }

    @app.on_action("greet")
    def handle_greet(event):
        name = app.state.get('name', '').strip()
        if name:
            app.state['greeting'] = f"Hello, {name}! Nice to meet you!"
        else:
            app.state['greeting'] = "Please enter your name first"

    @app.on_action("quit")
    def handle_quit(event):
        app.quit()

    if __name__ == '__main__':
        app.run()

Key Concepts Demonstrated
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **State Management**: ``initial_state`` sets up reactive state
2. **Templates**: Jinja2 templates with custom tags (``frame``, ``vstack``, ``textinput``, ``button``)
3. **State Binding**: The ``textinput`` with ``id="name"`` automatically binds to ``app.state['name']``
4. **Actions**: Buttons trigger actions that are handled by ``@app.on_action()`` decorators
5. **Reactivity**: Changing ``app.state['greeting']`` automatically re-renders the UI

Login Form Example
------------------

Here's a complete login form with validation:

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

        {% vstack spacing=0 %}
          Username:
          {% textinput id="username" placeholder="Enter username" width=30 %}{% endtextinput %}
        {% endvstack %}

        {% vstack spacing=0 %}
          Password:
          {% textinput id="password" placeholder="Enter password" width=30 action="login" %}{% endtextinput %}
        {% endvstack %}

        {% hstack spacing=2 %}
          {% button action="login" %}Login{% endbutton %}
          {% button action="clear" %}Clear{% endbutton %}
          {% button action="quit" %}Quit{% endbutton %}
        {% endhstack %}
      {% endvstack %}
    {% endframe %}
            """
        }

    @app.on_action("login")
    def handle_login(event):
        username = app.state.get('username', '')
        password = app.state.get('password', '')

        if not username:
            app.state['status'] = 'Error: Username is required'
        elif not password:
            app.state['status'] = 'Error: Password is required'
        elif username == 'admin' and password == 'password':
            app.state['status'] = f'Success! Welcome, {username}!'
        else:
            app.state['status'] = 'Error: Invalid credentials'
            app.state['password'] = ''  # Clear password on failed login

    @app.on_action("clear")
    def handle_clear(event):
        app.state['username'] = ''
        app.state['password'] = ''
        app.state['status'] = 'Form cleared'

    @app.on_action("quit")
    def handle_quit(event):
        app.quit()

    if __name__ == '__main__':
        app.run()

Try logging in with:
* Username: ``admin``
* Password: ``password``

Features Shown
~~~~~~~~~~~~~~

* Form validation
* Error messages
* Multiple buttons with different actions
* Clearing form data
* Focus navigation (press Tab to move between fields)
* Enter key in password field triggers login action

Common Patterns
---------------

Keyboard Shortcuts
~~~~~~~~~~~~~~~~~~

Add custom keyboard shortcuts:

.. code-block:: python

    @app.on_key("ctrl+s")
    def save(event):
        # Save logic here
        pass

    @app.on_key("ctrl+q")
    def quit_app(event):
        app.quit()

Navigation Between Views
~~~~~~~~~~~~~~~~~~~~~~~~~

Create multiple views and navigate between them:

.. code-block:: python

    @app.view("home", default=True)
    def home_view():
        return {
            "template": """
    {% button action="go_to_settings" %}Settings{% endbutton %}
            """
        }

    @app.view("settings")
    def settings_view():
        return {
            "template": """
    Settings Page
    {% button action="go_home" %}Back to Home{% endbutton %}
            """
        }

    @app.on_action("go_to_settings")
    def go_to_settings(event):
        app.navigate("settings")

    @app.on_action("go_home")
    def go_home(event):
        app.navigate("home")

Working with Lists
~~~~~~~~~~~~~~~~~~

Display and interact with lists of data:

.. code-block:: python

    app = Wijjit(initial_state={
        'items': ['Apple', 'Banana', 'Cherry'],
        'selected': None
    })

    @app.view("main", default=True)
    def main_view():
        items_text = '\n'.join(f"- {item}" for item in app.state['items'])
        return {
            "template": f"""
    {% frame title="Items" %}
      {items_text}
    {% endframe %}
            """
        }

Next Steps
----------

Now that you've built your first Wijjit apps, you can:

* Follow the :doc:`tutorial` to build a complete todo list application
* Learn about :doc:`../user_guide/core_concepts` in depth
* Explore the :doc:`../user_guide/components` available in Wijjit
* Check out the :doc:`../examples/index` for more complex applications

Where to Go From Here
---------------------

* **Tutorial**: :doc:`tutorial` - Build a complete todo list app
* **User Guide**: :doc:`../user_guide/core_concepts` - Deep dive into Wijjit concepts
* **Examples**: 40+ runnable scripts under ``examples/basic``, ``examples/widgets``, and ``examples/advanced``
* **API Reference**: :doc:`../api_reference/core` - Detailed API documentation
