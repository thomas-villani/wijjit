"""Wijjit - Flask for Terminal Applications.

A declarative TUI framework using Jinja2 templates for building
terminal user interfaces with familiar web development patterns.
"""

__version__ = "0.1.0"

# from wijjit.elements.input.button import Button
# # Core components
from wijjit.core.app import Wijjit

# from wijjit.core.events import (
#     ActionEvent,
#     ChangeEvent,
#     Event,
#     EventType,
#     FocusEvent,
#     Handler,
#     HandlerRegistry,
#     HandlerScope,
#     KeyEvent,
# )
# from wijjit.core.focus import FocusManager
# from wijjit.core.renderer import Renderer
# from wijjit.core.state import State
#
# # Elements
# from wijjit.elements.base import Container, Element, ElementType
# from wijjit.elements.input import (
#     Checkbox,
#     CheckboxGroup,
#     Radio,
#     RadioGroup,
# )
# from wijjit.elements.input.button import Button
#
# from wijjit.elements.input.text import TextArea, TextInput
#
# # Helpers
# from wijjit.helpers import load_filesystem_tree
#
# # Layout components
# from wijjit.layout.bounds import Bounds, Size, parse_size
# from wijjit.layout.frames import BorderStyle, Frame, FrameStyle
#
# # Terminal utilities
# from wijjit.terminal.ansi import (
#     ANSIColor,
#     ANSICursor,
#     ANSIScreen,
#     ANSIStyle,
#     clip_to_width,
#     colorize,
#     strip_ansi,
#     visible_length,
# )
# from wijjit.terminal.input import InputHandler, Key, Keys, KeyType
# from wijjit.terminal.screen import ScreenManager, alternate_screen

__all__ = [
    #     # Version
    #     "__version__",
    #     # Core
    #     "State",
    #     "Renderer",
    #     "FocusManager",
    "Wijjit",
    #     "ViewConfig",
    #     # Events
    #     "Event",
    #     "EventType",
    #     "KeyEvent",
    #     "ActionEvent",
    #     "ChangeEvent",
    #     "FocusEvent",
    #     "Handler",
    #     "HandlerRegistry",
    #     "HandlerScope",
    #     # Terminal - ANSI
    #     "ANSIColor",
    #     "ANSIStyle",
    #     "ANSICursor",
    #     "ANSIScreen",
    #     "strip_ansi",
    #     "visible_length",
    #     "clip_to_width",
    #     "colorize",
    #     # Terminal - Screen
    #     "ScreenManager",
    #     "alternate_screen",
    #     # Terminal - Input
    #     "InputHandler",
    #     "Key",
    #     "Keys",
    #     "KeyType",
    #     # Layout
    #     "Bounds",
    #     "Size",
    #     "parse_size",
    #     "Frame",
    #     "FrameStyle",
    #     "BorderStyle",
    #     # Elements
    #     "Element",
    #     "Container",
    #     "ElementType",
    #     "TextInput",
    #     "Button",
    #     "Checkbox",
    #     "Radio",
    #     "CheckboxGroup",
    #     "RadioGroup",
    #     "TextArea",
    #     # Helpers
    #     "load_filesystem_tree",
]
