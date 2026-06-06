Rendering API
=============

``wijjit.rendering`` sits between the layout engine and the terminal. It converts style information into cells and handles ANSI diffing.

Key classes
-----------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.rendering.paint_context.PaintContext
   wijjit.rendering.ansi_adapter.ansi_string_to_cells
   wijjit.rendering.ansi_adapter.cells_to_ansi
