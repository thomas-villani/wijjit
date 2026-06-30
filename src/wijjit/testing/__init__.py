"""Testing utilities for driving Wijjit apps headlessly.

This package provides a harness for running a Wijjit application without a real
terminal, feeding scripted keyboard and mouse input through the real event-loop
dispatch path, and reading back the rendered screen as plain text or ANSI.

Example
-------
>>> from wijjit import Wijjit
>>> from wijjit.testing import WijjitHarness
>>> app = Wijjit()
>>> # ... register views ...
>>> with WijjitHarness(app, size=(80, 24)) as h:
...     h.press("tab")
...     h.type("admin")
...     h.press("enter")
...     print(h.screen())
"""

from wijjit.testing.app_builder import app_from_template
from wijjit.testing.examples import (
    ExampleLoadError,
    discover_examples,
    load_example_app,
)
from wijjit.testing.harness import ScriptedInputHandler, WijjitHarness

__all__ = [
    "WijjitHarness",
    "ScriptedInputHandler",
    "app_from_template",
    "load_example_app",
    "discover_examples",
    "ExampleLoadError",
]
