Core API
========

The ``wijjit.core`` package glues together every subsystem in the runtime—views, rendering, events, focus, overlays, wiring, and notifications. Use this reference when extending framework behaviour or embedding Wijjit inside another application.

Application lifecycle
---------------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.core.app.Wijjit

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

Module documentation
--------------------

.. automodule:: wijjit.core.app
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.event_loop
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.view_router
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.renderer
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.focus
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.hover
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.mouse_router
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.overlay
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.notification_manager
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.wiring
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.render_context
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.vdom
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.reconciler
   :members:
   :show-inheritance:
   :noindex:

.. automodule:: wijjit.core.element_registry
   :members:
   :show-inheritance:
   :noindex:
