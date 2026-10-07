"""Containers smaller than their own chrome never hand out negative sizes.

A frame too small for its borders and padding, or a stack smaller than its
padding plus spacing, used to compute a negative interior and pass it down
to children (and to the frame's ScrollManager as the viewport). Nothing was
visibly wrong because painting clips, but negative bounds are nonsense for
anything that measures them. The interior is now clamped at zero.
"""

import pytest

from wijjit.core.renderer import Renderer
from wijjit.layout.engine import FrameNode, LayoutNode, layout_children
from wijjit.layout.scroll import ScrollManager

LINES = "\n".join(f"line {i}" for i in range(12))

TEMPLATES = {
    "tiny_frame": "{% frame width=3 height=3 %}{% text %}hello{% endtext %}{% endframe %}",
    "frame_1x1": "{% frame width=1 height=1 %}{% text %}x{% endtext %}{% endframe %}",
    "padded_frame": (
        "{% frame width=6 height=4 padding=4 %}"
        "{% text %}hello{% endtext %}{% button id='b' %}Go{% endbutton %}"
        "{% endframe %}"
    ),
    "scrollable_children": (
        "{% frame width=5 height=3 padding=2 scrollable=true %}"
        "{% vstack %}"
        + "".join(f"{{% text %}}row {i}{{% endtext %}}" for i in range(8))
        + "{% endvstack %}{% endframe %}"
    ),
    "scrollable_text": (
        "{% frame width=4 height=2 padding=(2, 2, 2, 2) scrollable=true "
        'overflow_x="auto" %}' + LINES + "{% endframe %}"
    ),
    "vstack_padding_spacing": (
        "{% vstack width=4 height=3 padding=3 spacing=2 %}"
        "{% text %}a{% endtext %}{% text %}b{% endtext %}{% text %}c{% endtext %}"
        "{% endvstack %}"
    ),
    "hstack_padding_gap": (
        "{% hstack width=4 height=2 padding=3 column_gap=2 %}"
        "{% text %}a{% endtext %}{% text %}b{% endtext %}"
        "{% endhstack %}"
    ),
    "nested": (
        "{% frame width=4 height=4 padding=1 %}"
        "{% frame height=3 %}{% vstack padding=2 %}{% text %}deep{% endtext %}"
        "{% endvstack %}{% endframe %}{% endframe %}"
    ),
}


def _walk(node: LayoutNode):
    yield node
    children = list(layout_children(node))
    if isinstance(node, FrameNode):
        children.append(node.content_container)
    for child in children:
        yield from _walk(child)


@pytest.fixture
def viewport_spy(monkeypatch):
    """Record every viewport size handed to a ScrollManager."""
    seen: list[int] = []
    original_init = ScrollManager.__init__
    original_update = ScrollManager.update_viewport_size

    def init(self, content_size, viewport_size, initial_position=0):
        seen.append(viewport_size)
        original_init(self, content_size, viewport_size, initial_position)

    def update(self, size):
        seen.append(size)
        original_update(self, size)

    monkeypatch.setattr(ScrollManager, "__init__", init)
    monkeypatch.setattr(ScrollManager, "update_viewport_size", update)
    return seen


@pytest.mark.parametrize("name", sorted(TEMPLATES))
@pytest.mark.parametrize("size", [(3, 3), (8, 6), (1, 1)])
def test_no_negative_bounds_or_viewports(name, size, viewport_spy):
    width, height = size
    renderer = Renderer()
    _, elements, layout_ctx = renderer.render_with_layout(
        TEMPLATES[name], width=width, height=height
    )
    # Re-render once so reused frames run the update paths as well
    _, elements, layout_ctx = renderer.render_with_layout(
        TEMPLATES[name], width=width, height=height
    )

    for node in _walk(layout_ctx.root):
        if node.bounds is not None:
            assert node.bounds.width >= 0, (node, node.bounds)
            assert node.bounds.height >= 0, (node, node.bounds)
    for element in elements:
        if element.bounds is not None:
            assert element.bounds.width >= 0, (element, element.bounds)
            assert element.bounds.height >= 0, (element, element.bounds)
    assert all(v >= 0 for v in viewport_spy), viewport_spy


def test_tiny_frame_child_gets_zero_not_negative():
    """The case from the bug report: a 3x3 frame with default padding."""
    _, _, layout_ctx = Renderer().render_with_layout(
        TEMPLATES["tiny_frame"], width=20, height=10
    )
    frame_node = next(n for n in _walk(layout_ctx.root) if isinstance(n, FrameNode))
    inner = frame_node.content_container.bounds
    # 3 wide - 2 borders - (1 + 1) padding would be -1
    assert inner.width == 0
    assert inner.height == 1
