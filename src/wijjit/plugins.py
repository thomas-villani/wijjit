"""Public plugin seam for third-party Wijjit elements.

This module is the process-global source of truth for third-party UI element
registrations, so a widget can be shipped as a separate pip-installable package
without editing framework internals or monkeypatching. A registration couples a
VNode *type name* (consumed by :class:`~wijjit.core.element_registry.ElementRegistry`)
with an optional Jinja *tag* (a ``{% mytag %}`` template extension) and optional
type-name aliases.

Because both underlying registries are built *per Renderer* (a fresh
``ElementRegistry`` and a fresh Jinja ``Environment`` are created in
``Renderer.__init__``, and the devtools validator builds its own), a plugin
cannot be injected into one live instance. Instead every new registry / renderer
drains this global registry at construction, so the app renderer *and* the
validator pick plugins up automatically.

Registration surfaces
----------------------
- :func:`register_element` - the canonical call a plugin package makes at import
  time (module level), so entry-point discovery works.
- :func:`element` - decorator sugar over :func:`register_element`.
- ``Wijjit.register_element`` - an instance method (see
  :mod:`wijjit.core.app`) that also live-patches an already-constructed app.

Discovery
---------
An installed package declares an entry point under the ``wijjit.plugins`` group
(mirroring the ``pytest11`` precedent); :func:`ensure_plugins_loaded` imports
each declared module once so its top-level :func:`register_element` calls run.

Scope
-----
v1 supports *leaf* elements (self-closing / simple-body widgets). Custom
*containers* (which need layout-tree-builder and validator integration) are a
deferred follow-up.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wijjit.exceptions import PluginRegistrationError
from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from jinja2.ext import Extension

    from wijjit.elements.base import Element

logger = get_logger(__name__)


@dataclass(frozen=True)
class ElementPlugin:
    """One third-party element registration.

    Attributes
    ----------
    type_name : str
        The VNode type string the tag emits and the element registry maps to
        ``element_cls``.
    element_cls : type
        The :class:`~wijjit.elements.base.Element` subclass to instantiate.
    aliases : tuple of str
        Extra type-name aliases that also resolve to ``element_cls``.
    extension : type or None
        The Jinja2 ``Extension`` class providing the ``{% tag %}``, or ``None``
        for a class-only registration (usable via a hand-built VNode but with no
        template tag).
    tag_name : str or None
        The primary template tag name, for introspection.
    override_builtin : bool
        Whether this registration was allowed to shadow a built-in name.
    source : str
        ``"runtime"`` for a direct call, or the entry-point name for a
        discovered plugin.
    """

    type_name: str
    element_cls: type[Element]
    aliases: tuple[str, ...] = ()
    extension: type[Extension] | None = None
    tag_name: str | None = None
    override_builtin: bool = False
    source: str = "runtime"

    def names(self) -> tuple[str, ...]:
        """Return the type name plus all aliases."""
        return (self.type_name, *self.aliases)


# Ordered list of registered plugins (drain order is registration order).
_PLUGIN_LIST: list[ElementPlugin] = []
# name -> plugin lookup (type_name and every alias key the same plugin).
_PLUGINS_BY_NAME: dict[str, ElementPlugin] = {}
# Deduplicated tag-extension classes, in registration order.
_EXTENSIONS: list[type[Extension]] = []
# Whether entry-point discovery has run this process.
_discovered: bool = False
# Lazily computed built-in collision sets (never change at runtime).
_builtin_type_names: frozenset[str] | None = None
_builtin_tag_names: frozenset[str] | None = None


def _get_builtin_type_names() -> frozenset[str]:
    """Return the built-in VNode type names (cached), for collision checks."""
    global _builtin_type_names
    if _builtin_type_names is None:
        from wijjit.core.element_registry import builtin_type_names

        _builtin_type_names = builtin_type_names()
    return _builtin_type_names


def _get_builtin_tag_names() -> frozenset[str]:
    """Return the built-in Jinja tag names (cached), for collision checks."""
    global _builtin_tag_names
    if _builtin_tag_names is None:
        from wijjit.core.renderer import builtin_tag_names

        _builtin_tag_names = builtin_tag_names()
    return _builtin_tag_names


def _extension_tag_names(ext_cls: type[Extension]) -> set[str]:
    """Return the tag names declared by an extension class."""
    return set(getattr(ext_cls, "tags", ()) or ())


def _same_source(a: type, b: type) -> bool:
    """Whether two classes are "the same" element from a reload perspective.

    A plugin module re-executed (a reload, or a test harness re-running a demo
    file) produces a fresh class *object* with the same ``__module__`` and
    ``__qualname__`` as the original. Treating that as a collision would make an
    innocent reload crash, so it is instead handled as an idempotent refresh.
    """
    return getattr(a, "__module__", None) == getattr(b, "__module__", None) and getattr(
        a, "__qualname__", None
    ) == getattr(b, "__qualname__", None)


def _remove_plugin(plugin: ElementPlugin) -> None:
    """Remove a plugin and its (unshared) extension from the global registry."""
    if plugin in _PLUGIN_LIST:
        _PLUGIN_LIST.remove(plugin)
    for name in plugin.names():
        if _PLUGINS_BY_NAME.get(name) is plugin:
            del _PLUGINS_BY_NAME[name]
    ext = plugin.extension
    if ext is not None and ext in _EXTENSIONS:
        still_used = any(p.extension is ext for p in _PLUGIN_LIST)
        if not still_used:
            _EXTENSIONS.remove(ext)


def register_element(
    type_name: str,
    element_cls: type[Element],
    *,
    tag: str | None = None,
    aliases: Sequence[str] = (),
    extension: type[Extension] | None = None,
    override: bool = False,
    source: str = "runtime",
) -> None:
    """Register a third-party element (and optionally its template tag).

    Parameters
    ----------
    type_name : str
        The VNode type string for the element (e.g. ``"SparkGauge"``).
    element_cls : type
        The :class:`~wijjit.elements.base.Element` subclass to instantiate.
    tag : str, optional
        A template tag name to synthesize (e.g. ``"sparkgauge"`` ->
        ``{% sparkgauge %}``). When given and ``extension`` is ``None``, a leaf
        tag extension is generated via
        :func:`wijjit.tags.plugin_ext.make_element_extension`.
    aliases : sequence of str, optional
        Extra type-name aliases that also resolve to ``element_cls``.
    extension : type, optional
        A hand-written Jinja2 ``Extension`` class to use instead of a
        synthesized one (advanced). Honored over ``tag`` for the tag machinery,
        but ``tag`` is still recorded for introspection.
    override : bool, optional
        Allow shadowing a built-in or previously-registered name / tag. Off by
        default so collisions raise loudly.
    source : str, optional
        Provenance label; discovery sets this to the entry-point name.

    Raises
    ------
    PluginRegistrationError
        If ``element_cls`` is not an ``Element`` subclass, or a type name / tag
        collides with a built-in or another plugin and ``override`` is not set.
    """
    from wijjit.elements.base import Element

    if not (isinstance(element_cls, type) and issubclass(element_cls, Element)):
        raise PluginRegistrationError(
            f"element_cls for {type_name!r} must be a subclass of "
            f"wijjit.elements.base.Element, got {element_cls!r}"
        )

    alias_tuple = tuple(aliases)
    names = (type_name, *alias_tuple)

    # Idempotency: re-registering the identical (type_name, class) is a no-op,
    # and re-registering the same-named class from the same source module (a
    # reload / re-exec producing a fresh class object) transparently refreshes
    # the registration rather than colliding with itself.
    existing = _PLUGINS_BY_NAME.get(type_name)
    if existing is not None and not override:
        if existing.element_cls is element_cls:
            logger.debug(
                "Element plugin %r already registered; ignoring duplicate", type_name
            )
            return
        if _same_source(existing.element_cls, element_cls):
            logger.debug(
                "Re-registering element plugin %r from the same source (reload)",
                type_name,
            )
            _remove_plugin(existing)

    if override:
        # Drop any plugin currently occupying one of these names so the new one
        # cleanly replaces it (extension included).
        for name in names:
            old = _PLUGINS_BY_NAME.get(name)
            if old is not None:
                _remove_plugin(old)

    builtin_types = _get_builtin_type_names()
    for name in names:
        if name in builtin_types and not override:
            raise PluginRegistrationError(
                f"type name {name!r} collides with a built-in element; pass "
                f"override=True to shadow it (advanced)"
            )
        other = _PLUGINS_BY_NAME.get(name)
        if other is not None and other.element_cls is not element_cls and not override:
            raise PluginRegistrationError(
                f"type name {name!r} is already registered by another plugin "
                f"({other.element_cls!r}); pass override=True to replace it"
            )

    # Resolve the tag extension.
    ext_cls = extension
    resolved_tag = tag
    if ext_cls is None and tag is not None:
        from wijjit.tags.plugin_ext import make_element_extension

        ext_cls = make_element_extension(tag, type_name)

    if ext_cls is not None:
        tag_names = _extension_tag_names(ext_cls)
        if resolved_tag is None and tag_names:
            resolved_tag = sorted(tag_names)[0]
        builtin_tags = _get_builtin_tag_names()
        for tname in tag_names:
            if tname in builtin_tags and not override:
                raise PluginRegistrationError(
                    f"tag {tname!r} collides with a built-in tag; pass "
                    f"override=True to shadow it (advanced)"
                )
            for plugin in _PLUGIN_LIST:
                if (
                    plugin.extension is not None
                    and plugin.extension is not ext_cls
                    and tname in _extension_tag_names(plugin.extension)
                    and not override
                ):
                    raise PluginRegistrationError(
                        f"tag {tname!r} is already registered by plugin "
                        f"{plugin.type_name!r}; pass override=True to replace it"
                    )

    plugin = ElementPlugin(
        type_name=type_name,
        element_cls=element_cls,
        aliases=alias_tuple,
        extension=ext_cls,
        tag_name=resolved_tag,
        override_builtin=override,
        source=source,
    )
    _PLUGIN_LIST.append(plugin)
    for name in names:
        _PLUGINS_BY_NAME[name] = plugin
    if ext_cls is not None and ext_cls not in _EXTENSIONS:
        _EXTENSIONS.append(ext_cls)
    logger.debug(
        "Registered element plugin %r (tag=%r, aliases=%r)",
        type_name,
        resolved_tag,
        alias_tuple,
    )


def element(
    type_name: str | None = None,
    *,
    tag: str | None = None,
    aliases: Sequence[str] = (),
    override: bool = False,
) -> Callable[[type[Element]], type[Element]]:
    """Class decorator that registers the decorated element.

    Parameters
    ----------
    type_name : str, optional
        VNode type name; defaults to the decorated class's ``__name__``.
    tag : str, optional
        Template tag name to synthesize (see :func:`register_element`).
    aliases : sequence of str, optional
        Extra type-name aliases.
    override : bool, optional
        Allow shadowing a built-in / existing registration.

    Returns
    -------
    Callable
        A decorator returning the class unchanged.

    Examples
    --------
    >>> from wijjit import element, Element
    >>> @element("SparkGauge", tag="sparkgauge")
    ... class SparkGauge(Element):
    ...     def render_to(self, ctx):
    ...         ...
    """

    def decorator(cls: type[Element]) -> type[Element]:
        register_element(
            type_name or cls.__name__,
            cls,
            tag=tag,
            aliases=aliases,
            override=override,
        )
        return cls

    return decorator


def registered_plugins() -> list[ElementPlugin]:
    """Return a snapshot of all registered element plugins, in registration order."""
    return list(_PLUGIN_LIST)


def plugin_extensions() -> list[type[Extension]]:
    """Return a snapshot of all registered plugin tag-extension classes."""
    return list(_EXTENSIONS)


def clear_plugins() -> None:
    """Remove all registered plugins and reset discovery (test/reset hook)."""
    global _discovered
    _PLUGIN_LIST.clear()
    _PLUGINS_BY_NAME.clear()
    _EXTENSIONS.clear()
    _discovered = False


def ensure_plugins_loaded() -> None:
    """Run entry-point discovery once per process (idempotent, cheap after first)."""
    global _discovered
    if _discovered:
        return
    # Set the flag first: a broken plugin must not cause a re-scan loop, and a
    # re-entrant construction during discovery must short-circuit.
    _discovered = True
    _load_entry_point_plugins()


def _load_entry_point_plugins() -> None:
    """Import every module declared under the ``wijjit.plugins`` entry-point group.

    Importing a plugin module runs its top-level :func:`register_element` calls
    (the same side-effect model as pytest's ``pytest11`` plugins). One broken
    plugin is logged and skipped; it never prevents the framework or the other
    plugins from loading.
    """
    from importlib.metadata import entry_points

    try:
        eps = entry_points(group="wijjit.plugins")
    except Exception as exc:  # metadata backend hiccup - never fatal
        logger.warning("Failed to enumerate 'wijjit.plugins' entry points: %s", exc)
        return

    for ep in eps:
        try:
            ep.load()
        except Exception as exc:  # one broken plugin must not break wijjit
            logger.warning("Failed to load wijjit plugin %r: %s", ep.name, exc)


__all__ = [
    "ElementPlugin",
    "register_element",
    "element",
    "registered_plugins",
    "plugin_extensions",
    "ensure_plugins_loaded",
    "clear_plugins",
]
