"""Frames inside grid colspan/rowspan cells get their borders drawn.

A span cell is a ``GridSpanWrapper`` layout node, which is not a
``Container``. The renderer's border pass only recursed into ``FrameNode``
and ``Container``, so a bordered frame inside a span cell rendered its text
with no border at all.
"""

from wijjit.layout.engine import FrameNode, GridSpanWrapper, layout_children
from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = """
{% frame title="Outer" width=40 height=16 %}
  {% grid rows=2 cols=3 %}
    {% colspan cols=2 %}
      {% frame border="double" width=20 height=3 %}Wide{% endframe %}
    {% endcolspan %}
    {% frame width=10 height=3 %}N{% endframe %}
    {% frame width=10 height=3 %}A{% endframe %}
    {% frame width=10 height=3 %}B{% endframe %}
    {% frame width=10 height=3 %}C{% endframe %}
  {% endgrid %}
  {% grid rows=2 cols=2 %}
    {% rowspan rows=2 %}
      {% frame border="double" width=10 height=6 %}Tall{% endframe %}
    {% endrowspan %}
    {% frame width=10 height=3 %}Top{% endframe %}
    {% frame width=10 height=3 %}Bot{% endframe %}
  {% endgrid %}
{% endframe %}
"""


def test_span_cell_frames_have_borders():
    with WijjitHarness(app_from_template(TEMPLATE), size=(50, 18)) as h:
        lines = h.screen().splitlines()
    wide_row = next(i for i, line in enumerate(lines) if "Wide" in line)
    # Border above, sides around, border below the colspan frame
    assert "╔" in lines[wide_row - 1] and "╗" in lines[wide_row - 1]
    assert lines[wide_row].count("║") >= 2
    assert "╚" in lines[wide_row + 1] and "╝" in lines[wide_row + 1]

    tall_row = next(i for i, line in enumerate(lines) if "Tall" in line)
    assert "╔" in lines[tall_row - 1]
    assert "╚" in lines[tall_row + 4]


def test_span_cell_frame_links_to_outer_frame():
    """The nested frame inside a span cell clips to the enclosing frame."""
    from wijjit.core.renderer import Renderer

    _, _, layout_ctx = Renderer().render_with_layout(TEMPLATE, width=50, height=18)
    root = layout_ctx.root

    def walk(node):
        yield node
        children = list(layout_children(node))
        if isinstance(node, FrameNode):
            children.append(node.content_container)
        for child in children:
            yield from walk(child)

    nodes = list(walk(root))
    outer = next(n for n in nodes if isinstance(n, FrameNode) and n.frame.style.title)
    wrapped = [n.child for n in nodes if isinstance(n, GridSpanWrapper)]
    assert len(wrapped) == 2
    for node in wrapped:
        assert isinstance(node, FrameNode)
        assert node.frame.parent_frame is outer.frame


def test_layout_children():
    from wijjit.elements.base import TextElement
    from wijjit.layout.engine import ElementNode, VStack

    leaf = ElementNode(TextElement(text="x"))
    wrapper = GridSpanWrapper(child=leaf, colspan=2)
    stack = VStack(children=[wrapper])
    assert layout_children(stack) == [wrapper]
    assert layout_children(wrapper) == [leaf]
    assert wrapper.children == [leaf]
    assert layout_children(leaf) == []
