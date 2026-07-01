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

From PyPI (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~

Using ``uv`` — add Wijjit to an existing project, or install it into the active environment:

.. code-block:: bash

    uv add wijjit          # add to a uv-managed project's pyproject.toml
    # or
    uv pip install wijjit  # install into the current environment

Using ``pip``:

.. code-block:: bash

    pip install wijjit

``uv`` creates and manages an isolated environment (``.venv``) and reuses cached wheels for fast, reproducible installs.

From source (development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the repository and install in editable mode with the ``dev`` extra (tests, linting, types, and docs):

.. code-block:: bash

    git clone https://github.com/thomas-villani/wijjit.git
    cd wijjit
    uv sync --all-extras          # runtime + dev + images + xlsx into .venv

The equivalent with ``pip``:

.. code-block:: bash

    python -m venv .venv
    source .venv/bin/activate      # or .venv\Scripts\activate on Windows
    pip install -U pip setuptools wheel
    pip install -e ".[dev]"

This pulls in ``pytest``, ``pytest-cov``, ``ruff``, ``mypy``, ``sphinx``, ``myst-parser``, ``sphinx-copybutton``, and the other tools listed in :file:`pyproject.toml`.

Verify your environment
-----------------------

Run a smoke test and docs build:

.. code-block:: bash

    uv run pytest -m "not slow"
    uv run python -c "import wijjit; print(wijjit.__version__)"  # confirm import + version
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
* ``tinycss2`` – CSS parsing for themes/styles.
* ``wcwidth`` – correct display widths for wide/combining characters.

Optional ``images`` extra:

.. code-block:: bash

    uv add "wijjit[images]"
    # or
    pip install "wijjit[images]"

This installs ``Pillow`` to enable the ``ImageView`` element (ASCII/ANSI image rendering). From a source checkout, use ``uv sync --extra images`` or ``pip install -e ".[images]"`` instead.

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

Clipboard copy/paste uses the system clipboard via ``pyperclip``, which needs ``xclip`` or ``xsel`` installed (e.g. ``sudo apt install xclip``). Without them, Wijjit falls back to an internal in-process clipboard — copy/paste still works inside the app, just not across other programs.

macOS
~~~~~

iTerm2 offers the best experience (truecolor + inline images). Apple's default Terminal.app is also fully supported.

Troubleshooting
---------------

``ImportError: No module named 'wijjit'``
    Confirm the package is installed (``uv add wijjit`` / ``pip install wijjit``, or ``pip install -e .`` for a source checkout) and that the correct virtual environment is active.

Broken borders or glyphs
    Switch to a font with box-drawing characters (e.g., Fira Code, JetBrains Mono). On Windows, prefer Windows Terminal over ``cmd.exe``.

Slow rendering / lag
    Disable high-frequency animations, trim overly large tables, or run inside a truecolor terminal rather than nested multiplexers.

Next steps
----------

* Build your first app in :doc:`quickstart`.
* Follow the :doc:`tutorial` to assemble a complete todo list with modals.
* Dive into architectural details in :doc:`../user_guide/core_concepts`.
