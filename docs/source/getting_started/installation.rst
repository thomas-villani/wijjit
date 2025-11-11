Installation
============

Requirements
------------

Wijjit requires Python 3.8 or later.

Installing from Source
----------------------

Currently, Wijjit is only available from source. To install:

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/yourusername/wijjit.git
       cd wijjit

2. Install in development mode:

   Using ``uv`` (recommended):

   .. code-block:: bash

       uv pip install -e .

   Or using ``pip``:

   .. code-block:: bash

       pip install -e .

Dependencies
------------

Wijjit has the following core dependencies:

* **jinja2** (>=3.1.0) - Template engine
* **prompt-toolkit** (>=3.0) - Cross-platform terminal I/O
* **rich** (>=13.0) - ANSI rendering and tables

Optional dependencies:

* **pygments** (>=2.0) - Syntax highlighting for code blocks
* **sphinx-rtd-theme** - For building documentation

All dependencies are automatically installed when you install Wijjit.

Development Installation
------------------------

If you want to contribute to Wijjit, install the development dependencies:

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/yourusername/wijjit.git
    cd wijjit

    # Install in development mode with dev dependencies
    uv pip install -e ".[dev]"

    # Or with pip
    pip install -e ".[dev]"

This installs additional tools for testing and development:

* **pytest** - Testing framework
* **pytest-cov** - Coverage reporting
* **black** - Code formatting
* **mypy** - Type checking
* **ruff** - Linting

Verifying Installation
----------------------

To verify that Wijjit is installed correctly, try running one of the examples:

.. code-block:: bash

    python examples/hello_world.py

You should see a simple "Hello, World!" message in your terminal. Press ``q`` to quit.

Alternative: Run a quick test in Python:

.. code-block:: python

    from wijjit import Wijjit

    app = Wijjit()

    @app.view("main", default=True)
    def main_view():
        return {"template": "Wijjit is installed! Press Ctrl+C to exit."}

    app.run()

Platform-Specific Notes
-----------------------

Windows
~~~~~~~

Wijjit works on Windows using Windows Terminal or the newer Windows Console. Some Unicode box-drawing characters may not display correctly in older terminal emulators.

For best results, use:

* Windows Terminal (recommended)
* Windows 10/11 with modern console

Linux
~~~~~

Wijjit works out of the box on most Linux distributions. Ensure your terminal supports UTF-8 encoding:

.. code-block:: bash

    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8

macOS
~~~~~

Wijjit works well with iTerm2 and the default Terminal.app on macOS.

Troubleshooting
---------------

ImportError: No module named 'wijjit'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make sure you installed Wijjit in development mode with ``-e`` flag:

.. code-block:: bash

    pip install -e .

Unicode/Display Issues
~~~~~~~~~~~~~~~~~~~~~~

If you see broken characters or boxes instead of proper borders:

1. Ensure your terminal supports UTF-8
2. Check that your terminal font includes box-drawing characters
3. Try a different terminal emulator
4. On Windows, use Windows Terminal instead of cmd.exe

Performance Issues
~~~~~~~~~~~~~~~~~~

For large applications, consider:

* Limiting the number of elements rendered at once
* Using pagination for large tables/lists
* Disabling mouse support if not needed

Next Steps
----------

Now that you have Wijjit installed, check out:

* :doc:`quickstart` - Build your first Wijjit app
* :doc:`tutorial` - Step-by-step tutorial building a todo list
* :doc:`../user_guide/core_concepts` - Learn the core concepts
