Testing
=======

Wijjit relies on pytest with strict markers plus mypy and Ruff to keep regressions out. This guide explains how the suites are organized and which commands to run before every pull request.

Directory layout
----------------

``tests/`` mirrors the runtime tree:

* ``tests/core`` – app lifecycle, events, routing, overlays, renderer, state.
* ``tests/layout`` – bounds/engine/frames/scroll math.
* ``tests/elements`` – each widget family (input/display/modal/menu).
* ``tests/tags`` – template extensions.
* ``tests/terminal`` – ANSI helpers, screen buffer, input devices.
* ``tests/integration`` – cross-cutting flows (render pipeline, menu wiring, template compilation).
* ``tests/e2e`` – end-to-end scripts using prompt-toolkit simulators.
* ``tests/benchmarks`` – performance checks (opt-in).

Quick commands
--------------

.. code-block:: bash

    # Default suite (unit + integration)
    uv run pytest

    # Fast smoke pass: skip slow tests
    uv run pytest -m "not slow"

    # Coverage report
    uv run pytest --cov=src/wijjit

    # Ruff + mypy (lint + types)
    uv run ruff check src tests
    uv run mypy src tests

Markers
-------

Defined in ``pytest.ini`` (strictly enforced):

* ``@pytest.mark.unit`` – default; fast focused tests.
* ``@pytest.mark.integration`` – touches multiple subsystems.
* ``@pytest.mark.e2e`` – launches near-real TUIs; slower.
* ``@pytest.mark.slow`` – >1s runtime; excluded from quick pass.
* ``@pytest.mark.visual`` – snapshot/visual regression tests (uses Syrupy).
* ``@pytest.mark.benchmark`` – performance measurements (requires ``pytest-benchmark``).

Use these markers consistently so CI jobs can target subsets.

Snapshots & visual tests
------------------------

* Syrupy snapshots live under ``tests/__snapshots__/``. Review diffs carefully; regenerate by deleting the snapshot file or using ``--snapshot-update``.
* Visual tests should focus on rendered buffers rather than string contains; this keeps regressions obvious.

Writing new tests
-----------------

1. Place the test next to the feature’s module (e.g., ``tests/core/test_overlay.py`` for overlay work).
2. Use fixtures from ``tests/conftest.py`` to bootstrap apps, screens, or templates efficiently.
3. Mock terminal I/O sparingly—prefer running through the real renderer to catch layout issues.
4. When adding a new element or tag, create both unit tests for low-level logic and integration tests to ensure it renders inside a view.
5. Keep tests deterministic: avoid sleeping unless you’re specifically testing timing; favor dependency injection for clocks/randomness.

CI expectations
---------------

Before merging, run:

.. code-block:: bash

    uv run ruff check src tests
    uv run mypy src tests
    uv run pytest -m "not slow"
    uv run pytest --cov=src/wijjit

For docs or UI-heavy changes, also run ``uv run make -C docs html`` and attach screenshots/asciicasts when updating interactions. Slow/e2e/visual suites can be run locally or in CI depending on the change magnitude—mention in the PR description if you skipped any and why.
