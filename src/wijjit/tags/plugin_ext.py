"""Boilerplate-free Jinja tag factory for third-party leaf elements.

:func:`make_element_extension` generates a Jinja2 ``Extension`` class for a
*leaf* plugin element from just ``(tag_name, type_name)``, reusing the same
shared helpers the built-in leaf tags use (``parse_tag_attributes``,
``apply_common_attributes``, ``get_element_marker``). A plugin author therefore
never has to hand-write the ``parse()`` / ``CallBlock`` boilerplate; they call
:func:`wijjit.plugins.register_element` with ``tag=...`` and this module does the
rest.

Scope note
----------
The generated tag builds a *leaf* VNode (``add_vnode`` + interleave marker). It
does not open a container scope, so a body between ``{% tag %}`` and
``{% endtag %}`` is consumed but its children are not attached. Custom container
plugins are a deferred follow-up.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.core.render_context import get_render_context
from wijjit.core.vdom import VNodeBuilder
from wijjit.tags.layout import (
    apply_common_attributes,
    get_element_marker,
    parse_tag_attributes,
)


def make_element_extension(
    tag_name: str,
    type_name: str,
    *,
    default_width: int | str = "auto",
    default_height: int | str = 1,
) -> type[Extension]:
    """Build a leaf-element Jinja ``Extension`` class for a plugin element.

    The returned class registers the ``{% tag_name %}`` block tag. At render
    time it builds a ``VNodeBuilder(type_name)``, forwards every template
    attribute as a prop (the element registry then filters them to the
    element's constructor signature), applies layout sizing, and emits the
    element into the layout tree.

    Parameters
    ----------
    tag_name : str
        Template tag name (e.g. ``"sparkgauge"`` -> ``{% sparkgauge %}`` /
        ``{% endsparkgauge %}``).
    type_name : str
        VNode type string the tag emits; must match the element's registration.
    default_width, default_height : int or str, optional
        Layout size used when the template does not pass ``width`` / ``height``.
        Accepts the usual specs (``int``, ``"auto"``, ``"fill"``, ``"50%"``).

    Returns
    -------
    type
        A new ``Extension`` subclass, ready to hand to ``env.add_extension``.
    """
    end_tag = f"end{tag_name}"

    class _PluginElementExtension(Extension):
        """Auto-generated leaf-element tag extension."""

        tags = {tag_name}

        def parse(self, parser: Parser) -> nodes.CallBlock:
            lineno = next(parser.stream).lineno
            kwargs = parse_tag_attributes(parser, end_tag, lineno)
            body = parser.parse_statements((f"name:{end_tag}",), drop_needle=True)
            node = nodes.CallBlock(
                self.call_method("_render", [], kwargs), [], [], body
            ).set_lineno(lineno)
            return cast(nodes.CallBlock, node)

        def _render(self, caller: Callable[[], str], **kwargs: Any) -> str:
            context = get_render_context().layout_context

            # Resolve the element id (explicit, else positional per this frame).
            element_id = kwargs.pop("id", None)
            if element_id is None:
                element_id = context.generate_id(tag_name)

            # Template width/height override the factory defaults; pop them so
            # they flow through set_layout (whose sync must win) rather than
            # being forwarded as plain props.
            width = kwargs.pop("width", default_width)
            height = kwargs.pop("height", default_height)

            vnode = VNodeBuilder(type_name, key=str(element_id))
            vnode.set_prop("id", element_id)
            apply_common_attributes(vnode, kwargs)
            vnode.set_layout(width=width, height=height)

            context.add_vnode(vnode)
            caller()  # consume the (leaf) body
            return get_element_marker(context)

    _PluginElementExtension.__name__ = f"{type_name}Extension"
    _PluginElementExtension.__qualname__ = _PluginElementExtension.__name__
    return _PluginElementExtension
