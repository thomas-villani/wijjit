Layout API
==========

Wijjit’s layout engine converts template tags into positioned elements. The modules below govern size specifications, stacking behaviour, frames, scrolling, and dirty-region tracking.

Size & geometry
---------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.layout.bounds.Bounds
   wijjit.layout.bounds.Size
   wijjit.layout.bounds.parse_size
   wijjit.layout.bounds.parse_margin

Engine primitives
-----------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.layout.engine.LayoutNode
   wijjit.layout.engine.ElementNode
   wijjit.layout.engine.Container
   wijjit.layout.engine.VStack
   wijjit.layout.engine.HStack
   wijjit.layout.engine.SizeConstraints

Frames & scrolling
------------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.layout.frames.Frame
   wijjit.layout.frames.FrameStyle
   wijjit.layout.frames.BorderStyle
   wijjit.layout.scroll.ScrollManager
   wijjit.layout.scroll.render_vertical_scrollbar

Dirty tracking
--------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.layout.dirty.DirtyRegionManager

Module documentation
--------------------

.. automodule:: wijjit.layout.bounds
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.layout.engine
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.layout.frames
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.layout.scroll
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.layout.dirty
   :members:
   :show-inheritance:
   :noindex:
