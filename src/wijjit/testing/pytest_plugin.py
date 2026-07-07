"""Pytest plugin exposing Wijjit test-runner fixtures.

Registered as a ``pytest11`` entry point (see ``pyproject.toml``), so once
``wijjit`` is installed the fixtures and markers below are available in any test
suite with no ``conftest.py`` wiring. Opt out per-run with ``-p no:wijjit``.

Fixtures
--------
wijjit_make_app
    Factory building a :class:`~wijjit.core.app.Wijjit` from a template string
    (via :func:`~wijjit.testing.app_builder.app_from_template`) or returning a
    provided app.
wijjit_harness
    Factory building a started :class:`~wijjit.testing.harness.WijjitHarness`
    from an app or template; each harness is closed automatically at teardown.

Fixture names are ``wijjit_``-prefixed so they never shadow a fixture in the
host project's own test suite.

Markers
-------
wijjit_app
    Marks a test that drives a Wijjit app.
wijjit_snapshot
    Marks a Wijjit screen-snapshot test.

Notes
-----
The heavy framework imports (:class:`~wijjit.core.app.Wijjit`,
:func:`~wijjit.testing.app_builder.app_from_template`,
:class:`~wijjit.testing.harness.WijjitHarness`) are deferred into the fixture
bodies. This plugin auto-loads for *every* pytest run on a machine with wijjit
installed, so importing the framework (and prompt_toolkit) at module import time
would add startup cost to unrelated test suites.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit
    from wijjit.testing.harness import WijjitHarness


def pytest_configure(config: pytest.Config) -> None:
    """Register Wijjit markers so ``--strict-markers`` accepts them."""
    config.addinivalue_line(
        "markers", "wijjit_app: mark a test that drives a Wijjit app"
    )
    config.addinivalue_line(
        "markers", "wijjit_snapshot: mark a Wijjit screen-snapshot test"
    )


@pytest.fixture
def wijjit_make_app() -> Callable[..., Wijjit]:
    """Return a factory that builds (or passes through) a Wijjit app.

    Returns
    -------
    callable
        ``make(template=None, *, app=None, **kwargs) -> Wijjit``. With ``app``
        set, returns it unchanged; otherwise builds one from ``template`` via
        :func:`~wijjit.testing.app_builder.app_from_template` (``kwargs`` are
        forwarded).
    """
    from wijjit.testing.app_builder import app_from_template

    def _make(
        template: str | None = None, *, app: Wijjit | None = None, **kwargs: Any
    ) -> Wijjit:
        if app is not None:
            return app
        if template is None:
            raise ValueError("wijjit_make_app() requires either a template or an app.")
        return app_from_template(template, **kwargs)

    return _make


@pytest.fixture
def wijjit_harness(
    wijjit_make_app: Callable[..., Wijjit],
) -> Iterator[Callable[..., WijjitHarness]]:
    """Return a factory for started harnesses, closed at teardown.

    Returns
    -------
    callable
        ``drive(app_or_template, *, size=(80, 24), **kwargs) -> WijjitHarness``.
        Accepts a :class:`~wijjit.core.app.Wijjit` or a template string; extra
        ``kwargs`` are forwarded to :func:`app_from_template` when building from
        a template.
    """
    from wijjit.core.app import Wijjit
    from wijjit.testing.harness import WijjitHarness

    started: list[WijjitHarness] = []

    def _drive(
        app_or_template: Wijjit | str,
        *,
        size: tuple[int, int] = (80, 24),
        **kwargs: Any,
    ) -> WijjitHarness:
        if isinstance(app_or_template, Wijjit):
            app = app_or_template
        else:
            app = wijjit_make_app(app_or_template, **kwargs)
        driver = WijjitHarness(app, size=size).start()
        started.append(driver)
        return driver

    yield _drive

    for driver in started:
        driver.close()
