"""Wijjit exception hierarchy.

All exceptions raised by Wijjit's public API derive from :class:`WijjitError`, so
applications can catch every framework error with a single ``except WijjitError``.

Where a public entry point historically surfaced a builtin exception
(``ValueError``, ``RuntimeError``), the corresponding Wijjit type *also* inherits
that builtin. Existing handlers such as ``except ValueError`` therefore keep
working unchanged, while new code can catch the more specific Wijjit type.

Examples
--------
>>> from wijjit.exceptions import WijjitError, StateKeyError
>>> try:
...     app.state["items"] = [1, 2, 3]  # reserved key
... except StateKeyError as exc:
...     print("bad state key:", exc)
"""

from __future__ import annotations


class WijjitError(Exception):
    """Base class for all Wijjit-specific exceptions."""


class StateKeyError(WijjitError, ValueError):
    """Raised when a reserved or invalid key is used on :class:`~wijjit.State`.

    Inherits :class:`ValueError` for backward compatibility with handlers written
    against Wijjit's earlier behavior.
    """


class ConfigError(WijjitError, RuntimeError):
    """Raised for configuration errors (missing env var, bad config file, ...).

    Inherits :class:`RuntimeError` for backward compatibility.
    """


class KeyBindingError(WijjitError, ValueError):
    """Raised when a key binding is invalid or reserved (e.g. binding Ctrl+Q).

    Inherits :class:`ValueError` for backward compatibility.
    """


class TemplateError(WijjitError):
    """Raised when a template fails to parse or render.

    Wraps the underlying Jinja2 exception, which remains available via
    ``__cause__``. Callers can catch template failures without importing
    :mod:`jinja2` directly.
    """


class PluginRegistrationError(WijjitError, ValueError):
    """Raised when a third-party element plugin cannot be registered.

    Covers an ``element_cls`` that is not an :class:`~wijjit.elements.base.Element`
    subclass, and type-name / tag-name collisions with a built-in or another
    plugin (unless ``override=True`` is passed to
    :func:`~wijjit.plugins.register_element`). Inherits :class:`ValueError` so
    existing ``except ValueError`` handlers around registration keep working.
    """


__all__ = [
    "WijjitError",
    "StateKeyError",
    "ConfigError",
    "KeyBindingError",
    "TemplateError",
    "PluginRegistrationError",
]
