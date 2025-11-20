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

1. Assign a **base class** to each element. Built-in widgets expose ``get_style_classes`` (e.g., ``["button", "button.label"]``). You can override this in custom elements.
2. StyleResolver fetches ``theme.get_style("button")`` and merges the returned ``Style``.
3. If the element is focused/hovered/disabled/selected, additional pseudo-class entries (``button:focus``) are merged.
4. Inline overrides (``inline_overrides={"fg_color": (255, 0, 0)}``) are merged last.

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

    app.renderer.set_theme(neon)

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
* Dark/light switching – store the current theme name in ``state.theme`` and call ``app.renderer.set_theme(THEMES[state.theme])`` whenever it changes.

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

* Browse ``examples/theme_switcher.py`` (upcoming) for a live theme palette with hot swapping.
* Pair styling knowledge with :doc:`components` to craft cohesive layouts, and revisit :doc:`state_management` to drive theme toggles from user settings.
