Contributing
============

We welcome pull requests! This guide explains the local setup, coding standards, and review expectations so contributions land smoothly.

Environment setup
-----------------

1. Fork/clone the repository.
2. Install dependencies with ``uv`` (recommended):

   .. code-block:: bash

       uv sync --all-extras    # runtime + dev + images + xlsx into .venv

   or with ``pip``:

   .. code-block:: bash

       python -m venv .venv
       source .venv/bin/activate
       pip install -e ".[dev]"

3. Activate your environment before running commands (``source .venv/bin/activate`` or ``uv run <cmd>``).

Day-to-day commands
-------------------

* Tests: ``uv run pytest`` (see :doc:`testing` for marker breakdown).
* Lint: ``uv run ruff check src tests`` (CI gates on ``ruff check src/``).
* Format: ``uv run black src tests`` (Black is the project formatter; run it before committing).
* Type checking: ``uv run mypy src`` (CI gates on ``mypy src/`` only).
* Docs: ``uv run make -C docs html`` (requires Sphinx extras from ``.[dev]``).

Coding standards
----------------

* Python 3.11, Black-formatted with Ruff-enforced lint (line length 120). Use type hints everywhere. ``pyproject.toml`` sets ``mypy --strict`` as the goal, but a handful of modules still carry targeted per-module error-code overrides (see the ``[tool.mypy.overrides]`` blocks) while their typing is cleaned up, so the gate is "strict except where explicitly relaxed" rather than fully strict everywhere yet.
* Keep modules snake_case, classes CapWords, actions/events short verbs (``submit``, ``quit``).
* Write descriptive docstrings for new public APIs—Sphinx autodoc pulls these into the reference.
* Favor explicit imports and avoid wildcard imports.
* When editing templates, prefer declarative stacks/frames over manual spacing; keep IDs stable for focus/state wiring.

Commit & PR expectations
------------------------

* Commits should be focused and present tense (e.g., ``Add spinner demo``). Squash locally if you end up with WIP commits.
* Before opening a PR, run tests, lint, mypy, and docs build; include a checklist in the PR body describing which commands you ran.
* Provide context in the PR description: problem solved, high-level approach, any trade-offs.
* Reference related issues/design docs (``plan/`` or ``AGENTS.md``) when applicable.
* For user-facing changes (UI, docs), attach screenshots or asciinema recordings to help reviewers.

Review process
--------------

* Expect at least one subsystem-aware reviewer (core, layout, elements, terminal, etc.).
* Be ready to discuss performance (layout allocations, render cycles) and ergonomics (does the API fit existing patterns?).
* Address feedback promptly—either push fixes or provide rationale for alternative approaches.

Communicating changes
---------------------

* Update docs alongside code. E.g., new elements require updates in :doc:`../user_guide/components`, template tags in :doc:`../user_guide/templates`, etc.
* If you touch release-critical files (``src/wijjit/__init__.py``, ``docs/index.rst``), mention it in the PR summary so maintainers can prioritize review.

Need help?
----------

File an issue describing the bug/feature, or start a draft PR with questions inline. We’d rather collaborate early than rewrite late. Also consult ``CLAUDE.md`` and ``plan/`` notes for architectural decisions before proposing sweeping changes.
