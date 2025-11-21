Installation
============

Wijjit targets Python 3.11+ and modern terminals (Windows Terminal, iTerm2, Kitty, Alacritty, GNOME Terminal, etc.) with UTF-8 fonts that include box-drawing characters.

Requirements
------------

* Python ``>= 3.11`` (matching ``pyproject.toml``)
* A virtual environment manager (``uv`` is recommended for reproducible, cached installs)
* Build dependencies for Rich/Prompt Toolkit (standard on Linux/macOS, ``build-essential`` on Debian/Ubuntu)

Install Wijjit
--------------

Using ``uv`` (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git clone https://github.com/yourusername/wijjit.git
    cd wijjit
    uv pip install -e .

``uv`` will create an isolated environment (``.venv``) and reuse cached wheels for fast rebuilds.

Using ``pip``
~~~~~~~~~~~~~

.. code-block:: bash

    python -m venv .venv
    source .venv/bin/activate  # or .venv\Scripts\activate on Windows
    pip install -U pip setuptools wheel
    pip install -e .

Development dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

Install everything needed for tests, linting, types, and documentation:

.. code-block:: bash

    uv pip install -e ".[dev]"
    # or
    pip install -e ".[dev]"

This pulls in ``pytest``, ``pytest-cov``, ``ruff``, ``mypy``, ``sphinx``, ``myst-parser``, ``sphinx-copybutton``, and other tools listed in :file:`pyproject.toml`.

Verify your environment
-----------------------

Run a smoke test and docs build:

.. code-block:: bash

    uv run pytest -m "not slow"
    uv run python -m wijjit --version  # optional helper
    uv run make -C docs html           # ensure Sphinx extensions import correctly

You can also launch a demo:

.. code-block:: bash

    uv run python examples/basic/hello_world.py

Dependencies
------------

Core libraries installed automatically:

* ``jinja2`` – template engine for layouts.
* ``prompt-toolkit`` – keyboard/mouse input, screen buffering.
* ``rich`` – ANSI rendering utilities and colors.
* ``pyperclip`` – clipboard integration for text inputs.

Optional additions in ``.[dev]``:

* ``myst-parser`` – Markdown support in docs.
* ``sphinx-copybutton`` – quality-of-life improvements for code samples.
* Testing/tooling stack (pytest, ruff, mypy, syrupy snapshots, etc.).

Platform notes
--------------

Windows
~~~~~~~

Use Windows Terminal or another modern emulator that supports UTF-8 and mouse reporting. Older ``cmd.exe`` shells will not render rounded borders correctly.

Linux
~~~~~

Ensure locale variables are set:

.. code-block:: bash

    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8

macOS
~~~~~

iTerm2 offers the best experience (truecolor + inline images). Apple's default Terminal.app is also fully supported.

Troubleshooting
---------------

``ImportError: No module named 'wijjit'``
    Confirm the package is installed in editable mode (``pip install -e .``) and that your virtual environment is active.

Broken borders or glyphs
    Switch to a font with box-drawing characters (e.g., Fira Code, JetBrains Mono). On Windows, prefer Windows Terminal over ``cmd.exe``.

Slow rendering / lag
    Disable high-frequency animations, trim overly large tables, or run inside a truecolor terminal rather than nested multiplexers.

Next steps
----------

* Build your first app in :doc:`quickstart`.
* Follow the :doc:`tutorial` to assemble a complete todo list with modals.
* Dive into architectural details in :doc:`../user_guide/core_concepts`.
