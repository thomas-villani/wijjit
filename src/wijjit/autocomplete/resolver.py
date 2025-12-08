"""Resolve autocomplete attribute to Completer instance.

This module provides the resolve_autocomplete function which converts various
autocomplete attribute values from templates into Completer instances.

Functions
---------
resolve_autocomplete
    Resolve an autocomplete attribute value to a Completer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from wijjit.autocomplete.completer import Completer, StateCompleter, WordCompleter

if TYPE_CHECKING:
    from wijjit import Wijjit

logger = logging.getLogger(__name__)


def resolve_autocomplete(
    value: Any,
    element_id: str | None,
    app: Wijjit,
) -> Completer | None:
    """Resolve autocomplete attribute to a Completer.

    This function handles the various ways autocomplete can be specified
    in templates and converts them to a Completer instance.

    Parameters
    ----------
    value : Any
        The value of the autocomplete attribute from the template.
        Can be: list, str, bool, or Completer instance.
    element_id : str or None
        The element's ID (used for auto-wiring lookup).
    app : Wijjit
        The app instance (for completer registry and state access).

    Returns
    -------
    Completer or None
        Resolved completer, or None if autocomplete is disabled.

    Resolution Order
    ----------------
    1. None/False -> None (disabled)
    2. Completer instance -> use directly
    3. list -> WordCompleter(list)
    4. "state.key" -> StateCompleter(key)
    5. str -> lookup in app.completers
    6. True -> lookup by element ID in app.completers

    Examples
    --------
    Inline word list:

    >>> resolve_autocomplete(["apple", "banana"], "fruit", app)
    WordCompleter(["apple", "banana"])

    State reference:

    >>> resolve_autocomplete("state.tags", "tag", app)
    StateCompleter("tags")

    Named completer lookup:

    >>> app.completers["fruits"] = WordCompleter([...])
    >>> resolve_autocomplete("fruits", "input", app)
    WordCompleter(...)

    Auto-wire by element ID:

    >>> app.completers["#username"] = CallbackCompleter(...)
    >>> resolve_autocomplete(True, "username", app)
    CallbackCompleter(...)
    """
    # Disabled
    if value is None or value is False:
        return None

    # Already a Completer
    if isinstance(value, Completer):
        # Bind app if it's a StateCompleter
        if isinstance(value, StateCompleter):
            value.bind_app(app)
        return value

    # Inline word list
    if isinstance(value, (list, tuple)):
        # Filter to only string items
        words = [w for w in value if isinstance(w, str)]
        if words:
            return WordCompleter(words)
        return None

    # String: could be state reference or named completer
    if isinstance(value, str):
        # State reference: "state.key_name"
        if value.startswith("state."):
            state_key = value[6:]  # Remove "state." prefix
            completer = StateCompleter(state_key)
            completer.bind_app(app)
            return completer

        # Named completer lookup
        completers = getattr(app, "completers", {})
        if value in completers:
            completer = completers[value]
            if isinstance(completer, StateCompleter):
                completer.bind_app(app)
            return completer

        # Not found
        logger.warning(f"Autocomplete completer '{value}' not found in app.completers")
        return None

    # Boolean True: auto-wire by element ID
    if value is True:
        if not element_id:
            logger.warning("autocomplete=true requires element to have an id")
            return None

        completers = getattr(app, "completers", {})

        # Try with # prefix first, then without
        for lookup_key in [f"#{element_id}", element_id]:
            if lookup_key in completers:
                completer = completers[lookup_key]
                if isinstance(completer, StateCompleter):
                    completer.bind_app(app)
                return completer

        logger.warning(
            f"autocomplete=true but no completer registered for "
            f"'#{element_id}' or '{element_id}'"
        )
        return None

    # Unknown type
    logger.warning(f"Invalid autocomplete value type: {type(value).__name__}")
    return None
