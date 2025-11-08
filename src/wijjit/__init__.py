"""Wijjit - Flask for Terminal Applications.

A declarative TUI framework using Jinja2 templates for building
terminal user interfaces with familiar web development patterns.
"""

__version__ = "0.1.0"

# Core components
from .core.app import ViewConfig, Wijjit
from .core.events import (
    ActionEvent,
    ChangeEvent,
    Event,
    EventType,
    FocusEvent,
    Handler,
    HandlerRegistry,
    HandlerScope,
    KeyEvent,
)
from .core.focus import FocusManager
from .core.renderer import Renderer
from .core.state import State

# Elements
from .elements.base import Container, Element, ElementType
from .elements.input import Button, TextArea, TextInput

# Layout components
from .layout.bounds import Bounds, Size, parse_size
from .layout.frames import BorderStyle, Frame, FrameStyle

# Terminal utilities
from .terminal.ansi import (
    ANSIColor,
    ANSICursor,
    ANSIScreen,
    ANSIStyle,
    clip_to_width,
    colorize,
    strip_ansi,
    visible_length,
)
from .terminal.input import InputHandler, Key, Keys, KeyType
from .terminal.screen import ScreenManager, alternate_screen

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
    "TextArea",
]
