Styling & Themes
================

Wijjit renders every element via a style resolver that behaves much like CSS. Understanding how styles cascade and how to override them lets you craft polished TUIs without hand-tuning ANSI escape codes.

Building blocks
---------------

* :class:`wijjit.styling.style.Style` – small dataclass describing foreground/background RGB colors plus text attributes (bold, italic, underline, dim, reverse).
* :class:`wijjit.styling.theme.Theme` – mapping from class names (``button``, ``button:focus``, ``frame.border``) to ``Style`` objects. ``DefaultTheme`` ships with sensible colors for dark terminals.
* :class:`wijjit.styling.resolver.StyleResolver` – merges base styles, pseudo-classes, and inline overrides to produce the final attributes passed to the renderer.
* :class:`wijjit.rendering.paint_context.PaintContext` – holds the resolver and exposes helper methods (``ctx.style_resolver``) to elements when drawing.

Theme lookup flow
-----------------

1. Each element passes a **base class** string when it draws, e.g. ``ctx.style_resolver.resolve_style(self, "button")``. The resolver also folds in any user CSS classes from ``element.classes``.
2. StyleResolver fetches ``theme.get_style("button")`` and merges the returned ``Style``.
3. If the element is focused/hovered/disabled/selected, additional pseudo-class entries (``button:focus``) are merged.
4. Inline overrides (``resolve_style(self, "button", inline_overrides={"fg_color": (255, 0, 0)})``) are merged last.

Changing the theme
------------------

Create a theme and pass it to the renderer:

.. code-block:: python

    from wijjit.styling.theme import Theme
    from wijjit.styling.style import Style

    neon = Theme("neon", {
        "frame": Style(fg_color=(0, 255, 200)),
        "frame:focus": Style(fg_color=(255, 105, 180), bold=True),
        "button": Style(bg_color=(255, 0, 128), fg_color=(0, 0, 0)),
        "button:hover": Style(bg_color=(255, 85, 170)),
    })

    # Register the custom Theme object, then activate it by name
    app.renderer.theme_manager.register_theme(neon)
    app.renderer.theme_manager.set_theme("neon")

The built-in themes (``"default"``, ``"dark"``, ``"light"``, ``"high_contrast"``)
are already registered, so switching to one of those is a single call:

.. code-block:: python

    app.renderer.theme_manager.set_theme("dark")

Themes can be swapped at runtime (e.g., toggle between light/dark). Elements re-render automatically because the theme change marks all dirty regions.

Inline overrides in templates
-----------------------------

Many tags accept a ``style`` or ``classes`` attribute:

.. code-block:: jinja

    {% button action="danger" style={"bg_color": (200, 0, 0)} %}Delete{% endbutton %}

You can also expose a ``class`` attribute to reuse theme entries (e.g., ``class="toolbar.button"``). Consistent naming conventions help manage large design systems.

Dynamic styling
---------------

* Derive colors from state – pass RGB tuples or bool flags to inline ``style`` based on theme preference stored in ``state``.
* Toggle pseudo-classes manually – custom elements can set ``self.focused``/``self.hovered`` to trigger ``:focus``/``:hover`` styles.
* Dark/light switching – store the current theme name in ``state.theme`` and call ``app.renderer.theme_manager.set_theme(state.theme)`` whenever it changes (register any custom ``Theme`` objects once at startup so their names are known).

Built-in style classes
----------------------

The theme system provides comprehensive style classes for all elements. Here are the key ones:

**Frame styles**::

    frame              # Base frame content
    frame:focus        # Focused frame content
    frame.border       # Frame border characters
    frame.border:focus # Focused frame border

**Scrollbar styles**::

    scrollbar          # Base scrollbar
    scrollbar:focus    # Scrollbar when parent is focused
    scrollbar.track    # Scrollbar track character
    scrollbar.track:focus
    scrollbar.thumb    # Scrollbar thumb (position indicator)
    scrollbar.thumb:focus

**Modal styles** (separate from frame for customization)::

    modal              # Modal content background
    modal:focus        # Focused modal
    modal.border       # Modal border
    modal.border:focus # Focused modal border
    modal.text         # Modal text content
    modal.backdrop     # Semi-transparent backdrop

**Input styles**::

    input              # Text input base
    input:focus        # Focused input
    input:disabled     # Disabled input
    input.placeholder  # Placeholder text (dim gray)

**Button styles**::

    button             # Base button
    button:focus       # Focused button
    button:hover       # Hovered button (mouse)
    button:disabled    # Disabled button

Global focus color
------------------

You can set a global focus color that overrides all element focus styles:

.. code-block:: python

    # Set a consistent focus color for all elements
    app.config['FOCUS_COLOR'] = (255, 128, 0)  # Orange

    # Or use the default cyan
    app.config['FOCUS_COLOR'] = (0, 255, 255)

    # Reset to theme defaults
    app.config['FOCUS_COLOR'] = None

This is particularly useful for:

* Accessibility – ensure high-visibility focus indicators
* Branding – match focus color to your application's accent color
* Consistency – same focus color across light/dark themes

Scrollbar theming
-----------------

Scrollbars in frames and text areas use dedicated styles that respond to focus state:

.. code-block:: python

    from wijjit.styling.theme import Theme
    from wijjit.styling.style import Style

    custom_theme = Theme("custom", {
        # Track (the background line)
        "scrollbar.track": Style(fg_color=(60, 60, 60)),
        "scrollbar.track:focus": Style(fg_color=(80, 80, 80)),

        # Thumb (the position indicator)
        "scrollbar.thumb": Style(fg_color=(150, 150, 150)),
        "scrollbar.thumb:focus": Style(fg_color=(0, 255, 255)),  # Cyan when focused
    })

Scrollbars can be hidden while keeping scroll functionality:

.. code-block:: jinja

    {% frame scrollable=True show_scrollbar=False %}
        Content scrolls but no scrollbar visible
    {% endframe %}

Modal vs Frame styles
---------------------

Modals use their own style prefix (``modal.*``) rather than inheriting frame styles. This allows independent customization:

.. code-block:: python

    # Frames use frame.* styles
    "frame.border": Style(fg_color=(100, 100, 100)),
    "frame.border:focus": Style(fg_color=(0, 255, 255)),

    # Modals use modal.* styles (different colors)
    "modal.border": Style(fg_color=(150, 150, 150)),
    "modal.border:focus": Style(fg_color=(255, 200, 0)),  # Gold border for modals

Placeholder text styling
------------------------

Input placeholders are styled separately from input text, appearing dimmed:

.. code-block:: python

    "input.placeholder": Style(fg_color=(128, 128, 128), dim=True)

This is automatically applied when an input shows placeholder text (when empty).

Advanced theming tips
---------------------

* Namespaces – use dotted class names (``stats.card.header``) to mimic BEM-style hierarchies.
* Share palettes – define helper functions that return consistent ``Style`` objects for colors (primary, danger, info). Store them centrally to avoid drifting shades.
* Animations – while ANSI animations are limited, you can alternate between two styles on a timer (update ``state`` + ``app.refresh_interval``) to simulate blinking cursors or progress pulses.

Testing & verification
----------------------

* Snapshot tests (via ``syrupy``) catch accidental style regressions—render a view, capture the buffer, and compare against expected output.
* Use ``make -C docs html`` to rebuild documentation whenever style-related APIs change; link to theme references for contributors.
* Check contrast ratios manually if you target accessibility; terminals vary widely in brightness/contrast.

Where to go next
----------------

* Browse ``examples/advanced/preferences_demo.py`` for a live settings palette with theme + typography toggles.
* Pair styling knowledge with :doc:`components` to craft cohesive layouts, and revisit :doc:`state_management` to drive theme toggles from user settings.
