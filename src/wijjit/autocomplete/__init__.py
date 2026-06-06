"""Autocomplete functionality for Wijjit applications.

This module provides autocomplete/auto-suggestion popup functionality
for text input elements. It supports static word lists, dynamic callbacks,
async suggestion providers, and state-based word lists.

Classes
-------
CompleterConfig
    Configuration dataclass for autocomplete behavior.
Completer
    Abstract base class for autocompleters.
WordCompleter
    Completer with a static word list.
CallbackCompleter
    Completer that calls a user-provided function.
AsyncCompleter
    Completer that calls an async function.
StateCompleter
    Completer that reads word list from app.state.
AutocompleteState
    Tracks autocomplete popup state.

Functions
---------
get_word_at_cursor
    Extract the word at cursor position.
replace_word_at_cursor
    Replace word at cursor with replacement text.

Examples
--------
Basic usage with static word list:

>>> from wijjit.autocomplete import WordCompleter
>>> completer = WordCompleter(["apple", "apricot", "banana"])
>>> completer.get_suggestions("ap")
['apple', 'apricot']

Using in a template:

>>> # In your view function:
>>> from wijjit.autocomplete import WordCompleter
>>> fruits = WordCompleter(["apple", "apricot", "banana", "cherry"])
>>> return {"template": template, "data": {"fruit_completer": fruits}}

In template::

    {% textinput id="fruit" autocomplete=fruit_completer %}{% endtextinput %}

Dynamic suggestions with callback:

>>> from wijjit.autocomplete import CallbackCompleter
>>> def get_users(prefix, context):
...     return [u.name for u in db.query_users(prefix)]
>>> completer = CallbackCompleter(get_users)

Async suggestions:

>>> from wijjit.autocomplete import AsyncCompleter
>>> async def fetch_suggestions(prefix, context):
...     response = await api.search(prefix)
...     return [r.name for r in response.results]
>>> completer = AsyncCompleter(fetch_suggestions)

State-based dynamic list:

>>> from wijjit.autocomplete import StateCompleter
>>> # In template: autocomplete="state.available_tags"
>>> # Or programmatically:
>>> completer = StateCompleter("available_tags")
"""

from wijjit.autocomplete.completer import (
    AsyncCompleter,
    CallbackCompleter,
    Completer,
    CompleterConfig,
    StateCompleter,
    WordCompleter,
)
from wijjit.autocomplete.mixin import AutocompleteMixin
from wijjit.autocomplete.popup import AutocompletePopup
from wijjit.autocomplete.resolver import resolve_autocomplete
from wijjit.autocomplete.state import AutocompleteState
from wijjit.autocomplete.utils import get_word_at_cursor, replace_word_at_cursor

__all__ = [
    # Configuration
    "CompleterConfig",
    # Completer base and implementations
    "Completer",
    "WordCompleter",
    "CallbackCompleter",
    "AsyncCompleter",
    "StateCompleter",
    # Mixin for input elements
    "AutocompleteMixin",
    # Popup element
    "AutocompletePopup",
    # Resolver
    "resolve_autocomplete",
    # State
    "AutocompleteState",
    # Utilities
    "get_word_at_cursor",
    "replace_word_at_cursor",
]
