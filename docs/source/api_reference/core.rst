Core API
========

The ``wijjit.core`` package glues together every subsystem in the runtime—views, rendering, events, focus, overlays, wiring, and notifications. Use this reference when extending framework behaviour or embedding Wijjit inside another application.

Application lifecycle
---------------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.core.app.Wijjit

Inline rendering
----------------

The ``wijjit.inline`` module provides APIs for rendering Wijjit templates without entering alternate screen mode. Content is output directly to terminal scrollback.

.. py:function:: wijjit.render_inline(template, *, width=None, height="auto", print_output=True, file=None, **context)

   One-shot template rendering to stdout. See :doc:`../user_guide/inline_rendering`.

.. py:class:: wijjit.InlineApp(template, *, height="auto", width=None, initial_state=None, refresh_interval=0.1, enable_input=False, quit_key="ctrl+q")

   Async context manager for interactive inline displays with reactive state.
   See :doc:`../user_guide/inline_rendering`.

Event loop & routing
--------------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.core.event_loop.EventLoop
   wijjit.core.view_router.ViewRouter
   wijjit.core.view_router.ViewConfig
   wijjit.core.renderer.Renderer
   wijjit.core.render_context.RenderContext

Virtual DOM & Reconciliation
----------------------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.core.vdom.VNode
   wijjit.core.vdom.VNodeBuilder
   wijjit.core.reconciler.Reconciler
   wijjit.core.reconciler.DiffType
   wijjit.core.element_registry.ElementRegistry

Interaction managers
--------------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.core.focus.FocusManager
   wijjit.core.hover.HoverManager
   wijjit.core.mouse_router.MouseEventRouter
   wijjit.core.overlay.OverlayManager
   wijjit.core.notification_manager.NotificationManager
   wijjit.core.wiring.ElementWiringManager

Supporting structures
---------------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.core.overlay.LayerType
   wijjit.core.overlay.Overlay
