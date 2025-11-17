"""Core application components for Wijjit."""

from wijjit.core.event_loop import EventLoop
from wijjit.core.mouse_router import MouseEventRouter
from wijjit.core.overlay import LayerType, Overlay, OverlayManager
from wijjit.core.view_router import ViewConfig, ViewRouter
from wijjit.core.wiring import ElementWiringManager

__all__ = [
    "EventLoop",
    "ElementWiringManager",
    "LayerType",
    "MouseEventRouter",
    "Overlay",
    "OverlayManager",
    "ViewConfig",
    "ViewRouter",
]
