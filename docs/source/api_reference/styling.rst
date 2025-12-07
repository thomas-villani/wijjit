Styling API
===========

Style and theme management live in ``wijjit.styling``. These classes determine how elements look and how overrides cascade.

Overview
--------

The styling system provides:

* **Theme-based styling**: 4 built-in themes (default, dark, light, high_contrast) with 150+ style definitions
* **Pseudo-class support**: ``:focus``, ``:hover``, ``:disabled``, ``:checked``, ``:selected``
* **Scrollbar theming**: Separate styles for ``scrollbar.track`` and ``scrollbar.thumb`` with focus states
* **Modal-specific styles**: Modals use ``modal.*`` styles instead of inheriting from frames
* **Placeholder styling**: Input placeholders use ``input.placeholder`` style (dim gray)
* **Global focus color**: Set ``FOCUS_COLOR`` config to override all focus styles

Key style classes
~~~~~~~~~~~~~~~~~

::

    # Frame and scrollbar
    frame, frame:focus, frame.border, frame.border:focus
    scrollbar.track, scrollbar.track:focus
    scrollbar.thumb, scrollbar.thumb:focus

    # Modal (separate from frame)
    modal, modal:focus, modal.border, modal.border:focus, modal.text

    # Input
    input, input:focus, input:disabled, input.placeholder

    # Button
    button, button:focus, button:hover, button:disabled

Key classes
-----------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.styling.style.Style
   wijjit.styling.resolver.StyleResolver
   wijjit.styling.theme.Theme
   wijjit.styling.theme.DefaultTheme
   wijjit.styling.theme.ThemeManager

Module documentation
--------------------

.. automodule:: wijjit.styling.style
   :members:
   :noindex:

.. automodule:: wijjit.styling.resolver
   :members:
   :noindex:

.. automodule:: wijjit.styling.theme
   :members:
   :noindex:
