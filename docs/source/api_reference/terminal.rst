Terminal API
============

The ``wijjit.terminal`` package abstracts ANSI escapes, screen buffers, keyboard/mouse input, and cursor control. Use these classes when building custom renderers or writing low-level tests.

ANSI helpers
------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.terminal.ansi.ANSIColor
   wijjit.terminal.ansi.ANSIStyle
   wijjit.terminal.ansi.ANSICursor
   wijjit.terminal.ansi.ANSIScreen
   wijjit.terminal.ansi.visible_length
   wijjit.terminal.ansi.wrap_text
   wijjit.terminal.ansi.clip_to_width
   wijjit.terminal.ansi.strip_ansi
   wijjit.terminal.ansi.colorize

Input & mouse
-------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.terminal.input.KeyType
   wijjit.terminal.input.Key
   wijjit.terminal.input.Keys
   wijjit.terminal.input.InputHandler
   wijjit.terminal.mouse.MouseEvent
   wijjit.terminal.mouse.MouseEventType
   wijjit.terminal.mouse.MouseButton
   wijjit.terminal.mouse.MouseTrackingMode
   wijjit.terminal.mouse.MouseEventParser

Screen & buffers
----------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.terminal.screen.ScreenManager
   wijjit.terminal.screen.alternate_screen
   wijjit.terminal.cell.Cell
   wijjit.terminal.cell.CellPool
   wijjit.terminal.screen_buffer.ScreenBuffer
   wijjit.terminal.screen_buffer.DiffRenderer
