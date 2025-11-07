"""Wijjit - Flask for Terminal Applications.

A declarative TUI framework using Jinja2 templates for building
terminal user interfaces with familiar web development patterns.
"""

__version__ = "0.1.0"

# Core components
from .core.state import State
from .core.renderer import Renderer
from .core.focus import FocusManager
from .core.app import Wijjit, ViewConfig
from .core.events import (
    Event,
    EventType,
    KeyEvent,
    ActionEvent,
    ChangeEvent,
    FocusEvent,
    Handler,
    HandlerRegistry,
    HandlerScope,
)

# Terminal utilities
from .terminal.ansi import (
    ANSIColor,
    ANSIStyle,
    ANSICursor,
    ANSIScreen,
    strip_ansi,
    visible_length,
    clip_to_width,
    colorize,
)
from .terminal.screen import ScreenManager, alternate_screen
from .terminal.input import InputHandler, Key, Keys, KeyType

# Layout components
from .layout.bounds import Bounds, Size, parse_size
from .layout.frames import Frame, FrameStyle, BorderStyle

# Elements
from .elements.base import Element, Container, ElementType
from .elements.input import TextInput, Button

__all__ = [
    # Version
    "__version__",
    # Core
    "State",
    "Renderer",
    "FocusManager",
    "Wijjit",
    "ViewConfig",
    # Events
    "Event",
    "EventType",
    "KeyEvent",
    "ActionEvent",
    "ChangeEvent",
    "FocusEvent",
    "Handler",
    "HandlerRegistry",
    "HandlerScope",
    # Terminal - ANSI
    "ANSIColor",
    "ANSIStyle",
    "ANSICursor",
    "ANSIScreen",
    "strip_ansi",
    "visible_length",
    "clip_to_width",
    "colorize",
    # Terminal - Screen
    "ScreenManager",
    "alternate_screen",
    # Terminal - Input
    "InputHandler",
    "Key",
    "Keys",
    "KeyType",
    # Layout
    "Bounds",
    "Size",
    "parse_size",
    "Frame",
    "FrameStyle",
    "BorderStyle",
    # Elements
    "Element",
    "Container",
    "ElementType",
    "TextInput",
    "Button",
]
