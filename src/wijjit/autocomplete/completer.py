"""Completer classes for autocomplete functionality.

This module provides the Completer abstract base class and several
implementations for providing autocomplete suggestions.

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
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wijjit.autocomplete.utils import filter_suggestions

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit


@dataclass
class CompleterConfig:
    """Configuration for autocomplete behavior.

    Parameters
    ----------
    trigger : str
        Trigger mode: "auto" for automatic popup, "manual" for explicit
        trigger via trigger_key. Default: "manual"
    min_chars : int
        Minimum characters before auto-trigger shows popup. Only used
        when trigger="auto". Default: 1
    trigger_key : str
        Key combination for manual trigger. Default: "ctrl+/" (ctrl+space is
        intercepted or sends NUL in many terminals, so ctrl+/ is the reliable
        default; set trigger_key="ctrl+space" explicitly to use it).
    case_sensitive : bool
        Whether matching is case-sensitive. Default: False
    match_anywhere : bool
        If True, matches substring anywhere in word instead of just prefix.
        Default: False
    max_suggestions : int
        Maximum number of suggestions to display. Default: 10
    select_on_tab : bool
        Whether Tab key selects current suggestion. Default: True
    close_on_blur : bool
        Whether to close popup when input loses focus. Default: True
    """

    trigger: str = "manual"
    min_chars: int = 1
    trigger_key: str = "ctrl+/"
    case_sensitive: bool = False
    match_anywhere: bool = False
    max_suggestions: int = 10
    select_on_tab: bool = True
    close_on_blur: bool = True

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.trigger not in ("auto", "manual"):
            raise ValueError(
                f"trigger must be 'auto' or 'manual', got '{self.trigger}'"
            )
        if self.min_chars < 0:
            raise ValueError(f"min_chars must be >= 0, got {self.min_chars}")
        if self.max_suggestions < 1:
            raise ValueError(
                f"max_suggestions must be >= 1, got {self.max_suggestions}"
            )


class Completer(ABC):
    """Abstract base class for autocompleters.

    Subclasses must implement the get_suggestions() method to provide
    autocomplete suggestions based on a prefix.

    Parameters
    ----------
    **config_kwargs : Any
        Configuration options passed to CompleterConfig.

    Attributes
    ----------
    config : CompleterConfig
        Configuration for autocomplete behavior.

    Examples
    --------
    Create a simple completer:

    >>> class MyCompleter(Completer):
    ...     def get_suggestions(self, prefix, context=None):
    ...         return ["apple", "apricot"] if prefix.startswith("a") else []
    """

    def __init__(self, **config_kwargs: Any) -> None:
        self.config = CompleterConfig(**config_kwargs)

    @abstractmethod
    def get_suggestions(
        self, prefix: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Return list of suggestions for the given prefix.

        Parameters
        ----------
        prefix : str
            The word/text to complete.
        context : dict, optional
            Optional context (element state, app state, etc.).

        Returns
        -------
        list of str
            Matching suggestions, already filtered and sorted.
        """
        pass

    async def get_suggestions_async(
        self, prefix: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Async version of get_suggestions.

        Parameters
        ----------
        prefix : str
            The word/text to complete.
        context : dict, optional
            Optional context (element state, app state, etc.).

        Returns
        -------
        list of str
            Matching suggestions.

        Notes
        -----
        Default implementation calls the sync version. Override in subclasses
        that need async operations (e.g., API calls, database queries).
        """
        return self.get_suggestions(prefix, context)


class WordCompleter(Completer):
    """Completer with a static word list.

    Parameters
    ----------
    words : list of str
        List of words to use for suggestions.
    **config_kwargs : Any
        Configuration options passed to CompleterConfig.

    Attributes
    ----------
    words : list of str
        The word list for suggestions.

    Examples
    --------
    Create a word completer:

    >>> completer = WordCompleter(["apple", "apricot", "banana"])
    >>> completer.get_suggestions("ap")
    ['apple', 'apricot']

    With case-insensitive matching:

    >>> completer = WordCompleter(["Apple", "Apricot"], case_sensitive=False)
    >>> completer.get_suggestions("AP")
    ['Apple', 'Apricot']
    """

    def __init__(self, words: list[str], **config_kwargs: Any) -> None:
        super().__init__(**config_kwargs)
        self.words = words

    def get_suggestions(
        self, prefix: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Get suggestions matching the prefix.

        Parameters
        ----------
        prefix : str
            The word/text to complete.
        context : dict, optional
            Optional context (unused by WordCompleter).

        Returns
        -------
        list of str
            Matching words, up to max_suggestions.
        """
        return filter_suggestions(
            self.words,
            prefix,
            case_sensitive=self.config.case_sensitive,
            match_anywhere=self.config.match_anywhere,
            max_suggestions=self.config.max_suggestions,
        )


class CallbackCompleter(Completer):
    """Completer that calls a user-provided function.

    Parameters
    ----------
    callback : callable
        Function to call for suggestions.
        Signature: callback(prefix: str, context: dict | None) -> list[str]
    **config_kwargs : Any
        Configuration options passed to CompleterConfig.

    Attributes
    ----------
    callback : callable
        The callback function.

    Examples
    --------
    Create a callback completer:

    >>> def get_users(prefix, context):
    ...     users = ["alice", "bob", "charlie"]
    ...     return [u for u in users if u.startswith(prefix)]
    >>> completer = CallbackCompleter(get_users)
    >>> completer.get_suggestions("a")
    ['alice']
    """

    def __init__(
        self,
        callback: Callable[[str, dict[str, Any] | None], list[str]],
        **config_kwargs: Any,
    ) -> None:
        super().__init__(**config_kwargs)
        self.callback = callback

    def get_suggestions(
        self, prefix: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Get suggestions by calling the callback.

        Parameters
        ----------
        prefix : str
            The word/text to complete.
        context : dict, optional
            Optional context passed to callback.

        Returns
        -------
        list of str
            Suggestions from callback, up to max_suggestions.
        """
        results = self.callback(prefix, context)
        return results[: self.config.max_suggestions]


class AsyncCompleter(Completer):
    """Completer that calls an async function.

    Parameters
    ----------
    callback : async callable
        Async function to call for suggestions.
        Signature: async callback(prefix: str, context: dict | None) -> list[str]
    **config_kwargs : Any
        Configuration options passed to CompleterConfig.

    Attributes
    ----------
    callback : async callable
        The async callback function.

    Examples
    --------
    Create an async completer:

    >>> async def fetch_users(prefix, context):
    ...     # Simulate API call
    ...     await asyncio.sleep(0.1)
    ...     return ["alice", "bob"]
    >>> completer = AsyncCompleter(fetch_users)

    Notes
    -----
    The sync get_suggestions() method raises RuntimeError because
    AsyncCompleter requires an async context.
    """

    def __init__(
        self,
        callback: Callable[[str, dict[str, Any] | None], Awaitable[list[str]]],
        **config_kwargs: Any,
    ) -> None:
        super().__init__(**config_kwargs)
        self.callback = callback

    def get_suggestions(
        self, prefix: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Sync fallback - raises RuntimeError.

        Parameters
        ----------
        prefix : str
            The word/text to complete.
        context : dict, optional
            Optional context.

        Raises
        ------
        RuntimeError
            Always raised because AsyncCompleter requires async context.
        """
        raise RuntimeError(
            "AsyncCompleter.get_suggestions() requires async context. "
            "Use get_suggestions_async() instead."
        )

    async def get_suggestions_async(
        self, prefix: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Get suggestions asynchronously.

        Parameters
        ----------
        prefix : str
            The word/text to complete.
        context : dict, optional
            Optional context passed to callback.

        Returns
        -------
        list of str
            Suggestions from async callback, up to max_suggestions.
        """
        results = await self.callback(prefix, context)
        return results[: self.config.max_suggestions]


class StateCompleter(Completer):
    """Completer that reads word list from app.state.

    This enables dynamic word lists that update when state changes.
    The state key should contain a list of strings.

    Parameters
    ----------
    state_key : str
        Key in app.state containing the word list.
    **config_kwargs : Any
        Configuration options passed to CompleterConfig.

    Attributes
    ----------
    state_key : str
        The state key to read from.

    Examples
    --------
    Use with app.state:

    >>> app.state.tags = ["python", "javascript", "rust"]
    >>> completer = StateCompleter("tags")
    >>> completer.bind_app(app)
    >>> completer.get_suggestions("py")
    ['python']

    Notes
    -----
    The bind_app() method must be called before using the completer.
    This is typically done automatically by the framework during wiring.
    """

    def __init__(self, state_key: str, **config_kwargs: Any) -> None:
        # Default to auto-trigger for state-based completers
        if "trigger" not in config_kwargs:
            config_kwargs["trigger"] = "auto"
        if "min_chars" not in config_kwargs:
            config_kwargs["min_chars"] = 1
        super().__init__(**config_kwargs)
        self.state_key = state_key
        self._app: Wijjit | None = None

    def bind_app(self, app: Wijjit) -> None:
        """Bind to app instance.

        Parameters
        ----------
        app : Wijjit
            The app instance to read state from.

        Notes
        -----
        Called by framework during element wiring.
        """
        self._app = app

    def get_suggestions(
        self, prefix: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Get suggestions from state.

        Parameters
        ----------
        prefix : str
            The word/text to complete.
        context : dict, optional
            Optional context (unused by StateCompleter).

        Returns
        -------
        list of str
            Matching words from state, up to max_suggestions.

        Notes
        -----
        Returns empty list if:
        - App is not bound
        - State key doesn't exist
        - State value is not a list
        - Prefix is empty
        """
        if not self._app:
            return []

        # Get word list from state
        words = getattr(self._app.state, self.state_key, None)
        if not words or not isinstance(words, list):
            return []

        return filter_suggestions(
            words,
            prefix,
            case_sensitive=self.config.case_sensitive,
            match_anywhere=self.config.match_anywhere,
            max_suggestions=self.config.max_suggestions,
        )
