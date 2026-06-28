# Creating New Elements in Wijjit

This guide documents the process of creating and integrating new UI elements into the Wijjit framework, based on lessons learned from implementing the `ImageView` element.

## Overview

Adding a new element requires:

1. **Element class** - The Python class that handles rendering and behavior
2. **Template tag extension** - Jinja2 extension for template syntax
3. **Registration** - Registering the element factory
4. **Exports** - Making the element available in the public API

## File Locations

| Component | Location |
|-----------|----------|
| Element class | `src/wijjit/elements/{category}/{name}.py` |
| Template tag | `src/wijjit/tags/{category}.py` |
| Element registry | `src/wijjit/core/element_registry.py` |
| Category exports | `src/wijjit/elements/{category}/__init__.py` |
| Renderer extensions | `src/wijjit/core/renderer.py` |
| Tests | `tests/elements/test_{name}.py` |
| Demo | `examples/widgets/{name}_demo.py` |

Categories: `display`, `input`, `layout`

## Step 1: Create the Element Class

### Basic Structure

```python
"""Element description.

This module provides the ElementName element which...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wijjit.elements.base import Element, ElementType

if TYPE_CHECKING:
    from wijjit.rendering.paint_context import PaintContext


class MyElement(Element):
    """Element for doing X.

    Parameters
    ----------
    id : str, optional
        Element identifier
    classes : str or list of str, optional
        CSS class names for styling
    width : int or str, optional
        Width specification (int, "auto", "fill", "50%")
    height : int or str, optional
        Height specification (int, "auto", "fill", "50%")
    # ... other parameters

    Attributes
    ----------
    # ... document public attributes
    """

    def __init__(
        self,
        id: str | None = None,
        classes: str | list[str] | None = None,
        width: int | str | None = None,
        height: int | str | None = None,
        # ... other parameters
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.element_type = ElementType.DISPLAY  # or INPUT
        self.focusable = False  # True for interactive elements

        # Store sizing specs for intrinsic size calculation
        self.width_spec = width
        self.height_spec = height

        # Element-specific attributes
        # ...

    def get_intrinsic_size(self) -> tuple[int, int]:
        """Get the intrinsic (preferred) size of the element.

        Returns
        -------
        tuple of (int, int)
            (width, height) in characters/lines

        Notes
        -----
        This is called by the layout engine to determine how much
        space the element needs when sizing is set to "auto".
        """
        # Calculate based on content and specs
        return (width, height)

    def render_to(self, ctx: "PaintContext") -> None:
        """Render the element to the paint context.

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds
        """
        # Use ctx.bounds to know where to render
        # Use ctx.write_cell(x, y, cell) to write content
        pass
```

### Important: Sizing Specs

If your element accepts `width` and `height` parameters, store them as instance attributes (e.g., `self.width_spec`, `self.height_spec`). These are used by `get_intrinsic_size()` to calculate the element's preferred size.

The layout engine will pass the `width` and `height` from the template's layout specs to your element's constructor automatically (see "How Layout Specs Work" below).

### Intrinsic Size Calculation

The `get_intrinsic_size()` method is critical for proper layout. It should return the natural size of the element based on:

1. Explicit size specs (if width=30 is specified, use 30)
2. Content-derived size (if width="auto", calculate from content)
3. Reasonable defaults for missing content

Example from ImageView:

```python
def get_intrinsic_size(self) -> tuple[int, int]:
    if self.width_spec is not None and isinstance(self.width_spec, int):
        width = self.width_spec
        # Calculate height from aspect ratio
        height = int(width / aspect_ratio)
    elif self.height_spec is not None and isinstance(self.height_spec, int):
        height = self.height_spec
        # Calculate width from aspect ratio
        width = int(height * aspect_ratio)
    else:
        # Use natural size
        width, height = self._calculate_natural_size()

    return (max(1, width), max(1, height))
```

## Step 2: Create the Template Tag Extension

### Basic Structure

```python
class MyElementExtension(Extension):
    """Jinja2 extension for {% myelement %} tag.

    Syntax:
        {% myelement id="foo" width=30 %}{% endmyelement %}
    """

    tags = {"myelement"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        lineno = next(parser.stream).lineno
        kwargs = parse_tag_attributes(parser, "endmyelement", lineno)

        node = nodes.CallBlock(
            self.call_method("_render_myelement", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endmyelement",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_myelement(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        width: int | str = "auto",
        height: int | str = "auto",
        # ... other parameters
        **kwargs: Any,
    ) -> str:
        # Get layout context
        render_ctx = get_render_context()
        context = render_ctx.layout_context

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("myelement")

        # Build VNode
        vnode = VNodeBuilder("MyElement", key=id)

        # Set element-specific props
        vnode.set_prop("some_prop", some_value)

        # IMPORTANT: Set layout specs for width/height
        # These will be merged with props and passed to the element constructor
        vnode.set_layout(width=width, height=height)

        context.add_vnode(vnode)

        # Consume body (if element has content)
        caller()

        # Return marker for text interleaving
        return get_element_marker(context)
```

### Key Points

1. **Use `set_layout()` for sizing**: Call `vnode.set_layout(width=..., height=...)` to pass sizing specs. Width and height are **automatically synced to props**, so elements receive them as constructor parameters.

2. **Use `set_prop()` for element-specific properties**: Call `vnode.set_prop("name", value)` for properties that aren't layout-related.

3. **Return the element marker**: Always return `get_element_marker(context)` so the element is properly positioned in the parent's children list.

4. **Different layout vs element dimensions**: If your element needs different values for layout dimensions (e.g., with borders) vs internal dimensions, set the internal dimensions with `set_prop()` BEFORE calling `set_layout()`. The auto-sync only applies if the prop isn't already set.

```python
# Example: Element with borders where layout includes border space
vnode.set_prop("width", inner_width)   # Internal working width
vnode.set_prop("height", inner_height) # Internal working height
vnode.set_layout(width=inner_width + 2, height=inner_height + 2)  # Layout includes borders
```

## Step 3: Register the Element

### In `element_registry.py`

Add the element factory to the registry's `__init__`:

```python
from wijjit.elements.display.myelement import MyElement

# In ElementRegistry.__init__:
self._factories["MyElement"] = MyElement
```

### In the category's `__init__.py`

Export the element from its category module:

```python
# In src/wijjit/elements/display/__init__.py
from wijjit.elements.display.myelement import MyElement

__all__ = [
    # ... existing exports
    "MyElement",
]
```

### In `renderer.py`

Register the template extension:

```python
from wijjit.tags.display import MyElementExtension

# In Renderer.__init__, add to extensions list:
extensions=[
    # ... existing extensions
    MyElementExtension,
]
```

## How Layout Specs Work

Understanding how layout specs flow from template to element is crucial:

1. **Template parsing**: `{% myelement width=30 %}` calls `_render_myelement(width=30)`

2. **VNode creation**: Extension calls `vnode.set_layout(width=30, height="auto")`
   - This stores `{"width": 30, "height": "auto"}` in `vnode.layout_spec`
   - **Auto-sync**: Width and height are automatically copied to `vnode.props` (if not already set)

3. **Element creation**: `ElementRegistry.create_element(vnode)` is called
   - Props already contain width/height from auto-sync
   - Filters to only params accepted by the element's `__init__`
   - Calls `MyElement(width=30, height="auto", ...)`

4. **Layout calculation**: Layout engine calls `element.get_intrinsic_size()`
   - Element uses `self.width_spec` and `self.height_spec` to calculate size

5. **Bounds assignment**: Layout engine assigns bounds based on intrinsic size
   - Element receives bounds via `set_bounds()`
   - `render_to()` uses `ctx.bounds` to know where to render

## Common Pitfalls

### 1. Layout specs not reaching the element

**Problem**: Element's `width_spec`/`height_spec` are `None` even though template specifies them.

**Solution**: Use `vnode.set_layout(width=..., height=...)` - it automatically syncs width/height to props. If you're setting different values for element vs layout (e.g., for borders), set the element dimensions with `set_prop()` BEFORE calling `set_layout()`.

### 2. Element stretched to fill container

**Problem**: Element fills entire container instead of using intrinsic size.

**Solution**:
- Ensure `get_intrinsic_size()` returns the correct size
- The layout engine respects intrinsic sizes for elements with `height="auto"` (the default)
- Only elements with `height="fill"` get stretched

### 3. Wrong intrinsic size calculation

**Problem**: Element doesn't respect specified width/height.

**Solution**: Check that `get_intrinsic_size()` properly handles:
- `width_spec` is an int (use it directly)
- `width_spec` is "auto" or None (calculate from content)
- `width_spec` is "fill" (return minimum reasonable size)

## Testing New Elements

Create comprehensive tests in `tests/elements/test_myelement.py`:

```python
class TestMyElementInitialization:
    """Test element initialization."""

    def test_default_initialization(self):
        elem = MyElement()
        assert elem.width_spec is None
        assert elem.height_spec is None

    def test_custom_initialization(self):
        elem = MyElement(width=30, height=20)
        assert elem.width_spec == 30
        assert elem.height_spec == 20


class TestMyElementIntrinsicSize:
    """Test intrinsic size calculations."""

    def test_intrinsic_size_with_width_spec(self):
        elem = MyElement(width=30)
        size = elem.get_intrinsic_size()
        assert size[0] == 30
        # height should be calculated appropriately


class TestMyElementRendering:
    """Test rendering."""

    def test_render_produces_output(self):
        elem = MyElement(...)
        elem.set_bounds(Bounds(0, 0, 30, 10))
        output = render_element(elem, width=30, height=10)
        assert len(output) > 0
```

## Example: ImageView Implementation

For a complete example, see:

- Element: `src/wijjit/elements/display/image.py`
- Template tag: `src/wijjit/tags/display.py` (ImageViewExtension)
- Tests: `tests/elements/test_imageview.py`
- Demo: `examples/widgets/imageview_demo.py`

Key lessons from ImageView:

1. Store `width_spec` and `height_spec` as instance attributes
2. Use them in `get_intrinsic_size()` to calculate proper dimensions
3. Consider aspect ratio preservation when only one dimension is specified
4. Clamp to reasonable maximums to prevent layout issues
5. Handle missing content gracefully (placeholder rendering)
